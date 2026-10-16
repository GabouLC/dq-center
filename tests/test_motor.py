"""Motor de calidad sobre MASTER (HU-02, HU-03): estados, niveles, muestras y tendencia."""

import json
from datetime import timedelta
import re

from dqc.datagen import generador as g
from dqc.modelo import CORTES, NIVEL_POR_DIMENSION
from dqc.motor.puntuacion import scores
from dqc.motor.reglas import expandir

from conftest import CORTES_PRUEBA


def test_catalogo_tiene_36_reglas_y_48_expandidas(reglas):
    assert len(reglas) == 36
    assert len(expandir(reglas)) == 48


def test_cada_corte_evalua_las_48_reglas_con_su_nivel(ejecuciones):
    for e in ejecuciones.values():
        assert len(e.resultados) == 48
        assert all(r.nivel == NIVEL_POR_DIMENSION[r.dimension] for r in e.resultados)


def test_hay_reglas_en_ok_alerta_y_falla(ejecuciones):
    estados = {r.estado for e in ejecuciones.values() for r in e.resultados}
    assert {"OK", "ALERTA", "FALLA"} <= estados


def test_variacion_de_volumen_sin_corte_anterior_es_sin_datos(ejecuciones):
    primeras = [r for r in ejecuciones[CORTES[0]].resultados if r.tipo == "variacion_volumen"]
    assert {r.estado for r in primeras} == {"SIN_DATOS"}


def test_muestras_traen_la_fila_sin_exponer_pii(ejecuciones):
    r = next(r for r in ejecuciones[CORTES_PRUEBA[0]].resultados if r.id_regla == "PER-VAL-05")
    assert set(r.muestra) == set(r.fallidos[:20])
    fila = json.loads(r.muestra[r.fallidos[0]])
    assert str(fila["id_persona"]) == r.fallidos[0]
    # La muestra se lee de MASTER: el correo va cifrado. Los bytes cifrados pueden traer
    # un 0x40 ("@") al azar, así que se exige que no tenga forma de correo, no que falte la arroba.
    assert not re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", str(fila["email"]))


def test_estructura_detecta_canal_venta_el_9_de_septiembre(ejecuciones):
    antes = {c for c, _ in ejecuciones[g.CANAL_VENTA - timedelta(days=1)].esquemas["poliza"]}
    despues = {c for c, _ in ejecuciones[g.CANAL_VENTA].esquemas["poliza"]}
    assert despues - antes == {"canal_venta"}


def test_los_incidentes_bajan_el_score_del_dia(ejecuciones):
    globales = {c: scores(e.resultados).global_ for c, e in ejecuciones.items()}
    for incidente in (g.PERSONA_TARDE, g.REPROCESO):
        assert globales[incidente] < globales[incidente - timedelta(days=1)] - 1, incidente


def test_las_tendencias_del_periodo(ejecuciones):
    def cumplimiento(corte, regla):
        return next(r.cumplimiento for r in ejecuciones[corte].resultados if r.id_regla == regla)

    primero, ultimo = CORTES_PRUEBA[0], CORTES_PRUEBA[-1]
    assert cumplimiento(ultimo, "PER-VAL-03") > cumplimiento(primero, "PER-VAL-03") + 3  # campaña de contactos
    assert cumplimiento(ultimo, "PAG-CON-02") > cumplimiento(primero, "PAG-CON-02") + 3  # campaña de cobranza
    assert cumplimiento(ultimo, "POL-CON-03") < cumplimiento(primero, "POL-CON-03") - 2  # atraso de bajas
