# dq-center

Portal de calidad de datos para una aseguradora ficticia. Datos 100 % sintéticos.

## Reglas del proyecto

- No usar conectores corporativos (Interseguro: bases, Gmail, Drive, Jira, Confluence,
  logging, Freshservice). Nada de datos, nombres de tablas ni código de la empresa.
- Cuentas: GitHub `GabouLC`, GCP `gabrielomchos88@gmail.com`.
- Especificación: [docs/brief.md](docs/brief.md). Catálogo de reglas:
  [config/reglas_iniciales.yaml](config/reglas_iniciales.yaml).

## Etapas

infra → datos sintéticos y manifiesto → reglas en Firestore → motor → API → web →
deploy → README. Un commit por etapa. Antes de cada etapa, decir qué se va a hacer.
