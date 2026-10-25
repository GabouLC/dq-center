"""API del Portal Smart-DQ (FastAPI). Rutas de negocio con el prefijo /api/v1.

Seguridad (HU-13): se entra con correo y contraseña (dqc.api.autenticacion) o con
Google vía Firebase; cada ruta exige un token válido y un rol registrado, y el rol
decide qué módulos responde. Una contraseña temporal solo deja cambiarla. Los campos SENSIBLE solo se muestran a gobierno y
admin, y cada acceso denegado o restringido queda en la auditoría.
Rendimiento (HU-15): cada solicitud se mide; si pasa de 8 s, se registra.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from dqc import __version__
from dqc.api import vistas
from dqc.api.autenticacion import Autenticador, ErrorAcceso
from dqc.api.configuracion import ROLES
from dqc.api.datos import FuenteBusiness
from dqc.modelo import TABLAS_CORTE
from dqc.motor.reglas import CAMPOS_REGLA, Regla, a_documento, desde_documento, expandir, validar
from dqc.motor.sql import ContextoSQL, sql_regla
from dqc.pipeline.configuracion import Fuente, cifrados, clasificacion

log = logging.getLogger("dqc.api")
LIMITE_SEGUNDOS = 8.0

# Módulos del portal: (clave, nombre, permiso que lo habilita), en el orden del menú.
MODULOS = [
    ("resumen", "Resumen", "leer"),
    ("validaciones", "Validaciones", "leer"),
    ("certificacion", "Certificación", "leer"),
    ("fuentes", "Fuentes", "leer"),
    ("contratos", "Contrato de datos", "leer"),
    ("linaje", "Linaje", "leer"),
    ("glosario", "Glosario", "leer"),
    ("reglas", "Reglas", "configurar"),
    ("ejecuciones", "Ejecuciones", "configurar"),
    ("usuarios", "Usuarios y roles", "administrar"),
    ("auditoria", "Auditoría", "administrar"),
]
# Con una contraseña temporal solo se puede ver el perfil y cambiarla.
RUTAS_CLAVE_TEMPORAL = {"/api/v1/auth/me", "/api/v1/auth/clave"}
PERMISOS = {
    "lector": {"leer"},
    "gobierno": {"leer", "ver_sensibles", "editar_glosario"},
    "admin": {"leer", "ver_sensibles", "editar_glosario", "configurar", "administrar"},
}


@dataclass
class Usuario:
    email: str
    rol: str


@dataclass
class Servicios:
    plataforma: object
    fuente: FuenteBusiness
    config: object
    fuentes_homologacion: dict[str, Fuente]
    verificar_token: Callable[[str], str]
    lanzar: Callable[[date | None, str], dict]
    origenes: list[str] = field(default_factory=list)
    autenticador: Autenticador | None = None
    vivo: object | None = None  # dqc.api.vivo.Simulador


class PedidoEjecucion(BaseModel):
    fecha_corte: date | None = None


class PedidoRol(BaseModel):
    rol: Literal["admin", "gobierno", "lector"]


class PedidoPausa(BaseModel):
    pausado: bool


class PedidoSesion(BaseModel):
    email: str = Field(max_length=254)
    clave: str = Field(max_length=256)


class PedidoCambioClave(BaseModel):
    actual: str = Field(max_length=256)
    nueva: str = Field(max_length=256)


class PedidoTermino(BaseModel):
    termino: str = Field(min_length=1, max_length=120)
    definicion: str = Field(min_length=1, max_length=2_000)
    dominio: str = Field(min_length=1, max_length=60)
    sinonimos: list[str] = Field(default_factory=list, max_length=30)
    campos: list[str] = Field(default_factory=list, max_length=30)


def _error(codigo: int, mensaje) -> JSONResponse:
    nombres = {400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 409: "Conflict",
               422: "Unprocessable Entity", 423: "Locked", 500: "Internal Server Error", 503: "Service Unavailable"}
    return JSONResponse({"statusCode": codigo, "error": nombres.get(codigo, "Error"), "message": mensaje}, status_code=codigo)


def crear_app(s: Servicios, precargar: bool = True) -> FastAPI:
    @asynccontextmanager
    async def ciclo_de_vida(_):
        # El primer usuario no debería esperar la lectura en frío de BigQuery.
        if precargar:
            threading.Thread(target=_precargar, daemon=True).start()
        if s.vivo:
            s.vivo.iniciar()
        yield

    def _precargar():
        try:
            s.fuente.precargar()
        except Exception:  # noqa: BLE001 - si falla, la primera solicitud lo reintenta
            log.warning("no se pudo precargar las vistas de contrato", exc_info=True)

    app = FastAPI(
        title="Smart-DQ API", version=__version__, docs_url="/api/v1/docs", openapi_url="/api/v1/openapi.json",
        lifespan=ciclo_de_vida,
    )
    if s.origenes:
        app.add_middleware(
            CORSMiddleware, allow_origins=s.origenes, allow_methods=["*"], allow_headers=["Authorization", "Content-Type"]
        )

    # ── errores con el formato del documento de arquitectura ───────────────

    @app.exception_handler(StarletteHTTPException)
    async def _http(_, exc: StarletteHTTPException):
        return _error(exc.status_code, exc.detail)

    @app.exception_handler(RequestValidationError)
    async def _validacion(_, exc: RequestValidationError):
        return _error(400, [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()])

    @app.exception_handler(Exception)
    async def _inesperado(_, exc: Exception):
        log.exception("error no controlado")
        return _error(500, "No se pudo leer: error interno")

    # ── rendimiento (HU-15) ────────────────────────────────────────────────

    @app.middleware("http")
    async def _medir(request: Request, call_next):
        inicio = time.perf_counter()
        respuesta = await call_next(request)
        duracion = time.perf_counter() - inicio
        respuesta.headers["Server-Timing"] = f"app;dur={duracion * 1000:.0f}"
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        if duracion > LIMITE_SEGUNDOS:
            log.warning("solicitud lenta: %s %.1f s", request.url.path, duracion)
            await run_in_threadpool(s.config.auditar, {
                "accion": "RENDIMIENTO_LENTO", "email": None, "recurso": request.url.path,
                "detalle": f"{duracion:.1f} s (límite {LIMITE_SEGUNDOS:.0f} s)",
            })
        return respuesta

    # ── autenticación y autorización (HU-13) ───────────────────────────────

    def usuario_actual(request: Request, authorization: str | None = Header(default=None)) -> Usuario:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Falta el token de sesión")
        try:
            email = s.verificar_token(authorization.removeprefix("Bearer ").strip()).lower()
        except Exception:  # noqa: BLE001 - cualquier falla de verificación es un token inválido
            raise HTTPException(401, "Token inválido o vencido") from None
        rol = s.config.usuarios().get(email)
        if rol is None:
            s.config.auditar({"accion": "ACCESO_DENEGADO", "email": email, "recurso": request.url.path,
                              "detalle": "cuenta sin rol en el portal"})
            raise HTTPException(403, f"{email} no tiene acceso al portal")
        if request.url.path not in RUTAS_CLAVE_TEMPORAL and s.autenticador and s.autenticador.debe_cambiar(email):
            s.config.auditar({"accion": "ACCESO_DENEGADO", "email": email, "recurso": request.url.path,
                              "detalle": "contraseña temporal sin cambiar"})
            raise HTTPException(403, "Cambia tu contraseña temporal para continuar")
        return Usuario(email, rol)

    def autenticador() -> Autenticador:
        if s.autenticador is None:
            raise HTTPException(404, "El inicio de sesión con contraseña no está habilitado")
        return s.autenticador

    def requiere(permiso: str):
        def dependencia(request: Request, u: Usuario = Depends(usuario_actual)) -> Usuario:
            if permiso not in PERMISOS[u.rol]:
                s.config.auditar({"accion": "ACCESO_DENEGADO", "email": u.email, "recurso": request.url.path,
                                  "detalle": f"el rol {u.rol} no tiene el permiso {permiso}"})
                raise HTTPException(403, "No tiene acceso al módulo solicitado")
            return u
        return dependencia

    lector, configurar, administrar = requiere("leer"), requiere("configurar"), requiere("administrar")

    # ── apoyo ──────────────────────────────────────────────────────────────

    def ultimas() -> dict[date, dict]:
        return vistas.ultimas_por_corte(s.fuente.ejecuciones())

    def ejecucion_de(corte: date | None) -> dict:
        todas = ultimas()
        if not todas:
            raise HTTPException(404, "Todavía no hay ejecuciones")
        if corte is None:
            return list(todas.values())[-1]
        if corte not in todas:
            raise HTTPException(404, f"No hay ejecuciones del corte {corte}")
        return todas[corte]

    def esquema_de(id_ejecucion: str) -> dict[str, list[tuple[str, str]]]:
        esquema: dict[str, list[tuple[str, str]]] = {}
        for f in sorted(vistas.de_la_ejecucion(s.fuente.esquemas(), id_ejecucion), key=lambda f: f["posicion"]):
            esquema.setdefault(f["tabla"], []).append((f["columna"], f["tipo"]))
        return esquema

    def tabla_valida(tabla: str) -> str:
        if tabla not in TABLAS_CORTE:
            raise HTTPException(404, f"No existe la tabla {tabla}")
        return tabla

    # ── salud ──────────────────────────────────────────────────────────────

    @app.get("/health/liveness")
    def vivo():
        return {"estado": "ok", "version": __version__}

    @app.get("/health/readiness")
    def listo():
        try:
            s.fuente.ejecuciones()
        except Exception as e:  # noqa: BLE001
            raise HTTPException(503, f"No se pudo leer: {type(e).__name__}") from None
        return {"estado": "ok"}

    # ── sesión ─────────────────────────────────────────────────────────────

    @app.post("/api/v1/auth/sesion")
    def entrar(pedido: PedidoSesion, a: Autenticador = Depends(autenticador)):
        """Correo y contraseña -> token de sesión. Un solo mensaje para correo o contraseña errados."""
        try:
            return a.entrar(pedido.email, pedido.clave)
        except ErrorAcceso as e:
            raise HTTPException(e.codigo, e.mensaje) from None

    @app.post("/api/v1/auth/clave")
    def cambiar_clave(pedido: PedidoCambioClave, u: Usuario = Depends(usuario_actual), a: Autenticador = Depends(autenticador)):
        """Cambia la contraseña y devuelve un token nuevo: las demás sesiones de la cuenta se cierran."""
        try:
            return a.cambiar(u.email, pedido.actual, pedido.nueva)
        except ErrorAcceso as e:
            raise HTTPException(e.codigo, e.mensaje) from None

    @app.get("/api/v1/auth/me")
    def yo(u: Usuario = Depends(usuario_actual)):
        permisos = PERMISOS[u.rol]
        return {
            "email": u.email,
            "rol": u.rol,
            "permisos": sorted(permisos),
            "modulos": [{"clave": c, "nombre": n} for c, n, p in MODULOS if p in permisos],
            "debe_cambiar": bool(s.autenticador and s.autenticador.debe_cambiar(u.email)),
        }

    # ── simulación en vivo ─────────────────────────────────────────────────

    @app.get("/api/v1/vivo")
    def vivo(desde: int = Query(0, ge=0), _: Usuario = Depends(lector)):
        """Estado de la simulación en vivo y los eventos posteriores a `desde`."""
        if s.vivo is None:
            return {"activo": False, "version": 0, "eventos": []}
        return s.vivo.estado(desde)

    @app.post("/api/v1/vivo/pausa")
    def pausar_vivo(pedido: PedidoPausa, u: Usuario = Depends(configurar)):
        if s.vivo is None:
            raise HTTPException(404, "La simulación en vivo no está activa")
        s.vivo.pausar(pedido.pausado)
        s.config.auditar({"accion": "EJECUTAR", "email": u.email, "recurso": "vivo",
                          "detalle": "pausa" if pedido.pausado else "reanuda"})
        return s.vivo.estado(10**9)

    @app.post("/api/v1/vivo/adelantar")
    def adelantar_vivo(_: Usuario = Depends(configurar)):
        """Hace llegar el siguiente archivo ahora."""
        if s.vivo is None:
            raise HTTPException(404, "La simulación en vivo no está activa")
        s.vivo.adelantar()
        return {"estado": "ok"}

    # ── HU-09: resumen ─────────────────────────────────────────────────────

    @app.get("/api/v1/cortes")
    def cortes(_: Usuario = Depends(lector)):
        """Cortes evaluados con su score global y cuántas tablas quedaron sin certificar."""
        resumen = vistas.resumen(ultimas(), s.fuente.resultados(), s.fuente.certificaciones())
        return [
            {
                "fecha_corte": c["fecha_corte"],
                "id_ejecucion": c["id_ejecucion"],
                "terminada_en": c["terminada_en"],
                "global": c["global"],
                "no_certificadas": sum(e == "NO_CERTIFICADO" for e in c["certificacion"].values()),
            }
            for c in resumen["cortes"]
        ]

    @app.get("/api/v1/resumen")
    def resumen(_: Usuario = Depends(lector)):
        return vistas.resumen(ultimas(), s.fuente.resultados(), s.fuente.certificaciones())

    # ── validaciones ───────────────────────────────────────────────────────

    @app.get("/api/v1/validaciones")
    def validaciones(
        corte: date | None = None, tabla: str | None = None, nivel: str | None = None,
        estado: str | None = None, _: Usuario = Depends(lector),
    ):
        e = ejecucion_de(corte)
        filas = vistas.validaciones(
            vistas.de_la_ejecucion(s.fuente.resultados(), e["id_ejecucion"]), {r["id"]: r for r in s.config.reglas()}
        )
        filas = [
            f for f in filas
            if (not tabla or f["tabla"] == tabla) and (not nivel or f["nivel"] == nivel) and (not estado or f["estado"] == estado)
        ]
        return {"fecha_corte": e["fecha_corte"], "id_ejecucion": e["id_ejecucion"], "reglas": filas}

    @app.get("/api/v1/validaciones/comparar")
    def comparar(a: date, b: date, _: Usuario = Depends(lector)):
        resultados = s.fuente.resultados()
        ea, eb = ejecucion_de(a), ejecucion_de(b)
        return {
            "a": a, "b": b,
            "reglas": vistas.comparar(
                vistas.de_la_ejecucion(resultados, ea["id_ejecucion"]), vistas.de_la_ejecucion(resultados, eb["id_ejecucion"])
            ),
        }

    @app.get("/api/v1/validaciones/{id_regla}/{tabla}/fallidos")
    def fallidos(
        request: Request, id_regla: str, tabla: str, corte: date | None = None,
        limite: int = Query(20, ge=1, le=100), u: Usuario = Depends(lector),
    ):
        tabla_valida(tabla)
        e = ejecucion_de(corte)
        total, filas = s.fuente.fallidos(e["id_ejecucion"], id_regla, tabla, limite)
        dac = clasificacion(s.config.contratos()).get(tabla, {})
        ve_sensibles = "ver_sensibles" in PERMISOS[u.rol]
        muestras, restringidos = [], set()
        for f in filas:
            fila, ocultos = vistas.enmascarar(f["detalle"], dac, ve_sensibles)
            restringidos |= set(ocultos)
            muestras.append({"llave": f["llave"], "fila": fila})
        if restringidos:
            s.config.auditar({"accion": "ACCESO_RESTRINGIDO", "email": u.email, "recurso": request.url.path,
                              "detalle": f"campos sensibles ocultos: {', '.join(sorted(restringidos))}"})
        return {"fecha_corte": e["fecha_corte"], "id_regla": id_regla, "tabla": tabla, "total": total,
                "muestras": muestras, "campos_restringidos": sorted(restringidos)}

    # ── HU-12: certificación integral ──────────────────────────────────────

    @app.get("/api/v1/certificacion")
    def certificacion(corte: date | None = None, _: Usuario = Depends(lector)):
        e = ejecucion_de(corte)
        tablas = vistas.certificacion(
            e["fecha_corte"],
            vistas.de_la_ejecucion(s.fuente.certificaciones(), e["id_ejecucion"]),
            vistas.de_la_ejecucion(s.fuente.hallazgos(), e["id_ejecucion"]),
            vistas.de_la_ejecucion(s.fuente.resultados(), e["id_ejecucion"]),
            s.config.contratos(),
            esquema_de(e["id_ejecucion"]),
        )
        historia = {
            c: {x["tabla"]: x["estado"] for x in vistas.de_la_ejecucion(s.fuente.certificaciones(), ej["id_ejecucion"])}
            for c, ej in ultimas().items()
        }
        return {"fecha_corte": e["fecha_corte"], "tablas": tablas, "historia": historia}

    # ── fuentes ────────────────────────────────────────────────────────────

    @app.get("/api/v1/fuentes")
    def fuentes(_: Usuario = Depends(lector)):
        return vistas.fuentes(s.fuente.cargas(), s.fuente.incidencias_por_corte(), s.config.contratos())

    @app.get("/api/v1/fuentes/{tabla}/estructura")
    def estructura(tabla: str, _: Usuario = Depends(lector)):
        return vistas.estructura(tabla_valida(tabla), ultimas(), s.fuente.esquemas())

    @app.get("/api/v1/fuentes/{tabla}/incidencias")
    def incidencias(
        request: Request, tabla: str, corte: date, limite: int = Query(50, ge=1, le=200), u: Usuario = Depends(lector),
    ):
        filas = s.fuente.incidencias(tabla_valida(tabla), corte, limite)
        destino_de = {c.origen.upper(): c.destino for c in s.fuentes_homologacion[tabla].columnas}
        dac = clasificacion(s.config.contratos()).get(tabla, {})
        ve_sensibles = "ver_sensibles" in PERMISOS[u.rol]
        restringidos = set()
        for f in filas:
            f["valores"], ocultos = vistas.enmascarar_valores(f["valores"], destino_de, dac, ve_sensibles)
            restringidos |= set(ocultos)
        if restringidos:
            s.config.auditar({"accion": "ACCESO_RESTRINGIDO", "email": u.email, "recurso": request.url.path,
                              "detalle": f"campos sensibles ocultos: {', '.join(sorted(restringidos))}"})
        return filas

    # ── contrato de datos ──────────────────────────────────────────────────

    @app.get("/api/v1/contratos")
    def contratos(_: Usuario = Depends(lector)):
        e = ejecucion_de(None)
        reglas = [desde_documento(d) for d in s.config.reglas()]
        return vistas.contratos(
            s.config.contratos(), reglas, esquema_de(e["id_ejecucion"]),
            vistas.de_la_ejecucion(s.fuente.resultados(), e["id_ejecucion"]),
        )

    # ── HU-11: linaje ──────────────────────────────────────────────────────

    @app.get("/api/v1/linaje/{tabla}")
    def linaje(tabla: str, _: Usuario = Depends(lector)):
        tabla_valida(tabla)
        ids = {e["id_ejecucion"] for e in ultimas().values()}
        certs = [c for c in s.fuente.certificaciones() if c["tabla"] == tabla and c["id_ejecucion"] in ids]
        return vistas.linaje(tabla, s.fuentes_homologacion[tabla], s.config.contratos()[tabla], certs)

    # ── HU-10: glosario ────────────────────────────────────────────────────

    @app.get("/api/v1/glosario")
    def glosario(q: str | None = None, dominio: str | None = None, _: Usuario = Depends(lector)):
        return vistas.buscar_glosario(s.config.glosario(), q, dominio)

    @app.get("/api/v1/glosario/{id_termino}")
    def termino(id_termino: str, _: Usuario = Depends(lector)):
        for t in s.config.glosario():
            if t["id"] == id_termino:
                return t
        raise HTTPException(404, f"No existe el término {id_termino}")

    @app.put("/api/v1/glosario/{id_termino}")
    def guardar_termino(id_termino: str, datos: PedidoTermino, u: Usuario = Depends(requiere("editar_glosario"))):
        doc = {"id": id_termino, **datos.model_dump()}
        s.config.guardar_termino(doc, u.email)
        s.config.auditar({"accion": "ACTUALIZAR", "email": u.email, "recurso": f"glosario/{id_termino}", "detalle": doc["termino"]})
        return doc

    # ── HU-03: reglas configurables ────────────────────────────────────────

    def validar_regla(datos: dict) -> Regla:
        errores = validar(datos)
        if errores:
            raise HTTPException(422, errores)
        regla = Regla(**datos)
        if regla.activa:
            todas = ultimas()
            if todas:
                corte, e = list(todas.items())[-1]
                ctx = ContextoSQL(
                    funciones=s.plataforma.funciones,
                    cifrados=cifrados(s.config.contratos()),
                    columnas={t: [c for c, _ in cols] for t, cols in esquema_de(e["id_ejecucion"]).items()},
                )
                for r in expandir([regla]):
                    error = s.plataforma.probar(sql_regla(r, corte, ctx))
                    if error:
                        raise HTTPException(422, [f"el SQL de la regla no compila: {error}"])
        return regla

    @app.get("/api/v1/reglas")
    def reglas(_: Usuario = Depends(lector)):
        return sorted(s.config.reglas(), key=lambda r: r["id"])

    @app.post("/api/v1/reglas", status_code=201)
    def crear_regla(datos: dict = Body(...), u: Usuario = Depends(configurar)):
        if datos.get("id") and s.config.regla(datos["id"]):
            raise HTTPException(409, f"Ya existe la regla {datos['id']}")
        regla = validar_regla(datos)
        s.config.guardar_regla(a_documento(regla), u.email)
        s.config.auditar({"accion": "CREAR", "email": u.email, "recurso": f"reglas/{regla.id}", "detalle": regla.tipo})
        return s.config.regla(regla.id)

    @app.patch("/api/v1/reglas/{id_regla}")
    def editar_regla(id_regla: str, cambios: dict = Body(...), u: Usuario = Depends(configurar)):
        actual = s.config.regla(id_regla)
        if actual is None:
            raise HTTPException(404, f"No existe la regla {id_regla}")
        if cambios.get("id", id_regla) != id_regla:
            raise HTTPException(422, ["el id de una regla no se puede cambiar"])
        datos = {k: v for k, v in {**actual, **cambios}.items() if k in CAMPOS_REGLA and v is not None}
        regla = validar_regla(datos)
        s.config.guardar_regla(a_documento(regla), u.email)
        accion = "DESACTIVAR" if actual.get("activa", True) and not regla.activa else "ACTUALIZAR"
        s.config.auditar({"accion": accion, "email": u.email, "recurso": f"reglas/{id_regla}",
                          "detalle": ", ".join(f"{k}={v}" for k, v in cambios.items())})
        return s.config.regla(id_regla)

    # ── ejecuciones ────────────────────────────────────────────────────────

    @app.get("/api/v1/ejecuciones")
    def ejecuciones(_: Usuario = Depends(lector)):
        return sorted(s.fuente.ejecuciones(), key=lambda e: e["terminada_en"], reverse=True)[:100]

    @app.post("/api/v1/ejecuciones", status_code=202)
    def lanzar(pedido: PedidoEjecucion, u: Usuario = Depends(configurar)):
        resultado = s.lanzar(pedido.fecha_corte, u.email)
        s.fuente.invalidar()
        s.config.auditar({"accion": "EJECUTAR", "email": u.email, "recurso": "ejecuciones",
                          "detalle": str(pedido.fecha_corte or "último corte")})
        return resultado

    # ── usuarios, roles y auditoría ────────────────────────────────────────

    @app.get("/api/v1/admin/usuarios")
    def usuarios(_: Usuario = Depends(administrar)):
        return [
            {"email": e, "rol": r, **(s.autenticador.estado(e) if s.autenticador else {})}
            for e, r in sorted(s.config.usuarios().items())
        ]

    @app.put("/api/v1/admin/usuarios/{email}")
    def guardar_usuario(email: str, pedido: PedidoRol, u: Usuario = Depends(administrar)):
        email = email.lower()
        if "@" not in email:
            raise HTTPException(422, ["correo inválido"])
        if email == u.email and pedido.rol != "admin":
            raise HTTPException(422, ["no puedes quitarte el rol admin"])
        anterior = s.config.usuarios().get(email)
        s.config.guardar_usuario(email, pedido.rol, u.email)
        s.config.auditar({"accion": "CREAR" if anterior is None else "ACTUALIZAR", "email": u.email,
                          "recurso": f"usuarios/{email}", "detalle": f"rol {anterior or '-'} -> {pedido.rol}"})
        respuesta = {"email": email, "rol": pedido.rol}
        # Un alta recibe una contraseña temporal; se muestra una sola vez al administrador.
        if s.autenticador and s.config.credencial(email) is None:
            respuesta["clave_temporal"] = s.autenticador.asignar_temporal(email)
        return respuesta

    @app.post("/api/v1/admin/usuarios/{email}/clave")
    def restablecer_clave(email: str, u: Usuario = Depends(administrar), a: Autenticador = Depends(autenticador)):
        """Contraseña temporal nueva: cierra las sesiones abiertas y desbloquea la cuenta."""
        email = email.lower()
        if email not in s.config.usuarios():
            raise HTTPException(404, f"No existe el usuario {email}")
        temporal = a.asignar_temporal(email)
        s.config.auditar({"accion": "RESTABLECER_CLAVE", "email": u.email, "recurso": f"usuarios/{email}",
                          "detalle": "contraseña temporal nueva"})
        return {"email": email, "clave_temporal": temporal}

    @app.delete("/api/v1/admin/usuarios/{email}", status_code=204)
    def borrar_usuario(email: str, u: Usuario = Depends(administrar)):
        email = email.lower()
        if email == u.email:
            raise HTTPException(422, ["no puedes quitarte el acceso a ti mismo"])
        if email not in s.config.usuarios():
            raise HTTPException(404, f"No existe el usuario {email}")
        s.config.borrar_usuario(email)
        s.config.auditar({"accion": "DESACTIVAR", "email": u.email, "recurso": f"usuarios/{email}", "detalle": "acceso retirado"})

    @app.get("/api/v1/admin/auditoria")
    def auditoria(limite: int = Query(200, ge=1, le=1000), _: Usuario = Depends(administrar)):
        return s.config.auditoria(limite)

    return app


assert set(PERMISOS) == set(ROLES)
