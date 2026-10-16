# Sprint 1 · Base del pipeline

**Estado:** terminado · **Compromiso:** 22 SP, 5 historias · **Terminado:** 22 SP, 5 historias ·
**Incremento:** commits [`369a0d7`](https://github.com/GabouLC/dq-center/commit/369a0d7) y
[`e286dc2`](https://github.com/GabouLC/dq-center/commit/e286dc2), sobre la base técnica de
`6025505` a `6a24f78` · **Milestone:** [Sprint 1](https://github.com/GabouLC/dq-center/milestone/1)

## 1. Sprint Planning

**Fecha, duración y asistentes:** completar con el calendario del equipo. La planificación se
presentó al docente en el *Sprint 1 Planning* (Sprint1_Planning_SMART-DQ.pptx).

### ¿Por qué es valioso este sprint? · Objetivo del sprint

**Objetivo del sprint.** Construir la base del pipeline de datos: ingesta a RAW, homologación
hacia MASTER, primeras validaciones de calidad y cifrado de la información sensible.

**Valor.** Sin esta base nada puede validarse ni certificarse, y la PII quedaría expuesta desde
la primera carga. Al cerrar el sprint, cada corte llega a MASTER homologado, cifrado y con sus
reglas N1 evaluadas.

### ¿Qué se puede terminar? · Historias seleccionadas

**Capacidad.** Velocidad sugerida de 20 a 24 SP. Se comprometieron 22.

**Historias priorizadas** (del *Sprint 1 Planning* del equipo):

| # | Historia | SP | Complejidad | Rol del backlog | Responsable | Issue |
|---|---|---|---|---|---|---|
| 1 | HU-01 · Ingestar datos sintéticos en la capa RAW | 3 | Baja-media | Data Engineer | Cristhian Pimentel | [#1](https://github.com/GabouLC/dq-center/issues/1) |
| 2 | HU-14 · Homologar el modelo de datos hacia la capa MASTER | 5 | Media | Data Architect | Jesus de la Cruz | [#14](https://github.com/GabouLC/dq-center/issues/14) |
| 3 | HU-05 · Clasificar datos según la taxonomía DAC | 3 | Baja-media | Data Architect | Jesus de la Cruz | [#5](https://github.com/GabouLC/dq-center/issues/5) |
| 4 | HU-02 · Ejecutar validaciones de calidad de Nivel 1 | 3 | Baja-media | Data Engineer | Cristhian Pimentel | [#2](https://github.com/GabouLC/dq-center/issues/2) |
| 5 | HU-06 · Cifrar automáticamente los datos sensibles | 8 | Alta | Data Architect | Jesus de la Cruz | [#6](https://github.com/GabouLC/dq-center/issues/6) |

**Por qué este orden.**

- HU-01 va primero: sin datos en RAW no hay nada que homologar, validar ni cifrar.
- HU-14 deja un modelo estándar en MASTER, que es donde corren las reglas y el cifrado.
- HU-05 decide qué campos son PII antes de cifrarlos: HU-06 depende de esa clasificación.
- HU-02 prueba el motor de reglas sobre MASTER con las validaciones más simples (N1).
- HU-06 es la de mayor riesgo (8 SP): entra en este sprint para que ningún dato sensible
  llegue a MASTER en claro desde el primer corte.

**Fuera del sprint.** Reglas N2 y N3, certificación, Gate y publicación (Sprint 2), y el portal
(Sprint 3).

### ¿Cómo se hará? · Plan de trabajo

Cada historia se dividió en tareas técnicas: son el Sprint Backlog de la sección 2. El trabajo
sigue el flujo de los datos: primero el generador y la ingesta, después la homologación y la
clasificación, al final el motor y el cifrado. Cada tarea cierra con su prueba automatizada.

## 2. Sprint Backlog

Las tareas de cada historia, con su responsable. Al cierre del sprint el tablero quedó así:

| Por hacer | En curso | Hechas |
|---|---|---|
| 0 | 0 | 20 tareas de 5 historias |

**HU-01 · Ingesta a RAW** · Cristhian Pimentel
- [x] Generador de datos sintéticos: 5 tablas y 2 referencias, 6 cortes mensuales y errores sembrados con su manifiesto (`src/dqc/datagen/generador.py`)
- [x] Zona de aterrizaje: un CSV por fuente y corte, con hora de llegada (`src/dqc/datagen/exportar.py`)
- [x] Validación de la estructura del CSV y rechazo con motivo (`src/dqc/pipeline/ingesta.py`)
- [x] Carga a RAW como texto, sin transformar, y registro de cada carga (`dq_raw.registro_cargas`)
- [x] Pruebas: `tests/test_ingesta.py`, `tests/test_flujo.py`

**HU-14 · Homologación a MASTER** · Jesus de la Cruz
- [x] Mapa de cada fuente al modelo estándar: nombres, tipos y formatos de fecha (`config/homologacion.yaml`)
- [x] SQL de homologación por fuente y corte (`src/dqc/pipeline/homologacion.py`)
- [x] Registros no homologables a `incidencias_homologacion`, fuera de MASTER
- [x] Funciones equivalentes en BigQuery y DuckDB, como `parsear_fecha` (`src/dqc/pipeline/funciones.py`)

**HU-05 · Clasificación DAC** · Jesus de la Cruz
- [x] Contrato de datos por tabla con la categoría DAC de cada campo (`config/contratos.yaml`)
- [x] Validación del contrato al cargarlo: toda columna tiene categoría válida (`src/dqc/pipeline/configuracion.py`)
- [x] Contratos en Firestore (`src/dqc/gcp/firestore.py`)

**HU-02 · Calidad N1** · Cristhian Pimentel
- [x] Catálogo de 36 reglas, 48 al expandir las transversales (`config/reglas_iniciales.yaml`)
- [x] Motor: SQL por tipo de regla en dialecto BigQuery, traducido a DuckDB para las pruebas (`src/dqc/motor/sql.py`, `motor.py`)
- [x] Estado de cada regla según su umbral, con muestra de registros fallidos (`src/dqc/motor/puntuacion.py`)
- [x] Prueba de aceptación contra el manifiesto de errores sembrados (`src/dqc/pipeline/verificacion.py`)

**HU-06 · Cifrado** · Jesus de la Cruz
- [x] Llaves AEAD por campo en `dq_seguridad.llaves` (KMS simulado)
- [x] Cifrado determinístico (DNI) y aleatorio (nombres, correo, celular) al pasar a MASTER, con el campo como dato asociado
- [x] Equivalente local con `cryptography` (AES-SIV y AES-GCM) para correr sin GCP
- [x] El motor descifra en memoria solo los campos que usa cada regla (ADR 0007)

**Transversal:** CI con GitHub Actions (`e8a7b4f`), carga a BigQuery en el sandbox (`9ccf16d`) y
configuración en Firestore (`9098ad4`).

## 3. Seguimiento · Daily Scrum

**Impedimentos registrados**

| Impedimento | Efecto | Resolución | Estado |
|---|---|---|---|
| La cuenta de facturación de GCP no se pudo crear (error `OR_BACR2_59`) | Sin Cloud Run, Scheduler ni particiones | Todo corre en el sandbox de BigQuery (ADR 0008) | Abierto |
| `sqlglot` no traducía `SAFE.PARSE_DATE` de BigQuery a DuckDB | La homologación de fechas fallaba en local | Función `parsear_fecha` por plataforma | Resuelto |
| DuckDB 1.5 eliminó `duckdb.typing` | Las funciones de cifrado no se registraban | Migración a `duckdb.sqltypes` | Resuelto |
| `COUNTIF` sobre un conjunto vacío devuelve `NULL` en DuckDB | Cumplimiento indefinido en reglas sin filas | Se trata como 0 | Resuelto |

**Burndown.** El incremento se integró en un solo commit (`369a0d7`), así que el repositorio no
muestra el avance día a día. La línea real se registra con la plantilla de burndown de
[plantillas.md](plantillas.md) a partir del tablero del equipo. Resultado: 22 de 22 SP, sin arrastre.

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

**Incremento.** Seis cortes mensuales (abril a septiembre de 2026) pasan de CSV a RAW, de RAW a
MASTER homologado y cifrado, y se evalúan con las reglas N1. Para reproducirlo:

```bash
python -m dqc.datagen                       # datos sintéticos y manifiesto
python -m dqc.pipeline --db data/dq.duckdb  # flujo completo y verificación
```

**Resultado:** 5 de 5 historias aceptadas. La verificación contra el manifiesto da 0 errores
sin detectar y 0 detectados de más en ingesta, homologación y reglas, tanto en DuckDB
([pipeline-local.txt](../evidencias/pipeline-local.txt)) como en BigQuery
([bigquery.txt](../evidencias/bigquery.txt)).

### HU-01 · Ingestar datos sintéticos en la capa RAW

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Un CSV válido se carga en RAW | `test_archivo_valido_se_carga_tal_cual` ([test_ingesta.py](../../tests/test_ingesta.py)) | 32 cargas exitosas en BigQuery ([bigquery.txt](../evidencias/bigquery.txt)) |
| Los registros se conservan sin modificaciones | `test_raw_conserva_los_valores_tal_cual_vienen` ([test_flujo.py](../../tests/test_flujo.py)) | RAW guarda todo como texto, sin transformar |
| La carga exitosa queda registrada | `test_lo_rechazado_no_llega_a_raw_y_queda_registrado` ([test_flujo.py](../../tests/test_flujo.py)) | [Fuentes › Siniestro](../evidencias/portal/hu01-fuentes-siniestro-rechazo.png): estado *Exitosa* por archivo |
| Un error de estructura o formato rechaza la carga y registra el error | `test_estructura_invalida_se_rechaza`, `test_archivo_mal_formado_se_rechaza_con_su_motivo` | [Fuentes › Siniestro](../evidencias/portal/hu01-fuentes-siniestro-rechazo.png): julio *Rechazada*, «faltan columnas: ESTADO_SINIESTRO» |

### HU-14 · Homologar el modelo de datos hacia la capa MASTER

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Los datos de RAW se transforman al modelo estándar de MASTER | `test_la_homologacion_cubre_el_contrato_con_los_mismos_tipos` ([test_flujo.py](../../tests/test_flujo.py)) | [Fuentes › Póliza](../evidencias/portal/hu14-fuentes-poliza-estructura.png): estructura de MASTER por corte |
| Nombres distintos entre fuentes se unifican | `test_master_usa_los_nombres_estandar` | [Linaje](../evidencias/portal/hu11-linaje.png): `NUM_DOC` → `nro_documento` |
| El dato homologado queda disponible para N1 y N2 | `test_cada_corte_evalua_las_48_reglas_con_su_nivel` ([test_motor.py](../../tests/test_motor.py)) | Las 48 reglas corren sobre MASTER en los 6 cortes |
| Un registro no homologable se registra como incidencia y queda fuera de MASTER | `test_los_registros_no_homologables_quedan_fuera_de_master` | Incidencias por corte ([bigquery.txt](../evidencias/bigquery.txt)): importes y fechas de aviso no convertibles |

### HU-05 · Clasificar datos según la taxonomía DAC

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Los campos de Póliza y Persona reciben su categoría | `test_los_contratos_cubren_las_tablas_con_sus_tipos_reales` ([test_firestore.py](../../tests/test_firestore.py)) | [Contrato de datos](../evidencias/portal/hu05-contrato-dac.png) |
| La información pública se clasifica como Público | `test_dni_nombres_y_correo_son_sensibles_cifrados` ([test_flujo.py](../../tests/test_flujo.py)): `tipo_documento` es Público | [Contrato de datos](../evidencias/portal/hu05-contrato-dac.png): chips *Público* |
| La información restringida se clasifica como Sensible | `test_dni_nombres_y_correo_son_sensibles_cifrados`: `monto_reclamado` es Sensible | [Contrato de datos](../evidencias/portal/hu05-contrato-dac.png): `fecha_nacimiento`, `sexo` y `ubigeo` como *Sensible* |
| DNI, nombre y correo se clasifican como Sensible Cifrado | `test_dni_nombres_y_correo_son_sensibles_cifrados`, `test_contrato_con_dac_y_columna_fuera_de_contrato` ([test_api.py](../../tests/test_api.py)) | [Contrato de datos](../evidencias/portal/hu05-contrato-dac.png): 6 campos de Persona como *Sensible cifrado* |

### HU-02 · Ejecutar validaciones de calidad de Nivel 1

El backlog habla de PASS y FAIL. El motor usa tres estados: **OK** es PASS; **ALERTA** (hasta
2 puntos bajo el umbral) y **FALLA** son FAIL con observación.

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Las pruebas N1 se ejecutan sobre los registros | `test_cada_corte_evalua_las_48_reglas_con_su_nivel` ([test_motor.py](../../tests/test_motor.py)) | 19 reglas N1 por corte ([bigquery.txt](../evidencias/bigquery.txt)) |
| Un registro que cumple se marca PASS | `test_estado_segun_umbral` ([test_reglas.py](../../tests/test_reglas.py)) | [Validaciones de julio](../evidencias/portal/hu02-hu03-validaciones-julio.png) |
| Un registro que incumple se marca FAIL con observación | `test_muestras_traen_la_fila_sin_exponer_pii`, `test_cada_etapa_detecta_exactamente_lo_sembrado` | [Detalle de una regla](../evidencias/portal/hu13-validaciones-gobierno.png): registros fallidos con su fila |
| Al terminar, queda el estado de cada regla | `test_hay_reglas_en_ok_alerta_y_falla` | Tabla de reglas por corte en [pipeline-local.txt](../evidencias/pipeline-local.txt) |

### HU-06 · Cifrar automáticamente los datos sensibles

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Un campo PII se cifra en el Privacy Gate | `test_ningun_campo_pii_queda_en_texto_plano_en_master` ([test_flujo.py](../../tests/test_flujo.py)) | En BigQuery los campos PII de MASTER son `BYTES` ([bigquery.txt](../evidencias/bigquery.txt)) |
| Un campo que se compara usa cifrado determinístico | `test_deterministico_iguala_documentos_y_aleatorio_no`, `test_el_dni_en_master_no_coincide_con_raw_pero_se_descifra_igual` | Mismo DNI, mismo cifrado: permite unicidad sin descifrar |
| Un campo que no se compara usa cifrado no determinístico | `test_deterministico_iguala_documentos_y_aleatorio_no` | [Linaje de un campo cifrado](../evidencias/portal/hu06-hu11-linaje-campo-cifrado.png) |
| Ningún PII queda en texto plano al almacenarse | `test_ningun_campo_pii_queda_en_texto_plano_en_master`, `test_business_no_expone_pii_en_claro` | Muestras cifradas en [bigquery.txt](../evidencias/bigquery.txt) |

### Definition of Done por historia

| Criterio de la Definition of Done | HU-01 | HU-14 | HU-05 | HU-02 | HU-06 |
|---|---|---|---|---|---|
| Código en `main` y CI en verde | Sí | Sí | Sí | Sí | Sí |
| Cada criterio de aceptación con prueba automatizada | 4 de 4 | 4 de 4 | 4 de 4 | 4 de 4 | 4 de 4 |
| 0 diferencias contra el manifiesto | Ingesta | Homologación | No aplica | Reglas | No aplica |
| Desvíos del documento de arquitectura en un ADR | [0009](../adr/0009-datos-sinteticos.md) | [0006](../adr/0006-capas-y-privacy-gate.md) | No hubo | [0004](../adr/0004-evaluacion-sql.md), [0010](../adr/0010-pruebas.md) | [0006](../adr/0006-capas-y-privacy-gate.md), [0007](../adr/0007-pii-solo-en-memoria.md) |
| Evidencia en `docs/evidencias` | Sí | Sí | Sí | Sí | Sí |
| Issue cerrado y enlazado a su evidencia | [#1](https://github.com/GabouLC/dq-center/issues/1) | [#14](https://github.com/GabouLC/dq-center/issues/14) | [#5](https://github.com/GabouLC/dq-center/issues/5) | [#2](https://github.com/GabouLC/dq-center/issues/2) | [#6](https://github.com/GabouLC/dq-center/issues/6) |

Las cinco historias cumplen la Definition of Done: forman el incremento del Sprint 1.

### Reunión de revisión

- **Fecha y asistentes:** completar.
- **Historias demostradas y aceptadas:** las cinco, con la demostración de la sección 4.
- **Comentarios de los interesados:** completar con la plantilla de [plantillas.md](plantillas.md).

**Product Backlog tras la revisión.** Sin historias nuevas. Siguen, en orden: HU-03, HU-04,
HU-07 y HU-08 (Sprint 2). Se agrega como pendiente técnico resolver la facturación de GCP.

## 5. Sprint Retrospective (borrador con los hechos del sprint)

| Funcionó | Por mejorar |
|---|---|
| Sembrar errores conocidos y exigir que el pipeline encuentre exactamente esos dio un criterio de aceptación objetivo. | La facturación de GCP sigue bloqueada: sin ella no hay Cloud Run. Hay que escalarlo con soporte de Google Cloud Billing. |
| El mismo SQL corre en DuckDB y en BigQuery: se prueba en segundos y sin nube. | Todo el incremento entró en un solo commit, así que el avance diario no se ve en el repositorio. |
| Cada desvío del Documento de Arquitectura quedó en un ADR. | Las diferencias de dialecto entre BigQuery y DuckDB aparecieron tarde; conviene probarlas al empezar cada historia. |

**Acciones propuestas:** un pull request por historia vinculado a su issue; resolver la
facturación antes del Sprint 3; probar cada función nueva en los dos motores desde el inicio.
Completar con la opinión del equipo usando [plantillas.md](plantillas.md).
