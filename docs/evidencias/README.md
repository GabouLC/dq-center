# Evidencia de las historias de usuario

Lo que respalda las revisiones de los sprints ([docs/sprints](../sprints/README.md)). Todo sale
de datos sintéticos de una aseguradora ficticia.

## Datos y pruebas

| Archivo | Qué muestra | Historias |
|---|---|---|
| [pipeline-local.txt](pipeline-local.txt) | Corrida completa de los 6 cortes en DuckDB: score por tabla, reglas fuera de OK, matriz de certificación y verificación contra el manifiesto (0 diferencias en las 4 etapas) | HU-01 a HU-08, HU-14 |
| [bigquery.txt](bigquery.txt) | Consultas al proyecto `dq-center-gabou` (sandbox): cargas y rechazos en RAW, incidencias de homologación, PII cifrada en MASTER, reglas por nivel, certificaciones, hallazgos del Gate y objetos de BUSINESS | HU-01 a HU-08, HU-14 |
| [pruebas.txt](pruebas.txt) | Reporte de pytest con el nombre de cada prueba | Todas |

El CI corre las mismas pruebas y el build de la web en cada push:
[GitHub Actions](https://github.com/GabouLC/dq-center/actions).

Para regenerarlos:

```bash
python -m dqc.pipeline > docs/evidencias/pipeline-local.txt
python -m pytest -v > docs/evidencias/pruebas.txt
```

## Capturas del portal (`portal/`)

| Captura | Historias | Qué muestra |
|---|---|---|
| [hu01-fuentes-siniestro-rechazo](portal/hu01-fuentes-siniestro-rechazo.png) | HU-01 | Cargas por corte; la de julio rechazada por estructura y su reentrega |
| [hu14-fuentes-poliza-estructura](portal/hu14-fuentes-poliza-estructura.png) | HU-14 | Estructura de MASTER corte a corte; `canal_venta` aparece en septiembre |
| [hu05-contrato-dac](portal/hu05-contrato-dac.png) | HU-05 | Contrato de Persona con su clasificación DAC por campo |
| [hu06-hu11-linaje-campo-cifrado](portal/hu06-hu11-linaje-campo-cifrado.png) | HU-06, HU-11 | `NUM_DOC` de la fuente pasa a `nro_documento` con cifrado determinístico |
| [hu02-hu03-validaciones-julio](portal/hu02-hu03-validaciones-julio.png) | HU-02, HU-03 | Reglas N1, N2 y N3 de julio con su estado |
| [hu03-reglas-configurables](portal/hu03-reglas-configurables.png) | HU-03 | Catálogo de reglas editable por el administrador |
| [hu04-hu07-hu12-certificacion-junio](portal/hu04-hu07-hu12-certificacion-junio.png) | HU-04, HU-07, HU-12 | Siniestro no certificado por PII en claro; retenido por el Gate |
| [hu04-hu12-certificacion-septiembre](portal/hu04-hu12-certificacion-septiembre.png) | HU-04, HU-12 | Sellos de septiembre con calidad, privacidad y trazabilidad |
| [hu04-ejecuciones](portal/hu04-ejecuciones.png) | HU-04, HU-09 | Corridas del motor y lanzamiento a demanda |
| [hu09-resumen](portal/hu09-resumen.png) | HU-09 | Dashboard del último corte |
| [hu09-resumen-julio](portal/hu09-resumen-julio.png) | HU-09 | Dashboard de julio, con fallas y una tabla no certificada |
| [hu11-linaje](portal/hu11-linaje.png) | HU-11 | Recorrido RAW → MASTER → BUSINESS de Persona |
| [hu10-glosario-busqueda](portal/hu10-glosario-busqueda.png) | HU-10 | Búsqueda «dni» en el glosario |
| [hu13-login](portal/hu13-login.png) · [error](portal/hu13-login-error.png) | HU-13 | Inicio de sesión y mensaje único ante credenciales inválidas |
| [hu13-alta-clave-temporal](portal/hu13-alta-clave-temporal.png) | HU-13 | Alta de usuario con contraseña temporal de un solo uso |
| [hu13-cambio-clave-obligatorio](portal/hu13-cambio-clave-obligatorio.png) | HU-13 | Cambio obligatorio de la contraseña temporal |
| [hu13-validaciones-gobierno](portal/hu13-validaciones-gobierno.png) · [lector](portal/hu13-validaciones-lector.png) | HU-13 | El mismo registro: gobierno ve los campos sensibles, el lector no |
| [hu13-auditoria-acceso-denegado](portal/hu13-auditoria-acceso-denegado.png) | HU-13 | Un lector intentó abrir Usuarios: 403 auditado |
| [hu13-usuarios](portal/hu13-usuarios.png) · [hu13-hu15-auditoria](portal/hu13-hu15-auditoria.png) | HU-13, HU-15 | Usuarios con estado de cuenta; auditoría de sesiones y accesos |
