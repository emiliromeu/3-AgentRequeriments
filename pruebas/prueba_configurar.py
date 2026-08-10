#!/usr/bin/env python3
"""LA VENTANA Y LA HOJA DE LA MESA DICEN LO MISMO. Cero red, cero API.

QUE PROTEGE ESTA SUITE, Y POR QUE CAMBIO
----------------------------------------
Nacio en la fase 20 protegiendo un INTERRUPTOR: `configurar.py --solo-ley` /
`--con-criterio` encendia cuatro piezas a la vez y esta suite comprobaba que
ninguna se quedaba atras.

En la fase 21 ese interruptor DESAPARECE: los dos botones estan siempre en la
ventana y el modo lo elige quien pulsa, consulta a consulta. Con eso se va casi
todo el estado que podia descuadrarse, y esta suite pasa a proteger lo unico
que queda -y lo que de verdad importaba siempre-:

  · que los DOS BOTONES aparezcan sin tocar ningun fichero;
  · que TODA frase que sale en pantalla este dentro de `GUIA.md`, porque la
    guia se imprime y el papel no se entera de que el codigo ha cambiado;
  · que si no lo esta, el agente NO ABRA, y diga cual es la frase.

Mejor no abrir que abrir mintiendo: quien lea la hoja decidira con la hoja.
"""
import contextlib
import io
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
    for v in (C.VAR_DGT, C.VAR_TEAC):
        e.pop(v, None)
    return subprocess.run([sys.executable, "configurar.py", *args],
                          cwd=str(RAIZ), capture_output=True, text=True, env=e)


def recargar():
    """Los modulos se reimportan para que nada quede pegado de la vez anterior."""
    for m in [x for x in list(sys.modules) if x.startswith("agente_fiscal")]:
        del sys.modules[m]
    for m in ("interfaz",):
        sys.modules.pop(m, None)
    from agente_fiscal import configuracion as C2
    from agente_fiscal import dgt as D2
    from agente_fiscal import teac as T2
    return C2, D2, T2


# ------------------------------------- 1. LOS BOTONES NO DEPENDEN DE FICHEROS
print("\n=== 1. LOS DOS BOTONES APARECEN SIN TOCAR NADA ===")
print("  Es para enseñarlo delante de gente. Si para que aparezca el segundo")
print("  boton hubiera que editar un fichero, habria que abrir una consola.\n")
comprobar("no queda fichero de modo que haya que mantener",
          not (RAIZ / "modo.json").exists(),
          "sigue habiendo modo.json")
comprobar("ni funcion para guardarlo", not hasattr(C, "guardar_modo"))
comprobar("ni funcion que decida si el segundo boton existe",
          not hasattr(C, "hay_boton_criterio"))
comprobar("ni textos de ventana atados a una variable global",
          not hasattr(C, "textos_con_criterio"))

fuente_ventana = (RAIZ / "interfaz.py").read_text("utf-8")
i_criterio = fuente_ventana.find("boton_criterio = ")
comprobar("el segundo boton se crea SIEMPRE, sin ningun if delante",
          i_criterio > 0
          and "if " not in fuente_ventana[i_criterio - 260:i_criterio],
          fuente_ventana[max(0, i_criterio - 90):i_criterio + 40])

# ------------------------------------- 2. LA GUIA, LO UNICO QUE PUEDE MENTIR
print("\n=== 2. DESCOORDINAR LA GUIA: EL AGENTE NO ABRE ===")
print("  Se rompe cada cosa por separado y se mira si lo detecta Y si dice")
print("  CUAL es. Decir «algo va mal» no sirve para arreglarlo.\n")

guardada = C.GUIA.read_text("utf-8")

# a) la guia sin marca, como si alguien la hubiera editado a mano
C.GUIA.write_text(guardada.replace(C.MARCA.format(modo=C.UNICO), ""),
                  encoding="utf-8")
C2, _D, _T = recargar()
r2 = C2.revisar()
print(f"    (a) GUIA.md sin marca -> {r2.descuadres}")
comprobar("(a) lo detecta", not r2.coherente)
comprobar("(a) y dice que es GUIA.md",
          any("GUIA.md" in d for d in r2.descuadres), str(r2.descuadres))
C.GUIA.write_text(guardada, encoding="utf-8")

# b) una frase que sale en pantalla y NO esta en la guia. Es el caso REAL: no
#    hace falta que nadie edite la guia, basta con cambiar un texto de la
#    ventana y no acordarse del papel.
sin_frase = guardada
import interfaz  # noqa: E402

quitada = interfaz.NO_ENCONTRADO_CON_CRITERIO
for trozo in (quitada, quitada.replace("todavia", "todavía")):
    sin_frase = sin_frase.replace(trozo, "(esta frase la borro alguien)")
comprobar("(b) la frase estaba en la guia y se ha podido quitar",
          sin_frase != guardada,
          "la mutacion NO ocurrio: la prueba no probaria nada")
C.GUIA.write_text(sin_frase, encoding="utf-8")
C2, _D, _T = recargar()
r2 = C2.revisar()
print(f"    (b) una frase de la ventana fuera de la guia -> "
      f"{len(r2.descuadres)} descuadre(s)")
comprobar("(b) lo detecta", not r2.coherente)
comprobar("(b) y dice QUE frase es",
          any(quitada[:40] in d for d in r2.descuadres), str(r2.descuadres)[:200])
comprobar("(b) y explica la consecuencia, no solo el sintoma",
          any("leera otra cosa" in d for d in r2.descuadres), str(r2.descuadres)[:200])
C.GUIA.write_text(guardada, encoding="utf-8")
C2, _D, _T = recargar()
comprobar("(b) y al deshacerlo vuelve a estar coherente", C2.revisar().coherente,
          str(C2.revisar().descuadres))

# --------------------------------------- 3. Y LO DICE EN CRISTIANO
print("\n=== 3. LO QUE VE UNA PERSONA ===")
C.GUIA.write_text(sin_frase, encoding="utf-8")
C2, _D, _T = recargar()
try:
    C2.exigir_coherencia()
    comprobar("levanta el aviso", False, "no lo levanto")
except C2.Descoordinado as e:
    lineas = e.en_cristiano()
    print("    " + "\n    ".join(lineas))
    comprobar("dice que NO se abre", any("no se abre" in l.lower() for l in lineas))
    comprobar("dice de donde sale la guia",
              any("guias/GUIA.md" in l for l in lineas), str(lineas))
    comprobar("dice a quien avisar", any("Emili" in l for l in lineas))
    comprobar("y explica POR QUE no se abre a medias",
              any("decidiria" in l for l in lineas))
    comprobar("sin una sola traza de python",
              not any("Traceback" in l or "  File " in l for l in lineas))

# ------------------------------------------- 4. LA TERMINAL TAMBIEN PARA
print("\n=== 4. LA TERMINAL PARA IGUAL, ANTES DE GASTAR UNA LLAMADA ===")
r = subprocess.run([sys.executable, "fase4.py", "consultar", "algo",
                    "--ejercicio", "2023", "--motor", "ensayo"],
                   cwd=str(RAIZ), capture_output=True, text=True)
comprobar("fase4 se niega", r.returncode != 0, f"codigo {r.returncode}")
comprobar("y lo dice", "medio configurar" in r.stdout.lower(), r.stdout[:200])
comprobar("sin llegar a consultar", "CONSULTA FISCAL" not in r.stdout)

C.GUIA.write_text(guardada, encoding="utf-8")
C2, _D, _T = recargar()

# --------------------------------------------------- 5. QUE HAY DENTRO
print("\n=== 5. configurar.py DICE LO QUE HAY (lo mismo que la ventana) ===")
r = limpio()
s = r.stdout
comprobar("dice que los dos botones estan siempre",
          "los dos botones" in s.lower(), s[:160])
comprobar("dice las normas cargadas", "722" in s)
comprobar("y cuantas consultas de la DGT hay", "consultas de la DGT" in s)
comprobar("y cuantas resoluciones", "resoluciones economico" in s)
comprobar("y lo que cuesta CADA boton",
          "Consultar la ley" in s and "Consultar tambien el criterio" in s, s[-400:])
comprobar("con los dos precios en euros", s.count("EUR") >= 2)
comprobar("sale en verde si todo cuadra", r.returncode == 0, str(r.returncode))
comprobar("y ya no ofrece encender ni apagar nada",
          "--solo-ley" not in s and "--con-criterio" not in s, s[:200])

# --------------------------------- 6. EL ENTORNO MANDA (las suites dependen)
print("\n=== 6. EL ENTORNO SIGUE MANDANDO EN LA TERMINAL ===")
print("  Las suites encienden la DGT con AGENTE_DGT=1 para una ejecucion y no")
print("  deben depender de como este el equipo, ni dejarlo tocado.\n")
C2, D2, T2 = recargar()
comprobar("sin variables, el valor por defecto es la ley sola", not D2.activa())
os.environ[C.VAR_DGT] = "1"
os.environ[C.VAR_TEAC] = "1"
C2, D2, T2 = recargar()
comprobar("con AGENTE_DGT=1 la DGT se enciende", D2.activa())
comprobar("y el TEAC igual", T2.activa())
comprobar("y eso NO descoordina nada: ya no hay estado global que cuadrar",
          C2.revisar().coherente, str(C2.revisar().descuadres))
os.environ.pop(C.VAR_DGT, None)
os.environ.pop(C.VAR_TEAC, None)

# --------------------- 7. EL MODO ES DE CADA CONSULTA
print("\n=== 7. EL MODO ES DE CADA CONSULTA, Y LA RESPUESTA LO REGISTRA ===")
print("  Es lo que quita el estado oculto: la respuesta sabe con que se hizo")
print("  porque se decidio al pulsarla, no en una variable de hace semanas.\n")
import fase4  # noqa: E402
from agente_fiscal import modelo as MOD  # noqa: E402

ix, g = fase4.cargar_corpus()
for pedido in (False, True):
    m = MOD.crear_motor("ensayo")
    with contextlib.redirect_stdout(io.StringIO()):
        res = fase4.consultar("deduccion de cuotas soportadas", 2023, m, ix, g,
                              con_criterio=pedido)
    comprobar(f"con_criterio={pedido}: la respuesta lo registra",
              res.get("con_criterio") is pedido, str(res.get("con_criterio")))
    comprobar(f"con_criterio={pedido}: y el texto de estado es el suyo",
              interfaz.explicacion(res["estado"], pedido)
              == interfaz.EXPLICACION_POR_MODO[res["estado"]][pedido])

# ----------------------------- 8. CONTROL NEGATIVO: VERLA FALLAR
print("\n=== 8. LA PRUEBA SABE PONERSE ROJA ===")
print("  Ninguna prueba se da por buena sin verla fallar cuando debe fallar.")
print("  Se quita la comprobacion de frases y se mira si esta suite lo pilla.\n")

# OJO: `revisar()` hace `import interfaz` por dentro, y `recargar()` ha vaciado
# sys.modules varias veces. Si se muta el objeto que tiene esta prueba en la
# mano puede ser OTRO modulo distinto del que mira `revisar()`, y entonces la
# mutacion no ocurre y la suite pasa sin haber probado nada. Se coge el que hay
# en sys.modules AHORA, que es el que se va a usar.
import importlib  # noqa: E402

vivo = importlib.import_module("interfaz")
original = vivo.TEXTOS_DE_ESTADO
try:
    vivo.TEXTOS_DE_ESTADO = []              # como si nadie comprobara nada
    C.GUIA.write_text(sin_frase, encoding="utf-8")
    r2 = C.revisar()
    print(f"    sin frases que comprobar, con la guia rota: "
          f"coherente={r2.coherente}")
    comprobar("sin la comprobacion, una guia rota pasaria por buena",
              r2.coherente,
              "la mutacion no ocurrio: revisar() no mira interfaz.TEXTOS_DE_ESTADO")
    comprobar("y el bloque 2 lo habria cazado (con la lista entera sale rojo)",
              True)
finally:
    vivo.TEXTOS_DE_ESTADO = original
    C.GUIA.write_text(guardada, encoding="utf-8")

r_final = C.revisar()
comprobar("el equipo queda como estaba y coherente", r_final.coherente,
          str(r_final.descuadres))

print("\n" + "=" * 62)
print(f"FALLOS: {len(fallos)}")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
