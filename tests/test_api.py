"""API del portal (Sprint 3): HU-09 a HU-13 y HU-15, sobre la simulación en DuckDB."""

import time

import pytest
from fastapi.testclient import TestClient

from dqc.api.app import LIMITE_SEGUNDOS, Servicios, crear_app
from dqc.api.configuracion import USUARIOS_DEMO, ConfiguracionLocal
from dqc.api.datos import FuenteBusiness
from dqc.api.servicios import lanzador_en_proceso, verificador_demo
from dqc.datagen.generador import AGOSTO, JULIO, JUNIO, SEPTIEMBRE

from conftest import CONFIG

ADMIN, GOBIERNO, LECTOR = "admin@demo.local", "gobierno@demo.local", "lector@demo.local"


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    return ConfiguracionLocal(tmp_path_factory.mktemp("config") / "config.json", CONFIG)


@pytest.fixture(scope="module")
def cliente(simulacion, config, fuentes):
    usuarios = list(USUARIOS_DEMO) + ["sinrol@demo.local"]
    servicios = Servicios(
        plataforma=simulacion.plataforma,
        fuente=FuenteBusiness(simulacion.plataforma),
        config=config,
        fuentes_homologacion=fuentes,
        verificar_token=verificador_demo(usuarios),
        lanzar=lanzador_en_proceso(simulacion.plataforma, config, fuentes),
        usuarios_demo=list(USUARIOS_DEMO),
    )
    return TestClient(crear_app(servicios))


def como(email: str) -> dict:
    return {"Authorization": f"Bearer demo:{email}"}


def get(cliente, ruta, email=LECTOR, **params):
    respuesta = cliente.get(ruta, headers=como(email), params=params)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


# ── HU-13: autenticación, roles y auditoría ─────────────────────────────────


def test_sin_token_o_con_token_invalido_responde_401(cliente):
    assert cliente.get("/api/v1/resumen").status_code == 401
    respuesta = cliente.get("/api/v1/resumen", headers={"Authorization": "Bearer demo:nadie@x.com"})
    assert respuesta.status_code == 401
    assert set(respuesta.json()) == {"statusCode", "error", "message"}


def test_cuenta_sin_rol_responde_403_y_queda_auditada(cliente, config):
    assert cliente.get("/api/v1/resumen", headers=como("sinrol@demo.local")).status_code == 403
    assert any(e["accion"] == "ACCESO_DENEGADO" and e["email"] == "sinrol@demo.local" for e in config.auditoria())


def test_cada_rol_ve_solo_sus_modulos(cliente):
    modulos = {email: {m["clave"] for m in get(cliente, "/api/v1/auth/me", email)["modulos"]} for email in (ADMIN, GOBIERNO, LECTOR)}
    assert {"reglas", "usuarios", "auditoria"} <= modulos[ADMIN]
    assert modulos[GOBIERNO] == modulos[LECTOR]
    assert not {"reglas", "usuarios", "auditoria"} & modulos[LECTOR]


def test_un_lector_no_puede_administrar(cliente, config):
    assert cliente.get("/api/v1/admin/usuarios", headers=como(LECTOR)).status_code == 403
    assert cliente.post("/api/v1/reglas", headers=como(LECTOR), json={}).status_code == 403
    assert any(e["accion"] == "ACCESO_DENEGADO" and e["email"] == LECTOR for e in config.auditoria())


def test_campos_sensibles_ocultos_para_el_lector_y_visibles_para_gobierno(cliente, config):
    ruta = "/api/v1/validaciones/PER-VAL-04/persona/fallidos"
    lector = get(cliente, ruta, LECTOR, corte=str(JULIO))
    gobierno = get(cliente, ruta, GOBIERNO, corte=str(JULIO))
    fila_l, fila_g = lector["muestras"][0]["fila"], gobierno["muestras"][0]["fila"]
    assert fila_l["fecha_nacimiento"] == "•••• restringido" and fila_g["fecha_nacimiento"] == "1900-01-01"
    assert fila_l["nro_documento"] == fila_g["nro_documento"] == "•••• cifrado"  # PII: nunca en claro
    assert "fecha_nacimiento" in lector["campos_restringidos"] and gobierno["campos_restringidos"] == []
    assert any(e["accion"] == "ACCESO_RESTRINGIDO" and e["email"] == LECTOR for e in config.auditoria())


# ── HU-09: dashboard ────────────────────────────────────────────────────────


def test_resumen_muestra_tendencia_pass_y_certificacion(cliente):
    cortes = {c["fecha_corte"]: c for c in get(cliente, "/api/v1/resumen")["cortes"]}
    assert len(cortes) == 6
    assert cortes[str(JULIO)]["global"] < cortes[str(JUNIO)]["global"] < 100
    assert 0 < cortes[str(SEPTIEMBRE)]["pct_pass"] < 100
    assert cortes[str(AGOSTO)]["certificacion"]["poliza"] == "NO_CERTIFICADO"


def test_validaciones_de_un_corte_empiezan_por_las_fallas(cliente):
    datos = get(cliente, "/api/v1/validaciones", corte=str(JULIO))
    assert len(datos["reglas"]) == 48
    assert (datos["reglas"][0]["id_regla"], datos["reglas"][0]["estado"]) == ("GEN-OPO-01", "FALLA")
    solo_n1 = get(cliente, "/api/v1/validaciones", corte=str(JULIO), nivel="N1")["reglas"]
    assert solo_n1 and {r["nivel"] for r in solo_n1} == {"N1"}


def test_comparar_cortes_muestra_primero_lo_que_empeoro(cliente):
    filas = get(cliente, "/api/v1/validaciones/comparar", a=str(JUNIO), b=str(JULIO))["reglas"]
    empeoraron = [(f["id_regla"], f["tabla"]) for f in filas if f["empeoro"]]
    assert ("GEN-OPO-01", "persona") in empeoraron
    assert filas[0]["empeoro"]


# ── HU-12: certificación integral ───────────────────────────────────────────


def test_certificacion_integral_de_junio(cliente):
    datos = get(cliente, "/api/v1/certificacion", corte=str(JUNIO))
    siniestro = next(t for t in datos["tablas"] if t["tabla"] == "siniestro")
    assert siniestro["estado"] == "NO_CERTIFICADO"
    assert siniestro["calidad"]["ok"] and not siniestro["privacidad"]["ok"]
    assert siniestro["privacidad"]["hallazgos"] == [{"tipo": "PII_EN_CLARO", "columna": "causa", "bloqueante": True, "registros": 6}]
    assert siniestro["trazabilidad"]["publicado"] is False
    persona = next(t for t in datos["tablas"] if t["tabla"] == "persona")
    assert all(c["protegido"] for c in persona["privacidad"]["campos_cifrados"])
    assert persona["trazabilidad"]["objeto_business"] == "dq_business.p_persona"
    assert datos["historia"][str(JULIO)]["persona"] == "NO_CERTIFICADO"


# ── fuentes y contrato ──────────────────────────────────────────────────────


def test_fuentes_muestran_rechazos_volumen_e_incidencias(cliente):
    tablas = {t["tabla"]: t for t in get(cliente, "/api/v1/fuentes")}
    rechazada = [c for c in tablas["siniestro"]["cargas"] if c["estado"] == "RECHAZADA"]
    assert [c["detalle"] for c in rechazada] == ["faltan columnas: ESTADO_SINIESTRO"]
    agosto = next(c for c in tablas["poliza"]["cargas"] if c["fecha_corte"] == str(AGOSTO))
    assert agosto["variacion_pct"] == pytest.approx(22, abs=0.1)
    assert all(c["incidencias"] > 0 for c in tablas["pago"]["cargas"])


def test_estructura_detecta_columna_nueva(cliente):
    cortes = get(cliente, "/api/v1/fuentes/poliza/estructura")["cortes"]
    assert cortes[-1]["agregadas"] == ["canal_venta"]


def test_contrato_con_dac_y_columna_fuera_de_contrato(cliente):
    contratos = {c["tabla"]: c for c in get(cliente, "/api/v1/contratos")}
    assert contratos["poliza"]["fuera_de_contrato"] == ["canal_venta"]
    documento = next(c for c in contratos["persona"]["campos"] if c["nombre"] == "nro_documento")
    assert documento["dac"] == "SENSIBLE_CIFRADO" and documento["protegido"] and documento["tipo_real"] == "BYTES"


# ── HU-11: linaje ───────────────────────────────────────────────────────────


def test_linaje_de_persona_de_raw_a_business(cliente):
    datos = get(cliente, "/api/v1/linaje/persona")
    assert [n["capa"] for n in datos["nodos"]] == ["RAW", "MASTER", "BUSINESS", "BUSINESS"]
    documento = next(c for c in datos["campos"] if c["master"] == "nro_documento")
    assert documento["raw"] == "NUM_DOC" and "cifrado determinístico" in documento["transformacion"]
    assert datos["cortes_retenidos"] == [str(JULIO)]


# ── HU-10: glosario ─────────────────────────────────────────────────────────


def test_glosario_busca_sin_tildes_y_filtra_por_dominio(cliente):
    assert get(cliente, "/api/v1/glosario", q="dni")[0]["id"] == "dni"
    assert get(cliente, "/api/v1/glosario", q="poliza")[0]["termino"] == "Póliza"
    assert {t["dominio"] for t in get(cliente, "/api/v1/glosario", dominio="Persona")} == {"Persona"}
    assert get(cliente, "/api/v1/glosario/prima-total")["campos"] == ["poliza.prima_total"]


def test_solo_gobierno_y_admin_editan_el_glosario(cliente):
    termino = {"termino": "Endoso", "definicion": "Modificación de una póliza vigente.", "dominio": "Póliza"}
    assert cliente.put("/api/v1/glosario/endoso", headers=como(LECTOR), json=termino).status_code == 403
    assert cliente.put("/api/v1/glosario/endoso", headers=como(GOBIERNO), json=termino).status_code == 200
    assert get(cliente, "/api/v1/glosario", q="endoso")[0]["id"] == "endoso"


# ── HU-03: reglas configurables desde el portal ─────────────────────────────


def test_admin_cambia_un_umbral_y_queda_auditado(cliente, config):
    respuesta = cliente.patch("/api/v1/reglas/PER-VAL-03", headers=como(ADMIN), json={"umbral": 95})
    assert respuesta.status_code == 200 and respuesta.json()["umbral"] == 95
    assert config.regla("PER-VAL-03")["actualizado_por"] == ADMIN
    assert any(e["recurso"] == "reglas/PER-VAL-03" for e in config.auditoria())


def test_una_regla_invalida_o_con_sql_roto_no_se_guarda(cliente):
    nueva = {"id": "POL-VAL-09", "tabla": "poliza", "dim": "validez", "tipo": "expresion", "umbral": 99, "sev": "MEDIA"}
    sin_cumple = cliente.post("/api/v1/reglas", headers=como(ADMIN), json=nueva)
    assert sin_cumple.status_code == 422 and "requiere 'cumple'" in sin_cumple.json()["message"][0]
    sql_roto = cliente.post("/api/v1/reglas", headers=como(ADMIN), json={**nueva, "cumple": "columna_que_no_existe > 0"})
    assert sql_roto.status_code == 422 and "no compila" in sql_roto.json()["message"][0]
    valida = cliente.post("/api/v1/reglas", headers=como(ADMIN), json={**nueva, "cumple": "moneda != 'EUR'"})
    assert valida.status_code == 201


# ── ejecuciones y usuarios ──────────────────────────────────────────────────


def test_admin_lanza_una_corrida_y_aparece_en_el_portal(cliente):
    antes = len(get(cliente, "/api/v1/ejecuciones"))
    respuesta = cliente.post("/api/v1/ejecuciones", headers=como(ADMIN), json={})
    assert respuesta.status_code == 202 and respuesta.json()["estado"] == "terminada"
    assert len(get(cliente, "/api/v1/ejecuciones")) == antes + 1


def test_admin_gestiona_usuarios_pero_no_se_quita_el_acceso(cliente):
    assert cliente.put("/api/v1/admin/usuarios/nuevo@demo.local", headers=como(ADMIN), json={"rol": "lector"}).status_code == 200
    assert {"email": "nuevo@demo.local", "rol": "lector"} in get(cliente, "/api/v1/admin/usuarios", ADMIN)
    assert cliente.delete(f"/api/v1/admin/usuarios/{ADMIN}", headers=como(ADMIN)).status_code == 422
    assert cliente.delete("/api/v1/admin/usuarios/nuevo@demo.local", headers=como(ADMIN)).status_code == 204


# ── HU-15: rendimiento ──────────────────────────────────────────────────────


@pytest.mark.parametrize("ruta", [
    "/api/v1/resumen", "/api/v1/validaciones", "/api/v1/certificacion", "/api/v1/fuentes",
    "/api/v1/contratos", "/api/v1/linaje/poliza", "/api/v1/glosario", "/api/v1/fuentes/persona/estructura",
])
def test_cada_seccion_responde_en_menos_de_8_segundos(cliente, ruta):
    inicio = time.perf_counter()
    respuesta = cliente.get(ruta, headers=como(LECTOR))
    assert respuesta.status_code == 200
    assert time.perf_counter() - inicio < LIMITE_SEGUNDOS
    assert respuesta.headers["Server-Timing"].startswith("app;dur=")
    assert respuesta.headers["X-Content-Type-Options"] == "nosniff"


def test_sondas_de_salud(cliente):
    assert cliente.get("/health/liveness").json()["estado"] == "ok"
    assert cliente.get("/health/readiness").json()["estado"] == "ok"
