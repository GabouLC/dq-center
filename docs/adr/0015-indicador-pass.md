# 0015 · El % de reglas en PASS es el indicador principal

**Estado:** aceptada (2026-10-15). Ajusta la puntuación del brief.

## Contexto

El brief proponía un score ponderado (pesos 3, 2 y 1 por nivel) como cifra principal del
Resumen. Con los datos diarios, ese score varía muy poco: entre 96,9 y 99,6 en los 92 días. En
cambio, las reglas en OK van de 33 a 40 de 48. Un número que casi no se mueve no ayuda a decidir
si se puede confiar en un día. El backlog, además, habla de reglas en PASS y FAIL.

## Decisión

El Resumen muestra primero el **% de reglas en PASS**: reglas en OK sobre reglas con datos
(`vistas._pct_pass`). ALERTA cuenta como no-PASS y SIN_DATOS se excluye. También se calcula por
tabla. El score ponderado sigue disponible como métrica alternativa.

## Consecuencias

- El indicador coincide con el PASS y el FAIL de los criterios de HU-02, HU-03 y HU-09.
- Una regla en ALERTA baja el indicador aunque no bloquee la certificación: el sello por tabla
  (HU-04) sigue siendo la respuesta a «¿se puede usar este dato?».
