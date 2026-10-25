"""Evidencia en BigQuery de HU-01 a HU-08 y su paridad con la corrida local.

Consulta el proyecto de GCP y escribe docs/evidencias/bigquery.txt con:
  - la verificación contra el manifiesto de errores sembrados, calculada con lo que quedó en BigQuery;
  - la paridad con la corrida completa en DuckDB: cada resultado comparado fila por fila;
  - un resumen por historia: cargas, incidencias, PII cifrada, reglas, sellos, Gate y BUSINESS.

Antes de consultar, un dry run estima los bytes que se van a leer y se detiene si pasan de 1 GB.
En el sandbox no hay cobro, pero el tope aplica igual.

  DQC_PROYECTO=dq-center-gabou python scripts/evidencia_bigquery.py [--duckdb data/dq_completo.duckdb]
"""

from __future__ import annotations

import argparse
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pyarrow.parquet as pq
from google.cloud import bigquery

from dqc.modelo import HOMOLOGACION, INGESTA, PRIVACIDAD, TABLAS_CORTE

RAIZ = Path(__file__).resolve().parents[1]
TOPE = 1024**3

# Última ejecución de cada corte: es la que vale si un corte se evaluó más de una vez.
ULTIMAS = (
    "SELECT id_ejecucion FROM dq_engine.ejecuciones "
    "QUALIFY ROW_NUMBER() OVER (PARTITION BY fecha_corte ORDER BY iniciada_en DESC) = 1"
)

# Lo que se compara entre BigQuery y DuckDB: (nombre, consulta). Cada fila tiene que coincidir.
PARIDAD = [
    ("Cargas en RAW (archivo, filas, estado, motivo)",
     "SELECT tabla, fecha_corte, archivo, filas, estado, detalle FROM dq_raw.registro_cargas"),
    ("Incidencias de homologación",
     "SELECT fecha_corte, tabla, llave, columnas FROM dq_master.incidencias_homologacion"),
    ("Resultados de reglas (universo, cumplen, estado)",
     f"SELECT fecha_corte, id_regla, tabla, nivel, universo, cumplen, estado FROM dq_engine.resultados "
     f"WHERE id_ejecucion IN ({ULTIMAS})"),
    ("Registros fallidos por regla",
     f"SELECT fecha_corte, id_regla, tabla, llave FROM dq_engine.fallidos WHERE id_ejecucion IN ({ULTIMAS})"),
    ("Sellos de certificación",
     f"SELECT fecha_corte, tabla, estado, reglas_bloqueantes, reglas_con_observacion, hallazgos, publicado "
     f"FROM dq_engine.certificaciones WHERE id_ejecucion IN ({ULTIMAS})"),
    ("Hallazgos del Privacy Gate",
     f"SELECT fecha_corte, tabla, tipo, columna, llave, bloqueante FROM dq_engine.hallazgos_privacidad "
     f"WHERE id_ejecucion IN ({ULTIMAS})"),
    *[(f"Filas por corte en MASTER.{t}", f"SELECT fecha_corte, COUNT(*) AS filas FROM dq_master.{t} GROUP BY fecha_corte")
      for t in TABLAS_CORTE],
    *[(f"Filas por corte en BUSINESS.p_{t}", f"SELECT fecha_corte, COUNT(*) AS filas FROM dq_business.p_{t} GROUP BY fecha_corte")
      for t in TABLAS_CORTE],
]

RESUMEN = [
    ("HU-01 · Cargas en RAW por estado",
     "SELECT estado, COUNT(*) AS cargas, SUM(filas) AS filas, COUNT(DISTINCT fecha_corte) AS cortes "
     "FROM dq_raw.registro_cargas GROUP BY estado ORDER BY estado"),
    ("HU-01 · Cargas rechazadas, con su motivo (no llegan a RAW)",
     "SELECT fecha_corte, tabla, archivo, detalle FROM dq_raw.registro_cargas WHERE estado = 'RECHAZADA' "
     "ORDER BY fecha_corte"),
    ("HU-14 · Incidencias de homologación (registros que quedan fuera de MASTER)",
     "SELECT tabla, columnas, COUNT(*) AS registros, COUNT(DISTINCT fecha_corte) AS cortes, "
     "MIN(fecha_corte) AS desde, MAX(fecha_corte) AS hasta FROM dq_master.incidencias_homologacion "
     "GROUP BY tabla, columnas ORDER BY tabla, columnas"),
    ("HU-06 · Tipo de cada campo PII en MASTER: se guardan cifrados (BYTES, AEAD)",
     "SELECT table_name, column_name, data_type FROM dq_master.INFORMATION_SCHEMA.COLUMNS "
     "WHERE data_type = 'BYTES' ORDER BY table_name, ordinal_position"),
    ("HU-06 · Muestra de Persona en MASTER (último corte)",
     "SELECT id_persona, SUBSTR(TO_BASE64(nro_documento), 1, 24) || '…' AS nro_documento_cifrado, "
     "SUBSTR(TO_BASE64(email), 1, 24) || '…' AS email_cifrado FROM dq_master.persona "
     "WHERE fecha_corte = (SELECT MAX(fecha_corte) FROM dq_master.persona) ORDER BY id_persona LIMIT 3"),
    ("HU-02 / HU-03 · Reglas evaluadas por nivel y estado (92 cortes, última ejecución de cada uno)",
     f"SELECT nivel, COUNT(DISTINCT id_regla || tabla) AS reglas, COUNTIF(estado = 'OK') AS ok, "
     f"COUNTIF(estado = 'ALERTA') AS alerta, COUNTIF(estado = 'FALLA') AS falla, "
     f"COUNTIF(estado = 'SIN_DATOS') AS sin_datos FROM dq_engine.resultados WHERE id_ejecucion IN ({ULTIMAS}) "
     f"GROUP BY nivel ORDER BY nivel"),
    ("HU-04 · Sellos por tabla en los 92 cortes",
     f"SELECT tabla, COUNTIF(estado = 'CERTIFICADO') AS certificado, "
     f"COUNTIF(estado = 'CERTIFICADO_CON_OBSERVACIONES') AS con_observaciones, "
     f"COUNTIF(estado = 'NO_CERTIFICADO') AS no_certificado FROM dq_engine.certificaciones "
     f"WHERE id_ejecucion IN ({ULTIMAS}) GROUP BY tabla ORDER BY tabla"),
    ("HU-04 / HU-07 · Tablas no certificadas y su motivo (retenidas por el Gate)",
     f"SELECT fecha_corte, tabla, reglas_bloqueantes, privacidad_ok, hallazgos, publicado "
     f"FROM dq_engine.certificaciones WHERE id_ejecucion IN ({ULTIMAS}) AND estado = 'NO_CERTIFICADO' "
     f"ORDER BY fecha_corte, tabla"),
    ("HU-07 · Hallazgos del Privacy Gate",
     f"SELECT tipo, tabla, columna, bloqueante, COUNT(*) AS registros, COUNT(DISTINCT fecha_corte) AS cortes, "
     f"MIN(fecha_corte) AS desde, MAX(fecha_corte) AS hasta FROM dq_engine.hallazgos_privacidad "
     f"WHERE id_ejecucion IN ({ULTIMAS}) GROUP BY tipo, tabla, columna, bloqueante ORDER BY desde"),
    ("HU-07 · Evidencia del sello: versión del motor y de las reglas",
     f"SELECT version_motor, version_reglas, COUNT(*) AS sellos, MIN(certificado_en) AS primero, "
     f"MAX(certificado_en) AS ultimo FROM dq_engine.certificaciones WHERE id_ejecucion IN ({ULTIMAS}) "
     f"GROUP BY version_motor, version_reglas"),
    ("HU-08 · Objetos de BUSINESS (p_ = tablas con lo certificado, v_ = vistas)",
     "SELECT table_name, table_type FROM dq_business.INFORMATION_SCHEMA.TABLES ORDER BY table_name"),
    ("HU-08 · Cortes publicados por tabla y último corte en su vista v_",
     " UNION ALL ".join(
         f"SELECT '{t}' AS tabla, (SELECT COUNT(DISTINCT fecha_corte) FROM dq_business.p_{t}) AS cortes_publicados, "
         f"(SELECT MAX(fecha_corte) FROM dq_business.v_{t}) AS corte_en_la_vista"
         for t in TABLAS_CORTE
     ) + " ORDER BY tabla"),
    ("HU-08 · Cortes no certificados que llegaron a BUSINESS (debe estar vacío)",
     " UNION ALL ".join(
         f"SELECT c.fecha_corte, c.tabla FROM dq_engine.certificaciones AS c "
         f"JOIN (SELECT DISTINCT fecha_corte FROM dq_business.p_{t}) AS p USING (fecha_corte) "
         f"WHERE c.tabla = '{t}' AND c.estado = 'NO_CERTIFICADO' AND c.id_ejecucion IN ({ULTIMAS})"
         for t in TABLAS_CORTE
     )),
]


def formatear(filas: list[dict]) -> str:
    if not filas:
        return "(sin filas)"
    columnas = list(filas[0])
    texto = [[("" if v is None else str(v)) for v in f.values()] for f in filas]
    anchos = [max(len(c), *(len(t[i]) for t in texto)) for i, c in enumerate(columnas)]
    lineas = ["  ".join(c.ljust(a) for c, a in zip(columnas, anchos)), "  ".join("-" * a for a in anchos)]
    lineas += ["  ".join(v.ljust(a) for v, a in zip(t, anchos)).rstrip() for t in texto]
    return "\n".join(lineas)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--proyecto", default=os.environ.get("DQC_PROYECTO"))
    parser.add_argument("--duckdb", type=Path, default=RAIZ / "data" / "dq_completo.duckdb")
    parser.add_argument("--manifiesto", type=Path, default=RAIZ / "data" / "manifiesto_errores.parquet")
    parser.add_argument("--salida", type=Path, default=RAIZ / "docs" / "evidencias" / "bigquery.txt")
    args = parser.parse_args()
    if not args.proyecto:
        parser.error("indica --proyecto o define DQC_PROYECTO")

    cliente = bigquery.Client(project=args.proyecto, location="US")
    consultas = [sql for _, sql in PARIDAD + RESUMEN] + [
        "SELECT tabla, fecha_corte, archivo FROM dq_raw.registro_cargas WHERE estado = 'RECHAZADA'",
    ]
    estimados = sum(
        cliente.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)).total_bytes_processed
        for sql in consultas
    )
    print(f"Dry run: las consultas leerían {estimados / 1024**2:.1f} MB.")
    if estimados > TOPE:
        raise SystemExit("Más de 1 GB: no se consulta.")
    config = bigquery.QueryJobConfig(maximum_bytes_billed=TOPE)

    def bq(sql: str) -> list[dict]:
        return [dict(f.items()) for f in cliente.query(sql, job_config=config).result()]

    local = duckdb.connect(str(args.duckdb), read_only=True)

    def dk(sql: str) -> list[dict]:
        cursor = local.execute(sql)
        nombres = [d[0] for d in cursor.description]
        return [dict(zip(nombres, f)) for f in cursor.fetchall()]

    secciones = []

    # Verificación contra el manifiesto, con lo que quedó en BigQuery
    manifiesto = pq.read_table(args.manifiesto).to_pylist()
    rechazos = {(f["tabla"], f["fecha_corte"], f["archivo"]) for f in bq(consultas[-1])}
    incidencias = {(f["tabla"], f["fecha_corte"], f["llave"]) for f in bq(PARIDAD[1][1])}
    fallidos = {(f["id_regla"], f["tabla"], f["fecha_corte"], f["llave"]) for f in bq(PARIDAD[3][1])}
    fugas = {(f["tabla"], f["fecha_corte"], f["llave"]) for f in bq(PARIDAD[5][1]) if f["tipo"] == "PII_EN_CLARO"}
    reglas = {f["id_regla"] for f in bq(f"SELECT DISTINCT id_regla FROM dq_engine.resultados")}
    cortes = {f["fecha_corte"] for f in bq("SELECT DISTINCT fecha_corte FROM dq_engine.ejecuciones")}

    def esperados(etapa: str) -> set[tuple]:
        return {(m["tabla"], m["fecha_corte"], m["llave"]) for m in manifiesto if m["id_regla"] == etapa and m["fecha_corte"] in cortes}

    sembrados = {
        (m["id_regla"], m["tabla"], m["fecha_corte"], m["llave"])
        for m in manifiesto if m["fecha_corte"] in cortes and m["id_regla"] in reglas
    }
    verificacion = [
        ("ingesta", esperados(INGESTA), rechazos),
        ("homologación", esperados(HOMOLOGACION), incidencias),
        ("reglas", sembrados, fallidos),
        ("privacidad", esperados(PRIVACIDAD), fugas),
    ]
    filas = [
        {"etapa": etapa, "sembrados": len(e), "detectados": len(d), "sin_detectar": len(e - d), "de_mas": len(d - e)}
        for etapa, e, d in verificacion
    ]
    exacto = all(f["sin_detectar"] == 0 and f["de_mas"] == 0 for f in filas)
    secciones.append((f"Verificación contra el manifiesto de errores sembrados ({len(cortes)} cortes en BigQuery)", formatear(filas)))

    # Paridad con DuckDB
    filas, iguales = [], True
    for nombre, sql in PARIDAD:
        en_bq = Counter(tuple(f.values()) for f in bq(sql))
        en_dk = Counter(tuple(f.values()) for f in dk(sql))
        diferencias = sum(((en_bq - en_dk) + (en_dk - en_bq)).values())
        iguales &= diferencias == 0
        filas.append({"qué se compara": nombre, "filas_bigquery": sum(en_bq.values()),
                      "filas_duckdb": sum(en_dk.values()), "diferencias": diferencias})
    secciones.append((f"Paridad con la corrida completa en DuckDB ({args.duckdb.name})", formatear(filas)))

    for titulo, sql in RESUMEN:
        secciones.append((titulo, formatear(bq(sql))))

    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    texto = (
        f"Evidencia en BigQuery · proyecto {args.proyecto} (sandbox, datos sintéticos)\n"
        f"Generada: {ahora} · consultas estimadas por dry run: {estimados / 1024**2:.1f} MB\n"
        f"Verificación contra el manifiesto: {'0 diferencias' if exacto else 'HAY DIFERENCIAS'} · "
        f"paridad con DuckDB: {'0 diferencias' if iguales else 'HAY DIFERENCIAS'}\n"
    )
    texto += "".join(f"\n## {titulo}\n\n{cuerpo}\n" for titulo, cuerpo in secciones)
    args.salida.write_text(texto, encoding="utf-8", newline="\n")
    print(texto.split("\n## ")[0])
    raise SystemExit(0 if exacto and iguales else 1)


if __name__ == "__main__":
    main()
