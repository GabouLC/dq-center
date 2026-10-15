# 0006 · Capas RAW → MASTER → BUSINESS y Privacy Gate con AEAD

**Estado:** aceptada (2026-10-15). Implementa HU-01, HU-05, HU-06, HU-08 y HU-14.

## Contexto

El backlog pide conservar los datos en bruto (RAW), homologarlos a un modelo
estándar (MASTER) y exponer solo lo certificado (BUSINESS). También pide que
ningún campo de PII quede almacenado en texto plano.

## Decisión

- **RAW** (`dq_raw`): cada CSV se valida (encabezado, número de campos, UTF-8) y
  se guarda sin tocar los valores. Un archivo inválido se rechaza y queda en
  `registro_cargas` con su motivo.
- **MASTER** (`dq_master`): `config/homologacion.yaml` renombra las columnas y
  convierte los tipos, sin corregir valores. Un registro con un valor no
  convertible va a `incidencias_homologacion` y no pasa.
- **Privacy Gate:** en la misma consulta de homologación se cifran los campos que el
  contrato clasifica como `SENSIBLE_CIFRADO`:
  - con cifrado **determinístico** (`DETERMINISTIC_ENCRYPT`) los que hay que
    comparar, como el número de documento, porque la unicidad y los cruces
    siguen funcionando;
  - con cifrado **aleatorio** (`AEAD.ENCRYPT`) el resto.

  El AAD es `tabla.campo`, así que un valor cifrado no sirve en otra columna.
- **Llaves:** los keysets viven en `dq_seguridad.llaves`, un dataset que solo lee
  el flujo. Ese es el "KMS simulado" del caso de negocio. Con facturación activa,
  los keysets se envuelven con Cloud KMS (`KEYS.KEYSET_CHAIN`) sin cambiar el resto.
- **BUSINESS** (`dq_business`): solo recibe cortes certificados (Sprint 2).

## Consecuencias

- RAW sí contiene PII en claro: es la zona de aterrizaje y debe tener el acceso
  más restringido de todos los datasets.
- El motor necesita leer las llaves para validar formatos de PII (ver ADR 0007).
