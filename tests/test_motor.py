"""Prueba de aceptación: el motor detecta exactamente los errores sembrados."""

from pathlib import Path

import pytest

from dqc.datagen.generador import AGOSTO, JULIO, SEPTIEMBRE
from dqc.datagen.salida import escribir_parquet
from dqc.modelo import CORTES
from dqc.motor.backends import BackendDuckDB
from dqc.motor.motor import Motor, comparar_con_manifiesto
from dqc.motor.puntuacion import scores
from dqc.motor.reglas import cargar_yaml, expandir

CATALOGO = Path(__file__).parents[1] / "config" / "reglas_iniciales.yaml"


@pytest.fixture(scope="session")
def datos(resultado, tmp_path_factory):
    salida = tmp_path_factory.mktemp("datos")
    escribir_parquet(resultado, salida)
    return salida


@pytest.fixture(scope="session")
def ejecuciones(datos):
    """Simula la historia: carga corte por corte y corre el motor después de cada carga."""
    backend = BackendDuckDB()
    backend.cargar_referencias(datos)
    motor = Motor(backend, cargar_yaml(CATALOGO))
    historia = []
    for corte in CORTES:
        backend.cargar_corte(datos, corte)
        historia.append(motor.ejecutar(corte, origen="simulacion"))
    return {e.fecha_corte: e for e in historia}


def test_catalogo_tiene_36_reglas_y_48_expandidas():
    reglas = cargar_yaml(CATALOGO)
    assert len(reglas) == 36
    assert len(expandir(reglas)) == 48


def test_motor_detecta_exactamente_el_manifiesto(ejecuciones, resultado):
    faltantes, sobrantes = comparar_con_manifiesto(list(ejecuciones.values()), resultado.manifiesto)
    assert not faltantes, f"{len(faltantes)} sembrados sin detectar, p. ej. {sorted(faltantes)[:5]}"
    assert not sobrantes, f"{len(sobrantes)} fallidos no sembrados, p. ej. {sorted(sobrantes)[:5]}"


def test_cada_corte_evalua_las_48_reglas(ejecuciones):
    for e in ejecuciones.values():
        assert len(e.resultados) == 48


def test_hay_reglas_en_ok_alerta_y_falla(ejecuciones):
    estados = {r.estado for e in ejecuciones.values() for r in e.resultados}
    assert {"OK", "ALERTA", "FALLA"} <= estados


def test_variacion_de_volumen_sin_corte_anterior_es_sin_datos(ejecuciones):
    primeras = [r for r in ejecuciones[CORTES[0]].resultados if r.tipo == "variacion_volumen"]
    assert {r.estado for r in primeras} == {"SIN_DATOS"}


def test_estructura_detecta_canal_venta_en_septiembre(ejecuciones):
    antes = {c for c, _ in ejecuciones[AGOSTO].esquemas["poliza"]}
    despues = {c for c, _ in ejecuciones[SEPTIEMBRE].esquemas["poliza"]}
    assert despues - antes == {"canal_venta"}


def test_resumen_cae_en_julio_agosto_y_se_recupera_en_septiembre(ejecuciones):
    globales = {c: scores(e.resultados).global_ for c, e in ejecuciones.items()}
    junio = CORTES[2]
    assert globales[JULIO] < globales[junio]
    assert globales[AGOSTO] < globales[junio]
    assert globales[SEPTIEMBRE] > globales[AGOSTO]
    assert globales[SEPTIEMBRE] > globales[JULIO]
