"""Datos sintéticos diarios de julio a septiembre: incidentes, tendencias y ruido."""

from collections import Counter
from datetime import date, datetime, time, timedelta

from dqc.datagen import generador as g
from dqc.datagen.generador import ZONA_LIMA, generar
from dqc.modelo import CORTES, LLAVES, TABLAS_CORTE

from conftest import ESCALA


def _errores(resultado, regla: str) -> Counter:
    return Counter(m["fecha_corte"] for m in resultado.manifiesto if m["id_regla"] == regla)


def test_es_determinista(resultado):
    otro = generar(escala=ESCALA)
    assert otro.manifiesto == resultado.manifiesto
    assert otro.por_corte["persona"][g.DOCUMENTO_NULO] == resultado.por_corte["persona"][g.DOCUMENTO_NULO]


def test_un_corte_por_dia_de_julio_a_septiembre():
    assert (CORTES[0], CORTES[-1], len(CORTES)) == (date(2026, 7, 1), date(2026, 9, 30), 92)
    assert all((b - a).days == 1 for a, b in zip(CORTES, CORTES[1:]))


def test_solo_el_reproceso_varia_mas_de_15_por_ciento(resultado):
    fuera_de_rango = {
        (tabla, actual)
        for tabla in TABLAS_CORTE
        for anterior, actual in zip(CORTES, CORTES[1:])
        if abs(len(resultado.por_corte[tabla][actual]) / len(resultado.por_corte[tabla][anterior]) - 1) > 0.15
    }
    assert fuera_de_rango == {("poliza", g.REPROCESO)}


def test_solo_persona_del_14_de_julio_llega_tarde(resultado):
    tardias = {
        (tabla, corte)
        for (tabla, corte), llegada in resultado.llegadas.items()
        if llegada > datetime.combine(corte + timedelta(days=2), time(9), ZONA_LIMA)
    }
    assert tardias == {("persona", g.PERSONA_TARDE)}


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


def test_canal_venta_aparece_desde_el_9_de_septiembre(resultado):
    for corte, filas in resultado.por_corte["poliza"].items():
        assert ("canal_venta" in filas[0]) == (corte >= g.CANAL_VENTA)


def test_los_dni_de_7_digitos_se_corrigen_el_15_de_septiembre(resultado):
    por_corte = Counter(
        m["fecha_corte"] for m in resultado.manifiesto if m["id_regla"] == "PER-VAL-01" and "7 dígitos" in m["descripcion"]
    )
    assert all(por_corte[c] > 0 for c in CORTES if c < g.CORRECCION_DNI)
    assert all(por_corte[c] == 0 for c in CORTES if c >= g.CORRECCION_DNI)


def test_el_fin_de_semana_casi_no_hay_polizas_nuevas(resultado):
    nuevas = Counter(p.desde for p in resultado.entidades["poliza"] if p.origen == "NORMAL" and p.desde >= CORTES[0])
    habiles = [nuevas[c] for c in CORTES if c.weekday() < 5]
    domingos = [nuevas[c] for c in CORTES if c.weekday() == 6]
    assert sum(habiles) / len(habiles) > 4 * sum(domingos) / len(domingos)


def test_los_errores_transitorios_cambian_de_un_dia_a_otro(resultado):
    estados_sucios = _errores(resultado, "POL-VAL-01")
    por_dia = [estados_sucios[c] for c in CORTES]
    assert 0 in por_dia and len(set(por_dia)) >= 3


def test_las_campanas_mejoran_y_el_atraso_de_bajas_empeora(resultado):
    primero, ultimo = CORTES[0], CORTES[-1]
    for regla in ("PER-VAL-03", "PAG-CON-02"):  # campaña de contactos y de cobranza
        assert _errores(resultado, regla)[ultimo] < _errores(resultado, regla)[primero] * 0.8, regla
    assert _errores(resultado, "POL-CON-03")[ultimo] > _errores(resultado, "POL-CON-03")[primero] * 1.5
    assert _errores(resultado, "VEH-VAL-01")[ultimo] < _errores(resultado, "VEH-VAL-01")[primero]
