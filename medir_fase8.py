#!/usr/bin/env python3
"""MEDIDA DEL ANTES Y EL DESPUES de meter una norma en el corpus.

    python medir_fase8.py antes    > /ruta/antes.json
    python medir_fase8.py despues  > /ruta/despues.json
    python medir_fase8.py comparar antes.json despues.json

Todo deterministico y local: BM25, el grafo de remisiones y el corte por
pertinencia. NI UNA llamada al modelo. Por eso se puede medir tantas veces
como haga falta sin que cueste nada.

Lo que se mide, y por que ese y no otro:

  · remisiones      cuantas se resuelven y cuantas quedan colgando. Es lo que
                    una norma nueva viene a desbloquear.
  · puestos         en que puesto sale el articulo que cada consulta del banco
                    busca. Una norma nueva compite por esos puestos.
  · corte           que preceptos pasan el filtro de pertinencia y llegan al
                    redactor, y de que norma es cada uno. Aqui es donde se ve
                    la contaminacion: material de la norma nueva colandose en
                    consultas que no van de eso.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import fase4
from agente_fiscal import estado as EST

CASOS = RAIZ / "casos" / "banco_recuperacion.txt"


def cuerpo_de(ix, registro) -> str:
    """Etiqueta corta de la norma a la que pertenece un precepto."""
    clave = registro.get("cuerpo_clave") or registro.get("norma_id") or ""
    try:
        return ix.normas.por_clave(clave).etiqueta
    except Exception:
        return clave


def medir(ix, grafo) -> dict:
    import banco

    datos: dict = {}

    # --- corpus ---------------------------------------------------------
    datos["corpus"] = {
        "normas": len(ix.normas),
        "preceptos": len(ix.docs),
        "cuerpos": [c.etiqueta for c in ix.normas.cuerpos.values()],
    }

    # --- remisiones -----------------------------------------------------
    s = grafo.stats
    datos["remisiones"] = {
        "total": s.total,
        "resueltas": s.resueltas,
        "cruzadas": s.cruzadas,
        "pendientes_externas": s.pendientes_externas,
        "pendientes_ambiguas": s.pendientes_ambiguas,
        "no_encontradas": s.no_encontradas,
        "pendientes_total": (s.pendientes_externas + s.pendientes_ambiguas
                             + s.no_encontradas),
        # A que normas de fuera se apunta y cuantas veces. Es la lista de la
        # compra: dice que norma tocaria ingerir despues.
        "normas_externas": dict(sorted(s.normas_externas.items(),
                                       key=lambda kv: -kv[1])[:15]),
    }

    # Quien remite a quien, por norma. Con esto se comprueba que lo que se
    # resuelve se resuelve BIEN: una remision cruzada tiene que apuntar a la
    # norma que toca, no a un articulo del mismo numero en otra ley.
    cruzadas = []
    for clave, remisiones in grafo.adelante.items():
        for r in remisiones:
            if r.ambito != "cruzada":
                continue
            org = grafo.por_clave.get(r.origen)
            dst = grafo.por_clave.get(r.destino)
            if not org or not dst:
                continue
            cruzadas.append({
                "origen": f"{cuerpo_de(ix, org.registro)} {org.registro['referencia']}",
                "destino": f"{cuerpo_de(ix, dst.registro)} {dst.registro['referencia']}",
                "texto": (getattr(r, "texto", "") or "")[:90],
            })
    datos["cruzadas"] = sorted(cruzadas, key=lambda x: (x["origen"], x["destino"]))

    # --- banco bloque 1: puesto de cada consulta -------------------------
    casos = banco.leer_casos(CASOS)
    puestos = []
    for caso in casos:
        cuerpo_esperado, motivo = ix.normas.resolver(caso["norma"])
        resultados, _ = ix.buscar(caso["consulta"], tope=max(caso["tope"], 10))
        puesto, salieron = None, []
        for i, r in enumerate(resultados, 1):
            rg = r.doc.registro
            num = rg["referencia"].replace("Articulo ", "")
            salieron.append(f"{num} [{cuerpo_de(ix, rg).split()[0]}]")
            if (puesto is None and num in caso["aceptables"]
                    and rg["cuerpo_clave"] == cuerpo_esperado):
                puesto = i
        puestos.append({
            "consulta": caso["consulta"],
            "norma": caso["norma"],
            "aceptables": caso["aceptables"],
            "tope": caso["tope"],
            "puesto": puesto,
            "verde": puesto is not None and puesto <= caso["tope"],
            "top6": salieron[:6],
            "linea": caso["linea"],
        })
    datos["puestos"] = puestos
    datos["banco_b1"] = {
        "verdes": sum(1 for p in puestos if p["verde"]),
        "total": len(puestos),
    }

    # --- corte por pertinencia -------------------------------------------
    # Para cada consulta del banco: que llega al redactor y de que norma es.
    corte = []
    for caso in casos:
        resultados, _ = ix.buscar(caso["consulta"], tope=5)
        seleccion = EST.seleccionar_material(ix, caso["consulta"], resultados,
                                             grafo)
        enviados = []
        for reg in seleccion.elegidos:
            enviados.append({
                "referencia": reg["referencia"],
                "norma": cuerpo_de(ix, reg),
            })
        corte.append({
            "consulta": caso["consulta"],
            "enviados": enviados,
            "n_enviados": len(enviados),
            "n_candidatos": len(seleccion.detalle),
        })
    datos["corte"] = corte

    return datos


def medir_puerta(ix, grafo) -> dict:
    """La puerta de materia: preguntas de otros impuestos NO pueden entrar.

    Se ejecuta la consulta entera con el motor de ensayo (no gasta nada) y se
    mira el codigo y el estado. Una norma general como la LGT es justo lo que
    podria abrir esta puerta por accidente: la LGT tambien aplica al IRPF, y
    ese es el argumento con el que se cuela cualquier cosa.
    """
    from agente_fiscal import modelo as MOD

    PREGUNTAS = [
        ("retencion del IRPF de un alquiler de vivienda habitual", 2023, "IRPF"),
        ("como tributa en el IRPF la venta de acciones", 2023, "IRPF"),
        ("plazo para contestar un requerimiento de Hacienda sobre el IVA",
         2023, "IVA+procedimiento"),
        ("tipo de IVA de los libros", 2023, "IVA"),
    ]
    salida = []
    for pregunta, ejercicio, clase in PREGUNTAS:
        motor = MOD.crear_motor("ensayo")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            res = fase4.consultar(pregunta, ejercicio, motor, ix, grafo)
        salida.append({
            "pregunta": pregunta,
            "clase": clase,
            "codigo": res["codigo"],
            "estado": res["estado"],
            "preceptos": res["preceptos"],
            "enviados": res.get("preceptos_enviados") or [],
            "motivo": (res.get("motivo") or "")[:160],
        })
    return {"puerta": salida}


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2

    if argv[0] == "comparar":
        return comparar(Path(argv[1]), Path(argv[2]))

    ix, grafo = fase4.cargar_corpus()
    datos = medir(ix, grafo)
    datos.update(medir_puerta(ix, grafo))
    datos["momento"] = argv[0]
    print(json.dumps(datos, ensure_ascii=False, indent=2))
    return 0


# ------------------------------------------------------------------ comparar


def comparar(ruta_a: Path, ruta_b: Path) -> int:
    a = json.loads(ruta_a.read_text(encoding="utf-8"))
    b = json.loads(ruta_b.read_text(encoding="utf-8"))

    def linea(t=""):
        print(t)

    linea("=" * 78)
    linea("  FASE 8 - ANTES Y DESPUES")
    linea("=" * 78)

    ca, cb = a["corpus"], b["corpus"]
    linea(f"\nCORPUS   {ca['normas']} normas / {ca['preceptos']} preceptos"
          f"   ->   {cb['normas']} normas / {cb['preceptos']} preceptos")
    nuevas = [c for c in cb["cuerpos"] if c not in ca["cuerpos"]]
    linea(f"         nuevas: {', '.join(nuevas) if nuevas else '(ninguna)'}")

    ra, rb = a["remisiones"], b["remisiones"]
    linea("\nREMISIONES")
    linea(f"  {'':22s} {'antes':>8s} {'despues':>9s} {'cambio':>8s}")
    for campo, rotulo in [
        ("total", "detectadas"),
        ("resueltas", "resueltas"),
        ("cruzadas", "cruzadas entre normas"),
        ("pendientes_total", "PENDIENTES"),
        ("pendientes_externas", "  a norma de fuera"),
        ("pendientes_ambiguas", "  ambiguas"),
        ("no_encontradas", "  no encontradas"),
    ]:
        va, vb = ra[campo], rb[campo]
        d = vb - va
        linea(f"  {rotulo:22s} {va:8d} {vb:9d} {d:+8d}")

    linea("\nBANCO BLOQUE 1")
    linea(f"  verdes: {a['banco_b1']['verdes']}/{a['banco_b1']['total']}"
          f"  ->  {b['banco_b1']['verdes']}/{b['banco_b1']['total']}")
    linea()
    linea(f"  {'consulta':52s} {'antes':>6s} {'desp':>6s}  ")
    linea("  " + "-" * 72)
    empeoran, rompen = [], []
    pa = {p["consulta"]: p for p in a["puestos"]}
    for p in b["puestos"]:
        antes = pa.get(p["consulta"])
        if antes is None:
            continue
        va = antes["puesto"]
        vb = p["puesto"]
        ta = "-" if va is None else str(va)
        tb = "-" if vb is None else str(vb)
        marca = ""
        if va is not None and vb is not None and vb > va:
            marca = "  EMPEORA"
            empeoran.append((p["consulta"], va, vb))
        elif va is not None and vb is None:
            marca = "  SE PIERDE"
            rompen.append((p["consulta"], va, None))
        elif va is not None and vb is not None and vb < va:
            marca = "  mejora"
        if antes["verde"] and not p["verde"]:
            marca += "  <-- SE PONE EN ROJO"
            rompen.append((p["consulta"], va, vb))
        linea(f"  {p['consulta'][:52]:52s} {ta:>6s} {tb:>6s}{marca}")

    linea("\nCORTE POR PERTINENCIA - contaminacion")
    conocidas = set(ca["cuerpos"])
    contaminadas = []
    for c in b["corte"]:
        intrusos = [e for e in c["enviados"] if e["norma"] not in conocidas]
        if intrusos:
            contaminadas.append((c["consulta"], intrusos))
    if not contaminadas:
        linea("  NINGUNA consulta del banco recibe material de la norma nueva.")
    else:
        for consulta, intrusos in contaminadas:
            linea(f"  {consulta[:56]}")
            for i in intrusos:
                linea(f"      <- {i['norma']} {i['referencia']}")

    linea("\nPUERTA DE MATERIA")
    pb = {x["pregunta"]: x for x in b["puerta"]}
    for x in a["puerta"]:
        y = pb.get(x["pregunta"], {})
        linea(f"  [{x['clase']:18s}] {x['pregunta'][:44]:44s}")
        linea(f"       antes: codigo {x['codigo']} {x['estado']}"
              f"   ->   despues: codigo {y.get('codigo')} {y.get('estado')}")

    linea("\n" + "=" * 78)
    if rompen:
        linea(f"  ROTO: {len(rompen)} consulta(s) del banco han empeorado a rojo")
    elif empeoran:
        linea(f"  OJO: {len(empeoran)} consulta(s) bajan de puesto sin ponerse rojas")
    else:
        linea("  Ninguna consulta del banco empeora.")
    linea("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
