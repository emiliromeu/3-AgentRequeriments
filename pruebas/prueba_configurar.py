#!/usr/bin/env python3
"""UN SOLO MANDO, REVERSIBLE Y SIN MEDIAS TINTAS. Cero red, cero API.

Lo que se juega:
  · ir y volver deja el sistema IDENTICO. Si no, no es reversible;
  · descoordinar UNA pieza y que el agente se niegue a abrir diciendo cual.
    Mejor no abrir que abrir mintiendo.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from agente_fiscal import configuracion as C

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {obtenido}" if not ok else ""))
    if not ok:
        fallos.append(que)


def limpio(*args):
    """configurar.py con el entorno LIMPIO: sin variables que manden encima."""
    e = dict(os.environ)
    for v in (C.VAR_DGT, C.VAR_TEAC, C.VAR_TEXTOS):
        e.pop(v, None)
    return subprocess.run([sys.executable, "configurar.py", *args],
                          cwd=str(RAIZ), capture_output=True, text=True, env=e)


def foto() -> dict:
    """El estado del sistema en un dict comparable."""
    return {
        "modo": C.modo_guardado(),
        "guia": hashlib.sha256(C.GUIA.read_bytes()).hexdigest()[:16],
        "guia_dice": C.modo_de_la_guia(),
    }


def recargar():
    """El modo se lee de disco en cada llamada, pero los modulos cachean poco.
    Se vuelven a importar para que nada quede pegado de la vez anterior."""
    for m in [x for x in list(sys.modules) if x.startswith("agente_fiscal")]:
        del sys.modules[m]
    from agente_fiscal import configuracion as C2
    from agente_fiscal import dgt as D2
    from agente_fiscal import teac as T2
    return C2, D2, T2


# ---------------------------------------------------- 1. IDA Y VUELTA
print("\n=== 1. IR Y VOLVER DEJA EL SISTEMA IDENTICO ===")
partida = foto()
print(f"    de partida : {partida}")

r = limpio("--con-criterio")
comprobar("--con-criterio sale bien", r.returncode == 0, r.stdout[-200:])
con = foto()
print(f"    con criterio: {con}")
comprobar("el modo cambia", con["modo"] == C.CON_CRITERIO, con["modo"])
comprobar("y la guia tambien", con["guia"] != partida["guia"])
comprobar("la guia dice lo mismo que el modo",
          con["guia_dice"] == C.CON_CRITERIO, con["guia_dice"])

C2, D2, T2 = recargar()
for v in (C.VAR_DGT, C.VAR_TEAC, C.VAR_TEXTOS):
    os.environ.pop(v, None)
comprobar("la DGT queda encendida", D2.activa())
comprobar("y el TEAC tambien", T2.activa())
comprobar("y los textos de la ventana", C2.textos_con_criterio())

r = limpio("--solo-ley")
comprobar("--solo-ley sale bien", r.returncode == 0, r.stdout[-200:])
vuelta = foto()
print(f"    de vuelta  : {vuelta}")
comprobar("VUELVE EXACTAMENTE AL PUNTO DE PARTIDA", vuelta == partida,
          f"{partida} != {vuelta}")

C2, D2, T2 = recargar()
comprobar("la DGT vuelve a estar apagada", not D2.activa())
comprobar("y el TEAC tambien", not T2.activa())
comprobar("y los textos", not C2.textos_con_criterio())

# ------------------------------------------- 2. DESCOORDINAR A MANO
print("\n=== 2. DESCOORDINAR UNA PIEZA: EL AGENTE NO ABRE ===")
print("  Se rompe cada pieza por separado y se mira si lo detecta Y si dice")
print("  CUAL es. Decir «algo va mal» no sirve para arreglarlo.\n")

# a) la guia: se le quita la marca, como si alguien la hubiera editado
guardada = C.GUIA.read_text("utf-8")
C.GUIA.write_text(guardada.replace(C.MARCA.format(modo=C.SOLO_LEY), ""),
                  encoding="utf-8")
C2, _D, _T = recargar()
r2 = C2.revisar()
print(f"    (a) GUIA.md sin marca -> {r2.descuadres}")
comprobar("(a) lo detecta", not r2.coherente)
comprobar("(a) y dice que es GUIA.md",
          any("GUIA.md" in d for d in r2.descuadres), str(r2.descuadres))
C.GUIA.write_text(guardada, encoding="utf-8")

# b) la guia del OTRO modo, que si tiene marca pero la equivocada
C.GUIA.write_text((C.DIR_GUIAS / "GUIA.con-criterio.md").read_text("utf-8"),
                  encoding="utf-8")
C2, _D, _T = recargar()
r2 = C2.revisar()
print(f"    (b) GUIA.md del otro modo -> {r2.descuadres}")
comprobar("(b) lo detecta", not r2.coherente)
comprobar("(b) y dice los dos modos que no cuadran",
          any("con-criterio" in d and "solo-ley" in d for d in r2.descuadres),
          str(r2.descuadres))
C.GUIA.write_text(guardada, encoding="utf-8")

# c) una fuente encendida a mano con el modo en solo-ley
os.environ[C.VAR_DGT] = "1"
C2, _D, _T = recargar()
r2 = C2.revisar()
print(f"    (c) AGENTE_DGT=1 con modo solo-ley -> {r2.descuadres}")
comprobar("(c) lo detecta", not r2.coherente)
comprobar("(c) y dice que es la fuente DGT",
          any("fuente DGT" in d for d in r2.descuadres), str(r2.descuadres))
os.environ.pop(C.VAR_DGT, None)

# d) los textos por su cuenta
os.environ[C.VAR_TEXTOS] = "1"
C2, _D, _T = recargar()
r2 = C2.revisar()
print(f"    (d) AGENTE_DGT_TEXTOS=1 -> {r2.descuadres}")
comprobar("(d) lo detecta", not r2.coherente)
comprobar("(d) y dice que son los textos",
          any("textos" in d for d in r2.descuadres), str(r2.descuadres))
os.environ.pop(C.VAR_TEXTOS, None)

# --------------------------------------- 3. Y LO DICE EN CRISTIANO
print("\n=== 3. LO QUE VE UNA PERSONA ===")
os.environ[C.VAR_DGT] = "1"
C2, _D, _T = recargar()
try:
    C2.exigir_coherencia()
    comprobar("levanta el aviso", False, "no lo levanto")
except C2.Descoordinado as e:
    lineas = e.en_cristiano()
    print("    " + "\n    ".join(lineas))
    comprobar("dice que NO se abre", any("NO se abre" in l for l in lineas))
    comprobar("dice cual es la pieza",
              any("fuente DGT" in l for l in lineas))
    comprobar("da la orden exacta para arreglarlo",
              any("configurar.py --solo-ley" in l for l in lineas))
    comprobar("y explica POR QUE no se abre a medias",
              any("decidiria" in l for l in lineas))
    comprobar("sin una sola traza de python",
              not any("Traceback" in l or "  File " in l for l in lineas))
os.environ.pop(C.VAR_DGT, None)

# ------------------------------------------- 4. LA TERMINAL TAMBIEN PARA
print("\n=== 4. LA TERMINAL PARA IGUAL, ANTES DE GASTAR UNA LLAMADA ===")
e = dict(os.environ)
e[C.VAR_DGT] = "1"
r = subprocess.run([sys.executable, "fase4.py", "consultar", "algo",
                    "--ejercicio", "2023", "--motor", "ensayo"],
                   cwd=str(RAIZ), capture_output=True, text=True, env=e)
comprobar("fase4 se niega", r.returncode != 0, f"codigo {r.returncode}")
comprobar("y lo dice", "medio configurar" in r.stdout.lower(), r.stdout[:200])
comprobar("sin llegar a consultar", "CONSULTA FISCAL" not in r.stdout)

# --------------------------------------------------- 5. EL ESTADO
print("\n=== 5. --estado DICE LO QUE HAY ===")
r = limpio("--estado")
s = r.stdout
comprobar("dice el modo", "MODO: solo-ley" in s, s[:120])
comprobar("lista las cuatro piezas",
          all(p in s for p in ("fuente DGT", "fuente TEAC",
                               "textos de la ventana", "GUIA.md")))
comprobar("dice las normas cargadas", "722" in s)
comprobar("y cuantas consultas de la DGT hay", "consultas de la DGT" in s)
comprobar("y cuantas resoluciones", "resoluciones economico" in s)
comprobar("y lo que cuesta una consulta", "EUR" in s and "cuesta" in s.lower())
comprobar("y lo que costaria en el otro modo", "seria $" in s)
comprobar("sale en verde si todo cuadra", r.returncode == 0, str(r.returncode))

# --------------------------------- 6. EL ENTORNO MANDA SOBRE EL FICHERO
print("\n=== 6. EL ENTORNO SIGUE MANDANDO (las suites dependen de ello) ===")
os.environ[C.VAR_DGT] = "1"
os.environ[C.VAR_TEAC] = "1"
C2, D2, T2 = recargar()
comprobar("con AGENTE_DGT=1 la DGT se enciende aunque el modo sea solo-ley",
          D2.activa() and C2.modo_guardado() == C.SOLO_LEY)
comprobar("y el TEAC igual", T2.activa())
os.environ.pop(C.VAR_DGT, None)
os.environ.pop(C.VAR_TEAC, None)

print("\n" + "=" * 62)
print(f"FALLOS: {len(fallos)}")
for f in fallos:
    print("  -", f)
print(f"\nmodo al terminar: {C.modo_guardado()} · guia: {C.modo_de_la_guia()}")
sys.exit(1 if fallos else 0)
