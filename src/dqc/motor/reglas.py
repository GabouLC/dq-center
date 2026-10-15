"""Catálogo de reglas: carga, validación y expansión de las reglas transversales."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, fields
from pathlib import Path

import sqlglot
import yaml

from dqc.modelo import DIMENSIONES, PESO_SEVERIDAD, TABLAS_CORTE, TABLAS_REF

TIPOS_FILA = {"no_nulo", "al_menos_uno", "unico", "regex", "dominio", "expresion", "referencia"}
TIPOS_TABLA = {"frescura", "variacion_volumen", "minimo_filas"}
TIPOS = TIPOS_FILA | TIPOS_TABLA

_IDENTIFICADOR = re.compile(r"^[a-z_][a-z0-9_]*$")
_ID_REGLA = re.compile(r"^[A-Z]{3}-[A-Z]{3}-\d{2}$")
# "fecha_corte + 2 días, 09:00 America/Lima (según registro_cargas)"
_LIMITE = re.compile(r"fecha_corte \+ (\d+) d[ií]as?, (\d{1,2}):(\d{2}) ([A-Za-z_]+/[A-Za-z_]+)")


@dataclass
class Regla:
    id: str
    tabla: str
    dim: str
    tipo: str
    umbral: float
    sev: str
    activa: bool = True
    campo: str | None = None
    campos: list[str] = field(default_factory=list)
    patron: str | None = None
    valores: list[str] = field(default_factory=list)
    filtro: str | None = None
    cumple: str | None = None
    join: dict | None = None
    ref: str | None = None
    ref_filtro: str | None = None
    limite: str | None = None
    max_variacion_pct: float | None = None
    min: int | None = None
    descripcion: str | None = None

    @property
    def es_de_tabla(self) -> bool:
        return self.tipo in TIPOS_TABLA

    def campos_usados(self) -> set[str]:
        """Campos de la tabla que la regla vigila; sirve para la cobertura del contrato."""
        usados = set(self.campos)
        if self.campo:
            usados.add(self.campo)
        for fragmento in (self.cumple, self.filtro):
            if fragmento:
                usados |= {
                    c.name for c in sqlglot.parse_one(fragmento, read="bigquery").find_all(sqlglot.exp.Column)
                    if c.table in ("", "t")
                }
        return usados

    def limite_frescura(self) -> tuple[int, int, int, str]:
        """(días, hora, minuto, zona) del límite de una regla de frescura."""
        m = _LIMITE.search(self.limite or "")
        if not m:
            raise ValueError(f"{self.id}: límite de frescura ilegible: {self.limite!r}")
        return int(m[1]), int(m[2]), int(m[3]), m[4]


_CAMPOS_REGLA = {f.name for f in fields(Regla)}


def _fragmento_sql_valido(fragmento: str) -> str | None:
    """Devuelve un error si el fragmento no es una sola expresión SQL de BigQuery."""
    if ";" in fragmento:
        return "no puede contener ';'"
    try:
        expresion = sqlglot.parse_one(fragmento, read="bigquery")
    except sqlglot.errors.ParseError as e:
        return f"SQL inválido: {e.errors[0]['description'] if e.errors else e}"
    prohibidos = (sqlglot.exp.DDL, sqlglot.exp.DML, sqlglot.exp.Command)
    if isinstance(expresion, prohibidos) or any(expresion.find_all(*prohibidos)):
        return "solo se permiten expresiones, no sentencias"
    return None


def validar(datos: dict) -> list[str]:
    """Errores de una regla en formato dict (tal como viene del YAML o del portal)."""
    errores = []
    desconocidos = set(datos) - _CAMPOS_REGLA
    if desconocidos:
        errores.append(f"atributos desconocidos: {sorted(desconocidos)}")
    for requerido in ("id", "tabla", "dim", "tipo", "umbral", "sev"):
        if datos.get(requerido) in (None, ""):
            errores.append(f"falta '{requerido}'")
    if errores:
        return errores

    tipo, tabla = datos["tipo"], datos["tabla"]
    if not _ID_REGLA.match(str(datos["id"])):
        errores.append("el id debe tener la forma ABC-DEF-01")
    if tipo not in TIPOS:
        errores.append(f"tipo desconocido: {tipo}")
    if datos["dim"] not in DIMENSIONES:
        errores.append(f"dimensión desconocida: {datos['dim']}")
    if datos["sev"] not in PESO_SEVERIDAD:
        errores.append(f"severidad desconocida: {datos['sev']}")
    if tabla == "*":
        if tipo not in TIPOS_TABLA:
            errores.append("solo las reglas de frescura y volumetría pueden aplicar a todas las tablas")
    elif tabla not in TABLAS_CORTE:
        errores.append(f"tabla desconocida: {tabla}")
    try:
        if not 0 <= float(datos["umbral"]) <= 100:
            errores.append("el umbral debe estar entre 0 y 100")
    except (TypeError, ValueError):
        errores.append("el umbral debe ser un número")

    campos = datos.get("campos") or []
    for campo in campos + ([datos["campo"]] if datos.get("campo") else []):
        if not _IDENTIFICADOR.match(str(campo)):
            errores.append(f"nombre de campo inválido: {campo}")

    def requiere(*atributos):
        for a in atributos:
            if not datos.get(a):
                errores.append(f"el tipo {tipo} requiere '{a}'")

    if tipo in ("no_nulo", "al_menos_uno", "unico"):
        requiere("campos")
    elif tipo == "regex":
        requiere("campo", "patron")
    elif tipo == "dominio":
        requiere("campo", "valores")
    elif tipo == "expresion":
        requiere("cumple")
    elif tipo == "referencia":
        requiere("campo", "ref")
        ref = str(datos.get("ref") or "")
        tabla_ref, _, columna_ref = ref.partition(".")
        if ref and (tabla_ref not in TABLAS_CORTE + TABLAS_REF or not _IDENTIFICADOR.match(columna_ref)):
            errores.append(f"referencia inválida: {ref} (forma tabla.columna)")
    elif tipo == "frescura":
        requiere("limite")
        if datos.get("limite") and not _LIMITE.search(datos["limite"]):
            errores.append("el límite debe tener la forma 'fecha_corte + N días, HH:MM Zona/Horaria'")
    elif tipo == "variacion_volumen":
        requiere("max_variacion_pct")
    elif tipo == "minimo_filas":
        requiere("min")

    join = datos.get("join")
    if join is not None:
        if (
            not isinstance(join, dict)
            or join.get("tabla") not in TABLAS_CORTE + TABLAS_REF
            or not _IDENTIFICADOR.match(str(join.get("llave", "")))
        ):
            errores.append("join debe ser {tabla: <tabla conocida>, llave: <campo>}")

    for atributo in ("filtro", "cumple", "ref_filtro"):
        if datos.get(atributo):
            error = _fragmento_sql_valido(datos[atributo])
            if error:
                errores.append(f"{atributo}: {error}")
    return errores


def desde_dict(datos: dict) -> Regla:
    errores = validar(datos)
    if errores:
        raise ValueError(f"regla {datos.get('id', '?')} inválida: " + "; ".join(errores))
    return Regla(**datos)


def expandir(reglas: list[Regla]) -> list[Regla]:
    """Reemplaza cada regla con tabla '*' por una regla por cada tabla por corte."""
    expandidas = []
    for r in reglas:
        if r.tabla == "*":
            for tabla in TABLAS_CORTE:
                expandidas.append(Regla(**{**r.__dict__, "tabla": tabla}))
        else:
            expandidas.append(r)
    return expandidas


def cargar_yaml(ruta: str | Path) -> list[Regla]:
    with open(ruta, encoding="utf-8") as f:
        datos = yaml.safe_load(f)["reglas"]
    reglas = [desde_dict(d) for d in datos]
    ids = [r.id for r in reglas]
    repetidos = {i for i in ids if ids.count(i) > 1}
    if repetidos:
        raise ValueError(f"ids repetidos en el catálogo: {sorted(repetidos)}")
    return reglas
