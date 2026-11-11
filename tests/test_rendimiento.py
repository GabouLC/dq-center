"""Parte pura de scripts/medir_rendimiento.py (HU-15): percentiles, veredicto, plan de peticiones e informe.

No arranca la API ni toca la red: todo se calcula con datos inventados.
"""

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

from dqc.api.app import LIMITE_SEGUNDOS, MODULOS

RAIZ = Path(__file__).parents[1]


@pytest.fixture(scope="module")
def mr():
    spec = importlib.util.spec_from_file_location("medir_rendimiento", RAIZ / "scripts" / "medir_rendimiento.py")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo  # los dataclass del script lo necesitan registrado
    spec.loader.exec_module(modulo)
    yield modulo
    sys.modules.pop(spec.name, None)


# ── percentiles ─────────────────────────────────────────────────────────────


def test_percentiles_con_datos_inventados(mr):
    assert mr.percentil([5, 1, 3, 2, 4], 50) == 3  # sin importar el orden de entrada
    assert mr.percentil([10, 20, 30, 40], 50) == 25  # entre los dos del medio
    assert mr.percentil(list(range(1, 101)), 95) == pytest.approx(95.05)
    assert mr.percentil([7, 9, 11], 0) == 7 and mr.percentil([7, 9, 11], 100) == 11
    assert mr.percentil([42], 95) == 42


def test_percentil_rechaza_lo_que_no_tiene_sentido(mr):
    with pytest.raises(ValueError):
        mr.percentil([], 50)
    with pytest.raises(ValueError):
        mr.percentil([1, 2], 101)


def test_estadisticas_de_una_seccion(mr):
    e = mr.estadisticas([float(i) for i in range(1, 21)])  # 20 repeticiones: 1..20 ms
    assert e == {"n": 20, "p50": pytest.approx(10.5), "p95": pytest.approx(19.05), "max": 20.0}
    assert mr.estadisticas([]) == {"n": 0, "p50": None, "p95": None, "max": None}


# ── veredicto contra el límite de 8 s ───────────────────────────────────────


def test_el_limite_es_el_de_la_api(mr):
    assert mr.LIMITE_MS == LIMITE_SEGUNDOS * 1000


def test_veredicto_cumple_si_frio_y_carga_estan_bajo_el_limite(mr):
    assert mr.veredicto([12.0, 95.0], [30.0, 410.0], errores=0) == (True, "CUMPLE")
    # «menos de 8 s»: justo en el límite ya no cumple
    assert mr.veredicto([7999.9], [100.0], 0)[0] is True
    assert mr.veredicto([8000.0], [100.0], 0) == (False, "NO CUMPLE (frío)")


def test_veredicto_dice_por_que_no_cumple(mr):
    assert mr.veredicto([100.0], [9000.0], 0) == (False, "NO CUMPLE (carga)")
    assert mr.veredicto([8500.0], [9000.0], 0) == (False, "NO CUMPLE (frío, carga)")
    assert mr.veredicto([100.0], [200.0], 3) == (False, "NO CUMPLE (3 errores)")  # rápido pero con errores
    assert mr.veredicto([], [200.0], 0) == (False, "NO CUMPLE (frío)")  # sin dato no se da por cumplido
    assert mr.veredicto([100.0], [], 0) == (False, "NO CUMPLE (carga)")


# ── Server-Timing, plan de peticiones y datos de la cabecera ────────────────


def test_server_timing(mr):
    assert mr.ms_de_server_timing("app;dur=123") == 123.0
    assert mr.ms_de_server_timing("db;dur=5.5, app;dur=40") == 40.0
    assert mr.ms_de_server_timing("cache;desc=hit") is None
    assert mr.ms_de_server_timing(None) is None


def test_las_rutas_se_arman_con_los_ultimos_cortes(mr):
    cortes = ["2026-07-03", "2026-07-01", "2026-07-02"]  # desordenadas a propósito
    assert mr.resolver("/api/v1/certificacion?corte={ultimo}", cortes) == "/api/v1/certificacion?corte=2026-07-03"
    assert mr.resolver("/api/v1/validaciones/comparar?a={penultimo}&b={ultimo}", cortes) == (
        "/api/v1/validaciones/comparar?a=2026-07-02&b=2026-07-03"
    )
    assert mr.resolver("/api/v1/resumen", []) == "/api/v1/resumen"  # lo fijo no depende de /cortes
    # con un solo corte no hay con qué comparar; sin cortes no hay corte elegido
    assert mr.resolver("/api/v1/validaciones/comparar?a={penultimo}&b={ultimo}", ["2026-07-01"]) is None
    assert mr.resolver("/api/v1/certificacion?corte={ultimo}", []) is None


def test_fechas_y_datos_de_la_cabecera_del_informe(mr):
    cortes = json.dumps([{"fecha_corte": "2026-07-02"}, {"fecha_corte": "2026-07-01"}]).encode()
    assert mr.fechas_de_cortes(cortes) == ["2026-07-01", "2026-07-02"]
    assert mr.fechas_de_cortes(b"no es json") == [] and mr.fechas_de_cortes(None) == []
    fuentes = json.dumps([
        {"tabla": "persona", "cargas": [{"estado": "EXITOSA", "filas": 100}, {"estado": "RECHAZADA", "filas": 7}]},
        {"tabla": "poliza", "cargas": [{"estado": "EXITOSA", "filas": 50}]},
    ]).encode()
    assert mr.datos_cargados(cortes, fuentes) == (2, 150)  # las rechazadas no cuentan
    assert mr.datos_cargados(None, b"{}") == (None, None)


def test_el_plan_tiene_las_11_secciones_en_el_orden_del_menu(mr):
    assert list(mr.SECCIONES) == [clave for clave, _, _ in MODULOS]


def test_cada_ruta_del_plan_existe_en_la_api(mr):
    app = (RAIZ / "src" / "dqc" / "api" / "app.py").read_text(encoding="utf-8")
    rutas = [re.compile("^" + re.sub(r"\{[^/]+\}", "[^/]+", r) + "$") for r in re.findall(r'@app\.get\("([^"]+)"', app)]
    plan = {p.split("?")[0] for etapas in mr.SECCIONES.values() for etapa in etapas for p in etapa}
    assert not [p for p in plan if not any(r.match(p) for r in rutas)]


# ── estimación en BigQuery ──────────────────────────────────────────────────


def test_estimacion_de_lectura_y_tope(mr):
    tamanos = {"dq_engine.resultados": 4_000_000, "dq_engine.fallidos": 30_000_000, "dq_raw.registro_cargas": 1_000_000}
    leidas = ["dq_engine.resultados", "dq_raw.registro_cargas"]  # fallidos no se lee al precargar
    assert mr.estimar_lectura(tamanos, leidas, lecturas=6) == (5_000_000, 30_000_000, False)
    por_lectura, total, pasa = mr.estimar_lectura(tamanos, leidas, lecturas=6, tope=29_999_999)
    assert pasa and total == 30_000_000
    assert mr.estimar_lectura({"a": mr.TOPE_BYTES}, ["a"], 1)[2] is False  # justo el tope no se pasa


# ── informe ─────────────────────────────────────────────────────────────────


def _medicion(mr, lenta: str | None = None):
    """Una medición inventada: todo rápido, salvo que se indique una sección lenta bajo carga."""
    carga = lambda ms: mr.Carga(ms=ms, servidor_ms=ms / 2, peticiones=3, bytes=2048)  # noqa: E731
    secciones = list(mr.SECCIONES)
    return mr.Medicion(
        justo={s: carga(30.0) for s in secciones}, frio={s: carga(20.0) for s in secciones},
        caliente={s: [carga(10.0 + i) for i in range(20)] for s in secciones},
        concurrencia={s: [carga(9000.0 if s == lenta else 80.0 + i) for i in range(50)] for s in secciones},
        inicios_de_sesion=[300.0, 350.0], usuarios=10, rondas=5, repeticiones=20,
        vivo_s=2.0, listo_s=3.0, cortes=92, filas=1_374_037, lentas=0,
    )


def _meta(mr):
    return mr.Meta(
        modo="local", fecha="2026-11-11 00:00 UTC", base="copia de prueba", maquina="prueba",
        versiones={"python": "3.12.10", "duckdb": "1.5.6", "fastapi": "0.1", "uvicorn": "0.1"},
    )


def test_el_informe_cuenta_las_secciones_que_cumplen(mr):
    texto, cumplen = mr.informe(_medicion(mr), _meta(mr))
    assert cumplen == 11
    assert texto.splitlines()[-1] == "Resultado: 11 de 11 secciones por debajo de 8 s en frío y bajo carga"
    assert "92 cortes" in texto and "1374037 filas" in texto

    texto, cumplen = mr.informe(_medicion(mr, lenta="reglas"), _meta(mr))
    assert cumplen == 10
    assert texto.splitlines()[-1] == "Resultado: 10 de 11 secciones por debajo de 8 s en frío y bajo carga"
    assert re.search(r"^reglas .*NO CUMPLE \(carga\)$", texto, re.MULTILINE)


def test_lecturas_previstas_crecen_con_la_caducidad(mr):
    assert mr.lecturas_previstas(usuarios=10, caducidad=False) == 6
    assert mr.lecturas_previstas(usuarios=10, caducidad=True) == 26  # 2 peticiones del Resumen leen las vistas, por usuario


def test_el_informe_incluye_la_cache_vencida_cuando_se_midio(mr):
    medicion = _medicion(mr)
    medicion.caducidad = [mr.Carga(ms=1500.0 + 100 * i, servidor_ms=1400.0, peticiones=6) for i in range(10)]
    texto, cumplen = mr.informe(medicion, _meta(mr))
    linea = next(x for x in texto.splitlines() if x.startswith("Caché vencida"))
    assert "10 usuarios" in linea and "mejor 1500 ms" in linea and "peor 2400 ms" in linea and linea.endswith("CUMPLE el límite de 8 s")
    assert cumplen == 11  # la caché vencida se informa aparte: no cambia el resultado por sección

    medicion.caducidad[-1] = mr.Carga(ms=8100.0, servidor_ms=8000.0, peticiones=6)
    assert next(x for x in mr.informe(medicion, _meta(mr))[0].splitlines() if x.startswith("Caché vencida")).endswith("NO CUMPLE el límite de 8 s")
