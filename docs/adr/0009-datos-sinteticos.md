# 0009 · Aseguradora ficticia y datos sintéticos

**Estado:** aceptada (2026-10-15).

## Contexto

El caso de negocio se inspira en una aseguradora real. El repositorio es un
entregable académico y personal, y no debe contener datos, nombres de tablas ni
código de ninguna empresa.

## Decisión

Todo el sistema trabaja sobre una aseguradora ficticia. El generador
(`dqc.datagen`) crea los datos con Faker y una semilla fija. Los nombres de
tablas, columnas, productos, dueños y consumidores son inventados. Los ubigeos
son códigos públicos del INEI.

## Consecuencias

- El repositorio se puede mostrar sin restricciones.
- Ningún componente se conecta a sistemas corporativos.
