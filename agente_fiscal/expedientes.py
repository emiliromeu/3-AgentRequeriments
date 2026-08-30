"""LOS EXPEDIENTES GUARDADOS, EN UNA LISTA QUE SE PUEDE ENSEÑAR.

Hay 5.325 carpetas en `datos/trazas`, cada una con la pregunta, la respuesta
que se enseño, cada cita con su veredicto y los articulos que la sostienen. No
habia forma de ver ninguna desde la ventana. Esto es lo que hace falta para
poder listarlas.

Aqui NO se decide nada de una respuesta: se lee lo justo para pintar una fila
-cuando, que se pregunto, como acabo- y quien quiera la respuesta entera va a
`ver_ejemplo.cargar`, que la reconstruye del expediente sin inventarse un dato.

----------------------------------------------------------------------------
POR QUE HAY UN INDICE, Y NO SE LEE LA CARPETA CADA VEZ
----------------------------------------------------------------------------
Medido en este Mac, sobre 5.325 expedientes:

    solo los nombres de carpeta ............  0,02 s
    + abrir pregunta.txt de cada una, EN FRIO .. 68,8 s
    lo mismo, con la cache del sistema caliente .. 1,2 s

Son 13 ms por carpeta en frio, y el primer arranque del dia en el PC de la
oficina es siempre el caso frio. Sesenta y nueve segundos para abrir una
pantalla que se usa a diario no es lento: es que no se abre.

LA FECHA NO CUESTA NADA, y eso decide la forma de todo esto: el nombre de la
carpeta ES el sello de tiempo. Ordenar, agrupar por dia y decir cuando fue cada
consulta sale de `scandir` y de nada mas. Lo caro es la PREGUNTA, que vive
dentro de un fichero.

----------------------------------------------------------------------------
QUE GUARDA EL INDICE
----------------------------------------------------------------------------
Una entrada por expediente, y solo lo que necesita una FILA de la lista:

    sello .......... el nombre de la carpeta. Es la clave y es la fecha.
    pregunta ....... recortada; en la fila no cabe mas
    estado ......... CRITERIO CLARO / DISCUTIDO / NO ENCONTRADO / ...
    ejercicio ...... el año con el que se contesto
    comunidad ...... con cual se hizo
    con_criterio ... si se pulso el segundo boton
    motor .......... con que motor: es lo que distingue el banco
    modelo ......... quien contesto de verdad. `claude-opus-5` o nada
    viene_de ....... de que vuelta anterior cuelga, para armar el hilo

NO guarda la respuesta. Ni el texto, ni las citas, ni los avisos. Dos motivos:
el indice se lee entero cada vez que se abre la lista y pesaria megas, y sobre
todo que una copia del texto es una copia que puede quedarse vieja o decir algo
distinto de lo que hay en el expediente. La respuesta se lee SIEMPRE del
expediente, en el momento de abrirlo.

----------------------------------------------------------------------------
Y QUE PASA CUANDO SE QUEDA VIEJO, O ROTO
----------------------------------------------------------------------------
EL INDICE ES UNA CACHE, NO LA VERDAD. La verdad es el disco, y preguntarle que
carpetas hay cuesta 0,02 s. Todo lo de aqui sale de esa asimetria:

  VIEJO ....... se compara con lo que hay en disco y se leen SOLO las carpetas
                que faltan. Como los nombres son sellos de tiempo y solo se
                añaden, lo normal es que falten las de hoy: unas pocas.
  BORRADAS .... las entradas cuya carpeta ya no esta se caen solas.
  ROTO ........ un JSON ilegible, truncado o de otra version se trata como si
                no existiera: se rehace entero. No se intenta reparar nada.
  NO SE PUEDE
  ESCRIBIR .... se sigue sin cache. La proxima vez volvera a costar lo que
                cueste, y nada mas. Un disco lleno no puede llevarse por
                delante el historial, igual que no puede llevarse una consulta.

NUNCA BLOQUEA, y esa es la regla que manda sobre las demas: si el indice falla
por lo que sea, la lista se pinta mas despacio. No deja de existir. Por eso
`filas()` acepta que le pasen las que ya se tienen y devuelve lo que puede,
y por eso nada de aqui lanza una excepcion hacia arriba.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_TRAZAS = RAIZ / "datos" / "trazas"
# Dentro de `datos/trazas/`, que ya no viaja por git -.gitignore, linea 44-.
# Con guion bajo delante para que no se confunda nunca con un expediente: los
# expedientes empiezan por un digito.
INDICE = DIR_TRAZAS / "_indice.json"
# Si cambia lo que se guarda por fila, sube esto y el indice viejo se rehace
# solo. Es mas barato que migrarlo, y no puede quedar a medias.
VERSION = 1

# Cuanto de la pregunta se guarda. En una fila de lista no cabe mas, y guardar
# la pregunta entera convertiria el indice en una segunda copia de las dudas de
# los clientes: hay una, y esta en el expediente.
LARGO_PREGUNTA = 200

# ---------------------------------------------------------------- el filtro
#
# LOS MOTORES QUE NO SON EL DE VERDAD. `ensayo` fabrica respuestas con una
# regla fija; los otros dos existen para provocar fallos en las suites.
MOTORES_DE_PRUEBA = ("ensayo", "siempre-falla", "sin-techo")
# Y LOS ESTADOS QUE NUNCA LLEGARON A SER UNA CONSULTA. La ventana no puede
# producirlos -sus botones no se encienden sin duda y sin año valido-, asi que
# si estan es porque los hizo un guion. No hay nada que leer en ellos.
NUNCA_FUE_CONSULTA = ("SIN PREGUNTA", "FALTA EJERCICIO",
                      "PREGUNTA DEMASIADO LARGA")

RE_SELLO = re.compile(r"^(\d{8})T(\d{6})")


def es_expediente(nombre: str) -> bool:
    """¿Es el nombre de una carpeta de expediente? El sello lo dice."""
    return bool(RE_SELLO.match(nombre))


def fecha_de(sello) -> tuple:
    """Del sello a («29/08/2026», «21:47»). Dos vacios si no se puede leer.

    NO SE INVENTA UNA FECHA. Un expediente sin sello reconocible -no deberia
    haberlos, pero una carpeta copiada a mano podria- devuelve vacio y quien
    llame no pinta nada. Una fecha supuesta en un historial es peor que ninguna:
    es lo que se usa para decir «esta es la del martes».
    """
    m = RE_SELLO.match(Path(str(sello or "")).name)
    if not m:
        return "", ""
    d, h = m.group(1), m.group(2)
    return f"{d[6:8]}/{d[4:6]}/{d[0:4]}", f"{h[0:2]}:{h[2:4]}"


def es_de_prueba(fila: dict) -> bool:
    """¿Esta la hizo un guion mio y no el departamento?

    DOS SEÑALES, Y LAS DOS SALEN DEL PROPIO EXPEDIENTE:

      · EL MOTOR. `resultado.json` guarda con cual se hizo. Medido sobre los
        5.119 expedientes con resultado: 3.684 llevan un motor de prueba.
      · EL ESTADO. Otros 536 acabaron en «SIN PREGUNTA», «FALTA EJERCICIO» o
        «PREGUNTA DEMASIADO LARGA», que la ventana no puede producir.

    LO QUE NO SIRVE, Y PARECIA QUE SI: filtrar por si gasto tokens. De las 79
    consultas hechas con el modelo de verdad, solo 31 gastaron -las demas se
    resolvieron antes de llamar-. Habria escondido 48 consultas reales.

    LO QUE ESTE FILTRO NO PUEDE HACER, dicho aqui para que no se le suponga
    mas de lo que es: los expedientes que se paran ANTES de elegir motor no
    llevan el campo, asi que un `ERROR` de un guion y un `ERROR` del despacho
    son indistinguibles. En el PC de la oficina eso da igual -alli no hay
    banco-; en este Mac deja pasar unos 820. Por eso el interruptor existe y
    por eso el filtro se puede apagar: un filtro que se equivoca y no se puede
    apagar esconde para siempre justo lo que alguien esta buscando.
    """
    if (fila.get("motor") or "") in MOTORES_DE_PRUEBA:
        return True
    return (fila.get("estado") or "") in NUNCA_FUE_CONSULTA


# ¿LA ESCRIBIO UN MODELO, O UNA REGLA FIJA?
#
# ESTA ES LA PREGUNTA DE SEGURIDAD, Y NO ES LA MISMA QUE `es_de_prueba`.
# Aquella ordena la lista y se puede apagar con una casilla; esta decide si un
# texto puede salir de la herramienta, y no se apaga con nada.
#
# EL FALLO QUE LA TRAE, del 30/08/2026: abriendo del historial una consulta
# hecha con `--motor ensayo` -cuyo texto lo fabrica una regla fija de
# `modelo.py`, no un modelo- la ventana la pintaba como CRITERIO CLARO, con sus
# citas, y con «Copiar respuesta» y «Escribirlo para el cliente» ENCENDIDOS. Lo
# copiado no llevaba ni una palabra diciendo que era inventado.
#
# LA CAUSA, Y ES LO QUE HAY QUE RECORDAR: el aviso de «esto es de prueba» vivia
# en la SESION -`motor.es_modelo_real`, cierto mientras esa ventana estaba
# abierta- y no en el EXPEDIENTE. El historial cruza esa frontera y el aviso no
# cruzaba con el. El dato estaba en disco desde siempre; nadie lo miraba.
#
# SE DECIDE POR AFIRMACION, NO POR SOSPECHA. Solo se dice «fabricada» cuando el
# expediente lo dice. Si no lleva el campo no se afirma nada: no se puede
# acusar a un expediente de ser falso por no llevar una etiqueta. Y esta
# medido: de las 2.159 respuestas ACEPTADAS que hay en disco, CERO no llevan
# campo `motor`. La duda no existe hoy, y si algun dia existiera, el silencio
# es el lado correcto en el que equivocarse -no marca de mas, no bloquea de
# mas- porque el texto de un expediente sin motor es texto que un verificador
# acepto.
FABRICADA = (
    "Esta respuesta la escribió una REGLA FIJA del modo de prueba, no un "
    "modelo. No es una consulta real: no vale para nada más que para probar "
    "la herramienta, y por eso no se puede copiar ni mandar a nadie."
)


def es_fabricada(res: dict) -> bool:
    """¿HAY UN TEXTO, y lo invento el motor de ensayo?

    LAS DOS MITADES HACEN FALTA, y la segunda me la salte al primer intento:
    marcaba la CONSULTA entera y no el TEXTO. Un «NO ENCONTRADO» hecho con el
    motor de ensayo no tiene nada fabricado dentro -no hay texto- y su estado
    lo calculo el codigo por reglas, igual de cierto con un motor que con
    otro. Marcarlo de prueba tapaba una respuesta legitima con un aviso que no
    le tocaba, y ademas rompia `prueba_no_encontrado`, que hace justo eso.

    Lo que hay que proteger es el TEXTO que sale de aqui hacia un cliente. Sin
    texto no hay nada de lo que proteger.
    """
    if (res.get("motor") or "") not in MOTORES_DE_PRUEBA:
        return False
    return bool(res.get("respuesta") or res.get("orientacion"))


# ---------------------------------------------------------------- el indice


def _leer_indice() -> dict:
    """Lo que haya guardado. Un indice ilegible es un indice que no existe."""
    try:
        d = json.loads(INDICE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(d, dict) or d.get("version") != VERSION:
        # De otra version, o algo que no es lo que esperamos. Se rehace: es
        # mas barato que migrarlo y no puede quedarse a medias.
        return {}
    filas = d.get("expedientes")
    return filas if isinstance(filas, dict) else {}


def _guardar_indice(filas: dict) -> str:
    """Guarda la cache. Devuelve por que no se pudo, o cadena vacia.

    NO LANZA. Que no se pueda escribir la cache no puede tumbar el historial:
    lo unico que pasa es que la proxima vez se vuelve a leer del disco. Es la
    misma regla que en `traza.Traza`, y por el mismo motivo.
    """
    try:
        INDICE.parent.mkdir(parents=True, exist_ok=True)
        # Se escribe al lado y se mueve encima: si el programa se cierra a
        # mitad, lo que queda es el indice viejo entero y no uno truncado.
        # Un JSON a medias se lee como «no hay indice», que tampoco seria
        # grave, pero no hay motivo para dejarlo pasar.
        tmp = INDICE.with_suffix(".json.parcial")
        tmp.write_text(json.dumps({"version": VERSION, "expedientes": filas},
                                  ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, INDICE)
        return ""
    except OSError as e:
        return f"no se ha podido guardar el indice: {e}"


def _leer_expediente(sello: str) -> dict:
    """Los datos de UNA fila, leidos del disco. Lo caro de todo esto."""
    carpeta = DIR_TRAZAS / sello
    fila = {"sello": sello, "pregunta": "", "estado": "", "ejercicio": "",
            "comunidad": "", "con_criterio": False, "motor": "", "modelo": "",
            "viene_de": ""}
    try:
        with open(carpeta / "pregunta.txt", encoding="utf-8") as f:
            fila["pregunta"] = " ".join(f.read(LARGO_PREGUNTA * 3).split())[
                :LARGO_PREGUNTA]
    except OSError:
        pass
    try:
        with open(carpeta / "resultado.json", encoding="utf-8") as f:
            r = json.load(f)
        fila["estado"] = str(r.get("estado") or "")
        fila["ejercicio"] = str(r.get("ejercicio") or "")
        fila["comunidad"] = str(r.get("comunidad") or "")
        fila["con_criterio"] = bool(r.get("con_criterio"))
        fila["motor"] = str(r.get("motor") or "")
        fila["modelo"] = str(r.get("modelo") or "")
        fila["viene_de"] = str(r.get("viene_de") or "")
    except (OSError, ValueError):
        pass
    if not fila["viene_de"]:
        # Los expedientes viejos lo guardaban solo en `hilo.json`.
        try:
            with open(carpeta / "hilo.json", encoding="utf-8") as f:
                fila["viene_de"] = str((json.load(f) or {}).get("viene_de") or "")
        except (OSError, ValueError):
            pass
    return fila


def sellos_en_disco() -> list:
    """Los expedientes que hay, de mas nuevo a mas viejo. 0,02 s.

    `scandir` y no `listdir` porque hay que descartar lo que no es una carpeta
    de expediente -el propio indice, por ejemplo- y `scandir` ya trae esa
    respuesta sin una llamada mas al sistema por cada entrada.
    """
    try:
        with os.scandir(DIR_TRAZAS) as it:
            nombres = [e.name for e in it
                       if es_expediente(e.name) and e.is_dir()]
    except OSError:
        return []
    return sorted(nombres, reverse=True)


def filas(limite: int = 0, progreso=None) -> tuple:
    """Las filas de la lista, de mas nueva a mas vieja.

    Devuelve `(filas, aviso)`. `aviso` dice por que la cache no se pudo
    guardar, o cadena vacia; NUNCA es un motivo para no enseñar la lista.

    `limite` lee solo las N mas nuevas -lo que se ve al abrir- y deja el resto
    para despues. `progreso` recibe (hechas, total) mientras se leen las que
    faltan, para que quien llame pueda pintar mientras tanto.
    """
    guardado = _leer_indice()
    hay = sellos_en_disco()
    if limite:
        hay = hay[:limite]
    faltan = [s for s in hay if s not in guardado]
    for i, sello in enumerate(faltan, 1):
        guardado[sello] = _leer_expediente(sello)
        if progreso is not None and (i % 40 == 0 or i == len(faltan)):
            progreso(i, len(faltan))
    # LAS BORRADAS SE CAEN SOLAS, pero solo cuando se ha mirado el disco
    # ENTERO. Con `limite` se ha visto una ventana de los mas nuevos, y quitar
    # de la cache todo lo que no este en esa ventana la borraria casi entera en
    # cada apertura.
    #
    # Y SE MIRA SIEMPRE, NO SOLO CUANDO HAY ALGO NUEVO. Aqui esto colgaba de
    # `if faltan:`, asi que una carpeta borrada sin ninguna nueva detras se
    # quedaba en el indice para siempre: la lista enseñaba una fila que ya no
    # existe, y al pulsarla no habia expediente. Lo caza `prueba_historial`.
    sobran = []
    if not limite:
        vivos = set(hay)
        sobran = [k for k in guardado if k not in vivos]
        for k in sobran:
            del guardado[k]
    aviso = ""
    if faltan or sobran:
        aviso = _guardar_indice(guardado)
    return [guardado[s] for s in hay if s in guardado], aviso


# ------------------------------------------------------------------ buscar


def _plano(t: str) -> str:
    """Sin acentos y en minusculas: se busca como se escribe con prisa."""
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower())
                   if unicodedata.category(c) != "Mn")


def buscar(filas_: list, texto: str) -> list:
    """Las filas cuya pregunta contiene lo que se busca.

    Se mira SOLO la pregunta. Buscar dentro de las respuestas obligaria a abrir
    los 5.325 expedientes en cada tecla, y quien busca en un historial busca
    por lo que pregunto: es lo unico que escribio.
    """
    aguja = _plano(texto).strip()
    if not aguja:
        return filas_
    return [f for f in filas_ if aguja in _plano(f.get("pregunta", ""))]


# ------------------------------------------------------------------- hilos


def hilos(filas_: list) -> list:
    """Agrupa las vueltas de una misma conversacion en una sola fila.

    Cada vuelta es un expediente propio -cada respuesta se verifico contra un
    material concreto en un momento concreto- y lleva de cual viene. La cadena
    se recorre hacia atras, que es como se diseño.

    Devuelve una lista de grupos, cada uno `[mas antigua, ..., mas reciente]`.
    En la lista se enseña la ULTIMA: es la que tiene el contexto entero, y es
    la que alguien recuerda haber leido.
    """
    por_sello = {f["sello"]: f for f in filas_}
    hijos: dict = {}
    for f in filas_:
        padre = f.get("viene_de") or ""
        if padre and padre in por_sello:
            hijos.setdefault(padre, []).append(f["sello"])
    # Una vuelta es raiz si no cuelga de ninguna que tengamos delante.
    raices = [f for f in filas_
              if not (f.get("viene_de") and f["viene_de"] in por_sello)]
    grupos = []
    for r in raices:
        cadena, pila = [], [r["sello"]]
        while pila:
            s = pila.pop(0)
            cadena.append(por_sello[s])
            pila.extend(sorted(hijos.get(s, [])))
        grupos.append(cadena)
    # De mas nuevo a mas viejo por su ultima vuelta, que es lo que se enseña.
    grupos.sort(key=lambda g: g[-1]["sello"], reverse=True)
    return grupos
