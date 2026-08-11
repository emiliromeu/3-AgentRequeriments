"""LLAMADA 1 - Analizar la pregunta. No la responde: la clasifica.

Lo que devuelve el modelo se valida por REGLAS antes de usarse. El esquema
JSON garantiza la forma; las reglas comprueban que los valores tengan sentido.
Si no cuadra, se reintenta UNA vez con los errores concretos. A la segunda, se
para y se dice.

EL EJERCICIO ES EL CAMPO CRITICO, y no se fia del modelo:
un ano solo se acepta si aparece ESCRITO en la pregunta. Si el modelo deduce
"2024" porque hoy es 2024, el ano no estara en el texto y el sistema para y
pregunta. Esto es una comprobacion de codigo, no una instruccion del prompt:
las instrucciones se pueden desobedecer, esta no.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

EJERCICIO_MINIMO = 1993  # la Ley del IVA entra en vigor el 1-1-1993
EJERCICIO_MAXIMO = 2100

# LOS CODIGOS DE IMPUESTO SALEN DEL CORPUS, NO DE UNA LISTA.
#
# Aqui habia un enum escrito a mano -("IVA","IRPF","IS","ITP-AJD","IIEE",...)-
# y el corpus derivaba los suyos del titulo de las normas. Dos fuentes de
# verdad, y se descuadraron en cuanto entro la Ley del Patrimonio: el corpus
# empezo a decir que cubria Patrimonio -la pantalla lo enseñaba- y el
# analizador no tenia codigo para decirlo, asi que toda pregunta de Patrimonio
# salia como «otro» y se rechazaba CON UN MENSAJE QUE ENUMERABA PATRIMONIO
# ENTRE LO QUE SI SE CUBRE. La pantalla se contradecia a si misma.
#
# Es la tercera vez con el mismo patron: las tres copias de la regla del año y
# los dos caminos de la etiqueta del TEAC. Cuando dos sitios tienen que decir
# lo mismo, uno lo dice y el otro lo lee.
#
# Ahora: `codigos(normas)`. Si mañana se ingiere la Ley del Impuesto sobre
# Sucesiones, ISD aparece sin que nadie escriba nada.

# LO QUE NO CUBRIMOS PERO SABEMOS NOMBRAR. Esto NO es una lista de cobertura
# -la cobertura la decide el corpus y solo el corpus-: es vocabulario, para que
# el rechazo pueda decir «la consulta es de ITP-AJD» en vez de «es de otro».
# Un rechazo que nombra el impuesto le dice al gestor que le hemos entendido y
# que no lo tenemos; «otro» le deja pensando que no le hemos entendido.
#
# Si alguno de estos se ingiere algun dia, el corpus manda y deja de estar
# fuera: `codigos` lo quita de aqui. Por eso anadir uno no abre nada.
IMPUESTOS_FUERA = ("ITP-AJD", "ISD", "IIEE", "IBI", "IAE")

SIN_CLASIFICAR = ("otro", "desconocido")


def codigos(normas=None) -> tuple:
    """Los codigos que el analizador puede devolver, para ESTE corpus.

    Los primeros son los que se cubren -salen de los titulos de las normas
    cargadas-; despues los que sabemos nombrar y no tenemos; y al final los dos
    de siempre. Sin `normas` quedan solo estos ultimos, que es lo honrado: sin
    corpus no se cubre nada.
    """
    dentro = sorted(normas.impuestos()) if normas is not None else []
    fuera = [x for x in IMPUESTOS_FUERA if x not in dentro]
    return tuple(dentro) + tuple(fuera) + SIN_CLASIFICAR

# Tope de longitud de las listas. Ya NO va en el esquema (la API no admite
# maxItems); se comprueba en `validar`, con el mismo rechazo y reintento.
MAX_ARTICULOS = 15
MAX_TERMINOS = 12

# Esquema que la API fuerza en la respuesta. Solo estas claves: cualquier cosa
# que el modelo quisiera anadir (por ejemplo, una respuesta a la duda) no cabe.
#
# LO QUE LOS STRUCTURED OUTPUTS **NO** ADMITEN, y por que este esquema esta
# escrito asi (documentacion oficial de structured outputs):
#   - maxItems                -> los topes se comprueban abajo, en codigo
#   - minLength / maxLength   -> idem
#   - minimum / maximum       -> el rango del ejercicio se comprueba en codigo
#   - pattern                 -> el formato de "163 bis" se comprueba en codigo
#   - type: ["integer","null"] -> hay que usar anyOf, que si esta admitido
#   - additionalProperties distinto de false
# Un esquema invalido da 400 y tumba la ejecucion entera; por eso existe
# `fase4.py esquema`, que lo comprueba con UNA llamada.
ESQUEMA = {
    "type": "object",
    "properties": {
        # El enum lo rellena `esquema_de(normas)` con lo que haya en el corpus.
        # Aqui queda la forma, no la lista.
        "impuesto": {"type": "string", "enum": list(codigos())},
        # No se puede escribir ["integer", "null"]: hay que usar anyOf.
        "ejercicio": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        "ejercicio_fundamento": {"type": "string"},
        "articulos_sospechados": {"type": "array", "items": {"type": "string"}},
        "terminos_busqueda": {"type": "array", "items": {"type": "string"}},
        "resumen_duda": {"type": "string"},
    },
    "required": [
        "impuesto",
        "ejercicio",
        "ejercicio_fundamento",
        "articulos_sospechados",
        "terminos_busqueda",
        "resumen_duda",
    ],
    "additionalProperties": False,
}

def esquema_de(normas=None) -> dict:
    """El esquema con los codigos de ESTE corpus dentro.

    Se construye a cada consulta y no se guarda: si se cacheara, ingerir una
    norma nueva no cambiaria el esquema hasta reiniciar, y eso es exactamente
    el descuadre que esto viene a cerrar.
    """
    esquema = json.loads(json.dumps(ESQUEMA))     # copia honda, barata
    esquema["properties"]["impuesto"]["enum"] = list(codigos(normas))
    return esquema


SISTEMA = """\
Eres el clasificador de un sistema de consulta fiscal de una gestoria espanola.

TU UNICA TAREA es clasificar la pregunta que te den. NO la respondas. No des
tu opinion juridica, no cites normas de memoria, no adelantes conclusiones.
Lo que escribas fuera de los campos del JSON se descarta.

Devuelve estos campos:

- impuesto: de que impuesto trata. Si no encaja en ninguno, "desconocido".

- ejercicio: el ANO del caso, solo si la pregunta lo dice. Si no lo dice, pon
  null. NUNCA supongas el ano en curso ni ninguno otro: un caso de 2023
  contestado con la ley de hoy parece impecable y esta mal, y nadie lo nota.
  Solo pon un numero si ese ano esta escrito en la pregunta.

- ejercicio_fundamento: de donde sale el ano, citando el trozo de la pregunta
  donde aparece; o por que no se puede saber.

- articulos_sospechados: numeros de articulo que podrian aplicar ("95",
  "163 bis"). Solo si tienes motivo. Lista vacia si no lo tienes: es una pista
  para el buscador, no una cita, y una pista falsa hace perder tiempo.

- terminos_busqueda: LO MAS IMPORTANTE. Son el puente entre como habla el
  cliente y como habla la ley. Quien pregunta dice "coche"; la ley dice
  "vehiculo automovil de turismo". Quien pregunta dice "facturas de comidas";
  la ley dice "servicios de hosteleria". Propon los terminos DEL ARTICULADO,
  no los de la pregunta. Entre 3 y 8, en singular y sin articulos.

- resumen_duda: una frase con lo que se pregunta. Sin responderla.
"""


@dataclass
class Analisis:
    impuesto: str = "desconocido"
    ejercicio: int | None = None
    ejercicio_fundamento: str = ""
    articulos_sospechados: list = field(default_factory=list)
    terminos_busqueda: list = field(default_factory=list)
    resumen_duda: str = ""
    crudo: dict = field(default_factory=dict)


_RE_NUM_ART = re.compile(r"^\d{1,3}(\s+[a-zA-Zaeiouáéíóú]+){0,2}$")


def validar(datos, normas=None) -> tuple[Analisis | None, list[str]]:
    """Comprueba el JSON del analizador. Devuelve (analisis, errores).

    `normas` es el registro del corpus: de ahi salen los codigos de impuesto
    admitidos. Sin el se admiten solo los que no dependen del corpus, que es
    lo que hace que un descuido -llamar sin pasarlo- se note en seguida en
    vez de colar cualquier cosa.
    """
    errores: list[str] = []
    if not isinstance(datos, dict):
        return None, ["la respuesta no es un objeto JSON"]

    faltan = [c for c in ESQUEMA["required"] if c not in datos]
    if faltan:
        errores.append(f"faltan campos obligatorios: {', '.join(faltan)}")
    sobran = [c for c in datos if c not in ESQUEMA["properties"]]
    if sobran:
        # Campos de mas suelen ser el modelo intentando responder.
        errores.append(f"campos no permitidos: {', '.join(sobran)}")
    if errores:
        return None, errores

    impuesto = datos["impuesto"]
    admitidos = codigos(normas)
    if impuesto not in admitidos:
        errores.append(f"impuesto {impuesto!r} no esta en {admitidos}")

    ejercicio = datos["ejercicio"]
    if ejercicio is not None:
        if not isinstance(ejercicio, int) or isinstance(ejercicio, bool):
            errores.append("ejercicio debe ser un entero o null")
        elif not (EJERCICIO_MINIMO <= ejercicio <= EJERCICIO_MAXIMO):
            errores.append(
                f"ejercicio {ejercicio} fuera de rango "
                f"[{EJERCICIO_MINIMO}, {EJERCICIO_MAXIMO}]"
            )

    terminos = datos["terminos_busqueda"]
    if not isinstance(terminos, list) or not terminos:
        errores.append("terminos_busqueda no puede estar vacio")
    else:
        for t in terminos:
            if not isinstance(t, str) or not (2 <= len(t.strip()) <= 60):
                errores.append(f"termino de busqueda invalido: {t!r}")
        if len(terminos) > MAX_TERMINOS:
            errores.append(
                f"{len(terminos)} terminos de busqueda; el maximo es {MAX_TERMINOS}"
            )

    arts = datos["articulos_sospechados"]
    if not isinstance(arts, list):
        errores.append("articulos_sospechados debe ser una lista")
    else:
        if len(arts) > MAX_ARTICULOS:
            errores.append(
                f"{len(arts)} articulos sospechados; el maximo es {MAX_ARTICULOS}"
            )
        for a in arts:
            if not isinstance(a, str) or not _RE_NUM_ART.match(a.strip()):
                errores.append(
                    f"articulo sospechado con formato raro: {a!r} "
                    f"(se espera '95' o '163 bis')"
                )

    resumen = datos["resumen_duda"]
    if not isinstance(resumen, str) or len(resumen) > 400:
        errores.append("resumen_duda ausente o demasiado largo (max 400)")

    if errores:
        return None, errores

    return (
        Analisis(
            impuesto=impuesto,
            ejercicio=ejercicio,
            ejercicio_fundamento=str(datos["ejercicio_fundamento"])[:300],
            articulos_sospechados=[a.strip() for a in arts],
            terminos_busqueda=[t.strip() for t in terminos],
            resumen_duda=resumen.strip(),
        ),
        [],
    )


def annos_escritos(pregunta: str) -> set:
    """Anos que aparecen literalmente en la pregunta."""
    return {
        int(m)
        for m in re.findall(r"\b(\d{4})\b", pregunta)
        if EJERCICIO_MINIMO <= int(m) <= EJERCICIO_MAXIMO
    }


def leer_ejercicio(crudo) -> tuple:
    """Un ejercicio de fuera -> (año, motivo). (None, por que) si no vale.

    Acepta lo que una persona escribe de verdad -«2023», « 2023 », 2023- y
    RECHAZA todo lo demas diciendo por que en cristiano. Nada de adivinar:
    «23» podria ser 1923 o 2023, y «2023-2024» son dos ejercicios distintos con
    dos leyes distintas. Ante la duda se pregunta, no se elige.
    """
    if crudo is None:
        return None, "ni --ejercicio ni la pregunta indican el ejercicio del caso"
    texto = str(crudo).strip()
    if not texto:
        return None, ("el año del caso ha llegado vacio. Escribe los cuatro "
                      "digitos del ejercicio, por ejemplo 2023")
    if not texto.isdigit():
        if re.fullmatch(r"\d{4}\s*[-/aA]\s*\d{4}", texto):
            return None, (
                f"«{texto}» son dos ejercicios y cada uno puede tener su "
                f"redaccion de la ley: consulta uno cada vez")
        return None, (
            f"«{texto}» no es un año. Escribe solo los cuatro digitos del "
            f"ejercicio, por ejemplo 2023")
    if len(texto) != 4:
        return None, (
            f"«{texto}» no son cuatro digitos. Escribe el año entero: 2023, "
            f"no 23")
    año = int(texto)
    if not (EJERCICIO_MINIMO <= año <= EJERCICIO_MAXIMO):
        return None, (
            f"el año {año} esta fuera de lo que cubre esta herramienta "
            f"({EJERCICIO_MINIMO}-{EJERCICIO_MAXIMO})")
    return año, ""


def resolver_ejercicio(
    pregunta: str, analisis: Analisis, ejercicio_cli: int | None
) -> tuple[int | None, str]:
    """Decide el ejercicio del caso. Devuelve (ejercicio, explicacion).

    Orden: manda --ejercicio. Si no lo hay, se acepta el del modelo SOLO si
    ese ano esta escrito en la pregunta. Si no, se devuelve None y el sistema
    para y pregunta.
    """
    if ejercicio_cli is not None:
        # SE VALIDA AQUI, QUE ES POR DONDE PASA TODO EL MUNDO.
        #
        # No se validaba en absoluto: se devolvia lo que llegara. Medido de
        # punta a punta, «abc» salia con CRITERIO CLARO y ejercicio 'abc';
        # «23», «2023-2024» y «ejercicio 2023» tambien. Los que fallaban lo
        # hacian por casualidad -no encontraban versiones- y no por control.
        #
        # UN AÑO MAL INTERPRETADO ES EL FALLO MAS SILENCIOSO DE ESTE SISTEMA:
        # una consulta de 2023 contestada con la ley de hoy sale impecable, con
        # sus citas y sus enlaces, y esta mal. La ventana ya validaba; la
        # terminal y cualquier otro camino, no.
        valido, motivo = leer_ejercicio(ejercicio_cli)
        if valido is None:
            return None, motivo
        return valido, f"indicado a mano: {valido}"

    if analisis.ejercicio is None:
        return None, "ni --ejercicio ni la pregunta indican el ejercicio del caso"

    escritos = annos_escritos(pregunta)
    if analisis.ejercicio in escritos:
        return (
            analisis.ejercicio,
            f"el ano {analisis.ejercicio} aparece escrito en la pregunta "
            f"({analisis.ejercicio_fundamento})",
        )

    # El modelo ha puesto un ano que no esta en la pregunta: se lo ha supuesto.
    return None, (
        f"el analizador propuso el ejercicio {analisis.ejercicio}, pero ese ano "
        f"NO aparece escrito en la pregunta"
        + (f" (los que aparecen son: {sorted(escritos)})" if escritos else "")
        + ". No se supone un ejercicio: hay que indicarlo"
    )


def mensaje_reintento(errores: list[str]) -> str:
    return (
        "Tu respuesta anterior no paso la validacion:\n"
        + "\n".join(f"  - {e}" for e in errores)
        + "\nDevuelve SOLO el JSON corregido, con esos campos y nada mas."
    )
