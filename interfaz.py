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
CLARO_CON_DGT = (
    "La ley y el reglamento no se contradicen, y el criterio de la DGT que "
    "hay en la herramienta va en la misma linea. NO incluye los tribunales, "
    "y el criterio puede cambiar: comprueba las citas antes de decidir."
)

EXPLICACION = {
    EST.CLARO: (CLARO_CON_DGT if textos_con_dgt() else CLARO_SIN_DGT),
    EST.DISCUTIDO: (
        "Los textos encontrados apuntan a soluciones distintas, o hay avisos "
        "que no se han podido cerrar. Lee los avisos de arriba y comprueba las "
        "citas antes de decidir: aqui no hay un criterio unico."
    ),
    EST.NO_ENCONTRADO: (
        "No hay respaldo suficiente. Abajo tienes los articulos encontrados "
        "para mirarlos tu."
    ),
}

COLOR = {
    EST.CLARO: "#1b5e20",
    EST.DISCUTIDO: "#8a5300",
    EST.NO_ENCONTRADO: "#7a1f1f",
}
FONDO = {
    EST.CLARO: "#e8f5e9",
    EST.DISCUTIDO: "#fff6e0",
    EST.NO_ENCONTRADO: "#fdecea",
}

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
        raiz.configure(bg="#f4f4f4")

        self.fuente = tkfont.nametofont("TkDefaultFont").copy()
        self.fuente.configure(size=11)
        self.fuente_texto = tkfont.Font(family="Georgia", size=12)
        self.fuente_estado = tkfont.Font(size=15, weight="bold")

        self._construir()
        raiz.after(80, self._vaciar_avisos)
        # El corpus tarda un segundo en cargar: se hace despues de pintar la
        # ventana para que no parezca que no ha arrancado.
        raiz.after(120, self._arrancar_motor)

    # ------------------------------------------------------------ montaje

    def _construir(self) -> None:
        marco = tk.Frame(self.raiz, bg="#f4f4f4", padx=16, pady=12)
        marco.pack(fill="both", expand=True)
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(6, weight=1)

        cabecera = tk.Label(
            marco, text="Consulta fiscal sobre el IVA", bg="#f4f4f4",
            font=tkfont.Font(size=16, weight="bold"), anchor="w",
        )
        cabecera.grid(row=0, column=0, sticky="ew")

        self.aviso_motor = tk.Label(
            marco, text="", bg="#f4f4f4", fg="#7a1f1f", anchor="w",
            font=self.fuente,
        )
        self.aviso_motor.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        # --- la duda ---
        tk.Label(marco, text="Tu duda", bg="#f4f4f4", font=self.fuente,
                 anchor="w").grid(row=2, column=0, sticky="ew")
        self.caja = tk.Text(marco, height=4, wrap="word", font=self.fuente,
                            relief="solid", borderwidth=1, padx=8, pady=6)
        self.caja.grid(row=3, column=0, sticky="ew", pady=(2, 10))
        self.caja.bind("<KeyRelease>", lambda _e: self._revisar_boton())

        # --- ejercicio + boton ---
        fila = tk.Frame(marco, bg="#f4f4f4")
        fila.grid(row=4, column=0, sticky="ew")
        tk.Label(fila, text="Ejercicio (el año del caso):", bg="#f4f4f4",
                 font=self.fuente).pack(side="left")
        self.ejercicio = tk.StringVar()
        self.ejercicio.trace_add("write", lambda *_: self._revisar_boton())
        self.caja_ejercicio = tk.Entry(fila, textvariable=self.ejercicio,
                                       width=8, font=self.fuente,
                                       relief="solid", borderwidth=1)
        self.caja_ejercicio.pack(side="left", padx=(8, 12))
        # Se deja VACIO a proposito. Ver la regla 2 de la cabecera.
        tk.Label(fila, text="obligatorio: la ley cambia cada año",
                 bg="#f4f4f4", fg="#666", font=self.fuente).pack(side="left")

        self.boton = tk.Button(fila, text="Consultar", font=self.fuente,
                               command=self._lanzar, state="disabled",
                               padx=18, pady=4)
        self.boton.pack(side="right")

        # --- progreso ---
        self.marco_progreso = tk.Frame(marco, bg="#f4f4f4")
        self.marco_progreso.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        self.barra = ttk.Progressbar(self.marco_progreso, mode="indeterminate")
        self.paso = tk.Label(self.marco_progreso, text="", bg="#f4f4f4",
                             fg="#333", font=self.fuente, anchor="w")

        # --- resultado ---
        self.resultado = tk.Frame(marco, bg="#f4f4f4")
        self.resultado.grid(row=6, column=0, sticky="nsew", pady=(12, 0))
        self.resultado.columnconfigure(0, weight=1)
        self.resultado.rowconfigure(3, weight=1)

        self.panel_estado = tk.Frame(self.resultado, bg="#f4f4f4")
        self.panel_estado.grid(row=0, column=0, sticky="ew")
        self.panel_estado.columnconfigure(0, weight=1)
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
        self.panel_avisos = tk.Frame(self.resultado, bg="#fff8e1")
        self.panel_avisos.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.panel_avisos.grid_remove()

        barra_acciones = tk.Frame(self.resultado, bg="#f4f4f4")
        barra_acciones.grid(row=2, column=0, sticky="ew", pady=(10, 4))
        self.boton_copiar = tk.Button(barra_acciones, text="Copiar respuesta",
                                      font=self.fuente, command=self._copiar,
                                      state="disabled")
        self.boton_copiar.pack(side="left")
        self.copiado = tk.Label(barra_acciones, text="", bg="#f4f4f4",
                                fg="#1b5e20", font=self.fuente)
        self.copiado.pack(side="left", padx=8)

        caja = tk.Frame(self.resultado)
        caja.grid(row=3, column=0, sticky="nsew")
        caja.columnconfigure(0, weight=1)
        caja.rowconfigure(0, weight=1)
        self.texto = tk.Text(caja, wrap="word", font=self.fuente_texto,
                             relief="solid", borderwidth=1, padx=14, pady=12,
                             state="disabled", spacing1=2, spacing3=6,
                             background="white")
        self.texto.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(caja, command=self.texto.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.texto.configure(yscrollcommand=scroll.set)

        self.texto.tag_configure("enlace", foreground="#0b57d0",
                                 underline=True)
        self.texto.tag_bind("enlace", "<Enter>",
                            lambda _e: self.texto.configure(cursor="hand2"))
        self.texto.tag_bind("enlace", "<Leave>",
                            lambda _e: self.texto.configure(cursor=""))
        self.texto.tag_bind("enlace", "<Button-1>", self._abrir_enlace)
        self.texto.tag_configure("titulo", font=tkfont.Font(size=12,
                                                            weight="bold"))
        self.texto.tag_configure("apagado", foreground="#555")

        self.pie = tk.Label(marco, text="", bg="#f4f4f4", fg="#777",
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
        self._pintar_avisos(res.get("senales") or [])

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
        self.etiqueta_estado.configure(
            text=titulo, fg=COLOR.get(clave, "#333"),
            bg=FONDO.get(clave, "#eee"),
        )
        self.etiqueta_explicacion.configure(
            text=explicacion, bg=FONDO.get(clave, "#eee"), fg="#333",
        )
        self.panel_estado.configure(bg=FONDO.get(clave, "#eee"))
        self.etiqueta_estado.grid(row=0, column=0, sticky="ew")
        self.etiqueta_explicacion.grid(row=1, column=0, sticky="ew",
                                       pady=(0, 8))

    def _pintar_avisos(self, senales: list) -> None:
        for w in self.panel_avisos.winfo_children():
            w.destroy()
        if not senales:
            self.panel_avisos.grid_remove()
            return
        tk.Label(self.panel_avisos, text="AVISOS", bg="#fff8e1", fg="#8a5300",
                 font=tkfont.Font(size=10, weight="bold"), anchor="w",
                 padx=12, pady=6).pack(fill="x")
        for s in senales:
            # El hueco de abajo va en el pack, NO en el Label: el `pady` de un
            # widget es una distancia sola, y una pareja (0, 4) lo revienta.
            tk.Label(self.panel_avisos, text="• " + s, bg="#fff8e1",
                     fg="#5d4200", font=self.fuente, anchor="w",
                     justify="left", wraplength=820,
                     padx=12).pack(fill="x", pady=(0, 4))
        self.panel_avisos.grid()

    def _escribir_texto(self, trozos: list) -> None:
        self.texto.configure(state="normal")
        self.texto.delete("1.0", "end")
        for texto, etiqueta in trozos:
            self.texto.insert("end", texto, etiqueta)
        self.texto.configure(state="disabled")

    def _escribir_respuesta(self, cuerpo: str, res: dict) -> None:
        """El texto verificado, con los enlaces del BOE pinchables."""
        self.texto.configure(state="normal")
        self.texto.delete("1.0", "end")
        self._enlaces: dict[str, str] = {}
        pos = 0
        for i, m in enumerate(RE_ENLACE.finditer(cuerpo)):
            self.texto.insert("end", cuerpo[pos:m.start()])
            etiqueta = f"url{i}"
            self._enlaces[etiqueta] = m.group(0)
            self.texto.insert("end", m.group(0), ("enlace", etiqueta))
            pos = m.end()
        self.texto.insert("end", cuerpo[pos:])

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
