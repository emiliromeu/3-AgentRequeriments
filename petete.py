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
    """La fuente no responde o responde mal. Se dice, no se disimula."""


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

    def pedir(self, ruta: str, datos: dict | None = None) -> Respuesta:
        url = f"{BASE}{ruta}"
        cuerpo = urllib.parse.urlencode(datos).encode() if datos else None
        ultimo = ""
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
        raise FuenteCaida(ultimo or "sin respuesta")

    def sesion(self) -> None:
        """El buscador quiere una sesion abierta. Se abre una sola vez."""
        if not self._sesion:
            self.pedir("/do/form")
            self._sesion = True

    # ------------------------------------------------------------- consultas

    def buscar(self, terminos: str = "", numero: str = "",
               tab: str = TAB_VINCULANTES, pagina: int = 1) -> str:
        self.sesion()
        campos = {f"NMCMP_{i}": n for i, n in CAMPO.items()}
        for i in range(1, 7):
            campos[f"VLCMP_{i}"] = ""
            campos[f"OPCMP_{i}"] = ".Y"
        campos["VLCMP_1"] = numero
        campos["VLCMP_6"] = terminos
        campos["type1" if tab == TAB_GENERALES else "type2"] = "on"
        campos.update({"cmpOrder": "FECHA-SALIDA", "dirOrder": "desc",
                       "auto": "", "tab": tab, "page": str(pagina)})
        return self.pedir("/do/search", campos).cuerpo

    def documento(self, doc_id: str, tab: str = TAB_VINCULANTES) -> str:
        self.sesion()
        return self.pedir("/do/document", {"doc": doc_id, "tab": tab}).cuerpo


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


def extraer(crudo: str, numero_pedido: str = "") -> dict:
    """HTML de un documento -> campos. Si no reconoce la forma, PARA.

    Se apoya en las etiquetas visibles, que son las mismas que declara el
    formulario de busqueda. Si la plantilla cambia y dejan de aparecer, esto
    lanza FormaInesperada en vez de guardar un registro medio vacio: un
    criterio fiscal a medias es peor que ninguno.
    """
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

    salida = []
    # viewDocument('ID', 'TAB') dentro de una fila; el numero de consulta esta
    # en el texto de la misma fila.
    for m in re.finditer(r"viewDocument\(\s*['\"]([^'\"]+)['\"]", crudo):
        doc_id = m.group(1)
        # contexto de la fila para sacar el numero visible
        ini = crudo.rfind("<tr", 0, m.start())
        fin = crudo.find("</tr>", m.start())
        fila = _texto(crudo[ini if ini >= 0 else m.start(): fin if fin > 0 else m.end()])
        num = ""
        mm = re.search(r"\b([VC]?\d{3,5}-\d{2})\b", fila)
        if mm:
            num = mm.group(1)
        salida.append({"doc_id": doc_id, "numero": num,
                       "resumen": fila[:180]})
    return salida


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

    fallos, avisos_ = [], []
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
    if not fallos:
        try:
            crudo = fuente.buscar(numero=CANARIO_NUM)
            resultados = extraer_resultados(crudo)
            elegido = next((x for x in resultados
                            if x["numero"].upper() == CANARIO_NUM), None)
            if elegido is None:
                print("NO")
                fallos.append(
                    f"la busqueda respondio pero {CANARIO_NUM} no estaba entre "
                    f"los {len(resultados)} resultados")
            else:
                doc_id = elegido["doc_id"]
                print(f"SI   (id {doc_id})")
        except FuenteCaida as e:
            print("NO")
            fallos.append(f"la busqueda no responde: {e}")
        except FormaInesperada as e:
            print("CAMBIO DE FORMA")
            fallos.append(f"la lista de resultados ha cambiado: {e}")
    else:
        print("(no se prueba)")

    # 4. el documento se puede leer y trae lo que esperamos
    print("  [3/3] el documento se lee ....... ", end="", flush=True)
    if doc_id:
        try:
            crudo = fuente.documento(doc_id)
            campos = extraer(crudo, CANARIO_NUM)
            if not campos.get("contestacion"):
                print("VACIO")
                fallos.append("el documento no trae contestacion")
            else:
                print(f"SI   ({len(campos['contestacion'])} caracteres)")
        except FuenteCaida as e:
            print("NO")
            fallos.append(f"el documento no responde: {e}")
        except FormaInesperada as e:
            print("CAMBIO DE FORMA")
            fallos.append(f"el documento ha cambiado de forma: {e}")
    else:
        print("(no se prueba)")

    print()
    print("=" * ANCHO)
    if fallos:
        print("  CANARIO EN ROJO — la fuente de criterio NO es fiable ahora")
        print()
        for f in fallos:
            print(f"    · {f}")
        print()
        print("  Que significa: el agente puede seguir contestando con la LEY.")
        print("  Lo que no puede es anadir criterio de la DGT. Cuando se")
        print("  integre (fase 9B), esto tiene que verse en pantalla, nunca")
        print("  quedarse en silencio.")
    else:
        print("  CANARIO EN VERDE — la fuente responde y tiene la forma de siempre")
    for a in avisos_:
        print(f"\n  aviso: {a}")
    print("=" * ANCHO)
    return 1 if fallos else 0


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
