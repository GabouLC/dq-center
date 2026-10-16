"""Configuración del portal: reglas, contratos, glosario, usuarios, credenciales y auditoría.

Dos implementaciones con la misma interfaz:
  ConfiguracionLocal      un archivo JSON, sembrado desde config/*.yaml (modo local)
  ConfiguracionFirestore  Firestore en modo nativo (dqc.gcp.firestore)
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

import yaml

from dqc.motor.reglas import a_documento, cargar_yaml
from dqc.pipeline.configuracion import cargar_contratos

ROLES = ("admin", "gobierno", "lector")

# Usuarios de demostración del modo local (no existen en GCP); entran con DQC_CLAVE_DEMO.
USUARIOS_DEMO = {"admin@demo.local": "admin", "gobierno@demo.local": "gobierno", "lector@demo.local": "lector"}


def cargar_glosario(ruta: str | Path) -> list[dict]:
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)["terminos"]


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConfiguracionLocal:
    def __init__(self, ruta: Path, config: Path, admins: list[str] | None = None):
        self.ruta = ruta
        self._lock = threading.Lock()
        if ruta.exists():
            self._datos = json.loads(ruta.read_text(encoding="utf-8"))
            return
        self._datos = {
            "reglas": {r.id: {**a_documento(r), "actualizado_por": "semilla"} for r in cargar_yaml(config / "reglas_iniciales.yaml")},
            "contratos": cargar_contratos(config / "contratos.yaml"),
            "glosario": {t["id"]: t for t in cargar_glosario(config / "glosario.yaml")},
            "usuarios": {**USUARIOS_DEMO, **{a.lower(): "admin" for a in admins or []}},
            "credenciales": {},
            "auditoria": [],
        }
        self._guardar()

    def _guardar(self) -> None:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.ruta.write_text(json.dumps(self._datos, ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    # reglas
    def reglas(self) -> list[dict]:
        return list(self._datos["reglas"].values())

    def regla(self, id_regla: str) -> dict | None:
        return self._datos["reglas"].get(id_regla)

    def guardar_regla(self, doc: dict, usuario: str) -> None:
        with self._lock:
            self._datos["reglas"][doc["id"]] = {**doc, "actualizado_en": _ahora(), "actualizado_por": usuario}
            self._guardar()

    # contratos y glosario
    def contratos(self) -> dict[str, dict]:
        return self._datos["contratos"]

    def glosario(self) -> list[dict]:
        return list(self._datos["glosario"].values())

    def guardar_termino(self, doc: dict, usuario: str) -> None:
        with self._lock:
            self._datos["glosario"][doc["id"]] = {**doc, "actualizado_en": _ahora(), "actualizado_por": usuario}
            self._guardar()

    # usuarios
    def usuarios(self) -> dict[str, str]:
        return dict(self._datos["usuarios"])

    def guardar_usuario(self, email: str, rol: str, usuario: str) -> None:
        with self._lock:
            self._datos["usuarios"][email] = rol
            self._guardar()

    def borrar_usuario(self, email: str) -> None:
        """Quita el rol y la contraseña: las sesiones abiertas de la cuenta dejan de valer."""
        with self._lock:
            self._datos["usuarios"].pop(email, None)
            self._datos.setdefault("credenciales", {}).pop(email, None)
            self._guardar()

    # credenciales (dqc.api.autenticacion): hash de la contraseña, intentos y bloqueo
    def credencial(self, email: str) -> dict | None:
        return self._datos.get("credenciales", {}).get(email)

    def guardar_credencial(self, email: str, cambios: dict) -> None:
        with self._lock:
            credenciales = self._datos.setdefault("credenciales", {})
            credenciales[email] = {**credenciales.get(email, {}), **cambios}
            self._guardar()

    # auditoría
    def auditar(self, evento: dict) -> None:
        with self._lock:
            self._datos["auditoria"].append({**evento, "fecha": _ahora()})
            self._datos["auditoria"] = self._datos["auditoria"][-2000:]
            self._guardar()

    def auditoria(self, limite: int = 200) -> list[dict]:
        return list(reversed(self._datos["auditoria"][-limite:]))
