#!/usr/bin/env python3
"""EL CAMPO «NORMATIVA» DE LA DGT: LA DESIGNACION DETRAS DE LOS ARTICULOS.

    python pruebas/prueba_normativa_dgt.py

Cero red, cero API.

QUE PROTEGE. La DGT escribe el campo de dos maneras, y hasta ahora solo se
entendia una:

    Ley 37/1992 arts. 75, 78, 80-cuatro      la norma DELANTE   (se entendia)
    Articulos 29, 227 y 249 de la Ley 58/2003  la norma DETRAS  (no se entendia)

En la segunda, la marca de articulo abre el trozo, lo de delante esta vacio y
la designacion salia vacia: 35 consultas de 845 se quedaban invisibles por
esto. Es el mismo error de direccion que ya se corrigio en las remisiones del
BOE: mirar solo hacia un lado.

Y POR QUE CADA CASO BUENO VIENE CON SU ADVERSARIO. Mirar hacia atras es
peligroso justo al reves: si se mira demasiado lejos, o demasiado, unos
articulos reales de OTRA norma acaban colgados de una de las nuestras, que es
peor que no resolverlos. Los tres adversarios de aqui no son inventados: son
los tres que aparecieron al medir sobre las 845 consultas, y cada uno costo
una version del arreglo.

    RDLeg 1/1993 arts 19, 21, 45         los del ITP, atribuidos a la LIVA
    Art. 9.Bis Regl. 282/2011 Ley 37/1992  el 9 bis europeo, atribuido a la LIVA
    Art. 214 Directiva 2006/112/CE Ley 37/1992  el 214 de la Directiva, idem

Ninguno se resuelve hoy, y ninguno debe resolverse nunca: ante la duda, nada.
"""
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4  # noqa: E402
from agente_fiscal import dgt as DGT  # noqa: E402

LGT = "BOE-A-2003-23186#0"
LIVA = "BOE-A-1992-28740#0"
RGAT = "BOE-A-2007-15984#0"
LIRPF = "BOE-A-2006-20764#0"

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:104]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix, _ = fase4.cargar_corpus()
NORMAS = ix.normas


def pares(texto, modulo=DGT):
    """(articulo, cuerpo) de cada precepto leido del campo."""
    return [(p.numero, p.cuerpo)
            for p in modulo.analizar_normativa(texto, NORMAS).preceptos]


# Cada entrada: (rotulo, campo tal cual lo escribe la DGT, pares esperados).
# El cuerpo vacio significa «no se resuelve», y es una expectativa tan dura
# como las otras: resolverlo seria el fallo.
CASOS = [
    # ---- 1. la designacion detras, que es lo que se arregla
    ("POSITIVO  la norma detras, con «de la»",
     "Artículos 29, 227 y 249 de la Ley 58/2003, de 17 de diciembre, "
     "General Tributaria.",
     [("29", LGT), ("227", LGT), ("249", LGT)]),
    ("POSITIVO  la norma detras, sin conector",
     "Artículo 93 Ley 58/2003",
     [("93", LGT)]),
    ("POSITIVO  «del Real Decreto», que se cortaba a si mismo",
     "Arts. 88, 107 y 131 del Real Decreto 1065/2007, de 27 de julio",
     [("88", RGAT), ("107", RGAT), ("131", RGAT)]),
    ("POSITIVO  articulo con sufijo",
     "Artículo 54 ter Real Decreto 1065/2007",
     [("54 ter", RGAT)]),

    # ---- 2. los adversarios: mirar detras sin pasarse
    # LA PAREJA DE LA GUARDA. Los dos campos son el mismo texto; lo unico que
    # cambia es si delante de la marca hay algo. La forma sale del campo de la
    # V1089-16 -«TRLITPAJD RDLeg 1/1993 arts 19, 21, 45. RDLeg 4/2015 ...»-,
    # acortada para dejar la norma de detras pegada a los numeros, que es la
    # unica postura en la que el anclaje ya no protege y solo queda la guarda.
    #
    # Medido sobre las 845: con el anclaje puesto, aflojar la guarda no rompe
    # ninguna consulta real; solo anade dos aciertos (el art. 105 de la
    # V1806-21 y la V2578-21). Se mantiene estricta de todos modos, porque el
    # riesgo es de construccion y no de muestra: en cuanto la DGT escriba un
    # campo con esta forma, la guarda floja cuelga articulos del ITP de la Ley
    # del IVA. Ante la duda, nada.
    ("ADVERSARIO  delante hay norma, aunque no la reconozca: NO se mira detras",
     "RDLeg 1/1993 art. 45 Ley 37/1992",
     [("45", "")]),
    ("POSITIVO  el mismo texto, pero sin nada delante: ahi si se mira",
     "art. 45 Ley 37/1992",
     [("45", LIVA)]),
    ("ADVERSARIO  la norma de detras no esta pegada a los numeros",
     "Art. 9.Bis Regl. 282/2011 Ley 37/1992 art. 11 y 69",
     [("9", "")]),
    ("ADVERSARIO  detras hay dos normas: se corta en la primera",
     "Art. 214 Directiva 2006/112/CE Ley 37/1992 art. 25-Tres",
     [("214", "")]),

    # ---- 3. las dos direcciones en el mismo campo, que es el caso real
    # Copiado tal cual del campo de la V1802-05, saltos de linea incluidos:
    # son el separador que parte el campo en trozos, y escribirlo en una sola
    # linea seria probar otra cosa.
    ("PAREJA  una norma que no tenemos y otra que si, en el mismo campo",
     "Art. 105 del Real Decreto Legislativo 3/2004\n\n"
     " Arts. 31, 66 y 194 de la Ley 58/2003",
     [("105", ""), ("31", LGT), ("66", LGT), ("194", LGT)]),

    # ---- 4. la forma de toda la vida, que no puede haberse movido
    ("CONTROL  la norma DELANTE sigue igual",
     "Ley 37/1992 arts. 75, 78, 80-cuatro, 89",
     [("75", LIVA), ("78", LIVA), ("80", LIVA), ("89", LIVA)]),
    ("CONTROL  sigla, coma y norma delante",
     "LIRPF, Ley 35/2006, Art. 33",
     [("33", LIRPF)]),
]

print("\n=== 1. LOS CASOS, CADA BUENO CON SU ADVERSARIO ===\n")
for rotulo, campo, esperado in CASOS:
    obtenido = pares(campo)
    comprobar(f"{rotulo}\n        «{' '.join(campo.split())[:78]}»",
              obtenido == esperado, obtenido)


# ============================================================ 2. MUTACIONES
print("\n=== 2. LA PRUEBA SABE PONERSE ROJA ===")
print("  Se rompe el codigo de verdad -el fichero, no un doble- y se mira "
      "cual cae.\n")

FUENTE = (RAIZ / "agente_fiscal" / "dgt.py").read_text(encoding="utf-8")


def con_el_codigo_roto(sustituir_esto, por_esto):
    """Carga `dgt.py` con un cambio real dentro. Devuelve el modulo mutado."""
    if sustituir_esto not in FUENTE:
        raise AssertionError(f"la mutacion ya no encaja: {sustituir_esto[:60]}")
    mod = types.ModuleType("agente_fiscal.dgt_mutado")
    mod.__package__ = "agente_fiscal"          # para el «from . import ...»
    mod.__file__ = str(RAIZ / "agente_fiscal" / "dgt.py")
    # `@dataclass` busca el modulo en `sys.modules` para resolver anotaciones,
    # asi que tiene que estar puesto ANTES de ejecutarlo.
    sys.modules[mod.__name__] = mod
    try:
        exec(compile(FUENTE.replace(sustituir_esto, por_esto, 1),
                     mod.__file__, "exec"), mod.__dict__)
    finally:
        del sys.modules[mod.__name__]
    return mod


MUTACIONES = [
    ("(a) se quita la rama entera: se vuelve a mirar solo hacia delante",
     "            if not designacion.strip():",
     "            if False:",
     ["POSITIVO  la norma detras, con «de la»",
      "POSITIVO  la norma detras, sin conector",
      "POSITIVO  «del Real Decreto», que se cortaba a si mismo",
      "POSITIVO  articulo con sufijo",
      "POSITIVO  el mismo texto, pero sin nada delante: ahi si se mira",
      "PAREJA  una norma que no tenemos y otra que si, en el mismo campo"]),

    ("(b) la guarda se afloja a «ninguna norma que yo reconozca»",
     "            if not designacion.strip():",
     "            if not _RE_NORMA_EXPLICITA.search(designacion):",
     ["ADVERSARIO  delante hay norma, aunque no la reconozca: "
      "NO se mira detras"]),

    ("(c) se deja de exigir que la norma vaya PEGADA a los numeros",
     "                primera = _RE_NORMA_EXPLICITA.match(detras)",
     "                primera = _RE_NORMA_EXPLICITA.search(detras)",
     ["ADVERSARIO  la norma de detras no esta pegada a los numeros"]),

    ("(d) no se corta la designacion donde empieza otra norma",
     "                    otra = _RE_NORMA_EXPLICITA.search(detras, primera.end())",
     "                    otra = None",
     ["ADVERSARIO  detras hay dos normas: se corta en la primera"]),

    ("(e) el corte busca la otra norma desde el indice 1, dentro de si misma",
     "                    otra = _RE_NORMA_EXPLICITA.search(detras, primera.end())",
     "                    otra = _RE_NORMA_EXPLICITA.search(detras, 1)",
     ["POSITIVO  «del Real Decreto», que se cortaba a si mismo",
      "POSITIVO  articulo con sufijo"]),
]

for rotulo, viejo, nuevo, deben_caer in MUTACIONES:
    print(f"  {rotulo}")
    roto = con_el_codigo_roto(viejo, nuevo)
    caidos = [r for r, campo, esperado in CASOS
              if pares(campo, roto) != esperado]
    for r in caidos:
        print(f"      cae: {r}")
    for esperado_caido in deben_caer:
        comprobar(f"    y cae «{esperado_caido[:56]}»",
                  esperado_caido in caidos, caidos)
    comprobar("    y NO se lleva por delante ningun otro caso",
              set(caidos) <= set(deben_caer),
              sorted(set(caidos) - set(deben_caer)))

# y al deshacerlo, todo verde otra vez
comprobar("(f) sin mutar, los casos vuelven a pasar todos",
          all(pares(campo) == esperado for _, campo, esperado in CASOS))

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f.replace("\n", " ")[:100])
sys.exit(1 if fallos else 0)
