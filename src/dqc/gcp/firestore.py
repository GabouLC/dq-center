"""Firestore: reglas, contratos y usuarios del portal.

Colecciones:
  reglas/{id}        una regla del catálogo (sin expandir), con activa y auditoría
  contratos/{tabla}  dueño, consumidores y campos pactados de cada tabla
  usuarios/{email}   rol (admin o lector)
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import yaml
from google.cloud import firestore

from dqc.motor.reglas import Regla, a_documento, desde_documento

REGLAS, CONTRATOS, USUARIOS = "reglas", "contratos", "usuarios"


def cargar_reglas(db: firestore.Client) -> list[Regla]:
    return sorted((desde_documento(d.to_dict()) for d in db.collection(REGLAS).stream()), key=lambda r: r.id)


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
        (REGLAS, r.id, {**a_documento(r), "actualizado_en": ahora, "actualizado_por": "semilla"})
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


class ConfiguracionFirestore:
    """Configuración del portal en Firestore. Los roles se guardan 30 s en memoria."""

    def __init__(self, db: firestore.Client):
        self.db = db
        self._usuarios: tuple[float, dict[str, str]] | None = None

    def reglas(self) -> list[dict]:
        return [d.to_dict() for d in self.db.collection(REGLAS).stream()]

    def regla(self, id_regla: str) -> dict | None:
        doc = self.db.collection(REGLAS).document(id_regla).get()
        return doc.to_dict() if doc.exists else None

    def guardar_regla(self, doc: dict, usuario: str) -> None:
        self.db.collection(REGLAS).document(doc["id"]).set(
            {**doc, "actualizado_en": datetime.now(timezone.utc), "actualizado_por": usuario}
        )

    def contratos(self) -> dict[str, dict]:
        return {d.id: d.to_dict() for d in self.db.collection(CONTRATOS).stream()}

    def usuarios(self) -> dict[str, str]:
        if self._usuarios is None or self._usuarios[0] < time.monotonic():
            roles = {d.id: d.to_dict()["rol"] for d in self.db.collection(USUARIOS).stream()}
            self._usuarios = (time.monotonic() + 30, roles)
        return self._usuarios[1]

    def guardar_usuario(self, email: str, rol: str, usuario: str) -> None:
        self.db.collection(USUARIOS).document(email).set(
            {"rol": rol, "actualizado_en": datetime.now(timezone.utc), "actualizado_por": usuario}, merge=True
        )
        self._usuarios = None

    def borrar_usuario(self, email: str) -> None:
        self.db.collection(USUARIOS).document(email).delete()
        self._usuarios = None
