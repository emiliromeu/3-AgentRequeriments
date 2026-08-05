#!/usr/bin/env python3
"""LA CLAVE SE PIDE EN UNA VENTANA, NO EN LA CONSOLA.

POR QUE EXISTE ESTE FICHERO. En Windows, `getpass` no lee de stdin ni escribe
en stdout: usa `msvcrt.putwch` y `msvcrt.getwch`, que hablan DIRECTAMENTE con la
consola. Tres consecuencias, y las tres se notaron en un PC de verdad:

  1. el prompt sale por un canal distinto que el resto del texto, asi que puede
     no verse donde toca -o no verse-;
  2. no se ve nada al escribir, asi que quien pega una clave no sabe si se ha
     pegado: la pantalla parece parada;
  3. `getwch()` lee teclas crudas. Si la consola no tiene el atajo activado,
     Ctrl+V no pega: mete un `\\x16` DENTRO de la clave, y el fallo aparece
     despues, sin que nadie entienda por que.

El arreglo no es afinar `getpass`, es dejar de depender de el. Una ventana de
tkinter no usa `msvcrt`, tiene pegado nativo, puede ensenar lo que se escribe y
puede decir el error sin cerrarse.

TKINTER SE PUEDE DAR POR SEGURO AQUI: la aplicacion es una ventana de tkinter,
asi que si no estuviera no habria nada que instalar. Aun asi, si no hay entorno
grafico se cae a la consola, que es mejor que no poder instalar.

Este modulo NO importa nada de fuera de la libreria estandar: corre ANTES de
que se hayan instalado las dependencias.
"""

from __future__ import annotations

TITULO = "Consulta fiscal — clave de acceso"

EXPLICACION = (
    "El agente habla con Claude, y para eso necesita una clave de acceso.\n"
    "Es un texto largo que empieza por  sk-ant-  y se saca asi:\n"
    "\n"
    "    1.  Entra en   https://platform.claude.com\n"
    "    2.  Menu «API keys»  →  «Create key»\n"
    "    3.  Le pones un nombre, la creas y la copias\n"
    "\n"
    "Pegala aqui con Ctrl+V. Se guarda SOLO en este equipo, en un fichero que "
    "no se comparte ni se sube a ningun sitio."
)

# Paleta, la misma de la ventana del agente: esto es lo primero que ve alguien
# de la herramienta, y que parezca otra cosa no ayuda.
PAPEL = "#EFEEF3"
PAPEL2 = "#FFFFFF"
TINTA = "#17171D"
TINTA2 = "#4A4A55"
FILETE = "#DCDBE3"
LILA = "#5D3FCB"


def hay_entorno_grafico() -> bool:
    """¿Se puede abrir una ventana? Se comprueba ABRIENDO una, no suponiendo.

    Es la unica prueba que vale: que `import tkinter` funcione no dice nada de
    si hay pantalla donde dibujar.
    """
    try:
        import tkinter as tk
    except Exception:  # noqa: BLE001
        return False
    try:
        raiz = tk.Tk()
        raiz.withdraw()
        raiz.destroy()
        return True
    except Exception:  # noqa: BLE001
        return False


class _Dialogo:
    """La ventana. Se queda abierta hasta que la clave vale o se cancela."""

    def __init__(self, tk, comprobador, guardar):
        import queue

        self.tk = tk
        self.comprobador = comprobador
        self.guardar = guardar
        self.clave = ""
        self.cancelado = False
        self.comprobando = False
        # Por aqui vuelve el resultado del hilo que comprueba la clave.
        self.respuestas: "queue.Queue[tuple]" = queue.Queue()

        self.raiz = tk.Tk()
        self.raiz.title(TITULO)
        self.raiz.configure(bg=PAPEL)
        self.raiz.minsize(600, 400)
        self.raiz.protocol("WM_DELETE_WINDOW", self._cancelar)

        marco = tk.Frame(self.raiz, bg=PAPEL, padx=26, pady=22)
        marco.pack(fill="both", expand=True)

        tk.Label(marco, text="Falta la clave de acceso", bg=PAPEL, fg=TINTA,
                 font=("Helvetica", 16, "bold"), anchor="w",
                 justify="left").pack(fill="x")
        tk.Label(marco, text="Esto se pide una vez. Despues no vuelve a "
                             "aparecer.", bg=PAPEL, fg=TINTA2,
                 font=("Helvetica", 11), anchor="w",
                 justify="left").pack(fill="x", pady=(2, 14))

        caja = tk.Frame(marco, bg=PAPEL2, highlightthickness=1,
                        highlightbackground=FILETE)
        caja.pack(fill="x", pady=(0, 16))
        tk.Label(caja, text=EXPLICACION, bg=PAPEL2, fg=TINTA,
                 font=("Helvetica", 11), justify="left", anchor="w",
                 padx=16, pady=14, wraplength=560).pack(fill="x")

        self.valor = tk.StringVar()
        self.entrada = tk.Entry(marco, textvariable=self.valor, show="•",
                                font=("Menlo", 13), width=48,
                                bg=PAPEL2, fg=TINTA, insertbackground=TINTA,
                                highlightthickness=1,
                                highlightbackground=FILETE,
                                highlightcolor=LILA, relief="flat")
        self.entrada.pack(fill="x", ipady=8)

        fila = tk.Frame(marco, bg=PAPEL)
        fila.pack(fill="x", pady=(8, 0))
        self.ver = tk.IntVar(value=0)
        tk.Checkbutton(fila, text="Mostrar lo que escribo", variable=self.ver,
                       command=self._alternar_visible, bg=PAPEL, fg=TINTA2,
                       activebackground=PAPEL, selectcolor=PAPEL2,
                       font=("Helvetica", 11)).pack(side="left")

        self.aviso = tk.Label(marco, text="", bg=PAPEL, fg=TINTA2,
                              font=("Helvetica", 11), anchor="w",
                              justify="left", wraplength=560)
        self.aviso.pack(fill="x", pady=(12, 0))

        botones = tk.Frame(marco, bg=PAPEL)
        botones.pack(fill="x", pady=(16, 0))
        self.boton = tk.Button(botones, text="Comprobar y guardar",
                               command=self._aceptar, font=("Helvetica", 12),
                               state="disabled")
        self.boton.pack(side="right")
        tk.Button(botones, text="Ahora no", command=self._cancelar,
                  font=("Helvetica", 12)).pack(side="right", padx=(0, 8))

        # PEGAR TIENE QUE FUNCIONAR. La clave se copia de la web de Anthropic;
        # nadie la teclea. Tk ya trae el atajo de cada sistema, pero se anaden
        # los tres a mano porque el que falte es justo el que use la oficina.
        # Se devuelve "break" para que el atajo propio de Tk no pegue OTRA vez.
        for atajo in ("<Control-v>", "<Control-V>", "<Command-v>"):
            self.entrada.bind(atajo, self._pegar)
        self.entrada.bind("<Return>", lambda _e: self._aceptar())
        self.valor.trace_add("write", lambda *_a: self._revisar())

        self.entrada.focus_set()
        self.raiz.bind("<Escape>", lambda _e: self._cancelar())
        self._centrar()
        self.raiz.after(80, self._vaciar_respuestas)

    # ------------------------------------------------------------ acciones

    def _centrar(self) -> None:
        self.raiz.update_idletasks()
        an, al = self.raiz.winfo_width(), self.raiz.winfo_height()
        x = (self.raiz.winfo_screenwidth() - an) // 2
        y = (self.raiz.winfo_screenheight() - al) // 3
        self.raiz.geometry(f"+{max(0, x)}+{max(0, y)}")
        try:
            self.raiz.lift()
            self.raiz.attributes("-topmost", True)
            self.raiz.after(400, lambda: self.raiz.attributes("-topmost", False))
        except Exception:  # noqa: BLE001
            pass

    def _pegar(self, _evento=None):
        try:
            texto = self.raiz.clipboard_get()
        except Exception:  # noqa: BLE001
            return "break"
        try:
            self.entrada.delete("sel.first", "sel.last")
        except Exception:  # noqa: BLE001
            pass
        # Una clave pegada de una web puede traer salto de linea o espacios
        # alrededor. Se limpian aqui: es exactamente el fallo que nadie ve.
        self.entrada.insert("insert", " ".join(texto.split()))
        return "break"

    def _alternar_visible(self) -> None:
        self.entrada.configure(show="" if self.ver.get() else "•")

    def _revisar(self) -> None:
        """El boton solo se enciende cuando hay algo que comprobar."""
        if self.comprobando:
            return
        clave = self.valor.get().strip()
        self.boton.configure(state=("normal" if clave else "disabled"))
        if clave and not clave.startswith("sk-"):
            self._decir("Las claves empiezan por  sk-ant- . Comprueba que la "
                        "has copiado entera.", TINTA2)
        else:
            self._decir("")

    def _decir(self, texto: str, color: str = TINTA2) -> None:
        self.aviso.configure(text=texto, fg=color)

    def _aceptar(self) -> None:
        if self.comprobando:
            return
        clave = self.valor.get().strip()
        if not clave:
            return
        self.comprobando = True
        self.boton.configure(state="disabled", text="Comprobando...")
        self._decir("Preguntando si la clave funciona. Un momento.")
        self.raiz.update_idletasks()

        # La comprobacion sale a la red y tarda. Va en un hilo para que la
        # ventana no se quede congelada: una ventana congelada se cierra.
        #
        # EL RESULTADO VUELVE POR UNA COLA, NO LLAMANDO A `after` DESDE EL HILO.
        # Tkinter no es reentrante: `after` desde un hilo que no es el suyo se
        # pierde en silencio, y la ventana se queda con «Comprobando...» para
        # siempre. Es el mismo patron que usa `interfaz.py`, y por el mismo
        # motivo.
        import threading

        def trabajo():
            try:
                self.guardar(clave)
                vale, motivo = self.comprobador()
            except Exception:  # noqa: BLE001
                vale, motivo = False, ("No se ha podido comprobar la clave. "
                                       "Suele ser falta de conexion a internet.")
            self.respuestas.put((clave, vale, motivo))

        threading.Thread(target=trabajo, daemon=True).start()

    def _vaciar_respuestas(self) -> None:
        """El hilo de la ventana, y solo el, recoge lo que dejo el otro."""
        import queue

        try:
            while True:
                self._resultado(*self.respuestas.get_nowait())
        except queue.Empty:
            pass
        except Exception:  # noqa: BLE001
            return
        try:
            self.raiz.after(80, self._vaciar_respuestas)
        except Exception:  # noqa: BLE001
            pass          # la ventana ya no esta: no hay nada que recoger

    def _resultado(self, clave: str, vale: bool, motivo: str) -> None:
        self.comprobando = False
        self.boton.configure(text="Comprobar y guardar", state="normal")
        if vale:
            self.clave = clave
            self.raiz.destroy()
            return
        # NO SE CIERRA. Se dice aqui mismo y se deja reintentar: descubrirlo
        # despues, en la primera consulta, es lo que esto viene a evitar.
        self._decir(motivo, "#8A2E2E")
        self.entrada.focus_set()
        self.entrada.select_range(0, "end")

    def _cancelar(self) -> None:
        self.cancelado = True
        self.raiz.destroy()

    def correr(self) -> str:
        self.raiz.mainloop()
        return self.clave


def pedir_clave(comprobador, guardar) -> tuple:
    """(clave, cancelado). «» y True si la persona lo deja para luego.

    `guardar(clave)` la escribe donde toque y `comprobador()` dice si sirve.
    Se pasan de fuera para que este modulo no sepa nada del .env ni de la API:
    aqui solo hay ventana.
    """
    import tkinter as tk

    d = _Dialogo(tk, comprobador, guardar)
    clave = d.correr()
    return clave, d.cancelado
