#!/usr/bin/env python3
"""DE QUE HAY CRITERIO GUARDADO. Contado de la despensa, no escrito a mano.

Cero red y cero API: se lee `datos/dgt` y `datos/teac`, que es lo que hay en
este disco.

POR QUE EXISTE ESTE FICHERO, y es la quinta vez esta semana. El pie del
segundo boton decia «TODAS DE IVA por ahora». Era verdad el dia que se
escribio y dejo de serlo en cuanto la siembra metio criterio de Renta, de
Sociedades, de Patrimonio, de la LGT y de los reglamentos. Nadie mintio: se
escribio un hecho como si fuera una constante.

Una frase a mano sobre lo que el sistema cubre es una fecha de caducidad sin
etiqueta. La cobertura no se afirma: se cuenta.

COMO SE CUENTA. Cada consulta de la DGT y cada resolucion del TEAC dicen de
que preceptos hablan; el impuesto de un precepto lo dice el corpus
-`normas.impuesto_de_precepto`, que mira el titulo en que vive-. Asi que el
impuesto de una consulta es el de los preceptos que cita, y no hay ninguna
lista intermedia que se pueda quedar vieja.

LO QUE NO SE RESUELVE NO SE CUENTA, y eso es deliberado: una consulta que esta
en el disco pero cuyo campo «normativa» no se deja leer NO se puede encontrar
en una busqueda, asi que para quien pregunta no existe. Contarla seria decir
que hay cobertura donde no la hay, que es exactamente el fallo que este
fichero viene a cerrar.
"""
from . import dgt as _D
from . import teac as _T

# Como se llaman los impuestos en pantalla. Los codigos salen del corpus
# -`impuesto_de_precepto`-; esto es solo como se escriben para leerlos.
EN_CRISTIANO = {
    "IVA": "IVA",
    "IRPF": "Renta",
    "IS": "Sociedades",
    "IP": "Patrimonio",
    "ISD": "Sucesiones y Donaciones",
    "ITPAJD": "Transmisiones y Actos Juridicos",
    "IEDMT": "Determinados Medios de Transporte",
    "IDREDCIC": "Deposito de Residuos",
}

# Lo que no es de ningun impuesto en particular: procedimiento, recaudacion,
# infracciones. Vale para cualquier pregunta, asi que se cuenta aparte y no
# como si fuera un impuesto mas.
GENERAL = "normas generales"


def resumen(ix) -> dict:
    """{codigo de impuesto: {"dgt": n, "teac": m}}, contado del disco.

    `ix` es el indice del corpus ya cargado: se necesita para saber en que
    titulo vive cada precepto, que es lo que dice de que impuesto es.
    """
    normas = ix.normas
    # LA CLAVE DE UN PRECEPTO ES «norma#cuerpo#articulo N», que es la misma
    # identidad que usa todo lo demas. Si no esta en el indice, el documento
    # cita algo que no tenemos y no cuenta como cobertura.
    cache_impuesto: dict = {}

    def impuesto_de(cuerpo: str, numero: str) -> str:
        clave = f"{cuerpo}#articulo {numero}"
        if clave not in cache_impuesto:
            doc = ix.por_clave.get(clave)
            cache_impuesto[clave] = (normas.impuesto_de_precepto(doc.registro)
                                     if doc else None)
        return cache_impuesto[clave]

    cuenta: dict = {}

    def apuntar(impuestos: set, fuente: str) -> None:
        for i in impuestos:
            clave = i or GENERAL
            cuenta.setdefault(clave, {"dgt": 0, "teac": 0})
            cuenta[clave][fuente] += 1

    for c in _D.CacheDGT().todas():
        impuestos = {impuesto_de(p.cuerpo, p.numero)
                     for p in c.preceptos(normas) if p.cuerpo}
        apuntar({i for i in impuestos if i is not None}, "dgt")

    for r in _T.CacheTEAC().todas():
        # El TEAC devuelve pares (cuerpo, articulo), no objetos.
        impuestos = {impuesto_de(cuerpo, numero)
                     for cuerpo, numero in r.preceptos(normas) if cuerpo}
        apuntar({i for i in impuestos if i is not None}, "teac")

    return cuenta


def documentos(ix) -> tuple:
    """(documentos distintos que se pueden encontrar, cuantos tocan 2+ impuestos).

    HACE FALTA PARA QUE LA TABLA NO ENGAÑE. Las cifras por impuesto SUMAN MAS
    que documentos hay, porque una consulta que cita la Ley del IVA y la LGT
    cuenta en las dos filas. Eso es lo correcto -para quien pregunta de IVA,
    esa consulta es criterio de IVA- pero leido en columna parece que hay 653
    consultas «de IVA», y no es eso: son 653 documentos que HABLAN de IVA.

    Asi que se dice el numero de documentos distintos al lado, y cuantos son
    los que tocan mas de uno. Con las dos cifras la columna deja de poder
    leerse mal, y no cuesta ni una linea de mas de las que ya habia.
    """
    normas = ix.normas

    def impuesto_de(cuerpo: str, numero: str):
        doc = ix.por_clave.get(f"{cuerpo}#articulo {numero}")
        return normas.impuesto_de_precepto(doc.registro) if doc else None

    distintos = varios = 0
    for c in _D.CacheDGT().todas():
        suyos = {impuesto_de(p.cuerpo, p.numero)
                 for p in c.preceptos(normas) if p.cuerpo}
        suyos = {i for i in suyos if i is not None}
        if suyos:
            distintos += 1
            varios += len(suyos) > 1
    for r in _T.CacheTEAC().todas():
        suyos = {impuesto_de(cuerpo, numero)
                 for cuerpo, numero in r.preceptos(normas) if cuerpo}
        suyos = {i for i in suyos if i is not None}
        if suyos:
            distintos += 1
            varios += len(suyos) > 1
    return distintos, varios


def por_impuesto(ix) -> list:
    """[(nombre en cristiano, total)], de mas a menos. Los generales al final."""
    cuenta = resumen(ix)
    filas = []
    for codigo, n in cuenta.items():
        total = n["dgt"] + n["teac"]
        if not total:
            continue
        filas.append((EN_CRISTIANO.get(codigo, codigo), total, codigo))
    filas.sort(key=lambda f: (f[2] == GENERAL, -f[1]))
    return [(nombre, total) for nombre, total, _c in filas]


def frase(ix) -> str:
    """Una linea con de que hay criterio y cuanto. Para el pie del boton.

    CON EL NUMERO AL LADO, porque «hay criterio de Renta» y «hay criterio de
    Renta: 12 documentos» no dicen lo mismo, y quien decide si pulsa el
    segundo boton necesita el segundo.
    """
    filas = por_impuesto(ix)
    if not filas:
        return ("todavia no hay nada guardado: el segundo boton no encontrara "
                "criterio de ningun impuesto")
    trozos = [f"{nombre} ({total})" for nombre, total in filas]
    return "ahora mismo hay criterio guardado de " + ", ".join(trozos)


def impuestos_cubiertos(ix) -> list:
    """LOS IMPUESTOS QUE EL AGENTE CUBRE DE VERDAD. Los siglas, sin traducir.

    UN IMPUESTO CUENTA CUANDO HAY UN CUERPO DEDICADO A EL, no cuando aparece
    un articulo suelto que habla de el. La regla es estructural y sale del
    corpus, no de una lista escrita aqui.

    POR QUE HACE FALTA EL SUELO. Contando precepto a precepto salian NUEVE
    impuestos, y dos de ellos con UN articulo cada uno: el 661-1 y el 671-1 del
    libro sexto del Codigo tributario de Catalunya, que son adaptaciones
    autonomicas dentro de otra norma. Decir que el agente «cubre el impuesto
    sobre determinados medios de transporte» porque tiene un articulo sobre su
    tipo de gravamen es la misma clase de promesa que este proyecto existe para
    no hacer: quien pregunte por ese impuesto no va a encontrar nada.

    Hoy da seis, que son los seis de verdad.
    """
    vistos = {ix.normas.impuesto_de_cuerpo(c) for c in ix.normas.cuerpos}
    return sorted(v for v in vistos if v)


def impuestos_del_corpus(ix) -> list:
    """[(nombre en cristiano, cuantos preceptos)] de lo que el agente cubre.

    Es otra frase que estaba escrita a mano -«responde solo con la Ley y el
    Reglamento del IVA»- con trece normas y cuatro impuestos dentro.

    Se cuentan TODOS los preceptos, incluidos los sueltos de un impuesto que no
    llega al suelo: van a «normas generales», que es donde el agente los va a
    buscar de todas formas. Lo que el suelo decide es que se ANUNCIA, no que se
    ignora.
    """
    cubiertos = set(impuestos_cubiertos(ix))
    cuenta: dict = {}
    for d in ix.docs:
        i = ix.normas.impuesto_de_precepto(d.registro) or GENERAL
        if i not in cubiertos:
            i = GENERAL
        cuenta[i] = cuenta.get(i, 0) + 1
    filas = sorted(cuenta.items(), key=lambda f: (f[0] == GENERAL, -f[1]))
    return [(EN_CRISTIANO.get(c, c), n) for c, n in filas]


def titulo(ix) -> str:
    """EL TITULO DE LA VENTANA. Con la cuenta, no con la lista.

    Decia «Consulta fiscal — IVA» con seis impuestos dentro: la cuarta frase de
    esta familia que envejecio porque estaba escrita a mano. Poner los seis
    nombres tampoco vale -no caben en una barra de titulo y volveria a
    quedarse vieja de otra manera-, asi que va la cuenta, que se recalcula
    sola.
    """
    n = len(impuestos_cubiertos(ix))
    if n == 0:
        return "Consulta fiscal"
    if n == 1:
        return f"Consulta fiscal — {EN_CRISTIANO.get(impuestos_cubiertos(ix)[0], '')}"
    return f"Consulta fiscal — {n} impuestos"


def frase_de_la_ley(ix) -> str:
    """Con que ley responde el primer boton. La lista sale del corpus."""
    filas = [n for n, _c in impuestos_del_corpus(ix)]
    if not filas:
        return "no hay ninguna norma cargada"
    if len(filas) == 1:
        return f"responde con la ley de {filas[0]}"
    return ("responde con la ley de " + ", ".join(filas[:-1])
            + f" y {filas[-1]}")


# --------------------------------------------------- que ha entrado desde ayer

# LA CUENTA DE LA ULTIMA VEZ QUE SE ABRIO. Vive con la despensa y no en el
# corpus: es un dato de ESTE equipo -cuando lo vio esta persona por ultima
# vez- y no algo que deba viajar por git.
def _ruta_marca():
    from pathlib import Path
    return (Path(__file__).resolve().parent.parent / "datos" / "dgt"
            / "visto.json")


def novedades(ix) -> dict:
    """{antes, ahora, nuevas, cuando} y DEJA LA MARCA PUESTA.

    POR QUE HACE FALTA. La despensa la lleno yo en el Mac y viaja por git; en
    la oficina crece de golpe cuando alguien hace pull. Hoy no hay nada que se
    lo diga: el criterio nuevo esta ahi y nadie se entera de que esta.

    NO PREGUNTA A LA RED NI TOCA GIT. Compara la cuenta de ahora con la de la
    ultima vez que se abrio, que es todo lo que hace falta para decirlo.

    NUNCA LEVANTA: se llama al arrancar la ventana.
    """
    import json
    from datetime import date

    salida = {"antes": None, "ahora": 0, "nuevas": 0, "cuando": ""}
    try:
        cuenta = resumen(ix)
        ahora = sum(n["dgt"] + n["teac"] for n in cuenta.values())
        salida["ahora"] = ahora
        f = _ruta_marca()
        if f.is_file():
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                salida["antes"] = int(d.get("documentos"))
                salida["cuando"] = str(d.get("cuando") or "")
            except (ValueError, TypeError, OSError):
                pass
        if salida["antes"] is not None:
            salida["nuevas"] = max(0, ahora - salida["antes"])
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"documentos": ahora,
                                 "cuando": date.today().isoformat()},
                                ensure_ascii=False),
                     encoding="utf-8")
    except Exception:                            # noqa: BLE001
        pass
    return salida


def aviso_de_novedades(ix) -> str:
    """«Han entrado N consultas nuevas». Vacio si no hay nada que decir.

    LA PRIMERA VEZ NO DICE NADA, y es a proposito: sin marca anterior, la
    unica cuenta honrada seria «hay 2.400», que no es una novedad sino un
    inventario, y el inventario ya esta en «Que hay dentro».
    """
    n = novedades(ix)
    if not n["nuevas"]:
        return ""
    desde = f" desde el {n['cuando'][8:10]}/{n['cuando'][5:7]}" if n["cuando"] else ""
    return (f"Han entrado {n['nuevas']} documentos de criterio nuevos"
            f"{desde}. Ya se usan al pulsar «Consultar también el criterio».")
