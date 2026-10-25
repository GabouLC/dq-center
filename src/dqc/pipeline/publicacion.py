"""Publicación en BUSINESS (HU-08) y vistas de contrato del portal.

  p_<tabla>         solo los cortes certificados por el Quality & Privacy Gate.
                    La PII sigue cifrada: BUSINESS no expone nada en claro.
  v_<tabla>         el último corte certificado de cada tabla.
  v_calidad_*       vistas de contrato sobre resultados, cargas e incidencias:
                    lo único que lee el portal (no consulta RAW ni MASTER).
"""

from __future__ import annotations

from datetime import date

from dqc.modelo import BUSINESS, ENGINE, ESQUEMAS, ESQUEMAS_ENGINE, MASTER, RAW
from dqc.sql_util import fecha

# Tablas que deben existir antes de crear las vistas de contrato.
TABLAS_BASE = [(ENGINE, t, columnas) for t, columnas in ESQUEMAS_ENGINE.items()] + [
    (RAW, "registro_cargas", ESQUEMAS["registro_cargas"]),
    (MASTER, "incidencias_homologacion", ESQUEMAS["incidencias_homologacion"]),
]


def _proyeccion(dataset: str, tabla: str, columnas: list[tuple[str, str]]) -> str:
    return f"SELECT {', '.join(c for c, _ in columnas)} FROM {dataset}.{tabla}"


def vistas_contrato() -> dict[str, str]:
    vistas = {f"v_calidad_{t}": _proyeccion(ENGINE, t, columnas) for t, columnas in ESQUEMAS_ENGINE.items()}
    vistas["v_calidad_cargas"] = _proyeccion(RAW, "registro_cargas", ESQUEMAS["registro_cargas"])
    vistas["v_calidad_incidencias"] = _proyeccion(MASTER, "incidencias_homologacion", ESQUEMAS["incidencias_homologacion"])
    return vistas


def preparar_almacen(plataforma) -> None:
    """Tablas de resultados vacías y vistas de contrato, para que el portal funcione desde el inicio."""
    plataforma.preparar()
    for dataset, tabla, columnas in TABLAS_BASE:
        plataforma.crear_tabla(dataset, tabla, columnas)
    for nombre, sql in vistas_contrato().items():
        plataforma.crear_vista(BUSINESS, nombre, sql)


def publicar(plataforma, certificaciones, corte: date, primero: bool) -> None:
    """Copia a BUSINESS cada tabla certificada en el corte; las demás no se exponen.

    Si el corte ya estaba publicado (una reevaluación), primero se quita: así una tabla que
    deja de estar certificada sale de BUSINESS, y en el sandbox el corte no se duplica.
    """
    for c in certificaciones:
        if not primero:
            plataforma.quitar_corte(BUSINESS, f"p_{c.tabla}", corte)
        if not c.certificado:
            continue
        plataforma.materializar(
            f"SELECT * FROM {MASTER}.{c.tabla} WHERE fecha_corte = {fecha(corte)}",
            BUSINESS, f"p_{c.tabla}", corte, primero,
        )
        plataforma.crear_vista(
            BUSINESS,
            f"v_{c.tabla}",
            f"SELECT * FROM {BUSINESS}.p_{c.tabla} "
            f"WHERE fecha_corte = (SELECT MAX(fecha_corte) FROM {BUSINESS}.p_{c.tabla})",
        )
        c.publicado = True
