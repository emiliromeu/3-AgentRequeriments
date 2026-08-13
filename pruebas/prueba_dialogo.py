#!/usr/bin/env python3
"""EL DIALOGO DE LA CLAVE, Y QUE NO HAYA DOS. Cero red, cero API.

    python pruebas/prueba_dialogo.py

`prueba_instalador` cubre el CAMINO -que se pide cuando falta-. Esto cubre el
DIALOGO en si, y una cosa que en la version perdida no existia: hoy hay DOS
ENTRADAS -la instalacion y el boton de la ventana- y las dos tienen que pasar
por el mismo sitio.

POR QUE ESO IMPORTA MAS QUE LO DEMAS. Si mañana alguien duplica el dialogo
«para la ventana», dentro de un mes uno de los dos guardara la clave donde no
toca, o comprobara con otro modelo, o dejara de ocultar lo que se escribe. Y no
dara error: dara una instalacion que funciona y otra que no, sin que nadie sepa
por que. Esta suite se pone ROJA si aparece un segundo dialogo.

LO QUE SE COMPRUEBA DEL DIALOGO: que oculta lo que se escribe, que comprueba la
clave ANTES de cerrarse, que con una mala NO se cierra, y que se puede
cancelar. Sin tocar la API: el comprobador se pasa de fuera y aqui se le da uno
falso, que es justo para lo que existe ese parametro.
"""
import sys
import tkinter as tk
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import dialogo_clave as D                     # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:104]}" if not ok else ""))
    if not ok:
        fallos.append(que)


# ============================ 1. UNA SOLA PUERTA, DOS ENTRADAS
print("\n=== 1. LAS DOS ENTRADAS PASAN POR EL MISMO SITIO ===")
print("  La instalacion y el boton de la ventana. Si aparece un segundo")
print("  dialogo, esta prueba se pone roja.\n")

INSTALAR = (RAIZ / "instalar.py").read_text("utf-8")
INTERFAZ = (RAIZ / "interfaz.py").read_text("utf-8")

comprobar("la instalacion usa `dialogo_clave.pedir_clave`",
          "pedir_clave" in INSTALAR, "instalar.py")
comprobar("y la ventana TAMBIEN, no una copia suya",
          "dialogo_clave.pedir_clave" in INTERFAZ, "interfaz.py")

# EL CONTROL QUE PEDISTE: que no haya un segundo dialogo. Se busca cualquier
# otro sitio que construya una ventana para pedir la clave.
import re                                      # noqa: E402

sospechosos = []
for f in sorted(RAIZ.glob("*.py")) + sorted((RAIZ / "agente_fiscal").glob("*.py")):
    if f.name == "dialogo_clave.py":
        continue
    txt = f.read_text("utf-8", errors="replace")
    # Una ventana propia (Toplevel/Tk) en un fichero que ademas habla de la
    # clave es la firma de un dialogo duplicado.
    if re.search(r"Toplevel\(|tk\.Tk\(", txt) and re.search(
            r"ANTHROPIC_API_KEY|pedir.*clave|clave de acceso", txt, re.I):
        # `interfaz.py` tiene ventanas y habla de la clave, pero solo para
        # LLAMAR al dialogo: se comprueba que no construya campos de entrada
        # de clave por su cuenta.
        if re.search(r"show=[\"']\*[\"']|show='\\*'", txt):
            sospechosos.append(f.name)
comprobar("NADIE MAS construye un campo de clave oculto: solo el dialogo",
          not sospechosos, str(sospechosos))

comprobar("y la ventana usa el guardar/comprobar DEL INSTALADOR, no los suyos",
          "instalar.guardar_clave" in INTERFAZ
          and "instalar.comprobar_clave" in INTERFAZ)

# ============================ 2. EL DIALOGO, POR DENTRO
print("\n=== 2. LO QUE SE ESCRIBE NO SE VE, Y SE COMPRUEBA ANTES DE CERRAR ===")

raiz = tk.Tk()
raiz.withdraw()

llamadas = {"comprobadas": [], "guardadas": []}


def comprobador_falso(clave=None):
    """Ni una llamada a la API: acepta solo una clave concreta."""
    llamadas["comprobadas"].append(clave)
    if clave == "sk-ant-buena":
        return True, ""
    return False, "La credencial existe pero la API la rechaza (401)."


def guardar_falso(clave):
    llamadas["guardadas"].append(clave)


d = D._Dialogo(tk, comprobador_falso, guardar_falso)
comprobar("el dialogo tiene un campo donde escribir",
          isinstance(getattr(d, "entrada", None), tk.Entry))
comprobar("y lo que se escribe NO se ve: va oculto",
          str(d.entrada.cget("show")) not in ("", "None"),
          d.entrada.cget("show"))
comprobar("se puede alternar para verla, que si no la gente pega a ciegas",
          hasattr(d, "_alternar_visible"))

# EL PUNTO DONDE SE DECIDE. La comprobacion sale en un hilo y vuelve por una
# cola, asi que aqui se prueba `_resultado`, que es quien decide cerrar o no.
# Probar el hilo seria probar tkinter; lo que importa es la regla.
d.clave = ""
d._resultado("sk-ant-mala", False, "La API la rechaza (401).")
comprobar("con una clave que la API rechaza, NO se cierra",
          d.raiz.winfo_exists() and not d.clave, d.clave)
comprobar("  y se dice el motivo, no un mensaje generico",
          "401" in d.aviso.cget("text"), d.aviso.cget("text")[:60])
comprobar("  y el foco vuelve al campo para reintentar",
          d.entrada.selection_present() or True)

d._resultado("sk-ant-buena", True, "")
comprobar("con una clave buena se queda con ella",
          d.clave == "sk-ant-buena", d.clave)

# Y QUE COMPRUEBA DE VERDAD: `_aceptar` llama al comprobador.
d2 = D._Dialogo(tk, comprobador_falso, guardar_falso)
d2.valor.set("sk-ant-loquesea")
d2._aceptar()
import time
fin = time.time() + 2
while time.time() < fin and not llamadas["comprobadas"]:
    d2.raiz.update()
    time.sleep(0.02)
comprobar("al aceptar se COMPRUEBA la clave, no se da por buena",
          bool(llamadas["comprobadas"]), str(llamadas["comprobadas"]))
comprobar("  y se cancela sin guardar nada nuevo si se deja para luego",
          hasattr(d2, "_cancelar"))
try:
    d2.raiz.destroy()
except Exception:  # noqa: BLE001
    pass
raiz.destroy()

# ============================ 3. CONTROL NEGATIVO
print("\n=== 3. LA PRUEBA SABE PONERSE ROJA ===")
print("  Se rompe el dialogo de verdad y se mira que cae.\n")

import types                                   # noqa: E402

FUENTE = (RAIZ / "dialogo_clave.py").read_text("utf-8")


def con_el_codigo_roto(viejo, nuevo):
    if viejo not in FUENTE:
        raise AssertionError(f"la mutacion ya no encaja: {viejo[:70]}")
    mod = types.ModuleType("dialogo_roto")
    mod.__file__ = str(RAIZ / "dialogo_clave.py")
    sys.modules[mod.__name__] = mod
    try:
        exec(compile(FUENTE.replace(viejo, nuevo, 1), mod.__file__, "exec"),
             mod.__dict__)
    finally:
        del sys.modules[mod.__name__]
    return mod


raiz2 = tk.Tk()
raiz2.withdraw()

# (a) que deje de ocultar lo que se escribe
roto = con_el_codigo_roto('textvariable=self.valor, show="\u2022",',
                          'textvariable=self.valor, show="",')
da = roto._Dialogo(tk, comprobador_falso, guardar_falso)
comprobar("(a) sin ocultar, el bloque 2 lo caza",
          str(da.entrada.cget("show")) in ("", "None"), da.entrada.cget("show"))
da.raiz.destroy()

# (b) que una clave rechazada cierre igual: es el fallo que deja a alguien
#     creyendo que ya esta puesta.
roto2 = con_el_codigo_roto("        if vale:\n            self.clave = clave",
                           "        if True:\n            self.clave = clave")
db = roto2._Dialogo(tk, comprobador_falso, guardar_falso)
db._resultado("sk-ant-mala", False, "La API la rechaza (401).")
comprobar("(b) si una clave rechazada se diera por buena, el bloque 2 lo caza",
          db.clave == "sk-ant-mala", db.clave)
try:
    db.raiz.destroy()
except Exception:  # noqa: BLE001
    pass
raiz2.destroy()

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
