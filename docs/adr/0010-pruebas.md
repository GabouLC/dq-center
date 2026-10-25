# 0010 · El mismo SQL en DuckDB y un manifiesto de errores sembrados

**Estado:** aceptada (2026-10-15). Ajusta el ADR-10 del Documento de Arquitectura.

## Contexto

Para probar el motor contra BigQuery hacen falta credenciales y tiempo, y eso no
sirve para GitHub Actions. Además, una prueba que solo verifica que el motor
"corre" no demuestra que detecte lo que debe.

## Decisión

- El motor genera SQL de BigQuery. La plataforma local lo traduce a DuckDB con
  sqlglot. Las pocas funciones que no se traducen bien (cifrado y lectura de
  fechas) tienen una implementación por plataforma con la misma firma.
- El generador siembra errores conocidos y los anota en `manifiesto_errores`: qué
  regla, qué registro y en qué corte. La prueba de aceptación corre el flujo
  completo y exige que cada etapa detecte **exactamente** lo sembrado:
  - los archivos rechazados en la ingesta;
  - los registros enviados a incidencias en la homologación;
  - los registros fallidos de cada regla.
- La misma simulación se puede correr contra BigQuery (`python -m dqc.gcp simular`), y
  `scripts/evidencia_bigquery.py` compara cada resultado con el de DuckDB, fila por fila,
  con un tope de 1 GB estimado por dry run.

## Consecuencias

- Las pruebas corren en menos de un minuto y sin credenciales, en local y en CI.
- Si una traducción de sqlglot diverge de BigQuery, la simulación en GCP lo
  muestra. Por eso se corre al cambiar el motor o la homologación.
