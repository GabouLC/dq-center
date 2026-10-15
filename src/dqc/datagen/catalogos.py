"""Catálogos fijos: ubigeos reales del INEI, productos ficticios y listas de apoyo."""

_LIMA = [
    "Lima", "Ancón", "Ate", "Barranco", "Breña", "Carabayllo", "Chaclacayo",
    "Chorrillos", "Cieneguilla", "Comas", "El Agustino", "Independencia",
    "Jesús María", "La Molina", "La Victoria", "Lince", "Los Olivos",
    "Lurigancho", "Lurín", "Magdalena del Mar", "Pueblo Libre", "Miraflores",
    "Pachacámac", "Pucusana", "Puente Piedra", "Punta Hermosa", "Punta Negra",
    "Rímac", "San Bartolo", "San Borja", "San Isidro", "San Juan de Lurigancho",
    "San Juan de Miraflores", "San Luis", "San Martín de Porres", "San Miguel",
    "Santa Anita", "Santa María del Mar", "Santa Rosa", "Santiago de Surco",
    "Surquillo", "Villa El Salvador", "Villa María del Triunfo",
]
_CALLAO = [
    "Callao", "Bellavista", "Carmen de la Legua Reynoso", "La Perla", "La Punta",
    "Ventanilla", "Mi Perú",
]
_AREQUIPA = [
    "Arequipa", "Alto Selva Alegre", "Cayma", "Cerro Colorado", "Characato",
    "Chiguata", "Jacobo Hunter", "La Joya", "Mariano Melgar", "Miraflores",
    "Mollebaya", "Paucarpata", "Pocsi", "Polobaya", "Quequeña", "Sabandía",
    "Sachaca", "San Juan de Siguas", "San Juan de Tarucani",
    "Santa Isabel de Siguas", "Santa Rita de Siguas", "Socabaya", "Tiabaya",
    "Uchumayo", "Vitor", "Yanahuara", "Yarabamba", "Yura",
    "José Luis Bustamante y Rivero",
]
_TRUJILLO = [
    "Trujillo", "El Porvenir", "Florencia de Mora", "Huanchaco", "La Esperanza",
    "Laredo", "Moche", "Poroto", "Salaverry", "Simbal", "Víctor Larco Herrera",
]
_CHICLAYO = [
    "Chiclayo", "Chongoyape", "Eten", "Eten Puerto", "José Leonardo Ortiz",
    "La Victoria", "Lagunas", "Monsefú", "Nueva Arica", "Oyotún", "Picsi",
    "Pimentel", "Reque", "Santa Rosa", "Saña", "Cayaltí", "Pátapo", "Pomalca",
    "Pucalá", "Tumán",
]
_CUSCO = [
    "Cusco", "Ccorca", "Poroy", "San Jerónimo", "San Sebastián", "Santiago",
    "Saylla", "Wanchaq",
]


def _provincia(prefijo: str, departamento: str, provincia: str, distritos: list[str]):
    return [
        (f"{prefijo}{i:02d}", departamento, provincia, d)
        for i, d in enumerate(distritos, start=1)
    ]


# (ubigeo, departamento, provincia, distrito): 118 distritos.
UBIGEOS = (
    _provincia("1501", "LIMA", "LIMA", _LIMA)
    + _provincia("0701", "CALLAO", "CALLAO", _CALLAO)
    + _provincia("0401", "AREQUIPA", "AREQUIPA", _AREQUIPA)
    + _provincia("1301", "LA LIBERTAD", "TRUJILLO", _TRUJILLO)
    + _provincia("1401", "LAMBAYEQUE", "CHICLAYO", _CHICLAYO)
    + _provincia("0801", "CUSCO", "CUSCO", _CUSCO)
)

# Peso de cada provincia al asignar el ubigeo de una persona.
PESO_PREFIJO_UBIGEO = {"1501": 60, "0701": 8, "0401": 10, "1301": 8, "1401": 7, "0801": 7}

# Ubigeos que no existen en ref_ubigeo: códigos fuera de rango y códigos que
# perdieron el cero inicial al pasar por un campo numérico.
UBIGEOS_INVALIDOS = ["150144", "150150", "150199", "070110", "040135", "70101", "40101", "80108", "000000"]

# (cod_producto, nombre, ramo, activo, peso en la emisión de pólizas)
PRODUCTOS = [
    ("VEH-01", "Auto Total", "VEHICULAR", True, 10),
    ("VEH-02", "Auto Esencial", "VEHICULAR", True, 8),
    ("VEH-03", "Auto Flota Pyme", "VEHICULAR", True, 4),
    ("SOA-01", "SOAT Auto", "SOAT", True, 11),
    ("SOA-02", "SOAT Moto", "SOAT", True, 5),
    ("VID-01", "Vida Individual", "VIDA", True, 8),
    ("VID-02", "Vida con Ahorro", "VIDA", True, 8),
    ("VID-03", "Vida Renta Educativa", "VIDA", True, 8),
    ("VID-04", "Vida Clásico", "VIDA", False, 0),
    ("SAL-01", "Salud Integral", "SALUD", True, 10),
    ("SAL-02", "Salud Oncológico", "SALUD", True, 7),
    ("SAL-03", "Accidentes Personales", "SALUD", True, 5),
    ("HOG-01", "Hogar Total", "HOGAR", True, 9),
    ("HOG-02", "Hogar Contenido", "HOGAR", True, 7),
    ("HOG-03", "Hogar Básico", "HOGAR", False, 0),
]
RAMOS_VEHICULARES = {"VEHICULAR", "SOAT"}

MARCAS_AUTO = {
    "Toyota": ["Yaris", "Corolla", "Hilux", "RAV4"],
    "Hyundai": ["Accent", "Tucson", "Creta"],
    "Kia": ["Rio", "Picanto", "Sportage"],
    "Nissan": ["Sentra", "Versa", "Frontier"],
    "Chevrolet": ["Sail", "Onix"],
    "Suzuki": ["Swift", "Vitara"],
    "Mitsubishi": ["L200", "Outlander"],
    "Volkswagen": ["Gol", "Amarok"],
}
MARCAS_MOTO = {
    "Honda": ["CB190R", "XR150L"],
    "Yamaha": ["FZ25", "XTZ125"],
    "Bajaj": ["Pulsar NS200", "Boxer 150"],
}

CAUSAS = {
    "VEHICULAR": ["Choque", "Robo total", "Robo de accesorios", "Daño a terceros"],
    "SOAT": ["Atropello", "Choque con lesionados", "Volcadura"],
    "VIDA": ["Fallecimiento natural", "Fallecimiento accidental", "Invalidez"],
    "SALUD": ["Hospitalización", "Cirugía", "Atención ambulatoria"],
    "HOGAR": ["Incendio", "Robo domiciliario", "Daño por agua"],
}

MEDIOS_PAGO = ["TARJETA_CREDITO", "DEBITO_AUTOMATICO", "TRANSFERENCIA", "PAGO_EFECTIVO"]
CANALES_VENTA = ["CORREDOR", "DIGITAL", "AGENCIA", "BANCASEGUROS", "TELEMARKETING"]
DOMINIOS_EMAIL = ["gmail.com", "hotmail.com", "outlook.com", "yahoo.es"]
GIROS_EMPRESA = [
    "Inversiones", "Comercial", "Transportes", "Constructora", "Distribuidora",
    "Servicios Generales", "Agroindustrias", "Importaciones",
]

# Caracteres válidos de un VIN (sin I, O ni Q).
ALFABETO_VIN = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"
