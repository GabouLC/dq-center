"""Literales de SQL en dialecto BigQuery, compartidos por el motor y el flujo."""

from datetime import date

import sqlglot


def literal(valor: str) -> str:
    """Literal de texto escapado para BigQuery (las barras invertidas se duplican)."""
    return sqlglot.exp.Literal.string(valor).sql(dialect="bigquery")


def fecha(d: date) -> str:
    return f"DATE '{d.isoformat()}'"
