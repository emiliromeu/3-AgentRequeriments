#!/usr/bin/env python3
"""TRAER LA VERSION NUEVA SIN ROMPER NADA. Cero red, cero API.

    python pruebas/prueba_actualizar.py

Dos piezas, y las dos existen porque la despensa la llena el Mac y viaja por
git: en la oficina el criterio nuevo aparece de golpe al hacer pull, y hasta
ahora no habia nada que lo dijera ni nada con que traerlo sin terminal.

  (a) EL AVISO: «han entrado N documentos nuevos». No toca git ni la red:
      compara con la cuenta de la ultima apertura.
  (b) `actualizar.bat`: lo pulsa una PERSONA. Nada se actualiza solo.

LO QUE ESTA SUITE VIGILA DEL .BAT es el ORDEN, que es donde esta el riesgo:
todo lo que solo MIRA va antes de lo que puede ROMPER. Un pull que aborta a
mitad deja el arbol a medias -«unable to checkout working tree»- y quien lo
sufre es quien tenia que consultar algo en ese momento.

El .bat no se puede ejecutar aqui -no hay Windows- asi que se comprueba lo que
si se puede: el orden, que no falte ningun camino de fallo y que ninguno se
quede mudo. El gemelo `actualizar.command` si se ejecuta, y es el mismo camino.
"""
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:110]}" if not ok else ""))
    if not ok:
        fallos.append(que)


# ==================================== 1. LAS RUTAS LARGAS
print("\n=== 1. LOS NOMBRES LARGOS, QUE ES CONTRA LO QUE IBA A CHOCAR ===")
print("  Windows corta las rutas a 260 caracteres CONTANDO la carpeta del")
print("  usuario. Habia nueve ficheros de 216: `git checkout` aborta A MITAD")
print("  y deja medio arbol escrito, que es el peor de los finales.\n")

import subprocess
seguidos = subprocess.run(["git", "ls-files"], cwd=str(RAIZ),
                          capture_output=True, text=True).stdout.splitlines()
largos = [f for f in seguidos if len(f) > 150]
comprobar("ningun fichero del repositorio pasa de 150 caracteres",
          not largos, largos[:2])
peor = max((len(f) for f in seguidos), default=0)
print(f"    el mas largo mide {peor} caracteres")

import medir_sin_resultados as MSR                # noqa: E402
largo = ("Reglamento General de las actuaciones y los procedimientos de "
         "gestion e inspeccion tributaria y de desarrollo de las normas "
         "comunes de los procedimientos de aplicacion de los tributos art. 195")
nombre = MSR._nombre_de_fichero(largo)
comprobar("y el que los generaba ya no puede volver a hacerlo",
          len(nombre) <= MSR.TOPE_NOMBRE + 5, f"{len(nombre)}: {nombre}")
comprobar("  recortando por en medio: la cola es lo que distingue un caso",
          nombre.endswith("art_195.html"), nombre)


# ==================================== 2. EL ORDEN DEL .BAT
print("\n=== 2. LO QUE SOLO MIRA VA ANTES DE LO QUE PUEDE ROMPER ===")
BAT = (RAIZ / "actualizar.bat").read_text("utf-8")

def antes(a, b):
    return BAT.index(a) < BAT.index(b)

comprobar("core.longpaths se pone ANTES de tocar el arbol",
          antes("core.longpaths true", "git pull"))
comprobar("  y solo para este repositorio, no global",
          "--global" not in BAT)
comprobar("se mira que no haya cambios sin guardar ANTES del pull",
          antes("git status --porcelain", "git pull"))
comprobar("el FETCH va antes que el PULL: trae referencias sin tocar el arbol",
          antes("git fetch", "git pull"))
comprobar("  y si el remoto no contesta, se para AHI",
          "goto sin_remoto" in BAT and antes("goto sin_remoto", "git pull"))
comprobar("el pull es --ff-only: no inventa una fusion en el equipo de nadie",
          "git pull --ff-only" in BAT)


# ==================================== 3. NINGUN CAMINO MUDO
print("\n=== 3. NINGUNA SALIDA SE QUEDA CALLADA ===")
etiquetas = set(re.findall(r"^:(\w+)", BAT, re.M))
gotos = set(re.findall(r"goto\s+(\w+)", BAT))
comprobar("todos los `goto` tienen su etiqueta", not (gotos - etiquetas),
          gotos - etiquetas)
comprobar("  y no sobra ninguna etiqueta", not (etiquetas - gotos),
          etiquetas - gotos)
for camino, pista in (("sin_remoto", "permiso"), ("hay_cambios", "Emili"),
                      ("pull_fallido", "sigue funcionando"),
                      ("sin_git", "Avisa a Emili"), ("sin_repo", "instalar")):
    trozo = BAT.split(f":{camino}")[1].split("exit /b")[0]
    comprobar(f"«{camino}» explica que hacer", pista.lower() in trozo.lower(),
              trozo[:80])
    comprobar(f"   y espera antes de cerrarse", "pause" in trozo)
comprobar("cuando el remoto falla se dice que NO se ha tocado nada",
          "no se ha tocado nada" in
          BAT.split(":sin_remoto")[1].split("exit /b")[0].lower())
comprobar("cuando el pull falla se dice que el agente SIGUE funcionando",
          "sigue funcionando" in
          BAT.split(":pull_fallido")[1].split("exit /b")[0].lower())

# Las reglas de Windows de siempre.
ordenes = [l for l in BAT.splitlines()
           if l.strip() and not l.strip().upper().startswith("REM")]
comprobar("ni un parentesis suelto dentro de un echo",
          not [l for l in ordenes if l.strip().lower().startswith("echo")
               and re.search(r"(?<!\^)[()]", l)])
comprobar("ni una tilde en una linea de orden",
          not [l for l in ordenes if re.search(r"[áéíóúñÁÉÍÓÚÑ¿¡]", l)])


# ==================================== 4. EL AVISO DE CRITERIO NUEVO
print("\n=== 4. EL AVISO DE QUE HA ENTRADO CRITERIO NUEVO ===")
print("  La primera vez NO dice nada: sin marca anterior, la unica cuenta")
print("  honrada seria «hay 2.400», que es un inventario y no una novedad.\n")

import json
import shutil
import tempfile
import fase4                                     # noqa: E402
from agente_fiscal import cobertura as COB       # noqa: E402

ix, _g = fase4.cargar_corpus()
corral = Path(tempfile.mkdtemp())
_ruta = COB._ruta_marca
COB._ruta_marca = lambda: corral / "visto.json"
try:
    comprobar("sin marca previa, no se dice nada",
              COB.aviso_de_novedades(ix) == "", COB.aviso_de_novedades(ix))
    comprobar("  pero la marca queda puesta", (corral / "visto.json").is_file())
    comprobar("con la despensa igual, sigue callado",
              COB.aviso_de_novedades(ix) == "")
    d = json.loads((corral / "visto.json").read_text("utf-8"))
    (corral / "visto.json").write_text(json.dumps(
        {"documentos": d["documentos"] - 40, "cuando": "2026-08-20"}))
    av = COB.aviso_de_novedades(ix)
    comprobar("si han entrado 40, lo dice", "40" in av, av)
    comprobar("  y dice desde cuando", "20/08" in av, av)
    comprobar("  y para que sirve: el segundo boton", "criterio" in av, av)
    comprobar("y despues se calla: no se repite cada dia",
              COB.aviso_de_novedades(ix) == "")
finally:
    COB._ruta_marca = _ruta
    shutil.rmtree(corral, ignore_errors=True)

comprobar("la marca no viaja por git: es de ESTE equipo",
          "datos/dgt/visto.json" in (RAIZ / ".gitignore").read_text("utf-8"))
# LAS ORDENES, NO LOS COMENTARIOS. Es la tercera vez que una comprobacion se
# da por buena o por mala leyendo la frase que EXPLICA algo en vez de la que lo
# hace: en `interfaz.py` la palabra sale en un comentario sobre GUIA.md.
_ordenes_ventana = "\n".join(
    l for l in (RAIZ / "interfaz.py").read_text("utf-8").splitlines()
    if l.strip() and not l.strip().startswith("#"))
comprobar("y la ventana no actualiza sola: solo avisa",
          "git pull" not in _ordenes_ventana and
          "git fetch" not in _ordenes_ventana)

print("\n" + "=" * 74)
if fallos:
    print(f"{len(fallos)} FALLO(S):")
    for f in fallos:
        print(f"   - {f}")
    sys.exit(1)
print("TODO EN VERDE · se avisa, y actualiza quien decide")
sys.exit(0)
