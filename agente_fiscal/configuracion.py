"""QUE LA HOJA DE LA MESA DIGA LO MISMO QUE LA VENTANA.

----------------------------------------------------------------------------
ESTO ERA UN INTERRUPTOR, Y HA DEJADO DE SERLO
----------------------------------------------------------------------------
Encender las fuentes eran CUATRO cosas coordinadas por la memoria de alguien:
`AGENTE_DGT`, `AGENTE_TEAC`, `AGENTE_DGT_TEXTOS` y cambiar `GUIA.md` a mano. Se
juntaron aqui en un modo unico, guardado en disco, para que no pudieran
descuadrarse.

DESDE QUE LOS DOS BOTONES ESTAN SIEMPRE EN LA VENTANA no queda nada que
encender. Si una consulta lleva criterio lo decide QUIEN PULSA, y la respuesta
dice con cual se hizo porque lo sabe de primera mano. El modo guardado se ha
quitado en vez de dejarlo ahi sin efecto: un interruptor que ya no interrumpe
nada es peor que no tenerlo, porque el siguiente que lo lea creera que manda.

----------------------------------------------------------------------------
LO QUE SI PUEDE SEGUIR MINTIENDO: EL PAPEL
----------------------------------------------------------------------------
`GUIA.md` se imprime y se queda en la mesa. El codigo cambia y el papel no se
entera. Asi que lo unico que se comprueba aqui -y se comprueba al ARRANCAR- es
que TODAS las frases que pueden salir en pantalla estan dentro de la guia.

    ORDEN DE MANDO de las fuentes:  variable de entorno  >  apagado

El entorno manda a proposito: las suites encienden la DGT con `AGENTE_DGT=1`
para una ejecucion concreta y no deben depender de como este el equipo. La
VENTANA no pasa por ahi: cada boton dice explicitamente lo que quiere.

----------------------------------------------------------------------------
LA REGLA QUE NO SE NEGOCIA
----------------------------------------------------------------------------
Si la guia y la ventana NO dicen lo mismo, el agente NO abre. Mejor no abrir
que abrir mintiendo: una herramienta que dice tener criterio administrativo
cuando no lo tiene manda a un profesional a firmar sin mirar.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

GUIA = RAIZ / "GUIA.md"
DIR_GUIAS = RAIZ / "guias"

# UNA SOLA GUIA. Hubo dos -una por modo- mientras el modo era global. Desde
# que los dos botones estan siempre en la ventana, la guia tiene que describir
# los dos SIEMPRE, asi que solo hay una y no hay nada que elegir.
UNICO = "dos-botones"
MODOS = (UNICO,)

# Las variables de siempre. Siguen valiendo para probar sin tocar disco.
VAR_DGT = "AGENTE_DGT"
VAR_TEAC = "AGENTE_TEAC"

# La marca que lleva dentro cada guia para saber cual es. Va en el propio
# fichero y no en un registro aparte: un registro se puede quedar viejo, y la
# marca viaja con el texto que describe.
MARCA = "<!-- MODO: {modo} -->"

APAGADO = ("", "0", "no", "off")


def _encendida(variable: str) -> bool | None:
    """Que dice el ENTORNO de este interruptor. None = no dice nada."""
    valor = os.environ.get(variable)
    if valor is None:
        return None
    return valor.strip() not in APAGADO


def con_criterio() -> bool:
    """El valor por defecto cuando NADIE dice nada. Solo el entorno.

    Lo usa la TERMINAL sin bandera, y por defecto es que no: lo barato y lo
    que no toca la red. La VENTANA no pasa por aqui -cada boton pasa su
    decision explicita- y por eso ya no hay estado oculto que se descuadre.
    """
    del_entorno = _encendida(VAR_DGT)
    return bool(del_entorno) if del_entorno is not None else False


def modo_de_la_guia() -> str:
    """Que modo describe el GUIA.md que hay ahora mismo en disco.

    Se lee la MARCA que lleva dentro. Si no la lleva -porque alguien la ha
    editado a mano y se la ha cargado- se dice que no se sabe, y eso ya es
    motivo para no abrir: una guia sin marca es una guia que nadie sabe si
    dice la verdad.
    """
    if not GUIA.is_file():
        return "(no hay GUIA.md)"
    texto = GUIA.read_text(encoding="utf-8", errors="replace")
    for modo in MODOS:
        if MARCA.format(modo=modo) in texto:
            return modo
    return "(sin marca)"


# --------------------------------------------------------------- coherencia


@dataclass
class Revision:
    """Que dice cada pieza, y si todas dicen lo mismo."""

    modo: str = UNICO
    piezas: dict = field(default_factory=dict)
    descuadres: list = field(default_factory=list)

    @property
    def coherente(self) -> bool:
        return not self.descuadres

    def a_json(self) -> dict:
        return {"modo": self.modo, "piezas": self.piezas,
                "coherente": self.coherente, "descuadres": self.descuadres}


MARCA_COBERTURA = ("<!-- COBERTURA -->", "<!-- /COBERTURA -->")


def bloque_de_cobertura(texto: str) -> str:
    """Lo que hay hoy entre las dos marcas de la guia. Vacio si no estan."""
    abre, cierra = MARCA_COBERTURA
    i, j = texto.find(abre), texto.find(cierra)
    if i < 0 or j < 0 or j < i:
        return ""
    return texto[i + len(abre):j].strip()


def texto_de_cobertura(ix) -> str:
    """DE QUE impuestos hay criterio. SIN CIFRAS, y eso es la correccion.

    La primera version ponia aqui la tabla con los numeros: 653 de IVA, 525 de
    Renta... Y la guia es una HOJA IMPRESA que esta en la mesa. Un numero que
    crece solo -la siembra baja documentos cada pocos minutos- convierte esa
    hoja en algo condenado a mentir, y a la comprobacion en una alarma que
    salta cada pocas horas por algo que no es un fallo.

    LO QUE SE IMPRIME TIENE QUE SER LO QUE NO CAMBIA SOLO. De que impuestos
    hay criterio cambia cuando se siembra un impuesto nuevo, o sea casi nunca
    y por una decision. Cuantos documentos hay cambia mientras se lee la hoja.

    Las cifras exactas viven en «Qué hay dentro», que se cuenta al abrir y por
    definicion esta al dia.
    """
    from agente_fiscal import cobertura as C
    nombres = [nombre for nombre, _total in C.por_impuesto(ix)]
    if not nombres:
        return ("Ahora mismo **no hay criterio guardado** de ningún impuesto. "
                "El segundo botón responderá con la ley igual que el primero.")
    return ("Hay criterio guardado de: **" + "**, **".join(nombres) + "**.\n\n"
            "*Cuántos documentos hay de cada uno lo dice la propia "
            "herramienta, en «Qué hay dentro»: ahí se cuenta al abrir y "
            "siempre está al día. Aquí no, porque esta hoja se imprime y la "
            "copia crece sola.*")


def revisar(ix=None) -> Revision:
    """¿Dice la hoja de la mesa lo mismo que la ventana?

    Se comprueba lo unico que queda que pueda mentir: que TODAS las frases que
    pueden salir en pantalla esten dentro de GUIA.md. Antes esto lo hacia una
    suite aparte que se perdio -`prueba_textos_guia`-; ahora vive aqui, y se
    ejecuta AL ARRANCAR, que es cuando sirve.
    """
    r = Revision(modo=UNICO)
    r.piezas = {"GUIA.md": modo_de_la_guia()}

    if r.piezas["GUIA.md"] != UNICO:
        r.descuadres.append(
            f"GUIA.md dice «{r.piezas['GUIA.md']}» y deberia ser la guia de los "
            f"dos botones. La hoja que hay en la mesa no describe la "
            f"herramienta")
        return r

    guia = _plano(GUIA.read_text(encoding="utf-8", errors="replace"))
    try:
        import interfaz
        frases = interfaz.TEXTOS_DE_ESTADO
    except Exception:  # noqa: BLE001 - sin tkinter no se puede comprobar
        return r

    r.piezas["frases de estado en la guia"] = f"{len(frases)} comprobadas"
    for frase in frases:
        if _plano(frase) not in guia:
            r.descuadres.append(
                f"una frase que sale en pantalla NO esta en GUIA.md: "
                f"«{frase[:56]}...». Quien lea la hoja leera otra cosa que "
                f"quien mire la ventana")

    return r


def desfase_de_la_guia(ix) -> str:
    """¿Se ha quedado vieja la hoja? Devuelve el aviso, o cadena vacia.

    NO ESTA EN `revisar` Y NO BLOQUEA, y esa es la diferencia que importa.

    `revisar` compara PROMESAS: las frases de los tres estados, lo que el
    sistema dice que hace y lo que dice que no hace. Si eso diverge, quien lea
    la hoja decidira con una herramienta que no existe, y por eso no se abre.

    Esto otro compara un DATO QUE CRECE SOLO. Que la hoja se quede vieja no es
    un fallo del sistema ni engaña a nadie sobre lo que hace: solo hay que
    reimprimirla. Impedir abrir por eso seria dejar a la gestoria sin
    herramienta porque la copia de criterio ha mejorado, que es absurdo.

    Aun asi se avisa, porque una hoja vieja en la mesa acaba usandose.
    """
    if ix is None:
        return ""
    hay = _plano(bloque_de_cobertura(
        GUIA.read_text(encoding="utf-8", errors="replace")))
    if not hay:
        return ("La guía impresa no dice de qué impuestos hay criterio. "
                "Se arregla con «python configurar.py --regenerar-guia».")
    if hay != _plano(texto_de_cobertura(ix)):
        return ("La guía impresa se ha quedado vieja: ya hay criterio de más "
                "impuestos de los que dice. La herramienta funciona igual; "
                "para reimprimirla, «python configurar.py --regenerar-guia».")
    return ""


def _plano(texto: str) -> str:
    """Sin tildes ni espacios de mas, SOLO para comparar frases.

    La ventana va en ASCII porque la consola de Windows no siempre sabe pintar
    tildes, y GUIA.md se imprime y las lleva. Lo que tiene que coincidir son
    las PALABRAS.
    """
    import re
    import unicodedata

    d = unicodedata.normalize("NFD", texto or "")
    plano = "".join(c for c in d if unicodedata.category(c) != "Mn").lower()
    plano = plano.replace("«", '"').replace("»", '"').replace("—", "-")
    return re.sub(r"\s+", " ", plano).strip()


def exigir_coherencia() -> None:
    """Se llama al arrancar. Si algo no cuadra, NO se sigue.

    Lanza `Descoordinado`, que quien arranca traduce a una frase. Aqui no se
    imprime nada: este modulo no sabe si le esta hablando a una terminal o a
    una ventana.
    """
    r = revisar()
    if not r.coherente:
        raise Descoordinado(r)


class Descoordinado(Exception):
    """Las piezas no dicen lo mismo. Se para y se dice cual."""

    def __init__(self, revision: Revision):
        self.revision = revision
        super().__init__("; ".join(revision.descuadres))

    def en_cristiano(self) -> list:
        """Las lineas que se le enseñan a una persona."""
        lineas = [
            "La hoja de instrucciones NO dice lo que hace la herramienta,",
            "y por eso no se abre.",
            "",
        ]
        lineas += [f"  · {d}" for d in self.revision.descuadres]
        lineas += [
            "",
            "Lo arregla Emili: la guia se genera desde guias/GUIA.md.",
            "",
            "No se abre a medias a proposito: si la ventana dijera una cosa",
            "y la hoja de la mesa dijera otra, alguien decidiria con la que",
            "tuviera delante.",
        ]
        return lineas
