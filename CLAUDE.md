# dq-center

Smart-DQ: portal de calidad y privacidad de datos para una aseguradora ficticia.
Proyecto del curso Diseño e Implementación de Sistemas (USMP 2026-II, Grupo 6).
Datos 100 % sintéticos.

## Qué NO es

- No es un sistema en producción ni usa datos reales: la aseguradora es ficticia (ADR 0009).
- No está desplegado en Cloud Run. El diseño lo prevé (ADR 0003), pero sin facturación todo corre
  en local o en el sandbox de BigQuery más Firestore (ADR 0008; README, «Despliegue en Cloud Run»).
- No usa Cloud Composer, Dataplex ni API Gateway (ADR 0003, 0004 y 0005).
- No es el lugar para cambiar reglas, umbrales ni severidades: las propuestas van a
  [docs/auditoria-reglas.md](docs/auditoria-reglas.md).

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

Qué hace cada paso al desplegar y dónde se cumple cada HU:
[docs/guia-despliegue-y-trazabilidad.md](docs/guia-despliegue-y-trazabilidad.md).

## Cómo saber que algo funciona

- Siempre: `.venv/Scripts/python -m pytest -q` (127 passed al 27/10/2026) y `cd web && npm run build`
  (`✓ built`). Es lo mismo que corre el CI en cada pull request.
- Si tocaste el pipeline o el motor: corre `dqc.pipeline` sobre un `data/` limpio y compara con
  `docs/evidencias/pipeline-local.txt`.
- Si tocaste el portal: `scripts/capturas_portal.py` y revisa `docs/evidencias/portal/`.
- Si tocaste el SQL de BigQuery: `scripts/evidencia_bigquery.py` (paridad con DuckDB).
- No digas «listo» sin haber corrido las pruebas y el build.

## Lo que aprendimos

Cada vez que se resuelva un error raro, agrega una línea: qué pasó y cómo se arregló.

- `Could not set lock on file "data/dq.duckdb"`: la API tiene la base abierta. Detenla y repite.
- Las tablas del sandbox de BigQuery vencen a los 60 días: antes de una demo tardía, vuelve a
  cargar con `simular` (unas 9 h). Si la carga se corta, se reanuda con `--desde` (ADR 0014).
- Las capturas usan sus propios puertos (8001 y 5174) para no chocar con una demo abierta.
- En PowerShell 5.1 no existe `&&`: separa los comandos con `;`.
