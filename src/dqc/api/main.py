"""Arranque de la API: uvicorn dqc.api.main:app (o python -m dqc.api).

Variables de entorno:
  DQC_MODO      local (DuckDB + configuración en JSON, por defecto) o gcp (BigQuery + Firestore)
  DQC_AUTH      demo (usuarios de demostración, solo fuera de Cloud Run) o firebase
  DQC_DB        archivo DuckDB del modo local (por defecto data/dq.duckdb)
  DQC_CONFIG    carpeta de configuración (por defecto config)
  DQC_PROYECTO  proyecto de GCP; DQC_SANDBOX=1 si no tiene facturación
  DQC_JOB       projects/<p>/locations/<r>/jobs/<j>: las corridas a demanda lanzan ese Cloud Run Job
  DQC_ORIGENES  orígenes permitidos por CORS, separados por coma
  DQC_ADMINS    correos con rol admin en el modo local, separados por coma
"""

from __future__ import annotations

import os
from pathlib import Path

from dqc.api.app import Servicios, crear_app
from dqc.api.configuracion import USUARIOS_DEMO, ConfiguracionLocal
from dqc.api.datos import FuenteBusiness
from dqc.api.servicios import lista_env, lanzador_en_proceso, lanzador_job, verificador_demo, verificador_firebase
from dqc.pipeline.configuracion import cargar_homologacion


def crear_servicios() -> Servicios:
    config_dir = Path(os.environ.get("DQC_CONFIG", "config"))
    fuentes = cargar_homologacion(config_dir / "homologacion.yaml")
    modo = os.environ.get("DQC_MODO", "local")

    if modo == "local":
        from dqc.plataforma.local import PlataformaDuckDB

        plataforma = PlataformaDuckDB(os.environ.get("DQC_DB", "data/dq.duckdb"))
        config = ConfiguracionLocal(Path(os.environ.get("DQC_CONFIG_LOCAL", "data/config_local.json")), config_dir, lista_env("DQC_ADMINS"))
    else:
        from google.cloud import bigquery, firestore

        from dqc.gcp.firestore import ConfiguracionFirestore
        from dqc.plataforma.bigquery import UBICACION, PlataformaBigQuery

        proyecto = os.environ["DQC_PROYECTO"]
        plataforma = PlataformaBigQuery(bigquery.Client(project=proyecto, location=UBICACION), os.environ.get("DQC_SANDBOX") == "1")
        config = ConfiguracionFirestore(firestore.Client(project=proyecto))

    demo = os.environ.get("DQC_AUTH", "demo" if modo == "local" else "firebase") == "demo"
    usuarios_demo = list(USUARIOS_DEMO) if demo else []
    verificar = verificador_demo(usuarios_demo) if demo else verificador_firebase(os.environ["DQC_PROYECTO"])
    job = os.environ.get("DQC_JOB")
    return Servicios(
        plataforma=plataforma,
        fuente=FuenteBusiness(plataforma),
        config=config,
        fuentes_homologacion=fuentes,
        verificar_token=verificar,
        lanzar=lanzador_job(job) if job else lanzador_en_proceso(plataforma, config, fuentes),
        origenes=lista_env("DQC_ORIGENES") or ["http://localhost:5173"],
        usuarios_demo=usuarios_demo,
    )


app = crear_app(crear_servicios())
