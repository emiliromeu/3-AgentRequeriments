#!/usr/bin/env python3
"""SIEMBRA DE LA CACHE DE CRITERIO DE LA DGT.

    python sembrar.py plan          # que se va a bajar, sin bajar nada
    python sembrar.py sembrar       # baja, se puede parar y retomar
    python sembrar.py informe       # que hay en la despensa

NO GASTA NI UNA LLAMADA A LA API DE ANTHROPIC. Esto es descarga y nada mas: no
enciende la DGT, no toca el agente y no cambia ningun estado.

----------------------------------------------------------------------------
POR QUE
----------------------------------------------------------------------------
Cada consulta nueva contra PETETE tarda decenas de segundos. Si el departamento
enciende la DGT y cada duda cuesta medio minuto, la cierran y no vuelven. Con la
despensa llena, los temas frecuentes salen instantaneos y sin depender de que la
fuente este viva ese dia, que ya hemos visto que no siempre lo esta.

----------------------------------------------------------------------------
COMO SE PORTA
----------------------------------------------------------------------------
· Volumen bajo y pausas: usa el mismo `petete.Fuente` de siempre.
· SE PUEDE PARAR Y RETOMAR. Lo ya descargado no se vuelve a pedir, y el avance
  queda en `datos/dgt/siembra.json` despues de CADA consulta, no al final.
· Si la fuente se cae, PARA y dice por donde iba. No reintenta en bucle: los
  reintentos con tope ya los hace `petete.Fuente`, y encima de eso insistir es
  como se tumba un servicio publico.
· Tope de consultas, para no pasarse de lo acordado.

Se busca por el campo NORMATIVA («37/1992 95»), que es lo que de verdad
encuentra consultas SOBRE un articulo. Buscar por texto libre trae lo que
menciona las palabras, que no es lo mismo.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import petete
from agente_fiscal import dgt as DGT

AVANCE = RAIZ / "datos" / "dgt" / "siembra.json"
DIARIO = RAIZ / "datos" / "dgt" / "siembra.log"
ANCHO = 78

TOPE_POR_DEFECTO = 150
POR_ARTICULO = 5          # cuantas consultas, las mas recientes, de cada uno


def ahora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def apuntar(texto: str) -> None:
    """Al diario y a la pantalla. Esto puede correr horas sin nadie delante."""
    DIARIO.parent.mkdir(parents=True, exist_ok=True)
    with DIARIO.open("a", encoding="utf-8") as f:
        f.write(f"{ahora()}  {texto}\n")
    print(texto, flush=True)


# ------------------------------------------------------------------- el plan


def orden_articulo(a: str) -> int:
    m = re.match(r"^(\d+)", a)
    return int(m.group(1)) if m else 999


# Los temas que pidio el encargo, por articulo de la LIVA y del RIVA.
TEMAS = [
    ("deducciones", "LIVA", ["95", "96", "97", "99", "100"]),
    ("modificacion de base imponible", "LIVA", ["80"]),
    ("rectificacion de cuotas", "LIVA", ["89"]),
    ("tipos", "LIVA", ["91"]),
    ("prorrata", "LIVA", ["102", "103", "104", "105", "106"]),
    ("bienes de inversion", "LIVA", ["107", "110"]),
    ("devoluciones", "LIVA", ["115", "116", "119"]),
    ("obligaciones formales", "LIVA", ["164"]),
]

# Como se nombra cada norma en el campo «normativa» de PETETE.
NUMERO_NORMA = {"LIVA": "37/1992", "RIVA": "1624/1992", "LGT": "58/2003"}

# Y como se llama cada una para NUESTRO resolutor, que es otra cosa: el numero
# suelto («37/1992») es lo que entiende el buscador de PETETE, y no resuelve
# contra el corpus. Dos mapas porque son dos idiomas.
DESIGNACION = {
    "LIVA": "Ley 37/1992",
    "RIVA": "Reglamento del Impuesto sobre el Valor Añadido",
    "LGT": "Ley 58/2003",
}

# La LGT entra en la siembra a partir de la segunda pasada. Motivo, medido: de
# las 19 consultas del banco, SIETE se quedaban sin criterio ninguno, y los
# articulos que les faltaban son casi todos de procedimiento -27, 135, 138,
# 198, 203, 236, 239, 267-. La primera siembra solo miro IVA, asi que en
# procedimiento la despensa estaba vacia por construccion, no por falta de
# criterio en la fuente.


def _numero_de_articulo(a: str) -> str:
    """«31 bis» -> «31 bis»; «disposicion adicional quinta» -> «».

    A PETETE se le busca por numero de articulo. Una disposicion no tiene
    numero que buscar, asi que no se pide: pedirla es gastar una peticion en
    una busqueda que sabemos que no encuentra nada.
    """
    return a if re.match(r"^\d", a.strip()) else ""


def articulos_sin_criterio() -> list:
    """(norma, articulo) que el banco MANDA AL REDACTOR y no tienen criterio.

    No es una lista escrita a mano: se calcula. Para cada consulta del banco se
    corre la busqueda y el corte de material -deterministas los dos, ni una
    llamada al modelo- y se mira que preceptos acaban en el material. Los que
    no tienen ni una consulta cacheada que los cite son el agujero.

    Se apunta a lo que SE MANDA y no a lo que el banco espera: el recorte de
    criterio compara contra los preceptos del material, asi que ahi es donde se
    nota el vacio.
    """
    import fase4, banco
    from agente_fiscal import estado as EST

    ix, grafo = fase4.cargar_corpus()
    N = ix.normas
    clave_de = {}
    for etiqueta, designacion in DESIGNACION.items():
        clave, _m = N.resolver(designacion)
        if clave:
            clave_de[clave] = etiqueta

    cobertura: Counter = Counter()
    for c in DGT.CacheDGT().todas():
        for p in c.preceptos(N):
            if p.comparable:
                cobertura[(p.cuerpo, p.numero.lower())] += 1

    faltan: Counter = Counter()
    for caso in banco.leer_casos(banco.CASOS):
        res, _ = ix.buscar(caso["consulta"], tope=5)
        sel = EST.seleccionar_material(ix, caso["consulta"], res, grafo)
        for r in sel.elegidos:
            cuerpo = r.get("cuerpo_clave", "")
            num = r["referencia"].replace("Articulo ", "").strip().lower()
            if cuerpo not in clave_de or cobertura.get((cuerpo, num)):
                continue
            if not _numero_de_articulo(num):
                continue
            faltan[(clave_de[cuerpo], num)] += 1

    return [{"norma": n, "articulo": a, "veces": v}
            for (n, a), v in sorted(faltan.items(), key=lambda x: (-x[1], x[0][1]))]


def construir_plan() -> list:
    """La lista, ordenada por lo que mas aparece en el banco y en las remisiones."""
    import fase4, banco

    ix, grafo = fase4.cargar_corpus()
    N = ix.normas
    liva = "BOE-A-1992-28740#0"
    riva = next(c.clave for c in N.cuerpos.values()
                if c.etiqueta.startswith("Reglamento"))
    clave_de = {"LIVA": liva, "RIVA": riva}

    casos = banco.leer_casos(banco.CASOS)
    en_banco: Counter = Counter()
    for c in casos:
        cuerpo, _ = N.resolver(c["norma"])
        for a in c["aceptables"]:
            en_banco[(cuerpo, a)] += 1

    entrantes: Counter = Counter()
    for clave, rems in grafo.atras.items():
        d = grafo.por_clave.get(clave)
        if d:
            r = d.registro
            entrantes[(r.get("cuerpo_clave"),
                       r["referencia"].replace("Articulo ", ""))] = len(rems)

    temas = list(TEMAS)
    # Del Reglamento, los que ya estan en el banco: son los que la gente pregunta.
    del_banco = sorted({a for c in casos for a in c["aceptables"]
                        if N.resolver(c["norma"])[0] == riva}, key=orden_articulo)
    temas.append(("Reglamento (los del banco)", "RIVA", del_banco))

    # SEGUNDA PASADA: los agujeros medidos, no supuestos. Ver
    # `articulos_sin_criterio`. Van al final para que la primera siembra siga
    # siendo reproducible: lo de antes no se mueve de sitio.
    huecos = articulos_sin_criterio()
    for etiqueta in ("LIVA", "RIVA", "LGT"):
        arts = [h["articulo"] for h in huecos if h["norma"] == etiqueta]
        if arts:
            temas.append((f"agujeros del banco ({etiqueta})", etiqueta, arts))

    clave_de["LGT"] = N.resolver(DESIGNACION["LGT"])[0] or ""

    filas = []
    for tema, norma, arts in temas:
        for a in arts:
            filas.append({
                "tema": tema, "norma": norma, "articulo": a,
                "cuerpo": clave_de[norma],
                "banco": en_banco.get((clave_de[norma], a), 0),
                "remisiones": entrantes.get((clave_de[norma], a), 0),
            })
    filas.sort(key=lambda f: (-f["banco"], -f["remisiones"],
                              orden_articulo(f["articulo"])))
    return filas


# ------------------------------------------------------------------ avance


def leer_avance() -> dict:
    if AVANCE.is_file():
        try:
            return json.loads(AVANCE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            apuntar("[aviso] el fichero de avance estaba corrupto; se empieza uno "
                    "nuevo (lo ya descargado NO se pierde: esta en la cache)")
    return {"creado": ahora(), "articulos": {}, "descargadas": [],
            "fallidas": {}, "cortes": []}


def guardar_avance(av: dict) -> None:
    AVANCE.parent.mkdir(parents=True, exist_ok=True)
    av["actualizado"] = ahora()
    AVANCE.write_text(json.dumps(av, ensure_ascii=False, indent=1),
                      encoding="utf-8")


# ----------------------------------------------------------------- sembrar


def modo_plan(args) -> int:
    filas = construir_plan()
    print("=" * ANCHO)
    print("  PLAN DE SIEMBRA")
    print("=" * ANCHO)
    print(f"\n  {'#':>2s} {'norma':5s} {'art':12s} {'banco':>5s} {'remis':>5s}  tema")
    print("  " + "-" * 70)
    for i, f in enumerate(filas, 1):
        print(f"  {i:2d} {f['norma']:5s} {f['articulo']:12s} "
              f"{f['banco']:5d} {f['remisiones']:5d}  {f['tema']}")
    print(f"\n  {len(filas)} articulos x {args.por_articulo} consultas = "
          f"{len(filas) * args.por_articulo} como mucho (tope {args.tope})")
    return 0


def modo_sembrar(args) -> int:
    filas = construir_plan()
    av = leer_avance()
    cache = petete.Cache()
    fuente = petete.Fuente(silencioso=True)

    apuntar("=" * ANCHO)
    apuntar(f"SIEMBRA · {len(filas)} articulos, tope {args.tope} consultas, "
            f"{args.por_articulo} por articulo")
    apuntar("=" * ANCHO)

    ya = len(av["descargadas"])
    if ya:
        apuntar(f"se retoma: {ya} consultas ya descargadas en pasadas anteriores")

    bajadas = 0
    for n, fila in enumerate(filas, 1):
        etiqueta = f"{fila['norma']} art. {fila['articulo']}"
        if len(av["descargadas"]) >= args.tope:
            apuntar(f"\n[tope] alcanzadas {args.tope} consultas: se para aqui")
            break

        # --- 1. que consultas hay sobre este articulo -------------------
        pendientes = av["articulos"].get(etiqueta, {}).get("numeros")
        if pendientes is None:
            consulta = f"{NUMERO_NORMA[fila['norma']]} {fila['articulo']}"
            try:
                campos = fuente._campos("", "", petete.TAB_VINCULANTES, 1)
                campos = [(k, consulta if k == "VLCMP_3" else v)
                          for k, v in campos]
                crudo = fuente.pedir("/do/search", campos).cuerpo
                resultados = petete.extraer_resultados(crudo)
            except petete.FuenteCaida as e:
                apuntar(f"\n[PARADA] la fuente no responde buscando {etiqueta}: {e}")
                av["cortes"].append({"cuando": ahora(), "donde": etiqueta,
                                     "motivo": str(e)})
                guardar_avance(av)
                return _resumen_corte(av, args)
            except petete.FormaInesperada as e:
                apuntar(f"  [{n:2d}/{len(filas)}] {etiqueta:18s} FORMA INESPERADA: {e}")
                av["fallidas"][etiqueta] = f"forma inesperada: {e}"
                guardar_avance(av)
                continue
            # Las mas recientes primero: la busqueda ya viene ordenada por fecha.
            pendientes = [r["numero"] for r in resultados if r["numero"]][:args.por_articulo]
            for r in resultados:
                if r["numero"]:
                    cache.apuntar_id(r["numero"], r["doc_id"],
                                     r.get("tab") or petete.TAB_VINCULANTES)
            av["articulos"][etiqueta] = {"numeros": pendientes,
                                         "hallados": len(resultados),
                                         "cuando": ahora()}
            guardar_avance(av)

        apuntar(f"  [{n:2d}/{len(filas)}] {etiqueta:18s} "
                f"{len(pendientes)} consulta(s): {', '.join(pendientes) or '(ninguna)'}")

        # --- 2. bajarlas, saltando lo que ya esta ------------------------
        for numero in pendientes:
            if len(av["descargadas"]) >= args.tope:
                break
            if cache.tiene(numero):
                if numero not in av["descargadas"]:
                    av["descargadas"].append(numero)
                    guardar_avance(av)
                continue
            try:
                petete.obtener_consulta(numero, cache, fuente, verboso=False)
                av["descargadas"].append(numero)
                bajadas += 1
                guardar_avance(av)   # tras CADA una: si se corta, no se pierde
                apuntar(f"        + {numero}")
            except petete.FuenteCaida as e:
                apuntar(f"\n[PARADA] la fuente no responde bajando {numero}: {e}")
                av["cortes"].append({"cuando": ahora(), "donde": numero,
                                     "motivo": str(e)})
                guardar_avance(av)
                return _resumen_corte(av, args)
            except petete.FormaInesperada as e:
                apuntar(f"        ! {numero}: forma inesperada, NO se guarda ({e})")
                av["fallidas"][numero] = f"forma inesperada: {e}"
                guardar_avance(av)

    apuntar(f"\nsiembra terminada: {bajadas} nuevas en esta pasada, "
            f"{len(av['descargadas'])} en total")
    guardar_avance(av)
    return modo_informe(args)


def _resumen_corte(av: dict, args) -> int:
    apuntar("")
    apuntar("=" * ANCHO)
    apuntar("  SIEMBRA INTERRUMPIDA — la fuente ha dejado de responder")
    apuntar("=" * ANCHO)
    apuntar(f"  descargadas hasta ahora : {len(av['descargadas'])}")
    apuntar(f"  articulos ya explorados : {len(av['articulos'])}")
    apuntar("")
    apuntar("  No se ha perdido nada: se retoma con  python sembrar.py sembrar")
    apuntar("  y sigue por donde iba, sin volver a bajar lo que ya esta.")
    return 1


# ----------------------------------------------------------------- informe


def modo_informe(args) -> int:
    import fase4
    ix, _g = fase4.cargar_corpus()
    N = ix.normas
    av = leer_avance()
    cache_dgt = DGT.CacheDGT()
    consultas = cache_dgt.todas()

    print()
    print("=" * ANCHO)
    print("  LA DESPENSA DE CRITERIO")
    print("=" * ANCHO)

    crudos = list(petete.DIR_CRUDO.glob("*.html"))
    bytes_crudo = sum(f.stat().st_size for f in crudos)
    bytes_json = sum(f.stat().st_size for f in petete.DIR_CONSULTAS.glob("*.json"))
    print(f"\n  consultas guardadas : {len(consultas)}")
    print(f"  fallidas            : {len(av.get('fallidas', {}))}")
    print(f"  cortes por caida    : {len(av.get('cortes', []))}")
    print(f"  ocupa               : {(bytes_crudo + bytes_json)/1024:.0f} KB "
          f"({bytes_crudo/1024:.0f} crudo + {bytes_json/1024:.0f} campos)")

    # --- pares y formas no reconocidas ---
    pares = car = ext = sin = 0
    avisos = []
    for c in consultas:
        a = DGT.analizar_normativa(c.normativa, N)
        pares += len(a.preceptos)
        car += sum(1 for p in a.preceptos if p.estado == "cargada")
        ext += sum(1 for p in a.preceptos if p.estado == "externa")
        sin += sum(1 for p in a.preceptos if p.estado == "sin_norma")
        for s in a.sin_reconocer:
            avisos.append((c.numero, s))
    print(f"\n  pares (norma, articulo) : {pares}")
    print(f"    a norma CARGADA       : {car}   <- los que pueden dar señal")
    print(f"    de norma externa      : {ext}")
    print(f"    sin norma identificada: {sin}")
    print(f"  avisos de forma no reconocida: {len(avisos)}")
    for numero, s in avisos[:8]:
        print(f"     {numero}: {s[:96]}")

    # --- cobertura por articulo: LO QUE MAS IMPORTA ---
    cobertura: Counter = Counter()
    for c in consultas:
        for p in c.preceptos(N):
            if p.comparable:
                cobertura[(p.cuerpo, p.numero)] += 1

    filas = construir_plan()
    print(f"\n  COBERTURA POR ARTICULO (los de 0 son los temas sin criterio)")
    print(f"  {'norma':5s} {'art':12s} {'consultas':>9s}  tema")
    print("  " + "-" * 62)
    ceros = []
    for f in filas:
        n = cobertura.get((f["cuerpo"], f["articulo"]), 0)
        marca = "" if n else "   <-- SIN CRITERIO"
        if not n:
            ceros.append(f"{f['norma']} {f['articulo']}")
        print(f"  {f['norma']:5s} {f['articulo']:12s} {n:9d}  {f['tema']}{marca}")
    print(f"\n  articulos con criterio : {len(filas) - len(ceros)}/{len(filas)}")
    if ceros:
        print(f"  SIN criterio           : {', '.join(ceros)}")
        print("  En esos temas el agente no podra dar criterio aunque se encienda.")
    return 0


def main(argv: list[str]) -> int:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="modo", required=True)
    for nombre, funcion in (("plan", modo_plan), ("sembrar", modo_sembrar),
                            ("informe", modo_informe)):
        p = sub.add_parser(nombre)
        p.add_argument("--tope", type=int, default=TOPE_POR_DEFECTO)
        p.add_argument("--por-articulo", type=int, default=POR_ARTICULO,
                       dest="por_articulo")
        p.set_defaults(func=funcion)
    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\ninterrumpido: lo descargado esta guardado, se retoma con "
              "'python sembrar.py sembrar'")
        return 130


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
