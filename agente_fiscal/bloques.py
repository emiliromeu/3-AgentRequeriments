"""Clasificacion de bloques y construccion de la referencia canonica.

TRAMPA COMPROBADA CONTRA EL CORPUS REAL, no descartar:
el atributo `id` del bloque NO es el numero de articulo.
    id="a1-2"  -> titulo "Articulo 163 quinvicies"
    id="a8-2"  -> titulo "Articulo 8 bis"
    id="a2-2"  -> titulo "Articulo 163 duovicies" (etc.)
Indexar por el id produce citas falsas con toda la apariencia de correctas.
La referencia canonica SIEMPRE se deriva del atributo `titulo`; el id se
guarda solo porque es el ancla del enlace profundo al HTML del BOE.
"""

from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------- tipos

ARTICULO = "articulo"
DISP_ADICIONAL = "disposicion_adicional"
DISP_TRANSITORIA = "disposicion_transitoria"
DISP_DEROGATORIA = "disposicion_derogatoria"
DISP_FINAL = "disposicion_final"
ANEXO = "anexo"
ENCABEZADO = "encabezado"
PREAMBULO = "preambulo"
FIRMA = "firma"
METADATO = "metadato"        # bloques del BOE que no son norma ([Informacion relacionada])
DESCONOCIDO = "desconocido"

# Los que se pueden citar en una respuesta. Las disposiciones entran de pleno
# derecho: ahi viven las excepciones.
TIPOS_CITABLES = frozenset(
    {ARTICULO, DISP_ADICIONAL, DISP_TRANSITORIA, DISP_DEROGATORIA, DISP_FINAL, ANEXO}
)

TIPOS_DISPOSICION = frozenset(
    {DISP_ADICIONAL, DISP_TRANSITORIA, DISP_DEROGATORIA, DISP_FINAL}
)

ETIQUETA_TIPO = {
    ARTICULO: "Articulo",
    DISP_ADICIONAL: "Disposicion adicional",
    DISP_TRANSITORIA: "Disposicion transitoria",
    DISP_DEROGATORIA: "Disposicion derogatoria",
    DISP_FINAL: "Disposicion final",
    ANEXO: "Anexo",
    ENCABEZADO: "Encabezado estructural",
    PREAMBULO: "Preambulo",
    FIRMA: "Firma",
    METADATO: "Metadato del BOE",
    DESCONOCIDO: "SIN RECONOCER",
}

# ---------------------------------------------------------------- ordinales

_ORDINALES = [
    "primera", "segunda", "tercera", "cuarta", "quinta", "sexta", "septima",
    "octava", "novena", "decima", "undecima", "duodecima", "decimotercera",
    "decimocuarta", "decimoquinta", "decimosexta", "decimoseptima",
    "decimoctava", "decimonovena", "vigesima", "vigesimoprimera",
    "vigesimosegunda", "vigesimotercera", "vigesimocuarta", "vigesimoquinta",
    "vigesimosexta", "vigesimoseptima", "vigesimoctava", "vigesimonovena",
    "trigesima",
]
ORDINAL_A_NUMERO = {p: i + 1 for i, p in enumerate(_ORDINALES)}
# Variantes que el BOE alterna sin criterio fijo.
ORDINAL_A_NUMERO.update(
    {
        "septima": 7, "setima": 7, "decimo tercera": 13, "decima tercera": 13,
        "decimoctava": 18, "decimooctava": 18, "undecima": 11, "decimoprimera": 11,
        "duodecima": 12, "decimosegunda": 12,
    }
)

# Sufijos latinos de articulos intercalados (art. 163 bis, 163 quater...).
#
# NO se usan para DECIDIR si algo es sufijo, solo para avisar de uno que no
# conociamos. La diferencia importa: si el sufijo se descartase por no estar en
# la lista, "Articulo 163 quater" se indexaria como "Articulo 163" y una cita
# al 163 quater devolveria el texto del 163. Ambos existen en esta ley.
# El BOE ademas escribe variantes y erratas ("cuarter", "quinque", "sexvivies"),
# asi que la lista nunca va a estar completa: se captura cualquier sufijo y se
# avisa de los desconocidos.
SUFIJOS_CONOCIDOS = frozenset(
    """bis ter quater quinquies sexies septies octies nonies decies undecies
    duodecies terdecies quaterdecies quindecies quinquiesdecies sexiesdecies
    septiesdecies octiesdecies noniesdecies vicies unvicies duovicies tervicies
    quatervicies quinvicies sexvicies septvicies octovicies novovicies""".split()
)

# Todas las expresiones se aplican sobre el titulo SIN TILDES y en minusculas
# (ver sin_tildes: conserva las posiciones, asi que los tramos capturados
# siguen valiendo para recortar el titulo original).
_RE_ARTICULO = re.compile(
    r"^articulos?\s+(?P<num>\d+)(?P<suf>(?:\s+[a-z]+){0,2})\s*\.?\s*$"
)
_RE_RANGO_ARTICULOS = re.compile(r"^articulos\s+.+\s+a\s+.+")
_RE_DISPOSICION = re.compile(
    r"^disposicion\s+(?P<clase>adicional|transitoria|derogatoria|final)"
    r"(?:\s+(?P<ord>[\w\s]+?))?\s*\.?$"
)
_RE_ANEXO = re.compile(r"^anexo\b\s*(?P<num>[ivxlc\d]*)")
_RE_ENCABEZADO = re.compile(r"^(titulo|capitulo|seccion|libro|parte|subseccion)\b")
_RE_METADATO = re.compile(r"^\[.+\]$")

# Nivel jerarquico para reconstruir el arbol de la ley.
NIVEL_ENCABEZADO = {
    "libro": 0, "parte": 0, "titulo": 1, "capitulo": 2,
    "seccion": 3, "subseccion": 4,
}


def sin_tildes(texto: str) -> str:
    """Quita tildes y pasa a minusculas. Base de toda comparacion.

    Para los acentos del castellano conserva la longitud de la cadena
    ('quater' -> 'quater', 6 y 6), de modo que un tramo localizado sobre el
    texto normalizado sirve para recortar el texto original. Quien dependa de
    eso debe comprobarlo con `posiciones_estables`.
    """
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn").lower()


def posiciones_estables(original: str, normalizado: str) -> bool:
    """True si se puede recortar `original` con indices de `normalizado`."""
    return len(original) == len(normalizado)


def normalizar(texto: str) -> str:
    """Clave de comparacion: sin tildes, sin puntuacion sobrante, un solo espacio."""
    limpio = sin_tildes(texto)
    limpio = re.sub(r"[^\w\s/]", " ", limpio)
    return re.sub(r"\s+", " ", limpio).strip()


class Clasificacion:
    """Resultado de clasificar un bloque."""

    __slots__ = (
        "tipo", "numero", "numero_norm", "ordinal", "referencia",
        "referencia_corta", "clave", "es_rango", "motivo", "avisos",
    )

    def __init__(
        self,
        tipo: str,
        numero: str = "",
        numero_norm: str = "",
        ordinal: int | None = None,
        referencia: str = "",
        referencia_corta: str = "",
        clave: str = "",
        es_rango: bool = False,
        motivo: str = "",
        avisos: list[str] | None = None,
    ):
        self.tipo = tipo
        self.numero = numero
        self.numero_norm = numero_norm
        self.ordinal = ordinal
        self.referencia = referencia
        self.referencia_corta = referencia_corta
        self.clave = clave
        self.es_rango = es_rango
        self.motivo = motivo  # por que no se reconocio, si es el caso
        self.avisos = avisos or []  # rarezas que si se reconocieron


def clasificar(titulo: str, id_bloque: str, tipo_boe: str) -> Clasificacion:
    """Clasifica un bloque a partir de su titulo (fuente primaria).

    `tipo_boe` es el atributo `tipo` del XML (precepto / encabezado /
    preambulo / firma / nota_inicial). Se usa solo como desempate, porque el
    BOE marca como "precepto" cosas que son encabezados (Seccion 1, Capitulo V).
    """
    bruto = (titulo or "").strip()
    t = bruto.rstrip(".").strip()
    # Se compara siempre sobre el titulo sin tildes: el BOE alterna "quater" y
    # "quater", y una tilde no puede decidir si un articulo se encuentra o no.
    tn = sin_tildes(t)  # sin colapsar espacios: alinearia mal los indices
    estable = posiciones_estables(t, tn)

    def recorte(desde: int, hasta: int) -> str:
        """Tramo del titulo ORIGINAL (con sus tildes) segun indices normalizados."""
        return t[desde:hasta] if estable else tn[desde:hasta]

    if not t:
        # Sin titulo: el unico apoyo que queda es el tipo declarado y el id.
        if tipo_boe in ("preambulo", "nota_inicial") or id_bloque in ("preambulo", "pr"):
            return Clasificacion(PREAMBULO, referencia="Preambulo", clave="preambulo")
        if tipo_boe == "firma":
            return Clasificacion(FIRMA, referencia="Firma", clave="firma")
        return Clasificacion(
            DESCONOCIDO, motivo=f"bloque sin titulo (tipo BOE={tipo_boe!r})"
        )

    # -- bloques que el BOE cuelga de la norma pero no son norma --
    if _RE_METADATO.match(t):
        return Clasificacion(METADATO, referencia=t, clave=normalizar(t))

    # -- encabezados estructurales (Titulo, Capitulo, Seccion...) --
    if _RE_ENCABEZADO.match(tn):
        return Clasificacion(ENCABEZADO, referencia=t, clave=normalizar(t))

    # -- rango de articulos suprimidos: "Articulos 163 bis a 163 quater" --
    if _RE_RANGO_ARTICULOS.match(tn):
        return Clasificacion(
            ARTICULO,
            numero=t,
            numero_norm=normalizar(t),
            referencia=t,
            referencia_corta=t,
            clave=normalizar(t),
            es_rango=True,
        )

    # -- articulo --
    m = _RE_ARTICULO.match(tn)
    if m:
        num = m.group("num")
        # El sufijo se conserva SIEMPRE, se conozca o no. Descartarlo fusionaria
        # el "163 quater" con el "163", que son preceptos distintos.
        suf_norm = " ".join((m.group("suf") or "").split())
        suf_display = " ".join(recorte(*m.span("suf")).split())
        avisos = []
        for palabra in suf_norm.split():
            if palabra not in SUFIJOS_CONOCIDOS:
                avisos.append(
                    f"sufijo de articulo no catalogado: {palabra!r} "
                    f"(se conserva en la referencia, no se pierde)"
                )
        numero = f"{num} {suf_display}".strip()
        norm = normalizar(f"{num} {suf_norm}".strip())
        return Clasificacion(
            ARTICULO,
            numero=numero,
            numero_norm=norm,
            referencia=f"Articulo {numero}",
            referencia_corta=f"art. {numero}",
            clave=f"articulo {norm}",
            avisos=avisos,
        )

    # -- disposiciones --
    m = _RE_DISPOSICION.match(tn)
    if m:
        tipo = {
            "adicional": DISP_ADICIONAL,
            "transitoria": DISP_TRANSITORIA,
            "derogatoria": DISP_DEROGATORIA,
            "final": DISP_FINAL,
        }[m.group("clase")]
        ord_txt = recorte(*m.span("ord")).strip() if m.group("ord") else ""
        ord_norm = normalizar(m.group("ord") or "")
        ordinal = ORDINAL_A_NUMERO.get(ord_norm.replace(" ", "")) or ORDINAL_A_NUMERO.get(ord_norm)
        etiqueta = ETIQUETA_TIPO[tipo]
        return Clasificacion(
            tipo,
            numero=ord_txt,
            numero_norm=ord_norm,
            ordinal=ordinal,
            referencia=f"{etiqueta} {ord_txt}".strip(),
            referencia_corta=f"{_ABREV[tipo]} {ord_txt}".strip(),
            clave=f"{tipo} {ord_norm}".strip(),
        )

    # -- anexo --
    m = _RE_ANEXO.match(tn)
    if m:
        num = recorte(*m.span("num")).strip() if m.group("num") else ""
        return Clasificacion(
            ANEXO,
            numero=num,
            numero_norm=normalizar(num),
            referencia=f"Anexo {num}".strip(),
            referencia_corta=f"anexo {num}".strip(),
            clave=normalizar(f"anexo {num}"),
        )

    if tipo_boe in ("preambulo", "nota_inicial"):
        return Clasificacion(PREAMBULO, referencia=t or "Preambulo", clave="preambulo")
    if tipo_boe == "firma":
        return Clasificacion(FIRMA, referencia=t or "Firma", clave="firma")

    return Clasificacion(
        DESCONOCIDO,
        referencia=t,
        motivo=f"titulo no encaja en ningun patron conocido (tipo BOE={tipo_boe!r})",
    )


_ABREV = {
    DISP_ADICIONAL: "DA",
    DISP_TRANSITORIA: "DT",
    DISP_DEROGATORIA: "DD",
    DISP_FINAL: "DF",
}


def nivel_de_encabezado(titulo: str) -> int:
    """Profundidad jerarquica de un encabezado, para reconstruir el arbol."""
    primera = normalizar(titulo).split(" ")[0] if titulo else ""
    return NIVEL_ENCABEZADO.get(primera, 9)
