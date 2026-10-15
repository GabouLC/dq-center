"""Operaciones contra GCP.

  python -m dqc.gcp preparar [--sandbox]
      Crea los datasets dq_raw y dq_engine y sus tablas.
  python -m dqc.gcp simular [--datos data/out] [--reglas config/reglas_iniciales.yaml]
      Carga los 6 cortes uno por uno, corre el motor después de cada carga,
      guarda los resultados en dq_engine y los compara con el manifiesto.

El proyecto sale de --proyecto o de la variable DQC_PROYECTO.
"""

import argparse
import os
from collections import Counter
from pathlib import Path

from google.cloud import bigquery

from dqc.gcp.bigquery import (
    UBICACION, AlmacenBigQuery, BackendBigQuery, CargaBigQuery, leer_manifiesto, preparar,
)
from dqc.modelo import CORTES
from dqc.motor.motor import Motor, comparar_con_manifiesto
from dqc.motor.puntuacion import scores
from dqc.motor.reglas import cargar_yaml


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--proyecto", default=os.environ.get("DQC_PROYECTO"))
    sub = parser.add_subparsers(dest="comando", required=True)
    p_preparar = sub.add_parser("preparar")
    p_preparar.add_argument("--sandbox", action="store_true", help="proyecto sin facturación")
    p_simular = sub.add_parser("simular")
    p_simular.add_argument("--datos", type=Path, default=Path("data/out"))
    p_simular.add_argument("--reglas", type=Path, default=Path("config/reglas_iniciales.yaml"))
    args = parser.parse_args()
    if not args.proyecto:
        parser.error("indica --proyecto o define DQC_PROYECTO")

    cliente = bigquery.Client(project=args.proyecto, location=UBICACION)
    if args.comando == "preparar":
        creadas = preparar(cliente, sandbox=args.sandbox)
        print(f"Tablas creadas: {', '.join(creadas) if creadas else 'ninguna (ya existían)'}")
        return

    carga = CargaBigQuery(cliente)
    motor = Motor(BackendBigQuery(cliente), cargar_yaml(args.reglas), hilos=8)
    almacen = AlmacenBigQuery(cliente)
    carga.cargar_referencias(args.datos)
    ejecuciones = []
    for i, corte in enumerate(CORTES):
        carga.cargar_corte(args.datos, corte, primero=i == 0)
        e = motor.ejecutar(corte, origen="simulacion")
        almacen.guardar(e)
        ejecuciones.append(e)
        estados = Counter(r.estado for r in e.resultados)
        duracion = (e.terminada_en - e.iniciada_en).total_seconds()
        print(
            f"{corte}  global {scores(e.resultados).global_:5.1f}  "
            f"OK {estados['OK']:>2}  ALERTA {estados['ALERTA']:>2}  FALLA {estados['FALLA']:>2}  ({duracion:.0f} s)"
        )
    faltantes, sobrantes = comparar_con_manifiesto(ejecuciones, leer_manifiesto(cliente))
    print(f"Manifiesto: {len(faltantes)} sin detectar, {len(sobrantes)} detectados de más")
    raise SystemExit(0 if not faltantes and not sobrantes else 1)


if __name__ == "__main__":
    main()
