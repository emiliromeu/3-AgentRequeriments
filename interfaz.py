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
from agente_fiscal import dgt as DGT
from agente_fiscal import estado as EST

# ----------------------------------------------------------------- textos
#
# El estado lo calcula el codigo por reglas. Aqui solo se traduce a algo que
# entienda quien no ha leido el proyecto. La explicacion del CRITERIO CLARO es
# innegociable y va SIEMPRE: si alguien lee "criterio claro" y entiende
# "Hacienda opina esto", la herramienta hace dano en vez de ayudar.

# EL TEXTO DEL CRITERIO CLARO, EN DOS VERSIONES.
#
# El de hoy dice que la DGT no esta. Es cierto y tiene que seguir diciendolo
# MIENTRAS sea cierto. Cuando la DGT entre de verdad dejara de serlo, y la
# frase pasara a ser justo lo contrario de lo que hace falta.
#
# La version nueva esta escrita y NO se usa todavia.
#
# TIENE SU PROPIO INTERRUPTOR, Y NO EL DE LA DGT. Estuvieron atados al mismo y
# fue un error: encender el motor y cambiar lo que lee el profesional son dos
# decisiones distintas. Con `AGENTE_DGT=1` para probar, el texto cambiaba solo
# y la ventana pasaba a decir lo contrario que la hoja impresa de GUIA.md, que
# es justo lo que no puede pasar.
#
# Los dos textos -este y el de GUIA.md- se cambian A LA VEZ, a mano, el dia que
# se decida que la DGT esta de verdad. Hasta entonces esta variable no se toca:
#
#     AGENTE_DGT_TEXTOS=1     cambia la frase de la ventana
#
# Las dos frases dicen lo mismo en lo que importa: que el ESTADO habla de los
# textos, no de lo que Hacienda vaya a hacer.
VARIABLE_TEXTOS = "AGENTE_DGT_TEXTOS"


def textos_con_dgt() -> bool:
    import os
    return os.environ.get(VARIABLE_TEXTOS, "").strip() not in ("", "0", "no", "off")


CLARO_SIN_DGT = (
    "La ley y el reglamento no se contradicen. NO dice que criterio aplica "
    "Hacienda: la DGT y los tribunales no estan en esta herramienta."
)
# Y la de las TRES fuentes, para cuando entren la DGT y el TEAC. Tambien
# inactiva: se enciende con AGENTE_DGT_TEXTOS a la vez que GUIA.md, nunca sola.
CLARO_CON_TRES_FUENTES = (
    "La ley y el reglamento no se contradicen, y ni la doctrina del TEAC ni "
    "el criterio de la DGT que hay en la herramienta apuntan a otra cosa. NO "
    "incluye sentencias de los tribunales de justicia, y el criterio puede "
    "cambiar: comprueba las citas antes de decidir."
)
CLARO_CON_DGT = (
    "La ley y el reglamento no se contradicen, y el criterio de la DGT que "
    "hay en la herramienta va en la misma linea. NO incluye los tribunales, "
    "y el criterio puede cambiar: comprueba las citas antes de decidir."
)

# EL TEXTO DE DISCUTIDO, ANTES Y DESPUES DE SEPARAR LOS EJES.
#
# El de hoy dice «o hay avisos que no se han podido cerrar», y desde la
# separacion eso ya no es cierto: los avisos de cobertura tienen bloque propio y
# NO ponen la respuesta en DISCUTIDO. La frase esta preparada, no activada, y
# se cambia A LA VEZ que GUIA.md -ver GUIA_ESTADOS_NUEVO.md- con el mismo
# interruptor que el resto de textos.
#
# Se puede esperar sin riesgo: con la DGT y el TEAC apagados el desacuerdo de
# fondo solo puede venir de ellos, asi que DISCUTIDO NO SALE HOY y esta frase
# no llega a pantalla. El dia que se enciendan las fuentes es justo el dia que
# se cambian los dos textos.
DISCUTIDO_HOY = (
    "Los textos encontrados apuntan a soluciones distintas, o hay avisos "
    "que no se han podido cerrar. Lee los avisos de arriba y comprueba las "
    "citas antes de decidir: aqui no hay un criterio unico."
)
DISCUTIDO_CON_EJES = (
    "Hay textos que apuntan a soluciones distintas: criterio de años "
    "distintos sobre el mismo articulo, o un tribunal pronunciandose sobre "
    "criterio que esta respuesta cita. Lee el desacuerdo de arriba y "
    "comprueba las citas antes de decidir: aqui no hay un criterio unico."
)

EXPLICACION = {
    EST.CLARO: (CLARO_CON_DGT if textos_con_dgt() else CLARO_SIN_DGT),
    EST.DISCUTIDO: (DISCUTIDO_CON_EJES if textos_con_dgt() else DISCUTIDO_HOY),
    EST.NO_ENCONTRADO: (
        "No hay respaldo suficiente. Abajo tienes los articulos encontrados "
        "para mirarlos tu."
    ),
}

# --------------------------------------------------------------- la paleta
#
# Viene de la maqueta «Consulta IVA - Direccion visual», modo «Papel claro».
# Se traduce lo que tkinter sabe hacer -color, tipografia, tamaños, espaciado,
# jerarquia- y se deja fuera lo que no (esquinas redondeadas, sombras,
# degradados, transiciones). Ver la lista al final del rediseño.

PAPEL = "#EFEEF3"      # fondo de la ventana
PAPEL2 = "#FFFFFF"     # superficie de lectura
TINTA = "#17171D"      # texto principal
TINTA2 = "#4A4A55"     # texto secundario
FILETE = "#DCDBE3"     # bordes y separadores
ENLACE = "#5D3FCB"     # el lila en su version oscura, sobre papel
LILA = "#C0A5FF"       # el acento claro: marca y filete, NUNCA parrafo

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
COLOR = {
    EST.CLARO: "#5D3FCB",        # el lila oscuro, legible sobre papel
    EST.DISCUTIDO: "#6E6879",    # lila desaturado
    EST.NO_ENCONTRADO: "#4A4A55",  # gris: ni alarma ni error
}
# El filete de 4 px a la izquierda del estado, que es la marca de la maqueta.
FILETE_ESTADO = {
    EST.CLARO: LILA,
    EST.DISCUTIDO: "#9A93AD",
    EST.NO_ENCONTRADO: "#8E8E99",
}
# El fondo NO cambia con el estado: es siempre papel. En la version anterior
# cada estado teñia su panel (verde, ambar, rojo) y eso era justo el semaforo.
FONDO = {e: PAPEL2 for e in (EST.CLARO, EST.DISCUTIDO, EST.NO_ENCONTRADO)}


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
)
FALLO_GENERICO = ("No se ha podido completar la consulta. Vuelve a intentarlo; "
                  "si sigue igual, avisa a Emili.")


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


RE_ENLACE = re.compile(r"https?://[^\s)\]}>,;]+")


# ------------------------------------------------------------------ ventana


class Ventana:
    def __init__(self, raiz: tk.Tk, motor_nombre: str):
        self.raiz = raiz
        self.motor_nombre = motor_nombre
        self.avisos: "queue.Queue[tuple]" = queue.Queue()
        self.trabajando = False
        self.respuesta_actual = ""
        self.ix = None
        self.grafo = None
        self.motor = None

        raiz.title("Consulta fiscal — IVA")
        raiz.minsize(880, 640)
        raiz.configure(bg=PAPEL)

        # La escala de la maqueta, trasladada a puntos. Las proporciones se
        # respetan; los valores absolutos no, porque la maqueta esta dibujada a
        # 2776 px de ancho y esta ventana mide mil y pico.
        f_ui = elegir_fuente("interfaz")
        f_cita = elegir_fuente("cita")
        f_ref = elegir_fuente("referencia")

        self.fuente = tkfont.Font(family=f_ui, size=11)
        self.fuente_menuda = tkfont.Font(family=f_ui, size=10)
        self.fuente_rotulo = tkfont.Font(family=f_ref, size=9)
        self.fuente_titular = tkfont.Font(family=f_ui, size=17, weight="bold")
        self.fuente_estado = tkfont.Font(family=f_ui, size=15, weight="bold")
        # LA CITA ES LO MAS GRANDE DE LA PANTALLA, y en serif. Es la unica
        # forma de que se lea como cita y no como parrafo, que es lo que pide
        # la maqueta y lo unico que hace util esta herramienta.
        self.fuente_cita = tkfont.Font(family=f_cita, size=14)
        self.fuente_texto = tkfont.Font(family=f_ui, size=12)
        self.fuente_referencia = tkfont.Font(family=f_ref, size=10)

        self._construir()
        raiz.after(80, self._vaciar_avisos)
        # El corpus tarda un segundo en cargar: se hace despues de pintar la
        # ventana para que no parezca que no ha arrancado.
        raiz.after(120, self._arrancar_motor)

    # ------------------------------------------------------------ montaje

    def _construir(self) -> None:
        marco = tk.Frame(self.raiz, bg=PAPEL, padx=16, pady=12)
        marco.pack(fill="both", expand=True)
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(6, weight=1)

        # El rotulo menudo en versalitas sobre el titular: de la maqueta.
        encabezado = tk.Frame(marco, bg=PAPEL)
        encabezado.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        tk.Label(encabezado, text="DEPARTAMENTO FISCAL", bg=PAPEL, fg="#8E8E99",
                 font=self.fuente_rotulo, anchor="w").pack(anchor="w")
        cabecera = tk.Label(
            encabezado, text="Consulta fiscal sobre el IVA", bg=PAPEL,
            fg=TINTA, font=self.fuente_titular, anchor="w",
        )
        cabecera.pack(anchor="w", pady=(2, 0))

        self.aviso_motor = tk.Label(
            marco, text="", bg=PAPEL, fg=TINTA2, anchor="w",
            font=self.fuente,
        )
        self.aviso_motor.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        # --- la duda ---
        tk.Label(marco, text="Tu duda", bg=PAPEL, font=self.fuente,
                 anchor="w").grid(row=2, column=0, sticky="ew")
        self.caja = tk.Text(marco, height=4, wrap="word", font=self.fuente,
                            relief="solid", borderwidth=1, padx=10, pady=8,
                            bg=PAPEL2, fg=TINTA,
                            highlightthickness=1,
                            highlightbackground=FILETE,
                            highlightcolor=ENLACE, bd=0)
        self.caja.grid(row=3, column=0, sticky="ew", pady=(2, 10))
        self.caja.bind("<KeyRelease>", lambda _e: self._revisar_boton())

        # --- ejercicio + boton ---
        fila = tk.Frame(marco, bg=PAPEL)
        fila.grid(row=4, column=0, sticky="ew")
        tk.Label(fila, text="Ejercicio (el año del caso):", bg=PAPEL,
                 font=self.fuente).pack(side="left")
        self.ejercicio = tk.StringVar()
        self.ejercicio.trace_add("write", lambda *_: self._revisar_boton())
        self.caja_ejercicio = tk.Entry(fila, textvariable=self.ejercicio,
                                       width=8, font=self.fuente,
                                       bg=PAPEL2, fg=TINTA, bd=0,
                                       highlightthickness=1,
                                       highlightbackground=FILETE,
                                       highlightcolor=ENLACE)
        self.caja_ejercicio.pack(side="left", padx=(8, 12))
        # Se deja VACIO a proposito. Ver la regla 2 de la cabecera.
        tk.Label(fila, text="obligatorio: la ley cambia cada año",
                 bg=PAPEL, fg=TINTA2, font=self.fuente_menuda).pack(side="left")

        self.boton = tk.Button(fila, text="Consultar", font=self.fuente,
                               command=self._lanzar, state="disabled",
                               padx=18, pady=4)
        self.boton.pack(side="right")

        # --- progreso ---
        self.marco_progreso = tk.Frame(marco, bg=PAPEL)
        self.marco_progreso.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        self.barra = ttk.Progressbar(self.marco_progreso, mode="indeterminate")
        self.paso = tk.Label(self.marco_progreso, text="", bg=PAPEL,
                             fg="#333", font=self.fuente, anchor="w")

        # --- resultado ---
        self.resultado = tk.Frame(marco, bg=PAPEL)
        self.resultado.grid(row=6, column=0, sticky="nsew", pady=(12, 0))
        self.resultado.columnconfigure(0, weight=1)
        self.resultado.rowconfigure(3, weight=1)

        self.panel_estado = tk.Frame(self.resultado, bg=PAPEL)
        self.panel_estado.grid(row=0, column=0, sticky="ew")
        self.panel_estado.columnconfigure(1, weight=1)
        # El filete de 4 px de la maqueta: un Frame estrecho a la izquierda.
        # Es lo unico que lleva el color del estado.
        self.filete_estado = tk.Frame(self.panel_estado, width=4, bg=FILETE)
        self.etiqueta_estado = tk.Label(
            self.panel_estado, text="", font=self.fuente_estado, anchor="w",
            justify="left", padx=12, pady=8,
        )
        self.etiqueta_explicacion = tk.Label(
            self.panel_estado, text="", font=self.fuente, anchor="w",
            justify="left", wraplength=820, padx=12, pady=0,
        )

        # Los avisos de fecha van ARRIBA, antes del texto: si se ponen al final
        # no los lee nadie, y son justo lo que puede invalidar la respuesta.
        self.panel_avisos = tk.Frame(self.resultado, bg=PAPEL2)
        self.panel_avisos.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.panel_avisos.grid_remove()

        barra_acciones = tk.Frame(self.resultado, bg=PAPEL)
        barra_acciones.grid(row=2, column=0, sticky="ew", pady=(10, 4))
        self.boton_copiar = tk.Button(barra_acciones, text="Copiar respuesta",
                                      font=self.fuente, command=self._copiar,
                                      state="disabled")
        self.boton_copiar.pack(side="left")
        self.copiado = tk.Label(barra_acciones, text="", bg=PAPEL,
                                fg="#1b5e20", font=self.fuente)
        self.copiado.pack(side="left", padx=8)

        caja = tk.Frame(self.resultado)
        caja.grid(row=3, column=0, sticky="nsew")
        caja.columnconfigure(0, weight=1)
        caja.rowconfigure(0, weight=1)
        self.texto = tk.Text(caja, wrap="word", font=self.fuente_texto,
                             bd=0, highlightthickness=1,
                             highlightbackground=FILETE,
                             padx=22, pady=18, fg=TINTA,
                             state="disabled", spacing1=2, spacing3=6,
                             background=PAPEL2)
        self.texto.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(caja, command=self.texto.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.texto.configure(yscrollcommand=scroll.set)

        self.texto.tag_configure("enlace", foreground=ENLACE, underline=True,
                                 font=self.fuente_referencia)
        self.texto.tag_bind("enlace", "<Enter>",
                            lambda _e: self.texto.configure(cursor="hand2"))
        self.texto.tag_bind("enlace", "<Leave>",
                            lambda _e: self.texto.configure(cursor=""))
        self.texto.tag_bind("enlace", "<Button-1>", self._abrir_enlace)
        self.texto.tag_configure("titulo", font=tkfont.Font(
            family=elegir_fuente("interfaz"), size=12, weight="bold"),
            foreground=TINTA, spacing3=6)
        self.texto.tag_configure("apagado", foreground=TINTA2,
                                 font=self.fuente_menuda)
        # LA JERARQUIA QUE HACE UTIL LA PANTALLA. La cita es lo mas grande y
        # va en serif; la referencia, en monoespaciada y menuda. Distinta
        # familia y distinto tamaño: asi una cita no se confunde nunca con la
        # explicacion que la rodea.
        self.texto.tag_configure("cita", font=self.fuente_cita, foreground=TINTA,
                                 lmargin1=14, lmargin2=14, spacing1=8, spacing3=8)
        self.texto.tag_configure("referencia", font=self.fuente_referencia,
                                 foreground=TINTA2)
        self.texto.tag_configure("rotulo", font=self.fuente_rotulo,
                                 foreground="#8E8E99", spacing1=10)

        self.pie = tk.Label(marco, text="", bg=PAPEL, fg="#8E8E99",
                            font=tkfont.Font(size=9), anchor="w")
        self.pie.grid(row=7, column=0, sticky="ew", pady=(8, 0))

        self.caja.focus_set()

    # ------------------------------------------------------------ arranque

    def _arrancar_motor(self) -> None:
        """Carga corpus y motor. Si falla, se dice en cristiano y se bloquea."""
        self._escribir_texto([("Cargando la ley y el reglamento...\n", "apagado")])
        try:
            self.ix, self.grafo = fase4.cargar_corpus()
        except Exception as e:  # noqa: BLE001
            self._bloquear(
                "No se encuentra la copia de la ley. Avisa a Emili.",
                str(e),
            )
            return

        motor, err = fase4.preparar_motor(self.motor_nombre, silencioso=True)
        if motor is None:
            self._bloquear(en_cristiano(err), err)
            return
        self.motor = motor

        if not motor.es_modelo_real:
            self.aviso_motor.configure(
                text="MODO DE PRUEBA: las respuestas las fabrica una regla "
                     "fija, NO son una consulta real."
            )
        self._escribir_texto([
            ("Escribe tu duda, pon el año del caso y pulsa Consultar.\n\n",
             "apagado"),
            ("Esta herramienta responde solo con la Ley y el Reglamento del "
             "IVA. No incluye consultas de la DGT ni sentencias.\n", "apagado"),
        ])
        self.pie.configure(
            text=f"{len(self.ix.docs)} preceptos cargados · "
                 f"cada consulta queda guardada en el expediente"
        )
        self._revisar_boton()

    def _bloquear(self, frase: str, detalle_tecnico: str = "") -> None:
        """Deja la ventana inservible pero explicada. Nunca con una traza."""
        self.boton.configure(state="disabled")
        self._pintar_estado("NO SE PUEDE CONSULTAR", frase,
                            EST.NO_ENCONTRADO)
        self._escribir_texto([(frase + "\n", "titulo")])
        # El detalle tecnico va al log de la terminal, JAMAS a la pantalla.
        if detalle_tecnico:
            print(f"[arranque] {detalle_tecnico}", file=sys.stderr)

    # -------------------------------------------------------------- estado

    def _revisar_boton(self) -> None:
        """El boton solo se activa con duda Y ejercicio validos."""
        if self.trabajando or self.motor is None:
            return
        duda = self.caja.get("1.0", "end").strip()
        ejercicio = self.ejercicio.get().strip()
        valido = (
            ejercicio.isdigit()
            and AN.EJERCICIO_MINIMO <= int(ejercicio) <= AN.EJERCICIO_MAXIMO
        )
        self.boton.configure(state="normal" if (duda and valido) else "disabled")

    # -------------------------------------------------------------- lanzar

    def _lanzar(self) -> None:
        duda = self.caja.get("1.0", "end").strip()
        ejercicio = int(self.ejercicio.get().strip())
        self.trabajando = True
        self.boton.configure(state="disabled", text="Consultando...")
        self.boton_copiar.configure(state="disabled")
        self.copiado.configure(text="")
        self.respuesta_actual = ""
        self.panel_avisos.grid_remove()
        for w in self.panel_avisos.winfo_children():
            w.destroy()
        self.etiqueta_estado.grid_forget()
        self.etiqueta_explicacion.grid_forget()
        self._escribir_texto([])
        self.paso.pack(side="left")
        self.barra.pack(side="right", fill="x", expand=True, padx=(12, 0))
        self.barra.start(12)
        self.paso.configure(text="Preparando la consulta...")

        hilo = threading.Thread(target=self._trabajar, args=(duda, ejercicio),
                                daemon=True)
        hilo.start()

    def _trabajar(self, duda: str, ejercicio: int) -> None:
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
                                      self.grafo, progreso=progreso)
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
        except queue.Empty:
            pass
        self.raiz.after(80, self._vaciar_avisos)

    def _parar_barra(self) -> None:
        self.barra.stop()
        self.barra.pack_forget()
        self.paso.pack_forget()
        self.trabajando = False
        self.boton.configure(text="Consultar")
        self._revisar_boton()

    def _sin_nada_que_copiar(self) -> None:
        """Deja el portapapeles fuera de juego. Se llama SIEMPRE que no hay
        texto verificado en pantalla.

        `_lanzar` ya lo limpia al empezar cada consulta, asi que hoy no se
        puede llegar aqui con una respuesta vieja dentro. Se hace igual: la
        regla de que no salga texto sin verificar no puede depender de que
        alguien se acuerde de limpiar en otro sitio. Copiar es ensenar.
        """
        self.respuesta_actual = ""
        self.boton_copiar.configure(state="disabled")
        self.copiado.configure(text="")

    def _terminar_roto(self, frase: str) -> None:
        self._parar_barra()
        self._sin_nada_que_copiar()
        self._pintar_estado("NO SE HA PODIDO CONSULTAR", frase,
                            EST.NO_ENCONTRADO)
        self._escribir_texto([(frase + "\n", "titulo")])

    # ------------------------------------------------------------ pintar

    def _terminar(self, res: dict) -> None:
        self._parar_barra()

        # 1. Fallos: ni estado ni texto, solo la frase.
        if res.get("fallo"):
            frase = (en_cristiano(res.get("motivo", ""))
                     if res["fallo"] == "modelo" else FALLO_GENERICO)
            self._terminar_roto(frase)
            return
        if res["codigo"] == 3:      # falta el ejercicio: no deberia pasar aqui
            self._terminar_roto("Falta el año del caso.")
            return

        estado = res.get("estado") or EST.NO_ENCONTRADO
        self._pintar_estado(estado, EXPLICACION.get(estado, ""), estado)
        self._pintar_avisos(res.get("senales") or [],
                            res.get("cobertura") or [],
                            res.get("estructural") or "")

        # 2. El texto: SOLO si paso el verificador. `respuesta` viene vacia
        #    cuando no se puede ensenar, y entonces se ensena otra cosa.
        if res.get("respuesta"):
            self.respuesta_actual = res["respuesta"]
            self._escribir_respuesta(res["respuesta"], res)
            self.boton_copiar.configure(state="normal")
        else:
            self._sin_nada_que_copiar()
            self._escribir_sin_respaldo(res)

        self.pie.configure(
            text=f"Expediente guardado en {res.get('traza', '(sin traza)')}"
        )

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
        self.filete_estado.grid(row=0, column=0, rowspan=2, sticky="ns")
        self.etiqueta_estado.grid(row=0, column=1, sticky="ew")
        self.etiqueta_explicacion.grid(row=1, column=1, sticky="ew",
                                       pady=(0, 12))

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
            tk.Label(self.panel_avisos, text=texto, bg=PAPEL2, fg=TINTA2,
                     font=tkfont.Font(size=10, weight="bold"), anchor="w",
                     padx=12, pady=6).pack(fill="x")

        def linea(texto: str, color: str = TINTA) -> None:
            # El hueco de abajo va en el pack, NO en el Label: el `pady` de un
            # widget es una distancia sola, y una pareja (0, 4) lo revienta.
            tk.Label(self.panel_avisos, text=texto, bg=PAPEL2,
                     fg=color, font=self.fuente, anchor="w",
                     justify="left", wraplength=820,
                     padx=12).pack(fill="x", pady=(0, 4))

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
            linea(estructural, TINTA2)
        self.panel_avisos.grid()

    def _escribir_texto(self, trozos: list) -> None:
        self.texto.configure(state="normal")
        self.texto.delete("1.0", "end")
        for texto, etiqueta in trozos:
            self.texto.insert("end", texto, etiqueta)
        self.texto.configure(state="disabled")

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
        self.texto.configure(state="disabled")

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
        self.texto.configure(state="disabled")

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
        if not self.respuesta_actual:
            return
        self.raiz.clipboard_clear()
        self.raiz.clipboard_append(self.respuesta_actual)
        self.copiado.configure(text="copiado")
        self.raiz.after(2000, lambda: self.copiado.configure(text=""))


# ------------------------------------------------------------------- main


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Ventana de consulta fiscal.")
    ap.add_argument("--motor", choices=["anthropic", "ensayo"],
                    default="anthropic")
    args = ap.parse_args(argv)

    raiz = tk.Tk()
    Ventana(raiz, args.motor)
    raiz.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
