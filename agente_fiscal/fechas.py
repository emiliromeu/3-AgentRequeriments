"""LA FECHA DE PUBLICACION DE UNA NORMA, preguntada al BOE. Con cache en disco.

Existe por un agujero concreto: `/analisis` dice QUE normas posteriores tocan
a una, pero de cada una da solo tres cosas -id_norma, relacion y texto- y
NINGUNA fecha. Comprobado sobre los 725 posteriores del corpus entero.

La fecha va dentro de la prosa del texto -«por Ley 5/2022, de 9 de marzo»- y
esa ademas es la fecha de DISPOSICION, no la de publicacion en el BOE. Sacarla
de ahi seria una fecha aproximada con aspecto de dato exacto, y encima haria
falta una tabla de nombres de mes escrita a mano.

Donde SI la da el BOE es en `/metadatos` de la norma modificadora, en el campo
`fecha_publicacion`. Eso es una peticion por norma, y por eso esto guarda en
crudo: la segunda vez no se pregunta.

QUE NO HACE: no inventa. Si el BOE no tiene esa norma en la base consolidada
-pasa con resoluciones y con normas autonomicas viejas- devuelve cadena vacia
y quien llama lo anota como que falta. Una fecha inventada seria peor que no
tenerla, porque nadie la volveria a mirar.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from . import boe_api

ACEPTA_JSON = "application/json"
ETIQUETA = "metadatos"

# Cortesia con una API publica que se va a llamar en tanda.
PAUSA_SEGUNDOS = 0.25


def _ya_dijo_que_no(norma_id: str, dir_crudo: Path) -> bool:
    """¿Ya preguntamos por esta norma y el BOE contesto que no la tiene?

    Muchas normas que MODIFICAN no estan en la base consolidada: el BOE solo
    consolida las que consolida. Sin esto, cada reingestion volveria a pedir
    las mismas y a recibir los mismos 404, que es ruido para ellos y minuto y
    medio para nosotros.

    Para volver a preguntar por una, se borra su `fallo-metadatos_*` del crudo.
    """
    carpeta = dir_crudo / norma_id
    if not carpeta.is_dir():
        return False
    for sidecar in carpeta.glob("fallo-" + ETIQUETA + "_*.meta.json"):
        try:
            if json.loads(sidecar.read_text(encoding="utf-8")).get("codigo_http") == 404:
                return True
        except (json.JSONDecodeError, OSError):
            continue
    return False


def _de_crudo(ruta: Path) -> str:
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return ""
    cuerpo = datos.get("data")
    if isinstance(cuerpo, list):
        cuerpo = cuerpo[0] if cuerpo else {}
    if not isinstance(cuerpo, dict):
        return ""
    crudo = str(cuerpo.get("fecha_publicacion") or "").strip()
    # El BOE la da como 19871219.
    if len(crudo) == 8 and crudo.isdigit():
        return f"{crudo[:4]}-{crudo[4:6]}-{crudo[6:8]}"
    return ""


def publicacion_de(norma_id: str, dir_crudo: Path, permitir_red: bool = True) -> str:
    """La fecha de publicacion en el BOE, en ISO. Cadena vacia si no se sabe."""
    if not norma_id or norma_id == "(sin id)":
        return ""
    ruta = boe_api.ultimo_crudo(norma_id, dir_crudo, ETIQUETA)
    if ruta is not None:
        return _de_crudo(ruta)
    if not permitir_red or _ya_dijo_que_no(norma_id, dir_crudo):
        return ""
    try:
        time.sleep(PAUSA_SEGUNDOS)
        respuesta = boe_api.descargar_y_guardar(norma_id, "/metadatos", ACEPTA_JSON, dir_crudo, ETIQUETA)
    except boe_api.ErrorBOE:
        # El BOE no tiene esa norma consolidada. Se queda sin fecha, y se dice.
        return ""
    except OSError:
        return ""
    return _de_crudo(respuesta.ruta)


def poner_fechas(reformas, dir_crudo: Path, permitir_red: bool = True) -> None:
    """Rellena `fecha_publicacion` de cada reforma. Una peticion por norma."""
    vistas: dict[str, str] = {}
    for reforma in reformas:
        clave = getattr(reforma, "id_norma", "") or ""
        if clave not in vistas:
            vistas[clave] = publicacion_de(clave, dir_crudo, permitir_red)
        reforma.fecha_publicacion = vistas[clave]
