"""EL «NO ENCONTRADO» DEJA DE SER UN CALLEJON: SE ORIENTA, NO SE CONTESTA.

Cuando la busqueda recupera preceptos pero el mejor no cubre bastante de lo que
se pregunta, hasta ahora se tiraban los preceptos y se decia que no hay nada.
Estaban ahi, se habian recuperado, y no se enseñaban.

QUE SE HACE AHORA, en UNA llamada de redaccion, y tres cosas:

  1. QUE SI SE HA ENCONTRADO Y POR QUE NO BASTA. «He encontrado el articulo X,
     que regula esto en general, pero tu caso depende de Y y eso no esta en lo
     que tengo». Con sus citas, porque es texto recuperado como cualquier otro.

  2. ORIENTAR SOBRE DONDE VIVE LA RESPUESTA, NO CUAL ES. «Esto parece de
     Sucesiones y de Transmisiones a la vez», «depende de la residencia del
     causante», «lo regula el reglamento de facturacion, que no esta aqui».

  3. PEDIR EL DATO QUE FALTA. «Si me dices si el vehiculo esta a nombre de la
     empresa o del socio, puedo acotar». Enlaza con la caja de continuacion.

----------------------------------------------------------------------------
Y AQUI ESTA TODO EL RIESGO, ASI QUE SE DICE ENTERO
----------------------------------------------------------------------------
Este es EL SITIO DEL SISTEMA DONDE EL MODELO TIENE MAS TENTACION DE RELLENAR,
porque se le esta pidiendo que hable justo cuando no tiene material. Un modelo
de lenguaje sabe de memoria que la reduccion de empresa familiar ronda el 95% y
que el plazo de Sucesiones son seis meses. Nada de eso puede salir de aqui.

    ORIENTAR ES DECIR DONDE BUSCAR. CONTESTAR ES DECIR QUE DICE LA LEY.

    «depende de la residencia del causante»          -> orientacion
    «en Cataluña la reduccion es del 95%»            -> DERECHO SIN CITA
    «el plazo es de seis meses»                      -> DERECHO SIN CITA
    «lo regula el articulo 20 de la Ley 29/1987»     -> DERECHO SIN CITA

Las tres ultimas son verdad, probablemente. Y da igual: si sale de la memoria
del modelo y no del texto recuperado, este sistema no lo dice. Esa es su unica
razon de ser.

TRES CANDADOS, Y NINGUNO SE FIA DEL DE AL LADO
----------------------------------------------------------------------------
  1. EL PROMPT, con todas las letras. Necesario y NO suficiente: un prompt es
     una peticion, no una garantia.

  2. EL VERIFICADOR ENTERO, el de siempre. Cualquier fragmento entrecomillado
     tiene que estar LETRA POR LETRA en el material. Si el modelo se inventa
     una cita, se cae la orientacion entera, como se cae una respuesta.

  3. `derecho_sin_cita`, QUE ES NUEVO Y ESTA AQUI. El verificador comprueba lo
     que se cita; NO comprueba lo que se afirma sin citar nada. «En Cataluña la
     reduccion es del 95%» no lleva comillas ni referencia, asi que para el
     verificador no existe. Para este guardian si.

El tercero existe porque el segundo tiene ese hueco, y en el camino normal ese
hueco no importa -alli el redactor tiene material y no necesita inventar- pero
aqui es justo donde va a apretar.

SI NO PASA, NO SALE. Se vuelve al NO ENCONTRADO de toda la vida, con los
preceptos en crudo. Ante la duda, nada.
"""
from __future__ import annotations

import re
import unicodedata

from . import citas as C

# ---------------------------------------------------------------- el prompt

# Se añade AL FINAL del sistema de siempre, como `PARA_EL_CLIENTE`: las reglas
# de citacion no se relajan por ser una orientacion. Lo que cambia es EL
# TRABAJO, y eso hay que decirlo entero porque es lo contrario de lo que el
# modelo espera que se le pida.
ORIENTAR = """

--- ESTA VEZ NO HAY MATERIAL PARA CONTESTAR ---

La busqueda ha recuperado los preceptos de abajo, pero NINGUNO resuelve lo que
se pregunta. Tu trabajo AHORA NO ES CONTESTAR LA PREGUNTA. Es orientar.

ESCRIBE TRES COSAS, EN ESTE ORDEN:

1. QUE SE HA ENCONTRADO Y POR QUE NO BASTA.
   LOS DOS PRECEPTOS MAS CERCANOS A LO QUE SE PREGUNTA, NO TODOS. Citalos como
   siempre -fragmento literal entrecomillado, articulo y norma- y di por que no
   resuelven este caso. Los demas, si acaso, en una linea y sin citarlos.

   Explicar cinco preceptos que no valen es un recorrido por lo que no sirve, y
   lo que hace falta esta en los puntos 2 y 3. Si ninguno de los recuperados se
   acerca, dilo en una frase y pasa al 2.

2. DONDE VIVE LA RESPUESTA, SIN DECIR CUAL ES.
   De que impuesto o de que norma parece ser la pregunta; de que dato depende;
   si hay que mirar normativa autonomica; si lo regula un reglamento que no
   esta aqui. Nombrar una norma que no tienes esta BIEN: «lo regula el
   reglamento de facturacion, que no esta en lo que tengo».

3. QUE DATO FALTA PARA ACOTAR.
   Una o dos preguntas concretas cuya respuesta cambiaria donde hay que buscar.
   Terminalo invitando a añadirlo, que hay una caja debajo para eso.

LA LINEA QUE NO SE CRUZA, Y ES TODA LA REGLA DE ESTE ENCARGO:

    SE ORIENTA SOBRE DONDE BUSCAR. NO SE CONTESTA LA PREGUNTA.

Prohibido, aunque lo sepas y aunque sea verdad:

  · un porcentaje, un tipo de gravamen o una cuantia;
  · un plazo, un numero de dias, meses o años;
  · un numero de articulo que no venga del material de abajo;
  · cualquier frase que diga QUE DICE la ley sin un fragmento literal del
    material detras.

    «depende de donde tuviera la residencia el causante»   -> SI
    «en Cataluña la reduccion es del 95 por ciento»        -> NO
    «el plazo para presentarlo son seis meses»             -> NO
    «lo regula el articulo 20 de la Ley 29/1987»           -> NO
    «esto lo regula la normativa de Sucesiones, que aqui
     no esta cargada»                                      -> SI

Lo que escribas se comprueba entero, igual que una respuesta. Una orientacion
con una cifra puesta de memoria no se enseña: se tira y quien pregunta se queda
sin nada. Mas vale corta y util que larga y con una cifra inventada.

Y CORTA DE VERDAD: el trabajo esta en el 2 y en el 3. El 1 es para que se vea
que se ha mirado, no para repasar el corpus.
"""

# ------------------------------------------------------- el tercer candado

# QUE SE PERSIGUE. Cifras y plazos son lo que un modelo suelta de memoria sin
# darse cuenta, y son justo lo que un gestor copiaria en un correo.
#
# NO SE PERSIGUEN LOS AÑOS: «el ejercicio 2023» o «la reforma de 2021» son
# contexto, no derecho, y aparecen en cualquier orientacion honrada.
_RE_PORCENTAJE = re.compile(
    r"\b\d{1,3}(?:[.,]\d+)?\s*(?:%|por\s*ciento|por\s*100)", re.I)
_RE_PLAZO = re.compile(
    r"\b(?:\d{1,4}|un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|"
    r"once|doce|quince|veinte|treinta)\s+"
    r"(?:dias?|meses?|años?|anos?|semanas?|trimestres?)\b", re.I)
_RE_DINERO = re.compile(
    r"\b\d[\d.,]*\s*(?:€|euros?)\b", re.I)
# «articulo 95», «artículo 95», «art. 95», «arts. 20 y 21». El numero es lo que
# importa: «el articulo aplicable» sin numero no afirma nada.
#
# CON TILDE Y SIN ELLA. La primera version solo llevaba «iculo», asi que
# «artículo 99» -que es como lo escribe el modelo, en castellano correcto- se le
# escapaba entero. Solo lo cazaba el rechazo por referencias sueltas, y eso solo
# funciona cuando el numero va con el nombre de la norma al lado: «mira el
# artículo 99» a secas no es una referencia suelta y habria pasado.
_RE_ARTICULO = re.compile(
    r"\b(?:art(?:s?\.|[ií]culos?)?)\s*\d+", re.I)

_MOTIVOS = (
    (_RE_PORCENTAJE, "un porcentaje"),
    (_RE_PLAZO, "un plazo"),
    (_RE_DINERO, "una cuantia"),
    (_RE_ARTICULO, "un numero de articulo"),
)

# Lo que va entre comillas es TEXTO RECUPERADO, y el verificador ya lo ha
# comprobado letra por letra. Un 95% que salga de dentro de un fragmento
# literal es la ley hablando, no el modelo.
_RE_ENTRECOMILLADO = re.compile(r"[«\"“]([^»\"”]*)[»\"”]")
# Y lo que va en el parentesis de una cita es la REFERENCIA de ese fragmento:
# «...» (articulo 95 de la Ley 37/1992, https://...). Ese «articulo 95» no es
# una afirmacion suelta: es de donde sale lo entrecomillado.
_RE_PARENTESIS = re.compile(r"\(([^()]*)\)")
# NI EL PARENTESIS QUE LA CIERRA NI LA COMA QUE LA SIGUE. Con `\S+` la URL se
# tragaba el «)» final, el parentesis se quedaba sin cerrar, dejaba de tapar y
# el «articulo 95» de la propia referencia salia denunciado como derecho sin
# cita. Es la misma clase de caracteres que ya usa `interfaz.RE_ENLACE`.
_RE_URL = re.compile(r"https?://[^\s)\]}>,;]+")


def _tapar(texto: str) -> str:
    """Deja el texto con lo comprobado tapado, para mirar SOLO lo demas.

    Se sustituye por espacios y no se borra: asi las posiciones no se mueven.

    QUE SE TAPA, Y QUIEN LO DECIDE. Lo entrecomillado y su referencia son texto
    recuperado que el verificador ya ha comprobado letra por letra: un 95% que
    salga de ahi dentro es la ley hablando, no el modelo.

    Y LA REFERENCIA LA SEÑALA `citas`, NO UNA REGLA ESCRITA AQUI. Hay DOS
    formas validas de citar y las dos se usan:

        «fragmento» (articulo 95 de la Ley 37/1992, https://...)
        El articulo 95 de la Ley 37/1992 dispone que «fragmento»

    La primera version de esto solo tapaba parentesis, asi que en la segunda
    forma el «articulo 95» quedaba a la vista y salia denunciado como un numero
    de articulo dicho de memoria. Escribir aqui la segunda regla habria sido la
    tercera copia de algo que ya sabe `citas.extraer`: se le pregunta a el.
    """
    def blanco(m):
        return " " * len(m.group(0))

    t = _RE_ENTRECOMILLADO.sub(blanco, texto or "")
    t = _RE_PARENTESIS.sub(blanco, t)
    t = _RE_URL.sub(blanco, t)

    # Y las referencias que `citas` ha reconocido como parte de una cita de
    # verdad, esten donde esten.
    try:
        lista, _sueltas = C.extraer(texto or "")
    except Exception:                            # noqa: BLE001
        return t
    for cita in lista:
        ref = getattr(cita, "referencia", None)
        bruto = getattr(ref, "bruto", "") if ref else ""
        contexto = getattr(cita, "contexto", "") or ""
        if not bruto:
            continue
        # Se tapa DENTRO DEL CONTEXTO de esa cita, no en todo el texto: un
        # «articulo 20» dicho de memoria tres parrafos mas abajo no queda
        # amnistiado porque exista una cita legitima al articulo 20 arriba.
        i = t.find(contexto) if contexto else -1
        trozo = contexto if i >= 0 else ""
        if not trozo:
            continue
        j = trozo.find(bruto)
        if j >= 0:
            t = t[:i + j] + " " * len(bruto) + t[i + j + len(bruto):]
    return t


def derecho_sin_cita(texto: str) -> list[tuple[str, str]]:
    """Lo que afirma derecho sin apoyarse en el material. Vacio = limpio.

    Devuelve [(que es, el trozo)] para poder decirlo en la traza. Se mira SOLO
    fuera de los fragmentos literales y de las referencias: dentro de esos, el
    verificador ya ha hecho su trabajo y lo que hay es la ley, no el modelo.
    """
    fuera = _tapar(texto or "")
    hallazgos: list[tuple[str, str]] = []
    for patron, que in _MOTIVOS:
        for m in patron.finditer(fuera):
            hallazgos.append((que, m.group(0).strip()))
    return hallazgos


def _sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower())
                   if unicodedata.category(c) != "Mn")


def motivo_de(hallazgos) -> str:
    """Una frase para la traza. Nunca va a pantalla: a pantalla va el NO
    ENCONTRADO de siempre, que ya explica lo que hay."""
    if not hallazgos:
        return ""
    partes = ", ".join(f"{q} («{t}»)" for q, t in hallazgos[:4])
    return (f"la orientacion afirma derecho sin cita: {partes}"
            + (f" y {len(hallazgos) - 4} mas" if len(hallazgos) > 4 else ""))
