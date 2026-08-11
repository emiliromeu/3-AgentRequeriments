#!/usr/bin/env python3
"""QUE LE HACE AL SISTEMA AÑADIR NORMAS AL CORPUS. Cero red, cero API.

    python3 medir_corpus.py                  el corpus tal como esta
    python3 medir_corpus.py --atribuir       ademas, norma por norma

Cada vez que entra una norma pasan tres cosas, y solo la primera es la que se
busca: se puede citar mas ley, cambia el ORDEN de la busqueda para preguntas que
no tienen nada que ver, y aparecen designaciones nuevas que el resolutor de
remisiones no habia visto nunca. Las dos ultimas son las que rompen cosas.

QUE MIDE, y por que estas tres:

  · LA RECUPERACION, con las preguntas del banco. Es el efecto de segundo orden
    -el reordenamiento estadistico- y es el que no se ve venir.
  · LAS REMISIONES DECLINADAS. OJO CON EL NOMBRE, que casi me cuesta un
    numero falso en un informe: `stats.no_encontradas` NO son remisiones mal
    resueltas. Son remisiones que el resolutor IDENTIFICA y se NIEGA a
    resolver, que es «ante la duda, nada» funcionando.

    Las 85 que habia antes de esta tanda son casi todas de la misma familia y
    estan bien declinadas: la ley dice «articulo 9 del Real Decreto
    1624/1992», pero el articulado de ESE decreto son 8 articulos -el resto
    esta en el Reglamento que aprueba-, asi que el articulo 9 de esa
    designacion no existe. Resolverlo «por aproximacion» seria justo el fallo
    que no puede pasar.

    UNA REMISION MAL RESUELTA NO SE PUEDE CONTAR DESDE AQUI: por definicion
    parece una buena. Eso lo mide la bateria de la fase 3 con casos
    adversarios, y ahi es donde vale el «cero mal resueltas».
  · LA ATRIBUCION POR NORMA. Si algo baja, hace falta saber CUAL de las normas
    nuevas lo causa, para poder retirar una sin retirarlas todas. Se mide
    montando un indice con las de antes MAS UNA, una por una.

NADA DE RESPALDOS SILENCIOSOS. Si una consulta falla, revienta o devuelve cero;
no devuelve algo plausible. Un respaldo silencioso ya nos convirtio una vez un
error de comparacion en un numero creible.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from agente_fiscal import referencias as R  # noqa: E402
from agente_fiscal import texto as T  # noqa: E402
from agente_fiscal.indice import Indice  # noqa: E402

CORPUS = RAIZ / "datos" / "corpus"
CASOS = RAIZ / "casos" / "banco_recuperacion.txt"
TOPE = 6

# Las que ya estaban antes de esta tanda. Se listan a mano A PROPOSITO: es la
# referencia contra la que se compara, y tiene que ser un dato fijo, no «lo que
# haya en el directorio», que cambia justo cuando se ingiere.
ANTES = [
    "BOE-A-1992-28740",   # Ley del IVA
    "BOE-A-1992-28925",   # Reglamento del IVA
    "BOE-A-2003-23186",   # LGT
    "BOE-A-2006-20764",   # Ley del IRPF
    "BOE-A-2007-6820",    # Reglamento del IRPF
    "BOE-A-2014-12328",   # Ley del IS
    "BOE-A-2015-7771",    # Reglamento del IS
]


def ruta(nid: str) -> Path:
    return CORPUS / f"{nid}.jsonl"


def indice_de(ids: list) -> Indice:
    rutas = [ruta(n) for n in ids]
    faltan = [r.name for r in rutas if not r.is_file()]
    if faltan:
        raise SystemExit(f"[FALLO] no estan ingeridas: {', '.join(faltan)}")
    return Indice(rutas)


def preguntas() -> list:
    """Las preguntas del banco, del MISMO fichero que usa `banco.py`.

    No se copian aqui: si se copiaran, el dia que se anada un caso al banco
    esta medida seguiria midiendo los de antes y nadie se enteraria.
    """
    if not CASOS.is_file():
        raise SystemExit(f"[FALLO] no existe {CASOS}: sin preguntas no hay medida")
    fuera = []
    for linea_texto in CASOS.read_text(encoding="utf-8").splitlines():
        linea_texto = linea_texto.strip()
        if not linea_texto or linea_texto.startswith("#") or "|" not in linea_texto:
            continue
        partes = [x.strip() for x in linea_texto.split("|")]
        fuera.append({"pregunta": partes[0],
                      "norma": partes[1] if len(partes) > 1 else "",
                      "esperado": partes[2] if len(partes) > 2 else ""})
    if not fuera:
        raise SystemExit(f"[FALLO] {CASOS} no tiene ninguna pregunta dentro")
    return fuera


def recupera(ix: Indice, pregunta: str, norma: str = "") -> list:
    """Los TOPE preceptos que salen primero. Referencias, en orden."""
    # POR LA MISMA PUERTA QUE EL AGENTE: ver `fase4.recuperar`. Con `ix.buscar`
    # a secas, esta medida comparaba dos corpus con una recuperacion que el
    # sistema ya no usa.
    import fase4
    cuerpo, _m = ix.normas.resolver(norma) if norma else (None, "")
    imp = ix.normas.impuesto_de_cuerpo(cuerpo) if cuerpo else ""
    res, _h, _r = fase4.recuperar(ix, R.GrafoRemisiones(ix.docs), pregunta,
                                  imp, tope=TOPE)
    return [r.doc.referencia for r in res]


def remisiones(ix: Indice) -> dict:
    grafo = R.GrafoRemisiones(ix.docs)
    s = grafo.stats
    return {
        "total": s.total,
        "resueltas": s.resueltas,
        "externas": s.pendientes_externas,
        "ambiguas": s.pendientes_ambiguas,
        "declinadas": s.no_encontradas,
        "sin_resolver": [f"{r.etiqueta_destino} (en {r.origen}): {r.motivo}"
                         for r in s.sin_resolver],
        "grafo": grafo,
    }


def cruzadas(ix: Indice, grafo, de: str, a: str) -> int:
    """Remisiones RESUELTAS que salen de la norma `de` y caen en la norma `a`."""
    n = 0
    for origen, lista in grafo.adelante.items():
        doc = ix.por_clave.get(origen)
        if doc is None or doc.registro.get("norma_id") != de:
            continue
        for rem in lista:
            destino = getattr(rem, "destino", None)
            if not destino:
                continue
            d = ix.por_clave.get(destino)
            if d is not None and d.registro.get("norma_id") == a:
                n += 1
    return n


def foto(ids: list, etiqueta: str) -> dict:
    ix = indice_de(ids)
    rem = remisiones(ix)
    return {
        "etiqueta": etiqueta,
        "normas": len(ids),
        "preceptos": len(ix.docs),
        "cuerpos": len(ix.normas.cuerpos),
        "impuestos": sorted(ix.normas.impuestos()),
        "recuperacion": {p["pregunta"]: recupera(ix, p["pregunta"],
                                                p.get("norma", ""))
                         for p in preguntas()},
        "remisiones": {k: v for k, v in rem.items() if k != "grafo"},
        "_ix": ix,
        "_grafo": rem["grafo"],
    }


def comparar(a: dict, b: dict) -> dict:
    """Que cambia entre dos fotos. Solo hechos, sin juicio."""
    movidas = []
    for pregunta, antes in a["recuperacion"].items():
        ahora = b["recuperacion"].get(pregunta, [])
        if antes != ahora:
            movidas.append({"pregunta": pregunta, "antes": antes, "ahora": ahora,
                            "primero_cambia": (antes[:1] != ahora[:1]),
                            "perdidos": [x for x in antes if x not in ahora]})
    return {
        "movidas": movidas,
        "primero_cambia": sum(1 for m in movidas if m["primero_cambia"]),
        "con_perdida": sum(1 for m in movidas if m["perdidos"]),
        "declinadas": (b["remisiones"]["declinadas"]
                       - a["remisiones"]["declinadas"]),
    }


def linea(f: dict) -> None:
    r = f["remisiones"]
    print(f"  {f['etiqueta']:<42} {f['preceptos']:>5} preceptos · "
          f"{f['cuerpos']:>2} cuerpos · {r['declinadas']} declinadas")


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--atribuir", action="store_true",
                    help="mide tambien norma a norma, para poder retirar una")
    ap.add_argument("--cruzadas", nargs=2, metavar=("DE", "A"), default=None,
                    help="remisiones resueltas de una norma a otra")
    args = ap.parse_args(argv)

    todas = sorted(n.name[:-6] for n in CORPUS.glob("*.jsonl")
                   if not n.name.endswith(".descartados.jsonl"))
    nuevas = [n for n in todas if n not in ANTES]

    print("=" * 74)
    print("QUE LE HACE AL SISTEMA ESTA TANDA DE NORMAS")
    print("=" * 74)
    print(f"antes  : {len(ANTES)} normas")
    print(f"nuevas : {len(nuevas)} -> {', '.join(nuevas) if nuevas else '(ninguna)'}")

    print("\nFOTOS")
    antes = foto(ANTES, "antes (las 7 de siempre)")
    linea(antes)
    if not nuevas:
        print("\nNo hay normas nuevas: no hay nada que comparar.")
        return 0
    despues = foto(todas, f"despues (con las {len(nuevas)} nuevas)")
    linea(despues)

    d = comparar(antes, despues)
    print("\nRECUPERACION (las preguntas del banco, primeros "
          f"{TOPE} preceptos)")
    print(f"  preguntas medidas          : {len(antes['recuperacion'])}")
    print(f"  con el orden cambiado      : {len(d['movidas'])}")
    print(f"  con OTRO primer resultado  : {d['primero_cambia']}")
    print(f"  que PIERDEN algun precepto : {d['con_perdida']}")
    for m in d["movidas"]:
        if m["perdidos"] or m["primero_cambia"]:
            print(f"    · «{m['pregunta'][:52]}»")
            print(f"        antes: {', '.join(m['antes'][:4])}")
            print(f"        ahora: {', '.join(m['ahora'][:4])}")
            if m["perdidos"]:
                print(f"        SE PIERDE: {', '.join(m['perdidos'])}")

    print("\nREMISIONES")
    for f in (antes, despues):
        r = f["remisiones"]
        print(f"  {f['etiqueta']:<30} total {r['total']:>5} · "
              f"resueltas {r['resueltas']:>5} · externas {r['externas']:>4} · "
              f"ambiguas {r['ambiguas']:>3} · DECLINADAS {r['declinadas']}")
    if despues["remisiones"]["sin_resolver"]:
        print("\n  LAS DECLINADAS, agrupadas:")
        for s in despues["remisiones"]["sin_resolver"]:
            print(f"    - {s[:100]}")

    if args.cruzadas:
        de, a = args.cruzadas
        n1 = cruzadas(despues["_ix"], despues["_grafo"], de, a)
        n2 = cruzadas(despues["_ix"], despues["_grafo"], a, de)
        print(f"\nREMISIONES CRUZADAS")
        print(f"  {de} -> {a}: {n1}")
        print(f"  {a} -> {de}: {n2}")

    if args.atribuir:
        print("\nATRIBUCION: las 7 de siempre MAS UNA, una por una")
        print("  Asi se sabe cual retirar sin retirarlas todas.\n")
        print(f"  {'norma anadida':<22} {'preceptos':>9} {'mueven':>7} "
              f"{'1o cambia':>10} {'pierden':>8} {'declin.':>9}")
        for n in nuevas:
            f = foto(ANTES + [n], n)
            dd = comparar(antes, f)
            print(f"  {n:<22} {f['preceptos'] - antes['preceptos']:>+9} "
                  f"{len(dd['movidas']):>7} {dd['primero_cambia']:>10} "
                  f"{dd['con_perdida']:>8} "
                  f"{f['remisiones']['declinadas']:>9}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
