# 0002 · Python + FastAPI + Firestore

**Estado:** aceptada (2026-10-15). Reemplaza el ADR-08 del Documento de Arquitectura
y la elección de Node.js 24 + Hapi + TypeORM para la API.

## Contexto

El documento propone la API en Node.js con Hapi y los usuarios, roles y auditoría
en PostgreSQL sobre Cloud SQL. Cloud SQL más pequeño cuesta unos USD 25 a 30 al
mes aunque nadie lo use, y exige facturación activa. El motor ya está en Python,
como pide el mismo documento. El piloto corre en un sandbox sin costo comercial.

## Decisión

La API se escribe en Python con FastAPI y comparte el paquete `dqc` con el motor:
las reglas, la puntuación y la validación de SQL son el mismo código en los dos.
Usuarios, roles, reglas, contratos, glosario y auditoría se guardan en Firestore
en modo nativo, que tiene capa gratuita y no necesita una base encendida.

## Consecuencias

- Costo fijo cero; el único servicio con cargo por uso es BigQuery, dentro de su capa gratuita.
- Un solo lenguaje en el backend: menos piezas para un equipo de cinco.
- Se pierde la integridad referencial de PostgreSQL. Se compensa validando en la
  API antes de escribir y guardando quién y cuándo cambió cada documento.
