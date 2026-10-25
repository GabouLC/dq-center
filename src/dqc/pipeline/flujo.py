"""El flujo de un corte, como una tubería de etapas (Pipes and Filters):

  ingesta -> homologación + cifrado -> motor de calidad -> revisión de privacidad
          -> certificación -> publicación en BUSINESS -> evidencia en dq_engine
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dqc.modelo import CORTES, ENGINE, ESQUEMAS, MASTER, RAW, TABLAS_CORTE
from dqc.motor.certificacion import Certificacion, certificar, version_reglas
from dqc.motor.motor import Ejecucion, Motor, guardar_ejecucion
from dqc.motor.reglas import Regla
from dqc.pipeline.configuracion import Fuente, cifrados
from dqc.pipeline.homologacion import sql_homologacion
from dqc.pipeline.ingesta import EXITOSA, Carga, Entrega, validar_csv
from dqc.pipeline.privacidad import columnas_del_corte, revisar
from dqc.pipeline.publicacion import preparar_almacen, publicar


def cortes_por_procesar(plataforma, desde: date | None, cortes: list[date] = CORTES) -> list[date]:
    """Todos los cortes, o los que faltan si se reanuda desde `desde`.

    Para reanudar, cada corte anterior a `desde` tiene que estar evaluado; si no, quedaría un hueco.
    """
    if desde is None:
        return list(cortes)
    if desde not in cortes:
        raise ValueError(f"{desde} no es un corte: van del {cortes[0]} al {cortes[-1]}")
    evaluados = set()
    if plataforma.columnas("ejecuciones", ENGINE):
        filas = plataforma.consultar(f"SELECT DISTINCT fecha_corte FROM {ENGINE}.ejecuciones")
        evaluados = {f["fecha_corte"] for f in filas}
    faltan = [c for c in cortes if c < desde and c not in evaluados]
    if faltan:
        raise ValueError(f"no se puede reanudar desde el {desde}: el {faltan[0]} no está evaluado")
    return [c for c in cortes if c >= desde]


@dataclass
class ResultadoCorte:
    fecha_corte: date
    cargas: list[Carga]
    incidencias: list[dict]
    ejecucion: Ejecucion
    certificaciones: list[Certificacion]


class Flujo:
    def __init__(
        self,
        plataforma,
        fuentes: dict[str, Fuente],
        contratos: dict[str, dict],
        reglas: list[Regla],
        landing: Path | None = None,
        hilos: int = 1,
    ):
        self.plataforma = plataforma
        self.fuentes = fuentes
        self.contratos = contratos
        self.cifrados = cifrados(contratos)
        self.landing = landing
        self.motor = Motor(plataforma, reglas, hilos=hilos, cifrados=self.cifrados)
        self.version_reglas = version_reglas(reglas)

    def preparar(self) -> None:
        preparar_almacen(self.plataforma)

    def ingerir(self, entregas: list[Entrega], corte: date, primero: bool) -> tuple[list[Carga], dict[str, Carga]]:
        """Valida y carga en RAW las entregas de un corte; devuelve todas las cargas y las aceptadas por tabla."""
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

    def homologar(self, aceptadas: dict[str, Carga], corte: date, primero: bool) -> list[dict]:
        """RAW -> MASTER con cifrado; devuelve las incidencias de los registros que no se pudieron homologar."""
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

    def evaluar(self, corte: date, origen: str, primero: bool = False) -> tuple[Ejecucion, list[Certificacion]]:
        """Motor + Quality & Privacy Gate + publicación de lo certificado, con su evidencia."""
        ejecucion = self.motor.ejecutar(corte, origen)
        for tabla in TABLAS_CORTE:  # la estructura de cada tabla tal como llegó ese día
            pactados = {c["nombre"] for c in self.contratos[tabla]["campos"]}
            ejecucion.esquemas[tabla] = columnas_del_corte(self.plataforma, tabla, corte, pactados)
        hallazgos = [
            h
            for tabla in TABLAS_CORTE
            for h in revisar(self.plataforma, tabla, corte, self.contratos[tabla], self.cifrados.get(tabla, {}))
        ]
        certificaciones = certificar(ejecucion, hallazgos, self.version_reglas)
        publicar(self.plataforma, certificaciones, corte, primero)
        base = {"id_ejecucion": ejecucion.id_ejecucion, "fecha_corte": corte}
        guardar_ejecucion(self.plataforma, ejecucion, {
            "certificaciones": [
                {
                    **base, "tabla": c.tabla, "dominio": c.dominio, "estado": c.estado,
                    "calidad_ok": c.calidad_ok, "privacidad_ok": c.privacidad_ok,
                    "reglas_bloqueantes": ",".join(c.reglas_bloqueantes),
                    "reglas_con_observacion": ",".join(c.reglas_con_observacion),
                    "hallazgos": len(c.hallazgos), "cobertura": c.cobertura, "publicado": c.publicado,
                    "version_motor": c.version_motor, "version_reglas": c.version_reglas,
                    "certificado_en": c.certificado_en,
                }
                for c in certificaciones
            ],
            "hallazgos_privacidad": [
                {**base, "tabla": h.tabla, "tipo": h.tipo, "columna": h.columna, "llave": h.llave, "bloqueante": h.bloqueante}
                for h in hallazgos
            ],
        })
        return ejecucion, certificaciones

    def procesar_corte(
        self, corte: date, entregas: list[Entrega], primero: bool = False, origen: str = "simulacion"
    ) -> ResultadoCorte:
        """Procesa las entregas de un corte (en orden de llegada) y lo evalúa."""
        del_corte = [e for e in entregas if e.fecha_corte == corte]
        cargas, aceptadas = self.ingerir(del_corte, corte, primero)
        incidencias = self.homologar(aceptadas, corte, primero)
        ejecucion, certificaciones = self.evaluar(corte, origen, primero)
        return ResultadoCorte(corte, cargas, incidencias, ejecucion, certificaciones)
