"""Parte pura de scripts/verificar_portal.py: colores, razón de contraste WCAG, umbrales y el informe.

No arranca servidores ni navegadores (ni importa Playwright): todo se calcula con colores conocidos.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).parents[1]


@pytest.fixture(scope="module")
def vp():
    spec = importlib.util.spec_from_file_location("verificar_portal", RAIZ / "scripts" / "verificar_portal.py")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo  # los dataclass del script lo necesitan registrado
    spec.loader.exec_module(modulo)
    yield modulo
    sys.modules.pop(spec.name, None)


BLANCO, NEGRO = (255, 255, 255), (0, 0, 0)


# ── interpretar colores ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("rgb(15, 27, 45)", (15, 27, 45, 1.0)),
        ("rgba(15, 27, 45, 0.5)", (15, 27, 45, 0.5)),
        ("rgb(95 168 255 / 0.14)", (95, 168, 255, 0.14)),  # sintaxis moderna, con espacios
        ("rgb(95 168 255 / 25%)", (95, 168, 255, 0.25)),
        ("rgb(50%, 0%, 100%)", (127.5, 0, 255, 1.0)),
        ("  RGB(0,0,0)  ", (0, 0, 0, 1.0)),  # mayúsculas y espacios sobrantes
        ("rgba(0, 0, 0, 0)", (0, 0, 0, 0.0)),
        ("transparent", (0, 0, 0, 0.0)),
        ("color(srgb 1 0.5 0 / 0.8)", (255, 127.5, 0, 0.8)),
        ("#fff", (255, 255, 255, 1.0)),
        ("#777777", (119, 119, 119, 1.0)),
        ("#0f1b2d80", (15, 27, 45, 128 / 255)),
    ],
)
def test_parsear_color_entiende_rgb_rgba_y_otras_formas(vp, texto, esperado):
    assert vp.parsear_color(texto) == pytest.approx(esperado)


@pytest.mark.parametrize("texto", ["", "azul", "rgb(1, 2)", "rgb(1, 2, 3, 4, 5)", "rgb(a, b, c)", "oklch(0.5 0.1 200)", "#12", "var(--tinta)", None])
def test_parsear_color_devuelve_none_si_no_lo_entiende(vp, texto):
    assert vp.parsear_color(texto) is None


def test_parsear_color_recorta_a_los_rangos_validos(vp):
    assert vp.parsear_color("rgba(300, -5, 10, 1.7)") == (255.0, 0.0, 10.0, 1.0)


# ── razón de contraste ──────────────────────────────────────────────────────


def test_blanco_sobre_negro_es_21_a_1(vp):
    assert vp.razon_contraste(BLANCO, NEGRO) == pytest.approx(21.0)
    assert vp.razon_contraste(NEGRO, BLANCO) == pytest.approx(21.0)  # el orden no importa


def test_mismo_color_es_1_a_1(vp):
    assert vp.razon_contraste((40, 90, 160), (40, 90, 160)) == pytest.approx(1.0)


def test_gris_777_sobre_blanco_es_justo_el_que_no_llega_a_4_5(vp):
    razon = vp.razon_contraste((119, 119, 119), BLANCO)
    assert razon == pytest.approx(4.48, abs=0.01)
    assert razon < 4.5


def test_gris_767676_sobre_blanco_es_el_mas_claro_que_cumple(vp):
    assert vp.razon_contraste((118, 118, 118), BLANCO) >= 4.5


def test_tinta_del_portal_sobre_su_superficie_clara(vp):
    # --tinta #0f1b2d sobre --superficie #ffffff: texto principal del tema claro
    assert vp.razon_contraste((15, 27, 45), BLANCO) > 15


def test_luminancia_de_los_extremos(vp):
    assert vp.luminancia(NEGRO) == 0
    assert vp.luminancia(BLANCO) == pytest.approx(1.0)


# ── componer con transparencia ──────────────────────────────────────────────


def test_componer_con_alfa_mezcla_proporcional(vp):
    assert vp.componer((0, 0, 0, 0.5), BLANCO) == pytest.approx((127.5, 127.5, 127.5))
    assert vp.componer((10, 20, 30, 1.0), BLANCO) == (10, 20, 30)  # opaco: no deja pasar el fondo
    assert vp.componer((10, 20, 30, 0.0), (1, 2, 3)) == (1, 2, 3)  # transparente: solo el fondo


# ── umbrales ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("tamano", "peso", "umbral"),
    [(14.5, 400, 4.5), (18, 700, 4.5), (19, 700, 3.0), (19, 600, 4.5), (23.9, 400, 4.5), (24, 400, 3.0), (29, 800, 3.0), (76, 400, 3.0)],
)
def test_umbral_del_texto_grande_y_del_normal(vp, tamano, peso, umbral):
    assert vp.umbral_para(tamano, peso) == umbral


# ── medir un texto contra su fondo efectivo ─────────────────────────────────


def test_medir_contraste_texto_claro_sobre_fondo_opaco(vp):
    m = vp.medir_contraste("rgb(15, 27, 45)", [{"bg": "rgb(255, 255, 255)", "img": None, "sel": ""}], 14.5, 400)
    assert m.estado == "ok" and m.razon > 15 and m.umbral == 4.5


def test_medir_contraste_detecta_el_que_no_llega(vp):
    m = vp.medir_contraste("rgb(119, 119, 119)", [{"bg": "rgb(255, 255, 255)"}], 14.5, 400)
    assert m.estado == "falla" and m.razon == pytest.approx(4.48, abs=0.01)


def test_el_mismo_gris_pasa_si_el_texto_es_grande(vp):
    assert vp.medir_contraste("rgb(119, 119, 119)", [{"bg": "rgb(255, 255, 255)"}], 24, 400).estado == "ok"  # 3:1
    assert vp.medir_contraste("rgb(119, 119, 119)", [{"bg": "rgb(255, 255, 255)"}], 19, 700).estado == "ok"
    assert vp.medir_contraste("rgb(119, 119, 119)", [{"bg": "rgb(255, 255, 255)"}], 19, 400).estado == "falla"


def test_medir_contraste_compone_las_capas_semitransparentes_hasta_la_primera_opaca(vp):
    # texto negro sobre un velo blanco al 50 % puesto sobre negro: el fondo efectivo es gris 127,5
    capas = [{"bg": "rgba(255, 255, 255, 0.5)"}, {"bg": "rgb(0, 0, 0)"}, {"bg": "rgb(255, 255, 255)"}]  # la última ya no se mira
    m = vp.medir_contraste("rgb(0, 0, 0)", capas, 14, 400)
    assert m.fondo == pytest.approx((127.5, 127.5, 127.5))
    assert m.razon == pytest.approx(vp.razon_contraste(NEGRO, (127.5, 127.5, 127.5)))


def test_capas_transparentes_se_saltan(vp):
    capas = [{"bg": "rgba(0, 0, 0, 0)"}, {"bg": "rgb(20, 28, 42)"}]
    m = vp.medir_contraste("rgb(238, 242, 249)", capas, 14.5, 400)
    assert m.estado == "ok" and m.fondo == (20, 28, 42)


def test_el_alfa_del_texto_y_la_opacidad_bajan_el_contraste(vp):
    capas = [{"bg": "rgb(255, 255, 255)"}]
    opaco = vp.medir_contraste("rgb(0, 0, 0)", capas, 14, 400)
    claro = vp.medir_contraste("rgba(0, 0, 0, 0.5)", capas, 14, 400)
    semitransparente = vp.medir_contraste("rgb(0, 0, 0)", capas, 14, 400, opacidad=0.5)
    assert opaco.razon == pytest.approx(21)
    assert claro.razon == pytest.approx(semitransparente.razon) and claro.razon < 5


def test_un_degradado_o_una_imagen_dejan_el_fondo_indeterminado(vp):
    capas = [{"bg": "rgba(0, 0, 0, 0)"}, {"bg": "rgba(0, 0, 0, 0)", "img": "linear-gradient(red, blue)", "sel": "section.hero"}, {"bg": "rgb(255, 255, 255)"}]
    m = vp.medir_contraste("rgb(255, 255, 255)", capas, 14.5, 400)
    assert m.estado == "indeterminado" and m.razon is None and "section.hero" in m.motivo


def test_colores_que_no_se_entienden_son_indeterminados_nunca_aprobados(vp):
    assert vp.medir_contraste("oklch(0.5 0.1 200)", [{"bg": "rgb(0, 0, 0)"}], 14, 400).estado == "indeterminado"
    assert vp.medir_contraste("rgb(0, 0, 0)", [{"bg": "azul"}], 14, 400).estado == "indeterminado"
    assert vp.medir_contraste("rgba(0, 0, 0, 0)", [{"bg": "rgb(255, 255, 255)"}], 14, 400).estado == "indeterminado"  # texto transparente


def test_sin_capa_opaca_el_fondo_es_el_lienzo_blanco(vp):
    m = vp.medir_contraste("rgb(0, 0, 0)", [], 14, 400)
    assert m.fondo == (255, 255, 255) and m.razon == pytest.approx(21)


def test_hexa_y_formato_de_razon(vp):
    assert vp.hexa((15, 27, 45)) == "#0f1b2d" and vp.hexa(None) == "?"
    assert vp._ratio(4.4812) == "4,48:1" and vp._ratio(None) == "?"


# ── resultados e informe ────────────────────────────────────────────────────


def test_una_comprobacion_sin_verificaciones_o_con_una_falla_no_es_pass(vp):
    c = vp.Comprobacion("x", "Prueba")
    assert c.estado == "OMITIDA"  # nunca corrió
    c.ejecutada = True
    assert c.estado == "FAIL"  # corrió pero no verificó nada: no se da por buena
    c.ok(True, "algo")
    assert c.estado == "PASS"
    c.ok(False, "otra cosa", "se vio X")
    assert c.estado == "FAIL" and [s.texto for s in c.fallas] == ["otra cosa"]
    c.subs.pop()
    c.error = "TimeoutError: ..."
    assert c.estado == "FAIL"  # una excepción tampoco pasa


def test_el_informe_trae_la_tabla_el_detalle_y_los_indeterminados(vp):
    a = vp.Comprobacion("a", "Inicio de sesión", ejecutada=True)
    a.ok(True, "carga")
    b = vp.Comprobacion("b", "Roles", ejecutada=True)
    b.ok(False, "lector ve 7", "vio 11")
    texto = vp.informe([a, b], ["Cabecera"], ["- [claro] fondo con degradado: 3 textos"], ["- una excepción documentada"])
    assert texto.startswith("Cabecera")
    assert "a Inicio de sesión" in texto.replace("  ", " ") and "PASS" in texto and "FAIL" in texto
    assert "[FAIL] lector ve 7 -> vio 11" in texto
    assert "CONTRASTE INDETERMINADO" in texto and "3 textos" in texto and "una excepción documentada" in texto


def test_el_informe_sin_indeterminados_lo_dice(vp):
    c = vp.Comprobacion("f", "Contraste", ejecutada=True)
    c.ok(True, "ok")
    assert "Ninguno." in vp.informe([c], indeterminados=[])


# ── el script se puede importar sin Playwright ──────────────────────────────


def test_importar_el_script_no_exige_playwright(vp):
    assert not hasattr(vp, "sync_playwright")  # Playwright solo se importa dentro de main()
    assert vp.PUERTO_API == 8002 and vp.PUERTO_WEB == 5182  # los puertos propios (8003 es del otro script)
    assert len(vp.SECCIONES) == 11 and {p.clave for p in vp.PANTALLAS} >= {"clave", "entrar", "resumen"}


# ── borrar solo lo que es del script ────────────────────────────────────────


def test_no_borra_una_carpeta_que_no_es_de_salida(vp, tmp_path):
    ajena = tmp_path / "mis_cosas"
    ajena.mkdir()
    (ajena / "importante.txt").write_text("no se toca", encoding="utf-8")
    with pytest.raises(SystemExit):
        vp.borrar_carpeta_de_salida(ajena)
    assert (ajena / "importante.txt").exists()


def test_no_borra_data_ni_la_raiz_del_repo(vp):
    with pytest.raises(SystemExit):
        vp.borrar_carpeta_de_salida(RAIZ / "data")
    with pytest.raises(SystemExit):
        vp.borrar_carpeta_de_salida(RAIZ)


def test_borra_una_carpeta_con_la_marca_del_script(vp, tmp_path):
    suya = tmp_path / "salida"
    suya.mkdir()
    (suya / vp.MARCA_DE_SALIDA).write_text("marca", encoding="utf-8")
    (suya / "resultado.txt").write_text("viejo", encoding="utf-8")
    vp.borrar_carpeta_de_salida(suya)
    assert not suya.exists()
