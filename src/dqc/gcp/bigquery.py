"""BigQuery: datasets, carga corte por corte, backend del motor y almacén de resultados.

Modo sandbox (proyecto sin facturación): BigQuery vence tablas y particiones a
los 60 días, y las particiones por fecha de corte de abril a julio vencerían al
instante. En ese modo las tablas se agrupan (cluster) por fecha_corte en vez de
particionarse, y cada corte se agrega en lugar de reemplazar su partición.
Todo se escribe con load jobs, que son gratis y funcionan en el sandbox.
"""

from __future__ import annotations

import io
from datetime import date, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from google.api_core.exceptions import Conflict
from google.cloud import bigquery

from dqc.modelo import ESQUEMAS, TABLAS_CORTE, TABLAS_REF
from dqc.motor.motor import Ejecucion

DATASET_RAW = "dq_raw"
DATASET_ENGINE = "dq_engine"
UBICACION = "US"

ESQUEMAS_ENGINE = {
    "ejecuciones": [
        ("id_ejecucion", "STRING"), ("fecha_corte", "DATE"), ("origen", "STRING"),
        ("iniciada_en", "TIMESTAMP"), ("terminada_en", "TIMESTAMP"), ("reglas", "INT64"),
    ],
    "resultados": [
        ("id_ejecucion", "STRING"), ("fecha_corte", "DATE"), ("id_regla", "STRING"), ("tabla", "STRING"),
        ("dimension", "STRING"), ("severidad", "STRING"), ("tipo", "STRING"), ("umbral", "FLOAT64"),
        ("universo", "INT64"), ("cumplen", "INT64"), ("cumplimiento", "FLOAT64"), ("estado", "STRING"),
    ],
    "fallidos": [
        ("id_ejecucion", "STRING"), ("fecha_corte", "DATE"), ("id_regla", "STRING"), ("tabla", "STRING"),
        ("llave", "STRING"), ("detalle", "STRING"),
    ],
    "esquemas": [
        ("id_ejecucion", "STRING"), ("fecha_corte", "DATE"), ("tabla", "STRING"), ("posicion", "INT64"),
        ("columna", "STRING"), ("tipo", "STRING"),
    ],
}


def _campos(columnas: list[tuple[str, str]]) -> list[bigquery.SchemaField]:
    return [bigquery.SchemaField(nombre, tipo) for nombre, tipo in columnas]


def preparar(cliente: bigquery.Client, sandbox: bool) -> list[str]:
    """Crea los datasets y las tablas que falten. Devuelve las tablas creadas."""
    proyecto = cliente.project
    creadas = []
    for dataset in (DATASET_RAW, DATASET_ENGINE):
        ds = bigquery.Dataset(f"{proyecto}.{dataset}")
        ds.location = UBICACION
        cliente.create_dataset(ds, exists_ok=True)

    tablas = [(DATASET_RAW, t, ESQUEMAS[t]) for t in [*TABLAS_REF, *TABLAS_CORTE, "registro_cargas", "manifiesto_errores"]]
    tablas += [(DATASET_ENGINE, t, columnas) for t, columnas in ESQUEMAS_ENGINE.items()]
    for dataset, nombre, columnas in tablas:
        tabla = bigquery.Table(f"{proyecto}.{dataset}.{nombre}", schema=_campos(columnas))
        if any(c == "fecha_corte" for c, _ in columnas):
            if sandbox:
                tabla.clustering_fields = ["fecha_corte"]
            else:
                tabla.time_partitioning = bigquery.TimePartitioning(field="fecha_corte")
        try:
            cliente.create_table(tabla)
            creadas.append(f"{dataset}.{nombre}")
        except Conflict:
            pass
    return creadas


def _particionada(cliente: bigquery.Client, tabla: str) -> bool:
    return cliente.get_table(tabla).time_partitioning is not None


def _parquet_en_memoria(tabla: pa.Table) -> io.BytesIO:
    buffer = io.BytesIO()
    pq.write_table(tabla, buffer)
    buffer.seek(0)
    return buffer


class CargaBigQuery:
    """Carga los Parquet del generador en dq_raw, como lo haría un proceso de ingesta."""

    def __init__(self, cliente: bigquery.Client):
        self.cliente = cliente
        self.raw = f"{cliente.project}.{DATASET_RAW}"

    def _cargar(self, origen: io.IOBase, destino: str, disposicion: str, agregar_columnas: bool) -> None:
        config = bigquery.LoadJobConfig(source_format=bigquery.SourceFormat.PARQUET, write_disposition=disposicion)
        if agregar_columnas:
            config.schema_update_options = [bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION]
        self.cliente.load_table_from_file(origen, destino, job_config=config).result()

    def cargar_referencias(self, datos: Path) -> None:
        for tabla in [*TABLAS_REF, "manifiesto_errores"]:
            with open(datos / f"{tabla}.parquet", "rb") as f:
                self._cargar(f, f"{self.raw}.{tabla}", "WRITE_TRUNCATE", agregar_columnas=False)

    def cargar_corte(self, datos: Path, corte: date, primero: bool) -> None:
        """Reemplaza la partición del corte; en el sandbox, agrega el corte (y vacía en el primero)."""
        registro = pq.read_table(datos / "registro_cargas.parquet").filter(
            pc.field("fecha_corte") == pa.scalar(corte, pa.date32())
        )
        fuentes = {t: open(datos / t / f"{corte.isoformat()}.parquet", "rb") for t in TABLAS_CORTE}
        fuentes["registro_cargas"] = _parquet_en_memoria(registro)
        try:
            for tabla, origen in fuentes.items():
                destino = f"{self.raw}.{tabla}"
                if _particionada(self.cliente, destino):
                    self._cargar(origen, f"{destino}${corte:%Y%m%d}", "WRITE_TRUNCATE", agregar_columnas=True)
                elif primero:
                    self._cargar(origen, destino, "WRITE_TRUNCATE", agregar_columnas=False)
                else:
                    self._cargar(origen, destino, "WRITE_APPEND", agregar_columnas=True)
        finally:
            for origen in fuentes.values():
                origen.close()


class BackendBigQuery:
    def __init__(self, cliente: bigquery.Client):
        self.cliente = cliente
        self.raw = f"{cliente.project}.{DATASET_RAW}"

    def consultar(self, sql_bigquery: str) -> list[dict]:
        config = bigquery.QueryJobConfig(default_dataset=self.raw)
        return [dict(fila.items()) for fila in self.cliente.query(sql_bigquery, job_config=config).result()]

    def columnas(self, tabla: str) -> list[tuple[str, str]]:
        sql = (
            f"SELECT column_name, data_type FROM `{self.raw}`.INFORMATION_SCHEMA.COLUMNS "
            f"WHERE table_name = @tabla ORDER BY ordinal_position"
        )
        config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("tabla", "STRING", tabla)]
        )
        return [(f["column_name"], f["data_type"]) for f in self.cliente.query(sql, job_config=config).result()]


def _json(valor):
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    return valor


class AlmacenBigQuery:
    """Guarda cada ejecución del motor en dq_engine (con load jobs, sin streaming)."""

    def __init__(self, cliente: bigquery.Client):
        self.cliente = cliente
        self.engine = f"{cliente.project}.{DATASET_ENGINE}"

    def _agregar(self, tabla: str, filas: list[dict]) -> None:
        if not filas:
            return
        config = bigquery.LoadJobConfig(
            schema=_campos(ESQUEMAS_ENGINE[tabla]),
            write_disposition="WRITE_APPEND",
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        )
        filas = [{k: _json(v) for k, v in f.items()} for f in filas]
        self.cliente.load_table_from_json(filas, f"{self.engine}.{tabla}", job_config=config).result()

    def guardar(self, e: Ejecucion) -> None:
        base = {"id_ejecucion": e.id_ejecucion, "fecha_corte": e.fecha_corte}
        self._agregar("ejecuciones", [{
            **base, "origen": e.origen, "iniciada_en": e.iniciada_en,
            "terminada_en": e.terminada_en, "reglas": len(e.resultados),
        }])
        self._agregar("resultados", [
            {
                **base, "id_regla": r.id_regla, "tabla": r.tabla, "dimension": r.dimension,
                "severidad": r.severidad, "tipo": r.tipo, "umbral": r.umbral, "universo": r.universo,
                "cumplen": r.cumplen, "cumplimiento": r.cumplimiento, "estado": r.estado,
            }
            for r in e.resultados
        ])
        self._agregar("fallidos", [
            {**base, "id_regla": r.id_regla, "tabla": r.tabla, "llave": llave, "detalle": r.muestra.get(llave)}
            for r in e.resultados
            for llave in r.fallidos
        ])
        self._agregar("esquemas", [
            {**base, "tabla": tabla, "posicion": i, "columna": columna, "tipo": tipo}
            for tabla, columnas in e.esquemas.items()
            for i, (columna, tipo) in enumerate(columnas, start=1)
        ])


def leer_manifiesto(cliente: bigquery.Client) -> list[dict]:
    sql = f"SELECT * FROM `{cliente.project}.{DATASET_RAW}.manifiesto_errores`"
    return [dict(f.items()) for f in cliente.query(sql).result()]
