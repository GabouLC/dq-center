"""Plataforma en BigQuery, con los guardianes del documento de arquitectura.

Guardianes: cada consulta tiene un tope de bytes facturables y solo se escribe
en los datasets del flujo. Todo se escribe con load jobs o consultas con tabla
destino, que funcionan en el sandbox (sin DML).

Modo sandbox (proyecto sin facturación): BigQuery vence tablas y particiones a
los 60 días, y las particiones de abril a julio vencerían al instante. En ese
modo las tablas se agrupan por fecha_corte en vez de particionarse, y cada
corte se agrega (el primero vacía la tabla) en lugar de reemplazar su partición.
"""

from __future__ import annotations

import base64
import io
from datetime import date, datetime

import pyarrow as pa
import pyarrow.parquet as pq
import sqlglot
from google.api_core.exceptions import BadRequest, NotFound
from google.cloud import bigquery

from dqc.modelo import BUSINESS, ENGINE, MASTER, RAW, SEGURIDAD
from dqc.pipeline.funciones import LLAVE_ALEATORIA, LLAVE_DETERMINISTICA, FuncionesBigQuery

UBICACION = "US"
DATASETS = (RAW, MASTER, ENGINE, SEGURIDAD, BUSINESS)
ESCRIBIBLES = {RAW, MASTER, ENGINE, BUSINESS}
TOPE_BYTES = 2 * 1024**3  # 2 GB por consulta: el volumen real es de MB


def _json(valor):
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    if isinstance(valor, bytes):
        return base64.b64encode(valor).decode()  # así espera BigQuery un BYTES en JSON
    return valor


class PlataformaBigQuery:
    def __init__(self, cliente: bigquery.Client, sandbox: bool):
        self.cliente = cliente
        self.proyecto = cliente.project
        self.sandbox = sandbox
        self.funciones = FuncionesBigQuery()

    def _tabla(self, dataset: str, tabla: str) -> str:
        return f"{self.proyecto}.{dataset}.{tabla}"

    # ── preparación ─────────────────────────────────────────────────────────

    def preparar(self) -> None:
        for dataset in DATASETS:
            ds = bigquery.Dataset(f"{self.proyecto}.{dataset}")
            ds.location = UBICACION
            self.cliente.create_dataset(ds, exists_ok=True)
        llaves = self._tabla(SEGURIDAD, "llaves")
        try:
            existentes = next(iter(self.cliente.query(f"SELECT COUNT(*) AS n FROM `{llaves}`").result()))["n"]
        except NotFound:
            existentes = 0
        if existentes:
            return
        # Los keysets se crean dentro de BigQuery y se guardan con un load job.
        sql = (
            f"SELECT '{LLAVE_DETERMINISTICA}' AS nombre, KEYS.NEW_KEYSET('DETERMINISTIC_AEAD_AES_SIV_CMAC_256') AS keyset "
            f"UNION ALL SELECT '{LLAVE_ALEATORIA}', KEYS.NEW_KEYSET('AEAD_AES_GCM_256')"
        )
        filas = [dict(f.items()) for f in self.cliente.query(sql).result()]
        self.agregar(SEGURIDAD, "llaves", filas, [("nombre", "STRING"), ("keyset", "BYTES")], _guardian=False)

    def reiniciar(self) -> None:
        for dataset in (BUSINESS, RAW, MASTER, ENGINE):  # primero las vistas de BUSINESS
            try:
                for tabla in self.cliente.list_tables(f"{self.proyecto}.{dataset}"):
                    self.cliente.delete_table(tabla.reference, not_found_ok=True)
            except NotFound:
                pass

    def crear_tabla(self, dataset: str, tabla: str, columnas: list[tuple[str, str]]) -> None:
        nueva = bigquery.Table(self._tabla(dataset, tabla), schema=[bigquery.SchemaField(n, t) for n, t in columnas])
        if any(c == "fecha_corte" for c, _ in columnas):
            if self.sandbox:
                nueva.clustering_fields = ["fecha_corte"]
            else:
                nueva.time_partitioning = bigquery.TimePartitioning(field="fecha_corte")
        self.cliente.create_table(nueva, exists_ok=True)

    def _calificar(self, sql_bigquery: str) -> str:
        """Una vista de BigQuery necesita las tablas con el proyecto: dataset.tabla -> proyecto.dataset.tabla."""
        arbol = sqlglot.parse_one(sql_bigquery, read="bigquery")
        for tabla in arbol.find_all(sqlglot.exp.Table):
            if tabla.args.get("db") is not None and tabla.args.get("catalog") is None:
                tabla.set("catalog", sqlglot.exp.to_identifier(self.proyecto, quoted=True))
        return arbol.sql(dialect="bigquery")

    def crear_vista(self, dataset: str, nombre: str, sql_bigquery: str) -> None:
        if dataset not in ESCRIBIBLES:
            raise PermissionError(f"el flujo no escribe en {dataset}")
        consulta = self._calificar(sql_bigquery)
        try:
            vista = self.cliente.get_table(self._tabla(dataset, nombre))
            vista.view_query = consulta
            self.cliente.update_table(vista, ["view_query"])
        except NotFound:
            vista = bigquery.Table(self._tabla(dataset, nombre))
            vista.view_query = consulta
            self.cliente.create_table(vista)

    # ── consultas ───────────────────────────────────────────────────────────

    def _config(self, **extra) -> bigquery.QueryJobConfig:
        return bigquery.QueryJobConfig(
            default_dataset=f"{self.proyecto}.{MASTER}", maximum_bytes_billed=TOPE_BYTES, **extra
        )

    def consultar(self, sql_bigquery: str) -> list[dict]:
        return [dict(f.items()) for f in self.cliente.query(sql_bigquery, job_config=self._config()).result()]

    def probar(self, sql_bigquery: str) -> str | None:
        try:
            self.cliente.query(sql_bigquery, job_config=self._config(dry_run=True, use_query_cache=False))
        except BadRequest as e:
            return e.message
        return None

    def columnas(self, tabla: str, dataset: str = MASTER) -> list[tuple[str, str]]:
        try:
            esquema = self.cliente.get_table(self._tabla(dataset, tabla)).schema
        except NotFound:
            return []
        tipos = {"INTEGER": "INT64", "FLOAT": "FLOAT64", "BOOLEAN": "BOOL"}
        return [(c.name, tipos.get(c.field_type, c.field_type)) for c in esquema]

    # ── escritura ───────────────────────────────────────────────────────────

    def _destino(self, dataset: str, tabla: str, corte: date | None, primero: bool, config) -> str:
        if dataset not in ESCRIBIBLES:
            raise PermissionError(f"el flujo no escribe en {dataset}")
        destino = self._tabla(dataset, tabla)
        existe = bool(self.columnas(tabla, dataset))
        if corte is None:
            config.write_disposition = "WRITE_TRUNCATE"
            return destino
        if self.sandbox:
            config.clustering_fields = ["fecha_corte"]
            config.write_disposition = "WRITE_TRUNCATE" if primero else "WRITE_APPEND"
        else:
            config.time_partitioning = bigquery.TimePartitioning(field="fecha_corte")
            config.write_disposition = "WRITE_TRUNCATE" if existe else "WRITE_APPEND"
            if existe:
                destino = f"{destino}${corte:%Y%m%d}"
        if existe and config.write_disposition == "WRITE_APPEND" or "$" in destino:
            config.schema_update_options = [bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION]
        return destino

    def escribir(self, dataset: str, tabla: str, datos: pa.Table, corte: date | None, primero: bool = False) -> int:
        config = bigquery.LoadJobConfig(source_format=bigquery.SourceFormat.PARQUET)
        destino = self._destino(dataset, tabla, corte, primero, config)
        buffer = io.BytesIO()
        pq.write_table(datos, buffer)
        buffer.seek(0)
        self.cliente.load_table_from_file(buffer, destino, job_config=config).result()
        return datos.num_rows

    def materializar(self, sql_bigquery: str, dataset: str, tabla: str, corte: date | None, primero: bool = False) -> int:
        config = self._config()
        config.destination = self._destino(dataset, tabla, corte, primero, config)
        return self.cliente.query(sql_bigquery, job_config=config).result().total_rows

    def agregar(
        self, dataset: str, tabla: str, filas: list[dict], esquema: list[tuple[str, str]], _guardian: bool = True
    ) -> None:
        if not filas:
            return
        if _guardian and dataset not in ESCRIBIBLES:
            raise PermissionError(f"el flujo no escribe en {dataset}")
        config = bigquery.LoadJobConfig(
            schema=[bigquery.SchemaField(n, t) for n, t in esquema],
            write_disposition="WRITE_APPEND",
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        )
        filas = [{k: _json(v) for k, v in f.items()} for f in filas]
        self.cliente.load_table_from_json(filas, self._tabla(dataset, tabla), job_config=config).result()
