"""Corre el motor.

Uso local (DuckDB, sin GCP): simula la historia cargando corte por corte.
  python -m dqc.motor local [--datos data/out] [--reglas config/reglas_iniciales.yaml]
"""

import argparse
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

from dqc.modelo import CORTES, TABLAS_CORTE
from dqc.motor.backends import BackendDuckDB
from dqc.motor.motor import Motor, comparar_con_manifiesto
from dqc.motor.puntuacion import scores
from dqc.motor.reglas import cargar_yaml


def _pct(valor: float | None) -> str:
    return "   s/d" if valor is None else f"{valor:6.1f}"


def local(args) -> int:
    backend = BackendDuckDB()
    backend.cargar_referencias(args.datos)
    motor = Motor(backend, cargar_yaml(args.reglas))
    ejecuciones = []
    print(f"{'corte':<12}{'global':>8}" + "".join(f"{t:>11}" for t in TABLAS_CORTE) + "   OK ALERTA FALLA")
    for corte in CORTES:
        backend.cargar_corte(args.datos, corte)
        e = motor.ejecutar(corte, origen="simulacion")
        ejecuciones.append(e)
        s = scores(e.resultados)
        estados = Counter(r.estado for r in e.resultados)
        print(
            f"{corte.isoformat():<12}{_pct(s.global_):>8}"
            + "".join(f"{_pct(s.por_tabla.get(t)):>11}" for t in TABLAS_CORTE)
            + f"{estados['OK']:>5}{estados['ALERTA']:>7}{estados['FALLA']:>6}"
        )

    print("\nReglas fuera de OK (cumplimiento por corte):")
    for regla in motor.reglas:
        por_corte = {
            e.fecha_corte: r for e in ejecuciones for r in e.resultados
            if (r.id_regla, r.tabla) == (regla.id, regla.tabla)
        }
        if all(r.estado in ("OK", "SIN_DATOS") for r in por_corte.values()):
            continue
        celdas = "".join(
            f"{_pct(por_corte[c].cumplimiento)}{por_corte[c].estado[0]:>2}" for c in CORTES
        )
        print(f"  {regla.id:<11}{regla.tabla:<10}umbral {regla.umbral:>5}  {celdas}")

    manifiesto = pq.read_table(args.datos / "manifiesto_errores.parquet").to_pylist()
    faltantes, sobrantes = comparar_con_manifiesto(ejecuciones, manifiesto)
    print(f"\nManifiesto: {len(manifiesto):,} errores sembrados; "
          f"{len(faltantes)} sin detectar, {len(sobrantes)} detectados de más")
    return 0 if not faltantes and not sobrantes else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="comando", required=True)
    p_local = sub.add_parser("local", help="simula la historia en DuckDB")
    p_local.add_argument("--datos", type=Path, default=Path("data/out"))
    p_local.add_argument("--reglas", type=Path, default=Path("config/reglas_iniciales.yaml"))
    args = parser.parse_args()
    raise SystemExit(local(args))


if __name__ == "__main__":
    main()
