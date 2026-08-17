#!/usr/bin/env python3
"""EL ARRANQUE EXIGE QUE EL CORPUS SEA EL QUE DICE SER. Cero red, cero API.

    python pruebas/prueba_sellos.py

`sellos.comprobar` existia desde hace tiempo y NADIE LO EXIGIA: solo se usaba
para pintar una linea en «Que hay dentro». Un corpus mutilado abria igual.

POR QUE ESTO SI BLOQUEA, cuando la guia y la despensa no. La regla del proyecto
es que un DERIVADO que falta se rehace y se sigue -la guia se regenera sola-,
pero una PROMESA rota se para. El corpus es una promesa: el agente dice que
contesta con el texto oficial del BOE. Media ley no se regenera sola, y lo peor
es que no da error: da respuestas peores en silencio, con la misma cara de
seguridad que las buenas.

Y LO QUE NO PUEDE PASAR es que bloquee donde no debe. Un corpus SIN SELLAR no
esta corrupto: esta sin sellar, que es el estado de cualquier corpus de prueba
montado en un directorio temporal. Ahi se abre igual, como se decidio.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import instalar                                  # noqa: E402
from agente_fiscal import sellos as SL           # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:112]}" if not ok else ""))
    if not ok:
        fallos.append(que)


def corpus_de_mentira(sellar=True, mutilar=None):
    """Un corpus en un temporal. `mutilar` = cuantas lineas quitar."""
    d = Path(tempfile.mkdtemp())
    (d / "datos" / "corpus").mkdir(parents=True)
    ruta = d / "datos" / "corpus" / "BOE-A-1111-1111.jsonl"
    ruta.write_text("".join(
        json.dumps({"norma_id": "BOE-A-1111-1111", "tipo": "articulo",
                    "numero": str(i), "referencia": f"Articulo {i}"}) + "\n"
        for i in range(1, 21)), encoding="utf-8")
    if sellar:
        SL.sellar(ruta)
    if mutilar:
        lineas = ruta.read_text(encoding="utf-8").splitlines(True)
        ruta.write_text("".join(lineas[:-mutilar]), encoding="utf-8")
    return d, ruta


# ==================================== 1. EL CORPUS DE ESTE EQUIPO
print("\n=== 1. EL DE VERDAD CUADRA ===")
comprobar("el corpus de este equipo no tiene problemas",
          not instalar.corpus_no_cuadra(), instalar.corpus_no_cuadra()[:2])
comprobar("y por tanto el arranque no lo marca como roto",
          "corpus_roto" not in instalar.que_falta(), instalar.que_falta())

# ==================================== 2. MUTILADO: SE BLOQUEA
print("\n=== 2. UN CORPUS MUTILADO NO ABRE ===")
print("  Se le quitan cinco preceptos DESPUES de sellarlo, que es exactamente")
print("  lo que pasa cuando una ingesta se corta a medias.\n")

d, ruta = corpus_de_mentira(sellar=True, mutilar=5)
problemas = SL.comprobar([ruta])
comprobar("`comprobar` lo detecta", bool(problemas), problemas)
if problemas:
    print(f"    «{problemas[0][:100]}»")
    comprobar("  dice QUE norma no cuadra", "BOE-A-1111-1111" in problemas[0])
    comprobar("  dice CUANTOS preceptos faltan", "faltan 5" in problemas[0],
              problemas[0])
    comprobar("  y da el comando para reingerirla",
              "fase1.py ingerir" in problemas[0])
shutil.rmtree(d, ignore_errors=True)

# ==================================== 3. SIN SELLAR: SIGUE ABRIENDO
print("\n=== 3. SIN SELLAR NO SE BLOQUEA: NO ES LO MISMO QUE ROTO ===")
print("  Es el estado de cualquier corpus de prueba en un temporal, y el de")
print("  cualquier copia anterior a que esto existiera.\n")

d2, ruta2 = corpus_de_mentira(sellar=False)
comprobar("un corpus SIN SELLAR no da ningun problema",
          SL.comprobar([ruta2]) == [], SL.comprobar([ruta2]))
d3, ruta3 = corpus_de_mentira(sellar=False, mutilar=5)
comprobar("  ni siquiera mutilado, porque no hay contra que comparar",
          SL.comprobar([ruta3]) == [], SL.comprobar([ruta3]))
comprobar("  y `estado` NO lo canta como verde: lo dice sin sellar",
          SL.estado([ruta2])["sellado"] is False)
shutil.rmtree(d2, ignore_errors=True)
shutil.rmtree(d3, ignore_errors=True)

# Y un corpus vacio tampoco bloquea: ahi lo que falta es el corpus entero, y de
# eso ya se encarga el paso de la ingesta.
comprobar("sin ningun .jsonl no se bloquea por sellos", SL.comprobar([]) == [])

# ==================================== 4. CONTROL NEGATIVO
print("\n=== 4. LA PRUEBA SABE PONERSE ROJA ===")
print("  Se quita la exigencia del arranque y se mira que un corpus mutilado")
print("  vuelve a abrir.\n")

import types                                     # noqa: E402

FUENTE = (RAIZ / "instalar.py").read_text("utf-8")
VIEJO = ("    elif corpus_no_cuadra():\n"
         "        # SOLO SI NO FALTA: si falta, primero se baja; comprobar "
         "sellos de algo\n"
         "        # que aun no esta seria decir dos cosas a la vez.\n"
         "        pendiente.append(\"corpus_roto\")")
comprobar("la exigencia esta en `que_falta`, que es donde se decide si abre",
          VIEJO in FUENTE)

if VIEJO in FUENTE:
    mod = types.ModuleType("instalar_roto")
    mod.__file__ = str(RAIZ / "instalar.py")
    sys.modules[mod.__name__] = mod
    try:
        exec(compile(FUENTE.replace(VIEJO, "", 1), mod.__file__, "exec"),
             mod.__dict__)
    finally:
        del sys.modules[mod.__name__]
    # Se le apunta a un corpus mutilado de verdad.
    d4, ruta4 = corpus_de_mentira(sellar=True, mutilar=5)
    mod.CORPUS = ruta4.parent
    instalar_ok = instalar.CORPUS
    try:
        instalar.CORPUS = ruta4.parent
        comprobar("(a) CON la exigencia, el corpus mutilado se marca como roto",
                  bool(instalar.corpus_no_cuadra()),
                  instalar.corpus_no_cuadra())
    finally:
        instalar.CORPUS = instalar_ok
    comprobar("(b) sin la exigencia, `que_falta` ya no lo dice y el agente "
              "abriria", "corpus_roto" not in mod.que_falta(), mod.que_falta())
    shutil.rmtree(d4, ignore_errors=True)

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
