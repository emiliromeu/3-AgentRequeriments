"""LA COLA DE DESCARGA POR DEMANDA. Cero llamadas a la API de Anthropic.

El plan de siembra esta AGOTADO: se bajo todo lo que habia para los 630
articulos planeados, y el corpus tiene 2.043. Ampliar el plan seria sembrar a
ciegas articulos que nadie pregunta.

La cola es lo que hace que la despensa crezca con lo que SI se pregunta, y que
crecer no dependa de que alguien lance la siembra desde fuera.

----------------------------------------------------------------------------
LO QUE SE APUNTA, Y LO QUE NO
----------------------------------------------------------------------------
La clave es `(cuerpo, articulo)`. NO la pregunta, y esto es deliberado:

  · es lo que PETETE sabe buscar -«37/1992 95»-, igual que la siembra;
  · NO LLEVA NADA DEL CLIENTE. Un numero de articulo no dice quien pregunto ni
    que. Las trazas -que si lo dicen- viven en otro sitio y no salen del
    despacho;
  · y hace la deduplicacion trivial: dos personas preguntando lo mismo son una
    sola entrada con `veces` a 2.

----------------------------------------------------------------------------
LOS TRES DUPLICADOS, QUE NO SON EL MISMO
----------------------------------------------------------------------------
  1. dos preguntas, mismo articulo      -> una entrada, `veces += 1`
  2. ya esta en la despensa             -> no se apunta, y se mira otra vez al
                                           bajar por si entro mientras tanto
  3. YA SE BUSCO Y NO HABIA             -> el caro, y el que muerde

El tercero es el que hay que recordar. Medido en la siembra: 53 de 630
articulos NO TIENEN ninguna consulta en PETETE. Sin memoria, la cola los pediria
cada vez, para siempre, contra un servicio publico.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
COLA = RAIZ / "datos" / "dgt" / "cola.json"

# DONDE CAE LO QUE BAJA LA COLA, Y POR QUE EN OTRA CARPETA.
#
# `consultas/` esta sembrado POR PLAN: refleja lo que decidimos sembrar y no
# dice nada de ningun cliente, asi que viaja por git -son horas contra un
# servicio publico y no tiene sentido repetirlas en cada equipo-.
#
# `demanda/` lo llena lo que PREGUNTA el departamento. El contenido de una
# consulta de la DGT es publico y no lleva datos de nadie, pero EL CONJUNTO Y
# LAS FECHAS si: un commit del martes con tres consultas sobre reduccion de
# empresa familiar dice que ese martes un cliente pregunto por una sucesion de
# empresa familiar. Git guarda eso para siempre.
#
# Asi que no viaja, por el mismo criterio que ya separa el corpus y las trazas:
# VIAJA LO CARO QUE NO DICE NADA DE NADIE; NO VIAJA LO BARATO QUE SI LO DICE.
# La siembra por plan son horas; la demanda son una o dos consultas, no hay
# nada que ahorrar compartiendolas.
DEMANDA = RAIZ / "datos" / "dgt" / "demanda"

# CUANTO SE TARDA EN VOLVER A PEDIR UN ARTICULO QUE NO TENIA CRITERIO.
#
# 90 dias, y el numero es una DECISION, no una medida: no hay datos todavia
# para medirlo, porque haria falta una serie de articulos que estuvieran vacios
# y dejaran de estarlo, y la cola es de hoy.
#
# El razonamiento: PETETE publica cada semana, asi que un articulo sin criterio
# hoy puede tenerlo dentro de unos meses; pero preguntarlo mas a menudo es
# gastar peticiones en algo que casi nunca cambia. Tres meses deja cuatro
# intentos al año por articulo, que para 53 articulos vacios son 212 peticiones
# anuales: calderilla para la fuente y suficiente para no perderse una novedad
# mas de un trimestre.
#
# SE PUEDE MEDIR CUANDO HAYA DATOS: si al reintentar a los 90 dias casi ninguno
# ha cambiado, el numero se sube; si cambian muchos, se baja. Lo que dira si
# acertamos es la proporcion de reintentos que traen algo, y eso solo se sabe
# despues de dos o tres vueltas.
DIAS_REINTENTO = 90

# Cuantos dias sin poder bajar nada antes de decirlo en la ventana. Una cola
# desatendida que falla en silencio es peor que no tenerla: parece que crece y
# no crece.
DIAS_SIN_BAJAR_AVISO = 5

PENDIENTE = "pendiente"
SIN_RESULTADOS = "sin_resultados"   # se busco y la fuente no tiene nada
BAJADA = "bajada"


def _hoy() -> str:
    return date.today().isoformat()


def leer() -> dict:
    if not COLA.is_file():
        return {"creada": _hoy(), "entradas": {}, "ultima_bajada": "",
                "ultimo_intento": ""}
    try:
        d = json.loads(COLA.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # UNA COLA ILEGIBLE NO PARA NADA. Se empieza de cero: lo que se pierde
        # son apuntes que se volveran a hacer en la siguiente consulta.
        return {"creada": _hoy(), "entradas": {}, "ultima_bajada": "",
                "ultimo_intento": ""}
    d.setdefault("entradas", {})
    return d


def guardar(d: dict) -> None:
    COLA.parent.mkdir(parents=True, exist_ok=True)
    COLA.write_text(json.dumps(d, ensure_ascii=False, indent=1),
                    encoding="utf-8")


def clave(cuerpo: str, articulo: str) -> str:
    return f"{cuerpo}#{str(articulo).strip().lower()}"


def apuntar(faltan: list) -> int:
    """Apunta `[(cuerpo, articulo)]` que fueron al redactor sin criterio.

    NUNCA LEVANTA. La llama `fase4.consultar` en mitad de una consulta real, y
    una cola rota no puede tumbar la respuesta de nadie: eso seria cambiar una
    mejora por una averia. Devuelve cuantas entradas nuevas ha creado.
    """
    if not faltan:
        return 0
    try:
        d = leer()
        nuevas = 0
        for cuerpo, articulo in faltan:
            if not cuerpo or not str(articulo).strip():
                continue
            k = clave(cuerpo, articulo)
            e = d["entradas"].get(k)
            if e is None:
                d["entradas"][k] = {
                    "cuerpo": cuerpo, "articulo": str(articulo).strip(),
                    "veces": 1, "primera_vez": _hoy(), "ultima_vez": _hoy(),
                    "estado": PENDIENTE, "buscado": "", "intentos": 0}
                nuevas += 1
            else:
                e["veces"] = e.get("veces", 0) + 1
                e["ultima_vez"] = _hoy()
        guardar(d)
        return nuevas
    except Exception:                            # noqa: BLE001
        return 0


def _toca_reintentar(e: dict) -> bool:
    if e.get("estado") != SIN_RESULTADOS or not e.get("buscado"):
        return e.get("estado") == PENDIENTE
    try:
        buscado = date.fromisoformat(e["buscado"])
    except ValueError:
        return True
    return date.today() - buscado >= timedelta(days=DIAS_REINTENTO)


def pendientes(normas=None, cobertura=None) -> list:
    """Lo que toca pedir, lo mas preguntado primero.

    Se descarta aqui lo que YA tiene criterio: entre que se apunto y que se
    baja puede haber entrado por otra via -otra consulta, una siembra- y pedirlo
    seria gastar una peticion en algo que ya esta.
    """
    d = leer()
    fuera = []
    for k, e in d["entradas"].items():
        if not _toca_reintentar(e):
            continue
        if cobertura is not None and (e["cuerpo"],
                                      e["articulo"].lower()) in cobertura:
            continue
        fuera.append(e)
    return sorted(fuera, key=lambda e: (-e.get("veces", 0), e["articulo"]))


def marcar(cuerpo: str, articulo: str, estado: str, bajadas: int = 0) -> None:
    d = leer()
    e = d["entradas"].get(clave(cuerpo, articulo))
    if e is None:
        return
    e["estado"] = estado
    e["buscado"] = _hoy()
    e["intentos"] = e.get("intentos", 0) + 1
    if bajadas:
        e["bajadas"] = e.get("bajadas", 0) + bajadas
    if estado == BAJADA:
        d["ultima_bajada"] = _hoy()
    d["ultimo_intento"] = _hoy()
    guardar(d)


def dias_sin_bajar() -> int | None:
    """Cuantos dias lleva la cola sin traer nada. None si nunca ha traido.

    Es lo que se dice en la ventana. Una cola que lleva cinco dias sin poder
    bajar puede ser que no haya nada que pedir -bien- o que la fuente este
    caida, o que hayan cambiado la pagina. Las tres se ven igual desde dentro y
    las tres hay que poder mirarlas desde fuera.
    """
    d = leer()
    if not d.get("ultima_bajada"):
        return None
    try:
        return (date.today() - date.fromisoformat(d["ultima_bajada"])).days
    except ValueError:
        return None


def aviso_de_silencio() -> str:
    """Vacio si no hay nada que decir."""
    d = leer()
    if not [e for e in d["entradas"].values() if _toca_reintentar(e)]:
        return ""            # no hay cola: el silencio es normal
    dias = dias_sin_bajar()
    if dias is None:
        if not d.get("ultimo_intento"):
            return ""
        return ("Hay artículos apuntados y todavía no se ha podido traer nada "
                "de la fuente. Si sigue así mañana, avisa a Emili.")
    if dias >= DIAS_SIN_BAJAR_AVISO:
        return (f"Llevo {dias} días sin poder traer criterio nuevo, y hay "
                f"artículos apuntados. Puede que la fuente esté caída: avisa "
                f"a Emili si sigue igual.")
    return ""


def recien_bajado() -> dict:
    """{articulos, consultas} de la ultima vez que la cola trajo algo.

    Es el aviso que CIERRA EL CIRCULO. Sin el, la promesa -«apuntado para
    buscarlo»- no se cumple delante de nadie y a la tercera vez se deja de
    mirar.
    """
    d = leer()
    ult = d.get("ultima_bajada")
    if not ult:
        return {"articulos": 0, "consultas": 0, "cuando": ""}
    arts = [e for e in d["entradas"].values()
            if e.get("buscado") == ult and e.get("estado") == BAJADA]
    return {"articulos": len(arts),
            "consultas": sum(e.get("bajadas", 0) for e in arts),
            "cuando": ult}


# ---------------------------------------------------------------- el vaciado


def vaciar(tope: int = 3, pausa: float = 10.0, progreso=None) -> dict:
    """Pide a PETETE lo apuntado. -> {pedidos, bajadas, vacios, corte}.

    SOLO PETETE. El TEAC se consulta en caliente y es otra cosa: otra fuente,
    otro ritmo y otro trato. Meterlo aqui seria juntar dos problemas para
    resolver ninguno.

    EL RITMO ES EL DE LA SIEMBRA, sin excepciones: la misma `petete.Fuente` con
    su pausa de diez segundos. Una cola que se vacia deprisa porque «son solo
    unas pocas» es como se acaba bloqueado, y el que lo pagaria no es quien
    escribio la prisa.

    TOPE BAJO A PROPOSITO. Esto corre AL ABRIR el agente, en segundo plano y
    con alguien esperando para trabajar: tres articulos son medio minuto de
    fuente y no se nota. Lo que no se baja hoy se baja mañana; la cola no
    caduca.

    NO LEVANTA NUNCA. Corre por detras y nadie la mira: si algo falla, se
    apunta el intento y se vuelve mañana.
    """
    import time

    salida = {"pedidos": 0, "bajadas": 0, "vacios": 0, "corte": ""}
    try:
        import fase4
        import petete
        from . import dgt as _D

        ix, _g = fase4.cargar_corpus()
        N = ix.normas
        cobertura = {(p.cuerpo, p.numero.lower())
                     for c in _D.CacheDGT().todas()
                     for p in c.preceptos(N) if p.comparable}
        cola_pendiente = pendientes(N, cobertura)[:tope]
        if not cola_pendiente:
            return salida

        DEMANDA.mkdir(parents=True, exist_ok=True)
        fuente = petete.Fuente(silencioso=True)
        cache = petete.Cache()

        for i, e in enumerate(cola_pendiente):
            cuerpo = N.por_clave(e["cuerpo"])
            if cuerpo is None or not getattr(cuerpo, "numero", ""):
                marcar(e["cuerpo"], e["articulo"], SIN_RESULTADOS)
                continue
            if progreso:
                progreso(f"buscando criterio del art. {e['articulo']} "
                         f"({i + 1} de {len(cola_pendiente)})")
            try:
                campos = fuente._campos("", "", petete.TAB_VINCULANTES, 1)
                campos = [(k, f"{cuerpo.numero} {e['articulo']}"
                           if k == "VLCMP_3" else v) for k, v in campos]
                crudo = fuente.pedir("/do/search", campos).cuerpo
                resultados = petete.extraer_resultados(crudo)
            except petete.FuenteCaida as exc:
                # LA FUENTE SE CAE Y SE PARA. No se reintenta en bucle: los
                # reintentos con tope ya los hace `petete.Fuente`.
                salida["corte"] = str(exc)[:120]
                break
            except petete.FormaInesperada as exc:
                salida["corte"] = f"forma inesperada: {str(exc)[:90]}"
                break

            salida["pedidos"] += 1
            numeros = [r["numero"] for r in resultados if r["numero"]][:5]
            if not numeros:
                marcar(e["cuerpo"], e["articulo"], SIN_RESULTADOS)
                salida["vacios"] += 1
                time.sleep(pausa)
                continue

            bajadas = 0
            for numero in numeros:
                if cache.tiene(numero) or (DEMANDA / f"{numero}.json").is_file():
                    continue
                time.sleep(pausa)
                try:
                    datos, _origen = petete.obtener_consulta(
                        numero, cache, fuente, verboso=False)
                except Exception:                # noqa: BLE001
                    continue
                if datos:
                    (DEMANDA / f"{numero}.json").write_text(
                        json.dumps(datos, ensure_ascii=False, indent=1),
                        encoding="utf-8")
                    bajadas += 1
            marcar(e["cuerpo"], e["articulo"],
                   BAJADA if bajadas else SIN_RESULTADOS, bajadas)
            salida["bajadas"] += bajadas
            time.sleep(pausa)
    except Exception as exc:                     # noqa: BLE001
        salida["corte"] = f"{type(exc).__name__}: {str(exc)[:90]}"
    return salida


def apuntados_de(preceptos) -> list:
    """De `[(cuerpo, articulo)]`, los que estan en la cola esperando turno.

    Es lo que convierte «no lo tengo» en «todavia no lo tengo». La cola ya
    apuntaba y ya bajaba, pero desde la ventana no se veia, asi que a la
    segunda consulta sin criterio la lectura era «esto no lo sabe» cuando la
    verdad era «esto lo esta buscando».

    NUNCA LEVANTA: se llama al pintar una respuesta.
    """
    try:
        d = leer()
        fuera = []
        for cuerpo, articulo in preceptos or []:
            e = d["entradas"].get(clave(cuerpo, articulo))
            if e is not None and _toca_reintentar(e):
                fuera.append(e["articulo"])
        return fuera
    except Exception:                            # noqa: BLE001
        return []


def resumen() -> dict:
    """El estado de la cola, para enseñarlo. Nunca levanta.

    SIN BARRA DE PROGRESO, y es deliberado: la cola avanza a saltos, por
    detras y solo al abrir el agente. Una barra sugiere que algo se mueve
    ahora mismo y que se puede esperar a que llegue, y las dos cosas son
    falsas. Un estado honesto -cuantos faltan, cuantos entraron y cuando- dice
    mas y no promete nada.
    """
    try:
        d = leer()
        pend = [e for e in d["entradas"].values() if _toca_reintentar(e)]
        ult = recien_bajado()
        return {"en_cola": len(pend),
                "ultima_vez_articulos": ult["articulos"],
                "ultima_vez_consultas": ult["consultas"],
                "cuando": ult["cuando"],
                "sin_bajar": dias_sin_bajar()}
    except Exception:                            # noqa: BLE001
        return {"en_cola": 0, "ultima_vez_articulos": 0,
                "ultima_vez_consultas": 0, "cuando": "", "sin_bajar": None}


def frase_de_estado() -> str:
    """Una linea para «Que hay dentro». Vacia si no hay nada que contar."""
    r = resumen()
    if not r["en_cola"] and not r["ultima_vez_articulos"]:
        return ""
    trozos = []
    if r["en_cola"]:
        trozos.append(f"{r['en_cola']} artículo(s) apuntados, buscando criterio")
    if r["ultima_vez_articulos"]:
        cuando = r["cuando"]
        try:
            cuando = date.fromisoformat(cuando).strftime("%d/%m")
        except ValueError:
            pass
        trozos.append(f"la última vez ({cuando}) entraron "
                      f"{r['ultima_vez_consultas']} consulta(s) sobre "
                      f"{r['ultima_vez_articulos']} artículo(s)")
    return ". ".join(trozos) + "."
