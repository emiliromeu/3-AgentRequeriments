"""EL CRITERIO DE LA DGT, VISTO DESDE EL AGENTE.

Este modulo es el puente entre lo que `petete.py` deja en la cache y el resto
del sistema. Nada mas. Aqui se decide como se cita una consulta, como se
comprueba y que dice del estado; la descarga vive en `petete.py` y no se toca.

----------------------------------------------------------------------------
DE QUE SE FIA ESTE MODULO, Y DE QUE NO
----------------------------------------------------------------------------
EL EXTRACTOR DE HTML NUNCA HA VISTO UN DOCUMENTO REAL DE PETETE. La fuente
llevaba caida todo el reconocimiento (fase 9 y 9A), asi que el troceo del HTML
esta escrito contra las etiquetas del formulario y sin confirmar.

Por eso aqui NO se mira ni una linea de HTML. Este modulo se apoya UNICAMENTE
en la forma del REGISTRO CACHEADO, que es un JSON que escribimos nosotros:

    numero  fecha  organo  normativa  cuestion_planteada
    descripcion_hechos  contestacion  doc_id  url_navegador  descargado

Si manana el troceo cambia, cambia `petete.py` y este modulo sigue igual. Y si
un campo viene vacio, aqui se trata como ausente, nunca se adivina.

----------------------------------------------------------------------------
CRITERIO NO ES NORMA
----------------------------------------------------------------------------
Una consulta de la DGT vincula a la Administracion frente al consultante, pero
NO es una norma. No fundamenta por si sola. Todo lo de aqui esta hecho para que
esa diferencia se vea a simple vista: el formato de cita, el orden en la
respuesta y lo que se le dice al redactor.

----------------------------------------------------------------------------
EL INTERRUPTOR
----------------------------------------------------------------------------
Con la DGT APAGADA el sistema se comporta EXACTAMENTE como antes de la fase 9B.
Esta apagada por defecto, y seguira apagada hasta que el extractor haya visto un
documento real: mientras eso no pase, la DGT no esta de verdad.

    AGENTE_DGT=1 python fase4.py consultar ...     la enciende
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_CACHE = RAIZ / "datos" / "dgt"
DIR_CONSULTAS = DIR_CACHE / "consultas"
MARCA_FUENTE = DIR_CACHE / "estado_fuente.json"

VARIABLE = "AGENTE_DGT"

# Como se cita. El formato es distinto del de la ley A PROPOSITO: quien lee la
# respuesta tiene que ver sin esfuerzo que esto es criterio y no norma.
ETIQUETA = "Consulta DGT"

# "DGT V1601-22", "consulta V1601-22", "consulta vinculante V1601-22"
RE_NUM_CONSULTA = re.compile(
    r"\b(?:DGT|consulta(?:\s+vinculante)?)\s+(?P<num>[VC]?\d{3,5}-\d{2})\b",
    re.IGNORECASE,
)
RE_NUM_SUELTO = re.compile(r"\b(?P<num>V\d{3,5}-\d{2})\b")

URL_NAVEGADOR = ("https://petete.tributos.hacienda.gob.es/consultas/"
                 "?num_consulta={num}")

# ------------------------------------------------- el campo «normativa»
#
# EL FALLO QUE ESTO EVITA, Y QUE YA COSTO CARO UNA VEZ. En la fase 6 una
# remision del Reglamento se resolvia contra la Ley porque se comparaba por
# NUMERO DE ARTICULO sin mirar de que norma era. Aqui pasaba lo mismo: una
# consulta que cita «RIRPF, RD 439/2007, art. 22» se comparaba con el articulo
# 22 de la Ley del IVA como si fueran el mismo precepto. No lo son.
#
# La regla es la misma que en las remisiones: ANTE LA DUDA, NO SE COMPARA.
# Perder una señal es barato; inventarse una es lo que hace que un profesional
# lea «criterio discutido» donde no hay discusion ninguna.
#
# Quien resuelve el nombre de la norma es `normas.Registro.resolver`, el mismo
# que usan las remisiones del BOE. No hay aqui ningun resolutor nuevo, ni una
# lista de siglas escrita a mano: los alias (LIVA, RIVA, LIRPF...) los conoce
# ya el registro porque salen del titulo oficial de cada norma.

# Donde empieza la lista de articulos dentro de un trozo: "art.", "arts.",
# "articulo", "articulos", con o sin mayuscula.
# El punto de la abreviatura se consume aqui: si se deja, la lista de numeros
# empieza por "." y el lector de numeros no arranca.
_RE_MARCA_ART = re.compile(r"\bart[íi]culos?\b\.?|\barts?\b\.?", re.IGNORECASE)

# Un trozo de campo por norma. El campo mezcla separadores sin criterio:
#
#     Ley 38/1992;Ley 37/1992                          punto y coma
#     LIRPF, Ley 35/2006, Art. 33 a 36.                una sola norma, con coma
#     LIRPF, Ley 35/2006, Art. 27.\n\n LIVA, Ley 37/1992, Art. 95.
#                                                      SALTO DE LINEA
#
# El salto de linea aparecio en las consultas de 2026 y sin el se perdian los
# articulos de todas las normas menos la primera: el campo entero se leia como
# un solo bloque, ganaba el primer "art." y el resto se tiraba EN SILENCIO.
# «de la Ley 58/2003», «del Real Decreto 1065/2007»: lo que une unos numeros
# de articulo con la norma que va detras.
_RE_CONECTOR = re.compile(r"(?:de\s+(?:la|el|los|las)|del|de)\s+", re.IGNORECASE)

_RE_SEPARADOR_NORMA = re.compile(r"\s*[;\r\n]+\s*")


@dataclass(frozen=True)
class Precepto:
    """Un articulo con SU norma. El numero solo no identifica nada."""

    numero: str
    cuerpo: str = ""        # clave del cuerpo, si la norma esta cargada
    norma_bruta: str = ""   # como venia escrita
    estado: str = "sin_norma"   # cargada | externa | sin_norma
    # DE DONDE VENIA SI SE CORRIGIO DE CUERPO. Vacio si no se toco. Se guarda
    # para poder auditarlo: una correccion silenciosa es indistinguible de un
    # acierto por casualidad, y esta cambia a que norma se atribuye una cita.
    corregido_desde: str = ""
    # Si la norma se identifico ABRIENDO la abreviatura. Tambien para auditar:
    # es una conjetura nuestra, no lo que escribio la fuente.
    expandido: bool = False

    @property
    def comparable(self) -> bool:
        """Solo se compara lo que se ha podido situar en una norma CARGADA."""
        return self.estado == "cargada" and bool(self.cuerpo)

    @property
    def clave(self) -> tuple:
        """Como se agrupa: por norma Y articulo, nunca por articulo solo."""
        return (self.cuerpo or f"externa:{self.norma_bruta.lower()}",
                self.numero.lower())


@dataclass
class Normativa:
    """Lo leido del campo, y lo que NO se ha sabido leer.

    `sin_reconocer` es la parte que importa tanto como la otra: si el campo
    trae una forma nueva, hay que ENTERARSE. Perder articulos en silencio es
    peor que fallar, porque una señal que no salta parece una señal que no
    tenia que saltar.
    """

    preceptos: list = field(default_factory=list)
    sin_reconocer: list = field(default_factory=list)

    @property
    def hay_formas_nuevas(self) -> bool:
        return bool(self.sin_reconocer)


# Un resto que todavia tiene un numero dentro es un articulo que se ha perdido.
_RE_QUEDA_NUMERO = re.compile(r"\d")


def _partir_por_designaciones(trozo: str):
    """Parte «Ley 56/2007 art. 2 bis RD 1619/2012 arts. 8 y 9» en dos.

    LA DGT NO SIEMPRE PONE SEPARADOR. El campo se trocea por «;» y saltos de
    linea, y hay consultas que encadenan dos o tres normas seguidas sin
    ninguno de los dos. El trozo queda con dos designaciones dentro y
    `_resolver_designacion` lo declina por falta de unanimidad, que es lo
    correcto ante una entrada mal troceada: el problema es el troceo.

    SE PARTE DELANTE DE UNA DESIGNACION SOLO SI YA HA HABIDO UNA MARCA DE
    ARTICULO ANTES. Sin esa condicion se estaria partiendo la designacion de
    sus propios articulos y dejandolos huerfanos, o peor, pegandoselos a la
    norma vecina.

    HUBO UNA TERCERA CONDICION Y SE QUITO: no partir si la norma venia
    enganchada por «de la», «del», «aprobado por». Parecia obligatoria -es la
    forma de «Articulos 29, 227 y 249 de la Ley 58/2003»- y resulto que no
    sostiene nada: medida sobre las 845, quitarla no cambia ni un par, porque
    esa forma ya la protege la condicion de la designacion propia. Y en la
    unica sonda donde cambiaba algo, el corte acertaba. No se guarda una
    guarda que no se puede ver fallar.
    """
    cortes, pos = [], 0
    while True:
        m = _RE_NORMA_EXPLICITA.search(trozo, pos)
        if not m:
            break
        pos = m.end()          # detras de esta, no dentro: «Real Decreto ...»
        if not m.start():
            continue           # la primera del trozo no abre nada nuevo
        desde = cortes[-1] if cortes else 0
        marca = _RE_MARCA_ART.search(trozo, desde, m.start())
        if not marca:
            continue           # aun estamos en la designacion, no detras

        # Y EL TROZO DE DELANTE TIENE QUE TRAER SU PROPIA DESIGNACION, DELANTE
        # DE SU MARCA. Si no la trae, la norma que estoy mirando ES SU
        # DESIGNACION, que va detras:
        #
        #   «Articulo 93 Ley 58/2003»
        #
        # Partir ahi deja el 93 huerfano y la Ley 58/2003 sin articulos, y las
        # dos mitades se declinan. No es hipotetico: la primera version de
        # este corte hizo exactamente eso y se llevo por delante ocho
        # consultas que resolvian bien, las mismas que arreglaba mirar detras.
        propia = _RE_NORMA_EXPLICITA.search(trozo, desde, marca.start())
        if not propia:
            continue
        cortes.append(m.start())
    if not cortes:
        return [trozo]
    limites = [0, *cortes, len(trozo)]
    return [trozo[a:b] for a, b in zip(limites, limites[1:])]


# LA LISTA DE ARTICULOS DETRAS DEL NOMBRE, SIN MARCA Y SEPARADA POR GUIONES.
#
#     Ley 27/2014 Impuesto sobre Sociedades - 17 - 76 - 87
#     Ley 37/1992 Impuesto sobre el Valor Añadido IVA - 20.Uno.9º - 69 - 164
#
# EL ANCLA ES EL GUION CON ESPACIOS A LOS DOS LADOS, y no es un detalle: en
# este proyecto el guion ya significa dos cosas mas, y las dos veces que se
# toco a la ligera hubo que revertir.
#
#     80-cuatro, 10-3    apartado del articulo   (sin espacios)
#     641-14             articulo entero del Codi catalan (sin espacios)
#     - 17 - 76          separador de lista      (con espacios)
#
# Exigiendo « - » con espacios, las otras dos lecturas no se rozan: no hay un
# solo caso en el corpus ni en la despensa donde un apartado o un articulo
# catalan se escriban con espacios alrededor del guion.
#
# Y ADEMAS SOLO ACTUA EN TROZOS SIN NINGUNA MARCA DE ARTICULO. Donde hay
# «art.» manda el camino de siempre; esta forma se reconoce por lo que le
# FALTA, que es justamente lo que la hacia invisible.
# SE LEE EL ARTICULO, NO EL APARTADO. La forma trae «- 76.2 - 17.3 - 20.Uno.9º»
# y el «.2» es el apartado, igual que el «-cuatro» de «80-cuatro». Medido: los
# 29 pares con apartado NO EXISTEN en el indice y el articulo base si, o sea
# que guardarlos enteros seria bajar consultas que no se pueden encontrar,
# justo lo que la puerta de la cadena viene a impedir.
_RE_ITEM_GUION = re.compile(
    r"\s+-\s+(\d+(?:\s+(?:bis|ter|qu[aá]ter|quinquies|sexies|septies|octies|"
    r"nonies|decies))?)(?=[\s.,;)ºª-]|$)", re.IGNORECASE)


def _lista_tras_guion(trozo: str) -> list:
    """[(designacion, [numeros])] de la forma «Norma Nombre - 17 - 76».

    Lista vacia si el trozo no es de esa forma, que es lo que pasa con todo lo
    demas: asi este camino no puede cambiar ni una consulta de las que ya
    resuelven.
    """
    if _RE_MARCA_ART.search(trozo):
        return []                       # con marca manda el camino de siempre
    if not _RE_ITEM_GUION.search(trozo):
        return []
    # Se parte por cada designacion explicita: un trozo puede traer dos normas
    # con su lista cada una, y aqui no hay marca que sirva de frontera.
    cortes = []
    pos = 0
    while True:
        m = _RE_NORMA_EXPLICITA.search(trozo, pos)
        if not m:
            break
        cortes.append(m.start())
        pos = m.end()
    if not cortes:
        return []
    limites = [*cortes, len(trozo)]
    fuera = []
    for a, b in zip(limites, limites[1:]):
        pieza = trozo[a:b]
        nums = _RE_ITEM_GUION.findall(pieza)
        if not nums:
            continue
        # La designacion es lo que va ANTES del primer guion de la lista.
        corte = _RE_ITEM_GUION.search(pieza).start()
        fuera.append((pieza[:corte].strip(" ,.;:"), nums))
    return fuera


def analizar_normativa(texto: str, normas=None) -> Normativa:
    """Como `pares_de_normativa`, pero contando ademas lo que no se reconocio."""
    from . import referencias as R

    salida = Normativa()
    # La marca doblada se deshace ANTES de trocear: si se dejara para despues,
    # el troceo ya habria decidido donde acaba la designacion mirando una marca
    # que no es la buena.
    texto = _desdoblar_marca(texto)
    troceado = [sub
                for bruto in _RE_SEPARADOR_NORMA.split(texto or "")
                for sub in _partir_por_designaciones(bruto)]
    for trozo in troceado:
        trozo = trozo.strip()
        if not trozo:
            continue

        m = _RE_MARCA_ART.search(trozo)
        designacion = (trozo[:m.start()] if m else trozo).strip(" ,.;:")
        if m:
            numeros, resto = R.leer_numeros(trozo[m.end():])

            # LA DESIGNACION PUEDE IR DETRAS DE LOS ARTICULOS.
            #
            #     «Articulos 29, 227 y 249 de la Ley 58/2003, de 17 de
            #      diciembre, General Tributaria»
            #
            # Aqui la marca abre el trozo y lo de delante esta vacio, asi que
            # la designacion salia vacia y no se resolvia nada. Es el mismo
            # error de direccion que ya se arreglo en las remisiones del BOE:
            # mirar solo hacia un lado.
            #
            # SOLO ACTUA CUANDO DELANTE NO HAY NADA. Literal: la designacion
            # vacia. Ni «casi nada», ni «nada que yo reconozca».
            #
            # La primera version pedia «que delante no haya una norma
            # EXPLICITA», usando `_RE_NORMA_EXPLICITA`. Y eso no es lo mismo:
            # ese patron no reconoce «RDLeg 1/1993», asi que en
            #
            #   «... TRLITPAJD RDLeg 1/1993 arts 19, 21, 45. RDLeg 4/2015 ...»
            #
            # creyo que delante no habia norma, miro detras y ATRIBUYO LOS
            # ARTICULOS 19, 21 Y 45 DEL TEXTO REFUNDIDO DE ITP A LA LEY DEL
            # IVA. Una mal resuelta, y de las peores: articulos reales de otra
            # norma pegados a la nuestra.
            #
            # Con la guarda estricta la rama no puede tocar NADA de lo que ya
            # resolvia, porque solo entra donde no habia designacion ninguna.
            # Y LA NORMA TIENE QUE IR PEGADA A LOS NUMEROS. No «en algun
            # sitio de lo que viene detras»: pegada, con «de la» o sin nada.
            #
            #   «Art. 9.Bis Regl. 282/2011 Ley 37/1992 art. 11 y 69»
            #
            # Buscando en todo lo de detras se encuentra «Ley 37/1992» -porque
            # «Regl. 282/2011» no se reconoce- y el articulo 9 bis del
            # reglamento europeo acaba atribuido a la Ley del IVA. Otra vez lo
            # mismo: saltar por encima de una designacion que no entiendo.
            #
            # Anclada al principio del resto, ese caso no pasa: detras del 9
            # viene «.Bis Regl. 282/2011...», que no empieza por norma. Se
            # queda sin resolver, que es lo correcto.
            if not designacion.strip():
                detras = (resto or trozo[m.end():]).lstrip(" ,.;:")
                conector = _RE_CONECTOR.match(detras)
                if conector:
                    detras = detras[conector.end():]
                primera = _RE_NORMA_EXPLICITA.match(detras)
                if primera:
                    # Y SE CORTA DONDE EMPIEZA OTRA COSA. Quedarse con todo lo
                    # de detras mete dos normas en la designacion:
                    #
                    #   «Art. 214 Directiva 2006/112/CE Ley 37/1992 art. 25-Tres»
                    #
                    # El 214 es de la Directiva; sin cortar, la designacion
                    # incluia tambien «Ley 37/1992» y el articulo acababa en la
                    # Ley del IVA. Cortando en la siguiente norma queda solo la
                    # Directiva, que no tenemos, y no se resuelve. Correcto.
                    fin = len(detras)
                    # DETRAS DE LA PRIMERA, no dentro. Buscando desde el
                    # indice 1, «Real Decreto 1065/2007» encuentra su propio
                    # «Decreto 1065/2007» y se corta a si misma en «Real».
                    otra = _RE_NORMA_EXPLICITA.search(detras, primera.end())
                    if otra:
                        fin = min(fin, otra.start())
                    marca = _RE_MARCA_ART.search(detras)
                    if marca:
                        fin = min(fin, marca.start())
                    designacion = detras[:fin].strip(" ,.;:")
        else:
            numeros, resto = [], ""
            # Un trozo sin marca de articulo es normal ("Ley 38/1992" a secas):
            # nombra la norma y no cita ningun precepto. No es forma nueva.
            #
            # PERO DESDE 2026 LA DGT ESCRIBE ASI, Y NO LLEVA MARCA NINGUNA:
            #
            #     Ley 27/2014 Impuesto sobre Sociedades - 17 - 76 - 87
            #
            # `_lista_tras_guion` la lee. Devuelve [] para todo lo demas, asi
            # que este trozo sigue comportandose igual que siempre.
            for desig, nums in _lista_tras_guion(trozo):
                cuerpo_g, estado_g = _resolver_designacion(desig, normas)
                for n in nums:
                    salida.preceptos.append(
                        _precepto(n, cuerpo_g, desig, estado_g, normas))
            if _lista_tras_guion(trozo):
                continue

        cuerpo, estado = _resolver_designacion(designacion, normas)

        for n in numeros:
            salida.preceptos.append(
                _precepto(n, cuerpo, designacion, estado, normas))
        if m and _RE_QUEDA_NUMERO.search(resto):
            salida.sin_reconocer.append(
                f"«{trozo.strip()}»: se leyeron {numeros or 'ningun articulo'} "
                f"y quedo sin leer «{resto.strip()[:40]}»")
    return salida


# LA MARCA DE ARTICULO, ESCRITA DOS VECES.
#
#     «TRLITPAJD RDLeg 1/1993 arts. Arts- 7, 31-2 y 57»
#     «RITPAJD RD 828/1995 art. Art 70»
#     «Ley 29/1987 arts. - 3, 4 y 30»
#
# La plantilla pone el rotulo -«arts.»- y encima el redactor escribe el suyo.
# El lector consume la primera marca y se encuentra una palabra donde esperaba
# un numero, asi que pierde la lista entera. Se ve sobre todo en documentos de
# 2025 y 2026: parece plantilla nueva.
#
# Y AQUI ESTA EL CUIDADO, que es todo el problema: «art. 70-2» es el articulo
# 70 apartado 2, y «art. 7-1-A)» tambien. Un patron que se coma un guion detras
# de la marca se lleva por delante el apartado y convierte el 70-2 en el 70 y
# el 2, que son DOS articulos que nadie cito.
#
# Por eso la segunda marca tiene que ser UNA PALABRA «art» de verdad, no
# cualquier cosa: se exige `art`/`arts` completo. Lo unico que se admite sin
# segunda palabra es el guion suelto pegado al rotulo -«arts. - 3»-, y ahi el
# guion va SEGUIDO DE ESPACIO, que es lo que lo distingue de «70-2».
_RE_MARCA_DOBLE = re.compile(
    r"\b(arts?\.?)\s*[:.]?\s+(?:arts?)\b\.?\s*-?\s*", re.IGNORECASE)
_RE_MARCA_GUION = re.compile(r"\b(arts?\.)\s+-\s+(?=\d)", re.IGNORECASE)


def _desdoblar_marca(texto: str) -> str:
    """«arts. Arts- 7» -> «arts. 7». Deja «art. 70-2» intacto."""
    t = _RE_MARCA_DOBLE.sub(r"\1 ", texto or "")
    return _RE_MARCA_GUION.sub(r"\1 ", t)


def pares_de_normativa(texto: str, normas=None) -> list:
    """«Ley 37/1992 arts. 75, 78, 80-cuatro, 89» -> cuatro Preceptos de la LIVA.

    Formas reales que se han visto en la cache y que hay que aguantar:

        Ley 37/1992 art. 95, 130              lista
        Ley 37/1992 arts. 75, 78, 80-cuatro   plural, y apartado pegado
        LIRPF, Ley 35/2006, Art. 33 a 36.     sigla + rango
        Ley 38/1992;Ley 37/1992               dos normas, sin articulos
        RIRPF, RD 439/2007, art. 22           otra norma, articulo que existe
                                              tambien en la nuestra

    La lista de numeros la lee `referencias.numeros_citados`, que es la misma
    que usa el grafo de remisiones para el BOE: listas, rangos y sufijos.
    """
    return analizar_normativa(texto, normas).preceptos


# Una designacion explicita: rango + numero/año. Es la forma que NO admite dos
# lecturas, y por eso es la que se busca cuando el trozo entero no resuelve.
_RE_NORMA_EXPLICITA = re.compile(
    r"\b(?:Ley\s+Org[aá]nica|Ley|Real\s+Decreto(?:\s+Legislativo|-ley)?|RD|"
    r"Reglamento|"
    r"Decreto|Orden|Directiva)\s+\d+/\d{2,4}", re.IGNORECASE)
# El «Legislativo» va en el patron de arriba, en la alternativa del Real
# Decreto. Sin el, «Real Decreto Legislativo 1/1993» NO se extraia, y eso
# tumbaba la abreviatura entera en cuanto llevaba sigla delante: «RDLeg
# 1/1993» a secas se resuelve por la cadena completa, pero «TRLITPAJD RDLeg
# 1/1993» -que es como la DGT escribe SIEMPRE el ITPAJD- no tenia ninguna
# candidata que resolviera. Por eso ITPAJD e ISD eran los peores del campo: sus
# normas solo se nombran abreviadas.


# LA ABREVIATURA DEL REAL DECRETO, QUE ERA LA MAYOR DEUDA DEL CAMPO.
#
# La fuente escribe «RD 439/2007» y «RDLeg 1/1993», y el resolutor solo conocia
# el nombre entero. Eran 68 consultas de 128 sin poder encontrarse.
#
# NO SE TRAGA LO QUE SE LE PAREZCA, y la diferencia no es cosmetica: «RDL» y
# «RD-ley» son el Real Decreto-LEY, que es OTRA norma con su propia numeracion.
# Expandir «RDL 8/2020» a «Real Decreto 8/2020» seria atribuirle articulos a
# quien no los dijo. Detras del rotulo tiene que venir el numero, y «Leg» se
# escribe entero.
_RE_ABREV_RDLEG = re.compile(r"\bRD\s*-?\s*Leg\.?\s*(\d+/\d{4})", re.IGNORECASE)
_RE_ABREV_RD = re.compile(r"\bRD\.?\s+(\d+/\d{4})", re.IGNORECASE)


def _expandir_abreviatura(designacion: str) -> str:
    """«RD 439/2007» -> «Real Decreto 439/2007». Deja lo demas igual."""
    d = _RE_ABREV_RDLEG.sub(r"Real Decreto Legislativo \1", designacion or "")
    return _RE_ABREV_RD.sub(r"Real Decreto \1", d)


def _precepto(numero: str, cuerpo: str, designacion: str, estado: str,
              normas=None) -> "Precepto":
    """Construye el Precepto APLICANDO la correccion de cuerpo.

    VA AQUI Y NO EN `_resolver_designacion` porque la correccion necesita el
    NUMERO del articulo, y la designacion se resuelve una vez para toda la
    lista: «Real Decreto 939/2005 arts. 82, 3» puede tener que corregir uno y
    el otro no. Y va en UNA funcion porque hay dos sitios que construyen
    Preceptos -la forma normal y la lista tras guion- y una regla que solo se
    aplica en uno de ellos es una regla que no se aplica.
    """
    if normas is not None and estado == "cargada" and cuerpo:
        hermano = normas.cuerpo_hermano_con(cuerpo, numero)
        if hermano:
            return Precepto(numero=numero, cuerpo=hermano,
                            norma_bruta=designacion, estado=estado,
                            corregido_desde=cuerpo)
        return Precepto(numero=numero, cuerpo=cuerpo,
                        norma_bruta=designacion, estado=estado)

    # LA ABREVIATURA, SOLO SI TAL CUAL NO HA RESUELTO. Se prueba lo que escribio
    # la fuente ANTES que lo que nosotros interpretamos, asi que abrir la
    # abreviatura no puede mover ni una cita que ya resolvia: solo llega a las
    # que se perdian.
    #
    # Y SE DECLINA SI EL ARTICULO NO EXISTE DONDE ATERRIZA. Esta es la
    # contencion propia de la expansion, y es distinta de la del hermano: ahi
    # respetamos lo que la fuente escribio aunque el articulo no exista -no
    # inventamos-, pero aqui la designacion la hemos interpretado NOSOTROS, y
    # una conjetura que no se puede corroborar no se queda. Medido: sin esto
    # entraban TRES citas a articulos que no existen en ninguno de los dos
    # cuerpos -«RD 1619/2012 art. 201», y ese reglamento tiene 27-.
    if normas is not None and estado != "cargada":
        abierta = _expandir_abreviatura(designacion)
        if abierta != designacion:
            c2, e2 = _resolver_designacion(abierta, normas)
            if e2 == "cargada" and c2:
                c2 = normas.cuerpo_hermano_con(c2, numero) or c2
                if normas.tiene_articulo(c2, numero):
                    return Precepto(numero=numero, cuerpo=c2,
                                    norma_bruta=designacion, estado="cargada",
                                    expandido=True)

    return Precepto(numero=numero, cuerpo=cuerpo, norma_bruta=designacion,
                    estado=estado)


def _resolver_designacion(designacion: str, normas=None) -> tuple:
    """(clave_cuerpo, estado) para el nombre de norma de un trozo del campo.

    El campo escribe la misma norma de dos maneras a la vez y sin separador:
    «LIVA Ley 37/1992». Pasarselo entero al resolutor no vale -y hace bien en
    no valer-: para el es un alias seguido de OTRA norma, que es justo el caso
    en que no debe adivinar.

    Asi que se prueban varias designaciones del mismo trozo y se exige que
    TODAS las que resuelvan lleven al mismo cuerpo. Si dos llevan a cuerpos
    distintos, no se resuelve: es la misma regla de siempre, ante la duda nada.

    NO se prueban trozos recortados a mano («Ley» suelto sacado de «Ley
    27/2014»): eso resolveria a la Ley del IVA y le atribuiria articulos de la
    Ley del Impuesto sobre Sociedades. Solo se prueban designaciones enteras.
    """
    if normas is None or not designacion:
        return "", "sin_norma"

    candidatas = [designacion]
    candidatas += _RE_NORMA_EXPLICITA.findall(designacion)
    candidatas += [p.strip() for p in designacion.split(",") if p.strip()]

    encontrados = set()
    for c in candidatas:
        clave, _motivo = normas.resolver(c)
        if clave:
            encontrados.add(clave)

    if len(encontrados) == 1:
        return encontrados.pop(), "cargada"
    if len(encontrados) > 1:
        # El trozo nombra dos normas cargadas distintas: no se sabe de cual es
        # el articulo, asi que no se compara con ninguna.
        return "", "sin_norma"
    return "", ("externa" if _parece_norma(designacion) else "sin_norma")


_RE_PARECE_NORMA = re.compile(
    r"\b(?:ley|real\s+decreto|rd|reglamento|decreto|orden|directiva|"
    r"l[a-z]{2,5}|r[a-z]{2,5})\b", re.IGNORECASE)


def _parece_norma(designacion: str) -> bool:
    """¿Esto nombra una norma, aunque no la tengamos? «Ley 38/1992», si."""
    return bool(_RE_PARECE_NORMA.search(designacion or ""))


def activa() -> bool:
    """Si la DGT participa. Apagada por defecto: ver la cabecera.

    El interruptor de verdad esta en `configuracion`: un solo modo para las
    cuatro piezas. La variable de entorno sigue mandando sobre el fichero, que
    es lo que permite a las suites encender la DGT para UNA ejecucion sin
    tocar como esta configurado el equipo.
    """
    from . import configuracion as C
    return C.con_criterio()


# --------------------------------------------------------------- la consulta


@dataclass
class Consulta:
    """Una consulta cacheada. Solo campos del registro, nada de HTML."""

    numero: str
    fecha: str = ""
    organo: str = ""
    normativa: str = ""
    cuestion: str = ""
    hechos: str = ""
    contestacion: str = ""
    url: str = ""
    descargado: str = ""

    @classmethod
    def de_registro(cls, r: dict) -> "Consulta":
        return cls(
            numero=(r.get("numero") or "").upper(),
            fecha=r.get("fecha") or "",
            organo=r.get("organo") or "",
            normativa=r.get("normativa") or "",
            cuestion=r.get("cuestion_planteada") or "",
            hechos=r.get("descripcion_hechos") or "",
            contestacion=r.get("contestacion") or "",
            url=r.get("url_navegador") or URL_NAVEGADOR.format(
                num=(r.get("numero") or "").upper()),
            descargado=r.get("descargado") or "",
        )

    @property
    def anio(self) -> int | None:
        """El año de la consulta. Sale del numero (V1601-**22**), y si no, de
        la fecha. El numero es mas fiable: la fecha la escribe la plantilla."""
        m = re.search(r"-(\d{2})$", self.numero)
        if m:
            n = int(m.group(1))
            return 2000 + n if n < 80 else 1900 + n
        m = re.search(r"(\d{4})", self.fecha)
        return int(m.group(1)) if m else None

    def preceptos(self, normas=None) -> list:
        """El campo 'normativa' -> lista de `Precepto`, con SU norma cada uno.

        Ver `pares_de_normativa`. Si no se pasa el registro de normas, los
        preceptos salen sin resolver y por tanto no se comparan con nada.
        """
        return pares_de_normativa(self.normativa or "", normas)

    def cita(self) -> str:
        """El formato de cita. Numero, fecha y enlace de navegador."""
        fecha = f", de {self.fecha}" if self.fecha else ""
        return f"[{ETIQUETA} {self.numero}{fecha} — {self.url}]"


# ------------------------------------------------------------------- la cache


class CacheDGT:
    """Lectura de lo que dejo `petete.py`. Solo lectura: aqui no se descarga."""

    def __init__(self, directorio: Path | None = None):
        self.dir = Path(directorio) if directorio else DIR_CONSULTAS
        self._memo: dict[str, Consulta | None] = {}

    def leer(self, numero: str) -> Consulta | None:
        numero = (numero or "").upper()
        if numero in self._memo:
            return self._memo[numero]
        f = self.dir / f"{numero}.json"
        consulta = None
        if f.is_file():
            try:
                consulta = Consulta.de_registro(
                    json.loads(f.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                consulta = None
        self._memo[numero] = consulta
        return consulta

    def tiene(self, numero: str) -> bool:
        return self.leer(numero) is not None

    def todas(self) -> list:
        if not self.dir.is_dir():
            return []
        salida = []
        for f in sorted(self.dir.glob("*.json")):
            c = self.leer(f.stem)
            if c:
                salida.append(c)
        return salida

    def buscar(self, terminos: str, tope: int = 3) -> list:
        """Busqueda LOCAL sobre lo cacheado. No sale a la red jamas.

        Es deliberadamente simple -cobertura de palabras- porque su trabajo no
        es rankear: es traer criterio que ya tenemos para que el redactor lo
        vea. Lo que decide la respuesta sigue siendo la ley.
        """
        from . import texto as T

        raices = set(T.tokenizar(terminos))
        if not raices:
            return []
        puntuadas = []
        for c in self.todas():
            campos = " ".join((c.cuestion, c.hechos, c.normativa,
                               c.contestacion))
            presentes = set(T.tokenizar(campos))
            comunes = raices & presentes
            if not comunes:
                continue
            puntuadas.append((len(comunes) / len(raices), c.anio or 0, c))
        # Mas cobertura primero; a igualdad, la mas reciente. La fecha manda.
        puntuadas.sort(key=lambda x: (-x[0], -x[1]))
        return [c for _, _, c in puntuadas[:tope]]


# ------------------------------------------------------- el estado de la fuente


def marcar_fuente(viva: bool, motivo: str = "") -> None:
    """Deja escrito si la fuente respondia la ultima vez. Lo escribe el canario."""
    DIR_CACHE.mkdir(parents=True, exist_ok=True)
    MARCA_FUENTE.write_text(json.dumps({
        "viva": bool(viva),
        "motivo": motivo,
        "cuando": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def fuente_viva() -> tuple[bool, str]:
    """(viva, motivo). Si nunca se ha comprobado, se asume CAIDA.

    Asumir que esta viva sin haberlo comprobado seria justo el fallo que la
    fase 9B viene a evitar: responder como si tuvieramos criterio cuando no
    sabemos si lo tenemos.
    """
    if not MARCA_FUENTE.is_file():
        return False, "la fuente no se ha comprobado todavia"
    try:
        d = json.loads(MARCA_FUENTE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False, "no se ha podido leer el estado de la fuente"
    return bool(d.get("viva")), d.get("motivo", "")


# --------------------------------------------------------- señales de estado


@dataclass
class Lectura:
    """Lo que la DGT aporta a una respuesta, ya masticado para el estado.

    DOS LISTAS, DOS EJES. `senales` es DESACUERDO DE FONDO y mueve el estado a
    DISCUTIDO; `cobertura` es lo que no se ha podido comprobar y se enseña sin
    tocar el estado. Ver la cabecera de `estado.py`.
    """

    consultas: list = field(default_factory=list)   # Consulta, verificadas
    senales: list = field(default_factory=list)     # desacuerdo -> DISCUTIDO
    cobertura: list = field(default_factory=list)   # huecos -> solo se enseñan
    antecedentes: list = field(default_factory=list)
    fuente_caida: bool = False
    motivo_fuente: str = ""

    @property
    def hay_discusion(self) -> bool:
        return bool(self.senales)


def _agrupar_por_precepto(consultas: list, normas=None) -> dict:
    """Agrupa por (NORMA, articulo). Nunca por articulo solo.

    Las consultas cuyo precepto no se ha podido situar en una norma cargada NO
    entran en ningun grupo: no se pueden comparar con nada, ni entre ellas.
    """
    grupos: dict = {}
    for c in consultas:
        for p in c.preceptos(normas):
            if not p.comparable:
                continue
            grupos.setdefault(p.clave, {"precepto": p, "consultas": []})
            grupos[p.clave]["consultas"].append(c)
    return grupos


def impuestos_de(consulta, normas) -> set:
    """De que impuesto(s) trata una consulta, segun su campo `normativa`.

    Hace falta para no mentir en pantalla. La copia local se llenó con
    consultas de IVA, y cuando llega una pregunta de Renta el seleccionador
    trae algunas por COINCIDENCIA DE NUMERO DE ARTICULO -el 30 existe en las
    dos leyes-. Decir entonces «se le pusieron delante 3 consultas y ninguna
    sostiene la respuesta» da a entender que se ha mirado el criterio de Renta,
    y no se ha mirado: lo que se miro era de otro impuesto.

    Se resuelve la normativa a cuerpos y se mira la materia de cada uno. Una
    misma consulta puede tratar de dos impuestos a la vez, y varias lo hacen.
    """
    from .normas import _acronimo, es_materia_de_impuesto

    salida = set()
    for par in pares_de_normativa(getattr(consulta, "normativa", "") or "", normas):
        clave = getattr(par, "clave", None)
        if not clave:
            continue
        cuerpo = normas.cuerpos.get(clave[0])
        if cuerpo is not None and es_materia_de_impuesto(cuerpo.materia):
            salida.add(_acronimo(cuerpo.materia))
    return salida


def leer_criterio(consultas: list, preceptos_verificados: list,
                  normas=None) -> Lectura:
    """Convierte las consultas citadas en señales de estado. LO CALCULA EL CODIGO.

    `consultas` tienen que ser SOLO las que tienen texto en el material (ver
    `redactor.Plan.enviadas`). No es una recomendacion: una consulta que el
    recorte no mando no la ve el redactor, no la puede citar y no puede
    confundir a nadie, asi que avisar de ella es ruido puro. Medido: pasando
    todas las que devuelve el buscador local salian 2,5 avisos por consulta de
    este tipo; pasando solo las mandadas, 0,9.

    IMPORTANTE, y conviene no engañarse: el codigo NO puede leer si un criterio
    «apunta en otra direccion» que la norma. Eso es semantica y aqui no hay
    quien la juzgue. Lo que si se puede medir son señales ESTRUCTURALES, que es
    lo que se hace, y cada una dice exactamente lo que sabe:

      1. varias consultas sobre el MISMO precepto y de años distintos
         -> el criterio ha podido evolucionar. La mas reciente manda y las
            anteriores se citan como antecedente. Esto SI es desacuerdo de
            fondo -dos textos de la misma casa sobre el mismo articulo- y va a
            `senales`, que mueve el estado.
      2. una consulta cuyo campo 'normativa' NO toca ninguno de los preceptos
         que sostienen la respuesta
         -> el criterio va de otra cosa. Eso NO es desacuerdo: es criterio que
            no se ha podido contrastar, asi que va a `cobertura` y se enseña
            sin tocar el estado. Meterlo en el mismo cajon que el punto 1 era
            parte de por que DISCUTIDO salia casi siempre.
    """
    lectura = Lectura(consultas=list(consultas))
    if not consultas:
        return lectura

    # Lo que sostiene la respuesta, tambien como pares (cuerpo, articulo). Se
    # aceptan claves completas del corpus ("BOE-...#0#articulo 80") o pares ya
    # hechos; una cadena suelta como "Articulo 80" NO vale, porque no dice de
    # que norma es y era justo el fallo que se esta corrigiendo.
    verificados = set()
    for p in (preceptos_verificados or []):
        if isinstance(p, (tuple, list)) and len(p) == 2:
            verificados.add((p[0], str(p[1]).lower()))
        elif isinstance(p, str) and p.count("#") >= 2:
            norma_id, indice, referencia = p.split("#", 2)
            numero = re.sub(r"^articulo\s+", "", referencia.strip(), flags=re.I)
            verificados.add((f"{norma_id}#{indice}", numero.lower()))

    # --- 1. el tiempo: la mas reciente manda ---------------------------
    for _clave, grupo in _agrupar_por_precepto(consultas, normas).items():
        cs, precepto = grupo["consultas"], grupo["precepto"]
        if len(cs) < 2:
            continue
        anios = {c.anio for c in cs if c.anio}
        if len(anios) < 2:
            continue
        ordenadas = sorted(cs, key=lambda c: c.anio or 0, reverse=True)
        reciente, previas = ordenadas[0], ordenadas[1:]
        etiqueta = _nombrar(precepto, normas)
        lectura.senales.append(
            f"sobre el {etiqueta} hay {len(cs)} consultas de años "
            f"distintos: la mas reciente es {reciente.numero} "
            f"({reciente.anio}) y es la que manda; "
            f"{', '.join(c.numero for c in previas)} "
            f"{'son' if len(previas) > 1 else 'es'} anterior"
            f"{'es' if len(previas) > 1 else ''} y puede estar superad"
            f"{'as' if len(previas) > 1 else 'a'}"
        )
        lectura.antecedentes.extend(previas)

    # --- 2. criterio que no habla de lo que sostiene la respuesta -------
    #
    # Solo se mira si hay ALGO comparable. Una consulta de otra norma no
    # "desalinea" nada: simplemente va de otra cosa, y decir lo contrario
    # seria la señal inventada que no queremos.
    if verificados:
        for c in consultas:
            comparables = [p for p in c.preceptos(normas) if p.comparable]
            if not comparables:
                continue
            if not any((p.cuerpo, p.numero.lower()) in verificados
                       for p in comparables):
                lectura.cobertura.append(
                    f"{c.numero} da criterio sobre {c.normativa or 'otra norma'}, "
                    f"que no es lo que sostiene esta respuesta: no se ha podido "
                    f"contrastar con la lectura de la norma"
                )

    return lectura


def _nombrar(precepto, normas=None) -> str:
    """«articulo 80 de la Ley 37/1992». Nunca «articulo 80» a secas."""
    if normas is not None and precepto.cuerpo:
        cuerpo = normas.por_clave(precepto.cuerpo)
        if cuerpo:
            return f"articulo {precepto.numero} de {cuerpo.etiqueta}"
    return f"articulo {precepto.numero}"
