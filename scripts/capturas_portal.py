"""Capturas del portal para docs/evidencias/portal, con Playwright (Chromium sin ventana).

Levanta una API local aislada sobre una copia de la corrida completa (sin simulación en vivo y
con su propia configuración en data/capturas/), el portal en modo desarrollo, saca cada captura y
apaga todo. Las capturas en vivo usan una copia de la base de la demo (cortes hasta el 24 de
septiembre). No toca data/dq.duckdb ni data/config_local.json.

  python scripts/capturas_portal.py [--completa data/dq_completo.duckdb] [--demo data/dq.duckdb]
                                    [--solo hu09-resumen,hu13-login]

Requiere Playwright con Chromium (pip install playwright && playwright install chromium) y
`npm ci` en web/. Cada captura que falla se informa y las demás siguen.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

RAIZ = Path(__file__).resolve().parents[1]
API, WEB = "http://127.0.0.1:8000", "http://localhost:5173"
CLAVE = "SmartDQ-2026"
ADMIN, GOBIERNO, LECTOR = "admin@demo.local", "gobierno@demo.local", "lector@demo.local"
VENTANA = {"width": 1440, "height": 900}
SOLO_VENTANA = {"hu13-validaciones-gobierno", "hu13-validaciones-lector", "hu09-panel-en-vivo"}


# ── servidores ─────────────────────────────────────────────────────────────


def esperar(url: str, segundos: float = 90) -> None:
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        try:
            urllib.request.urlopen(url, timeout=3).read()
            return
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            time.sleep(1)
    raise SystemExit(f"{url} no respondió en {segundos:.0f} s")


def levantar_api(base: Path, carpeta: Path, en_vivo: bool) -> subprocess.Popen:
    """API local sobre una copia de `base`, con configuración propia en `carpeta`."""
    if carpeta.exists():
        shutil.rmtree(carpeta)
    carpeta.mkdir(parents=True)
    shutil.copy(base, carpeta / "dq.duckdb")
    if en_vivo:  # el simulador lee las entregas pendientes de <carpeta>/landing
        landing = RAIZ / "data" / "landing"
        (carpeta / "landing").mkdir()
        shutil.copy(landing / "entregas.json", carpeta / "landing" / "entregas.json")
        for dia in sorted(p for p in landing.iterdir() if p.is_dir() and p.name > "2026-09-24"):
            shutil.copytree(dia, carpeta / "landing" / dia.name)
    entorno = {
        **os.environ,
        "DQC_DB": str(carpeta / "dq.duckdb"),
        "DQC_CONFIG_LOCAL": str(carpeta / "config_local.json"),
        "DQC_EN_VIVO": "1" if en_vivo else "0",
        "DQC_EN_VIVO_SEGUNDOS": "2",
        "PYTHONIOENCODING": "utf-8",
    }
    proceso = subprocess.Popen([sys.executable, "-m", "dqc.api", "--puerto", "8000"], cwd=RAIZ, env=entorno,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    esperar(f"{API}/health/readiness")
    return proceso


def levantar_web() -> subprocess.Popen:
    npm = "npm.cmd" if os.name == "nt" else "npm"
    proceso = subprocess.Popen([npm, "run", "dev", "--", "--strictPort"], cwd=RAIZ / "web",
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    esperar(WEB)
    return proceso


def apagar(proceso: subprocess.Popen) -> None:
    if os.name == "nt":  # npm lanza hijos: hay que cerrar el árbol completo
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proceso.pid)], capture_output=True)
    else:
        proceso.terminate()
    proceso.wait(timeout=30)


# ── API ────────────────────────────────────────────────────────────────────


def pedir(metodo: str, ruta: str, cuerpo: dict | None = None, token: str | None = None) -> dict | None:
    cabeceras = {"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})}
    pedido = urllib.request.Request(API + ruta, data=json.dumps(cuerpo).encode() if cuerpo is not None else None,
                                    method=metodo, headers=cabeceras)
    try:
        with urllib.request.urlopen(pedido) as r:
            return json.loads(r.read() or b"null")
    except urllib.error.HTTPError:
        return None  # los 403 buscados (acceso denegado) también llegan aquí


def sesion(email: str, clave: str = CLAVE) -> dict:
    return pedir("POST", "/api/v1/auth/sesion", {"email": email, "clave": clave})


# ── navegador ──────────────────────────────────────────────────────────────


class Capturador:
    def __init__(self, navegador, salida: Path):
        self.navegador = navegador
        self.salida = salida
        self.fallas: list[str] = []

    def pagina(self, sesion_: dict | None) -> Page:
        contexto = self.navegador.new_context(viewport=VENTANA, color_scheme="light", locale="es-PE")
        if sesion_:
            guardada = json.dumps({"token": sesion_["token"], "expira": sesion_["expira"]})
            contexto.add_init_script(f"sessionStorage.setItem('dqc.sesion', {json.dumps(guardada)})")
        pagina = contexto.new_page()
        pagina.on("dialog", lambda d: d.accept())
        return pagina

    @staticmethod
    def ir(pagina: Page, ruta: str, dia: str | None = None) -> None:
        pagina.goto(WEB + ruta)
        pagina.wait_for_load_state("networkidle")
        if dia:  # el día elegido vive en el store de Pinia, compartido por todos los módulos
            pagina.wait_for_function("() => document.querySelector('#app')?.__vue_app__")
            pagina.evaluate(
                "d => { document.querySelector('#app').__vue_app__.config.globalProperties.$pinia._s.get('cortes').elegido = d }",
                dia,
            )
            pagina.wait_for_load_state("networkidle")
        pagina.wait_for_timeout(700)  # animaciones de entrada

    def capturar(self, nombre: str, accion: Callable[[], Page]) -> None:
        try:
            pagina = accion()
            # Con un diálogo o un panel abierto, solo la ventana: el velo no cubre la página completa.
            pagina.screenshot(path=self.salida / f"{nombre}.png", full_page=nombre not in SOLO_VENTANA)
            pagina.context.close()
            print(f"  ok     {nombre}")
        except Exception as e:  # noqa: BLE001 - se informa y se sigue con la siguiente
            self.fallas.append(nombre)
            print(f"  FALLÓ  {nombre}: {str(e).splitlines()[0][:160]}")


def capturas_completas(c: Capturador) -> dict[str, Callable[[], Page]]:
    admin, gobierno, lector = sesion(ADMIN), sesion(GOBIERNO), sesion(LECTOR)

    def en(s, ruta, dia=None, despues=None):
        def accion():
            p = c.pagina(s)
            c.ir(p, ruta, dia)
            if despues:
                despues(p)
                p.wait_for_load_state("networkidle")
                p.wait_for_timeout(500)
            return p
        return accion

    def login_con_error():
        p = c.pagina(None)
        c.ir(p, "/entrar")
        p.fill("input[type=email]", LECTOR)
        p.fill("input[type=password]", "no-es-la-clave")
        p.click("button[type=submit]")
        p.get_by_text("Correo o contraseña incorrectos").wait_for()
        return p

    def detalle(regla):
        return lambda p: (p.get_by_role("button", name=regla, exact=True).first.click(),
                          p.get_by_role("dialog").wait_for())

    def alta(p):
        p.fill("input[placeholder='persona@dominio.com']", "nueva.analista@demo.local")
        p.click("button:has-text('Dar acceso')")
        p.get_by_text("Contraseña temporal").first.wait_for()

    def cambio_obligatorio():
        temporal = pedir("PUT", "/api/v1/admin/usuarios/pendiente@demo.local", {"rol": "lector"}, admin["token"])
        p = c.pagina(sesion("pendiente@demo.local", temporal["clave_temporal"]))
        c.ir(p, "/resumen")
        p.wait_for_url("**/clave**")
        return p

    def acceso_denegado(p):
        pedir("GET", "/api/v1/admin/usuarios", token=lector["token"])  # el intento queda auditado
        p.reload()
        p.wait_for_load_state("networkidle")
        p.get_by_role("button", name="Acceso denegado").click()

    return {
        "hu13-login": en(None, "/entrar"),
        "hu13-login-error": login_con_error,
        "hu09-resumen": en(gobierno, "/resumen"),
        "hu09-resumen-14-julio": en(gobierno, "/resumen", "2026-07-14"),
        "hu02-hu03-validaciones-14-julio": en(gobierno, "/validaciones", "2026-07-14"),
        "hu13-validaciones-gobierno": en(gobierno, "/validaciones", "2026-07-01", detalle("PER-VAL-04")),
        "hu13-validaciones-lector": en(lector, "/validaciones", "2026-07-01", detalle("PER-VAL-04")),
        "hu04-hu07-hu12-certificacion-7-agosto": en(gobierno, "/certificacion", "2026-08-07"),
        "hu04-hu12-certificacion-30-septiembre": en(gobierno, "/certificacion", "2026-09-30"),
        "hu01-fuentes-persona-llegadas": en(gobierno, "/fuentes", None, lambda p: p.get_by_role("button", name="Persona", exact=True).click()),
        "hu01-fuentes-siniestro-rechazo": en(gobierno, "/fuentes", None, lambda p: (
            p.get_by_role("button", name="Siniestro", exact=True).click(), p.get_by_label("Solo con problemas").check())),
        "hu14-fuentes-poliza-estructura": en(gobierno, "/fuentes", None, lambda p: p.get_by_role("button", name="Póliza", exact=True).click()),
        "hu05-contrato-dac": en(gobierno, "/contratos", None, lambda p: p.locator("button.cabecera", has_text="Persona").first.click()),
        "hu11-linaje": en(gobierno, "/linaje/persona"),
        "hu06-hu11-linaje-campo-cifrado": en(gobierno, "/linaje/persona", None, lambda p: p.locator("button.linea-campo", has_text="NUM_DOC").first.click()),
        "hu10-glosario-busqueda": en(gobierno, "/glosario", None, lambda p: p.get_by_label("Buscar término").fill("dni")),
        "hu03-reglas-configurables": en(admin, "/reglas"),
        "hu04-ejecuciones": en(admin, "/ejecuciones"),
        "hu13-usuarios": en(admin, "/usuarios"),
        "hu13-alta-clave-temporal": en(admin, "/usuarios", None, alta),
        "hu13-cambio-clave-obligatorio": cambio_obligatorio,
        "hu13-auditoria-acceso-denegado": en(admin, "/auditoria", None, acceso_denegado),
        "hu13-hu15-auditoria": en(admin, "/auditoria"),
    }


def capturas_en_vivo(c: Capturador) -> dict[str, Callable[[], Page]]:
    gobierno = sesion(GOBIERNO)

    def actividad():
        p = c.pagina(gobierno)
        c.ir(p, "/resumen")
        p.wait_for_timeout(9_000)  # llegan los primeros archivos del 25 de septiembre
        return p

    def panel():
        p = actividad()
        p.locator("button.pastilla").click()
        p.locator("#panel-vivo").wait_for()
        return p

    return {"hu09-actividad-en-vivo": actividad, "hu09-panel-en-vivo": panel}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--completa", type=Path, default=RAIZ / "data" / "dq_completo.duckdb")
    parser.add_argument("--demo", type=Path, default=RAIZ / "data" / "dq.duckdb")
    parser.add_argument("--salida", type=Path, default=RAIZ / "docs" / "evidencias" / "portal")
    parser.add_argument("--solo", help="nombres de captura separados por coma")
    args = parser.parse_args()
    solo = set(args.solo.split(",")) if args.solo else None
    capturas = RAIZ / "data" / "capturas"

    web = levantar_web()
    fallas: list[str] = []
    try:
        with sync_playwright() as pw:
            navegador = pw.chromium.launch()
            for fase, base, en_vivo, armar in (
                ("corrida completa", args.completa, False, capturas_completas),
                ("simulación en vivo", args.demo, True, capturas_en_vivo),
            ):
                api = levantar_api(base, capturas / ("vivo" if en_vivo else "completa"), en_vivo)
                try:
                    c = Capturador(navegador, args.salida)
                    print(f"{fase}:")
                    for nombre, accion in armar(c).items():
                        if solo is None or nombre in solo:
                            c.capturar(nombre, accion)
                    fallas += c.fallas
                finally:
                    apagar(api)
            navegador.close()
    finally:
        apagar(web)
    print(f"\n{'Todas las capturas listas.' if not fallas else 'Fallaron: ' + ', '.join(fallas)}")
    raise SystemExit(1 if fallas else 0)


if __name__ == "__main__":
    main()
