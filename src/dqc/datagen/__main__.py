"""Genera los datos sintéticos y los deja en la zona de aterrizaje.

Uso: python -m dqc.datagen [--salida data] [--semilla 20260930]
"""

import argparse
from collections import Counter
from pathlib import Path

from dqc.datagen.exportar import exportar
from dqc.datagen.generador import SEMILLA, generar
from dqc.modelo import CORTES, TABLAS_CORTE
from dqc.pipeline.configuracion import cargar_homologacion


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--salida", type=Path, default=Path("data"))
    parser.add_argument("--semilla", type=int, default=SEMILLA)
    parser.add_argument("--homologacion", type=Path, default=Path("config/homologacion.yaml"))
    args = parser.parse_args()

    resultado = generar(args.semilla)
    manifiesto = exportar(resultado, cargar_homologacion(args.homologacion), args.salida)

    print(f"Zona de aterrizaje en {(args.salida / 'landing').resolve()}\n")
    print(f"{'tabla':<10}" + "".join(f"{c.isoformat():>12}" for c in CORTES))
    for tabla in TABLAS_CORTE:
        print(f"{tabla:<10}" + "".join(f"{len(resultado.por_corte[tabla][c]):>12,}" for c in CORTES))
    print(f"\nmanifiesto_errores: {len(manifiesto):,} filas")
    conteo = Counter((m["id_regla"], m["fecha_corte"]) for m in manifiesto)
    print(f"{'regla':<14}" + "".join(f"{c.isoformat():>12}" for c in CORTES))
    for regla in sorted({m["id_regla"] for m in manifiesto}):
        print(f"{regla:<14}" + "".join(f"{conteo.get((regla, c), 0):>12,}" for c in CORTES))


if __name__ == "__main__":
    main()
