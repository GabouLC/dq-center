from datetime import datetime, time, timedelta

from dqc.datagen.generador import AGOSTO, JULIO, SEPTIEMBRE, ZONA_LIMA, generar
from dqc.modelo import CORTES, LLAVES, TABLAS_CORTE


def test_es_determinista(resultado):
    otro = generar()
    assert otro.manifiesto == resultado.manifiesto
    assert otro.por_corte["persona"][JULIO] == resultado.por_corte["persona"][JULIO]


def test_registro_cargas_cuadra_con_las_filas(resultado):
    for r in resultado.registro_cargas:
        assert r["filas"] == len(resultado.por_corte[r["tabla"]][r["fecha_corte"]])


def test_solo_poliza_de_agosto_varia_mas_de_15_por_ciento(resultado):
    filas = {(r["tabla"], r["fecha_corte"]): r["filas"] for r in resultado.registro_cargas}
    fuera_de_rango = {
        (tabla, actual)
        for tabla in TABLAS_CORTE
        for anterior, actual in zip(CORTES, CORTES[1:])
        if abs(filas[tabla, actual] / filas[tabla, anterior] - 1) > 0.15
    }
    assert fuera_de_rango == {("poliza", AGOSTO)}


def test_solo_persona_de_julio_llega_tarde(resultado):
    tardias = {
        (r["tabla"], r["fecha_corte"])
        for r in resultado.registro_cargas
        if r["cargado_en"] > datetime.combine(r["fecha_corte"] + timedelta(days=2), time(9), ZONA_LIMA)
    }
    assert tardias == {("persona", JULIO)}


def test_las_llaves_del_manifiesto_existen_en_su_corte(resultado):
    llaves = {
        (tabla, corte): {str(f[LLAVES[tabla]]) for f in filas}
        for tabla in TABLAS_CORTE
        for corte, filas in resultado.por_corte[tabla].items()
    }
    for m in resultado.manifiesto:
        if m["llave"] == m["tabla"]:  # regla de tabla completa
            continue
        assert m["llave"] in llaves[m["tabla"], m["fecha_corte"]], m


def test_canal_venta_aparece_recien_en_septiembre(resultado):
    for corte, filas in resultado.por_corte["poliza"].items():
        assert ("canal_venta" in filas[0]) == (corte >= SEPTIEMBRE)


def test_dni_de_7_digitos_se_corrigen_en_septiembre(resultado):
    por_corte = {}
    for m in resultado.manifiesto:
        if m["id_regla"] == "PER-VAL-01" and "7 dígitos" in m["descripcion"]:
            por_corte[m["fecha_corte"]] = por_corte.get(m["fecha_corte"], 0) + 1
    assert por_corte.get(SEPTIEMBRE, 0) == 0
    assert all(por_corte[c] > 0 for c in CORTES[:-1])
