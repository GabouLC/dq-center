# Auditoría del catálogo de reglas (DAMA)

Revisión de las 36 reglas de [config/reglas_iniciales.yaml](../config/reglas_iniciales.yaml)
con las seis dimensiones de calidad de DAMA, hecha el 24 de octubre de 2026 sobre los
resultados de los 92 cortes diarios (4.416 evaluaciones). **No cambia ninguna regla:** cada
propuesta la decide el Product Owner, porque cambiaría resultados ya aceptados en los Sprints 1 y 2.

Las cifras salen de consultar la corrida completa en DuckDB (`data/dq_completo.duckdb`) y el
manifiesto de errores sembrados. Lo que es opinión, y no dato, va marcado como *(opinión)*.

## Resumen

1. **El motor detecta exactamente lo sembrado.** En las 23 reglas que tienen errores sembrados no
   se escapa ninguno ni marca nada de más. Las otras 13 reglas dieron 100 % los 92 días porque el
   generador nunca las pone a prueba: no hay evidencia, con datos, de que detecten algo. Son
   PER-VAL-02, POL-COM-01, POL-INT-01, POL-VAL-02, POL-VAL-03, VEH-UNI-01, VEH-VAL-03, SIN-CON-01,
   SIN-CON-02, SIN-VAL-01, PAG-INT-01, PAG-UNI-01 y GEN-VOL-02.
2. **Las reglas CRÍTICAS con umbral 100 nunca bloquean de verdad.** La banda de ALERTA (hasta 2
   puntos bajo el umbral) convierte un 100 en un 98. PER-UNI-01 tuvo 920 personas duplicadas
   (99,34 % a 99,39 %) y quedó en ALERTA los 92 días; SIN-INT-01 tuvo 205 siniestros sin póliza,
   también en ALERTA los 92 días. Las 24 pólizas duplicadas del 20 de agosto quedaron en ALERTA.
3. **Faltan reglas:** Siniestro no tiene unicidad y Pago no tiene validez. La exactitud no se
   puede medir con estos datos: haría falta una fuente de verdad.

## Cobertura por tabla y dimensión

Integridad se toma como consistencia entre tablas, volumetría como completitud de registros y
oportunidad como actualidad.

| Tabla | Completitud | Unicidad | Validez | Consistencia | Actualidad | Exactitud |
|---|---|---|---|---|---|---|
| Persona | PER-COM-01, PER-COM-02, GEN-VOL | PER-UNI-01 | PER-VAL-01 a 05 | PER-INT-01 | GEN-OPO-01 | — |
| Póliza | POL-COM-01, GEN-VOL | POL-UNI-01 | POL-VAL-01 a 03 | POL-CON-01 a 03, POL-INT-01, POL-INT-02 | GEN-OPO-01 | — |
| Vehículo | solo GEN-VOL | VEH-UNI-01 | VEH-VAL-01 a 03 | VEH-INT-01 | GEN-OPO-01 | — |
| Siniestro | solo GEN-VOL | **ninguna** | SIN-VAL-01 | SIN-INT-01, SIN-CON-01 a 03 | GEN-OPO-01 | — |
| Pago | solo GEN-VOL | PAG-UNI-01 | **ninguna** | PAG-INT-01, PAG-CON-01, PAG-CON-02 | GEN-OPO-01 | — |

La actualidad solo mide la hora en que llega el archivo, no si su contenido está al día.

## Propuestas para decidir

### Cómo bloquean las reglas críticas

| Propuesta | Efecto en los 92 días |
|---|---|
| Quitar la banda de ALERTA en las reglas CRÍTICAS: debajo del umbral, FALLA | Persona y Siniestro dejarían de certificarse todos los días por PER-UNI-01 y SIN-INT-01; Póliza, el 20 de agosto también por POL-UNI-01 |
| Dejarla como está y documentar que una regla al 100 tolera hasta un 2 % | Ningún cambio en los resultados aceptados |

*(opinión)* La primera es la correcta para una regla crítica, pero cambia la evidencia de los
Sprints 1 y 2: conviene decidirla en la Sprint Planning del Sprint 3 y aplicarla desde ahí.

### Reglas que faltan

| Id propuesto | Dimensión | Severidad | Umbral | Qué revisa | Evidencia |
|---|---|---|---|---|---|
| SIN-UNI-01 | unicidad | CRÍTICA | 100 | `id_siniestro` único | Hoy no hay duplicados, pero es la única tabla sin unicidad, y de ella sale el conteo regulatorio |
| PAG-VAL-01 | validez | ALTA | 100 | `estado` en PENDIENTE, PAGADO o VENCIDO | Hoy está limpio; PAG-CON-02 compara textos exactos y un «Pendiente» pasaría sin verse. Las fuentes sí mandan variantes así: POL-VAL-01 tuvo 118 casos |
| PER-VAL-06 | validez | ALTA | 100 | `tipo_documento` en DNI, CE o RUC | PER-VAL-01, 02 y 04 filtran por el texto exacto: un «dni» se salta las tres |
| SIN-CON-04 | consistencia | ALTA | 100 | `monto_pagado` no supera la suma asegurada de la póliza | 8 siniestros por corte pagados por encima; estaría en FALLA todos los días (95,8 % a 97,0 %). Falta confirmar la moneda del siniestro |
| PAG-COM-01 | completitud | ALTA | 99,5 | cada póliza tiene todas sus cuotas | 2.280 combinaciones de póliza y corte con cuotas faltantes, por cuotas que la homologación rechazó; mediana 98,54 %, mínimo 78,93 % |
| GEN-COM-01 | completitud | ALTA | 99,5 | filas que llegan a MASTER sobre filas del archivo (tipo de regla nuevo) | El 3 de septiembre se rechazó el 4,24 % de las cuotas (407 de 9.588) y GEN-VOL-01 dio OK porque cuenta las filas de RAW |
| POL-CON-04 | consistencia | MEDIA | 99,5 | una póliza VIGENTE vehicular o SOAT tiene su vehículo | 6 pólizas vigentes sin vehículo el 20 de agosto |

### Umbrales que ya no avisan nada

| Regla | Resultado en los 92 días | Propuesta |
|---|---|---|
| PER-VAL-03 | FALLA 92 de 92 (84,6 % a 90,8 %; umbral 97) | Llevar el umbral cerca del nivel actual (~85), para que la alerta signifique «empeoró» |
| PER-VAL-05 | FALLA 92 de 92 (92,7 % a 93,1 %; umbral 97) | Igual, cerca de 92 |
| PAG-CON-02 | 85 FALLA y 7 ALERTA (91,6 % a 96,7 %; umbral 98) | No bajarla: el 92,4 % de las cuotas pendientes vencidas lleva más de 30 días así. Escalarlo a Cobranzas, porque alimenta el reporte regulatorio |
| POL-CON-03 | 37 OK, 52 ALERTA y 3 FALLA; promedio 98,52 % en julio, 97,68 % en agosto y 96,51 % en septiembre | No tocarla: va camino a fallar a diario y la tendencia es real |
| GEN-VOL-01 | Solo compara con el día anterior: el salto del 20 de agosto (+22 %) se quedó 41 días sin volver a avisar | *(opinión)* Comparar también con la mediana de los últimos 7 días |

### Reglas cuyo SQL no revisa lo que dice

| Regla | Qué pasa | Propuesta |
|---|---|---|
| SIN-CON-03 | El contrato dice que `monto_pagado` solo existe si el siniestro está PAGADO; la regla no revisa los RECHAZADO ni los ABIERTO con pago | Agregar la condición inversa |
| POL-INT-02 | La idea es rechazar pólizas **nuevas** de un producto inactivo, pero rechaza cualquier póliza: al dar de baja un producto, fallaría toda su cartera | Filtrar por fecha de emisión desde la baja |
| PER-COM-01 y PER-VAL-01 | El mismo documento nulo se cuenta dos veces: el 22 de julio, 43 nulos hicieron fallar a las dos | Que la validez excluya los nulos y los deje a la completitud |
| PER-VAL-04 | Castiga una `fecha_nacimiento` nula, aunque el contrato la marca como opcional | Excluir los nulos |
| POL-CON-03 | 432 de sus fallas son «fin de vigencia antes del inicio», que ya castiga POL-CON-01 | Excluir ese caso |
| Llaves nulas | Unicidad descarta los nulos y se los deja a completitud, pero POL-COM-01 no incluye `nro_poliza` y ninguna regla revisa `tipo_documento` ni `nro_cuota` nulos | Agregarlos a la completitud |
| VEH-UNI-01 | *(opinión)* Un mismo VIN puede tener, con razón, un SOAT y una póliza vehicular | Llave por VIN y ramo |
| POL-CON-02 | Usa la misma fórmula de IGV para todos los ramos | Confirmar si los seguros de vida están exonerados |

## Lo que se corrigió en el código

La misma revisión encontró que una tabla cuyo archivo no llega salía **certificada** con 0 % de
cobertura: la regla de oportunidad quedaba «sin datos» en vez de fallar. Desde el 24 de octubre,
la regla de oportunidad sin datos bloquea, y una tabla sin ninguna regla evaluada no se certifica
(`test_una_tabla_cuyo_archivo_no_llego_no_se_certifica`). No cambia ningún resultado de los 92
días: todos los archivos llegaron.
