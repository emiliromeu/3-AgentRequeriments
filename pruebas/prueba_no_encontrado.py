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
# LA PREGUNTA DICE DE QUE IMPUESTO ES, y no es cosmetico: desde que la puerta
# de materia rechaza «desconocido», una pregunta sin impuesto identificable se
# para ANTES de llegar al verificador, y esta suite existe para probar lo que
# pasa DESPUES del verificador. El modelo 303 es la declaracion del IVA y el
# analizador de verdad lo sabe; el del motor de ensayo es un tocon que solo
# reconoce la palabra literal.
v.caja.insert("1.0", "plazo para presentar el modelo 303 del IVA")
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
# SE PREGUNTA A LA VENTANA, NO SE LEE DE UNA ETIQUETA. Cambiado el 29/08/2026.
#
# Aqui se sacaba la ruta del expediente PARSEANDO el texto que se pinta en
# pantalla: `pie_respuesta.cget("text").replace("Expediente guardado en ", "")`.
# Funcionaba, y aun asi estaba mal por dos motivos:
#
#   · ataba una comprobacion de fondo -que el borrador rechazado no llega a la
#     pantalla- a la REDACCION de una etiqueta. Cambiar una palabra del rotulo
#     rompia una suite que no tiene nada que ver con el rotulo;
#   · y esa etiqueta ya no lleva la ruta. Llevaba una ruta absoluta de ESTE
#     ordenador, que en el PC de la oficina señala a otro sitio.
#
# `expediente_actual` es lo que la ventana sabe de verdad, y se rellena en
# `_terminar` antes de cualquier rama: tambien en un NO ENCONTRADO seco, que es
# justo el caso de esta suite y donde antes no habia nada que leer.
traza = Path(v.expediente_actual)
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

# =====================================================================
print("\n=== 6. NO SE PUEDE CITAR LO QUE NO SE LE PUSO DELANTE ===")
print("  El verificador resuelve contra el CORPUS ENTERO: una cita a")
print("  cualquier articulo cargado se comprueba bien, la hubiera visto el")
print("  redactor o no. Comprobar que una cita es literal y comprobar que la")
print("  respuesta se apoya en lo que se le dio son dos cosas distintas.\n")
from agente_fiscal import verificador as VF  # noqa: E402
import fase4 as _F4  # noqa: E402

_ix, _grafo = _F4.cargar_corpus()
_v = VF.Verificador(_ix)

# UN ARTICULO REAL, Y NOMBRANDO SU NORMA. La cita tiene que ser literal y
# RESOLUBLE: sin decir de que norma es, «Articulo 1» existe en 19 cuerpos y el
# verificador la deja en NO_VERIFICABLE antes de llegar a esta regla — se
# estaria probando otra cosa. Se escribe como las escribe el redactor.
_CLAVE = "BOE-A-1992-28740#0#articulo 95"
_doc = _ix.por_clave[_CLAVE]
_frag = " ".join((_doc.registro["texto_vigente"] or "").split())
# Del cuerpo del articulo, no de su rubrica: el epigrafe no sostiene nada.
_frag = _frag[_frag.index("Uno."):][:170]
_cita = (f"El {_doc.registro['referencia']} de la Ley 37/1992 dispone que "
         f"«{_frag}» ({_doc.registro['url']}).")
_mio = {_CLAVE}
# Otro precepto REAL del corpus: si el material de mentira fuera una clave
# inventada, el caso adversario podria estar pasando por un camino de error y
# no por la regla.
_otro = {"BOE-A-1992-28740#0#articulo 97"}

# --- EL POSITIVO: la misma cita, con su precepto en el material ---
_inf = _v.verificar_texto(_cita, None, claves_del_material=_mio)
comprobar("POSITIVO: con su precepto en el material, la cita se VERIFICA",
          all(d.estado == VF.VERIFICADA for d in _inf.dictamenes)
          and _inf.dictamenes,
          [(d.estado, d.motivo[:60]) for d in _inf.dictamenes])

# --- EL ADVERSARIO: la MISMA cita, con otro material ---
_inf2 = _v.verificar_texto(_cita, None, claves_del_material=_otro)
comprobar("ADVERSARIO: la misma cita, con otro material, se RECHAZA",
          _inf2.veredicto == VF.RECHAZADO, _inf2.veredicto)
comprobar("  y se dice por que, sin llamarla falsa: es literal, pero no se le "
          "puso delante",
          any("NO SE LE PUSO DELANTE" in d.motivo for d in _inf2.dictamenes),
          [d.motivo[:90] for d in _inf2.dictamenes])

# --- SIN DECIR EL MATERIAL, NO SE EXIGE: es lo que deja en pie a la bateria ---
_inf3 = _v.verificar_texto(_cita, None)
comprobar("sin material declarado no se exige nada (la bateria sigue en pie)",
          all(d.estado == VF.VERIFICADA for d in _inf3.dictamenes),
          [(d.estado, d.motivo[:50]) for d in _inf3.dictamenes])

# --- Y UN CONJUNTO VACIO NO ES «NO SE ME HA DICHO» ---
_inf4 = _v.verificar_texto(_cita, None, claves_del_material=set())
comprobar("un material VACIO si exige: no es lo mismo que no declararlo",
          _inf4.veredicto == VF.RECHAZADO, _inf4.veredicto)

print("\n" + "=" * 62)
print(f"FALLOS: {len(fallos)}")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
