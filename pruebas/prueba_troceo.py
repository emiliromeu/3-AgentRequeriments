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

# ESTA SUITE NO PUEDE ESCRIBIR EN EL CORPUS DE VERDAD. Se desvia AQUI, una vez
# y para todo el fichero, no bloque a bloque.
#
# Por que asi: la primera version lo desviaba solo donde llamaba a
# `modo_ingerir` a proposito... y habia OTRA llamada, en el control negativo,
# que se me paso. Mientras el troceador no entendio la numeracion del Codi las
# dos se negaban y no pasaba nada; el dia que se arreglo, LA PRUEBA INGIRIO LA
# NORMA CATALANA EN EL CORPUS DE PRODUCCION -13 normas, 2.121 preceptos, el
# sello descuadrado y el banco midiendo otro corpus-. Y lo hizo DOS VECES,
# porque la primera vez lo tape sitio a sitio.
#
# Una prueba que muta lo que mide no es una prueba. Si hay que desviar algo, se
# desvia en la puerta.
CORPUS_REAL = fase1.DIR_CORPUS
import tempfile as _tmp  # noqa: E402
fase1.DIR_CORPUS = Path(_tmp.mkdtemp())


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
                for f in CORPUS_REAL.glob("*.jsonl")
                if not f.name.endswith(".descartados.jsonl"))
# TRECE desde que entro la catalana. Se comprueba que estan TODAS las que
# tienen crudo en disco, no un numero escrito: un numero a mano caduca cada vez
# que se ingiere algo, y ya nos ha pasado.
comprobar("estan en el corpus todas las normas ingeridas",
          len(corpus) >= 12, len(corpus))

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
    # HISTORIA, PORQUE EXPLICA LA PUERTA: cuando se escribio esto la catalana
    # daba 10 citables y 151 sin reconocer (66,2%), y la puerta la paraba. Al
    # enseñarle al troceador la numeracion compuesta del Codi paso a 0 sin
    # reconocer. La puerta no se toco: dejo de tener motivo para pararla.
    comprobar("el troceador YA la entiende: cero sin reconocer",
              m["sin_reconocer"] == 0, m["sin_reconocer"])
    comprobar("  y reconoce su articulado entero, no cuatro disposiciones",
              m["citables"] > 150, m["citables"])
    # YA ESTA DENTRO, y entro por la puerta: la comprobacion de bloques sin
    # reconocer la dejo pasar porque no le queda ninguno.
    comprobar("  y ya esta en el corpus, con su sello", CATALANA in corpus
              and CATALANA in S.leer(CORPUS_REAL))
    comprobar("  sin haberla forzado",
              not S.leer(CORPUS_REAL).get(CATALANA, {}).get("forzado"),
              S.leer(CORPUS_REAL).get(CATALANA, {}).get("forzado"))

# =========================================== 3. LO QUE SE LEE EN PANTALLA
print("\n=== 3. EL MENSAJE SIRVE PARA DIAGNOSTICAR ===")
print("  «No se puede ingerir» no vale: hay que poder saber POR QUE en el")
print("  momento, sin abrir el codigo.\n")

import contextlib  # noqa: E402
import io  # noqa: E402

# ESTA PRUEBA NO ESCRIBE EN EL CORPUS DE VERDAD. NUNCA.
#
# La primera version llamaba a `fase1.modo_ingerir` directamente, dando por
# hecho que se negaria. Mientras el troceador no entendio la numeracion del
# Codi, se nego y no paso nada. El dia que se arreglo la numeracion, la puerta
# dejo de rechazarla y ESTA PRUEBA INGIRIO LA NORMA CATALANA EN EL CORPUS DE
# PRODUCCION: 13 normas, 2.121 preceptos, el sello descuadrado y el banco
# midiendo otro corpus. Una prueba que muta lo que mide no es una prueba.
#
# Ahora se ingiere contra un directorio TEMPORAL. Lo que se comprueba es el
# mensaje y el codigo, que es lo que importa, y lo que se escriba se escribe
# donde no molesta.
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    codigo = fase1.modo_ingerir(CATALANA, descargar=False)
salida = buf.getvalue()

# Se ingiere contra el temporal, asi que el corpus de verdad no se toca aunque
# esta norma ya no se rechace.
n_antes = len([f for f in CORPUS_REAL.glob("*.jsonl")
               if not f.name.endswith(".descartados.jsonl")])
comprobar("la prueba NO ha escrito en el corpus de verdad",
          n_antes == len(corpus), f"{n_antes} vs {len(corpus)}")

# DESDE QUE EL TROCEADOR ENTIENDE LA NUMERACION DEL CODI, esta norma YA NO se
# rechaza por bloques sin reconocer: pasa de 151 a 0. La puerta sigue estando y
# sigue haciendo su trabajo -lo prueba el bloque 1 con las doce y el control
# negativo de abajo-, pero esta norma dejo de ser su caso.
m = medida(CATALANA)
comprobar("ahora la catalana pasa la puerta del troceo", codigo == 0, codigo)
comprobar("  porque ya no hay bloques sin reconocer",
          m["sin_reconocer"] == 0, m["sin_reconocer"])
comprobar("  y se reconocen sus articulos, no cuatro disposiciones",
          m["citables"] > 150, m["citables"])
comprobar("  con la numeracion compuesta entera",
          any("611-1" in str(r.get("referencia", "")) for r in trocear(CATALANA)[0]))
comprobar("y el mensaje de la puerta ya no aparece",
          "NO SE INGIERE" not in salida, salida[-160:])

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

# (a) UNA NORMA QUE EL TROCEADOR DE VERDAD NO ENTIENDE.
#
# El control no puede depender de que exista por ahi una norma rota: la
# catalana lo estuvo y dejo de estarlo en cuanto se le enseño la numeracion
# compuesta, y este bloque se quedo sin sujeto. Se fabrica una, con rotulos
# que ninguna regla reconoce, y asi el control mide la PUERTA y no el estado
# del mundo.
import tempfile as _t2  # noqa: E402
import xml.etree.ElementTree as _ET  # noqa: E402

RARA = "BOE-A-9999-99999"
raiz = _ET.Element("documento")
for n in range(30):
    # Cinco reconocibles y veinticinco no: asi la proporcion no es 100% y el
    # control puede aflojar el tope para ver que la PRIMERA regla se rinde y
    # la segunda sigue parandola. Con 100% no se puede distinguir una de otra.
    titulo = f"Articulo {n}" if n < 5 else f"Regla ~{n}~ del cuaderno"
    b = _ET.SubElement(raiz, "bloque", id=f"b{n}", tipo="precepto",
                       titulo=titulo)
    v = _ET.SubElement(b, "version", id_norma=RARA,
                       fecha_publicacion="20260101", fecha_vigencia="20260101")
    _ET.SubElement(v, "p").text = f"Texto de la regla {n}."
xml_raro = _ET.tostring(raiz, encoding="utf-8")

d_raro = Path(_t2.mkdtemp())
(d_raro / RARA).mkdir()
cit_raro, desc_raro = P.trocear(xml_raro, RARA, "Norma de prueba", "")
sin_raro = [r for r in desc_raro if r["tipo"] == B.DESCONOCIDO]
prop = len(sin_raro) / (len(cit_raro) + len(desc_raro))
print(f"    la norma fabricada da {len(cit_raro)} citables y "
      f"{len(sin_raro)} sin reconocer ({prop:.0%})")
comprobar("(a) el troceador NO entiende una norma con rotulos raros",
          prop > fase1.TOPE_SIN_RECONOCER, prop)
comprobar("(a) y la segunda regla tambien la para: mas sin reconocer que "
          "citables", len(sin_raro) > len(cit_raro),
          f"{len(sin_raro)} vs {len(cit_raro)}")

original = fase1.TOPE_SIN_RECONOCER
try:
    fase1.TOPE_SIN_RECONOCER = 0.99
    pasa_primera = prop <= fase1.TOPE_SIN_RECONOCER
    print(f"    con el tope al 99%, la primera regla la dejaria pasar: "
          f"{pasa_primera}")
    comprobar("(a) aflojando el tope, la primera regla se rinde", pasa_primera)
    comprobar("(a bis) pero la segunda la sigue parando, que es para lo que "
              "esta", len(sin_raro) > len(cit_raro))
finally:
    fase1.TOPE_SIN_RECONOCER = original

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
