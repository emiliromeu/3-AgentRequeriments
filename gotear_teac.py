#!/usr/bin/env python3
"""EL GOTEO DEL TEAC: cubrir el corpus entero con doctrina, a ratos. Cero API.

    .venv/bin/python gotear_teac.py --minutos 5 --ensayo   <- la prueba, sin red
    .venv/bin/python gotear_teac.py                        <- una sesion de 90 min
    .venv/bin/python gotear_teac.py --estado               <- por donde va

EL GEMELO DE `gotear.py`, Y LE PIDE PRESTADO TODO LO QUE NO ES DEL TEAC: el
orden de utilidad, la memoria de «¿toca pedir esto?», el cerrojo de una sesion a
la vez, la escritura que no deja el cuaderno a medias y el resumen de sesion que
se abre al empezar. Dos copias de un cerrojo son dos cerrojos en cuanto alguien
arregle uno; aqui solo esta lo que de verdad cambia, que es la fuente.

    lo que cambia          DGT                   TEAC
    fuente                 PETETE                DYCTEA
    se busca por           texto libre           CODIGO de norma y precepto
    lo bajado cae en       datos/dgt/consultas   datos/teac/criterios
    cuaderno               datos/dgt/goteo.json  datos/teac/goteo_teac.json

----------------------------------------------------------------------------
LO QUE NO SE PUEDE BUSCAR, Y HAY QUE SABERLO ANTES DE EMPEZAR
----------------------------------------------------------------------------
DYCTEA no se busca por texto: se busca por SU codigo de norma y SU codigo de
precepto, sacados de su catalogo. Lo que su catalogo no lista, no se puede
pedir. Medido el 28/08/2026 sobre los 2.033 articulos del corpus:

    631 buscables  ·  1.402 que DYCTEA no lista

No es un fallo nuestro y no se arregla insistiendo: el Codi tributari catalan,
la Ley 27/2014 del IS, el Reglamento del IS y el texto refundido del ITPAJD no
estan en su catalogo, o estan sin preceptos. Se dicen y se saltan.

----------------------------------------------------------------------------
LA TRAMPA QUE COSTO 195 ARTICULOS, Y POR ESO ESTA ESCRITA AQUI
----------------------------------------------------------------------------
DYCTEA NOMBRA LOS REGLAMENTOS POR SU REAL DECRETO. Al Reglamento del IVA lo
llama «RD 1624/1992 Reglamento Impuesto...», no «Reglamento del Impuesto sobre
el Valor Añadido». `sembrar_teac.plan` lo buscaba por el titulo largo del
cuerpo, no lo encontraba, anotaba «DYCTEA no lista ese precepto» Y LO MARCABA
COMO HECHO.

Resultado, medido sobre `siembra_teac.json`: de 330 articulos «hechos», solo
135 se habian buscado de verdad. Los otros 195 se dieron por hechos sin pedir
nada -los 26 del Reglamento del IVA, los 22 del RIRPF, los 17 del RD 1065/2007,
los 12 del RIS...- y una segunda pasada se los habria vuelto a saltar, porque
la memoria decia que ya estaban.

Es la misma trampa del cuerpo hermano que ya nos costo un diagnostico en el
verificador: una designacion que contiene el nombre de una norma no es esa
norma, y el nombre con el que NOSOTROS llamamos a un cuerpo no es el nombre con
el que lo llama la fuente. Aqui se resuelve probando la DESIGNACION primero
-«RD 1624/1992»- y el titulo despues.

----------------------------------------------------------------------------
Y POR ESO ESTE GOTEO NO SE FIA DE `siembra_teac.json`
----------------------------------------------------------------------------
Empieza con el cuaderno en blanco y usa como señal de «esto ya esta cubierto»
LO QUE HAY EN LA DESPENSA, articulo por articulo. Un registro que marca como
hecho lo que no se hizo no es una memoria: es una manera de no volver a
mirarlo.
"""
import argparse
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import gotear                                     # noqa: E402
import sembrar_teac as ST                         # noqa: E402
import teac as T                                  # noqa: E402
from agente_fiscal import cola as COLA            # noqa: E402
from agente_fiscal import teac as TC              # noqa: E402

AVANCE = TC.DIR_CACHE / "goteo_teac.json"
CERROJO = TC.DIR_CACHE / "goteo_teac.cerrojo"
DESTINO = TC.DIR_CACHE / "criterios"

MINUTOS_POR_DEFECTO = 90

# Cuantas resoluciones se bajan como mucho de un articulo. El mismo motivo que
# en el goteo de la DGT: un articulo con doscientas se llevaria la sesion
# entera y dejaria sin mirar a los demas.
TOPE_POR_ARTICULO = 10

PAUSA_ENSAYO = 0.05


def _codigos_de(cuerpo, cat) -> tuple:
    """(codigo de norma en DYCTEA, sus preceptos). ('', {}) si no lo lista.

    LA DESIGNACION PRIMERO Y EL TITULO DESPUES. Ver la trampa de la cabecera:
    DYCTEA llama a los reglamentos por su real decreto, y buscarlos por su
    titulo largo devuelve vacio sin que nada parezca ir mal.
    """
    tipo = getattr(cuerpo, "tipo", "") or ""
    num = getattr(cuerpo, "numero", "") or ""
    agujas = []
    if num:
        if tipo.startswith("Regl") or tipo.startswith("Real"):
            agujas += [f"RD {num}", f"Real Decreto {num}",
                       f"RDLeg {num}", f"RD-Leg {num}",
                       f"Real Decreto Legislativo {num}"]
        else:
            agujas.append(f"{tipo} {num}")
    etiqueta = (getattr(cuerpo, "etiqueta", "") or "").split(",")[0]
    if etiqueta:
        agujas.append(etiqueta)
    for aguja in agujas:
        cod = ST.codigo_de_norma(cat, aguja)
        preceptos = (cat.get("preceptos") or {}).get(cod) or {}
        if cod and preceptos:
            return cod, preceptos
    return "", {}


def _numero(articulo: str) -> str:
    return str(articulo).replace("Articulo ", "").replace("articulo ", "").strip()


def cola_del_dia(ix, grafo, avance, despensa) -> tuple:
    """(por mirar hoy, [fuera de DYCTEA]). Sin pedir nada a nadie.

    El orden es el de `gotear.orden_de_utilidad`: el mismo del goteo de la DGT,
    y por el mismo motivo -si esto se para para siempre a mitad, lo bajado
    tiene que ser lo util-.
    """
    cat = ST._catalogo()
    N = ix.normas
    # QUE ARTICULOS TIENEN YA DOCTRINA EN LA DESPENSA. Es la señal de «esto ya
    # esta cubierto», y sale del disco y no de ningun registro de lo que
    # creemos haber hecho.
    con = set()
    for c in despensa.todas():
        for p in c.preceptos(N):
            if getattr(p, "comparable", False):
                con.add((p.cuerpo, str(p.numero).lower()))

    codigos = {}
    cola, fuera = [], []
    for cu, ar, por in gotear.orden_de_utilidad(ix, grafo):
        if cu not in codigos:
            codigos[cu] = _codigos_de(N.por_clave(cu), cat)
        cod_norma, preceptos = codigos[cu]
        cod_precepto = preceptos.get(_numero(ar), "") if cod_norma else ""
        if not cod_precepto:
            # DYCTEA NO LO LISTA. No se apunta como hecho: no se ha hecho.
            fuera.append(f"{cu}#{ar.lower()}")
            continue
        clave = f"{cu}#{ar.lower()}"
        if gotear.toca(avance, clave, (cu, ar.lower()) in con):
            cola.append((cu, ar, cod_norma, cod_precepto, por))
    return cola, fuera


def estado() -> int:
    import fase4
    ix, grafo = fase4.cargar_corpus()
    avance = gotear.leer_avance(AVANCE)
    cola, fuera = cola_del_dia(ix, grafo, avance, TC.CacheTEAC())
    total = len(gotear.orden_de_utilidad(ix, grafo))
    print(f"  articulos del corpus            : {total}")
    print(f"  que DYCTEA no lista             : {len(fuera)}")
    print(f"  buscables en DYCTEA             : {total - len(fuera)}")
    print(f"  ya mirados por este goteo       : {len(avance['articulos'])}")
    print(f"  QUEDAN POR MIRAR HOY            : {len(cola)}")
    if avance["sesiones"]:
        sin_terminar = sum(1 for s in avance["sesiones"]
                           if s.get("terminada") is False)
        print(f"\n  sesiones: {len(avance['sesiones'])}"
              + (f"  ({sin_terminar} cortada(s))" if sin_terminar else ""))
        for s in avance["sesiones"][-6:]:
            marca = ("" if s.get("terminada") is not False
                     else "   <- CORTADA, no llego al final")
            print(f"    {s.get('cuando')}  {s.get('minutos')} min  "
                  f"{s.get('articulos')} articulos  "
                  f"{s.get('bajadas')} criterios{marca}")
    return 0


def fuera_del_catalogo() -> int:
    """LOS QUE NO SE PUEDEN BUSCAR, CON SU CAUSA. Sin red y sin pedir nada.

    EXISTE PARA QUE NADIE LOS PERSIGA CREYENDO QUE FALTAN. Cuando el goteo
    termine dira «no queda nada por mirar» con 1.402 articulos del corpus sin
    una sola resolucion al lado, y eso tiene toda la pinta de un trabajo a
    medias. No lo es: es que DYCTEA no se puede buscar por texto -se busca por
    SU codigo de norma y SU codigo de precepto- y lo que su catalogo no lista,
    no se puede pedir. No es un fallo nuestro y no se arregla insistiendo.

    SE CALCULA, NO SE ESCRIBE. Un fichero con la lista se quedaria viejo el dia
    que DYCTEA añada preceptos a su catalogo, y entonces diria que no se puede
    buscar algo que si se puede, que es peor que no decir nada. Esto se lee del
    catalogo de hoy, cada vez.
    """
    import collections
    import fase4
    ix, grafo = fase4.cargar_corpus()
    cat = ST._catalogo()
    N = ix.normas

    SIN_NORMA = "la norma no esta en el catalogo de DYCTEA"
    SIN_PRECEPTOS = "DYCTEA tiene la norma pero no lista ni un precepto suyo"
    SIN_ESE = "DYCTEA lista la norma pero no ESE precepto"

    codigos, causas = {}, collections.Counter()
    por_cuerpo = collections.defaultdict(lambda: collections.Counter())
    for cu, ar, _por in gotear.orden_de_utilidad(ix, grafo):
        cuerpo = N.por_clave(cu)
        if cu not in codigos:
            codigos[cu] = _codigos_de(cuerpo, cat)
        cod, preceptos = codigos[cu]
        etiqueta = (getattr(cuerpo, "etiqueta", "") or cu)
        if not cod:
            motivo = SIN_NORMA
        elif not preceptos:
            motivo = SIN_PRECEPTOS
        elif not preceptos.get(_numero(ar)):
            motivo = SIN_ESE
        else:
            por_cuerpo[etiqueta]["buscables"] += 1
            continue
        causas[motivo] += 1
        por_cuerpo[etiqueta][motivo] += 1

    total = sum(causas.values())
    print(f"\n  ARTICULOS DEL CORPUS QUE NO SE PUEDEN BUSCAR EN DYCTEA: {total}")
    print("  No faltan por hacer: no se pueden pedir.\n")
    for motivo, n in causas.most_common():
        print(f"    {n:>5}  {motivo}")
    print(f"\n  Por cuerpo, lo buscable y lo que no:\n")
    print(f"    {'':46} {'buscables':>9} {'fuera':>7}")
    for et, c in sorted(por_cuerpo.items(),
                        key=lambda x: -(sum(x[1].values()) - x[1]["buscables"])):
        fuera = sum(c.values()) - c["buscables"]
        print(f"    {et[:44]:<46} {c['buscables']:>9} {fuera:>7}")
    print()
    print("  LOS QUE NO ESTAN EN EL CATALOGO son normas enteras: el libro sexto")
    print("  del Codi tributari catalan, la Ley 27/2014 del Impuesto sobre")
    print("  Sociedades, su Reglamento y el texto refundido del ITPAJD. DYCTEA")
    print("  no los tiene, y por ahi no hay doctrina que traer.")
    print()
    print("  LOS QUE SI ESTAN pero sin ese precepto son articulos sueltos: el")
    print("  catalogo de DYCTEA lista los preceptos sobre los que HAY doctrina,")
    print("  asi que un articulo que no aparece es, casi siempre, un articulo")
    print("  sobre el que el TEAC no se ha pronunciado.")
    print()
    return 0


def gotear_teac(minutos: int, ensayo: bool) -> int:
    import fase4
    ix, grafo = fase4.cargar_corpus()
    avance = gotear.leer_avance(AVANCE)
    # DOS CACHES Y NO SON LA MISMA: `T.Cache` es la del descargador -guarda lo
    # que llega- y `TC.CacheTEAC` la de lectura, que sabe que preceptos sostiene
    # cada criterio. Confundirlas es como se pide otra vez lo que ya se tiene.
    cache = T.Cache()
    cola, fuera = cola_del_dia(ix, grafo, avance, TC.CacheTEAC())

    print(f"  buscables en DYCTEA  : "
          f"{len(gotear.orden_de_utilidad(ix, grafo)) - len(fuera)}")
    print(f"  fuera de su catalogo : {len(fuera)}")
    print(f"  por mirar hoy        : {len(cola)}")
    print(f"  sesion de            : {minutos} minutos"
          + ("   (ENSAYO: no se sale a la red)" if ensayo else ""), flush=True)
    if not cola:
        print("\n  No queda nada por mirar. La doctrina esta al dia.")
        return 0

    fin = time.monotonic() + minutos * 60
    fuente = None if ensayo else T.Fuente(silencioso=True)
    if not ensayo:
        DESTINO.mkdir(parents=True, exist_ok=True)
    hechos = bajadas = vacios = 0
    corte = ""

    # EL RESUMEN SE ABRE AHORA, igual que en el goteo de la DGT y por lo mismo:
    # una sesion cortada tiene que dejar rastro. Ver `gotear.gotear`.
    sesion = None
    if not ensayo:
        sesion = {"cuando": gotear._hoy(), "empezada": gotear._ahora(),
                  "minutos": minutos, "articulos": 0, "bajadas": 0,
                  "vacios": 0, "corte": "", "terminada": False,
                  "ensayo": False, "por_mirar_al_empezar": len(cola)}
        avance["sesiones"].append(sesion)
        gotear.guardar_avance(avance, AVANCE)

    for cu, ar, cod_norma, cod_precepto, _por in cola:
        # EL TIEMPO SE MIRA ANTES DE EMPEZAR, nunca en mitad de un articulo.
        if time.monotonic() >= fin:
            corte = "se acabo el tiempo de la sesion"
            break
        clave = f"{cu}#{ar.lower()}"
        if ensayo:
            hechos += 1
            time.sleep(PAUSA_ENSAYO)
            continue
        try:
            filas = T.extraer_resultados(fuente.buscar(cod_norma, cod_precepto))
        except (T.FuenteCaida, T.FormaInesperada) as exc:
            # LA FUENTE SE CAE Y SE PARA. Los reintentos con tope ya los hace
            # `T.Fuente`; insistir aqui seria insistir en la puerta.
            corte = f"{type(exc).__name__}: {str(exc)[:90]}"
            break

        # PRIMERO LO QUE VINCULA. `prioridad` ya ordena doctrina y unificacion
        # de criterio por delante: si el tope corta, corta por lo de menos peso.
        filas.sort(key=ST.prioridad)
        nuevas = 0
        for f in filas[:TOPE_POR_ARTICULO]:
            ident = f.get("id")
            if not ident or cache.tiene(ident):
                continue
            try:
                _reg, origen = T.obtener_criterio(ident, cache, fuente,
                                                  verboso=False)
            except (T.FuenteCaida,) as exc:
                corte = f"FuenteCaida: {str(exc)[:90]}"
                break
            except Exception:                     # noqa: BLE001
                continue
            if origen == "red":
                nuevas += 1
        avance["articulos"][clave] = {
            "estado": COLA.BAJADA if nuevas else COLA.SIN_RESULTADOS,
            "buscado": gotear._hoy(), "bajadas": nuevas}
        hechos += 1
        bajadas += nuevas
        if not nuevas:
            vacios += 1
        if corte:
            break
        if hechos % 10 == 0:
            if sesion is not None:
                sesion.update({"articulos": hechos, "bajadas": bajadas,
                               "vacios": vacios})
            gotear.guardar_avance(avance, AVANCE)
            # CON `flush`: redirigido a fichero, el log se queda vacio media
            # hora y desde fuera no se distingue de un proceso colgado.
            print(f"    {hechos} articulos · {bajadas} criterios · "
                  f"{(fin - time.monotonic())/60:.0f} min restantes", flush=True)

    if ensayo:
        print(f"\n  articulos recorridos : {hechos}")
        print(f"  {corte or 'terminado: se recorrio todo'}")
        print("\n  ENSAYO: no se ha pedido nada ni se ha apuntado nada.")
        return 0

    if sesion is not None:
        sesion.update({"articulos": hechos, "bajadas": bajadas,
                       "vacios": vacios, "corte": corte, "terminada": True,
                       "acabada": gotear._ahora()})
    gotear.guardar_avance(avance, AVANCE)
    print(f"\n  articulos mirados : {hechos}")
    print(f"  criterios nuevos  : {bajadas}")
    print(f"  sin nada          : {vacios}")
    print(f"  {corte or 'terminado: no quedaba nada por mirar'}")
    print(f"\n  quedan por mirar  : {len(cola) - hechos}")
    if bajadas:
        print(f"\n  Lo bajado esta en {DESTINO} y VIAJA POR GIT.")
        print(f"  git add datos/teac/criterios && git commit && git push")
    return 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--minutos", type=int, default=MINUTOS_POR_DEFECTO)
    ap.add_argument("--ensayo", action="store_true",
                    help="no sale a la red: recorre y no apunta nada")
    ap.add_argument("--estado", action="store_true",
                    help="por donde va, sin pedir nada")
    ap.add_argument("--fuera", action="store_true",
                    help="los articulos que DYCTEA no deja buscar, con su causa")
    args = ap.parse_args(argv)

    # EL MISMO CERROJO, con su fichero. `--estado` no lo coge: solo mira.
    try:
        if args.fuera:
            return fuera_del_catalogo()
        if args.estado:
            return estado()
        with gotear.cerrojo(CERROJO):
            return gotear_teac(args.minutos, args.ensayo)
    except gotear.Ocupado as e:
        print(f"\n  {e}\n")
        return 1
    except gotear.AvanceIlegible as e:
        print(f"\n  {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
