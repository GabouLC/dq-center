# Brief de dq-center

> **Documento histórico (15 de octubre de 2026).** No se actualiza. Después cambiaron los datos
> (92 cortes diarios, [ADR 0012](adr/0012-cortes-diarios.md)), el inicio de sesión y los roles
> ([ADR 0011](adr/0011-inicio-de-sesion.md)), el indicador del portal
> ([ADR 0015](adr/0015-indicador-pass.md)) y el uso del sandbox ([ADR 0008](adr/0008-sandbox.md)).
> Lo vigente está en el [README](../README.md).

Especificación de origen del proyecto. El catálogo de reglas vive aparte, en
[config/reglas_iniciales.yaml](../config/reglas_iniciales.yaml).

## Objetivo

Construir desde cero un "Data Quality Center": un portal de calidad de datos para una
aseguradora **ficticia**, desplegado en un GCP personal y versionado en un repo privado
de GitHub personal. Todo con datos sintéticos.

**Regla:** no se usa ningún conector corporativo (Interseguro: bases, Gmail, Drive,
Jira). Nada de datos, nombres de tablas ni código de la empresa.

## Preparación

- git, gh, gcloud, Python 3.12+ y Node 20+.
- gcloud y gh con la cuenta personal (`gabrielomchos88@gmail.com`, GitHub `GabouLC`).
- Proyecto GCP nuevo en `us-central1` (BigQuery en `US`), con facturación enlazada y
  alerta de presupuesto de USD 10 (la alerta avisa, no corta el gasto).
- Repo privado `dq-center`, con un commit por etapa.

## Arquitectura (barata, capa gratuita)

- **BigQuery:** dataset `dq_raw` (tablas sintéticas) y `dq_engine` (ejecuciones,
  resultados por regla, muestras de registros fallidos y foto del esquema por corrida).
- **Firestore** (modo nativo, capa gratuita): reglas, umbrales, contratos y
  usuarios/roles, para que editar desde el portal sea rápido. Nada de Cloud SQL.
- **Motor en Python:** lee las reglas activas desde Firestore, genera el SQL de cada
  regla según su tipo, ejecuta y guarda resultados por fecha de corte. Corre como
  Cloud Run Job con Cloud Scheduler diario; también a demanda desde el portal.
- **API** FastAPI y **frontend** Vue 3 (Vite), ambos en Cloud Run.
- **Login** con Google vía Firebase Authentication; la API valida el token y el rol
  (admin / lector). Sin balanceador de carga ni IAP.
- **Artifact Registry** con política de limpieza (conservar las últimas 5 imágenes).
- **CI/CD** con GitHub Actions y Workload Identity Federation (sin llaves JSON).

## Puntuación

- Cumplimiento de una regla = filas que cumplen / filas del universo × 100.
  Universo vacío = "sin datos" (no puntúa). En `unico` no cumplen TODAS las filas cuya
  llave se repite. `frescura`, `variacion_volumen` y `minimo_filas` valen 100 o 0.
- Estado: **OK** si cumplimiento ≥ umbral; **ALERTA** si queda hasta 2 puntos por
  debajo; **FALLA** si queda más abajo.
- Score de dimensión y de tabla = promedio del cumplimiento ponderado por severidad
  (CRITICA 3, ALTA 2, MEDIA 1). Score global = promedio de las 5 tablas por corte.

## Módulos del portal

1. **Resumen por tabla:** score global y por dimensión, tendencia por fecha de corte.
2. **Validaciones:** reglas con % de cumplimiento, umbral, estado y muestra de fallidos;
   comparar dos cortes y ver qué reglas empeoraron.
3. **Fuentes:** tablas de origen, universo (conteos por corte, desde `registro_cargas`)
   y estructura (esquema por corrida y cambios detectados).
4. **Contrato de datos:** campos, tipos y obligatoriedad; cobertura e impacto.
5. **Configuración:** crear, editar y desactivar reglas y umbrales sin tocar código.
6. **Usuarios y roles.**

Fuera de alcance por ahora: módulos de marketing y de RR.HH.

## Listo cuando

- Las 36 reglas del catálogo están cargadas (48 al expandir las transversales).
- El motor corre los 6 cortes y, por cada regla y corte, los fallidos detectados
  coinciden exactamente con `manifiesto_errores`.
- Las pruebas (pytest) del motor y de la API pasan en GitHub Actions.
- El README explica arquitectura, costos y cómo correrlo local y en GCP.

## Forma de trabajo

Por etapas: infra → datos sintéticos y manifiesto → reglas en Firestore → motor →
API → web → deploy → README. Todo por CLI y scripts reproducibles; el navegador solo
para logins o pasos de consola.

## Modelo de datos (dataset `dq_raw`)

Cortes: fin de mes, de 2026-04-30 a 2026-09-30 (6). Crecimiento normal ~2 % por mes.
Las tablas por corte llevan `fecha_corte DATE` y se particionan por ella.
Generador en Python con Faker y semilla fija. Se carga corte por corte y el motor
corre después de cada carga, para simular la historia (incluido el cambio de esquema).
Los datos limpios cumplen el 100 % de las reglas; solo fallan las filas sembradas.

### Referencia (sin corte)

- **ref_producto** (~15, 2 inactivos): `cod_producto`, `nombre`,
  `ramo` [VEHICULAR|SOAT|VIDA|SALUD|HOGAR], `activo BOOL`
- **ref_ubigeo** (~120 distritos reales del INEI): `ubigeo` (6 dígitos),
  `departamento`, `provincia`, `distrito`

### Por corte

- **persona** (~5 000): `id_persona`, `tipo_documento` [DNI|CE|RUC],
  `nro_documento STRING`, `nombres`, `apellido_paterno`, `apellido_materno`,
  `razon_social`, `fecha_nacimiento`, `sexo` [M|F], `email`, `celular STRING`,
  `ubigeo STRING`, `fecha_alta`
- **poliza** (~8 000): `id_poliza`, `nro_poliza` ('POL-AAAA-NNNNNN'), `cod_producto`,
  `id_contratante`, `id_asegurado`, `fecha_emision`, `fecha_inicio_vigencia`,
  `fecha_fin_vigencia`, `moneda` [PEN|USD], `suma_asegurada`, `prima_neta`,
  `prima_total` (= prima_neta × 1.03 derecho de emisión × 1.18 IGV), `estado`
- **vehiculo** (~3 000, solo pólizas VEHICULAR o SOAT): `id_vehiculo`, `id_poliza`,
  `placa` ('ABC-123'), `nro_serie` (VIN de 17), `marca`, `modelo`,
  `anio_fabricacion`, `uso` [PARTICULAR|TAXI|CARGA], `valor_comercial`
- **siniestro** (~600): `id_siniestro`, `id_poliza`, `fecha_ocurrencia`,
  `fecha_aviso`, `causa`, `monto_reclamado`, `monto_pagado`, `estado`
- **pago** (~40 000 cuotas): `id_pago`, `id_poliza`, `nro_cuota`,
  `fecha_vencimiento`, `fecha_pago`, `monto`, `medio_pago`,
  `estado` [PENDIENTE|PAGADO|VENCIDO]

### Control

- **registro_cargas:** `tabla`, `fecha_corte`, `cargado_en TIMESTAMP`, `filas`
  (una fila por tabla y corte; de aquí salen oportunidad y volumetría).
- **manifiesto_errores:** `id_regla`, `tabla`, `fecha_corte`, `llave`, `descripcion`
  (cada fila sembrada, registrada en TODAS las reglas que debe romper).

### Contratos

En Firestore, uno por tabla: campos con tipo, obligatorio y descripción, un dueño
ficticio y consumidores ficticios: "Reporte regulatorio mensual", "Tablero comercial",
"Modelo de siniestralidad", "Campañas de renovación".

- Cobertura = % de campos del contrato con al menos una regla activa.
- Impacto = consumidores afectados cuando falla una regla de esa tabla.

## Escenarios sembrados

En todos los cortes (tasas aproximadas; el manifiesto es la fuente de verdad):

- persona duplicada con el mismo documento (~0.5 %).
- DNI de 7 dígitos porque perdió el cero inicial al cargarse como número (~1 %).
- `fecha_nacimiento` '1900-01-01' usada como valor por defecto (~0.5 %).
- celular de 8 dígitos o teléfono fijo (~4 %); email sin dominio (~2 %);
  ubigeo que no existe (~1.5 %).
- estado de póliza con minúsculas o espacios, p. ej. 'Vigente ' (~0.3 %).
- póliza con fin de vigencia antes del inicio (~0.4 %); póliza VIGENTE ya vencida (~1 %).
- `prima_total` calculada sin IGV (~1 %).
- placa sin guion, p. ej. 'ABC123' (~3 %); vehículo colgado de una póliza que no es
  vehicular (~0.5 %).
- siniestro fuera de la vigencia de su póliza (~0.7 %); siniestro sin póliza (~0.5 %).
- cuota PAGADO sin `fecha_pago` (~0.3 %); cuota PENDIENTE ya vencida (~3 %).

Eventos puntuales:

- **2026-07-31:** la carga de persona llega 2 días tarde y trae 40 `nro_documento` nulos.
- **2026-08-31:** un reproceso duplica 12 pólizas y el volumen de poliza sube 22 %.
- **2026-09-30:** se corrigen los DNI de 7 dígitos (la tendencia mejora), 30 pólizas
  nuevas usan un producto inactivo y poliza estrena la columna `canal_venta`
  (Fuentes > Estructura debe detectarla).

Objetivo: que haya reglas en OK, ALERTA y FALLA, y que el Resumen muestre la caída de
julio–agosto y la recuperación de septiembre.
