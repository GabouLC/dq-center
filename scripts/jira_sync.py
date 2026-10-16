"""Sincroniza el avance del repo con el Jira del equipo (proyecto SDGDCYP, tablero 1).

Refleja en Jira lo que está en docs/sprints: una épica por sprint, cada historia en
su sprint y su épica, las tareas del sprint backlog como subtareas, el responsable de
cada historia, enlaces a su issue de GitHub y a su evidencia, y los sprints cerrados.
Se puede correr varias veces: lo que ya existe no se duplica.

Credenciales en ~/.jira-usmp.env (JIRA_SITE, JIRA_EMAIL, JIRA_API_TOKEN); nunca en el repo.

  python scripts/jira_sync.py                          # muestra lo que haría, sin escribir
  python scripts/jira_sync.py --aplicar                # lo hace
  python scripts/jira_sync.py --sprint 1 --sin-epicas  # solo el Sprint 1, sin tocar épicas
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PROYECTO, TABLERO = "SDGDCYP", 1
REPO = "https://github.com/GabouLC/dq-center"

# Historia -> (issue de Jira, issue de GitHub)
HISTORIAS = {
    "HU-01": ("SDGDCYP-6", 1), "HU-14": ("SDGDCYP-7", 14), "HU-05": ("SDGDCYP-8", 5),
    "HU-02": ("SDGDCYP-9", 2), "HU-06": ("SDGDCYP-10", 6), "HU-13": ("SDGDCYP-11", 13),
    "HU-03": ("SDGDCYP-12", 3), "HU-04": ("SDGDCYP-13", 4), "HU-07": ("SDGDCYP-14", 7),
    "HU-08": ("SDGDCYP-15", 8), "HU-09": ("SDGDCYP-16", 9), "HU-10": ("SDGDCYP-17", 10),
    "HU-11": ("SDGDCYP-18", 11), "HU-12": ("SDGDCYP-19", 12), "HU-15": ("SDGDCYP-20", 15),
}
RESPONSABLES = {
    "HU-01": "Cristhian Pimentel", "HU-02": "Cristhian Pimentel",
    "HU-14": "Jesus de la Cruz", "HU-05": "Jesus de la Cruz", "HU-06": "Jesus de la Cruz", "HU-13": "Jesus de la Cruz",
    "HU-03": "Franco Delgado", "HU-04": "Franco Delgado", "HU-07": "Franco Delgado", "HU-08": "Franco Delgado",
    "HU-09": "Josue Borda", "HU-11": "Josue Borda", "HU-12": "Josue Borda", "HU-15": "Josue Borda",
    "HU-10": "Gabriel Leon",
}
SPRINTS = [
    {
        "numero": 1, "nombre": "SDGDCYP Sprint 1", "epica": "Base del pipeline",
        "inicio": "2026-10-01T09:00:00.000-05:00", "fin": "2026-10-05T18:00:00.000-05:00",
        "objetivo": "Construir la base del pipeline de datos: ingesta a RAW, homologación hacia MASTER, "
                    "primeras validaciones de calidad y cifrado de la información sensible.",
        "historias": ["HU-01", "HU-14", "HU-05", "HU-02", "HU-06"],
        "tareas": [("Base técnica: CI con GitHub Actions, carga a BigQuery en el sandbox y configuración en Firestore",
                    "Gabriel Leon")],
    },
    {
        "numero": 2, "nombre": "SDGDCYP Sprint 2", "epica": "Motor y Gate",
        "inicio": "2026-10-06T09:00:00.000-05:00", "fin": "2026-10-10T18:00:00.000-05:00",
        "objetivo": "Que cada corte salga del pipeline con un veredicto: reglas de Nivel 2 y 3, certificación "
                    "en tres estados, Quality & Privacy Gate y publicación en BUSINESS solo de lo certificado.",
        "historias": ["HU-03", "HU-04", "HU-07", "HU-08"],
        "tareas": [],
    },
    {
        "numero": 3, "nombre": "SDGDCYP Sprint 3", "epica": "Portal Smart-DQ",
        "inicio": "2026-10-11T09:00:00.000-05:00", "fin": "2026-10-15T23:00:00.000-05:00",
        "objetivo": "Llevar los resultados al negocio: un portal donde cada rol ve la salud y la certificación "
                    "de los datos, su linaje y su glosario, con acceso controlado y cada sección en menos de 8 s.",
        "historias": ["HU-13", "HU-09", "HU-12", "HU-11", "HU-10", "HU-15"],
        "tareas": [],  # las de «Base del portal» salen de docs/sprints/sprint-3.md
    },
]


# ── API de Jira ────────────────────────────────────────────────────────────


class Jira:
    def __init__(self, aplicar: bool):
        archivo = Path.home() / ".jira-usmp.env"
        env = dict(l.strip().split("=", 1) for l in archivo.read_text(encoding="utf-8").splitlines() if "=" in l)
        self.sitio = env["JIRA_SITE"].rstrip("/")
        credencial = f"{env['JIRA_EMAIL']}:{env['JIRA_API_TOKEN']}".encode()
        self.cabeceras = {"Authorization": "Basic " + base64.b64encode(credencial).decode(),
                          "Accept": "application/json", "Content-Type": "application/json"}
        self.aplicar = aplicar

    def pedir(self, metodo: str, ruta: str, cuerpo=None, **params):
        url = self.sitio + ruta + ("?" + urllib.parse.urlencode(params) if params else "")
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        pedido = urllib.request.Request(url, data=datos, method=metodo, headers=self.cabeceras)
        try:
            with urllib.request.urlopen(pedido) as r:
                texto = r.read()
                return json.loads(texto) if texto else None
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"{metodo} {ruta} -> {e.code}: {e.read().decode()[:400]}") from None

    def leer(self, ruta: str, **params):
        return self.pedir("GET", ruta, **params)

    def escribir(self, descripcion: str, metodo: str, ruta: str, cuerpo=None):
        print(("  hecho: " if self.aplicar else "  haría: ") + descripcion)
        return self.pedir(metodo, ruta, cuerpo) if self.aplicar else None

    def buscar(self, jql: str, campos: str = "summary") -> list[dict]:
        issues, token = [], None
        while True:
            params = {"jql": jql, "fields": campos, "maxResults": 100}
            if token:
                params["nextPageToken"] = token
            pagina = self.leer("/rest/api/3/search/jql", **params)
            issues += pagina.get("issues", [])
            token = pagina.get("nextPageToken")
            if not token:
                return issues


def adf(texto: str) -> dict:
    """Texto plano en el formato de documento de Jira."""
    return {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": texto}]}]}


def normalizar(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


# ── lo que dicen los documentos del sprint ─────────────────────────────────


def tareas_del_sprint(numero: int) -> dict[str, list[str]]:
    """Tareas del Sprint Backlog por historia; las que no son de una historia van en «sin_historia»."""
    texto = (RAIZ / "docs" / "sprints" / f"sprint-{numero}.md").read_text(encoding="utf-8")
    seccion = texto.split("## 2. Sprint Backlog", 1)[1].split("## 3.", 1)[0]
    grupos: dict[str, list[str]] = {}
    actual = "sin_historia"
    for linea in seccion.splitlines():
        cabecera = re.match(r"\*\*(HU-\d{2})?[^*]*\*\*", linea)
        if cabecera:
            actual = cabecera.group(1) or "sin_historia"
        elif linea.startswith("- [x] "):
            grupos.setdefault(actual, []).append(linea[6:].strip())
    return grupos


def resumen(tarea: str) -> str:
    """Sin las rutas de código entre paréntesis ni las comillas de código; Jira pide menos de 255 caracteres."""
    limpio = re.sub(r"\s*\([^)]*`[^)]*\)", "", tarea).replace("`", "")
    return limpio if len(limpio) <= 250 else limpio[:247] + "…"


# ── sincronización ─────────────────────────────────────────────────────────


def usuarios(jira: Jira) -> dict[str, str]:
    asignables = jira.leer("/rest/api/3/user/assignable/search", project=PROYECTO, maxResults=200)
    encontrados = {}
    for nombre in sorted(set(RESPONSABLES.values())):
        partes = normalizar(nombre).split()
        candidatos = [u for u in asignables if all(p in normalizar(u.get("displayName", "")).split() for p in partes)]
        if len(candidatos) == 1:
            encontrados[nombre] = candidatos[0]["accountId"]
            print(f"  {nombre} -> {candidatos[0]['displayName']}")
        else:
            print(f"  {nombre}: {'no está en el proyecto' if not candidatos else 'más de una coincidencia'}; queda sin asignar")
    return encontrados


def finalizar(jira: Jira, clave: str) -> None:
    if not jira.aplicar and clave.startswith("("):
        print(f"  haría: pasar {clave} a Finalizada")
        return
    issue = jira.leer(f"/rest/api/3/issue/{clave}", fields="status")
    if issue["fields"]["status"]["statusCategory"]["key"] == "done":
        return
    transiciones = jira.leer(f"/rest/api/3/issue/{clave}/transitions")["transitions"]
    hacia = next(t for t in transiciones if t["to"]["statusCategory"]["key"] == "done")
    jira.escribir(f"{clave} -> {hacia['to']['name']}", "POST", f"/rest/api/3/issue/{clave}/transitions",
                  {"transition": {"id": hacia["id"]}})


def asignar(jira: Jira, clave: str, cuenta: str | None, actual: str | None) -> None:
    if cuenta and cuenta != actual:
        jira.escribir(f"asignar {clave}", "PUT", f"/rest/api/3/issue/{clave}/assignee", {"accountId": cuenta})


def crear(jira: Jira, tipo: str, titulo: str, extra: dict) -> str:
    cuerpo = {"fields": {"project": {"key": PROYECTO}, "issuetype": {"name": tipo}, "summary": titulo, **extra}}
    creado = jira.escribir(f"crear {tipo} «{titulo[:70]}»", "POST", "/rest/api/3/issue", cuerpo)
    return creado["key"] if creado else f"(nueva {tipo})"


def sincronizar(jira: Jira, numeros: list[int], con_epicas: bool, con_responsables: bool) -> None:
    cuentas = {}
    if con_responsables:
        print("Responsables:")
        cuentas = usuarios(jira)
    existentes = {i["fields"]["summary"]: i for i in jira.buscar(
        f"project = {PROYECTO}", "summary,issuetype,parent,assignee,status")}
    sprints_tablero = {s["name"]: s for s in jira.leer(f"/rest/agile/1.0/board/{TABLERO}/sprint", maxResults=50)["values"]}

    for sprint in (s for s in SPRINTS if s["numero"] in numeros):
        n = sprint["numero"]
        print(f"\nSprint {n}:")

        # Épica del sprint (opcional: el equipo puede tener su propia organización)
        epica = None
        if con_epicas:
            titulo_epica = f"{sprint['epica']} (Sprint {n})"
            epica = existentes[titulo_epica]["key"] if titulo_epica in existentes else crear(
                jira, "Epic", titulo_epica, {"description": adf(sprint["objetivo"])})

        # Sprint con su objetivo y fechas
        datos_sprint = {"goal": sprint["objetivo"], "startDate": sprint["inicio"], "endDate": sprint["fin"]}
        if sprint["nombre"] in sprints_tablero:
            sp = sprints_tablero[sprint["nombre"]]
            if sp["state"] == "future":
                jira.escribir(f"objetivo y fechas de {sprint['nombre']}", "POST", f"/rest/agile/1.0/sprint/{sp['id']}", datos_sprint)
        else:
            sp = jira.escribir(f"crear {sprint['nombre']}", "POST", "/rest/agile/1.0/sprint",
                               {"name": sprint["nombre"], "originBoardId": TABLERO, **datos_sprint}) or {"id": None, "state": "future"}

        # Historias: épica, responsable, subtareas, enlaces y estado
        grupos = tareas_del_sprint(n)
        claves_sprint = []
        for hu in sprint["historias"]:
            clave, gh = HISTORIAS[hu]
            claves_sprint.append(clave)
            issue = jira.leer(f"/rest/api/3/issue/{clave}", fields="summary,parent,assignee,subtasks")
            if epica and (issue["fields"].get("parent") or {}).get("key") != epica:
                jira.escribir(f"{clave} ({hu}) dentro de la épica {epica}", "PUT", f"/rest/api/3/issue/{clave}",
                              {"fields": {"parent": {"key": epica}}})
            cuenta = cuentas.get(RESPONSABLES[hu])
            asignar(jira, clave, cuenta, (issue["fields"].get("assignee") or {}).get("accountId"))

            ya = {s["fields"]["summary"] for s in issue["fields"].get("subtasks", [])}
            for tarea in grupos.get(hu, []):
                titulo = resumen(tarea)
                if titulo in ya:
                    continue
                extra = {"parent": {"key": clave}, "description": adf(tarea.replace("`", ""))}
                if cuenta:
                    extra["assignee"] = {"accountId": cuenta}
                subtarea = crear(jira, "Subtask", titulo, extra)
                finalizar(jira, subtarea)
            for s in issue["fields"].get("subtasks", []):
                finalizar(jira, s["key"])

            for global_id, url, titulo in (
                (f"dq-center-github-{gh}", f"{REPO}/issues/{gh}", f"GitHub #{gh} · {hu}"),
                (f"dq-center-evidencia-{hu}", f"{REPO}/blob/main/docs/sprints/sprint-{n}.md", f"Evidencia de {hu} (Sprint {n})"),
            ):
                jira.escribir(f"enlace {clave} -> {titulo}", "POST", f"/rest/api/3/issue/{clave}/remotelink",
                              {"globalId": global_id, "object": {"url": url, "title": titulo}})
            finalizar(jira, clave)

        # Tareas que no son de una historia (base técnica del sprint)
        sueltas = [(resumen(t), RESPONSABLES["HU-09"]) for t in grupos.get("sin_historia", [])] + sprint["tareas"]
        for titulo, responsable in sueltas:
            if titulo in existentes:
                clave = existentes[titulo]["key"]
            else:
                extra = {"parent": {"key": epica}} if epica else {}
                if cuentas.get(responsable):
                    extra["assignee"] = {"accountId": cuentas[responsable]}
                clave = crear(jira, "Tarea", titulo, extra)
            claves_sprint.append(clave)
            finalizar(jira, clave)
        if epica:
            finalizar(jira, epica)

        # Historias y tareas al sprint; luego se inicia y se cierra
        if sp["state"] != "closed":
            jira.escribir(f"{len(claves_sprint)} issues a {sprint['nombre']}", "POST", f"/rest/agile/1.0/sprint/{sp['id']}/issue",
                          {"issues": [c for c in claves_sprint if not c.startswith("(")]})
            if sp["state"] == "future":
                jira.escribir(f"iniciar {sprint['nombre']}", "POST", f"/rest/agile/1.0/sprint/{sp['id']}",
                              {"state": "active", **datos_sprint})
            jira.escribir(f"cerrar {sprint['nombre']}", "POST", f"/rest/agile/1.0/sprint/{sp['id']}", {"state": "closed"})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--aplicar", action="store_true", help="escribir en Jira (sin esto, solo muestra el plan)")
    parser.add_argument("--sprint", type=int, action="append", choices=[1, 2, 3],
                        help="sprint a sincronizar (repetible; por defecto, todos)")
    parser.add_argument("--sin-epicas", action="store_true", help="no crear épicas ni cambiar la épica de las historias")
    parser.add_argument("--asignar", action="store_true", help="asignar cada historia a su responsable (envía correos)")
    args = parser.parse_args()
    jira = Jira(args.aplicar)
    sincronizar(jira, args.sprint or [1, 2, 3], not args.sin_epicas, args.asignar)
    if not jira.aplicar:
        print("\nNada se escribió. Para hacerlo: python scripts/jira_sync.py --aplicar")


if __name__ == "__main__":
    main()
