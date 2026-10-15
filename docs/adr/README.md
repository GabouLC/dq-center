# Decisiones de arquitectura (ADR)

Registro de las decisiones de implementación de dq-center, en formato Nygard.
Complementan el *Documento de Arquitectura v1.0* del Grupo 6 (USMP 2026-II):
cuando una decisión de aquí reemplaza o ajusta un ADR de ese documento, lo dice.

| ADR | Decisión | Relación con el documento |
|---|---|---|
| [0001](0001-alcance.md) | El Product Backlog define el alcance; el documento de arquitectura, los principios técnicos | Nuevo |
| [0002](0002-stack.md) | Python + FastAPI + Firestore en vez de Node/Hapi + PostgreSQL | Reemplaza ADR-08 y la tecnología de la API |
| [0003](0003-orquestacion.md) | Cloud Run Job + Cloud Scheduler en vez de Cloud Composer | Ajusta ADR-06 |
| [0004](0004-evaluacion-sql.md) | SQL generado por regla para todas las tablas, sin Dataplex | Reemplaza ADR-03 |
| [0005](0005-sin-api-gateway.md) | Sin API Gateway: CORS y verificación del token en la API | Ajusta ADR-07 |
| [0006](0006-capas-y-privacy-gate.md) | Capas RAW → MASTER → BUSINESS y Privacy Gate con AEAD | Nuevo (backlog HU-06, HU-08, HU-14) |
| [0007](0007-pii-solo-en-memoria.md) | El motor descifra solo lo que cada regla usa, y solo en memoria | Ajusta la sección 9.3 |
| [0008](0008-sandbox.md) | En el sandbox, tablas agrupadas por corte en vez de particionadas | Nuevo |
| [0009](0009-datos-sinteticos.md) | Aseguradora ficticia y datos 100 % sintéticos | Nuevo |
| [0010](0010-pruebas.md) | El mismo SQL en DuckDB y un manifiesto de errores sembrados | Ajusta ADR-10 |

Principios del documento que se mantienen tal cual: publicar solo resultados
completos (ADR-04), guardianes de acceso a datos (ADR-09), vistas de contrato
como interfaz del portal (ADR-05) y web en MVVM con Vue 3 y Pinia (ADR-07).
