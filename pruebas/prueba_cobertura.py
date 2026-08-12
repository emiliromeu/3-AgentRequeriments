#!/usr/bin/env python3
"""LA COBERTURA SE CUENTA, NO SE ESCRIBE. Cero red, cero API.

    python pruebas/prueba_cobertura.py

QUE PROTEGE, Y POR QUE ES LA QUINTA VEZ. El pie del segundo boton decia «TODAS
DE IVA por ahora». La guia decia «el criterio guardado es todo de IVA» y «la
herramienta cubre dos impuestos con la ley: IVA y Renta». El texto de
bienvenida decia «responde solo con la Ley y el Reglamento del IVA». Las tres
eran ciertas el dia que se escribieron.

La siembra metio criterio de Renta, de Sociedades, de Patrimonio y de las
normas generales, y el corpus paso a trece normas. Ninguna de las tres frases
se entero. Y el fallo no es que estuvieran mal escritas: es que una frase a
mano sobre lo que el sistema cubre es una fecha de caducidad sin etiqueta.

Esta suite comprueba que ninguna de las tres vuelve, y que lo que se enseña
sale de contar `datos/dgt` y `datos/teac`.
"""
import re
import sys
import time
import tkinter as tk
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4                                    # noqa: E402
import interfaz                                 # noqa: E402
from agente_fiscal import cobertura as COB      # noqa: E402
from agente_fiscal import configuracion as CONF  # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:104]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix, _grafo = fase4.cargar_corpus()

# ================================================ 1. SE CUENTA DE LOS DATOS
print("\n=== 1. LA COBERTURA SALE DE LA DESPENSA ===\n")

cuenta = COB.resumen(ix)
print(f"    {cuenta}\n")
comprobar("hay mas de un impuesto con criterio guardado", len(cuenta) > 1,
          list(cuenta))
comprobar("y NO es todo de IVA, que es lo que decia la frase vieja",
          sum(v["dgt"] + v["teac"] for k, v in cuenta.items()
              if k != "IVA") > 0,
          cuenta)
comprobar("cada impuesto viene con su numero",
          all(isinstance(v["dgt"], int) and isinstance(v["teac"], int)
              for v in cuenta.values()))

filas = COB.por_impuesto(ix)
comprobar("la lista va de mas a menos",
          [t for _n, t in filas[:-1]] == sorted(
              [t for _n, t in filas[:-1]], reverse=True),
          str(filas))
comprobar("y las normas generales van al final, que no son un impuesto",
          filas[-1][0] == COB.GENERAL, str(filas))

# ================================================ 2. LA VENTANA NO AFIRMA
print("\n=== 2. NI UNA AFIRMACION A MANO EN LA VENTANA ===\n")

FUENTE = (RAIZ / "interfaz.py").read_text("utf-8")
sin_comentarios = "\n".join(l for l in FUENTE.splitlines()
                            if not l.lstrip().startswith("#"))
PROHIBIDAS = (
    "TODAS DE IVA",
    "todo de IVA",
    "toda de IVA",
    "solo con la Ley y el Reglamento del IVA",
    "cubre dos impuestos",
)
for frase in PROHIBIDAS:
    comprobar(f"no vuelve «{frase}»", frase not in sin_comentarios)

raiz = tk.Tk()
v = interfaz.Ventana(raiz, "ensayo")
fin = time.time() + 2.5
while time.time() < fin:          # `_arrancar_motor` va con after(120)
    raiz.update()
    raiz.update_idletasks()
    time.sleep(0.02)

pie = v.pie_criterio.cget("text")
print(f"    pie del boton: {pie[:96]}...\n")
comprobar("el pie dice QUE anade", "DGT" in pie and "TEAC" in pie)
comprobar("y de que hay criterio, contado", "criterio guardado de" in pie, pie)
for nombre, total in filas:
    comprobar(f"  con «{nombre}» y su numero ({total})",
              f"{nombre} ({total})" in pie, pie)

bienvenida = v.texto.get("1.0", "end")
comprobar("la bienvenida dice cuantos articulos y cuantas normas",
          str(len(ix.docs)) in bienvenida and str(len(ix.rutas)) in bienvenida,
          bienvenida[:120])


def textos_de(w, acc=None):
    acc = [] if acc is None else acc
    try:
        t = w.cget("text")
        if t:
            acc.append(str(t))
    except Exception:  # noqa: BLE001
        pass
    for h in w.winfo_children():
        textos_de(h, acc)
    return acc


ventana_dentro = tk.Toplevel(raiz)
v._pintar_que_hay_dentro(ventana_dentro) if hasattr(
    v, "_pintar_que_hay_dentro") else None
dentro = "\n".join(textos_de(ventana_dentro))
if not dentro:
    ventana_dentro.destroy()
    v.boton_dentro.invoke()
    raiz.update()
    raiz.update_idletasks()
    dentro = "\n".join(textos_de(raiz.winfo_children()[-1]))
comprobar("«Qué hay dentro» dice de que hay criterio",
          "DE QUÉ HAY CRITERIO GUARDADO" in dentro, dentro[:120])
for nombre, total in filas:
    comprobar(f"  con «{nombre}» y {total}",
              nombre in dentro and str(total) in dentro)

# ================================================ 3. LA GUIA, IGUAL
print("\n=== 3. LA GUIA DICE LA MISMA CUENTA ===\n")

guia = CONF.GUIA.read_text("utf-8")
bloque = CONF.bloque_de_cobertura(guia)
comprobar("GUIA.md tiene el bloque de cobertura", bool(bloque))
comprobar("y coincide con lo contado",
          CONF._plano(bloque) == CONF._plano(CONF.texto_de_cobertura(ix)),
          bloque[:100])
comprobar("la revision al arrancar lo comprueba y sale coherente",
          CONF.revisar(ix).coherente,
          str(CONF.revisar(ix).descuadres))
comprobar("no vuelve «el criterio guardado es todo de IVA» en la guia",
          "todo de IVA" not in guia)

# ================================================ 4. CONTROL NEGATIVO
print("\n=== 4. LA PRUEBA SABE PONERSE ROJA ===")
print("  Se rompe la guia de verdad y se mira si la revision lo caza.\n")

original = guia
try:
    roto = guia.replace(bloque, "| IVA | 999999 |")
    CONF.GUIA.write_text(roto, encoding="utf-8")
    r = CONF.revisar(ix)
    comprobar("(a) si alguien edita la cobertura a mano, se caza",
              not r.coherente, str(r.descuadres))
    comprobar("  y se dice como arreglarlo",
              any("regenerar-guia" in d for d in r.descuadres),
              str(r.descuadres))

    abre, cierra = CONF.MARCA_COBERTURA
    sin_marcas = guia.replace(abre, "").replace(cierra, "")
    CONF.GUIA.write_text(sin_marcas, encoding="utf-8")
    r2 = CONF.revisar(ix)
    comprobar("(b) si alguien quita el bloque entero, tambien",
              not r2.coherente, str(r2.descuadres))

    CONF.GUIA.write_text(original, encoding="utf-8")
    comprobar("(c) al deshacerlo vuelve a ser coherente",
              CONF.revisar(ix).coherente)
finally:
    CONF.GUIA.write_text(original, encoding="utf-8")

# (d) y sin corpus NO se da por buena: se dice que no se ha mirado
sin_ix = CONF.revisar(None)
comprobar("(d) sin corpus, la cobertura se declara SIN COMPROBAR, no correcta",
          "sin comprobar" in sin_ix.piezas.get("cobertura de la guia", ""),
          str(sin_ix.piezas))

raiz.destroy()

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
