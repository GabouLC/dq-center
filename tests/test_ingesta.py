"""Validación de estructura de los CSV (HU-01), con archivos armados a mano."""

from datetime import date, datetime, timezone

import pytest

from dqc.pipeline.configuracion import ColumnaFuente, Fuente
from dqc.pipeline.ingesta import EXITOSA, RECHAZADA, Entrega, validar_csv

FUENTE = Fuente(
    tabla="pago",
    archivo="cobranzas",
    columnas=(
        ColumnaFuente("ID_CUOTA", "id_pago", "INT64"),
        ColumnaFuente("IMPORTE", "monto", "FLOAT64"),
        ColumnaFuente("CANAL", "canal", opcional=True),
    ),
)


def _validar(tmp_path, contenido: bytes):
    (tmp_path / "a.csv").write_bytes(contenido)
    entrega = Entrega("a.csv", "pago", date(2026, 4, 30), datetime(2026, 5, 1, 11, tzinfo=timezone.utc))
    return validar_csv(tmp_path, entrega, FUENTE)


def test_archivo_valido_se_carga_tal_cual(tmp_path):
    carga = _validar(tmp_path, b'"ID_CUOTA","IMPORTE"\n"1"," 10.50 "\n')
    assert carga.estado == EXITOSA and carga.filas == 1 and carga.detalle is None
    assert carga.datos.to_pylist() == [
        {"ID_CUOTA": "1", "IMPORTE": " 10.50 ", "fecha_corte": date(2026, 4, 30), "archivo": "a.csv"}
    ]


@pytest.mark.parametrize("contenido, motivo", [
    (b'"ID_CUOTA"\n"1"\n', "faltan columnas: IMPORTE"),
    (b'"ID_CUOTA","IMPORTE"\n"1","2","3"\n', "la línea 2 tiene 3 campos"),
    (b'"ID_CUOTA","IMPORTE","IMPORTE"\n', "columnas repetidas: IMPORTE"),
    (b"", "vacío"),
    ('"ID_CUOTA","IMPORTE"\n"1","ñ"\n'.encode("latin-1"), "UTF-8"),
])
def test_estructura_invalida_se_rechaza(tmp_path, contenido, motivo):
    carga = _validar(tmp_path, contenido)
    assert carga.estado == RECHAZADA and carga.datos is None
    assert motivo in carga.detalle


def test_columna_desconocida_se_acepta_y_se_anota(tmp_path):
    carga = _validar(tmp_path, b'"ID_CUOTA","IMPORTE","NUEVA"\n"1","2","x"\n')
    assert carga.estado == EXITOSA
    assert carga.detalle == "columnas no mapeadas: NUEVA"
    assert "NUEVA" in carga.datos.column_names
