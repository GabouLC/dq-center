"""Configuración del flujo: homologación de cada fuente y clasificación DAC de los contratos."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from dqc.modelo import DAC, LLAVES, MODOS_CIFRADO, TABLAS_CORTE

TIPOS_DESTINO = ("STRING", "INT64", "FLOAT64", "DATE", "BOOL")


@dataclass(frozen=True)
class ColumnaFuente:
    origen: str
    destino: str
    tipo: str = "STRING"
    formato: str | None = None
    verdadero: str | None = None
    falso: str | None = None
    opcional: bool = False


@dataclass(frozen=True)
class Fuente:
    tabla: str  # tabla de MASTER
    archivo: str  # prefijo del CSV y nombre de la tabla en RAW
    columnas: tuple[ColumnaFuente, ...]

    @property
    def por_corte(self) -> bool:
        return self.tabla in TABLAS_CORTE

    @property
    def requeridas(self) -> list[str]:
        return [c.origen for c in self.columnas if not c.opcional]

    @property
    def llave_origen(self) -> str:
        """Columna de origen que identifica el registro (la llave de MASTER o la primera)."""
        llave = LLAVES.get(self.tabla)
        return next((c.origen for c in self.columnas if c.destino == llave), self.columnas[0].origen)


def cargar_homologacion(ruta: str | Path) -> dict[str, Fuente]:
    with open(ruta, encoding="utf-8") as f:
        datos = yaml.safe_load(f)["fuentes"]
    fuentes = {}
    for tabla, fuente in datos.items():
        columnas = tuple(ColumnaFuente(**c) for c in fuente["columnas"])
        for c in columnas:
            if c.tipo not in TIPOS_DESTINO:
                raise ValueError(f"{tabla}.{c.destino}: tipo desconocido {c.tipo}")
            if c.tipo == "DATE" and not c.formato:
                raise ValueError(f"{tabla}.{c.destino}: una fecha necesita formato")
            if c.tipo == "BOOL" and (c.verdadero is None or c.falso is None):
                raise ValueError(f"{tabla}.{c.destino}: un booleano necesita verdadero y falso")
        fuentes[tabla] = Fuente(tabla=tabla, archivo=fuente["archivo"], columnas=columnas)
    return fuentes


def cargar_contratos(ruta: str | Path) -> dict[str, dict]:
    with open(ruta, encoding="utf-8") as f:
        contratos = yaml.safe_load(f)["contratos"]
    for tabla, contrato in contratos.items():
        for campo in contrato["campos"]:
            if campo.get("dac") not in DAC:
                raise ValueError(f"{tabla}.{campo['nombre']}: clasificación DAC inválida {campo.get('dac')!r}")
            cifrado = campo.get("cifrado")
            if (campo["dac"] == "SENSIBLE_CIFRADO") != (cifrado is not None) or (cifrado and cifrado not in MODOS_CIFRADO):
                raise ValueError(f"{tabla}.{campo['nombre']}: solo los campos SENSIBLE_CIFRADO llevan cifrado")
    return contratos


def cifrados(contratos: dict[str, dict]) -> dict[str, dict[str, str]]:
    """tabla -> campo -> modo de cifrado, para los campos SENSIBLE_CIFRADO."""
    return {
        tabla: {c["nombre"]: c["cifrado"] for c in contrato["campos"] if c.get("cifrado")}
        for tabla, contrato in contratos.items()
    }


def clasificacion(contratos: dict[str, dict]) -> dict[str, dict[str, str]]:
    """tabla -> campo -> clasificación DAC."""
    return {tabla: {c["nombre"]: c["dac"] for c in contrato["campos"]} for tabla, contrato in contratos.items()}
