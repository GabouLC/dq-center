"""Revisión de privacidad del Quality & Privacy Gate (HU-07).

Por cada tabla y corte de MASTER:
  CAMPO_SIN_CIFRAR        un campo SENSIBLE_CIFRADO no está guardado como BYTES     bloquea
  PII_EN_CLARO            un valor con forma de DNI, correo o celular aparece en
                          una columna de texto que no se cifra                     bloquea
  COLUMNA_SIN_CLASIFICAR  una columna que el contrato no conoce ni clasifica       observación
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from dqc.modelo import LLAVES, MASTER
from dqc.sql_util import fecha, literal

# Fragmentos con forma de PII dentro de un texto. \b evita falsos positivos
# dentro de códigos alfanuméricos (un VIN puede tener 8 dígitos seguidos).
PATRON_PII = r"\b\d{8}\b|\b9\d{8}\b|[^@\s]+@[^@\s]+\.[a-z]{2,}"


@dataclass(frozen=True)
class Hallazgo:
    tabla: str
    tipo: str
    columna: str
    bloqueante: bool
    llave: str | None = None


def columnas_del_corte(plataforma, tabla: str, corte: date, pactados: set[str]) -> list[tuple[str, str]]:
    """Columnas de la tabla en MASTER tal como llegaron en el corte.

    MASTER acumula columnas: una que llegó después (canal_venta) existe, vacía, en los cortes
    anteriores. Las del contrato cuentan siempre; las demás, solo si ese día traen datos.
    """
    columnas = plataforma.columnas(tabla, MASTER)
    extras = [c for c, _ in columnas if c not in pactados]
    if not extras:
        return columnas
    conteos = plataforma.consultar(
        "SELECT " + ", ".join(f"COUNT({c}) AS {c}" for c in extras)
        + f" FROM {MASTER}.{tabla} WHERE fecha_corte = {fecha(corte)}"
    )[0]
    return [(c, t) for c, t in columnas if c in pactados or conteos[c]]


def revisar(plataforma, tabla: str, corte: date, contrato: dict, cifrados_tabla: dict[str, str]) -> list[Hallazgo]:
    pactados = {c["nombre"] for c in contrato["campos"]}
    columnas = columnas_del_corte(plataforma, tabla, corte, pactados)
    tipos = dict(columnas)
    hallazgos = [
        Hallazgo(tabla, "CAMPO_SIN_CIFRAR", campo, True)
        for campo in cifrados_tabla
        if campo in tipos and tipos[campo] != "BYTES"
    ]
    hallazgos += [Hallazgo(tabla, "COLUMNA_SIN_CLASIFICAR", c, False) for c, _ in columnas if c not in pactados]

    texto = [c for c, tipo in columnas if tipo == "STRING" and c not in cifrados_tabla]
    if texto:
        patron = literal(PATRON_PII)
        marcas = ", ".join(f"IF(REGEXP_CONTAINS(t.{c}, {patron}), {literal(c + ' ')}, '')" for c in texto)
        alguna = " OR ".join(f"REGEXP_CONTAINS(t.{c}, {patron})" for c in texto)
        sql = (
            f"SELECT CAST(t.{LLAVES[tabla]} AS STRING) AS llave, CONCAT({marcas}) AS columnas\n"
            f"FROM {MASTER}.{tabla} AS t\n"
            f"WHERE t.fecha_corte = {fecha(corte)} AND ({alguna})"
        )
        for fila in plataforma.consultar(sql):
            for columna in fila["columnas"].split():
                hallazgos.append(Hallazgo(tabla, "PII_EN_CLARO", columna, True, fila["llave"]))
    return hallazgos
