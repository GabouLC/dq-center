# Actas de Daily Scrum

Reuniones virtuales de 15 minutos, a las 8:00 p. m. Asistieron Gabriel León (Product Owner),
Franco Delgado (Scrum Master), Jesus de la Cruz y Cristhian Pimentel. Josue Borda no asistió.

*Actas reconstruidas a partir del tablero de Jira, el orden del sprint backlog y los impedimentos
registrados en cada sprint.*

## Sprint 1 · 1 al 5 de octubre de 2026

### Daily 1 · viernes 2 de octubre

| Integrante | Qué terminé | Qué haré | Qué me bloquea |
|---|---|---|---|
| Cristhian Pimentel | Generador de datos sintéticos con errores sembrados y su manifiesto (HU-01) | Zona de aterrizaje: un CSV por fuente y corte | Nada |
| Jesus de la Cruz | Mapa de cada fuente al modelo estándar en `homologacion.yaml` (HU-14) | SQL de homologación por fuente | `SAFE.PARSE_DATE` de BigQuery no se traduce bien a DuckDB |
| Franco Delgado | Estrategia de prueba: aceptación contra el manifiesto de errores sembrados | Pruebas de ingesta | Nada |
| Gabriel León | Proyecto de GCP y datasets de cada capa | Configuración en Firestore | La cuenta de facturación no se puede crear (error `OR_BACR2_59`) |

**Impedimentos nuevos:** facturación de GCP (Gabriel); traducción de fechas entre dialectos (Jesus).

### Daily 2 · sábado 3 de octubre

| Integrante | Qué terminé | Qué haré | Qué me bloquea |
|---|---|---|---|
| Cristhian Pimentel | Zona de aterrizaje y validación de la estructura del CSV, con rechazo y motivo (HU-01) | Carga a RAW sin transformar y registro de cada carga | Nada |
| Jesus de la Cruz | Función `parsear_fecha` por plataforma: se destrabó la homologación | Incidencias de homologación fuera de MASTER | Nada |
| Franco Delgado | Pruebas de ingesta (`test_ingesta.py`) | Pruebas de homologación | Nada |
| Gabriel León | Decisión: trabajar en el sandbox de BigQuery mientras no haya facturación (registrada después en el ADR 0008) | CI con GitHub Actions | Facturación, sigue igual |

**Impedimentos resueltos:** traducción de fechas.

### Daily 3 · domingo 4 de octubre

| Integrante | Qué terminé | Qué haré | Qué me bloquea |
|---|---|---|---|
| Cristhian Pimentel | Carga a RAW y registro de cargas (HU-01); catálogo de reglas N1 (HU-02) | Estado de cada regla y muestras de fallidos | Un `COUNTIF` sobre un conjunto vacío devuelve `NULL` en DuckDB |
| Jesus de la Cruz | Homologación con incidencias (HU-14); contrato DAC por tabla (HU-05) | Llaves AEAD y cifrado (HU-06) | DuckDB 1.5 eliminó `duckdb.typing`; las funciones de cifrado no se registran |
| Franco Delgado | Verificación contra el manifiesto: 0 diferencias en ingesta y homologación | Prueba de las reglas N1 contra el manifiesto | Nada |
| Gabriel León | CI en verde; contratos en Firestore | Carga de los cortes en BigQuery | Facturación |

**Impedimentos nuevos:** `COUNTIF` vacío (Cristhian); `duckdb.typing` (Jesus).

### Daily 4 · lunes 5 de octubre

| Integrante | Qué terminé | Qué haré | Qué me bloquea |
|---|---|---|---|
| Cristhian Pimentel | Motor N1 con estados según umbral y muestras de fallidos (HU-02); el `COUNTIF` vacío se trata como 0 | Demo de la revisión | Nada |
| Jesus de la Cruz | Cifrado determinístico y aleatorio con `duckdb.sqltypes`; el motor descifra solo en memoria (HU-06, ADR 0007) | Demo de la revisión | Nada |
| Franco Delgado | Prueba de aceptación: 0 diferencias en ingesta, homologación y reglas | Preparar la revisión y la retrospectiva | Nada |
| Gabriel León | Cortes cargados en el sandbox de BigQuery | Revisión con el equipo | Facturación |

**Impedimentos resueltos:** `COUNTIF` vacío; `duckdb.typing`. **Abierto:** facturación.

## Sprint 2 · 6 al 19 de octubre de 2026

### Daily 1 · miércoles 7 de octubre

| Integrante | Qué terminé | Qué haré | Qué me bloquea |
|---|---|---|---|
| Franco Delgado | Reglas de consistencia e integridad (N2) del catálogo (HU-03) | Reglas de oportunidad y volumetría (N3) | Nada |
| Cristhian Pimentel | Nivel de cada regla según su dimensión | Dominio Póliza o Persona en cada resultado | Nada |
| Jesus de la Cruz | Revisión de la clasificación DAC para el Gate de privacidad | Diseño de la revisión de PII en claro | Nada |
| Gabriel León | Refinamiento de los criterios de HU-04 y HU-07 con el equipo | Revisar las reglas N2 | Facturación |

### Daily 2 · jueves 8 de octubre

| Integrante | Qué terminé | Qué haré | Qué me bloquea |
|---|---|---|---|
| Franco Delgado | Reglas N3 de oportunidad y volumetría (HU-03) | Validación de una regla antes de guardarla | Nada |
| Cristhian Pimentel | Dominio en cada resultado (HU-03) | Reglas en Firestore con la versión del catálogo | Nada |
| Jesus de la Cruz | Diseño de la revisión de privacidad | Empezar la revisión de PII en claro (HU-07) | Nada |
| Gabriel León | Revisión de las reglas N2 | Preparar la aceptación de HU-03 | DuckDB pide `pytz` para las fechas con zona horaria |

**Impedimento nuevo:** `pytz` en DuckDB.

### Daily 3 · viernes 9 de octubre

| Integrante | Qué terminé | Qué haré | Qué me bloquea |
|---|---|---|---|
| Franco Delgado | Validación de reglas antes de guardarlas; HU-03 lista para revisión | Certificación en tres estados (HU-04) | Nada |
| Cristhian Pimentel | Reglas en Firestore con versión; `pytz` agregado a las dependencias locales | Apoyo en la certificación | Nada |
| Jesus de la Cruz | Revisión de privacidad: DNI, celulares y correos en claro (HU-07) | Hallazgos como evidencia | Nada |
| Gabriel León | **HU-03 aceptada** | Criterios de bloqueo para HU-04 | Facturación |

**Impedimento resuelto:** `pytz`.

### Daily 4 · lunes 12 de octubre

| Integrante | Qué terminé | Qué haré | Qué me bloquea |
|---|---|---|---|
| Franco Delgado | Certificación en tres estados (HU-04) | Bloqueo por severidad: CRÍTICA o ALTA en FALLA | Una prueba combina `QUALIFY` con una agregación, que no es SQL válido |
| Cristhian Pimentel | Matriz de certificación por corte | Sello con versión del motor y de reglas | Nada |
| Jesus de la Cruz | Hallazgos guardados en `dq_engine.hallazgos_privacidad` (HU-07) | Que un hallazgo bloqueante impida certificar | Nada |
| Gabriel León | Revisión de los estados de certificación | Aceptación de HU-04 | Facturación |

**Impedimento nuevo:** consulta de prueba con `QUALIFY`.

### Daily 5 · martes 13 de octubre

| Integrante | Qué terminé | Qué haré | Qué me bloquea |
|---|---|---|---|
| Franco Delgado | Bloqueo por severidad; la consulta de prueba se reescribió con una CTE | Cerrar HU-04 | Nada |
| Cristhian Pimentel | Sello por tabla y corte con versión del motor y de reglas (HU-04) | Apoyo en el flujo por corte de HU-07 | Nada |
| Jesus de la Cruz | Avance en el bloqueo por hallazgos | Seguir con el bloqueo por hallazgos | Nada |
| Gabriel León | **HU-04 aceptada** | Seguimiento de HU-07 | Facturación |

**Impedimento resuelto:** consulta de prueba con `QUALIFY`.

### Daily 6 · miércoles 14 de octubre

| Integrante | Qué terminé | Qué haré | Qué me bloquea |
|---|---|---|---|
| Franco Delgado | Casos de prueba de privacidad contra el manifiesto | Prueba de la fuga de PII | Nada |
| Cristhian Pimentel | Datos diarios de julio a septiembre para las pruebas | Flujo por corte con privacidad | Nada |
| Jesus de la Cruz | Bloqueo por hallazgos, en pruebas | Terminar el bloqueo por hallazgos | Nada |
| Gabriel León | Seguimiento del sprint: 10 de 23 SP aceptados | Revisión del prototipo del portal | Facturación |

### Daily 7 · jueves 15 de octubre

| Integrante | Qué terminé | Qué haré | Qué me bloquea |
|---|---|---|---|
| Franco Delgado | Prueba de la fuga de PII sobre los datos diarios | Cerrar las tareas de HU-07 y empezar HU-08 | Nada |
| Cristhian Pimentel | Avance del flujo por corte con privacidad | Publicación en BUSINESS (HU-08) | Nada |
| Jesus de la Cruz | Avance del bloqueo por hallazgos | Cerrarlo | Nada |
| Gabriel León | Recarga de los 92 cortes en BigQuery, en marcha | Seguir la recarga | La recarga en el sandbox tarda horas |

**Impedimento nuevo:** la recarga en BigQuery tarda horas (la evidencia de HU-08 depende de ella).

### Daily 8 · viernes 16 de octubre

| Integrante | Qué terminé | Qué haré | Qué me bloquea |
|---|---|---|---|
| Franco Delgado | Tareas de HU-07 cerradas: el Gate encuentra las 8 fugas sembradas, ni una más | Pruebas de BUSINESS (HU-08) | Nada |
| Cristhian Pimentel | Flujo por corte con privacidad: ingesta, homologación, motor, Gate, certificación y publicación (HU-07) | Tablas `p_` y vistas `v_` por tabla (HU-08) | Nada |
| Jesus de la Cruz | Bloqueo por hallazgos: una fuga de PII impide certificar aunque la calidad esté bien | Vistas de contrato `v_calidad_*` | Nada |
| Gabriel León | Revisión de los criterios de HU-07 con el equipo | Preparar la revisión del sprint | La recarga de BigQuery se cortó a mitad de camino |

**Impedimento:** la recarga de BigQuery se cortó y no se puede reanudar; volver a empezar toma unas 9 horas.

### Daily 9 · lunes 19 de octubre

| Integrante | Qué terminé | Qué haré | Qué me bloquea |
|---|---|---|---|
| Franco Delgado | Pruebas de BUSINESS: solo cortes certificados, el último certificado en cada vista y nada de PII en claro | Demostración en la revisión | Nada |
| Cristhian Pimentel | Tablas `p_` y vistas `v_` de las cinco tablas (HU-08) | Demostración en la revisión | Nada |
| Jesus de la Cruz | Vistas de contrato; el portal solo lee BUSINESS | Demostración en la revisión | Nada |
| Gabriel León | Criterios de HU-07 y HU-08 revisados contra las pruebas | Revisión y retrospectiva | La evidencia de BigQuery sigue con los datos mensuales |
