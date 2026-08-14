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
# EL REGLAMENTO ES EL #1, NO EL #0, Y ESTO ESTUVO MAL DESDE SIEMPRE.
#
# El documento BOE-A-2007-15984 trae dos articulados: el Real Decreto
# 1065/2007 que aprueba -UN articulo, el «unico»- y el Reglamento General de
# las actuaciones, que tiene 233. La constante se llamaba RGAT y apuntaba al
# decreto, asi que los casos esperaban el articulo 88, el 107, el 131 y el
# «54 ter» en un cuerpo que no tiene ninguno.
#
# Pasaban porque el sistema resolvia igual de mal: la designacion «Real Decreto
# 1065/2007» resuelve limpiamente al decreto y nadie comprobaba que el articulo
# existiera alli. La suite y el codigo estaban equivocados EN EL MISMO SENTIDO,
# que es como un error se queda años.
#
# Corregido el 14/08/2026 con la comprobacion de existencia. La evidencia es
# del corpus: los siete articulos de estos casos estan en el #1 y ninguno en el
# #0. Mismo caso que el «Real Decreto Legislativo 1/1993» del banco.
RGAT = "BOE-A-2007-15984#1"
LIRPF = "BOE-A-2006-20764#0"
LIS = "BOE-A-2014-12328#0"
IP = "BOE-A-1991-14392#0"
RIVA1 = "BOE-A-1992-28925#1"
ISD = "BOE-A-1987-28141#0"

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
    # ACTUALIZADO EL 14/08/2026, y lo que vigila NO ha cambiado: que el 45 no
    # se cuelgue de la norma de DETRAS. Lo que ha cambiado es que la de delante
    # ya se lee: hasta hoy «RDLeg 1/1993» no resolvia -era la deuda de la
    # abreviatura, 68 consultas de 128- y el caso esperaba "" porque no habia
    # nada mejor. Ahora resuelve al Texto refundido, que es de donde ES el
    # articulo 45; se comprobo contra el corpus antes de tocar esto: el 45
    # esta en el #1 y no en el decreto.
    #
    # Sigue siendo adversario: si la guarda se aflojara, el 45 se iria a la Ley
    # 37/1992, que es lo que no puede pasar y lo que se comprueba.
    ("ADVERSARIO  delante hay norma: se resuelve CON ELLA, nunca con la de detras",
     "RDLeg 1/1993 art. 45 Ley 37/1992",
     [("45", "BOE-A-1993-25359#1")]),
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

    # ---- 4. D: varias normas en el mismo trozo, sin separador
    #
    # La DGT no siempre pone «;» ni salto de linea, y el trozo queda con dos
    # designaciones dentro. `_resolver_designacion` lo declina por falta de
    # unanimidad, y hace bien: el problema no es el resolvedor, es el troceo.
    ("POSITIVO D  dos normas seguidas sin separador",
     "Ley 37/1992 arts. 90, 91 Ley 58/2003, arts. 105, 106",
     [("90", LIVA), ("91", LIVA), ("105", LGT), ("106", LGT)]),
    # SE LLAMABA «la de en medio no la tenemos» Y YA LA TENEMOS. La Ley
    # 29/1987 se ingirio el 12/08/2026, asi que sus articulos 3 y 28 dejaron de
    # salir sin cuerpo. La expectativa se actualiza por eso -la norma esta
    # cargada, es evidencia independiente del sistema- y no porque el buscador
    # devolviera otra cosa. Lo que el caso sigue probando es lo mismo: tres
    # designaciones seguidas en un trozo, cada una con sus articulos.
    ("POSITIVO D  tres normas seguidas, cada una con los suyos",
     "Ley 19/1991 arts. 1, 3 y 7. Ley 29/1987 art. 3 y 28. "
     "Ley 35/2006 arts 1, 6, 8, 11 y 33",
     [("1", IP), ("3", IP), ("7", IP), ("3", ISD), ("28", ISD),
      ("1", LIRPF), ("6", LIRPF), ("8", LIRPF), ("11", LIRPF),
      ("33", LIRPF)]),

    # EL ADVERSARIO DE D, que es el que se cumplio de verdad: la primera
    # version del corte partia «Articulo 93 Ley 58/2003» en dos, dejaba el 93
    # huerfano y la Ley 58/2003 sin articulos, y se llevo por delante OCHO
    # consultas que resolvian bien. Las mismas que arreglaba mirar detras.
    ("ADVERSARIO D  no se parte una designacion de sus propios articulos",
     "Artículo 93 Ley 58/2003",
     [("93", LGT)]),
    # Copiado tal cual de la V0856-25, saltos de linea incluidos.
    ("ADVERSARIO D  ni cuando detras viene otra norma con los suyos",
     "Artículo 3,9 y 23 Real Decreto 1065/2007.\n\n"
     " artículos 5, 7 y 118 Ley 27/2014 del Impuesto sobre Sociedades",
     [("3", RGAT), ("9", RGAT), ("23", RGAT),
      ("5", LIS), ("7", LIS), ("118", LIS)]),
    ("ADVERSARIO D  una norma nombrada sin articulos no abre trozo",
     "Ley 37/1992 arts. 4, 5 Ley 38/1992",
     [("4", LIVA), ("5", LIVA)]),
    # De la V2484-24, tal cual. Sin exigir marca de articulo delante, el corte
    # entra antes de «RD 1624/1992», deja la primera mitad sin articulos y la
    # segunda con una abreviatura que no resuelve: el 62 se pierde.
    ("ADVERSARIO D  sin marca delante no hay nada que separar",
     "Real Decreto 1007/2023, de 5 de diciembre, RIVA RD 1624/1992 art. 62-6",
     [("62", RIVA1)]),
    # AÑADIDO EL 14/08/2026 PORQUE EL CONTROL SE HABIA QUEDADO SIN CASO. Al
    # abrir la abreviatura `RD`, el de arriba dejo de ver la mutacion (h): la
    # mutacion sigue partiendo mal, pero el trozo de detras ahora resuelve por
    # expansion al MISMO cuerpo, asi que el resultado no cambia y el caso no se
    # entera. Una mutacion que ya no se ve es un control perdido.
    #
    # Este campo es REAL -la V2689-23, copiado tal cual, faltas incluidas- y se
    # busco barriendo la despensa: de 1.263 campos distintos, solo DOS siguen
    # delatando esa mutacion. Sin la guarda, el articulo 148 se cuelga de la
    # Ley 37/1992, que es la norma de DETRAS.
    #
    # Que el 148 salga sin resolver no es un acierto: el campo esta mal escrito
    # -el punto y coma se come el 32 y el 33- y es una de las causas conocidas.
    # Lo que fija el caso es que ante eso NO se adivina.
    ("ADVERSARIO D  con dos normas y una marca, no se cuelga de la de detras",
     "Arts. 31; 32 y 33 Real Decreto 1065/2007 Ley 37/1992 art. 148 y siguentes",
     [("31", ""), ("148", "")]),

    # ---- 5. EL GUION, QUE YA SIGNIFICA TRES COSAS
    #
    # En este proyecto el guion se lee de tres maneras, y dos veces se toco a
    # la ligera y hubo que revertir. Los tres casos van juntos a proposito: si
    # alguien afloja el ancla, uno de los tres cae.
    #
    #     80-cuatro    apartado del articulo        (SIN espacios)
    #     641-14       articulo entero, Codi catalan (SIN espacios)
    #     - 17 - 76    separador de lista            (CON espacios)
    ("POSITIVO D2  la lista tras el nombre, sin marca de articulo",
     "Ley 27/2014 Impuesto sobre Sociedades - 17 - 76 - 87",
     [("17", LIS), ("76", LIS), ("87", LIS)]),
    ("POSITIVO D2  y con dos normas seguidas, cada una con su lista",
     "Ley 27/2014 Impuesto sobre Sociedades - 10 "
     "Ley 37/1992 Impuesto sobre el Valor Añadido IVA - 11",
     [("10", LIS), ("11", LIVA)]),
    ("ADVERSARIO D2  el guion SIN espacios es apartado, no separador",
     "Ley 37/1992 arts. 75, 78, 80-cuatro, 89",
     [("75", LIVA), ("78", LIVA), ("80", LIVA), ("89", LIVA)]),
    ("ADVERSARIO D2  «10-3» es el apartado 3 del articulo 10",
     "Ley 58/2003 art. 10-3",
     [("10", LGT)]),
    ("ADVERSARIO D2  y en el Codi catalan el guion va DENTRO del numero",
     "Codi tributari de Catalunya art. 641-14",
     [("641", "")]),
    # Y EL APARTADO TAMPOCO SE CUELA POR LA FORMA NUEVA: «- 76.2» es el
    # articulo 76. Medido: los 29 pares con apartado no existen en el indice y
    # el articulo base si, o sea que guardarlos enteros seria bajar consultas
    # que no se pueden encontrar.
    ("ADVERSARIO D2  el apartado detras del punto no es el articulo",
     "Ley 27/2014 Impuesto sobre Sociedades - 76.2 - 81 - 89.2",
     [("76", LIS), ("81", LIS), ("89", LIS)]),

    # ---- 6. la forma de toda la vida, que no puede haberse movido
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
      "PAREJA  una norma que no tenemos y otra que si, en el mismo campo",
      "ADVERSARIO D  no se parte una designacion de sus propios articulos",
      "ADVERSARIO D  ni cuando detras viene otra norma con los suyos"]),

    ("(b) la guarda se afloja a «ninguna norma que yo reconozca»",
     "            if not designacion.strip():",
     "            if not _RE_NORMA_EXPLICITA.search(designacion):",
     ["ADVERSARIO  delante hay norma: se resuelve CON ELLA, nunca con la "
      "de detras"]),

    ("(c) se deja de exigir que la norma vaya PEGADA a los numeros",
     "                primera = _RE_NORMA_EXPLICITA.match(detras)",
     "                primera = _RE_NORMA_EXPLICITA.search(detras)",
     ["ADVERSARIO  la norma de detras no esta pegada a los numeros"]),

    ("(d) no se corta la designacion donde empieza otra norma",
     "                    otra = _RE_NORMA_EXPLICITA.search(detras, primera.end())",
     "                    otra = None",
     ["ADVERSARIO  detras hay dos normas: se corta en la primera"]),

    ("(f) el troceo por designaciones no parte nada",
     "        cortes.append(m.start())",
     "        pass",
     ["POSITIVO D  dos normas seguidas sin separador",
      "POSITIVO D  tres normas seguidas, cada una con los suyos"]),

    ("(g) se parte sin exigir que el trozo traiga su designacion propia",
     "        propia = _RE_NORMA_EXPLICITA.search(trozo, desde, marca.start())\n"
     "        if not propia:\n            continue",
     "        pass",
     ["ADVERSARIO D  no se parte una designacion de sus propios articulos",
      "ADVERSARIO D  ni cuando detras viene otra norma con los suyos",
      "POSITIVO  la norma detras, con «de la»",
      "POSITIVO  la norma detras, sin conector",
      "POSITIVO  «del Real Decreto», que se cortaba a si mismo",
      "POSITIVO  articulo con sufijo",
      "POSITIVO  el mismo texto, pero sin nada delante: ahi si se mira",
      "ADVERSARIO  la norma de detras no esta pegada a los numeros",
      "ADVERSARIO  detras hay dos normas: se corta en la primera",
      "PAREJA  una norma que no tenemos y otra que si, en el mismo campo"]),

    ("(h) se parte sin exigir marca de articulo delante",
     "        marca = _RE_MARCA_ART.search(trozo, desde, m.start())\n"
     "        if not marca:\n            continue",
     "        marca = _RE_MARCA_ART.search(trozo, desde, m.start()) or m",
     ["ADVERSARIO D  con dos normas y una marca, no se cuelga de la de "
      "detras"]),

    ("(e) el corte busca la otra norma desde el indice 1, dentro de si misma",
     "                    otra = _RE_NORMA_EXPLICITA.search(detras, primera.end())",
     "                    otra = _RE_NORMA_EXPLICITA.search(detras, 1)",
     ["POSITIVO  «del Real Decreto», que se cortaba a si mismo",
      "POSITIVO  articulo con sufijo",
      "ADVERSARIO D  ni cuando detras viene otra norma con los suyos"]),
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
