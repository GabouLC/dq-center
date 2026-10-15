"""Escribe los datos sintéticos y el manifiesto en Parquet.

Uso: python -m dqc.datagen [--salida data/out] [--semilla 20260930]

Estructura de salida:
  ref_producto.parquet, ref_ubigeo.parquet
  <tabla>/<fecha_corte>.parquet   (una foto por tabla y corte)
  registro_cargas.parquet, manifiesto_errores.parquet
"""

import argparse
from collections import Counter
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from dqc.datagen.generador import SEMILLA, generar
from dqc.modelo import CORTES, TABLAS_CORTE, esquema

TIPOS_ARROW = {
    "STRING": pa.string(),
    "INT64": pa.int64(),
    "FLOAT64": pa.float64(),
    "BOOL": pa.bool_(),
    "DATE": pa.date32(),
    "TIMESTAMP": pa.timestamp("us", tz="UTC"),
}


def esquema_arrow(tabla: str, corte=None) -> pa.Schema:
    return pa.schema([(nombre, TIPOS_ARROW[tipo]) for nombre, tipo in esquema(tabla, corte)])


def escribir(filas: list[dict], destino: Path, schema: pa.Schema) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(filas, schema=schema), destino)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--salida", type=Path, default=Path("data/out"))
    parser.add_argument("--semilla", type=int, default=SEMILLA)
    args = parser.parse_args()

    resultado = generar(args.semilla)
    salida: Path = args.salida
    for tabla, filas in resultado.ref.items():
        escribir(filas, salida / f"{tabla}.parquet", esquema_arrow(tabla))
    for tabla in TABLAS_CORTE:
        for corte, filas in resultado.por_corte[tabla].items():
            escribir(filas, salida / tabla / f"{corte.isoformat()}.parquet", esquema_arrow(tabla, corte))
    escribir(resultado.registro_cargas, salida / "registro_cargas.parquet", esquema_arrow("registro_cargas"))
    escribir(resultado.manifiesto, salida / "manifiesto_errores.parquet", esquema_arrow("manifiesto_errores"))

    print(f"Datos en {salida.resolve()}\n")
    print(f"{'tabla':<10}" + "".join(f"{c.isoformat():>12}" for c in CORTES))
    for tabla in TABLAS_CORTE:
        print(f"{tabla:<10}" + "".join(f"{len(resultado.por_corte[tabla][c]):>12,}" for c in CORTES))
    print(f"\nmanifiesto_errores: {len(resultado.manifiesto):,} filas")
    conteo = Counter((m["id_regla"], m["fecha_corte"]) for m in resultado.manifiesto)
    reglas = sorted({m["id_regla"] for m in resultado.manifiesto})
    print(f"{'regla':<12}" + "".join(f"{c.isoformat():>12}" for c in CORTES))
    for regla in reglas:
        print(f"{regla:<12}" + "".join(f"{conteo.get((regla, c), 0):>12,}" for c in CORTES))


if __name__ == "__main__":
    main()
