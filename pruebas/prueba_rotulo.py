#!/usr/bin/env python3
"""EL ROTULO DEL ARTICULO SE ABREVIA, Y LA PUERTA SIGUE CERRANDO. Cero red, cero API.

    python pruebas/prueba_rotulo.py

EL CASO QUE LA JUSTIFICA. El Reglamento del ISD (RD 1629/1991) titula «Art. 1»
en vez de «Articulo 1». Con el rotulo escrito entero, 105 de sus 180 bloques se
quedaban SIN RECONOCER y la ingesta lo rechazaba. LA PUERTA HIZO BIEN SU
TRABAJO: una norma medio leida da respuestas peores sin dar error.

Y ES LA CAUSA DEL CASO «ISD 31» del banco: el plazo de seis meses para presentar
una herencia vive en ese reglamento, no en la Ley 29/1987 -que remite: «en los
plazos que reglamentariamente se fijen»-.

SE ARREGLA COMO PROPIEDAD DEL ROTULO, NO COMO UN CASO PARA ESTA NORMA. Un `if`
por norma seria la enesima lista escrita a mano y la siguiente con «Art 1»
volveria a rebotar. Esta suite prueba las dos mitades de eso:

  1. que la abreviatura se reconozca -con punto y sin el, singular y plural-;
  2. QUE NO SE TRAGUE CUALQUIER COSA que empiece por «art». Aflojar un patron
     es facil; aflojarlo de menos es lo que cuesta, y sin esta mitad nadie se
     enteraria de que «Artesania 3» pasa a ser un articulo.
  3. y que la PUERTA de bloques sin reconocer siga parando lo que debe, medido
     fabricando una norma rota, no leyendo el codigo.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase1                                    # noqa: E402
from agente_fiscal import bloques as B          # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:104]}" if not ok else ""))
    if not ok:
        fallos.append(que)


# ==================================== 1. LA ABREVIATURA SE RECONOCE
print("\n=== 1. «Art», «Art.», «Articulo»: todas son el mismo rotulo ===")

SI = [
    ("Art 1", "1"),                    # el del Reglamento del ISD, sin punto
    ("Art. 1", "1"),
    ("Articulo 1", "1"),
    ("Artículo 1.", "1"),
    ("Art. 8 bis", "8 bis"),
    ("Art 163 bis", "163 bis"),
    ("Artículo 641-14", "641-14"),     # el Codi tributari, que ya funcionaba
]
for titulo, numero in SI:
    c = B.clasificar(titulo, "x", "precepto")
    comprobar(f"«{titulo}» es un articulo, numero {numero}",
              c.tipo == B.ARTICULO and c.numero == numero,
              f"{c.tipo} / {c.numero}")

c = B.clasificar("Art. unico", "x", "precepto")
comprobar("«Art. unico» tambien: es el articulo aprobatorio de un RD",
          c.tipo == B.ARTICULO, c.tipo)
c = B.clasificar("Arts. 1 a 5", "x", "precepto")
comprobar("«Arts. 1 a 5» es el rango, en plural y abreviado",
          c.tipo == B.ARTICULO and c.es_rango, f"{c.tipo} rango={c.es_rango}")

# ==================================== 2. Y NO SE TRAGA CUALQUIER COSA
print("\n=== 2. LO QUE EMPIEZA POR «art» Y NO ES UN ARTICULO ===")
print("  Aflojar un patron es facil; aflojarlo de menos es lo que cuesta.\n")

NO = ["Artes graficas 1", "Artesania 3", "Articulacion 2", "Art",
      "Artefactos 12", "Articulos varios"]
for titulo in NO:
    c = B.clasificar(titulo, "x", "precepto")
    comprobar(f"«{titulo}» NO es un articulo", c.tipo != B.ARTICULO, c.tipo)

for titulo, esperado in (("Titulo I", B.ENCABEZADO),
                         ("Capitulo II", B.ENCABEZADO),
                         ("Disposicion adicional primera",
                          B.DISP_ADICIONAL)):
    c = B.clasificar(titulo, "x", "precepto")
    comprobar(f"«{titulo}» sigue siendo {esperado}", c.tipo == esperado, c.tipo)

# ==================================== 3. LA PUERTA SIGUE CERRANDO
print("\n=== 3. LA PUERTA DE BLOQUES SIN RECONOCER ===")
print("  Se fabrica una norma rota y se mide con la MISMA regla que usa la")
print("  ingesta, no leyendo el codigo.\n")


def veredicto(titulos: list) -> tuple:
    """(¿la rechaza?, proporcion) con la regla exacta de `fase1`."""
    citables, sin_reconocer = [], []
    for t in titulos:
        c = B.clasificar(t, "x", "precepto")
        (sin_reconocer if c.tipo == B.DESCONOCIDO else citables).append(t)
    total = len(citables) + len(sin_reconocer)
    prop = len(sin_reconocer) / total if total else 0.0
    rechaza = (prop > fase1.TOPE_SIN_RECONOCER
               or len(sin_reconocer) > len(citables))
    return rechaza, prop


rota = [f"Precepto numero {i}" for i in range(120)] + \
       [f"Art. {i}" for i in range(60)]
rechaza, prop = veredicto(rota)
comprobar(f"una norma con dos tercios sin reconocer se RECHAZA "
          f"({prop:.0%})", rechaza, f"prop={prop:.0%}")

sana = [f"Art. {i}" for i in range(170)] + ["Titulo I", "Capitulo II"]
rechaza_sana, prop_sana = veredicto(sana)
comprobar(f"y una sana con la abreviatura se ACEPTA ({prop_sana:.0%} sin "
          f"reconocer)", not rechaza_sana, f"prop={prop_sana:.0%}")

# La segunda regla, la de las normas pequeñas, donde el porcentaje miente.
pequena = [f"Art. {i}" for i in range(6)] + [f"Cosa rara {i}" for i in range(7)]
rechaza_peq, prop_peq = veredicto(pequena)
comprobar("en una norma pequeña, mas sin reconocer que citables tambien la "
          f"para ({prop_peq:.0%}, por debajo del tope)", rechaza_peq,
          f"prop={prop_peq:.0%}")

# EL CASO DE VERDAD: el Reglamento del ISD como estaba ANTES del arreglo.
# 105 de 180 sin reconocer. Se reproduce con el rotulo viejo para ver que la
# puerta lo paraba, que es lo que hizo.
import re                                        # noqa: E402

VIEJO = re.compile(r"^articulos?\s+(?P<num>\d+(?:-\d+)*)"
                   r"(?P<suf>(?:\s+[a-z]+){0,2})\s*\.?\s*$")
titulos_isd = [f"Art. {i}" for i in range(105)] + \
              [f"Articulo {i}" for i in range(75)]
viejos_ok = sum(1 for t in titulos_isd if VIEJO.match(B.sin_tildes(t.rstrip("."))))
nuevos_ok = sum(1 for t in titulos_isd
                if B.clasificar(t, "x", "precepto").tipo == B.ARTICULO)
print(f"\n    con el rotulo viejo se reconocian {viejos_ok} de {len(titulos_isd)}")
print(f"    con el nuevo                       {nuevos_ok} de {len(titulos_isd)}")
comprobar("antes del arreglo la puerta lo habria rechazado",
          veredicto([f"Art. {i}" for i in range(105)]
                    + [f"Articulo {i}" for i in range(75)])[0] is False
          and viejos_ok < len(titulos_isd), f"{viejos_ok}")
comprobar("y ahora se reconocen todos", nuevos_ok == len(titulos_isd),
          f"{nuevos_ok} de {len(titulos_isd)}")

# ==================================== 4. CONTROL NEGATIVO
print("\n=== 4. LA PRUEBA SABE PONERSE ROJA ===")
print("  Se rompe el rotulo de verdad y se mira que cae.\n")

import types                                     # noqa: E402

FUENTE = (RAIZ / "agente_fiscal" / "bloques.py").read_text("utf-8")


def con_el_codigo_roto(viejo, nuevo):
    if viejo not in FUENTE:
        raise AssertionError(f"la mutacion ya no encaja: {viejo[:60]}")
    mod = types.ModuleType("bloques_roto")
    mod.__package__ = "agente_fiscal"
    mod.__file__ = str(RAIZ / "agente_fiscal" / "bloques.py")
    sys.modules[mod.__name__] = mod
    try:
        exec(compile(FUENTE.replace(viejo, nuevo, 1), mod.__file__, "exec"),
             mod.__dict__)
    finally:
        del sys.modules[mod.__name__]
    return mod


# (a) que vuelva a exigir el rotulo entero: el Reglamento del ISD rebota otra vez
roto = con_el_codigo_roto('_ROTULO = r"art(?:iculo)?s?\\.?"',
                          '_ROTULO = r"articulos?"')
c = roto.clasificar("Art. 1", "x", "precepto")
comprobar("(a) con el rotulo entero, «Art. 1» deja de ser articulo y el "
          "bloque 1 lo caza", c.tipo != roto.ARTICULO, c.tipo)

# (b) que se afloje DE MAS: cualquier cosa que empiece por art
roto2 = con_el_codigo_roto('_ROTULO = r"art(?:iculo)?s?\\.?"',
                           '_ROTULO = r"art\\w*\\.?"')
c2 = roto2.clasificar("Artesania 3", "x", "precepto")
comprobar("(b) aflojando de mas, «Artesania 3» pasa a ser articulo y el "
          "bloque 2 lo caza", c2.tipo == roto2.ARTICULO, c2.tipo)

# (c) sin mutar, las dos cosas siguen bien
comprobar("(c) sin mutar: «Art. 1» si y «Artesania 3» no",
          B.clasificar("Art. 1", "x", "precepto").tipo == B.ARTICULO
          and B.clasificar("Artesania 3", "x", "precepto").tipo != B.ARTICULO)

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
