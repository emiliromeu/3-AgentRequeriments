"""LO QUE COMPARTEN LOS CLIENTES DE FUENTES EXTERNAS.

Aqui vive lo que da igual de que base publica se descargue: como se pide sin
tumbar el servicio ajeno, como se guarda lo descargado, y como se avisa de que
la fuente ha dejado de servir. Lo que NO vive aqui es como se busca, como se
pide un documento y como se trocea: eso es propio de cada fuente y cambia
entera de una a otra.

Sale de `petete.py` (DGT/PETETE, KnoSys sobre Java) al empezar el cliente del
TEAC (DYCTEA, ASP.NET WebForms). Dos fuentes reales medidas, con la parte comun
identificada: ni antes -habria sido adivinar- ni despues.

----------------------------------------------------------------------------
LO QUE HAY AQUI, Y POR QUE
----------------------------------------------------------------------------
RED       pausa entre peticiones, reintentos con tope, User-Agent que nos
          identifica y tiempo maximo. No es cortesia: es que estas fuentes son
          servicios publicos, van lentas y se caen, y quedarse colgado o
          insistir en bucle es como se tumba una.

CACHE     el crudo tal cual llego, que no se toca nunca, y los campos
          extraidos, que se pueden rehacer desde el crudo. Mas un indice.
          Es el mismo trato que la fase 1 le da al BOE.

CANARIO   estos endpoints son internos y sin documentar. La clasificacion en
          TRES cubos -nos rechazan / ha cambiado de forma / no responde- viene
          de haber culpado a la DGT de un bug nuestro durante dos dias.

FuenteCaida y FormaInesperada son errores DISTINTOS y por eso son clases
distintas: uno se arregla esperando y el otro mirando la pagina.
"""

from __future__ import annotations

import hashlib
import http.cookiejar
import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ANCHO = 78


# --------------------------------------------------------------------- salida


def titulo(t: str) -> None:
    print("=" * ANCHO)
    print(f"  {t}")
    print("=" * ANCHO)


def aviso(t: str) -> None:
    print(f"\n[!] {t}")


def ahora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------- fallos


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


class FuenteWeb:
    """El unico sitio que habla con la red. Con pausas y con tope.

    Cada fuente concreta la hereda y pone lo suyo: como se busca, como se pide
    un documento y, si hace falta, que certificado extra hay que aportar.
    """

    def __init__(self, base: str, ua: str, espera: int, reintentos: int,
                 pausa: float, pausa_reintento: float,
                 silencioso: bool = False, cafile: str = ""):
        self.base = base
        self.ua = ua
        self.espera = espera
        self.reintentos = reintentos
        self.pausa = pausa
        self.pausa_reintento = pausa_reintento
        self.silencioso = silencioso
        self.peticiones = 0
        self._ultima = 0.0

        ctx = ssl.create_default_context()
        if cafile:
            ctx.load_verify_locations(cafile=cafile)
        self.ctx = ctx
        self.op = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
            urllib.request.HTTPSHandler(context=ctx),
        )
        self._sesion = False

    # ------------------------------------------------------------ cabeceras

    def cabeceras(self) -> dict:
        """Las de siempre. Una fuente puede anadir las suyas sobreescribiendo."""
        return {
            "User-Agent": self.ua,
            "Accept-Language": "es-ES,es;q=0.9",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.base}/",
        }

    # ------------------------------------------------------------------ red

    def _respirar(self) -> None:
        """Pausa entre peticiones. No es cortesia: es no tumbarles el servicio."""
        falta = self.pausa - (time.time() - self._ultima)
        if falta > 0 and self._ultima:
            time.sleep(falta)

    def pedir(self, ruta: str, datos=None, metodo: str = "GET") -> Respuesta:
        """Una peticion, con pausa y con tope.

        `datos` puede ser un dict o una lista de pares. La LISTA importa: un
        buscador puede recibir los campos en un orden concreto y un dict no
        garantiza ninguno. Con GET los datos van en la URL.
        """
        url = f"{self.base}{ruta}"
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
            req = urllib.request.Request(url, data=cuerpo,
                                         headers=self.cabeceras())
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
                time.sleep(self.pausa_reintento)
        raise FuenteCaida(ultimo or "sin respuesta", ultimo_codigo)


def dias_de_certificado(url: str) -> int | None:
    """Dias que le quedan al certificado del servidor. None si no se puede ver.

    Se mira porque un certificado caduca sin avisar y el dia que lo hace la
    fuente deja de servir para todos. Enterarnos por el canario es barato;
    enterarnos porque el departamento no puede trabajar, no.
    """
    import socket
    import tempfile
    from datetime import datetime as _dt

    host = urllib.parse.urlparse(url).hostname or ""
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


# --------------------------------------------------------------------- cache


class CacheDocumentos:
    """El crudo, los campos y el indice.

    Se guardan DOS cosas, como en la fase 1: el HTML crudo tal cual llego, que
    no se toca nunca, y los campos extraidos, que se pueden rehacer desde el
    crudo. Si manana cambia el troceo, se reprocesa sin volver a descargar.
    """

    def __init__(self, dir_crudo: Path, dir_documentos: Path,
                 dir_busquedas: Path, indice: Path, raiz: Path,
                 dir_escritura: Path | None = None):
        """`dir_escritura` es DONDE CAEN los documentos nuevos. Por defecto,
        donde estan los demas.

        SE SEPARA DONDE SE LEE DE DONDE SE ESCRIBE, y no es un refinamiento:
        es lo que hacia que la copia de la oficina no se pudiera actualizar.

        `datos/dgt/consultas` VIAJA por git -es el barrido nuestro, publico y
        sin nada de nadie-. `datos/dgt/demanda` NO viaja, y a proposito: sus
        fechas dirian que consulta pidio un cliente y que dia. Pero la cola por
        demanda bajaba con esta misma cache, asi que cada descarga de la
        oficina caia TAMBIEN en `consultas/`. Dos consecuencias, las dos malas:

          · el `git pull` siguiente se encontraba ahi un fichero sin seguir con
            el nombre exacto de uno que traia, y ABORTABA la fusion entera. La
            semana de goteo no llegaba a nadie;
          · y el historial de trabajo del despacho quedaba en el directorio que
            viaja, que es justo lo que `cola.py` dice por escrito que no puede
            pasar.

        Escribiendo en `demanda/` y leyendo de los dos, la demanda deja de
        viajar y sigue estando disponible: `dgt.CacheDGT` ya miraba las dos
        carpetas.
        """
        self.dir_crudo = Path(dir_crudo)
        self.dir_documentos = Path(dir_documentos)
        self.dir_escritura = Path(dir_escritura or dir_documentos)
        self.dir_busquedas = Path(dir_busquedas)
        self.ruta_indice = Path(indice)
        self.raiz = Path(raiz)
        for d in (self.dir_crudo, self.dir_documentos, self.dir_escritura,
                  self.dir_busquedas):
            d.mkdir(parents=True, exist_ok=True)
        self.indice = self._leer_indice()

    # ------------------------------------------------------------- indice

    def _leer_indice(self) -> dict:
        """El indice. Si no esta, SE REHACE DEL DISCO en vez de empezar vacio.

        EL INDICE ES DERIVADO Y POR ESO YA NO VIAJA. Es el mapeo numero -> id
        interno de la fuente, y se reescribia en cada maquina cada vez que la
        cola bajaba algo: viajaba Y se reescribia en local, que es la
        combinacion que rompe el pull. De las tres salidas posibles -no viajar,
        no reescribirse, o que el pull sepa descartarlo- la que le toca es la
        primera, porque el dato no es de nadie: esta entero en los documentos.

        Un indice vacio no es inofensivo: sin el, cada consulta cuesta una
        busqueda extra contra la fuente PARA SIEMPRE. Por eso no se empieza de
        cero: se lee de los documentos que ya hay, que llevan dentro su
        `doc_id` y su `tab`, y se guarda para no repetirlo.
        """
        if self.ruta_indice.is_file():
            try:
                return json.loads(self.ruta_indice.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                aviso("el indice estaba corrupto; se rehace de los documentos "
                      "(el crudo y los documentos siguen ahi)")
        return self._indice_del_disco()

    def _indice_del_disco(self) -> dict:
        """Reconstruye el indice leyendo los documentos guardados."""
        consultas = {}
        for d in self._donde_leer():
            for f in sorted(d.glob("*.json")):
                try:
                    r = json.loads(f.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue
                if not isinstance(r, dict):
                    continue
                ficha = {k: r[k] for k in ("doc_id", "tab", "fecha")
                         if r.get(k)}
                if r.get("descargado"):
                    ficha["visto"] = r["descargado"]
                if ficha:
                    consultas[f.stem.upper()] = ficha
        indice = {"consultas": consultas, "creado": ahora(),
                  "rehecho_del_disco": ahora()}
        if consultas:
            # Se guarda ya: rehacerlo en cada arranque seria pagar dos mil
            # lecturas por no haber escrito una linea.
            try:
                self.ruta_indice.parent.mkdir(parents=True, exist_ok=True)
                self.ruta_indice.write_text(
                    json.dumps(indice, ensure_ascii=False, indent=2),
                    encoding="utf-8")
            except OSError:
                pass          # sin poder escribirlo se sigue: es un atajo
        return indice

    def _guardar_indice(self) -> None:
        self.ruta_indice.write_text(
            json.dumps(self.indice, ensure_ascii=False, indent=2),
            encoding="utf-8")

    # ---------------------------------------------------------- documentos

    def _donde_leer(self) -> list:
        """Las carpetas donde puede estar un documento, sin repetir."""
        if self.dir_escritura == self.dir_documentos:
            return [self.dir_documentos]
        return [self.dir_documentos, self.dir_escritura]

    def tiene(self, numero: str) -> bool:
        return any((d / f"{numero.upper()}.json").is_file()
                   for d in self._donde_leer())

    def leer(self, numero: str) -> dict | None:
        for d in self._donde_leer():
            f = d / f"{numero.upper()}.json"
            if not f.is_file():
                continue
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return None
        return None

    def guardar_crudo(self, numero: str, crudo: str) -> tuple:
        """El crudo, tal cual llego. Devuelve (ruta, sha256)."""
        f = self.dir_crudo / f"{numero}.html"
        f.write_text(crudo, encoding="utf-8")
        return f, hashlib.sha256(crudo.encode("utf-8")).hexdigest()

    def guardar_documento(self, numero: str, registro: dict) -> None:
        """EN `dir_escritura`, que no siempre es donde estan los demas."""
        (self.dir_escritura / f"{numero}.json").write_text(
            json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")

    def ruta_relativa(self, f: Path) -> str:
        """Relativa si cuelga del proyecto, absoluta si no. Guardar la ruta no
        puede ser motivo de que se pierda una descarga."""
        return str(f.relative_to(self.raiz) if f.is_relative_to(self.raiz) else f)

    # ----------------------------------------------------------- busquedas

    @staticmethod
    def _clave_busqueda(terminos: str, ambito: str) -> str:
        return hashlib.sha256(f"{ambito}|{terminos.strip().lower()}"
                              .encode("utf-8")).hexdigest()[:16]

    def busqueda(self, terminos: str, ambito: str) -> list | None:
        f = self.dir_busquedas / f"{self._clave_busqueda(terminos, ambito)}.json"
        if not f.is_file():
            return None
        try:
            return json.loads(f.read_text(encoding="utf-8"))["resultados"]
        except (json.JSONDecodeError, KeyError):
            return None

    def guardar_busqueda(self, terminos: str, ambito: str,
                         resultados: list) -> None:
        f = self.dir_busquedas / f"{self._clave_busqueda(terminos, ambito)}.json"
        f.write_text(json.dumps(
            {"terminos": terminos, "tab": ambito, "cuando": ahora(),
             "resultados": resultados}, ensure_ascii=False, indent=2),
            encoding="utf-8")


# ------------------------------------------------------------------- canario


class Canario:
    """Los TRES CUBOS DE CULPA, y el informe que sale de ellos.

    Existe porque un canario que solo sabe decir «la fuente no responde» nos
    tuvo dos dias culpando a la DGT de un bug nuestro: mandabamos POST donde su
    aplicacion manda GET, y su servidor se atragantaba. El codigo HTTP lo
    distingue sin adivinar nada:

        4xx  su servidor entendio la peticion y la rechaza: es NUESTRA
        5xx  su servidor se atraganta: es SUYO
        sin codigo: no llego a contestar, no se sabe de quien es
    """

    def __init__(self):
        self.fallos: list = []          # es de ELLOS
        self.culpa_nuestra: list = []   # es NUESTRO: preguntamos mal
        self.cambios: list = []         # la fuente cambio de forma
        self.avisos: list = []

    def clasificar(self, e: FuenteCaida, que: str) -> str:
        """Reparte una caida en su cubo. Devuelve la palabra para la pantalla."""
        codigo = getattr(e, "codigo", None)
        if codigo and 400 <= codigo < 500:
            self.culpa_nuestra.append(
                f"{que} fue RECHAZADA con {codigo}: su servidor la entendio y "
                f"no le gusta. El fallo es NUESTRO, no de la fuente: estamos "
                f"preguntando mal")
            return "RECHAZADA"
        if codigo and codigo >= 500:
            self.fallos.append(
                f"{que} fallo con {codigo}: es un error DE SU SERVIDOR. La "
                f"peticion iba bien formada")
            return "NO"
        self.fallos.append(
            f"{que} no llego a contestar ({e}). No se puede saber si el fallo "
            f"es suyo o nuestro")
        return "SIN RESPUESTA"

    @property
    def hay_fallo(self) -> bool:
        return bool(self.fallos or self.culpa_nuestra or self.cambios)

    def informar(self, marcar=None) -> int:
        """Pinta el veredicto y deja escrito el estado de la fuente."""
        print()
        print("=" * ANCHO)
        if self.culpa_nuestra:
            # Va PRIMERO porque es lo unico que podemos arreglar nosotros.
            print("  CANARIO EN ROJO — Y EL FALLO ES NUESTRO")
            print()
            for f in self.culpa_nuestra:
                print(f"    · {f}")
            print()
            print("  Que significa: la fuente esta bien. Somos nosotros los que")
            print("  preguntamos de una forma que no acepta. Se arregla en")
            print("  el cliente, no esperando a que la fuente arregle nada.")
        elif self.cambios:
            print("  CANARIO EN ROJO — LA FUENTE HA CAMBIADO DE FORMA")
            print()
            for f in self.cambios:
                print(f"    · {f}")
            print()
            print("  Que significa: responde, pero ya no devuelve lo que")
            print("  esperabamos. Estos endpoints son internos y sin documentar.")
            print("  Hay que mirar la pagina a mano antes de fiarse de nada.")
        elif self.fallos:
            print("  CANARIO EN ROJO — LA FUENTE NO RESPONDE")
            print()
            for f in self.fallos:
                print(f"    · {f}")
            print()
            print("  Que significa: el fallo es de su servidor, no de nuestra")
            print("  peticion. No hay nada que arreglar aqui: hay que esperar.")
            print("  El agente puede seguir contestando con la LEY; lo que no")
            print("  puede es anadir criterio, y eso tiene que verse en")
            print("  pantalla, nunca quedarse en silencio.")
        else:
            print("  CANARIO EN VERDE — la fuente responde y tiene la forma de siempre")
        for a in self.avisos:
            print(f"\n  aviso: {a}")
        print("=" * ANCHO)

        if marcar is not None:
            motivo = (self.culpa_nuestra or self.cambios or self.fallos or [""])[0]
            try:
                marcar(not self.hay_fallo, motivo[:200])
            except Exception:  # noqa: BLE001
                pass
        return 1 if self.hay_fallo else 0
