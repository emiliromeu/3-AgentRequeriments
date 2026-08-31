#!/usr/bin/env python3
"""EL ARRANQUE QUE FALLA LO DICE, EN LA PANTALLA QUE SE MIRA. Cero red, cero API.

    python pruebas/prueba_arranque.py

ANTES SE LLAMABA `prueba_boton`, y el nombre contaba el sintoma -«ningun boton
se queda gris en silencio»- en vez de lo que protege. Lo que protege es que
una ventana que NO HA PODIDO PREPARARSE lo diga, y lo diga donde se esta
mirando.

EL CASO REAL: en el PC de Windows los dos botones salian EN GRIS con la duda,
el año y la comunidad rellenados, y sin una palabra. En el Mac funcionaba.

LA ASIMETRIA NO ESTABA EN EL CODIGO, ESTABA EN QUIEN PODIA LEER EL ERROR. El
arranque va por `raiz.after`, asi que una excepcion que no cogiera nadie salia
por la traza de Tk y dejaba la ventana abierta, muda y con los botones grises.
En el Mac eso se ve en la terminal; Windows abre con `pythonw.exe`, QUE NO
TIENE CONSOLA NI stderr, y ahi no se veia en ningun sitio.

POR QUE SIGUE SIENDO UNA SUITE APARTE, Y NO SE FUNDIO EN `prueba_interfaz`
-31/08/2026-. Al repasarlas se propuso disolverla entera. Se pudo mudar lo que
NO era suyo:

    §3    los dos botones se apagan juntos   -> prueba_interfaz, preguntando
    §3bis las nueve pulsaciones mudas        -> prueba_interfaz, sin ventana
    §4    la ficha de comprobar_equipo       -> prueba_equipo, cero ventanas

Y lo que queda NO SE PUEDE MUDAR: estos tres bloques DOBLAN `preparar_motor` y
`cargar_corpus` ANTES de construir la ventana, porque el fallo esta en el
arranque. Necesitan una ventana que nazca rota, y eso no se puede hacer con la
ventana ya construida de otra suite. Meterlos alli no quitaria ni una ventana:
las mudaria de fichero y mezclaria «lo que se ve cuando funciona» con «lo que
se ve cuando no arranca», que son dos preguntas distintas.

Menos suites es un medio, no el objetivo. El objetivo era menos ventanas y
menos acoplamiento a los widgets, y las dos cosas se consiguen aqui: de OCHO
ventanas Tk en la suite vieja a SEIS, y leyendo la pantalla con
`cintas_visibles()` en vez de hurgando en `aviso_motor`.
"""
import contextlib
import io
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import tkinter as tk  # noqa: E402

import interfaz  # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:104]}" if not ok else ""))
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
    """Solo lo de la vista PUESTA. Lo de la otra no lo lee nadie.

    SE PREGUNTA A LA VENTANA, NO A UNA ETIQUETA: desde que la cinta apila
    -veinte sitios escriben en ella y al arrancar puede haber cinco cosas que
    decir-, `aviso_motor` es solo la fila de «ahora».
    """
    if v.vista_consulta.grid_info():
        return "  ".join(v.cintas_visibles())
    return (v.estado_en_pantalla()["rotulo"] + " " + v.lo_que_se_lee()).strip()


def con_gestor_escribiendo(v, raiz):
    """Rellena duda, año y comunidad: la situacion que se reporto."""
    v.caja.insert("1.0", "una duda cualquiera del departamento")
    v.ejercicio.set("2023")
    v.comunidad.set("Cataluña")
    with contextlib.redirect_stdout(io.StringIO()):
        v._revisar_boton()
    raiz.update()
    raiz.update_idletasks()


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
    """Solo lo de la vista PUESTA. Lo de la otra no lo lee nadie.

    SE PREGUNTA A LA VENTANA, NO A UNA ETIQUETA. Cambiado el 29/08/2026.
    Desde que la cinta apila -veinte sitios escriben en ella y al arrancar
    puede haber cinco cosas que decir-, `aviso_motor` es solo la fila de
    «ahora»: los avisos de estado tienen fila propia. Leer esa etiqueta sola
    daba «no dice nada» sobre una pantalla que estaba diciendo justo lo que
    esta suite existe para exigir.
    """
    if v.vista_consulta.grid_info():
        return "  ".join(v.cintas_visibles())
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




print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f_ in fallos:
    print("  -", f_)
sys.exit(1 if fallos else 0)
