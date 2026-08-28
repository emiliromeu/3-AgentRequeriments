"""QUE NORMAS COMPONEN EL CORPUS. La lista viaja; el texto no.

EL PROBLEMA QUE RESUELVE. `datos/corpus` esta excluido de git a proposito: son
26 MB que se regeneran solos desde el BOE, y versionar una copia del texto
oficial es guardar algo que ya esta guardado en otro sitio mejor. Pero al
excluir el texto se excluyo tambien, sin querer, LA LISTA DE QUE NORMAS HAY. Y
sin la lista el texto no se puede regenerar, porque nadie sabe que pedir.

Resultado: en el despacho habia dieciseis normas y en la oficina trece, y no
habia ningun camino para que llegaran las tres que faltaban.

  - `git pull` no las traia: el corpus no viaja.
  - El instalador tenia TRES ids escritos a mano, de cuando esto era solo IVA.
  - El boton «actualizar las normas» re-ingeria lo que hubiera EN LOCAL, asi
    que una maquina con trece se quedaba con trece para siempre. Cada equipo
    conservaba su propio agujero.

LA LISTA SE GENERA, NO SE ESCRIBE. Sale de `sellos.json`, que es lo que la
ingesta deja al terminar, mas el titulo que trae cada `.jsonl`. `fase1.py
ingerir` la regenera al acabar, asi que ingerir una norma aqui la publica para
todos los equipos en el siguiente commit, sin que nadie se acuerde de nada.

Una lista escrita a mano seria la septima de la semana, y ya sabemos como
acaban: la del instalador se quedo en tres.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# VIVE FUERA DE `datos/`, que esta excluido entero. Es el punto: esto es lo
# unico del corpus que tiene que viajar.
LISTA = RAIZ / "normas_del_corpus.json"

CORPUS = RAIZ / "datos" / "corpus"
SELLOS = CORPUS / "sellos.json"


def _titulo_de(norma_id: str) -> str:
    """El titulo oficial, sacado del propio corpus. No se escribe aqui."""
    ruta = CORPUS / f"{norma_id}.jsonl"
    if not ruta.is_file():
        return ""
    with ruta.open(encoding="utf-8") as f:
        for linea in f:
            if linea.strip():
                return str(json.loads(linea).get("norma_titulo") or "")
    return ""


def corto(titulo: str, norma_id: str) -> str:
    """«Ley 37/1992, de 28 de diciembre, del IVA.» -> «Ley 37/1992».

    Para las lineas de progreso del instalador, que se leen de reojo mientras
    se espera. El titulo entero no cabe y el id no dice nada a nadie.
    """
    if not titulo:
        return norma_id
    return titulo.split(",")[0].strip() or norma_id


def del_corpus() -> list[dict]:
    """La lista TAL COMO ESTA el corpus de este equipo. La verdad de campo."""
    if not SELLOS.is_file():
        return []
    sellos = json.loads(SELLOS.read_text(encoding="utf-8"))
    ids = sorted({k.split("#")[0] for k in sellos})
    salida = []
    for i in ids:
        t = _titulo_de(i)
        salida.append({"id": i, "nombre": corto(t, i), "titulo": t})
    return salida


def regenerar() -> list[dict]:
    """Publica en la lista lo que haya en el corpus. SIN QUITAR NADA.

    LA LISTA SOLO CRECE, y esto no es un detalle: es lo que la hace fiable.

    La primera version reescribia la lista con el corpus local tal cual, y en
    el despacho funcionaba porque aqui el corpus ES la referencia. En la
    oficina rompia el arreglo entero: se probo con un equipo de trece, se corto
    a mitad de ingerir la primera de las tres que faltaban, y la lista se
    reescribio con las CATORCE de esa maquina. A partir de ahi el equipo se
    creia completo y las dos que faltaban ya no existian para nadie. El mismo
    defecto que veniamos a arreglar, ahora por escrito y viajando.

    Uniendo en vez de sustituyendo, una ingesta a medias deja la lista como
    estaba y la siguiente pasada retoma. Y una norma nueva aqui se publica
    igual, que era el objetivo.

    Quitar una norma del catalogo es una decision deliberada -se cambia el
    fichero y se dice por que en el commit-, no algo que deba pasar por el
    hecho de que un equipo vaya atrasado.
    """
    tengo = {n["id"]: n for n in del_disco()}
    for n in del_corpus():
        tengo[n["id"]] = n              # el corpus local manda en el CONTENIDO
    normas = [tengo[i] for i in sorted(tengo)]

    # NO SE REESCRIBE SI LA LISTA NO HA CAMBIADO, y esto es lo que arreglo el
    # `git pull` de la oficina.
    #
    # Este fichero es de los pocos que VIAJA y ademas se genera en cada
    # maquina: lo rehace `fase1 ingerir`, y a `fase1 ingerir` lo llama el
    # INSTALADOR. O sea que cualquier equipo, el dia que se instala, se
    # encontraba su `normas_del_corpus.json` modificado — no en el contenido,
    # que era identico, sino en el `generado`, que se ponia con la fecha de
    # ese dia. A partir de ahi `actualizar` veia «cambios sin guardar» y se
    # negaba a actualizar, para siempre, en esa maquina.
    #
    # De las tres salidas -no viajar, no reescribirse, o que el pull sepa
    # descartarlo- a este le toca la segunda: TIENE que viajar, porque es lo
    # unico del corpus que puede llegar a otro equipo. Asi que se compara la
    # lista y solo se escribe si de verdad hay algo nuevo que publicar. La
    # fecha deja de ser «cuando se ejecuto esto» y pasa a ser «cuando cambio la
    # lista», que ademas es lo que alguien esperaria que significara.
    anterior = {}
    if LISTA.is_file():
        try:
            anterior = json.loads(LISTA.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            anterior = {}
    if anterior.get("normas") == normas:
        return normas

    LISTA.write_text(json.dumps(
        {"generado": date.today().isoformat(),
         "de": "datos/corpus/sellos.json — NO SE ESCRIBE A MANO",
         "normas": normas}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    return normas


def del_disco() -> list[dict]:
    """La lista que ha viajado por git. Es la que manda para instalar."""
    if not LISTA.is_file():
        return []
    try:
        d = json.loads(LISTA.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return [n for n in d.get("normas", []) if n.get("id")]


def ingerida(norma_id: str) -> bool:
    """¿Hay fichero? La pregunta cruda, sin mirar si es de fiar."""
    return (CORPUS / f"{norma_id}.jsonl").is_file()


def sembrada(norma_id: str) -> bool:
    """¿Ingerida Y SELLADA? Es lo que decide si la siembra se da por hecha.

    EL FICHERO NO BASTA, Y ES LO QUE HACE LA SIEMBRA RETOMABLE. `fase1 ingerir`
    escribe el `.jsonl` y DESPUES lo sella. Entre esas dos lineas cabe un
    Ctrl+C, un portatil que se cierra o una oficina que se va a comer: queda un
    fichero con aspecto de norma ingerida y sin sello. Mirando solo el fichero,
    la instalacion la daba por hecha y seguia; y como el arranque SI mira los
    sellos, el equipo acababa parado en «no tiene sello. Vuelve a ingerirla»,
    que es un callejon: el instalador nunca la iba a volver a ingerir porque
    creia que ya estaba.

    Contandola como no sembrada, retomar es no hacer nada especial: la
    siguiente pasada la ve pendiente, la ingiere y sigue por donde iba.

    SIN FICHERO DE SELLOS NO SE EXIGE SELLO. Un corpus entero sin sellar no
    esta a medias: esta sin sellar, que es como llega una copia anterior a que
    los sellos existieran. Exigirlo ahi seria volver a bajar las diecisiete
    para arreglar algo que no esta roto.
    """
    if not ingerida(norma_id):
        return False
    if not SELLOS.is_file():
        return True
    try:
        return norma_id in json.loads(SELLOS.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # El fichero de sellos ilegible no convierte en sospechosa a cada
        # norma: eso es un problema suyo, y lo dice `sellos.comprobar`.
        return True


def faltan() -> list[dict]:
    """Las de la lista que este equipo NO tiene todavia sembradas.

    ES LA LISTA LA QUE MANDA, NO LO QUE HAYA EN LOCAL. Al reves -que es como
    estaba- una maquina con trece normas no descubre nunca que existen tres
    mas: mira lo suyo, lo encuentra completo y se queda tranquila.
    """
    return [n for n in del_disco() if not sembrada(n["id"])]


def sobran() -> list[str]:
    """Lo ingerido aqui que NO esta en la lista. Solo para avisar.

    No se borra nada: puede ser una norma que se acaba de ingerir y todavia no
    se ha publicado. Pero conviene verlo, porque significa que la lista y el
    corpus se han separado.
    """
    de_la_lista = {n["id"] for n in del_disco()}
    return sorted(n["id"] for n in del_corpus() if n["id"] not in de_la_lista)
