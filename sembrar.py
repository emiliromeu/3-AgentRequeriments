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

TOPE_POR_DEFECTO = 800
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
# UNA SOLA REPRESENTACION DE LA NORMA, Y SALE DEL CORPUS.
#
# Aqui habia DOS mapas escritos a mano de tres normas cada uno -`NUMERO_NORMA`
# con «LIVA -> 37/1992» y `DESIGNACION` con «LIVA -> Ley 37/1992»- de cuando el
# corpus era solo IVA. Y la fila del plan llevaba una tercera forma, el nombre
# completo. Tres representaciones de lo mismo que habia que mantener en
# paralelo, y se descuadraron: al conectar el plan a `plan_siembra` la fila paso
# a llevar «Ley 37/1992» y `modo_sembrar` seguia buscando «LIVA» en
# `NUMERO_NORMA`. REVENTO A LOS NUEVE SEGUNDOS con un KeyError, sin bajar nada.
#
# Es el mismo patron de los cinco `ix.buscar` sueltos y de las tres copias de la
# regla del ano. Ahora la fila lleva TODO lo que necesitan los tres consumidores
# -clave de cuerpo, etiqueta, numero y articulo- y el numero lo da el corpus,
# que ya lo sabe: hasta los reglamentos, que heredan el del real decreto que los
# aprueba.


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
    # Del corpus, no de un mapa: cada cuerpo sabe como se llama.
    clave_de = {c.clave: c.etiqueta.split(",")[0] for c in N.cuerpos.values()}

    cobertura: Counter = Counter()
    for c in DGT.CacheDGT().todas():
        for p in c.preceptos(N):
            if p.comparable:
                cobertura[(p.cuerpo, p.numero.lower())] += 1

    faltan: Counter = Counter()
    for caso in banco.leer_casos(banco.CASOS):
        # POR LA MISMA PUERTA QUE EL AGENTE: ver `fase4.recuperar`.
        cuerpo_caso, _m = ix.normas.resolver(caso["norma"])
        imp = ix.normas.impuesto_de_cuerpo(cuerpo_caso) if cuerpo_caso else ""
        res, _h, reserva = fase4.recuperar(ix, grafo, caso["consulta"], imp,
                                           tope=5)
        sel = EST.seleccionar_material(ix, caso["consulta"], res, grafo,
                                       reserva=reserva)
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
    """La lista de siembra. LA CALCULA `plan_siembra`, no se escribe aqui.

    Antes se armaba con un mapa de tres normas -Ley del IVA, Reglamento del IVA
    y LGT- de cuando el corpus era solo IVA. El corpus paso a cuatro impuestos
    y la despensa se quedo donde estaba: 241 consultas, TODAS de IVA, y ningun
    aviso lo decia porque nadie medía eso.

    Se intercalan los impuestos en vez de vaciar uno y pasar al siguiente: la
    siembra de la DGT son horas y se puede cortar, y si se corta a mitad lo
    bajado tiene que estar repartido, no todo en IVA otra vez.
    """
    import fase4
    import plan_siembra

    ix, _g = fase4.cargar_corpus()
    N = ix.normas
    por_impuesto = plan_siembra.plan()
    listas = [por_impuesto.get(k) or [] for k in
              ("IVA", "IRPF", "IS", "IP", "GENERAL")]
    largo = max((len(x) for x in listas), default=0)
    filas = []
    for i in range(largo):
        for lista in listas:
            if i >= len(lista):
                continue
            f = lista[i]
            art = _numero_de_articulo(f["referencia"].replace("Articulo ", ""))
            if not art:
                continue          # a PETETE se le busca por numero
            cuerpo = N.por_clave(f["cuerpo_clave"])
            filas.append({
                # La identidad, y con lo que se cruza contra la despensa.
                "cuerpo": f["cuerpo_clave"],
                # Como se enseña.
                "norma": (f["cuerpo"] or "").split(",")[0],
                # Como lo busca PETETE: «37/1992 95».
                "numero": (cuerpo.numero if cuerpo else ""),
                "articulo": art,
                "banco": 1 if "banco" in (f["porque"] or "") else 0,
                "remisiones": f["puntos"],
                "tema": f["rubrica"],
            })
    return filas


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

    # EL TOPE ES DE ESTA TANDA, NO DEL ACUMULADO.
    #
    # Se comparaba contra `len(av["descargadas"])`, que arrastra lo de pasadas
    # anteriores. Con 228 ya descargadas, `--tope 2` paraba ANTES DE BAJAR
    # NADA: «0 nuevas en esta pasada». O sea que la prueba en pequeño -bajar
    # dos de verdad antes de lanzar horas- era imposible por construccion, y
    # ademas `--tope 800` no significaba 800 nuevas sino 800 menos lo que ya
    # hubiera. El TEAC ya lo contaba por tanda; este no.
    ya = len(av["descargadas"])
    nuevas_tanda = 0
    if ya:
        apuntar(f"se retoma: {ya} consultas ya descargadas en pasadas anteriores")

    bajadas = 0
    for n, fila in enumerate(filas, 1):
        etiqueta = f"{fila['norma']} art. {fila['articulo']}"
        if nuevas_tanda >= args.tope:
            apuntar(f"\n[tope] {args.tope} consultas en esta tanda: se para aqui")
            break

        # --- 1. que consultas hay sobre este articulo -------------------
        pendientes = av["articulos"].get(etiqueta, {}).get("numeros")
        if pendientes is None:
            if not fila["numero"]:
                apuntar(f"  [sin numero de norma] {etiqueta}: no se puede "
                        f"buscar en PETETE")
                continue
            consulta = f"{fila['numero']} {fila['articulo']}"
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
            if nuevas_tanda >= args.tope:
                break
            if cache.tiene(numero):
                # Ya estaba en disco de otra pasada: se apunta, pero NO cuenta
                # para el tope de la tanda. El tope mide lo que se le pide a la
                # fuente, que es lo que hay que dosificar.
                if numero not in av["descargadas"]:
                    av["descargadas"].append(numero)
                    guardar_avance(av)
                continue
            try:
                petete.obtener_consulta(numero, cache, fuente, verboso=False)
                av["descargadas"].append(numero)
                nuevas_tanda += 1
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

    nuevas_de_esta = av["descargadas"][ya:]
    apuntar(f"\nsiembra terminada: {bajadas} nuevas en esta pasada, "
            f"{len(av['descargadas'])} en total")
    guardar_avance(av)
    modo_informe(args)
    # LA PUERTA DE LA CADENA. Devuelve 1 si algo de lo bajado AHORA no se
    # puede encontrar, y quien encadena las tandas para ahi.
    return informe_de_tanda(nuevas_de_esta)


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


def alcanzables_de(consultas, N) -> tuple:
    """(alcanzables, total, [inalcanzables]) por (norma, articulo)."""
    malas = [c for c in consultas
             if not [x for x in c.preceptos(N) if getattr(x, "comparable", False)]]
    return len(consultas) - len(malas), len(consultas), malas


def informe_de_tanda(nuevas: list) -> int:
    """Lo bajado EN ESTA TANDA y cuanto de ello se puede encontrar.

    LA PUERTA DE LA CADENA MIDE LA TANDA, NO EL ACUMULADO. Con el acumulado la
    cadena se pararia siempre por los 65 que ya sabemos que no se leen -prosa
    del campo «normativa» de la DGT, diagnosticada y pendiente-, y una puerta
    que salta siempre se acaba ignorando. Lo que hay que cazar es material
    NUEVO que se baje y no se pueda encontrar.

    Devuelve el codigo de salida: 0 si todo lo bajado es alcanzable, 1 si no.
    """
    import fase4
    ix, _g = fase4.cargar_corpus()
    cache = DGT.CacheDGT()
    porn = {c.numero: c for c in cache.todas()}
    de_tanda = [porn[n] for n in nuevas if n in porn]
    if not de_tanda:
        print("\n  TANDA: no se ha bajado nada nuevo.")
        return 0
    alc, tot, malas = alcanzables_de(de_tanda, ix.normas)
    pct = 100 * alc / tot
    print(f"\n  LO BAJADO EN ESTA TANDA: {tot} consultas")
    print(f"  ALCANZABLE por (norma, art.): {alc} de {tot} ({pct:.1f}%)")
    if malas:
        print(f"  [PARADA] {len(malas)} de las bajadas AHORA no se encuentran.")
        print(f"           La cadena se para aqui. Bajar y no poder encontrarlo")
        print(f"           ocupa disco, parece cobertura y no lo es.")
        for c in malas[:6]:
            print(f"             {c.numero}: {(c.normativa or '')[:58]}")
        return 1
    print("  todo lo bajado en esta tanda se puede encontrar.")
    return 0


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
    # CUANTO DE LO BAJADO SE PUEDE ENCONTRAR. Bajar y no poder encontrarlo
    # ocupa disco, parece cobertura y no lo es: 118 criterios del TEAC se
    # sembraron asi y se descubrio tres dias despues, mirando a mano. Desde
    # entonces esta cifra va en el informe de CADA tanda.
    malas = [c for c in consultas
             if not [x for x in c.preceptos(N) if getattr(x, "comparable", False)]]
    pct = 100 * (len(consultas) - len(malas)) / len(consultas) if consultas else 0
    print(f"  ALCANZABLES por (norma, art.): "
          f"{len(consultas) - len(malas)} de {len(consultas)} ({pct:.1f}%)")
    if malas:
        print(f"  [AVISO] {len(malas)} NO se encuentran. La siguiente tanda NO "
              f"sale hasta saber por que:")
        for c in malas[:4]:
            print(f"            {c.numero}: {(c.normativa or '')[:60]}")
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
    print(f"  {'norma':<34s} {'art':12s} {'consultas':>9s}  tema")
    print("  " + "-" * 76)
    ceros = []
    for f in filas:
        n = cobertura.get((f["cuerpo"], f["articulo"].lower()), 0)
        marca = "" if n else "   <-- SIN CRITERIO"
        if not n:
            ceros.append(f"{f['norma']} {f['articulo']}")
        print(f"  {f['norma'][:34]:<34s} {f['articulo']:12s} {n:9d}  "
              f"{f['tema'][:28]}{marca}")
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
