"""Configuración local del portal (data/config_local.json): se completa con lo nuevo de config/*.yaml."""

import json
import os

from dqc.api.configuracion import ConfiguracionLocal, cargar_glosario
from dqc.modelo import ESQUEMAS
from dqc.motor.reglas import cargar_yaml

from conftest import CONFIG


def _leer(ruta) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def _escribir(ruta, datos: dict) -> None:
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")


def test_un_json_viejo_recibe_la_regla_y_el_termino_que_le_faltan(tmp_path):
    ruta = tmp_path / "config_local.json"
    ConfiguracionLocal(ruta, CONFIG)
    # Un JSON sembrado antes de que existieran PER-VAL-06 y «Carné de extranjería», con ediciones del portal
    viejo = _leer(ruta)
    del viejo["reglas"]["PER-VAL-06"], viejo["glosario"]["ce"]
    viejo["reglas"]["PER-VAL-03"] = {**viejo["reglas"]["PER-VAL-03"], "umbral": 95, "actualizado_por": "admin@demo.local"}
    viejo["glosario"]["dni"] = {**viejo["glosario"]["dni"], "definicion": "Texto editado en el portal.", "actualizado_por": "gobierno@demo.local"}
    viejo["usuarios"]["nuevo@demo.local"] = "lector"
    viejo["auditoria"].append({"accion": "ACTUALIZAR", "email": "admin@demo.local", "recurso": "reglas/PER-VAL-03"})
    _escribir(ruta, viejo)

    config = ConfiguracionLocal(ruta, CONFIG)

    # Lo que faltaba llega del YAML
    assert config.regla("PER-VAL-06")["valores"] == ["DNI", "CE", "RUC"]
    assert config.regla("PER-VAL-06")["actualizado_por"] == "semilla"
    assert next(t for t in config.glosario() if t["id"] == "ce")["termino"] == "Carné de extranjería"
    # Lo que ya existía no se pisa: las ediciones del portal ganan
    assert config.regla("PER-VAL-03")["umbral"] == 95 and config.regla("PER-VAL-03")["actualizado_por"] == "admin@demo.local"
    assert next(t for t in config.glosario() if t["id"] == "dni")["definicion"] == "Texto editado en el portal."
    # Usuarios y auditoría quedan como estaban
    assert config.usuarios()["nuevo@demo.local"] == "lector"
    assert config.auditoria(1)[0]["recurso"] == "reglas/PER-VAL-03"
    # Y se guardó: otra instancia lo ve igual sin volver a leer el YAML
    guardado = _leer(ruta)
    assert "PER-VAL-06" in guardado["reglas"] and "ce" in guardado["glosario"]
    assert len(guardado["reglas"]) == len(cargar_yaml(CONFIG / "reglas_iniciales.yaml"))
    assert len(guardado["glosario"]) == len(cargar_glosario(CONFIG / "glosario.yaml"))


def test_los_contratos_se_refrescan_desde_el_yaml(tmp_path):
    ruta = tmp_path / "config_local.json"
    ConfiguracionLocal(ruta, CONFIG)
    viejo = _leer(ruta)
    campo = next(c for c in viejo["contratos"]["persona"]["campos"] if c["nombre"] == "fecha_corte")
    actual = campo["descripcion"]
    campo["descripcion"] = "Fecha de la foto mensual"  # texto de un contrato que ya cambió en el YAML
    viejo["contratos"]["pago"]["campos"].append({"nombre": "campo_viejo", "tipo": "STRING", "dac": "PUBLICO"})
    _escribir(ruta, viejo)

    contratos = ConfiguracionLocal(ruta, CONFIG).contratos()

    persona = next(c for c in contratos["persona"]["campos"] if c["nombre"] == "fecha_corte")
    assert persona["descripcion"] == actual
    assert "campo_viejo" not in {c["nombre"] for c in contratos["pago"]["campos"]}
    assert _leer(ruta)["contratos"] == contratos


def test_si_no_cambia_nada_no_reescribe_el_archivo(tmp_path):
    ruta = tmp_path / "config_local.json"
    ConfiguracionLocal(ruta, CONFIG)
    antes = ruta.read_bytes()
    os.utime(ruta, ns=(1_000_000_000, 1_000_000_000))  # una fecha vieja: si se reescribe, cambia

    ConfiguracionLocal(ruta, CONFIG)

    assert ruta.read_bytes() == antes
    assert ruta.stat().st_mtime_ns == 1_000_000_000


# ── Glosario (HU-10) ────────────────────────────────────────────────────────


def test_el_glosario_tiene_42_terminos_con_campos_que_existen_en_el_esquema():
    terminos = cargar_glosario(CONFIG / "glosario.yaml")
    ids = [t["id"] for t in terminos]
    assert len(terminos) == 42 and len(set(ids)) == 42
    for t in terminos:
        for campo in t.get("campos", []):
            tabla, _, columna = campo.partition(".")
            assert columna in {c for c, _ in ESQUEMAS[tabla]}, (t["id"], campo)


def test_el_glosario_define_el_carne_de_extranjeria_y_el_estado_de_la_cuota():
    por_id = {t["id"]: t for t in cargar_glosario(CONFIG / "glosario.yaml")}
    ce = por_id["ce"]
    assert (ce["termino"], ce["dominio"]) == ("Carné de extranjería", "Persona")
    assert set(ce["sinonimos"]) == {"CE", "Carnet de extranjería"}
    assert ce["campos"] == ["persona.tipo_documento", "persona.nro_documento"]
    cuota = por_id["estado-cuota"]
    assert (cuota["termino"], cuota["dominio"], cuota["campos"]) == ("Estado de la cuota", "Póliza", ["pago.estado"])
    assert all(estado in cuota["definicion"] for estado in ("PENDIENTE", "PAGADO", "VENCIDO"))
