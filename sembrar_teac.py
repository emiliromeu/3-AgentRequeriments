#!/usr/bin/env python3
"""SIEMBRA DE LA DOCTRINA DEL TEAC, POR PRECEPTO.

    python sembrar_teac.py plan       # que se va a bajar, sin bajar nada
    python sembrar_teac.py sembrar    # baja, se puede parar y retomar
    python sembrar_teac.py informe    # que hay en la despensa, por articulo

NO GASTA NI UNA LLAMADA A LA API DE ANTHROPIC. Esto es descarga y nada mas.

----------------------------------------------------------------------------
POR QUE POR PRECEPTO
----------------------------------------------------------------------------
Porque es COMO SE BUSCA. `CacheTEAC.seleccionar` parte de los preceptos que
sostienen una respuesta y busca criterio sobre ellos; sembrar por tema o por
palabras traeria cosas que el agente nunca va a mirar.

Los articulos NO se eligen a mano: salen de sumar las remisiones que entran a
cada precepto dentro del corpus y lo que aparece en el banco y en la bateria,
esto ultimo con peso triple, porque lo que se pregunta importa mas que lo que
se cita. La LGT se acota a los titulos de procedimiento leyendo el `contexto`
de cada articulo.

----------------------------------------------------------------------------
COMO SE PORTA
----------------------------------------------------------------------------
· MISMO RITMO QUE CON PETETE. Usa `teac.Fuente`, que hereda pausas de 4 s,
  tope de reintentos y User-Agent que nos identifica. Que DYCTEA contesta en
  0,14 s no cambia nada: el descuido empieza justo donde sobra capacidad.
· SE PUEDE PARAR Y RETOMAR. Lo ya descargado no se vuelve a pedir y el avance
  se escribe DESPUES DE CADA CRITERIO, no al final.
· Si la fuente se cae, PARA y dice por donde iba. No insiste: los reintentos
  con tope ya los hace la fuente, y encima de eso insistir es como se tumba un
  servicio publico.
· TOPE de criterios por tanda.

PRIORIDAD: primero los calificados como DOCTRINA o UNIFICACION DE CRITERIO,
que son los que vinculan. Lo demas, despues y si queda cupo.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import teac as T  # noqa: E402
from agente_fiscal import teac as TC  # noqa: E402

AVANCE = TC.DIR_CACHE / "siembra_teac.json"
TOPE = 600

# Los codigos de norma de DYCTEA. Se leen del catalogo, no se escriben: el
# catalogo es suyo y puede cambiar.
NORMAS_CORPUS = {
    "BOE-A-1992-28740#0": "Ley 37/1992",
    "BOE-A-1992-28925#1": "RD 1624/1992",
    "BOE-A-2003-23186#0": "Ley 58/2003",
}


def _catalogo() -> dict:
    return json.loads((TC.DIR_CACHE / "catalogo.json").read_text("utf-8"))


def codigo_de_norma(cat: dict, aguja: str) -> str:
    """El codigo de DYCTEA de una norma. OJO CON LAS QUE LA MODIFICAN.

    La primera version cogia la primera entrada del catalogo que CONTUVIERA el
    nombre, y para «Ley 37/1992» devolvia `02:07:28:00:00`, que es «Ley 28/2014
    Modificacion de Ley 37/1992 de IVA...». Sembrar con ese codigo habria
    traido la doctrina de la ley modificadora en vez de la del IVA, y nadie lo
    habria notado: los criterios habrian llegado igual, solo que del sitio que
    no era.

    Es la misma trampa que al ingerir del BOE. Se descarta lo que se presenta
    como modificacion y se exige que el nombre EMPIECE por la designacion.
    """
    aguja = aguja.lower()
    for cod, nombre in cat["normas"].items():
        n = nombre.lower()
        if any(x in n for x in ("modifica", "modificación", "modificacion")):
            continue
        if n.startswith(aguja):
            return cod
    return ""


# --------------------------------------------------------------- el plan


def plan() -> list:
    """[(cuerpo, etiqueta, articulo, cod_norma, cod_precepto)], por prioridad.

    LA LISTA YA NO SE ESCRIBE AQUI. Antes habia tres cuerpos a mano -Ley del
    IVA, Reglamento del IVA y LGT- de cuando el corpus era solo IVA; el corpus
    paso a cuatro impuestos y la despensa se quedo donde estaba, sin que nada
    lo dijera. Ahora la lista la calcula `plan_siembra` con datos: lo que el
    banco manda al redactor, las remisiones entrantes y una cuota por impuesto.

    Aqui solo se traduce esa lista a los codigos de DYCTEA. Lo que no este en
    su catalogo se anota como aviso y se sigue: el catalogo es suyo.
    """
    import plan_siembra

    cat = _catalogo()
    salida = []
    por_impuesto = plan_siembra.plan()
    # Se intercalan los impuestos en vez de vaciar uno y pasar al siguiente:
    # si la fuente se cae a mitad, lo bajado esta repartido y no todo en IVA,
    # que es exactamente el sesgo que esto viene a corregir.
    listas = [por_impuesto.get(k) or [] for k in
              ("IVA", "IRPF", "IS", "IP", "GENERAL")]
    filas = [x for grupo in zip(*[l + [None] * (max(map(len, listas)) - len(l))
                                  for l in listas]) for x in grupo if x]
    for fila in filas:
        etiqueta = (fila["cuerpo"] or "").split(",")[0]
        cod_norma = codigo_de_norma(cat, etiqueta)
        art = fila["referencia"].replace("Articulo ", "").strip()
        cod_precepto = (cat["preceptos"].get(cod_norma) or {}).get(art, "")
        salida.append((fila["cuerpo_clave"], etiqueta, art, cod_norma,
                       cod_precepto))
    return salida


def _cargar_avance() -> dict:
    if AVANCE.is_file():
        try:
            return json.loads(AVANCE.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"hechos": [], "bajados": 0, "fallos": [], "avisos": [],
            "por_articulo": {}}


def _guardar_avance(a: dict) -> None:
    AVANCE.parent.mkdir(parents=True, exist_ok=True)
    AVANCE.write_text(json.dumps(a, ensure_ascii=False, indent=1),
                      encoding="utf-8")


def prioridad(fila: dict) -> int:
    """Doctrina y unificacion primero: son las que vinculan."""
    et = " ".join(str(fila.get(k) or "") for k in
                  ("etiqueta", "calificacion", "resolucion")).lower()
    if "unificacion" in et or "unificación" in et:
        return 0
    if "doctrina" in et:
        return 1
    return 2


# ------------------------------------------------------------- sembrar


def sembrar(tope: int) -> int:
    cache = T.Cache()
    fuente = T.Fuente()
    avance = _cargar_avance()
    hechos = set(avance["hechos"])
    tareas = plan()
    print(f"{len(tareas)} articulo(s) en el plan · tope de {tope} criterios\n",
          flush=True)

    bajados = 0
    for cuerpo, etiqueta, art, cod_norma, cod_precepto in tareas:
        marca = f"{etiqueta}#{art}"
        if marca in hechos:
            print(f"  [ya estaba] {marca}", flush=True)
            continue
        if not cod_precepto:
            print(f"  [sin codigo en el catalogo] {marca}", flush=True)
            avance["avisos"].append(f"{marca}: DYCTEA no lista ese precepto")
            hechos.add(marca)
            avance["hechos"] = sorted(hechos)
            _guardar_avance(avance)
            continue

        print(f"\n== {marca} ==", flush=True)
        try:
            crudo = fuente.buscar(cod_norma, cod_precepto)
            filas = T.extraer_resultados(crudo)
        except T.FuenteCaida as e:
            print(f"  LA FUENTE SE HA CAIDO buscando {marca}: {e}", flush=True)
            print(f"  se para aqui. Llevaba {avance['bajados']} criterio(s).",
                  flush=True)
            _guardar_avance(avance)
            return 1
        except T.FormaInesperada as e:
            print(f"  [forma no reconocida] {marca}: {e}", flush=True)
            avance["avisos"].append(f"{marca}: {e}")
            hechos.add(marca)
            avance["hechos"] = sorted(hechos)
            _guardar_avance(avance)
            continue

        filas.sort(key=prioridad)
        print(f"  {len(filas)} resultado(s) en DYCTEA", flush=True)
        n_art = 0
        for f in filas:
            if avance["bajados"] >= tope:
                print(f"\n  TOPE DE {tope} ALCANZADO. Se para y se puede "
                      f"retomar.", flush=True)
                avance["hechos"] = sorted(hechos)
                _guardar_avance(avance)
                return 0
            ident = f["id"]
            try:
                _reg, origen = T.obtener_criterio(ident, cache, fuente,
                                                  verboso=False)
            except T.FuenteCaida as e:
                print(f"  LA FUENTE SE HA CAIDO en {ident}: {e}", flush=True)
                print(f"  se para aqui. Llevaba {avance['bajados']} "
                      f"criterio(s).", flush=True)
                avance["hechos"] = sorted(hechos)
                _guardar_avance(avance)
                return 1
            except T.FormaInesperada as e:
                print(f"    [forma no reconocida] {ident}: {e}", flush=True)
                avance["avisos"].append(f"{ident}: {e}")
                continue
            except Exception as e:  # noqa: BLE001
                print(f"    [fallo] {ident}: {type(e).__name__}: {e}",
                      flush=True)
                avance["fallos"].append(f"{ident}: {e}")
                continue
            n_art += 1
            if origen == "red":
                avance["bajados"] += 1
                bajados += 1
                print(f"    {ident}  ({avance['bajados']}/{tope})", flush=True)
            _guardar_avance(avance)

        avance["por_articulo"][marca] = n_art
        hechos.add(marca)
        avance["hechos"] = sorted(hechos)
        _guardar_avance(avance)
        print(f"  {marca}: {n_art} criterio(s)", flush=True)

    print(f"\nHECHO. {bajados} criterio(s) nuevos en esta tanda.", flush=True)
    return 0


# -------------------------------------------------------------- informe


def informe() -> int:
    avance = _cargar_avance()
    cache = TC.CacheTEAC()
    todos = cache.todas()
    print(f"CRITERIOS EN LA COPIA LOCAL: {len(todos)}\n")

    citan_dgt = [c for c in todos if getattr(c, "consultas_dgt", "")]
    print(f"  citan consultas de la DGT por numero : {len(citan_dgt)}")
    unidades = collections.Counter(
        c.unidad or "(sin unidad)" for c in todos if not c.es_central)
    print(f"  de tribunales regionales             : {sum(unidades.values())}")
    for u, n in unidades.most_common():
        print(f"      {u}: {n}")
    cal = collections.Counter(c.calificacion or "(sin calificar)" for c in todos)
    print("\n  por calificacion:")
    for k, n in cal.most_common():
        print(f"      {k}: {n}")
    print(f"\n  bajados en la siembra : {avance['bajados']}")
    print(f"  fallos                : {len(avance['fallos'])}")
    print(f"  avisos de forma       : {len(avance['avisos'])}")

    print("\n  POR ARTICULO (los de cero son los temas sin doctrina):")
    for cuerpo, etiqueta, art, _cn, _cp in plan():
        n = avance["por_articulo"].get(f"{etiqueta}#{art}")
        estado = "sin sembrar" if n is None else f"{n} criterio(s)"
        aviso = "   <- SIN DOCTRINA" if n == 0 else ""
        print(f"      {etiqueta:14s} art. {art:>4s}  {estado}{aviso}")
    return 0


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="modo", required=True)
    sub.add_parser("plan")
    s = sub.add_parser("sembrar")
    s.add_argument("--tope", type=int, default=TOPE)
    sub.add_parser("informe")
    args = ap.parse_args(argv)

    if args.modo == "plan":
        for cuerpo, etiqueta, art, cn, cp in plan():
            print(f"  {etiqueta:14s} art. {art:>4s}  norma={cn} precepto={cp or '(no listado)'}")
        return 0
    if args.modo == "sembrar":
        return sembrar(args.tope)
    return informe()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
