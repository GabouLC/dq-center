"""Operaciones contra GCP.

  python -m dqc.gcp preparar [--sandbox]
      Crea los datasets dq_raw y dq_engine y sus tablas.
  python -m dqc.gcp sembrar --admin correo@dominio [--reemplazar]
      Carga en Firestore el catálogo de reglas, los contratos y los administradores.
  python -m dqc.gcp simular [--datos data/out]
      Carga los 6 cortes uno por uno, corre el motor después de cada carga,
      guarda los resultados en dq_engine y los compara con el manifiesto.
  python -m dqc.gcp ejecutar [--corte AAAA-MM-DD] [--origen programada]
      Corre el motor sobre un corte ya cargado (por defecto, el último).

Las reglas salen de Firestore, salvo que se pase --reglas-yaml.
El proyecto sale de --proyecto o de la variable DQC_PROYECTO.
"""

import argparse
import os
from collections import Counter
from datetime import date
from pathlib import Path

from google.cloud import bigquery, firestore

from dqc.gcp.bigquery import (
    DATASET_RAW, UBICACION, AlmacenBigQuery, BackendBigQuery, CargaBigQuery, leer_manifiesto, preparar,
)
from dqc.gcp.firestore import cargar_contratos, cargar_reglas, sembrar
from dqc.modelo import CORTES
from dqc.motor.motor import Ejecucion, Motor, comparar_con_manifiesto
from dqc.motor.puntuacion import scores
from dqc.motor.reglas import cargar_yaml

CATALOGO = Path("config/reglas_iniciales.yaml")
CONTRATOS = Path("config/contratos.yaml")


def _imprimir(e: Ejecucion) -> None:
    estados = Counter(r.estado for r in e.resultados)
    duracion = (e.terminada_en - e.iniciada_en).total_seconds()
    print(
        f"{e.fecha_corte}  global {scores(e.resultados).global_:5.1f}  "
        f"OK {estados['OK']:>2}  ALERTA {estados['ALERTA']:>2}  FALLA {estados['FALLA']:>2}  ({duracion:.0f} s)"
    )


def _ultimo_corte(cliente: bigquery.Client) -> date:
    sql = f"SELECT MAX(fecha_corte) AS corte FROM `{cliente.project}.{DATASET_RAW}.registro_cargas`"
    return next(iter(cliente.query(sql).result()))["corte"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--proyecto", default=os.environ.get("DQC_PROYECTO"))
    parser.add_argument("--reglas-yaml", type=Path, help="usar un catálogo YAML en vez de Firestore")
    sub = parser.add_subparsers(dest="comando", required=True)
    p = sub.add_parser("preparar")
    p.add_argument("--sandbox", action="store_true", help="proyecto sin facturación")
    p = sub.add_parser("sembrar")
    p.add_argument("--admin", action="append", default=[], help="correo de un administrador (repetible)")
    p.add_argument("--reemplazar", action="store_true", help="sobrescribir lo que ya existe")
    p = sub.add_parser("simular")
    p.add_argument("--datos", type=Path, default=Path("data/out"))
    p = sub.add_parser("ejecutar")
    p.add_argument("--corte", type=date.fromisoformat)
    p.add_argument("--origen", default="programada")
    args = parser.parse_args()
    if not args.proyecto:
        parser.error("indica --proyecto o define DQC_PROYECTO")

    cliente = bigquery.Client(project=args.proyecto, location=UBICACION)
    db = firestore.Client(project=args.proyecto)

    if args.comando == "preparar":
        creadas = preparar(cliente, sandbox=args.sandbox)
        print(f"Tablas creadas: {', '.join(creadas) if creadas else 'ninguna (ya existían)'}")
        return
    if args.comando == "sembrar":
        escritos = sembrar(db, cargar_yaml(CATALOGO), cargar_contratos(CONTRATOS), args.admin, args.reemplazar)
        print("Documentos escritos: " + ", ".join(f"{c} {n}" for c, n in escritos.items()))
        return

    reglas = cargar_yaml(args.reglas_yaml) if args.reglas_yaml else cargar_reglas(db)
    if not reglas:
        raise SystemExit("No hay reglas en Firestore: corre primero 'sembrar'.")
    motor = Motor(BackendBigQuery(cliente), reglas, hilos=8)
    almacen = AlmacenBigQuery(cliente)

    if args.comando == "ejecutar":
        e = motor.ejecutar(args.corte or _ultimo_corte(cliente), origen=args.origen)
        almacen.guardar(e)
        _imprimir(e)
        return

    carga = CargaBigQuery(cliente)
    carga.cargar_referencias(args.datos)
    ejecuciones = []
    for i, corte in enumerate(CORTES):
        carga.cargar_corte(args.datos, corte, primero=i == 0)
        e = motor.ejecutar(corte, origen="simulacion")
        almacen.guardar(e)
        ejecuciones.append(e)
        _imprimir(e)
    faltantes, sobrantes = comparar_con_manifiesto(ejecuciones, leer_manifiesto(cliente))
    print(f"Manifiesto: {len(faltantes)} sin detectar, {len(sobrantes)} detectados de más")
    raise SystemExit(0 if not faltantes and not sobrantes else 1)


if __name__ == "__main__":
    main()
