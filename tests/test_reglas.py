from datetime import date

import pytest

from dqc.modelo import ESQUEMAS, MASTER
from dqc.motor.motor import Motor
from dqc.motor.puntuacion import ResultadoRegla, estado, scores
from dqc.motor.reglas import desde_dict, validar
from dqc.motor.sql import limite_frescura_utc
from dqc.plataforma.local import PlataformaDuckDB

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


# ── Reglas del Sprint 3: sí detectan el defecto aunque los datos sintéticos nunca se lo den ──────
# Cada prueba arma a mano la tabla de MASTER en DuckDB y corre el motor con la regla del catálogo.

CORTE = date(2026, 7, 1)


def _evaluar(reglas, id_regla: str, tabla: str, filas: list[dict]) -> ResultadoRegla:
    plataforma = PlataformaDuckDB()
    completas = [{**{columna: None for columna, _ in ESQUEMAS[tabla]}, "fecha_corte": CORTE, **fila} for fila in filas]
    plataforma.agregar(MASTER, tabla, completas, ESQUEMAS[tabla])
    regla = next(r for r in reglas if r.id == id_regla)
    return Motor(plataforma, [regla]).ejecutar(CORTE).resultados[0]


def test_sin_uni_01_detecta_un_id_de_siniestro_repetido(reglas):
    limpia = _evaluar(reglas, "SIN-UNI-01", "siniestro", [{"id_siniestro": i} for i in range(1, 11)])
    assert (limpia.universo, limpia.cumplen, limpia.estado, limpia.fallidos) == (10, 10, "OK", [])

    ids = [1, 2, 3, 3, 4, 5, 6, 7, 8, 9]  # el 3 llega dos veces: las dos filas fallan
    repetida = _evaluar(reglas, "SIN-UNI-01", "siniestro", [{"id_siniestro": i} for i in ids])
    assert (repetida.universo, repetida.cumplen, repetida.estado) == (10, 8, "FALLA")
    assert repetida.fallidos == ["3", "3"]
    assert repetida.severidad == "CRITICA"


def test_pag_val_01_detecta_estados_fuera_del_dominio(reglas):
    estados = ["PAGADO"] * 3 + ["PENDIENTE"] * 2 + ["VENCIDO"] * 2 + ["Pendiente", "ANULADO", None]
    resultado = _evaluar(
        reglas, "PAG-VAL-01", "pago", [{"id_pago": i, "estado": e} for i, e in enumerate(estados, start=1)]
    )
    assert (resultado.universo, resultado.cumplen, resultado.estado) == (10, 7, "FALLA")
    # «Pendiente» (otra escritura), «ANULADO» (valor que no existe) y el nulo no cumplen
    assert set(resultado.fallidos) == {"8", "9", "10"}


def test_pag_val_01_acepta_los_tres_estados(reglas):
    estados = ["PENDIENTE", "PAGADO", "VENCIDO"]
    resultado = _evaluar(reglas, "PAG-VAL-01", "pago", [{"id_pago": i, "estado": e} for i, e in enumerate(estados, 1)])
    assert (resultado.universo, resultado.cumplen, resultado.estado) == (3, 3, "OK")


def test_per_val_06_detecta_tipos_de_documento_fuera_del_dominio(reglas):
    tipos = ["DNI"] * 4 + ["CE"] * 2 + ["RUC"] * 2 + ["dni", "PAS"]
    resultado = _evaluar(
        reglas, "PER-VAL-06", "persona", [{"id_persona": i, "tipo_documento": t} for i, t in enumerate(tipos, start=1)]
    )
    assert (resultado.universo, resultado.cumplen, resultado.estado) == (10, 8, "FALLA")
    # «dni» en minúsculas y «PAS» no cumplen: PER-VAL-01, 02 y 04 se los saltarían sin verlos
    assert set(resultado.fallidos) == {"9", "10"}
