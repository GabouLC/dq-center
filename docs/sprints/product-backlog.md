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

| Orden | Historia | Rol del backlog | SP | Sprint | Estado | Issue |
|---|---|---|---|---|---|---|
| 1 | HU-01 · Ingestar datos sintéticos en la capa RAW | Data Engineer | 3 | 1 | Terminada | [#1](https://github.com/GabouLC/dq-center/issues/1) |
| 2 | HU-14 · Homologar el modelo de datos hacia la capa MASTER | Data Architect | 5 | 1 | Terminada | [#14](https://github.com/GabouLC/dq-center/issues/14) |
| 3 | HU-05 · Clasificar datos según la taxonomía DAC | Data Architect | 3 | 1 | Terminada | [#5](https://github.com/GabouLC/dq-center/issues/5) |
| 4 | HU-02 · Ejecutar validaciones de calidad de Nivel 1 | Data Engineer | 3 | 1 | Terminada | [#2](https://github.com/GabouLC/dq-center/issues/2) |
| 5 | HU-06 · Cifrar automáticamente los datos sensibles | Data Architect | 8 | 1 | Terminada | [#6](https://github.com/GabouLC/dq-center/issues/6) |
| 6 | HU-03 · Ejecutar reglas de calidad de Nivel 2 | QA Specialist | 5 * | 2 | Terminada | [#3](https://github.com/GabouLC/dq-center/issues/3) |
| 7 | HU-04 · Certificar la calidad de los datos | QA Specialist | 5 * | 2 | Terminada | [#4](https://github.com/GabouLC/dq-center/issues/4) |
| 8 | HU-07 · Ejecutar el Quality & Privacy Gate | Data Owner | 8 * | 2 | Terminada | [#7](https://github.com/GabouLC/dq-center/issues/7) |
| 9 | HU-08 · Publicar datos certificados en BUSINESS | Data Owner | 3 * | 2 | Terminada | [#8](https://github.com/GabouLC/dq-center/issues/8) |
| 10 | HU-13 · Controlar el acceso a datos sensibles mediante roles | Data Architect | 5 * | 3 | Terminada | [#13](https://github.com/GabouLC/dq-center/issues/13) |
| 11 | HU-09 · Visualizar el estado de calidad de los datos | Oficina de Datos | 5 * | 3 | Terminada | [#9](https://github.com/GabouLC/dq-center/issues/9) |
| 12 | HU-12 · Consultar la certificación integral del dato | Data Owner | 3 * | 3 | Terminada | [#12](https://github.com/GabouLC/dq-center/issues/12) |
| 13 | HU-11 · Consultar el linaje de los datos | Oficina de Datos | 5 * | 3 | Terminada | [#11](https://github.com/GabouLC/dq-center/issues/11) |
| 14 | HU-10 · Consultar el glosario de negocio | Negocio | 2 * | 3 | Terminada | [#10](https://github.com/GabouLC/dq-center/issues/10) |
| 15 | HU-15 · Garantizar el tiempo de carga del portal | Negocio | 3 * | 3 | Terminada | [#15](https://github.com/GabouLC/dq-center/issues/15) |
| | **Total** | | **66** | | | |

\* Estimación propuesta con la escala del Sprint 1; se confirma con el equipo (planning poker).

## Escala de estimación

Story points en Fibonacci, como en el *Sprint 1 Planning*:

| SP | Complejidad | Ejemplo |
|---|---|---|
| 2 | Baja | HU-10: lectura y búsqueda sobre un catálogo |
| 3 | Baja-media | HU-01: carga y validación de estructura |
| 5 | Media | HU-14: homologación de varias fuentes con incidencias |
| 8 | Alta | HU-06: cifrado determinístico y aleatorio con llaves por campo |

## Refinamiento

Cambios al backlog que salieron de las revisiones:

| Fecha | Cambio | Origen |
|---|---|---|
| 2026-10-15 | HU-13 suma el inicio de sesión con correo y contraseña, el bloqueo por intentos y la contraseña temporal | Revisión del Sprint 3: «tiene que ser un inicio de sesión, no elegir roles» |
| 2026-10-15 | Se agrega como trabajo pendiente el despliegue en Cloud Run (no es una HU del backlog) | Impedimento abierto: facturación de GCP |

## Pendiente fuera de las historias

- Desplegar API, web y motor en Cloud Run cuando la facturación esté activa (ADR 0003).
- Activar el inicio de sesión con Google (Firebase) si el equipo lo quiere además de la contraseña (ADR 0011).
