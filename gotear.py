#!/usr/bin/env python3
"""EL GOTEO: cubrir el corpus entero, a ratos, DESDE MI MAC. Cero API.

    .venv/bin/python gotear.py --minutos 5 --ensayo   <- la prueba, NO sale a la red
    .venv/bin/python gotear.py                        <- una sesion de 90 minutos
    .venv/bin/python gotear.py --estado               <- por donde va, sin pedir nada

POR QUE AQUI Y NO EN LA OFICINA. Lo que baja el goteo VIAJA POR GIT, igual que
la siembra por plan: son consultas publicas de la DGT, no dicen nada de ningun
cliente y cuestan horas contra un servicio publico. Bajarlo una vez y repartirlo
es una peticion; que lo baje cada equipo son seis, y seis despensas distintas.

    EN LA OFICINA EL GOTEO NO CORRE. Alli solo la cola por demanda, que baja lo
    que se pregunta y NO viaja -sus fechas dirian que pregunto un cliente y
    cuando-. Ver `cola.py`.

----------------------------------------------------------------------------
EL LIMITE ES DE TIEMPO, NO DE NUMERO, Y NO ES UN DETALLE
----------------------------------------------------------------------------
Un articulo sin consultas se resuelve en una peticion -unos diez segundos- y uno
con cinco necesita seis, o sea un minuto largo. Con un tope por numero, dos
sesiones de «cincuenta articulos» pueden durar diez minutos o una hora, y
entonces no se puede decir cuando termina ni encajarlo en un hueco.

Con tope de tiempo, una sesion dura lo que dice. Lo que varia es cuanto avanza,
que es lo que se puede mirar despues.

EL TIEMPO SE COMPRUEBA ANTES DE EMPEZAR CADA ARTICULO, no en mitad. Cortar a la
mitad de un articulo dejaria sus consultas a medias y habria que decidir si eso
cuenta como buscado. Se termina el que se ha empezado y se para.

----------------------------------------------------------------------------
EL ORDEN: POR UTILIDAD, Y TODO EL CORPUS
----------------------------------------------------------------------------
Sin excluir nada -esa es la diferencia con `plan_siembra`, que corta por debajo
de dos remisiones entrantes-. Pero el orden importa, porque una sesion no llega
a todo: primero lo que el banco manda al redactor, luego lo que mas remisiones
recibe, y el resto detras. Si el goteo se para para siempre a mitad, lo que
habra bajado es lo util.

----------------------------------------------------------------------------
LA MEMORIA ES LA QUE YA HAY
----------------------------------------------------------------------------
Los plazos y la regla de «¿toca pedir esto?» salen de `cola.py` y no se copian
aqui: 90 dias para reintentar un articulo que salio vacio, 180 para refrescar
uno que ya tiene criterio. Dos copias de una regla son dos reglas en cuanto
alguien cambie una.

Lo que si es propio es el fichero de avance -`datos/dgt/goteo.json`-: la cola es
la lista de promesas hechas a alguien del departamento y el goteo es un barrido
nuestro. Mezclarlos haria que un barrido disparase el aviso de «la cola no da
abasto», que habla de otra cosa.
"""
import argparse
import contextlib
import json
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import petete                                    # noqa: E402
from agente_fiscal import cola as COLA           # noqa: E402
from agente_fiscal import dgt as D               # noqa: E402

AVANCE = RAIZ / "datos" / "dgt" / "goteo.json"
# EL CERROJO, AL LADO DEL AVANCE QUE PROTEGE. No viaja por git: dice que hay un
# proceso corriendo EN ESTA maquina, y en otra seria mentira desde el primer
# momento.
CERROJO = RAIZ / "datos" / "dgt" / "goteo.cerrojo"
# CAE EN `consultas/`, CON LA SIEMBRA POR PLAN, y no en `demanda/`: es lo mismo
# que aquella -un barrido nuestro, sin nada de ningun cliente- y por eso viaja.
DESTINO = RAIZ / "datos" / "dgt" / "consultas"

# MINUTOS POR SESION.
#
# 90. El razonamiento, porque no hay nada que medir aqui -es una decision sobre
# cuanto quiero tener el Mac ocupado-:
#
#   · a ~10 s por peticion son unas 540 peticiones, que a una peticion por
#     articulo vacio y unas 3,4 de media en los que traen algo son entre 160 y
#     500 articulos por sesion;
#   · es un hueco real: se lanza al ir a comer o al acabar el dia y ha terminado
#     cuando vuelvo, sin dejar el portatil toda la noche;
#   · y son 6 peticiones por minuto sostenidas hora y media, que para un
#     servicio publico es un goteo de verdad y no una descarga.
#
# Si se quisiera ir mas deprisa, lo que se sube es el numero de SESIONES, no el
# ritmo: la pausa de 10 s no se toca.
MINUTOS_POR_DEFECTO = 90
TOPE_CONSULTAS_POR_ARTICULO = 5   # el mismo que usa la cola

# Lo que «tarda» un articulo en el ensayo. No imita a la fuente -no se puede
# saber cuantas consultas trae cada uno sin preguntar- pero hace que el corte
# por tiempo se ejecute de verdad, que es lo que el ensayo tiene que probar.
PAUSA_ENSAYO = 0.05


def _hoy() -> str:
    return date.today().isoformat()


def _ahora() -> str:
    """Con la hora. `_hoy` da el dia, y dos sesiones del mismo dia se
    distinguen por la hora o no se distinguen."""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


class AvanceIlegible(Exception):
    """`goteo.json` esta ahi y no se puede leer. NO se empieza de cero."""


def leer_avance(ruta: Path | None = None) -> dict:
    """El avance del barrido. Un fichero AUSENTE es empezar; uno ROTO, no.

    LA DIFERENCIA ENTRE LAS DOS COSAS ES ONCE SESIONES DE TRABAJO. Esto se
    tragaba el `JSONDecodeError` y devolvia el diccionario vacio, o sea que un
    `goteo.json` a medias -y se escribia de una pasada, asi que un Ctrl+C en el
    momento justo lo dejaba a medias- se leia como «no se ha mirado nada
    todavia». Sin un aviso. La sesion siguiente volvia a recorrer el corpus
    entero y a pedirle a PETETE lo que ya teniamos: dieciseis horas de barrido
    contra un servicio publico, otra vez, y nadie con motivo para sospechar.

    Que no exista SI es empezar, y eso se mantiene: es el primer arranque.
    """
    ruta = Path(ruta or AVANCE)
    if not ruta.is_file():
        return {"creado": _hoy(), "articulos": {}, "sesiones": []}
    try:
        d = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise AvanceIlegible(
            f"{ruta.relative_to(RAIZ)} existe y no se puede leer: {e}\n"
            f"\n"
            f"  LO BAJADO NO SE PIERDE: esta en {DESTINO.relative_to(RAIZ)} y\n"
            f"  viaja por git. Lo que se ha roto es el cuaderno de por donde\n"
            f"  iba el barrido, que NO viaja -es de este Mac- asi que no hay\n"
            f"  ninguna copia de la que sacarlo.\n"
            f"\n"
            f"  Aqui no se sigue solo. Empezar de cero es una decision que\n"
            f"  cuesta horas de peticiones a PETETE para volver a bajar lo que\n"
            f"  ya esta, y sobre todo para volver a preguntar por los\n"
            f"  articulos que salieron vacios, que en disco no dejan rastro.\n"
            f"  Si aun asi es lo que toca, se aparta el fichero a mano:\n"
            f"      mv {ruta.relative_to(RAIZ)} "
            f"{ruta.relative_to(RAIZ)}.roto") from e
    d.setdefault("articulos", {})
    d.setdefault("sesiones", [])
    return d


def guardar_avance(d: dict, ruta: Path | None = None) -> None:
    """Al lado y renombrando, NUNCA encima. Un renombrado no deja a medias.

    `write_text` sobre el fichero bueno lo trunca antes de escribir: durante
    esas milesimas el avance de once sesiones esta en el disco a medio poner, y
    ahi es donde entra el Ctrl+C. Escribir al lado y renombrar hace que el
    fichero bueno sea siempre uno entero: el de antes o el de ahora.
    """
    ruta = Path(ruta or AVANCE)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    provisional = ruta.with_suffix(".json.escribiendo")
    provisional.write_text(json.dumps(d, ensure_ascii=False, indent=1),
                           encoding="utf-8")
    os.replace(provisional, ruta)


# --------------------------------------------------------------- EL CERROJO


class Ocupado(Exception):
    """Ya hay una sesion de goteo corriendo."""


@contextlib.contextmanager
def cerrojo(ruta: Path | None = None):
    """UNA SESION A LA VEZ. Se suelta al salir, pase lo que pase.

    QUE PASA HOY SIN ESTO. Dos sesiones a la vez -y es facil: la ventana de la
    izquierda lleva una hora y uno se olvida y lanza otra- leen las dos el
    mismo `goteo.json`, recorren la misma cola por utilidad, le piden a PETETE
    los mismos articulos, y al guardar GANA LA ULTIMA. El trabajo de la otra no
    queda en ninguna parte: no es que se apunte mal, es que no se apunta. Y por
    el camino se le piden a un servicio publico el doble de peticiones para
    bajar exactamente lo mismo.

    EL CERROJO CADUCA CON EL PROCESO, NO CON EL RELOJ. Un fichero con una hora
    dentro obliga a inventar un plazo -«si lleva mas de dos horas, se ignora»-
    y ese plazo o corta sesiones vivas o deja el cerrojo puesto para siempre
    cuando el portatil se apaga. Se guarda el PID y se pregunta al sistema si
    ese proceso sigue vivo, que no es un plazo: es la respuesta.
    """
    ruta = Path(ruta or CERROJO)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    quien = {"pid": os.getpid(), "desde": time.strftime("%Y-%m-%d %H:%M:%S")}
    try:
        descriptor = os.open(ruta, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        anterior = _quien_lo_tiene(ruta)
        if anterior is not None:
            raise Ocupado(
                f"Ya hay una sesion de goteo corriendo (pid {anterior['pid']}, "
                f"desde las {anterior['desde']}).\n"
                f"  Dos a la vez le piden a PETETE lo mismo dos veces y la "
                f"segunda en guardar\n"
                f"  se lleva por delante el avance de la primera. Espera a que "
                f"termine, o\n"
                f"  paralas las dos y vuelve a lanzar una.") from None
        # EL CERROJO DE UN MUERTO NO ES UN CERROJO. Se dice y se sigue: es lo
        # que queda cuando se cierra el portatil a mitad de sesion, y hacer
        # volver a alguien a borrar un fichero a mano por eso es garantizar que
        # el dia que estorbe se borre sin mirar.
        print("  (habia un cerrojo de una sesion que ya no existe: se retira)")
        ruta.unlink(missing_ok=True)
        descriptor = os.open(ruta, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(descriptor, json.dumps(quien).encode("utf-8"))
        os.close(descriptor)
        yield
    finally:
        # SE SUELTA PASE LO QUE PASE, tambien si la sesion revienta: un cerrojo
        # que solo se quita cuando todo va bien es el que se queda puesto.
        ruta.unlink(missing_ok=True)


def _quien_lo_tiene(ruta: Path | None = None):
    """El dueño del cerrojo si sigue vivo, `None` si es de un proceso muerto."""
    ruta = Path(ruta or CERROJO)
    try:
        quien = json.loads(ruta.read_text(encoding="utf-8"))
        pid = int(quien["pid"])
    except (OSError, ValueError, KeyError, TypeError):
        # Un cerrojo ilegible no bloquea: no sabe decir de quien es, asi que no
        # puede sostener que haya alguien.
        return None
    try:
        os.kill(pid, 0)          # no manda ninguna señal: solo pregunta
    except ProcessLookupError:
        return None
    except PermissionError:
        pass                     # existe y es de otro usuario: existe
    return quien


def orden_de_utilidad(ix, grafo) -> list:
    """Todo el corpus, lo mas util primero. -> [(clave_cuerpo, articulo, por que)]

    La puntuacion es la de `plan_siembra` -banco por doce, mas remisiones
    entrantes- pero SIN SU CORTE: aqui entra todo, y lo que la puntuacion decide
    es el orden, no quien entra.
    """
    # LA MISMA CUENTA QUE EL PLAN, y sin respaldo: si `puntos_del_banco`
    # fallara, esto revienta en vez de seguir con el orden a medias. Un guion
    # que sigue con la mitad de la señal describe otra cosa.
    import plan_siembra
    del_banco = plan_siembra.puntos_del_banco(ix, grafo)
    entrantes = {d.clave: len(grafo.le_mencionan(d.clave)) for d in ix.docs}

    filas = []
    for doc in ix.docs:
        r = doc.registro
        if r.get("tipo") != "articulo":
            continue
        num = str(r.get("numero_norm") or r.get("numero") or "").strip()
        if not num or not num[0].isdigit():
            continue
        cuerpo = r.get("cuerpo_clave", "")
        if not cuerpo:
            continue
        b = del_banco.get(doc.clave, 0)
        e = entrantes.get(doc.clave, 0)
        filas.append((b * plan_siembra.PESO_BANCO + e, cuerpo, num, b, e))
    filas.sort(key=lambda f: (-f[0], f[1], f[2]))
    return [(c, n, f"banco {b} · remisiones {e}") for _p, c, n, b, e in filas]


def toca(avance: dict, clave: str, con_criterio: bool) -> bool:
    """¿Toca pedir este articulo hoy? LA REGLA ES LA DE `cola.py`.

    Se le da forma de entrada de cola y se le pregunta a ella, en vez de repetir
    aqui los plazos. Si manana cambian los 90 o los 180 dias, cambian en los dos
    sitios porque solo hay uno.
    """
    e = avance["articulos"].get(clave)
    if e is None:
        return True
    fingida = {
        "estado": e.get("estado", COLA.PENDIENTE),
        "buscado": e.get("buscado", ""),
        "primera_vez": e.get("buscado", ""),
    }
    if con_criterio and fingida["estado"] == COLA.SIN_RESULTADOS:
        # Tiene criterio por otra via -la cola, otra siembra-: ya no es un
        # vacio que reintentar, es uno que refrescar.
        fingida["estado"] = COLA.BAJADA
    return COLA._toca_reintentar(fingida)


def estado() -> int:
    """Por donde va, sin pedir nada a nadie."""
    import fase4
    ix, grafo = fase4.cargar_corpus()
    avance = leer_avance()
    todos = orden_de_utilidad(ix, grafo)
    con = {(p.cuerpo, p.numero.lower())
           for c in D.CacheDGT().todas()
           for p in c.preceptos(ix.normas) if p.comparable}
    hechos = sum(1 for cu, ar, _ in todos
                 if not toca(avance, f"{cu}#{ar.lower()}",
                             (cu, ar.lower()) in con))
    print(f"  articulos del corpus            : {len(todos)}")
    print(f"  con criterio en la despensa     : "
          f"{sum(1 for cu, ar, _ in todos if (cu, ar.lower()) in con)}")
    print(f"  ya mirados por el goteo         : {len(avance['articulos'])}")
    print(f"  al dia (no toca pedirlos hoy)   : {hechos}")
    print(f"  QUEDAN POR MIRAR                : {len(todos) - hechos}")
    if avance["sesiones"]:
        # LAS CORTADAS SE VEN, Y SE VEN MARCADAS. Es para lo que se abre la
        # fila al empezar: una sesion que no llego al final tiene que salir
        # aqui, con lo que alcanzo a hacer, y no desaparecer de la lista.
        sin_terminar = sum(1 for s in avance["sesiones"]
                           if s.get("terminada") is False)
        print(f"\n  sesiones: {len(avance['sesiones'])}"
              + (f"  ({sin_terminar} cortada(s) sin terminar)"
                 if sin_terminar else ""))
        for s in avance["sesiones"][-6:]:
            # `terminada` no existe en las filas anteriores a este cambio: esas
            # no se marcan de ninguna forma, porque no se sabe.
            marca = ("" if s.get("terminada") is not False
                     else "   <- CORTADA, no llego al final")
            print(f"    {s.get('cuando')}  {s.get('minutos')} min  "
                  f"{s.get('articulos')} articulos  "
                  f"{s.get('bajadas')} consultas{marca}")
    return 0


def gotear(minutos: int, ensayo: bool) -> int:
    import fase4
    ix, grafo = fase4.cargar_corpus()
    avance = leer_avance()
    todos = orden_de_utilidad(ix, grafo)
    con = {(p.cuerpo, p.numero.lower())
           for c in D.CacheDGT().todas()
           for p in c.preceptos(ix.normas) if p.comparable}
    N = ix.normas

    cola_hoy = [(cu, ar, por) for cu, ar, por in todos
                if toca(avance, f"{cu}#{ar.lower()}", (cu, ar.lower()) in con)]
    print(f"  articulos del corpus : {len(todos)}")
    print(f"  por mirar hoy        : {len(cola_hoy)}")
    print(f"  sesion de            : {minutos} minutos"
          + ("   (ENSAYO: no se sale a la red)" if ensayo else ""), flush=True)
    if not cola_hoy:
        print("\n  No queda nada por mirar. El corpus esta al dia.")
        return 0

    fin = time.monotonic() + minutos * 60
    fuente = None if ensayo else petete.Fuente(silencioso=True)
    cache = None if ensayo else petete.Cache()
    if not ensayo:
        DESTINO.mkdir(parents=True, exist_ok=True)
    hechos = bajadas = vacios = 0
    corte = ""

    # EL RESUMEN SE ABRE AHORA, NO AL TERMINAR.
    #
    # Se escribia al final, asi que UNA SESION CORTADA NO DEJABA RASTRO: se
    # apuntaba lo que habia bajado -eso se guarda cada diez articulos- pero en
    # `sesiones` no aparecia nada. Y de las trece del goteo de la DGT, dos se
    # cortaron. Mirando la lista despues, esas dos horas no habian existido:
    # ni cuando fue, ni cuanto duro, ni por donde se quedo.
    #
    # Es el mismo fallo que el cuaderno que se leia como vacio, y duele por lo
    # mismo: lo que no deja rastro no se puede diagnosticar. Con ocho sesiones
    # de TEAC por delante, hace falta ANTES y no despues.
    #
    # LA FILA ES LA MISMA DE PRINCIPIO A FIN: se abre aqui con `terminada` en
    # falso, se va actualizando en el sitio con cada guardado periodico -asi
    # las cifras de una sesion cortada son las de verdad, no ceros- y al
    # terminar se cierra. No se añade una segunda: dos filas por sesion serian
    # dos sesiones en cuanto alguien las contara.
    sesion = None
    if not ensayo:
        sesion = {"cuando": _hoy(), "empezada": _ahora(), "minutos": minutos,
                  "articulos": 0, "bajadas": 0, "vacios": 0,
                  "corte": "", "terminada": False, "ensayo": False,
                  "por_mirar_al_empezar": len(cola_hoy)}
        avance["sesiones"].append(sesion)
        guardar_avance(avance)

    for cu, ar, por in cola_hoy:
        # EL TIEMPO SE MIRA ANTES DE EMPEZAR, nunca en mitad de un articulo.
        if time.monotonic() >= fin:
            corte = "se acabo el tiempo de la sesion"
            break
        clave = f"{cu}#{ar.lower()}"
        cuerpo = N.por_clave(cu)
        if cuerpo is None or not getattr(cuerpo, "numero", ""):
            avance["articulos"][clave] = {"estado": COLA.SIN_RESULTADOS,
                                          "buscado": _hoy(), "bajadas": 0}
            continue
        if ensayo:
            # EL ENSAYO NO APUNTA NADA, y esto se aprendio en la primera
            # pasada: escribio los 2.033 articulos como «buscados» y la sesion
            # de verdad se los habria saltado todos. Una prueba que deja el
            # sistema creyendo que el trabajo esta hecho es peor que no probar.
            #
            # Y SI DUERME, para que el corte por tiempo se pruebe de verdad.
            # Sin pausa, `--minutos 1 --ensayo` recorria el corpus entero en un
            # segundo y decia «terminado»: probaba el recorrido y no el limite,
            # que es la pieza nueva.
            hechos += 1
            time.sleep(PAUSA_ENSAYO)
            continue
        try:
            campos = fuente._campos("", "", petete.TAB_VINCULANTES, 1)
            campos = [(k, f"{cuerpo.numero} {ar}" if k == "VLCMP_3" else v)
                      for k, v in campos]
            crudo = fuente.pedir("/do/search", campos).cuerpo
            resultados = petete.extraer_resultados(crudo)
        except (petete.FuenteCaida, petete.FormaInesperada) as exc:
            # LA FUENTE SE CAE Y SE PARA. Los reintentos con tope ya los hace
            # `petete.Fuente`; insistir aqui seria insistir en la puerta.
            corte = f"{type(exc).__name__}: {str(exc)[:90]}"
            break

        numeros = [r["numero"] for r in resultados if r["numero"]
                   ][:TOPE_CONSULTAS_POR_ARTICULO]
        nuevas = 0
        for numero in numeros:
            if cache.tiene(numero) or (DESTINO / f"{numero}.json").is_file():
                continue
            time.sleep(petete.PAUSA)
            try:
                datos, _o = petete.obtener_consulta(numero, cache, fuente,
                                                    verboso=False)
            except Exception:                    # noqa: BLE001
                continue
            if datos:
                (DESTINO / f"{numero}.json").write_text(
                    json.dumps(datos, ensure_ascii=False, indent=1),
                    encoding="utf-8")
                nuevas += 1
        avance["articulos"][clave] = {
            "estado": COLA.BAJADA if numeros else COLA.SIN_RESULTADOS,
            "buscado": _hoy(), "bajadas": nuevas}
        hechos += 1
        bajadas += nuevas
        if not numeros:
            vacios += 1
        if hechos % 10 == 0:
            # LA FILA DE LA SESION, AL DIA EN CADA GUARDADO. Sin esto, una
            # sesion cortada dejaria su fila con ceros, que es peor que no
            # dejarla: parecerian noventa minutos sin hacer nada.
            if sesion is not None:
                sesion.update({"articulos": hechos, "bajadas": bajadas,
                               "vacios": vacios})
            guardar_avance(avance)        # RETOMABLE: si se corta, no se pierde
            # CON `flush`, Y NO ES UN DETALLE EN UNA SESION DE 90 MINUTOS.
            # Redirigido a fichero, Python guarda la salida en un buffer de
            # varios KB: el log se queda VACIO media hora y desde fuera no se
            # distingue de un proceso colgado. Lo unico que decia que iba bien
            # era contar ficheros en `consultas/`.
            print(f"    {hechos} articulos · {bajadas} consultas · "
                  f"{(fin - time.monotonic())/60:.0f} min restantes",
                  flush=True)
        time.sleep(petete.PAUSA)

    if ensayo:
        print(f"\n  articulos recorridos : {hechos}")
        print(f"  {corte or 'terminado: se recorrio todo'}")
        print("\n  ENSAYO: no se ha pedido nada ni se ha apuntado nada. El")
        print("  avance queda intacto para la sesion de verdad.")
        return 0

    # SE CIERRA LA QUE SE ABRIO, en el sitio. `terminada` es lo que distingue
    # una sesion que llego al final de una que se corto: sin ese campo habria
    # que adivinarlo por las cifras, y una sesion corta de verdad -«no quedaba
    # nada por mirar»- se parece a una cortada.
    if sesion is not None:
        sesion.update({"articulos": hechos, "bajadas": bajadas,
                       "vacios": vacios, "corte": corte, "terminada": True,
                       "acabada": _ahora()})
    guardar_avance(avance)
    print(f"\n  articulos mirados : {hechos}")
    print(f"  consultas nuevas  : {bajadas}")
    print(f"  sin nada          : {vacios}")
    print(f"  {corte or 'terminado: no quedaba nada por mirar'}")
    print(f"\n  quedan por mirar  : {len(cola_hoy) - hechos}")
    if not ensayo and bajadas:
        print(f"\n  Lo bajado esta en {DESTINO} y VIAJA POR GIT.")
        print(f"  git add datos/dgt/consultas && git commit && git push")
    return 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--minutos", type=int, default=MINUTOS_POR_DEFECTO)
    ap.add_argument("--ensayo", action="store_true",
                    help="no sale a la red: recorre y apunta. Para probar el "
                         "camino antes de lanzarlo de verdad.")
    ap.add_argument("--estado", action="store_true",
                    help="por donde va, sin pedir nada")
    args = ap.parse_args(argv)
    # EL ESTADO NO COGE EL CERROJO: solo mira, y tener que esperar a que
    # termine una sesion de noventa minutos para poder preguntar por donde va
    # es justo lo contrario de para lo que sirve.
    try:
        if args.estado:
            return estado()
        with cerrojo():
            return gotear(args.minutos, args.ensayo)
    except Ocupado as e:
        print(f"\n  {e}\n")
        return 1
    except AvanceIlegible as e:
        print(f"\n  {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
