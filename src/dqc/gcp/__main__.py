"""Operaciones contra GCP. El proyecto sale de --proyecto o de DQC_PROYECTO.

  python -m dqc.gcp preparar
      Crea los datasets de cada capa y las llaves de cifrado.
  python -m dqc.gcp sembrar --admin correo@dominio [--reemplazar]
      Carga en Firestore las reglas, los contratos (con su clasificación DAC) y los administradores.
      A cada administrador sin contraseña le imprime una temporal, que debe cambiar al entrar.
  python -m dqc.gcp simular [--datos data] [--desde AAAA-MM-DD]
      Corre los 92 cortes desde cero (ingesta, homologación, motor, Gate y publicación) y verifica
      contra el manifiesto. Con --desde reanuda una carga cortada: exige que los cortes anteriores
      estén evaluados, borra todo lo de ese corte en adelante (incluidas las corridas manuales),
      sigue desde ahí y verifica solo los cortes que procesó.
  python -m dqc.gcp ejecutar [--corte AAAA-MM-DD] [--origen programada]
      Corre el motor sobre un corte ya cargado (por defecto, el último).

--sandbox: proyecto sin facturación (tablas agrupadas por corte en vez de particionadas).
"""

import argparse
import os
import secrets
from collections import Counter
from datetime import date
from pathlib import Path

import pyarrow.parquet as pq
from google.cloud import bigquery, firestore

from dqc.api.autenticacion import Autenticador, Sesiones
from dqc.api.configuracion import cargar_glosario
from dqc.gcp.firestore import CONTRATOS, ConfiguracionFirestore, cargar_reglas, sembrar
from dqc.modelo import CORTES, RAW
from dqc.motor.motor import Ejecucion
from dqc.motor.puntuacion import scores
from dqc.motor.reglas import cargar_yaml
from dqc.pipeline.configuracion import cargar_contratos, cargar_homologacion
from dqc.pipeline.flujo import Flujo, cortes_por_procesar
from dqc.pipeline.ingesta import RECHAZADA, leer_entregas
from dqc.pipeline.verificacion import verificar
from dqc.plataforma.bigquery import UBICACION, PlataformaBigQuery


def _imprimir(e: Ejecucion, extra: str = "") -> None:
    estados = Counter(r.estado for r in e.resultados)
    duracion = (e.terminada_en - e.iniciada_en).total_seconds()
    print(
        f"{e.fecha_corte}  global {scores(e.resultados).global_:5.1f}  "
        f"OK {estados['OK']:>2}  ALERTA {estados['ALERTA']:>2}  FALLA {estados['FALLA']:>2}  "
        f"motor {duracion:.0f} s{extra}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--proyecto", default=os.environ.get("DQC_PROYECTO"))
    parser.add_argument("--sandbox", action="store_true", default=os.environ.get("DQC_SANDBOX") == "1")
    parser.add_argument("--config", type=Path, default=Path("config"))
    parser.add_argument("--reglas-yaml", action="store_true", help="leer las reglas del YAML y no de Firestore")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("preparar")
    p = sub.add_parser("sembrar")
    p.add_argument("--admin", action="append", default=[], help="correo de un administrador (repetible)")
    p.add_argument("--reemplazar", action="store_true", help="sobrescribir lo que ya existe")
    p = sub.add_parser("simular")
    p.add_argument("--datos", type=Path, default=Path("data"))
    p.add_argument("--desde", type=date.fromisoformat, help="reanudar desde este corte (AAAA-MM-DD)")
    p = sub.add_parser("ejecutar")
    p.add_argument("--corte", type=date.fromisoformat)
    p.add_argument("--origen", default="programada")
    args = parser.parse_args()
    if not args.proyecto:
        parser.error("indica --proyecto o define DQC_PROYECTO")
    if getattr(args, "desde", None) and args.desde not in CORTES:
        parser.error(f"--desde debe ser un corte entre {CORTES[0]} y {CORTES[-1]}")

    plataforma = PlataformaBigQuery(bigquery.Client(project=args.proyecto, location=UBICACION), args.sandbox)
    db = firestore.Client(project=args.proyecto)

    if args.comando == "preparar":
        plataforma.preparar()
        print("Datasets y llaves listos.")
        return
    if args.comando == "sembrar":
        escritos = sembrar(
            db,
            cargar_yaml(args.config / "reglas_iniciales.yaml"),
            cargar_contratos(args.config / "contratos.yaml"),
            cargar_glosario(args.config / "glosario.yaml"),
            args.admin,
            args.reemplazar,
        )
        print("Documentos escritos: " + ", ".join(f"{c} {n}" for c, n in escritos.items()))
        # Solo se asignan contraseñas: el secreto de sesión de la API no hace falta aquí.
        autenticador = Autenticador(ConfiguracionFirestore(db), Sesiones(secrets.token_bytes(32)))
        for email in (a.lower() for a in args.admin):
            if autenticador.config.credencial(email) is None:
                print(f"Contraseña temporal de {email}: {autenticador.asignar_temporal(email)}")
        return

    reglas = cargar_yaml(args.config / "reglas_iniciales.yaml") if args.reglas_yaml else cargar_reglas(db)
    if not reglas:
        raise SystemExit("No hay reglas en Firestore: corre primero 'sembrar'.")

    if args.comando == "ejecutar":
        contratos = {d.id: d.to_dict() for d in db.collection(CONTRATOS).stream()}
        flujo = Flujo(plataforma, {}, contratos, reglas, hilos=8)
        corte = args.corte or plataforma.consultar(
            f"SELECT MAX(fecha_corte) AS corte FROM {RAW}.registro_cargas WHERE estado = 'EXITOSA'"
        )[0]["corte"]
        e, certificaciones = flujo.evaluar(corte, origen=args.origen)
        _imprimir(e, "  " + ", ".join(f"{c.tabla} {c.estado}" for c in certificaciones))
        return

    if args.desde is None:
        plataforma.reiniciar()
    try:
        pendientes = cortes_por_procesar(plataforma, args.desde)
    except ValueError as e:
        parser.error(str(e))
    if args.desde is not None:
        for linea in plataforma.recortar(args.desde):
            print(f"Recortada {linea}")
    flujo = Flujo(
        plataforma,
        cargar_homologacion(args.config / "homologacion.yaml"),
        cargar_contratos(args.config / "contratos.yaml"),
        reglas,
        args.datos / "landing",
        hilos=8,
    )
    flujo.preparar()
    entregas = leer_entregas(args.datos / "landing")
    resultados = []
    for corte in pendientes:
        r = flujo.procesar_corte(corte, entregas, primero=corte == CORTES[0])
        resultados.append(r)
        rechazos = sum(c.estado == RECHAZADA for c in r.cargas)
        _imprimir(r.ejecucion, f"  rechazos {rechazos}  incidencias {len(r.incidencias)}")
    manifiesto = pq.read_table(args.datos / "manifiesto_errores.parquet").to_pylist()
    exacto = True
    for etapa, (faltantes, sobrantes) in verificar(resultados, manifiesto).items():
        exacto &= not faltantes and not sobrantes
        print(f"  {etapa:<13}{len(faltantes):>5} sin detectar {len(sobrantes):>5} detectados de más")
    raise SystemExit(0 if exacto else 1)


if __name__ == "__main__":
    main()
