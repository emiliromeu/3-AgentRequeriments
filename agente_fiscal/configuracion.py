"""EL MODO DEL SISTEMA. Un solo interruptor para cuatro piezas.

----------------------------------------------------------------------------
EL PROBLEMA QUE ESTO RESUELVE
----------------------------------------------------------------------------
Encender las fuentes eran CUATRO cosas que habia que acordarse de hacer a la
vez: `AGENTE_DGT`, `AGENTE_TEAC`, `AGENTE_DGT_TEXTOS` y cambiar `GUIA.md` a
mano. Cuatro cosas coordinadas por la memoria de una persona es una que se
olvida, y el resultado seria el peor posible: la ventana diciendo que la DGT
esta y la hoja de la mesa diciendo que no. Quien lea la hoja decidira con ella.

Aqui hay UN modo, y de el salen las cuatro. Ver `configurar.py`.

----------------------------------------------------------------------------
Y DESDE LOS DOS BOTONES, EL MODO YA NO DECIDE CADA CONSULTA
----------------------------------------------------------------------------
El modo decide si el SEGUNDO BOTON EXISTE -esa sigue siendo la decision del
despacho- pero si una consulta concreta lleva criterio lo elige quien pulsa.
Con eso desaparece casi todo el estado oculto: la respuesta sabe con que se
hizo porque se decidio al pulsarla, no en una variable puesta hace semanas.

Lo que queda por cuadrar es menos, pero sigue importando: que la guia de la
mesa describa los botones que hay, y que la terminal sin bandera no haga otra
cosa que la ventana.

----------------------------------------------------------------------------
POR QUE UN FICHERO Y NO SOLO VARIABLES DE ENTORNO
----------------------------------------------------------------------------
Una variable de entorno vive dentro de un proceso: `configurar.py` no puede
dejarla puesta para el doble clic de manana. Asi que el modo se GUARDA, y las
variables siguen valiendo porque son utiles para probar sin tocar el disco.

    ORDEN DE MANDO:  variable de entorno  >  fichero de modo  >  apagado

El entorno manda a proposito: las suites encienden la DGT con `AGENTE_DGT=1`
para una ejecucion concreta y no deben depender de como este configurado el
equipo, ni dejarlo tocado.

----------------------------------------------------------------------------
LA REGLA QUE NO SE NEGOCIA
----------------------------------------------------------------------------
Si las cuatro piezas NO dicen lo mismo, el agente NO abre. Mejor no abrir que
abrir mintiendo: una herramienta que dice tener criterio administrativo cuando
no lo tiene manda a un profesional a firmar sin mirar.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FICHERO = RAIZ / "modo.json"

GUIA = RAIZ / "GUIA.md"
DIR_GUIAS = RAIZ / "guias"

SOLO_LEY = "solo-ley"
CON_CRITERIO = "con-criterio"
MODOS = (SOLO_LEY, CON_CRITERIO)

# Las variables de siempre. No se tocan: siguen mandando sobre el fichero.
VAR_DGT = "AGENTE_DGT"
VAR_TEAC = "AGENTE_TEAC"
VAR_TEXTOS = "AGENTE_DGT_TEXTOS"

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


def modo_guardado() -> str:
    """El modo que hay escrito en disco. `solo-ley` si no hay nada."""
    if not FICHERO.is_file():
        return SOLO_LEY
    try:
        d = json.loads(FICHERO.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return SOLO_LEY
    modo = d.get("modo")
    return modo if modo in MODOS else SOLO_LEY


def guardar_modo(modo: str) -> None:
    from datetime import datetime, timezone

    if modo not in MODOS:
        raise ValueError(f"modo desconocido: {modo!r}")
    FICHERO.write_text(json.dumps({
        "modo": modo,
        "cuando": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lo_escribe": "configurar.py",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def hay_boton_criterio() -> bool:
    """¿EXISTE el segundo boton en la ventana?

    Esta es la decision del despacho, y sigue siendo suya: con `--solo-ley` el
    departamento no puede gastar de mas ni ver criterio administrativo aunque
    quiera. Lo que YA NO decide este fichero es si una consulta concreta lleva
    criterio: eso lo elige quien pulsa, boton a boton.
    """
    return modo_guardado() == CON_CRITERIO


def con_criterio() -> bool:
    """El valor por defecto cuando nadie dice nada. Entorno, luego fichero.

    Lo usa la TERMINAL sin bandera. La ventana no pasa por aqui: cada boton
    pasa su decision explicita, y por eso ya no hay estado oculto que se
    descuadre.
    """
    del_entorno = _encendida(VAR_DGT)
    if del_entorno is not None:
        return del_entorno
    return modo_guardado() == CON_CRITERIO


def textos_con_criterio() -> bool:
    """¿Los textos de la ventana hablan ya de las tres fuentes?"""
    del_entorno = _encendida(VAR_TEXTOS)
    if del_entorno is not None:
        return del_entorno
    return modo_guardado() == CON_CRITERIO


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

    modo: str = SOLO_LEY
    piezas: dict = field(default_factory=dict)
    descuadres: list = field(default_factory=list)

    @property
    def coherente(self) -> bool:
        return not self.descuadres

    def a_json(self) -> dict:
        return {"modo": self.modo, "piezas": self.piezas,
                "coherente": self.coherente, "descuadres": self.descuadres}


def revisar() -> Revision:
    """Las cuatro piezas, contrastadas contra el modo. Ninguna se supone.

    Se mira lo que CADA una dice de verdad -no lo que deberia decir- y se
    compara. Preguntarle al fichero de modo si el fichero de modo esta bien no
    comprobaria nada.
    """
    from . import dgt as D
    from . import teac as T

    modo = modo_guardado()
    esperado = (modo == CON_CRITERIO)

    r = Revision(modo=modo)
    r.piezas = {
        "boton de criterio": hay_boton_criterio(),
        "textos de la ventana": textos_con_criterio(),
        "GUIA.md": modo_de_la_guia(),
        # Ya NO deciden si una consulta lleva criterio -eso lo elige el boton-
        # pero siguen mandando en la TERMINAL sin bandera. Si alguien las ha
        # dejado puestas, la terminal y la ventana harian cosas distintas y
        # nadie lo notaria.
        "valor por defecto de la terminal": D.activa() or T.activa(),
    }

    for nombre in ("boton de criterio", "textos de la ventana",
                   "valor por defecto de la terminal"):
        if r.piezas[nombre] != esperado:
            r.descuadres.append(
                f"{nombre}: esta {'encendido' if r.piezas[nombre] else 'apagado'} "
                f"y el modo «{modo}» pide que este "
                f"{'encendido' if esperado else 'apagado'}")
    if r.piezas["GUIA.md"] != modo:
        r.descuadres.append(
            f"GUIA.md: describe «{r.piezas['GUIA.md']}» y el modo es «{modo}». "
            f"La hoja que hay en la mesa no dice lo que hace la herramienta")
    return r


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
            "La herramienta esta a medio configurar y NO se abre.",
            "",
            f"El modo guardado es «{self.revision.modo}», pero no todo lo "
            f"acompana:",
            "",
        ]
        lineas += [f"  · {d}" for d in self.revision.descuadres]
        lineas += [
            "",
            "Se arregla con UNA orden, que deja las cuatro piezas a la vez:",
            "",
            f"    python configurar.py --{self.revision.modo}",
            "",
            "No se abre a medias a proposito: si la ventana dijera que hay",
            "criterio de la DGT y la hoja de la mesa dijera que no, alguien",
            "decidiria con la que tuviera delante.",
        ]
        return lineas
