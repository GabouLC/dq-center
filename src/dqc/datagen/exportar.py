"""Exporta los datos sintéticos como los entregarían los sistemas de origen.

  <salida>/landing/<fecha_corte>/<archivo>_<AAAAMMDD>_<NN>.csv  un CSV por fuente y entrega
  <salida>/landing/entregas.json                                qué llegó y a qué hora
  <salida>/manifiesto_errores.parquet                           lo que el flujo debe detectar

Cada CSV usa los nombres y formatos de su fuente (config/homologacion.yaml),
con todos los valores entre comillas para que los espacios lleguen intactos.
"""

from __future__ import annotations

import csv
import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from dqc.datagen.generador import INGESTA, NO_CONVERTIBLE, RECHAZO_SINIESTRO, Resultado
from dqc.modelo import CORTES, ESQUEMAS, TABLAS_CORTE
from dqc.pipeline.configuracion import ColumnaFuente, Fuente
from dqc.tipos import esquema_arrow

# La primera entrega de siniestros del 28 de julio llega sin esta columna: se
# rechaza y el sistema de origen la reenvía corregida tres horas después.
RECHAZO = ("siniestro", RECHAZO_SINIESTRO, "ESTADO_SINIESTRO")


def _formatear(valor, c: ColumnaFuente) -> str:
    if valor is None:
        return ""
    if c.tipo == "DATE":
        return valor.strftime(c.formato)
    if c.tipo == "BOOL":
        return c.verdadero if valor else c.falso
    return str(valor)


def _no_convertible(valor, campo: str) -> str:
    """El valor en un formato que la homologación no acepta."""
    if campo == "monto":
        return f"S/ {valor:,.2f}"
    if campo == "fecha_aviso":
        return valor.strftime("%d/%m/%Y")
    raise ValueError(f"no sé cómo deformar {campo}")


def _escribir_csv(ruta: Path, fuente: Fuente, filas: list[dict], omitir: str | None) -> None:
    columnas = [
        c for c in fuente.columnas
        if c.origen != omitir and (not c.opcional or (filas and c.destino in filas[0]))
    ]
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator="\n")
        escritor.writerow([c.origen for c in columnas])
        for fila in filas:
            deformar = fila.get(NO_CONVERTIBLE)
            escritor.writerow([
                _no_convertible(fila[c.destino], c.destino) if c.destino == deformar else _formatear(fila[c.destino], c)
                for c in columnas
            ])


def exportar(resultado: Resultado, fuentes: dict[str, Fuente], salida: Path) -> list[dict]:
    """Escribe la zona de aterrizaje y el manifiesto. Devuelve el manifiesto completo."""
    landing = salida / "landing"
    entregas: list[dict] = []
    manifiesto = list(resultado.manifiesto)

    def entregar(tabla: str, corte: date, filas: list[dict], llegada: datetime, numero: int = 1, omitir=None) -> str:
        fuente = fuentes[tabla]
        relativa = Path(corte.isoformat()) / f"{fuente.archivo}_{corte:%Y%m%d}_{numero:02d}.csv"
        _escribir_csv(landing / relativa, fuente, filas, omitir)
        entregas.append({
            "archivo": relativa.as_posix(), "tabla": tabla,
            "fecha_corte": corte.isoformat(), "llegada": llegada.isoformat(),
        })
        return relativa.name

    for tabla, filas in resultado.ref.items():
        entregar(tabla, CORTES[0], filas, resultado.llegadas[tabla, CORTES[0]])
    for corte in CORTES:
        for tabla in TABLAS_CORTE:
            filas = resultado.por_corte[tabla][corte]
            llegada = resultado.llegadas[tabla, corte]
            if (tabla, corte) == RECHAZO[:2]:
                rechazado = entregar(tabla, corte, filas, llegada, 1, omitir=RECHAZO[2])
                manifiesto.append({
                    "id_regla": INGESTA, "tabla": tabla, "fecha_corte": corte, "llave": rechazado,
                    "descripcion": f"Archivo sin la columna {RECHAZO[2]}: se rechaza y se reenvía corregido",
                })
                entregar(tabla, corte, filas, llegada + timedelta(hours=3), 2)
            else:
                entregar(tabla, corte, filas, llegada)

    entregas.sort(key=lambda e: (e["llegada"], e["archivo"]))
    (landing / "entregas.json").write_text(json.dumps(entregas, indent=1), encoding="utf-8")
    pq.write_table(
        pa.Table.from_pylist(manifiesto, schema=esquema_arrow(ESQUEMAS["manifiesto_errores"])),
        salida / "manifiesto_errores.parquet",
    )
    return manifiesto
