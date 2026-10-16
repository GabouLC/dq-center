"""API del portal (Sprint 3): HU-09 a HU-13 y HU-15, sobre la simulación en DuckDB."""

import re
import time

import pytest
from fastapi.testclient import TestClient

from dqc.api import app
from dqc.api.app import LIMITE_SEGUNDOS, Servicios, crear_app
from dqc.api.autenticacion import Autenticador, Sesiones
from dqc.api.configuracion import USUARIOS_DEMO, ConfiguracionLocal
from dqc.api.datos import FuenteBusiness
from dqc.api.servicios import lanzador_en_proceso, verificador
from datetime import timedelta

from dqc.datagen import generador as g
from dqc.modelo import BUSINESS

from conftest import CONFIG, CORTES_PRUEBA

PRIMERO, ANTES_DEL_RETRASO = CORTES_PRUEBA[0], g.PERSONA_TARDE - timedelta(days=1)

ADMIN, GOBIERNO, LECTOR = "admin@demo.local", "gobierno@demo.local", "lector@demo.local"
SIN_ROL = "sinrol@demo.local"
CLAVE = "clave-de-prueba"
TOKENS: dict[str, str] = {}


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    return ConfiguracionLocal(tmp_path_factory.mktemp("config") / "config.json", CONFIG)


@pytest.fixture(scope="module")
def autenticador(config):
    a = Autenticador(config, Sesiones(b"secreto-de-pruebas".ljust(32, b"-")), iteraciones=1_000)
    for email in [*USUARIOS_DEMO, SIN_ROL]:
        a.fijar(email, CLAVE, debe_cambiar=False)
    return a


@pytest.fixture(scope="module")
def cliente(simulacion, config, fuentes, autenticador):
    servicios = Servicios(
        plataforma=simulacion.plataforma,
        fuente=FuenteBusiness(simulacion.plataforma),
        config=config,
        fuentes_homologacion=fuentes,
        verificar_token=verificador(autenticador),
        lanzar=lanzador_en_proceso(simulacion.plataforma, config, fuentes),
        autenticador=autenticador,
    )
    cliente = TestClient(crear_app(servicios))
    for email in USUARIOS_DEMO:
        TOKENS[email] = entrar(cliente, email, CLAVE).json()["token"]
    # Una cuenta sin rol no puede entrar; su token se firma a mano para probar el 403.
    TOKENS[SIN_ROL] = autenticador.sesiones.emitir(SIN_ROL, config.credencial(SIN_ROL)["clave"])[0]
    return cliente


def entrar(cliente, email: str, clave: str):
    return cliente.post("/api/v1/auth/sesion", json={"email": email, "clave": clave})


def con_token(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def como(email: str) -> dict:
    return con_token(TOKENS[email])


def get(cliente, ruta, email=LECTOR, **params):
    respuesta = cliente.get(ruta, headers=como(email), params=params)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


# ── HU-13: autenticación, roles y auditoría ─────────────────────────────────


def test_sin_token_o_con_token_invalido_responde_401(cliente):
    assert cliente.get("/api/v1/resumen").status_code == 401
    respuesta = cliente.get("/api/v1/resumen", headers=con_token(TOKENS[LECTOR][:-2] + "xx"))
    assert respuesta.status_code == 401
    assert set(respuesta.json()) == {"statusCode", "error", "message"}


def test_cuenta_sin_rol_responde_403_y_queda_auditada(cliente, config):
    assert cliente.get("/api/v1/resumen", headers=como(SIN_ROL)).status_code == 403
    assert any(e["accion"] == "ACCESO_DENEGADO" and e["email"] == SIN_ROL for e in config.auditoria())


def test_inicio_de_sesion_con_correo_y_contrasena(cliente, config):
    respuesta = entrar(cliente, " Lector@Demo.local ", CLAVE)
    assert respuesta.status_code == 200 and not respuesta.json()["debe_cambiar"]
    assert cliente.get("/api/v1/auth/me", headers=con_token(respuesta.json()["token"])).json()["rol"] == "lector"
    assert any(e["accion"] == "INICIO_SESION" and e["email"] == LECTOR for e in config.auditoria())


def test_el_error_de_inicio_no_dice_si_la_cuenta_existe(cliente):
    respuestas = [entrar(cliente, GOBIERNO, "no-es-la-clave"), entrar(cliente, "nadie@demo.local", CLAVE), entrar(cliente, SIN_ROL, CLAVE)]
    assert {r.status_code for r in respuestas} == {401}
    assert len({r.json()["message"] for r in respuestas}) == 1


def test_alta_con_contrasena_temporal_que_obliga_a_cambiarla(cliente, config):
    alta = cliente.put("/api/v1/admin/usuarios/temporal@demo.local", headers=como(ADMIN), json={"rol": "lector"}).json()
    sesion = entrar(cliente, "temporal@demo.local", alta["clave_temporal"]).json()
    assert sesion["debe_cambiar"]
    cabeceras = con_token(sesion["token"])
    assert cliente.get("/api/v1/auth/me", headers=cabeceras).json()["debe_cambiar"]
    assert cliente.get("/api/v1/resumen", headers=cabeceras).status_code == 403

    corta = cliente.post("/api/v1/auth/clave", headers=cabeceras, json={"actual": alta["clave_temporal"], "nueva": "corta"})
    assert corta.status_code == 422
    cambio = cliente.post("/api/v1/auth/clave", headers=cabeceras, json={"actual": alta["clave_temporal"], "nueva": "una frase larga y propia"})
    assert cambio.status_code == 200
    assert cliente.get("/api/v1/resumen", headers=cabeceras).status_code == 401  # el token anterior quedó cerrado
    assert cliente.get("/api/v1/resumen", headers=con_token(cambio.json()["token"])).status_code == 200
    assert any(e["accion"] == "CAMBIO_CLAVE" and e["email"] == "temporal@demo.local" for e in config.auditoria())


def test_restablecer_la_contrasena_cierra_las_sesiones_abiertas(cliente):
    alta = cliente.put("/api/v1/admin/usuarios/olvido@demo.local", headers=como(ADMIN), json={"rol": "gobierno"}).json()
    token = entrar(cliente, "olvido@demo.local", alta["clave_temporal"]).json()["token"]
    nueva = cliente.post("/api/v1/admin/usuarios/olvido@demo.local/clave", headers=como(ADMIN)).json()["clave_temporal"]
    assert nueva != alta["clave_temporal"]
    assert cliente.get("/api/v1/auth/me", headers=con_token(token)).status_code == 401
    assert entrar(cliente, "olvido@demo.local", alta["clave_temporal"]).status_code == 401
    assert entrar(cliente, "olvido@demo.local", nueva).status_code == 200
    assert cliente.post("/api/v1/admin/usuarios/olvido@demo.local/clave", headers=como(LECTOR)).status_code == 403


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
    lector = get(cliente, ruta, LECTOR, corte=str(PRIMERO))
    gobierno = get(cliente, ruta, GOBIERNO, corte=str(PRIMERO))
    fila_l, fila_g = lector["muestras"][0]["fila"], gobierno["muestras"][0]["fila"]
    assert fila_l["fecha_nacimiento"] == "•••• restringido" and fila_g["fecha_nacimiento"] == "1900-01-01"
    assert fila_l["nro_documento"] == fila_g["nro_documento"] == "•••• cifrado"  # PII: nunca en claro
    assert "fecha_nacimiento" in lector["campos_restringidos"] and gobierno["campos_restringidos"] == []
    assert any(e["accion"] == "ACCESO_RESTRINGIDO" and e["email"] == LECTOR for e in config.auditoria())


# ── HU-08: el portal solo lee BUSINESS ──────────────────────────────────────


def test_el_portal_solo_lee_la_capa_business(simulacion):
    leidas = []

    class Espia:
        def consultar(self, sql):
            leidas.append(sql)
            return simulacion.plataforma.consultar(sql)

    fuente = FuenteBusiness(Espia())
    fuente.precargar()
    fuente.fallidos(fuente.ejecuciones()[-1]["id_ejecucion"], "PER-VAL-04", "persona", 5)
    fuente.incidencias("pago", PRIMERO, 5)
    tablas = {t for sql in leidas for t in re.findall(r"\b(?:FROM|JOIN)\s+([\w.]+)", sql)}
    assert tablas and {t.split(".")[0] for t in tablas} == {BUSINESS}


# ── HU-09: dashboard ────────────────────────────────────────────────────────


def test_resumen_muestra_tendencia_pass_y_certificacion(cliente):
    cortes = {c["fecha_corte"]: c for c in get(cliente, "/api/v1/resumen")["cortes"]}
    assert len(cortes) == len(CORTES_PRUEBA)
    assert cortes[str(g.PERSONA_TARDE)]["global"] < cortes[str(ANTES_DEL_RETRASO)]["global"] < 100
    ultimo = cortes[str(CORTES_PRUEBA[-1])]
    assert 0 < ultimo["pct_pass"] < 100 and set(ultimo["pct_pass_tabla"]) == set(g.TABLAS_CORTE)
    assert cortes[str(g.REPROCESO)]["certificacion"]["poliza"] == "NO_CERTIFICADO"


def test_validaciones_de_un_corte_empiezan_por_las_fallas(cliente):
    datos = get(cliente, "/api/v1/validaciones", corte=str(g.PERSONA_TARDE))
    assert len(datos["reglas"]) == 48
    assert (datos["reglas"][0]["id_regla"], datos["reglas"][0]["estado"]) == ("GEN-OPO-01", "FALLA")
    solo_n1 = get(cliente, "/api/v1/validaciones", corte=str(g.PERSONA_TARDE), nivel="N1")["reglas"]
    assert solo_n1 and {r["nivel"] for r in solo_n1} == {"N1"}


def test_comparar_cortes_muestra_primero_lo_que_empeoro(cliente):
    filas = get(cliente, "/api/v1/validaciones/comparar", a=str(ANTES_DEL_RETRASO), b=str(g.PERSONA_TARDE))["reglas"]
    empeoraron = [(f["id_regla"], f["tabla"]) for f in filas if f["empeoro"]]
    assert ("GEN-OPO-01", "persona") in empeoraron
    assert filas[0]["empeoro"]


# ── HU-12: certificación integral ───────────────────────────────────────────


def test_certificacion_integral_del_dia_de_la_fuga(cliente):
    dia, registros = next(iter(g.FUGA_PII.items()))
    datos = get(cliente, "/api/v1/certificacion", corte=str(dia))
    siniestro = next(t for t in datos["tablas"] if t["tabla"] == "siniestro")
    assert siniestro["estado"] == "NO_CERTIFICADO"
    assert siniestro["calidad"]["ok"] and not siniestro["privacidad"]["ok"]
    assert siniestro["privacidad"]["hallazgos"] == [{"tipo": "PII_EN_CLARO", "columna": "causa", "bloqueante": True, "registros": registros}]
    assert siniestro["trazabilidad"]["publicado"] is False
    persona = next(t for t in datos["tablas"] if t["tabla"] == "persona")
    assert all(c["protegido"] for c in persona["privacidad"]["campos_cifrados"])
    assert persona["trazabilidad"]["objeto_business"] == "dq_business.p_persona"
    assert datos["historia"][str(g.PERSONA_TARDE)]["persona"] == "NO_CERTIFICADO"


# ── fuentes y contrato ──────────────────────────────────────────────────────


def test_fuentes_muestran_rechazos_volumen_e_incidencias(cliente):
    tablas = {t["tabla"]: t for t in get(cliente, "/api/v1/fuentes")}
    rechazada = [c for c in tablas["siniestro"]["cargas"] if c["estado"] == "RECHAZADA"]
    assert [c["detalle"] for c in rechazada] == ["faltan columnas: ESTADO_SINIESTRO"]
    reproceso = next(c for c in tablas["poliza"]["cargas"] if c["fecha_corte"] == str(g.REPROCESO))
    assert reproceso["variacion_pct"] == pytest.approx(22, abs=0.3)
    assert all(c["incidencias"] > 0 for c in tablas["pago"]["cargas"])


def test_estructura_detecta_columna_nueva(cliente):
    cortes = {c["fecha_corte"]: c for c in get(cliente, "/api/v1/fuentes/poliza/estructura")["cortes"]}
    assert cortes[str(g.CANAL_VENTA)]["agregadas"] == ["canal_venta"]
    assert cortes[str(CORTES_PRUEBA[-1])]["agregadas"] == []


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
    assert datos["cortes_retenidos"] == [str(g.PERSONA_TARDE), str(g.DOCUMENTO_NULO)]


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
    alta = cliente.put("/api/v1/admin/usuarios/nuevo@demo.local", headers=como(ADMIN), json={"rol": "lector"})
    assert alta.status_code == 200
    token = entrar(cliente, "nuevo@demo.local", alta.json()["clave_temporal"]).json()["token"]
    usuarios = {u["email"]: u for u in get(cliente, "/api/v1/admin/usuarios", ADMIN)}
    assert usuarios["nuevo@demo.local"]["rol"] == "lector" and usuarios["nuevo@demo.local"]["clave_temporal"]
    assert usuarios[LECTOR]["ultimo_acceso"] is not None and not usuarios[LECTOR]["bloqueada"]
    assert cliente.delete(f"/api/v1/admin/usuarios/{ADMIN}", headers=como(ADMIN)).status_code == 422
    assert cliente.delete("/api/v1/admin/usuarios/nuevo@demo.local", headers=como(ADMIN)).status_code == 204
    assert cliente.get("/api/v1/auth/me", headers=con_token(token)).status_code == 401


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


def test_una_solicitud_lenta_queda_registrada_en_la_auditoria(cliente, config, monkeypatch):
    monkeypatch.setattr(app, "LIMITE_SEGUNDOS", 0.0)  # cualquier solicitud supera el límite
    cliente.get("/health/liveness")
    assert any(e["accion"] == "RENDIMIENTO_LENTO" and e["recurso"] == "/health/liveness" for e in config.auditoria())


def test_sondas_de_salud(cliente):
    assert cliente.get("/health/liveness").json()["estado"] == "ok"
    assert cliente.get("/health/readiness").json()["estado"] == "ok"


def test_sin_simulacion_en_vivo_el_estado_dice_inactivo(cliente):
    assert get(cliente, "/api/v1/vivo") == {"activo": False, "version": 0, "eventos": []}
    assert cliente.post("/api/v1/vivo/adelantar", headers=como(ADMIN)).status_code == 404
