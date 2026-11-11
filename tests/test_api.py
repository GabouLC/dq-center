"""API del portal (Sprint 3): HU-09 a HU-13 y HU-15, sobre la simulación en DuckDB."""

import re
import threading
import time

import pytest
from fastapi.testclient import TestClient

from dqc.api import app, vistas
from dqc.api.app import LIMITE_SEGUNDOS, Servicios, crear_app
from dqc.api.autenticacion import Autenticador, Sesiones
from dqc.api.configuracion import USUARIOS_DEMO, ConfiguracionLocal
from dqc.api.datos import FuenteBusiness
from dqc.api.servicios import lanzador_en_proceso, verificador
from datetime import date, timedelta

from dqc.datagen import generador as g
from dqc.modelo import BUSINESS
from dqc.motor.reglas import expandir

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


def test_incidencias_ocultan_los_valores_sensibles_al_lector(cliente, config):
    ruta = "/api/v1/fuentes/pago/incidencias"
    lector = get(cliente, ruta, LECTOR, corte=str(PRIMERO))
    gobierno = get(cliente, ruta, GOBIERNO, corte=str(PRIMERO))
    assert lector and all(f["valores"] == "IMPORTE=•••• restringido" for f in lector)
    assert all(f["valores"].startswith("IMPORTE=") and "••••" not in f["valores"] for f in gobierno)
    assert any(e["accion"] == "ACCESO_RESTRINGIDO" and e["recurso"] == ruta and e["email"] == LECTOR
               for e in config.auditoria())


def test_la_contrasena_temporal_sin_cambiar_queda_auditada(cliente, config):
    alta = cliente.put("/api/v1/admin/usuarios/pendiente@demo.local", headers=como(ADMIN), json={"rol": "lector"}).json()
    token = entrar(cliente, "pendiente@demo.local", alta["clave_temporal"]).json()["token"]
    assert cliente.get("/api/v1/resumen", headers=con_token(token)).status_code == 403
    assert any(e["accion"] == "ACCESO_DENEGADO" and e["email"] == "pendiente@demo.local"
               and e["detalle"] == "contraseña temporal sin cambiar" for e in config.auditoria())


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


def test_con_la_cache_vencida_solo_una_peticion_relee_las_vistas():
    """HU-15: diez usuarios abren una sección justo cuando vence la caché de 10 minutos."""
    consultas, salida = [], threading.Event()

    class Lenta:
        def consultar(self, sql):
            consultas.append(sql)
            salida.wait(0.3)  # lo que tarda BigQuery: da tiempo a que lleguen las demás peticiones
            return []

    fuente = FuenteBusiness(Lenta())
    hilos = [threading.Thread(target=fuente.ejecuciones) for _ in range(10)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert len(consultas) == 7  # una lectura de las 7 vistas, no 70

    fuente.invalidar()  # un corte recién publicado: la siguiente lectura sí vuelve a las vistas
    fuente.ejecuciones()
    assert len(consultas) == 14


def test_una_lectura_empezada_antes_de_invalidar_no_queda_vigente():
    """Si el corte se publica mientras se lee, la caché no se da por buena durante 10 minutos."""
    consultas = []
    fuente = None

    class Invalida:
        def consultar(self, sql):
            consultas.append(sql)
            if len(consultas) == 1:
                fuente.invalidar()  # llega un corte nuevo en medio de la lectura
            return []

    fuente = FuenteBusiness(Invalida())
    fuente.precargar()
    fuente.ejecuciones()
    assert len(consultas) == 14  # la segunda lectura se hizo: la primera no quedó vigente


# ── HU-09: dashboard ────────────────────────────────────────────────────────


def test_resumen_muestra_tendencia_pass_y_certificacion(cliente):
    cortes = {c["fecha_corte"]: c for c in get(cliente, "/api/v1/resumen")["cortes"]}
    assert len(cortes) == len(CORTES_PRUEBA)
    assert cortes[str(g.PERSONA_TARDE)]["global"] < cortes[str(ANTES_DEL_RETRASO)]["global"] < 100
    ultimo = cortes[str(CORTES_PRUEBA[-1])]
    assert 0 < ultimo["pct_pass"] < 100 and set(ultimo["pct_pass_tabla"]) == set(g.TABLAS_CORTE)
    assert cortes[str(g.REPROCESO)]["certificacion"]["poliza"] == "NO_CERTIFICADO"


def test_validaciones_de_un_corte_empiezan_por_las_fallas(cliente, reglas):
    datos = get(cliente, "/api/v1/validaciones", corte=str(g.PERSONA_TARDE))
    assert len(datos["reglas"]) == len(expandir([r for r in reglas if r.activa]))  # sin fijar el total del catálogo
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


def negocio_ve(cliente, tabla: str, dia) -> str | None:
    """El último día certificado (hasta `dia`) que la ficha de certificación dice que sigue viendo negocio."""
    datos = get(cliente, "/api/v1/certificacion", corte=str(dia))
    return next(t for t in datos["tablas"] if t["tabla"] == tabla)["trazabilidad"]["ultimo_certificado"]


def test_cada_tabla_retenida_dice_que_dia_sigue_viendo_negocio(cliente):
    assert negocio_ve(cliente, "persona", g.PERSONA_TARDE) == "2026-07-13"
    assert negocio_ve(cliente, "siniestro", min(g.FUGA_PII)) == "2026-08-06"
    # Un día que sí se publicó es su propio último día certificado.
    assert negocio_ve(cliente, "persona", ANTES_DEL_RETRASO) == str(ANTES_DEL_RETRASO)
    # Póliza el 28 de septiembre: aquí solo se procesan algunos días y POL-CON-03 ya la retiene desde el 26, así que
    # negocio sigue en el último día publicado que haya. (Con la corrida completa es el 27: ver la prueba siguiente.)
    historia = get(cliente, "/api/v1/certificacion", corte="2026-09-28")["historia"]
    ultimo = max(d for d, e in historia.items() if d <= "2026-09-28" and e["poliza"] != "NO_CERTIFICADO")
    assert negocio_ve(cliente, "poliza", date(2026, 9, 28)) == ultimo < "2026-09-28"


def test_el_ultimo_dia_certificado_ignora_los_retenidos_y_los_dias_posteriores():
    historia = {
        date(2026, 7, 1): {"persona": "CERTIFICADO_CON_OBSERVACIONES", "pago": "NO_CERTIFICADO"},
        date(2026, 7, 2): {"persona": "NO_CERTIFICADO", "pago": "NO_CERTIFICADO"},
        date(2026, 7, 3): {"persona": "NO_CERTIFICADO"},
        date(2026, 7, 4): {"persona": "CERTIFICADO"},
    }
    assert vistas.ultimo_certificado(historia, "persona", date(2026, 7, 3)) == date(2026, 7, 1)  # con observaciones también se publica
    assert vistas.ultimo_certificado(historia, "persona", date(2026, 7, 4)) == date(2026, 7, 4)
    assert vistas.ultimo_certificado(historia, "pago", date(2026, 7, 4)) is None  # todavía no hay ningún día certificado
    assert vistas.ultimo_certificado(historia, "vehiculo", date(2026, 7, 4)) is None
    # La corrida completa: Póliza se publica hasta el 27 de septiembre y POL-CON-03 la retiene del 28 al 30.
    poliza = {date(2026, 9, d): {"poliza": "CERTIFICADO_CON_OBSERVACIONES" if d <= 27 else "NO_CERTIFICADO"} for d in range(24, 31)}
    assert [vistas.ultimo_certificado(poliza, "poliza", date(2026, 9, d)) for d in (27, 28, 30)] == [date(2026, 9, 27)] * 3


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


def motivos_del_dia(linaje: dict, dia, tipo: str | None = None) -> list[dict]:
    retenido = next(r for r in linaje["retenidos"] if r["fecha_corte"] == str(dia))
    return [m for m in retenido["motivos"] if tipo is None or m["tipo"] == tipo]


def test_linaje_de_persona_dice_por_que_se_retuvo_cada_dia(cliente):
    datos = get(cliente, "/api/v1/linaje/persona")
    assert [r["fecha_corte"] for r in datos["retenidos"]] == datos["cortes_retenidos"] == [str(g.PERSONA_TARDE), str(g.DOCUMENTO_NULO)]
    assert all(set(m) == {"tipo", "id", "texto"} for r in datos["retenidos"] for m in r["motivos"])
    # El 14 de julio llegó tarde el archivo; el 22, las personas con DNI llegaron sin documento.
    assert {"tipo": "regla", "id": "GEN-OPO-01", "texto": "el archivo llegó tarde"} in motivos_del_dia(datos, g.PERSONA_TARDE)
    assert {"tipo": "regla", "id": "PER-COM-01", "texto": "faltan datos obligatorios en nro_documento"} in motivos_del_dia(datos, g.DOCUMENTO_NULO)
    assert not motivos_del_dia(datos, g.PERSONA_TARDE, "privacidad")


def test_linaje_de_siniestro_explica_la_fuga_de_datos_personales(cliente):
    datos = get(cliente, "/api/v1/linaje/siniestro")
    assert set(map(str, g.FUGA_PII)) <= {r["fecha_corte"] for r in datos["retenidos"]}
    for dia, registros in g.FUGA_PII.items():
        assert motivos_del_dia(datos, dia, "privacidad") == [
            {"tipo": "privacidad", "id": "PII_EN_CLARO", "texto": f"datos personales sin cifrar en causa · {registros} registros"}
        ]
    # Lo que se publicó no aparece entre los retenidos.
    assert not {r["fecha_corte"] for r in datos["retenidos"]} & set(datos["cortes_publicados"])


def test_el_texto_del_motivo_se_arma_con_la_dimension_de_la_regla():
    assert vistas.texto_motivo_regla("GEN-VOL-01", {"dim": "volumetria", "tipo": "variacion_volumen"}) == "el volumen de registros cambió más de lo normal"
    assert vistas.texto_motivo_regla("GEN-VOL-02", {"dim": "volumetria", "tipo": "minimo_filas"}) == "llegaron muy pocos registros"
    assert vistas.texto_motivo_regla("PER-UNI-01", {"dim": "unicidad", "campos": ["tipo_documento", "nro_documento"]}) == (
        "hay registros duplicados en tipo_documento y nro_documento"
    )
    # Una regla que ya no está en el catálogo se explica por el código de su id; sin código, con una frase general.
    assert vistas.texto_motivo_regla("POL-INT-02", None) == "hay referencias a registros que no existen"
    assert vistas.texto_motivo_regla("XXX", None) == "falló una regla grave"
    uno = {"id_ejecucion": "e", "reglas_bloqueantes": ""}
    hallazgo = {"id_ejecucion": "e", "tipo": "PII_EN_CLARO", "columna": "causa", "bloqueante": True}
    assert vistas.motivos_de_retencion(uno, [hallazgo], {})[0]["texto"] == "datos personales sin cifrar en causa · 1 registro"
    assert vistas.motivos_de_retencion({**uno, "reglas_bloqueantes": "SIN_DATOS"}, [], {})[0]["texto"] == "ninguna de sus reglas pudo evaluarse"


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
    invalido = {**termino, "termino": 123}
    assert cliente.put("/api/v1/glosario/endoso", headers=como(GOBIERNO), json=invalido).status_code == 400
    assert get(cliente, "/api/v1/glosario", q="endoso")[0]["termino"] == "Endoso"


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
    antes = len(get(cliente, "/api/v1/ejecuciones", ADMIN))
    respuesta = cliente.post("/api/v1/ejecuciones", headers=como(ADMIN), json={})
    assert respuesta.status_code == 202 and respuesta.json()["estado"] == "terminada"
    assert len(get(cliente, "/api/v1/ejecuciones", ADMIN)) == antes + 1


@pytest.mark.parametrize("ruta", ["/api/v1/reglas", "/api/v1/ejecuciones"])
def test_reglas_y_ejecuciones_solo_se_leen_con_permiso_de_configurar(cliente, config, ruta):
    # Son los módulos Reglas y Ejecuciones del portal: la API responde igual que el menú.
    for email in (LECTOR, GOBIERNO):
        assert cliente.get(ruta, headers=como(email)).status_code == 403
        assert any(e["accion"] == "ACCESO_DENEGADO" and e["email"] == email and e["recurso"] == ruta for e in config.auditoria())
    assert get(cliente, ruta, ADMIN)


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


@pytest.mark.parametrize("ruta, email", [
    # las siete secciones de consulta, como lector
    ("/api/v1/resumen", LECTOR), ("/api/v1/validaciones", LECTOR), ("/api/v1/certificacion", LECTOR),
    ("/api/v1/fuentes", LECTOR), ("/api/v1/contratos", LECTOR), ("/api/v1/linaje/poliza", LECTOR),
    ("/api/v1/glosario", LECTOR), ("/api/v1/fuentes/persona/estructura", LECTOR),
    # las cuatro de administración, como admin: las 11 secciones del portal
    ("/api/v1/reglas", ADMIN), ("/api/v1/ejecuciones", ADMIN),
    ("/api/v1/admin/usuarios", ADMIN), ("/api/v1/admin/auditoria", ADMIN),
])
def test_cada_seccion_responde_en_menos_de_8_segundos(cliente, ruta, email):
    inicio = time.perf_counter()
    respuesta = cliente.get(ruta, headers=como(email))
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
