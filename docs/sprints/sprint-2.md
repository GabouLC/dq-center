# Sprint 2 · Motor y Gate

**Estado:** terminado · **Compromiso:** 21 SP (propuesta), 4 historias · **Terminado:** 21 SP,
4 historias · **Incremento:** commit [`565aa0a`](https://github.com/GabouLC/dq-center/commit/565aa0a) ·
**Milestone:** [Sprint 2](https://github.com/GabouLC/dq-center/milestone/3)

## 1. Sprint Planning

**Fecha, duración y asistentes:** completar con el calendario del equipo.

### ¿Por qué es valioso este sprint? · Objetivo del sprint

**Objetivo del sprint.** Que cada corte salga del pipeline con un veredicto: reglas de Nivel 2
y 3, certificación en tres estados, Quality & Privacy Gate y publicación en BUSINESS solo de
lo certificado.

**Valor.** Al cerrar el sprint, cada tabla de cada corte tiene un veredicto con su porqué, y
BUSINESS expone solo lo que pasó el Gate: el negocio deja de consumir datos sin revisar.

### ¿Qué se puede terminar? · Historias seleccionadas

**Capacidad.** Velocidad sugerida de 20 a 24 SP; el Sprint 1 cerró 22. Se comprometen 21.

**Historias priorizadas.** Los puntos son una propuesta con la escala del Sprint 1 y se
confirman con el equipo.

| # | Historia | SP | Complejidad | Rol del backlog | Responsable | Issue |
|---|---|---|---|---|---|---|
| 1 | HU-03 · Ejecutar reglas de calidad de Nivel 2 | 5 | Media | QA Specialist | Franco Delgado | [#3](https://github.com/GabouLC/dq-center/issues/3) |
| 2 | HU-04 · Certificar la calidad de los datos | 5 | Media | QA Specialist | Franco Delgado | [#4](https://github.com/GabouLC/dq-center/issues/4) |
| 3 | HU-07 · Ejecutar el Quality & Privacy Gate | 8 | Alta | Data Owner | Franco Delgado | [#7](https://github.com/GabouLC/dq-center/issues/7) |
| 4 | HU-08 · Publicar datos certificados en BUSINESS | 3 | Baja-media | Data Owner | Franco Delgado | [#8](https://github.com/GabouLC/dq-center/issues/8) |

**Por qué este orden.**

- HU-03 completa los tres niveles de calidad: sin N2 ni N3 no hay nada que certificar.
- HU-04 consolida los resultados de los tres niveles en un veredicto por tabla y corte.
- HU-07 suma la privacidad al veredicto. Es la historia de mayor riesgo, porque une calidad y
  protección, y depende del cifrado del Sprint 1 (HU-06) y de la certificación (HU-04).
- HU-08 va al final: solo se publica lo que el Gate aprobó.

**Fuera del sprint.** El portal, el acceso por rol y el rendimiento (Sprint 3).

### ¿Cómo se hará? · Plan de trabajo

Se completan primero los niveles N2 y N3 del motor, luego la certificación sobre sus
resultados, después la revisión de privacidad que convierte la certificación en el Gate, y al
final la publicación. El manifiesto de errores sembrados se extiende a la etapa de privacidad
para que el Gate tenga la misma prueba de aceptación que el motor.

## 2. Sprint Backlog

Las tareas de cada historia, con su responsable. Al cierre del sprint el tablero quedó así:

| Por hacer | En curso | Hechas |
|---|---|---|
| 0 | 0 | 14 tareas de 4 historias |

**HU-03 · Reglas N2 y N3** · Franco Delgado
- [x] Reglas de consistencia e integridad (N2) y de oportunidad y volumetría (N3); el nivel sale de la dimensión (`NIVEL_POR_DIMENSION` en `src/dqc/modelo.py`)
- [x] Cada resultado lleva su dominio, Póliza o Persona (`DOMINIO_POR_TABLA`)
- [x] Validación de una regla antes de guardarla: tipo, campos y umbral (`src/dqc/motor/reglas.py`)
- [x] Reglas en Firestore, con la versión del catálogo en cada ejecución

**HU-04 · Certificación** · Franco Delgado
- [x] Tres estados: Certificado, Certificado con observaciones y No certificado (`src/dqc/motor/certificacion.py`)
- [x] Una regla CRÍTICA o ALTA en FALLA bloquea; una MEDIA o una ALERTA quedan como observación
- [x] Sello por tabla y corte con versión del motor, versión de reglas y cobertura (`dq_engine.certificaciones`)

**HU-07 · Quality & Privacy Gate** · Franco Delgado
- [x] Revisión de privacidad: DNI, celulares o correos en claro fuera de los campos cifrados, campos PII sin cifrar y columnas nuevas sin clasificar (`src/dqc/pipeline/privacidad.py`)
- [x] Hallazgos guardados como evidencia (`dq_engine.hallazgos_privacidad`)
- [x] Un hallazgo bloqueante impide certificar aunque la calidad esté bien
- [x] Flujo por corte: ingesta, homologación, motor, privacidad, certificación y publicación (`src/dqc/pipeline/flujo.py`)

**HU-08 · Publicación en BUSINESS** · Franco Delgado
- [x] Tablas `p_<tabla>` solo con cortes certificados y vistas `v_<tabla>` con el último certificado (`src/dqc/pipeline/publicacion.py`)
- [x] Vistas de contrato `v_calidad_*`, la única interfaz del portal con los resultados
- [x] Corrida completa en BigQuery: las mismas tablas y vistas en `dq_business`

## 3. Seguimiento · Daily Scrum

**Impedimentos registrados**

| Impedimento | Efecto | Resolución | Estado |
|---|---|---|---|
| Sigue sin facturación en GCP | No hay Cloud Run Job ni Scheduler para la corrida diaria | El flujo corre por línea de comandos; el Job queda listo para cuando haya facturación (ADR 0003) | Abierto |
| DuckDB necesita `pytz` para las fechas con zona horaria | Fallaba el sello de la certificación en local | `pytz` se agregó a las dependencias locales | Resuelto |
| Una consulta de prueba combinaba `QUALIFY` con una agregación, que no es SQL válido | Fallaba la prueba de la última certificación por tabla | Se reescribió con una CTE | Resuelto |

**Burndown.** Igual que en el Sprint 1, el incremento entró en un solo commit (`565aa0a`). La
línea diaria se registra con [plantillas.md](plantillas.md). Resultado: 21 de 21 SP, sin arrastre.

**Registro de Daily Scrum.** Una fila por daily; el acta completa de cada una va con el formato
de [plantillas.md](plantillas.md).

| Daily | Fecha | Avance del equipo | Impedimentos nuevos |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |

## 4. Sprint Review e Incremento

**Incremento.** Cada uno de los 6 cortes recibe un sello por tabla. Matriz resultante, igual
en DuckDB y en BigQuery:

| Tabla | abr | may | jun | jul | ago | set |
|---|---|---|---|---|---|---|
| Persona | Obs. | Obs. | Obs. | **No cert.** (GEN-OPO-01: llegó tarde) | Obs. | Obs. |
| Póliza | Obs. | Obs. | Obs. | Obs. | **No cert.** (GEN-VOL-01: +22 % de volumen) | Obs. |
| Vehículo | Obs. | Obs. | Obs. | Obs. | Obs. | Obs. |
| Siniestro | Obs. | Obs. | **No cert.** (DNI en claro en `causa`) | Obs. | Obs. | Obs. |
| Pago | Obs. | Obs. | Obs. | Obs. | Obs. | Obs. |

Cada no certificación corresponde a un error sembrado a propósito, y la verificación contra el
manifiesto da 0 diferencias también en la etapa de privacidad
([pipeline-local.txt](../evidencias/pipeline-local.txt), [bigquery.txt](../evidencias/bigquery.txt)).

**Resultado:** 4 de 4 historias aceptadas.

### HU-03 · Ejecutar reglas de calidad de Nivel 2

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Con reglas configuradas, el motor las evalúa automáticamente | `test_catalogo_tiene_36_reglas_y_48_expandidas`, `test_cada_corte_evalua_las_48_reglas_con_su_nivel` ([test_motor.py](../../tests/test_motor.py)) | 14 reglas N2 y hasta 15 N3 por corte ([bigquery.txt](../evidencias/bigquery.txt)) |
| Si los datos cumplen, se registra PASS | `test_estado_segun_umbral` ([test_reglas.py](../../tests/test_reglas.py)) | [Validaciones de julio](../evidencias/portal/hu02-hu03-validaciones-julio.png) |
| Si incumplen, se registra FAIL con observación | `test_hay_reglas_en_ok_alerta_y_falla`, `test_cada_etapa_detecta_exactamente_lo_sembrado` ([test_flujo.py](../../tests/test_flujo.py)) | Reglas fuera de OK por corte en [pipeline-local.txt](../evidencias/pipeline-local.txt) |
| Se identifican las reglas que impiden la certificación | `test_la_certificacion_dice_que_reglas_la_bloquean` ([test_certificacion.py](../../tests/test_certificacion.py)) | Columna `reglas_bloqueantes` en [bigquery.txt](../evidencias/bigquery.txt) |
| Las reglas se asocian a los dominios Póliza y Persona (detalle del backlog) | `test_los_resultados_se_asocian_a_los_dominios_poliza_y_persona` | [Certificación](../evidencias/portal/hu04-hu07-hu12-certificacion-junio.png): dominio en cada sello |

### HU-04 · Certificar la calidad de los datos

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Se consolidan los resultados de los niveles | `test_matriz_de_certificacion` ([test_certificacion.py](../../tests/test_certificacion.py)) | Barras N1, N2 y N3 de cada sello ([captura](../evidencias/portal/hu04-hu12-certificacion-septiembre.png)) |
| Con las reglas requeridas en PASS, los datos quedan certificados | `test_una_media_en_falla_no_bloquea`, `test_matriz_de_certificacion` | 27 de 30 sellos certificados, todos con observaciones de reglas MEDIA o en ALERTA ([bigquery.txt](../evidencias/bigquery.txt)) |
| Con una regla requerida en FAIL, no se certifican | `test_la_certificacion_dice_que_reglas_la_bloquean` | Persona en julio y Póliza en agosto, *No certificada* |
| El resultado se registra para la trazabilidad | `test_cada_certificacion_lleva_su_sello` | Corrida, versión de motor y reglas, cobertura y fecha en cada sello; [Ejecuciones](../evidencias/portal/hu04-ejecuciones.png) |

### HU-07 · Ejecutar el Quality & Privacy Gate

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| El Gate valida calidad y privacidad sobre MASTER | `test_cada_etapa_detecta_exactamente_lo_sembrado` ([test_flujo.py](../../tests/test_flujo.py)) | Privacidad: 0 sin detectar y 0 de más ([pipeline-local.txt](../evidencias/pipeline-local.txt)) |
| Si cumple, queda habilitado hacia BUSINESS | `test_business_solo_tiene_cortes_certificados` ([test_certificacion.py](../../tests/test_certificacion.py)) | Columna `publicado` en [bigquery.txt](../evidencias/bigquery.txt) |
| Si no cumple una validación obligatoria, impide la certificación | `test_una_fuga_de_pii_bloquea_aunque_la_calidad_este_bien` | [Siniestro en junio](../evidencias/portal/hu04-hu07-hu12-certificacion-junio.png): *PII en texto claro en causa · 6 registros*, retenido por el Gate |
| Se conserva la evidencia del proceso | `test_columna_nueva_sin_clasificar_es_observacion`, `test_cada_certificacion_lleva_su_sello` | Hallazgos del Gate en [bigquery.txt](../evidencias/bigquery.txt) |

### HU-08 · Publicar datos certificados en BUSINESS

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Lo que aprobó el Gate queda disponible en BUSINESS | `test_business_solo_tiene_cortes_certificados` ([test_certificacion.py](../../tests/test_certificacion.py)) | Tablas `p_*` en `dq_business` ([bigquery.txt](../evidencias/bigquery.txt)) |
| Lo que no aprobó no se expone | `test_business_solo_tiene_cortes_certificados`, `test_la_vista_de_cada_tabla_muestra_su_ultimo_corte_certificado` | Siniestro de junio: *Retenido por el Gate* ([captura](../evidencias/portal/hu04-hu07-hu12-certificacion-junio.png)) |
| Los datos se publican en las vistas de BUSINESS | `test_las_vistas_de_contrato_responden`, `test_business_no_expone_pii_en_claro` | 5 tablas `p_`, 5 vistas `v_` y 8 vistas `v_calidad_*` ([bigquery.txt](../evidencias/bigquery.txt)) |
| El portal accede únicamente a BUSINESS | `test_el_portal_solo_lee_la_capa_business` ([test_api.py](../../tests/test_api.py)) | `src/dqc/api/datos.py` lee solo vistas `v_calidad_*` |

### Definition of Done por historia

| Criterio de la Definition of Done | HU-03 | HU-04 | HU-07 | HU-08 |
|---|---|---|---|---|
| Código en `main` y CI en verde | Sí | Sí | Sí | Sí |
| Cada criterio de aceptación con prueba automatizada | 4 de 4, más el detalle de dominios | 4 de 4 | 4 de 4 | 4 de 4 |
| 0 diferencias contra el manifiesto | Reglas | No aplica: la matriz se verifica con `test_matriz_de_certificacion` | Privacidad | No aplica |
| Desvíos del documento de arquitectura en un ADR | [0004](../adr/0004-evaluacion-sql.md) | No hubo | [0006](../adr/0006-capas-y-privacy-gate.md), [0007](../adr/0007-pii-solo-en-memoria.md) | No hubo: mantiene las vistas de contrato del documento |
| Evidencia en `docs/evidencias` | Sí | Sí | Sí | Sí |
| Issue cerrado y enlazado a su evidencia | [#3](https://github.com/GabouLC/dq-center/issues/3) | [#4](https://github.com/GabouLC/dq-center/issues/4) | [#7](https://github.com/GabouLC/dq-center/issues/7) | [#8](https://github.com/GabouLC/dq-center/issues/8) |

Las cuatro historias cumplen la Definition of Done: forman el incremento del Sprint 2.

### Reunión de revisión

- **Fecha y asistentes:** completar.
- **Historias demostradas y aceptadas:** las cuatro, con la matriz de certificación de la sección 4.
- **Comentarios de los interesados:** completar con la plantilla de [plantillas.md](plantillas.md).

**Product Backlog tras la revisión.** Sin historias nuevas. Siguen, en orden: HU-13, HU-09,
HU-12, HU-11, HU-10 y HU-15 (Sprint 3).

## 5. Sprint Retrospective (borrador con los hechos del sprint)

| Funcionó | Por mejorar |
|---|---|
| La prueba con el manifiesto se extendió a la privacidad: el Gate encuentra exactamente las 6 fugas sembradas. | Los puntos de este sprint no se estimaron en una planificación formal; se proponen después. |
| Separar *bloquea* de *observa* evitó que una regla de severidad media frene la publicación. | Otra vez un solo commit para todo el sprint. |
| La misma corrida en BigQuery dio la misma matriz que en local. | Sin facturación no se pudo programar la corrida diaria. |

**Acciones propuestas:** estimar en la planificación del Sprint 3 antes de empezar; un PR por
historia; dejar listo el Cloud Run Job aunque no se pueda desplegar. Completar con la opinión
del equipo usando [plantillas.md](plantillas.md).
