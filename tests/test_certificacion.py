"""Sprint 2: reglas N2 (HU-03), certificación (HU-04), Quality & Privacy Gate (HU-07) y BUSINESS (HU-08)."""

from datetime import date

from dqc.datagen import generador as g
from dqc.modelo import BUSINESS, CERTIFICADO, CON_OBSERVACIONES, CORTES, NO_CERTIFICADO, TABLAS_CORTE
from dqc.motor.certificacion import certificar
from dqc.motor.puntuacion import ResultadoRegla
from dqc.pipeline.configuracion import cifrados
from dqc.pipeline.publicacion import vistas_contrato

from conftest import CORTES_PRUEBA

# Cada incidente deja su tabla sin certificar ese día.
INCIDENTES = {
    ("persona", g.PERSONA_TARDE), ("persona", g.DOCUMENTO_NULO), ("poliza", g.REPROCESO),
    *(("siniestro", d) for d in g.FUGA_PII),
}
# El atraso de bajas lleva POL-CON-03 debajo de su umbral a fines de septiembre.
ORGANICAS = {("poliza", d) for d in CORTES_PRUEBA if d >= date(2026, 9, 26)}


def _cert(simulacion, tabla, corte):
    return next(c for c in simulacion.resultados[corte].certificaciones if c.tabla == tabla)


def _no_certificadas(simulacion) -> set:
    return {(c.tabla, corte) for corte, r in simulacion.resultados.items() for c in r.certificaciones if not c.certificado}


def test_matriz_de_certificacion(simulacion):
    assert _no_certificadas(simulacion) == INCIDENTES | ORGANICAS


def test_vehiculo_certifica_sin_observaciones_despues_de_la_limpieza(simulacion):
    for corte in CORTES_PRUEBA:
        if corte >= g.LIMPIEZA_VEHICULOS[1]:
            assert _cert(simulacion, "vehiculo", corte).estado == CERTIFICADO, corte
    assert _cert(simulacion, "vehiculo", CORTES_PRUEBA[0]).estado == CON_OBSERVACIONES


def test_la_certificacion_dice_que_reglas_la_bloquean(simulacion):
    assert _cert(simulacion, "persona", g.PERSONA_TARDE).reglas_bloqueantes == ["GEN-OPO-01"]
    assert "PER-COM-01" in _cert(simulacion, "persona", g.DOCUMENTO_NULO).reglas_bloqueantes
    assert _cert(simulacion, "poliza", g.REPROCESO).reglas_bloqueantes == ["GEN-VOL-01"]
    assert _cert(simulacion, "poliza", CORTES_PRUEBA[-1]).reglas_bloqueantes == ["POL-CON-03"]
    assert "PER-VAL-01" in _cert(simulacion, "persona", g.PERSONA_TARDE).reglas_con_observacion


def test_una_fuga_de_pii_bloquea_aunque_la_calidad_este_bien(simulacion):
    for dia, registros in g.FUGA_PII.items():
        c = _cert(simulacion, "siniestro", dia)
        assert c.calidad_ok and not c.privacidad_ok
        assert {(h.tipo, h.columna) for h in c.hallazgos if h.bloqueante} == {("PII_EN_CLARO", "causa")}
        assert len(c.hallazgos) == registros


def test_columna_nueva_sin_clasificar_es_observacion(simulacion):
    c = _cert(simulacion, "poliza", g.CANAL_VENTA)
    assert c.certificado
    assert [(h.tipo, h.columna, h.bloqueante) for h in c.hallazgos] == [("COLUMNA_SIN_CLASIFICAR", "canal_venta", False)]


def test_cada_certificacion_lleva_su_sello(simulacion):
    ids = {r.ejecucion.id_ejecucion for r in simulacion.resultados.values()}
    filas = [
        f for f in simulacion.plataforma.consultar(f"SELECT * FROM {BUSINESS}.v_calidad_certificaciones")
        if f["id_ejecucion"] in ids  # otras pruebas pueden lanzar corridas manuales
    ]
    assert len(filas) == len(CORTES_PRUEBA) * len(TABLAS_CORTE)
    for f in filas:
        assert f["id_ejecucion"] and f["version_motor"] and len(f["version_reglas"]) == 10
        assert f["publicado"] == (f["estado"] != NO_CERTIFICADO)


def test_una_media_en_falla_no_bloquea():
    resultados = [
        ResultadoRegla("PER-VAL-03", "persona", "validez", "MEDIA", "regex", 97, CORTES[0], 100, 50, []),
        ResultadoRegla("PER-UNI-01", "persona", "unicidad", "CRITICA", "unico", 100, CORTES[0], 100, 100, []),
    ]
    ejecucion = type("E", (), {"resultados": resultados, "fecha_corte": CORTES[0]})
    persona = next(c for c in certificar(ejecucion, [], "x") if c.tabla == "persona")
    assert persona.estado == CON_OBSERVACIONES
    assert persona.reglas_con_observacion == ["PER-VAL-03"]


# ── HU-03: reglas asociadas a dominios ──────────────────────────────────────


def test_los_resultados_se_asocian_a_los_dominios_poliza_y_persona(ejecuciones):
    dominios = {(r.tabla, r.dominio) for r in ejecuciones[CORTES_PRUEBA[0]].resultados}
    assert ("persona", "Persona") in dominios
    assert {d for t, d in dominios if t != "persona"} == {"Póliza"}


# ── HU-08: publicación en BUSINESS ──────────────────────────────────────────


def test_business_solo_tiene_cortes_certificados(simulacion):
    for tabla in TABLAS_CORTE:
        publicados = {
            f["fecha_corte"]
            for f in simulacion.plataforma.consultar(f"SELECT DISTINCT fecha_corte FROM {BUSINESS}.p_{tabla}")
        }
        assert publicados == {c for c in CORTES_PRUEBA if (tabla, c) not in _no_certificadas(simulacion)}, tabla


def test_la_vista_de_cada_tabla_muestra_su_ultimo_corte_certificado(simulacion):
    for tabla in TABLAS_CORTE:
        cortes = simulacion.plataforma.consultar(f"SELECT DISTINCT fecha_corte FROM {BUSINESS}.v_{tabla}")
        ultimo = max(c for c in CORTES_PRUEBA if (tabla, c) not in _no_certificadas(simulacion))
        assert [f["fecha_corte"] for f in cortes] == [ultimo], tabla


def test_business_no_expone_pii_en_claro(simulacion, contratos):
    for tabla, campos in cifrados(contratos).items():
        tipos = dict(simulacion.plataforma.columnas(f"p_{tabla}", BUSINESS))
        assert all(tipos[c] == "BYTES" for c in campos), tabla


def test_las_vistas_de_contrato_responden(simulacion):
    for nombre in vistas_contrato():
        filas = simulacion.plataforma.consultar(f"SELECT COUNT(*) AS n FROM {BUSINESS}.{nombre}")
        assert filas[0]["n"] > 0, nombre
