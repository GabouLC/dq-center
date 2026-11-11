# 0017 · Controles automáticos del repositorio

**Estado:** aceptada (2026-11-11).

## Contexto

dq-center es un trabajo académico con datos sintéticos, pero maneja credenciales reales (la cuenta
de GCP, el token de Jira, el secreto que firma las sesiones) y lo editan varias personas. Una
credencial subida por error o una dependencia vulnerable no se verían hasta tarde. El proyecto del
Taller de Proyectos (AgroSmart Insights) ya resolvió esto con un conjunto de controles; aquí se
adaptan los que aplican.

## Decisión

- **CodeQL** (Python y JavaScript/TypeScript) en cada pull request, en cada push a `main` y cada
  semana.
- **gitleaks** sobre todo el historial en cada pull request y cada semana, con una sola excepción
  documentada: la contraseña de demostración pública `SmartDQ-2026`.
- **Dependabot** semanal (pip, npm y acciones), sin automerge. `duckdb`, `faker` y `firebase` van en
  un pull request aparte porque pueden cambiar resultados.
- **Protección de `main`:** los cambios entran por pull request con los checks obligatorios en
  verde (pytest, build del portal, los dos análisis de CodeQL, gitleaks y las pruebas e2e), sin
  force-push ni borrado. No se exige aprobación mientras el equipo no revise entre sí; la plantilla de
  pull request y CODEOWNERS dejan listo ese paso. Escaneo de secretos y protección contra push de
  GitHub activados.
- **Pruebas e2e** con Playwright en el CI: inicio de sesión, roles, teclado y accesibilidad sobre un
  portal real con datos reducidos.
- **Plantilla de pull request** con la Definition of Done, **SECURITY.md** con solo los controles que
  existen y **.env.example** con todas las variables.

## Consecuencias

- Un pull request no se fusiona con el CI en rojo ni con una credencial en sus commits.
- Las credenciales siguen viviendo fuera del repositorio (variables de entorno de Windows o secretos
  de GitHub); `scripts/jira_sync.py` lee `JIRA_*` del entorno.
- El CI de cada pull request tarda unos minutos más por las pruebas e2e y CodeQL (corren en paralelo).
- No se adoptaron las pruebas de IA ni el despliegue en Render de AgroSmart: no aplican a este
  proyecto.
