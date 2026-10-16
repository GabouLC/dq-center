"""Genera los datos sintéticos y los deja en la zona de aterrizaje.

Uso: python -m dqc.datagen [--salida data] [--semilla 20260930] [--escala 1.0]
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
    parser.add_argument("--escala", type=float, default=1.0, help="tamaño de la cartera (1.0 = unas 1 500 personas)")
    parser.add_argument("--homologacion", type=Path, default=Path("config/homologacion.yaml"))
    args = parser.parse_args()

    resultado = generar(args.semilla, args.escala)
    manifiesto = exportar(resultado, cargar_homologacion(args.homologacion), args.salida)

    print(f"Zona de aterrizaje en {(args.salida / 'landing').resolve()}")
    print(f"{len(CORTES)} cortes diarios, del {CORTES[0]} al {CORTES[-1]}")
    print()
    print(f"{'tabla':<10}{'primer día':>12}{'último día':>12}")
    for tabla in TABLAS_CORTE:
        primero, ultimo = (len(resultado.por_corte[tabla][c]) for c in (CORTES[0], CORTES[-1]))
        print(f"{tabla:<10}{primero:>12,}{ultimo:>12,}")
    print()
    print(f"manifiesto_errores: {len(manifiesto):,} filas")
    por_regla = Counter(m["id_regla"] for m in manifiesto)
    dias = {r: len({m["fecha_corte"] for m in manifiesto if m["id_regla"] == r}) for r in por_regla}
    print(f"{'regla':<14}{'errores':>10}{'días':>7}")
    for regla in sorted(por_regla):
        print(f"{regla:<14}{por_regla[regla]:>10,}{dias[regla]:>7}")


if __name__ == "__main__":
    main()
