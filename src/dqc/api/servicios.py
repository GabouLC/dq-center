"""Piezas de la API que dependen del entorno: sesiones, verificación de tokens y lanzamiento de corridas."""

from __future__ import annotations

import os
import secrets
from contextlib import nullcontext
from collections.abc import Callable
from datetime import date
from pathlib import Path

from dqc.api.autenticacion import Autenticador
from dqc.api.configuracion import USUARIOS_DEMO

from dqc.modelo import BUSINESS
from dqc.motor.reglas import desde_documento
from dqc.pipeline.flujo import Flujo


def lista_env(variable: str) -> list[str]:
    return [v.strip() for v in os.environ.get(variable, "").split(",") if v.strip()]


def verificador_firebase(proyecto: str):
    import firebase_admin
    from firebase_admin import auth

    if not firebase_admin._apps:
        firebase_admin.initialize_app(options={"projectId": proyecto})

    def verificar(token: str) -> str:
        datos = auth.verify_id_token(token)
        if not datos.get("email_verified"):
            raise ValueError("correo no verificado")
        return datos["email"]

    return verificar


def secreto_sesiones(archivo: Path) -> bytes:
    """DQC_SECRETO (Secret Manager en Cloud Run) o, fuera de Cloud Run, uno aleatorio guardado junto a los datos."""
    if valor := os.environ.get("DQC_SECRETO"):
        return valor.encode()
    if os.environ.get("K_SERVICE"):
        raise RuntimeError("Define DQC_SECRETO (Secret Manager) para firmar las sesiones en Cloud Run")
    if not archivo.exists():
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(secrets.token_urlsafe(48), encoding="utf-8")
    return archivo.read_text(encoding="utf-8").strip().encode()


def verificador(autenticador: Autenticador, firebase: Callable[[str], str] | None = None) -> Callable[[str], str]:
    """Tokens propios (dqs1.*) y, si está configurado, los de Google vía Firebase."""

    def verificar(token: str) -> str:
        if autenticador.es_token(token):
            return autenticador.verificar(token)
        if firebase:
            return firebase(token)
        raise ValueError("token desconocido")

    return verificar


def preparar_demo(autenticador: Autenticador, clave: str) -> None:
    """Da a las cuentas de demostración la contraseña DQC_CLAVE_DEMO (solo fuera de Cloud Run)."""
    if os.environ.get("K_SERVICE"):
        raise RuntimeError("Las cuentas de demostración no pueden usarse en Cloud Run: define DQC_DEMO=0")
    usuarios = autenticador.config.usuarios()
    for email in USUARIOS_DEMO:
        if email in usuarios and autenticador.config.credencial(email) is None:
            autenticador.fijar(email, clave, debe_cambiar=False)


def lanzador_en_proceso(plataforma, config, fuentes, candado=None):
    """Corre el motor y el Gate dentro de la API (modo local y sandbox sin Cloud Run Jobs)."""

    def lanzar(corte: date | None, email: str) -> dict:
        with candado or nullcontext():
            return _lanzar(corte, email)

    def _lanzar(corte: date | None, email: str) -> dict:
        if corte is None:
            # El último corte ya evaluado: el de hoy puede estar a medio llegar (simulación en vivo).
            corte = plataforma.consultar(f"SELECT MAX(fecha_corte) AS corte FROM {BUSINESS}.v_calidad_ejecuciones")[0]["corte"]
        reglas = [desde_documento(d) for d in config.reglas()]
        flujo = Flujo(plataforma, fuentes, config.contratos(), reglas)
        ejecucion, certificaciones = flujo.evaluar(corte, origen=f"manual:{email}")
        return {
            "estado": "terminada",
            "id_ejecucion": ejecucion.id_ejecucion,
            "fecha_corte": corte,
            "certificaciones": {c.tabla: c.estado for c in certificaciones},
        }

    return lanzar


def lanzador_job(nombre_job: str):
    """Lanza el Cloud Run Job del motor; la corrida aparece en el portal cuando termina."""
    from google.cloud import run_v2

    cliente = run_v2.JobsClient()

    def lanzar(corte: date | None, email: str) -> dict:
        args = ["ejecutar", "--origen", f"manual:{email}"] + (["--corte", corte.isoformat()] if corte else [])
        sobrescritura = run_v2.RunJobRequest.Overrides(
            container_overrides=[run_v2.RunJobRequest.Overrides.ContainerOverride(args=args)]
        )
        operacion = cliente.run_job(request=run_v2.RunJobRequest(name=nombre_job, overrides=sobrescritura))
        return {"estado": "lanzada", "operacion": operacion.operation.name, "fecha_corte": corte}

    return lanzar
