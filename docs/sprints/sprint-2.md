# Sprint 2 · Motor y Gate

**Estado:** en curso · **Fechas:** martes 6 al lunes 19 de octubre de 2026 (dos semanas) ·
**Compromiso:** 23 SP, 4 historias · **Avance:** 10 de 23 SP (HU-03 y HU-04 aceptadas) ·
**Milestone:** [Sprint 2](https://github.com/GabouLC/dq-center/milestone/3) ·
**Jira:** SDGDCYP Sprint 2 (activo)

El repositorio ya tiene código para las cuatro historias (commit
[`565aa0a`](https://github.com/GabouLC/dq-center/commit/565aa0a)). El tablero refleja otra cosa: las
tareas que el equipo dio por cerradas y las historias que el Product Owner ya aceptó.

## 1. Sprint Planning

**Fecha, duración y asistentes:** martes 6 de octubre de 2026; dos semanas, hasta el lunes 19 de
octubre. Asistentes: completar.

### ¿Por qué es valioso este sprint? · Objetivo del sprint

**Objetivo del sprint.** Que cada corte salga del pipeline con un veredicto: reglas de Nivel 2
y 3, certificación en tres estados, Quality & Privacy Gate y publicación en BUSINESS solo de
lo certificado.

**Valor.** Al cerrar el sprint, cada tabla de cada corte tiene un veredicto con su porqué, y
BUSINESS expone solo lo que pasó el Gate: el negocio deja de consumir datos sin revisar.

### ¿Qué se puede terminar? · Historias seleccionadas

**Capacidad.** Velocidad sugerida de 20 a 24 SP; el Sprint 1 cerró 22. Se comprometen 23.

**Historias priorizadas.** Los puntos son los del Product Backlog del equipo en Jira.

| # | Historia | SP | Complejidad | Rol del backlog | Responsable | Issue | Estado |
|---|---|---|---|---|---|---|---|
| 1 | HU-03 · Ejecutar reglas de calidad de Nivel 2 | 5 | Media | QA Specialist | Franco Delgado | [#3](https://github.com/GabouLC/dq-center/issues/3) | Aceptada |
| 2 | HU-04 · Certificar la calidad de los datos | 5 | Media | QA Specialist | Franco Delgado | [#4](https://github.com/GabouLC/dq-center/issues/4) | Aceptada |
| 3 | HU-07 · Ejecutar el Quality & Privacy Gate | 8 | Alta | Data Owner | Franco Delgado | [#7](https://github.com/GabouLC/dq-center/issues/7) | En curso |
| 4 | HU-08 · Publicar datos certificados en BUSINESS | 5 | Media | Data Owner | Franco Delgado | [#8](https://github.com/GabouLC/dq-center/issues/8) | Por hacer |

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

Las tareas de cada historia, con su responsable. Tablero al día de hoy:

| Historias | Tareas por hacer | Tareas hechas |
|---|---|---|
| 2 aceptadas, 1 en curso, 1 por hacer | 5 | 9 de 14 |

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
- [ ] Un hallazgo bloqueante impide certificar aunque la calidad esté bien
- [ ] Flujo por corte: ingesta, homologación, motor, privacidad, certificación y publicación (`src/dqc/pipeline/flujo.py`)

**HU-08 · Publicación en BUSINESS** · Franco Delgado
- [ ] Tablas `p_<tabla>` solo con cortes certificados y vistas `v_<tabla>` con el último certificado (`src/dqc/pipeline/publicacion.py`)
- [ ] Vistas de contrato `v_calidad_*`, la única interfaz del portal con los resultados
- [ ] Corrida completa en BigQuery: las mismas tablas y vistas en `dq_business`

## 3. Seguimiento · Daily Scrum

**Impedimentos registrados**

| Impedimento | Efecto | Resolución | Estado |
|---|---|---|---|
| Sigue sin facturación en GCP | No hay Cloud Run Job ni Scheduler para la corrida diaria | El flujo corre por línea de comandos; el Job queda listo para cuando haya facturación (ADR 0003) | Abierto |
| La recarga diaria en BigQuery (92 cortes) tarda horas en el sandbox | La evidencia de BigQuery se actualiza recién al terminar | Corre de fondo; HU-08 la usa como criterio de cierre | Abierto |
| DuckDB necesita `pytz` para las fechas con zona horaria | Fallaba el sello de la certificación en local | `pytz` se agregó a las dependencias locales | Resuelto |
| Una consulta de prueba combinaba `QUALIFY` con una agregación, que no es SQL válido | Fallaba la prueba de la última certificación por tabla | Se reescribió con una CTE | Resuelto |

**Burndown.** 23 SP comprometidos; quedan 13 (HU-07 y HU-08). La línea diaria real sale del
tablero de Jira; la plantilla está en [plantillas.md](plantillas.md).

| Momento | SP pendientes |
|---|---|
| Inicio (6 de octubre) | 23 |
| Hoy | 13 |
| Cierre (19 de octubre) | 0 previstos |

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

La revisión del sprint es al cierre, el 19 de octubre. Hasta hoy, el Product Owner aceptó HU-03 y
HU-04 con esta evidencia; HU-07 y HU-08 se revisan al cierre.

**Avance del incremento.** El motor evalúa las 48 reglas en tres niveles y certifica cada tabla en
cada uno de los 92 cortes diarios. La verificación contra el manifiesto da 0 diferencias en las
reglas ([pipeline-local.txt](../evidencias/pipeline-local.txt)).

### HU-03 · Ejecutar reglas de calidad de Nivel 2

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Con reglas configuradas, el motor las evalúa automáticamente | `test_catalogo_tiene_36_reglas_y_48_expandidas`, `test_cada_corte_evalua_las_48_reglas_con_su_nivel` ([test_motor.py](../../tests/test_motor.py)) | 14 reglas N2 y hasta 15 N3 en cada uno de los 92 cortes ([pipeline-local.txt](../evidencias/pipeline-local.txt)) |
| Si los datos cumplen, se registra PASS | `test_estado_segun_umbral` ([test_reglas.py](../../tests/test_reglas.py)) | [Validaciones del 14 de julio](../evidencias/portal/hu02-hu03-validaciones-14-julio.png) |
| Si incumplen, se registra FAIL con observación | `test_hay_reglas_en_ok_alerta_y_falla`, `test_cada_etapa_detecta_exactamente_lo_sembrado` ([test_flujo.py](../../tests/test_flujo.py)) | Reglas fuera de OK por corte en [pipeline-local.txt](../evidencias/pipeline-local.txt) |
| Se identifican las reglas que impiden la certificación | `test_la_certificacion_dice_que_reglas_la_bloquean` ([test_certificacion.py](../../tests/test_certificacion.py)) | Motivo de cada día sin certificar en [pipeline-local.txt](../evidencias/pipeline-local.txt) |
| Las reglas se asocian a los dominios Póliza y Persona (detalle del backlog) | `test_los_resultados_se_asocian_a_los_dominios_poliza_y_persona` | [Certificación](../evidencias/portal/hu04-hu07-hu12-certificacion-7-agosto.png): dominio en cada sello |

### HU-04 · Certificar la calidad de los datos

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Se consolidan los resultados de los niveles | `test_matriz_de_certificacion` ([test_certificacion.py](../../tests/test_certificacion.py)) | Barras N1, N2 y N3 de cada sello ([captura](../evidencias/portal/hu04-hu12-certificacion-30-septiembre.png)) |
| Con las reglas requeridas en PASS, los datos quedan certificados | `test_una_media_en_falla_no_bloquea`, `test_matriz_de_certificacion` | 452 de 460 sellos certificados: 31 sin observaciones (Vehículo tras la limpieza, Póliza algunos días de julio) y 421 con observaciones ([pipeline-local.txt](../evidencias/pipeline-local.txt)) |
| Con una regla requerida en FAIL, no se certifican | `test_la_certificacion_dice_que_reglas_la_bloquean` | Persona el 14 y el 22 de julio; Póliza el 20 de agosto y del 28 al 30 de septiembre |
| El resultado se registra para la trazabilidad | `test_cada_certificacion_lleva_su_sello` | Corrida, versión de motor y reglas, cobertura y fecha en cada sello; [Ejecuciones](../evidencias/portal/hu04-ejecuciones.png) |

### HU-07 y HU-08 · En curso

Se revisan al cierre con sus criterios de aceptación del Product Backlog. Las pruebas que las
cubrirán ya existen en el repositorio (`test_una_fuga_de_pii_bloquea_aunque_la_calidad_este_bien`,
`test_business_solo_tiene_cortes_certificados`, `test_el_portal_solo_lee_la_capa_business`); falta
cerrar sus tareas y la evidencia de BigQuery.

### Definition of Done de las historias aceptadas

| Criterio de la Definition of Done | HU-03 | HU-04 |
|---|---|---|
| Código en `main` y CI en verde | Sí | Sí |
| Cada criterio de aceptación con prueba automatizada | 4 de 4, más el detalle de dominios | 4 de 4 |
| 0 diferencias contra el manifiesto | Reglas | No aplica: la matriz se verifica con `test_matriz_de_certificacion` |
| Desvíos del documento de arquitectura en un ADR | [0004](../adr/0004-evaluacion-sql.md) | No hubo |
| Evidencia en `docs/evidencias` | Sí | Sí |
| Issue cerrado y enlazado a su evidencia | [#3](https://github.com/GabouLC/dq-center/issues/3) | [#4](https://github.com/GabouLC/dq-center/issues/4) |

### Reunión de revisión

- **Fecha:** lunes 19 de octubre de 2026 (al cierre del sprint). Asistentes: completar.
- **Historias para demostrar:** las cuatro; HU-03 y HU-04 ya aceptadas.
- **Comentarios de los interesados:** completar con la plantilla de [plantillas.md](plantillas.md).

## 5. Sprint Retrospective

Se hace al cierre, el 19 de octubre, con la plantilla de [plantillas.md](plantillas.md). Notas
para llevar:

- La prueba con el manifiesto se extendió a la privacidad: el Gate encuentra exactamente las 8
  fugas sembradas (5 el 7 de agosto y 3 el 8).
- Los puntos del Jira y los del documento del sprint no coincidían; se unificaron con los del
  equipo.
- Sin facturación no se puede programar la corrida diaria ni acelerar la recarga en BigQuery.
