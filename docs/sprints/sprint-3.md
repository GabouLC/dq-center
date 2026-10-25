# Sprint 3 · Portal Smart-DQ

**Estado:** en curso · **Fechas:** sábado 24 de octubre (Sprint Planning) al lunes 2 de noviembre de
2026 · **Compromiso:** 31 SP, 6 historias y una tarea técnica ·
**Milestone:** [Sprint 3](https://github.com/GabouLC/dq-center/milestone/4) ·
**Jira:** SDGDCYP Sprint 3 (activo desde el 24 de octubre)

El sprint estaba previsto del 20 de octubre al 2 de noviembre. La Sprint Planning se hizo el 24,
con cuatro días de retraso, porque antes había que cerrar el Sprint 2 (su corrida en BigQuery
terminó ese día). La revisión se mantiene el lunes 2 de noviembre: el sprint dura seis días hábiles.

**Prototipo adelantado.** El repositorio ya tiene un prototipo funcional del portal (commits
[`fe181da`](https://github.com/GabouLC/dq-center/commit/fe181da),
[`075eccc`](https://github.com/GabouLC/dq-center/commit/075eccc),
[`12d0d91`](https://github.com/GabouLC/dq-center/commit/12d0d91),
[`a5f625a`](https://github.com/GabouLC/dq-center/commit/a5f625a) y
[`2e01263`](https://github.com/GabouLC/dq-center/commit/2e01263)), que sirvió para recoger
comentarios antes de planificar. Por eso buena parte del Sprint Backlog ya está hecha: lo que
queda es verificar cada criterio, atender los comentarios de la revisión del Sprint 2 y aceptar.

## 1. Sprint Planning

**Fecha:** sábado 24 de octubre de 2026. La preparó el Product Owner con estas decisiones; el
equipo la confirma en la primera daily, el lunes 26. **Participantes previstos:** Gabriel León
(Product Owner), Franco Delgado (Scrum Master), Jesus de la Cruz y Cristhian Pimentel.

### ¿Por qué es valioso este sprint? · Objetivo del sprint

**Objetivo del sprint.** Llevar los resultados al negocio: un portal donde cada rol ve la salud
y la certificación de los datos, su linaje y su glosario, con acceso controlado y cada sección
en menos de 8 segundos.

**Valor.** Los Sprints 1 y 2 dejaron cada corte con un veredicto por tabla. Sin el portal, ese
veredicto solo se ve con consultas; con él, negocio, gobierno y la Oficina de Datos responden
«¿puedo usar estos datos hoy?» por sí mismos.

### ¿Qué se puede terminar? · Historias seleccionadas

**Decisiones del Product Owner (24 de octubre)**

1. **Responsables.** Josue Borda no participó en ningún evento de los Sprints 1 y 2 ni confirmó su
   disponibilidad (acción de las dos retrospectivas). Sus cuatro historias se reasignan por
   afinidad con lo que cada integrante ya construyó:
   - HU-11 (linaje) a Jesus de la Cruz, que hizo la homologación y el cifrado;
   - HU-12 (certificación integral) y HU-15 (rendimiento) a Franco Delgado, que hizo la
     certificación y es el QA del equipo;
   - HU-09 (dashboard) a Cristhian Pimentel, que hizo el motor de reglas.
2. **Capacidad.** Las seis historias suman 31 SP, por encima de la velocidad de 22 y 23. Entran
   todas porque el prototipo ya cubre la mayor parte del trabajo. Si el sprint se atrasa, HU-15 es
   la primera en salir: va última y no bloquea a ninguna otra.
3. **Auditoría de reglas.** Entran SIN-UNI-01, PAG-VAL-01 y PER-VAL-06 como tarea técnica: hoy dan
   100 % en los 92 días, así que no cambian ningún sello aceptado. Las demás propuestas de la
   [auditoría](../auditoria-reglas.md), incluida la banda de ALERTA de las reglas CRÍTICAS, siguen en
   el Product Backlog.

**Historias comprometidas.** Los puntos son los del Product Backlog del equipo en Jira.

| # | Historia | SP | Complejidad | Rol del backlog | Responsable | Issue | Estado |
|---|---|---|---|---|---|---|---|
| 1 | HU-13 · Controlar el acceso a datos sensibles mediante roles | 5 | Media | Data Architect | Jesus de la Cruz | [#13](https://github.com/GabouLC/dq-center/issues/13) | En curso |
| 2 | HU-09 · Visualizar el estado de calidad de los datos | 5 | Media | Oficina de Datos | Cristhian Pimentel | [#9](https://github.com/GabouLC/dq-center/issues/9) | En curso |
| 3 | HU-12 · Consultar la certificación integral del dato | 5 | Media | Data Owner | Franco Delgado | [#12](https://github.com/GabouLC/dq-center/issues/12) | En curso |
| 4 | HU-11 · Consultar el linaje de los datos | 8 | Alta | Oficina de Datos | Jesus de la Cruz | [#11](https://github.com/GabouLC/dq-center/issues/11) | En curso |
| 5 | HU-10 · Consultar el glosario de negocio | 3 | Baja-media | Negocio | Gabriel León | [#10](https://github.com/GabouLC/dq-center/issues/10) | En curso |
| 6 | HU-15 · Garantizar el tiempo de carga del portal | 5 | Media | Negocio | Franco Delgado | [#15](https://github.com/GabouLC/dq-center/issues/15) | En curso |

Carga por integrante: Jesus 13 SP, Franco 10, Cristhian 5 más la tarea técnica de reglas y
Gabriel 3, además de su trabajo como Product Owner.

**Por qué este orden.**

- HU-13 va primero porque toda pantalla del portal necesita saber quién entra y qué puede ver.
- HU-09 es el mayor valor para el negocio: responde «¿puedo confiar en los datos de este día?».
- HU-12 reutiliza la certificación del Sprint 2 y la hace visible por tabla.
- HU-11 explica de dónde sale cada campo y por qué una tabla no se publicó.
- HU-10 es la más simple y no bloquea a ninguna otra.
- HU-15 cierra el sprint: se mide sobre todas las pantallas ya construidas.

**Fuera del sprint.** El despliegue en Cloud Run, que depende de la facturación de GCP, y el resto
de las propuestas de la auditoría de reglas.

### ¿Cómo se hará? · Plan de trabajo

Cada responsable verifica su historia contra los criterios del Product Backlog: primero con las
pruebas automatizadas, después en el portal con teclado, lector de pantalla y tema oscuro. Lo que
falte se corrige con una rama y un pull request por historia, revisado por otro integrante (acción
de la retrospectiva del Sprint 2). La evidencia se regenera con `scripts/capturas_portal.py`.

## 2. Sprint Backlog

Las tareas de cada historia, con su responsable. Las marcadas ya se hicieron en el prototipo.

| Historias | Tareas por hacer | Tareas hechas |
|---|---|---|
| 6 en curso | 10 | 23 de 33 |

**Base del portal** · todo el equipo
- [x] API FastAPI con prefijo `/api/v1`, sondas `/health` y errores con el formato del documento de arquitectura (`src/dqc/api/app.py`)
- [x] Web Vue 3 + TypeScript + Pinia en MVVM, con la línea de tiempo compartida por los módulos (`web/`)
- [x] La API lee solo las vistas de contrato de BUSINESS (`src/dqc/api/datos.py`)

**HU-13 · Acceso por rol** · Jesus de la Cruz
- [x] Roles admin, gobierno y lector, con permisos por módulo (`PERMISOS` y `MODULOS`)
- [x] Campos SENSIBLE ocultos para el lector, también en las incidencias; SENSIBLE_CIFRADO siempre ocultos
- [x] Auditoría de accesos denegados y de campos ocultos
- [x] Inicio de sesión con correo y contraseña, bloqueo por intentos y contraseña temporal (`src/dqc/api/autenticacion.py`, ADR 0011)
- [x] Administración de usuarios: alta, cambio de rol, restablecer contraseña y quitar acceso
- [ ] Probar el inicio de sesión, el bloqueo y el cambio de contraseña contra Firestore (modo GCP)
- [ ] Recorrer Entrar, Cambiar contraseña y Usuarios solo con teclado y con lector de pantalla

**HU-09 · Dashboard** · Cristhian Pimentel
- [x] Simulación en vivo: los archivos del día llegan uno por uno, el corte se publica al completarse y el portal se actualiza solo (`src/dqc/api/vivo.py`)
- [x] Indicador «En vivo», panel de actividad y avisos; línea de tiempo y mapa de certificación por día
- [x] Resumen: % de reglas que cumplen, puntaje de calidad, tendencia diaria y dimensiones por tabla
- [x] Validaciones: reglas del día con las fallas primero, filtros y detalle con los registros fallidos
- [x] Comparación entre dos días, con lo que empeoró primero
- [x] Ejecuciones: volver a evaluar un corte desde el portal y ver su resultado
- [ ] Recorrer Resumen y Validaciones con teclado y lector de pantalla: mapa de días y diálogo de detalle
- [ ] Revisar el tema oscuro de todas las pantallas con capturas

**HU-12 · Certificación integral** · Franco Delgado
- [x] Sello por tabla con calidad por nivel, privacidad (campos cifrados y hallazgos) y trazabilidad (ejecución, versiones, objeto en BUSINESS)
- [x] Certificación día por día de los 92 cortes y enlace al linaje
- [ ] Mostrar, cuando una tabla no se publica, qué día está viendo negocio (su último corte certificado) (comentario de la revisión del Sprint 2)

**HU-11 · Linaje** · Jesus de la Cruz
- [x] Recorrido RAW → MASTER → BUSINESS por tabla, con el archivo de origen y los objetos publicados
- [x] Cada campo con su nombre en la fuente, su transformación y si se cifra
- [ ] En el paso a BUSINESS, el motivo de cada día que no se publicó (comentario de la revisión del Sprint 2)

**HU-10 · Glosario** · Gabriel León
- [x] 40 términos con definición, dominio, sinónimos y campos donde aparecen (`config/glosario.yaml`)
- [x] Búsqueda sin tildes ni mayúsculas, filtro por dominio y edición solo para gobierno y admin
- [ ] Términos «Carné de extranjería» y «Estado de la cuota», que usan las reglas nuevas PER-VAL-06 y PAG-VAL-01

**HU-15 · Rendimiento** · Franco Delgado
- [x] Las vistas de BUSINESS se leen en paralelo y quedan 10 minutos en memoria; se precargan al arrancar
- [x] Cabecera `Server-Timing` en cada respuesta y auditoría de las que pasan de 8 s
- [x] Prueba automatizada por sección del portal
- [ ] Medir cada sección con la API sobre BigQuery (sandbox, 92 cortes) y dejar el resultado en la evidencia

**Reglas de la auditoría DAMA** · Cristhian Pimentel
- [ ] SIN-UNI-01 (unicidad de `id_siniestro`), PAG-VAL-01 (dominio de `estado` de la cuota) y PER-VAL-06 (dominio de `tipo_documento`) en el catálogo, con su prueba
- [ ] Actualizar el conteo de 48 a 51 evaluaciones por corte en la documentación y regenerar la evidencia

## 3. Seguimiento · Daily Scrum

Virtuales, de 15 minutos, a las 8:00 p. m. de cada día hábil. La primera es el lunes 26 de
octubre. Las actas van en [dailies.md](dailies.md).

**Impedimentos y riesgos**

| Riesgo o impedimento | Efecto | Respuesta | Estado |
|---|---|---|---|
| Sin facturación en GCP | No hay Cloud Run para publicar el portal | El portal se demuestra en local, contra DuckDB o contra BigQuery | Abierto |
| Josue Borda no participa | Cuatro historias sin responsable | Reasignadas en la Sprint Planning; Franco (SM) le escribe para saber si se suma | Abierto |
| 31 SP sobre una velocidad de 22 y 23, en seis días hábiles | Sprint cargado | El prototipo cubre 23 de 33 tareas; HU-15 sale primero si hace falta | Abierto |
| La primera carga del Resumen sobre BigQuery puede acercarse a los 8 s de HU-15 | Riesgo de incumplir el requisito | Lectura en paralelo y precarga al arrancar; medirlo con los 92 cortes | Abierto |
| Las tablas del sandbox vencen a los 60 días (hacia mediados de diciembre) | Habría que volver a cargar los 92 cortes, unas 9 horas | Alcanza para la revisión del 2 de noviembre | Abierto |

**Burndown.** 31 SP comprometidos. Línea ideal en seis días hábiles:

| Día | Fecha | SP ideal | SP real | Historias cerradas ese día |
|---|---|---|---|---|
| 0 | sábado 24 de octubre | 31 | 31 | |
| 1 | lunes 26 | 25,8 | | |
| 2 | martes 27 | 20,7 | | |
| 3 | miércoles 28 | 15,5 | | |
| 4 | jueves 29 | 10,3 | | |
| 5 | viernes 30 | 5,2 | | |
| 6 | lunes 2 de noviembre | 0 | | |

## 4. Sprint Review e Incremento

La revisión es al cierre, el lunes 2 de noviembre. Antes de planificar, el prototipo recibió estos
comentarios, que ya están incorporados:

| Comentario | Cambio en el prototipo | Commit |
|---|---|---|
| «El diseño es muy apagado; hazlo más interactivo y atractivo» | Navegación con íconos, tema claro y oscuro, gráfico con tooltip y vista de tabla, y diseño móvil | `075eccc` |
| «Tiene que ser un inicio de sesión, no elegir roles» | Inicio de sesión con correo y contraseña, bloqueo por intentos, contraseña temporal y cambio obligatorio (ADR 0011) | `12d0d91` |
| «Datos de julio a septiembre, con valores y variaciones realistas, y que se sienta vivo» | Cortes diarios con ruido, tendencias e incidentes; simulación en vivo con actividad y avisos; % de reglas en PASS como indicador principal | `a5f625a` |
| Revisión de accesibilidad y lenguaje claro (24 de octubre) | Teclado, foco y contraste AA; vocabulario único; gráficos legibles con daltonismo | `2e01263` |
| «Que sea más atractivo y dinámico, y que se entienda rápido para qué sirve cada sección» (24 de octubre) | Cada sección dice qué pregunta responde y cómo se lee; lectura rápida del día en una frase; menú agrupado por objetivo; recorrido de bienvenida con el viaje de los datos; movimiento con propósito y estados de carga y vacíos (PR #19); aspecto de «panel de control vivo»: banda azul con la lectura rápida, el % que cumple y los sellos, tarjetas con acento de estado y tendencia en área (PR #20) | 24 de octubre |

Para verlo:

```bash
python -m dqc.pipeline --db data/dq.duckdb --hasta 2026-09-24   # del 25 al 30 llegan en vivo
python -m dqc.api               # API en http://127.0.0.1:8000
cd web && npm run dev           # portal en http://localhost:5173
```

Cuentas de demostración: `admin@demo.local`, `gobierno@demo.local` y `lector@demo.local`, con la
contraseña `SmartDQ-2026`.

### Evidencia preliminar del prototipo

Se confirma en la revisión del 2 de noviembre; hasta entonces ninguna historia está aceptada.

| Historia | Criterios cubiertos por pruebas automatizadas | Capturas |
|---|---|---|
| HU-13 | Roles y módulos, campos sensibles por rol (también en las incidencias), acceso denegado auditado, inicio de sesión, contraseña temporal y bloqueo, también con intentos en paralelo ([test_api.py](../../tests/test_api.py), [test_autenticacion.py](../../tests/test_autenticacion.py)) | [Login](../evidencias/portal/hu13-login.png), [gobierno](../evidencias/portal/hu13-validaciones-gobierno.png), [lector](../evidencias/portal/hu13-validaciones-lector.png), [acceso denegado](../evidencias/portal/hu13-auditoria-acceso-denegado.png) |
| HU-09 | Resumen con tendencia y % que cumple, fallas primero, comparación de días, ejecución nueva y llegada en vivo, también con archivos atrasados ([test_api.py](../../tests/test_api.py), [test_vivo.py](../../tests/test_vivo.py)) | [Resumen](../evidencias/portal/hu09-resumen.png), [14 de julio](../evidencias/portal/hu09-resumen-14-julio.png), [en vivo](../evidencias/portal/hu09-actividad-en-vivo.png) |
| HU-12 | Certificación integral del día de la fuga y su historia (`test_certificacion_integral_del_dia_de_la_fuga`) | [7 de agosto](../evidencias/portal/hu04-hu07-hu12-certificacion-7-agosto.png), [30 de septiembre](../evidencias/portal/hu04-hu12-certificacion-30-septiembre.png) |
| HU-11 | Recorrido de Persona de RAW a BUSINESS (`test_linaje_de_persona_de_raw_a_business`) | [Linaje](../evidencias/portal/hu11-linaje.png), [campo cifrado](../evidencias/portal/hu06-hu11-linaje-campo-cifrado.png) |
| HU-10 | Búsqueda sin tildes, filtro por dominio y edición por rol (`test_glosario_busca_sin_tildes_y_filtra_por_dominio`, `test_solo_gobierno_y_admin_editan_el_glosario`) | [Glosario](../evidencias/portal/hu10-glosario-busqueda.png) |
| HU-15 | Cada sección en menos de 8 s y registro de las lentas (`test_cada_seccion_responde_en_menos_de_8_segundos`, `test_una_solicitud_lenta_queda_registrada_en_la_auditoria`) | [Reporte de pruebas](../evidencias/pruebas.txt) |

## 5. Sprint Retrospective

Se hace al cierre, el 2 de noviembre, con la plantilla de [plantillas.md](plantillas.md). Acciones
de la retrospectiva del Sprint 2 que hay que revisar:

- Un pull request por historia, revisado por otro integrante (Franco Delgado).
- Partir las historias de 8 SP en partes que se puedan aceptar antes del cierre (HU-11).
- Escalar la facturación de GCP con soporte (Gabriel León).
