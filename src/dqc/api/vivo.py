"""Simulación en vivo: las entregas pendientes llegan una por una mientras la API corre.

El pipeline deja procesados los cortes hasta una fecha (python -m dqc.pipeline --hasta)
y el resto queda en la zona de aterrizaje. Cada pocos segundos llega el siguiente
archivo: se valida y se carga en RAW. Cuando llegan todos los del día, el corte se
homologa, el motor lo evalúa, el Gate lo certifica y se publica en BUSINESS. Cada
paso queda como un evento que el portal muestra en su actividad.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from datetime import date, datetime, timezone
from pathlib import Path

from dqc.modelo import BUSINESS, CORTES, NO_CERTIFICADO
from dqc.motor.reglas import desde_documento
from dqc.pipeline.flujo import Flujo
from dqc.pipeline.ingesta import EXITOSA, Carga, Entrega, leer_entregas

log = logging.getLogger("dqc.vivo")

NOMBRE_TABLA = {"persona": "Persona", "poliza": "Póliza", "vehiculo": "Vehículo", "siniestro": "Siniestro", "pago": "Pago"}
GRAVEDAD = {"OK": 0, "SIN_DATOS": 0, "ALERTA": 1, "FALLA": 2}


class Simulador:
    def __init__(self, plataforma, config, fuentes, landing: Path, intervalo: float,
                 candado: threading.RLock, al_cerrar_corte: Callable[[], None]):
        self.plataforma = plataforma
        self.config = config
        self.fuentes = fuentes
        self.landing = landing
        self.intervalo = intervalo
        self.candado = candado
        self.al_cerrar_corte = al_cerrar_corte
        self.eventos: deque[dict] = deque(maxlen=300)
        self.version = 0
        self.pausado = False
        self._siguiente = 0
        self._proxima = time.monotonic() + intervalo
        self._despertar = threading.Event()
        self._pendientes: list[Entrega] = []
        self._aceptadas: dict[str, Carga] = {}
        self._corte: date | None = None
        self._estados: dict[tuple[str, str], str] = {}
        self._ultimo: date | None = None

    # ── estado para el portal ──────────────────────────────────────────────

    def estado(self, desde: int = 0) -> dict:
        en_curso = [e for e in self._pendientes if e.fecha_corte == self._corte] if self._corte else []
        return {
            "activo": True,
            "pausado": self.pausado,
            "intervalo": self.intervalo,
            "proximo_en": max(0.0, round(self._proxima - time.monotonic(), 1)) if self._pendientes else None,
            "ultimo_corte": self._ultimo,
            "corte_en_curso": self._corte,
            "archivos_recibidos": len(self._aceptadas),
            "archivos_pendientes": len(en_curso),
            "dias_pendientes": len({e.fecha_corte for e in self._pendientes}),
            "version": self.version,
            "eventos": [e for e in self.eventos if e["id"] > desde][-60:],
        }

    def pausar(self, pausado: bool) -> None:
        self.pausado = pausado
        self._evento("info", "Simulación en pausa" if pausado else "Simulación reanudada", None, None, None)

    def adelantar(self) -> None:
        """Hace llegar el siguiente archivo ahora (para la demo)."""
        self._proxima = time.monotonic()
        self._despertar.set()

    # ── ciclo ──────────────────────────────────────────────────────────────

    def iniciar(self) -> None:
        if self.preparar():
            threading.Thread(target=self._bucle, name="dqc-vivo", daemon=True).start()

    def preparar(self) -> bool:
        """Busca las entregas posteriores al último corte evaluado. False si no hay nada procesado."""
        procesados = self.plataforma.consultar(f"SELECT MAX(fecha_corte) AS corte FROM {BUSINESS}.v_calidad_ejecuciones")
        self._ultimo = procesados[0]["corte"] if procesados else None
        if self._ultimo is None:
            log.warning("simulación en vivo: no hay cortes procesados; corre primero dqc.pipeline")
            return False
        self._pendientes = [e for e in leer_entregas(self.landing) if e.fecha_corte > self._ultimo and e.fecha_corte in CORTES]
        filas = self.plataforma.consultar(
            f"SELECT id_regla, tabla, estado FROM {BUSINESS}.v_calidad_resultados WHERE fecha_corte = DATE '{self._ultimo}'"
        )
        self._estados = {(f["id_regla"], f["tabla"]): f["estado"] for f in filas}
        dias = len({e.fecha_corte for e in self._pendientes})
        self._evento("info", "Monitoreo en vivo iniciado",
                     f"Último corte evaluado: {self._ultimo}. Quedan {dias} días por llegar." if dias else
                     f"Último corte evaluado: {self._ultimo}. No hay entregas pendientes.", None, None)
        return True

    def _bucle(self) -> None:
        while self._pendientes:
            espera = self._proxima - time.monotonic()
            if espera > 0:
                self._despertar.wait(espera)
                self._despertar.clear()
                continue
            if self.pausado:
                self._proxima = time.monotonic() + 1
                continue
            try:
                self._llega_un_archivo()
            except Exception:  # noqa: BLE001 - la simulación no debe tumbar la API
                log.exception("error en la simulación en vivo")
                self._evento("critico", "Error en la simulación", "Revisa el log de la API.", None, None)
            self._proxima = time.monotonic() + self.intervalo
        self._evento("bien", "Todo al día", f"Se procesaron todas las entregas hasta {self._ultimo}.", None, self._ultimo)

    def _flujo(self) -> Flujo:
        reglas = [desde_documento(d) for d in self.config.reglas()]
        return Flujo(self.plataforma, self.fuentes, self.config.contratos(), reglas, self.landing)

    def _llega_un_archivo(self) -> None:
        entrega = self._pendientes.pop(0)
        if entrega.fecha_corte != self._corte:
            self._corte, self._aceptadas = entrega.fecha_corte, {}
        flujo = self._flujo()
        with self.candado:
            (carga,), aceptadas = flujo.ingerir([entrega], entrega.fecha_corte, primero=False)
        self._aceptadas.update(aceptadas)
        tabla = NOMBRE_TABLA.get(entrega.tabla, entrega.tabla)
        if carga.estado == EXITOSA:
            self._evento("info", f"Llegó {entrega.nombre}", f"{tabla} · {carga.filas:,} filas cargadas en RAW",
                         entrega.tabla, entrega.fecha_corte, "carga")
        else:
            self._evento("critico", f"Archivo rechazado: {entrega.nombre}", f"{tabla} · {carga.detalle}",
                         entrega.tabla, entrega.fecha_corte, "carga")
        if not any(e.fecha_corte == self._corte for e in self._pendientes):
            self._cerrar_corte(flujo, self._corte)

    def _cerrar_corte(self, flujo: Flujo, corte: date) -> None:
        with self.candado:
            incidencias = flujo.homologar(self._aceptadas, corte, primero=False)
            ejecucion, certificaciones = flujo.evaluar(corte, origen="en_vivo")
        self._ultimo, self._corte, self._aceptadas = corte, None, {}
        self.version += 1
        self.al_cerrar_corte()

        if incidencias:
            tablas = sorted({NOMBRE_TABLA[i["tabla"]] for i in incidencias})
            self._evento("aviso", f"{len(incidencias)} registros no se pudieron homologar",
                         f"{', '.join(tablas)}: quedan fuera de MASTER como incidencias", None, corte)
        estados = [r.estado for r in ejecucion.resultados]
        en_pass = sum(e == "OK" for e in estados)
        self._evento("info", f"Motor de calidad: {en_pass} de {len(estados)} reglas en PASS",
                     f"{estados.count('ALERTA')} en alerta y {estados.count('FALLA')} en falla", None, corte, "motor")

        nuevos = {(r.id_regla, r.tabla): r.estado for r in ejecucion.resultados}
        for (regla, tabla), estado in sorted(nuevos.items()):
            antes = self._estados.get((regla, tabla))
            if antes is None or antes == estado or estado == "SIN_DATOS":
                continue
            if GRAVEDAD[estado] > GRAVEDAD.get(antes, 0):
                tono = "critico" if estado == "FALLA" else "aviso"
                self._evento(tono, f"{regla} empeoró: {antes} → {estado}", NOMBRE_TABLA[tabla], tabla, corte, "regla")
            else:
                self._evento("bien", f"{regla} se recuperó: {antes} → {estado}", NOMBRE_TABLA[tabla], tabla, corte, "regla")
        self._estados = nuevos

        for c in certificaciones:
            if c.estado == NO_CERTIFICADO:
                motivo = ", ".join(c.reglas_bloqueantes) or ", ".join(
                    sorted({f"{h.tipo} en {h.columna}" for h in c.hallazgos if h.bloqueante}))
                self._evento("critico", f"{NOMBRE_TABLA[c.tabla]} no certificada", f"Retenida por el Gate: {motivo}",
                             c.tabla, corte, "certificacion")
        publicadas = [NOMBRE_TABLA[c.tabla] for c in certificaciones if c.publicado]
        self._evento("bien", f"Corte {corte:%d/%m} certificado y publicado",
                     f"{len(publicadas)} de {len(certificaciones)} tablas en BUSINESS: {', '.join(publicadas)}",
                     None, corte, "certificacion")

    def _evento(self, tono: str, titulo: str, detalle: str | None, tabla: str | None, corte: date | None,
                tipo: str = "sistema") -> None:
        self._siguiente += 1
        self.eventos.append({
            "id": self._siguiente,
            "cuando": datetime.now(timezone.utc).isoformat(),
            "tipo": tipo,
            "tono": tono,
            "titulo": titulo,
            "detalle": detalle,
            "tabla": tabla,
            "fecha_corte": corte,
        })
