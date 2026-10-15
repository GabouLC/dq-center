"""Escribe los datos sintéticos y el manifiesto en Parquet.

Uso: python -m dqc.datagen [--salida data/out] [--semilla 20260930]
"""

import argparse
from collections import Counter
from pathlib import Path

from dqc.datagen.generador import SEMILLA, generar
from dqc.datagen.salida import escribir_parquet
from dqc.modelo import CORTES, TABLAS_CORTE


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--salida", type=Path, default=Path("data/out"))
    parser.add_argument("--semilla", type=int, default=SEMILLA)
    args = parser.parse_args()

    resultado = generar(args.semilla)
    escribir_parquet(resultado, args.salida)

    print(f"Datos en {args.salida.resolve()}\n")
    print(f"{'tabla':<10}" + "".join(f"{c.isoformat():>12}" for c in CORTES))
    for tabla in TABLAS_CORTE:
        print(f"{tabla:<10}" + "".join(f"{len(resultado.por_corte[tabla][c]):>12,}" for c in CORTES))
    print(f"\nmanifiesto_errores: {len(resultado.manifiesto):,} filas")
    conteo = Counter((m["id_regla"], m["fecha_corte"]) for m in resultado.manifiesto)
    print(f"{'regla':<12}" + "".join(f"{c.isoformat():>12}" for c in CORTES))
    for regla in sorted({m["id_regla"] for m in resultado.manifiesto}):
        print(f"{regla:<12}" + "".join(f"{conteo.get((regla, c), 0):>12,}" for c in CORTES))


if __name__ == "__main__":
    main()
