"""Homologación RAW -> MASTER (HU-14) con el cifrado del Privacy Gate (HU-06).

Por cada fuente y corte genera dos consultas sobre el mismo paso de conversión:
  master       los registros convertidos al modelo estándar, con los campos
               SENSIBLE_CIFRADO ya cifrados: ninguna PII llega a MASTER en claro.
  incidencias  los registros con algún valor que no se pudo convertir al tipo
               destino; se registran y quedan fuera de MASTER.
No se corrige ningún valor (ni se recortan espacios): eso lo detecta el motor.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from dqc.modelo import RAW
from dqc.pipeline.configuracion import ColumnaFuente, Fuente
from dqc.pipeline.funciones import SQL_LLAVES
from dqc.sql_util import fecha, literal


def _valor(c: ColumnaFuente) -> str:
    # En el CSV un campo vacío es un nulo.
    return f"NULLIF(o.{c.origen}, '')"


def _convertir(c: ColumnaFuente, funciones) -> str:
    valor = _valor(c)
    if c.tipo in ("INT64", "FLOAT64"):
        return f"SAFE_CAST({valor} AS {c.tipo})"
    if c.tipo == "DATE":
        return funciones.parsear_fecha(valor, c.formato)
    if c.tipo == "BOOL":
        return f"CASE {valor} WHEN {literal(c.verdadero)} THEN TRUE WHEN {literal(c.falso)} THEN FALSE END"
    return valor


def _no_convertible(c: ColumnaFuente, funciones) -> str:
    return f"({_valor(c)} IS NOT NULL AND {_convertir(c, funciones)} IS NULL)"


@dataclass(frozen=True)
class SQLHomologacion:
    master: str
    incidencias: str


def sql_homologacion(
    fuente: Fuente,
    fecha_corte: date,
    archivo: str,
    columnas_raw: set[str],
    funciones,
    cifrados_tabla: dict[str, str],
) -> SQLHomologacion:
    """SQL (BigQuery) de la homologación de un archivo ya cargado en RAW."""
    en_raw = {c.upper() for c in columnas_raw}
    presentes = [c for c in fuente.columnas if c.origen.upper() in en_raw]  # las opcionales pueden faltar
    convertibles = [c for c in presentes if c.tipo != "STRING"]

    if convertibles:
        errores = "CONCAT(" + ", ".join(
            f"IF({_no_convertible(c, funciones)}, {literal(c.origen + ' ')}, '')" for c in convertibles
        ) + ")"
        valores = "CONCAT(" + ", ".join(
            f"IF({_no_convertible(c, funciones)}, CONCAT({literal(c.origen + '=')}, "
            f"{literal('***') if c.destino in cifrados_tabla else 'o.' + c.origen}, '; '), '')"
            for c in convertibles
        ) + ")"
    else:
        errores = valores = "''"

    convertido = (
        f"SELECT o.fecha_corte, o.archivo, o.{fuente.llave_origen} AS _llave, "
        + ", ".join(f"{_convertir(c, funciones)} AS {c.destino}" for c in presentes)
        + f", {errores} AS _errores, {valores} AS _valores\n"
        f"  FROM {RAW}.{fuente.archivo} AS o\n"
        f"  WHERE o.fecha_corte = {fecha(fecha_corte)} AND o.archivo = {literal(archivo)}"
    )

    salida = ["c.fecha_corte"] if fuente.por_corte else []
    for c in presentes:
        expresion = f"c.{c.destino}"
        if c.destino in cifrados_tabla:
            expresion = funciones.cifrar(expresion, cifrados_tabla[c.destino], fuente.tabla, c.destino)
        salida.append(f"{expresion} AS {c.destino}")
    llaves = f" CROSS JOIN {SQL_LLAVES} AS k" if any(c.destino in cifrados_tabla for c in presentes) else ""

    master = (
        f"WITH convertido AS (\n  {convertido}\n)\n"
        f"SELECT {', '.join(salida)}\n"
        f"FROM convertido AS c{llaves}\n"
        f"WHERE c._errores = ''"
    )
    incidencias = (
        f"WITH convertido AS (\n  {convertido}\n)\n"
        f"SELECT c.fecha_corte, {literal(fuente.tabla)} AS tabla, c.archivo, c._llave AS llave,\n"
        f"  TRIM(c._errores) AS columnas, c._valores AS valores\n"
        f"FROM convertido AS c\n"
        f"WHERE c._errores != ''"
    )
    return SQLHomologacion(master=master, incidencias=incidencias)
