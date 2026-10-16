"""Inicio de sesión (HU-13): contraseñas, sesiones firmadas, bloqueo por intentos y contraseñas temporales."""

import pytest

from dqc.api.autenticacion import (
    MAX_INTENTOS, Autenticador, ErrorAcceso, Sesiones, cifrar_clave, clave_correcta, clave_temporal, problemas_de_clave,
)
from dqc.api.configuracion import ConfiguracionLocal

from conftest import CONFIG

EMAIL, CLAVE = "lector@demo.local", "clave-de-prueba"


class Reloj:
    def __init__(self):
        self.ahora = 1_800_000_000.0

    def __call__(self) -> float:
        return self.ahora


@pytest.fixture
def reloj():
    return Reloj()


@pytest.fixture
def autenticador(tmp_path, reloj):
    config = ConfiguracionLocal(tmp_path / "config.json", CONFIG)
    a = Autenticador(config, Sesiones(b"s" * 32, reloj=reloj), iteraciones=1_000)
    a.fijar(EMAIL, CLAVE, debe_cambiar=False)
    return a


def test_la_contrasena_se_guarda_con_sal_y_nunca_en_claro():
    a, b = cifrar_clave(CLAVE, 1_000), cifrar_clave(CLAVE, 1_000)
    assert a != b and CLAVE not in a
    assert clave_correcta(CLAVE, a) and not clave_correcta("otra", a)
    assert not clave_correcta(CLAVE, "basura")


def test_reglas_de_una_contrasena_nueva():
    assert problemas_de_clave("corta", EMAIL)
    assert problemas_de_clave("lector-2026-seguro", EMAIL) == ["no puede contener tu usuario"]
    assert problemas_de_clave("aaaaaaaaaaaa", EMAIL) == ["es demasiado repetitiva"]
    assert problemas_de_clave("una frase larga y propia", EMAIL) == []
    assert len(clave_temporal()) == 12 and clave_temporal() != clave_temporal()


def test_sesion_valida_alterada_y_vencida(autenticador, reloj):
    token = autenticador.entrar(EMAIL, CLAVE)["token"]
    assert autenticador.verificar(token) == EMAIL
    prefijo, cuerpo, firma = token.split(".")
    with pytest.raises(ValueError):
        autenticador.verificar(f"{prefijo}.{cuerpo}.{firma[::-1]}")
    otro = Sesiones(b"o" * 32, reloj=reloj).emitir(EMAIL, autenticador.config.credencial(EMAIL)["clave"])[0]
    with pytest.raises(ValueError):
        autenticador.verificar(otro)
    reloj.ahora += 8 * 3600 + 1
    with pytest.raises(ValueError, match="vencida"):
        autenticador.verificar(token)


def test_cinco_intentos_fallidos_bloquean_la_cuenta_15_minutos(autenticador, reloj):
    for _ in range(MAX_INTENTOS):
        with pytest.raises(ErrorAcceso) as error:
            autenticador.entrar(EMAIL, "equivocada")
        assert error.value.codigo == 401
    with pytest.raises(ErrorAcceso) as error:
        autenticador.entrar(EMAIL, CLAVE)
    assert error.value.codigo == 423 and "15 min" in error.value.mensaje
    assert autenticador.estado(EMAIL)["bloqueada"]
    acciones = [e["accion"] for e in autenticador.config.auditoria()]
    assert acciones.count("INICIO_FALLIDO") == MAX_INTENTOS and "CUENTA_BLOQUEADA" in acciones

    reloj.ahora += 15 * 60 + 1
    assert autenticador.entrar(EMAIL, CLAVE)["token"]
    assert autenticador.config.credencial(EMAIL)["intentos"] == 0


def test_cambiar_la_contrasena_cierra_las_sesiones_anteriores(autenticador):
    viejo = autenticador.entrar(EMAIL, CLAVE)["token"]
    with pytest.raises(ErrorAcceso, match="actual"):
        autenticador.cambiar(EMAIL, "equivocada", "una frase larga y propia")
    with pytest.raises(ErrorAcceso) as error:
        autenticador.cambiar(EMAIL, CLAVE, CLAVE)
    assert "la contraseña nueva debe ser distinta de la actual" in error.value.mensaje
    nuevo = autenticador.cambiar(EMAIL, CLAVE, "una frase larga y propia")["token"]
    assert autenticador.verificar(nuevo) == EMAIL
    with pytest.raises(ValueError, match="sesión cerrada"):
        autenticador.verificar(viejo)


def test_la_contrasena_temporal_desbloquea_y_obliga_a_cambiarla(autenticador):
    for _ in range(MAX_INTENTOS):
        with pytest.raises(ErrorAcceso):
            autenticador.entrar(EMAIL, "equivocada")
    temporal = autenticador.asignar_temporal(EMAIL)
    sesion = autenticador.entrar(EMAIL, temporal)
    assert sesion["debe_cambiar"] and autenticador.debe_cambiar(EMAIL)
    autenticador.cambiar(EMAIL, temporal, "una frase larga y propia")
    assert not autenticador.debe_cambiar(EMAIL)


def test_quitar_el_acceso_cierra_la_sesion(autenticador):
    token = autenticador.entrar(EMAIL, CLAVE)["token"]
    autenticador.config.borrar_usuario(EMAIL)
    with pytest.raises(ValueError):
        autenticador.verificar(token)
    with pytest.raises(ErrorAcceso):
        autenticador.entrar(EMAIL, CLAVE)
