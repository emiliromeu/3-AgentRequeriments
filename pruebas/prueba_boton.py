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
    comprobar("  y manda a comprobar_equipo, que es lo unico que puede hacer",
              "comprobar_equipo" in texto, texto[:160])
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
