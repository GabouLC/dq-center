# Sprint 3 · Portal Smart-DQ

**Estado:** terminado el 11 de noviembre de 2026, nueve días después del cierre previsto ·
**Fechas:** sábado 24 de octubre (Sprint Planning) al lunes 2 de noviembre de 2026 (previsto); cerrado en
Jira el 8 de noviembre ·
**Compromiso:** 31 SP, 6 historias y una tarea técnica · **Terminado:** 31 SP, 6 historias y la tarea
técnica ·
**Milestone:** [Sprint 3](https://github.com/GabouLC/dq-center/milestone/4) ·
**Jira:** SDGDCYP Sprint 3 (24 de octubre al 8 de noviembre); el equipo volvió a registrar cinco de las
historias en el Sprint 4 del tablero (30 de octubre al 12 de noviembre), ver
[Seguimiento](#3-seguimiento--daily-scrum)

El sprint estaba previsto del 20 de octubre al 2 de noviembre. La Sprint Planning se hizo el 24, con
cuatro días de retraso, porque antes había que cerrar el Sprint 2 (su corrida en BigQuery terminó ese
día). El 2 de noviembre pasó sin revisión: el repositorio no tiene commits entre el 25 de octubre y el
10 de noviembre, y lo que quedaba del Sprint Backlog se cerró el 11 de noviembre. La revisión y la
retrospectiva de este documento se **reconstruyeron ese día** a partir de la verificación de cada
criterio contra el repositorio; así lo dice cada una.

**Prototipo adelantado.** El repositorio ya tenía un prototipo funcional del portal (commits
[`fe181da`](https://github.com/GabouLC/dq-center/commit/fe181da),
[`075eccc`](https://github.com/GabouLC/dq-center/commit/075eccc),
[`12d0d91`](https://github.com/GabouLC/dq-center/commit/12d0d91),
[`a5f625a`](https://github.com/GabouLC/dq-center/commit/a5f625a) y
[`2e01263`](https://github.com/GabouLC/dq-center/commit/2e01263)), que sirvió para recoger
comentarios antes de planificar. Por eso buena parte del Sprint Backlog ya estaba hecha el 24 de
octubre: lo que quedaba era verificar cada criterio, atender los comentarios de la revisión del Sprint 2
y aceptar.

## 1. Sprint Planning

**Fecha:** sábado 24 de octubre de 2026. La preparó el Product Owner con estas decisiones; el equipo la
iba a confirmar en la primera daily, el lunes 26. **Participantes previstos:** Gabriel León (Product
Owner), Franco Delgado (Scrum Master), Jesus de la Cruz y Cristhian Pimentel.

### ¿Por qué es valioso este sprint? · Objetivo del sprint

**Objetivo del sprint.** Llevar los resultados al negocio: un portal donde cada rol ve la salud y la
certificación de los datos, su linaje y su glosario, con acceso controlado y cada sección en menos de 8
segundos.

**Valor.** Los Sprints 1 y 2 dejaron cada corte con un veredicto por tabla. Sin el portal, ese
veredicto solo se ve con consultas; con él, negocio, gobierno y la Oficina de Datos responden
«¿puedo usar estos datos hoy?» por sí mismos.

### ¿Qué se puede terminar? · Historias seleccionadas

**Decisiones del Product Owner (24 de octubre)**

1. **Responsables.** Josue Borda no participó en ningún evento de los Sprints 1 y 2 ni confirmó su
   disponibilidad (acción de las dos retrospectivas). Sus cuatro historias se reasignaban por
   afinidad con lo que cada integrante ya había construido: HU-11 a Jesus de la Cruz, HU-12 y HU-15 a
   Franco Delgado, HU-09 a Cristhian Pimentel. **Ese plan no es lo que quedó en Jira:** al registrar de
   nuevo las historias en el Sprint 4 (7 de noviembre), el equipo las repartió distinto. La tabla de
   abajo sigue a Jira, que es el registro del equipo.
2. **Capacidad.** Las seis historias suman 31 SP, por encima de la velocidad de 22 y 23. Entraban
   todas porque el prototipo ya cubría la mayor parte del trabajo. Si el sprint se atrasaba, HU-15 era
   la primera en salir: va última y no bloquea a ninguna otra.
3. **Auditoría de reglas.** Entran SIN-UNI-01, PAG-VAL-01 y PER-VAL-06 como tarea técnica: dan
   100 % en los 92 días, así que no cambian ningún sello aceptado. Las demás propuestas de la
   [auditoría](../auditoria-reglas.md), incluida la banda de ALERTA de las reglas CRÍTICAS, siguen en
   el Product Backlog.

**Historias comprometidas.** Los puntos son los del Product Backlog del equipo en Jira. La columna
«Responsable» es la que tiene Jira (la de la copia del Sprint 4 cuando existe).

| # | Historia | SP | Complejidad | Rol del backlog | Responsable en Jira | Issue | Jira | Estado |
|---|---|---|---|---|---|---|---|---|
| 1 | HU-13 · Controlar el acceso a datos sensibles mediante roles | 5 | Media | Data Architect | Sin responsable (plan: Jesus de la Cruz) | [#13](https://github.com/GabouLC/dq-center/issues/13) | SDGDCYP-11 | Terminada |
| 2 | HU-09 · Visualizar el estado de calidad de los datos | 5 | Media | Oficina de Datos | Gabriel León | [#9](https://github.com/GabouLC/dq-center/issues/9) | SDGDCYP-16 y 90 | Terminada |
| 3 | HU-12 · Consultar la certificación integral del dato | 5 | Media | Data Owner | Jesus de la Cruz | [#12](https://github.com/GabouLC/dq-center/issues/12) | SDGDCYP-19 y 92 | Terminada |
| 4 | HU-11 · Consultar el linaje de los datos | 8 | Alta | Oficina de Datos | Gabriel León | [#11](https://github.com/GabouLC/dq-center/issues/11) | SDGDCYP-18 y 91 | Terminada |
| 5 | HU-10 · Consultar el glosario de negocio | 3 | Baja-media | Negocio | Franco Delgado | [#10](https://github.com/GabouLC/dq-center/issues/10) | SDGDCYP-17 y 89 | Terminada en el repositorio; en Jira, en revisión de Franco |
| 6 | HU-15 · Garantizar el tiempo de carga del portal | 5 | Media | Negocio | Jesus de la Cruz | [#15](https://github.com/GabouLC/dq-center/issues/15) | SDGDCYP-20 y 93 | Terminada |

Cristhian Pimentel y Josue Borda no tienen historias de este sprint en Jira. Todos los commits del
sprint en el repositorio son de Gabriel León.

**Por qué este orden.**

- HU-13 va primero porque toda pantalla del portal necesita saber quién entra y qué puede ver.
- HU-09 es el mayor valor para el negocio: responde «¿puedo confiar en los datos de este día?».
- HU-12 reutiliza la certificación del Sprint 2 y la hace visible por tabla.
- HU-11 explica de dónde sale cada campo y por qué una tabla no se publicó.
- HU-10 es la más simple y no bloquea a ninguna otra.
- HU-15 cierra el sprint: se mide sobre todas las pantallas ya construidas.

**Fuera del sprint.** El despliegue en Cloud Run, que depende de la facturación de GCP, y el resto de
las propuestas de la auditoría de reglas.

### ¿Cómo se hará? · Plan de trabajo

Cada responsable verifica su historia contra los criterios del Product Backlog: primero con las pruebas
automatizadas, después en el portal con teclado, lector de pantalla y tema oscuro. Lo que falte se
corrige con una rama y un pull request, revisado por otro integrante (acción de la retrospectiva del
Sprint 2). La evidencia se regenera con `scripts/capturas_portal.py`.

## 2. Sprint Backlog

Las tareas de cada historia. El 24 de octubre, 23 de 33 estaban hechas en el prototipo; las otras 10 se
cerraron el 11 de noviembre.

| Historias | Tareas por hacer | Tareas hechas |
|---|---|---|
| 6 terminadas | 0 | 33 de 33 |

**Base del portal**
- [x] API FastAPI con prefijo `/api/v1`, sondas `/health` y errores con el formato del documento de arquitectura (`src/dqc/api/app.py`)
- [x] Web Vue 3 + TypeScript + Pinia en MVVM, con la línea de tiempo compartida por los módulos (`web/`)
- [x] La API lee solo las vistas de contrato de BUSINESS (`src/dqc/api/datos.py`)

**HU-13 · Acceso por rol**
- [x] Roles admin, gobierno y lector, con permisos por módulo (`PERMISOS` y `MODULOS`)
- [x] Campos SENSIBLE ocultos para el lector, también en las incidencias; SENSIBLE_CIFRADO siempre ocultos
- [x] Auditoría de accesos denegados y de campos ocultos
- [x] Inicio de sesión con correo y contraseña, bloqueo por intentos y contraseña temporal (`src/dqc/api/autenticacion.py`, ADR 0011)
- [x] Administración de usuarios: alta, cambio de rol, restablecer contraseña y quitar acceso
- [x] Probar el inicio de sesión, el bloqueo y el cambio de contraseña contra Firestore (modo GCP)
- [x] Recorrer Entrar, Cambiar contraseña y Usuarios solo con teclado y con lector de pantalla

**HU-09 · Dashboard**
- [x] Simulación en vivo: los archivos del día llegan uno por uno, el corte se publica al completarse y el portal se actualiza solo (`src/dqc/api/vivo.py`)
- [x] Indicador «En vivo», panel de actividad y avisos; línea de tiempo y mapa de certificación por día
- [x] Resumen: % de reglas que cumplen, puntaje de calidad, tendencia diaria y dimensiones por tabla
- [x] Validaciones: reglas del día con las fallas primero, filtros y detalle con los registros fallidos
- [x] Comparación entre dos días, con lo que empeoró primero
- [x] Ejecuciones: volver a evaluar un corte desde el portal y ver su resultado
- [x] Recorrer Resumen y Validaciones con teclado y lector de pantalla: mapa de días y diálogo de detalle
- [x] Revisar el tema oscuro de todas las pantallas con capturas

**HU-12 · Certificación integral**
- [x] Sello por tabla con calidad por nivel, privacidad (campos cifrados y hallazgos) y trazabilidad (ejecución, versiones, objeto en BUSINESS)
- [x] Certificación día por día de los 92 cortes y enlace al linaje
- [x] Mostrar, cuando una tabla no se publica, qué día está viendo negocio (su último corte certificado) (comentario de la revisión del Sprint 2)

**HU-11 · Linaje**
- [x] Recorrido RAW → MASTER → BUSINESS por tabla, con el archivo de origen y los objetos publicados
- [x] Cada campo con su nombre en la fuente, su transformación y si se cifra
- [x] En el paso a BUSINESS, el motivo de cada día que no se publicó (comentario de la revisión del Sprint 2)

**HU-10 · Glosario**
- [x] 40 términos con definición, dominio, sinónimos y campos donde aparecen (`config/glosario.yaml`)
- [x] Búsqueda sin tildes ni mayúsculas, filtro por dominio y edición solo para gobierno y admin
- [x] Términos «Carné de extranjería» y «Estado de la cuota», que usan las reglas nuevas PER-VAL-06 y PAG-VAL-01

**HU-15 · Rendimiento**
- [x] Las vistas de BUSINESS se leen en paralelo y quedan 10 minutos en memoria; se precargan al arrancar
- [x] Cabecera `Server-Timing` en cada respuesta y auditoría de las que pasan de 8 s
- [x] Prueba automatizada por sección del portal
- [x] Medir cada sección con la API sobre BigQuery (sandbox, 92 cortes) y dejar el resultado en la evidencia

**Reglas de la auditoría DAMA**
- [x] SIN-UNI-01 (unicidad de `id_siniestro`), PAG-VAL-01 (dominio de `estado` de la cuota) y PER-VAL-06 (dominio de `tipo_documento`) en el catálogo, con su prueba
- [x] Actualizar el conteo de 48 a 51 evaluaciones por corte en la documentación y regenerar la evidencia

Las tareas se dejan con el texto con que se crearon en Jira, para que la sincronización no las duplique.
Lo que cerró el 11 de noviembre, con su evidencia:

- Firestore: 14 de 14 comprobaciones ([acceso-firestore.txt](../evidencias/acceso-firestore.txt)).
- Teclado, lector de pantalla (árbol de accesibilidad de Chromium) y tema oscuro: `scripts/verificar_portal.py`
  ([accesibilidad-y-e2e.txt](../evidencias/accesibilidad-y-e2e.txt) y [`portal/oscuro/`](../evidencias/portal/oscuro)).
- Glosario: 42 términos al sumar «Carné de extranjería» y «Estado de la cuota» a los 40 del prototipo.
- Prueba por sección: ahora cubre las 11 (antes cubría 7), con 12 rutas.
- Medición de HU-15: [rendimiento.txt](../evidencias/rendimiento.txt) (API local) y
  [rendimiento-bigquery.txt](../evidencias/rendimiento-bigquery.txt) (BigQuery).
- Reglas: catálogo de 39 reglas y 51 evaluaciones por corte; los 92 cortes, también en BigQuery
  ([pipeline-local.txt](../evidencias/pipeline-local.txt) y [bigquery.txt](../evidencias/bigquery.txt)).

## 3. Seguimiento · Daily Scrum

**No hay actas de daily de este sprint.** El repositorio no tiene commits entre el 25 de octubre y el 10
de noviembre, y en Jira la actividad del equipo está el 29 de octubre y del 7 al 11 de noviembre. No se
reconstruyen dailies que no se pueden respaldar con esos registros; se deja constancia en
[dailies.md](dailies.md). Las dailies estaban previstas para las 8:00 p. m. de cada día hábil desde el
lunes 26 de octubre.

**Qué muestra Jira (tablero del equipo)**

| Fecha | Qué pasó |
|---|---|
| 24 de octubre | Se crea el Sprint 3 con las seis historias y sus tareas |
| 29 de octubre | Las seis historias originales (SDGDCYP-11 y 16 a 20) y las tareas de reglas y conteo (SDGDCYP-87 y 88) pasan a Finalizada |
| 30 de octubre | Empieza el Sprint 4 del tablero (termina el 12 de noviembre) |
| 7 de noviembre | Se registran en el Sprint 4 cinco copias de las historias: HU-10 (SDGDCYP-89), HU-09 (90), HU-11 (91), HU-12 (92) y HU-15 (93), con puntos, descripción y responsable; se finalizan las tareas de glosario (SDGDCYP-79) y de medición sobre BigQuery (SDGDCYP-83) |
| 8 de noviembre | Se cierra el Sprint 3 |
| 9 al 11 de noviembre | SDGDCYP-93, 91, 90 y 92 pasan a Done; SDGDCYP-89 (HU-10) queda en In Review, a cargo de Franco |

Jira dio las historias por finalizadas el 29 de octubre, antes de que el repositorio tuviera varias de
sus tareas: las tres reglas y el conteo de 51 (SDGDCYP-87 y 88) y la medición de rendimiento
(SDGDCYP-83), junto con la prueba contra Firestore y las pruebas e2e, entraron el 11 de noviembre. Para
el release cuenta lo que el repositorio puede demostrar.

**Impedimentos y riesgos**

| Riesgo o impedimento | Efecto | Respuesta | Estado |
|---|---|---|---|
| Sin facturación en GCP | No hay Cloud Run para publicar el portal | El portal se demuestra en local, contra DuckDB o contra BigQuery | Abierto |
| Josue Borda no participa | Cuatro historias sin responsable | Reasignadas en la Sprint Planning; Jira las muestra con otros responsables; Josue sigue sin historias | Abierto |
| 31 SP sobre una velocidad de 22 y 23, en seis días hábiles | Sprint cargado | El prototipo cubría 23 de 33 tareas; se confirmó el riesgo: el sprint terminó nueve días tarde, sin recortar HU-15 | Cerrado |
| La primera carga del Resumen sobre BigQuery puede acercarse a los 8 s de HU-15 | Riesgo de incumplir el requisito | Lectura en paralelo y precarga al arrancar; medido con los 92 cortes ([rendimiento-bigquery.txt](../evidencias/rendimiento-bigquery.txt)) | Cerrado |
| Las tablas del sandbox vencen a los 60 días (hacia mediados de diciembre) | Habría que volver a cargar los 92 cortes, unas 9 horas | Alcanzó para este cierre; hay que recargar si se vuelve a demostrar después | Abierto |
| Jira y repositorio fuera de sincronía | Las historias figuraban terminadas sin tener todo el trabajo | El trabajo faltante se cerró el 11 de noviembre y Jira recibió la evidencia como comentarios, sin cambiar estados ni responsables | Cerrado |

**Burndown.** 31 SP comprometidos. Línea ideal en seis días hábiles, y lo real según dos fuentes: lo
que marcó Jira y lo que el repositorio podía demostrar contra los criterios.

| Día | Fecha | SP ideal | SP pendientes según Jira | SP pendientes según el repositorio |
|---|---|---|---|---|
| 0 | sábado 24 de octubre | 31 | 31 | 31 |
| 1 | lunes 26 | 25,8 | 31 | 31 |
| 2 | martes 27 | 20,7 | 31 | 31 |
| 3 | miércoles 28 | 15,5 | 31 | 31 |
| 4 | jueves 29 | 10,3 | 0 | 31 |
| 5 | viernes 30 | 5,2 | 0 | 31 |
| 6 | lunes 2 de noviembre | 0 | 0 | 31 |
| | domingo 8 de noviembre (cierre en Jira) | | 0 | 31 |
| | miércoles 11 de noviembre | | 3 (HU-10 en revisión) | 0 |

El repositorio no tiene commits entre el 25 de octubre y el 10 de noviembre, así que esa columna no
baja hasta el 11 de noviembre, cuando se verificaron y cerraron todos los criterios. La línea de Jira
cae de golpe el 29 de octubre.

## 4. Sprint Review e Incremento

**Incremento.** El Portal Smart-DQ: una API FastAPI (`src/dqc/api/`) y una web Vue 3 (`web/`) con 11
secciones que leen solo las vistas de contrato de BUSINESS. Cada rol (administrador, gobierno y lector)
ve sus módulos y, según su permiso, los campos sensibles; el acceso, el bloqueo por intentos y las
contraseñas temporales se probaron contra Firestore real
([acceso-firestore.txt](../evidencias/acceso-firestore.txt)). En local, el portal se actualiza solo con
la simulación en vivo. El catálogo evalúa 51 reglas por corte, con las tres de la auditoría. El
rendimiento de las 11 secciones se mide con la API local y sobre BigQuery
([rendimiento.txt](../evidencias/rendimiento.txt),
[rendimiento-bigquery.txt](../evidencias/rendimiento-bigquery.txt)); el teclado, el lector de pantalla y
el contraste, en [accesibilidad-y-e2e.txt](../evidencias/accesibilidad-y-e2e.txt). La arquitectura y sus
diagramas están en [arquitectura.md](../arquitectura.md).

```bash
python -m dqc.pipeline --db data/dq.duckdb --hasta 2026-09-24   # del 25 al 30 llegan en vivo
python -m dqc.api                                               # API en http://127.0.0.1:8000
cd web && npm run dev                                           # portal en http://localhost:5173
python scripts/medir_rendimiento.py                             # HU-15 con la API local (--modo gcp: BigQuery)
python scripts/verificar_acceso_firestore.py                    # HU-13 contra Firestore real (con DQC_PROYECTO)
```

Cuentas de demostración: `admin@demo.local`, `gobierno@demo.local` y `lector@demo.local`, con la
contraseña `SmartDQ-2026`. Las capturas de las secciones en tema oscuro están en
`docs/evidencias/portal/oscuro/`, una por sección. Los criterios de aceptación son los de cada issue;
las filas que no son de un issue dicen de dónde salen (comentario de la revisión del Sprint 2, del
prototipo o tarea del sprint).

**Comentarios que recibió el prototipo antes de planificar**

| Comentario | Cambio en el prototipo | Commit |
|---|---|---|
| «El diseño es muy apagado; hazlo más interactivo y atractivo» | Navegación con íconos, tema claro y oscuro, gráfico con tooltip y vista de tabla, y diseño móvil | `075eccc` |
| «Tiene que ser un inicio de sesión, no elegir roles» | Inicio de sesión con correo y contraseña, bloqueo por intentos, contraseña temporal y cambio obligatorio (ADR 0011) | `12d0d91` |
| «Datos de julio a septiembre, con valores y variaciones realistas, y que se sienta vivo» | Cortes diarios con ruido, tendencias e incidentes; simulación en vivo con actividad y avisos; % de reglas en PASS como indicador principal | `a5f625a` |
| Revisión de accesibilidad y lenguaje claro (24 de octubre) | Teclado, foco y contraste AA; vocabulario único; gráficos legibles con daltonismo | `2e01263` |
| «Que sea más atractivo y dinámico, y que se entienda rápido para qué sirve cada sección» (24 de octubre) | Cada sección dice qué pregunta responde y cómo se lee; lectura rápida del día en una frase; menú agrupado por objetivo; recorrido de bienvenida con el viaje de los datos; movimiento con propósito y estados de carga y vacíos (PR #19); aspecto de «panel de control vivo»: banda azul con la lectura rápida, el % que cumple y los sellos, tarjetas con acento de estado y tendencia en área (PR #20) | 24 de octubre |

### HU-13 · Controlar el acceso a datos sensibles mediante roles

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Un campo Sensible se asocia a un rol autorizado | `test_dni_nombres_y_correo_son_sensibles_cifrados` ([test_flujo.py](../../tests/test_flujo.py)); `test_contrato_con_dac_y_columna_fuera_de_contrato`, `test_campos_sensibles_ocultos_para_el_lector_y_visibles_para_gobierno` ([test_api.py](../../tests/test_api.py)) | Clasificación DAC de cada campo ([Contrato de Persona](../evidencias/portal/hu05-contrato-dac.png)) y qué rol lo ve ([Usuarios y roles](../evidencias/portal/hu13-usuarios.png)). Son roles de la aplicación, no grupos de IAM de GCP ([ADR 0016](../adr/0016-roles-de-la-aplicacion.md)): gobierno y administrador ven los campos SENSIBLE; los SENSIBLE_CIFRADO no los ve nadie en claro |
| Con el rol autorizado, el campo Sensible se muestra | `test_campos_sensibles_ocultos_para_el_lector_y_visibles_para_gobierno`, `test_incidencias_ocultan_los_valores_sensibles_al_lector` | [Validaciones con gobierno](../evidencias/portal/hu13-validaciones-gobierno.png): el mismo registro fallido que ve el lector, sin el aviso de campos ocultos |
| Sin el rol autorizado, el acceso se restringe | `test_campos_sensibles_ocultos_para_el_lector_y_visibles_para_gobierno`, `test_incidencias_ocultan_los_valores_sensibles_al_lector`, `test_cada_rol_ve_solo_sus_modulos`, `test_un_lector_no_puede_administrar`, `test_reglas_y_ejecuciones_solo_se_leen_con_permiso_de_configurar`, `test_cuenta_sin_rol_responde_403_y_queda_auditada`; en el menú del portal, la comprobación de roles de `scripts/verificar_portal.py` (7 secciones para el lector, 11 para el administrador) | [Validaciones con lector](../evidencias/portal/hu13-validaciones-lector.png): campos ocultos con el aviso de que el acceso quedó registrado; [acceso denegado](../evidencias/portal/hu13-auditoria-acceso-denegado.png) |
| Cada acceso denegado queda registrado para la auditoría | `test_cuenta_sin_rol_responde_403_y_queda_auditada`, `test_un_lector_no_puede_administrar`, `test_la_contrasena_temporal_sin_cambiar_queda_auditada`, `test_campos_sensibles_ocultos_para_el_lector_y_visibles_para_gobierno` (evento `ACCESO_RESTRINGIDO`) | [Auditoría](../evidencias/portal/hu13-hu15-auditoria.png) y [en tema oscuro](../evidencias/portal/oscuro/auditoria.png); inicios, intentos fallidos, bloqueos y cambios también quedan en la auditoría de Firestore ([acceso-firestore.txt](../evidencias/acceso-firestore.txt)) |
| Tarea del sprint: inicio de sesión, bloqueo por intentos y contraseña temporal ([ADR 0011](../adr/0011-inicio-de-sesion.md)) | `test_cinco_intentos_fallidos_bloquean_la_cuenta_15_minutos`, `test_intentos_en_paralelo_no_se_saltan_el_bloqueo`, `test_la_contrasena_temporal_desbloquea_y_obliga_a_cambiarla`, `test_cambiar_la_contrasena_cierra_las_sesiones_anteriores`, `test_quitar_el_acceso_cierra_la_sesion` ([test_autenticacion.py](../../tests/test_autenticacion.py)); `test_alta_con_contrasena_temporal_que_obliga_a_cambiarla`, `test_restablecer_la_contrasena_cierra_las_sesiones_abiertas`, `test_el_error_de_inicio_no_dice_si_la_cuenta_existe` | 14 de 14 comprobaciones contra Firestore real, con dos instancias de la API ([acceso-firestore.txt](../evidencias/acceso-firestore.txt)); [login](../evidencias/portal/hu13-login.png), [alta con clave temporal](../evidencias/portal/hu13-alta-clave-temporal.png), [cambio obligatorio](../evidencias/portal/hu13-cambio-clave-obligatorio.png) |
| Tarea del sprint: Entrar, Cambiar contraseña y Usuarios con teclado y lector de pantalla | Sin prueba en `tests/`: lo comprueba `scripts/verificar_portal.py` con Playwright, en `/entrar`, `/clave` y Usuarios: teclado y árbol de accesibilidad (lo que lee el lector de pantalla) | [accesibilidad-y-e2e.txt](../evidencias/accesibilidad-y-e2e.txt); [Usuarios](../evidencias/portal/oscuro/usuarios.png) en tema oscuro |

**Decisión de diseño:** [ADR 0011](../adr/0011-inicio-de-sesion.md) (inicio de sesión propio) y
[ADR 0016](../adr/0016-roles-de-la-aplicacion.md) (roles de la aplicación, no IAM de GCP; ajusta el
criterio a).

### HU-09 · Visualizar el estado de calidad de los datos

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Con ejecuciones, el dashboard muestra el estado de las reglas ejecutadas | `test_resumen_muestra_tendencia_pass_y_certificacion`, `test_validaciones_de_un_corte_empiezan_por_las_fallas` ([test_api.py](../../tests/test_api.py)) | [Resumen](../evidencias/portal/hu09-resumen.png), [Validaciones del 14 de julio](../evidencias/portal/hu02-hu03-validaciones-14-julio.png); en tema oscuro, [Resumen](../evidencias/portal/oscuro/resumen.png) y [Validaciones](../evidencias/portal/oscuro/validaciones.png) |
| Las reglas aprobadas se identifican como PASS | `test_resumen_muestra_tendencia_pass_y_certificacion` (`pct_pass` del día y por tabla); `test_estado_segun_umbral` ([test_reglas.py](../../tests/test_reglas.py)) | «% de reglas que cumplen (PASS)» en el [Resumen](../evidencias/portal/hu09-resumen.png); el portal rotula «Cumple» a la regla en OK ([ADR 0015](../adr/0015-indicador-pass.md)) |
| Las reglas fallidas se identifican como FAIL | `test_validaciones_de_un_corte_empiezan_por_las_fallas`, `test_comparar_cortes_muestra_primero_lo_que_empeoro`, `test_campos_sensibles_ocultos_para_el_lector_y_visibles_para_gobierno` (registros fallidos de una regla), `test_estado_segun_umbral` | [Validaciones del 14 de julio](../evidencias/portal/hu02-hu03-validaciones-14-julio.png): fallas primero; [detalle con los registros fallidos](../evidencias/portal/hu13-validaciones-lector.png) |
| Al terminar una ejecución, el dashboard refleja el resultado | `test_admin_lanza_una_corrida_y_aparece_en_el_portal` ([test_api.py](../../tests/test_api.py)); `test_el_dia_siguiente_llega_archivo_por_archivo` ([test_vivo.py](../../tests/test_vivo.py)): el corte aparece en `v_calidad_ejecuciones` y se avisa para renovar la caché; `test_reevaluar_un_corte_que_deja_de_certificar_lo_saca_de_business` ([test_certificacion.py](../../tests/test_certificacion.py)) | [Ejecuciones](../evidencias/portal/hu04-ejecuciones.png), [actividad en vivo](../evidencias/portal/hu09-actividad-en-vivo.png), [panel en vivo](../evidencias/portal/hu09-panel-en-vivo.png) |
| Comentario del prototipo: que se sienta vivo (simulación en vivo) | `test_un_archivo_que_llega_tarde_no_se_pierde`, `test_el_dia_siguiente_llega_archivo_por_archivo` ([test_vivo.py](../../tests/test_vivo.py)); `test_sin_simulacion_en_vivo_el_estado_dice_inactivo` ([test_api.py](../../tests/test_api.py)). Que la web consulte `/vivo` y se recargue sola no tiene prueba automatizada: se ve en el portal | [Archivos del 25 de septiembre llegando](../evidencias/portal/hu09-actividad-en-vivo.png); [ADR 0013](../adr/0013-simulacion-en-vivo.md): solo en local |
| Comentario del prototipo: lectura rápida del día | Sin prueba automatizada de su texto: la frase se arma en la web (`LecturaRapida.vue`) con la certificación y la comparación del día, que sí tienen prueba: `test_certificacion_integral_del_dia_de_la_fuga`, `test_comparar_cortes_muestra_primero_lo_que_empeoro`. `scripts/verificar_portal.py` (Playwright) solo comprueba que el Resumen la muestre | [Resumen del 14 de julio](../evidencias/portal/hu09-resumen-14-julio.png): explica en una frase que Persona quedó retenida por llegar tarde |
| Comentario del prototipo: recorrido de bienvenida | Sin prueba automatizada de su contenido: se ve en el portal en la primera visita al Resumen (`RecorridoGuiado.vue`). `scripts/verificar_portal.py` solo comprueba que Esc lo cierre y devuelva el foco | [Último paso: el viaje de los datos](../evidencias/portal/hu09-recorrido-viaje-datos.png) |
| Tarea del sprint: Resumen y Validaciones con teclado y lector de pantalla (mapa de días y diálogo de detalle) y tema oscuro | Sin prueba en `tests/`: lo comprueba `scripts/verificar_portal.py` con Playwright (teclado, mapa de días, diálogo de detalle de la regla y contraste en claro y en oscuro) | [accesibilidad-y-e2e.txt](../evidencias/accesibilidad-y-e2e.txt); [Resumen](../evidencias/portal/oscuro/resumen.png) y [Validaciones](../evidencias/portal/oscuro/validaciones.png) en tema oscuro |

**Decisión de diseño:** [ADR 0013](../adr/0013-simulacion-en-vivo.md) (simulación en vivo dentro de la
API, solo en local) y [ADR 0015](../adr/0015-indicador-pass.md) (el % de reglas en PASS es el
indicador principal).

### HU-12 · Consultar la certificación integral del dato

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Se ve si el conjunto de datos está certificado o no | `test_certificacion_integral_del_dia_de_la_fuga` ([test_api.py](../../tests/test_api.py)); `test_matriz_de_certificacion` ([test_certificacion.py](../../tests/test_certificacion.py)) | [Certificación del 7 de agosto](../evidencias/portal/hu04-hu07-hu12-certificacion-7-agosto.png), una ficha por tabla; [en tema oscuro](../evidencias/portal/oscuro/certificacion.png) |
| Con reglas fallidas, se ve que no está certificado y sus observaciones | `test_la_certificacion_dice_que_reglas_la_bloquean`, `test_una_media_en_falla_no_bloquea` ([test_certificacion.py](../../tests/test_certificacion.py)); `test_certificacion_integral_del_dia_de_la_fuga` | [Póliza bloqueada por POL-CON-03](../evidencias/portal/hu04-hu12-certificacion-30-septiembre.png); [Siniestro retenido por PII en claro](../evidencias/portal/hu04-hu07-hu12-certificacion-7-agosto.png) |
| Se verifica que los campos PII tienen la protección establecida | `test_certificacion_integral_del_dia_de_la_fuga` (`campos_cifrados` con `protegido`); `test_un_campo_que_debe_ir_cifrado_y_se_guardo_como_texto_bloquea` ([test_certificacion.py](../../tests/test_certificacion.py)); `test_ningun_campo_pii_queda_en_texto_plano_en_master` ([test_flujo.py](../../tests/test_flujo.py)) | Campos cifrados de Persona en la [ficha del 7 de agosto](../evidencias/portal/hu04-hu07-hu12-certificacion-7-agosto.png); [`NUM_DOC` a `nro_documento` con cifrado](../evidencias/portal/hu06-hu11-linaje-campo-cifrado.png) |
| Desde lo certificado en BUSINESS se llega a su linaje y a los resultados de calidad | `test_certificacion_integral_del_dia_de_la_fuga` (objeto en BUSINESS e historia por día), `test_linaje_de_persona_de_raw_a_business`. El enlace «Ver su linaje» no tiene prueba automatizada: se ve en el portal | Cada ficha trae su objeto en BUSINESS, la calidad por nivel y «Ver su linaje» ([captura](../evidencias/portal/hu04-hu07-hu12-certificacion-7-agosto.png)); [Linaje](../evidencias/portal/hu11-linaje.png) |
| Comentario de la revisión del Sprint 2: desde qué día ve negocio el último sello bueno | `test_cada_tabla_retenida_dice_que_dia_sigue_viendo_negocio`, `test_el_ultimo_dia_certificado_ignora_los_retenidos_y_los_dias_posteriores` ([test_api.py](../../tests/test_api.py)) | La ficha de cada tabla retenida dice «Negocio sigue viendo el …» (último día certificado); ver la [Certificación en tema oscuro](../evidencias/portal/oscuro/certificacion.png) |

### HU-11 · Consultar el linaje de los datos

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Se muestra el recorrido entre las capas | `test_linaje_de_persona_de_raw_a_business` ([test_api.py](../../tests/test_api.py)) | [Linaje de Persona](../evidencias/portal/hu11-linaje.png): RAW, MASTER y BUSINESS; [en tema oscuro](../evidencias/portal/oscuro/linaje.png) |
| Lo que viene de RAW se identifica en MASTER | `test_linaje_de_persona_de_raw_a_business` (`NUM_DOC` a `nro_documento`); `test_raw_conserva_los_valores_tal_cual_vienen`, `test_master_usa_los_nombres_estandar` ([test_flujo.py](../../tests/test_flujo.py)) | [Recorrido de cada campo](../evidencias/portal/hu06-hu11-linaje-campo-cifrado.png) |
| Lo certificado se identifica en BUSINESS | `test_linaje_de_persona_de_raw_a_business` (tabla `p_` y vista `v_`); `test_business_solo_tiene_cortes_certificados`, `test_la_vista_de_cada_tabla_muestra_su_ultimo_corte_certificado` ([test_certificacion.py](../../tests/test_certificacion.py)); `test_el_portal_solo_lee_la_capa_business` | «Publicado en BUSINESS» por día en el [Linaje](../evidencias/portal/hu11-linaje.png) |
| Se ven las etapas y transformaciones | `test_linaje_de_persona_de_raw_a_business` (transformación de cada campo, p. ej. «cifrado determinístico»). El nombre de las etapas que unen las capas no tiene aserción propia: se ve en la captura | [Linaje](../evidencias/portal/hu11-linaje.png): etapas entre capas y transformación de cada campo |
| Comentario de la revisión del Sprint 2: el motivo de cada día no publicado | `test_linaje_de_persona_dice_por_que_se_retuvo_cada_dia`, `test_linaje_de_siniestro_explica_la_fuga_de_datos_personales`, `test_el_texto_del_motivo_se_arma_con_la_dimension_de_la_regla` ([test_api.py](../../tests/test_api.py)) | El Linaje de Persona lista el 14 y el 22 de julio con su motivo ([tema oscuro](../evidencias/portal/oscuro/linaje.png)) |

### HU-10 · Consultar el glosario de negocio

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Se ven los términos del catálogo | `test_el_glosario_tiene_42_terminos_con_campos_que_existen_en_el_esquema` ([test_configuracion_local.py](../../tests/test_configuracion_local.py)); `test_glosario_busca_sin_tildes_y_filtra_por_dominio` ([test_api.py](../../tests/test_api.py)) | [Glosario](../evidencias/portal/hu10-glosario-busqueda.png); [en tema oscuro](../evidencias/portal/oscuro/glosario.png) |
| Al elegir un término, se ve su definición | `test_el_glosario_define_el_carne_de_extranjeria_y_el_estado_de_la_cuota` ([test_configuracion_local.py](../../tests/test_configuracion_local.py)); `test_glosario_busca_sin_tildes_y_filtra_por_dominio` (ficha de `prima-total`). Elegir el término en pantalla no tiene prueba de la web | [Glosario](../evidencias/portal/hu10-glosario-busqueda.png) |
| La búsqueda muestra los términos que coinciden | `test_glosario_busca_sin_tildes_y_filtra_por_dominio` (`dni`, `poliza`) | [Búsqueda «dni»](../evidencias/portal/hu10-glosario-busqueda.png) |
| Cada término muestra su dominio de negocio | `test_glosario_busca_sin_tildes_y_filtra_por_dominio` (filtro por Persona); `test_el_glosario_define_el_carne_de_extranjeria_y_el_estado_de_la_cuota` (Persona y Póliza) | [Glosario](../evidencias/portal/hu10-glosario-busqueda.png) |
| Tarea del sprint: edición solo para gobierno y administrador | `test_solo_gobierno_y_admin_editan_el_glosario` ([test_api.py](../../tests/test_api.py)) | [Glosario en tema oscuro](../evidencias/portal/oscuro/glosario.png) |
| Tarea del sprint: términos «Carné de extranjería» y «Estado de la cuota» | `test_el_glosario_define_el_carne_de_extranjeria_y_el_estado_de_la_cuota`, `test_un_json_viejo_recibe_la_regla_y_el_termino_que_le_faltan` ([test_configuracion_local.py](../../tests/test_configuracion_local.py)) | Los términos que usan PER-VAL-06 y PAG-VAL-01 |

Las pruebas leen el glosario del modo local. En el modo GCP se siembra en Firestore
(`python -m dqc.gcp`, `src/dqc/gcp/firestore.py`) y esa lectura no tiene prueba automatizada.

### HU-15 · Garantizar el tiempo de carga del Portal Smart-DQ

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Cualquier sección responde en menos de 8 segundos | `test_cada_seccion_responde_en_menos_de_8_segundos` ([test_api.py](../../tests/test_api.py)): 12 rutas que cubren las 11 secciones (las de consulta con el rol lector y las 4 de administración con el rol admin), sobre la simulación en DuckDB; `test_el_plan_tiene_las_11_secciones_en_el_orden_del_menu`, `test_cada_ruta_del_plan_existe_en_la_api` ([test_rendimiento.py](../../tests/test_rendimiento.py)) | Las 11 secciones, en frío y bajo carga: [rendimiento.txt](../evidencias/rendimiento.txt) (API local) y [rendimiento-bigquery.txt](../evidencias/rendimiento-bigquery.txt) (BigQuery). Mide la API hasta el último byte; no incluye bajar el JavaScript ni dibujar la pantalla |
| El dashboard muestra la información dentro del límite | `test_cada_seccion_responde_en_menos_de_8_segundos` (`/resumen` y `/validaciones`); `test_con_la_cache_vencida_solo_una_peticion_relee_las_vistas`, `test_al_vencer_la_cache_nadie_espera_y_la_renovacion_corre_aparte`, `test_un_corte_nuevo_si_obliga_a_esperar_datos_nuevos`, `test_una_lectura_empezada_antes_de_invalidar_no_queda_vigente` (la caché de 10 minutos) | Filas Resumen y Validaciones de [rendimiento.txt](../evidencias/rendimiento.txt) y [rendimiento-bigquery.txt](../evidencias/rendimiento-bigquery.txt) |
| Si se supera el límite, queda registrada la incidencia | `test_una_solicitud_lenta_queda_registrada_en_la_auditoria` ([test_api.py](../../tests/test_api.py)): evento `RENDIMIENTO_LENTO` | La Auditoría lo muestra como «Respuesta lenta (más de 8 s)»; la [captura](../evidencias/portal/hu13-hu15-auditoria.png) es de la pantalla y no contiene ningún evento de este tipo. Los informes de rendimiento cuentan las solicitudes que la API registró como lentas |
| Las pruebas de rendimiento permiten verificar el indicador | `test_veredicto_cumple_si_frio_y_carga_estan_bajo_el_limite`, `test_veredicto_dice_por_que_no_cumple`, `test_el_limite_es_el_de_la_api`, `test_percentiles_con_datos_inventados`, `test_estadisticas_de_una_seccion`, `test_el_informe_cuenta_las_secciones_que_cumplen` ([test_rendimiento.py](../../tests/test_rendimiento.py)) | Cada informe termina con «Resultado: N de 11 secciones por debajo de 8 s» ([rendimiento.txt](../evidencias/rendimiento.txt), [rendimiento-bigquery.txt](../evidencias/rendimiento-bigquery.txt)) |

**Qué dice la medición (11 de noviembre).** Con la API local, la apertura más lenta de las 11 secciones fue de 1,0 s
bajo carga. Sobre BigQuery (sandbox, 92 cortes), el Resumen tarda 1,4 s con la caché vigente y hasta 2,9 s con 10
usuarios a la vez; en frío (arranque sin caché) tarda 4,9 a 5,1 s, y 5,3 a 5,6 s al vencer la caché tras 10 minutos sin uso.
Todo queda por debajo de los 8 s, pero el Resumen en frío es el que tiene el margen más corto (cerca de 3 s). La
medición no incluye bajar el JavaScript ni dibujar la pantalla en el navegador.

### Tarea técnica · Tres reglas de la auditoría (SIN-UNI-01, PAG-VAL-01 y PER-VAL-06)

| Criterio del Sprint Backlog | Prueba automatizada | Evidencia |
|---|---|---|
| Las tres reglas están en el catálogo con la definición decidida: 51 evaluaciones por corte | `test_las_reglas_nuevas_tienen_la_definicion_decidida`, `test_catalogo_tiene_39_reglas_y_51_expandidas`, `test_cada_corte_evalua_las_51_reglas_con_su_nivel` ([test_motor.py](../../tests/test_motor.py)); `test_las_reglas_sobreviven_el_viaje_a_firestore` ([test_firestore.py](../../tests/test_firestore.py)) | [auditoria-reglas.md](../auditoria-reglas.md): las tres figuran como «Aplicada (Sprint 3)»; corrida de los 92 cortes en [pipeline-local.txt](../evidencias/pipeline-local.txt) y [bigquery.txt](../evidencias/bigquery.txt) |
| Detectan el defecto aunque los datos sintéticos nunca se lo den | `test_sin_uni_01_detecta_un_id_de_siniestro_repetido`, `test_pag_val_01_detecta_estados_fuera_del_dominio`, `test_pag_val_01_acepta_los_tres_estados`, `test_per_val_06_detecta_tipos_de_documento_fuera_del_dominio` ([test_reglas.py](../../tests/test_reglas.py)) | Cada prueba arma la tabla de MASTER a mano en DuckDB y corre el motor con la regla del catálogo |
| No cambian ningún sello aceptado (el puntaje sí sube: hasta 0,2 puntos el global y 1,2 el de Persona, y 3 reglas más quedan en OK cada día, porque las nuevas dan 100 %) | `test_las_reglas_nuevas_dan_100_en_los_datos_sinteticos` ([test_motor.py](../../tests/test_motor.py)), en los cortes de las pruebas; `test_matriz_de_certificacion` ([test_certificacion.py](../../tests/test_certificacion.py)) | Los 92 cortes, en [pipeline-local.txt](../evidencias/pipeline-local.txt) y [bigquery.txt](../evidencias/bigquery.txt); reporte de pytest en [pruebas.txt](../evidencias/pruebas.txt) |
| El glosario define los términos que usan las reglas nuevas, y una configuración ya sembrada los recibe | `test_el_glosario_define_el_carne_de_extranjeria_y_el_estado_de_la_cuota`, `test_un_json_viejo_recibe_la_regla_y_el_termino_que_le_faltan` ([test_configuracion_local.py](../../tests/test_configuracion_local.py)) | Términos en el [Glosario](../evidencias/portal/oscuro/glosario.png) |

### Definition of Done por historia

| Criterio de la Definition of Done | HU-13 | HU-09 | HU-12 | HU-11 | HU-10 | HU-15 |
|---|---|---|---|---|---|---|
| Código en `main` y CI en verde | Sí | Sí | Sí | Sí | Sí | Sí |
| Cada criterio de aceptación con prueba automatizada | 4 de 4; el primero, por categoría DAC y rol de la aplicación, no por grupo de IAM (ADR 0016) | 4 de 4; la lectura rápida y el recorrido no tienen prueba (son de la web) | 4 de 4; el enlace al linaje solo se ve en el portal | 4 de 4; el nombre de las etapas entre capas no tiene aserción propia | 4 de 4; elegir un término en pantalla no tiene prueba de la web | 4 de 4; pytest cubre las 11 secciones y el script las mide en frío y bajo carga |
| 0 diferencias contra el manifiesto | No aplica: se verifica con las pruebas de la API y con Firestore real | No aplica: se verifica con las pruebas de la API y de la simulación en vivo | No aplica: sus pruebas usan los incidentes sembrados (la fuga de PII, el archivo tarde) | No aplica: sus pruebas usan los incidentes sembrados | No aplica: se verifica con las pruebas del glosario | No aplica: es un requisito no funcional; se verifica con las mediciones |
| Desvíos del documento de arquitectura en un ADR | [0011](../adr/0011-inicio-de-sesion.md), [0016](../adr/0016-roles-de-la-aplicacion.md) | [0013](../adr/0013-simulacion-en-vivo.md), [0015](../adr/0015-indicador-pass.md) | Sin ADR | Sin ADR | Sin ADR | Sin ADR |
| Evidencia en `docs/evidencias` | Sí: capturas y [acceso-firestore.txt](../evidencias/acceso-firestore.txt) | Sí: capturas y [accesibilidad-y-e2e.txt](../evidencias/accesibilidad-y-e2e.txt) | Sí: capturas | Sí: capturas | Sí: capturas | Sí: [rendimiento.txt](../evidencias/rendimiento.txt) y [rendimiento-bigquery.txt](../evidencias/rendimiento-bigquery.txt) |
| Issue cerrado y enlazado a su evidencia | [#13](https://github.com/GabouLC/dq-center/issues/13) | [#9](https://github.com/GabouLC/dq-center/issues/9) | [#12](https://github.com/GabouLC/dq-center/issues/12) | [#11](https://github.com/GabouLC/dq-center/issues/11) | [#10](https://github.com/GabouLC/dq-center/issues/10) | [#15](https://github.com/GabouLC/dq-center/issues/15) |

La tarea técnica de las tres reglas no cambia ningún sello: la verificación de los 92 cortes contra el
manifiesto, con las 51 reglas, queda en [pipeline-local.txt](../evidencias/pipeline-local.txt) y
[bigquery.txt](../evidencias/bigquery.txt). El CI de GitHub Actions y los controles del repositorio
(CodeQL, gitleaks, Dependabot y la protección de `main`) son los del
[ADR 0017](../adr/0017-controles-del-repositorio.md).

### Reunión de revisión

*Acta reconstruida el 11 de noviembre de 2026 a partir de la verificación de cada criterio contra el
repositorio, el tablero de Jira y la revisión de los cambios. No hay registro de una reunión del equipo
en esa fecha: lo que sigue es lo que se comprobó, y queda pendiente que el equipo la confirme.*

- **Fecha:** 11 de noviembre de 2026 (la revisión estaba prevista para el 2 de noviembre).
- **Quién verificó:** Gabriel León, como Product Owner. Franco Delgado tiene HU-10 en revisión en Jira.
- **Historias verificadas contra sus criterios:** las seis y la tarea técnica de las tres reglas. Cada
  criterio tiene en las tablas de arriba su prueba o su evidencia, y dice cuando no tiene prueba
  automatizada.
- **Aceptación:** las seis historias cumplen sus criterios en el repositorio. En Jira, HU-10
  (SDGDCYP-89) sigue en revisión de Franco; no se cambió su estado.

**Hallazgos de la verificación**

| Hallazgo | Qué se hizo |
|---|---|
| Las secciones Reglas y Ejecuciones respondían a cualquier rol: solo la administración las usa, y el criterio «sin el rol autorizado, el acceso se restringe» no las cubría | Ahora piden el permiso de configurar; prueba `test_reglas_y_ejecuciones_solo_se_leen_con_permiso_de_configurar` |
| Una configuración local ya sembrada no recibía las reglas ni los términos nuevos: el portal seguía mostrando 36 reglas | La configuración local agrega lo que falta sin pisar lo existente; prueba `test_un_json_viejo_recibe_la_regla_y_el_termino_que_le_faltan` |
| HU-07 (cifrado): ninguna prueba cubría un campo que debe ir cifrado y llega como texto | Se agregó la prueba `test_un_campo_que_debe_ir_cifrado_y_se_guardo_como_texto_bloquea`: la tabla queda sin certificar |
| La prueba de HU-15 cubría 7 de las 11 secciones y la medición pendiente no existía | La prueba cubre las 11; `scripts/medir_rendimiento.py` mide cada una en frío y bajo carga, en local y en BigQuery |
| La medición de HU-15 sobre BigQuery mostró dos cosas: con la caché de 10 minutos vencida, cada petición volvía a leer las 7 vistas (con diez usuarios a la vez, 70 lecturas en lugar de 7), y esa espera llegaba a 8,6 s al abrir el Resumen, más de los 8 s del criterio; con el cambio, esa apertura tarda 5,3 a 5,6 s (no se investigó cuánto es de las conexiones en frío a Firestore y BigQuery tras la pausa) | Una sola petición lee las vistas; al vencer la caché nadie espera (se responde con lo último leído y se renueva en segundo plano); un corte publicado sí espera datos nuevos. Pruebas `test_con_la_cache_vencida_solo_una_peticion_relee_las_vistas`, `test_al_vencer_la_cache_nadie_espera_y_la_renovacion_corre_aparte`, `test_un_corte_nuevo_si_obliga_a_esperar_datos_nuevos` y `test_una_lectura_empezada_antes_de_invalidar_no_queda_vigente` (las dos primeras fallan con el código anterior); [rendimiento-bigquery.txt](../evidencias/rendimiento-bigquery.txt) |
| El criterio «las tres reglas no cambian ningún resultado» era inexacto: los sellos de los 92 días son los mismos, pero el puntaje sube hasta 0,2 puntos el global y 1,2 el de Persona | Se corrigió en [auditoria-reglas.md](../auditoria-reglas.md) y aquí; la corrida con las 51 evaluaciones está en [pipeline-local.txt](../evidencias/pipeline-local.txt) |
| Varios documentos seguían diciendo 36 reglas y 48 evaluaciones | Se actualizaron README, AGENTS.md y los ADR; los Sprints 1 y 2 conservan lo que fue cierto entonces |
| La re-evaluación de los 92 cortes en BigQuery con 51 reglas tardaba 96 s por día | Se publica por tabla en paralelo (62 s por día) y se agregó `ejecutar --todos`; resultado en [bigquery.txt](../evidencias/bigquery.txt) |

**Pendiente de decisión del Product Owner.** La banda de ALERTA de las reglas CRÍTICAS y las demás
propuestas de la [auditoría](../auditoria-reglas.md) siguen en el Product Backlog: cambiarían
resultados ya aceptados.

## 5. Sprint Retrospective

*Acta reconstruida el 11 de noviembre de 2026 a partir de los hechos del sprint (repositorio y
Jira); no hay registro de una reunión del equipo. Las acciones son propuestas para que el equipo las
confirme.*

**Fecha:** 11 de noviembre de 2026. **Elaborada por:** Gabriel León (Product Owner), con el
tablero de Jira y el historial del repositorio.

**Qué pasó con el plan.** Se comprometieron 31 SP para seis días hábiles, sobre una velocidad de 22
y 23. El prototipo cubría 23 de 33 tareas y por eso entraron todas las historias. El repositorio no tuvo
trabajo entre el 25 de octubre y el 10 de noviembre; las 10 tareas que faltaban, los hallazgos de
la revisión y la evidencia se cerraron el 11 de noviembre, nueve días después de la fecha prevista.
No se recortó HU-15, que era la primera en salir si el sprint se atrasaba.

**Seguimiento de las acciones del Sprint 2**

| Acción | Resultado |
|---|---|
| Reasignar las historias de Josue Borda en la Sprint Planning | Se hizo en el plan del 24 de octubre; el 7 de noviembre el equipo las repartió distinto en Jira y Josue sigue sin historias |
| Reanudar la carga de BigQuery desde donde se cortó | Hecho el 24 de octubre (`--desde`); el 11 de noviembre se volvió a usar para reevaluar los 92 cortes (`ejecutar --todos`) |
| Un pull request por historia, revisado por otro integrante | Cumplida a medias: desde el 11 de noviembre todo entra por pull request con el CI en verde, pero sin segunda persona que revise; el repositorio tiene dos colaboradores |
| Escalar la facturación de GCP | Sin cambios: no hay Cloud Run; el portal se demuestra en local o contra BigQuery |
| Partir las historias de 8 SP en partes que se puedan aceptar antes del cierre (HU-11) | No se hizo: HU-11 se aceptó entera al final |

| Empezar a hacer | Dejar de hacer | Continuar haciendo |
|---|---|---|
| Anotar la daily del día aunque sea una línea: este sprint no dejó ninguna | Cerrar tareas en Jira sin enlazar el commit o el pull request que las respalda | Probar en DuckDB y en BigQuery desde el primer día |
| Medir el rendimiento (HU-15) cuando el portal ya está armado, no al final | Dejar el trabajo de verificación (accesibilidad, tema oscuro, medición) para después del cierre | Exigir 0 diferencias contra el manifiesto en cada corrida completa |
| Revisar los permisos de cada ruta nueva de la API junto con su pantalla | Comprometer más puntos de los que dice la velocidad de los dos sprints anteriores | Un pull request por cambio, con el CI en verde: CodeQL, gitleaks y pruebas |

**Acciones propuestas**

| Acción | Responsable propuesto | Para cuándo |
|---|---|---|
| Registrar la daily de cada día hábil en [dailies.md](dailies.md), aunque sea de una línea | Franco Delgado (SM) | Desde el Sprint 4 |
| Enlazar en cada tarea de Jira el pull request o el commit que la cierra | Quien cierre la tarea | Desde el Sprint 4 |
| Pedir una aprobación en la protección de `main` cuando haya una segunda persona que revise (hoy se exigen 0) | Gabriel León (PO) | Cuando el equipo confirme quién revisa |
| Decidir la banda de ALERTA de las reglas CRÍTICAS y el resto de la auditoría | Gabriel León (PO) | Antes de la próxima Sprint Planning |
| Desplegar API y portal en Cloud Run cuando la facturación de GCP esté activa; si no, mantener la demostración en local | Gabriel León (PO) | Sin fecha: depende de la facturación |
| Volver a cargar los 92 cortes en BigQuery antes de una demostración posterior a mediados de diciembre (las tablas del sandbox vencen) | Gabriel León (PO) | Antes de esa demostración |

**El Sprint 4 del tablero** (30 de octubre al 12 de noviembre) es del equipo: allí volvieron a registrar
cinco de estas historias como copias (SDGDCYP-89 a 93). Este repositorio no abre un documento aparte
para ese sprint: el trabajo que cubre ya está en este.
