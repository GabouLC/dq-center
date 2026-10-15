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

# Niveles de calidad del backlog: N1 detecta errores básicos de cada registro
# (HU-02), N2 aplica reglas de negocio entre campos y tablas (HU-03) y N3 mide
# la salud de la carga completa antes de certificar (HU-04).
NIVEL_POR_DIMENSION = {
    "completitud": "N1",
    "unicidad": "N1",
    "validez": "N1",
    "consistencia": "N2",
    "integridad": "N2",
    "oportunidad": "N3",
    "volumetria": "N3",
}

# Capas del flujo RAW -> MASTER -> BUSINESS y datasets de soporte.
RAW, MASTER, BUSINESS = "dq_raw", "dq_master", "dq_business"
ENGINE, SEGURIDAD = "dq_engine", "dq_seguridad"

# Etapas fuera del motor que también se verifican contra el manifiesto.
INGESTA, HOMOLOGACION, PRIVACIDAD = "INGESTA", "HOMOLOGACION", "PRIVACIDAD"

# Dominios de negocio del backlog: cada tabla pertenece a uno.
DOMINIO_POR_TABLA = {
    "persona": "Persona",
    "poliza": "Póliza",
    "vehiculo": "Póliza",
    "siniestro": "Póliza",
    "pago": "Póliza",
}

# Una regla en FALLA bloquea la certificación si su severidad es una de estas (HU-04).
SEVERIDADES_BLOQUEANTES = ("CRITICA", "ALTA")
CERTIFICADO = "CERTIFICADO"
CON_OBSERVACIONES = "CERTIFICADO_CON_OBSERVACIONES"
NO_CERTIFICADO = "NO_CERTIFICADO"

DAC = ("PUBLICO", "SENSIBLE", "SENSIBLE_CIFRADO")
MODOS_CIFRADO = ("deterministico", "aleatorio")

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
        ("tabla", "STRING"), ("fecha_corte", "DATE"), ("archivo", "STRING"), ("cargado_en", "TIMESTAMP"),
        ("filas", "INT64"), ("estado", "STRING"), ("detalle", "STRING"),
    ],
    "incidencias_homologacion": [
        ("fecha_corte", "DATE"), ("tabla", "STRING"), ("archivo", "STRING"), ("llave", "STRING"),
        ("columnas", "STRING"), ("valores", "STRING"),
    ],
    "manifiesto_errores": [
        ("id_regla", "STRING"), ("tabla", "STRING"), ("fecha_corte", "DATE"), ("llave", "STRING"),
        ("descripcion", "STRING"),
    ],
}

# Resultados del motor en dq_engine.
ESQUEMAS_ENGINE = {
    "ejecuciones": [
        ("id_ejecucion", "STRING"), ("fecha_corte", "DATE"), ("origen", "STRING"),
        ("iniciada_en", "TIMESTAMP"), ("terminada_en", "TIMESTAMP"), ("reglas", "INT64"),
    ],
    "resultados": [
        ("id_ejecucion", "STRING"), ("fecha_corte", "DATE"), ("id_regla", "STRING"), ("tabla", "STRING"),
        ("dominio", "STRING"), ("nivel", "STRING"), ("dimension", "STRING"), ("severidad", "STRING"), ("tipo", "STRING"),
        ("umbral", "FLOAT64"), ("universo", "INT64"), ("cumplen", "INT64"), ("cumplimiento", "FLOAT64"),
        ("estado", "STRING"),
    ],
    "fallidos": [
        ("id_ejecucion", "STRING"), ("fecha_corte", "DATE"), ("id_regla", "STRING"), ("tabla", "STRING"),
        ("llave", "STRING"), ("detalle", "STRING"),
    ],
    "esquemas": [
        ("id_ejecucion", "STRING"), ("fecha_corte", "DATE"), ("tabla", "STRING"), ("posicion", "INT64"),
        ("columna", "STRING"), ("tipo", "STRING"),
    ],
    # Veredicto del Quality & Privacy Gate por tabla y corte, con su sello (HU-04, HU-07).
    "certificaciones": [
        ("id_ejecucion", "STRING"), ("fecha_corte", "DATE"), ("tabla", "STRING"), ("dominio", "STRING"),
        ("estado", "STRING"), ("calidad_ok", "BOOL"), ("privacidad_ok", "BOOL"),
        ("reglas_bloqueantes", "STRING"), ("reglas_con_observacion", "STRING"), ("hallazgos", "INT64"),
        ("cobertura", "FLOAT64"), ("publicado", "BOOL"), ("version_motor", "STRING"),
        ("version_reglas", "STRING"), ("certificado_en", "TIMESTAMP"),
    ],
    # Evidencia de la revisión de privacidad: qué se encontró, dónde y si bloquea.
    "hallazgos_privacidad": [
        ("id_ejecucion", "STRING"), ("fecha_corte", "DATE"), ("tabla", "STRING"), ("tipo", "STRING"),
        ("columna", "STRING"), ("llave", "STRING"), ("bloqueante", "BOOL"),
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
