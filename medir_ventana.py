#!/usr/bin/env python3
"""CUANTA PANTALLA SE LLEVA CADA COSA, CON UNA RESPUESTA REAL DENTRO.

    python medir_ventana.py                 el expediente por defecto
    python medir_ventana.py 20260805T224913 o el que se le diga

Cero red y cero API: la respuesta sale de un expediente ya guardado, por
`ver_ejemplo.cargar`, que es el mismo camino que usa la ventana de verdad.

POR QUE EXISTE. La respuesta «se ve apretada, y con media pagina inutil
abajo». Van tres intentos de arreglarlo retocando margenes y ninguno ha
funcionado, asi que antes de tocar nada mas hay que MIRAR: cuantas lineas de
respuesta caben sin desplazar, que proporcion de la ventana se lleva la
respuesta y que proporcion todo lo demas, y que hay exactamente en esa media
pagina de abajo. Discutir espaciados sin estos numeros es lo que ya ha fallado
tres veces.

La ventana se maximiza, que es como se usa.
"""
import sys
import tkinter as tk
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import interfaz            # noqa: E402
import ver_ejemplo         # noqa: E402


def _maximizar(raiz: tk.Tk) -> None:
    """Como la maximiza una persona. `zoomed` no existe en Mac; ahi se pone a
    la pantalla entera a mano, que es lo que hace el boton verde."""
    try:
        raiz.state("zoomed")
    except tk.TclError:
        raiz.geometry(f"{raiz.winfo_screenwidth()}x{raiz.winfo_screenheight()}+0+0")
    raiz.update()
    raiz.update_idletasks()


def _alto_visible_y_total(texto: tk.Text) -> tuple:
    """Lineas de PANTALLA -no de parrafo- que se ven y que hay en total."""
    visibles = 0
    indice = texto.index("@0,0")
    while True:
        caja = texto.dlineinfo(indice)
        if caja is None:
            break
        visibles += 1
        siguiente = texto.index(f"{indice} + 1 display line")
        if siguiente == indice:
            break
        indice = siguiente
    primera, ultima = texto.yview()
    proporcion = max(ultima - primera, 1e-9)
    return visibles, round(visibles / proporcion)


def medir(expediente: str) -> int:
    res, faltan = ver_ejemplo.cargar(expediente)
    if res is None:
        for f in faltan:
            print("  ", f)
        return 1
    for f in faltan:
        print(f"  (aviso) {f}")

    raiz = tk.Tk()
    v = interfaz.Ventana(raiz, "ensayo")
    _maximizar(raiz)
    # Se pinta igual que en `ver_ejemplo`: la pregunta y el año del propio
    # expediente, y `_terminar` con el resultado tal cual quedo guardado.
    v.caja.delete("1.0", "end")
    v.caja.insert("1.0", res["_pregunta"])
    v.ejercicio.set(res["_ejercicio"])
    v._revisar_boton()
    v._terminar(res)
    raiz.update()
    raiz.update_idletasks()

    alto = raiz.winfo_height()
    ancho = raiz.winfo_width()
    print("=" * 70)
    print(f"VENTANA MAXIMIZADA: {ancho} x {alto} px")
    print("=" * 70)

    texto = v.texto
    visibles, total = _alto_visible_y_total(texto)
    print(f"\nLA RESPUESTA")
    print(f"  lineas de pantalla que se ven sin desplazar : {visibles}")
    print(f"  lineas de pantalla que tiene en total       : {total}")
    print(f"  o sea, se ve de una vez                     : "
          f"{100 * visibles / max(total, 1):.0f}%")

    print(f"  alto de la caja de respuesta                : "
          f"{texto.winfo_height()} px "
          f"({100 * texto.winfo_height() / alto:.0f}% de la ventana)")
    f = texto.cget("font")
    fuente = v.fuente_texto
    print(f"  cada linea de pantalla ocupa                : "
          f"{texto.winfo_height() / max(visibles, 1):.0f} px")
    print(f"  y la letra mide                             : "
          f"{fuente.metrics('linespace')} px de alto")
    print(f"  separacion configurada (spacing1/2/3)       : "
          f"{texto.cget('spacing1')} / {texto.cget('spacing2')} / "
          f"{texto.cget('spacing3')}")

    print(f"\nQUE SE LLEVA CADA FRANJA · solo lo que se ve")
    filas = []
    for hijo in _en_orden_vertical(raiz):
        if not hijo.winfo_ismapped():
            continue
        h = hijo.winfo_height()
        if h < 12:
            continue
        y = hijo.winfo_rooty() - raiz.winfo_rooty()
        filas.append((y, h, _nombre(hijo), hijo))
    filas.sort(key=lambda x: (x[0], x[1], x[2]))
    # Solo las hojas: un Frame que contiene a otro no dice nada por si mismo.
    hojas = [x for x in filas
             if not any(o[3].winfo_parent() == str(x[3]) for o in filas)]
    for y, h, nombre, _w in hojas:
        print(f"  y={y:5d}..{y + h:5d}  alto={h:5d}  ({100 * h / alto:4.1f}%)  "
              f"{nombre}")

    arriba = texto.winfo_rooty() - raiz.winfo_rooty()
    abajo = arriba + texto.winfo_height()
    print(f"\nEL REPARTO VERTICAL")
    print(f"  de 0 a {arriba}: TODO LO QUE VA ANTES DE LA RESPUESTA  "
          f"({100 * arriba / alto:.0f}%)")
    print(f"  de {arriba} a {abajo}: la respuesta                    "
          f"({100 * texto.winfo_height() / alto:.0f}%)")
    print(f"  de {abajo} a {alto}: lo que va debajo                  "
          f"({100 * (alto - abajo) / alto:.0f}%)")
    print(f"\n  QUE HAY ENCIMA DE LA RESPUESTA:")
    for y, h, nombre, _w in hojas:
        if y < arriba:
            print(f"     y={y:5d} alto={h:4d}  {nombre}")
    print(f"\n  QUE HAY DEBAJO DE LA RESPUESTA:")
    hay = False
    for y, h, nombre, _w in hojas:
        if y >= abajo - 4:
            print(f"     y={y:5d} alto={h:4d}  {nombre}")
            hay = True
    if not hay:
        print("     nada")

    raiz.destroy()
    return 0


def _nombre(w) -> str:
    """Como llamar a un trozo de ventana para que se entienda en la lista."""
    clase = w.__class__.__name__
    try:
        rotulo = str(w.cget("text")).replace("\n", " ")[:44]
    except Exception:
        rotulo = ""
    return f"{clase:11s} {rotulo}" if rotulo else clase


def _en_orden_vertical(w, acc=None):
    acc = [] if acc is None else acc
    for h in w.winfo_children():
        acc.append(h)
        _en_orden_vertical(h, acc)
    return acc


if __name__ == "__main__":
    sys.exit(medir(sys.argv[1] if len(sys.argv) > 1 else ver_ejemplo.EXPEDIENTE))
