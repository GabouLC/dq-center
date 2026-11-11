# Workflows de GitHub Actions

Tres workflows. Cada uno corre en `ubuntu-latest` y no necesita credenciales de GCP ni de Jira.

| Workflow | Cuándo corre | Qué hace | Si falla |
|---|---|---|---|
| `ci.yml` | Push a `main` y todo PR | Dos jobs: instala el paquete y corre `pytest -q` (motor, flujo y API sobre DuckDB), y en `web/` hace `npm ci` y `npm run build` (tipos con `vue-tsc` y build de Vite) | Una prueba o el build se rompió: el cambio no está listo. Se arregla en el PR. |
| `codeql.yml` | PR a `main`, push a `main`, lunes 06:00 UTC y a mano | Análisis estático (SAST) del código propio en Python y en JavaScript/TypeScript. Sube los hallazgos a Security > Code scanning | CodeQL encontró un problema de seguridad nuevo en el código del PR (inyección, uso inseguro de datos, etc.). Revisa la alerta, corrige y no la cierres como falso positivo sin explicarlo. |
| `secret-scan.yml` | PR, push a `main`, lunes 07:00 UTC y a mano | gitleaks busca claves, tokens, llaves privadas y cadenas de conexión. En PR y push mira los commits nuevos; la corrida semanal y la manual revisan todo el historial. Reglas y excepciones en `.gitleaks.toml` | Hay algo con forma de credencial. Si es real, **rótala** (genera otra y revoca la vieja): borrarla del archivo no basta, queda en el historial. Si es un falso positivo, se explica en `.gitleaks.toml`, no se ignora el archivo entero. |

## Nombres de los checks (para la protección de rama)

Son los nombres de los jobs, tal como los muestra GitHub en el PR:

| Check | Workflow |
|---|---|
| `Motor, flujo y API (pytest)` | `ci.yml` |
| `Portal (tipos y build)` | `ci.yml` |
| `Analizar (python)` | `codeql.yml` |
| `Analizar (javascript-typescript)` | `codeql.yml` |
| `Gitleaks (secretos)` | `secret-scan.yml` |

GitHub solo deja elegir un check como obligatorio después de que corrió al menos una vez en el repo.
Los jobs de la corrida semanal (lunes) no son checks de PR.

## Dependabot

`.github/dependabot.yml` no es un workflow: GitHub abre cada lunes los PR de actualización de pip,
npm (`web/`) y GitHub Actions. Esos PR pasan por los mismos checks de arriba. `duckdb`, `faker`
(fijado a propósito por la semilla del generador) y `firebase` llegan en PR separados y no se
fusionan solos.

## Notas

- Los resultados de CodeQL salen en Security > Code scanning. Si se activa la «configuración
  predeterminada» de code scanning, hay que desactivarla: no convive con `codeql.yml`.
- `secret-scan.yml` usa `gitleaks/gitleaks-action`, que no pide licencia mientras el repo esté en una
  cuenta personal. Si pasa a una organización, hará falta el secreto `GITLEAKS_LICENSE` o cambiar a
  descargar el binario de gitleaks con versión y checksum fijos.
- La versión de gitleaks está fijada (`GITLEAKS_VERSION`) en el workflow. Si la subes, vuelve a
  probar `.gitleaks.toml` en local: `gitleaks git . --redact` y `gitleaks dir . --redact`.
- Los workflows de acciones de terceros se mantienen al día con Dependabot (`github-actions`).
