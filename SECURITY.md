# Política de seguridad

## Alcance

dq-center (Smart-DQ) es un trabajo académico del curso Diseño e Implementación de Sistemas
(USMP, 2026-II, Grupo 6). Los datos son 100 % sintéticos y de una aseguradora ficticia
([ADR 0009](docs/adr/0009-datos-sinteticos.md)): no hay datos personales reales ni de ninguna
empresa. Aun así, el código maneja credenciales (contraseñas del portal, llaves de cifrado,
accesos a GCP y a Jira) y se trabaja como si fuera real.

La contraseña `SmartDQ-2026` es pública a propósito: es la de las cuentas `*@demo.local` del modo
local, y la API no arranca con ese atajo en Cloud Run ([ADR 0011](docs/adr/0011-inicio-de-sesion.md)).
No es un hallazgo.

## Cómo reportar una vulnerabilidad

Si encuentras una credencial expuesta, una forma de saltarse el login o los roles, o de ver
campos sensibles sin permiso:

1. **No abras un issue público** ni pongas el detalle en un pull request, comentario o chat del grupo.
2. Usa el aviso privado de GitHub: pestaña **Security > Report a vulnerability** del repositorio
   (disponible cuando el propietario lo active; ver la tabla de abajo).
3. Si esa opción aún no está activa, avisa directamente al Product Owner del proyecto
   (responsables en [docs/sprints/README.md](docs/sprints/README.md#responsables)), sin
   detalles en un canal público, para acordar cómo enviarlos.

Si lo que encontraste es una clave real (tuya o de alguien), avisa primero para que se **rote**:
borrarla del archivo no basta, porque queda en el historial de git.

## Controles vigentes

Solo lo que existe en el repositorio.

| Control | Qué hace | Dónde |
|---|---|---|
| CodeQL (SAST) | Análisis estático de Python y JavaScript/TypeScript en cada PR a `main`, en cada push a `main` y cada semana | `.github/workflows/codeql.yml` |
| gitleaks | Busca credenciales en cada PR y push a `main`; cada semana revisa todo el historial. Reglas y excepciones explicadas | `.github/workflows/secret-scan.yml`, `.gitleaks.toml` |
| Dependabot | Pull requests semanales de actualización de pip, npm (`web/`) y GitHub Actions. Ninguno se fusiona solo | `.github/dependabot.yml` |
| CI de pytest y build | Pruebas del motor, el flujo y la API (sobre DuckDB, sin credenciales) y tipos y build del portal | `.github/workflows/ci.yml` |
| Cifrado AEAD de datos personales (HU-06) | Los campos sensibles se cifran con llaves por campo (determinístico y aleatorio); el motor descifra solo lo que cada regla usa y solo en memoria | `src/dqc/pipeline/funciones.py`, [ADR 0006](docs/adr/0006-capas-y-privacy-gate.md), [ADR 0007](docs/adr/0007-pii-solo-en-memoria.md) |
| Contraseñas y bloqueo ([ADR 0011](docs/adr/0011-inicio-de-sesion.md)) | PBKDF2-SHA256 con 600 000 iteraciones y sal propia, nunca en claro; cinco intentos fallidos seguidos bloquean la cuenta 15 minutos; sesiones firmadas que vencen a las 8 horas | `src/dqc/api/autenticacion.py` |
| Roles y campos sensibles ocultos (HU-13) | Roles `admin`, `gobierno` y `lector`; quien no tiene el permiso de ver sensibles recibe esos campos ocultos | `src/dqc/api/app.py` |
| Auditoría | Inicios de sesión, intentos fallidos, bloqueos, cambios de contraseña y accesos denegados o restringidos quedan registrados; solo el rol `admin` la consulta | `src/dqc/api/app.py`, `src/dqc/api/configuracion.py` |

## A activar por el propietario del repositorio

Estos ajustes se hacen en la configuración de GitHub (no viven en el código). Hasta que alguien los
active, **no hay que darlos por vigentes**.

| Ajuste | Dónde en GitHub |
|---|---|
| Protección de la rama `main`: PR obligatorio, 1 aprobación, checks obligatorios (ver `.github/workflows/README.md`) | Settings > Branches |
| Secret scanning | Settings > Advanced Security |
| Push protection (bloquea el push que trae una clave) | Settings > Advanced Security |
| Dependabot alerts y Dependabot security updates | Settings > Advanced Security |
| Private vulnerability reporting (el aviso privado de arriba) | Settings > Advanced Security |

## Manejo de secretos

- Las credenciales van en variables de entorno (en Windows, variables de usuario) o en un `.env`
  local que git ignora. Nunca en archivos versionados, issues, capturas ni chats.
- `.env.example` lista las variables sin valores reales; cópialo a `.env` y complétalo.
- Dentro de GitHub Actions, los secretos van en Settings > Secrets and variables > Actions.
- `scripts/jira_sync.py` lee `JIRA_SITE`, `JIRA_EMAIL` y `JIRA_API_TOKEN` del entorno.
- En Cloud Run, `DQC_SECRETO` sale de Secret Manager y la API no arranca sin él.
- Si una clave real llegara a un commit, se rota primero (se genera una nueva y se revoca la vieja
  en el servicio que la emitió) y recién después se evalúa limpiar el historial, algo que se coordina
  con todo el equipo porque obliga a forzar el push.
