"""Funciones de SQL que cambian según la plataforma: cifrado y lectura de fechas.

El SQL se genera igual para BigQuery y DuckDB salvo estas funciones, que
sqlglot no traduce bien o que no existen en DuckDB.

Privacy Gate (HU-06), cifrado de los campos SENSIBLE_CIFRADO:
  BigQuery  DETERMINISTIC_ENCRYPT / AEAD.ENCRYPT con keysets de Tink.
  DuckDB    funciones de Python con AES-SIV (determinístico) y AES-GCM
            (aleatorio), equivalentes para correr local y en las pruebas.
Los keysets viven en dq_seguridad.llaves, un dataset al que solo accede el
flujo ("KMS simulado" en el sandbox; con facturación se envuelven con Cloud KMS).
El AAD de cada valor es "tabla.campo": un texto cifrado no sirve en otra columna.
"""

from __future__ import annotations

import os

from dqc.modelo import SEGURIDAD
from dqc.sql_util import literal

LLAVE_DETERMINISTICA = "pii_deterministica"
LLAVE_ALEATORIA = "pii_aleatoria"

# Una fila con los dos keysets; las expresiones los usan como k.k_det y k.k_ale.
SQL_LLAVES = (
    f"(SELECT MAX(IF(nombre = '{LLAVE_DETERMINISTICA}', keyset, NULL)) AS k_det, "
    f"MAX(IF(nombre = '{LLAVE_ALEATORIA}', keyset, NULL)) AS k_ale "
    f"FROM {SEGURIDAD}.llaves)"
)


def aad(tabla: str, campo: str) -> str:
    return literal(f"{tabla}.{campo}")


class FuncionesBigQuery:
    def parsear_fecha(self, expresion: str, formato: str) -> str:
        """Texto a DATE; NULL si no calza con el formato."""
        return f"SAFE.PARSE_DATE({literal(formato)}, {expresion})"

    def cifrar(self, expresion: str, modo: str, tabla: str, campo: str) -> str:
        if modo == "deterministico":
            return f"DETERMINISTIC_ENCRYPT(k.k_det, {expresion}, {aad(tabla, campo)})"
        return f"AEAD.ENCRYPT(k.k_ale, {expresion}, {aad(tabla, campo)})"

    def descifrar(self, expresion: str, modo: str, tabla: str, campo: str) -> str:
        if modo == "deterministico":
            return f"DETERMINISTIC_DECRYPT_STRING(k.k_det, {expresion}, {aad(tabla, campo)})"
        return f"AEAD.DECRYPT_STRING(k.k_ale, {expresion}, {aad(tabla, campo)})"


class FuncionesLocal:
    """Mismas firmas que en BigQuery, con funciones de DuckDB."""

    def parsear_fecha(self, expresion: str, formato: str) -> str:
        # sqlglot traduce SAFE.PARSE_DATE a un SAFE.CAST que DuckDB no entiende;
        # TRY_STRPTIME no es de BigQuery, así que sqlglot lo deja tal cual.
        return f"CAST(TRY_STRPTIME({expresion}, {literal(formato)}) AS DATE)"

    def cifrar(self, expresion: str, modo: str, tabla: str, campo: str) -> str:
        funcion = "dqc_cifrar_det" if modo == "deterministico" else "dqc_cifrar_ale"
        llave = "k.k_det" if modo == "deterministico" else "k.k_ale"
        return f"{funcion}({llave}, {expresion}, {aad(tabla, campo)})"

    def descifrar(self, expresion: str, modo: str, tabla: str, campo: str) -> str:
        funcion = "dqc_descifrar_det" if modo == "deterministico" else "dqc_descifrar_ale"
        llave = "k.k_det" if modo == "deterministico" else "k.k_ale"
        return f"{funcion}({llave}, {expresion}, {aad(tabla, campo)})"


def llaves_locales() -> dict[str, bytes]:
    """Llaves nuevas para DuckDB: 64 bytes para AES-SIV y 32 para AES-GCM."""
    return {LLAVE_DETERMINISTICA: os.urandom(64), LLAVE_ALEATORIA: os.urandom(32)}


def registrar_funciones_duckdb(con) -> None:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM, AESSIV
    from duckdb.sqltypes import BLOB, VARCHAR

    def cifrar_det(llave: bytes, valor: str, datos: str) -> bytes:
        return AESSIV(llave).encrypt(valor.encode(), [datos.encode()])

    def descifrar_det(llave: bytes, valor: bytes, datos: str) -> str:
        return AESSIV(llave).decrypt(valor, [datos.encode()]).decode()

    def cifrar_ale(llave: bytes, valor: str, datos: str) -> bytes:
        nonce = os.urandom(12)
        return nonce + AESGCM(llave).encrypt(nonce, valor.encode(), datos.encode())

    def descifrar_ale(llave: bytes, valor: bytes, datos: str) -> str:
        return AESGCM(llave).decrypt(valor[:12], valor[12:], datos.encode()).decode()

    # side_effects en el aleatorio: DuckDB no debe reutilizar un resultado (cada cifrado es distinto).
    con.create_function("dqc_cifrar_det", cifrar_det, [BLOB, VARCHAR, VARCHAR], BLOB)
    con.create_function("dqc_descifrar_det", descifrar_det, [BLOB, BLOB, VARCHAR], VARCHAR)
    con.create_function("dqc_cifrar_ale", cifrar_ale, [BLOB, VARCHAR, VARCHAR], BLOB, side_effects=True)
    con.create_function("dqc_descifrar_ale", descifrar_ale, [BLOB, BLOB, VARCHAR], VARCHAR)
