"""IDENTIDAD DE UN PRECEPTO: (norma, cuerpo, articulo).

Este modulo es el centro de la fase 6. Antes, un precepto se identificaba por
su numero de articulo, y eso basto mientras hubo una sola ley. Con dos normas
deja de bastar, y de tres maneras a la vez:

  - dentro de UNA norma puede haber dos articulados. El Real Decreto 1624/1992
    tiene los suyos (arts. 1-6: aprobar el Reglamento, modificar otros reales
    decretos) y ademas lleva como anexo el REGLAMENTO del IVA, que empieza otra
    vez por el articulo 1. Son dos "cuerpos".
  - entre normas, "articulo 8" es ambiguo: hay uno en la Ley y otro en el
    Reglamento, y no tienen nada que ver.
  - una norma cita a la otra con nombres que hay que reconocer ("de la Ley del
    Impuesto") sin confundirlos con los suyos propios ("de este Reglamento").

EL CUERPO SE DETECTA DE LA ESTRUCTURA, no de una lista de excepciones: se abre
un cuerpo nuevo cuando la numeracion de articulos REINICIA. Comprobado: la Ley
37/1992 tiene 0 reinicios en 215 articulos; el Real Decreto 1624/1992 tiene 1,
justo donde empieza el anexo. Cualquier real decreto aprobatorio o texto
refundido se trocea solo con la misma regla.

LOS NOMBRES Y ALIAS TAMBIEN SALEN DE LOS DATOS: del titulo oficial de la norma
("...por el que se aprueba el Reglamento del Impuesto sobre el Valor Anadido")
y de su rango y numero. No hay ningun diccionario escrito a mano.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import bloques as B

# Rangos que encabezan el nombre de un cuerpo normativo. Es vocabulario del
# castellano juridico -los rangos que existen-, no una lista de las normas del
# corpus: aqui no se escribe ninguna norma concreta.
#
# EL ORDEN IMPORTA: se comprueba con `startswith` y gana el primero que casa,
# asi que un rango largo tiene que ir ANTES del corto que lo prefija. Sin
# «Decreto Legislativo» delante de «Decreto», el Decreto Legislativo 1/2024 se
# leia como un «Decreto» cuya materia era «Legislativo 1/2024, de 12 de marzo»,
# y con esa materia no habia forma de nombrarlo.
_TIPOS = (
    "Reglamento", "Ley Organica", "Ley", "Real Decreto-ley",
    "Real Decreto Legislativo", "Real Decreto", "Texto Refundido",
    "Decreto-ley", "Decreto Legislativo", "Decreto", "Orden", "Estatuto",
    "Codigo",
)

# «POR EL QUE» Y «POR LA QUE», las dos. Una Orden se aprueba «por la que», y
# con solo el masculino su reglamento no llegaba a tener nombre: se quedaba en
# «Anexo 1 de la Orden», que no lo escribe nadie y no resuelve.
_RE_APRUEBA = re.compile(
    r"por (?:el|la) que se aprueban?\s+(?:el|la)\s+(?P<nombre>.+?)"
    r"(?:\s+y se modifica|\s*[,\.]|$)",
    re.IGNORECASE,
)
# El numero de una norma. Las ordenes ministeriales llevan delante la sigla del
# departamento -«Orden HFP/417/2017»- y esa sigla ES parte del numero: sin
# ella, la norma se llamaba «Orden 417/2017», que no es su nombre.
_RE_NUMERO = re.compile(r"\b((?:[A-ZÁÉÍÓÚ]{2,5}/)?\d+/\d{4})\b")
# "Ley 37/1992, de 28 de diciembre, del Impuesto sobre el Valor Anadido."
_RE_MATERIA = re.compile(
    r"\b(?:de|del|de la|sobre)\s+(?P<materia>[A-ZÁÉÍÓÚ][^,.;]{4,90})\s*$"
)

# La misma materia, sin exigir mayuscula inicial. Solo se usa cuando la
# estricta no encuentra nada; ver `_analizar_nombre`.
_RE_MATERIA_LAXA = re.compile(
    r"\b(?:de|del|de la|sobre)\s+(?P<materia>[^\s,.;][^,.;]{3,90})\s*$",
    re.IGNORECASE,
)

PALABRAS_VACIAS_MATERIA = {"de", "del", "la", "el", "los", "las", "sobre", "y", "a"}


def _acronimo(materia: str) -> str:
    """'Impuesto sobre el Valor Anadido' -> 'IVA'.

    SOBRE LA MATERIA LIMPIA. Si no, «Ley del Impuesto sobre Transmisiones...»
    daria «LDITPAJD» en vez de «ITPAJD», y ese codigo no casaria con el del
    mismo impuesto en el resto del corpus.
    """
    iniciales = [
        p[0].upper()
        for p in re.findall(r"[\wÁÉÍÓÚáéíóúñÑ]+", _solo_la_materia(materia))
        if p.lower() not in PALABRAS_VACIAS_MATERIA
    ]
    return "".join(iniciales)


# EL ROTULO DE UN NIVEL ESTRUCTURAL, SIN SU NUMERACION NI SU RANGO.
#
#   «TITULO II. Impuesto sobre el patrimonio (articulo 621-1 - articulo 622-2)»
#        ->  «Impuesto sobre el patrimonio»
#
# Hace falta porque `es_materia_de_impuesto` mira como EMPIEZA la materia -una
# ley de un tributo se titula «Impuesto sobre ...»- y con el «TITULO II.»
# delante no empieza por ahi nunca.
_RE_NIVEL = re.compile(
    r"^(?:libro|titulo|capitulo|seccion|subseccion|parte)\b[^.]*\.\s*",
    re.IGNORECASE)
_RE_RANGO_ROTULO = re.compile(r"\s*\(art[ií]culos?\s[^)]*\)\s*$", re.IGNORECASE)


def _materia_de_rotulo(rotulo: str) -> str:
    t = B.sin_tildes(rotulo or "").strip()
    t = _RE_NIVEL.sub("", t)
    return _RE_RANGO_ROTULO.sub("", t).strip()


@dataclass
class Cuerpo:
    """Un articulado con numeracion propia."""

    norma_id: str
    indice: int                       # 0 = el articulado de la propia norma
    nombre: str = ""                  # "Reglamento del Impuesto sobre el Valor Anadido"
    tipo: str = ""                    # "Reglamento" / "Ley" / "Real Decreto"
    numero: str = ""                  # "37/1992"
    materia: str = ""                 # "Impuesto sobre el Valor Anadido"
    norma_titulo: str = ""
    alias: set = field(default_factory=set)   # todo en minusculas y sin tildes

    @property
    def clave(self) -> str:
        return f"{self.norma_id}#{self.indice}"

    @property
    def etiqueta(self) -> str:
        """Como se nombra en una cita. Es lo que lee el fiscalista."""
        return self.nombre or f"{self.norma_id} (cuerpo {self.indice})"

    def referencia_de(self, referencia_local: str) -> str:
        """'Articulo 8' -> 'Articulo 8 del Reglamento del IVA'."""
        return f"{referencia_local} de {'la ' if self.tipo in ('Ley', 'Orden') else 'el '}{self.etiqueta}".replace(
            "de el ", "del "
        )


def _analizar_nombre(nombre: str) -> tuple[str, str, str]:
    """Nombre de un cuerpo -> (tipo, numero, materia)."""
    plano = re.sub(r"\s+", " ", nombre).strip()
    # Los titulos oficiales encadenan clausulas ("..., por el que se aprueba
    # ..., y se modifica ..."). La materia esta en la PRIMERA; sin cortar, la
    # expresion regular se lleva la cola de la ultima.
    plano = re.split(r",?\s+(?:por el que|por la que|y se modifica|y de)\b",
                     plano, 1)[0]
    tipo = ""
    for t in _TIPOS:
        if B.sin_tildes(plano).startswith(B.sin_tildes(t).lower()):
            tipo = t
            break
    m = _RE_NUMERO.search(plano)
    numero = m.group(1) if m else ""
    materia = ""
    mm = _RE_MATERIA.search(plano.rstrip("."))
    if mm:
        materia = mm.group("materia").strip()
    elif tipo and not numero and _RE_MATERIA_LAXA.search(nombre.rstrip(".")):
        # UN NOMBRE QUE ES TODO CLAUSULA. «Reglamento por el que se regulan
        # las obligaciones de facturacion» se queda en «Reglamento» al cortar
        # por «por el que», y un cuerpo llamado «Reglamento» a secas encaja
        # con los nueve reglamentos del corpus: no se puede citar.
        #
        # La condicion es estrecha a proposito -solo si no quedo ni numero ni
        # materia- porque la version laxa, aplicada a cualquier titulo, leeria
        # la fecha: de «Real Decreto 939/2005, de 29 de julio» sacaria la
        # materia «julio». Los cuerpos con numero no pasan por aqui.
        materia = _RE_MATERIA_LAXA.search(
            nombre.rstrip(".")).group("materia").strip()
    elif tipo:
        resto = plano[len(tipo):].lstrip(" ,")
        # SE QUITA EL PREAMBULO DE NUMERO Y FECHA. «Ley 35/2006, de 28 de
        # noviembre, del Impuesto sobre la Renta...»: sin quitarlo, la materia
        # salia como «35/2006, de 28 de noviembre, del Impuesto sobre...» y su
        # acronimo era «322NIRPFMPLISRNRP». Con la Ley del IVA no se notaba
        # porque su titulo acaba en la materia y la cogia la otra rama.
        resto = re.sub(
            r"^(?:[A-ZÁÉÍÓÚ]{2,5}/)?\d+/\d{4}\s*,?\s*"
            r"(?:de\s+\d{1,2}\s+de\s+[a-záéíóú]+\s*,?\s*)?",
            "", resto, flags=re.I)
        resto = re.sub(r"^(?:de[l]?\s+|la\s+|el\s+)", "", resto, flags=re.I)
        materia = resto.strip(" .,")
    return tipo, numero, materia


def es_materia_de_impuesto(materia: str) -> bool:
    """¿Esta materia nombra un impuesto?

    Se decide por como se titulan las normas, no por una lista de normas: una
    ley de un tributo se llama «Impuesto sobre ...» -sobre el Valor Anadido,
    sobre la Renta de las Personas Fisicas, sobre Sociedades-. La General
    Tributaria no: se llama «General Tributaria», porque no es de ningun
    impuesto en particular, y ese es exactamente el papel que se quiere
    distinguir.

    Se comprueba el PRINCIPIO de la materia y no si la palabra aparece en algun
    sitio: «Reglamento de los Impuestos Especiales» empieza por impuesto, pero
    «Ley de medidas para la prevencion del fraude en los impuestos» no es la
    ley de ningun impuesto.

    Y SE MIRA DESPUES DE QUITAR EL TIPO DE NORMA que a veces viene delante. La
    materia del texto refundido del ITP es «LEY DEL Impuesto sobre
    Transmisiones...» -su titulo es «Texto refundido de la Ley del Impuesto
    sobre...»-, asi que mirada en crudo no empieza por «Impuesto» y sus 75
    preceptos caian en «generales». Eso no es cosmetico: con una pregunta de
    fondo la busqueda restringe al impuesto y deja fuera las generales, o sea
    que la ley del ITP NO PODIA COMPETIR en una pregunta de ITP. Salia su
    Reglamento y nunca ella.

    Quitar el tipo no afloja la regla: «medidas para la prevencion del fraude»
    sigue sin empezar por «impuesto».
    """
    return _solo_la_materia(materia).startswith("impuesto")


def _solo_la_materia(texto: str) -> str:
    """«de la Ley del Impuesto sobre Sociedades» -> «impuesto sobre sociedades».

    Quita articulos y el tipo de norma que va delante, para poder comparar una
    materia con otra sin que estorbe como se la haya nombrado.
    """
    t = B.sin_tildes(texto or "").strip(" .,;:").lower()
    t = re.sub(r"^(?:de[l]?\s+|en\s+)?(?:la|el|los|las)\s+", "", t).strip()
    t = re.sub(r"^(?:ley|reglamento|real decreto(?: legislativo|-ley)?|"
               r"texto refundido|decreto|orden|directiva)\s+"
               r"(?:de[l]?\s+)?(?:la|el|los|las)?\s*", "", t).strip()
    return t


# PALABRAS QUE NO CUENTAN AL SIGLAR UN NOMBRE. Aparte de las de la materia,
# porque un nombre entero lleva conectores que una materia no lleva
# («Reglamento General DE las actuaciones Y los procedimientos DE gestion E
# inspeccion»). Se mantiene separada a proposito: `PALABRAS_VACIAS_MATERIA`
# decide las siglas de los impuestos -IVA, IRPF, ITPAJD- y esas ya estan
# medidas en todo el proyecto; tocarlas para arreglar los nombres cambiaria de
# paso la clasificacion por impuesto.
_VACIAS_NOMBRE = PALABRAS_VACIAS_MATERIA | {
    "e", "en", "para", "por", "que", "se", "su", "sus", "al", "con", "un",
    "una", "unos", "unas", "o", "u",
}

# Una sigla mas larga que esto no la escribe nadie: el Reglamento General de
# las actuaciones y los procedimientos de gestion e inspeccion... daria
# veintitantas letras, y eso ya no es una forma corta, es ruido.
TOPE_SIGLA = 12

# UN ROTULO ESTRUCTURAL DELANTE NO ES PARTE DEL NOMBRE DE LA NORMA.
#
# El titulo del Decreto Legislativo 1/2024 dice «por el que se aprueba el libro
# sexto del Codigo tributario de Catalunya». Lo aprobado se llama «Codigo
# tributario de Catalunya»; «libro sexto del» dice QUE PARTE se aprueba. Sin
# quitarlo, la unica forma de nombrarlo seria repitiendo el libro, que no lo
# escribe nadie.
# «Anexo» NO va en esta lista, y no es un olvido: «Anexo 1 de la Ley 27/2014»
# es el rotulo que ponemos NOSOTROS a un cuerpo sin nombre propio, y quitarselo
# dejaria «Ley 27/2014» como alias del anexo. La ley entera pasaria a encajar
# con dos cuerpos y dejaria de resolverse. Los de esta lista son divisiones que
# el BOE escribe dentro del nombre de lo que aprueba.
_RE_ROTULO_DELANTE = re.compile(
    r"^(?:libro|titulo|capitulo|seccion|subseccion|parte)\b[^,.]{0,40}?"
    r"\s+de[l]?\s+(?:la\s+|el\s+)?",
    re.IGNORECASE,
)


def _sigla_de_nombre(nombre: str) -> str:
    """«Reglamento General de Recaudacion» -> «RGR».

    La inicial de cada palabra que cuenta. Es la misma cuenta que `_acronimo`,
    pero sobre el nombre ENTERO y no sobre la materia: asi salen las siglas que
    escribe un gestor y que la materia sola no da -la materia del RGR es solo
    «Recaudacion», que siglada es «R» y no vale para nada-.
    """
    palabras = re.findall(r"[\wÁÉÍÓÚáéíóúñÑ]+", B.sin_tildes(nombre or ""))
    iniciales = [w[0] for w in palabras
                 if w not in _VACIAS_NOMBRE and not w[0].isdigit()]
    sigla = "".join(iniciales).upper()
    return sigla if 3 <= len(sigla) <= TOPE_SIGLA else ""


def _formas_del_nombre(nombre: str) -> set:
    """Las formas de nombrar a un cuerpo que salen de su NOMBRE OFICIAL.

    POR QUE HACE FALTA, si ya se generan alias de tipo + materia. Porque la
    materia se lee del final del titulo y se deja por el camino lo que la
    califica: la del Reglamento General de Recaudacion es «Recaudacion», y los
    alias salian «reglamento de recaudacion» y «reglamento del recaudacion»,
    ninguno de los cuales es como se llama la norma. «Reglamento General de
    Recaudacion» -su nombre, tal cual lo escribe el BOE y tal cual lo escribe
    un gestor- no era alias de nada, y sus 135 articulos no se podian citar.

    Medido antes de esto: de los once cuerpos que las normas del corpus
    aprueban -reglamentos y textos refundidos, donde vive el articulado que se
    cita-, SEIS no se podian nombrar. Son 704 de los 2043 articulos.

    NO HAY LISTA. Todo sale del titulo que ya guarda el corpus.
    """
    formas: set[str] = set()
    base = re.sub(r"\s+", " ", nombre or "").strip(" .,;:")
    if not base:
        return formas
    formas.add(base)
    sin_rotulo = _RE_ROTULO_DELANTE.sub("", base).strip()
    if sin_rotulo and sin_rotulo != base:
        formas.add(sin_rotulo)
    siglas = {s for s in (_sigla_de_nombre(f) for f in list(formas)) if s}
    return {B.sin_tildes(f) for f in formas | siglas}


def _generar_alias(tipo: str, numero: str, materia: str,
                   nombre: str = "") -> set:
    """Formas con las que el BOE puede nombrar a este cuerpo.

    Se generan del propio nombre, no de una lista. De "Ley 37/1992 ... del
    Impuesto sobre el Valor Anadido" salen "ley 37/1992", "ley del impuesto
    sobre el valor anadido", "ley del impuesto", "ley del iva" y "liva".
    """
    # EL NOMBRE OFICIAL, EL PRIMERO Y SIN CONDICIONES. Va antes del corte por
    # `tipo` a proposito: un cuerpo cuyo nombre no empieza por un rango
    # conocido -«libro sexto del Codigo tributario de Catalunya»- se quedaba
    # sin un solo alias, o sea sin manera de citarlo.
    alias: set[str] = set(_formas_del_nombre(nombre))
    if not tipo:
        return alias
    t = B.sin_tildes(tipo)
    alias.add(t)
    if numero:
        # El numero se normaliza como todo lo demas: desde que puede llevar
        # letras -«HFP/417/2017»- pegarlo en crudo dejaba un alias a medio
        # normalizar, que no casa con nada porque la busqueda va en minusculas.
        alias.add(f"{t} {B.sin_tildes(numero)}")
        # AQUI NO SE GENERA EL RANGO ABREVIADO -«RD 1619/2012»- Y ES A
        # PROPOSITO. Se probo, y el alias resolvia; lo que rompia estaba dos
        # modulos mas alla: `dgt.py` trata las abreviaturas como
        # INTERPRETACION NUESTRA y no como lo que escribio la fuente, y por eso
        # las somete a una contencion extra -si el articulo no existe donde
        # aterriza la abreviatura, la cita no entra-. Con «RD 1619/2012» ya
        # resuelto por alias, esa contencion dejaba de aplicarse y volvian a
        # entrar citas a articulos que no existen. La abreviatura se expande
        # donde ya se sabia expandir: `dgt._expandir_abreviatura`.
    if materia:
        m = B.sin_tildes(materia)
        # LAS TRES FORMAS, Y LA DE SIN CONECTOR NO ES UN CAPRICHO: la Ley
        # 58/2003 se llama «Ley General Tributaria» -sin «de»- y sin esta
        # linea su nombre entero no era alias suyo. Igual el «Reglamento
        # general del regimen sancionador tributario».
        alias.add(f"{t} {m}")
        alias.add(f"{t} de {m}")
        alias.add(f"{t} del {m}")
        # Prefijos cada vez mas cortos: "impuesto sobre el valor anadido",
        # "impuesto sobre el valor", ..., "impuesto". Asi encaja el
        # "de la Ley del Impuesto" que usa el Reglamento 113 veces.
        palabras = m.split()
        for n in range(1, len(palabras)):
            corto = " ".join(palabras[:n])
            if corto and corto not in PALABRAS_VACIAS_MATERIA:
                alias.add(f"{t} de {corto}")
                alias.add(f"{t} del {corto}")
        sigla = _acronimo(materia)
        if len(sigla) >= 2:
            s = sigla.lower()
            alias.add(f"{t} de {s}")
            alias.add(f"{t} del {s}")
            alias.add(f"{t[0]}{s}")           # "liva", "riva"
    return alias


def cuerpos_de_norma(norma_titulo: str, norma_id: str, n_cuerpos: int) -> list:
    """Construye los cuerpos de una norma a partir de su titulo oficial."""
    tipo0, numero0, materia0 = _analizar_nombre(norma_titulo)
    nombre0 = f"{tipo0} {numero0}".strip() if numero0 else (tipo0 or norma_id)
    if materia0 and tipo0:
        nombre0 = f"{tipo0} {numero0}".strip()

    cuerpos = [
        Cuerpo(norma_id, 0, nombre0, tipo0, numero0, materia0, norma_titulo,
               _generar_alias(tipo0, numero0, materia0, nombre0))
    ]

    # Los cuerpos siguientes son lo que la norma APRUEBA, y su nombre esta en
    # el propio titulo oficial: "por el que se aprueba el Reglamento del ...".
    aprobado = _RE_APRUEBA.search(norma_titulo)
    for i in range(1, n_cuerpos):
        if aprobado and i == 1:
            nombre = re.sub(r"\s+", " ", aprobado.group("nombre")).strip()
        else:
            nombre = f"Anexo {i} de {nombre0}"
        t, n, mat = _analizar_nombre(nombre)
        cuerpos.append(
            Cuerpo(norma_id, i, nombre, t, n or numero0, mat, norma_titulo,
                   _generar_alias(t, n, mat, nombre))
        )
    return cuerpos


# --------------------------------------------------------------- registro


# Lo que, tras un alias, delata que se habla de OTRA norma: un numero de
# norma, un parentesis de rango comunitario, un "n.º", o un nombre propio
# ("Concursal", "Civil", "General Tributaria").
_RE_DISCRIMINANTE = re.compile(
    r"^\s*(?:\(|n[.º°]|\d+\s*/\s*\d{4}|[A-ZÁÉÍÓÚ][a-záéíóúñ]{2,})"
)

_RE_DEMOSTRATIVO = re.compile(
    r"\b(est[ae]|el\s+presente|la\s+presente|presente)\s+$", re.IGNORECASE
)


class Registro:
    """Todos los cuerpos cargados. Resuelve un nombre a un cuerpo concreto."""

    def __init__(self, docs):
        self.cuerpos: dict[str, Cuerpo] = {}
        # Las comunidades se leen de los preceptos, no de los cuerpos: es un
        # dato del registro, como el impuesto.
        self._comunidades = {c for c in
                             ((d.registro.get("comunidad") or "").strip()
                              for d in docs) if c}
        vistos: dict[str, int] = {}
        for d in docs:
            r = d.registro
            vistos[r["norma_id"]] = max(
                vistos.get(r["norma_id"], 0), r.get("cuerpo_indice", 0)
            )
        titulos = {}
        for d in docs:
            titulos.setdefault(d.registro["norma_id"], d.registro["norma_titulo"])
        for norma_id, maximo in vistos.items():
            for c in cuerpos_de_norma(titulos[norma_id], norma_id, maximo + 1):
                self.cuerpos[c.clave] = c

        # QUE ARTICULOS TIENE CADA CUERPO. Sale de los mismos `docs` que todo
        # lo demas -no es un mapa escrito- y sirve para una sola cosa: saber si
        # una cita cae en un cuerpo que ni siquiera tiene ese articulo.
        self._articulos: dict[str, set] = {}
        for d in docs:
            r = d.registro
            if r.get("tipo") != "articulo":
                continue
            num = str(r.get("numero_norm") or r.get("numero") or "").strip()
            if num:
                self._articulos.setdefault(r["cuerpo_clave"], set()).add(num)

        # Se deja calculada la lista de materias de impuesto para no rehacerla
        # en cada llamada; `materia_dominante` desaparece porque con dos
        # impuestos dentro la pregunta «cual domina» ya no significa nada.
        self.materias_propias = self.materias_de_impuesto()

    # ------------------------------------------------------------- el papel
    #
    # QUE PAPEL JUEGA CADA NORMA EN ESTE CORPUS. Con una sola ley no hacia
    # falta preguntarselo. Con la General Tributaria dentro, si: la LGT habla
    # de plazos, notificaciones y sanciones EN ABSTRACTO, y su vocabulario
    # encaja con casi cualquier consulta. Sin distinguir papeles, el articulo
    # 55 LGT ("tipo de gravamen") compite de tu a tu con el articulo 91 LIVA
    # en una consulta sobre tipos de IVA, y gana sitio que no le toca.
    #
    # El papel NO se declara en una lista escrita a mano, que es justo lo que
    # este modulo evita en todo lo demas. Se deduce de la materia:
    #
    #   NORMA DEL IMPUESTO   alguno de sus cuerpos trata la materia que este
    #                        corpus tiene como propia (la que comparten mas
    #                        cuerpos: aqui, el Impuesto sobre el Valor Anadido)
    #   NORMA GENERAL        ninguno la trata: esta en el corpus para dar
    #                        apoyo, no para contestar sobre el impuesto
    #
    # El Real Decreto 1624/1992 sale bien parado sin excepciones: su cuerpo 0
    # no declara materia, pero su cuerpo 1 (el Reglamento) si, y el papel se
    # mira POR NORMA, no por cuerpo. Ingerir manana el Reglamento General de
    # Recaudacion lo clasificaria solo, sin tocar esto.

    IMPUESTO = "impuesto"
    GENERAL = "general"

    def materias_de_impuesto(self) -> set:
        """Las materias del corpus que nombran un impuesto. Puede haber varias.

        ANTES ERA UNA SOLA: «la materia dominante», la que mas cuerpos
        compartian. Con una ley de impuesto y unas cuantas generales bastaba.
        Con DOS impuestos dentro deja de tener sentido: el IVA y el IRPF son
        los dos normas de impuesto y solo uno puede ser dominante, asi que el
        otro quedaba clasificado como norma general y competia penalizado.
        """
        return {(c.materia or "").strip().lower()
                for c in self.cuerpos.values()
                if es_materia_de_impuesto(c.materia)}

    def impuestos(self) -> set:
        """Los impuestos que este corpus puede contestar, por sus siglas.

        Salen del titulo de las normas cargadas: «Impuesto sobre el Valor
        Anadido» -> IVA, «Impuesto sobre la Renta de las Personas Fisicas» ->
        IRPF. No hay lista escrita a mano en ninguna parte; si manana se
        ingiere Sociedades, aparece IS sin que nadie lo escriba.
        """
        return {_acronimo(c.materia) for c in self.cuerpos.values()
                if es_materia_de_impuesto(c.materia)}

    def nombres_de_impuesto(self) -> list:
        """Los mismos, con su nombre entero, para poder decirlos en cristiano."""
        vistos, salida = set(), []
        for c in self.cuerpos.values():
            m = (c.materia or "").strip()
            if es_materia_de_impuesto(m) and m.lower() not in vistos:
                vistos.add(m.lower())
                salida.append(m)
        return sorted(salida)

    def papel_de_norma(self, norma_id: str) -> str:
        """IMPUESTO si alguno de sus cuerpos trata la materia de ALGUN impuesto.

        «Alguno», no «el dominante»: ver `materias_de_impuesto`. Y basta con
        que lo sea UNO de sus cuerpos, que es lo que hace que un real decreto
        aprobatorio -cuyo cuerpo 0 no nombra materia ninguna- herede el papel
        del reglamento que aprueba.
        """
        propias = self.materias_de_impuesto()
        if not propias:
            return self.IMPUESTO      # corpus sin impuestos nombrados: todo es propio
        for c in self.cuerpos.values():
            if c.norma_id != norma_id:
                continue
            if (c.materia or "").strip().lower() in propias:
                return self.IMPUESTO
        return self.GENERAL

    def tiene_articulo(self, clave_cuerpo: str, numero: str) -> bool:
        """¿Existe ese articulo en ese cuerpo? Leido del corpus."""
        return str(numero).strip() in self._articulos.get(clave_cuerpo, set())

    def cuerpo_hermano_con(self, clave_cuerpo: str, numero: str) -> str:
        """El cuerpo HERMANO que si tiene ese articulo, o "" si no procede.

        POR QUE EXISTE. Un documento del BOE puede traer dos articulados: el
        del Real Decreto que aprueba -uno o seis articulos- y el del Reglamento
        aprobado -ciento y pico-. Cuando la fuente escribe «Real Decreto
        939/2005 art. 82», la designacion resuelve limpiamente al DECRETO, que
        tiene un solo articulo; el 82 es del Reglamento General de Recaudacion.
        La regla de unanimidad no lo ve porque no hay empate: hay una sola
        norma resuelta, y es la equivocada. Medido el 14/08/2026: NOVENTA Y DOS
        preceptos de la despensa estaban asi, dados por buenos.

        LAS CONDICIONES SON DE CONTENCION, y cada una quita un modo de fallar:

          · SOLO ENTRE CUERPOS DEL MISMO DOCUMENTO. No cruza a otras normas:
            eso ya no seria corregir una ambiguedad de cuerpo, seria buscar
            donde encaje, que es como se atribuye un articulo a quien no lo
            dijo.
          · SI EL CUERPO RESUELTO YA LO TIENE, no se toca. La correccion solo
            mira citas que hoy apuntan a un sitio donde ese articulo no existe.
          · SI NINGUNO LO TIENE, no se toca. Puede ser una errata de la fuente
            o una version antigua, y se queda como esta -o se declina- en vez
            de inventarle un sitio.
          · SI LO TIENEN VARIOS, no se corrige. Ante la duda, nada.
        """
        num = str(numero).strip()
        if not clave_cuerpo or not num:
            return ""
        if self.tiene_articulo(clave_cuerpo, num):
            return ""                       # donde esta ya es un sitio posible
        documento = clave_cuerpo.split("#")[0]
        hermanos = [c for c in self.cuerpos
                    if c != clave_cuerpo and c.split("#")[0] == documento
                    and self.tiene_articulo(c, num)]
        return hermanos[0] if len(hermanos) == 1 else ""

    def impuesto_de_cuerpo(self, clave_cuerpo: str) -> str:
        """De que impuesto es este cuerpo. Cadena vacia = de ninguno.

        Primero por su propia materia; si no la nombra -el cuerpo 0 de un real
        decreto aprobatorio no la nombra nunca-, por la de sus hermanos de la
        misma norma. Es la regla del papel aplicada al cuerpo: los ocho
        articulos que aprueban el Reglamento del IVA son del IVA aunque su
        rotulo no lo diga.
        """
        c = self.cuerpos.get(clave_cuerpo)
        if c is None:
            return ""
        if es_materia_de_impuesto(c.materia):
            return _acronimo(c.materia)
        for otro in self.cuerpos.values():
            if otro.norma_id == c.norma_id and es_materia_de_impuesto(otro.materia):
                return _acronimo(otro.materia)
        return ""

    def impuesto_de_precepto(self, registro) -> str:
        """De que impuesto es ESTE precepto. Cadena vacia = de ninguno.

        LA UNIDAD DE CLASIFICACION ES EL PRECEPTO, NO LA NORMA. Hasta ahora una
        norma era «de un impuesto» o «general» y bastaba, porque cada norma
        estatal trata de uno. Un CODIGO POR LIBROS no: en el libro sexto del
        Codi tributari de Catalunya cada impuesto es un TITULO, y la misma
        norma tiene dentro Renta, Patrimonio, Sucesiones e ITP. Clasificada
        como «general» competiria en las busquedas de los cuatro impuestos que
        tenemos, y sus articulos de Sucesiones saldrian en preguntas de IVA.

        POR QUE EL PRECEPTO Y NO EL TITULO, que era la otra opcion:

          · el precepto es lo que se recupera, lo que se filtra y lo que se
            cita. Cualquier unidad mas gruesa necesita despues un mapa a
            preceptos, asi que se acaba aqui igual, con un rodeo;
          · la EVIDENCIA si vive en el titulo -«TITULO II. Impuesto sobre el
            patrimonio»- y de ahi se lee; lo que se guarda es la RESPUESTA, y
            esa se pega al precepto;
          · y meter un nivel «titulo» en el modelo obligaria a tocar los
            registros de las doce normas ya ingeridas. Esto no toca ninguno:
            `contexto` ya esta en cada registro desde la fase 1.

        Se lee de los datos, sin lista en ninguna parte. Para Sucesiones e ITP
        el dia que entren no hay que escribir nada: sus titulos ya lo dicen.
        """
        ctx = registro.get("contexto") or []
        if isinstance(ctx, str):
            ctx = [ctx]
        for rotulo in ctx:
            materia = _materia_de_rotulo(str(rotulo))
            if es_materia_de_impuesto(materia):
                return _acronimo(materia)
        return self.impuesto_de_cuerpo(registro.get("cuerpo_clave") or "")

    def comunidad_de_precepto(self, registro) -> str:
        """De que comunidad es este precepto. Cadena vacia = estatal.

        LA AUSENCIA DEL CAMPO SIGNIFICA ESTATAL, y es a proposito: las doce
        normas estatales se ingirieron antes de que existiera y no llevan
        `comunidad`. Volver a ingerirlas solo para escribir un campo vacio
        cambiaria sus doce sellos -la herramienta que avisa de que el corpus se
        ha movido- a cambio de nada. Lo que hay es lo correcto: sin comunidad,
        estatal, que ademas es el valor seguro.
        """
        return (registro.get("comunidad") or "").strip()

    def comunidades(self) -> set:
        """Las comunidades de las que hay normativa cargada."""
        return set(self._comunidades)

    def impuestos_de_norma(self, norma_id: str) -> set:
        """TODOS los impuestos que trata una norma. Puede ser mas de uno.

        Es la regla del papel, pero sin obligar a elegir: una norma de varios
        impuestos ya no tiene que hacerse pasar por general.
        """
        fuera = set()
        for c in self.cuerpos.values():
            if c.norma_id == norma_id and es_materia_de_impuesto(c.materia):
                fuera.add(_acronimo(c.materia))
        return fuera

    def admite(self, registro, impuestos) -> bool:
        """¿Puede este precepto competir en una consulta de esos impuestos?

        `impuestos` es un conjunto de codigos; la cadena vacia dentro significa
        «y tambien las normas generales». `None` = no se filtra.
        """
        if impuestos is None:
            return True
        return self.impuesto_de_precepto(registro) in impuestos

    def admitidos_para(self, impuesto: str):
        """Que impuestos pueden competir en una consulta de ESE impuesto.

        Devuelve codigos, no cuerpos: la cadena vacia significa «y las normas
        generales», que aplican a todos. Antes esto devolvia un conjunto de
        CUERPOS, y valia mientras cada norma tratara de un solo impuesto; con
        un codigo por libros dentro -Renta, Patrimonio, Sucesiones e ITP en el
        mismo cuerpo- el cuerpo dejo de ser la unidad. Ver
        `impuesto_de_precepto`.

        DEVUELVE `None` SI EL IMPUESTO NO SE HA PODIDO DETERMINAR, y esa es la
        regla que no se negocia: filtrar con un impuesto equivocado es peor que
        no filtrar. Sin filtro se compite de mas y el corte por pertinencia
        hace su trabajo; con el filtro equivocado se pierde la ley que tocaba y
        NO SE NOTA, porque la respuesta sale igual de segura citando otra cosa.
        """
        if not impuesto or impuesto not in self.impuestos():
            return None
        return {impuesto, ""}

    def papel(self, clave_cuerpo: str) -> str:
        c = self.cuerpos.get(clave_cuerpo)
        return self.papel_de_norma(c.norma_id) if c else self.IMPUESTO

    def __len__(self) -> int:
        return len(self.cuerpos)

    def por_clave(self, clave: str):
        return self.cuerpos.get(clave)

    def encaja_con_varios(self, designacion: str) -> bool:
        """¿Esta designacion nombra a MAS DE UNA de las normas cargadas?

        Es la diferencia entre «no la tengo» y «no se cual de las que tengo».
        `resolver` ya lo sabe -se niega por eso- pero lo dice dentro de un
        motivo en prosa; aqui se pregunta en limpio para poder decirselo bien
        a quien lee la respuesta.
        """
        _clave, motivo = self.resolver(designacion)
        return "encaja con" in (motivo or "")

    def _otra_materia(self, sobra: str, candidato) -> str:
        """La materia AJENA que sigue al alias, o cadena vacia.

        NO SE MIRA CONTRA LAS NORMAS CARGADAS, y esa fue la primera version
        equivocada: comparando con los demas cuerpos, «Texto refundido de la
        Ley del Impuesto sobre Transmisiones...» se rechazaba -su materia es
        tambien la de su Reglamento- y «...sobre la Renta de no Residentes»
        pasaba, porque esa norma no esta cargada y no habia con que comparar.

        Lo que decide no es que exista la otra norma: es que la designacion
        SIGA NOMBRANDO UN IMPUESTO QUE NO ES EL DEL CANDIDATO. Si detras del
        alias viene «Impuesto sobre ...» y no es el suyo, se habla de otra
        norma, este cargada o no.
        """
        limpio = _solo_la_materia(sobra)
        if not limpio.startswith("impuesto"):
            return ""
        # LAS DOS PARTES SE LIMPIAN IGUAL. La materia guardada del texto
        # refundido es «Ley del Impuesto sobre Transmisiones...» -con su tipo
        # delante-, asi que comparada en crudo no casaba ni consigo misma y la
        # designacion BUENA se rechazaba.
        for texto in (candidato.materia, candidato.nombre):
            suyo = _solo_la_materia(texto or "")
            if suyo and limpio.startswith(suyo):
                return ""
        return limpio[:46]

    def resolver(self, designacion: str, cuerpo_actual: str = "",
                 cola: str = "") -> tuple:
        """Nombre de norma -> (clave_de_cuerpo, motivo). Ver `nombrar`."""
        clave, motivo, _consumido = self.nombrar(designacion, cuerpo_actual, cola)
        return clave, motivo

    def nombrar(self, designacion: str, cuerpo_actual: str = "",
                cola: str = "") -> tuple:
        """Igual que `resolver`, y ademas QUE PARTE del texto era el nombre.

        Devuelve (clave_de_cuerpo, motivo, designacion_consumida).

        Lo tercero hace falta porque quien llama no sabe donde acaba el nombre:
        recorta un trozo de texto corrido y lo manda entero. El que sabe donde
        acaba es este metodo, que es el que busca el alias mas largo. Sin
        devolverlo, el motivo que lee un fiscalista nombraba el recorte -prosa
        incluida- en vez de la norma.

        Devuelve (None, motivo, ...) si no se puede decidir. ANTE LA DUDA,
        NADA: una remision sin resolver es un aviso visible; una remision
        resuelta a la norma equivocada es un articulo real, con texto real, que
        no es el que toca, y el verificador la daria por buena.
        """
        if not designacion:
            return None, "sin designacion", ""
        # Se lleva la cuenta de las palabras ORIGINALES en paralelo a las
        # normalizadas: los indices de la busqueda son de la version sin
        # tildes y sin articulo delante, y lo que se ensena por pantalla -y lo
        # que se devuelve como nombre consumido- tiene que ser el texto tal
        # cual se escribio.
        crudas = re.sub(r"\s+", " ", designacion).strip(" .,;:").split()
        d = B.sin_tildes(" ".join(crudas))
        # LA PUNTUACION DE FINAL DE PALABRA NO CUENTA PARA BUSCAR EL ALIAS.
        # «Reglamento General de Recaudacion, https://...» traia la coma pegada
        # a la ultima palabra del nombre, y por esa coma el alias no casaba. Se
        # quita solo de la copia normalizada y sin partir palabras, para que
        # `crudas` siga teniendo las mismas y los indices sigan valiendo.
        d = re.sub(r"[,;:]+(?=\s|$)", "", d)
        antes = len(d.split())
        d = re.sub(r"^(?:de[l]?\s+|en\s+)?(?:la|el|los|las)\s+", "", d).strip()
        d = re.sub(r"^(?:est[ae]|presente)\s+", "", d).strip()
        saltadas = antes - len(d.split()) if d else antes
        if not d:
            return None, "designacion vacia", ""

        # La designacion viene recortada de un texto corrido y suele arrastrar
        # cola ("Ley del Impuesto se considerara..."). Se busca el alias MAS
        # LARGO que sea prefijo suyo.
        palabras = d.split()
        candidatos: list = []
        consumidas = 0
        for n in range(len(palabras), 0, -1):
            prefijo = " ".join(palabras[:n])
            candidatos = [c for c in self.cuerpos.values() if prefijo in c.alias]
            if candidatos:
                consumidas = n
                break

        if candidatos:
            # Y AQUI ESTA LA REGLA DE ORO. Lo que queda sin consumir decide:
            # si empieza por un numero de norma, un parentesis o un nombre
            # propio, la designacion es de OTRA norma y acortar seria
            # inventarse la coincidencia. "Ley 58/2003" no es "la Ley";
            # "Reglamento (UE) 282/2011" no es el Reglamento del IVA.
            nombrado = " ".join(crudas[saltadas:saltadas + consumidas]).strip(" .,;:")
            resto_original = " ".join(crudas[saltadas + consumidas:])
            sobra = (resto_original + " " + (cola or "")).strip(" ,;:.")

            # LO QUE SOBRA PUEDE SER SU PROPIO NOMBRE, DICHO OTRA VEZ.
            #
            # DYCTEA escribe «Ley 35/2006 Impuesto sobre la Renta de las
            # Personas Fisicas»: el numero y la materia pegados, sin coma. El
            # alias «ley 35/2006» casa, y lo que sobra -«Impuesto sobre la
            # Renta...»- no es otra norma: es LA MISMA, nombrada dos veces.
            # Sin esta excepcion se rechazaba, y 147 criterios del TEAC
            # quedaban en la despensa sin poder encontrarse.
            #
            # NO AFLOJA LA REGLA DE ORO. Solo se admite si lo que sobra es la
            # materia o el nombre DE ESE MISMO CUERPO: «Ley 58/2003» detras de
            # «la Ley» sigue siendo otra norma, porque «58/2003» no es la
            # materia de la Ley del IVA.
            if _RE_DISCRIMINANTE.match(sobra) and len(candidatos) == 1:
                suyo = B.sin_tildes(candidatos[0].materia or "")
                nombre_suyo = B.sin_tildes(candidatos[0].nombre or "")
                sobra_plana = B.sin_tildes(sobra)
                if suyo and (sobra_plana.startswith(suyo)
                             or (nombre_suyo and sobra_plana.startswith(nombre_suyo))):
                    return candidatos[0].clave, (
                        f"designa a {candidatos[0].etiqueta} (su nombre "
                        f"repetido detras del numero)"), nombrado

            # LO QUE SOBRA PUEDE SER LA MATERIA DE OTRO CUERPO CARGADO, y
            # entonces no es prosa que arrastra: es OTRA NORMA.
            #
            # «Texto refundido de la Ley del Impuesto sobre Sociedades»
            # resolvia al texto refundido del ITP. El tipo -«texto refundido»-
            # es alias por si solo, y lo que sobraba -«de la Ley del Impuesto
            # sobre Sociedades»- no empieza por numero ni por parentesis, asi
            # que `_RE_DISCRIMINANTE` lo tomaba por cola inofensiva del estilo
            # «Ley del Impuesto se considerara...».
            #
            # Funcionaba mientras SOLO HABIA UN TEXTO REFUNDIDO. Con dos, un
            # alias que no dice de que impuesto es deja de identificar nada, y
            # la designacion se resolvia por prefijo ignorando justo lo que la
            # distingue.
            #
            # SE MIRA CONTRA LOS DEMAS CUERPOS, NO CONTRA UNA LISTA: si lo que
            # sobra empieza por la materia o el nombre de otro cuerpo cargado,
            # se declina. Es la misma cuenta que la excepcion de arriba -que
            # admite cuando lo que sobra es su PROPIA materia- leida al reves.
            ajena = (self._otra_materia(sobra, candidatos[0])
                     if len(candidatos) == 1 else "")
            if ajena:
                return None, (
                    f"«{designacion.strip()[:38]}» encaja por el principio "
                    f"con {candidatos[0].etiqueta}, pero sigue nombrando "
                    f"«{ajena}»: es OTRA norma, no se resuelve"), nombrado

            if _RE_DISCRIMINANTE.match(sobra):
                # Se dice QUE alias caso y QUE sobro: sin las dos mitades el
                # mensaje parece repetir el nombre y no se entiende por que se
                # rechaza algo que a simple vista encajaba.
                # Del texto ORIGINAL, no de la version normalizada: el motivo
                # lo lee una persona, y «reglamento del iva» en minusculas
                # parece un error de otra cosa.
                return None, (
                    f"«{nombrado}» es alias de una norma cargada, pero la "
                    f"designacion sigue con «{sobra[:34]}»: es OTRA norma, "
                    f"no se resuelve"
                ), nombrado

        nombrado = " ".join(crudas[saltadas:saltadas + consumidas]).strip(" .,;:")
        if len(candidatos) == 1:
            return (candidatos[0].clave,
                    f"designa a {candidatos[0].etiqueta}", nombrado)
        if len(candidatos) > 1:
            # Un demostrativo desempata a favor del cuerpo en que estamos.
            propio = [c for c in candidatos if c.clave == cuerpo_actual]
            if propio:
                return (propio[0].clave,
                        f"designa al propio {propio[0].etiqueta}", nombrado)
            return None, (
                f"«{nombrado}» encaja con "
                f"{len(candidatos)} cuerpos ({', '.join(c.etiqueta for c in candidatos)}): "
                f"no se resuelve"
            ), nombrado
        return (None,
                f"«{designacion.strip()}» no corresponde a ninguna norma cargada",
                "")
