# 0013 · Simulación en vivo dentro de la API, solo en local

**Estado:** aceptada (2026-10-15).

## Contexto

El portal tenía que «sentirse vivo»: mostrar archivos que llegan y cortes que se certifican
mientras alguien lo mira. En GCP eso lo haría la corrida programada (ADR 0003), pero sin
facturación no hay Cloud Scheduler ni Cloud Run Job.

## Decisión

`python -m dqc.pipeline --hasta AAAA-MM-DD` procesa hasta esa fecha y deja pendientes los días
siguientes. En el modo local, un hilo de la API (`dqc.api.vivo.Simulador`) hace llegar un archivo
pendiente cada `DQC_EN_VIVO_SEGUNDOS` (20 s por defecto). Cuando un día tiene todos sus archivos,
corre el mismo `Flujo` que la corrida completa: homologa, evalúa, certifica y publica.
El simulador y las lecturas del portal comparten un candado, y la caché de lecturas se invalida
después de cada corte. El portal consulta `/api/v1/vivo` y se actualiza solo. Un administrador
puede pausar o adelantar la simulación; `DQC_EN_VIVO=0` la apaga.

## Consecuencias

- En local, la API escribe en el DuckDB: hay que detenerla antes de volver a correr
  `dqc.pipeline` sobre el mismo archivo.
- Los eventos de actividad viven en memoria y se pierden al reiniciar la API.
- En GCP no existe: allí cada corte llega por la corrida programada.
