# dq-center

Smart-DQ: portal de calidad y privacidad de datos para una aseguradora ficticia.
Proyecto del curso Diseño e Implementación de Sistemas (USMP 2026-II, Grupo 6).
Datos 100 % sintéticos.

## Reglas del proyecto

- No usar conectores corporativos (bases, Gmail, Drive, Jira, Confluence, logging,
  Freshservice). Nada de datos, nombres de tablas ni código de ninguna empresa.
- Cuentas: GitHub `GabouLC`, GCP `gabrielomchos88@gmail.com` (proyecto `dq-center-gabou`).
- Alcance: issues HU-01 a HU-15 (Product Backlog del curso). Decisiones: [docs/adr/](docs/adr/).
- Un commit por historia o etapa; cerrar el issue cuando sus criterios tengan prueba.

## Estructura

- `config/`: reglas (`reglas_iniciales.yaml`), contratos con clasificación DAC
  (`contratos.yaml`) y mapeo de homologación de cada fuente (`homologacion.yaml`).
- `src/dqc/datagen`: generador de datos y zona de aterrizaje (CSV + `entregas.json` + manifiesto).
- `src/dqc/pipeline`: ingesta a RAW, homologación a MASTER con el Privacy Gate y el flujo por corte.
- `src/dqc/motor`: reglas, SQL por tipo de regla y puntuación.
- `src/dqc/plataforma`: DuckDB (local y pruebas) y BigQuery, con la misma interfaz.
- `src/dqc/gcp`: Firestore y la CLI de GCP.

## Comandos

```bash
.venv/Scripts/python -m dqc.datagen                  # genera data/landing y el manifiesto
.venv/Scripts/python -m dqc.pipeline                 # flujo completo en DuckDB + verificación
.venv/Scripts/python -m pytest -q                    # pruebas (sin GCP)
DQC_PROYECTO=dq-center-gabou .venv/Scripts/python -m dqc.gcp --sandbox simular   # en BigQuery
```

Sin facturación en GCP: usar `--sandbox` (ver ADR 0008).
