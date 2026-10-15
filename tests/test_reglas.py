from datetime import date

import pytest

from dqc.motor.puntuacion import ResultadoRegla, estado, scores
from dqc.motor.reglas import desde_dict, validar
from dqc.motor.sql import limite_frescura_utc

BASE = {"id": "PER-VAL-09", "tabla": "persona", "dim": "validez", "umbral": 99, "sev": "MEDIA"}


def test_regla_valida_no_tiene_errores():
    assert validar({**BASE, "tipo": "regex", "campo": "email", "patron": "^.+@.+$"}) == []


@pytest.mark.parametrize("cambios, error", [
    ({"tipo": "regex", "campo": "email"}, "requiere 'patron'"),
    ({"tipo": "expresion", "cumple": "1 = 1; DROP TABLE persona"}, "no puede contener ';'"),
    ({"tipo": "expresion", "cumple": "fecha_alta >"}, "SQL inválido"),
    ({"tipo": "no_nulo", "campos": ["email OR 1=1"]}, "nombre de campo inválido"),
    ({"tipo": "no_nulo", "campos": ["email"], "tabla": "clientes"}, "tabla desconocida"),
    ({"tipo": "no_nulo", "campos": ["email"], "tabla": "*"}, "todas las tablas"),
    ({"tipo": "no_nulo", "campos": ["email"], "umbral": 120}, "entre 0 y 100"),
    ({"tipo": "referencia", "campo": "ubigeo", "ref": "ubigeos"}, "referencia inválida"),
    ({"tipo": "frescura", "limite": "mañana temprano", "tabla": "*"}, "el límite debe tener la forma"),
    ({"tipo": "no_nulo", "campos": ["email"], "color": "rojo"}, "atributos desconocidos"),
])
def test_regla_invalida(cambios, error):
    errores = validar({**BASE, **cambios})
    assert any(error in e for e in errores), errores


def test_desde_dict_rechaza_reglas_invalidas():
    with pytest.raises(ValueError, match="PER-VAL-09"):
        desde_dict({**BASE, "tipo": "dominio", "campo": "sexo"})


def test_campos_usados_incluye_los_de_expresiones():
    regla = desde_dict({
        **BASE, "tabla": "siniestro", "tipo": "expresion",
        "join": {"tabla": "poliza", "llave": "id_poliza"},
        "cumple": "t.fecha_ocurrencia BETWEEN j.fecha_inicio_vigencia AND j.fecha_fin_vigencia",
    })
    assert regla.campos_usados() == {"fecha_ocurrencia"}


def test_limite_de_frescura_en_hora_de_lima():
    regla = desde_dict({
        **BASE, "id": "GEN-OPO-01", "tabla": "*", "dim": "oportunidad", "tipo": "frescura",
        "limite": "fecha_corte + 2 días, 09:00 America/Lima (según registro_cargas)",
    })
    limite = limite_frescura_utc(regla, date(2026, 7, 31))
    assert limite.isoformat() == "2026-08-02T14:00:00+00:00"


@pytest.mark.parametrize("cumplimiento, esperado", [
    (None, "SIN_DATOS"), (100, "OK"), (99.5, "OK"), (98.0, "ALERTA"), (97.5, "ALERTA"), (97.4, "FALLA"),
])
def test_estado_segun_umbral(cumplimiento, esperado):
    assert estado(cumplimiento, 99.5) == esperado


def _resultado(tabla, dim, sev, universo, cumplen):
    return ResultadoRegla("X", tabla, dim, sev, "expresion", 100, date(2026, 4, 30), universo, cumplen, [])


def test_scores_ponderados_por_severidad_e_ignoran_sin_datos():
    s = scores([
        _resultado("persona", "validez", "CRITICA", 100, 100),  # 100 × 3
        _resultado("persona", "validez", "MEDIA", 100, 40),     # 40 × 1
        _resultado("persona", "volumetria", "ALTA", 0, 0),      # sin datos
        _resultado("poliza", "validez", "ALTA", 10, 5),         # 50
    ])
    assert s.por_tabla["persona"] == pytest.approx(85)
    assert s.por_dimension["persona", "volumetria"] is None
    assert s.global_ == pytest.approx((85 + 50) / 2)
