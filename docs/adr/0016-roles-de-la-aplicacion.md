# 0016 · Roles de la aplicación, no IAM de GCP, para los campos Sensibles

**Estado:** aceptada (2026-11-11). Ajusta el criterio a) de la HU-13.

## Contexto

La HU-13 pide asociar los campos Sensibles a un rol o a un grupo de IAM («IAM simulado»). La API
consulta BigQuery con una sola cuenta de servicio, así que IAM no distingue quién abre cada
pantalla del portal. La API sí lo sabe, porque autentica a cada persona (ADR 0011).

## Decisión

Administrador, gobierno y lector son **roles de la aplicación** (`usuarios` en Firestore, o
`data/config_local.json` en local). La API los traduce a permisos (`PERMISOS` en `dqc.api.app`) y
enmascara cada campo según su clasificación DAC (`vistas.enmascarar` y `vistas.enmascarar_valores`):

- SENSIBLE_CIFRADO nunca sale en claro, para nadie.
- SENSIBLE solo lo ven gobierno y administrador.
- Un campo sin clasificar se trata como SENSIBLE hasta que el contrato lo clasifique.

Cada acceso denegado o restringido queda en la auditoría. No hay grupos de IAM, ACL por dataset ni
etiquetas de política.

## Consecuencias

- Los criterios b), c) y d) de la HU-13 se cumplen en la API. El a) se cumple por categoría DAC y
  por rol de la aplicación, no por grupos de IAM.
- Quien consulte BigQuery fuera del portal no pasa por estos roles: el acceso directo a los
  datasets lo controla IAM del proyecto, que aquí no se modela.
- Con facturación y una cuenta de servicio por rol, las etiquetas de política por columna de
  BigQuery serían el paso siguiente.
