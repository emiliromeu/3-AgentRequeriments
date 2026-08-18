#!/usr/bin/env python3
"""NINGUN BOTON SE QUEDA GRIS EN SILENCIO. Cero red, cero API.

    python pruebas/prueba_boton.py

EL CASO REAL: en el PC de Windows los dos botones salian EN GRIS con la duda, el
año y la comunidad rellenados, y sin una palabra. En el Mac funcionaba.

LA ASIMETRIA NO ESTABA EN EL CODIGO, ESTABA EN QUIEN PODIA LEER EL ERROR. El
arranque va por `raiz.after`, asi que una excepcion que no cogiera nadie salia
por la traza de Tk y dejaba la ventana abierta, muda y con los botones grises.
En el Mac eso se ve en la terminal; Windows abre con `pythonw.exe`, QUE NO TIENE
CONSOLA NI stderr, y ahi no se veia en ningun sitio.

Un boton apagado sin explicacion es el peor mensaje posible: quien lo mira no
sabe si ha hecho algo mal o si la herramienta esta rota, y no tiene nada que
hacer.

LO QUE SE COMPRUEBA:
  1. Que el arranque, pase lo que pase, acaba diciendo algo.
  2. Que el boton apagado por falta de motor DICE POR QUE.
  3. Que se apagan LOS DOS, no uno.
  4. Y que la ficha de `comprobar_equipo` da la respuesta sin preguntar nada.
"""
import io
import contextlib
import sys
import tkinter as tk
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import interfaz                                  # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:110]}" if not ok else ""))
    if not ok:
        fallos.append(que)


def ventana(preparar=None):
    """Una ventana de verdad, con el arranque hecho. Devuelve (raiz, v)."""
    import time
    raiz = tk.Tk()
    raiz.withdraw()
    original = interfaz.fase4.preparar_motor
    if preparar is not None:
        interfaz.fase4.preparar_motor = preparar
    try:
        v = interfaz.Ventana(raiz, "ensayo")
        fin = time.time() + 3
        while time.time() < fin:
            raiz.update()
            raiz.update_idletasks()
            time.sleep(0.02)
        return raiz, v
    finally:
        interfaz.fase4.preparar_motor = original


# ============================== 0. LO QUE SE DICE, ¿SE VE?
print("\n=== 0. LA EXPLICACION TIENE QUE ESTAR EN LA PANTALLA QUE SE MIRA ===")
print("  ESTA SUITE DABA VERDE Y EL FALLO SEGUIA. Leia `v.texto` a pelo, y")
print("  `self.texto` vive en la vista de RESPUESTA. Al arrancar la ventana")
print("  esta en la de CONSULTA -es donde se escribe la duda- y la otra esta")
print("  quitada del grid: el mensaje se escribia entero, correcto, EN UNA")
print("  PANTALLA QUE NO SE VE. Delante quedaba el formulario con la duda, el")
print("  año, la comunidad y los dos botones en gris, sin una palabra.")
print("  Es el mismo error que dar por buena una comprobacion que en realidad")
print("  lee el comentario que explica por que algo NO se hace.\n")


def lo_que_se_ve(v) -> str:
    """Solo lo de la vista PUESTA. Lo de la otra no lo lee nadie."""
    if v.vista_consulta.grid_info():
        if not v.marco_motor.winfo_manager():
            return ""
        return v.aviso_motor.cget("text")
    return (v.etiqueta_estado.cget("text") + " " +
            v.texto.get("1.0", "end")).strip()


def con_gestor_escribiendo(v, raiz):
    """Rellena duda, año y comunidad: la situacion que se reporto."""
    v.caja.insert("1.0", "una duda cualquiera del departamento")
    v.ejercicio.set("2023")
    v.comunidad.set("Cataluña")
    with contextlib.redirect_stdout(io.StringIO()):
        v._revisar_boton()
    raiz.update()
    raiz.update_idletasks()


# LAS CAUSAS, cada una por su camino real. No se inventa ninguna: son las que
# pueden dejar el motor sin preparar con la ventana abierta igual.
def _revienta(msg):
    def f(*a, **k):
        raise RuntimeError(msg)
    return f


def _declina(err):
    def f(*a, **k):
        return None, err
    return f


CAUSAS = [
    ("pull a medias o dependencia que falta",
     {"preparar": _revienta("No module named 'anthropic'")}, "diagnostico"),
    ("no hay credencial",
     {"preparar": _declina("no se encuentra la credencial ANTHROPIC_API_KEY")},
     "Emili"),
    ("la cuenta sin saldo",
     {"preparar": _declina("your credit balance is too low")}, "saldo"),
    ("corpus incompleto o sellos que no cuadran",
     {"corpus": _revienta("el corpus no cuadra: 13 normas, se esperaban 17")},
     "vuelve a abrir"),
]

for nombre, doblado, pista in CAUSAS:
    raiz_c = tk.Tk()
    raiz_c.withdraw()
    op, oc = interfaz.fase4.preparar_motor, interfaz.fase4.cargar_corpus
    if doblado.get("preparar"):
        interfaz.fase4.preparar_motor = doblado["preparar"]
    if doblado.get("corpus"):
        interfaz.fase4.cargar_corpus = doblado["corpus"]
    try:
        import time as _t
        with contextlib.redirect_stderr(io.StringIO()):
            vc = interfaz.Ventana(raiz_c, "ensayo")
            fin = _t.time() + 4
            while _t.time() < fin:
                raiz_c.update()
                raiz_c.update_idletasks()
                _t.sleep(0.02)
            con_gestor_escribiendo(vc, raiz_c)
        visto = lo_que_se_ve(vc)
        comprobar(f"«{nombre}»: se ve algo en la pantalla puesta", bool(visto),
                  "NADA: boton gris en silencio")
        comprobar(f"   y dice SU causa, no una generica", pista in visto,
                  visto[:100])
        comprobar("   con los dos botones apagados",
                  str(vc.boton.cget("state")) == "disabled"
                  and (vc.boton_criterio is None
                       or str(vc.boton_criterio.cget("state")) == "disabled"))
    finally:
        interfaz.fase4.preparar_motor, interfaz.fase4.cargar_corpus = op, oc
        raiz_c.destroy()


# ==================================== 1. EL ARRANQUE SIEMPRE DICE ALGO
print("\n=== 1. UNA EXCEPCION EN EL ARRANQUE NO PUEDE DEJARLO MUDO ===")
print("  Es el caso de Windows: sin consola, la traza no la lee nadie.\n")


def revienta(*a, **k):
    raise RuntimeError("algo que nadie previo")


raiz, v = ventana(preparar=revienta)
try:
    texto = v.texto.get("1.0", "end")
    comprobar("la ventana NO se queda muda", texto.strip() != "", repr(texto[:60]))
    comprobar("  y dice que no ha podido prepararse",
              "no ha podido prepararse" in texto, texto[:120])
    comprobar("  y manda al diagnostico, que deja un fichero que se envia",
              "diagnostico" in texto, texto[:160])
    comprobar("los dos botones quedan apagados",
              str(v.boton.cget("state")) == "disabled"
              and (v.boton_criterio is None
                   or str(v.boton_criterio.cget("state")) == "disabled"),
              (v.boton.cget("state"),
               v.boton_criterio.cget("state") if v.boton_criterio else "-"))
    fallo = RAIZ / "datos" / "arranque_fallido.txt"
    comprobar("y el detalle queda EN DISCO, que es lo unico legible sin consola",
              fallo.is_file() and "algo que nadie previo" in
              fallo.read_text(encoding="utf-8"), fallo)
finally:
    raiz.destroy()


# ==================================== 2. EL BOTON DICE POR QUE
print("\n=== 2. EL BOTON APAGADO EXPLICA POR QUE ===")
print("  Antes `_revisar_boton` se volvia en silencio si no habia motor, asi")
print("  que se podia escribir la duda entera y no pasaba nada.\n")

raiz2 = tk.Tk()
raiz2.withdraw()
try:
    v2 = interfaz.Ventana(raiz2, "ensayo")
    v2.motor = None
    v2.caja.insert("1.0", "una duda cualquiera con su año")
    v2.ejercicio.set("2024")
    with contextlib.redirect_stdout(io.StringIO()):
        v2._revisar_boton()
    comprobar("con la duda y el año puestos y sin motor, el boton sigue "
              "apagado", str(v2.boton.cget("state")) == "disabled",
              v2.boton.cget("state"))
    # Lo que se mira es el ROTULO DE ESTADO, que es lo que la ventana pinta
    # cuando no se puede consultar. La cinta tambien avisa, pero el rotulo es
    # lo que queda fijo delante de quien mira los botones.
    rotulo = v2.etiqueta_estado.cget("text")
    comprobar("  PERO la ventana lo explica: el rotulo lo dice",
              "NO SE PUEDE CONSULTAR" in str(rotulo), rotulo)
finally:
    raiz2.destroy()


# ==================================== 3. LOS DOS, NO UNO
print("\n=== 3. SE APAGAN LOS DOS BOTONES ===")
print("  `_bloquear` apagaba solo el primero: la ventana decia «no se puede")
print("  consultar» y dejaba el segundo pulsable sobre un motor que no hay.\n")

raiz3 = tk.Tk()
raiz3.withdraw()
try:
    v3 = interfaz.Ventana(raiz3, "ensayo")
    v3._bloquear("una causa cualquiera")
    comprobar("el primero se apaga", str(v3.boton.cget("state")) == "disabled")
    comprobar("y el de criterio TAMBIEN",
              v3.boton_criterio is None
              or str(v3.boton_criterio.cget("state")) == "disabled",
              v3.boton_criterio.cget("state") if v3.boton_criterio else "-")
finally:
    raiz3.destroy()


# ============ 3bis. LOS BOTONES NUEVOS NO AÑADEN OTRO CAMINO MUDO
print("\n=== 3bis. CONTINUAR Y ESCRIBIR PARA EL CLIENTE ===")
print("  Los dos son nuevos, y los dos pueden no hacer nada al pulsarlos.")
print("  Un boton que se puede pulsar y se queda quieto es PEOR que uno")
print("  apagado: apagado al menos se ve que no toca.\n")

raiz3 = tk.Tk()
raiz3.withdraw()
try:
    import time as _t3
    with contextlib.redirect_stderr(io.StringIO()):
        v3 = interfaz.Ventana(raiz3, "ensayo")
        fin = _t3.time() + 4
        while _t3.time() < fin:
            raiz3.update()
            raiz3.update_idletasks()
            _t3.sleep(0.02)

    def pulsar(f, *a):
        """Pulsa y devuelve lo que se ve DESPUES. La cinta se limpia antes
        para no dar por bueno un mensaje que ya estaba puesto."""
        v3.aviso_motor.configure(text="")
        v3.marco_motor.pack_forget()
        with contextlib.redirect_stdout(io.StringIO()):
            f(*a)
        raiz3.update()
        return (v3.aviso_motor.cget("text")
                if v3.marco_motor.winfo_manager() else "")

    # A · SEGUIR sin nada escrito.
    v3.traza_actual = "/una/traza"
    v3.trabajando = False
    dicho = pulsar(v3._seguir)
    comprobar("seguir con la caja vacia lo DICE", bool(dicho), "no dice nada")
    comprobar("  y manda a escribir algo", "Escribe primero" in dicho, dicho[:80])

    # B · SEGUIR mientras hay una consulta en marcha.
    v3.caja_seguir.insert("1.0", "y si fuera una furgoneta")
    v3.trabajando = True
    dicho = pulsar(v3._seguir)
    comprobar("seguir con una consulta en marcha lo DICE", bool(dicho),
              "no dice nada")
    v3.trabajando = False

    # C · SEGUIR sin expediente: el disco lleno.
    v3.traza_actual = ""
    dicho = pulsar(v3._seguir)
    comprobar("seguir sin expediente lo DICE", bool(dicho), "no dice nada")
    comprobar("  y dice la causa probable", "disco lleno" in dicho, dicho[:90])

    # D · SEGUIR con la ventana bloqueada.
    v3.traza_actual = "/una/traza"
    v3.bloqueada = True
    dicho = pulsar(v3._seguir)
    comprobar("seguir con el agente sin preparar lo DICE", bool(dicho),
              "no dice nada")
    comprobar("  y manda al diagnostico, que deja un fichero que se envia",
              "diagnostico" in dicho, dicho[:90])
    v3.bloqueada = False

    # E · ESCRIBIR PARA EL CLIENTE, los mismos.
    v3.traza_actual = ""
    dicho = pulsar(v3._escribir_para_cliente)
    comprobar("reescribir sin expediente lo DICE", bool(dicho), "no dice nada")
    v3.traza_actual = "/una/traza"
    v3.trabajando = True
    dicho = pulsar(v3._escribir_para_cliente)
    comprobar("reescribir con algo en marcha lo DICE", bool(dicho),
              "no dice nada")
    v3.trabajando = False
    v3.motor = None
    dicho = pulsar(v3._escribir_para_cliente)
    comprobar("reescribir sin motor lo DICE", bool(dicho), "no dice nada")
    comprobar("  y manda al diagnostico, que deja un fichero que se envia",
              "diagnostico" in dicho, dicho[:90])

    # F · UNA RESPUESTA BUENA SIN EXPEDIENTE. El disco lleno: la respuesta
    # vale, pero no hay carpeta de donde reescribir.
    v3.motor = object()
    v3.aviso_motor.configure(text="")
    v3.marco_motor.pack_forget()
    with contextlib.redirect_stdout(io.StringIO()):
        v3.avisos.put(("hecho", {
            "estado": "CRITERIO CLARO", "respuesta": "un texto cualquiera",
            "traza": "", "expediente": False, "preceptos": [],
            "preceptos_enviados": [], "analisis": {}, "senales": [],
            "cobertura": [], "consumo": {}, "con_criterio": False,
            "codigo": 0, "motor": "ensayo", "ejercicio": 2023,
            "preceptos_descartados": [], "aporte": {}, "estructural": "",
            "recuperado": {}, "intentos": 1, "reintentos": 0,
            "cobertura_territorial": "", "comunidad": "", "pregunta": "x",
            "sin_copia_local": False, "aviso_expediente": ""}))
        v3._vaciar_avisos()
    raiz3.update()
    comprobar("con respuesta pero SIN expediente, reescribir queda apagado",
              str(v3.boton_cliente.cget("state")) == "disabled",
              v3.boton_cliente.cget("state"))
    visible3 = (v3.aviso_motor.cget("text")
                if v3.marco_motor.winfo_manager() else "")
    comprobar("  y se explica en vez de quedarse gris en silencio",
              "expediente" in visible3, visible3[:110])
    comprobar("  diciendo que la respuesta de arriba SI vale",
              "válida" in visible3, visible3[:110])
finally:
    raiz3.destroy()


# ==================================== 4. LA FICHA CONTESTA SOLA
print("\n=== 4. LA FICHA DE comprobar_equipo DICE POR QUE, SIN PREGUNTAR ===")

import comprobar_equipo as CE                    # noqa: E402

salida = io.StringIO()
with contextlib.redirect_stdout(salida):
    CE.ficha()
f = salida.getvalue()
for que, marca in (("el commit del equipo", "version"),
                   ("cuantas normas tiene", "normas"),
                   ("si los sellos cuadran", "sellos"),
                   ("si la credencial vale", "credencial"),
                   ("y POR QUE esta el boton apagado", "BOTON")):
    comprobar(f"la ficha dice {que}", marca in f, f[:80])
comprobar("avisa si el pull se quedo a medias",
          "sin guardar" in f or "version" in f)
comprobar("y NO gasta: la credencial se mira, no se usa",
          "NO se usa" in f)

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f_ in fallos:
    print("  -", f_)
sys.exit(1 if fallos else 0)
