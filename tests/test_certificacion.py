"""Sprint 2: reglas N2 (HU-03), certificación (HU-04), Quality & Privacy Gate (HU-07) y BUSINESS (HU-08)."""

from datetime import date

from dqc.datagen.generador import AGOSTO, JULIO, JUNIO, SEPTIEMBRE
from dqc.modelo import BUSINESS, CON_OBSERVACIONES, CORTES, NO_CERTIFICADO, TABLAS_CORTE
from dqc.motor.certificacion import certificar
from dqc.motor.puntuacion import ResultadoRegla
from dqc.pipeline.configuracion import cifrados
from dqc.pipeline.publicacion import vistas_contrato

NO_CERTIFICADAS = {("siniestro", JUNIO), ("persona", JULIO), ("poliza", AGOSTO)}


def _cert(simulacion, tabla, corte):
    return next(c for c in simulacion.resultados[corte].certificaciones if c.tabla == tabla)


def test_matriz_de_certificacion(simulacion):
    for corte in CORTES:
        for tabla in TABLAS_CORTE:
            esperado = NO_CERTIFICADO if (tabla, corte) in NO_CERTIFICADAS else CON_OBSERVACIONES
            assert _cert(simulacion, tabla, corte).estado == esperado, (tabla, corte)


def test_la_certificacion_dice_que_reglas_la_bloquean(simulacion):
    assert _cert(simulacion, "persona", JULIO).reglas_bloqueantes == ["GEN-OPO-01"]
    assert _cert(simulacion, "poliza", AGOSTO).reglas_bloqueantes == ["GEN-VOL-01"]
    assert "PER-VAL-01" in _cert(simulacion, "persona", JULIO).reglas_con_observacion


def test_una_fuga_de_pii_bloquea_aunque_la_calidad_este_bien(simulacion):
    c = _cert(simulacion, "siniestro", JUNIO)
    assert c.calidad_ok and not c.privacidad_ok
    assert {(h.tipo, h.columna) for h in c.hallazgos if h.bloqueante} == {("PII_EN_CLARO", "causa")}


def test_columna_nueva_sin_clasificar_es_observacion(simulacion):
    c = _cert(simulacion, "poliza", SEPTIEMBRE)
    assert c.certificado
    assert [(h.tipo, h.columna, h.bloqueante) for h in c.hallazgos] == [("COLUMNA_SIN_CLASIFICAR", "canal_venta", False)]


def test_cada_certificacion_lleva_su_sello(simulacion):
    ids = {r.ejecucion.id_ejecucion for r in simulacion.resultados.values()}
    filas = [
        f for f in simulacion.plataforma.consultar(f"SELECT * FROM {BUSINESS}.v_calidad_certificaciones")
        if f["id_ejecucion"] in ids  # otras pruebas pueden lanzar corridas manuales
    ]
    assert len(filas) == len(CORTES) * len(TABLAS_CORTE)
    for f in filas:
        assert f["id_ejecucion"] and f["version_motor"] and len(f["version_reglas"]) == 10
        assert f["publicado"] == (f["estado"] != NO_CERTIFICADO)


def test_una_media_en_falla_no_bloquea():
    resultados = [
        ResultadoRegla("PER-VAL-03", "persona", "validez", "MEDIA", "regex", 97, date(2026, 4, 30), 100, 50, []),
        ResultadoRegla("PER-UNI-01", "persona", "unicidad", "CRITICA", "unico", 100, date(2026, 4, 30), 100, 100, []),
    ]
    ejecucion = type("E", (), {"resultados": resultados, "fecha_corte": date(2026, 4, 30)})
    persona = next(c for c in certificar(ejecucion, [], "x") if c.tabla == "persona")
    assert persona.estado == CON_OBSERVACIONES
    assert persona.reglas_con_observacion == ["PER-VAL-03"]


# ── HU-03: reglas asociadas a dominios ──────────────────────────────────────


def test_los_resultados_se_asocian_a_los_dominios_poliza_y_persona(ejecuciones):
    dominios = {(r.tabla, r.dominio) for r in ejecuciones[JUNIO].resultados}
    assert ("persona", "Persona") in dominios
    assert {d for t, d in dominios if t != "persona"} == {"Póliza"}


# ── HU-08: publicación en BUSINESS ──────────────────────────────────────────


def test_business_solo_tiene_cortes_certificados(simulacion):
    for tabla in TABLAS_CORTE:
        publicados = {
            f["fecha_corte"]
            for f in simulacion.plataforma.consultar(f"SELECT DISTINCT fecha_corte FROM {BUSINESS}.p_{tabla}")
        }
        assert publicados == {c for c in CORTES if (tabla, c) not in NO_CERTIFICADAS}, tabla


def test_la_vista_de_cada_tabla_muestra_su_ultimo_corte_certificado(simulacion):
    for tabla in TABLAS_CORTE:
        cortes = simulacion.plataforma.consultar(f"SELECT DISTINCT fecha_corte FROM {BUSINESS}.v_{tabla}")
        assert [f["fecha_corte"] for f in cortes] == [SEPTIEMBRE], tabla


def test_business_no_expone_pii_en_claro(simulacion, contratos):
    for tabla, campos in cifrados(contratos).items():
        tipos = dict(simulacion.plataforma.columnas(f"p_{tabla}", BUSINESS))
        assert all(tipos[c] == "BYTES" for c in campos), tabla


def test_las_vistas_de_contrato_responden(simulacion):
    for nombre in vistas_contrato():
        filas = simulacion.plataforma.consultar(f"SELECT COUNT(*) AS n FROM {BUSINESS}.{nombre}")
        assert filas[0]["n"] > 0, nombre
