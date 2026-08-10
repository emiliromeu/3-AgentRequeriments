#!/usr/bin/env python3
"""NUNCA SE ENSENA TEXTO QUE EL VERIFICADOR NO HA ACEPTADO. Cero red, cero API.

Es LA regla que sostiene el sistema entero. Si se rompe, todo lo demas -las
citas, los estados, los avisos- deja de valer, porque el profesional estaria
leyendo texto que nadie ha comprobado y no tendria forma de saberlo.

Ni en gris, ni con aviso, ni a titulo orientativo. Y tampoco por el
portapapeles: copiar es ensenar.

    python pruebas/prueba_no_encontrado.py
"""
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import tkinter as tk

import interfaz
from agente_fiscal import estado as EST

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:110]}" if not ok else ""))
    if not ok:
        fallos.append(que)


raiz = tk.Tk()
v = interfaz.Ventana(raiz, "ensayo")


def esperar(cond, limite=240):
    fin = time.time() + limite
    while time.time() < fin:
        raiz.update()
        if cond():
            return True
        time.sleep(0.02)
    return False


def bombear(segundos=0.5):
    fin = time.time() + segundos
    while time.time() < fin:
        raiz.update()
        time.sleep(0.02)


esperar(lambda: v.motor is not None, 90)

# ------------------------------------------- 1. DE EXTREMO A EXTREMO
print("\n=== 1. UNA CONSULTA QUE NO SUPERA LA VERIFICACION ===")
# LA CONSULTA IMPORTA Y SU MOTIVO SE DEJA ESCRITO. Antes se usaba «que tipo de
# IVA se aplica a los libros», que daba NO ENCONTRADO porque la ficha del
# material nombraba la norma con el titulo del documento del BOE y el
# verificador no lo resolvia. Eso era un fallo del material -arreglado en la
# fase 18- y esta prueba se apoyaba en el sin saberlo.
v.caja.insert("1.0", "plazo para presentar el modelo 303")
v.ejercicio.set("2023")
v._revisar_boton()
v._lanzar()
esperar(lambda: not v.trabajando, 240)
bombear()

cuerpo = v.texto.get("1.0", "end")
estado = v.etiqueta_estado.cget("text")
print(f"    estado pintado: {estado}")
comprobar("sale NO ENCONTRADO", estado == EST.NO_ENCONTRADO, estado)
comprobar("con SU texto: manda a mirar los articulos de abajo",
          "Abajo tienes los articulos encontrados"
          in v.etiqueta_explicacion.cget("text"))
comprobar("se dice que no hay texto por no superar la comprobacion",
          "no ha superado la comprobacion" in cuerpo.lower(), cuerpo[:200])

# ------------------------------------ 2. EL BORRADOR NO LLEGA A PANTALLA
print("\n=== 2. EL BORRADOR RECHAZADO NO LLEGA A PANTALLA ===")
traza = Path(v.pie.cget("text").replace("Expediente guardado en ", "").strip())
borradores = sorted(traza.glob("borrador_*.txt")) if traza.is_dir() else []
print(f"    borradores en la traza: {[b.name for b in borradores]}")
comprobar("el expediente SI guarda el borrador (la traza queda intacta)",
          bool(borradores), str(traza))
if borradores:
    texto_rechazado = borradores[-1].read_text("utf-8")
    trozos = [l.strip() for l in texto_rechazado.splitlines()
              if len(l.strip()) > 40][:6]
    coladas = [t for t in trozos if t[:40] in cuerpo]
    comprobar("NADA del borrador ha llegado a la pantalla", not coladas,
              str(coladas[:1]))

comprobar("el boton de copiar esta desactivado",
          str(v.boton_copiar["state"]) == "disabled")
comprobar("y no hay respuesta guardada para copiar", not v.respuesta_actual,
          v.respuesta_actual[:60])

# ------------------------------ 3. SE ENSENA LO RECUPERADO, EN CRUDO
print("\n=== 3. SE ENSENA LO QUE SI SE ENCONTRO, PARA MIRARLO A MANO ===")
comprobar("aparece algun articulo recuperado, con su numero",
          "Articulo" in cuerpo, cuerpo[:200])
comprobar("y con enlaces del BOE pinchables", "boe.es" in cuerpo)
comprobar("con la etiqueta 'enlace' aplicada de verdad",
          bool(v.texto.tag_ranges("enlace")))

# ---------------------------- 4. COPIAR NO ARRASTRA LA ANTERIOR
print("\n=== 4. COPIAR NO PUEDE ARRASTRAR UNA RESPUESTA VIEJA ===")
print("  Copiar es ensenar: si el portapapeles guarda la respuesta buena de")
print("  antes, quien pegue creera que es la de ahora.")
v.respuesta_actual = "RESPUESTA VIEJA QUE NO DEBE SOBREVIVIR"
v.boton_copiar.configure(state="normal")
v._terminar({"codigo": 2, "estado": EST.NO_ENCONTRADO, "respuesta": "",
             "motivo": "la redaccion no supero la verificacion de citas",
             "senales": [], "cobertura": [], "preceptos": [], "traza": None,
             "fallo": None, "recuperado": []})
bombear(0.3)
comprobar("la respuesta vieja se borra", not v.respuesta_actual,
          v.respuesta_actual)
comprobar("y el boton vuelve a estar apagado",
          str(v.boton_copiar["state"]) == "disabled")

# ------------------------- 5. NI SIQUIERA SI VIENE UN BORRADOR EN EL DICT
print("\n=== 5. AUNQUE EL RESULTADO TRAIGA UN BORRADOR, NO SE PINTA ===")
print("  `respuesta` vacia significa «no se puede ensenar». Cualquier otro")
print("  campo con texto -borrador, motivo, lo que sea- NO es una respuesta.")
v._terminar({"codigo": 2, "estado": EST.NO_ENCONTRADO, "respuesta": "",
             "motivo": "no supero la verificacion",
             "borrador": "TEXTO PELIGROSO SIN VERIFICAR",
             "senales": [], "cobertura": [], "preceptos": [], "traza": None,
             "fallo": None, "recuperado": []})
bombear(0.3)
cuerpo2 = v.texto.get("1.0", "end")
comprobar("el borrador del dict NO aparece",
          "TEXTO PELIGROSO SIN VERIFICAR" not in cuerpo2, cuerpo2[:150])
comprobar("y sigue sin haber nada que copiar", not v.respuesta_actual)

# ---------------------------- 6. NINGUNA TRAZA DE PYTHON EN PANTALLA
print("\n=== 6. NINGUNA TRAZA DE PYTHON, NUNCA ===")
for marca in ("Traceback", "File \"", ".py\", line", "Exception", "sk-ant"):
    comprobar(f"no aparece «{marca}»", marca not in cuerpo2, cuerpo2[:150])

# -------------------- 7. CONTROL NEGATIVO: VERLA FALLAR
print("\n=== 7. LA PRUEBA SABE PONERSE ROJA ===")
print("  Se simula el fallo que esta prueba existe para cazar -que la ventana")
print("  pinte el borrador rechazado- y se comprueba que lo detectaria.\n")
PELIGRO = "TEXTO QUE EL VERIFICADOR TUMBO"
v._escribir_texto([(PELIGRO, None)])
v.respuesta_actual = PELIGRO
v.boton_copiar.configure(state="normal")
bombear(0.2)
cuerpo3 = v.texto.get("1.0", "end")
comprobar("si el borrador llegara a pantalla, la comprobacion 2 lo veria",
          PELIGRO in cuerpo3)
comprobar("y la de copiar tambien",
          v.respuesta_actual == PELIGRO
          and str(v.boton_copiar["state"]) == "normal")
print("    (las dos han detectado el texto peligroso: la prueba SI mide algo)")

raiz.destroy()
print("\n" + "=" * 62)
print(f"FALLOS: {len(fallos)}")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
