# 0003 · Cloud Run Job + Cloud Scheduler en vez de Cloud Composer

**Estado:** aceptada (2026-10-15). Ajusta el ADR-06 del Documento de Arquitectura.

## Contexto

El documento dispara la evaluación desde el Cloud Composer corporativo al
terminar cada carga. El piloto no tiene un Composer compartido, y un entorno
propio cuesta cientos de dólares al mes.

## Decisión

El flujo se procesa corte por corte: ingesta, homologación y motor corren uno
detrás de otro, así que la evaluación ocurre apenas termina la carga, que es lo
que buscaba el disparo por evento. En GCP, el motor se empaqueta como Cloud Run
Job. Cloud Scheduler lo corre una vez al día como respaldo, y el portal lo lanza
a demanda.

## Consecuencias

- Cero costo fijo de orquestación.
- No hay un orquestador con reintentos ni un tablero de DAGs. El historial de
  corridas vive en `dq_engine.ejecuciones`.
- Si más adelante hay un Composer disponible, basta un DAG que invoque el mismo
  Cloud Run Job.
