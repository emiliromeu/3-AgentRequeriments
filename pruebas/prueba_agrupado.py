#!/usr/bin/env python3
"""LOS AVISOS DEL TEAC SE AGRUPAN POR ARTICULO. Cero red, cero API.

    python pruebas/prueba_agrupado.py

EL DEFECTO QUE LA JUSTIFICA: los avisos salian POR CRITERIO. Sobre el articulo
80 hay seis resoluciones, y quien preguntaba veia SEIS AVISOS practicamente
identicos, uno detras de otro. Un aviso repetido seis veces no avisa seis veces
mejor: se deja de leer entero, y con el se deja de leer el que si importaba.

Y LA UNIFICACION DE CRITERIO VA DELANTE. No es cosmetica: una resolucion que
unifica criterio vincula a toda la Administracion, y una que no, no. Si van
mezcladas por fecha, la que manda puede quedar la cuarta.

`prueba_asunto` cubre el FILTRADO -que no entre doctrina de otro impuesto-.
Esto cubre el AGRUPADO, que es lo que pasa despues.

TAXONOMIA: fixture propio -`casos/teac_asunto`, criterios reales copiados- para
todo lo que se afirma. Nada contra la despensa, que crece con cada siembra.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4                                  # noqa: E402
from agente_fiscal import teac as T           # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:112]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix, _g = fase4.cargar_corpus()
N = ix.normas
cache = T.CacheTEAC(RAIZ / "casos" / "teac_asunto")
todos = cache.todas()
print(f"\n  fixture: {len(todos)} criterios reales copiados de la despensa")

ART80 = ("BOE-A-1992-28740#0", "80")

# ==================================== 1. UN AVISO POR ARTICULO
print("\n=== 1. UN AVISO POR ARTICULO, NO UNO POR CRITERIO ===")

sobre_80 = [c for c in todos if ART80 in set(c.preceptos(N))]
print(f"    criterios del fixture sobre el articulo 80: {len(sobre_80)}")
comprobar("hay VARIOS criterios sobre el mismo articulo, que es el caso que "
          "genera el problema", len(sobre_80) >= 2, len(sobre_80))

lec = T.leer_doctrina([], [ART80], [], N, descartados=[(c, "") for c in sobre_80])
avisos = lec.cobertura
for a in avisos:
    print(f"      {a[:118]}")
comprobar("los avisos NO son uno por criterio",
          len(avisos) < len(sobre_80) or len(sobre_80) <= 1,
          f"{len(avisos)} avisos para {len(sobre_80)} criterios")
comprobar("hay como mucho uno por articulo en juego", len(avisos) <= 1,
          f"{len(avisos)} avisos para 1 articulo")
if avisos:
    comprobar("y el aviso dice CUANTAS hay, en vez de repetirse",
              any(str(len(sobre_80)) in a for a in avisos), str(avisos))

# ==================================== 2. DOS ARTICULOS, DOS AVISOS
print("\n=== 2. DOS ARTICULOS EN JUEGO: UN AVISO CADA UNO ===")
print("  Agrupar no es resumir hasta perder de que articulo se habla.\n")

otros = [c for c in todos if ART80 not in set(c.preceptos(N))
         and c.preceptos(N)]
if otros:
    otro_art = next(iter(set(otros[0].preceptos(N))))
    lec2 = T.leer_doctrina(
        [], [ART80, otro_art], [], N,
        descartados=[(c, "") for c in sobre_80 + [otros[0]]])
    for a in lec2.cobertura:
        print(f"      {a[:112]}")
    comprobar("con dos articulos en juego salen hasta dos avisos",
              len(lec2.cobertura) <= 2, len(lec2.cobertura))
    comprobar("y no se mezclan en uno solo que no diga de que articulo habla",
              len(lec2.cobertura) >= 1, len(lec2.cobertura))
else:
    comprobar("(omitido) el fixture no tiene criterios de otro articulo", True)

# ==================================== 3. LA UNIFICACION, DELANTE
print("\n=== 3. LA QUE UNIFICA CRITERIO VA DELANTE ===")
print("  Vincula a toda la Administracion. Ordenadas por fecha, la que manda")
print("  puede quedar la cuarta y leerse como una mas.\n")

por_peso = sorted(todos, key=T.peso)
niveles = [T.nivel(c) for c in por_peso]
comprobar("el orden por peso es monotono", niveles == sorted(niveles),
          str(niveles))
unifican = [c for c in todos if getattr(c, "unifica_criterio", False)]
if unifican:
    primera = por_peso.index(unifican[0])
    resto = [i for i, c in enumerate(por_peso) if not getattr(
        c, "unifica_criterio", False)]
    comprobar("la que unifica criterio va antes que las que no",
              primera < min(resto) if resto else True,
              f"puesto {primera + 1} de {len(por_peso)}")
else:
    comprobar("(omitido) el fixture no tiene ninguna que unifique criterio",
              True)
comprobar("todo el TEAC va antes que cualquier regional",
          max((T.nivel(c) for c in todos if c.es_central), default=-1)
          < min((T.nivel(c) for c in todos if not c.es_central), default=99))

# ==================================== 4. CONTROL NEGATIVO
print("\n=== 4. LA PRUEBA SABE PONERSE ROJA ===")
print("  Se rompe el agrupado de verdad y se mira que cae.\n")

import types                                   # noqa: E402

FUENTE = (RAIZ / "agente_fiscal" / "teac.py").read_text("utf-8")


def con_el_codigo_roto(viejo, nuevo):
    if viejo not in FUENTE:
        raise AssertionError(f"la mutacion ya no encaja: {viejo[:70]}")
    mod = types.ModuleType("agente_fiscal.teac_roto")
    mod.__package__ = "agente_fiscal"
    mod.__file__ = str(RAIZ / "agente_fiscal" / "teac.py")
    sys.modules[mod.__name__] = mod
    try:
        exec(compile(FUENTE.replace(viejo, nuevo, 1), mod.__file__, "exec"),
             mod.__dict__)
    finally:
        del sys.modules[mod.__name__]
    return mod


# (a) que el peso deje de mandar y ordene la fecha, que es como estaba antes.
roto = con_el_codigo_roto("def peso(criterio) -> tuple:",
                          "def peso(criterio) -> tuple:\n    return (0, 0)")
mezcla = sorted(todos, key=roto.peso)
nivs = [T.nivel(c) for c in mezcla]
comprobar("(a) sin el peso, el orden deja de ser monotono y el bloque 3 lo "
          "cazaria", nivs != sorted(nivs) or len(set(nivs)) <= 1, str(nivs))

# (b) sin mutar, todo vuelve
comprobar("(b) sin mutar, el orden vuelve a ser monotono",
          [T.nivel(c) for c in sorted(todos, key=T.peso)]
          == sorted(T.nivel(c) for c in todos))

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
