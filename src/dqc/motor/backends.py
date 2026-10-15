"""Dónde corre el SQL: DuckDB en local y en las pruebas, BigQuery en GCP.

El motor siempre genera SQL de BigQuery; el backend de DuckDB lo traduce con
sqlglot. Así las pruebas ejercitan el mismo SQL que corre en producción.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import sqlglot

from dqc.modelo import TABLAS_CORTE, TABLAS_REF


class Backend(Protocol):
    def consultar(self, sql_bigquery: str) -> list[dict]: ...

    def columnas(self, tabla: str) -> list[tuple[str, str]]: ...


class BackendDuckDB:
    def __init__(self, conexion=None):
        import duckdb

        self.con = conexion or duckdb.connect()

    def consultar(self, sql_bigquery: str) -> list[dict]:
        sql = sqlglot.transpile(sql_bigquery, read="bigquery", write="duckdb")[0]
        cursor = self.con.execute(sql)
        nombres = [d[0] for d in cursor.description]
        return [dict(zip(nombres, fila)) for fila in cursor.fetchall()]

    def columnas(self, tabla: str) -> list[tuple[str, str]]:
        return self.con.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = ? ORDER BY ordinal_position",
            [tabla],
        ).fetchall()

    # ── carga local, corte por corte ────────────────────────────────────────

    def _existe(self, tabla: str) -> bool:
        return bool(self.con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?", [tabla]
        ).fetchone()[0])

    def cargar_referencias(self, datos: Path) -> None:
        for tabla in TABLAS_REF:
            self.con.execute(
                f"CREATE OR REPLACE TABLE {tabla} AS SELECT * FROM read_parquet(?)",
                [str(datos / f"{tabla}.parquet")],
            )

    def cargar_corte(self, datos: Path, corte) -> None:
        """Carga la foto de un corte; si trae columnas nuevas, las agrega a la tabla."""
        for tabla in TABLAS_CORTE:
            archivo = str(datos / tabla / f"{corte.isoformat()}.parquet")
            if not self._existe(tabla):
                self.con.execute(f"CREATE TABLE {tabla} AS SELECT * FROM read_parquet(?)", [archivo])
                continue
            actuales = {c for c, _ in self.columnas(tabla)}
            nuevas = self.con.execute(
                "SELECT column_name, column_type FROM (DESCRIBE SELECT * FROM read_parquet(?))", [archivo]
            ).fetchall()
            for columna, tipo in nuevas:
                if columna not in actuales:
                    self.con.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}")
            self.con.execute(f"DELETE FROM {tabla} WHERE fecha_corte = ?", [corte])
            self.con.execute(f"INSERT INTO {tabla} BY NAME SELECT * FROM read_parquet(?)", [archivo])

        registro = str(datos / "registro_cargas.parquet")
        if not self._existe("registro_cargas"):
            self.con.execute(f"CREATE TABLE registro_cargas AS SELECT * FROM read_parquet(?) WHERE false", [registro])
        self.con.execute("DELETE FROM registro_cargas WHERE fecha_corte = ?", [corte])
        self.con.execute(
            "INSERT INTO registro_cargas SELECT * FROM read_parquet(?) WHERE fecha_corte = ?", [registro, corte]
        )
