"""Flujo RAW -> MASTER (HU-01, HU-05, HU-06, HU-14) y prueba de aceptación contra el manifiesto."""

import csv

import pytest

from dqc.datagen.generador import RECHAZO_SINIESTRO
from dqc.modelo import BUSINESS, CORTES, ENGINE, ESQUEMAS, MASTER, RAW, TABLAS_CORTE
from dqc.pipeline.configuracion import cifrados, clasificacion
from dqc.pipeline.flujo import Flujo, cortes_por_procesar
from dqc.pipeline.funciones import SQL_LLAVES
from dqc.pipeline.ingesta import RECHAZADA, leer_entregas
from dqc.pipeline.verificacion import verificar
from dqc.plataforma.local import PlataformaDuckDB

from conftest import CORTES_PRUEBA

PRIMERO = CORTES_PRUEBA[0]


def test_cada_etapa_detecta_exactamente_lo_sembrado(simulacion, datos):
    resultado = verificar(list(simulacion.resultados.values()), datos.manifiesto)
    for etapa, (faltantes, sobrantes) in resultado.items():
        assert not faltantes, f"{etapa}: {len(faltantes)} sin detectar, p. ej. {sorted(faltantes)[:5]}"
        assert not sobrantes, f"{etapa}: {len(sobrantes)} de más, p. ej. {sorted(sobrantes)[:5]}"


# ── HU-01: ingesta ──────────────────────────────────────────────────────────


def test_archivo_mal_formado_se_rechaza_con_su_motivo(simulacion):
    rechazos = [c for c in simulacion.resultados[RECHAZO_SINIESTRO].cargas if c.estado == RECHAZADA]
    assert [(c.entrega.nombre, c.detalle) for c in rechazos] == [
        ("siniestros_20260728_01.csv", "faltan columnas: ESTADO_SINIESTRO")
    ]


def test_lo_rechazado_no_llega_a_raw_y_queda_registrado(simulacion):
    p = simulacion.plataforma
    archivos = p.consultar(f"SELECT DISTINCT archivo FROM {RAW}.siniestros WHERE fecha_corte = DATE '{RECHAZO_SINIESTRO}'")
    assert [a["archivo"] for a in archivos] == ["siniestros_20260728_02.csv"]
    estados = p.consultar(
        f"SELECT archivo, estado FROM {RAW}.registro_cargas WHERE tabla = 'siniestro' AND fecha_corte = DATE '{RECHAZO_SINIESTRO}' "
        "ORDER BY cargado_en"
    )
    assert [e["estado"] for e in estados] == ["RECHAZADA", "EXITOSA"]


def test_raw_conserva_los_valores_tal_cual_vienen(simulacion, datos):
    with open(datos.landing / PRIMERO.isoformat() / f"polizas_{PRIMERO:%Y%m%d}_01.csv", encoding="utf-8") as f:
        en_csv = {fila["ID_POLIZA"]: fila["ESTADO_POLIZA"] for fila in csv.DictReader(f)}
    en_raw = {
        f["ID_POLIZA"]: f["ESTADO_POLIZA"]
        for f in simulacion.plataforma.consultar(f"SELECT ID_POLIZA, ESTADO_POLIZA FROM {RAW}.polizas WHERE fecha_corte = DATE '{PRIMERO}'")
    }
    assert en_raw == en_csv
    con_espacios = simulacion.plataforma.consultar(
        f"SELECT COUNT(*) AS n FROM {RAW}.polizas WHERE ESTADO_POLIZA != TRIM(ESTADO_POLIZA)"
    )
    assert con_espacios[0]["n"] > 0  # los espacios sembrados siguen ahí


# ── HU-14: homologación ─────────────────────────────────────────────────────


def test_la_homologacion_cubre_el_contrato_con_los_mismos_tipos(fuentes, contratos):
    for tabla, contrato in contratos.items():
        mapeadas = {c.destino: c.tipo for c in fuentes[tabla].columnas}
        for campo in contrato["campos"]:
            if campo["nombre"] != "fecha_corte":
                assert mapeadas.get(campo["nombre"]) == campo["tipo"], (tabla, campo["nombre"])


def test_master_usa_los_nombres_estandar(simulacion):
    for tabla in TABLAS_CORTE:
        columnas = [c for c, _ in simulacion.plataforma.columnas(tabla, MASTER)]
        assert columnas[: len(ESQUEMAS[tabla])] == [c for c, _ in ESQUEMAS[tabla]], tabla


def test_los_registros_no_homologables_quedan_fuera_de_master(simulacion):
    p = simulacion.plataforma
    for corte, r in simulacion.resultados.items():
        for i in r.incidencias[:5]:
            llave = {"pago": "id_pago", "siniestro": "id_siniestro"}[i["tabla"]]
            en_master = p.consultar(
                f"SELECT COUNT(*) AS n FROM {MASTER}.{i['tabla']} WHERE fecha_corte = DATE '{corte}' AND {llave} = {i['llave']}"
            )
            assert en_master[0]["n"] == 0


# ── HU-05 y HU-06: clasificación DAC y cifrado ──────────────────────────────


def test_dni_nombres_y_correo_son_sensibles_cifrados(contratos):
    dac = clasificacion(contratos)["persona"]
    for campo in ("nro_documento", "nombres", "apellido_paterno", "apellido_materno", "email"):
        assert dac[campo] == "SENSIBLE_CIFRADO"
    assert dac["tipo_documento"] == "PUBLICO"
    assert clasificacion(contratos)["siniestro"]["monto_reclamado"] == "SENSIBLE"


def test_ningun_campo_pii_queda_en_texto_plano_en_master(simulacion, contratos):
    for tabla, campos in cifrados(contratos).items():
        tipos = dict(simulacion.plataforma.columnas(tabla, MASTER))
        for campo in campos:
            assert tipos[campo] == "BYTES", (tabla, campo)


def test_el_dni_en_master_no_coincide_con_raw_pero_se_descifra_igual(simulacion):
    p = simulacion.plataforma
    raw = {
        f["COD_CLIENTE"]: f["NUM_DOC"]
        for f in p.consultar(f"SELECT COD_CLIENTE, NUM_DOC FROM {RAW}.clientes WHERE fecha_corte = DATE '{PRIMERO}' LIMIT 200")
    }
    descifrado = p.consultar(
        f"SELECT CAST(x.id_persona AS STRING) AS id, {p.funciones.descifrar('x.nro_documento', 'deterministico', 'persona', 'nro_documento')} AS doc "
        f"FROM {MASTER}.persona AS x CROSS JOIN {SQL_LLAVES} AS k WHERE x.fecha_corte = DATE '{PRIMERO}'"
    )
    comparados = [d for d in descifrado if d["id"] in raw]
    assert len(comparados) == len(raw)
    assert all(d["doc"] == (raw[d["id"]] or None) for d in comparados)


def test_deterministico_iguala_documentos_y_aleatorio_no(simulacion):
    """Las personas duplicadas comparten documento y correo: el DNI cifrado coincide, el correo no."""
    fila = simulacion.plataforma.consultar(
        f"WITH duplicadas AS (\n"
        f"  SELECT nro_documento, email FROM {MASTER}.persona WHERE fecha_corte = DATE '{CORTES[-1]}'\n"
        f"  QUALIFY COUNT(*) OVER (PARTITION BY tipo_documento, nro_documento) > 1\n"
        f")\n"
        f"SELECT COUNT(*) AS filas, COUNT(DISTINCT nro_documento) AS documentos,\n"
        f"  COUNT(email) AS con_correo, COUNT(DISTINCT email) AS correos FROM duplicadas"
    )[0]
    assert fila["filas"] > 0
    assert fila["documentos"] * 2 == fila["filas"]  # cada par comparte el mismo DNI cifrado
    assert fila["correos"] == fila["con_correo"]  # el mismo correo se cifra distinto cada vez


# ── Reanudar una carga cortada ──────────────────────────────────────────────


def _reglas(ejecucion):
    return [(r.id_regla, r.tabla, r.universo, r.cumplen, r.estado) for r in ejecucion.resultados]


def test_reanudar_desde_un_corte_da_lo_mismo_que_de_corrido(simulacion, datos, fuentes, contratos, reglas):
    """Una carga que se corta en el cuarto corte y se reanuda desde el tercero termina igual."""
    plataforma = PlataformaDuckDB()
    flujo = Flujo(plataforma, fuentes, contratos, reglas, datos.landing)
    flujo.preparar()
    entregas = leer_entregas(datos.landing)
    for corte in CORTES_PRUEBA[:4]:
        flujo.procesar_corte(corte, entregas, primero=corte == PRIMERO)

    with pytest.raises(ValueError, match="no está evaluado"):
        cortes_por_procesar(plataforma, CORTES_PRUEBA[6], CORTES_PRUEBA)
    desde = CORTES_PRUEBA[2]
    assert cortes_por_procesar(plataforma, desde, CORTES_PRUEBA) == CORTES_PRUEBA[2:]
    assert plataforma.recortar(desde)
    reanudados = {c: flujo.procesar_corte(c, entregas) for c in CORTES_PRUEBA[2:4]}

    for corte, r in reanudados.items():
        esperado = simulacion.resultados[corte]
        assert _reglas(r.ejecucion) == _reglas(esperado.ejecucion), corte
        assert [(c.tabla, c.estado) for c in r.certificaciones] == [(c.tabla, c.estado) for c in esperado.certificaciones]
    # Cada corte queda una sola vez en la evidencia, en RAW y en BUSINESS
    contar = f"SELECT fecha_corte, COUNT(*) AS n FROM {{}} GROUP BY fecha_corte ORDER BY fecha_corte"
    assert [(f["fecha_corte"], f["n"]) for f in plataforma.consultar(contar.format(f"{ENGINE}.ejecuciones"))] == [
        (c, 1) for c in CORTES_PRUEBA[:4]
    ]
    for objeto in (f"{RAW}.registro_cargas", f"{MASTER}.persona", f"{BUSINESS}.p_persona"):
        assert plataforma.consultar(contar.format(objeto)) == [
            f for f in simulacion.plataforma.consultar(contar.format(objeto)) if f["fecha_corte"] in CORTES_PRUEBA[:4]
        ], objeto
