# Product Backlog

Fuente: *Product Backlog – Diseño e Implementación* del Grupo 6 (10/09/2026), con las 15
historias y sus criterios de aceptación. Aquí se mantiene ordenado y con su estado; cada
historia es un issue en GitHub.

## Objetivo del producto

Que el negocio use solo datos de Póliza y Persona certificados en calidad, privacidad y
trazabilidad, y que lo compruebe por sí mismo en un portal, reduciendo la validación de
semanas a horas.

*Redactado a partir de los objetivos que el backlog repite en HU-04, HU-10 y HU-12; el Product
Owner lo confirma.*

## Backlog ordenado

El orden aplica los criterios de [README.md](README.md#cómo-se-priorizó): dependencias, riesgo y
valor.

| Orden | Historia | Rol del backlog | SP | Sprint | Estado | Issue | Jira |
|---|---|---|---|---|---|---|---|
| 1 | HU-01 · Ingestar datos sintéticos en la capa RAW | Data Engineer | 3 | 1 | Terminada | [#1](https://github.com/GabouLC/dq-center/issues/1) | SDGDCYP-6 |
| 2 | HU-14 · Homologar el modelo de datos hacia la capa MASTER | Data Architect | 5 | 1 | Terminada | [#14](https://github.com/GabouLC/dq-center/issues/14) | SDGDCYP-7 |
| 3 | HU-05 · Clasificar datos según la taxonomía DAC | Data Architect | 3 | 1 | Terminada | [#5](https://github.com/GabouLC/dq-center/issues/5) | SDGDCYP-8 |
| 4 | HU-02 · Ejecutar validaciones de calidad de Nivel 1 | Data Engineer | 3 | 1 | Terminada | [#2](https://github.com/GabouLC/dq-center/issues/2) | SDGDCYP-9 |
| 5 | HU-06 · Cifrar automáticamente los datos sensibles | Data Architect | 8 | 1 | Terminada | [#6](https://github.com/GabouLC/dq-center/issues/6) | SDGDCYP-10 |
| 6 | HU-03 · Ejecutar reglas de calidad de Nivel 2 | QA Specialist | 5 | 2 | Terminada | [#3](https://github.com/GabouLC/dq-center/issues/3) | SDGDCYP-12 |
| 7 | HU-04 · Certificar la calidad de los datos | QA Specialist | 5 | 2 | Terminada | [#4](https://github.com/GabouLC/dq-center/issues/4) | SDGDCYP-13 |
| 8 | HU-07 · Ejecutar el Quality & Privacy Gate | Data Owner | 8 | 2 | Terminada | [#7](https://github.com/GabouLC/dq-center/issues/7) | SDGDCYP-14 |
| 9 | HU-08 · Publicar datos certificados en BUSINESS | Data Owner | 5 | 2 | Terminada | [#8](https://github.com/GabouLC/dq-center/issues/8) | SDGDCYP-15 |
| 10 | HU-13 · Controlar el acceso a datos sensibles mediante roles | Data Architect | 5 | 3 | Planificada | [#13](https://github.com/GabouLC/dq-center/issues/13) | SDGDCYP-11 |
| 11 | HU-09 · Visualizar el estado de calidad de los datos | Oficina de Datos | 5 | 3 | Planificada | [#9](https://github.com/GabouLC/dq-center/issues/9) | SDGDCYP-16 |
| 12 | HU-12 · Consultar la certificación integral del dato | Data Owner | 5 | 3 | Planificada | [#12](https://github.com/GabouLC/dq-center/issues/12) | SDGDCYP-19 |
| 13 | HU-11 · Consultar el linaje de los datos | Oficina de Datos | 8 | 3 | Planificada | [#11](https://github.com/GabouLC/dq-center/issues/11) | SDGDCYP-18 |
| 14 | HU-10 · Consultar el glosario de negocio | Negocio | 3 | 3 | Planificada | [#10](https://github.com/GabouLC/dq-center/issues/10) | SDGDCYP-17 |
| 15 | HU-15 · Garantizar el tiempo de carga del portal | Negocio | 5 | 3 | Planificada | [#15](https://github.com/GabouLC/dq-center/issues/15) | SDGDCYP-20 |
| | **Total** | | **76** | | | | |

Los puntos son los del Product Backlog del equipo en Jira (proyecto SDGDCYP).

## Escala de estimación

Story points en Fibonacci, como en el *Sprint 1 Planning*:

| SP | Complejidad | Ejemplo |
|---|---|---|
| 3 | Baja-media | HU-01: carga y validación de estructura; HU-10: búsqueda en un catálogo |
| 5 | Media | HU-14: homologación de varias fuentes con incidencias |
| 8 | Alta | HU-06: cifrado determinístico y aleatorio con llaves por campo; HU-11: linaje por campo |

## Refinamiento

Cambios al backlog que salieron de las revisiones:

| Fecha | Cambio | Origen |
|---|---|---|
| 2026-10-15 | HU-13 suma el inicio de sesión con correo y contraseña, el bloqueo por intentos y la contraseña temporal | Comentarios sobre el prototipo del portal: «tiene que ser un inicio de sesión, no elegir roles» |
| 2026-10-15 | Se agrega como trabajo pendiente el despliegue en Cloud Run (no es una HU del backlog) | Impedimento abierto: facturación de GCP |
| 2026-10-05 | Los datos pasan a cortes diarios (tarea técnica del Sprint 2) | Revisión del Sprint 1: con seis cortes mensuales no se ven tendencias ni la puntualidad |
| 2026-10-15 | HU-09 suma la simulación en vivo; los cortes diarios cubren de julio a septiembre con variaciones realistas | Comentarios sobre el prototipo del portal: «que se sienta vivo, con variaciones realistas» |
| 2026-10-19 | HU-12 y HU-11 suman el motivo de la retención y el último corte certificado visible para negocio | Revisión del Sprint 2 |

**Pendiente de decisión del Product Owner.** La [auditoría del catálogo de reglas](../auditoria-reglas.md)
(24 de octubre) propone que las reglas CRÍTICAS no tengan banda de ALERTA, siete reglas nuevas y
ajustes a umbrales y condiciones. Se decide en la Sprint Planning del Sprint 3: cambiaría resultados
ya aceptados en los Sprints 1 y 2.

## Pendiente fuera de las historias

- Desplegar API, web y motor en Cloud Run cuando la facturación esté activa (ADR 0003).
- Activar el inicio de sesión con Google (Firebase) si el equipo lo quiere además de la contraseña (ADR 0011).
