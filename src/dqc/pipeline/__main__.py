"""Corre el flujo completo en local (DuckDB), corte por corte, y lo verifica.

Uso: python -m dqc.pipeline [--datos data] [--db data/dq.duckdb]

Ingesta (CSV -> RAW), homologación y cifrado (RAW -> MASTER) y motor de
calidad. Al final compara cada etapa con el manifiesto de errores sembrados.
"""

import argparse
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

from dqc.modelo import CORTES, TABLAS_CORTE
from dqc.motor.puntuacion import scores
from dqc.motor.reglas import cargar_yaml
from dqc.pipeline.configuracion import cargar_contratos, cargar_homologacion
from dqc.pipeline.flujo import Flujo
from dqc.pipeline.ingesta import RECHAZADA, leer_entregas
from dqc.pipeline.verificacion import verificar
from dqc.plataforma.local import PlataformaDuckDB


def _pct(valor: float | None) -> str:
    return "   s/d" if valor is None else f"{valor:6.1f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--datos", type=Path, default=Path("data"))
    parser.add_argument("--db", default=":memory:", help="archivo DuckDB donde dejar el resultado")
    parser.add_argument("--config", type=Path, default=Path("config"))
    args = parser.parse_args()

    plataforma = PlataformaDuckDB(args.db)
    plataforma.reiniciar()
    plataforma.preparar()
    flujo = Flujo(
        plataforma,
        cargar_homologacion(args.config / "homologacion.yaml"),
        cargar_contratos(args.config / "contratos.yaml"),
        cargar_yaml(args.config / "reglas_iniciales.yaml"),
        args.datos / "landing",
    )
    entregas = leer_entregas(args.datos / "landing")

    print(f"{'corte':<12}{'global':>8}" + "".join(f"{t:>11}" for t in TABLAS_CORTE)
          + "   OK ALERTA FALLA  rechazos incidencias")
    resultados = []
    for i, corte in enumerate(CORTES):
        r = flujo.procesar_corte(corte, entregas, primero=i == 0)
        resultados.append(r)
        s = scores(r.ejecucion.resultados)
        estados = Counter(x.estado for x in r.ejecucion.resultados)
        rechazos = sum(c.estado == RECHAZADA for c in r.cargas)
        print(
            f"{corte.isoformat():<12}{_pct(s.global_):>8}"
            + "".join(f"{_pct(s.por_tabla.get(t)):>11}" for t in TABLAS_CORTE)
            + f"{estados['OK']:>5}{estados['ALERTA']:>7}{estados['FALLA']:>6}{rechazos:>10}{len(r.incidencias):>12}"
        )

    print("\nReglas fuera de OK (cumplimiento y estado por corte):")
    for regla in flujo.motor.reglas:
        por_corte = {
            r.fecha_corte: x for r in resultados for x in r.ejecucion.resultados
            if (x.id_regla, x.tabla) == (regla.id, regla.tabla)
        }
        if all(x.estado in ("OK", "SIN_DATOS") for x in por_corte.values()):
            continue
        celdas = "".join(f"{_pct(por_corte[c].cumplimiento)}{por_corte[c].estado[0]:>2}" for c in CORTES)
        print(f"  {regla.id:<11}{regla.tabla:<10}umbral {regla.umbral:>5}  {celdas}")

    manifiesto = pq.read_table(args.datos / "manifiesto_errores.parquet").to_pylist()
    print("\nVerificación contra el manifiesto:")
    exacto = True
    for etapa, (faltantes, sobrantes) in verificar(resultados, manifiesto).items():
        exacto &= not faltantes and not sobrantes
        print(f"  {etapa:<13}{len(faltantes):>5} sin detectar {len(sobrantes):>5} detectados de más")
    raise SystemExit(0 if exacto else 1)


if __name__ == "__main__":
    main()
