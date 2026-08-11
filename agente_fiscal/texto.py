"""Normalizacion, palabras vacias y lematizado para la busqueda.

Todo deterministico y con la libreria estandar. Aqui no hay IA de ninguna clase:
son reglas de sufijos del castellano.

POR QUE HACE FALTA LEMATIZAR: quien pregunta escribe "deduccion de un vehiculo"
y la ley dice "deducir" y "vehiculos". Comparando palabra a palabra no hay
coincidencia y el articulo correcto no sale. Reduciendo ambas a su raiz
(deduc-, vehicul-) si.
"""

from __future__ import annotations

import re
import unicodedata

VOCALES = "aeiou"

# Palabras vacias del castellano. Deliberadamente NO incluye terminos con carga
# fiscal (ley, articulo, impuesto, cuota, bienes...): esos los degrada solo el
# idf, que es quien sabe cuantas veces salen de verdad en este corpus.
PALABRAS_VACIAS = frozenset(
    """
    a al algo algun alguna algunas alguno algunos ante antes aquel aquella
    aquellas aquellos aqui asi aun aunque bajo bien cada casi como con contra
    cual cuales cuando cuanto cuyo cuya cuyos cuyas de del desde donde dos e el
    ella ellas ellos en entre era eran eres es esa esas ese eso esos esta estan
    estas este esto estos fue fueron ha habia han hasta hay la las le les lo los
    mas me mi mientras mismo misma mismos mismas mucho muy nada ni no nos o os
    otra otras otro otros para pero poco por porque que quien quienes se sea
    sean segun ser si sido sin sobre solo son su sus tal tambien tanto te tiene
    tienen toda todas todo todos tras un una unas uno unos y ya
    """.split()
)


def sin_tildes(texto: str) -> str:
    """Quita tildes y pasa a minusculas."""
    d = unicodedata.normalize("NFD", texto)
    return "".join(c for c in d if unicodedata.category(c) != "Mn").lower()


_RE_PALABRA = re.compile(r"[a-z0-9]+(?:[ºª])?")


def _regiones(p: str) -> tuple[int, int, int]:
    """Regiones R1, R2 y RV del algoritmo de Snowball para el castellano."""
    n = len(p)
    r1 = n
    for i in range(n - 1):
        if p[i] in VOCALES and p[i + 1] not in VOCALES:
            r1 = i + 2
            break
    r2 = n
    for i in range(r1, n - 1):
        if p[i] in VOCALES and p[i + 1] not in VOCALES:
            r2 = i + 2
            break

    rv = n
    if n > 3:
        if p[1] not in VOCALES:
            # consonante en segunda posicion: hasta la siguiente vocal
            for i in range(2, n):
                if p[i] in VOCALES:
                    rv = i + 1
                    break
        elif p[0] in VOCALES and p[1] in VOCALES:
            # dos vocales: hasta la siguiente consonante
            for i in range(2, n):
                if p[i] not in VOCALES:
                    rv = i + 1
                    break
        else:
            rv = 3
    return r1, r2, rv


def _acaba(p: str, suf: str, region: int) -> bool:
    return p.endswith(suf) and len(p) - len(suf) >= region


def _quitar(p: str, sufijos, region: int) -> tuple[str, str]:
    """Quita el sufijo mas largo que encaje dentro de `region`."""
    for s in sorted(sufijos, key=len, reverse=True):
        if _acaba(p, s, region):
            return p[: -len(s)], s
    return p, ""


_S1_BORRAR = (
    "anza anzas ico ica icos icas ismo ismos able ables ible ibles ista istas "
    "oso osa osos osas amiento amientos imiento imientos"
).split()
_S1_IC = "adora ador acion adoras adores aciones antes ancia ancias".split()
_S1_IDAD = "idad idades".split()
_S1_IVO = "iva ivo ivas ivos".split()

_S2B = (
    "ieron iendo iera ieras ieran ieses iesen iese ieseis aria arias arian "
    "ariais ariamos eria erias erian eriais eriamos iria irias irian iriais "
    "iriamos aban abas abais abamos aran aras arais aramos aren ares asen "
    "ases aseis asemos aron ando ados adas ados idos idas ada ado ida ido "
    "aba abas ara aras ase ases are ares aria ase ad ed id ar er ir "
    "amos iais eis eis en es is as os an"
).split()


def lematizar(p: str) -> str:
    """Raiz aproximada de una palabra castellana (Snowball ES, version compacta).

    No pretende ser linguisticamente perfecta: pretende que "deduccion",
    "deducciones", "deducir" y "deducibles" caigan en la misma clave.
    """
    if len(p) <= 3 or p.isdigit():
        return p

    r1, r2, rv = _regiones(p)
    original = p

    # -- paso 1: sufijos nominales --
    hecho = False
    for suf in sorted(_S1_BORRAR, key=len, reverse=True):
        if _acaba(p, suf, r2):
            p, hecho = p[: -len(suf)], True
            break
    if not hecho:
        for suf in sorted(_S1_IC, key=len, reverse=True):
            if _acaba(p, suf, r2):
                p = p[: -len(suf)]
                if _acaba(p, "ic", r2):
                    p = p[:-2]
                hecho = True
                break
    if not hecho:
        for suf in sorted(_S1_IDAD, key=len, reverse=True):
            if _acaba(p, suf, r2):
                p = p[: -len(suf)]
                for extra in ("abil", "ic", "iv"):
                    if _acaba(p, extra, r2):
                        p = p[: -len(extra)]
                        break
                hecho = True
                break
    if not hecho:
        for suf in sorted(_S1_IVO, key=len, reverse=True):
            if _acaba(p, suf, r2):
                p = p[: -len(suf)]
                if _acaba(p, "at", r2):
                    p = p[:-2]
                hecho = True
                break
    if not hecho:
        # La pareja -uccion / -ucir es la que mas duele en materia fiscal:
        # "deduccion" y "deducir" tienen que caer en la misma raiz (deduc-), y
        # con las reglas de Snowball a secas no lo hacen. Vale igual para
        # producir/produccion y reducir/reduccion.
        # -uccion va con R1, no con R2: en "deduccion" el sufijo empieza antes
        # de R2 y con la regla estandar no llegaria a aplicarse nunca.
        for suf, rep in (("ucciones", "uc"), ("uccion", "uc")):
            if _acaba(p, suf, r1):
                p, hecho = p[: -len(suf)] + rep, True
                break
    if not hecho:
        for suf, rep in (("logias", "log"), ("logia", "log"),
                         ("uciones", "u"), ("ucion", "u"),
                         ("encias", "ente"), ("encia", "ente")):
            if _acaba(p, suf, r2):
                p, hecho = p[: -len(suf)] + rep, True
                break
    if not hecho and _acaba(p, "mente", r1):
        p, hecho = p[:-5], True

    # -- paso 2: terminaciones verbales (solo si el paso 1 no toco nada) --
    if not hecho:
        p2, quitado = _quitar(p, _S2B, rv)
        if quitado:
            p = p2
            if p.endswith("gu"):
                p = p[:-1]
            hecho = True

    # -- paso 3: residuo --
    if not hecho:
        for suf in ("os", "a", "o", "e"):
            if _acaba(p, suf, rv):
                p = p[: -len(suf)]
                break

    # Una raiz de una o dos letras no distingue nada: mejor la palabra entera.
    return p if len(p) >= 3 else original


_RE_CORTE_PDF = re.compile(r"([a-záéíóúüñ])-[ \t]*\r?\n[ \t]*([a-záéíóúüñ])")


def unir_cortes_de_linea(texto: str) -> str:
    """Deshace la particion de palabras al final de renglon de un PDF.

    Al copiar de un requerimiento en PDF, una palabra partida llega asi:

        ...la deduc-
        cion del IVA de un co-
        che...

    Sin esto, el tokenizador ve `deduc`, `cion`, `co` y `che`, que no son
    palabras de nada: la busqueda se queda sin los dos terminos que importaban
    y la consulta acaba en NO ENCONTRADO por un guion.

    SOLO se une lo que tiene la firma exacta de un corte de renglon: minuscula,
    guion, salto, minuscula. Un guion seguido de mayuscula o de digito -«Real
    Decreto 1624/1992 -\\n1992»- se deja como esta, y un guion con espacios
    alrededor tambien: ahi el guion es del texto, no del renglon.
    """
    return _RE_CORTE_PDF.sub(r"\1\2", texto or "")


def palabras_exactas(texto: str) -> list[str]:
    """Las palabras tal cual, sin lematizar: solo minusculas y sin tildes."""
    salida = []
    for bruto in _RE_PALABRA.findall(sin_tildes(texto)):
        palabra = bruto.rstrip("ºª")
        if palabra and palabra not in PALABRAS_VACIAS and (
            len(palabra) > 1 or palabra.isdigit()
        ):
            salida.append(palabra)
    return salida


def tokenizar(texto: str, quitar_vacias: bool = True) -> list[str]:
    """Texto -> lista de raices, sin tildes, sin mayusculas, sin palabras vacias."""
    plano = sin_tildes(texto)
    salida = []
    for bruto in _RE_PALABRA.findall(plano):
        palabra = bruto.rstrip("ºª")
        if not palabra:
            continue
        if quitar_vacias and palabra in PALABRAS_VACIAS:
            continue
        if len(palabra) == 1 and not palabra.isdigit():
            continue
        salida.append(lematizar(palabra))
    return salida
