#!/usr/bin/env python3
"""VENTANA DE ESCRITORIO para el departamento fiscal.

    python interfaz.py                  # contra el modelo real
    python interfaz.py --motor ensayo   # sin gastar una sola llamada

Solo tkinter, que viene con Python: ni pip, ni servidor, ni navegador. Se abre
con doble clic en `abrir_agente.bat` (Windows) o `abrir_agente.command` (Mac).

ESTA VENTANA NO DECIDE NADA. Llama a `fase4.consultar`, que es el mismo camino
que usa la terminal, y ensena lo que devuelve. No interpreta, no reordena, no
suaviza. Si algo hay que cambiar en el criterio, se cambia en el motor y aqui
se ve solo.

Tres reglas que aqui son de vida o muerte, porque esto es lo unico que ve el
profesional que va a firmar el trabajo:

1. NUNCA se ensena texto que no haya pasado el verificador. Ni en gris, ni con
   aviso, ni a titulo orientativo. Si `respuesta` viene vacia, no hay nada que
   ensenar y se dice por que.
2. EL EJERCICIO NO SE RELLENA SOLO. Nunca con el ano en curso. Una consulta de
   2023 contestada con la ley de hoy sale impecable y esta mal, y no lo nota
   nadie. Es el fallo mas silencioso de todo el sistema.
3. NINGUNA TRAZA DE PYTHON en pantalla, y la clave no aparece jamas, ni entera
   ni en trozos. Todo fallo sale en una frase de persona.
"""

from __future__ import annotations

import argparse
import queue
import re
import sys
import threading
import traceback
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

try:
    import tkinter as tk
    from tkinter import font as tkfont
    from tkinter import ttk
except ImportError:  # pragma: no cover - depende de la instalacion de Python
    print(
        "Este Python no trae tkinter, que es lo que dibuja la ventana.\n"
        "En Windows: reinstala Python marcando 'tcl/tk and IDLE'.\n"
        "En Mac: instala Python desde python.org (el del sistema no lo trae).",
        file=sys.stderr,
    )
    raise SystemExit(1)

import fase4
from agente_fiscal import analizador as AN
from agente_fiscal import configuracion as CONF
from agente_fiscal import dgt as DGT
from agente_fiscal import estado as EST
from agente_fiscal import frescura as _FR

# CON CUANTOS DIAS DE MARGEN SE AVISA DE UN CERTIFICADO QUE CADUCA.
#
# Sesenta, y el argumento es de calendario, no de red: quien tiene que
# reaccionar puede estar de vacaciones, de viaje o de baja, y un mes no cubre
# eso. Con dos, el aviso aparece a tiempo de escribir al organismo, esperar
# respuesta y volver a mirar. Y no sale siempre: un certificado normal dura un
# año, asi que esta callado diez meses de cada doce.
DIAS_AVISO_CERTIFICADO = 60

# ----------------------------------------------------------------- textos
#
# El estado lo calcula el codigo por reglas. Aqui solo se traduce a algo que
# entienda quien no ha leido el proyecto. La explicacion del CRITERIO CLARO es
# innegociable y va SIEMPRE: si alguien lee "criterio claro" y entiende
# "Hacienda opina esto", la herramienta hace dano en vez de ayudar.

# LAS FRASES VAN POR PAREJAS: UNA POR BOTON.
#
# Hubo un momento en que esto era una variable global -`AGENTE_DGT_TEXTOS`- que
# decidia si la ventana hablaba de una fuente o de tres. Estaba mal por donde se
# mire: encender el motor y cambiar lo que lee el profesional son decisiones
# distintas, y atarlas a una variable puesta hace semanas era pedir que la
# ventana dijera una cosa y la hoja impresa otra.
#
# Ahora la frase la decide LA CONSULTA: la elige el boton que se pulso, y por
# eso no puede descuadrarse con nada. Lo que sigue haciendo falta es que TODAS
# esten dentro de GUIA.md, y eso se comprueba al arrancar -ver
# `configuracion.revisar()`-: el papel es lo unico que ya no se entera de que el
# codigo ha cambiado.

# ------------------------------------------------------------- los botones
#
# DOS BOTONES, UNO POR MODO, y SE DISTINGUEN POR LO QUE HACEN. Antes el pie
# decia tambien lo que costaba cada uno, y eso hacia justo lo contrario de lo
# que se pretendia: quien dudaba pulsaba el barato aunque necesitara el otro.
# El gasto esta asumido y decidido; ponerlo en pantalla solo sirve para que
# alguien se autolimite en una consulta que si necesitaba el criterio.
#
# EL COSTE SIGUE MEDIDOSE Y REGISTRANDOSE, en la traza y en los informes. Eso
# es para quien lleva la cuenta, no para quien consulta.
#
# El segundo va DEBAJO y no al lado: con los dos en la misma fila se pulsa el
# que queda mas a mano, no el que se queria.
BOTON_LEY = "Consultar la ley"
BOTON_CRITERIO = "Consultar tambien el criterio"

# LO QUE HACE EL BOTON ES FIJO; DE QUE HAY, SE CUENTA.
#
# Aqui ponia «...TODAS DE IVA por ahora». Era verdad el dia que se escribio y
# dejo de serlo en cuanto la siembra metio criterio de Renta, de Sociedades,
# de Patrimonio y de las normas generales. Una frase a mano sobre lo que el
# sistema cubre es una fecha de caducidad sin etiqueta, y es el quinto caso
# del mismo patron. La cobertura la cuenta `cobertura.frase`, de la despensa.
PIE_CRITERIO = ("anade consultas de la DGT y resoluciones del TEAC y de los "
                "tribunales regionales")

# Lo que se dice arriba, junto al estado, y lo que viaja en el texto copiado.
# Si alguien pega la respuesta en sus notas, tiene que saberse con que se hizo.
# Cuando la despensa no tiene nada para esa pregunta. SE LEE COMO LO QUE ES:
# todavia no hay criterio guardado sobre eso. No es una averia ni un fallo del
# que pregunta, y es lo primero que va a pasar cuando alguien pruebe una
# pregunta al azar con 241 consultas guardadas.
# DONDE BUSCAR SI HACE FALTA. Va pegado a todo mensaje de ausencia.
#
# EL PROBLEMA DE FONDO: «no hay criterio sobre esto» y «no hay criterio
# guardado sobre esto» se parecen mucho y dicen cosas opuestas. La primera es
# una afirmacion sobre el mundo que esta herramienta NO puede hacer -tiene una
# copia parcial, hecha a mano, de dos fuentes que publican decenas de miles de
# documentos-. La segunda es una afirmacion sobre nuestro disco, que es lo
# unico que sabemos.
#
# Quien lea la primera y no encuentre nada da el tema por cerrado. Por eso
# ningun mensaje de ausencia se queda sin decir DE DONDE habla y DONDE mirar.
DONDE_BUSCAR = ("Para mirarlo en la fuente: las consultas de la DGT están en "
                "PETETE (petete.tributos.hacienda.gob.es) y la doctrina del "
                "TEAC en DYCTEA.")

AVISO_DESPENSA = ("Esta copia es NUESTRA y es parcial: se va llenando poco a "
                  "poco. Si el segundo botón no encuentra nada sobre tu duda "
                  "no es un fallo, y tampoco significa que no haya criterio: "
                  "significa que aquí todavía no está. " + DONDE_BUSCAR)

# AQUI HABIA UN AVISO QUE DECIA QUE EL CRITERIO ERA «TODO DE IVA».
#
# Se escribio cuando lo era, y aviso bien durante semanas. Dejo de ser cierto
# con la siembra y se quedo en pantalla diciendolo igual, que es peor que no
# decir nada: manda a quien pregunta de Renta a buscar fuera cuando aqui hay
# 525 documentos de Renta.
#
# Lo sustituye `cobertura.frase`, que lo cuenta. Un aviso que se calcula no
# caduca; uno que se escribe, si.

HECHA_CON = {
    False: "Hecha solo con la ley y sus reglamentos. Sin criterio administrativo.",
    True: ("Hecha con la ley, el criterio de la DGT y las resoluciones "
           "economico-administrativas de la copia local."),
}


# LAS DOS FRASES DE «CRITERIO CLARO», UNA POR BOTON.
#
# El estado lo calcula el codigo igual en los dos casos, pero NO significa lo
# mismo: un CRITERIO CLARO hecho solo con la ley dice que la ley y el
# reglamento no se pelean, y nada mas. Decirlo igual que el otro seria dar por
# mirado lo que no se ha mirado.
CLARO_SIN_DGT = (
    "La ley y el reglamento no se contradicen. Esta respuesta se ha hecho SOLO "
    "con la ley: no se ha mirado el criterio de la DGT ni las resoluciones, "
    "que si estan en la herramienta. Para eso esta el otro boton."
)
CLARO_CON_TRES_FUENTES = (
    "La ley y el reglamento no se contradicen, y ni la doctrina del TEAC ni "
    "el criterio de la DGT que hay en la herramienta apuntan a otra cosa. NO "
    "incluye sentencias de los tribunales de justicia, y el criterio puede "
    "cambiar: comprueba las citas antes de decidir."
)
# Y LAS DOS DE «CRITERIO DISCUTIDO». Con la ley sola el desacuerdo solo puede
# venir de la propia norma; con criterio puede venir ademas de dos consultas de
# años distintos o de un tribunal que corrige a la DGT. No es el mismo aviso.
DISCUTIDO_SIN_DGT = (
    "Los textos de la ley y el reglamento apuntan a soluciones distintas. Lee "
    "el desacuerdo de arriba y comprueba las citas antes de decidir: aqui no "
    "hay un criterio unico, y ademas no se ha mirado que opina Hacienda."
)
# LOS DOS «NO ENCONTRADO», Y LA DIFERENCIA IMPORTA MAS DE LO QUE PARECE.
#
# Con el segundo boton, lo primero que le va a pasar a cualquiera que pruebe
# una pregunta al azar es que la copia local no tenga nada de esa materia: son
# 241 consultas, no las 200.000 que hay publicadas. Eso NO es una averia, y si
# se dice con las mismas palabras que un fallo, se lee como un fallo.
NO_ENCONTRADO_TEXTO = (
    "No hay respaldo suficiente. Abajo tienes los articulos encontrados "
    "para mirarlos tu."
)
NO_ENCONTRADO_CON_CRITERIO = (
    "No hay respaldo suficiente en la ley, y en NUESTRA copia de criterio "
    "todavia no hay nada sobre esto. Que no este aqui no quiere decir que no "
    "exista: la copia es parcial y se llena poco a poco. Abajo tienes los "
    "articulos encontrados."
)
DISCUTIDO_CON_EJES = (
    "Hay textos que apuntan a soluciones distintas: criterio de años "
    "distintos sobre el mismo articulo, o un tribunal pronunciandose sobre "
    "criterio que esta respuesta cita. Lee el desacuerdo de arriba y "
    "comprueba las citas antes de decidir: aqui no hay un criterio unico."
)

# EL TEXTO DEL ESTADO DEPENDE DE LA CONSULTA, NO DE UN INTERRUPTOR GLOBAL.
#
# Desde que hay dos botones, «CRITERIO CLARO» no significa lo mismo segun con
# que se haya hecho: uno hecho solo con la ley NO dice nada de lo que opina
# Hacienda, y uno hecho con criterio si. Atarlo a una variable de configuracion
# era justo lo que hacia que la ventana pudiera decir una cosa y la hoja otra.
EXPLICACION_POR_MODO = {
    EST.CLARO: {False: CLARO_SIN_DGT, True: CLARO_CON_TRES_FUENTES},
    EST.DISCUTIDO: {False: DISCUTIDO_SIN_DGT, True: DISCUTIDO_CON_EJES},
    EST.NO_ENCONTRADO: {False: NO_ENCONTRADO_TEXTO,
                        True: NO_ENCONTRADO_CON_CRITERIO},
}


def explicacion(estado: str, con_criterio: bool) -> str:
    """La frase del estado, para ESTA consulta."""
    return EXPLICACION_POR_MODO.get(estado, {}).get(bool(con_criterio), "")


# Todas las frases que pueden salir en pantalla. `configuracion.revisar` exige
# que TODAS esten dentro de GUIA.md: es lo que impide que la ventana y la hoja
# de la mesa digan cosas distintas.
TEXTOS_DE_ESTADO = [CLARO_SIN_DGT, CLARO_CON_TRES_FUENTES,
                    DISCUTIDO_SIN_DGT, DISCUTIDO_CON_EJES,
                    NO_ENCONTRADO_TEXTO, NO_ENCONTRADO_CON_CRITERIO]

# --------------------------------------------------------------- la paleta
#
# MODO OSCURO de la maqueta «Consulta IVA - Direccion visual»: negro y lila.
# Es el que se pidio desde el principio; el «papel claro» fue un desvio.
#
# Se traduce lo que tkinter sabe hacer -color, tipografia, tamaños, espaciado,
# jerarquia- y se deja fuera lo que no (esquinas redondeadas, sombras,
# degradados, transiciones). Ver la lista al final del rediseño.
#
# EL NEGRO NO ES NEGRO. #0F0E13 tiene una gota de violeta: un #000000 puro con
# texto blanco encima vibra y cansa a los diez minutos, y aqui se leen parrafos
# de ley enteros. Las tres superficies se separan por CLARIDAD, no por bordes:
# fondo -> panel -> campo, cada una un escalon mas clara.
#
# LOS NOMBRES SE QUEDAN. `PAPEL2` ya no es papel blanco sino la superficie de
# lectura, que es lo que siempre significo. Renombrarlos obligaria a tocar las
# suites, y lo que las suites protegen -que el fondo NO cambia con el estado-
# no tiene nada que ver con el color que sea.

PAPEL = "#0F0E13"      # fondo de la ventana
PAPEL2 = "#17161D"     # superficie de lectura: paneles y respuesta
ELEVADO = "#1F1D28"    # lo que se rellena: caja de la duda, campo del año
# LOS GRISES ESTAN MEDIDOS, NO ELEGIDOS A OJO. Sobre negro es facil pasarse de
# apagado: el primer TINTA3 daba 3,8:1 contra el panel y el minimo para texto
# menudo es 4,5:1. Se subio hasta 5,2:1. Los numeros de los diez pares estan al
# final del rediseño, en LEEME.
TINTA = "#EDECF2"      # texto principal
TINTA2 = "#A19DB0"     # texto secundario
TINTA3 = "#8B87A0"     # rotulos menudos y pie: 5,2:1, no 3,8:1
FILETE = "#2B2937"     # bordes y separadores
ENLACE = "#C8B0FF"     # el lila claro: sobre negro el oscuro no se lee
LILA = "#C0A5FF"       # el acento: marca, filete y boton principal
LILA_VIVO = "#D6C4FF"  # el mismo, al pasar por encima
LILA_TINTA = "#141019"  # texto sobre el boton lila
SELECCION = "#3A3350"   # el texto seleccionado con el raton

# LOS TRES ESTADOS NO SON UN SEMAFORO, Y ESTO ES LO QUE LO EVITA.
#
# La maqueta lo resuelve con «misma luminosidad, croma decreciente»: los tres
# comparten claridad y solo pierden saturacion. Del lila del criterio claro al
# gris del no encontrado, pasando por un lila apagado. Ni un rojo, ni un ambar,
# ni un verde en toda la pantalla.
#
# Importa porque «NO ENCONTRADO» es una respuesta legitima -a menudo la
# correcta- y pintarla de rojo la convierte en una averia. Quien la vea en gris
# entiende «aqui no hay nada que sostenga esto»; quien la vea en rojo entiende
# «se ha roto» y vuelve a preguntar de otra manera hasta que salga verde.
#
# En oscuro los tres SUBEN de claridad -sobre negro manda el claro, no el
# oscuro- pero la relacion entre ellos es la misma: mismo brillo, croma que
# baja. Comprobado: los tres pasan el filtro de colores de semaforo.
COLOR = {
    EST.CLARO: "#C0A5FF",          # lila, el acento de la casa
    EST.DISCUTIDO: "#A79FC4",      # lila desaturado
    EST.NO_ENCONTRADO: "#9A97A6",  # gris: ni alarma ni error
}
# El filete de 4 px a la izquierda del estado, que es la marca de la maqueta.
FILETE_ESTADO = {
    EST.CLARO: LILA,
    EST.DISCUTIDO: "#7C74A0",
    EST.NO_ENCONTRADO: "#514E5E",
}
# El fondo NO cambia con el estado: es siempre la superficie de lectura. En la
# version anterior cada estado teñia su panel (verde, ambar, rojo) y eso era
# justo el semaforo.
FONDO = {e: PAPEL2 for e in (EST.CLARO, EST.DISCUTIDO, EST.NO_ENCONTRADO)}


# ------------------------------------------------------------- el espacio
#
# ES LO QUE MAS SE NOTA, Y LO PRIMERO QUE SE PIERDE. Una ventana apretada
# parece vieja aunque los colores sean buenos: el ojo lee «formulario de 2003»
# antes de mirar un solo texto.
#
# Una sola escala, y todo sale de ella. Cuando los huecos se eligen uno a uno
# -aqui 6, alla 11, alla 14- no hay ritmo, y la falta de ritmo se ve aunque no
# se sepa nombrar.
AIRE = 8                # la unidad
MARGEN = AIRE * 4       # 32 · alrededor de todo
HUECO = AIRE * 3        # 24 · entre bloques distintos
HUECO2 = AIRE * 2       # 16 · dentro de un bloque
RELLENO = AIRE * 3      # 24 · dentro de las tarjetas

# ANCHO DE LECTURA. Un parrafo de ley a lo ancho de una pantalla de 27 pulgadas
# es ilegible: el ojo pierde el renglon al volver. La tipografia lleva un siglo
# diciendo lo mismo -entre 45 y 90 caracteres por linea- y no cambia porque el
# monitor sea grande.
#
# tkinter NO TIENE max-width. Se resuelve midiendo: al cambiar el tamaño de la
# ventana se calcula cuanto sobra y se convierte en margen interior, de modo
# que la columna de texto se queda quieta y lo que crece son los lados.
# ES UNA HERRAMIENTA DE TRABAJO, NO UNA APP DE MOVIL. Aqui se leen parrafos de
# texto legal denso durante meses seguidos, sentado y a distancia de escritorio.
# Los tamaños de una interfaz «compacta» son exactamente lo contrario de lo que
# hace falta.
COLUMNA_MAXIMA = 74     # caracteres por linea, con el cuerpo grande

# LA COLUMNA LATERAL. Maximizada, la medida de lectura son 876 px de 1.638: el
# 44% del ancho se queda en blanco a los lados mientras el estado, el aporte y
# los avisos se comen 102-355 px de ALTO por encima de la respuesta. Lo que
# sobra a lo ancho paga lo que falta a lo alto.
#
# El suelo no es decorativo: por debajo de `ANCHO_LATERAL` no caben los 876 de
# lectura mas los 400 de la columna, y dos columnas estrechas se leen peor que
# una ancha. Ahi se vuelve a apilar, que es lo que habia.
ANCHO_LATERAL = 1300           # por debajo de esto, apilado
ANCHO_COLUMNA_LATERAL = 400    # lo que se lleva la columna de al lado
ANCHO_BARRA = 20        # lo que ocupa la barra de desplazamiento
MARGEN_LECTURA = 16     # alrededor de la vista de respuesta

# EL INTERLINEADO ES LO QUE MAS SE NOTA EN TEXTO JURIDICO DENSO, mas que el
# cuerpo. Son parrafos largos sin puntos y aparte, y con las lineas juntas el
# ojo pierde el renglon al volver.
#
#   INTERLINEA          entre lineas del MISMO parrafo (spacing2)
#   INTERLINEA_PARRAFO  antes de cada parrafo (spacing1); el doble por detras
INTERLINEA = 7
INTERLINEA_PARRAFO = 9

# A partir de este ancho, el estado y los avisos van en dos columnas. Por
# debajo se apilan: dos columnas en una ventana estrecha son dos columnas
# ilegibles.
ANCHO_DOS_COLUMNAS = 1150

ANCHO_TARJETA = 720     # la tarjeta de la consulta, centrada
ANCHO_DUDA = 52         # caracteres de la caja de la duda

# EL SUELO DE LA RESPUESTA. Por debajo de esto el bloque deja de ser legible,
# asi que la ventana prefiere pedir mas alto antes que dejarlo mas bajo. No es
# el tamaño comodo -eso lo da la pantalla- es el minimo por el que vale la pena
# enseñar algo.
SUELO_RESPUESTA = 200

# NO HAY TOPE AL MARGEN, y es deliberado. El primer intento lo llevaba, y en un
# monitor de 2200px la columna se iba a 1648: el tope se alcanzaba antes que el
# ancho deseado y la linea volvia a cruzar la pantalla. Un tope al margen es un
# tope a lo que se quiere fijar, mirado del reves.


# ------------------------------------------------------------- tipografia
#
# Tres familias con papel distinto, que es lo que hace que una cita se lea como
# cita y no como parrafo. De la maqueta, con sus sustitutos:
#
#   INTERFAZ    Public Sans  ->  Segoe UI (Windows) / Helvetica (Mac)
#   CITA        Newsreader   ->  Georgia
#   REFERENCIA  IBM Plex Mono->  Consolas (Windows) / Menlo (Mac)
#
# Ninguna de las tres primeras esta en un PC de oficina, asi que se comprueba
# EN EJECUCION cual existe y se cae a la siguiente. Lo que no puede pasar es
# acabar en la fuente por defecto de tkinter sin que nadie se entere: por eso
# `fuentes_elegidas` guarda con cual se ha quedado cada una y se puede imprimir.

CADENAS = {
    "interfaz":   ["Public Sans", "Segoe UI", "Inter", "Helvetica Neue",
                   "Helvetica", "Arial", "DejaVu Sans"],
    "cita":       ["Newsreader", "Georgia", "Iowan Old Style", "Palatino",
                   "Times New Roman", "DejaVu Serif"],
    "referencia": ["IBM Plex Mono", "Consolas", "SF Mono", "Menlo",
                   "DejaVu Sans Mono", "Courier New"],
}

fuentes_elegidas: dict = {}


def elegir_fuente(cual: str) -> str:
    """La primera de la cadena que exista de verdad en esta maquina.

    Si no hay ninguna se devuelve "" y tkinter usa la suya; queda anotado en
    `fuentes_elegidas` como «(por defecto)» para que se vea en el arranque.
    """
    disponibles = {f.lower() for f in tkfont.families()}
    for nombre in CADENAS[cual]:
        if nombre.lower() in disponibles:
            fuentes_elegidas[cual] = nombre
            return nombre
    fuentes_elegidas[cual] = "(por defecto)"
    return ""

# Fallos, traducidos. La clave del diccionario es lo que se busca en el mensaje
# tecnico; el valor es lo unico que se ensena.
FALLOS = (
    (("credit balance", "saldo", "billing", "quota", "insufficient"),
     "La cuenta no tiene saldo. Avisa a Emili."),
    (("connection", "conexion", "network", "getaddrinfo", "timeout",
      "temporary failure", "ssl"),
     "No hay conexion a internet."),
    (("credencial", "api key", "api_key", "authentication", "401",
      "unauthorized", "no hay ninguna credencial", "sdk de anthropic"),
     "Falta la configuracion. Avisa a Emili."),
    (("rate limit", "429", "overloaded", "529"),
     "El servicio esta saturado ahora mismo. Prueba dentro de un minuto."),
    # LA RESPUESTA SE CORTO POR LARGA. No es una averia: es que cabia menos de
    # lo que hacia falta, y la unica salida util es preguntar algo mas
    # concreto. Decir «vuelve a intentarlo» aqui manda a repetir lo mismo.
    (("cortada", "max_tokens"),
     "La respuesta se ha cortado por su longitud. Prueba a preguntar una sola "
     "cosa, mas concreta."),
    # 5xx: es fallo del servidor, no de la consulta ni de la conexion. El
    # consejo bueno es esperar, igual que con el 429; sin esto caia en el
    # mensaje generico, que manda a avisar a Emili por algo que se arregla
    # solo en un minuto.
    (("500", "502", "503", "504", "internal server error", "bad gateway"),
     "El servicio ha fallado por su lado. Prueba dentro de un minuto."),
)
FALLO_GENERICO = ("No se ha podido completar la consulta. Vuelve a intentarlo; "
                  "si sigue igual, avisa a Emili.")


def _es_de_credencial(motivo: str) -> bool:
    """¿El arranque ha fallado por la clave? Entonces hay algo que ofrecer.

    Se mira contra los motivos que escribe `modelo.comprobar`, que son los
    unicos que llegan aqui: no hay lista de codigos de error por medio.
    """
    m = (motivo or "").lower()
    return any(x in m for x in ("credencial", "clave", "401", "api la rechaza",
                                "no tiene permiso", "saldo", "credito"))


def en_cristiano(mensaje: str) -> str:
    """Un fallo tecnico -> una frase de persona. Nunca sale otra cosa.

    Se mira el mensaje tecnico SOLO para clasificarlo. Lo que se devuelve es
    siempre una de las frases de arriba: asi ninguna traza, ninguna ruta y
    ningun trozo de clave puede llegar a la pantalla por descuido.
    """
    m = (mensaje or "").lower()
    for senales, frase in FALLOS:
        if any(s in m for s in senales):
            return frase
    return FALLO_GENERICO


# Las diecisiete y las dos ciudades autonomas. Es una lista de nombres para
# escribir mas rapido, NO una lista de cobertura: lo que se cubre lo dice el
# corpus -`normas.comunidades()`- y hoy es solo Cataluña. Se puede escribir
# cualquier otra cosa a mano; el campo no valida nada.
COMUNIDADES = (
    "", "Andalucía", "Aragón", "Asturias", "Baleares", "Canarias", "Cantabria",
    "Castilla-La Mancha", "Castilla y León", "Cataluña", "Ceuta",
    "Comunidad Valenciana", "Extremadura", "Galicia", "La Rioja", "Madrid",
    "Melilla", "Murcia", "Navarra", "País Vasco",
)

RE_ENLACE = re.compile(r"https?://[^\s)\]}>,;]+")


# ------------------------------------------------------------------ ventana


class Ventana:
    def __init__(self, raiz: tk.Tk, motor_nombre: str):
        self.raiz = raiz
        self.motor_nombre = motor_nombre
        self.avisos: "queue.Queue[tuple]" = queue.Queue()
        self.trabajando = False
        self.respuesta_actual = ""
        self.traza_actual = ""
        self.ejercicio_usado = None
        self.con_criterio = False
        self.ix = None
        self.grafo = None
        self.motor = None

        raiz.title("Consulta fiscal — IVA")
        # ABRE SEGUN LA PANTALLA QUE HAY, no segun un numero fijo.
        #
        # Estaba puesto a 1180x880 a pelo. En un portatil de 1280x800 eso es
        # mas alto que la pantalla: el gestor lo recorta por abajo y la
        # respuesta se queda sin sitio, que es exactamente el fallo que hubo
        # que arreglar. Se pide el 88% de lo que haya, con un techo para que en
        # un monitor de 27 pulgadas no abra ocupandolo todo.
        ancho = min(1320, int(raiz.winfo_screenwidth() * 0.86))
        alto = min(1000, int(raiz.winfo_screenheight() * 0.88))
        izq = max(0, (raiz.winfo_screenwidth() - ancho) // 2)
        arr = max(0, (raiz.winfo_screenheight() - alto) // 3)
        raiz.geometry(f"{ancho}x{alto}+{izq}+{arr}")
        # El suelo por debajo del cual la maqueta se rompe. Es un valor de
        # arranque: el definitivo lo pone `_suelo_de_la_ventana` cuando la
        # maqueta ya existe y puede decir lo que mide.
        raiz.minsize(860, 620)
        raiz.configure(bg=PAPEL)

        # La escala de la maqueta, trasladada a puntos. Las proporciones se
        # respetan; los valores absolutos no, porque la maqueta esta dibujada a
        # 2776 px de ancho y esta ventana mide mil y pico.
        f_ui = elegir_fuente("interfaz")
        f_cita = elegir_fuente("cita")
        f_ref = elegir_fuente("referencia")

        # JERARQUIA: SEIS TAMAÑOS, NO DOS.
        #
        # Si el titulo, el estado, la respuesta y las citas pesan igual, no hay
        # diseño: hay una lista de texto. Cada escalon tiene un trabajo, y se
        # nota de un vistazo cual es cada cosa sin leer una palabra.
        #
        #   22  titular      de que va esta ventana
        #   16  estado       la conclusion, lo primero que se busca
        #   15  cita         EL PRODUCTO: en serif, y mas grande que el parrafo
        #   12  respuesta    el cuerpo
        #   11  interfaz     rotulos, botones, campos
        #   10  referencia   la norma y la URL, en monoespaciada
        #    9  rotulo       versalitas de seccion y pie
        self.fuente = tkfont.Font(family=f_ui, size=13)
        self.fuente_menuda = tkfont.Font(family=f_ui, size=11)
        self.fuente_rotulo = tkfont.Font(family=f_ref, size=10)
        self.fuente_seccion = tkfont.Font(family=f_ref, size=10, weight="bold")
        self.fuente_titular = tkfont.Font(family=f_ui, size=24, weight="bold")
        self.fuente_estado = tkfont.Font(family=f_ui, size=19, weight="bold")
        self.fuente_subtitulo = tkfont.Font(family=f_ui, size=15,
                                            weight="bold")
        # LA CITA ES LO MAS GRANDE DE LA PANTALLA DESPUES DEL ESTADO, y en
        # serif. Es la unica forma de que se lea como cita y no como parrafo,
        # que es lo que pide la maqueta y lo unico que hace util esto.
        self.fuente_cita = tkfont.Font(family=f_cita, size=17)
        self.fuente_texto = tkfont.Font(family=f_ui, size=15)
        self.fuente_referencia = tkfont.Font(family=f_ref, size=12)

        # Los que tienen que reajustar su `wraplength` al cambiar el tamaño de
        # la ventana. Ver `_reajustar`.
        self._elasticos: list = []

        self._estilos()
        self._construir()
        self.raiz.bind("<Configure>", self._reajustar)
        raiz.after(80, self._vaciar_avisos)
        # El corpus tarda un segundo en cargar: se hace despues de pintar la
        # ventana para que no parezca que no ha arrancado.
        raiz.after(120, self._arrancar_motor)

    # ------------------------------------------------------------ estilos

    def _estilos(self) -> None:
        """LOS WIDGETS POR DEFECTO DE TKINTER PARECEN DE HACE VEINTE AÑOS.

        Un boton de tkinter trae relieve biselado, fondo del sistema y un borde
        de tres pixeles: da igual lo buena que sea la paleta, si se deja asi la
        ventana se lee como un formulario de 2003.

        Se estila con ttk y se fuerza el tema «clam», que es el UNICO que deja
        cambiar fondo y borde de verdad en los tres sistemas. En Mac el tema
        «aqua» ignora el color de fondo de los botones -los pinta el sistema- y
        en Windows «vista» hace lo mismo: sin cambiar de tema, todo esto no
        haria nada y no se notaria hasta verlo en la otra maquina.

        Lo que NO se puede: esquinas redondeadas, sombras, degradados y
        transiciones. tkinter no las tiene. Ver la lista del final.
        """
        self.estilo = ttk.Style()
        try:
            self.estilo.theme_use("clam")
        except tk.TclError:  # pragma: no cover - tk sin clam, no deberia pasar
            pass
        e = self.estilo

        # EL BOTON PRINCIPAL: lila lleno, sin borde, con aire dentro. El aire
        # de dentro es la mitad del trabajo: un boton apretado parece
        # deshabilitado aunque no lo este.
        e.configure("Primario.TButton", background=LILA, foreground=LILA_TINTA,
                    font=self.fuente, borderwidth=0, focuscolor="",
                    padding=(26, 12), relief="flat", anchor="center")
        e.map("Primario.TButton",
              background=[("disabled", "#26242F"), ("pressed", LILA),
                          ("active", LILA_VIVO)],
              foreground=[("disabled", TINTA3)])

        # EL SEGUNDO BOTON: mismo tamaño, contorno en vez de relleno. La
        # diferencia de peso dice cual es el camino corriente SIN que el otro
        # parezca prohibido: el criterio es util y quien lo necesite tiene que
        # pulsarlo sin sensacion de estar haciendo algo indebido.
        e.configure("Segundo.TButton", background=PAPEL2, foreground=ENLACE,
                    font=self.fuente, borderwidth=1, focuscolor="",
                    padding=(26, 12), relief="flat", bordercolor=FILETE,
                    lightcolor=PAPEL2, darkcolor=PAPEL2)
        e.map("Segundo.TButton",
              background=[("disabled", PAPEL2), ("active", "#221F2E")],
              foreground=[("disabled", "#4E4B5C")],
              bordercolor=[("active", LILA)])

        # Y EL DISCRETO: sin fondo ni borde, para lo que no compite.
        e.configure("Discreto.TButton", background=PAPEL, foreground=TINTA2,
                    font=self.fuente_menuda, borderwidth=0, focuscolor="",
                    padding=(14, 8), relief="flat")
        e.map("Discreto.TButton",
              background=[("active", "#1B1924")],
              foreground=[("active", ENLACE), ("disabled", TINTA3)])

        e.configure("Campo.TEntry", fieldbackground=ELEVADO, foreground=TINTA,
                    bordercolor=FILETE, lightcolor=FILETE, darkcolor=FILETE,
                    insertcolor=LILA, borderwidth=1, padding=(10, 9),
                    relief="flat")
        e.map("Campo.TEntry", bordercolor=[("focus", LILA)],
              lightcolor=[("focus", LILA)], darkcolor=[("focus", LILA)])

        e.configure("Barra.Horizontal.TProgressbar", background=LILA,
                    troughcolor=ELEVADO, bordercolor=ELEVADO,
                    lightcolor=LILA, darkcolor=LILA, borderwidth=0,
                    thickness=4)

        e.configure("Vertical.TScrollbar", background="#2E2B3A",
                    troughcolor=PAPEL2, bordercolor=PAPEL2, arrowcolor=TINTA3,
                    lightcolor="#2E2B3A", darkcolor="#2E2B3A", borderwidth=0,
                    arrowsize=12)
        e.map("Vertical.TScrollbar", background=[("active", "#413D52")])

    def _desplazable(self, padre, fondo=None):
        """Un area que se puede recorrer entera, pase lo que pase dentro.

        Se saco a funcion despues de encontrar el MISMO fallo en tres sitios:
        la columna de resultado, «Qué hay dentro» -que pide 949 px y abria a
        620- y la pantalla de descoordinacion, que en su peor caso -las seis
        frases fuera de la guia- se sale por 123 px.

        Los tres tienen en comun que lo que contienen NO tiene tamaño fijo:
        depende de cuantos avisos haya, de cuantas normas esten cargadas o de
        cuantas frases falten. Un alto fijo para contenido variable es una
        apuesta, y se pierde el dia que hay uno mas.
        """
        fondo = fondo or PAPEL
        caja = tk.Frame(padre, bg=fondo)
        caja.columnconfigure(0, weight=1)
        caja.rowconfigure(0, weight=1)
        lienzo = tk.Canvas(caja, bg=fondo, highlightthickness=0, bd=0)
        lienzo.grid(row=0, column=0, sticky="nsew")
        barra = ttk.Scrollbar(caja, orient="vertical", command=lienzo.yview,
                              style="Vertical.TScrollbar")
        barra.grid(row=0, column=1, sticky="ns", padx=(AIRE, 0))
        def _movida(primero, ultimo, _b=barra):
            """La barra se esconde cuando no hay nada que desplazar.

            Una barra que ocupa sitio y no hace nada es ruido; y una que
            aparece justo cuando hace falta dice, ella sola, que abajo queda
            mas. Estaba en la barra del texto, que ya no existe; su sitio es
            esta, que es la que desplaza.
            """
            _b.set(primero, ultimo)
            if float(primero) <= 0.0 and float(ultimo) >= 1.0:
                _b.grid_remove()
            else:
                _b.grid()
        lienzo.configure(yscrollcommand=_movida)
        self._barra_de = getattr(self, "_barra_de", {})
        self._barra_de[str(lienzo)] = barra
        dentro = tk.Frame(lienzo, bg=fondo)
        item = lienzo.create_window((0, 0), window=dentro, anchor="nw")
        dentro.bind("<Configure>",
                    lambda _e: lienzo.configure(scrollregion=lienzo.bbox("all")))
        lienzo.bind("<Configure>",
                    lambda e: lienzo.itemconfigure(item, width=e.width))
        for evento in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            lienzo.bind(evento, lambda e, c=lienzo: self._rueda_de(e, c))
        return caja, dentro, lienzo

    def _rueda_de(self, evento, lienzo):
        """La misma cuenta de `_rueda`, sobre el lienzo que se le diga."""
        if evento.num == 4:
            pasos = -3
        elif evento.num == 5:
            pasos = 3
        elif sys.platform == "darwin":
            pasos = -evento.delta
        else:
            pasos = -evento.delta // 120 * 3
        lienzo.yview_scroll(int(pasos), "units")
        return "break"

    def _pinchable(self, w) -> None:
        """Cursor de mano en lo que se puede pulsar. Es la señal mas barata que
        existe de «esto responde», y tkinter no la pone sola."""
        w.configure(cursor="hand2")

    # ------------------------------------------------------------ montaje

    def _construir(self) -> None:
        """DOS VISTAS, NO UNA. Es el cambio de fondo de esta version.

        Antes la pregunta y la respuesta compartian pantalla, y se estorbaban:
        el formulario ocupaba 380 px fijos que la respuesta no podia usar, asi
        que en una pantalla normal la respuesta se quedaba en media ventana y
        apretada. No era un problema de espaciado; era que sobraba una de las
        dos cosas en cada momento.

            VISTA DE CONSULTA    la pregunta, el año y los dos botones. Nada
                                 mas, centrado y con aire.
            VISTA DE RESPUESTA   la ventana entera para leer: estado, avisos y
                                 el texto con todo el sitio que hay.

        Las dos viven en la MISMA celda y se turnan con `grid()`/`grid_remove()`.
        Nada se destruye al cambiar: la pregunta escrita sigue donde estaba, que
        es lo que hace que «Nueva consulta» pueda devolverla tal cual para
        cambiarle solo el año.
        """
        self.marco = tk.Frame(self.raiz, bg=PAPEL)
        self.marco.pack(fill="both", expand=True)
        self.marco.columnconfigure(0, weight=1)
        self.marco.rowconfigure(0, weight=1)

        self.vista_consulta = tk.Frame(self.marco, bg=PAPEL,
                                       padx=MARGEN, pady=MARGEN)
        self.vista_consulta.grid(row=0, column=0, sticky="nsew")
        self.vista_respuesta = tk.Frame(self.marco, bg=PAPEL,
                                        padx=MARGEN_LECTURA,
                                        pady=MARGEN_LECTURA)
        self.vista_respuesta.grid(row=0, column=0, sticky="nsew")
        self.vista_respuesta.grid_remove()

        self._construir_consulta(self.vista_consulta)
        self._construir_respuesta(self.vista_respuesta)
        self.caja.focus_set()

    # ------------------------------------------------------- vista 1: pedir

    def _construir_consulta(self, raiz_vista) -> None:
        """LA PANTALLA DE PEDIR. Centrada, y no hay nada mas.

        Se centra de verdad -aire arriba y abajo, aire a los lados- porque
        cuando es lo unico que hay, pegarlo al borde de arriba deja media
        pantalla vacia debajo y parece que falta algo.
        """
        raiz_vista.columnconfigure(0, weight=1)
        raiz_vista.columnconfigure(1, weight=0)
        raiz_vista.columnconfigure(2, weight=1)
        raiz_vista.rowconfigure(0, weight=2)
        raiz_vista.rowconfigure(5, weight=3)

        centro = self.centro = tk.Frame(raiz_vista, bg=PAPEL)
        # EL SUELO SE FIJA CUANDO LA MAQUETA SABE LO QUE MIDE, y eso no es en
        # `after_idle` del constructor: ahi los hijos aun no tienen tamaño y
        # `winfo_reqheight` devuelve una cifra de mentira. Se pregunta cada vez
        # que el formulario cambia de tamaño, que es cuando puede contestar.
        centro.bind("<Configure>", lambda _e: self._suelo_de_la_ventana())
        centro.grid(row=1, column=1, rowspan=4, sticky="n")

        tk.Label(centro, text="D E P A R T A M E N T O   F I S C A L",
                 bg=PAPEL, fg=TINTA3, font=self.fuente_rotulo,
                 anchor="w").pack(anchor="w")
        tk.Label(centro, text="Consulta fiscal sobre el IVA", bg=PAPEL,
                 fg=TINTA, font=self.fuente_titular, anchor="w"
                 ).pack(anchor="w", pady=(AIRE, 0))

        self.marco_motor = tk.Frame(centro, bg=PAPEL2)
        tk.Frame(self.marco_motor, width=3, bg=LILA).pack(side="left", fill="y")
        self.aviso_motor = tk.Label(
            self.marco_motor, text="", bg=PAPEL2, fg=TINTA2, anchor="w",
            justify="left", font=self.fuente, padx=HUECO2, pady=HUECO2 - 2,
            wraplength=ANCHO_TARJETA - 40)
        self.aviso_motor.pack(side="left", fill="x", expand=True)

        self.tarjeta = tarjeta = tk.Frame(centro, bg=PAPEL2,
                                          highlightthickness=1,
                                          highlightbackground=FILETE,
                                          padx=RELLENO, pady=RELLENO)
        tarjeta.pack(fill="x", pady=(HUECO, 0))
        tarjeta.columnconfigure(0, weight=1)

        tk.Label(tarjeta, text="TU DUDA", bg=PAPEL2, fg=TINTA3,
                 font=self.fuente_seccion, anchor="w"
                 ).grid(row=0, column=0, sticky="ew")
        # AQUI SI CABEN CUATRO LINEAS. Cuando el formulario compartia pantalla
        # con la respuesta, cada linea se la quitaba a lo que hay que leer; con
        # la pantalla para el solo, no le quita nada a nadie.
        # La caja y su aviso van juntos en un cajon para no renumerar toda la
        # rejilla de la tarjeta por meter una linea debajo.
        cajon = tk.Frame(tarjeta, bg=PAPEL2)
        cajon.grid(row=1, column=0, sticky="ew", pady=(AIRE, HUECO))
        self.caja = tk.Text(cajon, height=4, width=ANCHO_DUDA, wrap="word",
                            font=self.fuente_texto,
                            relief="flat", borderwidth=0,
                            padx=HUECO2, pady=HUECO2 - 4,
                            bg=ELEVADO, fg=TINTA,
                            insertbackground=LILA, spacing2=4,
                            selectbackground=SELECCION, selectforeground=TINTA,
                            highlightthickness=1,
                            highlightbackground=FILETE,
                            highlightcolor=LILA, bd=0)
        self.caja.pack(fill="x")
        self.caja.bind("<KeyRelease>", lambda _e: self._revisar_boton())
        # PEGAR NO ES ESCRIBIR. `<KeyRelease>` no llega cuando se pega con el
        # boton derecho, y pegar es justo lo que hace alguien con un
        # requerimiento delante. `<<Modified>>` salta con cualquier cambio,
        # venga de donde venga; hay que rearmar la marca a mano.
        self.caja.bind("<<Modified>>", self._caja_cambiada)

        # EL AVISO DE LARGO, MIENTRAS SE ESCRIBE. Antes solo se enteraba al
        # pulsar: se pegaba el requerimiento entero, se pulsaba y llegaba un
        # rechazo. Va en gris y sin alarma, y solo aparece cuando hace falta.
        self.aviso_largo = tk.Label(
            cajon, text="", bg=PAPEL2, fg=TINTA2, font=self.fuente_menuda,
            anchor="w", justify="left", wraplength=ANCHO_TARJETA - 40)
        self.aviso_largo.pack(fill="x", pady=(AIRE, 0))
        self.aviso_largo.pack_forget()

        # DOS GRUPOS, Y SE PLIEGAN CUANDO NO CABEN.
        #
        # Antes era una sola fila con todo empaquetado `side="left"`. Pedia
        # 1.132 px, la tarjeta declaraba 720 y no los hacia cumplir
        # -`pack_propagate` en True-, asi que crecia en silencio hasta que el
        # desplegable de comunidad quedaba FUERA de la ventana. En este Mac
        # desaparecia por debajo de 960 px de ancho, o sea por debajo del
        # propio `minsize`. En un Windows con Segoe UI y escalado al 150 %, esa
        # fila pide hasta 1.700 px: fuera siempre.
        #
        # Un control fuera de la ventana es un control que no existe. Y no se
        # arregla con un ancho mayor, que solo mueve el umbral: se arregla
        # haciendo que la fila se PLIEGUE.
        self.fila_campos = tk.Frame(tarjeta, bg=PAPEL2)
        self.fila_campos.grid(row=2, column=0, sticky="ew")
        fila = self.grupo_ejercicio = tk.Frame(self.fila_campos, bg=PAPEL2)
        tk.Label(fila, text="Ejercicio (el año del caso):", bg=PAPEL2,
                 fg=TINTA, font=self.fuente).pack(side="left")
        self.ejercicio = tk.StringVar()
        self.ejercicio.trace_add("write", lambda *_: self._revisar_boton())
        self.caja_ejercicio = ttk.Entry(fila, textvariable=self.ejercicio,
                                        width=7, font=self.fuente,
                                        style="Campo.TEntry", justify="center")
        self.caja_ejercicio.pack(side="left", padx=(HUECO2, HUECO2 - 4))
        # Se deja VACIO a proposito. Ver la regla 2 de la cabecera.
        tk.Label(fila, text="obligatorio: la ley cambia cada año",
                 bg=PAPEL2, fg=TINTA2, font=self.fuente_menuda
                 ).pack(side="left")

        # LA COMUNIDAD, AL LADO DEL AÑO Y POR EL MISMO MOTIVO.
        #
        # Es un dato que, si falta, hace que la respuesta salga impecable y a
        # medias: en Renta y en Patrimonio media respuesta puede estar en la
        # norma autonomica. Un aviso al pie no sirve -se lee una vez y se deja
        # de ver-, asi que va donde va el año: en la pregunta.
        #
        # PERO NO BLOQUEA, Y ESA ES LA DIFERENCIA CON EL AÑO. Ver la nota
        # larga en el LEEME: el año no tiene alternativa segura -cualquier año
        # supuesto es un año equivocado- y la comunidad si la tiene: contestar
        # solo con lo estatal, diciendolo. Ademas la ventana NO SABE de que
        # impuesto es la pregunta hasta que el analizador la lee, o sea
        # despues de pulsar; exigirla aqui obligaria a saberlo antes.
        #
        # Vacia por defecto y nunca se rellena sola, ni siquiera con Cataluña:
        # rellenarla seria suponer donde vive el cliente.
        fila = self.grupo_comunidad = tk.Frame(self.fila_campos, bg=PAPEL2)
        tk.Label(fila, text="Comunidad:", bg=PAPEL2, fg=TINTA,
                 font=self.fuente).pack(side="left")
        self.comunidad = tk.StringVar()
        self.caja_comunidad = ttk.Combobox(
            fila, textvariable=self.comunidad, width=14, font=self.fuente,
            state="normal", values=COMUNIDADES)
        self.caja_comunidad.pack(side="left", padx=(HUECO2, HUECO2 - 4))
        tk.Label(fila, text="solo si el caso tiene tramo autonomico",
                 bg=PAPEL2, fg=TINTA2, font=self.fuente_menuda
                 ).pack(side="left")
        self._plegada = None
        self.fila_campos.bind("<Configure>", self._plegar_campos)

        tk.Frame(tarjeta, height=1, bg=FILETE).grid(
            row=3, column=0, sticky="ew", pady=(HUECO, HUECO))

        # DOS BOTONES, SIEMPRE LOS DOS. Ya no dependen de ningun fichero: si
        # se decide usar solo la ley, se decide aqui -no pulsando el segundo-,
        # no editando configuracion.
        fila_ley = tk.Frame(tarjeta, bg=PAPEL2)
        fila_ley.grid(row=4, column=0, sticky="ew")
        self.boton = ttk.Button(fila_ley, text=BOTON_LEY,
                                style="Primario.TButton",
                                command=lambda: self._lanzar(False),
                                state="disabled")
        self.boton.pack(side="left")
        self._pinchable(self.boton)

        # El segundo va DEBAJO y en su propia fila: con los dos al lado se
        # pulsa el que queda mas a mano, no el que se queria. Debajo, en gris,
        # QUE ANADE: fuentes, no precio.
        fila_criterio = tk.Frame(tarjeta, bg=PAPEL2)
        fila_criterio.grid(row=5, column=0, sticky="ew", pady=(HUECO2, 0))
        fila_criterio.columnconfigure(0, weight=1)
        self.boton_criterio = ttk.Button(
            fila_criterio, text=BOTON_CRITERIO, style="Segundo.TButton",
            command=lambda: self._lanzar(True), state="disabled")
        self.boton_criterio.grid(row=0, column=0, sticky="w")
        self._pinchable(self.boton_criterio)
        # LO QUE HACE, FIJO; DE QUE HAY, CONTADO. La segunda mitad se rellena
        # en `_arrancar_motor`, que es cuando el corpus ya esta cargado y se
        # puede contar la despensa. Hasta entonces se dice solo lo que hace.
        self.pie_criterio = tk.Label(
            fila_criterio, text=PIE_CRITERIO, bg=PAPEL2,
            fg=TINTA2, font=self.fuente_menuda, anchor="w",
            justify="left", wraplength=ANCHO_TARJETA - 40)
        self.pie_criterio.grid(row=1, column=0, sticky="ew", pady=(AIRE, 0))

        # --- progreso ---
        self.marco_progreso = tk.Frame(centro, bg=PAPEL)
        self.marco_progreso.pack(fill="x", pady=(HUECO2, 0))
        self.barra = ttk.Progressbar(self.marco_progreso, mode="indeterminate",
                                     style="Barra.Horizontal.TProgressbar")
        self.paso = tk.Label(self.marco_progreso, text="", bg=PAPEL,
                             fg=TINTA2, font=self.fuente, anchor="w")

        pie_fila = tk.Frame(centro, bg=PAPEL)
        pie_fila.pack(fill="x", pady=(HUECO, 0))
        self.pie = tk.Label(pie_fila, text="", bg=PAPEL, fg=TINTA3,
                            font=self.fuente_rotulo, anchor="w")
        self.pie.pack(side="left")
        self.boton_dentro = ttk.Button(
            pie_fila, text="Qué hay dentro", style="Discreto.TButton",
            command=self._abrir_estado)
        self.boton_dentro.pack(side="right")
        self._pinchable(self.boton_dentro)

    # ---------------------------------------------------- vista 2: leer

    def _construir_respuesta(self, raiz_vista) -> None:
        """LA PANTALLA DE LEER. La ventana entera, y nada que le quite sitio.

        Arriba una barra fina -el boton de volver y con que se hizo- y debajo
        todo lo demas dentro de un lienzo desplazable: estado, aporte, avisos y
        el texto. La barra de arriba es lo unico fijo, y ocupa una linea.
        """
        raiz_vista.columnconfigure(0, weight=1)
        raiz_vista.rowconfigure(1, weight=1)

        barra_alta = tk.Frame(raiz_vista, bg=PAPEL)
        barra_alta.grid(row=0, column=0, sticky="ew", pady=(0, AIRE))
        barra_alta.columnconfigure(1, weight=1)

        self.boton_volver = ttk.Button(
            barra_alta, text="←  Nueva consulta", style="Segundo.TButton",
            command=self._nueva_consulta)
        self.boton_volver.grid(row=0, column=0, sticky="w")
        self._pinchable(self.boton_volver)

        self.eco_pregunta = tk.Label(
            barra_alta, text="", bg=PAPEL, fg=TINTA3,
            font=self.fuente_menuda, anchor="w", justify="left")
        self.eco_pregunta.grid(row=0, column=1, sticky="ew", padx=(HUECO, 0))

        self.eco_expediente = tk.Label(
            barra_alta, text="", bg=PAPEL, fg=TINTA3,
            font=self.fuente_rotulo, anchor="e")
        self.eco_expediente.grid(row=0, column=2, sticky="e", padx=(HUECO, 0))

        # ESCRIBIRLO PARA EL CLIENTE. Nace apagado y solo se enciende cuando
        # hay una respuesta ACEPTADA en pantalla: si la consulta acabo en no
        # encontrado no hay nada que reescribir, y un boton encendido sobre
        # nada es una promesa que no se puede cumplir.
        #
        # UNA SOLA FORMA, la que pidio el departamento. Empezar con tres
        # -«resumelo», «alargalo», «para el cliente»- seria decidir por ellos
        # que formas quieren antes de que lo hayan usado.
        #
        # El rotulo dice QUE HACE, no como funciona: quien lo lee no tiene por
        # que saber que hay una segunda redaccion ni un verificador detras.
        self.boton_cliente = ttk.Button(
            barra_alta, text="Escribirlo para el cliente",
            style="Discreto.TButton", command=self._escribir_para_cliente,
            state="disabled")
        self.boton_cliente.grid(row=0, column=3, sticky="e", padx=(0, AIRE))
        self._pinchable(self.boton_cliente)

        self.boton_copiar = ttk.Button(barra_alta, text="Copiar respuesta",
                                       style="Discreto.TButton",
                                       command=self._copiar, state="disabled")
        self.boton_copiar.grid(row=0, column=4, sticky="e")
        self._pinchable(self.boton_copiar)
        self.copiado = tk.Label(barra_alta, text="", bg=PAPEL,
                                fg=LILA, font=self.fuente_menuda)
        self.copiado.grid(row=0, column=5, sticky="e", padx=(AIRE, 0))

        # --- lo que se lee ---
        #
        # EL ESTADO Y LOS AVISOS ARRIBA Y QUIETOS; EL TEXTO CON SU PROPIO VISOR.
        #
        # La version anterior metia las cuatro cosas en un solo lienzo que se
        # desplazaba entero. Resolvia que nada quedara fuera de alcance, pero
        # tenia un coste que solo se ve midiendo: el estado, el aporte y los
        # avisos ocupaban los primeros 470 px, asi que de la respuesta se veian
        # DOCE lineas antes de tener que desplazar.
        #
        # Ahora el bloque de arriba es fijo -se lee una vez- y el texto se
        # queda con todo lo que sobra y desplaza por su cuenta. Se pasa de 12
        # lineas a 24 sin tocar los tamaños.
        #
        # ¿Y SI HAY MUCHOS AVISOS? No queda nada inalcanzable, y esta medido:
        # sobre 864 consultas reales el maximo son CUATRO avisos, y en 820 de
        # ellas ninguno. Si algun dia fueran muchos, el bloque de arriba se
        # queda entero -grid sirve primero a las filas sin peso- y lo que se
        # encoge es el visor del texto, que tiene barra: mas apretado, pero
        # nada que no se pueda leer.
        self.resultado = tk.Frame(raiz_vista, bg=PAPEL)
        self.resultado.grid(row=1, column=0, sticky="nsew")
        self.resultado.columnconfigure(0, weight=1)
        # Fila 1: LA PAGINA. El estado va en la 0 y no se mueve.
        self.resultado.rowconfigure(1, weight=1)

        # LA BANDA DE ARRIBA USA EL ANCHO, NO EL ALTO.
        #
        # Apiladas, el estado, el aporte y los avisos se comian 392 px de alto
        # y dejaban la respuesta en doce lineas. Y mientras tanto, maximizada,
        # sobraban 900 px de ancho a los lados del parrafo sin hacer nada.
        #
        # En dos columnas -lo que se ha encontrado a la izquierda, lo que falta
        # por mirar a la derecha- la misma informacion ocupa la mitad de alto y
        # se lee igual de bien. Por debajo de `ANCHO_DOS_COLUMNAS` se vuelven a
        # apilar: en una ventana estrecha dos columnas serian dos columnas
        # ilegibles. Lo decide `_reajustar`.
        # LA PAGINA SE DESPLAZA ENTERA, Y EL TEXTO NO TIENE BARRA PROPIA.
        #
        # Antes habia dos zonas independientes: una banda fija arriba y un
        # `Text` con su propia barra debajo. Eso daba los dos sintomas que se
        # midieron: con una respuesta corta sobraban 325 px de caja vacia, y
        # con una larga se veian 17 lineas de 108 porque la banda se quedaba
        # con el primer tercio de la ventana para siempre.
        #
        # AQUI ESTUVO ANTES, Y SE CAMBIO POR ESTO MISMO. El comentario que
        # habia decia «se pasa de 12 lineas a 24» al clavar la banda. Medido
        # hoy no son 24 sino 17, y la banda de entonces se apilaba en 470 px;
        # ahora son dos columnas y ocupa 148-334 segun los avisos. La cuenta
        # que justificaba clavarla ya no da lo mismo.
        self.caja_lectura, self.pagina, self.lienzo_lectura = \
            self._desplazable(self.resultado)
        self.caja_lectura.grid(row=1, column=0, sticky="nsew")

        self.pagina.columnconfigure(0, weight=1)
        self.banda = tk.Frame(self.pagina, bg=PAPEL)
        self._lateral = None           # todavia sin decidir
        self.columna_izq = tk.Frame(self.banda, bg=PAPEL)
        self.columna_der = tk.Frame(self.banda, bg=PAPEL)
        self._dos_columnas = None       # todavia sin decidir

        # EL ESTADO ES LO UNICO QUE NO SE MUEVE. Es lo que no puedes perder
        # de vista mientras lees: si has bajado media respuesta y ya no ves si
        # el criterio era CLARO o DISCUTIDO, la respuesta se lee mal.
        self.panel_estado = tk.Frame(self.resultado, bg=PAPEL2)
        self.panel_estado.grid(row=0, column=0, sticky="ew")
        # EL ROTULO ENCIMA, NO AL LADO. Probadas las dos: al lado, el rotulo
        # se come 320 px de ancho y la explicacion se parte en CUATRO lineas
        # (88 px); encima, la explicacion tiene la columna entera y se queda
        # en tres, y el «hecha con» en una en vez de dos. Apilado ocupa menos
        # alto que en horizontal, que es justo lo contrario de lo que parece.
        self.panel_estado.columnconfigure(1, weight=1)
        self.filete_estado = tk.Frame(self.panel_estado, width=5, bg=FILETE)
        self.etiqueta_estado = tk.Label(
            self.panel_estado, text="", font=self.fuente_estado, anchor="w",
            # SIN `wraplength`: el rotulo va en una linea. Con 260 px se
            # partia en tres -medido- y el panel entero subia 60 px por una
            # cifra puesta a ojo. El mas largo, «NO SE HA PODIDO CONSULTAR»,
            # cabe de sobra en la columna.
            justify="left", padx=RELLENO, pady=(HUECO2 - 4),
        )
        # CLAVADO ARRIBA VA SOLO EL ROTULO. La explicacion y el «hecha con»
        # se leen una vez; el rotulo es lo que no puedes perder de vista
        # mientras lees, porque una respuesta de CRITERIO DISCUTIDO se lee de
        # otra manera que una de CRITERIO CLARO.
        #
        # Y no es solo doctrina: clavando el panel entero se comian 148 px y
        # de la respuesta se veian DIECINUEVE lineas al abrir, por debajo del
        # liston de veinte. Clavando solo el rotulo son 58, y los otros 90
        # vuelven a la pagina.
        self.panel_detalle = tk.Frame(self.columna_izq, bg=PAPEL2)
        self.panel_detalle.pack(fill="x")
        self.panel_detalle.columnconfigure(1, weight=1)
        self.filete_detalle = tk.Frame(self.panel_detalle, width=5, bg=FILETE)
        self.etiqueta_explicacion = tk.Label(
            # El hueco asimetrico va en el `grid`, NO aqui: `padx` de un
            # widget es UNA distancia y con (0, 24) tkinter revienta. Es la
            # tercera vez que caigo en la misma piedra.
            self.panel_detalle, text="", font=self.fuente, anchor="w",
            justify="left", pady=0,
        )
        # Zona «estado»: lo que queda a la derecha del rotulo, y el rotulo
        # mide lo que mida su palabra. Restar una cifra fija dejaba la
        # explicacion envolviendo a 642 px cuando tenia 771 disponibles: una
        # linea de mas, y esa linea vale dos de respuesta.

        self.etiqueta_hecha_con = tk.Label(
            self.panel_detalle, text="", font=self.fuente_menuda, anchor="w",
            justify="left", pady=0, fg=TINTA3,
        )
        # EL ANCHO SE PREGUNTA, NO SE CALCULA.
        #
        # Tres intentos de deducirlo -«la columna es el 60%, menos el relleno,
        # menos el rotulo»- y los tres dieron de menos: 642 px cuando habia
        # 771, y una linea de mas en la explicacion. Una linea de la banda
        # cuesta dos de respuesta.
        #
        # El panel ya sabe lo que mide. Se le pregunta cuando cambia.
        self.panel_detalle.bind("<Configure>", self._wrap_estado)

        # EL APORTE, DEBAJO DEL ESTADO. Probado tambien en la columna derecha
        # y sale peor: alli el ancho es menor, el texto se parte en mas lineas
        # y la banda sube de 257 a 276 px. La banda mide lo que su columna mas
        # alta, asi que lo que importa no es donde queda mejor sino como quedan
        # de igualadas las dos.
        self.panel_aporte = tk.Frame(self.columna_izq, bg=PAPEL2,
                                     highlightthickness=1,
                                     highlightbackground=FILETE)
        self.panel_aporte.pack(fill="x", pady=(AIRE + 2, 0))
        self.panel_aporte.pack_forget()

        # Los avisos van ARRIBA, antes del texto: si se ponen al final no los
        # lee nadie, y son justo lo que puede invalidar la respuesta.
        self.panel_avisos = tk.Frame(self.columna_der, bg=PAPEL2,
                                     highlightthickness=1,
                                     highlightbackground=FILETE,
                                     pady=AIRE - 4)
        self.panel_avisos.pack(fill="x")
        self.panel_avisos.pack_forget()

        # EL EXPEDIENTE SE VA A LA BARRA DE ARRIBA, con la pregunta.
        #
        # Tuvo fila propia -arriba primero, abajo despues- y en las dos
        # costaba 28 px de alto: una linea entera de respuesta por un dato que
        # se mira una vez al mes. En la barra de arriba no cuesta nada, porque
        # esa barra ya existe y le sobra ancho.
        self.pie_respuesta = self.eco_expediente

        caja = self.caja_texto = tk.Frame(self.pagina, bg=PAPEL2,
                                          highlightthickness=1,
                                          highlightbackground=FILETE)
        caja.columnconfigure(0, weight=1)
        caja.rowconfigure(0, weight=1)
        # EL TEXTO, QUE ES A LO QUE SE VIENE.
        #
        # `width=1, height=1` para que no pida sitio y se quede con lo que hay:
        # un Text sin medidas pide 80x24 caracteres, y eso fue exactamente lo
        # que un dia dejo la respuesta en dos lineas.
        self.texto = tk.Text(caja, wrap="word", font=self.fuente_texto,
                             width=1, height=1,
                             bd=0, highlightthickness=0,
                             padx=RELLENO, pady=RELLENO, fg=TINTA,
                             state="disabled",
                             spacing1=INTERLINEA_PARRAFO,
                             spacing2=INTERLINEA,
                             spacing3=INTERLINEA_PARRAFO * 2,
                             background=PAPEL2,
                             insertbackground=LILA, cursor="arrow",
                             takefocus=True,
                             selectbackground=SELECCION, selectforeground=TINTA)
        self.texto.grid(row=0, column=0, sticky="nsew")
        # SIN BARRA PROPIA: la que desplaza es la de la pagina. Dos barras
        # anidadas hacian que la respuesta pareciera una ventanita dentro de
        # la ventana, y ademas dejaban media pantalla sin usar.
        self._atar_desplazamiento()

        self.texto.tag_configure("enlace", foreground=ENLACE, underline=True,
                                 font=self.fuente_referencia)
        self.texto.tag_bind("enlace", "<Enter>",
                            lambda _e: self.texto.configure(cursor="hand2"))
        self.texto.tag_bind("enlace", "<Leave>",
                            lambda _e: self.texto.configure(cursor="arrow"))
        self.texto.tag_bind("enlace", "<Button-1>", self._abrir_enlace)
        self.texto.tag_configure("titulo", font=self.fuente_subtitulo,
                                 foreground=TINTA, spacing1=INTERLINEA_PARRAFO * 2,
                                 spacing3=INTERLINEA_PARRAFO)
        self.texto.tag_configure("apagado", foreground=TINTA2,
                                 font=self.fuente_menuda)
        # LA JERARQUIA QUE HACE UTIL LA PANTALLA. La cita es lo mas grande y
        # va en serif; la referencia, en monoespaciada y menuda. Distinta
        # familia y distinto tamaño: asi una cita no se confunde nunca con la
        # explicacion que la rodea. Y con AIRE DE VERDAD por arriba y por
        # abajo: una cita pegada al parrafo siguiente se lee como parte de el.
        self.texto.tag_configure("cita", font=self.fuente_cita, foreground=TINTA,
                                 lmargin1=HUECO2, lmargin2=HUECO2,
                                 rmargin=HUECO2,
                                 spacing1=AIRE * 3, spacing3=AIRE * 3)
        self.texto.tag_configure("referencia", font=self.fuente_referencia,
                                 foreground=TINTA2)
        self.texto.tag_configure("rotulo", font=self.fuente_seccion,
                                 foreground=TINTA3, spacing1=AIRE * 3)
        self.texto.tag_configure("columna")
        self.texto.tag_lower("columna")

    # ---------------------------------------------------- cambiar de vista

    def mostrar_cinta(self, texto: str) -> None:
        """La cinta de aviso sobre la tarjeta. `pack`, no `grid`.

        Dentro de un contenedor gestionado por `pack` no se puede meter un hijo
        con `grid`: tkinter no lo mezcla y lanza «cannot use geometry manager».
        Y va con `before=` porque `pack` coloca por orden de llegada, y esta
        nace despues de la tarjeta que tiene que ir debajo.
        """
        self.aviso_motor.configure(text=texto)
        self.marco_motor.pack(fill="x", pady=(HUECO, 0), before=self.tarjeta)

    def _mostrar(self, cual: str) -> None:
        """Cambia de vista. Nada se destruye: solo se quita del grid."""
        if cual == "respuesta":
            self.vista_consulta.grid_remove()
            self.vista_respuesta.grid()
            self.texto.focus_set()
        else:
            self.vista_respuesta.grid_remove()
            self.vista_consulta.grid()
            self.caja.focus_set()
        self._ancho_previo = 0
        self._reajustar()

    @staticmethod
    def _eco(duda: str, ejercicio: str, comunidad: str = "") -> str:
        """La pregunta, recortada, en la barra de arriba de la respuesta.

        Leyendo una respuesta larga es facil perder de vista que se pregunto
        exactamente, y sobre todo CON QUE AÑO: media respuesta depende de eso.
        Y desde que hay normativa autonomica, con que COMUNIDAD: media
        respuesta de Renta puede depender de eso igual.
        """
        duda = " ".join((duda or "").split())
        if len(duda) > 90:
            duda = duda[:88].rsplit(" ", 1)[0] + "…"
        if not duda:
            return ""
        eco = f"«{duda}»    ·    ejercicio {ejercicio}"
        if comunidad:
            eco += f"    ·    {comunidad}"
        return eco

    def _nueva_consulta(self) -> None:
        """Vuelve a preguntar CON LA PREGUNTA ANTERIOR PUESTA.

        Casi nunca se cambia la duda entera: se cambia el año, o una palabra.
        Devolver la caja en blanco obliga a reescribirla, y quien la reescriba
        de memoria no escribira exactamente lo mismo — con lo cual ya no esta
        comparando dos respuestas a la misma pregunta.

        Se selecciona el año, que es lo que mas se cambia, para que se pueda
        teclear otro encima sin borrar.
        """
        self._mostrar("consulta")
        self.caja_ejercicio.focus_set()
        self.caja_ejercicio.select_range(0, "end")

    # --------------------------------------------- desplazamiento

    def _suelo_de_la_ventana(self) -> None:
        """El minimo lo dice la maqueta, no una cifra escrita a mano.

        Estaba fijo en 620 de alto, y a esa altura el boton «Qué hay dentro»
        caia en y=691: FUERA de la ventana. Un control fuera de la ventana es
        un control que no existe, y no hay forma de descubrirlo mirando el
        codigo, porque nada falla: simplemente no esta.

        Y no se puede dejar clavado en otro numero mayor, porque lo que mide
        el formulario depende de la fuente del sistema y de su escalado: lo
        que en un Mac son 725 px en un Windows al 150 % son bastantes mas.
        Se pregunta.
        """
        try:
            alto = self.centro.winfo_reqheight() + HUECO * 2
            ancho = self.centro.winfo_reqwidth() + HUECO * 2
        except tk.TclError:  # pragma: no cover - ventana cerrandose
            return
        # Con un techo: si la maqueta pidiera mas que la pantalla, un minimo
        # mayor que el monitor deja la ventana imposible de colocar.
        alto = min(alto, int(self.raiz.winfo_screenheight() * 0.95))
        ancho = min(ancho, int(self.raiz.winfo_screenwidth() * 0.95))
        self.raiz.minsize(max(860, ancho), max(620, alto))

    def _ofrecer_cambiar_clave(self) -> None:
        """Un boton para volver a pedir la credencial, sin terminal."""
        b = ttk.Button(self.marco_motor, text="Poner otra clave de acceso",
                       style="Segundo.TButton", command=self._cambiar_clave)
        b.pack(pady=(HUECO2, 0))
        self._pinchable(b)
        self._boton_clave = b

    def _cambiar_clave(self) -> None:
        """Abre el MISMO dialogo del primer arranque. Ni uno nuevo ni parecido.

        Si hubiera dos sitios donde se pide la clave, dentro de un mes dirian
        cosas distintas y uno de los dos guardaria donde no toca.
        """
        import dialogo_clave
        import instalar
        clave, cancelado = dialogo_clave.pedir_clave(
            comprobador=instalar.comprobar_clave,
            guardar=instalar.guardar_clave)
        if cancelado or not clave:
            return
        self._escribir_texto([
            ("Clave guardada. Cierra y vuelve a abrir el agente.\n", "titulo")])

    def _actualizar_corpus(self) -> None:
        """Vuelve a bajar las normas del BOE. Desde la ventana, sin terminal.

        NO SE HACE SOLO Y NO SE HACE EN SILENCIO: mueve el corpus entero, o sea
        cambia los sellos y puede cambiar lo que se recupera. Se pide
        confirmacion diciendo lo que va a pasar y cuanto tarda.
        """
        from tkinter import messagebox
        if not messagebox.askokcancel(
                "Actualizar las normas",
                "Se vuelven a bajar las normas del BOE y se rehace la copia "
                "local.\n\nTarda unos minutos y hace falta internet. Mientras "
                "tanto no se puede consultar.\n\nDespués conviene mirar que "
                "todo sigue en su sitio.", parent=self.raiz):
            return
        self._bloquear(
            "Actualizando las normas desde el BOE. No cierres la ventana; "
            "cuando termine, cierra y vuelve a abrir el agente.")
        import subprocess
        import threading

        def trabajar() -> None:
            # SE RE-INGIERE LA LISTA, NO LO QUE HAYA EN LOCAL.
            #
            # Antes recorria `self.ix.rutas`, o sea las normas de ESTE equipo, y
            # por eso una maquina con trece se quedaba con trece para siempre:
            # el boton la ponia al dia de sus trece y las tres que no tenia
            # seguian sin existir para ella. Cada equipo conservaba su agujero,
            # y el boton parecia que lo arreglaba.
            from agente_fiscal import catalogo as CAT
            lista = CAT.del_disco() or [
                {"id": r.stem, "nombre": r.stem} for r in self.ix.rutas]
            fallos = []
            for i, n in enumerate(lista, 1):
                self.raiz.after(0, lambda i=i, n=n: self._bloquear(
                    f"Actualizando las normas desde el BOE ({i} de "
                    f"{len(lista)}): {n['nombre']}.\nNo cierres la ventana."))
                r = subprocess.run(
                    [sys.executable, str(RAIZ / "fase1.py"), "ingerir", n["id"]],
                    capture_output=True, text=True, cwd=str(RAIZ))
                if r.returncode:
                    fallos.append(n["id"])
            self.raiz.after(0, lambda: self._bloquear(
                "Normas actualizadas. Cierra y vuelve a abrir el agente."
                if not fallos else
                f"No se han podido actualizar {len(fallos)} normas. "
                f"Avisa a Emili."))

        threading.Thread(target=trabajar, daemon=True).start()

    def _vaciar_cola_por_detras(self) -> None:
        """Pide a PETETE lo apuntado, en un hilo, sin tocar la ventana.

        NO BLOQUEA NI PUEDE BLOQUEAR, y hay tres cosas que lo garantizan:

          · va en un hilo aparte, asi que la ventana sigue respondiendo;
          · es lo ULTIMO del arranque: cuando empieza, ya se puede consultar;
          · y no escribe en la ventana mientras trabaja. Lo que traiga se dira
            MAÑANA, al abrir. Un cartel que aparece a media consulta es una
            interrupcion, y esto no es urgente para nadie.

        Si falla, se calla: `cola.vaciar` no levanta y el intento queda
        apuntado. Lo que no se baje hoy se baja la proxima vez.
        """
        import threading

        def trabajar() -> None:
            try:
                from agente_fiscal import cola as _COLA
                _COLA.vaciar()
            except Exception:                    # noqa: BLE001
                pass

        threading.Thread(target=trabajar, daemon=True).start()

    def _plegar_campos(self, _evento=None) -> None:
        """El año y la comunidad, al lado si caben; apilados si no.

        SE PREGUNTA LO QUE MIDEN, no se supone. Un umbral en pixeles escrito a
        ojo acierta en el equipo donde se escribio y falla en el otro, que es
        exactamente lo que paso: en Mac la fila cabia y en Windows -Segoe UI,
        escalado del sistema- no, y el campo se pintaba fuera de la ventana sin
        que nada avisara.
        """
        try:
            hay = self.fila_campos.winfo_width()
            piden = (self.grupo_ejercicio.winfo_reqwidth()
                     + HUECO + self.grupo_comunidad.winfo_reqwidth())
        except tk.TclError:  # pragma: no cover - ventana cerrandose
            return
        if hay <= 1:
            return
        plegada = piden > hay
        if plegada == self._plegada:
            return
        self._plegada = plegada
        self.grupo_ejercicio.pack_forget()
        self.grupo_comunidad.pack_forget()
        if plegada:
            self.grupo_ejercicio.pack(side="top", anchor="w")
            self.grupo_comunidad.pack(side="top", anchor="w",
                                      pady=(HUECO2, 0))
        else:
            self.grupo_ejercicio.pack(side="left")
            self.grupo_comunidad.pack(side="left", padx=(HUECO, 0))

    def _ajustar_alto_del_texto(self) -> None:
        """EL TEXTO MIDE LO QUE MIDE SU CONTENIDO. Ni mas ni menos.

        Con alto fijo pasaban las dos cosas a la vez: una respuesta corta
        dejaba 325 px de caja en blanco -medido- y una larga se quedaba
        encerrada en un visor mientras media ventana la miraba. Quien desplaza
        es la pagina.

        `count displaylines` es lo que hay que preguntar, no las lineas del
        texto: lo que ocupa alto son las lineas de PANTALLA, y una sola frase
        larga en una columna de 74 son seis.
        """
        try:
            cuenta = self.texto.count("1.0", "end", "displaylines")
        except tk.TclError:  # pragma: no cover - ventana cerrandose
            return
        lineas = max(1, (cuenta or [1])[0])
        if lineas != int(self.texto.cget("height")):
            self.texto.configure(height=lineas)
        self._lineas_de_respuesta = lineas

    def _atar_desplazamiento(self) -> None:
        """LA RESPUESTA SE TIENE QUE PODER RECORRER ENTERA. Raton y teclado.

        tkinter no trae nada de esto puesto. Y la rueda NO es el mismo evento
        en los tres sistemas:

            Mac      <MouseWheel>, delta pequeño (1, 2, 3...) y ya en «lineas»
            Windows  <MouseWheel>, delta en multiplos de 120
            Linux    <Button-4> y <Button-5>, sin delta

        Escrito una sola vez para los tres, porque el que no se pruebe hoy es
        justo el que se rompera en el PC de la oficina.

        Se ata al LIENZO y a todo lo que hay dentro: la rueda la recibe el
        widget que esta debajo del raton, y debajo del raton casi siempre hay
        una etiqueta, no el lienzo. Sin recorrer los hijos, la rueda solo
        funcionaria en los huecos entre paneles.
        """
        # La rueda, tambien sobre la banda de arriba. Ahi no hay nada que
        # desplazar -es fija- pero quien mueve la rueda mirando el estado
        # espera que baje la respuesta, no que no pase nada.
        for evento in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            for w in (self.texto, self.panel_estado, self.panel_detalle,
                      self.panel_aporte, self.panel_avisos, self.resultado,
                      self.banda, self.pagina, self.caja_lectura):
                w.bind(evento, self._rueda)

        teclas = {
            "<Up>": lambda: self.lienzo_lectura.yview_scroll(-2, "units"),
            "<Down>": lambda: self.lienzo_lectura.yview_scroll(2, "units"),
            "<Prior>": lambda: self.lienzo_lectura.yview_scroll(-1, "pages"),
            "<Next>": lambda: self.lienzo_lectura.yview_scroll(1, "pages"),
            "<Home>": lambda: self.lienzo_lectura.yview_moveto(0.0),
            "<End>": lambda: self.lienzo_lectura.yview_moveto(1.0),
        }
        for tecla, accion in teclas.items():
            self.texto.bind(tecla, lambda _e, a=accion: (a(), "break")[1])
        # Pinchar en la respuesta le da el teclado. No se devuelve "break", asi
        # que el Text sigue con lo suyo y se puede seguir seleccionando.
        self.texto.bind("<Button-1>", lambda _e: self.texto.focus_set(),
                        add="+")

    def _rueda(self, evento):
        if evento.num == 4:               # Linux, rueda arriba
            pasos = -3
        elif evento.num == 5:             # Linux, rueda abajo
            pasos = 3
        elif sys.platform == "darwin":    # Mac: el delta ya viene en lineas
            pasos = -evento.delta
        else:                             # Windows: multiplos de 120
            pasos = -evento.delta // 120 * 3
        # LA QUE SE MUEVE ES LA PAGINA. El texto ya no desplaza por su cuenta:
        # mide lo que mide su contenido y va dentro del lienzo.
        self.lienzo_lectura.yview_scroll(int(pasos), "units")
        return "break"

    def _atar_rueda_a_los_hijos_de(self, w, lienzo) -> None:
        """Como `_atar_rueda_a_los_hijos`, pero sobre otro lienzo."""
        for evento in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            try:
                w.bind(evento, lambda e, c=lienzo: self._rueda_de(e, c))
            except tk.TclError:  # pragma: no cover
                return
        for hijo in w.winfo_children():
            self._atar_rueda_a_los_hijos_de(hijo, lienzo)

    def _atar_rueda_a_los_hijos(self, w=None) -> None:
        """La rueda, en cada etiqueta que se acaba de crear.

        Se llama despues de pintar los paneles porque sus hijos nacen y mueren
        con cada consulta: atarlos una vez al construir la ventana no serviria
        de nada.
        """
        w = self.resultado if w is None else w
        for evento in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            try:
                w.bind(evento, self._rueda)
            except tk.TclError:  # pragma: no cover
                return
        for hijo in w.winfo_children():
            self._atar_rueda_a_los_hijos(hijo)

    def _arriba(self) -> None:
        """Toda respuesta nueva empieza por el principio.

        Sin esto, una respuesta corta detras de una larga aparece con la vista
        donde quedo la anterior: en blanco. Y quien lo vea entiende que no ha
        contestado.

        Y de paso se repregunta por la barra: el `yscrollcommand` llega DESPUES
        de escribir, y hasta entonces la barra sigue diciendo lo que decia de
        la respuesta anterior.
        """
        try:
            self.texto.update_idletasks()
            self._ajustar_alto_del_texto()
            # LA DISPOSICION SE DECIDE AQUI, con la respuesta ya escrita y una
            # sola vez. En `_reajustar` -que corre con cada pixel del
            # arrastre- solo se aplica lo decidido.
            self._decidir_disposicion()
            self._colocar_lateral(self.raiz.winfo_width())
            self.lienzo_lectura.yview_moveto(0.0)
        except tk.TclError:  # pragma: no cover - ventana cerrandose
            pass

    # ------------------------------------------------- ancho de lectura

    def _reajustar(self, evento=None) -> None:
        """QUE UN PARRAFO NO CRUCE LA PANTALLA ENTERA.

        tkinter no tiene `max-width` ni nada que se le parezca, asi que se
        calcula: se mide cuanto ocupan 88 caracteres con la fuente que de
        verdad se ha elegido en ESTA maquina -no la que se pidio- y lo que
        sobra se reparte a los dos lados.

        VA EN MARGENES DE ETIQUETA, NO EN EL RELLENO DEL WIDGET. Es la
        diferencia entre limitar el parrafo y limitar la ventana: el relleno
        cuenta para el tamaño que el widget pide, y el margen de etiqueta no.
        Con relleno, la ventana no se podia maximizar.

        Se llama en cada `<Configure>`, o sea muchas veces por segundo mientras
        se arrastra el borde. Por eso sale enseguida si el ancho no ha cambiado:
        redibujar un Text en cada pixel del arrastre se ve a simple vista.
        """
        ancho = self.raiz.winfo_width()
        if ancho <= 1 or ancho == getattr(self, "_ancho_previo", 0):
            return
        self._ancho_previo = ancho

        # SE CALCULA DEL ANCHO DE LA VENTANA, NO DEL ANCHO DEL TEXT.
        #
        # `winfo_width()` del Text durante un `<Configure>` devuelve el ancho
        # de ANTES: el redibujado no ha ocurrido todavia. Medido, el margen
        # salia 391 px en una ventana de 1000 y 70 px en una de 1400, o sea al
        # reves de lo que tiene que ser. La ventana ya sabe cuanto mide.
        # LAS RESTAS SON LAS DE LA VISTA DE LECTURA, no las de la de pedir.
        # Con `MARGEN` (32) en vez de `MARGEN_LECTURA` (16) y `HUECO2` en vez
        # del relleno real del Text, la cuenta daba de menos y el margen salia
        # cero: el parrafo se iba a 837 px en una ventana de 1180.
        # Primero se coloca -o no- la columna, porque el margen del parrafo
        # depende de si esta; si se calcula antes, se usa la disposicion del
        # redibujado anterior.
        self._colocar_lateral(ancho)
        visible = max(320, ancho - MARGEN_LECTURA * 2 - ANCHO_BARRA
                      - RELLENO * 2)
        # Y SI HAY COLUMNA AL LADO, ESE ANCHO YA NO ES DEL TEXTO. Sin restarlo,
        # el parrafo se centraria respecto a la ventana entera y quedaria
        # medio debajo de la columna lateral.
        #
        # SE PREGUNTA POR LA DISPOSICION, NO POR EL ANCHO. Restarlo por ancho
        # descuenta 400 px tambien cuando la banda va encima -una respuesta
        # corta en una ventana grande-, y entonces el parrafo se estrecha y se
        # va a la izquierda sin que haya ninguna columna al lado. Medido: las
        # respuestas cortas pasaban de 293 a 326 px de blanco por esto.
        if self._lateral:
            visible = max(320, visible - ANCHO_COLUMNA_LATERAL - HUECO)
        deseado = self.fuente_texto.measure("0" * COLUMNA_MAXIMA)
        margen = max(0, (visible - deseado) // 2)
        try:
            self.texto.tag_configure("columna", lmargin1=margen,
                                     lmargin2=margen, rmargin=margen)
            # La cita va sangrada DENTRO de la columna, no desde el borde de la
            # ventana: si no, al maximizar se quedaba pegada a la izquierda
            # mientras el parrafo se centraba.
            self.texto.tag_configure("cita", lmargin1=margen + HUECO2,
                                     lmargin2=margen + HUECO2,
                                     rmargin=margen + HUECO2)
        except tk.TclError:  # pragma: no cover - ventana cerrandose
            return

        # Al cambiar el margen cambia el envoltorio, y con el el numero de
        # lineas de pantalla: el alto del texto hay que rehacerlo aqui o la
        # pagina se queda con el de la anchura anterior.
        self._ajustar_alto_del_texto()
        # Al cambiar el ancho de la ventana cambian las dos columnas, asi que
        # los dos anchos guardados dejan de valer.
        self._ancho_estado = self._ancho_avisos = 0
        self.raiz.after_idle(self._wrap_estado)
        self.raiz.after_idle(self._wrap_avisos)

        # Y las etiquetas, que en tkinter no se ajustan solas: `wraplength` es
        # un numero de pixeles, no un porcentaje.
        # CADA ETIQUETA SE AJUSTA A SU COLUMNA, NO A LA VENTANA.
        #
        # Antes todas usaban el ancho de la ventana entera. Con la banda en dos
        # columnas eso significa pedir que una frase quepa en 1.538 px dentro
        # de una columna de 995: tkinter no la parte -se lo has dicho tu- y la
        # RECORTA. Se perderia el final de la explicacion del estado, que es
        # justo la parte que dice lo que la respuesta NO cubre.
        disponible = max(320, ancho - MARGEN_LECTURA * 2 - ANCHO_BARRA)
        # CON COLUMNA AL LADO, LO QUE HAY DISPONIBLE ES LA COLUMNA. Todo lo de
        # la banda vive dentro de ella, y si se le dice que puede ocupar el
        # ancho de la ventana, lo pide: medido, la columna salia de 730 px
        # habiendola declarado de 400. `columnconfigure(minsize=...)` es un
        # minimo, no un tope; el tope lo pone el ajuste de linea.
        if self._lateral:
            disponible = ANCHO_COLUMNA_LATERAL
        if self._dos_columnas:
            zona = {"izq": int(disponible * 0.6) - HUECO2,
                    "der": disponible - int(disponible * 0.6)}
        else:
            zona = {"izq": disponible, "der": disponible}
        zona["ancho"] = disponible
        for widget, cual, resta in self._elasticos:
            try:
                widget.configure(
                    wraplength=max(200, zona.get(cual, disponible) - resta))
            except tk.TclError:  # pragma: no cover
                pass
        # Al cambiar el ancho cambia el ajuste de linea, o sea cuantas lineas
        # ocupa el mismo texto. Si no se recuenta, al estrechar la ventana el
        # final de la respuesta se queda fuera del alto reservado.
        #
        # Y SE VUELVE A DONDE SE ESTABA LEYENDO. Recontar cambia el alto de la
        # columna, y con el la fraccion que representa la posicion actual: sin
        # restituirla, arrastrar el borde de la ventana da saltos en el texto
        # que se esta leyendo.


    def _wrap_estado(self, _evento=None) -> None:
        """La explicacion se envuelve al hueco que le deja el rotulo, medido.

        Se sale enseguida si el ancho no ha cambiado: cambiar `wraplength`
        cambia el alto de la etiqueta, que dispara otro `<Configure>` del
        panel, que volveria a entrar aqui. Sin la guarda es un bucle.
        """
        ancho = self._ancho_de_la_banda(self.panel_detalle)
        if ancho <= 1 or ancho == getattr(self, "_ancho_estado", 0):
            return
        self._ancho_estado = ancho
        libre = ancho - RELLENO * 2 - 14
        for et in (self.etiqueta_explicacion, self.etiqueta_hecha_con):
            try:
                et.configure(wraplength=max(240, libre))
            except tk.TclError:  # pragma: no cover
                return

    def _ancho_de_la_banda(self, panel) -> int:
        """A que ancho se envuelve lo que va en la banda.

        AL LADO, LO MANDA LA COLUMNA; ENCIMA, LO MANDA EL PANEL. Y esto no es
        un detalle: `columnconfigure(minsize=...)` pone un MINIMO, no un tope.
        Preguntandole al panel lo que mide, el panel contesta lo que le pide su
        contenido -730 px medidos, para una columna de 400- y se come la mitad
        de la respuesta. El ancho de la columna lateral es una decision, no una
        consecuencia: se impone envolviendo el texto a esa medida.
        """
        if self._lateral:
            return ANCHO_COLUMNA_LATERAL
        return panel.winfo_width()

    def _wrap_avisos(self, _evento=None) -> None:
        """Lo mismo para los avisos: se envuelven al ancho de su panel."""
        ancho = self._ancho_de_la_banda(self.panel_avisos)
        if ancho <= 1 or ancho == getattr(self, "_ancho_avisos", 0):
            return
        self._ancho_avisos = ancho
        for et in self.panel_avisos.winfo_children():
            try:
                et.configure(wraplength=max(200, ancho - RELLENO * 2 - 10))
            except tk.TclError:  # pragma: no cover
                return

    def _decidir_disposicion(self) -> None:
        """¿La banda al lado o encima? Lo dice el LARGO DE LA RESPUESTA.

        LAS DOS DISPOSICIONES GANAN EN CASOS DISTINTOS, y esta medido sobre
        seis respuestas reales:

            respuesta      apilado          al lado
            10 lineas      293 px en blanco  489
            17 lineas        7 px en blanco  224
            101 lineas     15 lineas visibles  22
            154 lineas     12 lineas visibles  21

        Con una respuesta larga, la banda encima se come el primer tercio de
        la pantalla y de la respuesta se ven 12 lineas de 154. Con una corta
        pasa lo contrario: al lado, la pagina se queda en 10 lineas de alto y
        debajo hay media pantalla vacia, que es la queja original.

        EL UMBRAL NO SE ELIGE, SE MIDE. Es «las lineas que caben en la
        pagina»: si la respuesta llena la columna de lectura entera, la
        lateral se usa toda y el alto que libera es alto ganado; si no llega,
        la lateral solo añade blanco. Aqui son 28 lineas, y cae dentro del
        hueco de 17 a 101 que los datos dejan libre, asi que ninguno de los
        seis lo decide a codazos.

        Y SE DECIDE UNA VEZ, AL PINTAR. Recalcularlo en cada `<Configure>`
        haria que una respuesta justo en la frontera cambiara de disposicion
        al arrastrar un pixel el borde de la ventana, que es peor que
        cualquiera de las dos.
        """
        alto_linea = self.fuente_texto.metrics("linespace") + INTERLINEA
        alto = self.lienzo_lectura.winfo_height()
        # SI EL LIENZO NO SE HA DIBUJADO AUN, NO SE DECIDE. Recien pintado
        # devuelve un alto de mentira -300 px, o 1- y entonces «caben» sale 9
        # en vez de 28 y una respuesta de 17 lineas se declara larga. Medido:
        # el margen del parrafo se calculaba con la disposicion contraria y el
        # texto salia a 145 px de margen en una pantalla sin columna lateral.
        # Vale mas quedarse con la decision anterior que decidir a ciegas.
        if alto < 200:
            return
        caben = max(1, alto // alto_linea)
        self._respuesta_larga = (
            getattr(self, "_lineas_de_respuesta", 0) >= caben)

    def _colocar_lateral(self, ancho: int) -> None:
        """La banda AL LADO de la respuesta, o encima si no cabe.

        AL LADO GANA ALTO SIN TOCAR LA MEDIDA DE LECTURA. Los 876 px de
        columna se quedan igual; lo que cambia es que el estado, el aporte y
        los avisos dejan de comerse la franja de arriba y se van al hueco que
        ya estaba en blanco.

        Y LOS AVISOS VAN ARRIBA DEL TODO. Son lo que puede invalidar la
        respuesta: apilados iban primero por eso mismo, y al pasar a un lado
        no pueden quedar por debajo del aporte, que es informacion de segundo
        orden. En la columna: avisos, luego el detalle del estado, luego lo
        que ha añadido el criterio.
        """
        # DOS CONDICIONES, Y LAS DOS TIENEN QUE CUMPLIRSE. El ancho dice si
        # CABE la columna; el largo de la respuesta dice si COMPENSA.
        lateral = ancho >= ANCHO_LATERAL and getattr(
            self, "_respuesta_larga", False)
        if lateral == self._lateral:
            return
        self._lateral = lateral
        self.banda.grid_forget()
        self.caja_texto.grid_forget()
        if lateral:
            self.pagina.columnconfigure(1, minsize=ANCHO_COLUMNA_LATERAL,
                                        weight=0)
            self.caja_texto.grid(row=0, column=0, sticky="new")
            self.banda.grid(row=0, column=1, sticky="new",
                            padx=(HUECO, 0))
        else:
            self.pagina.columnconfigure(1, minsize=0, weight=0)
            self.banda.grid(row=0, column=0, sticky="ew")
            self.caja_texto.grid(row=1, column=0, sticky="ew",
                                 pady=(AIRE, 0))
        # La banda cambia de ancho, asi que sus dos columnas se recolocan y
        # los textos se vuelven a envolver.
        self._dos_columnas = None
        self._ancho_estado = self._ancho_avisos = 0
        self._colocar_banda(self.banda.winfo_width() or ancho)
        self.raiz.after_idle(self._wrap_estado)
        self.raiz.after_idle(self._wrap_avisos)
        # Y EL MARGEN DEL PARRAFO DEPENDE DE ESTO, asi que hay que rehacerlo.
        # Sin esto, al cambiar la disposicion el texto se queda con el margen
        # de la anterior: centrado para una columna que ya no esta, o al reves.
        self._ancho_previo = 0     # para que `_reajustar` no se salte el turno
        self.raiz.after_idle(self._reajustar)

    def _colocar_banda(self, ancho: int) -> None:
        """Una columna o dos, segun quepa. Se recoloca solo al cambiar.

        Se guarda la decision anterior y solo se toca el `grid` cuando cambia:
        recolocar en cada pixel del arrastre se ve a simple vista.
        """
        # En la columna de al lado nunca caben dos: es estrecha por
        # definicion, y ahi el orden lo manda el riesgo, no el hueco.
        dos = ancho >= ANCHO_DOS_COLUMNAS and not self._lateral
        if dos == self._dos_columnas:
            return
        self._dos_columnas = dos
        self.columna_izq.grid_forget()
        self.columna_der.grid_forget()
        if dos:
            # `uniform` NO es decorativo. Sin el, `weight` reparte solo el
            # SOBRANTE por encima de lo que cada columna pide, asi que una
            # columna que pide poco se queda pequeña para siempre: los avisos
            # se envolvian a 209 px dentro de una banda de 1.650. Con
            # `uniform`, las dos columnas se reparten el ancho 6 a 4 de verdad.
            self.banda.columnconfigure(0, weight=6, uniform="banda")
            self.banda.columnconfigure(1, weight=4, uniform="banda")
            self.columna_izq.grid(row=0, column=0, sticky="nsew")
            self.columna_der.grid(row=0, column=1, sticky="nsew",
                                  padx=(HUECO2, 0))
        else:
            self.banda.columnconfigure(0, weight=1, uniform="")
            self.banda.columnconfigure(1, weight=0, uniform="")
            # LOS AVISOS -`columna_der`- PRIMERO. Son lo que puede invalidar
            # la respuesta; el detalle del estado y el aporte van detras.
            self.columna_der.grid(row=0, column=0, sticky="ew")
            self.columna_izq.grid(row=1, column=0, sticky="ew",
                                  pady=(AIRE + 2, 0))

    def _columna(self) -> None:
        """Mete lo que se acaba de escribir dentro de la columna de lectura."""
        self.texto.tag_add("columna", "1.0", "end")
        self.texto.tag_lower("columna")

    # ------------------------------------------------------------ arranque

    def _arrancar_motor(self) -> None:
        """Carga corpus y motor, y PASE LO QUE PASE lo dice.

        Envuelve a `_arrancar` entero. Lo de dentro ya explicaba sus fallos
        conocidos -corpus, credencial, tkinter-, pero cualquier OTRA excepcion
        salia por `raiz.after`, Tk imprimia la traza y la ventana se quedaba
        abierta, con los dos botones grises y sin una palabra.

        Y EN WINDOWS NI LA TRAZA: se abre con `pythonw.exe`, que no tiene
        consola ni stderr. Por eso el mismo fallo se veia en el Mac -en la
        terminal- y era invisible en la oficina. La asimetria no estaba en el
        codigo: estaba en quien podia leer el error.
        """
        try:
            self._arrancar()
        except Exception as e:                   # noqa: BLE001
            self._bloquear(
                "El agente no ha podido prepararse. Haz doble clic en "
                "«comprobar_equipo» y enséñale a Emili lo que salga.",
                f"{type(e).__name__}: {e}")
            # Y AL DISCO, que es lo unico que se puede leer despues cuando la
            # ventana se abre sin consola.
            try:
                import traceback
                fallo = RAIZ / "datos" / "arranque_fallido.txt"
                fallo.parent.mkdir(parents=True, exist_ok=True)
                fallo.write_text(traceback.format_exc(), encoding="utf-8")
            except Exception:                    # noqa: BLE001
                pass

    def _arrancar(self) -> None:
        """Carga corpus y motor. Si falla, se dice en cristiano y se bloquea."""
        self._escribir_texto([("Cargando la ley y el reglamento...\n", "apagado")])
        try:
            self.ix, self.grafo = fase4.cargar_corpus()
        except Exception as e:  # noqa: BLE001
            # EL CORPUS SI BLOQUEA, Y TIENE QUE HACERLO: sin la ley no hay
            # nada que responder, y rehacerlo son minutos bajando del BOE, no
            # dos segundos. Pero DECIR «avisa a Emili» cuando el propio
            # programa lo baja solo es mandar a alguien a esperar por gusto:
            # se dice que se cierre y se vuelva a abrir, que es lo que lo
            # arregla.
            self._bloquear(
                "Falta el texto de las normas. Cierra esta ventana y vuelve "
                "a abrir el agente: se baja solo y tarda unos minutos. Si "
                "después de eso sigue igual, avisa a Emili.",
                str(e),
            )
            return

        motor, err = fase4.preparar_motor(self.motor_nombre, silencioso=True)
        if motor is None:
            # SI LO QUE FALLA ES LA CREDENCIAL, HAY BOTON. Hasta ahora la
            # ventana decia lo que pasaba y ahi se acababa: para arreglarlo
            # habia que abrir una terminal, y la oficina se quedaba parada
            # hasta que alguien me escribiera. El dialogo que la pide ya
            # existe -es el mismo del primer arranque- y lo unico que faltaba
            # era poder volver a el.
            self._bloquear(en_cristiano(err), err)
            if _es_de_credencial(err):
                self._ofrecer_cambiar_clave()
            return
        self.motor = motor

        if not motor.es_modelo_real:
            self.mostrar_cinta(
                "MODO DE PRUEBA: las respuestas las fabrica una regla fija, "
                "NO son una consulta real.")
        self._escribir_texto([
            ("Escribe tu duda, pon el año del caso y pulsa Consultar.\n\n",
             "apagado"),
            # NI UNA PALABRA A MANO SOBRE LO QUE CUBRE. Aqui ponia «responde
            # solo con la Ley y el Reglamento del IVA» con trece normas y
            # cuatro impuestos cargados. El detalle por impuesto esta en «Qué
            # hay dentro»; aqui va el titular, con sus cifras.
            (f"El primer botón responde con la ley: {len(self.ix.docs)} "
             f"artículos de {len(self.ix.rutas)} normas. El segundo añade "
             f"además el criterio guardado; en «Qué hay dentro» está de qué "
             f"impuestos y cuánto.\n", "apagado"),
        ])
        self.pie.configure(
            text=f"{len(self.ix.docs)} preceptos cargados  ·  "
                 f"cada consulta queda guardada en el expediente"
        )
        # DE QUE HAY CRITERIO, CONTADO DE LA DESPENSA. Nunca escrito.
        from agente_fiscal import cobertura as _C
        self.pie_criterio.configure(
            text=f"{PIE_CRITERIO}. {_C.frase(self.ix)}")

        # Y SI LA HOJA SE HA QUEDADO VIEJA, SE REHACE. Ya hay corpus, asi que
        # aqui si se puede contar la despensa y ponerla al dia. Antes esto
        # enseñaba un aviso diciendo que la rehiciera una persona: mandar a
        # alguien a ejecutar un comando que el programa puede ejecutar solo es
        # la misma pereza que bloquear por un derivado.
        try:
            hecho = CONF.asegurar(self.ix)
            if hecho:
                self.mostrar_cinta(hecho + " Imprímela otra vez si la tienes "
                                          "en la mesa.")
        except Exception:  # noqa: BLE001 - la guia nunca impide consultar
            pass

        # ------------------------------------------------------- LA COLA
        #
        # LO ULTIMO DEL ARRANQUE, Y POR DETRAS. La ventana ya funciona cuando
        # esto empieza: el motor esta listo, el texto escrito y los botones
        # vivos. Si la cola tardara o fallara, el gestor ya puede consultar.
        #
        # SIN PROGRAMADOR DE TAREAS. El portatil de la oficina se apaga por la
        # noche, asi que una tarea programada de madrugada no se ejecutaria
        # nunca. Se vacia AL ABRIR, que es el unico momento en que el equipo
        # esta encendido con seguridad.
        #
        # PRIMERO SE DICE LO QUE YA HAY, y luego se va a buscar: el aviso de lo
        # que entro anoche es de la vez anterior y no depende de que esta salga
        # bien.
        try:
            from agente_fiscal import cola as _COLA
            traido = _COLA.recien_bajado()
            if traido["articulos"]:
                self.mostrar_cinta(
                    f"Encontré criterio sobre {traido['articulos']} "
                    f"artículo(s) que preguntasteis: "
                    f"{traido['consultas']} consulta(s) nuevas. "
                    f"Ya están en el segundo botón.")
            silencio = _COLA.aviso_de_silencio()
            if silencio:
                self.mostrar_cinta(silencio)
        except Exception:  # noqa: BLE001 - la cola nunca impide consultar
            pass
        self._vaciar_cola_por_detras()
        self._reajustar()
        self._revisar_boton()

    def _bloquear(self, frase: str, detalle_tecnico: str = "") -> None:
        """Deja la ventana inservible pero explicada. Nunca con una traza."""
        self.boton.configure(state="disabled")
        # LOS DOS BOTONES, NO UNO. Aqui solo se apagaba el primero: el de
        # criterio se quedaba encendido sobre un motor que no existe, asi que
        # la ventana decia «no se puede consultar» y a la vez ofrecia un boton
        # que se podia pulsar. Se apagan juntos porque juntos se encienden.
        if getattr(self, "boton_criterio", None) is not None:
            self.boton_criterio.configure(state="disabled")
        self._pintar_estado("NO SE PUEDE CONSULTAR", frase,
                            EST.NO_ENCONTRADO)
        self._escribir_texto([(frase + "\n", "titulo")])
        # El detalle tecnico va al log de la terminal, JAMAS a la pantalla.
        if detalle_tecnico:
            print(f"[arranque] {detalle_tecnico}", file=sys.stderr)

    # -------------------------------------------------------------- estado

    def _revisar_boton(self) -> None:
        """Los botones solo se activan con duda Y ejercicio validos.

        Los dos van juntos: si se puede consultar, se puede con cualquiera de
        los dos. Cual se pulsa es del que pregunta.
        """
        if self.trabajando:
            return
        if self.motor is None:
            # UN BOTON GRIS SIN EXPLICACION ES EL PEOR MENSAJE POSIBLE: quien
            # lo mira no sabe si ha hecho algo mal o si la herramienta esta
            # rota, y no tiene nada que hacer.
            #
            # Aqui se volvia en silencio, asi que si el arranque no llegaba a
            # dejar motor -por lo que fuera- la ventana se quedaba con los dos
            # botones apagados y sin una palabra. En Mac se veia la causa en la
            # terminal; en Windows se abre con `pythonw.exe`, QUE NO TIENE
            # CONSOLA NI stderr, asi que no se veia en ningun sitio. El mismo
            # fallo, mudo en un sistema y explicado en el otro.
            self._pintar_estado(
                "NO SE PUEDE CONSULTAR",
                "El agente no ha terminado de prepararse.", EST.NO_ENCONTRADO)
            self.mostrar_cinta(
                "Los botones están apagados porque el agente no ha podido "
                "prepararse. Haz doble clic en «comprobar_equipo» y enséñale "
                "a Emili lo que salga.")
            return
        duda = self.caja.get("1.0", "end").strip()
        # LA REGLA DEL AÑO, UNA SOLA VEZ. Aqui habia una TERCERA copia escrita
        # a mano -isdigit y el rango-, aparte de la de `leer_ejercicio` y la
        # que tenia `fase4.main`. Coincidian hoy, que es lo que hace peligroso
        # este patron: coinciden hasta que alguien arregla una y no las otras.
        año, _motivo = AN.leer_ejercicio(self.ejercicio.get())
        cabe = self._avisar_del_largo(duda)
        estado = "normal" if (duda and año is not None and cabe) else "disabled"
        self.boton.configure(state=estado)
        if self.boton_criterio is not None:
            self.boton_criterio.configure(state=estado)

    def _caja_cambiada(self, _evento=None) -> None:
        """Cualquier cambio en la caja, incluido pegar con el raton."""
        self.caja.edit_modified(False)
        self._revisar_boton()

    def _avisar_del_largo(self, duda: str) -> bool:
        """Enseña el aviso de largo si toca. Devuelve si la duda cabe.

        TRES TRAMOS, no dos. Callado mientras hay sitio de sobra; un aviso
        tranquilo cuando se acerca -para que no pille por sorpresa a mitad de
        pegar-; y el motivo cuando ya no cabe.

        Y SE DICE QUE ESTO SE VA A CAER. El tope no es una manía: es que hoy
        la pregunta viaja al modelo tal cual, y un escrito entero cuesta
        dinero y da peor resultado que la duda concreta. Cuando la herramienta
        sepa leer un PDF, la restriccion desaparece. Sin esa frase parece una
        limitacion tonta, y una limitacion que parece tonta se salta.
        """
        n = len(duda)
        if n > fase4.TOPE_PREGUNTA:
            self.aviso_largo.configure(
                text=f"Son {n:,} caracteres y caben {fase4.TOPE_PREGUNTA:,}. "
                     f"Esto pasa al pegar un requerimiento entero: pega solo "
                     f"la parte que pregunta, o resúmela en unas líneas. "
                     f"(Cuando la herramienta sepa leer el PDF entero, esto "
                     f"dejará de hacer falta.)".replace(",", "."),
                fg=TINTA)
            self.aviso_largo.pack(fill="x", pady=(AIRE, 0))
            return False
        if n > fase4.TOPE_PREGUNTA * 0.75:
            self.aviso_largo.configure(
                text=f"Vas por {n:,} caracteres de {fase4.TOPE_PREGUNTA:,}."
                     .replace(",", "."),
                fg=TINTA2)
            self.aviso_largo.pack(fill="x", pady=(AIRE, 0))
            return True
        self.aviso_largo.pack_forget()
        return True

    # -------------------------------------------------------------- lanzar

    def _lanzar(self, con_criterio: bool = False) -> None:
        duda = self.caja.get("1.0", "end").strip()
        # Sin `int()` a pelo sobre lo que hay en la caja: hoy no puede fallar
        # porque el boton solo se enciende con un año valido, pero eso es
        # fiarse del estado de OTRO widget. Se pregunta a quien manda.
        ejercicio, _motivo = AN.leer_ejercicio(self.ejercicio.get())
        if ejercicio is None:      # el boton no deberia estar encendido
            self._revisar_boton()
            return
        self.trabajando = True
        self.con_criterio = con_criterio
        self.boton.configure(state="disabled", text="Consultando...")
        if self.boton_criterio is not None:
            self.boton_criterio.configure(state="disabled")
        self.boton_copiar.configure(state="disabled")
        self.copiado.configure(text="")
        self.respuesta_actual = ""
        self.panel_avisos.pack_forget()
        self.panel_aporte.pack_forget()
        for w in list(self.panel_avisos.winfo_children()) + \
                list(self.panel_aporte.winfo_children()):
            w.destroy()
        self.etiqueta_estado.grid_forget()
        self.etiqueta_explicacion.grid_forget()
        self.etiqueta_hecha_con.grid_forget()
        self._escribir_texto([])
        self.paso.pack(side="left")
        self.barra.pack(side="right", fill="x", expand=True, padx=(12, 0))
        self.barra.start(12)
        self.paso.configure(text="Preparando la consulta...")

        comunidad = self.comunidad.get().strip()
        hilo = threading.Thread(target=self._trabajar,
                                args=(duda, ejercicio, con_criterio,
                                      comunidad),
                                daemon=True)
        hilo.start()

    def _trabajar(self, duda: str, ejercicio: int,
                  con_criterio: bool = False, comunidad: str = "") -> None:
        """Corre FUERA del hilo de la ventana: tkinter no es reentrante."""
        import contextlib
        import io

        def progreso(texto: str) -> None:
            self.avisos.put(("paso", texto))

        try:
            # La salida por pantalla del motor no se pierde: se manda a la
            # terminal, que es donde se puede leer si hace falta depurar.
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                res = fase4.consultar(duda, ejercicio, self.motor, self.ix,
                                      self.grafo, progreso=progreso,
                                      con_criterio=con_criterio,
                                      comunidad=comunidad)
            print(buf.getvalue())
            self.avisos.put(("hecho", res))
        except Exception:  # noqa: BLE001
            # Cualquier cosa inesperada: la traza va a la terminal, y a la
            # pantalla una frase. Nunca al reves.
            traceback.print_exc()
            self.avisos.put(("roto", FALLO_GENERICO))

    # ------------------------------------------------------- cola de avisos

    def _vaciar_avisos(self) -> None:
        try:
            while True:
                clase, dato = self.avisos.get_nowait()
                if clase == "paso":
                    self.paso.configure(text=dato)
                elif clase == "hecho":
                    self._terminar(dato)
                elif clase == "roto":
                    self._terminar_roto(dato)
                elif clase == "cliente":
                    self._llego_para_cliente(dato)
        except queue.Empty:
            pass
        self.raiz.after(80, self._vaciar_avisos)

    def _parar_barra(self) -> None:
        self.barra.stop()
        self.barra.pack_forget()
        self.paso.pack_forget()
        self.trabajando = False
        self.boton.configure(text=BOTON_LEY)
        if self.boton_criterio is not None:
            self.boton_criterio.configure(text=BOTON_CRITERIO)
        self._revisar_boton()

    def _escribir_para_cliente(self) -> None:
        """La misma respuesta, escrita para mandarsela al cliente.

        Va en un hilo porque es una llamada al modelo y la ventana no se puede
        quedar congelada. Mientras tanto el boton se apaga: dos pulsaciones
        seguidas serian dos llamadas para lo mismo.

        SI EL VERIFICADOR LA RECHAZA NO ES UNA AVERIA, ES LA SALVAGUARDA
        FUNCIONANDO, y tiene que leerse asi. La respuesta buena SIGUE EN
        PANTALLA y no se ha perdido nada: lo unico que ha pasado es que la
        version bonita cambiaba una cita, y por eso no se enseña. Un mensaje de
        error aqui haria pensar que algo esta roto cuando lo que ha ocurrido es
        justo lo que tiene que ocurrir.
        """
        import threading

        if self.trabajando or not getattr(self, "traza_actual", ""):
            return
        self.trabajando = True
        self.boton_cliente.configure(state="disabled",
                                     text="Escribiendo...")
        self.mostrar_cinta("Escribiendo la misma respuesta para el cliente. "
                           "La de ahora no se pierde.")

        def trabajar() -> None:
            try:
                r = fase4.otra_forma(self.traza_actual, self.ejercicio_usado,
                                     self.motor, self.ix)
            except Exception as e:               # noqa: BLE001
                r = {"respuesta": "", "motivo": f"{type(e).__name__}: {e}",
                     "veredicto": ""}
            # POR LA COLA, NO POR `after`. Aqui habia `self.raiz.after(0, ...)`
            # llamado DESDE EL HILO, y tkinter no lo admite: revienta con «main
            # thread is not in main loop», el aviso nunca llega y el boton se
            # queda en «Escribiendo...» para siempre. La reescritura si se
            # hacia y se guardaba; lo que no volvia era la respuesta.
            #
            # La ventana ya tiene una cola para esto -`self.avisos`, que vacia
            # el bucle principal cada 80 ms- y es por lo que existe. Se usa esa.
            self.avisos.put(("cliente", r))

        threading.Thread(target=trabajar, daemon=True).start()

    def _llego_para_cliente(self, r: dict) -> None:
        self.trabajando = False
        self.boton_cliente.configure(text="Escribirlo para el cliente",
                                     state="normal")
        if r.get("respuesta"):
            self.respuesta_actual = r["respuesta"]
            self._escribir_texto([
                ("Escrito para el cliente\n", "titulo"),
                ("Misma respuesta y mismas citas, en otro tono. Comprobada "
                 "igual que la anterior.\n\n", "apagado"),
                (r["respuesta"], "cuerpo"),
            ])
            self.mostrar_cinta("Listo. «Copiar respuesta» se lleva esta.")
            return

        # RECHAZADA: la de antes sigue ahi, y se dice como lo que es.
        self.mostrar_cinta(
            "La versión para el cliente cambiaba una cita al reescribirla, "
            "así que no se enseña. La respuesta que tienes delante sigue "
            "siendo la buena y no se ha perdido nada.")

    def _sin_nada_que_copiar(self) -> None:
        """Deja el portapapeles fuera de juego. Se llama SIEMPRE que no hay
        texto verificado en pantalla.

        `_lanzar` ya lo limpia al empezar cada consulta, asi que hoy no se
        puede llegar aqui con una respuesta vieja dentro. Se hace igual: la
        regla de que no salga texto sin verificar no puede depender de que
        alguien se acuerde de limpiar en otro sitio. Copiar es ensenar.
        """
        self.respuesta_actual = ""
        self.traza_actual = ""
        self.ejercicio_usado = None
        self.boton_copiar.configure(state="disabled")
        # Y EL DE REESCRIBIR CON EL, porque dependen de lo mismo: que haya una
        # respuesta aceptada delante. Si no hay que copiar, no hay que
        # reescribir.
        if getattr(self, "boton_cliente", None) is not None:
            self.boton_cliente.configure(state="disabled")
        self.copiado.configure(text="")

    def _terminar_roto(self, frase: str) -> None:
        self._parar_barra()
        self._sin_nada_que_copiar()
        self._mostrar("respuesta")
        self._pintar_estado("NO SE HA PODIDO CONSULTAR", frase,
                            EST.NO_ENCONTRADO)
        self._escribir_texto([(frase + "\n", "titulo")])


    # ------------------------------------------------- que hay dentro

    def _abrir_estado(self, _evento=None) -> None:
        """LA PANTALLA DE ESTADO, DENTRO DE LA APP.

        Es lo que se enseña para decidir si se enciende el criterio, asi que
        tiene que caber de una vez y leerse sin que nadie la explique. Numeros
        y frases cortas; ni una ruta de fichero, ni una variable de entorno.
        """
        from agente_fiscal import dgt as _D
        from agente_fiscal import teac as _T

        v = tk.Toplevel(self.raiz)
        v.title("Qué hay dentro")
        v.configure(bg=PAPEL)
        # Abre segun la pantalla, y con barra: el contenido pide 949 px y
        # antes abria a 620. Se salia por 329 px y no habia forma de llegar.
        alto = min(940, int(v.winfo_screenheight() * 0.86))
        v.geometry(f"720x{alto}")
        v.minsize(620, 460)
        caja_v, marco, lienzo_v = self._desplazable(v)
        caja_v.pack(fill="both", expand=True)
        marco.configure(padx=MARGEN, pady=MARGEN)

        def titulo(texto):
            tk.Label(marco, text=texto, bg=PAPEL, fg=TINTA3,
                     font=self.fuente_seccion, anchor="w").pack(
                         fill="x", pady=(HUECO, AIRE))

        def caja():
            c = tk.Frame(marco, bg=PAPEL2, highlightthickness=1,
                         highlightbackground=FILETE, pady=AIRE)
            c.pack(fill="x")
            return c

        def linea(padre, izq, der="", fuerte=False):
            f = tk.Frame(padre, bg=PAPEL2)
            f.pack(fill="x", padx=RELLENO, pady=3)
            tk.Label(f, text=izq, bg=PAPEL2, fg=TINTA,
                     font=(self.fuente_titular if fuerte else self.fuente),
                     anchor="w", justify="left", wraplength=430).pack(side="left")
            if der:
                # La cifra en monoespaciada y en lila: es lo que se viene a
                # mirar, y asi las columnas quedan alineadas de verdad.
                tk.Label(f, text=der, bg=PAPEL2, fg=ENLACE,
                         font=self.fuente_referencia, anchor="e").pack(side="right")

        tk.Label(marco, text="D E N T R O   D E   L A   H E R R A M I E N T A",
                 bg=PAPEL, fg=TINTA3, font=self.fuente_rotulo,
                 anchor="w").pack(fill="x")
        tk.Label(marco, text="Qué hay dentro", bg=PAPEL,
                 fg=TINTA, font=self.fuente_titular, anchor="w"
                 ).pack(fill="x", pady=(AIRE, 0))

        # --- las normas ---
        # AGRUPADO POR IMPUESTO, NO UNA LINEA POR CUERPO.
        #
        # Con cuatro normas cabia; con diez cuerpos la pantalla se fue a 45
        # lineas y dejo de caber de una vez. Subir el tope no arregla nada:
        # crecia UNA LINEA POR CUERPO, asi que con doce tampoco cabria.
        #
        # Agrupado crece una linea por IMPUESTO, que es como piensa quien mira:
        # nadie viene a saber cuantos cuerpos normativos hay, viene a saber si
        # su impuesto esta dentro.
        #
        # TERCER CRECIMIENTO: SE PLIEGA, NO SE DESPLAZA. Con doce normas la
        # pantalla volvio a pasar de 40 lineas. Subir el tope no arregla nada
        # -es la tercera vez- y desplazar tampoco, aunque esta ventana YA se
        # desplaza: esta pantalla existe para contestar UNA pregunta -«¿esta mi
        # impuesto dentro?»- y una respuesta que hay que ir a buscar bajando ya
        # no es una respuesta de un vistazo.
        #
        # Plegado, la lista de normas concretas se esconde detras de un boton.
        # Asi crece UNA linea por impuesto en vez de tres, y el detalle sigue
        # estando entero para quien lo quiera. El desplazamiento se queda donde
        # debe estar: de red por si acaso, no como forma de leer.
        titulo(f"NORMAS CARGADAS · lo que mira «{BOTON_LEY}»")
        c = caja()
        total = 0
        if self.ix is not None:
            from agente_fiscal.normas import _acronimo, es_materia_de_impuesto
            grupos: dict = {}
            for cuerpo in self.ix.normas.cuerpos.values():
                n = sum(1 for d in self.ix.docs
                        if d.registro.get("cuerpo_clave") == cuerpo.clave)
                total += n
                # LA MATERIA, SIN EL TIPO DE NORMA DELANTE. La del texto
                # refundido del ITP es «Ley del Impuesto sobre Transmisiones
                # ...», asi que en crudo salia como un GRUPO APARTE, duplicando
                # el de su propio impuesto y con un rotulo que empieza por «Ley
                # del». Se normaliza igual que en `es_materia_de_impuesto`.
                from agente_fiscal.normas import _solo_la_materia
                materia = (cuerpo.materia or "").strip()
                if es_materia_de_impuesto(materia):
                    limpia = _solo_la_materia(materia)
                    # Se recupera la capitalizacion del original: `limpia` va
                    # en minusculas y esto es un rotulo de pantalla.
                    corte = len(materia) - len(limpia)
                    bonita = materia[corte:] if corte > 0 else materia
                    clave = f"{bonita} ({_acronimo(materia)})"
                else:
                    clave = "Normas generales"
                g = grupos.setdefault(clave, {"n": 0, "normas": []})
                g["n"] += n
                nombre = cuerpo.etiqueta.split(",")[0]
                if nombre not in g["normas"]:
                    g["normas"].append(nombre)
            # UNA LINEA POR IMPUESTO, CON LO QUE MIRA CADA BOTON.
            #
            # Habia DOS tablas -las normas aqui, el criterio mas abajo- y las
            # dos nombraban los mismos impuestos, una debajo de otra. Con siete
            # impuestos eso son catorce lineas para contestar dos preguntas que
            # se leen mejor juntas: «que ley tengo de esto» y «cuanto criterio».
            # Y las dos CRECEN con cada siembra y cada ingesta, asi que la
            # pantalla se pasaba de largo sola. Es la cuarta vez que crece; la
            # respuesta sigue siendo plegar, no subir el tope.
            # SE EMPAREJA POR CODIGO DE IMPUESTO, no por el nombre que se
            # pinta: «IVA» no esta dentro de «Impuesto sobre el Valor Añadido»,
            # y emparejando por texto la cifra se quedaba fuera justo en los
            # dos impuestos mas grandes.
            from agente_fiscal import cobertura as _C
            crudo = _C.resumen(self.ix) if self.ix else {}
            criterio = {k: v["dgt"] + v["teac"] for k, v in crudo.items()}
            self._detalle_normas = []
            for nombre, g in sorted(grupos.items(),
                                    key=lambda kv: (kv[0] == "Normas generales",
                                                    kv[0])):
                codigo = (nombre.rsplit("(", 1)[-1].rstrip(")")
                          if nombre.endswith(")") else "")
                suyo = criterio.get(codigo)
                if nombre == "Normas generales":
                    suyo = criterio.get(_C.GENERAL)
                linea(c, nombre, f"{g['n']} artículos"
                      + (f"  ·  {suyo} de criterio" if suyo else ""))
                sub = tk.Label(c, text="   " + " · ".join(g["normas"]),
                               bg=PAPEL2, fg=TINTA3, font=self.fuente_menuda,
                               anchor="w", justify="left", wraplength=520,
                               padx=RELLENO)
                self._detalle_normas.append(sub)
            linea(c, "", f"{total} en total")

            # EL PLIEGUE. Empieza cerrado: quien abre esta pantalla viene a ver
            # si su impuesto esta, no como se llama cada real decreto.
            # ACTUALIZAR LAS NORMAS, SIN TERMINAL. El corpus es una foto y
            # envejece; quien lo nota es quien consulta, y no tiene por que
            # abrir una consola para arreglarlo.
            self._boton_actualizar = ttk.Button(
                c, text="Actualizar las normas desde el BOE",
                style="Discreto.TButton", command=self._actualizar_corpus)
            self._boton_actualizar.pack(anchor="w", padx=RELLENO,
                                        pady=(AIRE, 0))
            self._pinchable(self._boton_actualizar)
            edad = _FR.edad_del_corpus(RAIZ / "datos" / "corpus")
            if edad.get("dias") is not None:
                tk.Label(c, text=(
                    f"   Bajada el {edad['mas_vieja'].strftime('%d/%m/%Y')}"
                    f"  ·  {edad['dias']} días"), bg=PAPEL2,
                    fg=(TINTA if edad["dias"] >= _FR.DIAS_SOSPECHOSO
                        else TINTA3),
                    font=self.fuente_menuda, anchor="w", padx=RELLENO
                ).pack(fill="x")

            self._normas_abiertas = False
            boton_pliegue = ttk.Button(c, style="Discreto.TButton")

            def plegar() -> None:
                self._normas_abiertas = not self._normas_abiertas
                for w in self._detalle_normas:
                    if self._normas_abiertas:
                        w.pack(fill="x")
                    else:
                        w.pack_forget()
                boton_pliegue.configure(
                    text=("Ocultar las normas concretas"
                          if self._normas_abiertas
                          else f"Ver las {len(self.ix.rutas)} normas, una a una"))

            boton_pliegue.configure(command=plegar)
            plegar()
            plegar()          # deja el rotulo puesto y el detalle cerrado
            boton_pliegue.pack(anchor="w", padx=RELLENO, pady=(AIRE, 0))
            self._pinchable(boton_pliegue)
            self.boton_pliegue_normas = boton_pliegue

            # QUE EL CORPUS ESTA ENTERO, DICHO EN LA PANTALLA QUE SE ENSEÑA
            # PARA DUDAR DE UNA RESPUESTA. Un corpus truncado no da error: da
            # respuestas peores en silencio. Quien venga aqui a preguntarse
            # «¿esto lo tiene?» tiene que poder ver que si, y que se ha
            # comprobado, no que se supone. Ver `sellos`.
            from agente_fiscal import sellos as _S
            est = _S.estado(self.ix.rutas)
            tk.Label(c, text=("✓  " if not est["problemas"] and est["sellado"]
                              else "·  ") + est["frase"],
                     bg=PAPEL2,
                     fg=(TINTA2 if est["sellado"] and not est["problemas"]
                         else TINTA),
                     font=self.fuente_menuda, anchor="w", justify="left",
                     wraplength=560, padx=RELLENO,
                     # `pady` de un WIDGET es UNA distancia. El par va en el
                     # `pack`. Es la cuarta vez que caigo en esto.
                     ).pack(fill="x", pady=(HUECO2 - 4, 0))
        else:
            linea(c, "cargando...")

        # --- la copia local ---
        # EL TITULO DICE QUE ES CADA CIFRA. Sin esto, «IVA 653» se lee como
        # «hay 653 consultas de IVA», y no es eso: son 653 documentos que
        # HABLAN de IVA, y uno que cita la Ley del IVA y la LGT esta en las dos
        # filas. La suma de la columna es mayor que el numero de documentos, y
        # tiene que ser asi: para quien pregunta de IVA, esa consulta es
        # criterio de IVA. Lo que no puede es leerse mal.
        titulo(f"DE QUÉ HABLA EL CRITERIO GUARDADO · lo que añade "
               f"«{BOTON_CRITERIO}»")
        c = caja()
        # DE QUE HAY, POR IMPUESTO Y CONTADO.
        #
        # Antes habia tres cifras -consultas de la DGT, doctrina del TEAC,
        # resoluciones de los TEAR- y debajo una frase fija diciendo que todo
        # era de IVA. Las tres cifras seguian siendo ciertas y la frase no, y
        # es la frase lo que la gente lee para decidir si pulsa el segundo
        # boton. Ahora es una sola tabla, por impuesto, contada de la copia
        # local: dice lo mismo que las tres cifras -la suma- y ademas lo que
        # aquellas no decian.
        consultas = len(list(_D.DIR_CONSULTAS.glob("*.json"))) \
            if _D.DIR_CONSULTAS.is_dir() else 0
        todas = _T.CacheTEAC().todas()
        if self.ix is not None:
            from agente_fiscal import cobertura as _C
            filas = _C.por_impuesto(self.ix)
            if not filas:
                linea(c, "todavía no hay nada guardado")
            # LOS IMPUESTOS YA ESTAN ARRIBA, uno por linea, con su cifra de
            # criterio al lado de la de articulos. Repetirlos aqui era decir lo
            # mismo dos veces y hacer crecer la pantalla el doble de rapido.
            linea(c, "Consultas de la Dirección General de Tributos "
                     "y Doctrina del TEAC y tribunales regionales",
                  f"{consultas} + {len(todas)}")
            # Y LA CUENTA QUE CUADRA LA COLUMNA. La suma de arriba es mayor
            # que esto, y aqui se ve por que.
            distintos, varios = _C.documentos(self.ix)
            linea(c, f"de ellos se encuentran, y {varios} hablan de más de "
                     f"un impuesto", f"{distintos}")
        else:
            linea(c, "cargando...")
        tk.Label(c, text=AVISO_DESPENSA, bg=PAPEL2, fg=TINTA2,
                 font=self.fuente_menuda, anchor="w", justify="left",
                 wraplength=560, padx=RELLENO, pady=HUECO2 - 4).pack(fill="x")

        # AQUI HUBO DOS BLOQUES QUE YA NO HACEN FALTA.
        #
        # Primero «LO QUE CUESTA CADA CONSULTA», con los dos precios: se quito
        # porque el gasto esta asumido y verlo solo conseguia que alguien
        # pulsara el barato cuando necesitaba el otro.
        #
        # Y despues «QUÉ MIRA CADA BOTÓN», que lo sustituyo. Tambien sobra: la
        # tabla de arriba dice de que hay criterio Y CUANTO, que es lo mismo
        # pero con la cifra, y el pie del segundo boton lo repite en la
        # pantalla de consultar. Tres sitios diciendo lo mismo son tres sitios
        # donde uno se puede quedar viejo.

        # --- el canario ---
        titulo("LAS FUENTES, AHORA MISMO")
        c = caja()
        self._estado_fuentes = {}
        for nombre, mod in (("Tributos (consultas de la DGT)", _D),
                            ("DYCTEA (resoluciones)", _T)):
            viva, motivo = mod.fuente_viva()
            texto = ("responde" if viva else
                     f"sin comprobar hoy" if "no se ha comprobado" in motivo
                     else "no responde")
            f = tk.Frame(c, bg=PAPEL2)
            f.pack(fill="x", padx=RELLENO, pady=3)
            tk.Label(f, text=nombre, bg=PAPEL2, fg=TINTA, font=self.fuente,
                     anchor="w").pack(side="left")
            et = tk.Label(f, text=texto, bg=PAPEL2,
                          fg=(ENLACE if viva else TINTA3),
                          font=self.fuente_referencia, anchor="e")
            et.pack(side="right")
            self._estado_fuentes[nombre] = et

            # EL CERTIFICADO, DONDE PASA LA GENTE. Ya existia
            # `fuente_web.dias_de_certificado`, pero solo lo llamaban los
            # guiones de consola: la comprobacion solo servia si alguien se
            # acordaba de ejecutarla, y quien tiene que acordarse suele estar
            # de viaje justo ese mes. El de PETETE caduca el 26/09.
            #
            # SE AVISA CON MARGEN Y SE DICE QUE HACER, no solo que caduca: un
            # aviso que da una fecha y ningun verbo deja a quien lo lee igual
            # de parado que sin aviso.
            try:
                dias_cert = mod.FW.dias_de_certificado(mod.BASE)
            except Exception:  # noqa: BLE001 - sin red no se avisa de nada
                dias_cert = None
            if dias_cert is not None and dias_cert <= DIAS_AVISO_CERTIFICADO:
                tk.Label(c, text=(
                    f"   El certificado de esta web caduca en {dias_cert} "
                    f"días. Cuando pase, el agente NO podrá ampliar con "
                    f"criterio nuevo (lo guardado sigue sirviendo). No es "
                    f"cosa nuestra: lo renueva el organismo. Si el día "
                    f"llega y no responde, avisa a Emili."),
                    bg=PAPEL2, fg=TINTA, font=self.fuente_menuda, anchor="w",
                    justify="left", wraplength=540, padx=RELLENO
                ).pack(fill="x")

        tk.Label(c, text="Las respuestas salen SIEMPRE de la copia local: que "
                         "una fuente no responda no impide consultar, solo "
                         "quiere decir que hoy no se puede ampliar.",
                 bg=PAPEL2, fg=TINTA2, font=self.fuente_menuda, anchor="w",
                 justify="left", wraplength=560, padx=RELLENO,
                 pady=HUECO2 - 4).pack(fill="x")

        cerrar = ttk.Button(marco, text="Cerrar", command=v.destroy,
                            style="Discreto.TButton")
        cerrar.pack(anchor="e", pady=(HUECO, 0))
        self._pinchable(cerrar)
        # La rueda, sobre cada etiqueta y no solo en los huecos.
        self._atar_rueda_a_los_hijos_de(marco, lienzo_v)
        v.transient(self.raiz)
        v.lift()

    # ------------------------------------------------------------ pintar

    def _terminar(self, res: dict) -> None:
        self._parar_barra()
        # LA VENTANA ENTERA PARA LEER. A partir de aqui el formulario estorba:
        # ya se ha usado, y cada pixel suyo es un pixel que no tiene el texto.
        self._mostrar("respuesta")
        self.eco_pregunta.configure(
            text=self._eco(self.caja.get("1.0", "end").strip(),
                           self.ejercicio.get().strip(),
                           res.get("comunidad") or ""))

        # 1. Fallos: ni estado ni texto, solo la frase.
        if res.get("fallo"):
            frase = (en_cristiano(res.get("motivo", ""))
                     if res["fallo"] == "modelo" else FALLO_GENERICO)
            self._terminar_roto(frase)
            return
        # 3 = la consulta se para ANTES de mirar nada: no hay pregunta, la
        # pregunta no cabe, o el año no vale. Aqui ponia «Falta el año del
        # caso» para los tres, y desde que hay tope de longitud eso es
        # mentira: a quien pega un requerimiento de 15.000 caracteres se le
        # decia que faltaba el año. El motivo lo escribe `fase4` en cristiano
        # y para cada caso; se enseña ese, no una frase fija de aqui.
        #
        # El motivo NO pasa por `en_cristiano`: eso es para fallos tecnicos,
        # donde lo que se filtra son rutas y trozos de clave. Estos tres
        # motivos ya estan escritos para quien los lee y no llevan nada
        # tecnico dentro; pasarlos por ahi los convertiria en el mensaje
        # generico, que es justo lo que se quiere evitar.
        if res["codigo"] == 3:
            motivo = (res.get("motivo") or "").strip()
            self._terminar_roto(
                (motivo[0].upper() + motivo[1:] + ".") if motivo
                else "Falta el año del caso.")
            return

        estado = res.get("estado") or EST.NO_ENCONTRADO
        # CON QUE SE HIZO, junto al estado. Lo dice el motor en el resultado,
        # no la ventana por su cuenta: si algun dia no coincidieran, mandaria
        # lo que de verdad se uso.
        self.con_criterio = bool(res.get("con_criterio"))
        self.comunidad_usada = res.get("comunidad") or ""
        self.aviso_territorial = res.get("cobertura_territorial") or ""
        self._pintar_estado(estado, explicacion(estado, self.con_criterio),
                            estado)
        self.etiqueta_hecha_con.configure(text=HECHA_CON[self.con_criterio])
        self._pintar_aporte(res)
        # El aviso territorial va con los de cobertura, que es lo que es: no
        # es un desacuerdo entre textos -eso mueve el estado- sino algo que no
        # se ha podido mirar. Va el PRIMERO porque puede ser media respuesta.
        coberturas = list(res.get("cobertura") or [])
        if res.get("cobertura_territorial"):
            coberturas.insert(0, res["cobertura_territorial"])
        self._pintar_avisos(res.get("senales") or [], coberturas,
                            res.get("estructural") or "")

        # 2. El texto: SOLO si paso el verificador. `respuesta` viene vacia
        #    cuando no se puede ensenar, y entonces se ensena otra cosa.
        if res.get("respuesta"):
            self.respuesta_actual = res["respuesta"]
            self._escribir_respuesta(res["respuesta"], res)
            self.boton_copiar.configure(state="normal")
            # La traza es lo unico que hace falta para reescribir: el material
            # esta dentro. Se guarda aqui, con la respuesta aceptada delante.
            self.traza_actual = res.get("traza") or ""
            # EL EJERCICIO QUE SE USO, no el que haya ahora en la caja: el
            # gestor puede haberlo cambiado mientras leia, y la reescritura
            # tiene que verificarse contra la MISMA version de la ley que la
            # respuesta que reescribe.
            self.ejercicio_usado = res.get("ejercicio")
            if self.traza_actual:
                self.boton_cliente.configure(state="normal")
        else:
            self._sin_nada_que_copiar()
            self._escribir_sin_respaldo(res)

        # EL PIE NO PUEDE AFIRMAR QUE ALGO ESTA GUARDADO SIN SABERLO. Con el
        # disco lleno seguia diciendo «Expediente guardado en ...» señalando a
        # una carpeta que no existe. Lo dice `fase4`, que es quien escribe.
        if res.get("expediente", True):
            self.pie_respuesta.configure(
                text=f"Expediente guardado en {res.get('traza', '(sin traza)')}")
        else:
            self.pie_respuesta.configure(
                text="AVISO: esta consulta NO ha quedado guardada en el "
                     "expediente. Si la vas a usar, copiala tu.")

    def _pintar_estado(self, titulo: str, explicacion: str, clave: str) -> None:
        """El estado, con el filete de la maqueta y SIN teñir el fondo.

        El color solo aparece en el filete de la izquierda y en el rotulo. El
        panel se queda en papel pase lo que pase: es lo que impide que los tres
        estados se lean como un semaforo.
        """
        fondo = FONDO.get(clave, PAPEL2)
        self.etiqueta_estado.configure(
            text=titulo, fg=COLOR.get(clave, TINTA), bg=fondo,
        )
        self.etiqueta_explicacion.configure(
            text=explicacion, bg=fondo, fg=TINTA2,
        )
        self.panel_estado.configure(bg=fondo,
                                    highlightthickness=1,
                                    highlightbackground=FILETE)
        self.filete_estado.configure(bg=FILETE_ESTADO.get(clave, FILETE))
        self.filete_estado.grid(row=0, column=0, sticky="ns")
        self.etiqueta_estado.grid(row=0, column=1, sticky="ew")
        # El detalle, en la pagina y con el mismo filete de color para que se
        # lea como lo que es: la continuacion del rotulo de arriba.
        self.panel_detalle.configure(bg=fondo, highlightthickness=1,
                                     highlightbackground=FILETE)
        self.filete_detalle.configure(bg=FILETE_ESTADO.get(clave, FILETE))
        self.filete_detalle.grid(row=0, column=0, rowspan=2, sticky="ns")
        self.etiqueta_explicacion.grid(row=0, column=1, sticky="ew",
                                       padx=(RELLENO, RELLENO),
                                       pady=(HUECO2 - 4, 0))
        self.etiqueta_hecha_con.configure(bg=fondo)
        self.etiqueta_hecha_con.grid(row=1, column=1, sticky="ew",
                                     padx=(RELLENO, RELLENO),
                                     pady=(AIRE - 2, HUECO2 - 2))
        # El ancho se recalcula A LA FUERZA: el `<Configure>` del panel puede
        # haber llegado ya, con el panel todavia estrecho, y entonces la
        # guarda de «si no ha cambiado, no toques» deja puesto un ancho de
        # cuando no habia nada dentro. Medido: la explicacion se quedaba
        # envolviendo a 209 px dentro de una columna de 1.002.
        self._ancho_estado = 0
        self._wrap_estado()
        self.panel_detalle.after_idle(self._wrap_estado)
        # LA RUEDA, SOBRE TODO LO QUE ACABA DE NACER. Los avisos y el detalle
        # del estado se crean en cada respuesta, asi que atarlos una vez en el
        # constructor no vale: la rueda la recibe el widget que esta debajo
        # del raton, y debajo del raton casi siempre hay una etiqueta.
        self._atar_rueda_a_los_hijos_de(self.resultado, self.lienzo_lectura)
        self._atar_rueda_a_los_hijos(self.panel_estado)


    def _pintar_aporte(self, res: dict) -> None:
        """QUE HA APORTADO EL CRITERIO, en una linea y con numeros.

        Es la demostracion entera: la misma pregunta con los dos botones y la
        diferencia a la vista. Sin esto habria que leerse las dos respuestas
        enteras y compararlas a ojo, y nadie lo hace.
        """
        for w in self.panel_aporte.winfo_children():
            w.destroy()
        if not res.get("con_criterio"):
            self.panel_aporte.pack_forget()
            return

        # TRES CASOS, NO DOS. Y la diferencia no es de matiz.
        #
        # Con Renta ingerida y la copia de criterio llena de IVA, el
        # seleccionador trae consultas por COINCIDENCIA DE NUMERO DE ARTICULO
        # -el 30 existe en las dos leyes-. Decir entonces «se le pusieron
        # delante 3 y ninguna sostiene la respuesta» da a entender que se ha
        # mirado el criterio de Renta. No se ha mirado.
        #
        # Y «ESTA DUDA LA RESUELVE LA LEY SOLA» SOLO SE PUEDE DECIR CUANDO SE
        # HA COMPROBADO CRITERIO DE ESA MATERIA. Es una afirmacion sobre lo que
        # opina la Administracion, y no se sostiene sin haber mirado.
        a = res.get("aporte") or {}
        usadas, resol = a.get("consultas_dgt") or [], a.get("resoluciones") or []
        impuesto = a.get("impuesto") or ""
        misma = a.get("en_material_misma_materia")
        otra = a.get("en_material_otra_materia")
        if misma is None and otra is None:
            # Expedientes anteriores a esta distincion: todo se cuenta como
            # de la misma materia, que es lo que se suponia entonces.
            misma, otra = list(a.get("consultas_en_material") or []), []
        misma, otra = list(misma or []), list(otra or [])
        habia_r = len(a.get("resoluciones_en_material") or [])
        de_esto = f" de {impuesto}" if impuesto else ""

        if usadas or resol:
            partes = []
            if usadas:
                partes.append(f"{len(usadas)} consulta(s) de la DGT")
            if resol:
                partes.append(f"{len(resol)} resolución(es)")
            texto = ("Lo que ha añadido el criterio: " + " y ".join(partes)
                     + ", citadas y comprobadas una a una.")
            detalle = "  ·  ".join(usadas + resol)
            color = TINTA
        elif misma or habia_r:
            texto = (f"Se le pusieron delante {len(misma)} consulta(s) de la "
                     f"DGT y {habia_r} resolución(es){de_esto}, y NINGUNA "
                     f"sostiene la respuesta: esta duda la resuelve la ley sola.")
            detalle = "  ·  ".join(misma)
            color = TINTA2
        elif otra:
            texto = (f"En la copia local no hay criterio{de_esto}. Lo que se "
                     f"encontró —{len(otra)} consulta(s)— es de otro impuesto "
                     f"y coincidía solo por el número de artículo, así que no "
                     f"se ha comprobado criterio de esta materia. Puede "
                     f"haberlo en la fuente: aquí no está.")
            detalle = "  ·  ".join(otra)
            color = TINTA2
        else:
            texto = (f"En la copia local todavía no hay criterio{de_esto}. No "
                     "es un fallo ni quiere decir que no exista: esta copia es "
                     "parcial y esta duda aún no está dentro.")
            detalle = ""
            color = TINTA2

        et = tk.Label(self.panel_aporte, text=texto, bg=PAPEL2, fg=color,
                      font=self.fuente, anchor="w", justify="left",
                      padx=RELLENO, pady=AIRE - 2)
        et.pack(fill="x")
        elasticos = [(et, "izq", RELLENO * 2)]
        if detalle:
            ed = tk.Label(self.panel_aporte, text=detalle, bg=PAPEL2, fg=ENLACE,
                          font=self.fuente_referencia, anchor="w",
                          justify="left", padx=RELLENO)
            ed.pack(fill="x", pady=(0, AIRE - 2))
            elasticos.append((ed, "izq", RELLENO * 2))
        # Los de dentro de los paneles se rehacen en cada consulta, asi que la
        # lista de elasticos se limpia de los que ya no existen: si no, crece
        # sin parar y `_reajustar` acaba hablandole a widgets destruidos.
        self._elasticos = [x for x in self._elasticos if x[0].winfo_exists()]
        self._elasticos += elasticos
        self.panel_aporte.pack(fill="x", pady=(AIRE + 2, 0))
        self._atar_rueda_a_los_hijos(self.panel_aporte)
        self._ancho_previo = 0
        self._reajustar()

    def _pintar_avisos(self, senales: list, cobertura: list,
                       estructural: str = "") -> None:
        """TRES NIVELES, POR LO QUE EL LECTOR PUEDE HACER CON CADA UNO.

            DESACUERDO ................ los textos se contradicen. Es lo que
                                        pone el estado en DISCUTIDO.
            LO QUE NO SE HA PODIDO
            MIRAR ..................... huecos ACCIONABLES: hay algo concreto
                                        que mirar. Enteros. NO tocan el estado.
            limite del corpus ......... normas que no tenemos y no vamos a
                                        tener. Una linea, en gris, al final.

        El segundo bloque SE PINTA SIEMPRE que hay respuesta, aunque este
        vacio. Un bloque que solo aparece cuando hay algo que decir es un
        bloque que nadie busca cuando no aparece: leer «no falta nada por
        mirar» es informacion, y no verlo no lo es.

        El tercero va en una linea y en gris a proposito: sale en casi todas
        las respuestas y no hay nada que hacer con el. Entero y arriba, ocupaba
        el mismo sitio que los que si hay que leer, y se los llevaba por
        delante. Un aviso que sale siempre no es un aviso, es decoracion.
        """
        for w in self.panel_avisos.winfo_children():
            w.destroy()

        def rotulo(texto: str) -> None:
            tk.Label(self.panel_avisos, text=texto, bg=PAPEL2, fg=TINTA3,
                     font=self.fuente_seccion, anchor="w",
                     # `pady` de un Label es UNA distancia, no una pareja:
                     # con (8, 6) tkinter revienta. Ya esta escrito abajo y
                     # aun asi cai otra vez.
                     padx=RELLENO, pady=AIRE - 1).pack(fill="x")

        def linea(texto: str, color: str = TINTA) -> None:
            # El hueco de abajo va en el pack, NO en el Label: el `pady` de un
            # widget es una distancia sola, y una pareja (0, 4) lo revienta.
            et = tk.Label(self.panel_avisos, text=texto, bg=PAPEL2,
                          fg=color, font=self.fuente, anchor="w",
                          justify="left", padx=RELLENO)
            et.pack(fill="x", pady=(0, AIRE - 2))


        if senales:
            rotulo("DESACUERDO ENTRE LOS TEXTOS")
            for s in senales:
                linea("• " + s)

        rotulo("LO QUE NO SE HA PODIDO MIRAR")
        if cobertura:
            for s in cobertura:
                linea("• " + s)
        else:
            linea("Nada que mirar: los articulos que sostienen la respuesta "
                  "estan vigentes en el ejercicio y no hay doctrina pendiente "
                  "de comprobar.", TINTA2)
        if estructural:
            linea(estructural, TINTA3)
        self.panel_avisos.pack(fill="x")
        self._atar_rueda_a_los_hijos(self.panel_avisos)
        self._ancho_avisos = 0
        self.panel_avisos.bind("<Configure>", self._wrap_avisos)
        self.panel_avisos.after_idle(self._wrap_avisos)
        self._ancho_previo = 0
        self._reajustar()

    def _escribir_texto(self, trozos: list) -> None:
        self.texto.configure(state="normal")
        self.texto.delete("1.0", "end")
        for texto, etiqueta in trozos:
            self.texto.insert("end", texto, etiqueta)
        self._columna()
        self.texto.configure(state="disabled")
        self._arriba()

    # Un fragmento citado, en cualquiera de las comillas que usa el redactor.
    RE_CITA = re.compile(r"«[^»]{4,}»|“[^”]{4,}”|\"[^\"]{8,}\"")
    # La referencia que va pegada detras: (articulo 95 de la Ley 37/1992, URL).
    RE_REFERENCIA = re.compile(r"\([^)]{6,400}\)|\[[^\]]{6,400}\]")

    def _escribir_con_jerarquia(self, cuerpo: str) -> None:
        """LO MAS LEGIBLE DE LA PANTALLA TIENE QUE SER LA CITA.

        Todo el valor de esta herramienta es que la persona pueda comprobar lo
        que se le dice. Si la cita se lee igual que el parrafo que la rodea, es
        decoracion, y entonces nadie la comprueba.

        Se marcan tres cosas distintas y se les da familia y tamaño distintos:

            cita        el fragmento entre comillas -> serif, grande
            referencia  el parentesis con articulo y norma -> mono, menuda
            enlace      la URL dentro de la referencia -> mono, lila, pinchable

        Aqui NO se reescribe ni se reordena nada: se marca lo que ya venia. El
        texto que se copia al portapapeles sigue siendo el mismo.
        """
        pos = 0
        marcas = []
        for m in self.RE_CITA.finditer(cuerpo):
            marcas.append((m.start(), m.end(), "cita"))
        for m in self.RE_REFERENCIA.finditer(cuerpo):
            marcas.append((m.start(), m.end(), "referencia"))
        marcas.sort()

        n_enlace = 0
        for ini, fin, clase in marcas:
            if ini < pos:          # solapamiento: manda la primera marca
                continue
            self.texto.insert("end", cuerpo[pos:ini])
            trozo = cuerpo[ini:fin]
            if clase == "referencia":
                # Dentro de la referencia, la URL se marca aparte para que se
                # pueda pinchar. Es el gesto que hace comprobable la cita.
                p = 0
                for me in RE_ENLACE.finditer(trozo):
                    self.texto.insert("end", trozo[p:me.start()], "referencia")
                    etiqueta = f"url{n_enlace}"
                    n_enlace += 1
                    self._enlaces[etiqueta] = me.group(0)
                    self.texto.insert("end", me.group(0), ("enlace", etiqueta))
                    p = me.end()
                self.texto.insert("end", trozo[p:], "referencia")
            else:
                self.texto.insert("end", trozo, clase)
            pos = fin

        # La cola, y las URL sueltas que no iban dentro de un parentesis.
        resto = cuerpo[pos:]
        p = 0
        for me in RE_ENLACE.finditer(resto):
            self.texto.insert("end", resto[p:me.start()])
            etiqueta = f"url{n_enlace}"
            n_enlace += 1
            self._enlaces[etiqueta] = me.group(0)
            self.texto.insert("end", me.group(0), ("enlace", etiqueta))
            p = me.end()
        self.texto.insert("end", resto[p:])

    def _escribir_respuesta(self, cuerpo: str, res: dict) -> None:
        """El texto verificado, con los enlaces del BOE pinchables."""
        self.texto.configure(state="normal")
        self.texto.delete("1.0", "end")
        self._enlaces: dict[str, str] = {}
        self._escribir_con_jerarquia(cuerpo)

        verificadas = res.get("preceptos") or []
        if verificadas:
            self.texto.insert(
                "end",
                f"\n\n———\nCitas comprobadas una a una contra el texto oficial. "
                f"Preceptos que la sostienen: {', '.join(verificadas)}.\n",
                "apagado",
            )
        self._columna()
        self.texto.configure(state="disabled")
        self._arriba()

    def _escribir_sin_respaldo(self, res: dict) -> None:
        """NO ENCONTRADO: nunca el borrador, solo lo recuperado en crudo."""
        trozos = [
            ("No se muestra ningun texto redactado: no ha superado la "
             "comprobacion de citas.\n\n", "titulo"),
        ]
        if res.get("motivo"):
            trozos.append((f"Motivo: {res['motivo']}\n\n", "apagado"))
        self.texto.configure(state="normal")
        self.texto.delete("1.0", "end")
        for t, e in trozos:
            self.texto.insert("end", t, e)

        # Los articulos encontrados, para mirarlos a mano. Se leen de la traza,
        # que es donde estan con su enlace.
        self._enlaces = {}
        encontrados = self._leer_recuperado(res)
        if encontrados:
            self.texto.insert("end", "Articulos encontrados, por si quieres "
                                     "mirarlos tu:\n\n", "titulo")
            for i, (referencia, rubrica, url) in enumerate(encontrados):
                self.texto.insert("end", f"· {referencia}")
                if rubrica:
                    self.texto.insert("end", f" — {rubrica}")
                self.texto.insert("end", "\n   ")
                if url:
                    etiqueta = f"url{i}"
                    self._enlaces[etiqueta] = url
                    self.texto.insert("end", url, ("enlace", etiqueta))
                self.texto.insert("end", "\n\n")
        else:
            self.texto.insert(
                "end",
                "No se encontro ningun articulo. Esta herramienta solo tiene "
                "la Ley y el Reglamento del IVA: si la duda es de otro "
                "impuesto, no puede contestarla.\n",
            )
        self._columna()
        self.texto.configure(state="disabled")
        self._arriba()

    def _leer_recuperado(self, res: dict) -> list:
        """(referencia, rubrica, enlace) de lo recuperado, desde la traza.

        La rubrica no esta en la traza: se saca del corpus, que ya esta
        cargado, buscando por clave. Asi la lista se lee sin tener que abrir
        el JSON de la ley.
        """
        import json

        ruta = Path(res.get("traza") or "") / "recuperado.json"
        if not ruta.is_file():
            return []
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        salida = []
        for d in datos:
            doc = self.ix.por_clave.get(d.get("clave", "")) if self.ix else None
            rubrica = doc.registro.get("rubrica", "") if doc else ""
            salida.append((d.get("referencia", ""), rubrica, d.get("url", "")))
        return salida

    # ------------------------------------------------------------ acciones

    def _abrir_enlace(self, evento) -> None:
        for etiqueta in self.texto.tag_names(f"@{evento.x},{evento.y}"):
            url = getattr(self, "_enlaces", {}).get(etiqueta)
            if url:
                webbrowser.open_new_tab(url)
                return

    def _copiar(self) -> None:
        """Lo copiado LLEVA CON QUE SE HIZO. Una respuesta pegada en unas notas
        pierde la pantalla que la explicaba; sin esta linea, dentro de un mes
        nadie sabra si aquello llevaba criterio administrativo o no."""
        if not self.respuesta_actual:
            return
        # LA COMUNIDAD VIAJA CON EL TEXTO, por el mismo motivo que el modo:
        # una respuesta de Renta pegada en unas notas no dice, por si sola, si
        # llevaba la deduccion autonomica de Cataluña o si salio estatal.
        cabecera = HECHA_CON[getattr(self, "con_criterio", False)]
        com = getattr(self, "comunidad_usada", "")
        if com:
            cabecera += f" · comunidad: {com}"
        aviso = getattr(self, "aviso_territorial", "")
        self.raiz.clipboard_clear()
        self.raiz.clipboard_append(
            f"[{cabecera}]\n"
            + (f"[AVISO: {aviso}]\n" if aviso else "")
            + "\n" + self.respuesta_actual)
        self.copiado.configure(text="copiado")
        self.raiz.after(2000, lambda: self.copiado.configure(text=""))


# ------------------------------------------------------------------- main


def ventana_de_descoordinacion(raiz, error) -> None:
    """La pantalla de «no abro, y te digo por que». Sin traza y sin jerga."""
    raiz.title("Consulta fiscal — sin configurar")
    raiz.configure(bg=PAPEL)
    # 780x520 estaba medido a ojo. En el peor caso -las seis frases de estado
    # fuera de la guia- el contenido pide 643 px y se salia por 123. Se abre
    # segun lo que haga falta, con techo de pantalla.
    raiz.geometry("820x620")
    raiz.minsize(620, 400)
    f_ui = elegir_fuente("interfaz")
    marco = tk.Frame(raiz, bg=PAPEL, padx=MARGEN, pady=MARGEN)
    marco.pack(fill="both", expand=True)
    tk.Label(marco, text="No se abre: falta terminar de configurar",
             bg=PAPEL, fg=TINTA, font=(f_ui, 20, "bold"),
             anchor="w", justify="left").pack(fill="x", pady=(0, HUECO))
    caja = tk.Frame(marco, bg=PAPEL2, highlightthickness=1,
                    highlightbackground=FILETE)
    caja.pack(fill="both", expand=True)
    # El mismo filete lila del estado: esto no es un error del sistema, es una
    # decision deliberada de no abrir, y se pinta como tal.
    tk.Frame(caja, width=4, bg=LILA).pack(side="left", fill="y")
    # Con barra: el numero de descuadres no tiene tope, y un aviso que no se
    # puede leer entero no es un aviso.
    texto = tk.Text(caja, wrap="word", bg=PAPEL2, fg=TINTA, font=(f_ui, 12),
                    bd=0, highlightthickness=0, padx=RELLENO, pady=RELLENO,
                    width=1, height=1)
    texto.pack(side="left", fill="both", expand=True)
    barra = ttk.Scrollbar(caja, orient="vertical", command=texto.yview,
                          style="Vertical.TScrollbar")
    barra.pack(side="right", fill="y")
    texto.configure(yscrollcommand=barra.set)
    texto.insert("1.0", "\n".join(error.en_cristiano()))
    texto.configure(state="disabled")
    boton = tk.Button(marco, text="Cerrar", command=raiz.destroy,
                      font=(f_ui, 12), bg=ELEVADO, fg=TINTA,
                      activebackground=FILETE, activeforeground=TINTA,
                      relief="flat", bd=0, padx=HUECO, pady=AIRE,
                      cursor="hand2", highlightthickness=0)
    boton.pack(anchor="e", pady=(HUECO, 0))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Ventana de consulta fiscal.")
    ap.add_argument("--motor", choices=["anthropic", "ensayo"],
                    default="anthropic")
    args = ap.parse_args(argv)

    raiz = tk.Tk()

    # PRIMERO SE REHACE LO QUE SE PUEDE REHACER, Y DESPUES SE EXIGE.
    #
    # `GUIA.md` es un fichero generado, y tras un `git pull` no existe. Pararse
    # ahi y decir «lo arregla Emili» es pedirle a quien consulta que resuelva
    # un problema que no tiene y que el programa arregla solo. Ver
    # `configuracion.asegurar`.
    from agente_fiscal import configuracion as CONF
    aviso_guia = ""
    try:
        aviso_guia = CONF.asegurar()
    except Exception as e:  # noqa: BLE001
        # Si NO se puede rehacer -falta `guias/GUIA.md`, que si viaja- eso ya
        # no es un derivado que falta: es el original. Se sigue y lo dira
        # `exigir_coherencia`, que para eso esta.
        aviso_guia = f"No se ha podido rehacer la hoja de instrucciones: {e}"

    # MEJOR NO ABRIR QUE ABRIR MINTIENDO. Si las fuentes, los textos y la guia
    # no dicen lo mismo, la ventana podria estar afirmando que hay criterio de
    # la DGT mientras la hoja de la mesa dice que no. Quien lea la hoja
    # decidira con ella, y nadie se enterara.
    try:
        CONF.exigir_coherencia()
    except CONF.Descoordinado as e:
        ventana_de_descoordinacion(raiz, e)
        raiz.mainloop()
        return 1

    ventana = Ventana(raiz, args.motor)
    if aviso_guia:
        # En una linea y sin alarma: se ha arreglado solo, no ha pasado nada.
        ventana.mostrar_cinta(aviso_guia)
    raiz.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
