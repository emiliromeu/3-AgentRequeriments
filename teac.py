#!/usr/bin/env python3
"""CLIENTE DEL TEAC — doctrina y criterios de los tribunales economicos.

    python teac.py buscar --norma "Ley 37/1992" --precepto 80
    python teac.py criterio 00/01298/2004/00/00
    python teac.py cache
    python teac.py canario

FASE 10. Solo descarga y cache. No se integra con el agente: eso es la fase 11.

NO GASTA NI UNA LLAMADA A LA API DE ANTHROPIC.

----------------------------------------------------------------------------
QUE ES DISTINTO DE PETETE, Y POR QUE IMPORTA
----------------------------------------------------------------------------
DYCTEA es ASP.NET WebForms, no KnoSys. Daba miedo por el `__VIEWSTATE` de 400
KB, y resulta que NO HACE FALTA: el postback del formulario solo redirige a una
URL GET con los filtros en la query. Buscar aqui es mas facil que en PETETE.

Y los datos vienen MUCHO mejor estructurados:

  · el criterio es un CAMPO propio, no prosa dentro de la resolucion;
  · las referencias normativas vienen AGRUPADAS POR NORMA, con sus preceptos
    en una lista debajo. Nada de parsear «Ley 37/1992 arts. 75, 78, 80-cuatro»
    como hubo que hacer con la DGT: aqui se respeta la estructura que viene y
    no se vuelve a interpretar prosa. Todo el trabajo de la fase 9C aqui
    sobra, y por eso no se repite.

----------------------------------------------------------------------------
POR QUE SE BUSCA POR PRECEPTO
----------------------------------------------------------------------------
El buscador corta en 100 resultados. Filtrando solo por norma, la Ley del IVA
da 1127 y se pierden mil. Filtrando por precepto se baja del tope -el articulo
80 da 71- y se puede paginar entero. Ademas es lo que encaja con el agente, que
ya sabe que articulos sostienen la respuesta.

Se pide por NOMBRE («Ley 37/1992») y numero de articulo, y el cliente traduce a
los codigos internos (`02:07:01:00:00:1029`). Nadie tiene que saberselos.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from agente_fiscal import fuente_web as FW
from agente_fiscal.fuente_web import (      # noqa: F401
    ANCHO, FormaInesperada, FuenteCaida, Respuesta, aviso, titulo,
)

BASE = "https://serviciostelematicosext.hacienda.gob.es/TEAC/DYCTEA"
URL_NAVEGADOR = BASE + "/criterio.aspx?id={id}"

DIR = RAIZ / "datos" / "teac"
DIR_CRUDO = DIR / "crudo"
DIR_CRITERIOS = DIR / "criterios"
DIR_BUSQUEDAS = DIR / "busquedas"
INDICE = DIR / "indice.json"
CATALOGO = DIR / "catalogo.json"

UA = ("agente-fiscal-gestoria/1.0 (cliente de consulta de una gestoria; "
      "uso interno y volumen bajo)")

# Que DYCTEA conteste en 0,14 s no cambia el ritmo: sigue siendo un servicio
# publico y el descuido empieza justo donde sobra capacidad.
ESPERA = 45
REINTENTOS = 3
PAUSA = 4.0
PAUSA_REINTENTO = 8.0

# El radio «Busqueda por Criterios» del formulario, con sus valores REALES
# leidos del HTML. Los puse a ojo la primera vez y me equivoque: el 1 no es
# «vinculantes» sino «NO vinculantes», que es justo lo contrario.
CRITERIO_VINCULANTES = "0"
CRITERIO_NO_VINCULANTES = "1"
CRITERIO_TODOS = "2"

# Un id de criterio: la resolucion mas el numero de criterio.
RE_ID = re.compile(r"^\d{2}/\d{4,5}/\d{4}/\d{2}/\d{1,2}(?:/\d+)?$")


# ------------------------------------------------------------------- la fuente


class Fuente(FW.FuenteWeb):
    """DYCTEA. De la base hereda red, pausas y reintentos."""

    def __init__(self, espera: int = ESPERA, reintentos: int = REINTENTOS,
                 pausa: float = PAUSA, silencioso: bool = False):
        super().__init__(base=BASE, ua=UA, espera=espera, reintentos=reintentos,
                         pausa=pausa, pausa_reintento=PAUSA_REINTENTO,
                         silencioso=silencioso)

    def cabeceras(self) -> dict:
        """Sin `X-Requested-With`: aqui no hay AJAX y decir que si lo hay seria
        presentarse como algo que no somos."""
        return {
            "User-Agent": self.ua,
            "Accept-Language": "es-ES,es;q=0.9",
            "Referer": f"{self.base}/",
        }

    # ------------------------------------------------------------ catalogo

    def portada(self) -> str:
        """La pagina del formulario. Trae dentro TODO el catalogo de normas y
        preceptos (1,3 MB), asi que se pide una vez y se guarda."""
        return self.pedir("/").cuerpo

    # ------------------------------------------------------------- buscar

    def buscar(self, norma: str, precepto: str = "", pagina: int = 1,
               solo_vinculantes: bool = False) -> str:
        """Los filtros van en la URL. El `__VIEWSTATE` no se toca."""
        return self.pedir("/criterios.aspx", [
            ("s", "1"), ("rs", ""), ("rn", ""), ("ra", ""),
            ("fd", ""), ("fh", ""), ("u", ""),
            ("n", norma), ("p", precepto),
            ("c1", ""), ("c2", ""), ("c3", ""),
            ("tc", "1"), ("tr", ""), ("tp", ""), ("tf", ""),
            ("c", CRITERIO_VINCULANTES if solo_vinculantes else CRITERIO_TODOS),
            ("pg", str(pagina)),
        ]).cuerpo

    def criterio(self, id_criterio: str) -> str:
        return self.pedir("/criterio.aspx", [("id", id_criterio)]).cuerpo

    def texto_resolucion(self, id_criterio: str) -> str:
        """El texto largo va en un IFRAME aparte, no en la pagina del criterio.

        Cuesta una peticion mas y merece la pena: es donde el TEAC cita las
        consultas de la DGT por numero. Sin esto, el campo `consultas_dgt`
        saldria casi siempre vacio y pareceria que la señal estructural no es
        viable, cuando lo que pasa es que no habriamos mirado donde vive.
        """
        return self.pedir("/textoresolucion.aspx", [("id", id_criterio)]).cuerpo


# ------------------------------------------------------------------- extraer


def _texto(fragmento: str) -> str:
    """HTML -> texto legible. Igual que en petete: los <br> y los cierres de
    bloque son saltos, el resto se colapsa."""
    import html as _html
    t = re.sub(r"<(script|style).*?</\1>", " ", fragmento, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</(p|div|tr|li|h\d|ul)>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = _html.unescape(t)
    t = re.sub(r"[ \t\xa0]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n\n", t).strip()


def _bloque(crudo: str, id_div: str) -> str:
    """El contenido de un <div id='...'>. Devuelve '' si no esta."""
    m = re.search(r"<div\s+id='" + re.escape(id_div) + r"'[^>]*>(.*?)</div>",
                  crudo, re.S | re.I)
    return m.group(1) if m else ""


def _tras_rotulo(crudo: str, id_div: str) -> str:
    """El valor de un campo «Rotulo: valor», sin el rotulo."""
    bruto = _bloque(crudo, id_div)
    if not bruto:
        return ""
    # El rotulo va en un <span class='criterioNegrita'> o antes de los dos
    # puntos; se quita para quedarse solo con el valor.
    sin_rotulo = re.sub(r"<span class='criterioNegrita'>\s*[^<]*?:\s*</span>",
                        "", bruto, flags=re.I)
    texto = _texto(sin_rotulo)
    return re.sub(r"^[^:]{0,40}:\s*", "", texto).strip()


def extraer_referencias(crudo: str) -> list:
    """Las referencias normativas, RESPETANDO la estructura que viene.

    Vienen ya agrupadas: una norma y debajo la lista de sus preceptos. Aqui no
    se interpreta nada; solo se lee lo que el TEAC ya ha separado. Esa es la
    diferencia con la DGT, cuyo campo `normativa` es texto corrido y hubo que
    parsear a mano en la fase 9C.
    """
    lista = re.search(r"<ul\s+id='referenciasNormativas'>(.*?)</ul>\s*(?:</div>|$)",
                      crudo, re.S | re.I)
    if not lista:
        return []
    salida = []
    for m in re.finditer(r"<li class='elementoNorma'>(.*?)(?:<ul>(.*?)</ul>)?</li>",
                         lista.group(1), re.S | re.I):
        norma = _texto(m.group(1) or "").strip()
        preceptos = [_texto(p).strip() for p in re.findall(
            r"<li class='elementoPrecepto'>(.*?)</li>", m.group(2) or "",
            re.S | re.I)]
        if norma:
            salida.append({"norma": norma, "preceptos": preceptos})
    return salida


def consultas_dgt_citadas(*textos: str) -> list:
    """Los numeros de consulta de la DGT que aparecen en el criterio.

    EL CAMPO QUE HACE ESTRUCTURAL LA SEÑAL. Hoy el criterio discutido se deduce
    de que dos consultas hablen del mismo articulo; si el TEAC dice «segun la
    consulta V3533-19», eso ya no es una coincidencia de numeros: es el propio
    tribunal diciendo sobre que criterio se pronuncia.

    Se busca en TODOS los campos que se le pasen porque no se sabe donde viven:
    en la unica resolucion del reconocimiento estaban en el texto largo, y el
    campo Criterio es corto y no las traia.

    El reconocedor es el de `dgt.py`, no uno nuevo: si manana cambia como se
    escribe un numero de consulta, cambia en un sitio.
    """
    from agente_fiscal import dgt as D

    vistos = []
    for t in textos:
        for patron in (D.RE_NUM_CONSULTA, D.RE_NUM_SUELTO):
            for m in patron.finditer(t or ""):
                num = m.group("num").upper()
                if num not in vistos:
                    vistos.append(num)
    return sorted(vistos)


# Sin estos campos un criterio no vale para nada: si faltan, se para.
IMPRESCINDIBLES = ("resolucion", "criterio")


def extraer_criterio(crudo: str, id_pedido: str = "",
                     crudo_texto: str = "") -> dict:
    """HTML de un criterio -> campos. Si no reconoce la forma, PARA.

    Igual que en petete: mas vale no guardar nada que guardar medio registro.
    Un criterio a medias es peor que ninguno, porque parece completo.
    """
    # LA RESPUESTA TIENE QUE ESTAR ENTERA. Una pagina cortada a la mitad deja
    # el criterio -que va arriba- pero se lleva por delante las referencias
    # normativas y los conceptos, y eso es medio registro: parece completo y no
    # lo esta. Se comprueba por ESTRUCTURA y no por contenido, porque exigir
    # que haya referencias seria suponer que ningun criterio se publica sin
    # ellas, y eso no lo sabemos.
    if crudo and "</html>" not in crudo[-2000:]:
        raise FormaInesperada(
            "la respuesta viene cortada: no llega al final del documento. No "
            "se guarda nada, porque lo que falta son las referencias "
            "normativas y los conceptos, que van al final")

    titulo_bruto = _bloque(crudo, "criterioDatosTitulo")
    negritas = re.findall(r"<span class='criterioNegrita'>(.*?)</span>",
                          titulo_bruto, re.S | re.I)
    n_criterio = _texto(negritas[0]) if len(negritas) > 0 else ""
    de_cuantos = _texto(negritas[1]) if len(negritas) > 1 else ""
    resolucion = _texto(negritas[2]) if len(negritas) > 2 else ""

    contenido = _bloque(crudo, "criterioDatosContenido")
    # El texto largo NO esta en esta pagina: viene de `textoresolucion.aspx`,
    # que aqui se carga en un iframe. Si no se pasa, queda vacio y se dice.
    texto_res = _texto(crudo_texto) if crudo_texto else ""

    campos = {
        "id": id_pedido,
        "resolucion": resolucion,
        "n_criterio": n_criterio,
        "de_criterios": de_cuantos,
        "calificacion": _tras_rotulo(crudo, "criterioDatosCalificacion"),
        "unidad": _tras_rotulo(crudo, "criterioDatosUnidad"),
        "fecha": _tras_rotulo(crudo, "criterioDatosFecha"),
        "asunto": _tras_rotulo(crudo, "criterioDatosAsunto"),
        "criterio": _texto(contenido),
        "referencias": extraer_referencias(crudo),
        "conceptos": [_texto(x).strip() for x in re.findall(
            r"<li>(.*?)</li>", _bloque(crudo, "criterioDatosConceptos") or "",
            re.S | re.I)],
        "texto_resolucion": texto_res,
    }

    faltan = [c for c in IMPRESCINDIBLES if not campos.get(c)]
    if faltan:
        raise FormaInesperada(
            f"no se reconocen los campos {', '.join(faltan)} en el criterio. "
            f"La pagina de DYCTEA puede haber cambiado de forma: hay que "
            f"mirarla antes de fiarse de nada de lo que salga")

    # Unificacion de criterio: el TEAC lo dice en el propio criterio o lo marca
    # como concepto. Se mira en los dos sitios.
    marca = "unificaci"
    campos["unifica_criterio"] = bool(
        re.search(r"unificaci[oó]n de criterio", campos["criterio"], re.I)
        or any(marca in c.lower() for c in campos["conceptos"]))

    campos["consultas_dgt"] = consultas_dgt_citadas(
        campos["criterio"], campos["asunto"], campos["texto_resolucion"])
    return campos


RE_FILA = re.compile(
    r"Criterio\s+(?P<ncrit>\d+)\s+de\s+la\s+resoluci[oó]n\s+"
    r"(?P<res>[\d/]+)\s+del\s+(?P<fecha>\d{2}/\d{2}/\d{4})\s*-\s*(?P<unidad>[^<\n]+)",
    re.I)


def extraer_resultados(crudo: str) -> list:
    """La lista de criterios de una pagina de resultados."""
    if "criterio.aspx" not in crudo and "Criterio" not in crudo:
        raise FormaInesperada(
            "la pagina de resultados no trae ningun criterio ni enlaces a "
            "criterio.aspx: o han cambiado la plantilla del buscador, o no es "
            "una pagina de resultados")
    salida = []
    # Las comillas de los atributos son SIMPLES en esta plantilla. Exigir
    # dobles hacia que la lista saliera vacia aunque la busqueda dijera «71
    # resultados», que es el peor fallo posible: parece que no hay nada.
    for m in re.finditer(
            r"<a[^>]+href=['\"]([^'\"]*criterio\.aspx[^'\"]*)['\"][^>]*>(.*?)</a>",
            crudo, re.S | re.I):
        href, etiqueta = m.group(1), _texto(m.group(2))
        mid = re.search(r"id=([^&\"]+)", href)
        f = RE_FILA.search(etiqueta)
        salida.append({
            "id": (mid.group(1) if mid else "").replace("%2f", "/").replace("%2F", "/"),
            "resolucion": f.group("res") if f else "",
            "n_criterio": f.group("ncrit") if f else "",
            "fecha": f.group("fecha") if f else "",
            "unidad": (f.group("unidad").strip() if f else ""),
            "etiqueta": etiqueta[:160],
        })
    return salida


def cuantos_resultados(crudo: str) -> tuple:
    """(cuantos, si_hay_tope). El buscador corta en 100 y lo dice."""
    m = re.search(r"Se han obtenido\s+([\d.]+)\s+resultados", crudo, re.I)
    n = int(m.group(1).replace(".", "")) if m else -1
    tope = bool(re.search(r"[Ss]olo aparecer[aá]n los primeros", crudo))
    return n, tope


# ------------------------------------------------------------------ catalogo


RE_PAR_CATALOGO = re.compile(r'\[\\?"([\d:]+:\d+)\\?",\s*\\?"([^"\\]{1,60})\\?"\]')


def extraer_catalogo(crudo: str) -> dict:
    """Normas y preceptos del formulario, para traducir nombres a codigos."""
    import html as _html

    normas = {}
    m = re.search(r'<select[^>]*name="[^"]*ddlNorma"[^>]*>(.*?)</select>',
                  crudo, re.S | re.I)
    if m:
        for v, t in re.findall(r'<option[^>]*value="([^"]*)"[^>]*>(.*?)</option>',
                               m.group(1), re.S | re.I):
            nombre = _html.unescape(re.sub(r"<[^>]+>", "", t)).strip()
            if v and nombre:
                normas[v] = nombre

    # Los preceptos van embebidos en el JavaScript como pares
    # ["02:07:01:00:00:1029", "80"].
    preceptos: dict = {}
    for codigo, etiqueta in RE_PAR_CATALOGO.findall(crudo):
        norma = ":".join(codigo.split(":")[:5])
        preceptos.setdefault(norma, {})[etiqueta.strip()] = codigo

    if not normas or not preceptos:
        raise FormaInesperada(
            "la portada de DYCTEA no trae el catalogo de normas y preceptos "
            "donde esperabamos: han cambiado el formulario")
    return {"normas": normas, "preceptos": preceptos,
            "cuando": FW.ahora()}


def buscar_norma(catalogo: dict, texto: str) -> tuple:
    """«Ley 37/1992» -> (codigo, nombre completo). Sin adivinar."""
    t = texto.strip().lower()
    exactos = [(v, n) for v, n in catalogo["normas"].items() if n.lower() == t]
    if exactos:
        return exactos[0]

    # Por PREFIJO antes que por subcadena. «Ley 37/1992» aparece dentro de
    # «Ley 9/1998 Modifica la Ley 37/1992...», que habla de ella pero NO es
    # ella; el nombre de la norma buscada empieza por su propia designacion.
    # Sin esta regla, pedir la Ley del IVA por su numero salia ambiguo entre
    # tres normas y no habia forma de nombrarla sin copiar el titulo entero.
    empiezan = [(v, n) for v, n in catalogo["normas"].items()
                if n.lower().startswith(t)]
    if len(empiezan) == 1:
        return empiezan[0]
    if len(empiezan) > 1:
        raise FormaInesperada(
            "«" + texto + "» encaja con " + str(len(empiezan)) + " normas: "
            + "; ".join(n for _, n in empiezan[:6])
            + ". Concreta mas: aqui no se adivina cual quieres")

    parciales = [(v, n) for v, n in catalogo["normas"].items() if t in n.lower()]
    if len(parciales) == 1:
        return parciales[0]
    if not parciales:
        return "", ""
    # Varias: no se elige por nosotros. Se devuelven para que el usuario mire.
    raise FormaInesperada(
        "«" + texto + "» encaja con " + str(len(parciales)) + " normas: "
        + "; ".join(n for _, n in parciales[:6])
        + ". Concreta mas: aqui no se adivina cual quieres")


# --------------------------------------------------------------------- cache


class Cache(FW.CacheDocumentos):
    """La cache del TEAC. Sin mapeo numero<->id: aqui el documento se pide por
    su propio numero de resolucion, que es lo que usa la gente."""

    def __init__(self):
        super().__init__(dir_crudo=DIR_CRUDO, dir_documentos=DIR_CRITERIOS,
                         dir_busquedas=DIR_BUSQUEDAS, indice=INDICE, raiz=RAIZ)

    @staticmethod
    def nombre_fichero(id_criterio: str) -> str:
        return id_criterio.replace("/", "-")

    def tiene(self, id_criterio: str) -> bool:
        return super().tiene(self.nombre_fichero(id_criterio))

    def leer(self, id_criterio: str) -> dict | None:
        return super().leer(self.nombre_fichero(id_criterio))

    def guardar(self, id_criterio: str, crudo: str, campos: dict) -> dict:
        nombre = self.nombre_fichero(id_criterio).upper()
        f_crudo, sha = self.guardar_crudo(nombre, crudo)
        registro = dict(campos)
        registro.update({
            "id": id_criterio,
            "url_navegador": URL_NAVEGADOR.format(id=id_criterio),
            "descargado": FW.ahora(),
            "sha256_crudo": sha,
            "crudo": self.ruta_relativa(f_crudo),
        })
        self.guardar_documento(nombre, registro)
        ficha = self.indice["consultas"].setdefault(id_criterio, {})
        ficha.update({"resolucion": campos.get("resolucion", ""),
                      "fecha": campos.get("fecha", ""),
                      "descargado": registro["descargado"]})
        self._guardar_indice()
        return registro

    # ------------------------------------------------------------ catalogo

    def catalogo(self, fuente: "Fuente | None" = None) -> dict:
        """El catalogo, de disco. Solo se baja si no esta: son 1,3 MB."""
        if CATALOGO.is_file():
            try:
                return json.loads(CATALOGO.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                aviso("el catalogo estaba corrupto; se vuelve a pedir")
        if fuente is None:
            raise FuenteCaida("no hay catalogo local y no se ha permitido "
                              "salir a la red")
        cat = extraer_catalogo(fuente.portada())
        CATALOGO.parent.mkdir(parents=True, exist_ok=True)
        CATALOGO.write_text(json.dumps(cat, ensure_ascii=False), encoding="utf-8")
        return cat


# ----------------------------------------------------------------- obtener


def obtener_criterio(id_criterio: str, cache: Cache, fuente: Fuente | None,
                     verboso: bool = True) -> tuple:
    """(registro, origen). Si esta en cache NO se toca la red."""
    guardado = cache.leer(id_criterio)
    if guardado:
        return guardado, "cache"
    if fuente is None:
        raise FuenteCaida("no esta en la cache y no se ha permitido salir a la red")
    if verboso:
        print(f"  descargando {id_criterio}")
    crudo = fuente.criterio(id_criterio)
    try:
        crudo_texto = fuente.texto_resolucion(id_criterio)
    except FuenteCaida as e:
        # El texto es donde viven las citas a la DGT. Si no se puede traer, NO
        # se guarda un criterio a medias haciendo creer que no cita ninguna.
        raise FuenteCaida(
            f"el criterio se ha traido pero su texto no ({e}); no se guarda "
            f"medio registro", getattr(e, "codigo", None))
    campos = extraer_criterio(crudo, id_criterio, crudo_texto)
    return cache.guardar(id_criterio, crudo, campos), "red"


def normalizar_id(texto: str) -> str:
    """«00/01298/2004/00/00» -> «00/01298/2004/00/0/1».

    La gente escribe el numero de RESOLUCION; el criterio anade su numero. Si
    ya viene con el, se respeta.
    """
    t = texto.strip()
    partes = t.split("/")
    if len(partes) == 6:
        return t
    if len(partes) == 5:
        # El quinto segmento del id de criterio es de un digito.
        return "/".join(partes[:4] + [partes[4].lstrip("0") or "0", "1"])
    return t


# ------------------------------------------------------------------- modos


def modo_buscar(args) -> int:
    titulo(f"BUSCAR  norma «{args.norma}»"
           + (f"  precepto {args.precepto}" if args.precepto else ""))
    cache = Cache()
    fuente = Fuente(silencioso=False)
    try:
        cat = cache.catalogo(fuente)
    except FuenteCaida as e:
        aviso(f"no se ha podido preparar el catalogo: {e}")
        return 1
    except FormaInesperada as e:
        aviso(f"DYCTEA ha cambiado de forma: {e}")
        return 3

    try:
        cod_norma, nombre = buscar_norma(cat, args.norma)
    except FormaInesperada as e:
        aviso(str(e))
        return 2
    if not cod_norma:
        aviso(f"no se encuentra ninguna norma que encaje con «{args.norma}»")
        return 2
    print(f"\n  norma   : {nombre}")
    print(f"            {cod_norma}")

    cod_precepto = ""
    if args.precepto:
        preceptos = cat["preceptos"].get(cod_norma, {})
        cod_precepto = preceptos.get(str(args.precepto), "")
        if not cod_precepto:
            aviso(f"la norma no tiene el precepto «{args.precepto}». "
                  f"Los hay como: "
                  f"{', '.join(sorted(preceptos)[:8])}")
            return 2
        print(f"  precepto: {args.precepto}   {cod_precepto}")

    todos, pagina = [], 1
    while pagina <= args.paginas:
        try:
            crudo = fuente.buscar(cod_norma, cod_precepto, pagina,
                                  solo_vinculantes=args.vinculantes)
            filas = extraer_resultados(crudo)
        except FuenteCaida as e:
            aviso(f"la fuente no responde: {e}")
            return 1
        except FormaInesperada as e:
            aviso(f"DYCTEA ha cambiado de forma: {e}")
            return 3
        if pagina == 1:
            n, tope = cuantos_resultados(crudo)
            print(f"\n  {n} resultado(s)"
                  + ("   [OJO: el buscador corta en 100; acota mas]" if tope else ""))
            print()
        if not filas:
            break
        for f in filas:
            marca = "  [en cache]" if cache.tiene(f["id"]) else ""
            print(f"  {f['fecha']:11s} {f['resolucion']:22s} {f['unidad'][:18]:20s}"
                  f"{marca}")
            if args.detalle:
                print(f"     {f['etiqueta'][:100]}")
        todos.extend(filas)
        pagina += 1
    cache.guardar_busqueda(f"{cod_norma}|{cod_precepto}",
                           "vinc" if args.vinculantes else "todos", todos)
    print(f"\n  {len(todos)} criterio(s) listados en {pagina - 1} pagina(s)")
    print(f"  Para traer uno:  python teac.py criterio <resolucion>")
    return 0


def modo_criterio(args) -> int:
    id_criterio = normalizar_id(args.id)
    titulo(f"CRITERIO {id_criterio}")
    cache = Cache()
    fuente = None if args.solo_cache else Fuente()
    try:
        r, origen = obtener_criterio(id_criterio, cache, fuente)
    except FuenteCaida as e:
        aviso(f"No se ha podido traer el criterio: {e}")
        if args.solo_cache:
            print("\n  No se ha salido a la red porque lo has pedido con "
                  "--solo-cache.")
        else:
            print("\n  La fuente del TEAC no responde. Lo que ya este en la "
                  "cache\n  se sigue pudiendo consultar con --solo-cache.")
        return 1
    except FormaInesperada as e:
        aviso(f"DYCTEA ha respondido con una forma que no reconozco: {e}")
        print("\n  NO se ha guardado nada.")
        return 3

    print(f"\norigen: {origen.upper()}"
          + ("   (no se ha tocado la red)" if origen == "cache" else ""))
    _pintar(r, completo=args.completo)
    return 0


def _pintar(r: dict, completo: bool = False) -> None:
    print(f"\n  resolucion   : {r.get('resolucion')}")
    print(f"  criterio     : {r.get('n_criterio')} de {r.get('de_criterios')}")
    print(f"  fecha        : {r.get('fecha')}")
    print(f"  unidad       : {r.get('unidad')}")
    print(f"  calificacion : {r.get('calificacion')}")
    print(f"  UNIFICA CRITERIO: {'SI' if r.get('unifica_criterio') else 'no'}")
    print(f"  enlace       : {r.get('url_navegador')}")

    print("\n  ASUNTO")
    print("  " + "-" * 66)
    for l in (r.get("asunto") or "").split("\n"):
        print(f"  {l}")

    print("\n  CRITERIO")
    print("  " + "-" * 66)
    t = r.get("criterio") or ""
    if not completo and len(t) > 900:
        t = t[:900] + "…"
    for l in t.split("\n"):
        print(f"  {l}")

    print("\n  REFERENCIAS NORMATIVAS  (tal y como vienen, sin reinterpretar)")
    print("  " + "-" * 66)
    for ref in r.get("referencias") or []:
        print(f"  · {ref['norma']}")
        for p in ref["preceptos"]:
            print(f"       {p}")

    print("\n  CONCEPTOS")
    print("  " + "-" * 66)
    for c in r.get("conceptos") or []:
        print(f"  · {c}")

    print("\n  CONSULTAS DE LA DGT QUE CITA")
    print("  " + "-" * 66)
    cs = r.get("consultas_dgt") or []
    print("  " + (", ".join(cs) if cs else "(ninguna)"))

    print(f"\n  texto de la resolucion: {len(r.get('texto_resolucion') or '')} caracteres")
    if completo and r.get("texto_resolucion"):
        print("  " + "-" * 66)
        print(r["texto_resolucion"])


def modo_cache(args) -> int:
    titulo("LA CACHE DEL TEAC")
    cache = Cache()
    criterios = sorted(DIR_CRITERIOS.glob("*.json"))
    crudos = list(DIR_CRUDO.glob("*.html"))
    bytes_todo = (sum(f.stat().st_size for f in crudos)
                  + sum(f.stat().st_size for f in criterios))
    print(f"\n  criterios guardados : {len(criterios)}")
    print(f"  documentos crudos   : {len(crudos)}")
    print(f"  busquedas guardadas : {len(list(DIR_BUSQUEDAS.glob('*.json')))}")
    print(f"  ocupa               : {bytes_todo/1024:.0f} KB")
    print(f"  catalogo            : {'si' if CATALOGO.is_file() else 'no'}")
    print(f"\n  carpeta: {DIR}")
    if not criterios:
        print("\n  Todavia no hay nada. Trae uno:")
        print("    python teac.py criterio 00/01298/2004/00/00")
        return 0

    con_dgt = 0
    print(f"\n  {'fecha':11s} {'resolucion':22s} {'unif':5s} consultas DGT")
    print("  " + "-" * 66)
    for f in criterios[:args.tope]:
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        cs = r.get("consultas_dgt") or []
        con_dgt += bool(cs)
        print(f"  {r.get('fecha',''):11s} {r.get('resolucion',''):22s} "
              f"{'SI' if r.get('unifica_criterio') else '-':5s} "
              f"{', '.join(cs) if cs else '-'}")
    print(f"\n  citan consultas de la DGT: {con_dgt} de {len(criterios)}")
    return 0


# ------------------------------------------------------------------- canario

CANARIO_ID = "00/01298/2004/00/0/1"
CANARIO_NORMA = "02:07:01:00:00"        # Ley 37/1992
CANARIO_PRECEPTO = "02:07:01:00:00:1029"  # articulo 80


def modo_canario(args) -> int:
    titulo("CANARIO DE LA FUENTE (TEAC / DYCTEA)")
    print(f"\n  fuente : {BASE}")
    print(f"  patron : criterio {CANARIO_ID}\n")

    can = FW.Canario()
    fuente = Fuente(silencioso=True)

    dias = FW.dias_de_certificado(BASE)
    if dias is None:
        can.avisos.append("no se ha podido leer la caducidad del certificado")
    elif dias < 0:
        can.fallos.append(f"el certificado del servidor CADUCO hace {-dias} dias")
    elif dias < 30:
        can.avisos.append(f"el certificado caduca en {dias} dias")

    print("  [1/3] el sitio responde ......... ", end="", flush=True)
    try:
        r = fuente.pedir("/criterios.aspx", [("s", "1")])
        print(f"SI   ({r.segundos:.1f}s)")
    except FuenteCaida as e:
        print(can.clasificar(e, "la portada"))

    print("  [2/3] la busqueda funciona ...... ", end="", flush=True)
    hay = False
    if not can.hay_fallo:
        try:
            crudo = fuente.buscar(CANARIO_NORMA, CANARIO_PRECEPTO)
            filas = extraer_resultados(crudo)
            n, _tope = cuantos_resultados(crudo)
            if not filas:
                print("SIN RESULTADOS")
                can.cambios.append(
                    "la busqueda respondio pero no se ha sabido leer ningun "
                    "criterio: o ha cambiado la plantilla, o ya no hay "
                    "criterios de ese precepto")
            else:
                hay = True
                print(f"SI   ({n} resultados)")
        except FuenteCaida as e:
            print(can.clasificar(e, "la busqueda"))
        except FormaInesperada as e:
            print("CAMBIO DE FORMA")
            can.cambios.append(f"la lista de resultados ha cambiado: {e}")
    else:
        print("(no se prueba)")

    print("  [3/3] el criterio se lee ........ ", end="", flush=True)
    if hay:
        try:
            campos = extraer_criterio(fuente.criterio(CANARIO_ID), CANARIO_ID,
                                      fuente.texto_resolucion(CANARIO_ID))
            print(f"SI   ({len(campos['criterio'])} caracteres, "
                  f"{len(campos['referencias'])} norma(s) citadas)")
        except FuenteCaida as e:
            print(can.clasificar(e, "la peticion del criterio"))
        except FormaInesperada as e:
            print("CAMBIO DE FORMA")
            can.cambios.append(f"el criterio ha cambiado de forma: {e}")
    else:
        print("(no se prueba)")

    return can.informar()


# ----------------------------------------------------------------------- cli


def main(argv: list[str]) -> int:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(
        description="Cliente del TEAC (DYCTEA). Solo descarga y cache.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest="modo", required=True)

    b = sub.add_parser("buscar", help="criterios por norma y precepto")
    b.add_argument("--norma", required=True)
    b.add_argument("--precepto", default="")
    b.add_argument("--paginas", type=int, default=3)
    b.add_argument("--vinculantes", action="store_true",
                   help="solo criterios vinculantes (c=1) en vez de todos")
    b.add_argument("--detalle", action="store_true")
    b.set_defaults(func=modo_buscar)

    c = sub.add_parser("criterio", help="traer un criterio")
    c.add_argument("id")
    c.add_argument("--completo", action="store_true")
    c.add_argument("--solo-cache", action="store_true", dest="solo_cache")
    c.set_defaults(func=modo_criterio)

    k = sub.add_parser("cache")
    k.add_argument("--tope", type=int, default=40)
    k.set_defaults(func=modo_cache)

    n = sub.add_parser("canario")
    n.set_defaults(func=modo_canario)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\ninterrumpido")
        return 130


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
