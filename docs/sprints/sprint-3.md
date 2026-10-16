# Sprint 3 · Portal Smart-DQ

**Estado:** planificado · **Fechas:** martes 20 de octubre al lunes 2 de noviembre de 2026 (dos
semanas) · **Compromiso previsto:** 31 SP, 6 historias ·
**Milestone:** [Sprint 3](https://github.com/GabouLC/dq-center/milestone/4) ·
**Jira:** SDGDCYP Sprint 3 (sin iniciar)

**Prototipo adelantado.** El repositorio ya tiene un prototipo funcional del portal (commits
[`fe181da`](https://github.com/GabouLC/dq-center/commit/fe181da),
[`075eccc`](https://github.com/GabouLC/dq-center/commit/075eccc),
[`12d0d91`](https://github.com/GabouLC/dq-center/commit/12d0d91) y
[`a5f625a`](https://github.com/GabouLC/dq-center/commit/a5f625a)), que sirvió para recoger
comentarios antes de planificar. Las historias se planifican, terminan y aceptan en este sprint.

## 1. Sprint Planning (preliminar)

**Fecha:** martes 20 de octubre de 2026, al iniciar el sprint. Este plan se confirma ese día.

**Objetivo del sprint.** Llevar los resultados al negocio: un portal donde cada rol ve la salud
y la certificación de los datos, su linaje y su glosario, con acceso controlado y cada sección
en menos de 8 segundos.

**Capacidad.** Velocidad sugerida de 20 a 24 SP; el Sprint 1 cerró 22 y el Sprint 2 compromete
23. Las seis historias suman 31 SP: por encima de la velocidad. En la Sprint Planning hay que
decidir si entra todo (el prototipo reduce el riesgo) o si HU-15 pasa a un sprint siguiente.

**Historias previstas.** Los puntos son los del Product Backlog del equipo en Jira.

| # | Historia | SP | Complejidad | Rol del backlog | Responsable | Issue | Estado |
|---|---|---|---|---|---|---|---|
| 1 | HU-13 · Controlar el acceso a datos sensibles mediante roles | 5 | Media | Data Architect | Jesus de la Cruz | [#13](https://github.com/GabouLC/dq-center/issues/13) | Por hacer |
| 2 | HU-09 · Visualizar el estado de calidad de los datos | 5 | Media | Oficina de Datos | Josue Borda | [#9](https://github.com/GabouLC/dq-center/issues/9) | Por hacer |
| 3 | HU-12 · Consultar la certificación integral del dato | 5 | Media | Data Owner | Josue Borda | [#12](https://github.com/GabouLC/dq-center/issues/12) | Por hacer |
| 4 | HU-11 · Consultar el linaje de los datos | 8 | Alta | Oficina de Datos | Josue Borda | [#11](https://github.com/GabouLC/dq-center/issues/11) | Por hacer |
| 5 | HU-10 · Consultar el glosario de negocio | 3 | Baja-media | Negocio | Gabriel León | [#10](https://github.com/GabouLC/dq-center/issues/10) | Por hacer |
| 6 | HU-15 · Garantizar el tiempo de carga del portal | 5 | Media | Negocio | Josue Borda | [#15](https://github.com/GabouLC/dq-center/issues/15) | Por hacer |

**Por qué este orden.**

- HU-13 va primero porque toda pantalla del portal necesita saber quién entra y qué puede ver.
- HU-09 es el mayor valor para el negocio: responde «¿puedo confiar en los datos de este corte?».
- HU-12 reutiliza la certificación del Sprint 2 y la hace visible por tabla.
- HU-11 explica de dónde sale cada campo y por qué una tabla quedó retenida.
- HU-10 es la más simple y no bloquea a ninguna otra.
- HU-15 cierra el sprint: se mide sobre todas las pantallas ya construidas.

**Fuera del sprint.** El despliegue en Cloud Run, que depende de la facturación de GCP.

## 2. Sprint Backlog

Se arma en la Sprint Planning del 20 de octubre. Refinamiento previo, a partir del prototipo:

**Base del portal**
- API FastAPI con prefijo `/api/v1`, sondas `/health` y errores con el formato del documento de arquitectura (`src/dqc/api/app.py`)
- Web Vue 3 + TypeScript + Pinia en MVVM, con la línea de tiempo compartida por los módulos (`web/`)
- La API lee solo las vistas de contrato de BUSINESS (`src/dqc/api/datos.py`)

**HU-13 · Acceso por rol**
- Roles admin, gobierno y lector, con permisos por módulo (`PERMISOS` y `MODULOS`)
- Campos SENSIBLE ocultos para el lector; SENSIBLE_CIFRADO siempre ocultos
- Auditoría de accesos denegados y de campos ocultos
- Inicio de sesión con correo y contraseña, bloqueo por intentos y contraseña temporal (`src/dqc/api/autenticacion.py`, ADR 0011)
- Administración de usuarios: alta, cambio de rol, restablecer contraseña y quitar acceso

**HU-09 · Dashboard**
- Simulación en vivo: los archivos del día llegan uno por uno, el corte se publica al completarse y el portal se actualiza solo (`src/dqc/api/vivo.py`)
- Indicador «En vivo», panel de actividad y avisos; línea de tiempo y mapa de certificación por día
- Resumen: % de reglas en PASS, score, tendencia diaria y dimensiones por tabla
- Validaciones: reglas del corte con las fallas primero, filtros y detalle con los registros fallidos
- Comparación entre dos días, con lo que empeoró primero
- Ejecuciones: lanzar una corrida desde el portal y ver su resultado

**HU-12 · Certificación integral**
- Sello por tabla con calidad por nivel, privacidad (campos cifrados y hallazgos) y trazabilidad (corrida, versiones, objeto en BUSINESS)
- Historia de los sellos de los 92 cortes y enlace al linaje

**HU-11 · Linaje**
- Recorrido RAW → MASTER → BUSINESS por tabla, con el archivo de origen y los objetos publicados
- Cada campo con su nombre en la fuente, su transformación y si se cifra

**HU-10 · Glosario**
- 40 términos con definición, dominio, sinónimos y campos donde aparecen (`config/glosario.yaml`)
- Búsqueda sin tildes ni mayúsculas, filtro por dominio y edición solo para gobierno y admin

**HU-15 · Rendimiento**
- Las vistas de BUSINESS se leen en paralelo y quedan 10 minutos en memoria; se precargan al arrancar
- Cabecera `Server-Timing` en cada respuesta y auditoría de las que pasan de 8 s
- Prueba automatizada por sección del portal

## 3. Seguimiento · Daily Scrum

Empieza el 20 de octubre. Riesgos conocidos gracias al prototipo:

| Riesgo o impedimento | Efecto | Respuesta prevista | Estado |
|---|---|---|---|
| Sin facturación en GCP | No hay Cloud Run para publicar el portal | El portal corre en local contra DuckDB o contra BigQuery | Abierto |
| La primera carga del Resumen sobre BigQuery puede acercarse al límite de 8 s de HU-15 | Riesgo de incumplir el requisito | Lectura en paralelo y precarga al arrancar; medirlo con los 92 cortes | Abierto |
| Compromiso de 31 SP sobre una velocidad de 20 a 24 | Sprint cargado | Decidir en la Sprint Planning si HU-15 queda fuera | Abierto |

## 4. Prototipo y comentarios recibidos

La revisión del sprint es al cierre, el lunes 2 de noviembre. Antes de planificar, el prototipo
recibió estos comentarios, que ya están incorporados:

| Comentario | Cambio en el prototipo | Commit |
|---|---|---|
| «El diseño es muy apagado; hazlo más interactivo y atractivo» | Navegación con íconos, tema claro y oscuro, gráfico con tooltip y vista de tabla, y diseño móvil | `075eccc` |
| «Tiene que ser un inicio de sesión, no elegir roles» | Inicio de sesión con correo y contraseña, bloqueo por intentos, contraseña temporal y cambio obligatorio (ADR 0011) | `12d0d91` |
| «Datos de julio a septiembre, con valores y variaciones realistas, y que se sienta vivo» | Cortes diarios con ruido, tendencias e incidentes; simulación en vivo con actividad y avisos; % de reglas en PASS como indicador principal | `a5f625a` |

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
| HU-13 | Roles y módulos, campos sensibles por rol, acceso denegado auditado, inicio de sesión, contraseña temporal y bloqueo ([test_api.py](../../tests/test_api.py), [test_autenticacion.py](../../tests/test_autenticacion.py)) | [Login](../evidencias/portal/hu13-login.png), [gobierno](../evidencias/portal/hu13-validaciones-gobierno.png), [lector](../evidencias/portal/hu13-validaciones-lector.png), [acceso denegado](../evidencias/portal/hu13-auditoria-acceso-denegado.png) |
| HU-09 | Resumen con tendencia y % en PASS, fallas primero, comparación de días, corrida nueva y llegada en vivo ([test_api.py](../../tests/test_api.py), [test_vivo.py](../../tests/test_vivo.py)) | [Resumen](../evidencias/portal/hu09-resumen.png), [14 de julio](../evidencias/portal/hu09-resumen-14-julio.png), [en vivo](../evidencias/portal/hu09-actividad-en-vivo.png) |
| HU-12 | Certificación integral del día de la fuga y su historia (`test_certificacion_integral_del_dia_de_la_fuga`) | [7 de agosto](../evidencias/portal/hu04-hu07-hu12-certificacion-7-agosto.png), [30 de septiembre](../evidencias/portal/hu04-hu12-certificacion-30-septiembre.png) |
| HU-11 | Recorrido de Persona de RAW a BUSINESS (`test_linaje_de_persona_de_raw_a_business`) | [Linaje](../evidencias/portal/hu11-linaje.png), [campo cifrado](../evidencias/portal/hu06-hu11-linaje-campo-cifrado.png) |
| HU-10 | Búsqueda sin tildes, filtro por dominio y edición por rol (`test_glosario_busca_sin_tildes_y_filtra_por_dominio`, `test_solo_gobierno_y_admin_editan_el_glosario`) | [Glosario](../evidencias/portal/hu10-glosario-busqueda.png) |
| HU-15 | Cada sección en menos de 8 s y registro de las lentas (`test_cada_seccion_responde_en_menos_de_8_segundos`, `test_una_solicitud_lenta_queda_registrada_en_la_auditoria`) | [Reporte de pruebas](../evidencias/pruebas.txt) |

## 5. Sprint Retrospective

Se hace al cierre, el 2 de noviembre, con la plantilla de [plantillas.md](plantillas.md).
