"""Remisiones entre preceptos: quien menciona a quien, en los dos sentidos.

Se detectan parseando el texto. Aqui no interviene ningun modelo.

EL SENTIDO QUE IMPORTA es el de vuelta. Hacia delante es facil: el articulo
dice "en los terminos del art. X" y se ve leyendo. Hacia atras no: una
disposicion del final de la ley mete una excepcion a un articulo sin que el
articulo se entere. Se lee el articulo completo, parece cerrado, y esta mal.
El indice inverso existe para eso.

REGLA DE ORO AL RESOLVER: ante la duda, no se resuelve.
Una remision mal resuelta devuelve el articulo equivocado, y eso es peor que no
devolver nada: el usuario no tiene forma de notarlo. Por eso "articulo 95 de
esta Ley" se resuelve y "articulo 95 del Reglamento" se queda en PENDIENTE
mientras el Reglamento no este en el corpus.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from . import bloques as B

# --------------------------------------------------------------- ambitos

INTERNA = "interna"      # al mismo cuerpo en que aparece: se resuelve
CRUZADA = "cruzada"      # a otro cuerpo YA CARGADO (Ley <-> Reglamento): se resuelve
EXTERNA = "externa"      # a una norma que no esta cargada: PENDIENTE
AMBIGUA = "ambigua"      # no se puede decidir a cual: PENDIENTE
LIVA = INTERNA           # nombre antiguo, se conserva por compatibilidad

# --------------------------------------------------------------- estados

RESUELTA = "resuelta"
PENDIENTE = "pendiente"          # identificada, pero fuera del corpus actual
NO_ENCONTRADA = "no_encontrada"  # dice ser de esta ley pero no existe el precepto

# --------------------------------------------------------------- patrones

# «article» ES LA MISMA PALABRA. Es una gestoria del Penedes y las preguntas
# llegan en catalan; la respuesta sale en catalan, y ahi el redactor escribe
# «article 80 de la Ley 37/1992»: el texto citado y el nombre de la norma
# quedan en castellano -que es la regla- pero la palabra de enlace se traduce.
# Medido: una respuesta impecable, con las ocho citas literales y correctas, se
# quedo en NO ENCONTRADO porque el lector de referencias no conocia «article» y
# el verificador vio ocho fragmentos entrecomillados «sin referencia».
#
# Esto NO afloja la verificacion: la cita se sigue comprobando letra a letra
# contra el precepto. Solo se reconoce una segunda forma de escribir el mismo
# nombre. En el articulado del BOE la palabra no aparece nunca, asi que en el
# escaneo del corpus es inerte.
_RE_ART = re.compile(r"\b(?:art[ií]culos?|articles?)\b", re.IGNORECASE)
_RE_DISP = re.compile(
    r"\bdisposici[oó]n(?:es)?\s+"
    r"(?P<clase>adicional(?:es)?|transitoria(?:s)?|final(?:es)?|derogatoria(?:s)?)\s+"
    r"(?P<resto>[\wªº\.\s]{1,40})",
    re.IGNORECASE,
)

# REMISIONES A UN ANEXO DE OTRA NORMA. No las cogia nadie: el escaneo solo
# buscaba «articulo N» y disposiciones, y un anexo no tiene numero de articulo.
# El caso real que lo destapo: el articulo 95 de la Ley del IVA define que es un
# «automovil de turismo» remitiendo al ANEXO del Real Decreto Legislativo
# 339/1990, que no esta en el corpus. Sin esa definicion no se sabe si el
# vehiculo del cliente es un turismo, y el sistema no avisaba: lo salvo el
# redactor por su cuenta, y eso no puede ser el plan.
#
# SE EXIGE DESIGNACION CON NUMERO («339/1990»), y no vale un nombre a secas.
# Medido sobre el corpus: hay 28 menciones de «anexo» y solo UNA es una
# remision de verdad a otra norma. Sin el numero, el titulo del propio anexo
# -«ANEXO / REGLAMENTO DEL IMPUESTO...»- se colaba como remision.
_RE_ANEXO = re.compile(
    r"\banexos?\b[^.;:]{0,40}?\b(?P<norma>(?:Real\s+Decreto(?:\s+Legislativo|-ley)?|"
    r"Ley\s+Org[aá]nica|Ley|Reglamento|Directiva|Orden|Decreto)"
    r"\s+\d+/\d{2,4})",
    re.IGNORECASE,
)

_RE_NUMERO = re.compile(r"\s*(\d+)")
_RE_PALABRA_SUF = re.compile(r"\s+([a-zA-ZáéíóúÁÉÍÓÚ]+)")

# Lo que puede ir detras de "disposicion adicional" y ser un ordinal de verdad.
# Existe porque el patron de arriba captura los 40 caracteres siguientes sin
# mirar que son: en un texto normal ("las disposiciones adicionales SE
# aplicaran", "la disposicion final Y el anexo") eso fabricaba remisiones a
# preceptos que no existen en ninguna norma.
#
# "unica" entra porque el BOE la usa de ordinal ("disposicion derogatoria
# unica") aunque no sea un numero.
_ORDINALES_VALIDOS = frozenset(B.ORDINAL_A_NUMERO) | {"unica", "unico"}
_RE_ORDINAL_NUMERICO = re.compile(r"^\d{1,3}$")


def _ordinal_de(palabras: list) -> tuple:
    """(ordinal, cuantas palabras ocupa), o (None, 0) si eso no es un ordinal.

    Se admiten tres formas, que son las que usa el BOE:
      - la palabra suelta: "primera", "vigesimosegunda", "unica"
      - el ordinal partido en dos: "vigesimo segunda", "decimo tercera"
      - el numero: "22", "1"

    Se prueba PRIMERO la forma de dos palabras: "vigesimo" a secas no esta en
    el vocabulario, asi que mirar solo la primera dejaria fuera justo las
    disposiciones altas, que son las que mas se citan por ser las nuevas.
    """
    if not palabras:
        return None, 0

    if len(palabras) >= 2:
        compuesto = B.normalizar(f"{palabras[0]} {palabras[1]}")
        if compuesto.replace(" ", "") in _ORDINALES_VALIDOS:
            return compuesto, 2

    suelta = B.normalizar(palabras[0])
    if suelta in _ORDINALES_VALIDOS or _RE_ORDINAL_NUMERICO.match(suelta):
        return suelta, 1
    return None, 0

# Cosas que cuelgan de un numero de articulo y NO son otro articulo:
# "20, apartado uno, numero 22.º", "68.Dos.2.º", "13.2.º", "5, letra c)".
_ATADURAS = [
    re.compile(r"\s*[ºª]"),
    re.compile(r"\s*\.\s*\d+"),
    re.compile(r"\s*\.\s*[ºª]"),
    re.compile(
        r"\s*\.\s*(?:uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|"
        r"doce|trece|catorce|quince|dieciseis|diecisiete|dieciocho|diecinueve|veinte)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\s*,?\s*apartad[oa]s?\s+[\wªº]+(?:\s+y\s+[\wªº]+)?", re.IGNORECASE),
    re.compile(r"\s*,?\s*n[uú]meros?\s+[\d\.ºª]+(?:\s*[ºª])?", re.IGNORECASE),
    re.compile(r"\s*,?\s*letras?\s+[a-z][’']?\)", re.IGNORECASE),
    re.compile(r"\s*,?\s*p[aá]rrafos?\s+\w+", re.IGNORECASE),
]

# El BOE encadena con coma, con conjuncion y con las dos a la vez:
# "22, 26, y 27". Si no se contempla ", y" la lista se corta en el penultimo.
_RE_CONECTOR = re.compile(
    r"\s*(?:,\s*(?:y|e|o|u)\s+|,\s*|\s+(?:y|e|o|u)\s+)", re.IGNORECASE
)
_RE_RANGO = re.compile(r"\s*,?\s+a\s+(?=\d)", re.IGNORECASE)

# Un apartado pegado al numero. El articulo es el numero; lo que cuelga detras
# es su apartado y NO otro articulo. Cuatro pinturas del mismo caso, todas
# vistas en consultas reales:
#
#     80-cuatro     guion + palabra
#     10-3          guion + numero
#     93.Cuatro     punto + palabra
#     94.Uno.1º     encadenado, y con ordinal al final
#
# El espacio admitido es [ \t] y NO \s: con \s un punto final de bloque se
# comeria el salto de linea y el nombre de la norma siguiente.
_RE_APARTADO_PEGADO = re.compile(
    r"(?:[ \t]*[-.][ \t]*(?:[a-záéíóúñ]+|\d+)[ \t]*[ºª]?)+", re.IGNORECASE)


def numeros_citados(texto: str) -> list[str]:
    """Solo los numeros. Ver `leer_numeros` si hace falta saber que sobro."""
    return leer_numeros(texto)[0]


def leer_numeros(texto: str) -> tuple:
    """Lee una lista de numeros de articulo de un texto suelto.

    Devuelve (numeros, resto): lo que ha sabido leer y lo que queda sin leer.
    El RESTO importa: si ahi queda un numero, es que el campo trae una forma
    que no reconocemos y estamos perdiendo articulos. Perderlos en silencio es
    peor que fallar, asi que quien llama lo cuenta y lo dice.

    «95, 130» -> ['95', '130']          «33 a 36» -> ['33','34','35','36']
    «80-cuatro» -> ['80']               «93.Cuatro, 94.Uno.1º» -> ['93','94']

    Es la parte PURA de `GrafoRemisiones._leer_articulos`, sacada aqui para que
    la use tambien el campo «normativa» de las consultas de la DGT. Se comparte
    lo que se puede compartir: los mismos patrones de lista, de rango y de
    conector. Lo que NO se comparte es el resto de aquel metodo, que decide
    ambito contra el corpus y produce remisiones: eso es del grafo y aqui no
    pinta nada.

    Aqui el rango se expande por aritmetica y no contra el corpus, porque este
    texto puede hablar de una norma que no tenemos cargada.
    """
    numeros: list[str] = []
    cursor = 0
    pendiente_rango = False
    while True:
        m = _RE_NUMERO.match(texto, cursor)
        if not m:
            break
        numero = m.group(1)
        cursor = m.end()

        if pendiente_rango and numeros:
            try:
                desde = int(re.match(r"^(\d+)", numeros[-1]).group(1))
                hasta = int(numero)
            except (AttributeError, ValueError):
                desde = hasta = 0
            if 0 < desde < hasta and hasta - desde <= 400:
                numeros.extend(str(n) for n in range(desde + 1, hasta + 1))
            else:
                numeros.append(numero)
            pendiente_rango = False
        else:
            numeros.append(numero)

        # Sufijo latino ("163 bis"): cuenta como parte del numero.
        ms = _RE_PALABRA_SUF.match(texto, cursor)
        if ms and ms.group(1).lower() in B.SUFIJOS_CONOCIDOS:
            numeros[-1] = f"{numero} {ms.group(1).lower()}"
            cursor = ms.end()

        # Apartado pegado (guion o punto, palabra o numero): se consume.
        ma = _RE_APARTADO_PEGADO.match(texto, cursor)
        if ma:
            cursor = ma.end()

        while True:
            for patron in _ATADURAS:
                mt = patron.match(texto, cursor)
                if mt and mt.end() > cursor:
                    cursor = mt.end()
                    break
            else:
                break

        mr = _RE_RANGO.match(texto, cursor)
        if mr:
            cursor = mr.end()
            pendiente_rango = True
            continue
        mc = _RE_CONECTOR.match(texto, cursor)
        if mc and _RE_NUMERO.match(texto, mc.end()):
            cursor = mc.end()
            continue
        break
    return numeros, texto[cursor:]

# "de esta Ley", "de la presente Ley" y la errata "articulo 65 esta ley".
_RE_ES_ESTA_LEY = re.compile(
    r"^[\s,;]*(?:de\s+)?(?:est[ae]|la\s+presente)\s+ley\b", re.IGNORECASE
)
# Otra norma citada expresamente.
_RE_ES_OTRA_NORMA = re.compile(
    # El articulo determinado es opcional pero tiene que estar contemplado:
    # el BOE escribe "del Reglamento" y tambien "de la Ley 18/1991". Sin el
    # "la" no se reconocia la segunda forma y la remision acababa buscandose
    # dentro de la LIVA.
    r"^[\s,;]*de[l]?\s+(?:l[ao]s?\s+|el\s+)?"
    r"(?:citad[oa]s?\s+|mencionad[oa]s?\s+|referid[oa]s?\s+|"
    r"mism[oa]\s+|presente\s+|propi[oa]\s+)?"
    # "Ley" seguida de palabra en mayuscula es una ley con nombre propio
    # (Concursal, Hipotecaria, General Tributaria...). Se comprueba respetando
    # las mayusculas, de ahi el (?-i:...): esta ley se refiere a si misma como
    # "esta Ley", nunca como "la Ley Tal".
    # Se captura la designacion completa ("Ley 37/1992", no "Ley 3"): esa
    # etiqueta se le ensena al usuario y tiene que poder comprobarla.
    r"(?P<norma>Reglamento(?:\s*\([^)]{1,12}\))?(?:\s*n[.ºo°]*\s*[\d/]+)?|"
    r"C[oó]digo(?:\s+\w+)?|Tratado(?:\s+\w+){0,2}|"
    r"Directiva(?:\s+\d+/\d+(?:/[A-Z]+)?)?|"
    r"Ley\s+Org[aá]nica(?:\s+\d+/\d+)?|Ley\s+\d+/\d+|Ley\s+de\s+\w+(?:\s+\w+)?|"
    r"(?-i:Ley\s+[A-ZÁÉÍÓÚ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚ][a-záéíóúñ]+)?)|"
    r"Real\s+Decreto(?:-ley)?(?:\s+\d+/\d+)?|Decreto(?:\s+\d+/\d+)?|"
    r"Estatuto(?:\s+\w+)?|Convenio|Acuerdo|Texto\s+Refundido|Orden)",
    re.IGNORECASE,
)
# "de dicha Ley", "de la misma Ley": el determinante anaforico remite a una
# norma nombrada antes, nunca a esta (para si misma la ley dice "de esta Ley").
# Solo con determinante anaforico se admite "Ley" a secas como norma externa;
# suelto seria demasiado goloso y se llevaria por delante remisiones internas.
_RE_ES_OTRA_NORMA_ANAFORA = re.compile(
    r"^[\s,;]*de\s+(?:dich[oa]s?|aquell[oa]s?|"
    r"l[ao]s?\s+(?:citad[oa]s?|mencionad[oa]s?|referid[oa]s?|mism[oa]s?))\s+"
    r"(?P<norma>Ley|Reglamento|Directiva|Norma|Texto\s+Refundido)\b",
    re.IGNORECASE,
)
# Marcas de que el articulo mencionado es el de una norma ya nombrada antes.
_RE_ANAFORA = re.compile(
    r"(referid[oa]|citad[oa]|mencionad[oa]|dich[oa]|aludid[oa]|indicad[oa]|"
    r"anterior|mismo)\s*$",
    re.IGNORECASE,
)
_RE_POSESIVO = re.compile(r"\bsus?\s*$", re.IGNORECASE)
_RE_NORMA_CERCA = re.compile(
    r"\b(Reglamento|C[oó]digo\s+\w+|Tratado|Directiva|Ley\s+\d+/\d+|"
    r"Ley\s+de\s+\w+|Real\s+Decreto[\w\-]*\s*\d*/?\d*|Estatuto|Convenio)\b",
    re.IGNORECASE,
)

# Nombre de norma que sigue a una remision: "de la Ley del Impuesto",
# "del presente Reglamento", "de la Ley 58/2003". Se captura hasta la primera
# coma o punto, que es donde acaba la designacion en el lenguaje del BOE.
_RE_DESIGNACION = re.compile(
    # Sin ancla ^: se busca dentro de una ventana, no solo pegado al numero.
    # (El BOE intercala "apartados uno a siete", "ambos", etc.)
    r"\b(?:de[l]?|en|conforme\s+a|seg[uú]n)\s+"
    # OJO: el grupo repetido va DENTRO del grupo con nombre. Si se repite el
    # propio grupo con nombre, Python devuelve solo la ultima vuelta: en "de
    # esta misma Ley" se quedaba con "misma" y perdia el "esta", que es
    # justo el que decide que la remision es interna.
    r"(?P<det>(?:(?:l[ao]s?|el|est[ae]|aquell[ao]s?|dich[ao]s?|citad[ao]s?|"
    r"mencionad[ao]s?|referid[ao]s?|mism[ao]s?|presente|propi[ao]|su[s]?)\s+){0,3})"
    r"(?P<nombre>(?:Reglamento|Ley|Real\s+Decreto(?:-ley)?|Decreto(?:-ley)?|"
    r"C[oó]digo|Tratado|Directiva|Orden|Estatuto|Texto\s+Refundido|Convenio|"
    r"Acuerdo|Norma)[^,.;:()]{0,60})",
    re.IGNORECASE,
)
# Demostrativo: senala a la norma en que se esta, no a otra.
_RE_DEMOSTRATIVO = re.compile(r"\b(est[ae]|presente)\b", re.IGNORECASE)
# Determinantes que apuntan a una norma nombrada ANTES, no a la actual.
_RE_DET_ANAFORICO = re.compile(
    r"\b(dich[ao]s?|citad[ao]s?|mencionad[ao]s?|referid[ao]s?|aquell[ao]s?|"
    r"mism[ao]s?|su[s]?)\b", re.IGNORECASE
)

# UNA DESIGNACION QUE CONTIENE EL NOMBRE DE UNA NORMA NO ES ESA NORMA.
#
# «Texto refundido de la Ley del Impuesto sobre Sociedades» lleva dentro, letra
# por letra, el nombre de la Ley 27/2014. Y es OTRA norma: el texto refundido
# es el RDLeg 4/2004, al que la Ley 27/2014 derogo. Resolverlas a la misma es
# atribuir un articulo a una ley que no lo tiene.
#
# El resolutor ya lo hacia bien -con la designacion entera devuelve None-; lo
# que fallaba es que nunca la recibia entera: el extractor busca el nombre a
# partir de «de la Ley...» y el cualificador se quedaba delante, fuera de la
# captura. Asi que se mira lo que hay DELANTE, igual que la regla de oro mira
# lo que queda detras.
#
# Son formas de DERIVAR una norma de otra, y todas significan «no es esa»:
#
#     texto refundido de ...      el RDLeg que refunde una ley
#     texto articulado de ...     el decreto que articula una ley de bases
#     reglamento de desarrollo    la norma que desarrolla otra
#     estatuto / codigo de ...    recopilaciones con nombre propio
#
# NO entra «Reglamento del Impuesto sobre...» a secas, que es el nombre propio
# de una norma que SI tenemos cargada: lo que descalifica es el «de desarrollo
# de», no la palabra reglamento.
_RE_NORMA_DERIVADA = re.compile(
    r"\b(?:texto\s+refundido|texto\s+articulado|reglamento\s+de\s+desarrollo|"
    r"estatuto|c[oó]digo)\s+(?:de[l]?\s+)?$",
    re.IGNORECASE,
)
# La misma familia, pero mirando HACIA DELANTE: «... al texto refundido de la
# Ley del Impuesto sobre Sociedades». Aqui el cualificador va detras de la
# referencia y por eso se ancla al principio.
_RE_NORMA_DERIVADA_DELANTE = re.compile(
    r"^(?:a[l]?\s+|de[l]?\s+|en\s+e[l]?\s+)?"
    r"(?:texto\s+refundido|texto\s+articulado|reglamento\s+de\s+desarrollo)"
    r"\s+(?:de[l]?\s+)?(?:la|el|los)?\s*[^,.;]{0,60}",
    re.IGNORECASE,
)

VENTANA_CUALIFICADOR = 110   # cuanto se mira por delante buscando "de esta Ley"
VENTANA_POSTERIOR = 60       # cuanto se mira DETRAS de la referencia
VENTANA_DESIGNACION = 70     # cuanto se admite entre el numero y el nombre de la norma
VENTANA_ANTERIOR = 160       # cuanto por detras buscando una norma ya nombrada


@dataclass
class Remision:
    """Una mencion concreta de un precepto dentro del texto de otro."""

    origen: str                 # clave del precepto donde aparece
    texto: str                  # fragmento literal, tal cual esta en la ley
    ambito: str                 # LIVA / EXTERNA / AMBIGUA
    estado: str                 # RESUELTA / PENDIENTE / NO_ENCONTRADA
    destino: str = ""           # clave del precepto de destino, si se resolvio
    etiqueta_destino: str = ""  # "Articulo 95", para poder mostrarlo
    norma_externa: str = ""     # que otra norma, si es EXTERNA
    motivo: str = ""            # por que no se resolvio
    por_rango: bool = False     # vino de "articulos 92 a 114"


@dataclass
class Estadisticas:
    total: int = 0
    resueltas: int = 0
    pendientes_externas: int = 0
    pendientes_ambiguas: int = 0
    no_encontradas: int = 0
    cruzadas: int = 0
    normas_externas: dict = field(default_factory=lambda: defaultdict(int))
    sin_resolver: list = field(default_factory=list)


class GrafoRemisiones:
    """Indice de remisiones en los dos sentidos, construido sobre el corpus."""

    def __init__(self, docs, registro=None):
        self.docs = docs
        self.por_clave = {d.clave: d for d in docs}
        if registro is None:
            from .normas import Registro as _R
            registro = _R(docs)
        self.normas = registro

        # TODO se indexa POR CUERPO. "articulo 8" no es una clave: lo es
        # "articulo 8 del cuerpo tal de la norma cual".
        self.articulos: dict[str, dict[str, str]] = defaultdict(dict)
        self.base_numerica: dict[str, dict[int, list[str]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self.disposiciones: dict[str, dict[tuple[str, str], str]] = defaultdict(dict)

        for d in docs:
            r = d.registro
            cuerpo = r.get("cuerpo_clave") or r["norma_id"]
            if r["tipo"] == B.ARTICULO and not r["es_rango"]:
                self.articulos[cuerpo][r["numero_norm"]] = d.clave
                m = re.match(r"^(\d+)", r["numero_norm"])
                if m:
                    self.base_numerica[cuerpo][int(m.group(1))].append(r["numero_norm"])
            if r["tipo"] in B.TIPOS_DISPOSICION:
                self.disposiciones[cuerpo][(r["tipo"], r["numero_norm"])] = d.clave
                if r.get("ordinal"):
                    self.disposiciones[cuerpo][(r["tipo"], str(r["ordinal"]))] = d.clave

        self.adelante: dict[str, list[Remision]] = defaultdict(list)
        self.atras: dict[str, list[Remision]] = defaultdict(list)
        self.stats = Estadisticas()
        self._construir()

    # ------------------------------------------------------------ construir

    def _construir(self) -> None:
        for d in self.docs:
            texto_bloque = d.registro.get("texto_vigente") or ""
            partes = texto_bloque.split("\n")
            # Fuera el encabezado: "Articulo 95. Limitaciones..." no es una
            # remision, es el rotulo del propio precepto. Si se dejara, cada
            # articulo se citaria a si mismo y el grafo quedaria inservible.
            cuerpo = "\n".join(partes[1:]) if len(partes) > 1 else ""

            for rem in self._remisiones_de(
                d.clave, cuerpo, d.registro.get("cuerpo_clave") or d.registro["norma_id"]
            ):
                self.stats.total += 1
                if rem.estado == RESUELTA:
                    self.stats.resueltas += 1
                    if rem.ambito == CRUZADA:
                        self.stats.cruzadas += 1
                    if rem.destino != rem.origen:
                        self.adelante[rem.origen].append(rem)
                        self.atras[rem.destino].append(rem)
                elif rem.estado == PENDIENTE:
                    if rem.ambito == EXTERNA:
                        self.stats.pendientes_externas += 1
                        etiqueta = rem.norma_externa or "(sin identificar)"
                        self.stats.normas_externas[etiqueta] += 1
                    else:
                        self.stats.pendientes_ambiguas += 1
                    self.adelante[rem.origen].append(rem)
                else:
                    self.stats.no_encontradas += 1
                    self.stats.sin_resolver.append(rem)
                    self.adelante[rem.origen].append(rem)

    # ------------------------------------------------------------ escaneo

    def _remisiones_de(self, origen: str, texto: str, cuerpo_origen: str = ""):
        for m in _RE_ART.finditer(texto):
            yield from self._leer_articulos(
                origen, texto, m.end(), m.start(), cuerpo_origen
            )
        for m in _RE_DISP.finditer(texto):
            rem = self._leer_disposicion(origen, texto, m, cuerpo_origen)
            if rem:
                yield rem
        for m in _RE_ANEXO.finditer(texto):
            rem = self._leer_anexo(origen, m, cuerpo_origen)
            if rem:
                yield rem

    def _leer_anexo(self, origen: str, m, cuerpo_origen: str = ""):
        """Un «anexo de <norma con numero>». Ver `_RE_ANEXO`.

        Si la norma esta CARGADA no se emite nada: de las normas del corpus
        tenemos el articulado, y un anexo nuestro ya es un precepto mas. Lo que
        importa es el anexo de una norma que NO tenemos.
        """
        nombre = re.sub(r"\s+", " ", m.group("norma")).strip(" .,;:")
        clave, _motivo = self.normas.resolver(nombre, cuerpo_origen)
        if clave:
            return None
        return Remision(
            origen, m.group(0).strip(), EXTERNA, PENDIENTE,
            etiqueta_destino="Anexo", norma_externa=nombre,
            motivo="remite al anexo de una norma que no esta en el corpus",
        )

    def _leer_articulos(
        self, origen: str, texto: str, cursor: int,
        inicio_palabra: int | None = None, cuerpo_origen: str = "",
    ):
        """Lee la lista de numeros que sigue a la palabra 'articulo(s)'.

        Sabe leer listas ("69, 70 y 72"), rangos ("92 a 114") y numeros con
        cosas colgando ("20, apartado uno, numero 22.º").
        """
        numeros: list[str] = []
        inicio = cursor
        pendiente_rango = False

        while True:
            m = _RE_NUMERO.match(texto, cursor)
            if not m:
                break
            numero = m.group(1)
            cursor = m.end()

            # Un sufijo latino solo cuenta si el articulo existe de verdad.
            ms = _RE_PALABRA_SUF.match(texto, cursor)
            if ms:
                candidato = B.normalizar(f"{numero} {ms.group(1)}")
                # Contra TODOS los cuerpos, no solo el de origen: "8 bis" es
                # articulo de la Ley y no del Reglamento, y si se valida solo
                # contra el origen el escaner corta ahi y se pierde el "de la
                # Ley del Impuesto" que venia detras. El sufijo es parte de
                # como esta escrita la cita; a que norma apunta se decide
                # despues.
                if any(candidato in arts for arts in self.articulos.values()):
                    numero = f"{numero} {ms.group(1)}"
                    cursor = ms.end()

            if pendiente_rango and numeros:
                numeros.extend(
                    self._expandir_rango(numeros[-1], numero, cuerpo_origen)
                )
                pendiente_rango = False
            else:
                numeros.append(numero)

            # Se consume todo lo que cuelgue del numero.
            while True:
                for patron in _ATADURAS:
                    ma = patron.match(texto, cursor)
                    if ma and ma.end() > cursor:
                        cursor = ma.end()
                        break
                else:
                    break

            mr = _RE_RANGO.match(texto, cursor)
            if mr:
                cursor = mr.end()
                pendiente_rango = True
                continue
            mc = _RE_CONECTOR.match(texto, cursor)
            if mc and _RE_NUMERO.match(texto, mc.end()):
                cursor = mc.end()
                continue
            break

        if not numeros:
            return

        cuerpo_destino, ambito, norma, motivo_ambito = self._ambito(
            texto, inicio, cursor, cuerpo_origen
        )
        # El fragmento literal arranca en la palabra "articulo", no unos
        # caracteres antes: cortar a ciegas dejaba citas como "l articulo 91".
        desde = inicio_palabra if inicio_palabra is not None else inicio
        literal = re.sub(r"\s+", " ", texto[desde:cursor]).strip()

        delante = texto[cursor: cursor + VENTANA_CUALIFICADOR]
        for numero in numeros:
            yield self._resolver_articulo(
                origen, numero, literal, ambito, norma, delante,
                cuerpo_destino, motivo_ambito,
            )

    def _expandir_rango(self, desde: str, hasta: str, cuerpo: str = "") -> list[str]:
        """'92 a 114' son todos los de en medio, no dos.

        Se incluyen los intercalados (92 bis) porque juridicamente el rango los
        comprende. Solo se devuelven los que existen en el corpus.
        """
        try:
            a = int(re.match(r"^(\d+)", B.normalizar(desde)).group(1))
            b = int(re.match(r"^(\d+)", B.normalizar(hasta)).group(1))
        except (AttributeError, ValueError):
            return [hasta]
        if b < a or b - a > 400:
            return [hasta]
        salida = []
        for n in range(a + 1, b + 1):
            salida.extend(sorted(self.base_numerica.get(cuerpo, {}).get(n, [])))
        return salida

    def _ambito(self, texto: str, inicio: int, fin: int, cuerpo_origen: str = ""):
        """Decide a QUE CUERPO apunta la remision.

        Devuelve (clave_cuerpo_destino, ambito, etiqueta_norma, motivo).
        clave_cuerpo_destino es None cuando no se puede decidir, y entonces la
        remision se queda PENDIENTE. Es deliberado: una remision sin resolver
        es un aviso visible; una resuelta a la norma equivocada es un articulo
        real, con texto real, que no es el que toca — y el verificador la daria
        por buena. Antes 200 pendientes que una mal resuelta.
        """
        delante = texto[fin: fin + VENTANA_CUALIFICADOR]
        # La designacion no siempre va pegada al numero: el BOE escribe
        # "articulo 22, apartados uno a siete de la Ley del Impuesto" y
        # "articulo 79diez de la Ley del Impuesto". Se busca en una ventana
        # corta, cortando antes de que empiece OTRA remision para no robarle
        # su norma.
        corte = len(delante)
        m_otra_ref = _RE_ART.search(delante)
        if m_otra_ref:
            corte = m_otra_ref.start()
        m_punto = re.search(r"[.;]\s", delante)
        if m_punto:
            corte = min(corte, m_punto.start())
        ventana = delante[:min(corte, VENTANA_DESIGNACION)]
        m = _RE_DESIGNACION.search(ventana)

        if m is None and m_otra_ref is not None:
            # Enumeracion que comparte una sola designacion al final:
            # "articulo 9 y en el apartado 2 del articulo 16 de la Ley del
            # Impuesto". Las dos remisiones son de la Ley, pero la segunda se
            # lleva el nombre. Se hereda SOLO si lo que hay en medio es corto
            # y no nombra ninguna otra norma, para no robarsela a otro.
            hueco = delante[:m_otra_ref.start()]
            extendida = delante[:min(len(delante), VENTANA_CUALIFICADOR)]
            m_ext = _RE_DESIGNACION.search(extendida, m_otra_ref.start())
            if (
                m_ext is not None
                and len(hueco) <= 60
                and _RE_DESIGNACION.search(hueco) is None
            ):
                m, ventana = m_ext, extendida

        if m:
            det = m.group("det") or ""
            nombre = re.sub(r"\s+", " ", m.group("nombre")).strip(" .,;:")
            # "de dicha Ley", "del citado Reglamento", "su disposicion...":
            # apuntan a una norma nombrada antes en el texto, no a esta.
            # PERO el demostrativo manda sobre el anaforico: "de esta misma
            # Ley" es interna, por mucho que lleve "misma" dentro. Sin esta
            # excepcion, la Ley del IVA dejaba de resolver remisiones suyas
            # («articulo 107 de esta misma Ley»).
            if _RE_DET_ANAFORICO.search(det) and not _RE_DEMOSTRATIVO.search(det):
                return None, AMBIGUA, nombre, (
                    f"«{det.strip()} {nombre}» remite a una norma nombrada antes; "
                    f"no se resuelve"
                )
            # LO QUE VA DELANTE DEL NOMBRE. Ver `_RE_NORMA_DERIVADA`: si la
            # designacion venia precedida de «texto refundido de», «texto
            # articulado de» y demas, lo citado es una norma DERIVADA de esta,
            # no esta. Ante la duda, nada.
            derivada = _RE_NORMA_DERIVADA.search(ventana[:m.start()])
            if derivada:
                cual = " ".join(derivada.group(0).split())
                return None, EXTERNA, f"{cual} {nombre}", (
                    f"«{cual} {nombre}» no es «{nombre}»: es otra norma "
                    f"derivada de ella, y no esta cargada; no se resuelve"
                )
            clave, motivo = self.normas.resolver(
                nombre, cuerpo_origen, cola=ventana[m.end():]
            )
            if clave:
                ambito = INTERNA if clave == cuerpo_origen else CRUZADA
                etiqueta = self.normas.por_clave(clave).etiqueta
                return clave, ambito, etiqueta, motivo
            # NO RESOLVER TIENE DOS CAUSAS Y NO SON LA MISMA.
            #
            #   la norma NO ESTA        -> EXTERNA. Se puede decir «no la
            #                              tengo», y es un limite permanente.
            #   ENCAJA CON VARIAS       -> AMBIGUA. La tengo, y mas de una vez:
            #                              lo que no se es cual. Decir «no esta
            #                              en el corpus» manda a buscar fuera
            #                              lo que esta dentro.
            #
            # Se distinguen desde que hay dos leyes de impuesto cargadas: «la
            # Ley del Impuesto» encaja con la del IVA y con la del IRPF, y el
            # Reglamento del IRPF la nombra asi en casi todos sus articulos.
            if self.normas.encaja_con_varios(nombre):
                return None, AMBIGUA, nombre, motivo
            return None, EXTERNA, nombre, motivo

        # Sin designacion. Si justo antes hay "el referido/citado..." o un "su",
        # lo mas probable es que hable de una norma nombrada antes.
        detras = texto[max(0, inicio - VENTANA_ANTERIOR): inicio]
        antes_inmediato = re.sub(r"\bart[ií]culos?\b\s*$", "", detras, flags=re.IGNORECASE)
        if _RE_ANAFORA.search(antes_inmediato) or _RE_POSESIVO.search(antes_inmediato):
            m2 = None
            for m2 in _RE_NORMA_CERCA.finditer(detras):
                pass
            return None, AMBIGUA, (m2.group(0) if m2 else ""), (
                "se menciona «el referido/citado articulo» sin decir de que norma"
            )

        # LA NORMA PUEDE VENIR DESPUES, Y ENTONCES NO ES INTERNA.
        #
        # «se añade una disposicion adicional octava AL TEXTO REFUNDIDO de la
        # Ley del Impuesto sobre Sociedades, aprobado por Real Decreto
        # Legislativo 4/2004»: aqui el nombre de la norma va DETRAS de la
        # referencia, asi que el extractor -que mira delante- no encuentra
        # designacion y da la remision por interna. Y no lo es: es a una norma
        # derivada que ademas esta derogada.
        #
        # Se mira una ventana corta por delante, lo justo para pillar el
        # cualificador pegado. Ante la duda, nada: PENDIENTE, no interna.
        despues = texto[fin:fin + VENTANA_POSTERIOR] if fin else ""
        m_der = _RE_NORMA_DERIVADA_DELANTE.match(despues.lstrip(" ,"))
        if m_der:
            cual = " ".join(m_der.group(0).split())[:60]
            return None, EXTERNA, cual, (
                f"la referencia va seguida de «{cual}»: es una norma derivada "
                f"de otra, no la norma en la que estamos; no se resuelve")

        # Un articulo a secas es interno a SU cuerpo.
        return cuerpo_origen, INTERNA, "", "sin designacion: interna a su cuerpo"

    def _resolver_articulo(
        self, origen: str, numero: str, literal: str, ambito: str, norma: str,
        delante: str = "", cuerpo_destino: str | None = None,
        motivo_ambito: str = "",
    ) -> Remision:
        etiqueta = f"Articulo {numero}"

        if cuerpo_destino is None:
            # No se ha podido decidir el cuerpo: PENDIENTE, con el motivo.
            return Remision(
                origen, literal, ambito, PENDIENTE,
                etiqueta_destino=etiqueta, norma_externa=norma,
                motivo=motivo_ambito or "no se ha podido determinar la norma",
            )

        clave = self.articulos.get(cuerpo_destino, {}).get(B.normalizar(numero))
        if clave:
            doc = self.por_clave[clave]
            cuerpo = self.normas.por_clave(cuerpo_destino)
            return Remision(
                origen, literal, ambito, RESUELTA,
                destino=clave,
                etiqueta_destino=(
                    cuerpo.referencia_de(doc.registro["referencia"])
                    if cuerpo and ambito == CRUZADA
                    else doc.registro["referencia"]
                ),
                norma_externa=norma if ambito == CRUZADA else "",
            )

        # El cuerpo esta cargado pero ese articulo no existe en el.
        cuerpo = self.normas.por_clave(cuerpo_destino)
        donde = cuerpo.etiqueta if cuerpo else cuerpo_destino
        m = _RE_NORMA_CERCA.search(delante)
        if ambito == INTERNA and m:
            citada = re.sub(r"\s+", " ", m.group(0)).strip()
            return Remision(
                origen, literal, EXTERNA, PENDIENTE,
                etiqueta_destino=etiqueta, norma_externa=citada,
                motivo=f"no existe en {donde} y la frase nombra {citada}: "
                       f"se trata como remision externa",
            )
        return Remision(
            origen, literal, ambito, NO_ENCONTRADA,
            etiqueta_destino=etiqueta,
            motivo=f"se menciona el {etiqueta} de {donde}, pero ahi no existe",
        )

    @staticmethod
    def _leer_disposicion_ordinal(palabras: list) -> tuple:
        """Metodo puente: la comprobacion vive en `_ordinal_de`, a nivel de
        modulo, para poder probarla sin construir el grafo entero."""
        return _ordinal_de(palabras)

    def _leer_disposicion(
        self, origen: str, texto: str, m, cuerpo_origen: str = ""
    ) -> Remision | None:
        clase = B.sin_tildes(m.group("clase"))
        tipo = {
            "adicional": B.DISP_ADICIONAL, "adicionales": B.DISP_ADICIONAL,
            "transitoria": B.DISP_TRANSITORIA, "transitorias": B.DISP_TRANSITORIA,
            "final": B.DISP_FINAL, "finales": B.DISP_FINAL,
            "derogatoria": B.DISP_DEROGATORIA, "derogatorias": B.DISP_DEROGATORIA,
        }.get(clase)
        if not tipo:
            return None

        resto = m.group("resto")
        palabras = re.findall(r"[\wªº]+", resto)
        if not palabras:
            return None

        # Lo que sigue tiene que ser DE VERDAD un ordinal. Sin esta
        # comprobacion se cogia la palabra siguiente fuera cual fuera, y una
        # frase corriente como "las disposiciones adicionales SE aplicaran"
        # fabricaba una remision a la inexistente "disposicion adicional se".
        # Salian 13 remisiones falsas, todas contra preceptos que no existen.
        ordinal, consumidas = _ordinal_de(palabras)
        if ordinal is None:
            return None
        ultima = palabras[consumidas - 1]
        fin = m.start("resto") + (resto.find(ultima) + len(ultima))

        cuerpo_destino, ambito, norma, motivo_ambito = self._ambito(
            texto, m.start(), fin, cuerpo_origen
        )
        literal = re.sub(r"\s+", " ", texto[m.start(): fin]).strip()
        etiqueta = f"{B.ETIQUETA_TIPO[tipo]} {palabras[0]}"

        if cuerpo_destino is None:
            return Remision(
                origen, literal, ambito, PENDIENTE,
                etiqueta_destino=etiqueta, norma_externa=norma,
                motivo=motivo_ambito or f"remite a {norma or 'otra norma'}",
            )

        disps = self.disposiciones.get(cuerpo_destino, {})
        clave = disps.get((tipo, ordinal))
        if clave is None:
            clave = disps.get(
                (tipo, str(B.ORDINAL_A_NUMERO.get(ordinal.replace(" ", ""), "")))
            )
        if clave:
            return Remision(
                origen, literal, ambito, RESUELTA, destino=clave,
                etiqueta_destino=self.por_clave[clave].registro["referencia"],
            )
        return Remision(
            origen, literal, ambito, NO_ENCONTRADA, etiqueta_destino=etiqueta,
            motivo=f"no existe una {etiqueta.lower()} en ese cuerpo",
        )

    # ------------------------------------------------------------ consulta

    def menciona_a(self, clave: str) -> list[Remision]:
        """Preceptos que ESTE menciona (resueltos, sin repetir)."""
        vistos, salida = set(), []
        for r in self.adelante.get(clave, []):
            if r.estado == RESUELTA and r.destino not in vistos:
                vistos.add(r.destino)
                salida.append(r)
        return salida

    def le_mencionan(self, clave: str) -> list[Remision]:
        """Preceptos que mencionan a ESTE. El sentido que se olvida."""
        vistos, salida = set(), []
        for r in self.atras.get(clave, []):
            if r.origen not in vistos:
                vistos.add(r.origen)
                salida.append(r)
        return salida

    def pendientes_de(self, clave: str) -> list[Remision]:
        """Remisiones que salen de este precepto y NO se han resuelto."""
        return [r for r in self.adelante.get(clave, []) if r.estado != RESUELTA]
