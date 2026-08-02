"""Troceo del XML consolidado del BOE a registros, uno por precepto.

Decisiones de diseno que conviene no deshacer sin pensarlo:

1. SE TROCEA POR PRECEPTO, nunca por longitud. Un articulo largo se queda
   entero; dos articulos cortos no se juntan. La unidad de trabajo del
   fiscalista es el articulo.

2. EL CUERPO Y LAS NOTAS DEL BOE VAN SEPARADOS. En el XML, los <p
   class="nota_pie"> no son texto normativo: son el historial de reformas
   ("Se modifica el apartado 2 por el art. 1.1 de la Ley 28/2014"). Si se
   mezclaran con el articulado pasarian dos cosas malas:
     - la busqueda por palabras daria positivos sobre texto que no es norma;
     - el verificador podria dar por buena una cita literal contra una frase
       que el legislador nunca promulgo.
   Van en `notas_boe`, aparte, y ademas sirven para avisar de cambios de version.

3. TODAS LAS VERSIONES, CADA UNA CON SUS FECHAS. Un caso de 2023 se contesta
   con el texto vigente en 2023. Guardar solo la consolidada de hoy haria
   imposible eso, y el error seria invisible.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime

from . import bloques as B

CLASES_NOTA = ("nota_pie", "nota_pie_2", "nota_pie_3")

# Marca interna para el aparato editorial del BOE (ver _lineas).
CLASE_EDITORIAL = "nota_editorial"

_RE_REF_BOE = re.compile(r"\bBOE-[A-Z]-\d{4}-\d+\b")
_RE_NORMA_CITADA = re.compile(
    r"\b((?:Ley Org[aá]nica|Ley|Real Decreto-ley|Real Decreto Legislativo|"
    r"Real Decreto|Decreto-ley|Orden|Reglamento)\s+[\w/\-]*\d+/\d{4})",
    re.IGNORECASE,
)
# El BOE escribe "Ley 66/1997, de 30 de diciembre": el ano no va tras el mes,
# va dentro del numero de la norma. Por eso el ano es opcional aqui y, si falta,
# se toma del "NN/AAAA" de la norma citada.
_RE_FECHA_LARGA = re.compile(
    r"\bde\s+(\d{1,2})\s+de\s+([a-zA-ZáéíóúÁÉÍÓÚ]+)(?:\s+de\s+(\d{4}))?", re.IGNORECASE
)
_RE_ANNO_EN_NORMA = re.compile(r"/(\d{4})\b")
_MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
_RE_SUPRIMIDO = re.compile(
    r"^\(?\s*(suprimid|derogad|sin contenido|anulad)", re.IGNORECASE
)


class ErrorParseo(Exception):
    """El XML no tiene la forma esperada. Se cuenta, no se traga."""


# ------------------------------------------------------------------ fechas


# Por debajo de este ano una fecha de vigencia es, con seguridad, una errata
# del origen: no hay legislacion tributaria consolidada anterior.
ANNO_MINIMO_CREIBLE = 1900
# Margen de retroactividad admisible. Una norma puede tener efectos retroactivos
# de meses; de decadas, no.
ANNOS_RETROACTIVIDAD_MAX = 5


def fecha_iso(compacta: str | None) -> str:
    """'19921229' -> '1992-12-29'. Cadena vacia si no es una fecha valida."""
    s = (compacta or "").strip()
    if not re.fullmatch(r"\d{8}", s):
        return ""
    try:
        datetime.strptime(s, "%Y%m%d")
    except ValueError:
        return ""
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"


def revisar_vigencia(f_vig: str, f_pub: str) -> tuple[str, str]:
    """Comprueba si una fecha de vigencia es creible.

    Devuelve (fecha_efectiva, motivo). Si la fecha es creible, la efectiva es
    la misma y el motivo va vacio.

    Existe porque el propio BOE trae erratas: el articulo 115 de la Ley del IVA
    declara fecha_vigencia='09980101' (ano 998) cuando se publico el
    31-12-1997. Corregirlo por lo callado seria tapar un error del origen; y
    dejarlo tal cual haria que ese texto pareciese vigente desde la Edad Media
    al filtrar por ejercicio. Asi que se conserva el valor crudo, se calcula
    aparte uno utilizable y se deja constancia del cambio.
    """
    if not f_vig:
        return (f_pub, "sin fecha de vigencia: se usa la de publicacion") if f_pub else ("", "")

    anno = int(f_vig[:4])
    if anno < ANNO_MINIMO_CREIBLE:
        return (
            f_pub or f_vig,
            f"fecha de vigencia imposible en el origen ({f_vig}); "
            f"se usa la de publicacion ({f_pub or 'no hay'})",
        )
    if f_pub and anno < int(f_pub[:4]) - ANNOS_RETROACTIVIDAD_MAX:
        return (
            f_vig,
            f"vigencia ({f_vig}) muy anterior a la publicacion ({f_pub}): "
            f"revisar, se respeta el valor del BOE",
        )
    return f_vig, ""


# ------------------------------------------------------------------ texto


def _texto_plano(elem: ET.Element) -> str:
    """Texto de un elemento con los espacios colapsados."""
    return re.sub(r"\s+", " ", "".join(elem.itertext())).strip()


def _render_tabla(tabla: ET.Element) -> str:
    """Una tabla como texto legible. Las tablas de tipos del IVA son norma."""
    filas = []
    for tr in tabla.iter("tr"):
        celdas = [_texto_plano(c) for c in tr if c.tag in ("td", "th")]
        if any(celdas):
            filas.append(" | ".join(celdas))
    return "\n".join(filas)


def _lineas(nodo: ET.Element, editorial: bool = False):
    """Recorre el contenido de una version en orden y devuelve (clase, texto).

    Trata <table> como una unidad (si no, itertext() la deja ilegible) y baja
    dentro de <blockquote>.

    SOBRE LOS BLOCKQUOTE, que tiene mas miga de la que parece:
    el BOE mete su aparato editorial en <blockquote> CON atributo class
    ('soloTexto', 'siempreSeVe', 'noDesde20160101', 'docrel'...). Dentro van
    avisos suyos ("Tengase en cuenta que...") escritos con la MISMA clase de
    parrafo que el articulado ('parrafo'), asi que por la clase del <p> no hay
    manera de distinguirlos: el unico marcador fiable es el contenedor.
    Los <blockquote> sin class son los del historial de reformas, cuyos <p>
    si vienen marcados como nota_pie.

    Que esto importe no es teorico: son 179 parrafos que se colaban en el
    cuerpo del articulado. Ahi dentro el BOE llega a reproducir redacciones
    alternativas, de modo que un verificador de citas podria dar por buena una
    frase que en ese ejercicio no era la vigente.
    """
    for hijo in nodo:
        if hijo.tag == "p":
            clase = hijo.get("class") or ""
            if editorial and clase not in CLASES_NOTA:
                clase = CLASE_EDITORIAL
            yield (clase, _texto_plano(hijo))
        elif hijo.tag == "table":
            yield (CLASE_EDITORIAL if editorial else "tabla", _render_tabla(hijo))
        elif hijo.tag in ("blockquote", "div", "ul", "ol"):
            # Un blockquote con class abre aparato editorial; sin class, no.
            marca = editorial or (hijo.tag == "blockquote" and bool(hijo.get("class")))
            yield from _lineas(hijo, marca)
        elif hijo.tag in ("li",):
            yield (CLASE_EDITORIAL if editorial else "", _texto_plano(hijo))


# ------------------------------------------------------------------ notas


def _analizar_nota(texto: str) -> dict:
    """Estructura minima de una nota del BOE (historial de reformas).

    Deterministico y sin IA: solo lo que se lee literalmente en la nota.
    """
    bajo = B.sin_tildes(texto)
    if bajo.startswith("se modifica") or "se modifican" in bajo[:40]:
        accion = "modifica"
    elif bajo.startswith("se anade") or bajo.startswith("se aade") or "se anaden" in bajo[:40]:
        accion = "anade"
    elif bajo.startswith("se suprime") or "se suprimen" in bajo[:40]:
        accion = "suprime"
    elif bajo.startswith("se deroga") or "se derogan" in bajo[:40]:
        accion = "deroga"
    elif "correccion de errores" in bajo:
        accion = "correccion"
    else:
        accion = "otro"

    norma = _RE_NORMA_CITADA.search(texto)
    norma_txt = norma.group(1) if norma else ""

    fecha = ""
    m = _RE_FECHA_LARGA.search(texto)
    if m:
        mes = _MESES.get(B.sin_tildes(m.group(2)))
        anno = m.group(3)
        if not anno and norma_txt:
            en_norma = _RE_ANNO_EN_NORMA.search(norma_txt)
            anno = en_norma.group(1) if en_norma else None
        if mes and anno:
            fecha = f"{int(anno):04d}-{mes:02d}-{int(m.group(1)):02d}"

    return {
        "texto": texto,
        "accion": accion,
        "norma_citada": norma_txt,
        "fecha_norma": fecha,
        "refs_boe": sorted(set(_RE_REF_BOE.findall(texto))),
    }


# ------------------------------------------------------------------ bloques


def _rubrica(lineas: list[tuple[str, str]], referencia: str) -> str:
    """El epigrafe del articulo: 'Articulo 95. Limitaciones del derecho a deducir.'
    devuelve 'Limitaciones del derecho a deducir.'"""
    for clase, texto in lineas:
        if clase in ("articulo", "anexo") and texto:
            partes = texto.split(".", 1)
            if len(partes) == 2 and partes[1].strip():
                return partes[1].strip()
            return ""
    return ""


def _versiones_de(
    bloque: ET.Element,
) -> tuple[list[dict], list[dict], list[str], list[str]]:
    """Devuelve (versiones, notas_boe, notas_editoriales, incidencias)."""
    versiones: list[dict] = []
    notas: list[dict] = []
    editoriales: list[str] = []
    vistas_notas: set[str] = set()
    vistas_edit: set[str] = set()
    incidencias: list[str] = []

    nodos = bloque.findall("version")
    if not nodos:
        incidencias.append("bloque sin ninguna <version>")

    for orden, v in enumerate(nodos):
        lineas = list(_lineas(v))
        # El cuerpo es SOLO texto promulgado: ni historial de reformas ni
        # anotaciones del BOE. Lo demas se guarda aparte, nunca se tira.
        cuerpo_lineas = [
            t for c, t in lineas if c not in CLASES_NOTA and c != CLASE_EDITORIAL and t
        ]
        notas_lineas = [t for c, t in lineas if c in CLASES_NOTA and t]
        for t in (t for c, t in lineas if c == CLASE_EDITORIAL and t):
            if t not in vistas_edit:
                vistas_edit.add(t)
                editoriales.append(t)

        # Las notas se acumulan a nivel de bloque: el BOE las repite en cada
        # version y no aportan nada duplicadas.
        for n in notas_lineas:
            if n not in vistas_notas:
                vistas_notas.add(n)
                notas.append(_analizar_nota(n))

        texto = "\n".join(cuerpo_lineas)
        f_pub = fecha_iso(v.get("fecha_publicacion"))
        f_vig = fecha_iso(v.get("fecha_vigencia"))

        f_efectiva, motivo = revisar_vigencia(f_vig, f_pub)
        if motivo:
            incidencias.append(f"version #{orden}: {motivo}")
        if not f_vig:
            incidencias.append(
                f"version #{orden} sin fecha_vigencia utilizable "
                f"(valor crudo={v.get('fecha_vigencia')!r})"
            )
        if not texto.strip():
            incidencias.append(f"version #{orden} sin texto")

        versiones.append(
            {
                "orden": orden,
                "id_norma_origen": v.get("id_norma") or "",
                "fecha_publicacion": f_pub,
                "fecha_vigencia": f_vig,
                # La que debe usarse para filtrar por ejercicio. Coincide con
                # fecha_vigencia salvo erratas del origen, siempre anotadas.
                "fecha_vigencia_efectiva": f_efectiva,
                "vigencia_corregida": bool(motivo and f_efectiva != f_vig),
                "texto": texto,
                "caracteres": len(texto),
                "suprimido": bool(_RE_SUPRIMIDO.match(texto.strip())),
                "_lineas": lineas,  # se descarta antes de serializar
            }
        )

    return versiones, notas, editoriales, incidencias


def _contexto_estructural(pila: list[tuple[int, str]]) -> list[str]:
    return [titulo for _, titulo in pila]


def trocear(
    xml_bytes: bytes,
    norma_id: str,
    norma_titulo: str,
    url_html: str,
) -> tuple[list[dict], list[dict]]:
    """XML consolidado completo -> (registros_citables, registros_descartados).

    Nada se tira en silencio: lo que no es citable (encabezados, preambulo,
    firma) sale en la segunda lista para poder auditarlo.
    """
    try:
        raiz = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise ErrorParseo(f"El XML del BOE no se puede parsear: {e}") from e

    estado = raiz.findtext("./status/code", default="")
    if estado and estado != "200":
        raise ErrorParseo(
            f"El XML trae status={estado}: {raiz.findtext('./status/text', '')}"
        )

    nodos = raiz.findall(".//bloque")
    if not nodos:
        raise ErrorParseo(
            "El XML no contiene ningun <bloque>. La estructura de la API ha "
            "cambiado: ejecuta el modo 'inspeccionar' antes de seguir."
        )

    citables: list[dict] = []
    descartados: list[dict] = []
    pila: list[tuple[int, str]] = []  # (nivel, titulo) de encabezados abiertos

    # --- deteccion del CUERPO, por estructura ---
    # Un real decreto aprobatorio lleva dos articulados: el suyo y el del
    # reglamento o texto refundido que aprueba (su anexo), que vuelve a
    # empezar por el articulo 1. Se abre cuerpo nuevo cuando la numeracion
    # REINICIA. No hay lista de normas especiales: es la propia estructura.
    cuerpo_indice = 0
    maximo_articulo = 0

    for posicion, bl in enumerate(nodos):
        id_bloque = bl.get("id") or ""
        titulo = (bl.get("titulo") or "").strip()
        tipo_boe = bl.get("tipo") or ""

        cls = B.clasificar(titulo, id_bloque, tipo_boe)

        if cls.tipo == B.ARTICULO and not cls.es_rango:
            m_num = re.match(r"(\d+)", cls.numero_norm)
            if m_num:
                numero_actual = int(m_num.group(1))
                if numero_actual < maximo_articulo:
                    cuerpo_indice += 1
                    maximo_articulo = numero_actual
                    pila.clear()   # el arbol de titulos tambien empieza de cero
                else:
                    maximo_articulo = max(maximo_articulo, numero_actual)

        versiones, notas, editoriales, incidencias = _versiones_de(bl)
        avisos = list(cls.avisos)

        # El BOE marca con fecha_caducidad los bloques que dejaron de estar en
        # vigor (p.ej. los arts. 163 bis/ter/quater, caducados el 28-11-2014).
        # Es decisivo para fechar un caso: en 2013 se aplicaban, en 2023 no.
        caducidad = fecha_iso(bl.get("fecha_caducidad"))
        if bl.get("fecha_caducidad") and not caducidad:
            incidencias.append(
                f"fecha_caducidad ilegible: {bl.get('fecha_caducidad')!r}"
            )

        # Un encabezado (Titulo VIII, Capitulo I...) no se cita, pero situa a
        # los preceptos que vienen detras.
        if cls.tipo == B.ENCABEZADO:
            nivel = B.nivel_de_encabezado(titulo)
            rotulo = titulo
            if versiones:
                extra = [
                    t
                    for c, t in versiones[0]["_lineas"]
                    if c in ("titulo_tit", "capitulo_tit", "seccion") and t
                ]
                if extra:
                    rotulo = f"{titulo}. {extra[0]}"
            while pila and pila[-1][0] >= nivel:
                pila.pop()
            pila.append((nivel, rotulo))

        # Las disposiciones y los anexos van al final de la ley, pero NO
        # cuelgan del ultimo titulo: penden de la norma entera. Heredar ahi la
        # pila daria un contexto falso ("Disposicion adicional primera" dentro
        # de "Titulo XIII. Infracciones y sanciones").
        if cls.tipo in B.TIPOS_DISPOSICION or cls.tipo == B.ANEXO:
            contexto: list[str] = []
        else:
            contexto = _contexto_estructural(pila)

        for v in versiones:
            v.pop("_lineas", None)

        registro = {
            "id_bloque": id_bloque,
            "posicion": posicion,
            "norma_id": norma_id,
            "norma_titulo": norma_titulo,
            "tipo": cls.tipo,
            "tipo_boe": tipo_boe,
            "referencia": cls.referencia,
            "referencia_corta": cls.referencia_corta,
            # La identidad completa: norma + cuerpo + precepto. `clave_local`
            # se conserva porque dentro de un cuerpo se sigue citando
            # "articulo 8" a secas.
            "clave": f"{norma_id}#{cuerpo_indice}#{cls.clave}" if cls.clave else "",
            "clave_local": cls.clave,
            "cuerpo_indice": cuerpo_indice,
            "cuerpo_clave": f"{norma_id}#{cuerpo_indice}",
            "numero": cls.numero,
            "numero_norm": cls.numero_norm,
            "ordinal": cls.ordinal,
            "es_rango": cls.es_rango,
            "titulo_bloque": titulo,
            "contexto": contexto,
            "url": f"{url_html}#{id_bloque}" if id_bloque else url_html,
            "url_api": (
                f"https://www.boe.es/datosabiertos/api/legislacion-consolidada/"
                f"id/{norma_id}/texto/bloque/{id_bloque}"
            ),
            "n_versiones": len(versiones),
            "versiones": versiones,
            "notas_boe": notas,
            "notas_editoriales": editoriales,
            "caducado_desde": caducidad,
            "incidencias": incidencias,
            "avisos": avisos,
        }

        if versiones:
            ultima = versiones[-1]
            registro["rubrica"] = ""
            registro["texto_vigente"] = ultima["texto"]
            # Siempre la efectiva: es la que se usa para situar un ejercicio.
            registro["vigente_desde"] = ultima["fecha_vigencia_efectiva"]
            registro["fecha_primera_version"] = versiones[0]["fecha_vigencia_efectiva"]
            registro["fechas_vigencia"] = [
                v["fecha_vigencia_efectiva"] for v in versiones
            ]
            registro["suprimido"] = ultima["suprimido"]
        else:
            registro.update(
                {
                    "rubrica": "",
                    "texto_vigente": "",
                    "vigente_desde": "",
                    "fecha_primera_version": "",
                    "fechas_vigencia": [],
                    "suprimido": False,
                }
            )

        if cls.tipo in B.TIPOS_CITABLES:
            citables.append(registro)
        else:
            descartados.append(registro)

    # La rubrica hay que sacarla de las lineas, que ya se han descartado; se
    # recalcula de forma barata sobre el texto vigente.
    for r in citables:
        r["rubrica"] = _rubrica_de_texto(r["texto_vigente"], r["titulo_bloque"])

    return citables, descartados


def _rubrica_de_texto(texto: str, titulo_bloque: str) -> str:
    """Primera linea del articulo menos el rotulo: deja el epigrafe."""
    if not texto:
        return ""
    primera = texto.split("\n", 1)[0].strip()
    base = B.normalizar(titulo_bloque)
    if base and B.normalizar(primera).startswith(base):
        resto = primera[len(titulo_bloque):].lstrip(" .")
        return resto.strip()
    return ""
