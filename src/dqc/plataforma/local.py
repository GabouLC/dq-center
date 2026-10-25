"""Plataforma local sobre DuckDB: un esquema por dataset de BigQuery."""

from __future__ import annotations

import functools
import threading
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
TIPOS_DUCKDB = {
    "STRING": "VARCHAR",
    "INT64": "BIGINT",
    "FLOAT64": "DOUBLE",
    "BOOL": "BOOLEAN",
    "DATE": "DATE",
    "BYTES": "BLOB",
    "TIMESTAMP": "TIMESTAMPTZ",
}


def _con_candado(metodo):
    """Una conexión de DuckDB no admite hilos en paralelo (la API atiende en varios)."""

    @functools.wraps(metodo)
    def envuelto(self, *args, **kwargs):
        with self._candado:
            return metodo(self, *args, **kwargs)

    return envuelto


class PlataformaDuckDB:
    def __init__(self, ruta: str = ":memory:"):
        self._candado = threading.RLock()
        self.con = duckdb.connect(ruta)
        self.funciones = FuncionesLocal()
        registrar_funciones_duckdb(self.con)
        for dataset in DATASETS:
            self.con.execute(f"CREATE SCHEMA IF NOT EXISTS {dataset}")
        self.con.execute(f"SET search_path = '{MASTER}'")

    @_con_candado
    def preparar(self) -> None:
        self.con.execute(f"CREATE TABLE IF NOT EXISTS {SEGURIDAD}.llaves (nombre VARCHAR, keyset BLOB)")
        if not self.con.execute(f"SELECT COUNT(*) FROM {SEGURIDAD}.llaves").fetchone()[0]:
            for nombre, llave in llaves_locales().items():
                self.con.execute(f"INSERT INTO {SEGURIDAD}.llaves VALUES (?, ?)", [nombre, llave])

    @_con_candado
    def reiniciar(self) -> None:
        objetos = self.con.execute(
            "SELECT table_schema, table_name, table_type FROM information_schema.tables "
            "WHERE table_schema IN (?, ?, ?, ?) ORDER BY table_type DESC",  # primero las vistas
            [RAW, MASTER, ENGINE, BUSINESS],
        ).fetchall()
        for dataset, nombre, tipo in objetos:
            self.con.execute(f"DROP {'VIEW' if tipo == 'VIEW' else 'TABLE'} IF EXISTS {dataset}.{nombre}")

    @_con_candado
    def recortar(self, desde: date) -> list[str]:
        tablas = self.con.execute(
            "SELECT c.table_schema, c.table_name FROM information_schema.columns c "
            "JOIN information_schema.tables t USING (table_schema, table_name) "
            "WHERE c.column_name = 'fecha_corte' AND t.table_type = 'BASE TABLE' AND c.table_schema IN (?, ?, ?, ?)",
            [RAW, MASTER, ENGINE, BUSINESS],
        ).fetchall()
        recortadas = []
        for dataset, tabla in tablas:
            sobran = self.con.execute(f"SELECT COUNT(*) FROM {dataset}.{tabla} WHERE fecha_corte >= ?", [desde]).fetchone()[0]
            if sobran:
                self.con.execute(f"DELETE FROM {dataset}.{tabla} WHERE fecha_corte >= ?", [desde])
                recortadas.append(f"{dataset}.{tabla}: {sobran} filas desde el {desde}")
        return recortadas

    @_con_candado
    def quitar_corte(self, dataset: str, tabla: str, corte: date) -> int:
        if not self.columnas(tabla, dataset):
            return 0
        sobran = self.con.execute(f"SELECT COUNT(*) FROM {dataset}.{tabla} WHERE fecha_corte = ?", [corte]).fetchone()[0]
        if sobran:
            self.con.execute(f"DELETE FROM {dataset}.{tabla} WHERE fecha_corte = ?", [corte])
        return sobran

    @_con_candado
    def crear_tabla(self, dataset: str, tabla: str, columnas: list[tuple[str, str]]) -> None:
        definicion = ", ".join(f"{c} {TIPOS_DUCKDB[t]}" for c, t in columnas)
        self.con.execute(f"CREATE TABLE IF NOT EXISTS {dataset}.{tabla} ({definicion})")

    @_con_candado
    def crear_vista(self, dataset: str, nombre: str, sql_bigquery: str) -> None:
        self.con.execute(f"CREATE OR REPLACE VIEW {dataset}.{nombre} AS {self._traducir(sql_bigquery)}")

    # ── consultas ───────────────────────────────────────────────────────────

    @staticmethod
    def _traducir(sql_bigquery: str) -> str:
        return sqlglot.transpile(sql_bigquery, read="bigquery", write="duckdb")[0]

    @_con_candado
    def consultar(self, sql_bigquery: str) -> list[dict]:
        cursor = self.con.execute(self._traducir(sql_bigquery))
        nombres = [d[0] for d in cursor.description]
        return [dict(zip(nombres, fila)) for fila in cursor.fetchall()]

    @_con_candado
    def probar(self, sql_bigquery: str) -> str | None:
        try:
            self.con.execute("EXPLAIN " + self._traducir(sql_bigquery))
        except Exception as e:  # noqa: BLE001 - DuckDB lanza varias clases de error
            return str(e).splitlines()[0]
        return None

    @_con_candado
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
                    nombre = columna.replace('"', '""')
                    self.con.execute(f'ALTER TABLE {destino} ADD COLUMN "{nombre}" {tipo}')
            if corte is None:
                self.con.execute(f"DELETE FROM {destino}")
            else:
                self.con.execute(f"DELETE FROM {destino} WHERE fecha_corte = ?", [corte])
            self.con.execute(f"INSERT INTO {destino} BY NAME SELECT * FROM _nuevo")
        filas = self.con.execute("SELECT COUNT(*) FROM _nuevo").fetchone()[0]
        self.con.execute("DROP TABLE _nuevo")
        return filas

    @_con_candado
    def escribir(self, dataset: str, tabla: str, datos: pa.Table, corte: date | None, primero: bool = False) -> int:
        self.con.register("_datos", datos)
        try:
            return self._reemplazar(dataset, tabla, "SELECT * FROM _datos", corte)
        finally:
            self.con.unregister("_datos")

    @_con_candado
    def materializar(self, sql_bigquery: str, dataset: str, tabla: str, corte: date | None, primero: bool = False) -> int:
        return self._reemplazar(dataset, tabla, self._traducir(sql_bigquery), corte)

    @_con_candado
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
