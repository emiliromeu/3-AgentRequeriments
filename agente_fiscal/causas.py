#!/usr/bin/env python3
"""POR QUE UNA CONSULTA DE LA DGT NO SE PUEDE ENCONTRAR. Cero red, cero API.

Una puerta que salta siempre por lo mismo se acaba ignorando. La cadena de
siembra paraba cada tanda por la abreviatura `RD 1065/2007`, que esta MEDIDA y
DECIDIDA -recupera 152 y pierde 96, asi que no se aplica-, y pararse por una
deuda conocida es gastar la unica señal que tenemos para lo que no lo es.

Asi que lo no alcanzable se clasifica por CAUSA:

  · si todo cae en causas ya diagnosticadas, la cadena SIGUE y el informe dice
    cuantas y de que causa;
  · si aparece una forma que ninguna causa explica, la cadena PARA. Para eso
    existe la puerta.

LAS CATEGORIAS SALEN DE HABERLAS MEDIDO, una por una, sobre las consultas
reales del disco. No son un mapa a mano de designaciones: son las formas en que
la fuente escribe el campo «normativa», y cada una se conto antes de escribirla
aqui.
"""
import re

# ---------------------------------------------------------------- las causas
#
# Cada una es (clave, explicacion, patron). El orden importa: se devuelve la
# primera que encaja, y van de la mas especifica a la mas general.

SIN_MARCA = "formato nuevo sin marca de articulo"
ABREVIATURA = "abreviatura RD / RDLeg no reconocida"
AJENA = "solo cita normas que no tenemos"
SIN_ARTICULOS = "la fuente no cita ningun articulo"
ERRATA = "errata de la fuente"

# LAS SEIS FORMAS QUE QUEDABAN SIN EXPLICAR, diagnosticadas una a una sobre las
# consultas del disco el 13/08/2026. Diagnosticar no es arreglar: estan aqui
# para que la puerta sepa distinguir deuda conocida de forma nueva, no porque
# se hayan resuelto.
APARTADO_CORTA = "el apartado con punto corta la lista de articulos"
DOS_PUNTOS = "dos puntos tras la marca de articulo"
SIGLA_SUELTA = "sigla + numero, sin la palabra Ley"
ENTRE_PARENTESIS = "la norma va entre parentesis detras de su nombre"
PUNTO_Y_COMA = "punto y coma dentro de la lista de articulos"
MEZCLA_AJENA = "norma ajena mezclada con una nuestra"

_RE_SIN_MARCA = re.compile(
    r"\b(?:Ley|Real\s+Decreto)\s+\d+/\d{4}[^\n]{0,90}?\s-\s\d")
_RE_ABREV = re.compile(r"\bRD\s*-?\s*Leg\.?\s*\d|\bRDLeg\.?\s*\d|\bRD\.?\s+\d+/\d")
_RE_ERRATA = re.compile(r"37/1192|27/20014|R\.eal|art\.\s*art\b|Ley 39/1987")
_RE_NUMERO_NORMA = re.compile(r"\b\d+/\d{4}\b")
_RE_ALGUN_ARTICULO = re.compile(
    r"\bart[íi]culos?\b\.?\s*:?\s*\d|\barts?\b\.?\s*:?\s*\d", re.IGNORECASE)

_RE_SIGLA = re.compile(r"\b(?:LIRPF|LIVA|LIS|LGT|LIP|RIRPF|RIVA|RIS)[.,]?\s+\d+/\d{4}")
_RE_DOS_PUNTOS = re.compile(r"\bArt[íi]culos?\s*:|\barts?\.?\s*:", re.IGNORECASE)
_RE_PARENTESIS = re.compile(r"\((?:Ley|Real\s+Decreto)\s+\d+/\d{4}")
_RE_PUNTO_Y_COMA = re.compile(r"\d\s*;\s*\d")
_RE_MEZCLA = re.compile(
    r"Directiva|Reglamento\s*\(|Regl\.|Convenio|Constituci[oó]n|"
    r"Ley 1/2000|Ley 40/2015|Ley 39/2015|Ley 49/2002|Ley 10/2012|Ley 38/1992")
# «Articulos 169.2 y 170 Ley 58/2003»: se lee el 169 y el «.2» corta la lista,
# asi que la designacion de detras ya no queda pegada a los numeros.
_RE_APARTADO = re.compile(r"\b\d+\.\d")


def _resuelve(normativa: str, normas) -> bool:
    """¿El lector de HOY saca algun precepto comparable de este campo?"""
    if normas is None:
        return False
    from . import dgt as _D
    try:
        return any(p.comparable
                   for p in _D.pares_de_normativa(normativa or "", normas))
    except Exception:                            # noqa: BLE001
        return False


def causa(normativa: str, numeros_cargados: set, normas=None) -> str:
    """Por que no se puede encontrar esta consulta. Cadena vacia = no se sabe.

    `numeros_cargados` son los numeros de las normas del corpus -«37/1992»,
    «29/1987»...-, que salen del propio corpus y no de una lista escrita.

    CADA CAUSA SE COMPRUEBA, NO SE PARECE. Y esto es un arreglo, no un adorno:
    hasta el 17/08/2026 se etiquetaba por parecido de texto, asi que bastaba
    que en el campo apareciera «RDLeg» para llamarlo «abreviatura no
    reconocida» AUNQUE LA ABREVIATURA YA SE LEYERA. Veintiuna consultas de la
    ultima tanda llevaban esa etiqueta y ninguna fallaba por eso: fallaban por
    dos formas que nadie habia diagnosticado.
    
    Una etiqueta que no se puede desmentir no clasifica: decora. Y aqui decorar
    es caro, porque la puerta de la cadena decide con esto: lo que tiene causa
    conocida no la para, y lo que no la tiene si.

    Asi que se pasa `normas` y se comprueba de verdad. Sin `normas` no se puede
    comprobar nada, y entonces NO SE CLASIFICA -se devuelve "" y para la
    puerta-, que es la unica respuesta honesta cuando no se ha mirado.
    """
    t = " ".join((normativa or "").split())
    if not t:
        return SIN_ARTICULOS

    # LA COMPROBACION QUE MANDA SOBRE TODAS. Si con el lector de hoy el campo
    # resuelve, NO HAY CAUSA DE FALLO QUE VALGA: lo que hubiera que arreglar ya
    # se arreglo. Devolver una causa aqui seria justo el defecto que se corrige.
    if normas is not None and _resuelve(t, normas):
        return ""

    # Y SIN PODER COMPROBAR, NO SE ETIQUETA. Ver la cabecera.
    if normas is None:
        return ""

    if _RE_SIN_MARCA.search(t):
        return SIN_MARCA
    if _RE_ABREV.search(t):
        # SE COMPRUEBA: se abre la abreviatura y se mira si sigue sin resolver.
        # Si al abrirla resuelve, la abreviatura NO es su causa -aunque el
        # texto la lleve- y hay que seguir buscando cual es.
        from . import dgt as _D
        if not _resuelve(_D._expandir_abreviatura(t), normas):
            return ABREVIATURA
    citadas = set(_RE_NUMERO_NORMA.findall(t))
    if citadas and not (citadas & numeros_cargados):
        return AJENA
    if _RE_ERRATA.search(t):
        return ERRATA
    if _RE_SIGLA.search(t):
        return SIGLA_SUELTA
    if _RE_DOS_PUNTOS.search(t):
        return DOS_PUNTOS
    if _RE_PARENTESIS.search(t):
        return ENTRE_PARENTESIS
    if _RE_MEZCLA.search(t):
        return MEZCLA_AJENA
    if _RE_PUNTO_Y_COMA.search(t):
        return PUNTO_Y_COMA
    if _RE_APARTADO.search(t):
        return APARTADO_CORTA
    if not _RE_ALGUN_ARTICULO.search(t):
        return SIN_ARTICULOS
    return ""          # NO SE SABE: esto es lo que para la cadena


def numeros_de(normas) -> set:
    """Los numeros de norma del corpus. Del corpus, no de una lista."""
    fuera = set()
    for c in normas.cuerpos.values():
        for a in c.alias:
            fuera.update(_RE_NUMERO_NORMA.findall(a))
    return fuera


def clasificar(consultas, normas) -> dict:
    """{causa: [consultas]}. La clave vacia son las que nadie explica."""
    numeros = numeros_de(normas)
    fuera: dict = {}
    for c in consultas:
        fuera.setdefault(causa(c.normativa, numeros, normas), []).append(c)
    return fuera
