# dq-center

Smart-DQ: portal de calidad y privacidad de datos para una aseguradora ficticia.
Proyecto del curso Diseño e Implementación de Sistemas (USMP 2026-II, Grupo 6).
Datos 100 % sintéticos.

## Reglas del proyecto

- No usar conectores corporativos (bases, Gmail, Drive, Jira, Confluence, logging,
  Freshservice). Nada de datos, nombres de tablas ni código de ninguna empresa. El Jira del
  curso (SDGDCYP) se actualiza solo con `scripts/jira_sync.py`, nunca con un conector.
- Cuentas: GitHub `GabouLC`, GCP `gabrielomchos88@gmail.com` (proyecto `dq-center-gabou`).
- Alcance: issues HU-01 a HU-15 (Product Backlog del curso). Decisiones: [docs/adr/](docs/adr/).
- Una rama y un pull request por historia, vinculado a su issue y revisado por otro integrante;
  cerrar el issue cuando sus criterios tengan prueba.

## Estructura

- `config/`: reglas (`reglas_iniciales.yaml`), contratos con clasificación DAC
  (`contratos.yaml`) y mapeo de homologación de cada fuente (`homologacion.yaml`).
- `src/dqc/datagen`: generador de datos y zona de aterrizaje (CSV + `entregas.json` + manifiesto).
- `src/dqc/pipeline`: ingesta a RAW, homologación a MASTER con el Privacy Gate y el flujo por corte.
- `src/dqc/motor`: reglas, SQL por tipo de regla y puntuación.
- `src/dqc/plataforma`: DuckDB (local y pruebas) y BigQuery, con la misma interfaz.
- `src/dqc/gcp`: Firestore y la CLI de GCP.

## Comandos

Paso a paso desde un clon limpio, con comprobaciones: [AGENTS.md](AGENTS.md).

```bash
.venv/Scripts/python -m dqc.datagen                       # genera data/landing y el manifiesto
.venv/Scripts/python -m dqc.pipeline --db data/dq.duckdb --hasta 2026-09-24  # 86 cortes (1 jul–24 set); del 25 al 30 llegan en vivo
.venv/Scripts/python -m dqc.api                           # API local (cuentas *@demo.local, clave SmartDQ-2026)
cd web && npm run dev                                     # portal en http://localhost:5173
.venv/Scripts/python -m pytest -q                         # pruebas (sin GCP)
DQC_PROYECTO=dq-center-gabou .venv/Scripts/python -m dqc.gcp --sandbox simular   # en BigQuery (unas 9 h)
DQC_PROYECTO=dq-center-gabou .venv/Scripts/python -m dqc.gcp --sandbox simular --desde 2026-09-08  # reanuda
DQC_PROYECTO=dq-center-gabou .venv/Scripts/python scripts/evidencia_bigquery.py  # evidencia y paridad
.venv/Scripts/python scripts/jira_sync.py [--aplicar]       # Jira del curso (JIRA_* en el entorno)
```

- `src/dqc/api`: API FastAPI. Lee solo las vistas `dq_business.v_calidad_*`; en modo local además
  corre la simulación en vivo (`vivo.py`) y las ejecuciones a demanda, así que escribe en el DuckDB:
  detenla antes de correr `dqc.pipeline`.
- `web/`: portal Vue 3 + TypeScript + Pinia.
- Capturas del portal: Playwright está en el venv (no es dependencia del proyecto).

Sin facturación en GCP: usar `--sandbox` (ver ADR 0008).
