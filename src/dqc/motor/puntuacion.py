"""Estados y scores: cumplimiento por regla, ponderado por severidad."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from dqc.modelo import PESO_SEVERIDAD

MARGEN_ALERTA = 2.0


def cumplimiento(universo: int, cumplen: int) -> float | None:
    """% de filas que cumplen; None si el universo está vacío ("sin datos")."""
    return None if universo == 0 else cumplen / universo * 100


def estado(valor: float | None, umbral: float) -> str:
    if valor is None:
        return "SIN_DATOS"
    if valor >= umbral:
        return "OK"
    if valor >= umbral - MARGEN_ALERTA:
        return "ALERTA"
    return "FALLA"


@dataclass
class ResultadoRegla:
    id_regla: str
    tabla: str
    dimension: str
    severidad: str
    tipo: str
    umbral: float
    fecha_corte: date
    universo: int
    cumplen: int
    fallidos: list[str]

    @property
    def cumplimiento(self) -> float | None:
        return cumplimiento(self.universo, self.cumplen)

    @property
    def estado(self) -> str:
        return estado(self.cumplimiento, self.umbral)


def _promedio_ponderado(resultados: list[ResultadoRegla]) -> float | None:
    con_datos = [r for r in resultados if r.cumplimiento is not None]
    peso = sum(PESO_SEVERIDAD[r.severidad] for r in con_datos)
    if peso == 0:
        return None
    return sum(r.cumplimiento * PESO_SEVERIDAD[r.severidad] for r in con_datos) / peso


@dataclass
class Scores:
    global_: float | None
    por_tabla: dict[str, float | None]
    por_dimension: dict[tuple[str, str], float | None]  # (tabla, dimensión)


def scores(resultados: list[ResultadoRegla]) -> Scores:
    """Scores de un corte. El global es el promedio simple de las tablas con datos."""
    por_tabla: dict[str, list[ResultadoRegla]] = defaultdict(list)
    por_dimension: dict[tuple[str, str], list[ResultadoRegla]] = defaultdict(list)
    for r in resultados:
        por_tabla[r.tabla].append(r)
        por_dimension[r.tabla, r.dimension].append(r)
    tablas = {t: _promedio_ponderado(rs) for t, rs in por_tabla.items()}
    con_datos = [v for v in tablas.values() if v is not None]
    return Scores(
        global_=sum(con_datos) / len(con_datos) if con_datos else None,
        por_tabla=tablas,
        por_dimension={k: _promedio_ponderado(rs) for k, rs in por_dimension.items()},
    )
