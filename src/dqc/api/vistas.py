"""Lo que muestra cada módulo del portal, calculado a partir de filas planas.

Sin FastAPI ni GCP: reciben filas de las vistas de contrato y la configuración,
y devuelven dicts listos para JSON. Cuando un corte tiene varias ejecuciones,
cuenta la última que terminó.
"""

from __future__ import annotations

import json
import unicodedata
from collections import Counter, defaultdict
from datetime import date

from dqc.modelo import BUSINESS, DIMENSIONES, DOMINIO_POR_TABLA, MASTER, RAW, TABLAS_CORTE
from dqc.motor.puntuacion import ResultadoRegla, scores
from dqc.motor.reglas import Regla, expandir
from dqc.pipeline.configuracion import Fuente

GRAVEDAD = {"SIN_DATOS": 0, "OK": 0, "ALERTA": 1, "FALLA": 2}
MASCARA_CIFRADO = "•••• cifrado"
MASCARA_RESTRINGIDO = "•••• restringido"


def ultimas_por_corte(ejecuciones: list[dict]) -> dict[date, dict]:
    ultimas: dict[date, dict] = {}
    for e in sorted(ejecuciones, key=lambda e: e["terminada_en"]):
        ultimas[e["fecha_corte"]] = e
    return dict(sorted(ultimas.items()))


def de_la_ejecucion(filas: list[dict], id_ejecucion: str) -> list[dict]:
    return [f for f in filas if f["id_ejecucion"] == id_ejecucion]


def _a_resultado(fila: dict) -> ResultadoRegla:
    return ResultadoRegla(
        id_regla=fila["id_regla"], tabla=fila["tabla"], dimension=fila["dimension"],
        severidad=fila["severidad"], tipo=fila["tipo"], umbral=fila["umbral"],
        fecha_corte=fila["fecha_corte"], universo=fila["universo"], cumplen=fila["cumplen"], fallidos=[],
    )


def _pct_pass(resultados: list[dict]) -> float | None:
    con_datos = [r for r in resultados if r["estado"] != "SIN_DATOS"]
    return sum(r["estado"] == "OK" for r in con_datos) / len(con_datos) * 100 if con_datos else None


# ── HU-09: dashboard ────────────────────────────────────────────────────────


def resumen(ultimas: dict[date, dict], resultados: list[dict], certificaciones: list[dict]) -> dict:
    """Score global, por tabla y dimensión, % de reglas en PASS y certificación de cada corte."""
    por_ejecucion: dict[str, list[dict]] = {}
    for r in resultados:
        por_ejecucion.setdefault(r["id_ejecucion"], []).append(r)
    cortes = []
    for corte, e in ultimas.items():
        filas = por_ejecucion.get(e["id_ejecucion"], [])
        s = scores([_a_resultado(r) for r in filas])
        cortes.append({
            "fecha_corte": corte,
            "id_ejecucion": e["id_ejecucion"],
            "terminada_en": e["terminada_en"],
            "global": s.global_,
            "pct_pass": _pct_pass(filas),
            "pct_pass_tabla": {t: _pct_pass([r for r in filas if r["tabla"] == t]) for t in TABLAS_CORTE},
            "por_tabla": {t: s.por_tabla.get(t) for t in TABLAS_CORTE},
            "por_dimension": {
                t: {d: s.por_dimension[t, d] for d in DIMENSIONES if (t, d) in s.por_dimension}
                for t in TABLAS_CORTE
            },
            "estados": dict(Counter(r["estado"] for r in filas)),
            "certificacion": {c["tabla"]: c["estado"] for c in de_la_ejecucion(certificaciones, e["id_ejecucion"])},
        })
    return {"cortes": cortes}


# ── Validaciones ────────────────────────────────────────────────────────────


def _orden_validacion(fila: dict):
    cumplimiento = fila["cumplimiento"]
    return (-GRAVEDAD[fila["estado"]], cumplimiento if cumplimiento is not None else 101, fila["id_regla"], fila["tabla"])


def validaciones(resultados_corte: list[dict], reglas: dict[str, dict]) -> list[dict]:
    """Reglas de un corte, de la más grave a la más sana."""
    filas = []
    for r in resultados_corte:
        config = reglas.get(r["id_regla"], {})
        filas.append({
            **{k: v for k, v in r.items() if k != "id_ejecucion"},
            "fallidos": r["universo"] - r["cumplen"],
            "descripcion": config.get("descripcion"),
            "definicion": {k: config[k] for k in ("campo", "campos", "patron", "valores", "filtro", "cumple", "ref", "ref_filtro", "limite") if config.get(k)},
        })
    return sorted(filas, key=_orden_validacion)


def comparar(resultados_a: list[dict], resultados_b: list[dict]) -> list[dict]:
    """Cambio de cada regla entre el corte A y el B; primero las que empeoraron."""
    a = {(r["id_regla"], r["tabla"]): r for r in resultados_a}
    b = {(r["id_regla"], r["tabla"]): r for r in resultados_b}
    filas = []
    for clave in sorted(a.keys() | b.keys()):
        ra, rb = a.get(clave), b.get(clave)
        ca = ra["cumplimiento"] if ra else None
        cb = rb["cumplimiento"] if rb else None
        ea = ra["estado"] if ra else "SIN_DATOS"
        eb = rb["estado"] if rb else "SIN_DATOS"
        delta = cb - ca if ca is not None and cb is not None else None
        filas.append({
            "id_regla": clave[0], "tabla": clave[1],
            "dimension": (rb or ra)["dimension"], "severidad": (rb or ra)["severidad"],
            "cumplimiento_a": ca, "cumplimiento_b": cb, "estado_a": ea, "estado_b": eb,
            "delta": delta,
            "empeoro": GRAVEDAD[eb] > GRAVEDAD[ea] or (delta is not None and delta < -1e-9),
        })
    return sorted(filas, key=lambda f: (not f["empeoro"], f["delta"] if f["delta"] is not None else 0))


# ── HU-13: enmascarado según la clasificación DAC y el rol ──────────────────


def enmascarar(detalle: str | None, clasificacion_tabla: dict[str, str], ve_sensibles: bool) -> tuple[dict | None, list[str]]:
    """La fila de una muestra con los campos protegidos ocultos, y los campos que se restringieron.

    SENSIBLE_CIFRADO nunca se muestra. SENSIBLE solo para roles autorizados. Una
    columna sin clasificar se trata como SENSIBLE hasta que el contrato la clasifique.
    """
    if detalle is None:
        return None, []
    fila = json.loads(detalle)
    restringidos = []
    for campo in fila:
        dac = clasificacion_tabla.get(campo, "SENSIBLE")
        if dac == "SENSIBLE_CIFRADO" and fila[campo] is not None:
            fila[campo] = MASCARA_CIFRADO
        elif dac == "SENSIBLE" and not ve_sensibles and fila[campo] is not None:
            fila[campo] = MASCARA_RESTRINGIDO
            restringidos.append(campo)
    return fila, restringidos


def enmascarar_valores(
    valores: str | None, destino_de: dict[str, str], clasificacion_tabla: dict[str, str], ve_sensibles: bool,
) -> tuple[str | None, list[str]]:
    """Los valores de una incidencia («COLUMNA=valor; …», con nombres de la fuente) con la misma regla.

    Cada columna de origen se clasifica por su campo de MASTER; si no tiene, se trata como SENSIBLE.
    """
    if not valores:
        return valores, []
    partes, restringidos = [], []
    for par in filter(None, (p.strip() for p in valores.split(";"))):
        origen, _, valor = par.partition("=")
        campo = destino_de.get(origen.upper(), origen)
        dac = clasificacion_tabla.get(campo, "SENSIBLE")
        if dac == "SENSIBLE_CIFRADO":
            valor = MASCARA_CIFRADO
        elif dac == "SENSIBLE" and not ve_sensibles:
            valor = MASCARA_RESTRINGIDO
            restringidos.append(campo)
        partes.append(f"{origen}={valor}")
    return "; ".join(partes), restringidos


# ── Fuentes ─────────────────────────────────────────────────────────────────


def fuentes(cargas: list[dict], incidencias: list[dict], contratos: dict[str, dict]) -> list[dict]:
    """Cada tabla con sus cargas (también las rechazadas) e incidencias de homologación por corte."""
    por_tabla = defaultdict(list)
    for fila in sorted(cargas, key=lambda f: f["cargado_en"]):
        por_tabla[fila["tabla"]].append(fila)
    incid = {(i["tabla"], i["fecha_corte"]): i["registros"] for i in incidencias}
    salida = []
    for tabla in TABLAS_CORTE:
        filas, anterior = [], None
        for f in por_tabla[tabla]:
            exitosa = f["estado"] == "EXITOSA"
            filas.append({
                **f,
                "variacion_pct": (f["filas"] / anterior - 1) * 100 if exitosa and anterior else None,
                "incidencias": incid.get((tabla, f["fecha_corte"]), 0) if exitosa else None,
            })
            if exitosa:
                anterior = f["filas"]
        contrato = contratos.get(tabla, {})
        salida.append({
            "tabla": tabla,
            "dominio": DOMINIO_POR_TABLA[tabla],
            "descripcion": contrato.get("descripcion"),
            "dueno": contrato.get("dueno"),
            "cargas": filas,
        })
    return salida


def estructura(tabla: str, ultimas: dict[date, dict], esquemas: list[dict]) -> dict:
    """Columnas de la tabla en cada corrida y qué cambió respecto del corte anterior."""
    por_ejecucion = defaultdict(list)
    for fila in esquemas:
        if fila["tabla"] == tabla:
            por_ejecucion[fila["id_ejecucion"]].append(fila)
    cortes, previas = [], None
    for corte, e in ultimas.items():
        columnas = sorted(por_ejecucion[e["id_ejecucion"]], key=lambda f: f["posicion"])
        actuales = {f["columna"]: f["tipo"] for f in columnas}
        cambios = {"agregadas": [], "eliminadas": [], "tipo_cambiado": []}
        if previas is not None:
            cambios["agregadas"] = [c for c in actuales if c not in previas]
            cambios["eliminadas"] = [c for c in previas if c not in actuales]
            cambios["tipo_cambiado"] = [
                {"columna": c, "antes": previas[c], "despues": t}
                for c, t in actuales.items() if c in previas and previas[c] != t
            ]
        cortes.append({
            "fecha_corte": corte,
            "columnas": [{"columna": f["columna"], "tipo": f["tipo"]} for f in columnas],
            **cambios,
        })
        previas = actuales
    return {"tabla": tabla, "cortes": cortes}


# ── Contrato de datos ───────────────────────────────────────────────────────


def contratos(
    contratos_config: dict[str, dict],
    reglas: list[Regla],
    esquema_actual: dict[str, list[tuple[str, str]]],
    resultados_ultimo: list[dict],
) -> list[dict]:
    """Campos pactados con su DAC, cobertura por reglas activas e impacto en los consumidores."""
    activas = [r for r in expandir(reglas) if r.activa]
    salida = []
    for tabla in TABLAS_CORTE:
        contrato = contratos_config.get(tabla)
        if not contrato:
            continue
        reales = dict(esquema_actual.get(tabla, []))
        campos = []
        for campo in contrato["campos"]:
            cubren = sorted(r.id for r in activas if r.tabla == tabla and campo["nombre"] in r.campos_usados())
            campos.append({
                **campo,
                "reglas": cubren,
                "en_esquema": campo["nombre"] in reales,
                "tipo_real": reales.get(campo["nombre"]),
                "protegido": campo.get("dac") != "SENSIBLE_CIFRADO" or reales.get(campo["nombre"]) == "BYTES",
            })
        pactados = {c["nombre"] for c in contrato["campos"]}
        de_la_tabla = [r for r in resultados_ultimo if r["tabla"] == tabla]
        en_falla = sorted(r["id_regla"] for r in de_la_tabla if r["estado"] == "FALLA")
        en_alerta = sorted(r["id_regla"] for r in de_la_tabla if r["estado"] == "ALERTA")
        salida.append({
            "tabla": tabla,
            "dominio": DOMINIO_POR_TABLA[tabla],
            "dueno": contrato["dueno"],
            "descripcion": contrato.get("descripcion"),
            "consumidores": contrato["consumidores"],
            "campos": campos,
            "cobertura": sum(1 for c in campos if c["reglas"]) / len(campos) * 100,
            "fuera_de_contrato": [c for c in reales if c not in pactados],
            "reglas_en_falla": en_falla,
            "reglas_en_alerta": en_alerta,
            "consumidores_afectados": contrato["consumidores"] if en_falla else [],
            "consumidores_en_riesgo": contrato["consumidores"] if en_alerta and not en_falla else [],
        })
    return salida


# ── HU-11: linaje ───────────────────────────────────────────────────────────


def _transformacion(columna, cifrado: str | None) -> str:
    pasos = []
    if columna.origen.lower() != columna.destino:
        pasos.append("renombrar")
    if columna.tipo != "STRING":
        pasos.append(f"convertir a {columna.tipo}" + (f" ({columna.formato})" if columna.formato else ""))
    if cifrado:
        pasos.append("cifrado determinístico" if cifrado == "deterministico" else "cifrado aleatorio")
    return " · ".join(pasos) or "copia"


# Por qué una regla bloqueante retiene un día, en palabras de negocio y según su dimensión. El texto
# del catálogo (`descripcion`) dice qué vigila la regla, no qué pasó; por eso se arma aquí.
MOTIVO_DIMENSION = {
    "oportunidad": "el archivo llegó tarde",
    "volumetria": "el volumen de registros cambió más de lo normal",
    "completitud": "faltan datos obligatorios",
    "unicidad": "hay registros duplicados",
    "validez": "hay valores con formato no válido",
    "consistencia": "hay datos que no cuadran entre sí",
    "integridad": "hay referencias a registros que no existen",
}
# Respaldo si la regla ya no está en el catálogo: el código va en su id (PER-COM-01).
DIMENSION_POR_CODIGO = {
    "OPO": "oportunidad", "VOL": "volumetria", "COM": "completitud", "UNI": "unicidad",
    "VAL": "validez", "CON": "consistencia", "INT": "integridad",
}
MOTIVO_PRIVACIDAD = {
    "PII_EN_CLARO": "datos personales sin cifrar",
    "CAMPO_SIN_CIFRAR": "campo sensible sin cifrar",
    "COLUMNA_SIN_CLASIFICAR": "columna sin clasificación de sensibilidad (DAC)",
}
DIMENSIONES_CON_CAMPO = {"completitud", "unicidad", "validez", "integridad"}


def texto_motivo_regla(id_regla: str, regla: dict | None) -> str:
    """Qué significa que la regla haya bloqueado: «el archivo llegó tarde», «faltan datos obligatorios en nro_documento»."""
    regla = regla or {}
    if regla.get("tipo") == "minimo_filas":
        return "llegaron muy pocos registros"
    codigo = id_regla.split("-")[1] if id_regla.count("-") == 2 else ""
    dimension = regla.get("dim") or DIMENSION_POR_CODIGO.get(codigo, "")
    texto = MOTIVO_DIMENSION.get(dimension, "falló una regla grave")
    campos = [c for c in (regla.get("campos") or [regla.get("campo")]) if c]
    return f"{texto} en {' y '.join(campos)}" if campos and dimension in DIMENSIONES_CON_CAMPO else texto


def motivos_de_retencion(certificacion: dict, hallazgos_dia: list[dict], reglas: dict[str, dict]) -> list[dict]:
    """Por qué un día no se publicó: las reglas bloqueantes y los hallazgos de privacidad que bloquean."""
    motivos = []
    for id_regla in (r for r in certificacion["reglas_bloqueantes"].split(",") if r):
        if id_regla == "SIN_DATOS":  # ninguna regla pudo evaluarse
            motivos.append({"tipo": "regla", "id": id_regla, "texto": "ninguna de sus reglas pudo evaluarse"})
        else:
            motivos.append({"tipo": "regla", "id": id_regla, "texto": texto_motivo_regla(id_regla, reglas.get(id_regla))})
    agrupados = Counter((h["tipo"], h["columna"]) for h in hallazgos_dia if h["bloqueante"])
    for (tipo, columna), n in sorted(agrupados.items()):
        texto = f"{MOTIVO_PRIVACIDAD.get(tipo, tipo)} en {columna}"
        if tipo == "PII_EN_CLARO":
            texto += f" · {n} {'registro' if n == 1 else 'registros'}"
        motivos.append({"tipo": "privacidad", "id": tipo, "texto": texto})
    return motivos


def linaje(
    tabla: str, fuente: Fuente, contrato: dict, certificaciones_tabla: list[dict],
    hallazgos_tabla: list[dict] | None = None, reglas: dict[str, dict] | None = None,
) -> dict:
    """Recorrido RAW -> MASTER -> BUSINESS de una tabla y de cada uno de sus campos.

    `retenidos` dice, por cada día que no se publicó, qué lo retuvo (regla bloqueante o privacidad).
    """
    dac = {c["nombre"]: c for c in contrato["campos"]}
    publicados = sorted(c["fecha_corte"] for c in certificaciones_tabla if c["publicado"])
    no_publicadas = sorted((c for c in certificaciones_tabla if not c["publicado"]), key=lambda c: c["fecha_corte"])
    retenidos = [
        {
            "fecha_corte": c["fecha_corte"],
            "motivos": motivos_de_retencion(
                c, [h for h in hallazgos_tabla or [] if h["id_ejecucion"] == c["id_ejecucion"]], reglas or {}
            ),
        }
        for c in no_publicadas
    ]
    nodos = [
        {"id": "raw", "capa": "RAW", "objeto": f"{RAW}.{fuente.archivo}", "detalle": f"CSV {fuente.archivo}_AAAAMMDD_NN.csv tal como llega"},
        {"id": "master", "capa": "MASTER", "objeto": f"{MASTER}.{tabla}", "detalle": "Modelo estándar, PII cifrada; aquí corre el motor de calidad"},
        {"id": "p", "capa": "BUSINESS", "objeto": f"{BUSINESS}.p_{tabla}", "detalle": "Solo cortes certificados"},
        {"id": "v", "capa": "BUSINESS", "objeto": f"{BUSINESS}.v_{tabla}", "detalle": "Último corte certificado"},
    ]
    aristas = [
        {"desde": "raw", "hacia": "master", "proceso": "Ingesta validada → homologación + Privacy Gate"},
        {"desde": "master", "hacia": "p", "proceso": "Quality & Privacy Gate → publicación"},
        {"desde": "p", "hacia": "v", "proceso": "Último corte certificado"},
    ]
    campos = []
    for c in fuente.columnas:
        info = dac.get(c.destino, {})
        campos.append({
            "raw": c.origen,
            "master": c.destino,
            "business": c.destino,
            "transformacion": _transformacion(c, info.get("cifrado")),
            "dac": info.get("dac", "SIN_CLASIFICAR"),
            "en_contrato": c.destino in dac,
        })
    return {
        "tabla": tabla,
        "dominio": DOMINIO_POR_TABLA[tabla],
        "nodos": nodos,
        "aristas": aristas,
        "campos": campos,
        "cortes_publicados": publicados,
        "cortes_retenidos": [r["fecha_corte"] for r in retenidos],
        "retenidos": retenidos,
    }


# ── HU-12: certificación integral ───────────────────────────────────────────


def ultimo_certificado(historia: dict[date, dict[str, str]], tabla: str, corte: date) -> date | None:
    """Último día, hasta `corte` inclusive, en que la tabla llegó a BUSINESS: lo que `v_<tabla>` mostraba entonces.

    `historia` es el estado de certificación de cada tabla por día. Una tabla con observaciones también se publica.
    """
    dias = [d for d, estados in historia.items() if d <= corte and estados.get(tabla) not in (None, "NO_CERTIFICADO")]
    return max(dias, default=None)


def certificacion(
    corte: date,
    certificaciones_corte: list[dict],
    hallazgos_corte: list[dict],
    resultados_corte: list[dict],
    contratos_config: dict[str, dict],
    esquema_actual: dict[str, list[tuple[str, str]]],
    historia: dict[date, dict[str, str]],
) -> list[dict]:
    """Calidad, privacidad y trazabilidad de cada tabla en un corte.

    Cada tabla dice también su `ultimo_certificado`, calculado con la `historia` de certificaciones: el día
    que negocio veía ese día (el mismo corte si se publicó; `None` si todavía no hay ningún día certificado).
    """
    salida = []
    for c in sorted(certificaciones_corte, key=lambda c: TABLAS_CORTE.index(c["tabla"])):
        tabla = c["tabla"]
        resultados = [r for r in resultados_corte if r["tabla"] == tabla]
        reales = dict(esquema_actual.get(tabla, []))
        cifrados = [f["nombre"] for f in contratos_config.get(tabla, {}).get("campos", []) if f.get("cifrado")]
        hallazgos = [h for h in hallazgos_corte if h["tabla"] == tabla]
        agrupados = Counter((h["tipo"], h["columna"], h["bloqueante"]) for h in hallazgos)
        salida.append({
            "tabla": tabla,
            "dominio": c["dominio"],
            "estado": c["estado"],
            "calidad": {
                "ok": c["calidad_ok"],
                "pct_pass": _pct_pass(resultados),
                "reglas_bloqueantes": [r for r in c["reglas_bloqueantes"].split(",") if r],
                "reglas_con_observacion": [r for r in c["reglas_con_observacion"].split(",") if r],
                "por_nivel": {
                    n: dict(Counter(r["estado"] for r in resultados if r["nivel"] == n)) for n in ("N1", "N2", "N3")
                },
            },
            "privacidad": {
                "ok": c["privacidad_ok"],
                "campos_cifrados": [{"campo": f, "protegido": reales.get(f) == "BYTES"} for f in cifrados],
                "hallazgos": [
                    {"tipo": t, "columna": col, "bloqueante": b, "registros": n} for (t, col, b), n in sorted(agrupados.items())
                ],
            },
            "trazabilidad": {
                "id_ejecucion": c["id_ejecucion"],
                "version_motor": c["version_motor"],
                "version_reglas": c["version_reglas"],
                "cobertura": c["cobertura"],
                "certificado_en": c["certificado_en"],
                "publicado": c["publicado"],
                "objeto_business": f"{BUSINESS}.p_{tabla}" if c["publicado"] else None,
                "ultimo_certificado": ultimo_certificado(historia, tabla, corte),
            },
            "fecha_corte": corte,
        })
    return salida


# ── HU-10: glosario ─────────────────────────────────────────────────────────


def _normalizar(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


def buscar_glosario(terminos: list[dict], q: str | None, dominio: str | None) -> list[dict]:
    """Búsqueda sin distinguir mayúsculas ni tildes, en término, sinónimos y definición."""
    encontrados = []
    for t in terminos:
        if dominio and _normalizar(t["dominio"]) != _normalizar(dominio):
            continue
        if q:
            texto = _normalizar(" ".join([t["termino"], t["definicion"], *t.get("sinonimos", [])]))
            if not all(palabra in texto for palabra in _normalizar(q).split()):
                continue
        encontrados.append(t)
    # Primero los que coinciden en el término mismo.
    clave = _normalizar(q or "")
    return sorted(encontrados, key=lambda t: (clave not in _normalizar(t["termino"]), _normalizar(t["termino"])))
