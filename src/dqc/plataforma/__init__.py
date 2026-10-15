"""Dónde corre el flujo: DuckDB (local y pruebas) o BigQuery (GCP).

Las dos plataformas reciben SQL de BigQuery; DuckDB lo traduce con sqlglot.
Así las pruebas ejercitan el mismo SQL que corre en producción.

Interfaz común:
  funciones                 funciones propias de la plataforma (cifrado, fechas)
  preparar()                datasets y llaves de cifrado
  reiniciar()               borra todo menos las llaves (para simular desde cero)
  consultar(sql)            filas como dicts; dataset por defecto: dq_master
  probar(sql)               error de compilación o None (dry run)
  columnas(tabla, dataset)  [(columna, tipo BigQuery)]
  escribir(dataset, tabla, arrow, corte, primero)        reemplaza el corte
  materializar(sql, dataset, tabla, corte, primero)      idem, desde una consulta
  agregar(dataset, tabla, filas, esquema)                agrega filas
Con corte=None se reemplaza la tabla completa.
"""
