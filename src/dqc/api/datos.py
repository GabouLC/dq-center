"""Lectura de resultados para el portal, solo desde las vistas de contrato de BUSINESS.

El portal nunca consulta RAW ni MASTER (restricción del caso de negocio). Los
resultados son pocos (decenas de filas por corrida), así que las vistas se leen
completas, en paralelo, y quedan 10 minutos en memoria. Solo cambian cuando hay
una corrida nueva, y lanzar una corrida invalida el caché. Así cada sección
responde muy por debajo de los 8 s de HU-15, también sobre BigQuery.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from dqc.modelo import BUSINESS
from dqc.sql_util import fecha, literal

CONSULTAS = {
    "ejecuciones": f"SELECT * FROM {BUSINESS}.v_calidad_ejecuciones",
    "resultados": f"SELECT * FROM {BUSINESS}.v_calidad_resultados",
    "certificaciones": f"SELECT * FROM {BUSINESS}.v_calidad_certificaciones",
    "hallazgos": f"SELECT * FROM {BUSINESS}.v_calidad_hallazgos_privacidad",
    "esquemas": f"SELECT * FROM {BUSINESS}.v_calidad_esquemas",
    "cargas": f"SELECT * FROM {BUSINESS}.v_calidad_cargas",
    "incidencias": (
        f"SELECT fecha_corte, tabla, COUNT(*) AS registros FROM {BUSINESS}.v_calidad_incidencias GROUP BY 1, 2"
    ),
}


class FuenteBusiness:
    def __init__(self, plataforma, vigencia: float = 600):
        self.plataforma = plataforma
        self.vigencia = vigencia
        self._datos: dict[str, list[dict]] = {}
        self._vence = 0.0
        self._lock = threading.Lock()

    def precargar(self) -> None:
        """Lee todas las vistas a la vez: el tiempo total es el de la consulta más lenta."""
        with ThreadPoolExecutor(len(CONSULTAS)) as pool:
            leidas = dict(zip(CONSULTAS, pool.map(self.plataforma.consultar, CONSULTAS.values())))
        with self._lock:
            self._datos = leidas
            self._vence = time.monotonic() + self.vigencia

    def invalidar(self) -> None:
        with self._lock:
            self._vence = 0.0

    def _vista(self, nombre: str) -> list[dict]:
        with self._lock:
            vigente = self._vence > time.monotonic()
        if not vigente:
            self.precargar()
        return self._datos[nombre]

    def ejecuciones(self) -> list[dict]:
        return self._vista("ejecuciones")

    def resultados(self) -> list[dict]:
        return self._vista("resultados")

    def certificaciones(self) -> list[dict]:
        return self._vista("certificaciones")

    def hallazgos(self) -> list[dict]:
        return self._vista("hallazgos")

    def esquemas(self) -> list[dict]:
        return self._vista("esquemas")

    def cargas(self) -> list[dict]:
        return self._vista("cargas")

    def incidencias_por_corte(self) -> list[dict]:
        return self._vista("incidencias")

    def incidencias(self, tabla: str, corte: date, limite: int) -> list[dict]:
        return self.plataforma.consultar(
            f"SELECT llave, archivo, columnas, valores FROM {BUSINESS}.v_calidad_incidencias "
            f"WHERE tabla = {literal(tabla)} AND fecha_corte = {fecha(corte)} ORDER BY llave LIMIT {int(limite)}"
        )

    def fallidos(self, id_ejecucion: str, id_regla: str, tabla: str, limite: int) -> tuple[int, list[dict]]:
        """Una sola consulta: la muestra y el total (COUNT(*) OVER () se calcula antes del LIMIT)."""
        filas = self.plataforma.consultar(
            f"SELECT llave, detalle, COUNT(*) OVER () AS total FROM {BUSINESS}.v_calidad_fallidos "
            f"WHERE id_ejecucion = {literal(id_ejecucion)} AND id_regla = {literal(id_regla)} AND tabla = {literal(tabla)} "
            f"ORDER BY detalle IS NULL, llave LIMIT {int(limite)}"
        )
        return (int(filas[0]["total"]) if filas else 0), filas
