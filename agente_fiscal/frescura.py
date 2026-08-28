#!/usr/bin/env python3
"""EL CORPUS ES UNA FOTO, Y LAS FOTOS ENVEJECEN. Cero API.

Es el unico punto donde el agente puede equivocarse SIN AVISAR. Todo lo demas
que puede fallar se nota: una fuente caida se dice, una cita sin verificar no
se enseña, una consulta sin criterio lo declara. Pero una ley que cambio en
marzo y una copia de febrero dan una respuesta impecable, segura y equivocada.

DOS COMPROBACIONES, Y LA BUENA ES LA EXACTA
-------------------------------------------
1. CON RED, exacta: el BOE dice en los metadatos de cada norma cuando la toco
   por ultima vez. Comparado con la fecha en que nosotros la ingerimos, no hay
   umbral que discutir: o ha cambiado o no.

2. SIN RED, por antigüedad: cuando no se puede preguntar, se avisa si la copia
   pasa de `DIAS_SOSPECHOSO`.

EL UMBRAL SALE DE LOS DATOS, NO DE UN NUMERO REDONDO. Medido el 13/08/2026
sobre las diecisiete normas del corpus, mirando cuando las habia tocado el BOE:

    mediana 135 dias · la mas reciente 10 · la mas antigua 239
    tocadas en los ultimos  90 dias:  7 de 17
    tocadas en los ultimos 180 dias: 13 de 17
    tocadas en los ultimos 365 dias: 17 de 17

A los 180 dias, TRECE DE DIECISIETE normas ya han cambiado al menos una vez, o
sea que un corpus de esa edad esta desactualizado casi con seguridad. A los 90
serian siete: avisar ahi seria avisar cuando aun es probable que no haya pasado
nada, y un aviso que salta antes de tiempo se aprende a ignorar. Al año lo han
hecho las diecisiete, asi que esperar tanto es garantizar el fallo.

Y NO SALTA SIEMPRE, que es la otra mitad: reingerir lo apaga, y la mediana dice
que una copia recien hecha aguanta unos cuatro meses antes de acercarse.
"""
import json
from datetime import date, datetime
from pathlib import Path

DIAS_SOSPECHOSO = 180

# Cuando el aviso pasa de «conviene» a «hay que hacerlo»: al año, TODAS las
# normas medidas habian cambiado.
DIAS_SEGURO_VIEJO = 365


def _fecha(texto: str):
    try:
        return datetime.strptime(str(texto)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def edad_del_corpus(dir_corpus: Path, hoy: date | None = None) -> dict:
    """{normas, mas_vieja, dias, sin_fecha}. Sin red y sin cargar el corpus.

    Se lee de `sellos.json`, que ya guarda cuando se ingirio cada norma: la
    fecha no hay que añadirla, hay que MIRARLA. Estaba ahi desde que existen
    los sellos y nadie la usaba para nada.
    """
    hoy = hoy or date.today()
    ruta = Path(dir_corpus) / "sellos.json"
    if not ruta.is_file():
        return {"normas": 0, "mas_vieja": None, "dias": None, "sin_fecha": 0}
    try:
        sellos = json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"normas": 0, "mas_vieja": None, "dias": None, "sin_fecha": 0}

    fechas, sin_fecha = [], 0
    for clave, valor in sellos.items():
        if clave == "sellado" or not isinstance(valor, dict):
            continue
        f = _fecha(valor.get("sellado"))
        if f is None:
            sin_fecha += 1
        else:
            fechas.append((f, clave))
    if not fechas:
        return {"normas": sin_fecha, "mas_vieja": None, "dias": None,
                "sin_fecha": sin_fecha}
    mas_vieja, cual = min(fechas)
    return {"normas": len(fechas) + sin_fecha, "mas_vieja": mas_vieja,
            "cual": cual, "dias": (hoy - mas_vieja).days,
            "sin_fecha": sin_fecha}


def retraso_de_consolidacion(dir_corpus: Path) -> dict:
    """LO QUE DE VERDAD MIDE SI VAMOS ATRASADOS. Sin red: ya esta en el sello.

    -> {normas, con_reformas, preceptos, preguntado, sin_dato, detalle}

    LA DISTINCION QUE COSTO UN DIAGNOSTICO ENTERO, escrita aqui para que no
    vuelva a costar otro:

        `consolidado_hasta` ES DEL BOE, NO NUESTRO. Es hasta donde llega el
        texto consolidado QUE EL BOE PUBLICA. El Reglamento del ITPAJD lo tiene
        en 2018 y eso NO significa que llevemos ocho años sin bajarlo: significa
        que el BOE no ha incorporado nada nuevo desde entonces. Puede ser una
        norma estable.

        `sellado` ES NUESTRO, y mide OTRA COSA: el dia que ejecutamos la
        ingesta. Mide nuestra diligencia. Por eso el aviso viejo no saltaba
        nunca -reingerir lo ponia a cero aunque no hubieramos traido nada
        nuevo- y por eso ya no se usa para esto.

        LO QUE DICE EL RETRASO DE VERDAD es si el BOE lista reformas
        POSTERIORES que su propio texto todavia no incorpora. Eso lo calcula
        `pendientes.leer` al ingerir, y desde hoy se guarda en el sello.

    Aqui no hay umbral que discutir: o hay reformas pendientes o no las hay.
    """
    ruta = Path(dir_corpus) / "sellos.json"
    vacio = {"normas": 0, "con_reformas": 0, "preceptos": 0,
             "preguntado": "", "sin_dato": 0, "detalle": []}
    if not ruta.is_file():
        return vacio
    try:
        sellos = json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return vacio

    normas = con = preceptos = sin_dato = 0
    preguntado = ""
    detalle = []
    for clave, valor in sorted(sellos.items()):
        if not isinstance(valor, dict) or clave == "sellado":
            continue
        normas += 1
        c = valor.get("consolidacion")
        if not isinstance(c, dict):
            # LOS SELLOS VIEJOS NO LO LLEVAN Y SE CUENTAN APARTE. Suponer que
            # una norma sin dato esta al dia es exactamente lo que no se puede
            # hacer: es la que no sabemos.
            sin_dato += 1
            continue
        n = int(c.get("reformas_pendientes") or 0)
        if c.get("preguntado", "") > preguntado:
            preguntado = c.get("preguntado", "")
        if n:
            con += 1
            tocados = c.get("preceptos_tocados") or []
            preceptos += len(tocados)
            detalle.append({"norma": clave, "reformas": n,
                            "preceptos": len(tocados),
                            "consolidado_hasta": c.get("consolidado_hasta", "")})
    detalle.sort(key=lambda d: (-d["reformas"], d["norma"]))
    return {"normas": normas, "con_reformas": con, "preceptos": preceptos,
            "preguntado": preguntado, "sin_dato": sin_dato, "detalle": detalle}


def horizonte(dir_corpus: Path) -> dict:
    """HASTA CUANDO LLEGA EL CORPUS. Sin red: ya esta en el sello.

    -> {hasta, norma, ejercicio_completo, por_norma, sin_dato}

    MANDA LA MAS ATRASADA, no la media ni la mas reciente. El corpus se usa
    entero para contestar una pregunta -la ley, su reglamento y lo que remita-
    asi que hasta donde llega el conjunto es hasta donde llega su eslabon mas
    corto. Una media diria «2025» teniendo dentro un reglamento parado en 2018.

    `ejercicio_completo` es el ultimo año que el corpus cubre DE ENERO A
    DICIEMBRE. Un corpus consolidado hasta el 09/11/2018 no cubre 2018: le
    faltan siete semanas, y una reforma de diciembre es justo la clase de cosa
    que entra en vigor el 1 de enero siguiente. Redondear hacia arriba aqui
    seria decir que se cubre un año que no se cubre.

    NO ES NUESTRO RETRASO, es el del texto que publica el BOE. Ver
    `retraso_de_consolidacion`: una norma estable puede llevar años sin
    tocarse y estar al dia.
    """
    ruta = Path(dir_corpus) / "sellos.json"
    vacio = {"hasta": "", "norma": "", "ejercicio_completo": None,
             "por_norma": {}, "sin_dato": []}
    if not ruta.is_file():
        return vacio
    try:
        sellos = json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return vacio

    por_norma, sin_dato = {}, []
    for clave, valor in sorted(sellos.items()):
        if not isinstance(valor, dict) or clave == "sellado":
            continue
        hasta = ((valor.get("consolidacion") or {}).get("consolidado_hasta")
                 or "")
        if _fecha(hasta) is None:
            # SIN DATO NO ES «LLEGA HASTA HOY». Es la que no sabemos, y se
            # cuenta aparte para que no desaparezca en el minimo.
            sin_dato.append(clave)
        else:
            por_norma[clave] = hasta
    if not por_norma:
        return {"hasta": "", "norma": "", "ejercicio_completo": None,
                "por_norma": {}, "sin_dato": sin_dato}
    norma = min(por_norma, key=lambda k: (por_norma[k], k))
    hasta = por_norma[norma]
    año = int(hasta[:4])
    return {"hasta": hasta, "norma": norma,
            "ejercicio_completo": año if hasta[5:] >= "12-31" else año - 1,
            "por_norma": por_norma, "sin_dato": sin_dato}


def aviso_de_horizonte(dir_corpus: Path, ejercicio: int | None) -> str:
    """EL AVISO CUANDO SE PREGUNTA POR DELANTE DEL CORPUS. Vacio si cabe.

    Es el mismo fallo que persigue todo este modulo, en su version mas dificil
    de ver: la respuesta sale bien formada, con su articulo y su enlace, y lo
    unico que le pasa es que el ejercicio por el que se pregunta cae MAS ALLA
    de donde llega la copia. No hay nada roto que enseñar.

    Va DENTRO de la respuesta, no en la documentacion de quien la lee. Un aviso
    que hay que ir a buscar a un LEEME no lo lee el programa que consume el
    JSON, y quien escribio ese programa se fue de la empresa.
    """
    if ejercicio is None:
        return ""
    h = horizonte(dir_corpus)
    if not h["hasta"]:
        return ("No se sabe hasta cuándo llega esta copia: ninguna norma tiene "
                "fecha de consolidación en su sello. Hay que reingerirlas para "
                "poder decirlo.")
    if f"{ejercicio}-12-31" <= h["hasta"]:
        return ""
    return (f"La consulta es de {ejercicio} y esta copia solo llega entera "
            f"hasta {h['ejercicio_completo']}: el texto consolidado más "
            f"atrasado es el de {h['norma']}, al {h['hasta']}. Lo que se "
            f"conteste sobre {ejercicio} puede no recoger reformas "
            f"posteriores a esa fecha.")


def aviso_de_consolidacion(dir_corpus: Path) -> str:
    """Que normas tienen reformas publicadas sin incorporar. Vacio si ninguna.

    NO DICE DIAS, dice QUE Y CUANTAS. Los dias eran el respaldo de cuando no
    se podia preguntar; esto es el dato exacto.
    """
    r = retraso_de_consolidacion(dir_corpus)
    if r["sin_dato"] and not r["normas"] - r["sin_dato"]:
        return ""            # ningun sello lo lleva todavia: no se inventa
    if not r["con_reformas"]:
        return ""
    nombres = ", ".join(d["norma"] for d in r["detalle"][:4])
    mas = (f" y {r['con_reformas'] - 4} mas"
           if r["con_reformas"] > 4 else "")
    cola = ""
    if r["preceptos"]:
        cola = (f" Afectan a {r['preceptos']} precepto(s), que quedan marcados "
                f"como no citables.")
    return (f"{r['con_reformas']} de {r['normas']} normas tienen reformas "
            f"publicadas que el texto consolidado del BOE todavía no "
            f"incorpora: {nombres}{mas}.{cola} No es un fallo del agente: es "
            f"que el BOE aún no las ha metido en el texto.")


def aviso_de_edad(dir_corpus: Path, hoy: date | None = None) -> str:
    """EL RESPALDO SIN RED. La frase para la ventana, o vacia si no hay nada.

    NO SE BORRA AUNQUE PAREZCA QUE SOBRA, y esto va escrito porque va a
    parecerlo: desde que el sello guarda las reformas pendientes, el aviso
    exacto es `aviso_de_consolidacion` y este mide otra cosa -cuanto hace que
    ingerimos-. Pero ese dato solo existe si ALGUIEN pregunto al BOE al
    ingerir; para un corpus que llego copiado de otro equipo, o de una version
    anterior a este cambio, lo unico que hay es la edad. Los 180 dias estan
    MEDIDOS para eso -ver la cabecera- y borrarlos dejaria ese caso mudo.

    TRANQUILA Y NO BLOQUEANTE. Un corpus viejo no es una promesa rota: es un
    dato que envejece. Impedir abrir por eso dejaria a la gestoria sin
    herramienta justo el dia que mas prisa tiene, y la respuesta seguiria
    siendo util para todo lo que no haya cambiado. Lo que no vale es callarse.
    """
    e = edad_del_corpus(dir_corpus, hoy)
    dias = e.get("dias")
    if dias is None or dias < DIAS_SOSPECHOSO:
        return ""
    cuando = e["mas_vieja"].strftime("%d/%m/%Y")
    if dias >= DIAS_SEGURO_VIEJO:
        return (f"La copia de las normas es de hace más de un año "
                f"({cuando}). En ese tiempo TODAS las leyes que usa el agente "
                f"han cambiado al menos una vez: conviene actualizarla antes "
                f"de fiarse de una respuesta. Se hace desde «Qué hay dentro».")
    meses = dias // 30
    return (f"La copia de las normas tiene {meses} meses ({cuando}). Las "
            f"leyes fiscales se reforman varias veces al año, así que puede "
            f"que alguna ya haya cambiado. Se actualiza desde «Qué hay "
            f"dentro»; mientras tanto el agente funciona igual.")
