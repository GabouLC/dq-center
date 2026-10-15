"""Escritura del resultado del generador en Parquet, una foto por tabla y corte."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from dqc.datagen.generador import Resultado
from dqc.modelo import TABLAS_CORTE, esquema

TIPOS_ARROW = {
    "STRING": pa.string(),
    "INT64": pa.int64(),
    "FLOAT64": pa.float64(),
    "BOOL": pa.bool_(),
    "DATE": pa.date32(),
    "TIMESTAMP": pa.timestamp("us", tz="UTC"),
}


def esquema_arrow(tabla: str, corte=None) -> pa.Schema:
    return pa.schema([(nombre, TIPOS_ARROW[tipo]) for nombre, tipo in esquema(tabla, corte)])


def ruta_corte(salida: Path, tabla: str, corte) -> Path:
    return salida / tabla / f"{corte.isoformat()}.parquet"


def _escribir(filas: list[dict], destino: Path, schema: pa.Schema) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(filas, schema=schema), destino)


def escribir_parquet(resultado: Resultado, salida: Path) -> None:
    """ref_*.parquet, <tabla>/<corte>.parquet, registro_cargas y manifiesto_errores."""
    for tabla, filas in resultado.ref.items():
        _escribir(filas, salida / f"{tabla}.parquet", esquema_arrow(tabla))
    for tabla in TABLAS_CORTE:
        for corte, filas in resultado.por_corte[tabla].items():
            _escribir(filas, ruta_corte(salida, tabla, corte), esquema_arrow(tabla, corte))
    _escribir(resultado.registro_cargas, salida / "registro_cargas.parquet", esquema_arrow("registro_cargas"))
    _escribir(resultado.manifiesto, salida / "manifiesto_errores.parquet", esquema_arrow("manifiesto_errores"))
