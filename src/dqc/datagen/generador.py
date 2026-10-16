"""Genera las tablas sintéticas de cada día y el manifiesto de errores sembrados.

Cada entidad (persona, póliza, vehículo, siniestro, cuota) nace una sola vez,
con su fecha de alta y como mucho un defecto persistente. Cada corte diario es
una foto de las entidades que ya existen ese día; los campos que cambian con el
tiempo (estado de la póliza, de la cuota y del siniestro) se calculan para cada
corte. Así un defecto persiste entre cortes como en una base real.

Para que la historia se parezca a una operación real, la calidad se mueve:

  - tendencias: una campaña de contactos corrige celulares, la cobranza
    actualiza cuotas vencidas, se limpian los vehículos, y cada vez más pólizas
    vencidas quedan como VIGENTE porque el proceso de bajas no las alcanza;
  - ruido diario: errores transitorios que aparecen un día y se corrigen al
    siguiente, más los lunes (lo acumulado del fin de semana) y menos el domingo;
  - incidentes con fecha: un archivo tardío, una carga con documentos nulos, un
    archivo rechazado, una fuga de PII, un reproceso que infla pólizas, importes
    con otro formato y una columna nueva sin clasificar.

Los datos limpios cumplen todas las reglas. Cada fila sembrada entra al
manifiesto una vez por cada regla que rompe en ese corte; el motor tiene que
detectar exactamente esas filas.
"""

from __future__ import annotations

import math
import random
import unicodedata
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta, timezone

from dateutil.relativedelta import relativedelta
from faker import Faker

from dqc.datagen import catalogos as cat
from dqc.modelo import (  # noqa: F401 (INGESTA se reexporta)
    COLUMNAS_NUEVAS, CORTES, HOMOLOGACION, INGESTA, PRIVACIDAD, TABLAS_CORTE,
)

SEMILLA = 20260930
# Perú no tiene horario de verano: America/Lima es siempre UTC-5.
ZONA_LIMA = timezone(timedelta(hours=-5), "America/Lima")
UN_DIA = timedelta(days=1)
INICIO = CORTES[0]

# Cartera al 30 de junio y altas por día hábil, con escala 1.
N_PERSONAS_BASE = 1500
N_POLIZAS_BASE = 2400
N_SINIESTROS_BASE = 200
ALTAS_DIARIAS = {"persona": 1.8, "poliza": 3.8, "siniestro": 1.3}
# Lunes a domingo: el fin de semana casi no hay altas.
FACTOR_ALTAS = [1.0, 1.0, 1.0, 1.0, 1.0, 0.35, 0.1]
# Errores transitorios: los lunes llega lo acumulado del fin de semana.
FACTOR_RUIDO = [2.0, 1.0, 1.0, 1.0, 1.0, 0.6, 0.4]

# Incidentes del período.
PERSONA_TARDE = date(2026, 7, 14)
DOCUMENTO_NULO = date(2026, 7, 22)
RECHAZO_SINIESTRO = date(2026, 7, 28)
FUGA_PII = {date(2026, 8, 7): 5, date(2026, 8, 8): 3}
REPROCESO = date(2026, 8, 20)
PICO_IMPORTES = (date(2026, 9, 2), date(2026, 9, 4))
CANAL_VENTA = COLUMNAS_NUEVAS["poliza"][0]
PRODUCTO_INACTIVO_DESDE = date(2026, 9, 16)
CORRECCION_DNI = date(2026, 9, 15)
# Campañas de mejora.
CAMPANA_COBRANZA = date(2026, 8, 3)
CAMPANA_CONTACTOS = date(2026, 8, 17)
LIMPIEZA_VEHICULOS = (date(2026, 8, 24), date(2026, 9, 11))

DESCRIPCIONES = {
    "DUPLICADA": "Persona duplicada con el mismo documento",
    "DNI_7_DIGITOS": "DNI de 7 dígitos: perdió el cero inicial al cargarse como número",
    "NACIMIENTO_1900": "fecha_nacimiento 1900-01-01 usada como valor por defecto",
    "CELULAR_INVALIDO": "Celular de 8 dígitos o teléfono fijo",
    "EMAIL_SIN_DOMINIO": "Email sin dominio",
    "UBIGEO_INEXISTENTE": "Ubigeo que no existe",
    "SIN_CONTACTO": "Persona sin email ni celular",
    "DOCUMENTO_NULO": "Carga del 22 de julio: nro_documento nulo",
    "PERSONA_TARDE": "El archivo de personas del 14 de julio llegó con más de dos días de retraso",
    "ESTADO_SUCIO": "Estado de póliza con minúsculas o espacios",
    "FIN_ANTES_DEL_INICIO": "Póliza con fin de vigencia antes del inicio",
    "VIGENTE_VENCIDA": "Póliza VIGENTE con la vigencia ya vencida: el proceso de bajas no la alcanzó",
    "PRIMA_SIN_IGV": "prima_total calculada sin IGV",
    "DUPLICADA_REPROCESO": "Reproceso del 20 de agosto: póliza duplicada",
    "VOLUMEN_REPROCESO": "Reproceso del 20 de agosto: el volumen de pólizas sube 22 %",
    "PRODUCTO_INACTIVO": "Póliza nueva con un producto inactivo",
    "PLACA_SIN_GUION": "Placa sin guion",
    "ANIO_INVALIDO": "Año de fabricación fuera de rango",
    "POLIZA_NO_VEHICULAR": "Vehículo colgado de una póliza que no es vehicular",
    "FUERA_DE_VIGENCIA": "Siniestro fuera de la vigencia de su póliza",
    "SIN_POLIZA": "Siniestro sin póliza",
    "MONTO_PAGADO_EXCEDE": "Monto pagado mayor que el reclamado",
    "PAGADO_SIN_FECHA": "Cuota PAGADO sin fecha_pago",
    "PENDIENTE_VENCIDA": "Cuota PENDIENTE ya vencida",
    "IMPORTE_NO_CONVERTIBLE": "IMPORTE con formato de moneda: no se puede convertir a número",
    "AVISO_NO_CONVERTIBLE": "FEC_AVISO en formato DD/MM/AAAA: no se puede convertir a fecha",
    "DNI_EN_CAUSA": "El DNI del reportante quedó escrito en la causa del siniestro",
}

# Campo que el exportador escribe con un formato que la homologación no acepta.
NO_CONVERTIBLE = "_no_convertible"


def _slug(texto: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return "".join(c for c in ascii_.lower() if c.isalnum())


def _poisson(rnd: random.Random, media: float) -> int:
    """Conteo de eventos de un día (Knuth; las medias son chicas)."""
    if media <= 0:
        return 0
    limite, k, p = math.exp(-media), 0, 1.0
    while True:
        p *= rnd.random()
        if p <= limite:
            return k
        k += 1


def _activo(defecto: str | None, corregido: date | None, corte: date) -> bool:
    return defecto is not None and (corregido is None or corte < corregido)


@dataclass
class Persona:
    id_persona: int
    tipo_documento: str
    nro_documento: str
    nombres: str | None
    apellido_paterno: str | None
    apellido_materno: str | None
    razon_social: str | None
    fecha_nacimiento: date | None
    sexo: str | None
    email: str | None
    celular: str | None
    celular_valido: str | None
    ubigeo: str | None
    fecha_alta: date
    defecto: str | None = None
    corregido: date | None = None
    id_original: int | None = None


@dataclass
class Poliza:
    id_poliza: int
    nro_poliza: str
    cod_producto: str
    ramo: str
    id_contratante: int
    id_asegurado: int
    fecha_emision: date
    fecha_inicio_vigencia: date
    fecha_fin_real: date
    fecha_fin_registrada: date
    moneda: str
    suma_asegurada: float
    prima_neta: float
    prima_total: float
    canal_venta: str
    estado_fijo: str | None
    desde: date
    hasta: date | None = None
    origen: str = "NORMAL"
    defecto: str | None = None

    def presente(self, corte: date) -> bool:
        return self.desde <= corte and (self.hasta is None or corte <= self.hasta)

    def estado_real(self, corte: date) -> str:
        if self.estado_fijo:
            return self.estado_fijo
        return "VIGENTE" if corte <= self.fecha_fin_real else "VENCIDA"


@dataclass
class Vehiculo:
    id_vehiculo: int
    id_poliza: int
    placa: str
    nro_serie: str
    marca: str
    modelo: str
    anio_fabricacion: int
    uso: str
    valor_comercial: float
    desde: date
    hasta: date | None = None
    defecto: str | None = None
    corregido: date | None = None

    def presente(self, corte: date) -> bool:
        return self.desde <= corte and (self.hasta is None or corte <= self.hasta)


@dataclass
class Siniestro:
    id_siniestro: int
    id_poliza: int
    fecha_ocurrencia: date
    fecha_aviso: date
    causa: str
    monto_reclamado: float
    monto_pagado_final: float
    resolucion: str
    defecto: str | None = None

    def estado(self, corte: date) -> str:
        dias = (corte - self.fecha_aviso).days
        if dias < 20:
            return "ABIERTO"
        if dias < 60:
            return "EN_EVALUACION"
        return self.resolucion


@dataclass
class Pago:
    id_pago: int
    id_poliza: int
    nro_cuota: int
    fecha_vencimiento: date
    fecha_pago_real: date | None
    monto: float
    medio_pago: str
    desde: date
    defecto: str | None = None
    corregido: date | None = None


@dataclass
class Resultado:
    ref: dict[str, list[dict]]
    por_corte: dict[str, dict[date, list[dict]]]
    llegadas: dict[tuple[str, date], datetime]  # (tabla, corte) -> llegada del archivo
    manifiesto: list[dict]
    entidades: dict[str, list] = field(repr=False, default_factory=dict)


class Generador:
    def __init__(self, semilla: int = SEMILLA, escala: float = 1.0):
        self.semilla = semilla
        self.escala = escala
        self.rnd = random.Random(semilla)
        self.fake = Faker("es_MX")
        self.fake.seed_instance(semilla)
        self.personas: list[Persona] = []
        self.polizas: list[Poliza] = []
        self.vehiculos: list[Vehiculo] = []
        self.siniestros: list[Siniestro] = []
        self.pagos: list[Pago] = []
        self._documentos: set[tuple[str, str]] = set()
        self._vins: set[str] = set()
        self._secuencia_poliza: dict[int, int] = {}
        self._productos_activos = [p for p in cat.PRODUCTOS if p[3]]
        self._productos_inactivos = [p for p in cat.PRODUCTOS if not p[3]]
        self._ubigeos_por_prefijo: dict[str, list[str]] = {}
        for ubigeo, *_ in cat.UBIGEOS:
            self._ubigeos_por_prefijo.setdefault(ubigeo[:4], []).append(ubigeo)

    # ── utilidades ──────────────────────────────────────────────────────────

    def _fecha_entre(self, desde: date, hasta: date) -> date:
        return desde + timedelta(days=self.rnd.randint(0, (hasta - desde).days))

    def _escalar(self, n: float, minimo: int = 1) -> int:
        return max(minimo, round(n * self.escala))

    def _altas_del_dia(self, tabla: str, dia: date) -> int:
        return _poisson(self.rnd, ALTAS_DIARIAS[tabla] * self.escala * FACTOR_ALTAS[dia.weekday()])

    def _documento_unico(self, tipo: str, generar) -> str:
        while True:
            nro = generar()
            if (tipo, nro) not in self._documentos:
                self._documentos.add((tipo, nro))
                return nro

    def _ubigeo(self) -> str:
        prefijos = list(cat.PESO_PREFIJO_UBIGEO)
        prefijo = self.rnd.choices(prefijos, [cat.PESO_PREFIJO_UBIGEO[p] for p in prefijos])[0]
        return self.rnd.choice(self._ubigeos_por_prefijo[prefijo])

    # ── generación ──────────────────────────────────────────────────────────

    def generar(self) -> "Generador":
        self._generar_personas()
        self._generar_polizas()
        self._generar_vehiculos()
        self._generar_siniestros()
        self._generar_pagos()
        return self

    def _generar_personas(self) -> None:
        for _ in range(self._escalar(N_PERSONAS_BASE)):
            self._agregar_persona(self._fecha_entre(date(2015, 1, 1), INICIO - UN_DIA))
        for dia in CORTES:
            for _ in range(self._altas_del_dia("persona", dia)):
                self._agregar_persona(dia)

        # Duplicadas: la copia entra después con otro id y el mismo documento.
        candidatas = [p for p in self.personas if p.defecto is None]
        for original in self.rnd.sample(candidatas, round(len(self.personas) * 0.004)):
            original.defecto = "DUPLICADA_ORIGINAL"
            self.personas.append(replace(
                original,
                id_persona=len(self.personas) + 1,
                fecha_alta=original.fecha_alta + timedelta(days=self.rnd.randint(10, 400)),
                defecto="DUPLICADA_COPIA",
                id_original=original.id_persona,
            ))

    def _agregar_persona(self, alta: date) -> None:
        r = self.rnd
        tipo = r.choices(["DNI", "CE", "RUC"], [85, 5, 10])[0]
        u = r.random()
        sin_contacto = u < 0.047
        tiene_email = not sin_contacto and u >= 0.127
        tiene_celular = not sin_contacto and not 0.127 <= u < 0.207
        tiene_ubigeo = r.random() >= 0.03

        # Un solo defecto persistente por persona. Los datos de contacto son los más flojos.
        u = r.random()
        defecto = corregido = None
        if sin_contacto:
            defecto = "SIN_CONTACTO"
        elif u < 0.012:
            if tipo == "DNI" and alta < CORRECCION_DNI:
                defecto, corregido = "DNI_7_DIGITOS", CORRECCION_DNI
        elif u < 0.020:
            defecto = "NACIMIENTO_1900" if tipo != "RUC" else None
        elif u < 0.180:
            if tiene_celular:
                defecto = "CELULAR_INVALIDO"
                # La campaña de actualización de contactos corrige poco más de la mitad.
                if r.random() < 0.6:
                    corregido = CAMPANA_CONTACTOS + timedelta(days=r.randint(0, 75))
        elif u < 0.260:
            defecto = "EMAIL_SIN_DOMINIO" if tiene_email else None
        elif u < 0.270:
            defecto = "UBIGEO_INEXISTENTE" if tiene_ubigeo else None

        if tipo == "RUC":
            nro = self._documento_unico(tipo, lambda: f"20{r.randint(100000000, 999999999)}")
            apellido = self.fake.last_name()
            giro = r.choice(cat.GIROS_EMPRESA)
            nombres = paterno = materno = sexo = nacimiento = None
            razon_social = f"{giro} {apellido} S.A.C."
            local, dominio = "contacto", f"{_slug(giro)[:5]}{_slug(apellido)}.com.pe"
        else:
            if defecto == "DNI_7_DIGITOS":
                # El DNI real empieza con cero; al cargarse como número lo pierde.
                nro = self._documento_unico(tipo, lambda: f"0{r.randint(1000000, 9999999)}")
            elif tipo == "DNI":
                nro = self._documento_unico(tipo, lambda: f"{r.randint(10000000, 79999999)}")
            else:
                nro = self._documento_unico(tipo, lambda: f"00{r.randint(1000000, 9999999)}")
            sexo = r.choice("MF")
            nombres = self.fake.first_name_male() if sexo == "M" else self.fake.first_name_female()
            paterno, materno = self.fake.last_name(), self.fake.last_name()
            razon_social = None
            if defecto == "NACIMIENTO_1900":
                nacimiento = date(1900, 1, 1)
            else:
                nacimiento = self._fecha_entre(date(1941, 1, 1), date(2007, 12, 31))
            local = f"{_slug(nombres.split()[0])}.{_slug(paterno)}{r.randint(1, 99)}"
            dominio = r.choice(cat.DOMINIOS_EMAIL)

        email = f"{local}@{dominio}" if tiene_email else None
        celular = celular_valido = f"9{r.randint(10000000, 99999999)}" if tiene_celular else None
        ubigeo = self._ubigeo() if tiene_ubigeo else None
        if defecto == "CELULAR_INVALIDO":
            celular = r.choice([
                f"9{r.randint(1000000, 9999999)}",
                f"01{r.randint(2000000, 7999999)}",
                f"{r.randint(2000000, 7999999)}",
            ])
        elif defecto == "EMAIL_SIN_DOMINIO":
            email = r.choice([f"{local}@", local, f"{local}@{dominio.split('.')[0]}"])
        elif defecto == "UBIGEO_INEXISTENTE":
            ubigeo = r.choice(cat.UBIGEOS_INVALIDOS)

        self.personas.append(Persona(
            id_persona=len(self.personas) + 1,
            tipo_documento=tipo,
            nro_documento=nro,
            nombres=nombres,
            apellido_paterno=paterno,
            apellido_materno=materno,
            razon_social=razon_social,
            fecha_nacimiento=nacimiento,
            sexo=sexo,
            email=email,
            celular=celular,
            celular_valido=celular_valido,
            ubigeo=ubigeo,
            fecha_alta=alta,
            defecto=defecto,
            corregido=corregido,
        ))

    def _generar_polizas(self) -> None:
        self._personas_por_alta = sorted(self.personas, key=lambda p: (p.fecha_alta, p.id_persona))
        self._altas = [p.fecha_alta for p in self._personas_por_alta]

        for _ in range(self._escalar(N_POLIZAS_BASE)):
            self._agregar_poliza(self._fecha_entre(date(2025, 5, 1), INICIO - UN_DIA))
        for dia in CORTES:
            for _ in range(self._altas_del_dia("poliza", dia)):
                inactivo = dia >= PRODUCTO_INACTIVO_DESDE and self.rnd.random() < 0.2
                self._agregar_poliza(
                    dia,
                    producto=self.rnd.choice(self._productos_inactivos) if inactivo else None,
                    origen="PRODUCTO_INACTIVO" if inactivo else "NORMAL",
                )

        # 20 de agosto: un reproceso duplica pólizas (otro id técnico, mismo nro_poliza)
        # y carga pólizas históricas vencidas hasta subir el volumen 22 %. Al día
        # siguiente se borran los duplicados; las históricas se quedan.
        normales = list(self.polizas)
        n_antes = sum(p.presente(REPROCESO - UN_DIA) for p in normales)
        n_dia = sum(p.presente(REPROCESO) for p in normales)
        candidatas = [
            p for p in normales
            if p.presente(REPROCESO - UN_DIA) and p.defecto is None and p.estado_fijo is None
        ]
        n_duplicadas = self._escalar(12, 3)
        for original in self.rnd.sample(candidatas, n_duplicadas):
            original.defecto = "DUPLICADA_REPROCESO_ORIGINAL"
            self.polizas.append(replace(
                original,
                id_poliza=len(self.polizas) + 1,
                origen="COPIA_REPROCESO",
                desde=REPROCESO,
                hasta=REPROCESO,
                defecto="DUPLICADA_REPROCESO_COPIA",
            ))
        for _ in range(round(n_antes * 1.22) - n_dia - n_duplicadas):
            historica = self._agregar_poliza(
                self._fecha_entre(date(2023, 6, 1), date(2025, 4, 30)), origen="HISTORICO"
            )
            historica.desde = REPROCESO

    def _persona_al(self, fecha: date) -> Persona:
        return self._personas_por_alta[self.rnd.randrange(bisect_right(self._altas, fecha))]

    def _montos(self, ramo: str) -> tuple[float, float]:
        r = self.rnd
        if ramo == "VEHICULAR":
            suma = round(r.uniform(25000, 180000), -2)
            prima = suma * r.uniform(0.03, 0.06)
        elif ramo == "SOAT":
            suma = 21400.0
            prima = r.uniform(55, 250)
        elif ramo == "VIDA":
            suma = round(r.uniform(50000, 600000), -3)
            prima = suma * r.uniform(0.003, 0.012)
        elif ramo == "SALUD":
            suma = round(r.uniform(100000, 1000000), -3)
            prima = r.uniform(1200, 6000)
        else:
            suma = round(r.uniform(80000, 900000), -3)
            prima = suma * r.uniform(0.001, 0.003)
        return suma, round(prima, 2)

    def _agregar_poliza(self, emision: date, producto=None, origen: str = "NORMAL") -> Poliza:
        r = self.rnd
        if producto is None:
            producto = r.choices(self._productos_activos, [p[4] for p in self._productos_activos])[0]
        cod_producto, _, ramo, _, _ = producto
        inicio = emision - timedelta(days=r.randint(0, 10))
        fin = inicio + relativedelta(years=1)
        moneda = "PEN" if ramo == "SOAT" or r.random() < 0.8 else "USD"
        suma, prima_neta = self._montos(ramo)
        contratante = self._persona_al(emision)
        asegurado = contratante
        if contratante.tipo_documento == "RUC" or r.random() >= 0.7:
            asegurado = self._persona_al(emision)
            while asegurado.tipo_documento == "RUC":
                asegurado = self._persona_al(emision)

        estado_fijo = defecto = None
        if origen == "NORMAL":
            u = r.random()
            estado_fijo = "ANULADA" if u < 0.04 else "SUSPENDIDA" if u < 0.06 else None
            # Pólizas vencidas que siguen como VIGENTE: hay un rezago heredado y, dentro
            # del período, el proceso de bajas se atrasa cada semana un poco más.
            atraso = 0.0
            if fin < INICIO:
                atraso = 0.07
            elif fin <= CORTES[-1]:
                atraso = 0.03 + 0.16 * (fin - INICIO).days / (CORTES[-1] - INICIO).days
            u = r.random()
            if u < 0.004:
                defecto = "FIN_ANTES_DEL_INICIO" if estado_fijo is None else None
            elif u < 0.012:
                defecto = "PRIMA_SIN_IGV"
            elif u < 0.012 + atraso:
                defecto = "VIGENTE_VENCIDA" if estado_fijo is None else None
        elif origen == "PRODUCTO_INACTIVO":
            defecto = "PRODUCTO_INACTIVO"

        igv = 1.0 if defecto == "PRIMA_SIN_IGV" else 1.18
        anio = emision.year
        self._secuencia_poliza[anio] = self._secuencia_poliza.get(anio, 0) + 1
        poliza = Poliza(
            id_poliza=len(self.polizas) + 1,
            nro_poliza=f"POL-{anio}-{self._secuencia_poliza[anio]:06d}",
            cod_producto=cod_producto,
            ramo=ramo,
            id_contratante=contratante.id_persona,
            id_asegurado=asegurado.id_persona,
            fecha_emision=emision,
            fecha_inicio_vigencia=inicio,
            fecha_fin_real=fin,
            # Error de digitación: el año de fin queda uno antes del inicio.
            fecha_fin_registrada=inicio - relativedelta(years=1) if defecto == "FIN_ANTES_DEL_INICIO" else fin,
            moneda=moneda,
            suma_asegurada=suma,
            prima_neta=prima_neta,
            prima_total=round(prima_neta * 1.03 * igv, 2),
            canal_venta=r.choice(cat.CANALES_VENTA),
            estado_fijo=estado_fijo,
            desde=emision,
            origen=origen,
            defecto=defecto,
        )
        self.polizas.append(poliza)
        return poliza

    def _generar_vehiculos(self) -> None:
        limpieza_inicio, limpieza_fin = LIMPIEZA_VEHICULOS
        for p in self.polizas:
            if p.origen == "NORMAL" and p.ramo in cat.RAMOS_VEHICULARES:
                sin_guion = self.rnd.random() < 0.03
                self._agregar_vehiculo(p, "PLACA_SIN_GUION" if sin_guion else None)
        # Vehículos colgados de pólizas que no son vehiculares: la limpieza de fines de
        # agosto los da de baja. Después de la limpieza no aparecen nuevos.
        no_vehiculares = [
            p for p in self.polizas
            if p.origen == "NORMAL" and p.ramo not in cat.RAMOS_VEHICULARES and p.desde < limpieza_inicio
        ]
        for p in self.rnd.sample(no_vehiculares, max(2, round(len(self.vehiculos) * 0.005))):
            self._agregar_vehiculo(p, "POLIZA_NO_VEHICULAR")
        for v in self.vehiculos:
            if v.defecto == "POLIZA_NO_VEHICULAR":
                v.hasta = self._fecha_entre(limpieza_inicio, limpieza_fin)
            elif v.defecto == "PLACA_SIN_GUION":
                # Las placas se corrigen en la limpieza; las nuevas, a los pocos días.
                v.corregido = (
                    self._fecha_entre(limpieza_inicio, limpieza_fin) if v.desde < limpieza_inicio
                    else v.desde + timedelta(days=self.rnd.randint(2, 6))
                )

    def _agregar_vehiculo(self, poliza: Poliza, defecto: str | None) -> None:
        r = self.rnd
        moto = poliza.cod_producto == "SOA-02"
        marcas = cat.MARCAS_MOTO if moto else cat.MARCAS_AUTO
        marca = r.choice(sorted(marcas))
        letras = "ABCDEFGHJKLMNPRSTUVWXYZ"
        placa = f"{r.choice(letras)}{r.choice(letras + '0123456789')}{r.choice(letras)}-{r.randint(100, 999)}"
        while True:
            vin = "".join(r.choice(cat.ALFABETO_VIN) for _ in range(17))
            if vin not in self._vins:
                self._vins.add(vin)
                break
        anio_emision = poliza.fecha_emision.year
        self.vehiculos.append(Vehiculo(
            id_vehiculo=len(self.vehiculos) + 1,
            id_poliza=poliza.id_poliza,
            placa=placa,
            nro_serie=vin,
            marca=marca,
            modelo=r.choice(marcas[marca]),
            anio_fabricacion=r.randint(max(2000, anio_emision - 15), anio_emision + 1),
            uso="PARTICULAR" if moto else r.choices(["PARTICULAR", "TAXI", "CARGA"], [80, 12, 8])[0],
            valor_comercial=(
                poliza.suma_asegurada if poliza.ramo == "VEHICULAR" else round(r.uniform(15000, 120000), -2)
            ),
            desde=poliza.desde,
            defecto=defecto,
        ))

    def _generar_siniestros(self) -> None:
        self._elegibles = sorted(
            (
                p for p in self.polizas
                if p.origen == "NORMAL" and p.estado_fijo is None and p.defecto != "FIN_ANTES_DEL_INICIO"
            ),
            key=lambda p: (p.fecha_emision, p.id_poliza),
        )
        self._emisiones = [p.fecha_emision for p in self._elegibles]
        self._polizas_fantasma = 0

        # El mínimo de filas de la volumetría (GEN-VOL-02) es 100: la tabla nunca baja de 150.
        for _ in range(max(150, round(N_SINIESTROS_BASE * self.escala))):
            self._agregar_siniestro(self._fecha_entre(date(2025, 7, 1), INICIO - UN_DIA))
        for dia in CORTES:
            for _ in range(self._altas_del_dia("siniestro", dia)):
                self._agregar_siniestro(dia)

    def _agregar_siniestro(self, aviso: date) -> None:
        r = self.rnd
        u = r.random()
        if u < 0.004:
            defecto = "SIN_POLIZA"
            self._polizas_fantasma += 1
            id_poliza = 9_000_000 + self._polizas_fantasma
            ramo = r.choice(sorted(cat.CAUSAS))
            ocurrencia = aviso - timedelta(days=r.randint(0, 20))
        else:
            # Pólizas emitidas antes del aviso que seguían vigentes hasta 30 días antes.
            desde = bisect_left(self._emisiones, aviso - timedelta(days=400))
            hasta = bisect_left(self._emisiones, aviso)
            candidatas = [
                p for p in self._elegibles[desde:hasta]
                if p.fecha_fin_real >= aviso - timedelta(days=30)
            ]
            if u < 0.011:
                defecto = "FUERA_DE_VIGENCIA"
                recientes = [p for p in candidatas if p.fecha_emision >= aviso - timedelta(days=60)]
                poliza = r.choice(recientes or candidatas)
                ocurrencia = poliza.fecha_inicio_vigencia - timedelta(days=r.randint(3, 45))
            else:
                # Algunos llegan con la fecha de aviso en otro formato: no se pueden homologar.
                defecto = "AVISO_NO_CONVERTIBLE" if r.random() < 0.01 else None
                poliza = r.choice(candidatas)
                ocurrencia = self._fecha_entre(
                    max(poliza.fecha_emision, aviso - timedelta(days=60)),
                    min(poliza.fecha_fin_real, aviso),
                )
            id_poliza, ramo = poliza.id_poliza, poliza.ramo

        tope = {"VEHICULAR": 40000, "SOAT": 20000, "VIDA": 300000, "SALUD": 60000, "HOGAR": 80000}[ramo]
        reclamado = round(r.uniform(tope * 0.04, tope), 2)
        self.siniestros.append(Siniestro(
            id_siniestro=len(self.siniestros) + 1,
            id_poliza=id_poliza,
            fecha_ocurrencia=ocurrencia,
            fecha_aviso=aviso,
            causa=r.choice(cat.CAUSAS[ramo]),
            monto_reclamado=reclamado,
            monto_pagado_final=round(reclamado * r.uniform(0.4, 1.0), 2),
            resolucion="PAGADO" if r.random() < 0.75 else "RECHAZADO",
            defecto=defecto,
        ))

    def _generar_pagos(self) -> None:
        r = self.rnd
        for p in self.polizas:
            if p.origen not in ("NORMAL", "PRODUCTO_INACTIVO"):
                continue
            n_cuotas = r.choices([1, 2, 4, 12], [40, 20, 25, 15])[0]
            monto = round(p.prima_total / n_cuotas, 2)
            medio = r.choice(cat.MEDIOS_PAGO)
            for k in range(1, n_cuotas + 1):
                vencimiento = p.fecha_inicio_vigencia + relativedelta(months=(k - 1) * (12 // n_cuotas))
                corregido = None
                if r.random() < 0.15:
                    pago_real = None
                    # Nadie pasa la cuota impaga a VENCIDO. La campaña de cobranza de
                    # agosto la actualiza en tres de cada cuatro casos.
                    defecto = "PENDIENTE_VENCIDA" if r.random() < 0.75 else None
                    if defecto and r.random() < 0.75:
                        corregido = CAMPANA_COBRANZA + timedelta(days=r.randint(0, 70))
                else:
                    pago_real = max(p.fecha_emision, vencimiento + timedelta(days=r.randint(-20, 20)))
                    u = r.random()
                    defecto = "PAGADO_SIN_FECHA" if u < 0.0045 else "IMPORTE_NO_CONVERTIBLE" if u < 0.0075 else None
                self.pagos.append(Pago(
                    id_pago=len(self.pagos) + 1,
                    id_poliza=p.id_poliza,
                    nro_cuota=k,
                    fecha_vencimiento=vencimiento,
                    fecha_pago_real=pago_real,
                    monto=monto,
                    medio_pago=medio,
                    desde=p.desde,
                    defecto=defecto,
                    corregido=corregido,
                ))

    # ── fotos por corte ─────────────────────────────────────────────────────

    def foto(self, corte: date) -> tuple[dict[str, list[dict]], list[dict]]:
        """Filas de cada tabla en un corte y filas del manifiesto de ese corte."""
        manifiesto: list[dict] = []
        con_error: set[tuple[str, int]] = set()

        def error(regla: str, tabla: str, llave: int | str, defecto: str) -> None:
            manifiesto.append({
                "id_regla": regla,
                "tabla": tabla,
                "fecha_corte": corte,
                "llave": str(llave),
                "descripcion": DESCRIPCIONES[defecto],
            })
            con_error.add((tabla, llave))

        filas: dict[str, list[dict]] = {t: [] for t in TABLAS_CORTE}

        copias_presentes = {
            p.id_original for p in self.personas
            if p.defecto == "DUPLICADA_COPIA" and p.fecha_alta <= corte
        }
        dni_presentes = [p for p in self.personas if p.fecha_alta <= corte and p.tipo_documento == "DNI" and p.defecto is None]
        nulos = set()
        if corte == DOCUMENTO_NULO:
            # Una carga mal mapeada deja sin documento a una de cada 22 personas con DNI.
            nulos = {p.id_persona for p in random.Random(f"{self.semilla}-nulos").sample(
                dni_presentes, max(3, round(len(dni_presentes) * 0.045)))}
        for p in self.personas:
            if p.fecha_alta > corte:
                continue
            nro, celular, email = p.nro_documento, p.celular, p.email
            d = p.defecto if _activo(p.defecto, p.corregido, corte) else None
            if p.id_persona in nulos:
                nro = None
                error("PER-COM-01", "persona", p.id_persona, "DOCUMENTO_NULO")
                error("PER-VAL-01", "persona", p.id_persona, "DOCUMENTO_NULO")
            elif d == "DNI_7_DIGITOS":
                nro = nro[1:]
                error("PER-VAL-01", "persona", p.id_persona, d)
            elif d == "NACIMIENTO_1900":
                error("PER-VAL-04", "persona", p.id_persona, d)
            elif d == "CELULAR_INVALIDO":
                error("PER-VAL-03", "persona", p.id_persona, d)
            elif d == "EMAIL_SIN_DOMINIO":
                error("PER-VAL-05", "persona", p.id_persona, d)
            elif d == "UBIGEO_INEXISTENTE":
                error("PER-INT-01", "persona", p.id_persona, d)
            elif d == "SIN_CONTACTO":
                error("PER-COM-02", "persona", p.id_persona, d)
            elif d == "DUPLICADA_COPIA" or (d == "DUPLICADA_ORIGINAL" and p.id_persona in copias_presentes):
                error("PER-UNI-01", "persona", p.id_persona, "DUPLICADA")
            if p.defecto == "CELULAR_INVALIDO" and d is None:
                celular = p.celular_valido
            filas["persona"].append({
                "fecha_corte": corte,
                "id_persona": p.id_persona,
                "tipo_documento": p.tipo_documento,
                "nro_documento": nro,
                "nombres": p.nombres,
                "apellido_paterno": p.apellido_paterno,
                "apellido_materno": p.apellido_materno,
                "razon_social": p.razon_social,
                "fecha_nacimiento": p.fecha_nacimiento,
                "sexo": p.sexo,
                "email": email,
                "celular": celular,
                "ubigeo": p.ubigeo,
                "fecha_alta": p.fecha_alta,
            })

        for p in self.polizas:
            if not p.presente(corte):
                continue
            d = p.defecto
            estado = p.estado_real(corte)
            if d == "VIGENTE_VENCIDA" and estado == "VENCIDA":
                estado = "VIGENTE"
                error("POL-CON-03", "poliza", p.id_poliza, d)
            elif d == "FIN_ANTES_DEL_INICIO":
                error("POL-CON-01", "poliza", p.id_poliza, d)
                if estado == "VIGENTE":
                    error("POL-CON-03", "poliza", p.id_poliza, d)
            elif d == "PRIMA_SIN_IGV":
                error("POL-CON-02", "poliza", p.id_poliza, d)
            elif d == "PRODUCTO_INACTIVO":
                error("POL-INT-02", "poliza", p.id_poliza, d)
            elif d and d.startswith("DUPLICADA_REPROCESO") and corte == REPROCESO:
                error("POL-UNI-01", "poliza", p.id_poliza, "DUPLICADA_REPROCESO")
            fila = {
                "fecha_corte": corte,
                "id_poliza": p.id_poliza,
                "nro_poliza": p.nro_poliza,
                "cod_producto": p.cod_producto,
                "id_contratante": p.id_contratante,
                "id_asegurado": p.id_asegurado,
                "fecha_emision": p.fecha_emision,
                "fecha_inicio_vigencia": p.fecha_inicio_vigencia,
                "fecha_fin_vigencia": p.fecha_fin_registrada,
                "moneda": p.moneda,
                "suma_asegurada": p.suma_asegurada,
                "prima_neta": p.prima_neta,
                "prima_total": p.prima_total,
                "estado": estado,
            }
            if corte >= CANAL_VENTA:
                fila["canal_venta"] = p.canal_venta
            filas["poliza"].append(fila)

        for v in self.vehiculos:
            if not v.presente(corte):
                continue
            placa = v.placa
            if _activo(v.defecto, v.corregido, corte) and v.defecto == "PLACA_SIN_GUION":
                placa = placa.replace("-", "")
                error("VEH-VAL-01", "vehiculo", v.id_vehiculo, v.defecto)
            elif v.defecto == "POLIZA_NO_VEHICULAR":
                error("VEH-INT-01", "vehiculo", v.id_vehiculo, v.defecto)
            filas["vehiculo"].append({
                "fecha_corte": corte,
                "id_vehiculo": v.id_vehiculo,
                "id_poliza": v.id_poliza,
                "placa": placa,
                "nro_serie": v.nro_serie,
                "marca": v.marca,
                "modelo": v.modelo,
                "anio_fabricacion": v.anio_fabricacion,
                "uso": v.uso,
                "valor_comercial": v.valor_comercial,
            })

        fugas = set()
        if corte in FUGA_PII:
            # El sistema de siniestros escribe el DNI del reportante en la causa.
            candidatos = [s for s in self.siniestros if s.fecha_aviso <= corte and s.defecto is None]
            elegir = random.Random(f"{self.semilla}-fuga-{corte}")
            fugas = {s.id_siniestro: f"{elegir.randint(10000000, 79999999)}"
                     for s in elegir.sample(candidatos, FUGA_PII[corte])}
        for s in self.siniestros:
            if s.fecha_aviso > corte:
                continue
            if s.defecto == "FUERA_DE_VIGENCIA":
                error("SIN-CON-01", "siniestro", s.id_siniestro, s.defecto)
            elif s.defecto == "SIN_POLIZA":
                error("SIN-INT-01", "siniestro", s.id_siniestro, s.defecto)
            elif s.defecto == "AVISO_NO_CONVERTIBLE":
                error(HOMOLOGACION, "siniestro", s.id_siniestro, s.defecto)
            causa = s.causa
            if s.id_siniestro in fugas:
                causa = f"{s.causa} - reportado por DNI {fugas[s.id_siniestro]}"
                error(PRIVACIDAD, "siniestro", s.id_siniestro, "DNI_EN_CAUSA")
            estado = s.estado(corte)
            fila = {
                "fecha_corte": corte,
                "id_siniestro": s.id_siniestro,
                "id_poliza": s.id_poliza,
                "fecha_ocurrencia": s.fecha_ocurrencia,
                "fecha_aviso": s.fecha_aviso,
                "causa": causa,
                "monto_reclamado": s.monto_reclamado,
                "monto_pagado": s.monto_pagado_final if estado == "PAGADO" else None,
                "estado": estado,
            }
            if s.defecto == "AVISO_NO_CONVERTIBLE":
                fila[NO_CONVERTIBLE] = "fecha_aviso"
            filas["siniestro"].append(fila)

        for c in self.pagos:
            if c.desde > corte:
                continue
            fecha_pago = None
            if c.fecha_pago_real is not None and c.fecha_pago_real <= corte:
                estado = "PAGADO"
                if c.defecto == "PAGADO_SIN_FECHA":
                    error("PAG-CON-01", "pago", c.id_pago, c.defecto)
                else:
                    fecha_pago = c.fecha_pago_real
            elif c.fecha_vencimiento >= corte:
                estado = "PENDIENTE"
            elif _activo(c.defecto, c.corregido, corte) and c.defecto == "PENDIENTE_VENCIDA":
                # Nadie actualizó el estado de la cuota impaga.
                estado = "PENDIENTE"
                error("PAG-CON-02", "pago", c.id_pago, c.defecto)
            else:
                estado = "VENCIDO"
            fila = {
                "fecha_corte": corte,
                "id_pago": c.id_pago,
                "id_poliza": c.id_poliza,
                "nro_cuota": c.nro_cuota,
                "fecha_vencimiento": c.fecha_vencimiento,
                "fecha_pago": fecha_pago,
                "monto": c.monto,
                "medio_pago": c.medio_pago,
                "estado": estado,
            }
            if c.defecto == "IMPORTE_NO_CONVERTIBLE":
                error(HOMOLOGACION, "pago", c.id_pago, c.defecto)
                fila[NO_CONVERTIBLE] = "monto"
            filas["pago"].append(fila)

        self._ruido(corte, filas, error, con_error)
        return filas, manifiesto

    def _ruido(self, corte: date, filas: dict[str, list[dict]], error, con_error: set) -> None:
        """Errores transitorios del día: aparecen en la foto de hoy y se corrigen mañana."""
        r = random.Random(f"{self.semilla}-ruido-{corte}")
        factor = FACTOR_RUIDO[corte.weekday()]
        # Algunos días una fuente tiene un mal día y triplica sus errores.
        mal_dia = r.choice(TABLAS_CORTE) if r.random() < 0.06 else None

        def elegir(tabla: str, media: float, condicion) -> list[dict]:
            media *= self.escala * factor * (3.5 if tabla == mal_dia else 1.0)
            llave = {"persona": "id_persona", "poliza": "id_poliza", "vehiculo": "id_vehiculo",
                     "siniestro": "id_siniestro", "pago": "id_pago"}[tabla]
            libres = [f for f in filas[tabla] if (tabla, f[llave]) not in con_error and condicion(f)]
            return r.sample(libres, min(len(libres), _poisson(r, media)))

        for f in elegir("persona", 2.0, lambda f: f["tipo_documento"] != "RUC"):
            f["fecha_nacimiento"] = date(1900, 1, 1)
            error("PER-VAL-04", "persona", f["id_persona"], "NACIMIENTO_1900")
        for f in elegir("persona", 2.5, lambda f: f["email"] or f["celular"]):
            f["email"] = f["celular"] = None
            error("PER-COM-02", "persona", f["id_persona"], "SIN_CONTACTO")
        for f in elegir("persona", 1.5, lambda f: f["ubigeo"] is not None):
            f["ubigeo"] = r.choice(cat.UBIGEOS_INVALIDOS)
            error("PER-INT-01", "persona", f["id_persona"], "UBIGEO_INEXISTENTE")
        for f in elegir("poliza", 1.3, lambda f: True):
            estado = f["estado"]
            f["estado"] = r.choice([estado.capitalize() + " ", estado.lower(), " " + estado])
            error("POL-VAL-01", "poliza", f["id_poliza"], "ESTADO_SUCIO")
        for f in elegir("poliza", 2.0, lambda f: True):
            f["prima_total"] = round(f["prima_neta"] * 1.03, 2)
            error("POL-CON-02", "poliza", f["id_poliza"], "PRIMA_SIN_IGV")
        for f in elegir("vehiculo", 0.6, lambda f: True):
            f["anio_fabricacion"] = r.choice([1975, 2035])
            error("VEH-VAL-02", "vehiculo", f["id_vehiculo"], "ANIO_INVALIDO")
        for f in elegir("siniestro", 0.7, lambda f: f["estado"] == "PAGADO"):
            f["monto_pagado"] = round(f["monto_reclamado"] * 1.12, 2)
            error("SIN-CON-03", "siniestro", f["id_siniestro"], "MONTO_PAGADO_EXCEDE")
        for f in elegir("pago", 5.0, lambda f: f["estado"] == "PAGADO"):
            f["fecha_pago"] = None
            error("PAG-CON-01", "pago", f["id_pago"], "PAGADO_SIN_FECHA")
        if PICO_IMPORTES[0] <= corte <= PICO_IMPORTES[1]:
            # El banco cambia el formato del importe durante tres días.
            for f in elegir("pago", len(filas["pago"]) * 0.04 / self.escala, lambda f: True):
                f[NO_CONVERTIBLE] = "monto"
                error(HOMOLOGACION, "pago", f["id_pago"], "IMPORTE_NO_CONVERTIBLE")

    def llegada(self, tabla: str, corte: date) -> datetime:
        """Hora en que llega el archivo: el día siguiente, de madrugada, con algún retraso."""
        r = random.Random(f"{self.semilla}-llegada-{tabla}-{corte}")
        if tabla == "persona" and corte == PERSONA_TARDE:
            local = datetime.combine(corte + timedelta(days=2), time(10, 20), ZONA_LIMA)
        else:
            local = datetime.combine(corte + UN_DIA, time(5, 30), ZONA_LIMA)
            local += timedelta(minutes=r.randint(0, 170))
            if r.random() < 0.05:
                # Llega tarde, pero dentro del plazo de dos días.
                local += timedelta(hours=r.randint(4, 22))
        return local.astimezone(timezone.utc)


def generar(semilla: int = SEMILLA, escala: float = 1.0) -> Resultado:
    g = Generador(semilla, escala).generar()
    ref = {
        "ref_producto": [
            {"cod_producto": c, "nombre": n, "ramo": r, "activo": a} for c, n, r, a, _ in cat.PRODUCTOS
        ],
        "ref_ubigeo": [
            {"ubigeo": u, "departamento": d, "provincia": p, "distrito": di} for u, d, p, di in cat.UBIGEOS
        ],
    }
    por_corte: dict[str, dict[date, list[dict]]] = {t: {} for t in TABLAS_CORTE}
    # Las referencias llegan una vez, antes que las tablas del primer corte.
    llegadas = {
        (tabla, INICIO): datetime.combine(INICIO + UN_DIA, time(5, 0), ZONA_LIMA).astimezone(timezone.utc)
        for tabla in ref
    }
    manifiesto: list[dict] = []
    for corte in CORTES:
        filas, errores = g.foto(corte)
        manifiesto += errores
        for tabla in TABLAS_CORTE:
            por_corte[tabla][corte] = filas[tabla]
            llegadas[tabla, corte] = g.llegada(tabla, corte)

    for regla, tabla, corte, defecto in [
        ("GEN-OPO-01", "persona", PERSONA_TARDE, "PERSONA_TARDE"),
        ("GEN-VOL-01", "poliza", REPROCESO, "VOLUMEN_REPROCESO"),
    ]:
        manifiesto.append({
            "id_regla": regla,
            "tabla": tabla,
            "fecha_corte": corte,
            "llave": tabla,
            "descripcion": DESCRIPCIONES[defecto],
        })

    return Resultado(
        ref=ref,
        por_corte=por_corte,
        llegadas=llegadas,
        manifiesto=manifiesto,
        entidades={
            "persona": g.personas,
            "poliza": g.polizas,
            "vehiculo": g.vehiculos,
            "siniestro": g.siniestros,
            "pago": g.pagos,
        },
    )
