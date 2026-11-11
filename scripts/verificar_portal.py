"""Verificación del portal con Playwright: pruebas e2e de humo, teclado, accesibilidad, tema oscuro y móvil.

Levanta (con --arrancar) SU PROPIA API en el puerto 8002 y SU PROPIO portal en el 5182, sobre una COPIA de la
base indicada con --db y una configuración nueva en una carpeta temporal (DQC_EN_VIVO=0, sin GCP: se descarta
toda variable DQC_* del entorno). No toca data/dq*.duckdb ni data/config_local.json. Sin --arrancar usa los
servidores que ya estén levantados (--api-url y --web-url).

Comprobaciones (cada una PASS o FAIL con su detalle; el código de salida es 1 si alguna falla):
  a  Inicio de sesión: carga, un solo mensaje genérico con clave equivocada, entra con la correcta.
  b  Roles: el menú muestra 7 secciones al lector y a gobierno, y 11 al administrador; un lector no ve nada
     de administración en /usuarios y la API le responde 403 en /api/v1/reglas y /api/v1/admin/usuarios.
  c  Resumen: título, «Lectura rápida», 5 sellos y el deslizador de días con ArrowLeft/ArrowRight.
  d  Teclado: «Saltar al contenido» es el primer Tab y lleva el foco a <main>; foco visible en los primeros 20 Tab
     de cada pantalla; sin trampas de foco; Esc cierra el recorrido guiado y el detalle de una regla y devuelve
     el foco; el mapa de días tiene un Tab por fila y se recorre con flechas.
  e  Nombres accesibles (árbol de accesibilidad de Chromium): todo botón, enlace, campo y gráfico con nombre,
     toda img con alt, sin ids repetidos, un h1 y un main por pantalla.
  f  Contraste WCAG (texto contra fondo efectivo) en claro y en oscuro: 4,5:1 (3:1 desde 24 px, o 19 px en
     negrita). Si el fondo es un degradado o una imagen, el elemento queda como INDETERMINADO y se informa aparte
     (con una estimación por muestreo de píxeles, que no cuenta como fallo).
  g  Móvil de 390 px: ninguna pantalla desborda en horizontal, en claro y en oscuro.
  h  Movimiento reducido: sin animaciones en curso salvo el indicador «En vivo».
  i  Sin errores de consola, excepciones de página ni respuestas 4xx/5xx inesperadas (los 401 buscados en (a)
     se descartan de forma explícita).

Las «pantallas» son las 11 secciones del administrador, /clave y /entrar.

  python scripts/verificar_portal.py --arrancar                      # completo: capturas oscuras + evidencia
  python scripts/verificar_portal.py --arrancar --rapido --db data/ci.duckdb   # lo que corre el CI (sin capturas)
  python scripts/verificar_portal.py --api-url http://127.0.0.1:8000 --web-url http://127.0.0.1:5173
  python scripts/verificar_portal.py --arrancar --rapido --solo f,g  # solo algunas comprobaciones

Sin --rapido guarda capturas a página completa en tema oscuro (docs/evidencias/portal/oscuro) y escribe
docs/evidencias/accesibilidad-y-e2e.txt (lo que haya después de «=== NOTAS (manuales) ===» se conserva).
Siempre deja el resultado y los registros de los servidores en --artefactos (por defecto data/verificar_portal),
más una captura de cada pantalla que falle.

Las funciones puras (colores, contraste, umbrales, informe) no arrancan nada y las prueba
tests/test_verificar_portal.py. Playwright solo se importa al correr el navegador:
pip install playwright && playwright install chromium (y `npm ci` en web/).
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from importlib import metadata
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parents[1]
HOST = "127.0.0.1"
PUERTO_API, PUERTO_WEB = 8002, 5182
CLAVE = "SmartDQ-2026"
ADMIN, GOBIERNO, LECTOR = "admin@demo.local", "gobierno@demo.local", "lector@demo.local"
ROLES = {"admin": ADMIN, "gobierno": GOBIERNO, "lector": LECTOR}
DIA_POR_DEFECTO = "2026-08-07"  # una tabla no certificada y de las tres clases de estado
ESCRITORIO = {"width": 1440, "height": 900}
MOVIL = {"width": 390, "height": 844}
TABS = 20
PACIENCIA = {"red": 15_000, "esqueletos": 10_000, "animaciones": 6_000, "fuentes": 8_000}  # ms que se espera en cada carga
MARCA_NOTAS = "=== NOTAS (manuales) ==="


@dataclass(frozen=True)
class Pantalla:
    clave: str
    ruta: str
    publica: bool = False
    con_dia: bool = False  # usa el día elegido (corte) del portal


SECCIONES = (
    Pantalla("resumen", "/resumen", con_dia=True),
    Pantalla("validaciones", "/validaciones", con_dia=True),
    Pantalla("certificacion", "/certificacion", con_dia=True),
    Pantalla("fuentes", "/fuentes"),
    Pantalla("contratos", "/contratos"),
    Pantalla("linaje", "/linaje/persona"),
    Pantalla("glosario", "/glosario"),
    Pantalla("reglas", "/reglas"),
    Pantalla("ejecuciones", "/ejecuciones"),
    Pantalla("usuarios", "/usuarios"),
    Pantalla("auditoria", "/auditoria"),
)
PANTALLAS = (*SECCIONES, Pantalla("clave", "/clave"), Pantalla("entrar", "/entrar", publica=True))
NOMBRES = {
    "a": "Inicio de sesión", "b": "Roles y permisos", "c": "Resumen", "d": "Teclado y foco",
    "e": "Nombres accesibles", "f": "Contraste WCAG", "g": "Móvil 390 px sin desborde",
    "h": "Movimiento reducido", "i": "Consola, excepciones y 4xx/5xx",
}

# Excepciones documentadas de las comprobaciones (falsos positivos y criterios de medición). Se listan en la evidencia.
EXCEPCIONES: list[str] = [
    "- (d) Foco visible: vale un outline, un box-shadow o un cambio de borde que aparezca al enfocar, en el propio elemento o en uno de sus 3 "
    "contenedores más cercanos. Motivo: los campos de búsqueda (Glosario, Linaje, Reglas) quitan el outline del input y dibujan el foco en su "
    "contenedor (.buscar:focus-within: borde de marca y anillo); la primera versión de la comprobación los daba por invisibles (falso positivo). "
    "Se lee el estilo cuando terminan las transiciones de 0,12 s del foco.",
    "- (f) Contraste: el rótulo curvo de los sellos (text.anillo > textPath, 8,6 px) se mide contra el disco del propio sello (--*-suave), no "
    "contra lo que haya detrás: la caja de un texto en curva cubre todo el sello y el muestreo de píxeles daba 3,4:1 por mezclar el fondo de la página.",
    "- (f) Contraste: no se miden los controles desactivados (:disabled, aria-disabled), el texto solo para lector de pantalla "
    "(.visualmente-oculto), lo que está fuera de la pantalla (el enlace «Saltar al contenido» hasta recibir el foco) ni lo recortado por un "
    "ancestro con overflow hidden. «¿Cómo se lee?» se abre antes de medir para que su texto también cuente.",
    "- (i) Consola y red: no cuentan los fallos de recursos externos (las fuentes de Google) ni el websocket de recarga en caliente de Vite "
    "(ws://…/?token=…, que solo existe en el servidor de desarrollo y en Windows puede fallar con ERR_NO_BUFFER_SPACE al abrir cientos de "
    "páginas seguidas); ambos se cuentan en las notas de (i).",
]


# ══ Parte pura: colores y contraste (WCAG 2.x) ═════════════════════════════════════════════════════════════


def _numero(texto: str) -> float | None:
    """Un número CSS, con o sin %: «50%» vale 0,5 (y en rgb() 127,5, de eso se encarga el llamador)."""
    texto = texto.strip()
    try:
        return float(texto[:-1]) / 100 if texto.endswith("%") else float(texto)
    except ValueError:
        return None


def parsear_color(texto: str) -> tuple[float, float, float, float] | None:
    """Interpreta un color CSS y devuelve (r, g, b, a): r, g y b de 0 a 255, a de 0 a 1.

    Entiende rgb()/rgba() (con comas o con espacios y «/ alfa», números o porcentajes), color(srgb r g b / a),
    #rgb, #rgba, #rrggbb, #rrggbbaa y transparent. Si no lo entiende devuelve None (el llamador lo trata como
    indeterminado, nunca como aprobado).
    """
    if not isinstance(texto, str):
        return None
    t = texto.strip().lower()
    if t == "transparent":
        return (0.0, 0.0, 0.0, 0.0)
    if (m := re.fullmatch(r"#([0-9a-f]+)", t)) and len(m.group(1)) in (3, 4, 6, 8):
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        return (float(r), float(g), float(b), int(h[6:8], 16) / 255 if len(h) == 8 else 1.0)
    if m := re.fullmatch(r"rgba?\((.*)\)", t):
        partes = [p for p in re.split(r"[\s,/]+", m.group(1).strip()) if p]
        por_canal = 1.0  # rgb(): los números ya van de 0 a 255 (y 50% vale 127,5, por _numero)
    elif m := re.fullmatch(r"color\(\s*srgb\s+(.*)\)", t):
        partes = [p for p in re.split(r"[\s/]+", m.group(1).strip()) if p]
        por_canal = 255.0  # color(srgb ...): los números van de 0 a 1
    else:
        return None
    if len(partes) not in (3, 4):
        return None
    canales: list[float] = []
    for p in partes[:3]:
        v = _numero(p)
        if v is None:
            return None
        canales.append(v * 255 if p.endswith("%") else v * por_canal)
    alfa = 1.0
    if len(partes) == 4:
        a = _numero(partes[3])
        if a is None:
            return None
        alfa = a
    r, g, b = (min(255.0, max(0.0, c)) for c in canales)
    return (r, g, b, min(1.0, max(0.0, alfa)))


def luminancia(rgb: tuple[float, float, float]) -> float:
    """Luminancia relativa WCAG de un color sRGB (canales de 0 a 255)."""
    def lineal(canal: float) -> float:
        c = canal / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (lineal(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def razon_contraste(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    """Razón de contraste WCAG entre dos colores opacos: de 1 (iguales) a 21 (blanco sobre negro)."""
    claro, oscuro = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (claro + 0.05) / (oscuro + 0.05)


def componer(frente: tuple[float, float, float, float], fondo: tuple[float, float, float]) -> tuple[float, float, float]:
    """Color opaco que resulta de poner `frente` (con su alfa) sobre un `fondo` opaco."""
    a = frente[3]
    return tuple(frente[i] * a + fondo[i] * (1 - a) for i in range(3))  # type: ignore[return-value]


def umbral_para(tamano_px: float, peso: int) -> float:
    """3:1 para el texto grande (24 px, o 19 px en negrita) y 4,5:1 para el resto."""
    return 3.0 if tamano_px >= 24 or (tamano_px >= 19 and peso >= 700) else 4.5


@dataclass(frozen=True)
class Medida:
    estado: str  # "ok", "falla" o "indeterminado"
    razon: float | None
    umbral: float
    texto: tuple[float, float, float] | None = None
    fondo: tuple[float, float, float] | None = None
    motivo: str = ""


def medir_contraste(color: str, capas: list[dict], tamano: float, peso: int, opacidad: float = 1.0) -> Medida:
    """Contraste de un texto contra su fondo efectivo.

    `capas` va del elemento hacia la raíz: cada una con `bg` (color de fondo), `img` (su background-image, o
    None) y `sel` (para el informe). Se suben las capas hasta la primera opaca y se componen de abajo hacia
    arriba. Si antes aparece una imagen o un degradado, el fondo es INDETERMINADO.
    """
    umbral = umbral_para(tamano, peso)
    pila: list[tuple[float, float, float, float]] = []
    for capa in capas:
        if capa.get("img"):
            return Medida("indeterminado", None, umbral, motivo=f"fondo con degradado o imagen en {capa.get('sel') or '?'}")
        c = parsear_color(capa.get("bg", ""))
        if c is None:
            return Medida("indeterminado", None, umbral, motivo=f"color de fondo que no se entiende: {capa.get('bg')!r}")
        if c[3] <= 0:
            continue
        pila.append(c)
        if c[3] >= 0.999:
            break
    fondo: tuple[float, float, float] = (255.0, 255.0, 255.0)  # sin capa opaca: el lienzo blanco del navegador
    for c in reversed(pila):
        fondo = componer(c, fondo)
    t = parsear_color(color)
    if t is None:
        return Medida("indeterminado", None, umbral, motivo=f"color de texto que no se entiende: {color!r}")
    alfa = t[3] * opacidad
    if alfa <= 0:
        return Medida("indeterminado", None, umbral, motivo="texto transparente (¿relleno con recorte de fondo?)")
    texto = componer((t[0], t[1], t[2], alfa), fondo)
    razon = razon_contraste(texto, fondo)
    return Medida("ok" if razon >= umbral else "falla", razon, umbral, texto, fondo)


def hexa(rgb: tuple[float, float, float] | None) -> str:
    return "?" if rgb is None else "#" + "".join(f"{round(c):02x}" for c in rgb)


def _ratio(valor: float | None) -> str:
    return "?" if valor is None else f"{valor:.2f}".replace(".", ",") + ":1"


# ══ Resultados ═════════════════════════════════════════════════════════════════════════════════════════════


@dataclass
class Sub:
    ok: bool
    texto: str
    observado: str = ""
    grupo: str = ""  # las verificaciones que se repiten en cada pantalla comparten grupo y texto
    donde: str = ""  # la pantalla (y su tema) de esta repetición


@dataclass
class Comprobacion:
    clave: str
    nombre: str
    subs: list[Sub] = field(default_factory=list)
    notas: list[str] = field(default_factory=list)
    resumen: str = ""
    error: str | None = None
    ejecutada: bool = False

    def ok(self, condicion: object, texto: str, observado: str = "", grupo: str = "", donde: str = "") -> bool:
        self.subs.append(Sub(bool(condicion), texto, observado, grupo, donde))
        return bool(condicion)

    @property
    def fallas(self) -> list[Sub]:
        return [s for s in self.subs if not s.ok]

    @property
    def estado(self) -> str:
        if not self.ejecutada:
            return "OMITIDA"
        return "FAIL" if self.error or self.fallas or not self.subs else "PASS"


def informe(comprobaciones: list[Comprobacion], cabecera: list[str] | None = None, indeterminados: list[str] | None = None,
            excepciones: list[str] | None = None) -> str:
    """Texto plano: cabecera, tabla de comprobaciones, el detalle de cada una y lo indeterminado."""
    lineas = list(cabecera or [])
    if lineas:
        lineas.append("")
    lineas += ["TABLA DE COMPROBACIONES", "-" * 23, f"{'':<2}{'Comprobación':<34}{'Resultado':<10}Detalle"]
    for c in comprobaciones:
        buenas = sum(s.ok for s in c.subs)
        detalle = "no se corrió en esta ejecución" if c.estado == "OMITIDA" else c.resumen or f"{buenas}/{len(c.subs)} verificaciones"
        lineas.append(f"{c.clave:<2}{c.nombre:<34}{c.estado:<10}{detalle}")
    lineas += ["", "DETALLE", "-" * 7]
    for c in comprobaciones:
        lineas.append(f"({c.clave}) {c.nombre}: {c.estado}")
        if c.error:
            lineas.append(f"    ERROR: {c.error}")
        impresos: set[str] = set()
        for s in c.subs:
            if not s.grupo:
                lineas.append(f"    [{'PASS' if s.ok else 'FAIL'}] {s.texto}" + (f" -> {s.observado}" if s.observado else ""))
                continue
            if s.grupo in impresos:
                continue
            impresos.add(s.grupo)
            miembros = [m for m in c.subs if m.grupo == s.grupo]
            buenos = [m for m in miembros if m.ok]
            if buenos:  # lo que cumple se resume en una línea; lo que falla va aparte, con lo observado
                lineas.append(f"    [PASS] {s.texto} ({len(buenos)}/{len(miembros)}: {', '.join(m.donde for m in buenos)})")
            for m in miembros:
                if not m.ok:
                    lineas.append(f"    [FAIL] {m.donde}: {m.texto}" + (f" -> {m.observado}" if m.observado else ""))
        for n in c.notas:
            lineas.append(f"    nota: {n}")
        lineas.append("")
    if indeterminados is not None:
        lineas += ["CONTRASTE INDETERMINADO (fondo con degradado o imagen; no cuenta como fallo)", "-" * 70]
        lineas += indeterminados or ["Ninguno."]
        lineas.append("")
    if excepciones:
        lineas += ["EXCEPCIONES DOCUMENTADAS DE LAS COMPROBACIONES", "-" * 46, *excepciones, ""]
    return "\n".join(lineas)


# ══ Servidores ═════════════════════════════════════════════════════════════════════════════════════════════


def puerto_ocupado(puerto: int) -> bool:
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex((HOST, puerto)) == 0


def esperar(url: str, segundos: float = 120) -> None:
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        try:
            urllib.request.urlopen(url, timeout=3).read()
            return
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            time.sleep(1)
    raise SystemExit(f"{url} no respondió en {segundos:.0f} s")


MARCA_DE_SALIDA = ".verificar_portal"


def borrar_carpeta_de_salida(ruta: Path) -> None:
    """Borra la carpeta de salida de una corrida anterior, y solo si lo es: dentro de data/ (nunca data/ misma) o con la
    marca que deja este script. Así `--artefactos .` o `--artefactos data` no borran nada que no sea suyo."""
    ruta = ruta.resolve()
    datos = (RAIZ / "data").resolve()
    suya = ruta != datos and ruta.is_relative_to(datos) or (ruta / MARCA_DE_SALIDA).exists()
    if not suya:
        raise SystemExit(
            f"No borro {ruta}: no es una carpeta de salida de este script (ni está dentro de data/, ni tiene {MARCA_DE_SALIDA}). "
            "Usa otra carpeta en --artefactos o bórrala tú."
        )
    shutil.rmtree(ruta)


class Servidores:
    """Su propia API y su propio portal; se apagan siempre, también si algo falla."""

    def __init__(self, base: Path, registros: Path):
        self.base = base
        self.registros = registros
        self.carpeta = Path(tempfile.mkdtemp(prefix="dqc-verificar-"))
        self.procesos: list[subprocess.Popen] = []
        self.api = f"http://{HOST}:{PUERTO_API}"
        self.web = f"http://{HOST}:{PUERTO_WEB}"

    def _lanzar(self, orden: list[str], cwd: Path, entorno: dict, registro: str) -> subprocess.Popen:
        self.registros.mkdir(parents=True, exist_ok=True)
        salida = open(self.registros / registro, "wb")  # noqa: SIM115 - vive lo que el proceso
        extra = {"start_new_session": True} if os.name != "nt" else {}
        proceso = subprocess.Popen(orden, cwd=cwd, env=entorno, stdout=salida, stderr=subprocess.STDOUT, **extra)
        self.procesos.append(proceso)
        return proceso

    def arrancar(self) -> None:
        for puerto in (PUERTO_API, PUERTO_WEB):
            if puerto_ocupado(puerto):
                raise SystemExit(f"El puerto {puerto} está ocupado (¿otra verificación en marcha?). Ciérrala y repite.")
        if not self.base.exists():
            raise SystemExit(f"No existe la base {self.base}. Genérala con python -m dqc.pipeline --db {self.base}")
        shutil.copy(self.base, self.carpeta / "dq.duckdb")
        wal = Path(str(self.base) + ".wal")  # lo que DuckDB aún no consolidó en el archivo
        if wal.exists():
            shutil.copy(wal, self.carpeta / "dq.duckdb.wal")
        entorno = {k: v for k, v in os.environ.items() if not k.startswith("DQC_")}  # nada de GCP ni de otras demos
        entorno.update(
            DQC_MODO="local", DQC_DB=str(self.carpeta / "dq.duckdb"), DQC_CONFIG_LOCAL=str(self.carpeta / "config_local.json"),
            DQC_EN_VIVO="0", DQC_DEMO="1", DQC_CLAVE_DEMO=CLAVE, PYTHONIOENCODING="utf-8",
        )
        self._lanzar([sys.executable, "-m", "dqc.api", "--puerto", str(PUERTO_API)], RAIZ, entorno, "api.log")
        esperar(f"{self.api}/health/readiness")
        npm = "npm.cmd" if os.name == "nt" else "npm"
        self._lanzar([npm, "run", "dev", "--", "--port", str(PUERTO_WEB), "--strictPort", "--host", HOST], RAIZ / "web",
                     {**os.environ, "DQC_API": self.api}, "web.log")
        esperar(self.web)

    def apagar(self) -> None:
        for proceso in self.procesos:
            try:
                if os.name == "nt":  # npm lanza hijos: se cierra el árbol completo
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proceso.pid)], capture_output=True)
                else:
                    os.killpg(os.getpgid(proceso.pid), signal.SIGTERM)
                proceso.wait(timeout=30)
            except (ProcessLookupError, subprocess.TimeoutExpired, OSError):
                pass
        shutil.rmtree(self.carpeta, ignore_errors=True)


# ══ API ════════════════════════════════════════════════════════════════════════════════════════════════════


def pedir(api: str, metodo: str, ruta: str, cuerpo: dict | None = None, token: str | None = None) -> tuple[int, object]:
    cabeceras = {"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})}
    pedido = urllib.request.Request(api + ruta, data=json.dumps(cuerpo).encode() if cuerpo is not None else None,
                                    method=metodo, headers=cabeceras)
    try:
        with urllib.request.urlopen(pedido, timeout=60) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"null")
        except ValueError:
            return e.code, None


def iniciar_sesion(api: str, email: str) -> dict:
    estado, datos = pedir(api, "POST", "/api/v1/auth/sesion", {"email": email, "clave": CLAVE})
    if estado != 200 or not isinstance(datos, dict):
        raise SystemExit(f"No se pudo iniciar sesión como {email} ({estado}): ¿la API tiene las cuentas de demostración?")
    return datos


# ══ JavaScript que corre dentro de la página ═══════════════════════════════════════════════════════════════

# Selector corto y legible de un elemento (hasta 4 niveles, con ids y las dos primeras clases).
JS_SEL = """(el) => {
  const partes = [];
  for (let e = el; e && e.nodeType === 1 && e !== document.documentElement && partes.length < 4; e = e.parentElement) {
    let p = e.tagName.toLowerCase();
    if (e.id) { partes.unshift(p + '#' + CSS.escape(e.id)); break; }
    p += [...e.classList].slice(0, 2).map((c) => '.' + CSS.escape(c)).join('');
    partes.unshift(p);
  }
  return partes.join(' > ');
}"""

JS_CONTRASTE = """() => {
  const sel = %(sel)s;
  const lienzo = document.createElement('canvas'); lienzo.width = lienzo.height = 1;
  const cx = lienzo.getContext('2d', { willReadFrequently: true });
  const norm = (c) => {
    if (/^rgba?\\(\\s*\\d+\\s*,/.test(c)) return c;
    cx.clearRect(0, 0, 1, 1); cx.fillStyle = '#000'; cx.fillStyle = c; cx.fillRect(0, 0, 1, 1);
    const d = cx.getImageData(0, 0, 1, 1).data;
    return `rgba(${d[0]}, ${d[1]}, ${d[2]}, ${+(d[3] / 255).toFixed(3)})`;
  };
  const alfa = (c) => { const p = c.match(/^rgba?\\(([^)]*)\\)/)[1].split(','); return p.length > 3 ? parseFloat(p[3]) : 1; };
  const recorta = (el, r) => {  // ¿queda algo a la vista tras el recorte de los ancestros con overflow hidden/clip?
    let x0 = r.left, x1 = r.right, y0 = r.top, y1 = r.bottom;
    for (let a = el.parentElement; a; a = a.parentElement) {
      const s = getComputedStyle(a);
      const cx_ = s.overflowX === 'hidden' || s.overflowX === 'clip', cy_ = s.overflowY === 'hidden' || s.overflowY === 'clip';
      if (!cx_ && !cy_) continue;
      const ar = a.getBoundingClientRect();
      if (cx_) { x0 = Math.max(x0, ar.left); x1 = Math.min(x1, ar.right); }
      if (cy_) { y0 = Math.max(y0, ar.top); y1 = Math.min(y1, ar.bottom); }
      if (x1 - x0 < 1 || y1 - y0 < 1) return false;
    }
    return true;
  };
  const candidatos = []; const vistos = new Set();
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) {
    const n = w.currentNode;
    const el = n.parentElement;
    if (!n.nodeValue.trim() || !el || vistos.has(el) || el.closest('script,style,noscript,option,datalist,template')) continue;
    vistos.add(el); candidatos.push({ el, nodo: n, tipo: 'texto' });
  }
  for (const el of document.querySelectorAll('input, textarea, select')) {
    if (['checkbox', 'radio', 'hidden', 'range', 'file', 'button', 'submit', 'reset', 'image', 'color'].includes(el.type)) continue;
    if (el.value) candidatos.push({ el, tipo: 'valor' }); else if (el.placeholder) candidatos.push({ el, tipo: 'placeholder' });
  }
  const alto = document.documentElement.scrollHeight;
  const salida = [];
  for (const c of candidatos) {
    const el = c.el;
    if (el.closest(':disabled, [aria-disabled="true"], [inert]')) continue;
    const s = getComputedStyle(el);
    if (s.visibility !== 'visible' || (s.clipPath || '').startsWith('inset')) continue;
    let opac = 1; for (let a = el; a; a = a.parentElement) opac *= parseFloat(getComputedStyle(a).opacity);
    if (opac < 0.05) continue;
    const r0 = el.getBoundingClientRect();
    if (r0.width < 2 || r0.height < 2 || r0.bottom <= 0 || r0.right <= 0 || r0.top + scrollY >= alto) continue;
    if (!recorta(el, r0)) continue;
    let rects;
    if (c.nodo) { const rg = document.createRange(); rg.selectNodeContents(c.nodo); rects = [...rg.getClientRects()]; } else rects = [r0];
    rects = rects.filter((r) => r.width >= 2 && r.height >= 2).slice(0, 4);
    if (!rects.length) continue;
    let color;
    if (el instanceof SVGElement) { color = s.fill; if (!color || color === 'none' || color.startsWith('url')) continue; }
    else if (c.tipo === 'placeholder') color = getComputedStyle(el, '::placeholder').color;
    else color = (s.webkitTextFillColor && s.webkitTextFillColor !== s.color) ? s.webkitTextFillColor : s.color;
    const capas = [];
    // El rótulo curvo de un sello (textPath) va sobre el disco del propio sello, no sobre lo que haya detrás.
    const disco = el.tagName.toLowerCase() === 'textpath' && el.closest('svg') ? el.closest('svg').querySelector('circle') : null;
    if (disco) capas.push({ bg: norm(getComputedStyle(disco).fill), img: null, sel: '' });
    else for (let a = el; a; a = a.parentElement) {
      const e = getComputedStyle(a);
      const img = e.backgroundImage !== 'none' ? e.backgroundImage.slice(0, 60) : null;
      const bg = norm(e.backgroundColor);
      if (img || alfa(bg) > 0) capas.push({ bg, img, sel: img ? sel(a) : '' });
      if (!img && alfa(bg) >= 0.999) break;
    }
    salida.push({
      sel: sel(el), texto: (c.nodo ? c.nodo.nodeValue : (el.value || el.placeholder)).trim().replace(/\\s+/g, ' ').slice(0, 40),
      tipo: c.tipo, color: norm(color), tamano: parseFloat(s.fontSize), peso: parseInt(s.fontWeight) || 400, opacidad: opac, capas,
      rects: rects.map((r) => [r.left + scrollX, r.top + scrollY, r.width, r.height]),
    });
  }
  return salida;
}""" % {"sel": JS_SEL}

# Estimación por píxeles de los textos con fondo degradado: se oculta todo el texto, se fotografía la página y se
# mide, bajo cada texto, el peor contraste que da su color con los píxeles del fondo.
CSS_SIN_TEXTO = (
    "*, *::before, *::after { color: transparent !important; -webkit-text-fill-color: transparent !important; "
    "text-shadow: none !important; caret-color: transparent !important; } svg text, svg tspan { fill: transparent !important; } "
    "::placeholder { color: transparent !important; }"
)
JS_MUESTREO = """async ({ png, items }) => {
  const bmp = await createImageBitmap(await (await fetch('data:image/png;base64,' + png)).blob());
  const lienzo = document.createElement('canvas'); lienzo.width = bmp.width; lienzo.height = bmp.height;
  const cx = lienzo.getContext('2d', { willReadFrequently: true }); cx.drawImage(bmp, 0, 0);
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const razon = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const out = {};
  for (const it of items) {
    const [tr, tg, tb, ta] = it.color; const a = ta * it.opacidad;
    let peor = Infinity, fondo = null;
    for (const [x, y, w, h] of it.rects) {
      const px = Math.max(0, Math.floor(x)), py = Math.max(0, Math.floor(y));
      const pw = Math.min(Math.ceil(w), bmp.width - px), ph = Math.min(Math.ceil(h), bmp.height - py);
      if (pw < 1 || ph < 1) continue;
      const d = cx.getImageData(px, py, pw, ph).data;
      const paso = Math.max(1, Math.floor(Math.sqrt(pw * ph / 300)));
      for (let yy = 0; yy < ph; yy += paso) for (let xx = 0; xx < pw; xx += paso) {
        const k = (yy * pw + xx) * 4; const f = [d[k], d[k + 1], d[k + 2]];
        const rz = razon([tr * a + f[0] * (1 - a), tg * a + f[1] * (1 - a), tb * a + f[2] * (1 - a)], f);
        if (rz < peor) { peor = rz; fondo = f; }
      }
    }
    out[it.i] = { razon: isFinite(peor) ? peor : null, fondo };
  }
  return out;
}"""

JS_FOCO = """async () => {
  const sel = %(sel)s;
  const el = document.activeElement;
  if (!el || el === document.body || el === document.documentElement) return { cuerpo: true };
  // El foco se dibuja con una transición de 0,12 s: se espera a que termine antes de leer los estilos.
  const asentar = () => Promise.all(document.getAnimations().filter((a) => a instanceof CSSTransition).map((a) => a.finished.catch(() => {})));
  // El propio elemento y sus 3 contenedores más cercanos (el campo de búsqueda dibuja el foco en su contenedor, con :focus-within).
  const leer = () => {
    const cadena = [];
    for (let e = el, n = 0; e && e !== document.body && n < 4; e = e.parentElement, n++) {
      const s = getComputedStyle(e);
      cadena.push({
        contorno: s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0 && !/,\\s*0\\)$/.test(s.outlineColor),
        sombra: s.boxShadow, borde: `${s.borderTopColor}|${s.borderLeftColor}`,
        descripcion: `outline ${s.outlineWidth} ${s.outlineStyle} ${s.outlineColor}; box-shadow ${s.boxShadow.slice(0, 70)}; border ${s.borderTopWidth} ${s.borderTopColor}`,
      });
    }
    return cadena;
  };
  await asentar();
  const con = leer();
  el.blur(); await asentar(); const sin = leer(); el.focus({ preventScroll: true });
  let como = 'ninguno', descripcion = con[0].descripcion;
  if (con[0].contorno) como = 'outline';
  else if (con[0].sombra !== sin[0].sombra) como = 'box-shadow';
  else if (con[0].borde !== sin[0].borde) como = 'borde del propio elemento';
  else for (let i = 1; i < con.length; i++) {
    if (con[i].contorno && !sin[i].contorno) { como = `outline del contenedor ${i}`; break; }
    if (con[i].sombra !== sin[i].sombra) { como = `box-shadow del contenedor ${i}`; break; }
    if (con[i].borde !== sin[i].borde) { como = `borde del contenedor ${i}`; break; }
  }
  if (!el.__vp) el.__vp = ++window.__vpn || (window.__vpn = 1);
  const nombre = el.getAttribute('aria-label') || el.innerText || el.value || el.getAttribute('title') || '';
  return {
    id: el.__vp, sel: sel(el), tag: el.tagName.toLowerCase(), nombre: nombre.trim().replace(/\\s+/g, ' ').slice(0, 40),
    visible: como !== 'ninguno', como, descripcion, enMain: !!el.closest('main'), enDialogo: !!el.closest('[role=dialog]'),
  };
}""" % {"sel": JS_SEL}

JS_TABULABLES = """() => [...document.querySelectorAll('a[href], button, input, select, textarea, summary, [tabindex]')]
  .filter((e) => e.tabIndex >= 0 && !e.disabled && e.getClientRects().length && getComputedStyle(e).visibility === 'visible' && !e.closest('[inert]')).length"""

JS_ESTRUCTURA = """() => {
  const sel = %(sel)s;
  const ids = {}; for (const e of document.querySelectorAll('[id]')) ids[e.id] = (ids[e.id] || 0) + 1;
  return {
    lang: document.documentElement.lang, titulo: document.title, viewport: !!document.querySelector('meta[name=viewport]'),
    h1: [...document.querySelectorAll('h1')].map((h) => h.innerText.trim()), main: document.querySelectorAll('main').length,
    duplicados: Object.entries(ids).filter(([, n]) => n > 1).map(([id, n]) => `${id} ×${n}`),
    sinAlt: [...document.querySelectorAll('img:not([alt])')].map((e) => sel(e)),
  };
}""" % {"sel": JS_SEL}

JS_DESBORDE = """() => {
  const sel = %(sel)s;
  // ¿Lo recorta o lo deja scrollear algún ancestro? Un elemento absoluto solo lo recorta un ancestro con overflow
  // que sea (o esté dentro de) su bloque contenedor, es decir, el ancestro posicionado más cercano.
  const recortado = (el) => {
    let dentro = getComputedStyle(el).position !== 'absolute';
    for (let a = el.parentElement; a && a !== document.body; a = a.parentElement) {
      const s = getComputedStyle(a);
      if (s.position === 'fixed') return true;
      if (!dentro && (s.position !== 'static' || s.transform !== 'none')) dentro = true;
      if (dentro && s.overflowX !== 'visible') return true;
    }
    return false;
  };
  const de = document.documentElement; const ancho = de.clientWidth; const sobran = [];
  for (const el of document.body.querySelectorAll('*')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0 || r.right <= ancho + 0.5 || getComputedStyle(el).position === 'fixed') continue;
    if (!recortado(el)) sobran.push({ sel: sel(el), derecha: Math.round(r.right), ancho: Math.round(r.width) });
  }
  return { sw: de.scrollWidth, cw: ancho, bsw: document.body.scrollWidth, sobran: sobran.slice(0, 8) };
}""" % {"sel": JS_SEL}

JS_ANIMACIONES = """() => {
  const sel = %(sel)s;
  return document.getAnimations().filter((a) => a.playState === 'running').map((a) => ({
    tipo: a.constructor.name, nombre: a.animationName || a.transitionProperty || a.id || '?',
    objetivo: a.effect && a.effect.target ? sel(a.effect.target) : '?',
  }));
}""" % {"sel": JS_SEL}

JS_SIN_ANIMACIONES_FINITAS = (
    "() => document.getAnimations().every((a) => a.playState !== 'running' || (a.effect && a.effect.getComputedTiming().iterations === Infinity))"
)


# ══ Navegador ══════════════════════════════════════════════════════════════════════════════════════════════


@dataclass
class Evento:
    tipo: str  # "consola", "excepcion", "respuesta" o "fallida"
    texto: str
    url: str = ""
    estado: int = 0
    metodo: str = ""
    contexto: str = ""
    motivo: str = ""  # lo llena la clasificación: por qué se descartó (si se descartó)


class Vigia:
    """Anota lo que sale mal en el navegador: errores de consola, excepciones y respuestas 4xx/5xx."""

    def __init__(self, api: str, web: str):
        self.origenes = {urlparse(api).netloc, urlparse(web).netloc}
        self.eventos: list[Evento] = []
        self.esperados: list[tuple[str, str, int, str]] = []  # (método, ruta, estado, motivo)
        self.externas = 0
        self.hmr = 0  # websocket de recarga en caliente de Vite: existe solo en el servidor de desarrollo

    def esperar(self, metodo: str, ruta: str, estado: int, motivo: str) -> None:
        self.esperados.append((metodo, ruta, estado, motivo))

    def vigilar(self, pagina, contexto: str) -> None:
        def propia(url: str) -> bool:
            return urlparse(url).netloc in self.origenes or not url.startswith("http")

        def consola(m) -> None:
            if m.type == "error":
                url = (m.location or {}).get("url", "")
                if "WebSocket connection to" in m.text and "token=" in m.text:
                    self.hmr += 1  # el HMR de Vite (no es del portal); en Windows falla a veces con ERR_NO_BUFFER_SPACE al abrir cientos de páginas
                elif url and not propia(url):
                    self.externas += 1
                else:
                    self.eventos.append(Evento("consola", m.text[:240], url, contexto=contexto))

        def respuesta(r) -> None:
            if r.status >= 400:
                if propia(r.url):
                    self.eventos.append(Evento("respuesta", f"{r.status} {r.request.method} {urlparse(r.url).path}", r.url, r.status, r.request.method, contexto))
                else:
                    self.externas += 1

        def fallida(r) -> None:
            if propia(r.url):
                self.eventos.append(Evento("fallida", f"{r.method} {r.url}: {r.failure}", r.url, metodo=r.method, contexto=contexto))
            else:
                self.externas += 1

        pagina.on("console", consola)
        pagina.on("pageerror", lambda e: self.eventos.append(Evento("excepcion", str(e)[:240], contexto=contexto)))
        pagina.on("response", respuesta)
        pagina.on("requestfailed", fallida)

    def clasificar(self) -> tuple[list[Evento], list[Evento]]:
        """(inesperados, descartados): los 401 buscados se descartan con su motivo, tanto la respuesta como el
        «Failed to load resource» que Chromium escribe en la consola por ella."""
        pendientes = list(self.esperados)  # cada respuesta esperada se gasta una vez: un 401 de más sí es inesperado
        inesperados: list[Evento] = []
        descartados: list[Evento] = []
        for e in self.eventos:
            coincide = None
            if e.tipo == "respuesta":
                coincide = next((x for x in pendientes if (x[0], x[1], x[2]) == (e.metodo, urlparse(e.url).path, e.estado)), None)
                if coincide:
                    pendientes.remove(coincide)
            elif e.tipo == "consola":  # el «Failed to load resource» de esa misma respuesta
                coincide = next((x for x in self.esperados if f"status of {x[2]}" in e.texto and urlparse(e.url).path == x[1]), None)
            if coincide:
                e.motivo = coincide[3]
                descartados.append(e)
            else:
                inesperados.append(e)
        return inesperados, descartados


class Laboratorio:
    """Abre páginas del portal con la sesión, el tema, el tamaño y el movimiento que pida cada comprobación."""

    def __init__(self, navegador, web: str, api: str, vigia: Vigia, artefactos: Path, dia: str | None):
        self.navegador = navegador
        self.web = web
        self.api = api
        self.vigia = vigia
        self.artefactos = artefactos
        self.dia = dia
        self.sesiones = {rol: iniciar_sesion(api, email) for rol, email in ROLES.items()}

    def contexto(self, rol: str | None = None, tema: str = "claro", tamano: dict | None = None, reducido: bool = False, etiqueta: str = ""):
        ctx = self.navegador.new_context(
            viewport=tamano or ESCRITORIO, color_scheme="light", locale="es-PE", reduced_motion="reduce" if reducido else "no-preference",
        )
        guion = []
        if rol:
            s = self.sesiones[rol]
            guion.append(f"try {{ sessionStorage.setItem('dqc.sesion', {json.dumps(json.dumps({'token': s['token'], 'expira': s['expira']}))}) }} catch (e) {{}}")
        guion.append(f"try {{ localStorage.setItem('dqc.tema', '{'oscuro' if tema == 'oscuro' else 'claro'}') }} catch (e) {{}}")
        ctx.add_init_script("\n".join(guion))
        ctx.set_default_timeout(20_000)
        return ctx

    def abrir(self, pantalla: Pantalla | str, rol: str | None = "admin", tema: str = "claro", tamano: dict | None = None,
              reducido: bool = False, etiqueta: str = "", esperar: bool = True):
        if isinstance(pantalla, str):
            pantalla = Pantalla("x", pantalla, publica=pantalla.startswith("/entrar"))
        ctx = self.contexto(None if pantalla.publica else rol, tema, tamano, reducido)
        pagina = ctx.new_page()
        self.vigia.vigilar(pagina, etiqueta or f"{pantalla.clave}/{tema}")
        # Se espera al DOM, no al evento load: las fuentes de Google (externas) pueden tardar y no son lo que se prueba.
        for intento in (1, 2):
            try:
                pagina.goto(self.web + pantalla.ruta, wait_until="domcontentloaded", timeout=45_000)
                break
            except Exception:  # noqa: BLE001 - un tropiezo de red o del servidor de desarrollo: se reintenta una vez
                if intento == 2:
                    raise
        if not esperar:  # para mirar lo que pasa mientras la página entra
            return pagina
        self.asentar(pagina)
        if pantalla.con_dia and self.dia:
            self.elegir_dia(pagina, self.dia)
        return pagina

    @staticmethod
    def asentar(pagina, extra_ms: int = 700) -> None:
        """Espera a la red, a que terminen las animaciones de entrada y a los conteos de cifras."""
        esperas = (
            ("red", lambda t: pagina.wait_for_load_state("networkidle", timeout=t)),
            ("esqueletos", lambda t: pagina.wait_for_function("() => !document.querySelector('.esqueleto')", timeout=t)),
            ("animaciones", lambda t: pagina.wait_for_function(JS_SIN_ANIMACIONES_FINITAS, timeout=t)),
            ("fuentes", lambda t: pagina.wait_for_function("() => !document.fonts || document.fonts.status === 'loaded'", timeout=t)),
        )
        for nombre, espera in esperas:
            try:
                espera(PACIENCIA[nombre])
            except Exception:  # noqa: BLE001 - si algo sigue cargando o animado, se mide igual
                if nombre in ("red", "fuentes"):
                    # Solo lo que depende de internet: las páginas que siguen no esperan lo mismo otra vez. Los esqueletos
                    # y las animaciones se esperan completos en cada pantalla, para no medir a medias por una lentitud pasajera.
                    PACIENCIA[nombre] = 1_500
        pagina.wait_for_timeout(extra_ms)

    def elegir_dia(self, pagina, dia: str) -> None:
        """El día elegido vive en el store de Pinia, compartido por todos los módulos."""
        pagina.wait_for_function("() => document.querySelector('#app')?.__vue_app__")
        pagina.evaluate("d => { document.querySelector('#app').__vue_app__.config.globalProperties.$pinia._s.get('cortes').elegido = d }", dia)
        self.asentar(pagina)

    def captura_si_falla(self, pagina, nombre: str, antes: int, c: Comprobacion) -> None:
        if len(c.fallas) > antes:
            try:
                carpeta = self.artefactos / "fallas"
                carpeta.mkdir(parents=True, exist_ok=True)
                pagina.screenshot(path=carpeta / f"{c.clave}-{nombre}.png", full_page=True)
            except Exception:  # noqa: BLE001 - la captura es un extra
                pass


def expandir_lectura(pagina) -> None:
    """Abre «¿Cómo se lee?» (si la pantalla lo tiene) para medir también su texto."""
    boton = pagina.locator("button.alternar[aria-expanded='false']")
    if boton.count():
        boton.first.click()
        pagina.wait_for_timeout(450)


def foco_al_inicio(pagina) -> None:
    pagina.evaluate("() => { if (document.activeElement && document.activeElement !== document.body) document.activeElement.blur(); window.scrollTo(0, 0) }")


# ══ (a) Inicio de sesión ═══════════════════════════════════════════════════════════════════════════════════


def comprobar_inicio(lab: Laboratorio, c: Comprobacion) -> None:
    p = lab.abrir("/entrar", rol=None, etiqueta="a/inicio")
    c.ok(p.get_by_role("heading", name="Iniciar sesión").is_visible(), "la página de inicio de sesión carga", f"título de pestaña: {p.title()!r}")
    c.ok(p.locator("#email").is_visible() and p.locator("#clave").is_visible(), "tiene los campos de correo y contraseña")

    def intentar(email: str, clave: str) -> list[str]:
        lab.vigia.esperar("POST", "/api/v1/auth/sesion", 401, "(a) clave equivocada a propósito")
        p.fill("#email", email)
        p.fill("#clave", clave)
        with p.expect_response(lambda r: r.url.endswith("/api/v1/auth/sesion")):
            p.click("button[type=submit]")
        p.locator("[role=alert]").first.wait_for()
        p.wait_for_timeout(250)
        return p.locator("[role=alert]").all_inner_texts()

    mensajes = intentar(LECTOR, "no-es-la-clave")
    c.ok(len(mensajes) == 1, "con clave equivocada sale UN solo mensaje", f"mensajes: {mensajes}")
    c.ok(len(mensajes) == 1 and "correo o contraseña incorrectos" in mensajes[0].lower(), "el mensaje es genérico (no dice cuál de los dos falló)")
    otro = intentar("nadie.existe@demo.local", "no-es-la-clave")
    c.ok(otro == mensajes, "una cuenta que no existe recibe exactamente el mismo mensaje", f"{otro}")
    c.ok(p.url.endswith("/entrar"), "tras el error se queda en /entrar", p.url)

    p.fill("#email", LECTOR)
    p.fill("#clave", CLAVE)
    p.click("button[type=submit]")
    p.wait_for_url("**/resumen")
    p.get_by_role("heading", name="Resumen", exact=True).wait_for()
    c.ok(True, "con la clave correcta entra al Resumen", p.url)
    c.ok(p.locator("[role=alert]").count() == 0, "al entrar ya no queda ningún mensaje de error")
    p.context.close()
    c.resumen = "carga, error genérico único (2 casos) y entrada correcta"


# ══ (b) Roles ══════════════════════════════════════════════════════════════════════════════════════════════


def comprobar_roles(lab: Laboratorio, c: Comprobacion) -> None:
    esperado = {"lector": 7, "gobierno": 7, "admin": 11}
    for rol, n in esperado.items():
        p = lab.abrir("/resumen", rol, etiqueta=f"b/menu-{rol}")
        enlaces = p.locator("nav[aria-label='Módulos'] a")
        nombres = enlaces.all_inner_texts()
        c.ok(enlaces.count() == n, f"{rol}: el menú tiene {n} secciones", f"{enlaces.count()}: {', '.join(x.splitlines()[0] for x in nombres)}")
        grupos = p.locator("nav[aria-label='Módulos'] .grupo").all_inner_texts()
        c.ok(("Administración" in grupos) == (rol == "admin"), f"{rol}: {'ve' if rol == 'admin' else 'no ve'} el grupo «Administración»", f"grupos: {grupos}")
        p.context.close()

    p = lab.abrir("/usuarios", "lector", etiqueta="b/usuarios-lector")
    ruta = urlparse(p.url).path
    c.ok(ruta != "/usuarios", "un lector que abre /usuarios es llevado a otra sección", ruta)
    c.ok(p.get_by_role("heading", name="Usuarios", exact=True).count() == 0, "no aparece el título «Usuarios»")
    c.ok(p.get_by_text("Dar acceso").count() == 0 and p.get_by_text("Administración").count() == 0,
         "no aparece nada de administración (ni «Dar acceso» ni el grupo del menú)")
    p.context.close()

    token_lector = lab.sesiones["lector"]["token"]
    for ruta_api in ("/api/v1/reglas", "/api/v1/admin/usuarios"):
        estado, _ = pedir(lab.api, "GET", ruta_api, token=token_lector)
        c.ok(estado == 403, f"la API responde 403 a un lector en {ruta_api}", f"respondió {estado}")
        estado_admin, _ = pedir(lab.api, "GET", ruta_api, token=lab.sesiones["admin"]["token"])
        c.ok(estado_admin == 200, f"y 200 al administrador en {ruta_api} (control)", f"respondió {estado_admin}")
        estado_sin, _ = pedir(lab.api, "GET", ruta_api)
        c.ok(estado_sin in (401, 403), f"sin sesión tampoco entra a {ruta_api}", f"respondió {estado_sin}")
    c.notas.append("los 403 de la API se piden con urllib (fuera del navegador): no entran en la comprobación (i)")
    c.resumen = "lector 7, gobierno 7, admin 11; /usuarios cerrado al lector; API 403 a lector"


# ══ (c) Resumen ════════════════════════════════════════════════════════════════════════════════════════════


def comprobar_resumen(lab: Laboratorio, c: Comprobacion) -> None:
    p = lab.abrir(Pantalla("resumen", "/resumen", con_dia=True), "gobierno", etiqueta="c/resumen")
    h1 = p.locator("h1").all_inner_texts()
    c.ok(h1 == ["Resumen"], "el único h1 es «Resumen»", f"{h1}")
    c.ok(p.get_by_role("heading", name="Lectura rápida").is_visible(), "se ve la «Lectura rápida»")
    sellos = p.locator(".hero-sellos figure")
    c.ok(sellos.count() == 5, "hay 5 sellos (uno por tabla)", f"{sellos.count()}: {[sellos.nth(i).get_attribute('aria-label') for i in range(sellos.count())]}")
    deslizador = p.get_by_role("slider", name="Día de datos")
    c.ok(deslizador.count() == 1, "hay un deslizador «Día de datos»")
    antes = int(deslizador.get_attribute("aria-valuenow"))
    texto_antes = deslizador.get_attribute("aria-valuetext")
    deslizador.focus()
    p.keyboard.press("ArrowLeft")
    p.wait_for_timeout(250)
    izquierda = int(deslizador.get_attribute("aria-valuenow"))
    texto_izq = deslizador.get_attribute("aria-valuetext")
    p.keyboard.press("ArrowRight")
    p.wait_for_timeout(250)
    derecha = int(deslizador.get_attribute("aria-valuenow"))
    c.ok(izquierda == antes - 1 and texto_izq != texto_antes, "ArrowLeft retrocede un día", f"{antes} -> {izquierda}; «{texto_antes}» -> «{texto_izq}»")
    c.ok(derecha == antes, "ArrowRight vuelve al día de partida", f"{izquierda} -> {derecha}")
    p.context.close()
    c.resumen = "h1, lectura rápida, 5 sellos y deslizador con flechas"


# ══ (d) Teclado y foco ═════════════════════════════════════════════════════════════════════════════════════


def comprobar_teclado_pantalla(lab: Laboratorio, p, pant: Pantalla, c: Comprobacion) -> None:
    """Los primeros 20 Tab de una pantalla recién cargada: foco visible, sin trampas y con «Saltar al contenido»."""
    total = p.evaluate(JS_TABULABLES)
    pasos = []
    for _ in range(TABS):
        p.keyboard.press("Tab")
        pasos.append(p.evaluate(JS_FOCO))
    reales = [x for x in pasos if not x.get("cuerpo")]
    if not pant.publica:
        primero = pasos[0]
        c.ok(not primero.get("cuerpo") and primero.get("nombre", "").startswith("Saltar al contenido"),
             "«Saltar al contenido» es el primer Tab", f"primero: {primero.get('nombre')!r} ({primero.get('sel')})", "d-saltar", pant.clave)
    invisibles = {}
    for x in reales:
        if not x["visible"]:
            invisibles[(x["sel"], x["descripcion"])] = x["nombre"]
    c.ok(not invisibles, f"foco visible (outline, box-shadow o borde, propio o del contenedor) en los primeros {TABS} Tab",
         "; ".join(f"{s} [{n or 'sin texto'}] -> {d}" for (s, d), n in list(invisibles.items())[:6]), "d-foco",
         f"{pant.clave} ({len(reales)} paradas)")
    ids = [x.get("id") for x in pasos]
    repetidos = [i for i in range(1, len(ids)) if ids[i] is not None and ids[i] == ids[i - 1]]
    distintos = len({i for i in ids if i is not None})
    esperados = min(TABS, total)
    c.ok(not repetidos and distintos >= 0.9 * esperados - 1, "sin trampas de foco: cada Tab avanza y no se cierra en un ciclo corto",
         f"Tab sin avance en los pasos {repetidos}; {distintos} elementos distintos de {esperados} esperados ({total} tabulables)", "d-trampa", pant.clave)
    if len(reales) == TABS and TABS >= 5:
        atras = []
        for _ in range(3):
            p.keyboard.press("Shift+Tab")
            atras.append(p.evaluate(JS_FOCO).get("id"))
        c.ok(atras == [ids[-2], ids[-3], ids[-4]], "Mayús+Tab vuelve por el mismo camino", f"{atras} vs {[ids[-2], ids[-3], ids[-4]]}", "d-atras", pant.clave)
    if not pant.publica:
        p.focus(".saltar")
        p.keyboard.press("Enter")
        p.wait_for_timeout(150)
        destino = p.evaluate("() => ({ tag: document.activeElement.tagName, id: document.activeElement.id })")
        c.ok(destino == {"tag": "MAIN", "id": "contenido"}, "«Saltar al contenido» (Enter) lleva el foco a <main>", f"{destino}", "d-main", pant.clave)
        p.keyboard.press("Tab")
        dentro = p.evaluate("() => ({ dentro: !!document.activeElement.closest('main'), el: document.activeElement.tagName })")
        c.ok(dentro["dentro"], "el siguiente Tab cae dentro del contenido, no vuelve al menú", f"{dentro}", "d-sigue", pant.clave)


def comprobar_teclado_especial(lab: Laboratorio, c: Comprobacion) -> None:
    # Recorrido guiado: no se abre solo con webdriver; se abre con Enter y Esc lo cierra devolviendo el foco.
    p = lab.abrir(Pantalla("resumen", "/resumen", con_dia=True), "gobierno", etiqueta="d/recorrido")
    c.ok(p.evaluate("navigator.webdriver") is True and p.get_by_role("dialog").count() == 0,
         "el recorrido guiado no se abre solo en un navegador automatizado (navigator.webdriver)")
    p.focus("#boton-recorrido")
    p.keyboard.press("Enter")
    p.get_by_role("dialog").wait_for()
    dentro = p.evaluate("() => !!document.activeElement.closest('[role=dialog]')")
    c.ok(dentro, "al abrir el recorrido el foco entra en el diálogo")
    for _ in range(8):
        p.keyboard.press("Tab")
    c.ok(p.evaluate("() => !!document.activeElement.closest('[role=dialog]')"), "el foco no se escapa del recorrido con Tab (diálogo modal)")
    p.keyboard.press("Escape")
    p.wait_for_timeout(300)
    c.ok(p.get_by_role("dialog").count() == 0, "Esc cierra el recorrido guiado")
    activo = p.evaluate("() => document.activeElement.id")
    c.ok(activo == "boton-recorrido", "y el foco vuelve al botón que lo abrió", f"foco en: {activo!r}")
    p.context.close()

    # Mapa de días del Resumen: una parada de Tab por fila y recorrido con flechas.
    p = lab.abrir(Pantalla("resumen", "/resumen", con_dia=True), "gobierno", etiqueta="d/mapa")
    filas = p.evaluate("() => [...document.querySelectorAll('.celdas')].map((f) => f.querySelectorAll('button[tabindex=\"0\"]').length)")
    c.ok(len(filas) >= 5 and all(n == 1 for n in filas), "mapa de días: una sola parada de Tab por fila", f"paradas por fila: {filas}")
    primera = p.locator(".celdas").first.locator("button[tabindex='0']")
    primera.focus()
    antes = p.evaluate("() => document.activeElement.getAttribute('aria-label')")
    p.keyboard.press("ArrowLeft")
    despues = p.evaluate("() => document.activeElement.getAttribute('aria-label')")
    p.keyboard.press("ArrowRight")
    vuelve = p.evaluate("() => document.activeElement.getAttribute('aria-label')")
    c.ok(despues != antes and vuelve == antes, "mapa de días: las flechas mueven el foco entre días", f"{antes!r} -> {despues!r} -> {vuelve!r}")
    p.context.close()

    # Detalle de una regla: Enter lo abre, Esc lo cierra y devuelve el foco.
    p = lab.abrir(Pantalla("validaciones", "/validaciones", con_dia=True), "gobierno", etiqueta="d/detalle-regla")
    abrir = p.locator("button.abrir-regla").first
    c.ok(abrir.count() == 1, "Validaciones tiene reglas con botón de detalle")
    abrir.focus()
    p.evaluate("() => document.activeElement.setAttribute('data-vp-abridor', '1')")
    p.keyboard.press("Enter")
    p.get_by_role("dialog").wait_for()
    p.wait_for_timeout(200)
    c.ok(p.evaluate("() => !!document.activeElement.closest('[role=dialog]')"), "al abrir el detalle el foco entra en el diálogo")
    for _ in range(12):
        p.keyboard.press("Tab")
    c.ok(p.evaluate("() => !!document.activeElement.closest('[role=dialog]')"), "el foco no se escapa del detalle con Tab (diálogo modal)")
    p.keyboard.press("Escape")
    p.wait_for_timeout(300)
    c.ok(p.get_by_role("dialog").count() == 0, "Esc cierra el detalle de la regla")
    c.ok(p.evaluate("() => document.activeElement.getAttribute('data-vp-abridor') === '1'"), "y el foco vuelve a la regla que lo abrió")
    p.context.close()


# ══ (e) Nombres accesibles ═════════════════════════════════════════════════════════════════════════════════

ROLES_CON_NOMBRE = {
    "button", "link", "textbox", "searchbox", "combobox", "checkbox", "radio", "switch", "slider", "spinbutton", "listbox",
    "menuitem", "tab", "img", "image", "graphics-document", "graphics-symbol",
}


def comprobar_nombres(lab: Laboratorio, p, pant: Pantalla, c: Comprobacion) -> None:
    """Nombre accesible según el propio árbol de accesibilidad de Chromium (aria-label, labelledby, label, texto, alt)."""
    cdp = p.context.new_cdp_session(p)
    arbol = cdp.send("Accessibility.getFullAXTree")["nodes"]
    sin_nombre = []
    revisados = 0
    for n in arbol:
        rol = (n.get("role") or {}).get("value")
        if n.get("ignored") or rol not in ROLES_CON_NOMBRE:
            continue
        revisados += 1
        if not ((n.get("name") or {}).get("value") or "").strip():
            sin_nombre.append((rol, n.get("backendDOMNodeId")))
    detalles = []
    for rol, backend in sin_nombre[:8]:
        try:
            objeto = cdp.send("DOM.resolveNode", {"backendNodeId": backend})["object"]["objectId"]
            r = cdp.send("Runtime.callFunctionOn", {
                "objectId": objeto, "returnByValue": True,
                "functionDeclaration": "function() { const sel = %s; return sel(this) + ' ' + this.outerHTML.slice(0, 90); }" % JS_SEL,
            })
            detalles.append(f"{rol}: {r['result']['value']}")
        except Exception as e:  # noqa: BLE001
            detalles.append(f"{rol}: (nodo {backend}: {e})")
    c.ok(not sin_nombre, "todo botón, enlace, campo, control e imagen expuesto tiene nombre accesible", "; ".join(detalles), "e-nombre", f"{pant.clave} ({revisados} controles)")
    cdp.detach()
    est = p.evaluate(JS_ESTRUCTURA)
    c.ok(not est["sinAlt"], "toda img tiene alt", ", ".join(est["sinAlt"]), "e-alt", pant.clave)
    c.ok(not est["duplicados"], "sin ids duplicados", ", ".join(est["duplicados"]), "e-ids", pant.clave)
    c.ok(len(est["h1"]) == 1 and est["main"] == 1, "un h1 y un main", f"h1: {est['h1']}, main: {est['main']}", "e-h1", pant.clave)
    c.ok(est["lang"] == "es" and bool(est["titulo"].strip()) and est["viewport"], "idioma (es), título de pestaña y viewport",
         f"lang={est['lang']!r}, título={est['titulo']!r}, viewport={est['viewport']}", "e-meta", pant.clave)


# ══ (f) Contraste ══════════════════════════════════════════════════════════════════════════════════════════


@dataclass
class Indeterminado:
    pantalla: str
    tema: str
    motivo: str
    cantidad: int = 0
    peor: float | None = None
    peor_texto: str = ""
    umbral: float = 4.5
    bajo_umbral: int = 0
    ejemplos: list[str] = field(default_factory=list)


def comprobar_contraste(lab: Laboratorio, p, pant: Pantalla, tema: str, c: Comprobacion, indet: list[Indeterminado], totales: dict) -> None:
    foco_al_inicio(p)
    expandir_lectura(p)
    items = p.evaluate(JS_CONTRASTE)
    fallos: dict[tuple, dict] = {}
    pendientes: list[tuple[int, dict, Medida]] = []
    for it in items:
        m = medir_contraste(it["color"], it["capas"], it["tamano"], it["peso"], it["opacidad"])
        totales["textos"] += 1
        if m.estado == "falla":
            clave = (it["sel"], hexa(m.texto), hexa(m.fondo), round(m.razon, 2))
            fallos.setdefault(clave, {"it": it, "m": m, "n": 0})["n"] += 1
        elif m.estado == "indeterminado":
            pendientes.append((len(pendientes), it, m))
        else:
            totales["ok"] += 1
    antes = len(c.fallas)
    lista = [f"{k[0]} «{v['it']['texto']}» texto {k[1]} sobre {k[2]} = {_ratio(v['m'].razon)} (mín. {_ratio(v['m'].umbral)}, {v['it']['tamano']:g}px/{v['it']['peso']}){f' ×{v['n']}' if v['n'] > 1 else ''}"
             for k, v in fallos.items()]
    c.ok(not fallos, "contraste de todo el texto medido ≥ mínimo (4,5:1; 3:1 desde 24 px o 19 px en negrita)",
         " | ".join(lista[:12]) + (f" | … y {len(lista) - 12} más" if len(lista) > 12 else ""), "f-contraste",
         f"{pant.clave}/{tema} ({len(items) - len(pendientes)} textos" + (f" +{len(pendientes)} indeterminados)" if pendientes else ")"))
    totales["fallos"] += len(fallos)
    if pendientes:
        # Estimación por píxeles (no es un fallo: solo informa).
        p.add_style_tag(content=CSS_SIN_TEXTO)
        p.wait_for_timeout(150)
        png = base64.b64encode(p.screenshot(full_page=True)).decode()
        entrada = []
        for i, it, _ in pendientes:
            color = parsear_color(it["color"]) or (0, 0, 0, 1)
            entrada.append({"i": i, "rects": it["rects"], "color": list(color), "opacidad": it["opacidad"]})
        muestreo = p.evaluate(JS_MUESTREO, {"png": png, "items": entrada})
        grupos: dict[str, Indeterminado] = {}
        for i, it, m in pendientes:
            g = grupos.setdefault(m.motivo, Indeterminado(pant.clave, tema, m.motivo, umbral=m.umbral))
            g.cantidad += 1
            r = (muestreo.get(str(i)) or {}).get("razon")
            if len(g.ejemplos) < 3:
                g.ejemplos.append(f"{it['sel']} «{it['texto']}»")
            if r is not None and (g.peor is None or r < g.peor):
                g.peor, g.peor_texto, g.umbral = r, f"{it['sel']} «{it['texto']}» ({it['tamano']:g}px/{it['peso']})", m.umbral
            if r is not None and r < m.umbral:
                g.bajo_umbral += 1
        indet.extend(grupos.values())
        totales["indeterminados"] += len(pendientes)
    lab.captura_si_falla(p, f"{pant.clave}-{tema}", antes, c)


def lineas_indeterminados(indet: list[Indeterminado]) -> list[str]:
    por_motivo: dict[tuple[str, str], list[Indeterminado]] = defaultdict(list)
    for g in indet:
        por_motivo[(g.motivo, g.tema)].append(g)
    lineas = []
    for (motivo, tema), grupos in sorted(por_motivo.items()):
        total = sum(g.cantidad for g in grupos)
        bajo = sum(g.bajo_umbral for g in grupos)
        peor = min((g for g in grupos if g.peor is not None), key=lambda g: g.peor, default=None)
        pantallas = ", ".join(f"{g.pantalla} ({g.cantidad})" for g in grupos)
        linea = f"- [{tema}] {motivo}: {total} textos en {pantallas}."
        if peor:
            linea += f" Muestreo de píxeles: peor razón {_ratio(peor.peor)} (mín. {_ratio(peor.umbral)}) en {peor.pantalla}: {peor.peor_texto}."
        linea += f" Bajo el mínimo por muestreo: {bajo}." if bajo else " Ninguno baja del mínimo por muestreo."
        lineas.append(linea)
    return lineas


# ══ (g) Móvil ══════════════════════════════════════════════════════════════════════════════════════════════


def comprobar_movil(lab: Laboratorio, p, pant: Pantalla, tema: str, c: Comprobacion) -> None:
    d = p.evaluate(JS_DESBORDE)
    antes = len(c.fallas)
    c.ok(d["sw"] <= d["cw"] and d["bsw"] <= d["cw"], "sin desborde horizontal a 390 px (scrollWidth ≤ clientWidth)",
         f"scrollWidth {d['sw']} > clientWidth {d['cw']}: " + ("; ".join(f"{s['sel']} llega a {s['derecha']}px (mide {s['ancho']}px)" for s in d["sobran"]) or f"body.scrollWidth {d['bsw']}"),
         "g-desborde", f"{pant.clave}/{tema}")
    lab.captura_si_falla(p, f"{pant.clave}-{tema}-movil", antes, c)


# ══ (h) Movimiento reducido ════════════════════════════════════════════════════════════════════════════════

EN_VIVO = re.compile(r"(\.pastilla|\.estado-vivo)\b.*\.punto(?![\w-])")  # el punto que pulsa del indicador «En vivo»


def comprobar_movimiento(lab: Laboratorio, p, nombre: str, c: Comprobacion) -> None:
    p.wait_for_timeout(1_200)
    animaciones = p.evaluate(JS_ANIMACIONES)
    propias = [a for a in animaciones if not EN_VIVO.search(a["objetivo"])]
    c.ok(not propias, "sin animaciones en curso (salvo «En vivo») con prefers-reduced-motion: reduce",
         "; ".join(f"{a['tipo']} {a['nombre']} en {a['objetivo']}" for a in propias[:6]) or "", "h-quieto", nombre)
    if animaciones and not propias:
        c.notas.append(f"{nombre}: solo corre el indicador «En vivo» ({len(animaciones)})")


def comprobar_movimiento_todo(lab: Laboratorio, c: Comprobacion) -> None:
    # Control positivo: sin la preferencia, el portal sí anima al entrar (si no, la comprobación no probaría nada).
    p = lab.abrir(Pantalla("resumen", "/resumen"), "admin", etiqueta="h/control", esperar=False)
    try:
        p.wait_for_function("() => document.getAnimations().length > 0", timeout=8_000)
        n = len(p.evaluate(JS_ANIMACIONES))
    except Exception:  # noqa: BLE001 - nunca hubo una animación
        n = 0
    c.ok(n > 0, "control: sin la preferencia, el Resumen sí tiene animaciones al entrar", f"{n} animaciones vistas")
    p.context.close()
    for pant in PANTALLAS:
        p = lab.abrir(pant, "admin", reducido=True, etiqueta=f"h/{pant.clave}")
        comprobar_movimiento(lab, p, pant.clave, c)
        p.context.close()
    # Estados con más movimiento: el recorrido guiado en su último paso (viaje de los datos) y el detalle de una regla.
    p = lab.abrir(Pantalla("resumen", "/resumen", con_dia=True), "admin", reducido=True, etiqueta="h/recorrido")
    p.click("#boton-recorrido")
    p.get_by_role("dialog").wait_for()
    for _ in range(4):
        p.keyboard.press("ArrowRight")
        p.wait_for_timeout(200)
    comprobar_movimiento(lab, p, "resumen con el recorrido en su último paso", c)
    p.context.close()
    p = lab.abrir(Pantalla("validaciones", "/validaciones", con_dia=True), "admin", reducido=True, etiqueta="h/detalle")
    p.locator("button.abrir-regla").first.click()
    p.get_by_role("dialog").wait_for()
    comprobar_movimiento(lab, p, "validaciones con el detalle abierto", c)
    p.context.close()
    c.resumen = f"{len(PANTALLAS)} pantallas + recorrido + detalle con prefers-reduced-motion"


# ══ (i) Consola y red ══════════════════════════════════════════════════════════════════════════════════════


def comprobar_errores(lab: Laboratorio, c: Comprobacion) -> None:
    inesperados, descartados = lab.vigia.clasificar()
    consola = [e for e in inesperados if e.tipo == "consola"]
    excepciones = [e for e in inesperados if e.tipo == "excepcion"]
    respuestas = [e for e in inesperados if e.tipo in ("respuesta", "fallida")]
    fmt = lambda lista: "; ".join(f"[{e.contexto}] {e.texto}" for e in lista[:6])  # noqa: E731
    c.ok(not consola, "sin errores de consola", fmt(consola))
    c.ok(not excepciones, "sin excepciones de página", fmt(excepciones))
    c.ok(not respuestas, "sin respuestas 4xx/5xx ni peticiones fallidas inesperadas", fmt(respuestas))
    por_motivo: dict[str, int] = defaultdict(int)
    for e in descartados:
        por_motivo[f"{e.metodo or 'consola'} {urlparse(e.url).path} {e.estado or ''}".strip() + f" ({e.motivo})"] += 1
    for k, n in por_motivo.items():
        c.notas.append(f"descartado a propósito: {k} ×{n}")
    if lab.vigia.hmr:
        c.notas.append(f"{lab.vigia.hmr} fallos del websocket de recarga en caliente de Vite ignorados: solo existe en el servidor de desarrollo, no en el portal")
    if lab.vigia.externas:
        c.notas.append(f"{lab.vigia.externas} fallos de recursos externos ignorados (fuentes de Google): no son del portal ni de la API")
    c.resumen = f"{len(inesperados)} inesperados; {len(descartados)} descartados a propósito (401 de (a))"


# ══ Orquestación ═══════════════════════════════════════════════════════════════════════════════════════════


def ejecutar(c: Comprobacion, fn, *args, imprimir: bool = True) -> None:
    c.ejecutada = True
    inicio = time.monotonic()
    try:
        fn(*args, c) if args else fn(c)
    except Exception as e:  # noqa: BLE001 - una comprobación rota es un FAIL, no detiene a las demás
        c.error = f"{type(e).__name__}: {str(e).splitlines()[0][:200]}"
        print(f"    ! {c.clave}: {c.error}\n{traceback.format_exc()}", file=sys.stderr)
    if imprimir:
        print(f"  {c.clave}  {c.nombre:<34}{c.estado:<6} {time.monotonic() - inicio:5.1f} s", flush=True)


def pase_escritorio(lab: Laboratorio, cs: dict[str, Comprobacion], tema: str, capturas: Path | None, totales: dict, indet: list[Indeterminado], activas: set[str]) -> None:
    """Una carga de cada pantalla en escritorio: captura, teclado (d), nombres (e) y contraste (f)."""
    t0 = time.monotonic()
    for pant in PANTALLAS:
        p = None
        try:
            p = lab.abrir(pant, "admin", tema=tema, etiqueta=f"{pant.clave}/{tema}")
            if capturas is not None:
                capturas.mkdir(parents=True, exist_ok=True)
                p.screenshot(path=capturas / f"{pant.clave}.png", full_page=True)
            if tema == "claro":
                if "d" in activas:
                    antes = len(cs["d"].fallas)
                    comprobar_teclado_pantalla(lab, p, pant, cs["d"])
                    lab.captura_si_falla(p, pant.clave, antes, cs["d"])
                if "e" in activas:
                    antes = len(cs["e"].fallas)
                    foco_al_inicio(p)
                    comprobar_nombres(lab, p, pant, cs["e"])
                    lab.captura_si_falla(p, pant.clave, antes, cs["e"])
            if "f" in activas:
                comprobar_contraste(lab, p, pant, tema, cs["f"], indet, totales)
        except Exception as e:  # noqa: BLE001 - una pantalla que se rompe no detiene a las demás
            mensaje = f"{type(e).__name__}: {str(e).splitlines()[0][:200]}"
            print(f"    ! {pant.clave}/{tema}: {mensaje}\n{traceback.format_exc()}", file=sys.stderr)
            for k in ("d", "e", "f"):
                if k in activas and (k == "f" or tema == "claro"):
                    cs[k].ok(False, f"{pant.clave}/{tema}: la pantalla se pudo recorrer", mensaje)
        finally:
            if p is not None:
                p.context.close()
    print(f"    pase de escritorio ({tema}) {time.monotonic() - t0:.0f} s", flush=True)


def pase_movil(lab: Laboratorio, c: Comprobacion) -> None:
    for tema in ("claro", "oscuro"):
        for pant in PANTALLAS:
            p = lab.abrir(pant, "admin", tema=tema, tamano=MOVIL, etiqueta=f"{pant.clave}/{tema}/movil")
            try:
                comprobar_movil(lab, p, pant, tema, c)
            finally:
                p.context.close()
    c.resumen = f"{len(PANTALLAS)} pantallas × 2 temas a 390 px"


def capturas_extra(lab: Laboratorio, carpeta: Path) -> None:
    """Capturas oscuras de lo que no es una sección: el detalle de una regla y el recorrido guiado (solo la ventana)."""
    carpeta.mkdir(parents=True, exist_ok=True)
    p = lab.abrir(Pantalla("validaciones", "/validaciones", con_dia=True), "admin", tema="oscuro", etiqueta="captura/detalle")
    p.locator("button.abrir-regla").first.click()
    p.get_by_role("dialog").wait_for()
    p.wait_for_timeout(600)
    p.screenshot(path=carpeta / "validaciones-detalle.png")
    p.context.close()
    p = lab.abrir(Pantalla("resumen", "/resumen", con_dia=True), "admin", tema="oscuro", etiqueta="captura/recorrido")
    p.click("#boton-recorrido")
    p.get_by_role("dialog").wait_for()
    for _ in range(4):
        p.keyboard.press("ArrowRight")
        p.wait_for_timeout(250)
    p.wait_for_timeout(4_500)
    p.screenshot(path=carpeta / "recorrido-guiado.png")
    p.context.close()


def conservar_notas(ruta: Path) -> str:
    """Lo escrito a mano al final de la evidencia (desde la marca de notas) sobrevive a una nueva corrida."""
    if ruta.exists():
        texto = ruta.read_text(encoding="utf-8")
        if MARCA_NOTAS in texto:
            return "\n" + texto[texto.index(MARCA_NOTAS):]
    return ""


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--arrancar", action="store_true", help=f"levanta su API ({PUERTO_API}) y su portal ({PUERTO_WEB}) sobre una copia de --db")
    parser.add_argument("--api-url", help="API ya levantada (sin --arrancar)")
    parser.add_argument("--web-url", help="portal ya levantado (sin --arrancar)")
    parser.add_argument("--db", type=Path, default=RAIZ / "data" / "dq_completo.duckdb")
    parser.add_argument("--rapido", action="store_true", help="sin capturas ni evidencia (es lo que corre el CI)")
    parser.add_argument("--dia", default=DIA_POR_DEFECTO, help="día de datos con el que se mide y se captura (si no existe, el último)")
    parser.add_argument("--solo", help="letras de las comprobaciones que se corren, separadas por coma (por ejemplo f,g)")
    parser.add_argument("--artefactos", type=Path, default=RAIZ / "data" / "verificar_portal")
    parser.add_argument("--evidencia", type=Path, default=RAIZ / "docs" / "evidencias" / "accesibilidad-y-e2e.txt")
    parser.add_argument("--capturas", type=Path, default=RAIZ / "docs" / "evidencias" / "portal" / "oscuro")
    args = parser.parse_args()
    if not args.arrancar and not (args.api_url and args.web_url):
        parser.error("indica --arrancar, o --api-url y --web-url de servidores ya levantados")
    activas = set(args.solo.replace(" ", "").lower().split(",")) if args.solo else set(NOMBRES)
    desconocidas = activas - set(NOMBRES)
    if desconocidas:
        parser.error(f"comprobaciones que no existen: {', '.join(sorted(desconocidas))} (las hay de la a a la i)")

    from playwright.sync_api import sync_playwright

    cs = {k: Comprobacion(k, n) for k, n in NOMBRES.items()}
    indeterminados: list[Indeterminado] = []
    totales = {"textos": 0, "ok": 0, "fallos": 0, "indeterminados": 0}
    inicio = time.monotonic()
    if args.artefactos.exists():
        borrar_carpeta_de_salida(args.artefactos)
    args.artefactos.mkdir(parents=True)
    (args.artefactos / MARCA_DE_SALIDA).write_text("carpeta de salida de scripts/verificar_portal.py\n", encoding="utf-8")
    servidores = Servidores(args.db, args.artefactos / "servidores") if args.arrancar else None
    version_chromium = "?"
    dia = args.dia
    try:
        if servidores:
            print(f"Levantando la API ({PUERTO_API}) y el portal ({PUERTO_WEB}) sobre una copia de {args.db} ...", flush=True)
            servidores.arrancar()
        api, web = (servidores.api, servidores.web) if servidores else (args.api_url.rstrip("/"), args.web_url.rstrip("/"))
        token = iniciar_sesion(api, ADMIN)["token"]
        _, cortes = pedir(api, "GET", "/api/v1/cortes", token=token)
        fechas = [x["fecha_corte"] for x in cortes] if isinstance(cortes, list) else []
        if dia not in fechas:
            dia = fechas[-1] if fechas else None
            print(f"  el día {args.dia} no está en la base: se usa {dia}", flush=True)
        vigia = Vigia(api, web)
        with sync_playwright() as pw:
            navegador = pw.chromium.launch()
            version_chromium = navegador.version
            print(f"Chromium {version_chromium} · día {dia} · {'rápido' if args.rapido else 'completo'}", flush=True)
            lab = Laboratorio(navegador, web, api, vigia, args.artefactos, dia)
            if "a" in activas:
                ejecutar(cs["a"], comprobar_inicio, lab)
            if "b" in activas:
                ejecutar(cs["b"], comprobar_roles, lab)
            if "c" in activas:
                ejecutar(cs["c"], comprobar_resumen, lab)
            if "d" in activas:
                ejecutar(cs["d"], comprobar_teclado_especial, lab, imprimir=False)
            claro = {"d", "e", "f"} & activas
            if claro:
                for k in claro:
                    cs[k].ejecutada = True
                print("  d/e/f  escritorio en tema claro ...", flush=True)
                pase_escritorio(lab, cs, "claro", None, totales, indeterminados, activas)
            capturas = None if (args.rapido or args.solo) else args.capturas
            if "f" in activas or capturas is not None:
                if "f" in activas:
                    cs["f"].ejecutada = True
                print("  f      escritorio en tema oscuro" + (" y capturas ..." if capturas else " ..."), flush=True)
                if capturas is not None and capturas.exists():
                    for vieja in capturas.glob("*.png"):  # solo las capturas de una corrida anterior, nada más
                        vieja.unlink()
                pase_escritorio(lab, cs, "oscuro", capturas, totales, indeterminados, activas)
                if capturas is not None:
                    capturas_extra(lab, capturas)
            if "f" in activas:
                cs["f"].resumen = (f"{totales['textos']} textos en {len(PANTALLAS)} pantallas × 2 temas: {totales['ok']} cumplen, "
                                   f"{totales['fallos']} fallan, {totales['indeterminados']} indeterminados")
            for k in claro:
                print(f"  {k}  {cs[k].nombre:<34}{cs[k].estado}", flush=True)
            if "g" in activas:
                ejecutar(cs["g"], pase_movil, lab)
            if "h" in activas:
                ejecutar(cs["h"], comprobar_movimiento_todo, lab)
            if "i" in activas:
                ejecutar(cs["i"], comprobar_errores, lab)
            navegador.close()
    finally:
        if servidores:
            servidores.apagar()

    comprobaciones = [cs[k] for k in NOMBRES]
    if "d" in activas:
        cs["d"].resumen = cs["d"].resumen or f"{len(PANTALLAS)} pantallas × {TABS} Tab, saltar al contenido, Esc en recorrido y detalle, mapa de días"
    if "e" in activas:
        cs["e"].resumen = cs["e"].resumen or f"{len(PANTALLAS)} pantallas: nombres, alt, ids, h1/main"
    cabecera = [
        "Smart-DQ · Verificación del portal: accesibilidad, teclado, tema oscuro, móvil y pruebas e2e de humo",
        f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Navegador: Chromium {version_chromium} (Playwright {metadata.version('playwright')}) · sin ventana",
        f"Base: copia de {args.db.relative_to(RAIZ) if args.db.is_relative_to(RAIZ) else args.db} · día de datos: {dia} · API {PUERTO_API}, portal {PUERTO_WEB}" if args.arrancar
        else f"Servidores: {args.api_url} y {args.web_url} · día de datos: {dia}",
        f"Modo: {'rápido (sin capturas)' if args.rapido else 'completo (con capturas oscuras a 1440 px)'}" + (f" · solo: {args.solo}" if args.solo else ""),
        f"Duración: {time.monotonic() - inicio:.0f} s",
    ]
    lineas_indet = lineas_indeterminados(indeterminados) if "f" in activas else None
    texto = informe(comprobaciones, cabecera, lineas_indet, EXCEPCIONES)
    print("\n" + texto)
    (args.artefactos / "resultado.txt").write_text(texto + "\n", encoding="utf-8")
    if not args.rapido and not args.solo:
        args.evidencia.parent.mkdir(parents=True, exist_ok=True)
        notas = conservar_notas(args.evidencia)
        archivos = sorted(p.name for p in args.capturas.glob("*.png")) if args.capturas.exists() else []
        extra = ["", "CAPTURAS EN TEMA OSCURO (1440 px, página completa salvo diálogos)", "-" * 58,
                 f"docs/evidencias/portal/oscuro/: {', '.join(archivos)}"]
        args.evidencia.write_text(texto + "\n" + "\n".join(extra) + "\n" + notas, encoding="utf-8")
        print(f"\nEvidencia: {args.evidencia}")
    falladas = [c.clave for c in comprobaciones if c.estado == "FAIL"]
    print(f"\n{'Todo en orden.' if not falladas else 'FALLAN: ' + ', '.join(falladas)}")
    raise SystemExit(1 if falladas else 0)


if __name__ == "__main__":
    main()
