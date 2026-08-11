#!/usr/bin/env python3
"""QUE ARTICULOS MERECE LA PENA SEMBRAR, Y POR QUE. Cero red, cero API.

    python3 plan_siembra.py                 la lista, con su porque
    python3 plan_siembra.py --json          para que la coman los sembradores

SEMBRAR A OJO ES LO QUE NOS HA DEJADO LA DESPENSA ENTERA EN IVA. `sembrar_teac`
llevaba tres cuerpos escritos a mano -Ley del IVA, Reglamento del IVA y LGT- de
cuando el corpus era solo IVA. El corpus ya son cuatro impuestos y la despensa
sigue donde estaba; ningun aviso lo dice, porque nadie mide eso.

COMO SE PRIORIZA, y las tres fuentes son distintas a proposito:

  1. LO QUE EL BANCO MANDA AL REDACTOR. Son 19 preguntas escritas mirando la
     ley, no la despensa: si un articulo llega al material de una de ellas, es
     un articulo por el que se pregunta de verdad.

  2. LO MAS CITADO POR REMISION DENTRO DEL CORPUS. Un precepto al que apuntan
     otros veinte es donde vive la excepcion que no se ve leyendo el articulo
     solo, y es justo donde una consulta de la DGT vale mas.

  3. EL REPARTO POR IMPUESTO, que es lo que arregla el sesgo. La cuota NO sale
     del tamano del corpus -si saliera, el 43% iria a normas generales, que es
     donde menos criterio hay y menos falta hace- sino de por donde entra el
     trabajo en una gestoria.

LO QUE ESTE GUION NO HACE: no descarga nada. Escribe la lista y para. Lo que se
siembre se decide mirandola.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from agente_fiscal import referencias as R  # noqa: E402
from agente_fiscal.indice import Indice  # noqa: E402

CORPUS = RAIZ / "datos" / "corpus"

# CUANTOS ARTICULOS POR IMPUESTO. La cuota es del REPARTO DEL TRABAJO de una
# gestoria, no del tamano del corpus:
#
#   · IVA e IRPF son el pan de cada dia y ademas es donde mas criterio publica
#     la DGT: se llevan la mitad entre los dos.
#   · SOCIEDADES pesa menos en numero de consultas pero cada una vale mas y su
#     articulado es mas denso en conceptos discutidos.
#   · PATRIMONIO tiene 47 articulos en total: con 10 se cubre lo que se
#     pregunta -minimo exento, exenciones, valoracion- y pedir mas seria
#     sembrar articulos por los que no pregunta nadie.
#   · GENERALES: solo procedimiento (LGT, RGAT, recaudacion, sancionador).
#     Aqui el criterio del TEAC es abundante y el de la DGT escaso, asi que la
#     cuota se gasta sobre todo en TEAC.
CUOTA = {"IVA": 30, "IRPF": 30, "IS": 22, "IP": 10, "GENERAL": 26}

# Un articulo del banco vale por estas remisiones entrantes. No es un ajuste
# fino: es decir que una pregunta real pesa mas que una cita interna.
PESO_BANCO = 12


def preguntas_del_banco() -> list:
    ruta = RAIZ / "casos" / "banco_recuperacion.txt"
    if not ruta.is_file():
        raise SystemExit(f"[FALLO] no existe {ruta}: sin banco no hay prioridad")
    fuera = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "|" in linea:
            fuera.append(linea.split("|")[0].strip())
    if not fuera:
        raise SystemExit(f"[FALLO] {ruta} no tiene preguntas dentro")
    return fuera


def plan() -> dict:
    """{impuesto: [ {clave, referencia, cuerpo, puntos, porque} ]}"""
    ix = Indice(CORPUS)
    grafo = R.GrafoRemisiones(ix.docs)
    N = ix.normas

    entrantes = {d.clave: len(grafo.le_mencionan(d.clave)) for d in ix.docs}

    # 1. lo que el banco manda al redactor, de verdad, corriendo la busqueda.
    del_banco: collections.Counter = collections.Counter()
    from agente_fiscal import estado as EST
    for p in preguntas_del_banco():
        res, _h = ix.buscar(p, tope=6)
        sel = EST.seleccionar_material(ix, p, res, grafo)
        for reg in sel.elegidos:
            del_banco[reg["clave"]] += 1

    puntos: collections.Counter = collections.Counter()
    porque: dict = {}
    # EL ARTICULADO DE UN DECRETO APROBATORIO NO SE SIEMBRA. Son «se aprueba
    # el reglamento», «entrada en vigor» y «modificacion del Real Decreto
    # 2402/1985»: nadie ha consultado nunca a la DGT sobre eso, y el articulo 4
    # del RD 1624/1992 se colaba en la lista del IVA por sus remisiones.
    aprobatorios = {
        c.clave for c in N.cuerpos.values()
        if c.indice == 0
        and any(o.norma_id == c.norma_id and o.indice != 0
                for o in N.cuerpos.values())}

    for d in ix.docs:
        # Solo articulos: las disposiciones no se consultan por numero en
        # DYCTEA ni en PETETE, y sembrar por ellas devuelve ruido.
        if not re.search(r"#articulo ", d.clave):
            continue
        if d.registro.get("cuerpo_clave") in aprobatorios:
            continue
        b, e = del_banco.get(d.clave, 0), entrantes.get(d.clave, 0)
        if not b and not e:
            continue
        puntos[d.clave] = b * PESO_BANCO + e
        trozos = []
        if b:
            trozos.append(f"lo manda el banco en {b} consulta(s)")
        if e:
            trozos.append(f"{e} remisiones entrantes")
        porque[d.clave] = " · ".join(trozos)

    por_impuesto: dict = collections.defaultdict(list)
    for clave, n in puntos.most_common():
        doc = ix.por_clave[clave]
        imp = N.impuesto_de_cuerpo(doc.registro.get("cuerpo_clave") or "") or "GENERAL"
        if len(por_impuesto[imp]) >= CUOTA.get(imp, 0):
            continue
        cuerpo = N.cuerpos.get(doc.registro.get("cuerpo_clave") or "")
        por_impuesto[imp].append({
            "clave": clave,
            "referencia": doc.registro["referencia"],
            "cuerpo": cuerpo.etiqueta if cuerpo else "?",
            "cuerpo_clave": doc.registro.get("cuerpo_clave"),
            "rubrica": (doc.registro.get("rubrica") or "")[:52],
            "puntos": n,
            "porque": porque[clave],
        })
    return dict(por_impuesto)


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true",
                    help="escribe la lista en JSON, para los sembradores")
    args = ap.parse_args(argv)

    p = plan()
    if args.json:
        print(json.dumps(p, ensure_ascii=False, indent=2))
        return 0

    print("=" * 76)
    print("PLAN DE SIEMBRA · que articulos y por que")
    print("=" * 76)
    total = sum(len(v) for v in p.values())
    print(f"{total} articulos. Cuota por impuesto: "
          + " · ".join(f"{k} {v}" for k, v in CUOTA.items()))
    for imp in ("IVA", "IRPF", "IS", "IP", "GENERAL"):
        lista = p.get(imp) or []
        print(f"\n{'-' * 76}\n{imp}  ({len(lista)} de {CUOTA.get(imp, 0)})")
        cuerpos = collections.Counter(x["cuerpo"] for x in lista)
        for c, n in cuerpos.most_common():
            print(f"    {n:>3}  {c[:64]}")
        print()
        for x in lista:
            print(f"    {x['puntos']:>4}  {x['referencia']:<26} "
                  f"{x['rubrica']:<52}")
            print(f"          {x['porque']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
