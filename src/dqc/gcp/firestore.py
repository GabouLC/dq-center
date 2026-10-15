"""Firestore: reglas, contratos y usuarios del portal.

Colecciones:
  reglas/{id}        una regla del catálogo (sin expandir), con activa y auditoría
  contratos/{tabla}  dueño, consumidores y campos pactados de cada tabla
  usuarios/{email}   rol (admin o lector)
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import yaml
from google.cloud import firestore

from dqc.motor.reglas import CAMPOS_REGLA, Regla, desde_dict

REGLAS, CONTRATOS, USUARIOS = "reglas", "contratos", "usuarios"
ROLES = {"admin", "lector"}


def regla_a_doc(regla: Regla) -> dict:
    return {k: v for k, v in asdict(regla).items() if v is not None and v != []}


def doc_a_regla(doc: dict) -> Regla:
    """Ignora los metadatos (actualizado_en, actualizado_por) que no son parte de la regla."""
    return desde_dict({k: v for k, v in doc.items() if k in CAMPOS_REGLA})


def cargar_reglas(db: firestore.Client) -> list[Regla]:
    return sorted((doc_a_regla(d.to_dict()) for d in db.collection(REGLAS).stream()), key=lambda r: r.id)


def cargar_contratos(ruta: str | Path) -> dict[str, dict]:
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)["contratos"]


def sembrar(
    db: firestore.Client,
    reglas: list[Regla],
    contratos: dict[str, dict],
    admins: list[str],
    reemplazar: bool = False,
) -> dict[str, int]:
    """Carga la configuración inicial. Sin reemplazar, no toca lo que ya existe."""
    ahora = datetime.now(timezone.utc)
    escritos = {REGLAS: 0, CONTRATOS: 0, USUARIOS: 0}
    documentos = [
        (REGLAS, r.id, {**regla_a_doc(r), "actualizado_en": ahora, "actualizado_por": "semilla"})
        for r in reglas
    ]
    documentos += [(CONTRATOS, tabla, {**c, "actualizado_en": ahora}) for tabla, c in contratos.items()]
    documentos += [(USUARIOS, email.lower(), {"rol": "admin", "creado_en": ahora}) for email in admins]

    lote = db.batch()
    for coleccion, id_doc, datos in documentos:
        ref = db.collection(coleccion).document(id_doc)
        if not reemplazar and ref.get().exists:
            continue
        lote.set(ref, datos)
        escritos[coleccion] += 1
    lote.commit()
    return escritos
