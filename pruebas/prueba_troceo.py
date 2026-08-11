#!/usr/bin/env python3
"""NO SE INGIERE UNA NORMA QUE EL TROCEADOR NO HA ENTENDIDO.

    python pruebas/prueba_troceo.py

Cero red, cero API: se trocea el crudo del BOE que ya esta en disco.

EL CASO QUE LO DESTAPO. El libro sexto del Codi tributari de Catalunya numera
sus articulos «611-1», «621-2», «641-14»; `bloques.py` espera «Articulo 12».
Troceado: 10 citables -el articulo unico, las disposiciones y el anexo- y 151
bloques SIN RECONOCER, o sea LOS 160 ARTICULOS. Se habria escrito una norma
vacia con aspecto de norma ingerida: fichero, sello y resumen, todo correcto, y
ni un articulo dentro. Nada lo impedia; se cazo troceando en memoria a mano.

Y LO PEOR NO ES INGERIRLA: es que despues NO DA ERROR. Da respuestas peores en
silencio, que es el fallo que mas nos ha costado cazar en todo el proyecto.

EL UMBRAL SALE DE LOS DATOS. Troceadas las doce normas del corpus -2.554
bloques- el resultado es el mismo en todas: CERO sin reconocer. La catalana:
66,2%. No hay zona gris; lo normal es cero y lo roto es dos tercios.
"""
import json
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase1  # noqa: E402
from agente_fiscal import bloques as B  # noqa: E402
from agente_fiscal import parser as P  # noqa: E402
from agente_fiscal import sellos as S  # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:100]}" if not ok else ""))
    if not ok:
        fallos.append(que)


CRUDO = RAIZ / "datos" / "crudo"
CATALANA = "BOE-A-2024-6951"


def trocear(norma_id):
    """(citables, descartados) de una norma, desde el crudo en disco."""
    d = CRUDO / norma_id
    ms = sorted(f for f in d.glob("metadatos_*.json")
                if not f.name.endswith(".meta.json"))
    xs = sorted(f for f in d.glob("texto_*.xml")
                if not f.name.endswith(".meta.json"))
    if not ms or not xs:
        return None, None
    meta = (json.loads(ms[-1].read_text(encoding="utf-8")).get("data") or [{}])[0]
    return P.trocear(xs[-1].read_bytes(), norma_id, meta.get("titulo", ""), "")


def medida(norma_id):
    cit, desc = trocear(norma_id)
    if cit is None:
        return None
    sin = [r for r in desc if r["tipo"] == B.DESCONOCIDO]
    total = len(cit) + len(desc)
    return {"citables": len(cit), "sin_reconocer": len(sin), "total": total,
            "proporcion": len(sin) / total if total else 0.0,
            # El rotulo vive en `referencia`, no en `rubrica` -que viene
            # vacia en lo no reconocido- y el BOE lo separa del numero con
            # un espacio DURO. Las dos cosas costaron una prueba en rojo que
            # acusaba al codigo de algo que no pasaba.
            "ejemplos": [str(r.get("referencia") or r.get("id_bloque"))
                         .replace(chr(160), " ") for r in sin[:3]]}


# =========================================== 1. DE DONDE SALE EL UMBRAL
print("\n=== 1. EL UMBRAL SALE DE LAS NORMAS QUE YA ESTAN ===")
print("  No es una intuicion: es lo que dan las doce del corpus.\n")

corpus = sorted(f.name[: -len(".jsonl")]
                for f in (RAIZ / "datos" / "corpus").glob("*.jsonl")
                if not f.name.endswith(".descartados.jsonl"))
comprobar("hay doce normas en el corpus", len(corpus) == 12, len(corpus))

peor, bloques, medidas = 0.0, 0, {}
for n in corpus:
    m = medida(n)
    if m is None:
        comprobar(f"{n}: hay crudo para volver a trocearla", False, "sin crudo")
        continue
    medidas[n] = m
    bloques += m["total"]
    peor = max(peor, m["proporcion"])
    comprobar(f"{n}: {m['citables']:>3} citables, "
              f"{m['sin_reconocer']} sin reconocer",
              m["sin_reconocer"] == 0, m["ejemplos"])
print(f"\n    {len(medidas)} normas · {bloques:,} bloques · "
      f"peor proporcion sin reconocer: {peor:.1%}")
comprobar("NINGUNA de las doce pasa de cero sin reconocer", peor == 0.0, peor)
comprobar("y el tope elegido las deja pasar todas con margen",
          peor < fase1.TOPE_SIN_RECONOCER,
          f"{peor:.1%} vs {fase1.TOPE_SIN_RECONOCER:.0%}")

# =========================================== 2. LA CATALANA SE RECHAZA
print("\n=== 2. LA CATALANA NO PASA ===")
m = medida(CATALANA)
if m is None:
    comprobar("hay crudo de la catalana para probar el rechazo", False,
              f"falta datos/crudo/{CATALANA}")
else:
    print(f"    {m['citables']} citables · {m['sin_reconocer']} sin reconocer "
          f"de {m['total']} ({m['proporcion']:.1%})")
    comprobar("el troceador no la entiende, y se nota en los numeros",
              m["proporcion"] > fase1.TOPE_SIN_RECONOCER, m["proporcion"])
    comprobar("  y lo que no entiende es EL ARTICULADO, no un bloque raro",
              all(str(e).startswith("Artículo") for e in m["ejemplos"]),
              m["ejemplos"])
    comprobar("  hay mas bloques sin reconocer que citables: la segunda regla",
              m["sin_reconocer"] > m["citables"],
              f"{m['sin_reconocer']} vs {m['citables']}")
    comprobar("  y NO esta en el corpus", CATALANA not in corpus)
    comprobar("  ni tiene sello", CATALANA not in S.leer(RAIZ / "datos" / "corpus"))

# =========================================== 3. LO QUE SE LEE EN PANTALLA
print("\n=== 3. EL MENSAJE SIRVE PARA DIAGNOSTICAR ===")
print("  «No se puede ingerir» no vale: hay que poder saber POR QUE en el")
print("  momento, sin abrir el codigo.\n")

import contextlib  # noqa: E402
import io  # noqa: E402

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    codigo = fase1.modo_ingerir(CATALANA, descargar=False)
salida = buf.getvalue()
comprobar("se niega con codigo de fallo", codigo == 1, codigo)
comprobar("  dice cuantos reconoce", "10" in salida and "citable" in salida)
comprobar("  dice cuantos NO", "151" in salida and "228" in salida)
comprobar("  y en que proporcion", "66.2%" in salida, salida[-200:])
comprobar("  enseña ejemplos de lo que no ha entendido",
          "Artículo 611-1" in salida)
comprobar("  explica que suele significar",
          "numera sus articulos de otra forma" in salida)
comprobar("  avisa de que el fallo seria SILENCIOSO",
          "sin que nadie sepa por que" in salida)
comprobar("  y dice como forzarlo si hiciera falta", "--forzar" in salida)
comprobar("y NO ha escrito nada en el corpus",
          not (RAIZ / "datos" / "corpus" / f"{CATALANA}.jsonl").exists())

# =========================================== 4. EL FORZADO DEJA RASTRO
print("\n=== 4. FORZAR SE PUEDE, PERO QUEDA ESCRITO ===")
print("  Una puerta sin forma de abrirla acaba borrada el dia que estorba;")
print("  una que se abre sin dejar constancia es peor que no tenerla.\n")

import tempfile  # noqa: E402

d = Path(tempfile.mkdtemp())
f = d / "BOE-A-9999-1.jsonl"
f.write_text('{"norma_id":"BOE-A-9999-1","precepto":"1","texto":"x"}\n',
             encoding="utf-8")
S.sellar(f, forzado="ingerida con --forzar: 151 de 228 bloques (66.2%) sin reconocer")
guardado = S.leer(d)["BOE-A-9999-1"]
comprobar("el sello guarda que se forzo", "forzado" in guardado, guardado)
comprobar("  y con los numeros, no solo un si", "66.2%" in guardado["forzado"],
          guardado.get("forzado"))
est = S.estado(sorted(d.glob("*.jsonl")))
comprobar("y la pantalla «Que hay dentro» lo canta",
          "forzadas" in est["frase"] and "BOE-A-9999-1" in est["frase"],
          est["frase"])
comprobar("  sin llamarlo problema de integridad: su sello cuadra",
          not est["problemas"], est["problemas"])

# =========================================== 5. CONTROL NEGATIVO
print("\n=== 5. LA PRUEBA SABE PONERSE ROJA ===")
print("  Ninguna prueba se da por buena sin verla fallar cuando debe fallar.\n")

original = fase1.TOPE_SIN_RECONOCER
try:
    fase1.TOPE_SIN_RECONOCER = 0.99      # se afloja la puerta hasta el absurdo
    cit, desc = trocear(CATALANA)
    sin = [r for r in desc if r["tipo"] == B.DESCONOCIDO]
    pasa = (len(sin) / (len(cit) + len(desc))) <= fase1.TOPE_SIN_RECONOCER
    print(f"    con el tope al 99%, la proporcion del 66,2% pasaria: {pasa}")
    comprobar("(a) aflojando el tope la catalana pasaria por la primera regla, "
              "y el bloque 2 lo cazaria", pasa, pasa)
    # ...pero la SEGUNDA regla la sigue parando, que es justo para lo que esta.
    comprobar("(a bis) y aun asi la segunda regla la para: mas sin reconocer "
              "que citables", len(sin) > len(cit), f"{len(sin)} vs {len(cit)}")
finally:
    fase1.TOPE_SIN_RECONOCER = original

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    codigo = fase1.modo_ingerir(CATALANA, descargar=False)
comprobar("(a) y al deshacerlo vuelve a negarse", codigo == 1, codigo)

# (b) el sello deja de anotar el forzado
d2 = Path(tempfile.mkdtemp())
f2 = d2 / "BOE-A-9999-2.jsonl"
f2.write_text('{"norma_id":"BOE-A-9999-2","precepto":"1","texto":"x"}\n',
              encoding="utf-8")
S.sellar(f2)                                  # sin `forzado`
est2 = S.estado(sorted(d2.glob("*.jsonl")))
print(f"    sin anotar el forzado, la pantalla dice: «{est2['frase'][:58]}...»")
comprobar("(b) sin anotarlo, una norma forzada pareceria normal, y el "
          "bloque 4 lo cazaria", "forzadas" not in est2["frase"], est2["frase"])

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for x in fallos:
    print("  -", x)
sys.exit(1 if fallos else 0)
