# 0014 · Reanudar una carga cortada con `--desde`

**Estado:** aceptada (2026-10-24). Ajusta el ADR 0008.

## Contexto

En el sandbox, cargar los 92 cortes toma unas 9 horas. La recarga se cortó el 7 de septiembre
y la única opción era empezar de cero (`reiniciar`). Sin DML, procesar de nuevo un corte que
quedó a medias lo duplicaría (ADR 0008).

## Decisión

`python -m dqc.gcp simular --desde AAAA-MM-DD` reanuda desde un corte:

1. `cortes_por_procesar` exige que todos los cortes anteriores estén evaluados en
   `dq_engine.ejecuciones`; si falta uno, se niega para no dejar huecos.
2. `recortar(desde)` deja cada tabla con `fecha_corte` solo con los cortes anteriores. En
   BigQuery reescribe la tabla con una consulta sobre sí misma (WRITE_TRUNCATE, con su mismo
   agrupamiento o particionado) y conserva las filas sin fecha. En DuckDB, `DELETE`.
3. Procesa desde ese corte y verifica contra el manifiesto los cortes que procesó.

## Consecuencias

- Borra todo lo de esos cortes en adelante, incluidas las corridas manuales.
- La prueba `test_reanudar_desde_un_corte_da_lo_mismo_que_de_corrido` corta una carga, la
  reanuda y exige los mismos resultados, sin duplicados, que una corrida de una vez.
- La comprobación de los 92 cortes en BigQuery la hace `scripts/evidencia_bigquery.py`: verifica
  contra el manifiesto con lo que quedó en BigQuery y compara cada resultado con DuckDB.
