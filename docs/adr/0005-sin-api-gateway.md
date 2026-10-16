# 0005 · Sin API Gateway

**Estado:** aceptada (2026-10-15). Ajusta el ADR-07 del Documento de Arquitectura.

## Contexto

El documento pone la API en un Cloud Run privado detrás de API Gateway, que exige
clave de API y aplica CORS. API Gateway agrega un servicio más que configurar y
mantener, y una clave de API embebida en una SPA no es un secreto.

## Decisión

La API corre en Cloud Run con acceso público, pero cada ruta de negocio exige un
token de sesión válido (propio o de Firebase, ADR 0011), y el rol se resuelve en Firestore. CORS
solo admite el origen del portal. Las rutas usan el prefijo `/api/v1` y hay
sondas `/health/liveness` y `/health/readiness`, como en el documento.

## Consecuencias

- La seguridad efectiva es la misma: sin token válido y rol asignado, la API responde 401 o 403.
- Una pieza menos que operar y nada de costo extra.
- Se pierde el límite de tasa del gateway. Lo reemplaza el tope de instancias de
  Cloud Run, que responde 429 cuando se alcanza.
