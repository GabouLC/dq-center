# 0012 · Cortes diarios sintéticos de julio a septiembre

**Estado:** aceptada (2026-10-15). Amplía el ADR 0009 y reemplaza el modelo de seis cortes
mensuales del brief.

## Contexto

Los datos sintéticos tenían seis cortes mensuales, de abril a septiembre de 2026. Con seis
puntos no se ven tendencias ni la puntualidad de cada archivo, y casi todo salía igual de un
corte a otro. La revisión del Sprint 1 lo señaló, y los comentarios al prototipo del portal
pidieron datos «realistas, con variaciones, que se sientan vivos».

## Decisión

Un corte por día del 1 de julio al 30 de septiembre de 2026: 92 cortes (`CORTES` en
`dqc.modelo`). El generador (`dqc.datagen.generador`, semilla 20260930) arma una historia:

- **Ruido de cada día:** errores pasajeros con más peso los lunes y algún «mal día».
- **Defectos persistentes y su corrección:** por ejemplo, campañas de cobranza y de contactos,
  y la limpieza de vehículos.
- **Tendencias:** una regla de Póliza que se degrada y otras que mejoran.
- **Incidentes con fecha fija:**

  | Fecha | Incidente |
  |---|---|
  | 14 de julio | Archivo tarde |
  | 22 de julio | Documentos nulos |
  | 28 de julio | Archivo rechazado |
  | 7 y 8 de agosto | Fuga de PII |
  | 20 de agosto | Reproceso de pólizas |
  | 9 de septiembre | Columna nueva `canal_venta` |

Cada error sembrado queda en el manifiesto, como antes (ADR 0010).

## Consecuencias

- Una corrida completa produce 92 × 48 evaluaciones y 460 sellos. En local tarda unos
  minutos; en el sandbox de BigQuery, unas 9 horas (ADR 0014).
- Las pruebas usan 22 días elegidos y una cartera a escala 0,25 (`tests/conftest.py`), y
  corren en menos de un minuto.
- El brief (`docs/brief.md`) queda como documento histórico del modelo mensual.
