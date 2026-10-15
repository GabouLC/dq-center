from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest

from dqc.datagen.exportar import exportar
from dqc.datagen.generador import generar
from dqc.modelo import CORTES
from dqc.motor.reglas import cargar_yaml
from dqc.pipeline.configuracion import cargar_contratos, cargar_homologacion
from dqc.pipeline.flujo import Flujo, ResultadoCorte
from dqc.pipeline.ingesta import leer_entregas
from dqc.plataforma.local import PlataformaDuckDB

CONFIG = Path(__file__).parents[1] / "config"


@dataclass
class Datos:
    landing: Path
    manifiesto: list[dict]


@dataclass
class Simulacion:
    plataforma: PlataformaDuckDB
    resultados: dict[date, ResultadoCorte]


@pytest.fixture(scope="session")
def resultado():
    """Datos sintéticos con la semilla fija; se generan una sola vez por sesión."""
    return generar()


@pytest.fixture(scope="session")
def fuentes():
    return cargar_homologacion(CONFIG / "homologacion.yaml")


@pytest.fixture(scope="session")
def contratos():
    return cargar_contratos(CONFIG / "contratos.yaml")


@pytest.fixture(scope="session")
def reglas():
    return cargar_yaml(CONFIG / "reglas_iniciales.yaml")


@pytest.fixture(scope="session")
def datos(resultado, fuentes, tmp_path_factory) -> Datos:
    salida = tmp_path_factory.mktemp("datos")
    return Datos(salida / "landing", exportar(resultado, fuentes, salida))


@pytest.fixture(scope="session")
def simulacion(datos, fuentes, contratos, reglas) -> Simulacion:
    """Simula la historia en DuckDB: cada corte pasa por ingesta, homologación y motor."""
    plataforma = PlataformaDuckDB()
    flujo = Flujo(plataforma, fuentes, contratos, reglas, datos.landing)
    flujo.preparar()
    entregas = leer_entregas(datos.landing)
    resultados = {c: flujo.procesar_corte(c, entregas, primero=i == 0) for i, c in enumerate(CORTES)}
    return Simulacion(plataforma, resultados)


@pytest.fixture(scope="session")
def ejecuciones(simulacion):
    return {c: r.ejecucion for c, r in simulacion.resultados.items()}
