# 0001 · El Product Backlog define el alcance

**Estado:** aceptada (2026-10-15)

## Contexto

El curso tiene dos documentos que describen el sistema desde ángulos distintos.
El *Product Backlog* (HU-01 a HU-15) pide un flujo por capas RAW → MASTER →
BUSINESS, tres niveles de calidad, un Quality & Privacy Gate con cifrado, glosario
y linaje. El *Documento de Arquitectura v1.0* describe una plataforma que evalúa
entidades ya cargadas, con detección por huella, Dataplex, Composer y un portal
en Node.js. No coinciden en alcance ni en tecnología.

## Decisión

Las historias de usuario del backlog son el alcance funcional: cada una es un
issue del repositorio y se cierra cuando sus criterios de aceptación tienen una
prueba automática. Del documento de arquitectura se adoptan los principios que
no dependen de servicios caros: el motor como tubería de etapas, publicar solo
resultados completos y sellados, guardianes de acceso a datos, vistas de
contrato, API versionada con sondas de salud y auditoría de accesos.

## Consecuencias

- El sprint planning del curso y el tablero del repositorio usan las mismas HU.
- Las diferencias técnicas con el documento quedan registradas en los ADR 0002 a 0005.
- Detección por huella, candado de ejecución y reconciliación con legacy quedan
  como principios por implementar después del backlog; no hay sistema legacy que reconciliar.
