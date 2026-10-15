"""Plataforma local sobre DuckDB: un esquema por dataset de BigQuery."""

from __future__ import annotations

from datetime import date

import duckdb
import pyarrow as pa
import sqlglot

from dqc.modelo import BUSINESS, ENGINE, MASTER, RAW, SEGURIDAD
from dqc.pipeline.funciones import FuncionesLocal, llaves_locales, registrar_funciones_duckdb
from dqc.tipos import esquema_arrow

DATASETS = (RAW, MASTER, ENGINE, SEGURIDAD, BUSINESS)

# Tipos de DuckDB con su nombre en BigQuery, para que la foto del esquema
# sea igual en las dos plataformas.
TIPOS_BIGQUERY = {
    "BIGINT": "INT64",
    "INTEGER": "INT64",
    "VARCHAR": "STRING",
    "DOUBLE": "FLOAT64",
    "BOOLEAN": "BOOL",
    "DATE": "DATE",
    "BLOB": "BYTES",
    "TIMESTAMP WITH TIME ZONE": "TIMESTAMP",
}

class PlataformaDuckDB:
    def __init__(self, ruta: str = ":memory:"):
        self.con = duckdb.connect(ruta)
        self.funciones = FuncionesLocal()
        registrar_funciones_duckdb(self.con)
        for dataset in DATASETS:
            self.con.execute(f"CREATE SCHEMA IF NOT EXISTS {dataset}")
        self.con.execute(f"SET search_path = '{MASTER}'")

    def preparar(self) -> None:
        self.con.execute(f"CREATE TABLE IF NOT EXISTS {SEGURIDAD}.llaves (nombre VARCHAR, keyset BLOB)")
        if not self.con.execute(f"SELECT COUNT(*) FROM {SEGURIDAD}.llaves").fetchone()[0]:
            for nombre, llave in llaves_locales().items():
                self.con.execute(f"INSERT INTO {SEGURIDAD}.llaves VALUES (?, ?)", [nombre, llave])

    def reiniciar(self) -> None:
        for dataset in (RAW, MASTER, ENGINE, BUSINESS):
            for (tabla,) in self.con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = ?", [dataset]
            ).fetchall():
                self.con.execute(f"DROP TABLE {dataset}.{tabla}")

    # ── consultas ───────────────────────────────────────────────────────────

    @staticmethod
    def _traducir(sql_bigquery: str) -> str:
        return sqlglot.transpile(sql_bigquery, read="bigquery", write="duckdb")[0]

    def consultar(self, sql_bigquery: str) -> list[dict]:
        cursor = self.con.execute(self._traducir(sql_bigquery))
        nombres = [d[0] for d in cursor.description]
        return [dict(zip(nombres, fila)) for fila in cursor.fetchall()]

    def probar(self, sql_bigquery: str) -> str | None:
        try:
            self.con.execute("EXPLAIN " + self._traducir(sql_bigquery))
        except Exception as e:  # noqa: BLE001 - DuckDB lanza varias clases de error
            return str(e).splitlines()[0]
        return None

    def columnas(self, tabla: str, dataset: str = MASTER) -> list[tuple[str, str]]:
        filas = self.con.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position",
            [dataset, tabla],
        ).fetchall()
        return [(columna, TIPOS_BIGQUERY.get(tipo, tipo)) for columna, tipo in filas]

    # ── escritura ───────────────────────────────────────────────────────────

    def _reemplazar(self, dataset: str, tabla: str, relacion: str, corte: date | None) -> int:
        destino = f"{dataset}.{tabla}"
        self.con.execute(f"CREATE OR REPLACE TEMP TABLE _nuevo AS {relacion}")
        if not self.columnas(tabla, dataset):
            self.con.execute(f"CREATE TABLE {destino} AS SELECT * FROM _nuevo")
        else:
            actuales = {c for c, _ in self.columnas(tabla, dataset)}
            for columna, tipo in self.con.execute(
                "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '_nuevo'"
            ).fetchall():
                if columna not in actuales:
                    self.con.execute(f"ALTER TABLE {destino} ADD COLUMN {columna} {tipo}")
            if corte is None:
                self.con.execute(f"DELETE FROM {destino}")
            else:
                self.con.execute(f"DELETE FROM {destino} WHERE fecha_corte = ?", [corte])
            self.con.execute(f"INSERT INTO {destino} BY NAME SELECT * FROM _nuevo")
        filas = self.con.execute("SELECT COUNT(*) FROM _nuevo").fetchone()[0]
        self.con.execute("DROP TABLE _nuevo")
        return filas

    def escribir(self, dataset: str, tabla: str, datos: pa.Table, corte: date | None, primero: bool = False) -> int:
        self.con.register("_datos", datos)
        try:
            return self._reemplazar(dataset, tabla, "SELECT * FROM _datos", corte)
        finally:
            self.con.unregister("_datos")

    def materializar(self, sql_bigquery: str, dataset: str, tabla: str, corte: date | None, primero: bool = False) -> int:
        return self._reemplazar(dataset, tabla, self._traducir(sql_bigquery), corte)

    def agregar(self, dataset: str, tabla: str, filas: list[dict], esquema: list[tuple[str, str]]) -> None:
        if not filas:
            return
        datos = pa.Table.from_pylist(filas, schema=esquema_arrow(esquema))
        self.con.register("_datos", datos)
        try:
            if not self.columnas(tabla, dataset):
                self.con.execute(f"CREATE TABLE {dataset}.{tabla} AS SELECT * FROM _datos")
            else:
                self.con.execute(f"INSERT INTO {dataset}.{tabla} BY NAME SELECT * FROM _datos")
        finally:
            self.con.unregister("_datos")
