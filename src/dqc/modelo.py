"""Constantes del modelo de datos compartidas por el generador, el motor y la API."""

from datetime import date

CORTES = [
    date(2026, 4, 30),
    date(2026, 5, 31),
    date(2026, 6, 30),
    date(2026, 7, 31),
    date(2026, 8, 31),
    date(2026, 9, 30),
]

TABLAS_REF = ["ref_producto", "ref_ubigeo"]
TABLAS_CORTE = ["persona", "poliza", "vehiculo", "siniestro", "pago"]

# Llave de fila de cada tabla por corte: es la que se guarda en el manifiesto
# y en las muestras de fallidos. Las reglas de tabla completa usan el nombre
# de la tabla como llave.
LLAVES = {
    "persona": "id_persona",
    "poliza": "id_poliza",
    "vehiculo": "id_vehiculo",
    "siniestro": "id_siniestro",
    "pago": "id_pago",
}

DIMENSIONES = [
    "completitud",
    "unicidad",
    "validez",
    "consistencia",
    "integridad",
    "oportunidad",
    "volumetria",
]

PESO_SEVERIDAD = {"CRITICA": 3, "ALTA": 2, "MEDIA": 1}

# Tipos en notación de BigQuery; el generador los traduce a Arrow.
ESQUEMAS = {
    "ref_producto": [
        ("cod_producto", "STRING"), ("nombre", "STRING"), ("ramo", "STRING"), ("activo", "BOOL"),
    ],
    "ref_ubigeo": [
        ("ubigeo", "STRING"), ("departamento", "STRING"), ("provincia", "STRING"), ("distrito", "STRING"),
    ],
    "persona": [
        ("fecha_corte", "DATE"), ("id_persona", "INT64"), ("tipo_documento", "STRING"),
        ("nro_documento", "STRING"), ("nombres", "STRING"), ("apellido_paterno", "STRING"),
        ("apellido_materno", "STRING"), ("razon_social", "STRING"), ("fecha_nacimiento", "DATE"),
        ("sexo", "STRING"), ("email", "STRING"), ("celular", "STRING"), ("ubigeo", "STRING"),
        ("fecha_alta", "DATE"),
    ],
    "poliza": [
        ("fecha_corte", "DATE"), ("id_poliza", "INT64"), ("nro_poliza", "STRING"),
        ("cod_producto", "STRING"), ("id_contratante", "INT64"), ("id_asegurado", "INT64"),
        ("fecha_emision", "DATE"), ("fecha_inicio_vigencia", "DATE"), ("fecha_fin_vigencia", "DATE"),
        ("moneda", "STRING"), ("suma_asegurada", "FLOAT64"), ("prima_neta", "FLOAT64"),
        ("prima_total", "FLOAT64"), ("estado", "STRING"),
    ],
    "vehiculo": [
        ("fecha_corte", "DATE"), ("id_vehiculo", "INT64"), ("id_poliza", "INT64"), ("placa", "STRING"),
        ("nro_serie", "STRING"), ("marca", "STRING"), ("modelo", "STRING"),
        ("anio_fabricacion", "INT64"), ("uso", "STRING"), ("valor_comercial", "FLOAT64"),
    ],
    "siniestro": [
        ("fecha_corte", "DATE"), ("id_siniestro", "INT64"), ("id_poliza", "INT64"),
        ("fecha_ocurrencia", "DATE"), ("fecha_aviso", "DATE"), ("causa", "STRING"),
        ("monto_reclamado", "FLOAT64"), ("monto_pagado", "FLOAT64"), ("estado", "STRING"),
    ],
    "pago": [
        ("fecha_corte", "DATE"), ("id_pago", "INT64"), ("id_poliza", "INT64"), ("nro_cuota", "INT64"),
        ("fecha_vencimiento", "DATE"), ("fecha_pago", "DATE"), ("monto", "FLOAT64"),
        ("medio_pago", "STRING"), ("estado", "STRING"),
    ],
    "registro_cargas": [
        ("tabla", "STRING"), ("fecha_corte", "DATE"), ("cargado_en", "TIMESTAMP"), ("filas", "INT64"),
    ],
    "manifiesto_errores": [
        ("id_regla", "STRING"), ("tabla", "STRING"), ("fecha_corte", "DATE"), ("llave", "STRING"),
        ("descripcion", "STRING"),
    ],
}

# Columnas que una tabla estrena desde un corte; Fuentes > Estructura debe detectarlas.
COLUMNAS_NUEVAS = {"poliza": (date(2026, 9, 30), [("canal_venta", "STRING")])}


def esquema(tabla: str, corte: date | None = None) -> list[tuple[str, str]]:
    """Columnas de una tabla tal como existen en un corte."""
    columnas = list(ESQUEMAS[tabla])
    if corte is not None and tabla in COLUMNAS_NUEVAS:
        desde, nuevas = COLUMNAS_NUEVAS[tabla]
        if corte >= desde:
            columnas += nuevas
    return columnas
