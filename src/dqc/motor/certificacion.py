"""Certificación por tabla y corte (HU-04): consolida los tres niveles y la privacidad.

Una tabla queda certificada si ninguna regla de severidad CRITICA o ALTA está en
FALLA y la revisión de privacidad no tiene hallazgos bloqueantes. Si además hay
reglas en ALERTA, reglas MEDIA en FALLA u observaciones de privacidad, queda
"certificada con observaciones". Cada veredicto lleva su sello: la corrida, la
versión del motor y la versión del catálogo de reglas con que se evaluó.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from dqc import __version__
from dqc.modelo import (
    CERTIFICADO, CON_OBSERVACIONES, DOMINIO_POR_TABLA, NO_CERTIFICADO, SEVERIDADES_BLOQUEANTES, TABLAS_CORTE,
)
from dqc.motor.reglas import Regla, a_documento
from dqc.pipeline.privacidad import Hallazgo


@dataclass
class Certificacion:
    tabla: str
    fecha_corte: date
    estado: str
    reglas_bloqueantes: list[str]
    reglas_con_observacion: list[str]
    hallazgos: list[Hallazgo]
    cobertura: float
    version_reglas: str
    version_motor: str = __version__
    publicado: bool = False
    certificado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def dominio(self) -> str:
        return DOMINIO_POR_TABLA[self.tabla]

    @property
    def certificado(self) -> bool:
        return self.estado != NO_CERTIFICADO

    @property
    def calidad_ok(self) -> bool:
        return not self.reglas_bloqueantes

    @property
    def privacidad_ok(self) -> bool:
        return not any(h.bloqueante for h in self.hallazgos)


def version_reglas(reglas: list[Regla]) -> str:
    """Huella corta del catálogo activo: cambia si cambia cualquier regla."""
    catalogo = json.dumps(sorted((a_documento(r) for r in reglas if r.activa), key=lambda d: d["id"]), sort_keys=True)
    return hashlib.sha1(catalogo.encode()).hexdigest()[:10]


def certificar(ejecucion, hallazgos: list[Hallazgo], version: str) -> list[Certificacion]:
    certificaciones = []
    for tabla in TABLAS_CORTE:
        resultados = [r for r in ejecucion.resultados if r.tabla == tabla]
        bloqueantes = sorted(
            r.id_regla for r in resultados if r.estado == "FALLA" and r.severidad in SEVERIDADES_BLOQUEANTES
        )
        observadas = sorted(
            r.id_regla for r in resultados
            if r.estado == "ALERTA" or (r.estado == "FALLA" and r.severidad not in SEVERIDADES_BLOQUEANTES)
        )
        de_la_tabla = [h for h in hallazgos if h.tabla == tabla]
        con_datos = sum(r.estado != "SIN_DATOS" for r in resultados)
        if bloqueantes or any(h.bloqueante for h in de_la_tabla):
            estado = NO_CERTIFICADO
        elif observadas or de_la_tabla:
            estado = CON_OBSERVACIONES
        else:
            estado = CERTIFICADO
        certificaciones.append(Certificacion(
            tabla=tabla,
            fecha_corte=ejecucion.fecha_corte,
            estado=estado,
            reglas_bloqueantes=bloqueantes,
            reglas_con_observacion=observadas,
            hallazgos=de_la_tabla,
            cobertura=con_datos / len(resultados) * 100 if resultados else 0.0,
            version_reglas=version,
        ))
    return certificaciones
