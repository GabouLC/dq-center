"""Firestore: configuración del portal.

Colecciones:
  reglas/{id}        una regla del catálogo (sin expandir), con activa y auditoría
  contratos/{tabla}  dueño, consumidores y campos pactados con su clasificación DAC
  glosario/{id}      términos de negocio (HU-10)
  usuarios/{email}   rol: admin, gobierno o lector (HU-13)
  auditoria/{auto}   cambios de configuración y accesos denegados o restringidos
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from google.cloud import firestore

from dqc.motor.reglas import Regla, a_documento, desde_documento

REGLAS, CONTRATOS, GLOSARIO, USUARIOS, AUDITORIA = "reglas", "contratos", "glosario", "usuarios", "auditoria"
VIGENCIA_CACHE = 30  # segundos


def cargar_reglas(db: firestore.Client) -> list[Regla]:
    return sorted((desde_documento(d.to_dict()) for d in db.collection(REGLAS).stream()), key=lambda r: r.id)


def sembrar(
    db: firestore.Client,
    reglas: list[Regla],
    contratos: dict[str, dict],
    glosario: list[dict],
    admins: list[str],
    reemplazar: bool = False,
) -> dict[str, int]:
    """Carga la configuración inicial. Sin reemplazar, no toca lo que ya existe."""
    ahora = datetime.now(timezone.utc)
    escritos = {REGLAS: 0, CONTRATOS: 0, GLOSARIO: 0, USUARIOS: 0}
    documentos = [
        (REGLAS, r.id, {**a_documento(r), "actualizado_en": ahora, "actualizado_por": "semilla"})
        for r in reglas
    ]
    documentos += [(CONTRATOS, tabla, {**c, "actualizado_en": ahora}) for tabla, c in contratos.items()]
    documentos += [(GLOSARIO, t["id"], {**t, "actualizado_en": ahora, "actualizado_por": "semilla"}) for t in glosario]
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
    """Misma interfaz que dqc.api.configuracion.ConfiguracionLocal, sobre Firestore."""

    def __init__(self, db: firestore.Client):
        self.db = db
        self._cache: dict[str, tuple[float, object]] = {}

    def _leer(self, clave: str, cargar):
        guardado = self._cache.get(clave)
        if guardado is None or guardado[0] < time.monotonic():
            guardado = (time.monotonic() + VIGENCIA_CACHE, cargar())
            self._cache[clave] = guardado
        return guardado[1]

    def _coleccion(self, nombre: str) -> dict[str, dict]:
        return self._leer(nombre, lambda: {d.id: d.to_dict() for d in self.db.collection(nombre).stream()})

    def _escribir(self, coleccion: str, id_doc: str, datos: dict, usuario: str) -> None:
        self.db.collection(coleccion).document(id_doc).set(
            {**datos, "actualizado_en": datetime.now(timezone.utc), "actualizado_por": usuario}
        )
        self._cache.pop(coleccion, None)

    def reglas(self) -> list[dict]:
        return list(self._coleccion(REGLAS).values())

    def regla(self, id_regla: str) -> dict | None:
        return self._coleccion(REGLAS).get(id_regla)

    def guardar_regla(self, doc: dict, usuario: str) -> None:
        self._escribir(REGLAS, doc["id"], doc, usuario)

    def contratos(self) -> dict[str, dict]:
        return self._coleccion(CONTRATOS)

    def glosario(self) -> list[dict]:
        return list(self._coleccion(GLOSARIO).values())

    def guardar_termino(self, doc: dict, usuario: str) -> None:
        self._escribir(GLOSARIO, doc["id"], doc, usuario)

    def usuarios(self) -> dict[str, str]:
        return {email: d["rol"] for email, d in self._coleccion(USUARIOS).items()}

    def guardar_usuario(self, email: str, rol: str, usuario: str) -> None:
        self._escribir(USUARIOS, email, {"rol": rol}, usuario)

    def borrar_usuario(self, email: str) -> None:
        self.db.collection(USUARIOS).document(email).delete()
        self._cache.pop(USUARIOS, None)

    def auditar(self, evento: dict) -> None:
        self.db.collection(AUDITORIA).add({**evento, "fecha": datetime.now(timezone.utc)})

    def auditoria(self, limite: int = 200) -> list[dict]:
        consulta = self.db.collection(AUDITORIA).order_by("fecha", direction=firestore.Query.DESCENDING).limit(limite)
        return [d.to_dict() for d in consulta.stream()]
