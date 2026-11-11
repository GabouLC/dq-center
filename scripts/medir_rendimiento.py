"""Mide el rendimiento del portal (HU-15: «cualquier sección carga en menos de 8 segundos»).

Para cada una de las 11 secciones del portal (las de MODULOS en src/dqc/api/app.py) mide el tiempo que
tarda en abrirse: las peticiones que el portal hace a la API, en el orden y con el paralelismo con que
las lanza (ver SECCIONES, deducido de web/src/vistas/*.vue, App.vue y los stores).

  Justo   primer recorrido apenas la API responde /health/liveness, sin esperar el precargado.
  Frío    primer recorrido tras /health/readiness (precargado terminado), una apertura por sección.
  Caliente  N aperturas seguidas por sección (p50, p95 y máximo).
  Concurrencia  varios usuarios a la vez, cada uno con su propia sesión, recorriendo todas las secciones.

La cabecera Server-Timing de cada respuesta (HU-15) separa el tiempo de la API del de red y cola.
El veredicto de cada sección compara con el límite de 8 s en frío y bajo concurrencia.

Modos (el script arranca SU PROPIA API en el puerto 8003 y la apaga al terminar):
  --modo local   DuckDB: usa una COPIA de data/dq_completo.duckdb y una configuración nueva en una
                 carpeta temporal; no toca data/dq*.duckdb ni data/config_local.json.
                 Evidencia: docs/evidencias/rendimiento.txt
  --modo gcp     BigQuery + Firestore (sandbox). Antes estima cuánto se va a leer (num_bytes, metadatos
                 gratis) y se detiene si pasa de 1 GB. Crea un administrador temporal en Firestore y lo
                 BORRA al terminar (usuario, credencial y eventos de auditoría), también si algo falla.
                 No lo corras mientras otro proceso reescribe las tablas de BigQuery: lo medido no valdría.
                 Evidencia: docs/evidencias/rendimiento-bigquery.txt

  python scripts/medir_rendimiento.py                          # local
  DQC_PROYECTO=dq-center-gabou python scripts/medir_rendimiento.py --modo gcp
  python scripts/medir_rendimiento.py --modo gcp --solo-estimar   # solo metadatos de BigQuery y sale
  python scripts/medir_rendimiento.py --caducidad              # suma una espera de 10 min: caché vencida con todos a la vez

Las funciones puras (percentiles, veredicto, plan de peticiones, informe) no arrancan nada y las prueba
tests/test_rendimiento.py. El resto necesita las dependencias del proyecto (.venv).
"""

from __future__ import annotations

import argparse
import http.client
import json
import math
import os
import platform
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
HOST = "127.0.0.1"
PUERTO = 8003
LIMITE_MS = 8000.0  # HU-15; tests/test_rendimiento.py lo compara con LIMITE_SEGUNDOS de la API
TIMEOUT_S = 30.0  # una petición que pasa de aquí se cuenta como error
TOPE_BYTES = 1024**3  # tope de lectura en BigQuery (mismo criterio que scripts/evidencia_bigquery.py)
CLAVE_DEMO = "SmartDQ-2026"  # cuentas *@demo.local del modo local (AGENTS.md)
ADMIN_DEMO = "admin@demo.local"  # solo el administrador ve las 11 secciones
PROYECTO_POR_DEFECTO = "dq-center-gabou"
VIGENCIA_CACHE_S = 600  # FuenteBusiness: las vistas quedan 10 minutos en memoria

# ── Qué pide el portal al abrir cada sección ─────────────────────────────────
# Se modela la peor apertura: recargar la página con la sesión guardada. Cada sección es una lista de
# etapas; las peticiones de una etapa van en paralelo y la etapa siguiente espera a la anterior:
#   E1  router.beforeEach espera a sesion.restaurar() -> /auth/me (web/src/stores/sesion.ts)
#   E2  la vista pide lo suyo con usarCarga (web/src/vistas/*.vue); App.vue arranca el sondeo de
#       /vivo (stores/vivo.ts) y, en Resumen, Validaciones y Certificación, LineaCortes pide /cortes
#   E3  cuando algo depende de /cortes: Validaciones y Certificación repiten su petición con el corte
#       elegido (usarCarga vigila cortes.elegido, que pasa de null al último), y el Resumen monta
#       LecturaRapida, que pide /certificacion y /validaciones/comparar con el día y el anterior.
# {ultimo} y {penultimo} son las dos últimas fechas de /cortes; la petición se arma al llegar a su etapa.
ME = "/api/v1/auth/me"
VIVO = "/api/v1/vivo?desde=0"
CORTES = "/api/v1/cortes"
SECCIONES: dict[str, list[list[str]]] = {
    "resumen": [
        [ME], [CORTES, "/api/v1/resumen", VIVO],
        ["/api/v1/certificacion?corte={ultimo}", "/api/v1/validaciones/comparar?a={penultimo}&b={ultimo}"],
    ],
    "validaciones": [[ME], [CORTES, "/api/v1/validaciones", VIVO], ["/api/v1/validaciones?corte={ultimo}"]],
    "certificacion": [[ME], [CORTES, "/api/v1/certificacion", VIVO], ["/api/v1/certificacion?corte={ultimo}"]],
    "fuentes": [[ME], ["/api/v1/fuentes", "/api/v1/fuentes/persona/estructura", VIVO]],
    "contratos": [[ME], ["/api/v1/contratos", VIVO]],
    "linaje": [[ME], ["/api/v1/linaje/persona", "/api/v1/glosario", VIVO]],
    "glosario": [[ME], ["/api/v1/glosario", VIVO]],
    "reglas": [[ME], ["/api/v1/reglas", VIVO]],
    "ejecuciones": [[ME], ["/api/v1/ejecuciones", VIVO]],
    "usuarios": [[ME], ["/api/v1/admin/usuarios", VIVO]],
    "auditoria": [[ME], ["/api/v1/admin/auditoria?limite=500", VIVO]],
}
MAX_PARALELAS = max(len(etapa) for etapas in SECCIONES.values() for etapa in etapas)
RUTA_FUENTES = "/api/v1/fuentes"


# ═══ Funciones puras (sin red ni procesos) ═══════════════════════════════════


def percentil(valores: Sequence[float], p: float) -> float:
    """Percentil p (0 a 100) con interpolación lineal entre vecinos (el método por defecto de NumPy)."""
    if not valores:
        raise ValueError("no hay valores para calcular el percentil")
    if not 0 <= p <= 100:
        raise ValueError("el percentil va de 0 a 100")
    orden = sorted(valores)
    k = (len(orden) - 1) * p / 100
    i = math.floor(k)
    j = min(i + 1, len(orden) - 1)
    return float(orden[i] + (orden[j] - orden[i]) * (k - i))


def estadisticas(valores: Sequence[float]) -> dict[str, float | int | None]:
    """n, p50, p95 y máximo; con una lista vacía, todo None."""
    if not valores:
        return {"n": 0, "p50": None, "p95": None, "max": None}
    return {"n": len(valores), "p50": percentil(valores, 50), "p95": percentil(valores, 95), "max": float(max(valores))}


def veredicto(frios: Sequence[float], concurrencia: Sequence[float], errores: int, limite_ms: float = LIMITE_MS) -> tuple[bool, str]:
    """CUMPLE si la peor apertura en frío y la peor bajo concurrencia son menores que el límite y no hubo errores.

    `frios` son las aperturas en frío (justo tras arrancar y tras el precargado); `concurrencia`, todas las de
    los usuarios simultáneos. Sin datos de una de las dos fases no se puede decir que cumple.
    """
    motivos = []
    if errores:
        motivos.append(f"{errores} errores")
    if not frios or max(frios) >= limite_ms:
        motivos.append("frío")
    if not concurrencia or max(concurrencia) >= limite_ms:
        motivos.append("carga")
    return (not motivos), ("CUMPLE" if not motivos else f"NO CUMPLE ({', '.join(motivos)})")


def ms_de_server_timing(cabecera: str | None) -> float | None:
    """Milisegundos de la métrica `app` de `Server-Timing: app;dur=123` (o de la primera con `dur`)."""
    if not cabecera:
        return None
    primera = None
    for metrica in cabecera.split(","):
        encontrado = re.search(r"dur=([0-9]+(?:\.[0-9]+)?)", metrica)
        if encontrado is None:
            continue
        if metrica.strip().startswith("app"):
            return float(encontrado.group(1))
        primera = primera if primera is not None else float(encontrado.group(1))
    return primera


def resolver(plantilla: str, cortes: Sequence[str]) -> str | None:
    """Arma la ruta con las dos últimas fechas de /cortes; None si la ruta necesita una que no hay."""
    fechas = sorted(cortes)
    if "{ultimo}" in plantilla and not fechas:
        return None
    if "{penultimo}" in plantilla and len(fechas) < 2:
        return None
    return plantilla.format(ultimo=fechas[-1] if fechas else "", penultimo=fechas[-2] if len(fechas) > 1 else "")


def fechas_de_cortes(cuerpo: bytes | None) -> list[str]:
    """Las fechas de corte que devuelve /api/v1/cortes (vacío si la respuesta no es la esperada)."""
    try:
        return sorted(str(c["fecha_corte"]) for c in json.loads(cuerpo or b"[]"))
    except (ValueError, KeyError, TypeError):
        return []


def datos_cargados(cortes: bytes | None, fuentes: bytes | None) -> tuple[int | None, int | None]:
    """(cortes evaluados, filas de las cargas EXITOSAS) a partir de /cortes y /fuentes; None si no se pudo leer."""
    try:
        lista = json.loads(cortes or b"")
        n_cortes = len(lista) if isinstance(lista, list) else None
    except ValueError:
        n_cortes = None
    try:
        tablas = json.loads(fuentes or b"")
        filas = sum(int(c["filas"]) for t in tablas for c in t["cargas"] if c["estado"] == "EXITOSA") if isinstance(tablas, list) else None
    except (ValueError, KeyError, TypeError):
        filas = None
    return n_cortes, filas


def estimar_lectura(tamanos: dict[str, int], leidas: Sequence[str], lecturas: int, tope: int = TOPE_BYTES) -> tuple[int, int, bool]:
    """(bytes de una lectura completa, total previsto, si pasa del tope).

    `tamanos` son los num_bytes de cada tabla; `leidas`, las que lee el portal al precargar; `lecturas`,
    cuántas veces se prevé leerlas. Se cuenta la tabla entera: es el tope superior de lo que escanea BigQuery.
    """
    por_lectura = sum(tamanos[t] for t in leidas)
    total = por_lectura * lecturas
    return por_lectura, total, total > tope


def lecturas_previstas(usuarios: int, caducidad: bool) -> int:
    """Cuántas veces se prevé que la API relea las vistas completas durante la corrida.

    6 de base, con holgura: 2 arranques (el hilo de precarga y la primera petición comparten una sola lectura) + 4
    renovaciones por si la corrida pasa de los 10 minutos y la caché vence. Con --caducidad, 2 más: al vencer, una
    petición renueva en segundo plano y las demás no leen (FuenteBusiness lee las vistas una sola vez); el parámetro
    de usuarios queda por si eso cambia.
    """
    return 6 + (2 if caducidad else 0)


def caducidad_cumple(cargas: Sequence["Carga"]) -> bool | None:
    """None si no se midió la caché vencida; si no, True cuando ninguna apertura falló ni llegó al límite."""
    if not cargas:
        return None
    return sum(c.errores for c in cargas) == 0 and max(c.ms for c in cargas) < LIMITE_MS


@dataclass
class Carga:
    """Una apertura de sección: tiempo de pared de todas sus etapas y lo que dijo el servidor."""

    ms: float
    servidor_ms: float  # suma, por etapa, del Server-Timing más alto
    peticiones: int
    errores: int = 0
    detalle: list[str] = field(default_factory=list)
    bytes: int = 0

    @property
    def red_ms(self) -> float:
        """Lo que no es tiempo de la API: conexión, cola del cliente y lectura de la respuesta."""
        return max(0.0, self.ms - self.servidor_ms)


@dataclass
class Medicion:
    justo: dict[str, Carga] = field(default_factory=dict)
    frio: dict[str, Carga] = field(default_factory=dict)
    caliente: dict[str, list[Carga]] = field(default_factory=dict)
    concurrencia: dict[str, list[Carga]] = field(default_factory=dict)
    inicios_de_sesion: list[float] = field(default_factory=list)  # ms, uno por usuario
    usuarios: int = 0
    rondas: int = 0
    repeticiones: int = 0
    vivo_s: float | None = None  # segundos hasta responder /health/liveness
    listo_s: float | None = None  # segundos hasta /health/readiness
    cortes: int | None = None
    filas: int | None = None
    lentas: int | None = None  # eventos RENDIMIENTO_LENTO que registró la API
    ultimas_fechas: list[str] = field(default_factory=list)  # las dos últimas de /cortes: {penultimo} y {ultimo}
    caducidad: list[Carga] = field(default_factory=list)  # aperturas del Resumen, todos a la vez, con la caché vencida


@dataclass
class Meta:
    modo: str
    fecha: str
    versiones: dict[str, str]
    maquina: str
    base: str
    puerto: int = PUERTO
    estimacion: str | None = None  # bloque de lectura prevista en BigQuery (solo modo gcp)


def formato_ms(valor: float | None) -> str:
    if valor is None:
        return "-"
    return f"{valor:.1f}" if valor < 100 else f"{valor:.0f}"


def tabla_texto(encabezado: Sequence[str], filas: Sequence[Sequence[str]], izquierda: Sequence[int] = (0,)) -> str:
    """Tabla de texto plano con columnas alineadas, como la de docs/evidencias/bigquery.txt."""
    anchos = [max(len(str(x)) for x in columna) for columna in zip(encabezado, *filas)]

    def linea(celdas: Sequence[str]) -> str:
        return "  ".join(
            str(c).ljust(a) if i in izquierda else str(c).rjust(a) for i, (c, a) in enumerate(zip(celdas, anchos))
        ).rstrip()

    return "\n".join([linea(encabezado), "  ".join("-" * a for a in anchos), *(linea(f) for f in filas)])


def _stat(valores: Sequence[float], clave: str) -> str:
    return formato_ms(estadisticas(valores)[clave])  # type: ignore[arg-type]


def informe(m: Medicion, meta: Meta) -> tuple[str, int]:
    """El texto de la evidencia y cuántas secciones cumplen. Pura: no mide nada."""
    cumplen, filas, filas_red, errores_vistos = 0, [], [], []
    for clave, etapas in SECCIONES.items():
        justo, frio = m.justo.get(clave), m.frio.get(clave)
        cal, conc = m.caliente.get(clave, []), m.concurrencia.get(clave, [])
        todas = [c for c in (justo, frio, *cal, *conc) if c is not None]
        errores = sum(c.errores for c in todas)
        errores_vistos += [d for c in todas for d in c.detalle]
        ok, texto = veredicto([c.ms for c in (justo, frio) if c is not None], [c.ms for c in conc], errores)
        cumplen += ok
        cal_ms, conc_ms = [c.ms for c in cal], [c.ms for c in conc]
        filas.append([
            clave, str(sum(len(e) for e in etapas)), str(len(etapas)),
            formato_ms(justo.ms if justo else None), formato_ms(frio.ms if frio else None),
            _stat(cal_ms, "p50"), _stat(cal_ms, "p95"), _stat(cal_ms, "max"),
            _stat(conc_ms, "p95"), _stat(conc_ms, "max"), str(errores), texto,
        ])
        kb = (sum(c.bytes for c in cal) / len(cal) / 1024) if cal else None
        filas_red.append([
            clave,
            _stat(cal_ms, "p50"), _stat([c.servidor_ms for c in cal], "p50"), _stat([c.red_ms for c in cal], "p50"),
            _stat(conc_ms, "p95"), _stat([c.servidor_ms for c in conc], "p95"), _stat([c.red_ms for c in conc], "p95"),
            formato_ms(kb),
        ])

    todas_las_aperturas = [
        (c.ms, clave, fase)
        for clave in SECCIONES
        for fase, cargas in (
            ("justo", [m.justo.get(clave)]), ("frío", [m.frio.get(clave)]),
            ("caliente", m.caliente.get(clave, [])), ("concurrencia", m.concurrencia.get(clave, [])),
        )
        for c in cargas if c is not None
    ] + [(c.ms, "resumen", "caché vencida") for c in m.caducidad]
    lineas = [
        f"Rendimiento del portal (HU-15: cada sección carga en menos de 8 s) · modo {meta.modo} · {meta.fecha}",
        "Python {python} · duckdb {duckdb} · FastAPI {fastapi} · uvicorn {uvicorn}".format(**meta.versiones),
        f"Máquina: {meta.maquina} · API y cliente en la misma máquina ({HOST}:{meta.puerto}), un solo proceso de uvicorn",
        f"Datos: {m.cortes if m.cortes is not None else '?'} cortes evaluados · "
        f"{m.filas if m.filas is not None else '?'} filas cargadas a RAW en las 5 tablas por corte (cargas EXITOSAS) · sintéticos",
        f"Base: {meta.base}",
    ]
    if m.vivo_s is not None:
        lineas.append(
            f"Arranque de la API: responde /health/liveness a los {m.vivo_s:.1f} s"
            + (f" y /health/readiness a los {m.listo_s:.1f} s" if m.listo_s is not None else "")
        )
    if meta.estimacion:
        lineas += ["", meta.estimacion]
    lineas += [
        "",
        "Cómo se midió",
        "- Abrir una sección es lo que hace el portal al recargar la página con la sesión guardada: primero /auth/me; después, en",
        "  paralelo, lo propio de la sección más /vivo; y, donde una petición depende de otra, una etapa más. El tiempo es el de",
        "  pared: la suma de las etapas, y en cada etapa vale la petición más lenta (no la suma de todas).",
        "- Justo: primer recorrido de las 11 secciones apenas la API responde /health/liveness, sin esperar el precargado de las vistas.",
        "- Frío: primer recorrido tras /health/readiness (precargado terminado), una apertura por sección.",
        f"- Caliente: {m.repeticiones} aperturas seguidas por sección (p50, p95 y máximo).",
        f"- Concurrencia: {m.usuarios} usuarios, cada uno con su propio inicio de sesión (administrador, la única cuenta que ve las 11",
        f"  secciones); luego recorren las 11 secciones a la vez, {m.rondas} rondas: {m.usuarios * m.rondas} aperturas por sección.",
        "- Veredicto: CUMPLE si la peor apertura en frío (la de «justo» o la de «frío») y la peor bajo concurrencia son menores de",
        "  8000 ms y no hubo errores. Los tiempos van en milisegundos.",
        "- Alcance: mide la API hasta el último byte; no incluye bajar el JavaScript ni dibujar la pantalla en el navegador.",
        "",
        "Peticiones que el portal hace al abrir cada sección (E = etapa; las de una misma etapa van en paralelo)",
    ]
    if len(m.ultimas_fechas) == 2:
        lineas.append(f"({{ultimo}} y {{penultimo}} son las dos últimas fechas de /cortes: {m.ultimas_fechas[1]} y {m.ultimas_fechas[0]})")
    for clave, etapas in SECCIONES.items():
        lineas.append(clave)
        lineas += [f"  E{i}  " + ", ".join(e) for i, e in enumerate(etapas, 1)]
    lineas += [
        "",
        "Tiempos de apertura por sección (ms)",
        tabla_texto(
            ["sección", "pet.", "et.", "justo", "frío", "cal. p50", "cal. p95", "cal. máx", "conc. p95", "conc. máx", "err.", "veredicto"],
            filas, izquierda=(0, 11),
        ),
        "",
        "Servidor y red (ms): «servidor» es el Server-Timing de la API; «red y cola» es el resto (conexión, cola del cliente, lectura)",
        tabla_texto(
            ["sección", "cal. p50", "servidor", "red y cola", "conc. p95", "servidor", "red y cola", "KB"],
            filas_red,
        ),
        "",
    ]
    if m.inicios_de_sesion:
        e = estadisticas(m.inicios_de_sesion)
        lineas.append(
            f"Inicio de sesión (PBKDF2, {len(m.inicios_de_sesion)} seguidos): p50 {formato_ms(e['p50'])} ms · "
            f"p95 {formato_ms(e['p95'])} ms · máx {formato_ms(e['max'])} ms"
        )
    if m.caducidad:
        ms = [c.ms for c in m.caducidad]
        e = estadisticas(ms)
        errores = sum(c.errores for c in m.caducidad)
        cumple = caducidad_cumple(m.caducidad)
        errores_vistos += [d for c in m.caducidad for d in c.detalle]
        lineas.append(
            f"Caché vencida ({len(ms)} usuarios abren el Resumen a la vez tras esperar a que venza; se les responde con lo último leído): mejor {formato_ms(min(ms))} ms · "
            f"p50 {formato_ms(e['p50'])} ms · peor {formato_ms(e['max'])} ms (API del peor: {formato_ms(max(c.servidor_ms for c in m.caducidad))} ms)"
            f" · {errores} errores · {'CUMPLE' if cumple else 'NO CUMPLE'} el límite de 8 s"
        )
    if todas_las_aperturas:
        peor = max(todas_las_aperturas)
        lineas.append(f"Apertura más lenta de todo el recorrido: {formato_ms(peor[0])} ms ({peor[1]}, {peor[2]})")
    if m.lentas is not None:
        lineas.append(f"Solicitudes que la propia API midió por encima de 8 s (auditoría RENDIMIENTO_LENTO): {m.lentas}")
    if errores_vistos:
        lineas.append("Errores vistos (hasta 5 distintos):")
        lineas += [f"  - {d}" for d in list(dict.fromkeys(errores_vistos))[:5]]
    lineas += [
        "",
        "Límites de la medición",
        "- Una sola máquina: el cliente de medición y la API comparten CPU, y cualquier otro proceso en marcha suma ruido.",
        "- «Justo» se parece a «frío» cuando el precargado de las vistas ya terminó al llegar la primera petición, como pasa con",
        "  DuckDB (el inicio de sesión tarda más que el precargado). Con la caché vacía de verdad (un arranque lento sobre BigQuery",
        "  o la caché vencida a los 10 minutos), FuenteBusiness lee las vistas una sola vez: al vencer los 10 minutos las peticiones",
        "  reciben lo último leído y una renueva en segundo plano; con datos nuevos (un corte publicado) esperan esa lectura.",
        "- La caché vencida " + (
            "se midió con --caducidad: es la fila «Caché vencida» de arriba."
            if m.caducidad else "no se midió en esta corrida (opción --caducidad, espera 10 minutos)."
        ),
        "- Los usuarios son sesiones distintas de una misma cuenta de administrador (con otros roles se ven menos secciones). Sus inicios",
        "  de sesión van de uno en uno: la API cuenta como intento cada inicio en curso (HU-13) y rechaza con 423 el sexto simultáneo.",
        f"Resultado: {cumplen} de {len(SECCIONES)} secciones por debajo de 8 s en frío y bajo carga",
    ]
    return "\n".join(lineas) + "\n", cumplen


# ═══ Cliente HTTP ════════════════════════════════════════════════════════════


@dataclass
class Respuesta:
    ruta: str
    estado: int | None
    ms: float
    servidor_ms: float | None
    bytes: int
    cuerpo: bytes | None
    error: str | None


def pedir(puerto: int, ruta: str, token: str | None = None, cuerpo: dict | None = None, guardar: bool = False,
          timeout: float = TIMEOUT_S) -> Respuesta:
    """Una petición con conexión nueva (como la primera de un navegador). Cualquier fallo queda en `error`."""
    inicio = time.perf_counter()
    conexion = http.client.HTTPConnection(HOST, puerto, timeout=timeout)
    try:
        cabeceras = {"Accept": "application/json", "Connection": "close"}
        if token:
            cabeceras["Authorization"] = f"Bearer {token}"
        datos = None
        if cuerpo is not None:
            datos = json.dumps(cuerpo).encode()
            cabeceras["Content-Type"] = "application/json"
        conexion.request("POST" if cuerpo is not None else "GET", ruta, body=datos, headers=cabeceras)
        respuesta = conexion.getresponse()
        leido = respuesta.read()
        ms = (time.perf_counter() - inicio) * 1000
        return Respuesta(
            ruta, respuesta.status, ms, ms_de_server_timing(respuesta.getheader("Server-Timing")), len(leido),
            leido if guardar else None, None if respuesta.status == 200 else f"HTTP {respuesta.status}",
        )
    except (OSError, http.client.HTTPException) as e:
        return Respuesta(ruta, None, (time.perf_counter() - inicio) * 1000, None, 0, None, type(e).__name__)
    finally:
        conexion.close()


def iniciar_sesion(puerto: int, email: str, clave: str) -> tuple[str, float]:
    """Un inicio de sesión. Los de una misma cuenta van de uno en uno: la API cuenta como intento cada inicio en curso
    (HU-13, contra el paralelismo) y con cinco en curso responde 423 al sexto, aunque la contraseña sea correcta."""
    r = pedir(puerto, "/api/v1/auth/sesion", cuerpo={"email": email, "clave": clave}, guardar=True)
    if r.error or not r.cuerpo:
        raise RuntimeError(f"no se pudo iniciar sesión ({r.error})")
    return json.loads(r.cuerpo)["token"], r.ms


def abrir_seccion(puerto: int, token: str, etapas: list[list[str]], ejecutor: ThreadPoolExecutor,
                  conservar: Sequence[str] = ()) -> tuple[Carga, dict[str, bytes]]:
    """Abre una sección como el portal: etapa por etapa, con las peticiones de cada etapa en paralelo."""
    inicio = time.perf_counter()
    cortes: list[str] = []
    errores: list[str] = []
    servidor, peticiones, total_bytes, cuerpos = 0.0, 0, 0, {}
    guardar = {CORTES, *conservar}
    for etapa in etapas:
        rutas = []
        for plantilla in etapa:
            ruta = resolver(plantilla, cortes)
            if ruta:
                rutas.append(ruta)
            elif "{" in plantilla:
                # Sin fechas de /cortes no se puede armar: no se descarta en silencio, la apertura cuenta como fallida.
                errores.append(f"{plantilla}: no se pudo armar, /cortes no dio las fechas")
        if len(rutas) == 1:
            respuestas = [pedir(puerto, rutas[0], token, guardar=rutas[0].split("?")[0] in guardar)]
        else:
            respuestas = list(ejecutor.map(lambda r: pedir(puerto, r, token, guardar=r.split("?")[0] in guardar), rutas))
        servidor += max((r.servidor_ms or 0.0 for r in respuestas), default=0.0)
        for r in respuestas:
            peticiones += 1
            total_bytes += r.bytes
            base = r.ruta.split("?")[0]
            if r.error:
                errores.append(f"{r.ruta}: {r.error}")
            elif base == CORTES:
                cortes = fechas_de_cortes(r.cuerpo)
            if r.cuerpo is not None and base in conservar:
                cuerpos[base] = r.cuerpo
    ms = (time.perf_counter() - inicio) * 1000
    return Carga(ms, servidor, peticiones, len(errores), errores[:3], total_bytes), cuerpos


# ═══ Fases de la medición ════════════════════════════════════════════════════


def recorrido_en_frio(puerto: int, token: str, conservar: Sequence[str] = ()) -> tuple[dict[str, Carga], dict[str, bytes]]:
    """Una apertura de cada sección, en el orden del menú."""
    cargas, cuerpos = {}, {}
    with ThreadPoolExecutor(MAX_PARALELAS) as ejecutor:
        for clave, etapas in SECCIONES.items():
            cargas[clave], guardados = abrir_seccion(puerto, token, etapas, ejecutor, conservar)
            cuerpos.update(guardados)
    return cargas, cuerpos


def fase_caliente(puerto: int, token: str, repeticiones: int) -> dict[str, list[Carga]]:
    with ThreadPoolExecutor(MAX_PARALELAS) as ejecutor:
        return {
            clave: [abrir_seccion(puerto, token, etapas, ejecutor)[0] for _ in range(repeticiones)]
            for clave, etapas in SECCIONES.items()
        }


def fase_concurrencia(puerto: int, usuarios: int, rondas: int, email: str, clave: str) -> tuple[dict[str, list[Carga]], list[float]]:
    """`usuarios` sesiones a la vez; cada ronda empieza junta y todos recorren las secciones en el mismo orden."""
    # (los inicios de sesión, uno tras otro; después, todos recorren a la vez)
    sesiones = [iniciar_sesion(puerto, email, clave) for _ in range(usuarios)]  # de uno en uno (ver iniciar_sesion)
    tokens = [t for t, _ in sesiones]
    barrera = threading.Barrier(usuarios)
    por_usuario: list[dict[str, list[Carga]]] = [{} for _ in range(usuarios)]
    fallos: list[str] = []

    def recorrer(i: int) -> None:
        try:
            with ThreadPoolExecutor(MAX_PARALELAS) as ejecutor:
                for _ in range(rondas):
                    barrera.wait(timeout=180)
                    for seccion, etapas in SECCIONES.items():
                        por_usuario[i].setdefault(seccion, []).append(abrir_seccion(puerto, tokens[i], etapas, ejecutor)[0])
        except Exception as e:  # noqa: BLE001 - se informa y se corta a los demás
            fallos.append(f"usuario {i}: {e!r}")
            barrera.abort()

    hilos = [threading.Thread(target=recorrer, args=(i,)) for i in range(usuarios)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    if fallos:
        raise RuntimeError("falló la fase de concurrencia: " + "; ".join(fallos))
    unidas = {s: [c for u in por_usuario for c in u[s]] for s in SECCIONES}
    return unidas, [ms for _, ms in sesiones]


def fase_caducidad(puerto: int, usuarios: int, email: str, clave: str, espera_s: float) -> list[Carga]:
    """Espera a que venza la caché de las vistas y abre el Resumen con todos los usuarios a la vez.

    Mide lo que ve el usuario justo al vencer: se responde con lo último leído y una petición renueva aparte.

    Los inicios de sesión se hacen antes de esperar (su PBKDF2 no cuenta). La espera cuenta desde la última
    petición, y la caché se renovó como tarde en ella: pasados 10 minutos está vencida.
    """
    tokens = [iniciar_sesion(puerto, email, clave)[0] for _ in range(usuarios)]
    print(f"    caché vencida: esperando {espera_s:.0f} s...", flush=True)
    time.sleep(espera_s)
    barrera = threading.Barrier(usuarios)

    def abrir(token: str) -> Carga:
        with ThreadPoolExecutor(MAX_PARALELAS) as ejecutor:
            barrera.wait(timeout=60)
            return abrir_seccion(puerto, token, SECCIONES["resumen"], ejecutor)[0]

    with ThreadPoolExecutor(usuarios) as pool:
        return list(pool.map(abrir, tokens))


def contar_lentas(puerto: int, token: str) -> int | None:
    """Cuántas solicitudes pasaron de 8 s según la propia API (auditoría RENDIMIENTO_LENTO)."""
    r = pedir(puerto, "/api/v1/admin/auditoria?limite=1000", token, guardar=True)
    try:
        return sum(1 for e in json.loads(r.cuerpo or b"") if e.get("accion") == "RENDIMIENTO_LENTO") if not r.error else None
    except (ValueError, AttributeError):
        return None


# ═══ La API propia ═══════════════════════════════════════════════════════════


def puerto_ocupado(puerto: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((HOST, puerto)) == 0


class ApiPropia:
    """Arranca `python -m dqc.api` con el entorno dado y lo apaga al salir; nunca mide una API ajena."""

    def __init__(self, puerto: int, entorno: dict[str, str], registro: Path):
        self.puerto, self.entorno, self.registro = puerto, entorno, registro
        self.proceso: subprocess.Popen | None = None
        self._registro = None
        self._t0 = 0.0

    def __enter__(self) -> ApiPropia:
        limite = time.monotonic() + 10  # el puerto de la API anterior tarda un instante en liberarse
        while puerto_ocupado(self.puerto) and time.monotonic() < limite:
            time.sleep(0.2)
        if puerto_ocupado(self.puerto):
            raise RuntimeError(f"el puerto {self.puerto} ya está en uso: no se mide una API ajena. Detén ese proceso o usa --puerto")
        self._registro = open(self.registro, "ab")  # noqa: SIM115 - se cierra en __exit__
        self._t0 = time.perf_counter()
        self.proceso = subprocess.Popen(
            [sys.executable, "-m", "dqc.api", "--puerto", str(self.puerto)],
            cwd=RAIZ, env=self.entorno, stdin=subprocess.DEVNULL, stdout=self._registro, stderr=subprocess.STDOUT,
        )
        return self

    def __exit__(self, *_) -> None:
        if self.proceso and self.proceso.poll() is None:
            self.proceso.terminate()
            try:
                self.proceso.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.proceso.kill()
                self.proceso.wait()
        if self._registro:
            self._registro.close()

    def cola_del_registro(self, lineas: int = 12) -> str:
        try:
            return "\n".join(self.registro.read_text(encoding="utf-8", errors="replace").splitlines()[-lineas:])
        except OSError:
            return "(sin registro)"

    def esperar(self, ruta: str, maximo_s: float) -> float:
        """Segundos desde el arranque hasta que `ruta` responde 200."""
        assert self.proceso is not None
        while time.perf_counter() - self._t0 < maximo_s:
            if self.proceso.poll() is not None:
                raise RuntimeError(f"la API terminó con código {self.proceso.returncode}:\n{self.cola_del_registro()}")
            if pedir(self.puerto, ruta, timeout=5).error is None:
                return time.perf_counter() - self._t0
            time.sleep(0.05)
        raise RuntimeError(f"la API no respondió {ruta} en {maximo_s:.0f} s:\n{self.cola_del_registro()}")


def entorno_de(modo: str, carpeta: Path, nombre: str, base: Path | None, proyecto: str) -> dict[str, str]:
    """Entorno limpio de DQC_*: nada heredado de la sesión (otra base, Firebase, un Cloud Run Job...)."""
    entorno = {k: v for k, v in os.environ.items() if not k.startswith("DQC_") and k != "K_SERVICE"}
    entorno.update(PYTHONIOENCODING="utf-8", DQC_CONFIG=str(RAIZ / "config"), DQC_CONFIG_LOCAL=str(carpeta / f"config_local_{nombre}.json"))
    if modo == "local":
        entorno.update(DQC_DB=str(base), DQC_EN_VIVO="0", DQC_DEMO="1")
    else:
        entorno.update(DQC_MODO="gcp", DQC_PROYECTO=proyecto, DQC_SANDBOX="1", DQC_DEMO="0", DQC_SECRETO=secrets.token_hex(32))
    return entorno


def medir(args: argparse.Namespace, carpeta: Path, base: Path | None, email: str, clave: str) -> Medicion:
    """Dos arranques de la API: el primero mide «justo»; el segundo, frío, caliente, concurrencia y, si se pide, caché vencida."""
    m = Medicion(usuarios=args.usuarios, rondas=args.rondas, repeticiones=args.repeticiones)
    espera = 120.0 if args.modo == "local" else 300.0

    print("1/2 Arranque sin esperar el precargado (justo)", flush=True)
    with ApiPropia(args.puerto, entorno_de(args.modo, carpeta, "justo", base, args.proyecto), carpeta / "api_justo.log") as api:
        api.esperar("/health/liveness", espera)
        token, _ = iniciar_sesion(args.puerto, email, clave)
        m.justo, _ = recorrido_en_frio(args.puerto, token)
    print("    " + ", ".join(f"{s} {formato_ms(c.ms)}" for s, c in m.justo.items()), flush=True)

    print("2/2 Arranque con precargado listo: frío, caliente y concurrencia", flush=True)
    with ApiPropia(args.puerto, entorno_de(args.modo, carpeta, "principal", base, args.proyecto), carpeta / "api_principal.log") as api:
        m.vivo_s = api.esperar("/health/liveness", espera)
        m.listo_s = api.esperar("/health/readiness", espera)
        token, _ = iniciar_sesion(args.puerto, email, clave)
        m.frio, cuerpos = recorrido_en_frio(args.puerto, token, conservar=(CORTES, RUTA_FUENTES))
        m.cortes, m.filas = datos_cargados(cuerpos.get(CORTES), cuerpos.get(RUTA_FUENTES))
        m.ultimas_fechas = fechas_de_cortes(cuerpos.get(CORTES))[-2:]
        print("    frío: " + ", ".join(f"{s} {formato_ms(c.ms)}" for s, c in m.frio.items()), flush=True)
        m.caliente = fase_caliente(args.puerto, token, args.repeticiones)
        print(f"    caliente: {args.repeticiones} aperturas por sección, listo", flush=True)
        m.concurrencia, m.inicios_de_sesion = fase_concurrencia(args.puerto, args.usuarios, args.rondas, email, clave)
        print(f"    concurrencia: {args.usuarios} usuarios x {args.rondas} rondas, listo", flush=True)
        if args.caducidad:
            m.caducidad = fase_caducidad(args.puerto, args.usuarios, email, clave, VIGENCIA_CACHE_S + 5)
            print("    caché vencida: " + ", ".join(formato_ms(c.ms) for c in m.caducidad), flush=True)
        m.lentas = contar_lentas(args.puerto, token)
    return m


# ═══ Modo local ══════════════════════════════════════════════════════════════


def copiar_base(origen: Path, carpeta: Path) -> Path:
    """Copia de la base (y de su .wal, si lo hay) en la carpeta temporal: el original no se abre ni se escribe."""
    if not origen.exists():
        raise SystemExit(f"No existe {origen}. Genera los datos con el pipeline o indica --db.")
    destino = carpeta / "dq_rendimiento.duckdb"
    shutil.copyfile(origen, destino)
    wal = origen.with_name(origen.name + ".wal")
    if wal.exists():
        shutil.copyfile(wal, destino.with_name(destino.name + ".wal"))
    return destino


# ═══ Modo gcp: estimación de lectura y administrador temporal ═════════════════


def tablas_de_las_vistas() -> tuple[list[str], list[str]]:
    """(todas las tablas que leen las vistas v_calidad_*, las que lee el portal al precargar), como dataset.tabla.

    Se deriva del propio código: publicacion.TABLAS_BASE (lo que hay detrás de las vistas) y datos.CONSULTAS
    (las vistas que lee el portal; `fallidos` e `incidencias` por tabla se piden solo al abrir un detalle).
    """
    from dqc.api.datos import CONSULTAS
    from dqc.modelo import ENGINE, MASTER, RAW
    from dqc.pipeline.publicacion import TABLAS_BASE

    todas = [f"{d}.{t}" for d, t, _ in TABLAS_BASE]
    vistas = {m for sql in CONSULTAS.values() for m in re.findall(r"v_calidad_(\w+)", sql)}
    destino = {"cargas": f"{RAW}.registro_cargas", "incidencias": f"{MASTER}.incidencias_homologacion"}
    leidas = [destino.get(v, f"{ENGINE}.{v}") for v in sorted(vistas)]
    desconocidas = [t for t in leidas if t not in todas]
    if desconocidas:
        raise RuntimeError(f"las vistas del portal leen tablas que no están en TABLAS_BASE: {desconocidas}")
    return todas, leidas


def estimar_bytes_bigquery(proyecto: str, lecturas: int) -> tuple[str, bool]:
    """Texto de la estimación y si pasa del tope. Solo lee metadatos (num_bytes): no ejecuta consultas ni cuesta."""
    from google.cloud import bigquery

    from dqc.plataforma.bigquery import UBICACION

    todas, leidas = tablas_de_las_vistas()
    cliente = bigquery.Client(project=proyecto, location=UBICACION)
    tamanos = {t: int(cliente.get_table(f"{proyecto}.{t}").num_bytes or 0) for t in todas}
    por_lectura, total, pasa = estimar_lectura(tamanos, leidas, lecturas)
    filas = [[t, f"{tamanos[t] / 1e6:.2f}", "sí" if t in leidas else "no (solo al abrir un detalle)"] for t in todas]
    texto = "\n".join([
        f"Lectura prevista en BigQuery (num_bytes de las tablas detrás de las vistas v_calidad_*; metadatos, sin costo) · proyecto {proyecto}",
        tabla_texto(["tabla", "MB", "la lee el portal al precargar"], filas, izquierda=(0, 2)),
        f"Una lectura completa de lo que precarga el portal: {por_lectura / 1e6:.2f} MB. Lecturas previstas: {lecturas} "
        f"(ver lecturas_previstas). Total previsto: {total / 1e6:.2f} MB "
        "(tope 1 GB; el sandbox no tiene facturación).",
    ])
    return texto, pasa


class AdminTemporal:
    """Administrador de prueba en Firestore (el modo gcp no tiene cuentas de demostración); siempre se borra."""

    def __init__(self, proyecto: str):
        from google.cloud import firestore

        self.db = firestore.Client(project=proyecto)
        self.email = f"rendimiento-hu15-{secrets.token_hex(3)}@demo.local"
        self.clave = secrets.token_urlsafe(24)  # solo en memoria

    def crear(self) -> None:
        from dqc.api.autenticacion import Autenticador, Sesiones
        from dqc.gcp.firestore import ConfiguracionFirestore

        config = ConfiguracionFirestore(self.db)
        config.guardar_usuario(self.email, "admin", "rendimiento-hu15")
        Autenticador(config, Sesiones(secrets.token_bytes(32))).fijar(self.email, self.clave, debe_cambiar=False)

    def borrar(self) -> str:
        """Borra usuario, credencial y eventos de auditoría de la cuenta, y comprueba que no quedó nada."""
        from google.cloud.firestore_v1.base_query import FieldFilter

        from dqc.gcp.firestore import AUDITORIA, CREDENCIALES, USUARIOS

        self.db.collection(USUARIOS).document(self.email).delete()
        self.db.collection(CREDENCIALES).document(self.email).delete()
        eventos = self.db.collection(AUDITORIA).where(filter=FieldFilter("email", "==", self.email))
        borrados = 0
        for doc in eventos.stream():
            doc.reference.delete()
            borrados += 1
        quedan = (
            self.db.collection(USUARIOS).document(self.email).get().exists
            or self.db.collection(CREDENCIALES).document(self.email).get().exists
            or any(True for _ in eventos.limit(1).stream())
        )
        if quedan:
            raise RuntimeError(f"NO se pudo borrar por completo la cuenta temporal {self.email}: revísala en Firestore")
        return f"cuenta temporal {self.email} borrada (usuario, credencial y {borrados} eventos de auditoría)"


# ═══ Programa ════════════════════════════════════════════════════════════════


def borrar_carpeta(carpeta: Path) -> None:
    """Borra la carpeta temporal que creó este script (con la copia de la base). En Windows el archivo puede tardar
    un instante en soltarse al apagar la API, así que reintenta; si no puede, avisa dónde quedó."""
    for _ in range(10):
        shutil.rmtree(carpeta, ignore_errors=True)
        if not carpeta.exists():
            return
        time.sleep(0.5)
    print(f"ATENCIÓN: no se pudo borrar la carpeta temporal {carpeta}; bórrala a mano.", file=sys.stderr)


def versiones() -> dict[str, str]:
    def de(paquete: str) -> str:
        try:
            return metadata.version(paquete)
        except metadata.PackageNotFoundError:
            return "no instalado"

    return {"python": platform.python_version(), "duckdb": de("duckdb"), "fastapi": de("fastapi"), "uvicorn": de("uvicorn")}


def leer_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, add_help=False)
    parser.add_argument("-h", "--help", "--ayuda", action="help", help="muestra esta ayuda y sale")
    parser.add_argument("--modo", choices=["local", "gcp"], default="local")
    parser.add_argument("--puerto", type=int, default=PUERTO, help=f"puerto de la API propia (por defecto {PUERTO})")
    parser.add_argument("--repeticiones", type=int, default=20, help="aperturas en caliente por sección (por defecto 20)")
    parser.add_argument("--usuarios", type=int, default=10, help="usuarios simultáneos (por defecto 10)")
    parser.add_argument("--rondas", type=int, default=5, help="rondas de la prueba de concurrencia (por defecto 5)")
    parser.add_argument("--db", type=Path, default=RAIZ / "data" / "dq_completo.duckdb", help="base que se copia (modo local)")
    parser.add_argument("--proyecto", default=os.environ.get("DQC_PROYECTO", PROYECTO_POR_DEFECTO), help="proyecto de GCP (modo gcp)")
    parser.add_argument("--salida", type=Path, help="archivo de evidencia (por defecto docs/evidencias/rendimiento[-bigquery].txt)")
    parser.add_argument("--carpeta-temporal", type=Path, help="dónde crear la carpeta temporal (por defecto, la del sistema)")
    parser.add_argument("--caducidad", action="store_true",
                        help="además, espera 10 min a que venza la caché de las vistas y mide el Resumen con todos los usuarios a la vez")
    parser.add_argument("--solo-estimar", action="store_true", help="modo gcp: solo estima la lectura en BigQuery (metadatos) y sale")
    args = parser.parse_args()
    if args.solo_estimar and args.modo != "gcp":
        parser.error("--solo-estimar es del modo gcp")
    if min(args.repeticiones, args.usuarios, args.rondas) < 1:
        parser.error("repeticiones, usuarios y rondas deben ser al menos 1")
    if args.salida is None:
        args.salida = RAIZ / "docs" / "evidencias" / ("rendimiento.txt" if args.modo == "local" else "rendimiento-bigquery.txt")
    return args


def main() -> int:
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    args = leer_argumentos()

    estimacion = None
    if args.modo == "gcp":
        estimacion, pasa = estimar_bytes_bigquery(args.proyecto, lecturas_previstas(args.usuarios, args.caducidad))
        print(estimacion, flush=True)
        if pasa:
            print("\nABORTADO: la lectura prevista pasa de 1 GB. No se midió nada.", file=sys.stderr)
            return 2
        if args.solo_estimar:
            return 0

    if args.carpeta_temporal:
        args.carpeta_temporal.mkdir(parents=True, exist_ok=True)
    carpeta = Path(tempfile.mkdtemp(prefix="dqc-rendimiento-", dir=args.carpeta_temporal))
    admin: AdminTemporal | None = None
    try:
        if args.modo == "local":
            base, email, clave = copiar_base(args.db, carpeta), ADMIN_DEMO, CLAVE_DEMO
            origen = f"copia temporal de {args.db.relative_to(RAIZ) if args.db.is_relative_to(RAIZ) else args.db} ({args.db.stat().st_size / 1e6:.0f} MB), configuración nueva, DQC_EN_VIVO=0, cuentas de demostración"
        else:
            admin = AdminTemporal(args.proyecto)
            admin.crear()
            base, email, clave = None, admin.email, admin.clave
            origen = f"BigQuery y Firestore del proyecto {args.proyecto} (sandbox), DQC_DEMO=0, administrador temporal"
        medicion = medir(args, carpeta, base, email, clave)
    finally:
        # La API ya se apagó (ApiPropia); recién ahora se borra lo que se creó.
        if admin is not None:
            try:
                print("Limpieza: " + admin.borrar(), flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"ATENCIÓN: {e}", file=sys.stderr)
        borrar_carpeta(carpeta)

    meta = Meta(
        modo=args.modo, fecha=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), versiones=versiones(),
        maquina=f"{platform.platform()} · {os.cpu_count()} CPU lógicas", base=origen, puerto=args.puerto, estimacion=estimacion,
    )
    texto, cumplen = informe(medicion, meta)
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(texto, encoding="utf-8", newline="\n")
    print(f"\nEvidencia en {args.salida}\n{texto.splitlines()[-1]}")
    # La caché vencida cuenta: HU-15 pide menos de 8 s en cualquier momento, también justo al vencer.
    return 0 if cumplen == len(SECCIONES) and caducidad_cumple(medicion.caducidad) is not False else 1


if __name__ == "__main__":
    sys.exit(main())
