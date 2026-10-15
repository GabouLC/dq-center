# 0007 · El motor descifra solo lo que cada regla usa, en memoria

**Estado:** aceptada (2026-10-15). Ajusta la sección 9.3 del Documento de Arquitectura.

## Contexto

Varias reglas validan el formato de campos que en MASTER están cifrados: el DNI
debe tener 8 dígitos, el correo debe tener dominio y el celular debe empezar con 9.
No se puede validar un formato sobre texto cifrado.

## Decisión

Cuando una regla usa campos cifrados, el motor envuelve la tabla en una
subconsulta que descifra solo esos campos. El texto claro existe únicamente
dentro de esa consulta y nunca se escribe. Las muestras de registros fallidos se
leen de MASTER tal cual, cifradas, y el portal muestra los campos cifrados
enmascarados. Así se cumple el principio del documento: el portal muestra
indicadores, no datos personales.

## Consecuencias

- La cuenta de servicio del motor es la única, además del flujo, que puede leer
  las llaves. Es el componente privilegiado.
- Quien revisa un fallido ve qué registro y qué regla fallaron, pero no el DNI en
  claro. Para verlo hace falta el procedimiento de excepción del caso de negocio.
