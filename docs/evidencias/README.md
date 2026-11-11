# Evidencia de las historias de usuario

Lo que respalda las revisiones de los sprints ([docs/sprints](../sprints/README.md)). Todo sale
de datos sintéticos de una aseguradora ficticia.

## Datos y pruebas

Los datos cubren 92 cortes diarios, del 1 de julio al 30 de septiembre de 2026.

| Archivo | Qué muestra | Historias |
|---|---|---|
| [pipeline-local.txt](pipeline-local.txt) | Corrida completa de los 92 cortes en DuckDB: score por tabla y día, reglas fuera de OK, días de cada sello, los no certificados con su motivo y la verificación contra el manifiesto (0 diferencias en las 4 etapas) | HU-01 a HU-08, HU-14 |
| [bigquery.txt](bigquery.txt) | Los 92 cortes en el proyecto `dq-center-gabou` (sandbox): verificación contra el manifiesto con lo que quedó en BigQuery, paridad fila por fila con la corrida de DuckDB, y por historia: cargas y rechazos, incidencias, PII cifrada, reglas por nivel, sellos, hallazgos del Gate y objetos de BUSINESS | HU-01 a HU-08, HU-14 |
| [pruebas.txt](pruebas.txt) | Reporte de pytest con el nombre de cada prueba | Todas |
| [acceso-firestore.txt](acceso-firestore.txt) | 14 comprobaciones del acceso contra Firestore real: inicio de sesión, bloqueo a los 5 intentos, contraseña temporal, cambio de rol, sesiones cerradas y auditoría | HU-13 |
| [rendimiento.txt](rendimiento.txt) | Las 11 secciones del portal con la API local: en frío, en caliente, bajo carga (10 usuarios) y con la caché vencida; veredicto contra los 8 s | HU-15 |
| [rendimiento-bigquery.txt](rendimiento-bigquery.txt) | Lo mismo con la API leyendo BigQuery (sandbox, 92 cortes), con la lectura estimada antes de medir | HU-15 |
| [accesibilidad-y-e2e.txt](accesibilidad-y-e2e.txt) | Pruebas e2e con Playwright: inicio de sesión, roles, teclado y foco, nombres accesibles, contraste WCAG en claro y oscuro, móvil de 390 px, movimiento reducido y consola | HU-09, HU-13 |

El CI corre las mismas pruebas y el build de la web en cada push:
[GitHub Actions](https://github.com/GabouLC/dq-center/actions).

Para regenerarlos:

```bash
python -m dqc.pipeline --db data/dq_completo.duckdb > docs/evidencias/pipeline-local.txt
python -m pytest -v > docs/evidencias/pruebas.txt
python scripts/medir_rendimiento.py --caducidad              # rendimiento.txt (API local, unos 12 minutos)
python scripts/verificar_portal.py --arrancar                # accesibilidad-y-e2e.txt y portal/oscuro/ (unos 5 minutos)
python scripts/verificar_acceso_firestore.py                 # acceso-firestore.txt (con DQC_PROYECTO)
python scripts/evidencia_bigquery.py      # con DQC_PROYECTO; antes, python -m dqc.gcp --sandbox simular
python scripts/medir_rendimiento.py --modo gcp --caducidad   # rendimiento-bigquery.txt (estima antes; se detiene si pasa de 1 GB)
```

## Capturas del portal (`portal/`)

Las capturas se regeneran con `scripts/capturas_portal.py` sobre la corrida completa de 92 cortes
con las 51 reglas (11 de noviembre). Las de HU-09 a HU-15 respaldan la revisión del Sprint 3 ([sprint-3.md](../sprints/sprint-3.md));
las de HU-01 a HU-08 y HU-14, las de los Sprints 1 y 2.

| Captura | Historias | Qué muestra |
|---|---|---|
| [hu01-fuentes-siniestro-rechazo](portal/hu01-fuentes-siniestro-rechazo.png) | HU-01 | Cargas con problemas: el archivo del 28 de julio rechazado por estructura y su reentrega |
| [hu01-fuentes-persona-llegadas](portal/hu01-fuentes-persona-llegadas.png) | HU-01 | Volumen diario y hora de llegada de cada archivo; el del 14 de julio pasó el límite |
| [hu14-fuentes-poliza-estructura](portal/hu14-fuentes-poliza-estructura.png) | HU-14 | El salto de volumen del 20 de agosto y `canal_venta` nueva desde el 9 de septiembre |
| [hu05-contrato-dac](portal/hu05-contrato-dac.png) | HU-05 | Contrato de Persona con su clasificación DAC por campo |
| [hu06-hu11-linaje-campo-cifrado](portal/hu06-hu11-linaje-campo-cifrado.png) | HU-06, HU-11 | `NUM_DOC` de la fuente pasa a `nro_documento` con cifrado determinístico |
| [hu02-hu03-validaciones-14-julio](portal/hu02-hu03-validaciones-14-julio.png) | HU-02, HU-03 | Reglas N1, N2 y N3 del 14 de julio con su estado |
| [hu03-reglas-configurables](portal/hu03-reglas-configurables.png) | HU-03 | Catálogo de reglas editable por el administrador |
| [hu04-hu07-hu12-certificacion-7-agosto](portal/hu04-hu07-hu12-certificacion-7-agosto.png) | HU-04, HU-07, HU-12 | Siniestro no certificado por PII en claro; retenido por el Gate |
| [hu04-hu12-certificacion-30-septiembre](portal/hu04-hu12-certificacion-30-septiembre.png) | HU-04, HU-12 | Póliza bloqueada por POL-CON-03 y Vehículo certificado sin observaciones |
| [hu04-ejecuciones](portal/hu04-ejecuciones.png) | HU-04, HU-09 | Corridas del motor y lanzamiento a demanda |
| [hu09-resumen](portal/hu09-resumen.png) | HU-09 | Dashboard del 30 de septiembre: % de reglas en PASS, sellos, tendencia diaria y mapa de certificación |
| [hu09-resumen-14-julio](portal/hu09-resumen-14-julio.png) | HU-09 | Dashboard del 14 de julio: la lectura rápida explica en una frase que Persona quedó retenida por llegar tarde |
| [hu09-recorrido-viaje-datos](portal/hu09-recorrido-viaje-datos.png) | HU-09 | Último paso del recorrido de bienvenida: cómo viajan los datos de RAW a BUSINESS |
| [hu09-actividad-en-vivo](portal/hu09-actividad-en-vivo.png) · [panel](portal/hu09-panel-en-vivo.png) | HU-09 | Archivos del 25 de septiembre llegando en vivo; el portal se actualiza solo |
| [hu11-linaje](portal/hu11-linaje.png) | HU-11 | Recorrido RAW → MASTER → BUSINESS de Persona |
| [hu10-glosario-busqueda](portal/hu10-glosario-busqueda.png) | HU-10 | Búsqueda «dni» en el glosario |
| [hu13-login](portal/hu13-login.png) · [error](portal/hu13-login-error.png) | HU-13 | Inicio de sesión y mensaje único ante credenciales inválidas |
| [hu13-alta-clave-temporal](portal/hu13-alta-clave-temporal.png) | HU-13 | Alta de usuario con contraseña temporal de un solo uso |
| [hu13-cambio-clave-obligatorio](portal/hu13-cambio-clave-obligatorio.png) | HU-13 | Cambio obligatorio de la contraseña temporal |
| [hu13-validaciones-gobierno](portal/hu13-validaciones-gobierno.png) · [lector](portal/hu13-validaciones-lector.png) | HU-13 | El mismo registro: gobierno ve los campos sensibles, el lector no |
| [hu13-auditoria-acceso-denegado](portal/hu13-auditoria-acceso-denegado.png) | HU-13 | Un lector intentó abrir Usuarios: 403 auditado |
| [hu13-usuarios](portal/hu13-usuarios.png) · [hu13-hu15-auditoria](portal/hu13-hu15-auditoria.png) | HU-13, HU-15 | Usuarios con estado de cuenta; auditoría de sesiones y accesos |

### Tema oscuro (`portal/oscuro/`)

Una captura por sección del portal en tema oscuro, a 1440 px, con la sesión del administrador y el
7 de agosto de 2026. Las genera `scripts/verificar_portal.py` junto con la comprobación de contraste;
no son capturas de una historia sino de la revisión del tema oscuro (HU-09).

| Captura | Sección |
|---|---|
| [resumen](portal/oscuro/resumen.png) · [recorrido-guiado](portal/oscuro/recorrido-guiado.png) | Resumen y su recorrido de bienvenida |
| [validaciones](portal/oscuro/validaciones.png) · [validaciones-detalle](portal/oscuro/validaciones-detalle.png) | Validaciones y el detalle de una regla |
| [certificacion](portal/oscuro/certificacion.png) | Certificación |
| [fuentes](portal/oscuro/fuentes.png) · [contratos](portal/oscuro/contratos.png) · [linaje](portal/oscuro/linaje.png) · [glosario](portal/oscuro/glosario.png) | Origen y gobierno |
| [reglas](portal/oscuro/reglas.png) · [ejecuciones](portal/oscuro/ejecuciones.png) · [usuarios](portal/oscuro/usuarios.png) · [auditoria](portal/oscuro/auditoria.png) | Administración |
| [entrar](portal/oscuro/entrar.png) · [clave](portal/oscuro/clave.png) | Inicio de sesión y cambio de contraseña |
