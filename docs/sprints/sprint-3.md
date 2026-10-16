# Sprint 3 · Portal Smart-DQ

**Estado:** terminado · **Compromiso:** 23 SP (propuesta), 6 historias · **Terminado:** 23 SP,
6 historias · **Incremento:** commits [`fe181da`](https://github.com/GabouLC/dq-center/commit/fe181da)
(portal), [`075eccc`](https://github.com/GabouLC/dq-center/commit/075eccc) (rediseño) y
[`12d0d91`](https://github.com/GabouLC/dq-center/commit/12d0d91) (inicio de sesión) ·
**Milestone:** [Sprint 3](https://github.com/GabouLC/dq-center/milestone/4)

## 1. Sprint Planning

**Objetivo del sprint.** Llevar los resultados al negocio: un portal donde cada rol ve la salud
y la certificación de los datos, su linaje y su glosario, con acceso controlado y cada sección
en menos de 8 segundos.

**Capacidad.** Velocidad sugerida de 20 a 24 SP; los sprints anteriores cerraron 22 y 21. Se
comprometen 23.

**Historias priorizadas.** Los puntos son una propuesta con la escala del Sprint 1 y se
confirman con el equipo.

| # | Historia | SP | Complejidad | Rol del backlog | Responsable | Issue |
|---|---|---|---|---|---|---|
| 1 | HU-13 · Controlar el acceso a datos sensibles mediante roles | 5 | Media | Data Architect | Jesus de la Cruz | [#13](https://github.com/GabouLC/dq-center/issues/13) |
| 2 | HU-09 · Visualizar el estado de calidad de los datos | 5 | Media | Oficina de Datos | Josue Borda | [#9](https://github.com/GabouLC/dq-center/issues/9) |
| 3 | HU-12 · Consultar la certificación integral del dato | 3 | Baja-media | Data Owner | Josue Borda | [#12](https://github.com/GabouLC/dq-center/issues/12) |
| 4 | HU-11 · Consultar el linaje de los datos | 5 | Media | Oficina de Datos | Josue Borda | [#11](https://github.com/GabouLC/dq-center/issues/11) |
| 5 | HU-10 · Consultar el glosario de negocio | 2 | Baja | Negocio | Gabriel León | [#10](https://github.com/GabouLC/dq-center/issues/10) |
| 6 | HU-15 · Garantizar el tiempo de carga del portal | 3 | Baja-media | Negocio | Josue Borda | [#15](https://github.com/GabouLC/dq-center/issues/15) |

**Por qué este orden.**

- HU-13 va primero porque toda pantalla del portal necesita saber quién entra y qué puede ver.
- HU-09 es el mayor valor para el negocio: responde «¿puedo confiar en los datos de este corte?».
- HU-12 reutiliza la certificación del Sprint 2 y la hace visible por tabla.
- HU-11 explica de dónde sale cada campo y por qué una tabla quedó retenida.
- HU-10 es la más simple y no bloquea a ninguna otra.
- HU-15 cierra el sprint: se mide sobre todas las pantallas ya construidas.

**Fuera del sprint.** El despliegue en Cloud Run, que depende de la facturación de GCP.

## 2. Sprint Backlog

**Base del portal**
- [x] API FastAPI con prefijo `/api/v1`, sondas `/health` y errores con el formato del documento de arquitectura (`src/dqc/api/app.py`)
- [x] Web Vue 3 + TypeScript + Pinia en MVVM, con la línea de cortes compartida por los módulos (`web/`)
- [x] La API lee solo las vistas de contrato de BUSINESS (`src/dqc/api/datos.py`)

**HU-13 · Acceso por rol**
- [x] Roles admin, gobierno y lector, con permisos por módulo (`PERMISOS` y `MODULOS`)
- [x] Campos SENSIBLE ocultos para el lector; SENSIBLE_CIFRADO siempre ocultos
- [x] Auditoría de accesos denegados y de campos ocultos
- [x] Inicio de sesión con correo y contraseña, bloqueo por intentos y contraseña temporal (`src/dqc/api/autenticacion.py`, ADR 0011)
- [x] Administración de usuarios: alta, cambio de rol, restablecer contraseña y quitar acceso

**HU-09 · Dashboard**
- [x] Resumen: score por corte, tendencia, porcentaje de reglas en PASS y mapa de calor por tabla y dimensión
- [x] Validaciones: reglas del corte con las fallas primero, filtros y detalle con los registros fallidos
- [x] Comparación entre dos cortes, con lo que empeoró primero
- [x] Ejecuciones: lanzar una corrida desde el portal y ver su resultado

**HU-12 · Certificación integral**
- [x] Sello por tabla con calidad por nivel, privacidad (campos cifrados y hallazgos) y trazabilidad (corrida, versiones, objeto en BUSINESS)
- [x] Historia de los sellos de los 6 cortes y enlace al linaje

**HU-11 · Linaje**
- [x] Recorrido RAW → MASTER → BUSINESS por tabla, con el archivo de origen y los objetos publicados
- [x] Cada campo con su nombre en la fuente, su transformación y si se cifra

**HU-10 · Glosario**
- [x] 40 términos con definición, dominio, sinónimos y campos donde aparecen (`config/glosario.yaml`)
- [x] Búsqueda sin tildes ni mayúsculas, filtro por dominio y edición solo para gobierno y admin

**HU-15 · Rendimiento**
- [x] Las vistas de BUSINESS se leen en paralelo y quedan 10 minutos en memoria; se precargan al arrancar
- [x] Cabecera `Server-Timing` en cada respuesta y auditoría de las que pasan de 8 s
- [x] Prueba automatizada por sección del portal

## 3. Seguimiento · Daily Scrum

**Impedimentos registrados**

| Impedimento | Efecto | Resolución | Estado |
|---|---|---|---|
| Sin facturación en GCP | No hay Cloud Run para publicar el portal | El portal corre en local contra DuckDB o contra BigQuery | Abierto |
| La primera carga del Resumen sobre BigQuery tardaba 7.5 s, cerca del límite de HU-15 | Riesgo de incumplir el requisito | Lectura en paralelo y precarga al arrancar: menos de 6 s en frío y 0.01 s después | Resuelto |
| La API y las pruebas abrían el mismo archivo DuckDB | Las pruebas fallaban con la API levantada | Las piezas compartidas pasaron a `src/dqc/api/servicios.py` | Resuelto |
| Una prueba del motor fallaba al azar: el correo cifrado podía contener el byte de «@» | CI intermitente | La prueba verifica que el valor no tenga forma de correo | Resuelto |

**Burndown.** El sprint tuvo tres integraciones (`fe181da`, `075eccc`, `12d0d91`); la línea
diaria se registra con [plantillas.md](plantillas.md). Resultado: 23 de 23 SP, sin arrastre.

**Dailies.** Se registran con el acta de [plantillas.md](plantillas.md).

## 4. Sprint Review e Incremento

**Incremento.** El Portal Smart-DQ con 11 módulos y tres roles. Para reproducirlo:

```bash
python -m dqc.api               # API en http://127.0.0.1:8000
cd web && npm run dev           # portal en http://localhost:5173
```

Cuentas de demostración: `admin@demo.local`, `gobierno@demo.local` y `lector@demo.local`, con la
contraseña `SmartDQ-2026`.

**Resultado:** 6 de 6 historias aceptadas.

**Comentarios recibidos en la revisión y cambios que generaron**

| Comentario | Cambio | Commit |
|---|---|---|
| «El diseño es muy apagado; hazlo más interactivo y atractivo» | Navegación con íconos, tema claro y oscuro, línea de cortes, gráfico con tooltip y vista de tabla, y diseño móvil | `075eccc` |
| «Tiene que ser un inicio de sesión, no elegir roles» | Inicio de sesión con correo y contraseña, bloqueo por intentos, contraseña temporal y cambio obligatorio (ADR 0011) | `12d0d91` |

### HU-13 · Controlar el acceso a datos sensibles mediante roles

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Un campo Sensible queda asociado a los roles autorizados | `test_cada_rol_ve_solo_sus_modulos` ([test_api.py](../../tests/test_api.py)) | Permiso `ver_sensibles` solo para gobierno y admin |
| Un usuario con el rol autorizado ve el campo | `test_campos_sensibles_ocultos_para_el_lector_y_visibles_para_gobierno` | [Gobierno](../evidencias/portal/hu13-validaciones-gobierno.png): ve `fecha_nacimiento` y `sexo` |
| Un usuario sin el rol autorizado no lo ve | `test_campos_sensibles_ocultos_para_el_lector_y_visibles_para_gobierno`, `test_un_lector_no_puede_administrar` | [Lector](../evidencias/portal/hu13-validaciones-lector.png): *restringido* y aviso de campos ocultos |
| Un acceso denegado queda registrado | `test_cuenta_sin_rol_responde_403_y_queda_auditada`, `test_un_lector_no_puede_administrar` | [Auditoría › Acceso denegado](../evidencias/portal/hu13-auditoria-acceso-denegado.png) |
| Inicio de sesión real (alcance agregado en la revisión) | `test_inicio_de_sesion_con_correo_y_contrasena`, `test_el_error_de_inicio_no_dice_si_la_cuenta_existe`, `test_alta_con_contrasena_temporal_que_obliga_a_cambiarla`, `test_restablecer_la_contrasena_cierra_las_sesiones_abiertas` y las 7 de [test_autenticacion.py](../../tests/test_autenticacion.py) | [Login](../evidencias/portal/hu13-login.png), [error](../evidencias/portal/hu13-login-error.png), [alta con clave temporal](../evidencias/portal/hu13-alta-clave-temporal.png), [cambio obligatorio](../evidencias/portal/hu13-cambio-clave-obligatorio.png) |

### HU-09 · Visualizar el estado de calidad de los datos

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Con ejecuciones, el dashboard muestra el estado de las reglas | `test_resumen_muestra_tendencia_pass_y_certificacion` ([test_api.py](../../tests/test_api.py)) | [Resumen](../evidencias/portal/hu09-resumen.png) |
| Se identifican las reglas en PASS | `test_resumen_muestra_tendencia_pass_y_certificacion` (porcentaje en PASS) | [Validaciones](../evidencias/portal/hu02-hu03-validaciones-julio.png): chips PASS |
| Se identifican las reglas en FAIL | `test_validaciones_de_un_corte_empiezan_por_las_fallas`, `test_comparar_cortes_muestra_primero_lo_que_empeoro` | [Resumen de julio](../evidencias/portal/hu09-resumen-julio.png): fallas y tablas no certificadas |
| Una ejecución nueva se refleja en el dashboard | `test_admin_lanza_una_corrida_y_aparece_en_el_portal` | [Ejecuciones](../evidencias/portal/hu04-ejecuciones.png) |

### HU-12 · Consultar la certificación integral del dato

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Se ve si el conjunto está certificado o no | `test_certificacion_integral_de_junio` ([test_api.py](../../tests/test_api.py)) | [Certificación de junio](../evidencias/portal/hu04-hu07-hu12-certificacion-junio.png) |
| Con reglas fallidas, se ve que no está certificado y sus observaciones | `test_certificacion_integral_de_junio` (historia: Persona en julio *No certificado*) | Historia de los sellos y *Con observación* en cada tabla |
| Los campos PII muestran su protección | `test_certificacion_integral_de_junio` (todos los campos cifrados de Persona protegidos) | Columna *Privacidad* del sello de Persona |
| Desde la certificación se llega al linaje y a los resultados de calidad | `test_certificacion_integral_de_junio` (objeto en BUSINESS) | Enlace *Ver su linaje* y bloque *Trazabilidad* ([septiembre](../evidencias/portal/hu04-hu12-certificacion-septiembre.png)) |

### HU-11 · Consultar el linaje de los datos

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Se muestra el recorrido entre capas | `test_linaje_de_persona_de_raw_a_business` ([test_api.py](../../tests/test_api.py)) | [Linaje de Persona](../evidencias/portal/hu11-linaje.png) |
| Un dato de RAW muestra su paso a MASTER | `test_linaje_de_persona_de_raw_a_business` (`NUM_DOC` → `nro_documento`) | [Campo cifrado](../evidencias/portal/hu06-hu11-linaje-campo-cifrado.png) |
| Un dato certificado muestra su exposición en BUSINESS | `test_linaje_de_persona_de_raw_a_business` (nodos BUSINESS y cortes retenidos) | Nodos `p_persona` y `v_persona` |
| Se ven las transformaciones de cada etapa | `test_linaje_de_persona_de_raw_a_business` (cifrado determinístico) | Detalle del campo con su transformación |

### HU-10 · Consultar el glosario de negocio

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Se ven los términos registrados | `test_glosario_busca_sin_tildes_y_filtra_por_dominio` ([test_api.py](../../tests/test_api.py)) | [Glosario](../evidencias/portal/hu10-glosario-busqueda.png) |
| Un término muestra su definición | `test_glosario_busca_sin_tildes_y_filtra_por_dominio` (detalle de `prima-total`) | Ficha del término |
| La búsqueda muestra los términos coincidentes | `test_glosario_busca_sin_tildes_y_filtra_por_dominio` («poliza» encuentra «Póliza») | Búsqueda «dni» en la captura |
| Se identifica el dominio del término | `test_glosario_busca_sin_tildes_y_filtra_por_dominio` (filtro por dominio) | Chip de dominio en cada término |
| Edición solo para gobierno y admin (detalle del backlog: autoservicio) | `test_solo_gobierno_y_admin_editan_el_glosario` | |

### HU-15 · Garantizar el tiempo de carga del portal

| Criterio de aceptación | Prueba automatizada | Evidencia |
|---|---|---|
| Cualquier sección responde en menos de 8 s | `test_cada_seccion_responde_en_menos_de_8_segundos`, 8 secciones ([test_api.py](../../tests/test_api.py)) | Cabecera `Server-Timing` en cada respuesta |
| El dashboard carga dentro del límite | La misma prueba, sección `/api/v1/resumen` | En BigQuery: menos de 6 s en frío y 0.01 s con caché |
| Si se supera el límite, se registra la incidencia | `test_una_solicitud_lenta_queda_registrada_en_la_auditoria` | Evento `RENDIMIENTO_LENTO` (*Más de 8 s* en la [Auditoría](../evidencias/portal/hu13-hu15-auditoria.png)); en la demo no hubo ninguno |
| Las pruebas de rendimiento verifican el indicador | `test_cada_seccion_responde_en_menos_de_8_segundos` corre en cada push en el CI | [Reporte de pruebas](../evidencias/pruebas.txt) |

## 5. Sprint Retrospective (borrador con los hechos del sprint)

| Funcionó | Por mejorar |
|---|---|
| Revisar el portal con capturas encontró problemas que las pruebas no ven: desbordes en móvil, ejes del gráfico y textos. | El modo demo sin contraseña no cumplía la idea de control de acceso; salió en la revisión, no en la planificación. |
| Medir el tiempo en BigQuery antes de cerrar evitó incumplir HU-15. | El portal sigue sin desplegarse por la facturación. |
| Los comentarios de la revisión se resolvieron dentro del mismo sprint. | Una prueba intermitente llegó al CI. |

**Acciones propuestas:** incluir criterios de seguridad explícitos (inicio de sesión, bloqueo) en
las historias de acceso; resolver la facturación y desplegar en Cloud Run; correr la suite
varias veces seguidas antes de cerrar un sprint. Completar con la opinión del equipo usando
[plantillas.md](plantillas.md).
