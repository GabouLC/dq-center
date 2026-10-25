# Levantar dq-center en local, paso a paso

Guía para cualquier agente de IA (Codex, Cursor, Copilot, Gemini, Claude) o persona que quiera
levantar el proyecto desde un clon limpio. Cada paso dice qué correr, cuánto tarda y cómo
comprobar que salió bien antes de seguir. Se probó el 24 de octubre de 2026 en Windows 11 con
Python 3.12.10, Node 24.22 y npm 11.19: en total, unos 9 minutos y 920 MB de disco.

No hace falta GCP, ni credenciales, ni conexión a ninguna base: los datos son sintéticos y todo
corre en DuckDB.

## Reglas para el agente

- No uses conectores ni datos de ninguna empresa. Los datos son 100 % sintéticos.
- No subas al repositorio `data/`, `.venv/`, `web/node_modules/` ni credenciales (el
  `.gitignore` ya los excluye).
- No cambies reglas, umbrales ni severidades de `config/`: cambiarían resultados ya aceptados.
  Las propuestas van en [docs/auditoria-reglas.md](docs/auditoria-reglas.md).
- Trabaja en una rama y abre un pull request; el CI corre las pruebas y el build en cada uno.
- Antes de decir «listo», corre las pruebas y el build (paso 6).

## 1. Requisitos

| Herramienta | Versión | Cómo comprobarla |
|---|---|---|
| Git | cualquiera reciente | `git --version` |
| Python | 3.12, la versión probada y la del CI | `python --version`; en Windows también `py -3.12 --version` |
| Node.js | 24 (la misma del CI) | `node --version` |

## 2. Clonar e instalar (unos 2 minutos)

**Windows (PowerShell):**

```powershell
git clone https://github.com/GabouLC/dq-center.git
cd dq-center
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[datagen,local,api,dev]"
```

**Linux o macOS:**

```bash
git clone https://github.com/GabouLC/dq-center.git
cd dq-center
python3.12 -m venv .venv
.venv/bin/python -m pip install -e ".[datagen,local,api,dev]"
```

No hace falta activar el entorno: todos los comandos llaman directo a `.venv`. En el resto de la
guía se usa la ruta de Windows (`.venv\Scripts\python`); en Linux o macOS, cámbiala por
`.venv/bin/python`.

**Comprobación:** `.venv\Scripts\python -c "import dqc, duckdb, fastapi; print('ok')"` imprime `ok`.

## 3. Generar los datos sintéticos (unos 25 segundos)

```powershell
.venv\Scripts\python -m dqc.datagen
```

Crea `data/landing` (un CSV por tabla y por día, del 1 de julio al 30 de septiembre de 2026, más
`entregas.json`) y `data/manifiesto_errores.parquet`, con los errores sembrados a propósito.

**Comprobación:** termina con una tabla de errores sembrados por regla; la última línea es
parecida a `VEH-VAL-02  57  41`. Existe `data\landing\entregas.json`.

## 4. Correr el pipeline (unos 4 minutos)

```powershell
.venv\Scripts\python -m dqc.pipeline --db data/dq.duckdb --hasta 2026-09-24
```

Procesa los cortes del 1 de julio al 24 de septiembre: ingesta a RAW, homologación y cifrado a
MASTER, 48 reglas de calidad, Quality & Privacy Gate y publicación en BUSINESS. Los días del 25 al
30 quedan pendientes para la simulación en vivo. Sin `--hasta` procesa los 92 días.

**Comprobación:** las últimas líneas son exactamente estas cuatro:

```
  ingesta          0 sin detectar     0 detectados de más
  homologacion     0 sin detectar     0 detectados de más
  reglas           0 sin detectar     0 detectados de más
  privacidad       0 sin detectar     0 detectados de más
```

Cualquier otro número significa que el flujo no detectó exactamente los errores sembrados: no
sigas, revisa el cambio que lo causó.

## 5. Levantar la API y el portal

En una terminal, la API (queda corriendo):

```powershell
.venv\Scripts\python -m dqc.api
```

**Comprobación:** en otra terminal, `curl http://127.0.0.1:8000/health/readiness` responde
`{"estado":"ok"}`.

En otra terminal, el portal (la primera vez, `npm ci` tarda alrededor de un minuto):

```powershell
cd web
npm ci
npm run dev
```

**Comprobación:** abre http://localhost:5173 y entra con una de las cuentas de demostración. Las
tres usan la contraseña `SmartDQ-2026`:

| Cuenta | Rol | Qué ve |
|---|---|---|
| `admin@demo.local` | Administrador | Todo, más reglas, ejecuciones, usuarios y auditoría |
| `gobierno@demo.local` | Gobierno de datos | Las secciones de consulta, con los campos sensibles |
| `lector@demo.local` | Lector | Las secciones de consulta, con los campos sensibles ocultos |

Con la API levantada, los días del 25 al 30 de septiembre llegan solos: un archivo cada 20
segundos. El portal muestra «En vivo» y se actualiza sin recargar.

## 6. Verificar antes de entregar un cambio (unos 2 minutos)

```powershell
.venv\Scripts\python -m pytest -q
cd web; npm run build
```

**Comprobación:** `127 passed` (o más, si agregaste pruebas) y `✓ built in …` sin errores de
tipos. Es lo mismo que corre el CI de GitHub Actions en cada pull request.

## Detener y volver a empezar

- Detén la API y el portal con `Ctrl+C` en sus terminales.
- Para repetir la demo en vivo: con la API detenida, vuelve a correr el paso 4.
- Para empezar de cero, borra la carpeta `data/` y repite desde el paso 3.

## Problemas frecuentes

| Síntoma | Causa | Qué hacer |
|---|---|---|
| `IO Error: Could not set lock on file "data/dq.duckdb"` al correr el pipeline | La API tiene abierta la base | Detén la API y vuelve a correr el paso 4 |
| `[Errno 10048]` o «address already in use» al levantar la API | El puerto 8000 está ocupado | Detén el otro proceso, o usa `python -m dqc.api --puerto 8001` y cambia el proxy en `web/vite.config.ts` |
| Vite abre el portal en 5174 en vez de 5173 | Otro portal ya usa el 5173 | Usa la dirección que muestra Vite, o cierra el otro portal |
| `pip` no encuentra versiones o falla al compilar | Otra versión de Python | Crea el entorno con `py -3.12` (Windows) o `python3.12` |
| El portal no carga datos o no deja entrar | La API no está levantada | Paso 5, primera terminal |
| `npm warn install-scripts …` al instalar | Aviso de npm 11 sobre scripts de instalación | No impide el build; se puede ignorar |
| PowerShell 5.1 no acepta `&&` | Esa versión no lo tiene | Separa los comandos con `;` o en líneas distintas |

## Más allá de lo local

- **Capturas de evidencia:** `.venv\Scripts\python scripts\capturas_portal.py` levanta su propia
  API y su propio portal en los puertos 8001 y 5174 (no choca con una demo abierta) y regenera
  `docs/evidencias/portal`. Necesita `pip install playwright` y `playwright install chromium`.
- **GCP (BigQuery y Firestore):** requiere acceso al proyecto `dq-center-gabou`; ver la sección
  «Correrlo en GCP» del [README](README.md).
- **Decisiones de diseño:** [docs/adr](docs/adr/README.md). **Seguimiento Scrum:** [docs/sprints](docs/sprints/README.md).
