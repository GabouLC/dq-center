"""Prueba el acceso (HU-13) contra Firestore REAL, con las mismas condiciones del modo GCP.

Comprueba, con el Autenticador de la API sobre ConfiguracionFirestore:
  - contraseña temporal: entra y obliga a cambiarla; cambiarla cierra la sesión anterior;
  - dos «instancias» (dos ConfiguracionFirestore con su propia memoria): un cambio, un
    restablecimiento, un bloqueo o quitar el acceso valen al instante en la otra;
  - bloqueo a los 5 intentos, también con intentos en paralelo y con un correo que no existe;
  - la contraseña temporal desbloquea; todo queda en la auditoría.

Crea cuentas verificacion-hu13-*@demo.local y, al terminar, las borra con sus credenciales y sus
eventos de auditoría. Usa unas 300 lecturas y escrituras de Firestore (la cuota gratuita diaria es
de 50 000 y 20 000), sin costo.

  DQC_PROYECTO=dq-center-gabou python scripts/verificar_acceso_firestore.py [--salida docs/evidencias/acceso-firestore.txt]
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from dqc.api.autenticacion import MAX_INTENTOS, Autenticador, ErrorAcceso, Sesiones
from dqc.gcp.firestore import AUDITORIA, ConfiguracionFirestore

RAIZ = Path(__file__).resolve().parents[1]
NUEVA = "una frase larga y propia 2026"


def codigo(autenticador: Autenticador, email: str, clave: str) -> int:
    """200 si entra; si no, el código del error (401 o 423)."""
    try:
        autenticador.entrar(email, clave)
        return 200
    except ErrorAcceso as e:
        return e.codigo


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--proyecto", default=os.environ.get("DQC_PROYECTO"))
    parser.add_argument("--salida", type=Path, default=RAIZ / "docs" / "evidencias" / "acceso-firestore.txt")
    args = parser.parse_args()
    if not args.proyecto:
        parser.error("indica --proyecto o define DQC_PROYECTO")

    db = firestore.Client(project=args.proyecto)
    secreto = secrets.token_bytes(32)
    # Dos instancias: cada una con su propia memoria, como dos réplicas de Cloud Run.
    a = Autenticador(ConfiguracionFirestore(db), Sesiones(secreto))
    b = Autenticador(ConfiguracionFirestore(db), Sesiones(secreto))
    sufijo = uuid.uuid4().hex[:6]
    cuenta, paralela, fantasma = (f"{n}-hu13-{sufijo}@demo.local" for n in ("verificacion", "verificacion-paralela", "inexistente"))
    creadas = [cuenta, paralela]
    resultados: list[tuple[str, bool, str]] = []

    def comprobar(nombre: str, ok: bool, detalle: str = "") -> None:
        resultados.append((nombre, bool(ok), detalle))
        print(f"  {'ok    ' if ok else 'FALLÓ '} {nombre}" + (f" · {detalle}" if detalle else ""), flush=True)

    try:
        for email in creadas:
            a.config.guardar_usuario(email, "lector", "verificacion")
        b.config._cache.clear()  # b arranca después del alta: lee los usuarios como una réplica nueva

        # 1. Contraseña temporal
        temporal = a.asignar_temporal(cuenta)
        sesion = a.entrar(cuenta, temporal)
        comprobar("La contraseña temporal entra y obliga a cambiarla", sesion["debe_cambiar"] and a.debe_cambiar(cuenta))

        # 2. Cambiarla cierra la sesión anterior
        nueva = a.cambiar(cuenta, temporal, NUEVA)
        viejo_cerrado = False
        try:
            a.verificar(sesion["token"])
        except ValueError:
            viejo_cerrado = True
        comprobar("Cambiar la contraseña cierra la sesión anterior",
                  a.verificar(nueva["token"]) == cuenta and viejo_cerrado and not a.debe_cambiar(cuenta))

        # 3. Otra instancia ve el cambio al instante (sin caché de credenciales)
        comprobar("Otra instancia acepta la contraseña nueva al instante", codigo(b, cuenta, NUEVA) == 200)
        comprobar("Otra instancia rechaza la temporal vieja al instante", codigo(b, cuenta, temporal) == 401)
        t2 = a.asignar_temporal(cuenta)
        comprobar("Restablecer la contraseña vale al instante en otra instancia",
                  codigo(b, cuenta, NUEVA) == 401 and codigo(b, cuenta, t2) == 200)

        # 4. Bloqueo a los 5 intentos, persistido en Firestore
        a.fijar(cuenta, NUEVA, debe_cambiar=False)
        intentos = [codigo(a, cuenta, "equivocada") for _ in range(MAX_INTENTOS)]
        comprobar(f"{MAX_INTENTOS} intentos fallidos dan {MAX_INTENTOS} veces 401", intentos == [401] * MAX_INTENTOS, str(intentos))
        comprobar("El sexto intento, aunque sea con la clave correcta, da 423", codigo(a, cuenta, NUEVA) == 423)
        guardado = b.config.credencial(cuenta) or {}
        comprobar("El bloqueo quedó guardado en Firestore y otra instancia lo respeta",
                  bool(guardado.get("bloqueado_hasta")) and codigo(b, cuenta, NUEVA) == 423)
        a.asignar_temporal(cuenta)
        comprobar("La contraseña temporal desbloquea la cuenta", not a.estado(cuenta)["bloqueada"])

        # 5. Intentos en paralelo
        a.fijar(paralela, NUEVA, debe_cambiar=False)
        with ThreadPoolExecutor(max_workers=10) as pool:
            codigos = list(pool.map(lambda _: codigo(a, paralela, "equivocada"), range(20)))
        comprobar("20 intentos en paralelo no pasan del límite",
                  codigos.count(401) <= MAX_INTENTOS and set(codigos) <= {401, 423},
                  f"{codigos.count(401)} con 401 y {codigos.count(423)} con 423")
        comprobar("La cuenta queda bloqueada tras los intentos en paralelo", codigo(a, paralela, NUEVA) == 423)

        # 6. Un correo que no existe se bloquea igual
        existente = [codigo(b, "verificacion-nueva@demo.local", "x") for _ in range(MAX_INTENTOS + 1)]
        inexistente = [codigo(b, fantasma, "x") for _ in range(MAX_INTENTOS + 1)]
        comprobar("Un correo que no existe se bloquea igual que uno que existe: el bloqueo no revela cuentas",
                  existente == inexistente == [401] * MAX_INTENTOS + [423], str(inexistente))

        # 7. Quitar el acceso cierra la sesión en otra instancia
        a.asignar_temporal(cuenta)
        a.fijar(cuenta, NUEVA, debe_cambiar=False)
        token = a.entrar(cuenta, NUEVA)["token"]
        a.config.borrar_usuario(cuenta)
        cerrada = False
        try:
            b.verificar(token)
        except ValueError:
            cerrada = True
        comprobar("Quitar el acceso cierra la sesión en otra instancia al instante", cerrada)

        # 8. Auditoría
        eventos = [e for e in a.config.auditoria(500) if str(e.get("email", "")).endswith(f"-hu13-{sufijo}@demo.local")]
        acciones = {e["accion"] for e in eventos}
        faltan = {"INICIO_SESION", "INICIO_FALLIDO", "CUENTA_BLOQUEADA", "CAMBIO_CLAVE"} - acciones
        comprobar("Inicios, intentos fallidos, bloqueos y cambios quedan en la auditoría", not faltan,
                  f"{len(eventos)} eventos" + (f"; faltan {sorted(faltan)}" if faltan else ""))
    finally:
        # Limpieza: las cuentas de verificación, sus credenciales y sus eventos de auditoría
        borrados = 0
        for email in creadas:
            a.config.borrar_usuario(email)
        correos = [*creadas, fantasma, "verificacion-nueva@demo.local"]
        for email in correos:
            db.collection("credenciales").document(email).delete()
            for doc in db.collection(AUDITORIA).where(filter=FieldFilter("email", "==", email)).stream():
                doc.reference.delete()
                borrados += 1
        print(f"  Limpieza: cuentas de verificación borradas y {borrados} eventos de auditoría", flush=True)

    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    fallas = [n for n, ok, _ in resultados if not ok]
    texto = (
        f"Acceso (HU-13) contra Firestore real · proyecto {args.proyecto} · {ahora}\n"
        f"Autenticador de la API con PBKDF2 de 600 000 iteraciones y dos instancias con memoria propia.\n"
        f"Resultado: {len(resultados) - len(fallas)} de {len(resultados)} comprobaciones correctas.\n\n"
        + "\n".join(f"{'OK    ' if ok else 'FALLÓ '} {n}" + (f" · {d}" if d else "") for n, ok, d in resultados)
        + "\n\nLas cuentas de verificación y sus eventos de auditoría se borraron al terminar.\n"
    )
    args.salida.write_text(texto, encoding="utf-8", newline="\n")
    print(f"\n{texto.splitlines()[2]}")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
