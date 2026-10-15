"""Compara lo que detectó el flujo con el manifiesto de errores sembrados."""

from __future__ import annotations

from dqc.modelo import HOMOLOGACION, INGESTA, PRIVACIDAD
from dqc.motor.motor import comparar_con_manifiesto
from dqc.pipeline.flujo import ResultadoCorte
from dqc.pipeline.ingesta import RECHAZADA


def verificar(resultados: list[ResultadoCorte], manifiesto: list[dict]) -> dict[str, tuple[set, set]]:
    """(faltantes, sobrantes) de cada etapa: ingesta, homologación, reglas y privacidad."""
    cortes = {r.fecha_corte for r in resultados}

    def esperados(etapa: str) -> set[tuple]:
        return {
            (m["tabla"], m["fecha_corte"], m["llave"])
            for m in manifiesto
            if m["id_regla"] == etapa and m["fecha_corte"] in cortes
        }

    rechazos = {
        (c.entrega.tabla, c.entrega.fecha_corte, c.entrega.nombre)
        for r in resultados
        for c in r.cargas
        if c.estado == RECHAZADA
    }
    incidencias = {(i["tabla"], i["fecha_corte"], i["llave"]) for r in resultados for i in r.incidencias}
    fugas = {
        (h.tabla, r.fecha_corte, h.llave)
        for r in resultados
        for c in r.certificaciones
        for h in c.hallazgos
        if h.tipo == "PII_EN_CLARO"
    }
    return {
        "ingesta": (esperados(INGESTA) - rechazos, rechazos - esperados(INGESTA)),
        "homologacion": (esperados(HOMOLOGACION) - incidencias, incidencias - esperados(HOMOLOGACION)),
        "reglas": comparar_con_manifiesto([r.ejecucion for r in resultados], manifiesto),
        "privacidad": (esperados(PRIVACIDAD) - fugas, fugas - esperados(PRIVACIDAD)),
    }
