"""Lectura de resultados para el portal, solo desde las vistas de contrato de BUSINESS.

El portal nunca consulta RAW ni MASTER (restricción del caso de negocio). Los
resultados son pocos (decenas de filas por corrida), así que las vistas se leen
completas, en paralelo, y quedan 10 minutos en memoria. Solo cambian cuando hay
una corrida nueva, y lanzar una corrida invalida el caché. Así cada sección
responde muy por debajo de los 8 s de HU-15, también sobre BigQuery.

Al vencer los 10 minutos nadie espera: se sigue respondiendo con lo último leído mientras
una sola petición renueva en segundo plano. Una corrida nueva (invalidar) sí obliga a
esperar datos nuevos, porque no se puede mostrar el corte anterior como si fuera el último.
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from datetime import date

from dqc.modelo import BUSINESS
from dqc.sql_util import fecha, literal

log = logging.getLogger(__name__)

REINTENTO_S = 30  # si una renovación en segundo plano falla, se vuelve a intentar pasado este plazo

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
    def __init__(self, plataforma, vigencia: float = 600, candado: threading.RLock | None = None):
        self.plataforma = plataforma
        # Con la simulación en vivo, no leer mientras un corte se está publicando.
        self.candado = candado or nullcontext()
        self.vigencia = vigencia
        self._datos: dict[str, list[dict]] = {}
        self._vence = 0.0
        self._generacion = 0  # sube con cada invalidación: una lectura empezada antes no queda vigente
        self._generacion_leida = 0  # la generación que había cuando se empezó a leer lo que hay en _datos
        self._lock = threading.Lock()
        self._renovando = threading.Lock()  # una sola petición renueva; las demás esperan o reutilizan

    def precargar(self) -> None:
        """Lee todas las vistas a la vez: el tiempo total es el de la consulta más lenta.

        Una lectura a la vez: si otra está en curso (el arranque o una renovación), espera y no repite las consultas;
        si al terminar ya hay datos vigentes, no lee de nuevo.
        """
        with self._renovando:
            if not self._vigente():
                self._leer()

    def _leer(self) -> None:
        with self._lock:
            generacion = self._generacion
        with self.candado, ThreadPoolExecutor(len(CONSULTAS)) as pool:
            leidas = dict(zip(CONSULTAS, pool.map(self.plataforma.consultar, CONSULTAS.values())))
        with self._lock:
            self._datos = leidas
            self._generacion_leida = generacion
            # Si se invalidó mientras se leía (un corte recién publicado), esta lectura puede ser vieja.
            self._vence = time.monotonic() + self.vigencia if generacion == self._generacion else 0.0

    def invalidar(self) -> None:
        with self._lock:
            self._generacion += 1
            self._vence = 0.0

    def _vigente(self) -> bool:
        with self._lock:
            return self._vence > time.monotonic()

    def _renovar_aparte(self) -> None:
        """Renueva las vistas en un hilo, con una sola renovación a la vez; quien llega mientras tanto no espera."""
        if not self._renovando.acquire(blocking=False):
            return

        def trabajo() -> None:
            try:
                self._leer()
            except Exception:
                log.warning("no se pudieron renovar las vistas de contrato; se sigue con las últimas leídas", exc_info=True)
                # Sin esto, cada petición lanzaría otra renovación fallida: se reintenta recién pasado este plazo.
                with self._lock:
                    if self._generacion_leida == self._generacion:
                        self._vence = time.monotonic() + REINTENTO_S
            finally:
                self._renovando.release()

        threading.Thread(target=trabajo, daemon=True, name="renovar-vistas").start()

    def _vista(self, nombre: str) -> list[dict]:
        with self._lock:
            vigente = self._vence > time.monotonic()
            # Vencida solo por el tiempo (nadie invalidó desde que se leyó): lo último leído sirve un rato más.
            vieja_sirve = bool(self._datos) and self._generacion_leida == self._generacion
        if not vigente:
            if vieja_sirve:
                # Al vencer la caché, 10 usuarios a la vez esperaban 8,6 s sobre BigQuery (HU-15): ahora nadie espera.
                self._renovar_aparte()
            else:
                # Sin datos todavía, o un corte nuevo acaba de publicarse: hay que esperar datos nuevos, pero una sola
                # petición los lee (antes, N peticiones leían las 7 vistas N veces: en BigQuery, N × 7 consultas).
                with self._renovando:
                    if not self._vigente():
                        self._leer()
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
