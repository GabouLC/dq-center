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

El CI corre las mismas pruebas y el build de la web en cada push:
[GitHub Actions](https://github.com/GabouLC/dq-center/actions).

Para regenerarlos:

```bash
python -m dqc.pipeline --db data/dq_completo.duckdb > docs/evidencias/pipeline-local.txt
python -m pytest -v > docs/evidencias/pruebas.txt
python scripts/evidencia_bigquery.py      # con DQC_PROYECTO; antes, python -m dqc.gcp --sandbox simular
```

## Capturas del portal (`portal/`)

Las capturas de HU-09 a HU-15 muestran el prototipo adelantado del portal: son evidencia
preliminar hasta la revisión del Sprint 3. Las de HU-01 a HU-08 y HU-14 respaldan historias ya
aceptadas en los Sprints 1 y 2.

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
| [hu09-resumen-14-julio](portal/hu09-resumen-14-julio.png) | HU-09 | Dashboard del 14 de julio, con Persona no certificada |
| [hu09-actividad-en-vivo](portal/hu09-actividad-en-vivo.png) · [panel](portal/hu09-panel-en-vivo.png) | HU-09 | Archivos del 25 de septiembre llegando en vivo; el portal se actualiza solo |
| [hu11-linaje](portal/hu11-linaje.png) | HU-11 | Recorrido RAW → MASTER → BUSINESS de Persona |
| [hu10-glosario-busqueda](portal/hu10-glosario-busqueda.png) | HU-10 | Búsqueda «dni» en el glosario |
| [hu13-login](portal/hu13-login.png) · [error](portal/hu13-login-error.png) | HU-13 | Inicio de sesión y mensaje único ante credenciales inválidas |
| [hu13-alta-clave-temporal](portal/hu13-alta-clave-temporal.png) | HU-13 | Alta de usuario con contraseña temporal de un solo uso |
| [hu13-cambio-clave-obligatorio](portal/hu13-cambio-clave-obligatorio.png) | HU-13 | Cambio obligatorio de la contraseña temporal |
| [hu13-validaciones-gobierno](portal/hu13-validaciones-gobierno.png) · [lector](portal/hu13-validaciones-lector.png) | HU-13 | El mismo registro: gobierno ve los campos sensibles, el lector no |
| [hu13-auditoria-acceso-denegado](portal/hu13-auditoria-acceso-denegado.png) | HU-13 | Un lector intentó abrir Usuarios: 403 auditado |
| [hu13-usuarios](portal/hu13-usuarios.png) · [hu13-hu15-auditoria](portal/hu13-hu15-auditoria.png) | HU-13, HU-15 | Usuarios con estado de cuenta; auditoría de sesiones y accesos |
