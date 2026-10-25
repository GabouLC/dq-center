"""Ingesta a RAW (HU-01): valida la estructura del CSV y lo carga sin modificarlo.

Un archivo con estructura inválida (faltan columnas, nombres de columna que no son
identificadores, filas con otro número de campos, codificación ilegible) se rechaza y no
llega a RAW; el rechazo queda en
registro_cargas con su motivo. Las columnas que la homologación no conoce se
aceptan y se conservan en RAW, pero se anotan en el detalle de la carga.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pyarrow as pa

from dqc.pipeline.configuracion import Fuente

EXITOSA, RECHAZADA = "EXITOSA", "RECHAZADA"
IDENTIFICADOR = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}")
RESERVADAS = {"fecha_corte", "archivo"}  # las agrega la ingesta


@dataclass(frozen=True)
class Entrega:
    """Un archivo que llegó a la zona de aterrizaje, con su hora de llegada."""

    archivo: str  # ruta relativa a la carpeta landing
    tabla: str
    fecha_corte: date
    llegada: datetime

    @property
    def nombre(self) -> str:
        return Path(self.archivo).name


def leer_entregas(landing: Path) -> list[Entrega]:
    with open(landing / "entregas.json", encoding="utf-8") as f:
        datos = json.load(f)
    entregas = [
        Entrega(
            archivo=d["archivo"],
            tabla=d["tabla"],
            fecha_corte=date.fromisoformat(d["fecha_corte"]),
            llegada=datetime.fromisoformat(d["llegada"]),
        )
        for d in datos
    ]
    return sorted(entregas, key=lambda e: (e.llegada, e.archivo))


@dataclass
class Carga:
    entrega: Entrega
    estado: str
    filas: int
    detalle: str | None
    datos: pa.Table | None = None  # columnas de origen + fecha_corte + archivo

    def registro(self) -> dict:
        return {
            "tabla": self.entrega.tabla,
            "fecha_corte": self.entrega.fecha_corte,
            "archivo": self.entrega.nombre,
            "cargado_en": self.entrega.llegada,
            "filas": self.filas,
            "estado": self.estado,
            "detalle": self.detalle,
        }


def validar_csv(landing: Path, entrega: Entrega, fuente: Fuente) -> Carga:
    def rechazo(motivo: str, filas: int = 0) -> Carga:
        return Carga(entrega, RECHAZADA, filas, motivo)

    try:
        with open(landing / entrega.archivo, encoding="utf-8", newline="") as f:
            filas = list(csv.reader(f))
    except FileNotFoundError:
        return rechazo("el archivo no existe")
    except UnicodeDecodeError:
        return rechazo("el archivo no está en UTF-8")
    if not filas:
        return rechazo("el archivo está vacío")

    encabezado, registros = filas[0], filas[1:]
    # Cada columna llega a RAW como identificador SQL: solo letras, dígitos y guion bajo.
    invalidas = [c for c in encabezado if not IDENTIFICADOR.fullmatch(c) or c.lower() in RESERVADAS]
    if invalidas:
        return rechazo(f"nombres de columna no válidos: {', '.join(repr(c) for c in invalidas)}", len(registros))
    faltantes = [c for c in fuente.requeridas if c not in encabezado]
    if faltantes:
        return rechazo(f"faltan columnas: {', '.join(faltantes)}", len(registros))
    repetidas = sorted({c for c in encabezado if encabezado.count(c) > 1})
    if repetidas:
        return rechazo(f"columnas repetidas: {', '.join(repetidas)}", len(registros))
    for numero, registro in enumerate(registros, start=2):
        if len(registro) != len(encabezado):
            return rechazo(
                f"la línea {numero} tiene {len(registro)} campos y el encabezado {len(encabezado)}", len(registros)
            )

    conocidas = {c.origen for c in fuente.columnas}
    no_mapeadas = [c for c in encabezado if c not in conocidas]
    columnas = {nombre: [r[i] for r in registros] for i, nombre in enumerate(encabezado)}
    columnas["fecha_corte"] = [entrega.fecha_corte] * len(registros)
    columnas["archivo"] = [entrega.nombre] * len(registros)
    esquema = pa.schema(
        [(c, pa.string()) for c in encabezado] + [("fecha_corte", pa.date32()), ("archivo", pa.string())]
    )
    return Carga(
        entrega,
        EXITOSA,
        len(registros),
        f"columnas no mapeadas: {', '.join(no_mapeadas)}" if no_mapeadas else None,
        pa.table(columnas, schema=esquema),
    )
