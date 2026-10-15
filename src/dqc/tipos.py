"""Tipos de BigQuery traducidos a Arrow, para escribir Parquet y tablas locales."""

import pyarrow as pa

TIPOS_ARROW = {
    "STRING": pa.string(),
    "INT64": pa.int64(),
    "FLOAT64": pa.float64(),
    "BOOL": pa.bool_(),
    "DATE": pa.date32(),
    "BYTES": pa.binary(),
    "TIMESTAMP": pa.timestamp("us", tz="UTC"),
}


def esquema_arrow(columnas: list[tuple[str, str]]) -> pa.Schema:
    return pa.schema([(nombre, TIPOS_ARROW[tipo]) for nombre, tipo in columnas])
