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
