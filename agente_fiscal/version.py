"""EN QUE VERSION DEL CODIGO SE GENERO ESTO. Cero red, cero API.

POR QUE EXISTE, con el caso entero porque es el tercero igual:

    Tres consultas fallaban con el mismo motivo -«la cita no dice de que norma
    es»- y las tres volvian a fallar en el reintento. Parecia un defecto vivo y
    daba pie a rehacer media rama del sistema. No lo era: las tres son de la
    noche del 5 de agosto ANTES de las 23:19, y a esa hora entro el arreglo que
    hace que la ficha del material diga el nombre del CUERPO en vez del titulo
    del documento del BOE. A esas tres se les pedia nombrar la norma
    enseñandoles un nombre que el verificador no acepta.

    Se descubrio comparando a mano la hora de las carpetas con `git log`. Si
    cada expediente hubiera dicho con que commit se genero, habria sido una
    columna.

MEDIR SOBRE UN HISTORICO MIENTRAS EL CODIGO CAMBIA DESCRIBE UN SISTEMA QUE YA NO
EXISTE. Es la tercera vez que muerde -ver el LEEME- y las tres veces costo lo
mismo: un diagnostico entero apuntando a algo ya arreglado.

QUE SE GUARDA Y POR QUE CADA COSA:

  commit  ... el hash corto. Es la columna por la que se filtra.
  fecha   ... para poder ordenar sin pedirle nada a git despues.
  sucio   ... CUANTOS FICHEROS HABIA SIN GUARDAR. Sin esto, una traza generada
              con cambios locales encima diria que es de un commit que no
              contiene lo que de verdad corrio. En mi Mac eso es casi siempre.

LO QUE NO PUEDE HACER NUNCA ES ROMPER UNA CONSULTA. Si no hay git, si el
subproceso tarda o si el repositorio esta a medias, se devuelve «desconocida» y
la consulta sigue. Un expediente sin version es peor que uno con version; un
expediente que no existe porque git tardo es MUCHO peor.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

DESCONOCIDA = "desconocida"

# Se pregunta a git UNA vez por proceso. La ventana abre un motor y contesta
# doce consultas: doce subprocesos para leer el mismo hash es tonteria, y el
# codigo no cambia mientras el programa corre.
_CACHE: dict | None = None


def _git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(RAIZ), capture_output=True,
                       text=True, timeout=20)
    return r.stdout.strip() if r.returncode == 0 else ""


def actual(recargar: bool = False) -> dict:
    """{commit, fecha, sucio, asunto}. Nunca lanza."""
    global _CACHE
    if _CACHE is not None and not recargar:
        return _CACHE
    datos = {"commit": DESCONOCIDA, "fecha": "", "sucio": 0, "asunto": ""}
    try:
        linea = _git("log", "-1", "--format=%h\t%cI\t%s")
        if linea:
            partes = linea.split("\t")
            datos["commit"] = partes[0]
            datos["fecha"] = partes[1] if len(partes) > 1 else ""
            datos["asunto"] = (partes[2] if len(partes) > 2 else "")[:80]
        estado = _git("status", "--porcelain")
        datos["sucio"] = len([l for l in estado.splitlines() if l.strip()])
    except Exception:                            # noqa: BLE001
        pass                                     # se queda en «desconocida»
    _CACHE = datos
    return datos


def de_expediente(carpeta) -> dict:
    """La version con la que se genero un expediente, leida de su carpeta.

    LOS VIEJOS NO LA LLEVAN Y NO PASA NADA: devuelven «desconocida», y quien
    mida los cuenta APARTE. Suponer que son de la version de hoy es
    exactamente el error que este modulo existe para no repetir.
    """
    import json
    f = Path(carpeta) / "version.json"
    if not f.is_file():
        return {"commit": DESCONOCIDA, "fecha": "", "sucio": 0, "asunto": ""}
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"commit": DESCONOCIDA, "fecha": "", "sucio": 0, "asunto": ""}
    return {"commit": d.get("commit") or DESCONOCIDA,
            "fecha": d.get("fecha") or "", "sucio": int(d.get("sucio") or 0),
            "asunto": d.get("asunto") or ""}


def etiqueta(v: dict) -> str:
    """«3c3c7f4 (+2 sin guardar)» o «desconocida». Para tablas."""
    if v.get("commit") in ("", None, DESCONOCIDA):
        return DESCONOCIDA
    return v["commit"] + (f" (+{v['sucio']} sin guardar)" if v.get("sucio") else "")


def reparto(carpetas) -> dict:
    """{etiqueta: cuantas}. Lo que hay que enseñar antes de cualquier media.

    Si una muestra abarca cuatro versiones del codigo, la media de esa muestra
    no describe ninguna de las cuatro.
    """
    from collections import Counter
    c = Counter(etiqueta(de_expediente(d)) for d in carpetas)
    return dict(c.most_common())
