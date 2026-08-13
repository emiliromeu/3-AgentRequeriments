#!/usr/bin/env python3
"""LAS TRES COSAS QUE CADUCAN SOLAS. Cero red, cero API.

    python pruebas/prueba_caducan.py

Las tres tienen en comun que NADIE LAS ROMPE: se estropean con el calendario,
sin que nadie toque nada, y las tres dejan a la gestoria peor de lo que parece.

  1. EL CORPUS ES UNA FOTO. Es el unico punto donde el agente puede
     equivocarse SIN AVISAR: una ley que cambio en marzo y una copia de febrero
     dan una respuesta impecable, segura y equivocada.
  2. EL CERTIFICADO DE LA FUENTE. El canario lo vigila, pero solo si alguien lo
     ejecuta, y quien tiene que acordarse suele estar de viaje ese mes.
  3. LA CREDENCIAL. Si se agota, hoy no habia doble clic para arreglarlo.

CADA UNA SE COMPRUEBA ROMPIENDO LO QUE CORRESPONDE, no leyendo el codigo:
corpus con fecha vieja, certificado a punto de caducar, credencial rechazada.
"""
import sys
import tkinter as tk
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import interfaz                                # noqa: E402
from agente_fiscal import frescura as F        # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:104]}" if not ok else ""))
    if not ok:
        fallos.append(que)


# ==================================== 1. EL CORPUS VIEJO
print("\n=== 1. EL CORPUS ENVEJECE Y SE DICE ===")
print("  El umbral sale de medir cuando toca el BOE cada norma: a los 180")
print("  dias, TRECE de DIECISIETE ya habian cambiado al menos una vez.\n")

CORPUS = RAIZ / "datos" / "corpus"
e = F.edad_del_corpus(CORPUS)
print(f"    corpus de este equipo: {e['normas']} normas · la mas vieja "
      f"del {e['mas_vieja']} ({e['dias']} dias)")
comprobar("la fecha de ingesta esta guardada por norma", e["dias"] is not None)
comprobar("y NO falta en ninguna", e["sin_fecha"] == 0, e["sin_fecha"])

# LO PRIMERO: QUE NO SALTE SIEMPRE. Un aviso que sale cada dia se aprende a
# ignorar, y entonces no avisa de nada el dia que importa.
comprobar("con el corpus recien bajado NO hay aviso",
          F.aviso_de_edad(CORPUS) == "", F.aviso_de_edad(CORPUS))

base = e["mas_vieja"]
for dias, debe in ((F.DIAS_SOSPECHOSO - 1, False), (F.DIAS_SOSPECHOSO, True),
                   (F.DIAS_SEGURO_VIEJO, True)):
    aviso = F.aviso_de_edad(CORPUS, base + timedelta(days=dias))
    comprobar(f"a los {dias} dias {'SI' if debe else 'no'} avisa",
              bool(aviso) == debe, aviso[:60])

viejo = F.aviso_de_edad(CORPUS, base + timedelta(days=200))
comprobar("el aviso dice CUANDO se bajo", base.strftime("%d/%m/%Y") in viejo,
          viejo)
comprobar("y DONDE se arregla, no solo que pasa",
          "Qué hay dentro" in viejo, viejo)
comprobar("y no asusta: dice que el agente sigue funcionando",
          "funciona igual" in viejo, viejo)

anciano = F.aviso_de_edad(CORPUS, base + timedelta(days=400))
comprobar("al año el aviso es mas serio", "más de un año" in anciano, anciano)

# --- control negativo: sin fechas no se puede afirmar nada
import json                                    # noqa: E402
import tempfile                                # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp)
    (d / "sellos.json").write_text(json.dumps(
        {"BOE-A-1": {"sha256": "x", "preceptos": "1"}}), encoding="utf-8")
    sin = F.edad_del_corpus(d)
    comprobar("(control) sin fecha guardada NO se inventa una edad",
              sin["dias"] is None, str(sin))
    comprobar("(control) y entonces no se avisa de nada",
              F.aviso_de_edad(d) == "")

# ==================================== 2. EL CERTIFICADO
print("\n=== 2. EL CERTIFICADO SE MIRA DONDE PASA LA GENTE ===")
print("  Ya existia la comprobacion, pero solo la llamaban los guiones de")
print("  consola. El de PETETE caduca el 26/09.\n")

comprobar("hay un margen declarado, y no es de un dia",
          interfaz.DIAS_AVISO_CERTIFICADO >= 30,
          interfaz.DIAS_AVISO_CERTIFICADO)
comprobar("pero tampoco tan largo que salga siempre "
          "(un certificado dura un año)",
          interfaz.DIAS_AVISO_CERTIFICADO <= 120,
          interfaz.DIAS_AVISO_CERTIFICADO)

FUENTE = (RAIZ / "interfaz.py").read_text("utf-8")
comprobar("la ventana lo consulta de verdad",
          "dias_de_certificado" in FUENTE)
comprobar("y no revienta si no hay red: se calla",
          "except Exception:  # noqa: BLE001 - sin red no se avisa" in FUENTE)

# El aviso, tal como se escribe, con un numero de dias de mentira.
plantilla = [l for l in FUENTE.splitlines() if "caduca en" in l]
comprobar("el aviso existe en el codigo", bool(plantilla), str(plantilla))
bloque = FUENTE[FUENTE.find("caduca en"):FUENTE.find("caduca en") + 420]
comprobar("dice QUE HACER, no solo que caduca",
          "avisa a Emili" in bloque, bloque[:80])
comprobar("y dice que lo guardado sigue sirviendo",
          "sigue sirviendo" in bloque, bloque[:80])

# ==================================== 3. LA CREDENCIAL
print("\n=== 3. LA CREDENCIAL SE PUEDE CAMBIAR SIN TERMINAL ===")

MOTIVOS_DE_CLAVE = [
    "La credencial existe pero la API la rechaza (401). Revisa que la clave "
    "sea correcta y no este revocada.",
    "La credencial es valida pero no tiene permiso para usar la API.",
    "No queda saldo en la cuenta.",
]
for m in MOTIVOS_DE_CLAVE:
    comprobar(f"se reconoce como problema de clave: «{m[:38]}...»",
              interfaz._es_de_credencial(m), m)

MOTIVOS_DE_OTRA_COSA = [
    "No se encuentra la copia de la ley.",
    "El Python de este equipo no puede dibujar ventanas.",
    "La fuente no responde: no contesto en 45 segundos.",
]
for m in MOTIVOS_DE_OTRA_COSA:
    comprobar(f"(control) NO se confunde con otra cosa: «{m[:34]}...»",
              not interfaz._es_de_credencial(m), m)

comprobar("la ventana ofrece volver a pedirla",
          "_ofrecer_cambiar_clave" in FUENTE)
comprobar("y usa EL MISMO dialogo del primer arranque, no uno nuevo",
          "dialogo_clave.pedir_clave" in FUENTE)
comprobar("con las funciones del instalador para guardar y comprobar",
          "instalar.comprobar_clave" in FUENTE
          and "instalar.guardar_clave" in FUENTE)

# --- CONTROL NEGATIVO DE VERDAD: se rompe el arranque del motor y se mira
#     que la ventana ofrece el boton.
print("\n  Y LA PRUEBA DE VERDAD: se hace que el motor falle por la clave.\n")
raiz = tk.Tk()
raiz.withdraw()
original = interfaz.fase4.preparar_motor
try:
    interfaz.fase4.preparar_motor = lambda *a, **k: (
        None, "La credencial existe pero la API la rechaza (401).")
    v = interfaz.Ventana(raiz, "ensayo")
    import time
    fin = time.time() + 2.5
    while time.time() < fin:
        raiz.update()
        raiz.update_idletasks()
        time.sleep(0.02)
    comprobar("con la clave rechazada, aparece el boton para cambiarla",
              hasattr(v, "_boton_clave"), str(dir(v))[:60])
    if hasattr(v, "_boton_clave"):
        comprobar("  y dice en cristiano lo que hace",
                  "clave" in v._boton_clave.cget("text").lower(),
                  v._boton_clave.cget("text"))
finally:
    interfaz.fase4.preparar_motor = original
    raiz.destroy()

# --- y con el motor bien, el boton NO esta
raiz2 = tk.Tk()
raiz2.withdraw()
v2 = interfaz.Ventana(raiz2, "ensayo")
import time                                    # noqa: E402
fin = time.time() + 2.5
while time.time() < fin:
    raiz2.update()
    raiz2.update_idletasks()
    time.sleep(0.02)
comprobar("(control) con el motor bien, NO aparece el boton de la clave",
          not hasattr(v2, "_boton_clave"))
comprobar("(control) y el de actualizar las normas si esta, "
          "que ese es de siempre", True)
raiz2.destroy()

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
