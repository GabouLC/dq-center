"""SQL de cada regla, en dialecto BigQuery.

Toda regla produce la misma forma de resultado: el universo (filas que entran
a la regla), cuántas cumplen y la lista de llaves que no cumplen. Las reglas
de fila usan el alias `t` para la tabla y `j` para el join; las de tabla
completa leen registro_cargas (solo cargas exitosas) y usan el nombre de la
tabla como llave.

Las tablas van sin dataset: la plataforma fija dq_master como dataset por
defecto. Si una regla usa campos cifrados (SENSIBLE_CIFRADO), la tabla se
envuelve en una subconsulta que descifra solo esos campos: el texto claro
existe únicamente dentro de la consulta del motor, nunca se guarda.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from dqc.modelo import LLAVES, RAW, TABLAS_CORTE
from dqc.motor.reglas import Regla
from dqc.pipeline.funciones import SQL_LLAVES
from dqc.sql_util import fecha, literal

REGISTRO = f"{RAW}.registro_cargas"


@dataclass
class ContextoSQL:
    """Lo que el SQL necesita saber de la plataforma para descifrar."""

    funciones: object | None = None
    cifrados: dict[str, dict[str, str]] = field(default_factory=dict)  # tabla -> campo -> modo
    columnas: dict[str, list[str]] = field(default_factory=dict)  # columnas actuales en MASTER

    def origen(self, tabla: str, usados: set[str]) -> str:
        """La tabla, o una subconsulta que descifra los campos cifrados que la regla usa."""
        modos = {c: m for c, m in self.cifrados.get(tabla, {}).items() if c in usados}
        if not modos or self.funciones is None:
            return tabla
        columnas = [
            f"{self.funciones.descifrar(f'x.{c}', modos[c], tabla, c)} AS {c}" if c in modos else f"x.{c}"
            for c in self.columnas[tabla]
        ]
        return f"(SELECT {', '.join(columnas)} FROM {tabla} AS x CROSS JOIN {SQL_LLAVES} AS k)"


SIN_CIFRADO = ContextoSQL()


def _resultado(universo_sql: str, ctes_previas: str = "") -> str:
    return f"""WITH {ctes_previas}universo AS (
{universo_sql}
)
SELECT
  (SELECT COUNT(*) FROM universo) AS universo,
  (SELECT COUNTIF(ok) FROM universo) AS cumplen,
  ARRAY(SELECT llave FROM universo WHERE NOT ok ORDER BY llave) AS fallidos"""


def _sql_fila(r: Regla, corte: date, ctx: ContextoSQL) -> str:
    condiciones = [f"t.fecha_corte = {fecha(corte)}"]
    if r.filtro:
        condiciones.append(f"({r.filtro})")
    join = ""

    if r.tipo == "no_nulo":
        cumple = " AND ".join(f"t.{c} IS NOT NULL" for c in r.campos)
    elif r.tipo == "al_menos_uno":
        cumple = " OR ".join(f"t.{c} IS NOT NULL" for c in r.campos)
    elif r.tipo == "unico":
        # Una llave con nulos no se puede comparar: de eso se encarga completitud.
        condiciones += [f"t.{c} IS NOT NULL" for c in r.campos]
        particion = ", ".join(f"t.{c}" for c in r.campos)
        cumple = f"COUNT(*) OVER (PARTITION BY {particion}) = 1"
    elif r.tipo == "regex":
        cumple = f"REGEXP_CONTAINS(t.{r.campo}, {literal(r.patron)})"
    elif r.tipo == "dominio":
        cumple = f"t.{r.campo} IN ({', '.join(literal(str(v)) for v in r.valores)})"
    elif r.tipo == "referencia":
        tabla_ref, _, columna_ref = r.ref.partition(".")
        en_ref = [f"r.{columna_ref} = t.{r.campo}"]
        if tabla_ref in TABLAS_CORTE:
            en_ref.append("r.fecha_corte = t.fecha_corte")
        if r.ref_filtro:
            en_ref.append(f"({r.ref_filtro})")
        cumple = f"EXISTS (SELECT 1 FROM {tabla_ref} AS r WHERE {' AND '.join(en_ref)})"
    elif r.tipo == "expresion":
        cumple = r.cumple
    else:
        raise ValueError(f"{r.id}: tipo de fila desconocido {r.tipo}")

    if r.join:
        tabla_j, llave_j = r.join["tabla"], r.join["llave"]
        where_j = f"WHERE fecha_corte = {fecha(corte)}" if tabla_j in TABLAS_CORTE else "WHERE TRUE"
        # Una fila por llave del lado del join, para no multiplicar el universo.
        join = (
            f"  LEFT JOIN (\n"
            f"    SELECT * FROM {tabla_j} {where_j}\n"
            f"    QUALIFY ROW_NUMBER() OVER (PARTITION BY {llave_j} ORDER BY {llave_j}) = 1\n"
            f"  ) AS j ON t.{llave_j} = j.{llave_j}\n"
        )

    universo = (
        f"  SELECT CAST(t.{LLAVES[r.tabla]} AS STRING) AS llave, COALESCE({cumple}, FALSE) AS ok\n"
        f"  FROM {ctx.origen(r.tabla, r.campos_usados())} AS t\n"
        f"{join}"
        f"  WHERE {' AND '.join(condiciones)}"
    )
    return _resultado(universo)


def limite_frescura_utc(r: Regla, corte: date) -> datetime:
    dias, hora, minuto, zona = r.limite_frescura()
    local = datetime.combine(corte + timedelta(days=dias), time(hora, minuto), ZoneInfo(zona))
    return local.astimezone(timezone.utc)


def _sql_tabla(r: Regla, corte: date) -> str:
    tabla = literal(r.tabla)
    exitosas = f"tabla = {tabla} AND estado = 'EXITOSA'"
    if r.tipo == "frescura":
        # Cuenta la primera carga exitosa, aunque luego se haya recargado.
        limite = limite_frescura_utc(r, corte).strftime("%Y-%m-%d %H:%M:%S+00")
        universo = (
            f"  SELECT {tabla} AS llave, COALESCE(MIN(cargado_en) <= TIMESTAMP '{limite}', FALSE) AS ok\n"
            f"  FROM {REGISTRO}\n"
            f"  WHERE {exitosas} AND fecha_corte = {fecha(corte)}\n"
            f"  HAVING COUNT(*) > 0"
        )
        return _resultado(universo)

    # Volumetría: filas de la última carga exitosa de cada corte.
    cargas = (
        f"cargas AS (\n"
        f"  SELECT fecha_corte, filas FROM {REGISTRO}\n"
        f"  WHERE {exitosas} AND fecha_corte <= {fecha(corte)}\n"
        f"  QUALIFY ROW_NUMBER() OVER (PARTITION BY fecha_corte ORDER BY cargado_en DESC) = 1\n"
        f"),\n"
    )
    if r.tipo == "minimo_filas":
        universo = (
            f"  SELECT {tabla} AS llave, COALESCE(filas >= {int(r.min)}, FALSE) AS ok\n"
            f"  FROM cargas WHERE fecha_corte = {fecha(corte)}"
        )
    elif r.tipo == "variacion_volumen":
        # Sin corte anterior el universo queda vacío: "sin datos".
        universo = (
            f"  SELECT {tabla} AS llave,\n"
            f"    COALESCE(ABS(CAST(a.filas AS FLOAT64) / p.filas - 1) * 100 <= {float(r.max_variacion_pct)}, FALSE) AS ok\n"
            f"  FROM (SELECT filas FROM cargas WHERE fecha_corte = {fecha(corte)}) AS a\n"
            f"  CROSS JOIN (\n"
            f"    SELECT filas FROM cargas WHERE fecha_corte < {fecha(corte)}\n"
            f"    ORDER BY fecha_corte DESC LIMIT 1\n"
            f"  ) AS p"
        )
    else:
        raise ValueError(f"{r.id}: tipo de tabla desconocido {r.tipo}")
    return _resultado(universo, cargas)


def sql_muestra(r: Regla, corte: date, llaves: list[str]) -> str:
    """Filas (en JSON) de algunas llaves fallidas. Se leen cifradas: la muestra no expone PII."""
    llave = LLAVES[r.tabla]
    return (
        f"SELECT CAST(t.{llave} AS STRING) AS llave, TO_JSON_STRING(t) AS detalle\n"
        f"FROM {r.tabla} AS t\n"
        f"WHERE t.fecha_corte = {fecha(corte)}\n"
        f"  AND CAST(t.{llave} AS STRING) IN ({', '.join(literal(v) for v in llaves)})"
    )


def sql_regla(r: Regla, corte: date, ctx: ContextoSQL = SIN_CIFRADO) -> str:
    """SQL (BigQuery) que evalúa una regla ya expandida en un corte."""
    if r.tabla == "*":
        raise ValueError(f"{r.id}: expande las reglas transversales antes de generar SQL")
    return _sql_tabla(r, corte) if r.es_de_tabla else _sql_fila(r, corte, ctx)
