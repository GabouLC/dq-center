"""Inicio de sesión con correo y contraseña (HU-13).

- Las contraseñas se guardan como PBKDF2-SHA256 con sal propia; nunca en claro.
- La sesión es un token firmado con HMAC-SHA256 que vence a las 8 horas. Lleva un
  sello de la contraseña vigente: cambiarla, restablecerla o quitar el acceso
  cierra las sesiones abiertas de esa cuenta.
- Cinco intentos fallidos seguidos bloquean la cuenta 15 minutos. El intento se cuenta antes
  de verificar la contraseña, así que varios en paralelo no se saltan el límite, y un correo
  que no existe se bloquea igual que uno que existe: el bloqueo no revela qué cuentas hay.
  Equivocar la contraseña actual al cambiarla también cuenta.
- Una contraseña temporal (alta o restablecimiento) obliga a cambiarla al entrar.
- Acceso cerrado por defecto: sin rol en el portal no se puede entrar, aunque la
  contraseña sea correcta, y el mensaje no distingue un caso del otro.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

PREFIJO = "dqs1"
ITERACIONES = 600_000
DURACION = timedelta(hours=8)
MAX_INTENTOS = 5
BLOQUEO = timedelta(minutes=15)
LARGO_MINIMO = 10
# Sin 0/O ni 1/l/I: la contraseña temporal se dicta o se copia a mano.
ALFABETO_TEMPORAL = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"


def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode()


def _de_b64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def cifrar_clave(clave: str, iteraciones: int = ITERACIONES) -> str:
    sal = secrets.token_bytes(16)
    resumen = hashlib.pbkdf2_hmac("sha256", clave.encode(), sal, iteraciones)
    return f"pbkdf2_sha256${iteraciones}${_b64(sal)}${_b64(resumen)}"


def clave_correcta(clave: str, guardada: str) -> bool:
    try:
        _, iteraciones, sal, resumen = guardada.split("$")
        calculado = hashlib.pbkdf2_hmac("sha256", clave.encode(), _de_b64(sal), int(iteraciones))
    except ValueError:
        return False
    return hmac.compare_digest(calculado, _de_b64(resumen))


def sello(clave_guardada: str) -> str:
    return hashlib.sha256(clave_guardada.encode()).hexdigest()[:16]


def problemas_de_clave(clave: str, email: str) -> list[str]:
    """Reglas de una contraseña nueva: largo antes que composición (NIST 800-63B)."""
    problemas = []
    if len(clave) < LARGO_MINIMO:
        problemas.append(f"debe tener al menos {LARGO_MINIMO} caracteres")
    usuario = email.split("@")[0].lower()
    if usuario and usuario in clave.lower():
        problemas.append("no puede contener tu usuario")
    if len(set(clave)) < 4:
        problemas.append("es demasiado repetitiva")
    return problemas


def clave_temporal() -> str:
    return "".join(secrets.choice(ALFABETO_TEMPORAL) for _ in range(12))


class Sesiones:
    """Tokens dqs1.<datos>.<firma>: autocontenidos, así que no hace falta guardar sesiones."""

    def __init__(self, secreto: bytes, duracion: timedelta = DURACION, reloj: Callable[[], float] = time.time):
        if len(secreto) < 32:
            raise ValueError("el secreto de sesión debe tener al menos 32 bytes")
        self._secreto = secreto
        self.duracion = duracion
        self.reloj = reloj

    def _firmar(self, cuerpo: str) -> str:
        return _b64(hmac.new(self._secreto, f"{PREFIJO}.{cuerpo}".encode(), hashlib.sha256).digest())

    def emitir(self, email: str, clave_guardada: str) -> tuple[str, int]:
        expira = int(self.reloj() + self.duracion.total_seconds())
        datos = {"sub": email, "exp": expira, "sello": sello(clave_guardada)}
        cuerpo = _b64(json.dumps(datos, separators=(",", ":")).encode())
        return f"{PREFIJO}.{cuerpo}.{self._firmar(cuerpo)}", expira

    def leer(self, token: str) -> dict:
        prefijo, cuerpo, firma = token.split(".")
        if prefijo != PREFIJO or not hmac.compare_digest(firma, self._firmar(cuerpo)):
            raise ValueError("firma inválida")
        datos = json.loads(_de_b64(cuerpo))
        if datos["exp"] < self.reloj():
            raise ValueError("sesión vencida")
        return datos


class ErrorAcceso(Exception):
    def __init__(self, codigo: int, mensaje: str | list[str]):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


@dataclass
class Autenticador:
    """Usa la configuración del portal (local o Firestore) para guardar las credenciales."""

    config: object
    sesiones: Sesiones
    iteraciones: int = ITERACIONES
    _senuelo: str = field(init=False, repr=False)
    # correo -> [intentos contados, bloqueado hasta (epoch), último intento (epoch)]
    _intentos: dict[str, list[float]] = field(init=False, repr=False, default_factory=dict)
    _candado: threading.Lock = field(init=False, repr=False, default_factory=threading.Lock)

    def __post_init__(self):
        # Una cuenta inexistente cuesta lo mismo que una contraseña equivocada.
        self._senuelo = cifrar_clave(secrets.token_urlsafe(16), self.iteraciones)

    def _ahora(self) -> datetime:
        return datetime.fromtimestamp(self.sesiones.reloj(), timezone.utc)

    def _auditar(self, accion: str, email: str, detalle: str) -> None:
        self.config.auditar({"accion": accion, "email": email, "recurso": "sesion", "detalle": detalle})

    def es_token(self, token: str) -> bool:
        return token.startswith(f"{PREFIJO}.")

    # ── bloqueo por intentos ────────────────────────────────────────────────

    def _reservar(self, email: str, credencial: dict | None) -> None:
        """Cuenta el intento antes de verificar la contraseña; 423 si la cuenta está bloqueada.

        Con cinco intentos ya contados (fallidos o todavía en curso) no se admite otro.
        """
        ahora = self.sesiones.reloj()
        with self._candado:
            if len(self._intentos) > 5_000:  # correos inventados: no dejar crecer la memoria
                vigentes = ahora - BLOQUEO.total_seconds()
                self._intentos = {e: v for e, v in self._intentos.items() if v[1] > ahora or v[2] > vigentes}
            contados, hasta, _ = self._intentos.get(email, [0, 0.0, 0.0])
            if credencial and credencial.get("bloqueado_hasta"):
                hasta = max(hasta, datetime.fromisoformat(credencial["bloqueado_hasta"]).timestamp())
            if hasta <= ahora and credencial:
                contados = max(contados, int(credencial.get("intentos", 0)))
            if hasta > ahora or contados >= MAX_INTENTOS:
                minutos = max(1, round(((hasta if hasta > ahora else ahora + BLOQUEO.total_seconds()) - ahora) / 60))
                raise ErrorAcceso(423, f"La cuenta está bloqueada por intentos fallidos. Prueba de nuevo en {minutos} min.")
            self._intentos[email] = [contados + 1, 0.0, ahora]

    def _fallo(self, email: str, credencial: dict | None, detalle: str) -> None:
        """Deja contado el intento fallido; al quinto, bloquea la cuenta 15 minutos."""
        ahora = self.sesiones.reloj()
        with self._candado:
            contados, hasta, _ = self._intentos.get(email, [1, 0.0, ahora])
            bloquear = hasta <= ahora and contados >= MAX_INTENTOS
            if bloquear:
                hasta = ahora + BLOQUEO.total_seconds()
                self._intentos[email] = [0, hasta, ahora]
        self._auditar("INICIO_FALLIDO", email, detalle)
        if bloquear:
            if credencial:
                bloqueo = datetime.fromtimestamp(hasta, timezone.utc).isoformat()
                self.config.guardar_credencial(email, {"intentos": 0, "bloqueado_hasta": bloqueo})
            self._auditar("CUENTA_BLOQUEADA", email, f"{MAX_INTENTOS} intentos fallidos seguidos")
        elif credencial:
            self.config.guardar_credencial(email, {"intentos": int(contados)})

    def _olvidar(self, email: str) -> None:
        with self._candado:
            self._intentos.pop(email, None)

    # ── sesión y contraseña ─────────────────────────────────────────────────

    def entrar(self, email: str, clave: str) -> dict:
        email = email.strip().lower()
        credencial = self.config.credencial(email)
        self._reservar(email, credencial)
        correcta = clave_correcta(clave, credencial["clave"] if credencial else self._senuelo)
        if not correcta or email not in self.config.usuarios():
            self._fallo(email, credencial, "contraseña incorrecta o cuenta sin acceso")
            raise ErrorAcceso(401, "Correo o contraseña incorrectos")

        self._olvidar(email)
        ahora = self._ahora()
        self.config.guardar_credencial(email, {"intentos": 0, "bloqueado_hasta": None, "ultimo_acceso": ahora.isoformat()})
        self._auditar("INICIO_SESION", email, "correo y contraseña")
        token, expira = self.sesiones.emitir(email, credencial["clave"])
        return {"token": token, "expira": expira, "debe_cambiar": bool(credencial.get("debe_cambiar"))}

    def verificar(self, token: str) -> str:
        datos = self.sesiones.leer(token)
        credencial = self.config.credencial(datos["sub"])
        if not credencial or sello(credencial["clave"]) != datos["sello"]:
            raise ValueError("sesión cerrada: la contraseña cambió o se quitó el acceso")
        return datos["sub"]

    def debe_cambiar(self, email: str) -> bool:
        credencial = self.config.credencial(email)
        return bool(credencial and credencial.get("debe_cambiar"))

    def cambiar(self, email: str, actual: str, nueva: str) -> dict:
        credencial = self.config.credencial(email)
        self._reservar(email, credencial)
        if not credencial or not clave_correcta(actual, credencial["clave"]):
            self._fallo(email, credencial, "contraseña actual incorrecta al cambiarla")
            raise ErrorAcceso(422, ["la contraseña actual no es correcta"])
        self._olvidar(email)
        problemas = problemas_de_clave(nueva, email)
        if nueva == actual:
            problemas.append("debe ser distinta de la actual")
        if problemas:
            raise ErrorAcceso(422, [f"la contraseña nueva {p}" for p in problemas])
        guardada = cifrar_clave(nueva, self.iteraciones)
        self.config.guardar_credencial(email, {"clave": guardada, "debe_cambiar": False})
        self._auditar("CAMBIO_CLAVE", email, "el usuario cambió su contraseña")
        token, expira = self.sesiones.emitir(email, guardada)
        return {"token": token, "expira": expira, "debe_cambiar": False}

    def fijar(self, email: str, clave: str, debe_cambiar: bool) -> None:
        self._olvidar(email)
        self.config.guardar_credencial(email, {
            "clave": cifrar_clave(clave, self.iteraciones), "debe_cambiar": debe_cambiar,
            "intentos": 0, "bloqueado_hasta": None,
        })

    def asignar_temporal(self, email: str) -> str:
        """Contraseña de un solo uso para un alta o un restablecimiento; desbloquea la cuenta."""
        temporal = clave_temporal()
        self.fijar(email, temporal, debe_cambiar=True)
        return temporal

    def estado(self, email: str) -> dict:
        credencial = self.config.credencial(email) or {}
        bloqueo = credencial.get("bloqueado_hasta")
        return {
            "ultimo_acceso": credencial.get("ultimo_acceso"),
            "bloqueada": bool(bloqueo and datetime.fromisoformat(bloqueo) > self._ahora()),
            "clave_temporal": bool(credencial.get("debe_cambiar")),
            "sin_clave": not credencial,
        }
