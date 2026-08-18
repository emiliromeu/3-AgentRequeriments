#!/usr/bin/env python3
"""¿AMPLIAR EL PLAN, DEJARLO A LA COLA, O LAS DOS? Cero red, cero API.

    .venv/bin/python medir_plan.py

El plan de siembra esta AGOTADO: se bajo todo lo que habia para los 630
articulos planeados y el corpus tiene 2.043. La tentacion es ampliarlo -por
remisiones entrantes, por los mas citados- y eso seria VOLVER A ELEGIR
NOSOTROS, que es justo lo que ha fallado dos veces: el plan de tres normas
cuando el corpus tenia cuatro impuestos, y la tupla que tiraba ISD e ITPAJD.

TRES NUMEROS PARA DECIDIRLO, y ninguno es una opinion:

  1. QUE PIDEN DE VERDAD. De las consultas reales de las trazas, que articulos
     acabaron delante del redactor y cuantos de esos tenian criterio. Es lo
     unico que dice si el agujero esta donde creemos.
  2. QUE HAY EN COLA HOY, y de que impuestos.
  3. CUANTO COSTARIA ampliar el plan a todo lo recuperable, en horas de
     peticiones a un servicio publico.

Solo cuenta lo que hizo una persona con el modelo real: las suites y el banco
son mios y contarlos diria que se pregunta lo que yo pruebo.
"""
import json
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

# El ritmo de la siembra, que es el que hay: no se acelera para que salga mejor.
PAUSA = 10
POR_ARTICULO = 5


def main() -> int:
    import fase4
    from agente_fiscal import dgt as D
    from agente_fiscal import cola as C

    ix, _g = fase4.cargar_corpus()
    N = ix.normas

    cobertura = {(p.cuerpo, p.numero.lower())
                 for c in D.CacheDGT().todas()
                 for p in c.preceptos(N) if p.comparable}

    print("=" * 74)
    print("1 · QUE PIDIERON LAS CONSULTAS REALES, Y CUANTO TENIA CRITERIO")
    print("=" * 74)
    # SE LEE DE `seleccion.json`, NO DE `resultado.json`. El resultado no
    # guarda los preceptos enviados en las trazas de agosto -ese campo es
    # posterior- y contarlos de ahi daba CERO articulos pedidos, que se lee
    # como «no piden nada» cuando lo que pasa es que se mira el sitio
    # equivocado. `seleccion.json` los tiene desde el principio, y ademas con
    # la CLAVE ENTERA: cuerpo y articulo, que es lo que hace falta para saber
    # si ese articulo concreto tiene criterio.
    pedidos = Counter()
    reales = 0
    for d in sorted((RAIZ / "datos" / "trazas").iterdir()):
        con = d / "consumo.json"
        sel = d / "seleccion.json"
        if not con.is_file() or not sel.is_file():
            continue
        try:
            if "claude" not in json.dumps(json.loads(
                    con.read_text(encoding="utf-8"))):
                continue
            j = json.loads(sel.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        reales += 1
        for r in (j.get("preceptos") or []):
            if r.get("decision") != "enviado":
                continue
            clave = r.get("clave") or ""
            if "#" not in clave:
                continue
            cuerpo, _, local = clave.rpartition("#")
            pedidos[(cuerpo, local.replace("articulo ", "").strip())] += 1

    print(f"  consultas reales con el modelo real : {reales}")
    print(f"  articulos distintos que pidieron    : {len(pedidos)}")
    if pedidos:
        # Se cuenta contra TODO el corpus: el numero de articulo solo no
        # identifica, asi que se mira si ese numero tiene criterio en ALGUN
        # cuerpo. Es una cota superior: si aqui ya falta, falta seguro.
        con_criterio = sum(1 for k in pedidos if k in cobertura)
        print(f"  de esos, con criterio en la despensa: {con_criterio} "
              f"({100 * con_criterio / len(pedidos):.0f}%)")
        print(f"  SIN criterio                        : "
              f"{len(pedidos) - con_criterio}")
        print()
        print("  los mas pedidos:")
        for (cu, a), v in pedidos.most_common(10):
            nombre = N.por_clave(cu)
            print(f"    art. {a:<10s} {(nombre.nombre if nombre else cu)[:26]:28s}"
                  f" pedido {v:>2}   "
                  f"{'con criterio' if (cu, a) in cobertura else 'SIN criterio'}")

    print()
    print("=" * 74)
    print("2 · QUE HAY EN COLA HOY")
    print("=" * 74)
    pend = C.pendientes(N, cobertura)
    print(f"  articulos apuntados esperando turno : {len(pend)}")
    if pend:
        por_imp = Counter(N.impuesto_de_cuerpo(e["cuerpo"]) or "GENERAL"
                          for e in pend)
        for k, v in por_imp.most_common():
            print(f"    {k:10s} {v}")
        print(f"  al ritmo de la cola (3 por apertura): "
              f"{-(-len(pend) // 3)} aperturas del agente")

    print()
    print("=" * 74)
    print("3 · CUANTO COSTARIA AMPLIAR EL PLAN A TODO EL CORPUS")
    print("=" * 74)
    # Solo articulos con numero: a PETETE se le busca por numero, y una
    # disposicion no lo tiene.
    import re
    recuperables = [d for d in ix.docs
                    if d.registro.get("tipo") == "articulo"
                    and re.match(r"^\d", str(d.registro.get("numero") or ""))]
    ya = {(d.registro["cuerpo_clave"],
           str(d.registro["numero"]).lower()) for d in recuperables} & cobertura
    faltan = len(recuperables) - len(ya)
    print(f"  articulos del corpus con numero     : {len(recuperables)}")
    print(f"  ya tienen criterio                  : {len(ya)}")
    print(f"  habria que pedir                    : {faltan}")
    # Una busqueda por articulo, mas una descarga por consulta que no tengamos.
    # Se cuenta el caso bueno -sin descargas- y el caso alto -todas nuevas-.
    bajo = faltan * PAUSA / 3600
    alto = faltan * (1 + POR_ARTICULO) * PAUSA / 3600
    print()
    print(f"  a {PAUSA}s por peticion:")
    print(f"    solo las busquedas          : {bajo:.1f} horas")
    print(f"    con hasta {POR_ARTICULO} consultas cada uno: {alto:.1f} horas")
    print()
    print("  El rango es ancho a proposito: cuantas descargas salen depende de")
    print("  cuantos articulos tengan criterio, y eso no se sabe hasta pedirlo.")
    print("  Lo medido en la ultima siembra: de 630 articulos, 53 no tenian")
    print("  ninguna consulta, y el resto trajo unas 2,7 de media.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
