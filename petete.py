#!/usr/bin/env python3
"""CLIENTE DE PETETE — las consultas de la Direccion General de Tributos.

    python petete.py buscar "creditos incobrables concurso"
    python petete.py consulta V1601-22
    python petete.py cache
    python petete.py canario

FASE 9A. Esto SOLO descarga y guarda. No se integra con el agente, no toca el
motor, ni el verificador, ni la interfaz. Eso es la 9B.

NO GASTA NI UNA LLAMADA A LA API DE ANTHROPIC.

----------------------------------------------------------------------------
LA CACHE ES EL PRODUCTO
----------------------------------------------------------------------------
Todo lo que se baja se guarda y no se vuelve a pedir. Se guardan DOS cosas,
como en la fase 1:

    el HTML crudo, tal cual llego, que no se toca nunca
    los campos extraidos, que se pueden rehacer desde el crudo

Si manana cambia el troceo, se reprocesa lo guardado sin volver a la web. Y con
veinte tardes de uso el departamento tiene su propia base de criterio en local,
que vale mas que la velocidad.

----------------------------------------------------------------------------
LA FUENTE ES LENTA Y SE CAE. NO ES UNA SOSPECHA: ESTA MEDIDO
----------------------------------------------------------------------------
Medido los dias 2 y 3 de agosto de 2026 (ver FASE9.md):

    lo estatico              0,1 - 0,6 s
    /do/info                 18 - 24 s, y a ratos agota el tiempo
    /do/search               504 a los 60 s, y luego 502 inmediato

Por eso aqui NADA se queda colgado: tiempo maximo por peticion, reintentos con
tope, pausa entre peticiones, y cuando la fuente no responde SE DICE. Nunca en
silencio y nunca a medias.

----------------------------------------------------------------------------
EL NUMERO Y EL ID NO SON LO MISMO
----------------------------------------------------------------------------
"V1601-22" es lo que usa la gente. El documento tiene ademas un identificador
interno que solo aparece en los resultados de busqueda. Se guarda el mapeo entre
los dos en el indice: sin el, cada consulta costaria una busqueda extra para
siempre.
"""

from __future__ import annotations

import argparse
import hashlib
import html as _html
import http.cookiejar
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DIR = RAIZ / "datos" / "dgt"
DIR_CRUDO = DIR / "crudo"
DIR_CONSULTAS = DIR / "consultas"
DIR_BUSQUEDAS = DIR / "busquedas"
INDICE = DIR / "indice.json"

BASE = "https://petete.tributos.hacienda.gob.es/consultas"
URL_NAVEGADOR = BASE + "/?num_consulta={num}"

# El intermedio de la FNMT. El servidor manda su certificado SIN la cadena
# completa, asi que un cliente estricto no lo puede verificar. La respuesta NO
# es desactivar la comprobacion -eso tiraria lo unico que garantiza que el
# criterio viene de quien dice- sino aportar el eslabon que falta.
CERT_FNMT = RAIZ / "agente_fiscal" / "certificados" / "fnmt_ac_componentes.pem"

UA = ("agente-fiscal-gestoria/1.0 (cliente de consulta de una gestoria; "
      "uso interno y volumen bajo)")

ESPERA = 45          # segundos maximos por peticion
REINTENTOS = 3       # y no mas
PAUSA = 4.0          # segundos entre peticiones, siempre
PAUSA_REINTENTO = 8.0

ANCHO = 78

# Los campos del formulario, comprobados contra el formulario real (fase 9).
CAMPO = {
    1: "NUM-CONSULTA", 2: "FECHA-SALIDA", 3: "NORMATIVA",
    4: "CUESTION-PLANTEADA", 5: "DESCRIPCION-HECHOS", 6: "FreeText",
    7: "CRITERIO",
}
TAB_GENERALES, TAB_VINCULANTES = "1", "2"

RE_NUM = re.compile(r"^[VC]?\d{3,5}-\d{2}$", re.I)


# --------------------------------------------------------------------- salida


def titulo(t: str) -> None:
    print("=" * ANCHO)
    print(f"  {t}")
    print("=" * ANCHO)


def aviso(t: str) -> None:
    print(f"\n[!] {t}")


class FuenteCaida(Exception):
    """La fuente no responde o responde mal. Se dice, no se disimula.

    `codigo` es el HTTP que devolvio, si llego a devolver alguno. Sirve para
    distinguir DE QUIEN es el fallo, que es justo lo que antes no se sabia:
    un 5xx es de su servidor y un 4xx es nuestro, por preguntar mal.
    """

    def __init__(self, mensaje: str, codigo: int | None = None):
        super().__init__(mensaje)
        self.codigo = codigo


class FormaInesperada(Exception):
    """La fuente responde, pero no tiene la forma que esperabamos.

    Es un error DISTINTO de que este caida, y por eso tiene su propia clase:
    estos endpoints son internos y sin documentar, y pueden cambiar cualquier
    martes. Si cambian, hay que parar y mirarlo, no guardar lo que salga.
    """


# ------------------------------------------------------------------- la fuente


@dataclass
class Respuesta:
    codigo: int
    cuerpo: str
    segundos: float
    url: str


class Fuente:
    """El unico sitio que habla con la red. Con pausas y con tope."""

    def __init__(self, espera: int = ESPERA, reintentos: int = REINTENTOS,
                 pausa: float = PAUSA, silencioso: bool = False):
        self.espera = espera
        self.reintentos = reintentos
        self.pausa = pausa
        self.silencioso = silencioso
        self.peticiones = 0
        self._ultima = 0.0

        ctx = ssl.create_default_context()
        if CERT_FNMT.is_file():
            ctx.load_verify_locations(cafile=str(CERT_FNMT))
        self.ctx = ctx
        self.op = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
            urllib.request.HTTPSHandler(context=ctx),
        )
        self._sesion = False

    def _respirar(self) -> None:
        """Pausa entre peticiones. No es cortesia: es no tumbarles el servicio."""
        falta = self.pausa - (time.time() - self._ultima)
        if falta > 0 and self._ultima:
            time.sleep(falta)

    def pedir(self, ruta: str, datos=None, metodo: str = "GET") -> Respuesta:
        """Una peticion, con pausa y con tope.

        `datos` puede ser un dict o una lista de pares. La LISTA importa: el
        buscador recibe los campos en un orden concreto y un dict no garantiza
        ninguno. Con GET los datos van en la URL, que es como los manda la
        propia aplicacion.
        """
        url = f"{BASE}{ruta}"
        cuerpo = None
        if datos:
            codificado = urllib.parse.urlencode(datos)
            if metodo.upper() == "GET":
                url = f"{url}?{codificado}"
            else:
                cuerpo = codificado.encode()
        ultimo = ""
        ultimo_codigo = None
        for intento in range(1, self.reintentos + 1):
            self._respirar()
            req = urllib.request.Request(url, data=cuerpo, headers={
                "User-Agent": UA,
                "Accept-Language": "es-ES,es;q=0.9",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{BASE}/",
            })
            t0 = time.time()
            try:
                with self.op.open(req, timeout=self.espera) as r:
                    texto = r.read().decode("utf-8", "replace")
                self.peticiones += 1
                self._ultima = time.time()
                return Respuesta(200, texto, time.time() - t0, url)
            except urllib.error.HTTPError as e:
                ultimo = f"el servidor respondio {e.code}"
                ultimo_codigo = e.code
                self.peticiones += 1
            except urllib.error.URLError as e:
                ultimo = f"no se pudo conectar ({getattr(e, 'reason', e)})"
            except TimeoutError:
                ultimo = f"no contesto en {self.espera} segundos"
            except Exception as e:  # noqa: BLE001
                ultimo = f"{type(e).__name__}"
            self._ultima = time.time()
            if not self.silencioso and intento < self.reintentos:
                print(f"    reintento {intento}/{self.reintentos - 1}: {ultimo}")
            if intento < self.reintentos:
                time.sleep(PAUSA_REINTENTO)
        raise FuenteCaida(ultimo or "sin respuesta", ultimo_codigo)

    def sesion(self) -> None:
        """Abre sesion pidiendo la pagina del buscador. Una sola vez."""
        if not self._sesion:
            self.pedir("/")
            self._sesion = True

    # ------------------------------------------------------------- consultas

    def _campos(self, terminos: str, numero: str, tab: str, pagina: int,
                orden: str = "FECHA-SALIDA", direccion: str = "1") -> list:
        """Los parametros de una busqueda, EN EL MISMO ORDEN que los manda la
        aplicacion.

        Copiados de una busqueda real capturada en el navegador (3 de agosto de
        2026). Se mandan los dos `type`, como hace el formulario, y `dirOrder`
        va en 0/1 y no en «asc»/«desc», que es lo que vale el desplegable.

        POR DEFECTO SE ORDENA POR FECHA, DE LA MAS RECIENTE A LA MAS ANTIGUA.
        El buscador NO ordena por relevancia -solo deja elegir entre numero de
        consulta, organo y fecha-, y ordenar por numero mezcla los años sin
        criterio: la primera pagina salia con consultas de 2006 y de 2025
        revueltas. Con fecha descendente, lo primero que se ve es el criterio
        vigente, que es el que manda.
        """
        return [
            ("type1", "on"), ("type2", "on"),
            ("NMCMP_1", "NUM-CONSULTA"), ("VLCMP_1", numero), ("OPCMP_1", ".Y"),
            ("NMCMP_2", "FECHA-SALIDA"), ("VLCMP_2", ""), ("dateIni_2", ""),
            ("OPCMP_2", ".Y"),
            ("NMCMP_3", "NORMATIVA"), ("VLCMP_3", ""), ("OPCMP_3", ".Y"),
            ("NMCMP_4", "CUESTION-PLANTEADA"), ("VLCMP_4", ""), ("OPCMP_4", ".Y"),
            ("NMCMP_5", "DESCRIPCION-HECHOS"), ("VLCMP_5", ""), ("OPCMP_5", ".Y"),
            ("NMCMP_6", "FreeText"), ("VLCMP_6", terminos), ("OPCMP_6", ".Y"),
            ("NMCMP_7", "CRITERIO"),
            ("cmpOrder", orden), ("dirOrder", direccion), ("auto", ""),
            ("tab", tab), ("page", str(pagina)),
        ]

    def buscar(self, terminos: str = "", numero: str = "",
               tab: str = TAB_VINCULANTES, pagina: int = 1) -> str:
        """POR GET, no por POST.

        Esto costo un canario en rojo y una acusacion injusta a la fuente. El
        JavaScript de la aplicacion llama a `$(...).load(url, params, cb)` con
        `params` como CADENA, y jQuery, cuando los parametros son una cadena,
        hace GET con ellos en la URL; solo hace POST si le pasas un objeto.
        Nosotros mandabamos POST. Comprobado capturando la peticion real en el
        navegador: sale un GET con la query entera detras.
        """
        self.sesion()
        return self.pedir("/do/search", self._campos(terminos, numero, tab,
                                                     pagina)).cuerpo

    def documento(self, doc_id: str, tab: str = TAB_VINCULANTES,
                  query: str = "") -> str:
        """Tambien por GET, y por el mismo motivo que `buscar`.

        `query` es el campo oculto que la pagina de resultados arrastra hasta
        aqui. Se manda si lo tenemos: es como lo pide la propia aplicacion.
        """
        self.sesion()
        datos = ([("query", query)] if query else []) + [
            ("doc", str(doc_id)), ("tab", str(tab))]
        return self.pedir("/do/document", datos).cuerpo


# ------------------------------------------------------------------- extraer


def _texto(fragmento: str) -> str:
    """HTML -> texto legible, sin etiquetas y sin espacios de sobra."""
    t = re.sub(r"<script.*?</script>", " ", fragmento, flags=re.S | re.I)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</(p|div|tr|li|h\d)>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = _html.unescape(t)
    t = re.sub(r"[ \t\xa0]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n\n", t).strip()


# Como se rotula cada campo en la pagina del documento. Se buscan por ETIQUETA
# y no por posicion: la posicion cambia en cuanto tocan la plantilla, la
# etiqueta es lo que lee una persona y sobrevive mas.
ETIQUETAS = {
    "numero": ("num. consulta", "nº consulta", "numero de consulta",
               "num-consulta", "n. consulta"),
    "organo": ("organo", "órgano"),
    "fecha": ("fecha salida", "fecha de salida", "fecha-salida"),
    "normativa": ("normativa", "normativa aplicable", "normativa/doctrina"),
    "descripcion": ("descripcion de hechos", "descripción de hechos",
                    "descripcion-hechos", "descripcion sucinta"),
    "cuestion": ("cuestion planteada", "cuestión planteada",
                 "cuestion-planteada"),
    "contestacion": ("contestacion completa", "contestación completa",
                     "contestacion", "contestación"),
}

# Campos sin los cuales un registro no vale para nada. Si faltan, se para.
IMPRESCINDIBLES = ("numero", "contestacion")


def _normaliza(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]", " ", s.lower()).strip()


# Como se llama cada campo en el marcado REAL, capturado el 3 de agosto de
# 2026 sobre V1601-22. La pagina del documento es una tabla y cada campo es una
# fila con su clase:
#
#   <tr class="CONTESTACION-COMPL">
#     <th scope="row" class="field">Contestación completa</th>
#     <td class="value">
#        <p class="CONTESTACION-COMPL">...</p>   (14 parrafos en este caso)
#     </td>
#   </tr>
#
# Se ancla en la CLASE y no en la etiqueta visible. La etiqueta cambia con
# cualquier retoque de redaccion -y de hecho nuestra suposicion inicial fallo
# por eso: pusimos "Nº CONSULTA" y la real es "Nº de consulta"-, mientras que
# la clase es la que usa su propia hoja de estilos.
CLASES = {
    "numero": "NUM-CONSULTA",
    "organo": "ORGANO",
    "fecha": "FECHA-SALIDA",
    "normativa": "NORMATIVA",
    "descripcion": "DESCRIPCION-HECHOS",
    "cuestion": "CUESTION-PLANTEADA",
    "contestacion": "CONTESTACION-COMPL",
}


def _por_clases(crudo: str) -> dict:
    """Los campos, leidos de las filas con clase. Devuelve {} si no hay ninguna."""
    campos: dict = {}
    for nombre, clase in CLASES.items():
        m = re.search(
            r'<tr[^>]*class="[^"]*\b' + re.escape(clase) + r'\b[^"]*"[^>]*>(.*?)</tr>',
            crudo, re.S | re.I)
        if not m:
            continue
        fila = m.group(1)
        # Dentro de la fila, solo la celda de valor: el <th> es el rotulo.
        mv = re.search(r'<td[^>]*class="[^"]*\bvalue\b[^"]*"[^>]*>(.*?)</td>',
                       fila, re.S | re.I)
        valor = _texto(mv.group(1) if mv else fila)
        if valor:
            campos[nombre] = valor
    return campos


def extraer(crudo: str, numero_pedido: str = "") -> dict:
    """HTML de un documento -> campos. Si no reconoce la forma, PARA.

    Dos caminos, en este orden:
      1. las CLASES de la tabla, que es como viene el documento real;
      2. si no hay ninguna, las etiquetas visibles, por si algun dia cambian
         el marcado y dejan solo los rotulos.

    Si no sale ni por una ni por otra, lanza FormaInesperada en vez de guardar
    un registro medio vacio: un criterio fiscal a medias es peor que ninguno.
    """
    campos_clase = _por_clases(crudo)
    if campos_clase:
        campos = {k: "" for k in ETIQUETAS}
        campos.update(campos_clase)
        if not campos["numero"] and numero_pedido:
            campos["numero"] = numero_pedido
        faltan = [c for c in IMPRESCINDIBLES if not campos[c]]
        if faltan:
            raise FormaInesperada(
                f"el documento trae la tabla de campos pero le faltan "
                f"{', '.join(faltan)}. Hay que mirar la pagina antes de "
                f"fiarse de lo que salga")
        campos["numero"] = campos["numero"].split()[0] if campos["numero"] else ""
        return campos

    texto = _texto(crudo)
    if not texto:
        raise FormaInesperada("el documento vino vacio")

    lineas = [l.strip() for l in texto.split("\n") if l.strip()]
    plano = [_normaliza(l) for l in lineas]

    campos: dict = {k: "" for k in ETIQUETAS}
    # Se recorre de arriba abajo: cada etiqueta abre una seccion que dura
    # hasta la siguiente etiqueta conocida.
    posiciones = []
    for i, l in enumerate(plano):
        for clave, rotulos in ETIQUETAS.items():
            for r in rotulos:
                rn = _normaliza(r)
                if l.startswith(rn):
                    posiciones.append((i, clave, len(rn)))
                    break
            else:
                continue
            break

    for j, (i, clave, largo) in enumerate(posiciones):
        fin = posiciones[j + 1][0] if j + 1 < len(posiciones) else len(lineas)
        primera = lineas[i][largo:].lstrip(" :.-\t")
        trozos = ([primera] if primera else []) + lineas[i + 1:fin]
        valor = "\n".join(t for t in trozos if t).strip()
        if valor and not campos[clave]:
            campos[clave] = valor

    if not campos["numero"] and numero_pedido:
        campos["numero"] = numero_pedido

    faltan = [c for c in IMPRESCINDIBLES if not campos[c]]
    if faltan:
        raise FormaInesperada(
            f"no se reconocen los campos {', '.join(faltan)} en el documento. "
            f"La pagina de PETETE puede haber cambiado de forma: hay que "
            f"mirarla antes de fiarse de nada de lo que salga."
        )

    campos["numero"] = campos["numero"].split()[0] if campos["numero"] else ""
    return campos


def extraer_resultados(crudo: str) -> list[dict]:
    """Lista de resultados de una busqueda -> [{numero, doc_id, ...}].

    El id interno sale de las llamadas viewDocument(...) que el propio KnoSys
    pone en cada fila. Es el unico sitio donde aparece.
    """
    if "viewDocument" not in crudo:
        # Puede ser legitimo (cero resultados) o que hayan cambiado la
        # plantilla. Se distingue mirando si dice algo de resultados.
        if re.search(r"(?i)(sin resultados|no se han encontrado|0 documentos)",
                     crudo):
            return []
        raise FormaInesperada(
            "la lista de resultados no trae ningun 'viewDocument': o no hay "
            "resultados y no lo dice como esperabamos, o han cambiado la "
            "plantilla del buscador"
        )

    # El marcado real, capturado el 3 de agosto de 2026:
    #
    #   <td id="doc_45970" onClick="return viewDocument(45970, 2);" ...>
    #     <h4><span class="NUM-CONSULTA"><strong> V1601-22 </strong></span></h4>
    #     <span class="DESCRIPCION-HECHOS"> ... </span>
    #
    # El id va SIN COMILLAS. La version anterior las exigia y por eso no
    # encontraba nada aunque la busqueda respondiera bien. Y el numero se saca
    # de la clase NUM-CONSULTA, que es semantica y aguanta mas que buscar un
    # patron suelto en el texto de la fila.
    salida = []
    # El (?<![A-Za-z]) es necesario: cada fila trae ademas un
    # onKeyDown="keyViewDocument(45970, 2)" para navegar con el teclado, y sin
    # el limite cada consulta salia DOS veces.
    for m in re.finditer(
        r"(?<![A-Za-z])viewDocument\(\s*['\"]?(?P<id>[^,'\")\s]+)['\"]?"
        r"\s*,\s*['\"]?(?P<tab>\d+)",
        crudo, re.IGNORECASE,
    ):
        ini = crudo.rfind("<td", 0, m.start())
        fin = crudo.find("</td>", m.start())
        celda = crudo[ini if ini >= 0 else m.start(): fin if fin > 0 else m.end()]

        num = ""
        mn = re.search(r'class="NUM-CONSULTA"[^>]*>(.*?)</span>', celda,
                       re.S | re.I)
        if mn:
            num = _texto(mn.group(1)).strip()
        if not num:   # respaldo: el patron suelto, por si cambian la clase
            mm = re.search(r"\b([VC]?\d{3,5}-\d{2})\b", _texto(celda))
            num = mm.group(1) if mm else ""

        salida.append({"doc_id": m.group("id"), "tab": m.group("tab"),
                       "numero": num.upper(),
                       "resumen": _texto(celda)[:180]})
    return salida


def extraer_consulta_query(crudo: str) -> str:
    """El campo oculto `query` de una pagina de resultados.

    La aplicacion lo arrastra a la peticion del documento (su JavaScript hace
    `query + "&doc=" + doc + "&tab=" + tab`), asi que se manda tambien: pedir
    el documento sin el es preguntar de una forma que ellos nunca usan.
    """
    m = re.search(r'id="query"[^>]*value="([^"]*)"', crudo, re.I)
    if not m:
        m = re.search(r'name="query"[^>]*value="([^"]*)"', crudo, re.I)
    return _html.unescape(m.group(1)) if m else ""


# --------------------------------------------------------------------- cache


class Cache:
    """El crudo, los campos y el mapeo numero <-> id interno."""

    def __init__(self):
        for d in (DIR_CRUDO, DIR_CONSULTAS, DIR_BUSQUEDAS):
            d.mkdir(parents=True, exist_ok=True)
        self.indice = self._leer_indice()

    @staticmethod
    def _leer_indice() -> dict:
        if INDICE.is_file():
            try:
                return json.loads(INDICE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                aviso("el indice estaba corrupto; se empieza uno nuevo "
                      "(el crudo y las consultas siguen ahi)")
        return {"consultas": {}, "creado": _ahora()}

    def _guardar_indice(self) -> None:
        INDICE.write_text(json.dumps(self.indice, ensure_ascii=False, indent=2),
                          encoding="utf-8")

    # ------------------------------------------------------------ consultas

    def tiene(self, numero: str) -> bool:
        return (DIR_CONSULTAS / f"{numero.upper()}.json").is_file()

    def leer(self, numero: str) -> dict | None:
        f = DIR_CONSULTAS / f"{numero.upper()}.json"
        if not f.is_file():
            return None
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def doc_id(self, numero: str) -> str:
        return self.indice["consultas"].get(numero.upper(), {}).get("doc_id", "")

    def apuntar_id(self, numero: str, doc_id: str, tab: str) -> None:
        """El mapeo numero -> id interno. Sin esto, cada consulta costaria una
        busqueda extra para siempre."""
        if not numero or not doc_id:
            return
        ficha = self.indice["consultas"].setdefault(numero.upper(), {})
        ficha["doc_id"] = doc_id
        ficha["tab"] = tab
        ficha.setdefault("visto", _ahora())
        self._guardar_indice()

    def guardar(self, numero: str, crudo: str, campos: dict, doc_id: str,
                tab: str) -> dict:
        numero = (numero or campos.get("numero") or "").upper()
        if not numero:
            raise FormaInesperada("el documento no trae numero de consulta")

        # 1) el crudo, tal cual llego, que no se toca nunca
        f_crudo = DIR_CRUDO / f"{numero}.html"
        f_crudo.write_text(crudo, encoding="utf-8")
        sha = hashlib.sha256(crudo.encode("utf-8")).hexdigest()

        # 2) los campos, que se pueden rehacer desde el crudo
        registro = {
            "numero": numero,
            "fecha": campos.get("fecha", ""),
            "organo": campos.get("organo", ""),
            "normativa": campos.get("normativa", ""),
            "cuestion_planteada": campos.get("cuestion", ""),
            "descripcion_hechos": campos.get("descripcion", ""),
            "contestacion": campos.get("contestacion", ""),
            "doc_id": doc_id,
            "tab": tab,
            # El enlace que se le ensena a una persona para comprobarlo. NO es
            # de donde sale el texto: ver el desdoblamiento en el LEEME.
            "url_navegador": URL_NAVEGADOR.format(num=numero),
            "descargado": _ahora(),
            "sha256_crudo": sha,
            # Relativa si cuelga del proyecto, absoluta si no. Guardar la ruta
            # no puede ser motivo de que se pierda una descarga.
            "crudo": str(f_crudo.relative_to(RAIZ)
                         if f_crudo.is_relative_to(RAIZ) else f_crudo),
        }
        (DIR_CONSULTAS / f"{numero}.json").write_text(
            json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")

        ficha = self.indice["consultas"].setdefault(numero, {})
        ficha.update({"doc_id": doc_id, "tab": tab,
                      "descargado": registro["descargado"],
                      "fecha": registro["fecha"]})
        self._guardar_indice()
        return registro

    # ------------------------------------------------------------ busquedas

    @staticmethod
    def _clave_busqueda(terminos: str, tab: str) -> str:
        return hashlib.sha256(f"{tab}|{terminos.strip().lower()}"
                              .encode("utf-8")).hexdigest()[:16]

    def busqueda(self, terminos: str, tab: str) -> list | None:
        f = DIR_BUSQUEDAS / f"{self._clave_busqueda(terminos, tab)}.json"
        if not f.is_file():
            return None
        try:
            return json.loads(f.read_text(encoding="utf-8"))["resultados"]
        except (json.JSONDecodeError, KeyError):
            return None

    def guardar_busqueda(self, terminos: str, tab: str, resultados: list) -> None:
        f = DIR_BUSQUEDAS / f"{self._clave_busqueda(terminos, tab)}.json"
        f.write_text(json.dumps(
            {"terminos": terminos, "tab": tab, "cuando": _ahora(),
             "resultados": resultados}, ensure_ascii=False, indent=2),
            encoding="utf-8")


def _ahora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ----------------------------------------------------------------- los modos


def obtener_consulta(numero: str, cache: Cache, fuente: Fuente | None,
                     verboso: bool = True) -> tuple[dict, str]:
    """Devuelve (registro, origen). origen es 'cache' o 'red'.

    Si esta en cache NO se toca la red. Es la regla de la fase 9A.
    """
    numero = numero.upper()
    guardada = cache.leer(numero)
    if guardada:
        return guardada, "cache"

    if fuente is None:
        raise FuenteCaida("no esta en la cache y no se ha permitido salir a la red")

    doc_id = cache.doc_id(numero)
    tab = cache.indice["consultas"].get(numero, {}).get("tab", TAB_VINCULANTES)

    if not doc_id:
        if verboso:
            print(f"  no esta en cache: hay que buscar el id interno de {numero}")
        tab = TAB_VINCULANTES if numero.upper().startswith("V") else TAB_GENERALES
        crudo = fuente.buscar(numero=numero, tab=tab)
        resultados = extraer_resultados(crudo)
        for r in resultados:
            if r["numero"]:
                cache.apuntar_id(r["numero"], r["doc_id"], tab)
        elegido = next((r for r in resultados
                        if r["numero"].upper() == numero), None)
        if elegido is None:
            raise FuenteCaida(
                f"la busqueda no devolvio la consulta {numero}. Puede que no "
                f"exista con ese numero, o que este en la otra base de datos "
                f"(generales / vinculantes)")
        doc_id = elegido["doc_id"]

    if verboso:
        print(f"  descargando el documento (id interno {doc_id})")
    crudo = fuente.documento(doc_id, tab)
    campos = extraer(crudo, numero)
    return cache.guardar(numero, crudo, campos, doc_id, tab), "red"


def modo_consulta(args) -> int:
    numero = args.numero.upper()
    if not RE_NUM.match(numero):
        print(f"'{numero}' no parece un numero de consulta. Se escriben como "
              f"V1601-22 o 0123-20.")
        return 2

    titulo(f"CONSULTA {numero}")
    cache = Cache()
    fuente = None if args.solo_cache else Fuente(silencioso=False)
    try:
        registro, origen = obtener_consulta(numero, cache, fuente)
    except FuenteCaida as e:
        aviso(f"No se ha podido traer la consulta: {e}")
        if args.solo_cache:
            # No se ha llamado a nadie: decir que la fuente no responde seria
            # mentir, y las dos situaciones se arreglan de forma distinta.
            print("\n  No se ha salido a la red porque lo has pedido con "
                  "--solo-cache.\n  Quita esa opcion para intentar traerla.")
        else:
            print("\n  La fuente de la DGT no responde. Lo que ya este en la "
                  "cache\n  se sigue pudiendo consultar con --solo-cache.")
        return 1
    except FormaInesperada as e:
        aviso(f"PETETE ha respondido con una forma que no reconozco: {e}")
        print("\n  NO se ha guardado nada. Hay que mirar la pagina a mano "
              "antes\n  de volver a fiarse de lo que devuelva.")
        return 3

    print(f"\norigen: {origen.upper()}"
          + ("   (no se ha tocado la red)" if origen == "cache" else ""))
    _pintar(registro, completo=args.completo)
    return 0


def _pintar(r: dict, completo: bool = False) -> None:
    def bloque(rotulo, texto, tope=400):
        if not texto:
            return
        print(f"\n{rotulo}")
        print("-" * len(rotulo))
        t = texto if completo else (texto[:tope] + ("…" if len(texto) > tope else ""))
        for linea in t.split("\n"):
            print(f"  {linea}")

    print(f"\n  numero    : {r['numero']}")
    print(f"  fecha     : {r.get('fecha') or '(no consta)'}")
    print(f"  organo    : {r.get('organo') or '(no consta)'}")
    print(f"  id interno: {r.get('doc_id') or '(no consta)'}")
    print(f"  enlace    : {r.get('url_navegador','')}")
    print(f"  descargado: {r.get('descargado','')}")
    bloque("NORMATIVA CITADA", r.get("normativa", ""))
    bloque("DESCRIPCION DE HECHOS", r.get("descripcion_hechos", ""))
    bloque("CUESTION PLANTEADA", r.get("cuestion_planteada", ""))
    bloque("CONTESTACION", r.get("contestacion", ""), tope=900)
    if not completo:
        print("\n  (--completo para el texto entero)")


def modo_buscar(args) -> int:
    terminos = args.terminos.strip()
    tab = TAB_GENERALES if args.generales else TAB_VINCULANTES
    titulo(f"BUSCAR  «{terminos}»")
    cache = Cache()

    guardada = cache.busqueda(terminos, tab)
    if guardada is not None and not args.refrescar:
        print("origen: CACHE   (no se ha tocado la red)")
        resultados = guardada
    else:
        fuente = Fuente()
        try:
            crudo = fuente.buscar(terminos=terminos, tab=tab)
            resultados = extraer_resultados(crudo)
        except FuenteCaida as e:
            aviso(f"La fuente de la DGT no responde: {e}")
            print("\n  No se ha podido buscar. Las consultas ya descargadas "
                  "siguen\n  disponibles: python petete.py cache")
            return 1
        except FormaInesperada as e:
            aviso(f"PETETE ha cambiado de forma: {e}")
            return 3
        for r in resultados:
            if r["numero"]:
                cache.apuntar_id(r["numero"], r["doc_id"], tab)
        cache.guardar_busqueda(terminos, tab, resultados)
        print(f"origen: RED   ({fuente.peticiones} peticion(es))")

    print(f"\n{len(resultados)} resultado(s)"
          + ("  —  en " + ("consultas generales" if tab == TAB_GENERALES
                           else "consultas vinculantes")))
    if not resultados:
        print("\n  Sin resultados. Prueba con menos palabras o con los "
              "terminos de la ley.")
        return 0
    print()
    for i, r in enumerate(resultados[:args.tope], 1):
        en_cache = "  [en cache]" if cache.tiene(r["numero"]) else ""
        print(f"  {i:2d}. {r['numero'] or '(sin numero)':12s} "
              f"id={r['doc_id']:>10s}{en_cache}")
        if r.get("resumen"):
            print(f"      {r['resumen'][:96]}")
    if len(resultados) > args.tope:
        print(f"\n  ... y {len(resultados) - args.tope} mas "
              f"(--tope para ver mas)")
    print(f"\n  Para traer una:  python petete.py consulta <numero>")
    return 0


def modo_cache(args) -> int:
    titulo("LA CACHE DE CRITERIO")
    cache = Cache()
    consultas = sorted(DIR_CONSULTAS.glob("*.json"))
    crudos = list(DIR_CRUDO.glob("*.html"))
    busquedas = list(DIR_BUSQUEDAS.glob("*.json"))
    mapeos = len(cache.indice.get("consultas", {}))

    bytes_crudo = sum(f.stat().st_size for f in crudos)
    print(f"\n  consultas guardadas : {len(consultas)}")
    print(f"  documentos crudos   : {len(crudos)}  ({bytes_crudo/1024:.0f} KB)")
    print(f"  busquedas guardadas : {len(busquedas)}")
    print(f"  numeros con id      : {mapeos}   "
          f"(cada uno ahorra una busqueda para siempre)")
    print(f"\n  carpeta: {DIR}")

    if not consultas:
        print("\n  Todavia no hay nada. Trae una:")
        print("    python petete.py consulta V1601-22")
        return 0

    print(f"\n  {'numero':12s} {'fecha':12s} {'descargado':21s} normativa")
    print("  " + "-" * 72)
    for f in consultas[:args.tope]:
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  {f.stem:12s}  (fichero ilegible)")
            continue
        print(f"  {r.get('numero',''):12s} {(r.get('fecha') or '-')[:12]:12s} "
              f"{r.get('descargado',''):21s} "
              f"{(r.get('normativa') or '-')[:30]}")
    if len(consultas) > args.tope:
        print(f"  ... y {len(consultas) - args.tope} mas")
    return 0


# ------------------------------------------------------------------- canario


CANARIO_NUM = "V1601-22"


def _dias_de_certificado() -> int | None:
    """Dias que le quedan al certificado del servidor. None si no se puede ver.

    Se mira porque el 26-09-2026 caduca el actual, y al renovarlo pueden
    arreglar la cadena incompleta... o cambiarla por otra cosa. Enterarnos por
    el canario es barato; enterarnos porque el departamento no puede trabajar,
    no.
    """
    import socket
    from datetime import datetime as _dt

    host = urllib.parse.urlparse(BASE).hostname or ""
    try:
        ctx = ssl.create_default_context()
        # Solo se quiere LEER la fecha del certificado: si la cadena esta
        # incompleta no debe impedir mirarla.
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((host, 443), timeout=15) as s:
            with ctx.wrap_socket(s, server_hostname=host) as ss:
                der = ss.getpeercert(binary_form=True)
        texto = ssl.DER_cert_to_PEM_cert(der)
        # `getpeercert()` con validacion desactivada no da el dict, asi que se
        # decodifica el DER con la utilidad de la propia biblioteca.
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as f:
            f.write(texto)
            ruta = f.name
        datos = ssl._ssl._test_decode_cert(ruta)  # noqa: SLF001
        Path(ruta).unlink(missing_ok=True)
        fin = _dt.strptime(datos["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(
            tzinfo=timezone.utc)
        return (fin - datetime.now(timezone.utc)).days
    except Exception:  # noqa: BLE001
        return None


def modo_canario(args) -> int:
    """Comprueba que la fuente sigue donde estaba y con la forma de siempre.

    Estos endpoints son internos y sin documentar: pueden cambiar cualquier
    martes sin que nadie avise. El canario es lo que hace que nos enteremos
    nosotros antes que el departamento fiscal.
    """
    titulo("CANARIO DE LA FUENTE (DGT / PETETE)")
    print(f"\n  fuente : {BASE}")
    print(f"  patron : consulta {CANARIO_NUM}\n")

    # Tres cubos distintos a proposito. Meterlos todos en "fallos" es lo que
    # hizo que un bug nuestro se leyera como una caida de la fuente.
    fallos = []          # es de ELLOS: su servidor no responde o se atraganta
    culpa_nuestra = []   # es NUESTRO: preguntamos mal y nos lo rechazan
    cambios = []         # la fuente cambio de forma: hay que mirarla
    avisos_ = []
    fuente = Fuente(silencioso=True)

    # 0. el certificado, que caduca y no lo mira nadie hasta que rompe
    if not CERT_FNMT.is_file():
        avisos_.append("falta el certificado intermedio de la FNMT: la "
                       "verificacion estricta va a fallar")
    dias = _dias_de_certificado()
    if dias is None:
        avisos_.append("no se ha podido leer la fecha de caducidad del "
                       "certificado del servidor")
    elif dias < 0:
        fallos.append(f"el certificado del servidor CADUCO hace {-dias} dias")
    elif dias < 30:
        avisos_.append(f"el certificado del servidor caduca en {dias} dias: "
                       f"cuando lo renueven puede cambiar la cadena")

    # 2. responde lo estatico
    print("  [1/3] el sitio responde ......... ", end="", flush=True)
    try:
        r = fuente.pedir("/do/form")
        print(f"SI   ({r.segundos:.1f}s)")
    except FuenteCaida as e:
        print("NO")
        fallos.append(f"el formulario no responde: {e}")

    # 3. la busqueda sigue devolviendo la consulta patron
    print("  [2/3] la busqueda funciona ...... ", end="", flush=True)
    doc_id = ""
    consulta_query = ""
    if not fallos:
        try:
            crudo = fuente.buscar(numero=CANARIO_NUM)
            resultados = extraer_resultados(crudo)
            elegido = next((x for x in resultados
                            if x["numero"].upper() == CANARIO_NUM), None)
            if elegido is None:
                # Respondio. Que no sepamos leerlo NO es que la fuente este
                # caida: o han cambiado la plantilla o la consulta ya no esta.
                print("SIN EL PATRON")
                cambios.append(
                    f"la busqueda respondio, pero {CANARIO_NUM} no estaba "
                    f"entre los {len(resultados)} resultados que hemos sabido "
                    f"leer. O ha cambiado la plantilla, o la consulta ya no "
                    f"esta donde estaba")
            else:
                doc_id = elegido["doc_id"]
                consulta_query = extraer_consulta_query(crudo)
                print(f"SI   (id {doc_id})")
        except FuenteCaida as e:
            # DE QUIEN ES EL FALLO. Antes esto decia siempre "la fuente no
            # responde", y con ese mensaje estuvimos culpando a la DGT de un
            # bug nuestro -mandabamos POST donde su aplicacion manda GET-.
            # El codigo HTTP lo distingue sin adivinar nada:
            #   4xx  su servidor entendio la peticion y la rechaza: es NUESTRA
            #   5xx  su servidor se atraganta: es SUYO
            #   sin codigo: no llego a contestar, no se puede saber de quien es
            codigo = getattr(e, "codigo", None)
            if codigo and 400 <= codigo < 500:
                print("RECHAZADA")
                culpa_nuestra.append(
                    f"la busqueda fue RECHAZADA con {codigo}: su servidor la "
                    f"entendio y no le gusta. El fallo es NUESTRO, no de la "
                    f"fuente: estamos preguntando mal")
            elif codigo and codigo >= 500:
                print("NO")
                fallos.append(
                    f"la busqueda fallo con {codigo}: es un error DE SU "
                    f"SERVIDOR. La peticion iba bien formada")
            else:
                print("SIN RESPUESTA")
                fallos.append(
                    f"la busqueda no llego a contestar ({e}). No se puede "
                    f"saber si el fallo es suyo o nuestro")
        except FormaInesperada as e:
            print("CAMBIO DE FORMA")
            cambios.append(f"la lista de resultados ha cambiado: {e}")
    else:
        print("(no se prueba)")

    # 4. el documento se puede leer y trae lo que esperamos
    print("  [3/3] el documento se lee ....... ", end="", flush=True)
    if doc_id:
        try:
            crudo = fuente.documento(doc_id, query=consulta_query)
            campos = extraer(crudo, CANARIO_NUM)
            if not campos.get("contestacion"):
                print("VACIO")
                fallos.append("el documento no trae contestacion")
            else:
                print(f"SI   ({len(campos['contestacion'])} caracteres)")
        except FuenteCaida as e:
            codigo = getattr(e, "codigo", None)
            if codigo and 400 <= codigo < 500:
                print("RECHAZADA")
                culpa_nuestra.append(
                    f"la peticion del documento fue rechazada con {codigo}: "
                    f"el fallo es NUESTRO")
            else:
                print("NO")
                fallos.append(f"el documento no responde: {e}")
        except FormaInesperada as e:
            print("CAMBIO DE FORMA")
            cambios.append(f"el documento ha cambiado de forma: {e}")
    else:
        print("(no se prueba)")

    print()
    print("=" * ANCHO)
    if culpa_nuestra:
        # Va PRIMERO porque es lo unico que podemos arreglar nosotros.
        print("  CANARIO EN ROJO — Y EL FALLO ES NUESTRO")
        print()
        for f in culpa_nuestra:
            print(f"    · {f}")
        print()
        print("  Que significa: la fuente esta bien. Somos nosotros los que")
        print("  preguntamos de una forma que no acepta. Se arregla en")
        print("  petete.py, no esperando a que la DGT arregle nada.")
    elif cambios:
        print("  CANARIO EN ROJO — LA FUENTE HA CAMBIADO DE FORMA")
        print()
        for f in cambios:
            print(f"    · {f}")
        print()
        print("  Que significa: responde, pero ya no devuelve lo que")
        print("  esperabamos. Estos endpoints son internos y sin documentar.")
        print("  Hay que mirar la pagina a mano antes de fiarse de nada.")
    elif fallos:
        print("  CANARIO EN ROJO — LA FUENTE NO RESPONDE")
        print()
        for f in fallos:
            print(f"    · {f}")
        print()
        print("  Que significa: el fallo es de su servidor, no de nuestra")
        print("  peticion. No hay nada que arreglar aqui: hay que esperar.")
        print("  El agente puede seguir contestando con la LEY; lo que no")
        print("  puede es anadir criterio de la DGT, y eso tiene que verse")
        print("  en pantalla, nunca quedarse en silencio.")
    else:
        print("  CANARIO EN VERDE — la fuente responde y tiene la forma de siempre")
    for a in avisos_:
        print(f"\n  aviso: {a}")
    print("=" * ANCHO)

    hay_fallo = bool(fallos or culpa_nuestra or cambios)
    # El estado queda escrito para que el agente sepa si puede contar con
    # criterio. "Preguntamos mal" tambien es fuente NO disponible.
    try:
        import sys as _s
        _s.path.insert(0, str(RAIZ))
        from agente_fiscal import dgt as _dgt
        motivo = (culpa_nuestra or cambios or fallos or [""])[0]
        _dgt.marcar_fuente(not hay_fallo, motivo[:200])
    except Exception:  # noqa: BLE001
        pass
    return 1 if hay_fallo else 0


# ----------------------------------------------------------------------- cli


def main(argv: list[str]) -> int:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(
        description="Cliente de PETETE (consultas de la DGT). Solo descarga y "
                    "cache: no toca el agente.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    sub = ap.add_subparsers(dest="modo", required=True)

    b = sub.add_parser("buscar", help="buscar consultas por terminos")
    b.add_argument("terminos")
    b.add_argument("--generales", action="store_true",
                   help="buscar en consultas generales en vez de vinculantes")
    b.add_argument("--refrescar", action="store_true",
                   help="ignorar la busqueda cacheada y volver a preguntar")
    b.add_argument("--tope", type=int, default=15)
    b.set_defaults(func=modo_buscar)

    c = sub.add_parser("consulta", help="traer una consulta por su numero")
    c.add_argument("numero")
    c.add_argument("--completo", action="store_true",
                   help="ensenar el texto entero, sin recortar")
    c.add_argument("--solo-cache", action="store_true", dest="solo_cache",
                   help="no salir a la red bajo ningun concepto")
    c.set_defaults(func=modo_consulta)

    k = sub.add_parser("cache", help="que hay guardado")
    k.add_argument("--tope", type=int, default=30)
    k.set_defaults(func=modo_cache)

    n = sub.add_parser("canario", help="comprobar que la fuente sigue viva")
    n.set_defaults(func=modo_canario)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\ninterrumpido")
        return 130


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
