"""Evalúa las reglas activas en un corte y arma la ejecución."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from dqc.modelo import TABLAS_CORTE
from dqc.motor.backends import Backend
from dqc.motor.puntuacion import ResultadoRegla
from dqc.motor.reglas import Regla, expandir
from dqc.motor.sql import sql_muestra, sql_regla


@dataclass
class Ejecucion:
    id_ejecucion: str
    fecha_corte: date
    origen: str
    iniciada_en: datetime
    terminada_en: datetime | None = None
    resultados: list[ResultadoRegla] = field(default_factory=list)
    # tabla -> [(columna, tipo)] tal como estaba al correr
    esquemas: dict[str, list[tuple[str, str]]] = field(default_factory=dict)


class Motor:
    def __init__(self, backend: Backend, reglas: list[Regla], hilos: int = 1, muestras: int = 20):
        self.backend = backend
        self.reglas = [r for r in expandir(reglas) if r.activa]
        self.hilos = hilos
        self.muestras = muestras

    def _evaluar_regla(self, regla: Regla, corte: date) -> ResultadoRegla:
        fila = self.backend.consultar(sql_regla(regla, corte))[0]
        resultado = ResultadoRegla(
            id_regla=regla.id,
            tabla=regla.tabla,
            dimension=regla.dim,
            severidad=regla.sev,
            tipo=regla.tipo,
            umbral=float(regla.umbral),
            fecha_corte=corte,
            universo=int(fila["universo"]),
            # Con universo vacío DuckDB devuelve NULL donde BigQuery devuelve 0.
            cumplen=int(fila["cumplen"] or 0),
            fallidos=list(fila["fallidos"] or []),
        )
        if resultado.fallidos and self.muestras and not regla.es_de_tabla:
            llaves = resultado.fallidos[: self.muestras]
            resultado.muestra = {
                f["llave"]: f["detalle"] for f in self.backend.consultar(sql_muestra(regla, corte, llaves))
            }
        return resultado

    def ejecutar(self, corte: date, origen: str = "manual") -> Ejecucion:
        ejecucion = Ejecucion(
            id_ejecucion=uuid.uuid4().hex,
            fecha_corte=corte,
            origen=origen,
            iniciada_en=datetime.now(timezone.utc),
        )
        if self.hilos > 1:
            with ThreadPoolExecutor(self.hilos) as pool:
                ejecucion.resultados = list(pool.map(lambda r: self._evaluar_regla(r, corte), self.reglas))
        else:
            ejecucion.resultados = [self._evaluar_regla(r, corte) for r in self.reglas]
        ejecucion.esquemas = {t: self.backend.columnas(t) for t in TABLAS_CORTE}
        ejecucion.terminada_en = datetime.now(timezone.utc)
        return ejecucion


def filas_de_ejecucion(e: Ejecucion) -> dict[str, list[dict]]:
    """Filas de las tablas de dq_engine (ejecuciones, resultados, fallidos, esquemas)."""
    base = {"id_ejecucion": e.id_ejecucion, "fecha_corte": e.fecha_corte}
    return {
        "ejecuciones": [{
            **base, "origen": e.origen, "iniciada_en": e.iniciada_en,
            "terminada_en": e.terminada_en, "reglas": len(e.resultados),
        }],
        "resultados": [
            {
                **base, "id_regla": r.id_regla, "tabla": r.tabla, "dimension": r.dimension,
                "severidad": r.severidad, "tipo": r.tipo, "umbral": r.umbral, "universo": r.universo,
                "cumplen": r.cumplen, "cumplimiento": r.cumplimiento, "estado": r.estado,
            }
            for r in e.resultados
        ],
        "fallidos": [
            {**base, "id_regla": r.id_regla, "tabla": r.tabla, "llave": llave, "detalle": r.muestra.get(llave)}
            for r in e.resultados
            for llave in r.fallidos
        ],
        "esquemas": [
            {**base, "tabla": tabla, "posicion": i, "columna": columna, "tipo": tipo}
            for tabla, columnas in e.esquemas.items()
            for i, (columna, tipo) in enumerate(columnas, start=1)
        ],
    }


def comparar_con_manifiesto(
    ejecuciones: list[Ejecucion], manifiesto: list[dict]
) -> tuple[set[tuple], set[tuple]]:
    """(faltantes, sobrantes): errores sembrados que el motor no vio y fallidos que no estaban sembrados."""
    detectados = {
        (r.id_regla, r.tabla, r.fecha_corte, llave)
        for e in ejecuciones
        for r in e.resultados
        for llave in r.fallidos
    }
    cortes = {e.fecha_corte for e in ejecuciones}
    esperados = {
        (m["id_regla"], m["tabla"], m["fecha_corte"], m["llave"])
        for m in manifiesto
        if m["fecha_corte"] in cortes
    }
    return esperados - detectados, detectados - esperados
