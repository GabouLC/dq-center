"""El flujo de un corte: ingesta -> homologación y Privacy Gate -> motor de calidad."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dqc.modelo import ESQUEMAS, MASTER, RAW
from dqc.motor.motor import Ejecucion, Motor, guardar_ejecucion
from dqc.motor.reglas import Regla
from dqc.pipeline.configuracion import Fuente, cifrados
from dqc.pipeline.homologacion import sql_homologacion
from dqc.pipeline.ingesta import EXITOSA, Carga, Entrega, validar_csv


@dataclass
class ResultadoCorte:
    fecha_corte: date
    cargas: list[Carga]
    incidencias: list[dict]
    ejecucion: Ejecucion


class Flujo:
    def __init__(
        self,
        plataforma,
        fuentes: dict[str, Fuente],
        contratos: dict[str, dict],
        reglas: list[Regla],
        landing: Path,
        hilos: int = 1,
    ):
        self.plataforma = plataforma
        self.fuentes = fuentes
        self.cifrados = cifrados(contratos)
        self.landing = landing
        self.motor = Motor(plataforma, reglas, hilos=hilos, cifrados=self.cifrados)

    def _ingerir(self, entregas: list[Entrega], corte: date, primero: bool) -> tuple[list[Carga], dict[str, Carga]]:
        cargas, aceptadas = [], {}
        for entrega in entregas:
            fuente = self.fuentes[entrega.tabla]
            carga = validar_csv(self.landing, entrega, fuente)
            if carga.estado == EXITOSA:
                self.plataforma.escribir(RAW, fuente.archivo, carga.datos, corte, primero)
                aceptadas[entrega.tabla] = carga  # si llegan dos válidas, vale la última
            self.plataforma.agregar(RAW, "registro_cargas", [carga.registro()], ESQUEMAS["registro_cargas"])
            cargas.append(carga)
        return cargas, aceptadas

    def _homologar(self, aceptadas: dict[str, Carga], corte: date, primero: bool) -> list[dict]:
        incidencias = []
        for tabla, carga in aceptadas.items():
            fuente = self.fuentes[tabla]
            columnas_raw = {c for c, _ in self.plataforma.columnas(fuente.archivo, RAW)}
            sql = sql_homologacion(
                fuente, corte, carga.entrega.nombre, columnas_raw, self.plataforma.funciones, self.cifrados.get(tabla, {})
            )
            self.plataforma.materializar(sql.master, MASTER, tabla, corte if fuente.por_corte else None, primero)
            nuevas = self.plataforma.consultar(sql.incidencias)
            self.plataforma.agregar(MASTER, "incidencias_homologacion", nuevas, ESQUEMAS["incidencias_homologacion"])
            incidencias += nuevas
        return incidencias

    def procesar_corte(
        self, corte: date, entregas: list[Entrega], primero: bool = False, origen: str = "simulacion"
    ) -> ResultadoCorte:
        """Procesa las entregas de un corte (en orden de llegada) y corre el motor."""
        del_corte = [e for e in entregas if e.fecha_corte == corte]
        cargas, aceptadas = self._ingerir(del_corte, corte, primero)
        incidencias = self._homologar(aceptadas, corte, primero)
        ejecucion = self.motor.ejecutar(corte, origen)
        guardar_ejecucion(self.plataforma, ejecucion)
        return ResultadoCorte(corte, cargas, incidencias, ejecucion)
