"""Corre el flujo completo en local (DuckDB), corte por corte, y lo verifica.

Uso: python -m dqc.pipeline [--datos data] [--db data/dq.duckdb] [--hasta AAAA-MM-DD]

Ingesta (CSV -> RAW), homologación y cifrado (RAW -> MASTER) y motor de
calidad. Al final compara cada etapa con el manifiesto de errores sembrados.
Con --hasta, los cortes posteriores quedan pendientes en la zona de aterrizaje:
la API los procesa en vivo, uno por uno (DQC_EN_VIVO).
"""

import argparse
from collections import Counter
from datetime import date
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

ESTADOS = {"CERTIFICADO": "certificada", "CERTIFICADO_CON_OBSERVACIONES": "con observaciones", "NO_CERTIFICADO": "no certificada"}


def _pct(valor: float | None) -> str:
    return "   s/d" if valor is None else f"{valor:6.1f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--datos", type=Path, default=Path("data"))
    parser.add_argument("--db", default=":memory:", help="archivo DuckDB donde dejar el resultado")
    parser.add_argument("--config", type=Path, default=Path("config"))
    parser.add_argument("--hasta", type=date.fromisoformat, default=CORTES[-1], help="último corte a procesar")
    args = parser.parse_args()

    plataforma = PlataformaDuckDB(args.db)
    plataforma.reiniciar()
    flujo = Flujo(
        plataforma,
        cargar_homologacion(args.config / "homologacion.yaml"),
        cargar_contratos(args.config / "contratos.yaml"),
        cargar_yaml(args.config / "reglas_iniciales.yaml"),
        args.datos / "landing",
    )
    flujo.preparar()
    entregas = leer_entregas(args.datos / "landing")
    cortes = [c for c in CORTES if c <= args.hasta]

    print(f"{'corte':<12}{'global':>8}" + "".join(f"{t:>11}" for t in TABLAS_CORTE)
          + "   OK ALERTA FALLA  rechazos incidencias")
    resultados = []
    for i, corte in enumerate(cortes):
        r = flujo.procesar_corte(corte, entregas, primero=i == 0)
        resultados.append(r)
        s = scores(r.ejecucion.resultados)
        estados = Counter(x.estado for x in r.ejecucion.resultados)
        rechazos = sum(c.estado == RECHAZADA for c in r.cargas)
        print(
            f"{corte.isoformat():<12}{_pct(s.global_):>8}"
            + "".join(f"{_pct(s.por_tabla.get(t)):>11}" for t in TABLAS_CORTE)
            + f"{estados['OK']:>5}{estados['ALERTA']:>7}{estados['FALLA']:>6}{rechazos:>10}{len(r.incidencias):>12}",
            flush=True,
        )

    print("\nReglas fuera de OK: días en cada estado y cumplimiento del primer y el último corte")
    print(f"  {'regla':<11}{'tabla':<10}{'umbral':>7}{'OK':>5}{'ALERTA':>7}{'FALLA':>6}{'primero':>9}{'último':>8}")
    for regla in flujo.motor.reglas:
        serie = [
            x for r in resultados for x in r.ejecucion.resultados if (x.id_regla, x.tabla) == (regla.id, regla.tabla)
        ]
        dias = Counter(x.estado for x in serie)
        if dias["ALERTA"] + dias["FALLA"] == 0:
            continue
        print(f"  {regla.id:<11}{regla.tabla:<10}{regla.umbral:>7}{dias['OK']:>5}{dias['ALERTA']:>7}{dias['FALLA']:>6}"
              f"{_pct(serie[0].cumplimiento):>9}{_pct(serie[-1].cumplimiento):>8}")

    print("\nCertificación: días en cada estado")
    for tabla in TABLAS_CORTE:
        conteo = Counter(c.estado for r in resultados for c in r.certificaciones if c.tabla == tabla)
        print(f"  {tabla:<10}" + "  ".join(f"{conteo[e]:>3} {nombre}" for e, nombre in ESTADOS.items()))
    print("\nCortes no certificados y su motivo:")
    for r in resultados:
        for c in r.certificaciones:
            if not c.certificado:
                motivo = ", ".join(c.reglas_bloqueantes) or "privacidad: " + ", ".join(
                    sorted({f"{h.tipo} en {h.columna}" for h in c.hallazgos if h.bloqueante})
                )
                print(f"  {r.fecha_corte} {c.tabla:<10} {motivo}")

    manifiesto = pq.read_table(args.datos / "manifiesto_errores.parquet").to_pylist()
    print("\nVerificación contra el manifiesto:")
    exacto = True
    for etapa, (faltantes, sobrantes) in verificar(resultados, manifiesto).items():
        exacto &= not faltantes and not sobrantes
        print(f"  {etapa:<13}{len(faltantes):>5} sin detectar {len(sobrantes):>5} detectados de más")
    raise SystemExit(0 if exacto else 1)


if __name__ == "__main__":
    main()
