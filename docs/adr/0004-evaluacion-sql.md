# 0004 · SQL generado por regla, sin Dataplex

**Estado:** aceptada (2026-10-15). Reemplaza el ADR-03 del Documento de Arquitectura.

## Contexto

El documento evalúa las tablas simples con escaneos de Dataplex (grupo A) y las
históricas con SQL por partición (grupo B). Dataplex cobra por volumen escaneado,
no se puede ejecutar en local y obliga a mantener dos caminos de evaluación.

## Decisión

Todas las reglas se evalúan con SQL que el motor genera a partir de su tipo
(no_nulo, único, regex, dominio, expresión, referencia, frescura y volumetría) y
solo sobre el corte evaluado, que es el equivalente a evaluar la partición nueva.
Las reglas se definen por configuración en Firestore, sin tocar código.

## Consecuencias

- Un solo camino de evaluación, que además corre igual en DuckDB (ver ADR 0010).
- Cada regla cuesta una consulta sobre un corte. Con los volúmenes del piloto
  (decenas de miles de filas) está muy por debajo de la capa gratuita.
- Una regla nueva se valida con un dry run antes de guardarse, para que no llegue al motor un SQL roto.
