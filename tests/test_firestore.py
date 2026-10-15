from pathlib import Path

from dqc.modelo import ESQUEMAS, TABLAS_CORTE
from dqc.motor.reglas import a_documento, cargar_yaml, desde_documento
from dqc.pipeline.configuracion import cargar_contratos

CONFIG = Path(__file__).parents[1] / "config"


def test_las_reglas_sobreviven_el_viaje_a_firestore():
    for regla in cargar_yaml(CONFIG / "reglas_iniciales.yaml"):
        doc = {**a_documento(regla), "actualizado_en": "2026-10-15", "actualizado_por": "semilla"}
        assert desde_documento(doc) == regla


def test_los_contratos_cubren_las_tablas_con_sus_tipos_reales():
    contratos = cargar_contratos(CONFIG / "contratos.yaml")
    assert set(contratos) == set(TABLAS_CORTE)
    for tabla, contrato in contratos.items():
        pactados = [(c["nombre"], c["tipo"]) for c in contrato["campos"]]
        assert pactados == ESQUEMAS[tabla], tabla
        assert contrato["consumidores"] and contrato["dueno"]
