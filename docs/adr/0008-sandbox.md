# 0008 · Modo sandbox: tablas agrupadas en vez de particionadas

**Estado:** aceptada (2026-10-15), mientras el proyecto no tenga facturación activa.

## Contexto

Sin facturación, BigQuery funciona en modo sandbox: vence tablas y particiones a
los 60 días y no admite DML. Con particiones por `fecha_corte`, los cortes de
abril a julio de 2026 vencerían apenas se cargan, porque su fecha ya tiene más
de 60 días.

## Decisión

Con `--sandbox`, las tablas por corte se agrupan (cluster) por `fecha_corte` en
vez de particionarse, y cada corte se agrega a la tabla (el primero la vacía).
Todas las escrituras usan load jobs o consultas con tabla de destino, que el
sandbox sí admite. Sin `--sandbox`, cada corte reemplaza su partición.

## Consecuencias

- En el sandbox, volver a procesar un corte suelto lo duplicaría. La simulación
  siempre empieza desde cero (`reiniciar`).
- Las tablas vencen a los 60 días: la simulación se puede repetir en minutos.
- Al activar la facturación se vuelve a correr sin `--sandbox`.
