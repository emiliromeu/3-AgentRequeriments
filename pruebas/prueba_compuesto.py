#!/usr/bin/env python3
"""EL NUMERO COMPUESTO DEL CODI, SIN ROMPER EL APARTADO ESTATAL. Cero red, cero API.

    python pruebas/prueba_compuesto.py

LA MISMA FORMA Y DOS COSAS DISTINTAS. «641-14» es un articulo entero del Codi
tributari de Catalunya; «10-3» es el apartado 3 del articulo 10 en una norma
estatal. Por eso leer el compuesto estuvo RECHAZADO: arreglaba lo catalan y
rompia lo estatal, y se prefirio perder 52 remisiones internas del Codi antes
que atribuir un articulo a quien no le toca.

LO QUE LO DESBLOQUEA son las dos cosas que se aprendieron con la abreviatura
del Real Decreto, y hay que probar LAS DOS por separado:

  1. SE PRUEBA PRIMERO LO QUE SE LEE HOY. Si el numero plano existe, se queda
     plano. El compuesto solo alcanza a lo que hoy se pierde.
  2. Y DECIDE EL CORPUS, no el patron: «641» a secas no existe en ningun
     cuerpo y «641 14» si.

El control negativo rompe las dos mitades, porque quitar una sola deja la otra
tapando el defecto -y entonces la suite pasaria verde con media regla-.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4                                    # noqa: E402
from agente_fiscal import referencias as R      # noqa: E402
from agente_fiscal.indice import Indice         # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:110]}" if not ok else ""))
    if not ok:
        fallos.append(que)


# ==================================== 1. EL CORPUS DE VERDAD
print("\n=== 1. LAS REMISIONES INTERNAS DEL CODI SE RESUELVEN ===")

ix, g = fase4.cargar_corpus()
catalanas = [r for r in g.stats.sin_resolver
             if r.origen.startswith("BOE-A-2024-6951")]
print(f"    remisiones resueltas en todo el corpus : {g.stats.resueltas}")
print(f"    del Codi, sin resolver                 : {len(catalanas)}")
comprobar("quedan 5 o menos sin resolver en el Codi (eran 53)",
          len(catalanas) <= 5, len(catalanas))
comprobar("y ninguna remision resuelta apunta a un precepto que no existe",
          not [r for rems in g.adelante.values() for r in rems
               if r.estado == R.RESUELTA and r.destino
               and r.destino not in ix.por_clave])


# ==================================== 2. EL POSITIVO Y EL ADVERSARIO, JUNTOS
print("\n=== 2. «641-14» ES ARTICULO Y «10-3» ES APARTADO, EN EL MISMO SITIO ===")
print("  Los dos en el mismo corpus de mentira: si la regla se pasara de")
print("  lista, el segundo se rompe en la misma pasada que arregla el primero.\n")


def _p(norma, cu, num, ref, texto, titulo, pos):
    return {"norma_id": norma, "cuerpo_indice": cu,
            "cuerpo_clave": f"{norma}#{cu}", "norma_titulo": titulo,
            "tipo": "articulo", "tipo_boe": "precepto", "referencia": ref,
            "referencia_corta": ref, "clave": f"{norma}#{cu}#{ref.lower()}",
            "clave_local": ref.lower(), "numero": num,
            "numero_norm": num.replace("-", " "), "contexto": [], "rubrica": "",
            "es_rango": False, "suprimido": False, "caducado_desde": "",
            "incidencias": [], "avisos": [], "vigente_desde": "1999-01-01",
            "fechas_vigencia": ["1999-01-01"], "n_versiones": 1,
            "versiones": [], "notas_boe": [], "texto_vigente": texto,
            "posicion": pos}


def corpus_de_mentira():
    d = Path(tempfile.mkdtemp())
    codi = [
        _p("BOE-A-9999-1", 1, "641-13", "Articulo 641-13",
           "Articulo 641-13. Uno.\nTexto llano.", "Codigo tributario", 1),
        _p("BOE-A-9999-1", 1, "641-14", "Articulo 641-14",
           "Articulo 641-14. Dos.\nSe aplica lo previsto en el articulo 641-13.",
           "Codigo tributario", 2)]
    ley = [
        _p("BOE-A-9999-2", 0, "10", "Articulo 10",
           "Articulo 10. Base.\nTexto llano.", "Ley de mentira 1/1999", 1),
        _p("BOE-A-9999-2", 0, "11", "Articulo 11",
           "Articulo 11. Tipo.\nSe estara a lo dispuesto en el articulo 10-3 "
           "de esta Ley.", "Ley de mentira 1/1999", 2)]
    for nombre, filas in (("BOE-A-9999-1", codi), ("BOE-A-9999-2", ley)):
        (d / f"{nombre}.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in filas),
            encoding="utf-8")
    return d


def resolver_con(modulo):
    """{texto de la remision: (estado, numero del destino)} en el corpus falso."""
    d = corpus_de_mentira()
    try:
        gg = modulo.GrafoRemisiones(Indice(d).docs)
        return {r.texto.strip(): (r.estado,
                                  r.destino.split("#")[-1] if r.destino else "")
                for rems in gg.adelante.values() for r in rems}
    finally:
        shutil.rmtree(d, ignore_errors=True)


hoy = resolver_con(R)
for t, v in sorted(hoy.items()):
    print(f"    «{t:22s}» {v[0]:14s} -> {v[1] or '-'}")

comprobar("EL POSITIVO: «641-13» se resuelve al articulo 641-13",
          hoy.get("articulo 641-13", ("", ""))[1] == "articulo 641-13", hoy)
comprobar("EL ADVERSARIO: «10-3» sigue siendo el apartado del articulo 10",
          hoy.get("articulo 10", ("", ""))[1] == "articulo 10", hoy)
comprobar("  y NO aparece ningun articulo «10-3»",
          not any("10-3" in v[1] for v in hoy.values()), hoy)


# ==================================== 3. CONTROL NEGATIVO, LAS DOS MITADES
print("\n=== 3. LA PRUEBA SABE PONERSE ROJA, POR LOS DOS LADOS ===")
print("  Quitar una sola mitad deja la otra tapando el defecto.\n")

import types                                     # noqa: E402

FUENTE = (RAIZ / "agente_fiscal" / "referencias.py").read_text("utf-8")


def con_el_codigo_roto(viejo, nuevo):
    if viejo not in FUENTE:
        raise AssertionError(f"la mutacion ya no encaja: {viejo[:70]}")
    mod = types.ModuleType("agente_fiscal.referencias_roto")
    mod.__package__ = "agente_fiscal"
    mod.__file__ = str(RAIZ / "agente_fiscal" / "referencias.py")
    sys.modules[mod.__name__] = mod
    try:
        exec(compile(FUENTE.replace(viejo, nuevo, 1), mod.__file__, "exec"),
             mod.__dict__)
    finally:
        del sys.modules[mod.__name__]
    return mod


# (a) SIN LA REGLA: vuelven a perderse las catalanas.
sin_regla = con_el_codigo_roto(
    "            mc = _RE_COMPUESTO.match(texto, cursor)",
    "            mc = None")
r_a = resolver_con(sin_regla)
comprobar("(a) sin la regla, «641-13» vuelve a no encontrarse",
          r_a.get("articulo 641", ("", ""))[0] == R.NO_ENCONTRADA, r_a)
cat_a = [x for x in sin_regla.GrafoRemisiones(ix.docs).stats.sin_resolver
         if x.origen.startswith("BOE-A-2024-6951")]
print(f"       y en el corpus de verdad: {len(cat_a)} catalanas sin resolver")
comprobar("  con las 48 del Codi perdidas otra vez", len(cat_a) >= 50,
          len(cat_a))

# (b) SIN LA PRIORIDAD DEL PLANO: «10-3» pasa a leerse como articulo.
sin_prioridad = con_el_codigo_roto(
    "                if hay_compuesto and not hay_plano:",
    "                if hay_compuesto or True:")
r_b = resolver_con(sin_prioridad)
comprobar("(b) sin la prioridad del plano, «10-3» deja de ser el apartado",
          r_b.get("articulo 10", ("", ""))[1] != "articulo 10", r_b)
comprobar("  y el 641-13 sigue bien, o sea que la mitad rota es la otra",
          r_b.get("articulo 641-13", ("", ""))[1] == "articulo 641-13", r_b)

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
