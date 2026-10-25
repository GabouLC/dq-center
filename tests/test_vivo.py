"""Simulación en vivo: el día siguiente llega archivo por archivo y se publica al completarse."""

import threading

from dqc.api.configuracion import ConfiguracionLocal
from dqc.api.vivo import Simulador
from dqc.modelo import BUSINESS
from dqc.pipeline.flujo import Flujo
from dqc.pipeline.ingesta import leer_entregas
from dqc.plataforma.local import PlataformaDuckDB

from conftest import CONFIG, CORTES_PRUEBA


def test_el_dia_siguiente_llega_archivo_por_archivo(datos, fuentes, contratos, reglas, tmp_path):
    plataforma = PlataformaDuckDB()
    flujo = Flujo(plataforma, fuentes, contratos, reglas, datos.landing)
    flujo.preparar()
    primero = CORTES_PRUEBA[0]
    flujo.procesar_corte(primero, leer_entregas(datos.landing), primero=True)

    publicados = []
    simulador = Simulador(plataforma, ConfiguracionLocal(tmp_path / "config.json", CONFIG), fuentes, datos.landing,
                          intervalo=60, candado=threading.RLock(), al_cerrar_corte=lambda: publicados.append(1))
    assert simulador.preparar()
    siguiente = simulador._pendientes[0].fecha_corte
    archivos = [e for e in simulador._pendientes if e.fecha_corte == siguiente]
    assert len(archivos) == 5 and simulador.estado()["dias_pendientes"] == 91

    for _ in archivos[:-1]:
        simulador._llega_un_archivo()
    estado = simulador.estado()
    assert (estado["corte_en_curso"], estado["archivos_recibidos"], estado["version"]) == (siguiente, 4, 0)
    assert publicados == []  # el corte no se evalúa hasta que llegan todos sus archivos

    simulador._llega_un_archivo()
    estado = simulador.estado()
    assert (estado["ultimo_corte"], estado["corte_en_curso"], estado["version"]) == (siguiente, None, 1)
    assert publicados == [1]
    titulos = [e["titulo"] for e in estado["eventos"]]
    assert sum(t.startswith("Llegó ") for t in titulos) == 5
    assert any(t.startswith("Motor de calidad") for t in titulos)
    assert any("certificado y publicado" in t for t in titulos)
    evaluados = plataforma.consultar(f"SELECT DISTINCT fecha_corte FROM {BUSINESS}.v_calidad_ejecuciones ORDER BY 1")
    assert [f["fecha_corte"] for f in evaluados] == [primero, siguiente]
    assert simulador.estado(desde=estado["eventos"][-1]["id"])["eventos"] == []


def test_un_archivo_que_llega_tarde_no_se_pierde(datos, fuentes, contratos, reglas, tmp_path):
    """Si un archivo de un día llega después de los del día siguiente, el día se cierra completo y en orden."""
    plataforma = PlataformaDuckDB()
    flujo = Flujo(plataforma, fuentes, contratos, reglas, datos.landing)
    flujo.preparar()
    flujo.procesar_corte(CORTES_PRUEBA[0], leer_entregas(datos.landing), primero=True)
    simulador = Simulador(plataforma, ConfiguracionLocal(tmp_path / "config.json", CONFIG), fuentes, datos.landing,
                          intervalo=60, candado=threading.RLock(), al_cerrar_corte=lambda: None)
    assert simulador.preparar()
    dia1, dia2 = sorted({e.fecha_corte for e in simulador._pendientes})[:2]
    del_dia1 = [e for e in simulador._pendientes if e.fecha_corte == dia1]
    del_dia2 = [e for e in simulador._pendientes if e.fecha_corte == dia2]
    simulador._pendientes = del_dia1[:-1] + del_dia2 + del_dia1[-1:]  # el último del día 1 llega al final

    for _ in range(len(simulador._pendientes)):
        simulador._llega_un_archivo()
    evaluados = plataforma.consultar(f"SELECT fecha_corte FROM {BUSINESS}.v_calidad_ejecuciones ORDER BY iniciada_en")
    assert [f["fecha_corte"] for f in evaluados] == [CORTES_PRUEBA[0], dia1, dia2]
    for tabla in ("persona", "poliza", "vehiculo", "siniestro", "pago"):
        filas = plataforma.consultar(f"SELECT COUNT(*) AS n FROM dq_master.{tabla} WHERE fecha_corte = DATE '{dia1}'")
        assert filas[0]["n"] > 0, tabla
