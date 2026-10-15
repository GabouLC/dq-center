"""Piezas de la API que dependen del entorno: verificación de tokens y lanzamiento de corridas."""

from __future__ import annotations

import os
from datetime import date

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


def verificador_demo(usuarios: list[str]):
    if os.environ.get("K_SERVICE"):
        raise RuntimeError("El modo demo no puede usarse en Cloud Run: define DQC_AUTH=firebase")

    def verificar(token: str) -> str:
        email = token.removeprefix("demo:")
        if not token.startswith("demo:") or email not in usuarios:
            raise ValueError("usuario demo desconocido")
        return email

    return verificar


def lanzador_en_proceso(plataforma, config, fuentes):
    """Corre el motor y el Gate dentro de la API (modo local y sandbox sin Cloud Run Jobs)."""

    def lanzar(corte: date | None, email: str) -> dict:
        if corte is None:
            corte = plataforma.consultar(
                f"SELECT MAX(fecha_corte) AS corte FROM {BUSINESS}.v_calidad_cargas WHERE estado = 'EXITOSA'"
            )[0]["corte"]
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
