import pytest

from dqc.datagen.generador import generar


@pytest.fixture(scope="session")
def resultado():
    """Datos sintéticos con la semilla fija; se generan una sola vez por sesión."""
    return generar()
