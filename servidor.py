#!/usr/bin/env python3
"""EL SERVIDOR LOCAL: LEVANTARSE, ABRIR EL NAVEGADOR Y CERRARSE BIEN.

    python servidor.py                  # contra el modelo real
    python servidor.py --motor ensayo   # sin gastar una sola llamada

ESTO NO PINTA NADA TODAVIA. Es el ciclo de vida, y va primero a proposito: un
servidor que se queda vivo en segundo plano en el PC de la oficina es PEOR que
una ventana fea, porque nadie lo ve. Mañana el puerto sigue tomado y hay dos
agentes corriendo. El aspecto se construye encima de esto, no antes.

============================================================================
EL PROBLEMA QUE NO TIENE UNA VENTANA
============================================================================
Una ventana de tkinter se cierra y el proceso muere. Una pestaña de navegador
NO: el servidor es otro proceso y no se entera de nada. Asi que hay que
decidir, desde fuera, cuando ya no hace falta.

Y AHI ESTA LA TRAMPA: LA AUSENCIA DE NOTICIAS NO ES UNA NOTICIA.

  · un portatil suspendido deja de latir, y la pestaña sigue abierta;
  · una pestaña en segundo plano ve su `setInterval` estrangulado a UNA VEZ
    POR MINUTO en Chrome y Edge;
  · y a los cinco minutos oculta la pueden CONGELAR entera.

Si el silencio bastara para cerrar, el agente se apagaria solo mientras alguien
lee una respuesta larga en otra pestaña. O peor: a mitad de una consulta de dos
minutos.

============================================================================
DOS SEÑALES, NO UNA. ES LA DECISION DE FONDO DE ESTE FICHERO
============================================================================

    SEÑAL FUERTE ... la pestaña DICE que se va. `pagehide` + `sendBeacon`, que
                     el navegador entrega aunque la pestaña ya se este
                     cerrando. Es un hecho, no una suposicion: se cierra
                     ENSEGUIDA.

    SEÑAL DEBIL .... el silencio. Solo dice que no se ha oido nada, y eso pasa
                     por cuatro motivos de los que TRES son inocentes. Se
                     espera MUCHO -`SILENCIO_MAXIMO`- y aun asi no basta por
                     si sola.

Y POR ENCIMA DE LAS DOS: SI HAY UNA CONSULTA EN MARCHA, NO SE CIERRA. Ni con
silencio ni con adios. Una consulta real tarda 102 segundos de mediana y deja
un expediente a medias si se corta; el navegador puede haberse cerrado por
error y la respuesta sigue haciendo falta. Se termina, se guarda, y entonces se
mira si queda alguien.

Esa es la respuesta a «como distingues que se ha ido de que esta callado»: no
se distingue por el silencio, se distingue porque IRSE SE DICE.
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import secrets
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

# ------------------------------------------------------------- los tiempos
#
# CADA UNO SALE DE ALGO MEDIBLE, no de un numero redondo.

# Cada cuanto late la pestaña cuando esta a la vista. Cinco segundos es
# suficiente para notar un cierre sucio -matar el navegador de un tiron- sin
# hacer una peticion por segundo.
LATIDO = 5.0

# CUANTO SILENCIO SE AGUANTA ANTES DE DARSE POR IDO. Tiene que ser mayor que
# el peor estrangulamiento conocido de un navegador, no que el latido:
#
#     setInterval en pestaña oculta ......  60 s  (Chrome, Edge)
#     congelacion tras 5 min oculta ...... 300 s
#     portatil suspendido ................ sin limite
#
# Con 420 s se cubren los dos primeros con margen. El tercero NO se cubre con
# ningun numero, y por eso el silencio no cierra solo: hace falta ademas que no
# haya trabajo en marcha, y aun asi es la señal debil. Un agente que se cierra
# solo tras siete minutos de portatil dormido es un incordio; uno que se cierra
# a los treinta segundos es inservible.
SILENCIO_MAXIMO = 420.0

# SI EL NAVEGADOR NO LLEGA A ABRIRSE, NO SE ESPERA PARA SIEMPRE. Pasa cuando
# `webbrowser.open` falla en silencio -un navegador corporativo con politicas-
# y entonces no hay nadie que vaya a latir nunca.
GRACIA_INICIAL = 90.0

# Cada cuanto mira el vigilante. No hace falta afinar: lo que decide son los
# margenes de arriba.
VIGILANCIA = 2.0


class Vida:
    """Quien esta mirando la pagina, y si se puede cerrar.

    SE MIRA POR PESTAÑA, NO POR «HAY ALGUIEN». Dos pestañas abiertas son dos
    clientes, y cerrar una NO puede llevarse por delante la otra: es lo que
    pasaria contando solo «el ultimo latido» sin saber de quien.
    """

    def __init__(self, ahora=time.monotonic):
        self._ahora = ahora
        self._lock = threading.Lock()
        # {id de pestaña: momento del ultimo latido}
        self.clientes: dict = {}
        # Cuantas consultas hay en marcha AHORA. Mientras sea > 0 no se cierra.
        self.trabajando = 0
        # Cuando arranco, para la gracia inicial.
        self.nacido = self._ahora()
        # Alguien ha llegado a conectarse alguna vez.
        self.hubo_alguien = False
        self.motivo_del_cierre = ""

    def late(self, quien: str) -> None:
        with self._lock:
            self.clientes[quien] = self._ahora()
            self.hubo_alguien = True

    def adios(self, quien: str) -> None:
        """La señal FUERTE: esta pestaña dice que se va."""
        with self._lock:
            self.clientes.pop(quien, None)

    def empieza_consulta(self) -> None:
        with self._lock:
            self.trabajando += 1

    def acaba_consulta(self) -> None:
        with self._lock:
            self.trabajando = max(0, self.trabajando - 1)

    def se_puede_cerrar(self) -> tuple:
        """(si_se_puede, motivo). El motivo se escribe en el log."""
        with self._lock:
            ahora = self._ahora()
            # 1 · POR ENCIMA DE TODO: una consulta a medias no se corta.
            if self.trabajando:
                return False, ""
            # 2 · Nadie ha llegado nunca: el navegador no abrio.
            if not self.hubo_alguien:
                if ahora - self.nacido > GRACIA_INICIAL:
                    return True, ("nadie abrio la pagina en "
                                  f"{GRACIA_INICIAL:.0f} s: el navegador no "
                                  "llego a arrancar")
                return False, ""
            # 3 · Todas las pestañas DIJERON que se iban. Señal fuerte.
            if not self.clientes:
                return True, "se cerraron todas las pestañas"
            # 4 · Silencio largo. Señal debil, con el margen de arriba.
            callados = [q for q, t in self.clientes.items()
                        if ahora - t > SILENCIO_MAXIMO]
            if len(callados) == len(self.clientes):
                return True, (f"ninguna pestaña da señales desde hace "
                              f"{SILENCIO_MAXIMO:.0f} s")
            return False, ""

    def limpiar_callados(self) -> None:
        """Quita las pestañas mudas SIN cerrar el servidor.

        Una pestaña que se cerro de golpe -matando el navegador- no manda
        adios. Si se quedara en la lista para siempre, `clientes` nunca se
        vaciaria y la señal fuerte no volveria a dispararse nunca.
        """
        with self._lock:
            ahora = self._ahora()
            for q in [q for q, t in self.clientes.items()
                      if ahora - t > SILENCIO_MAXIMO]:
                del self.clientes[q]


# ------------------------------------------------------- el sitio en disco
#
# DONDE SE APUNTA EL SERVIDOR QUE ESTA VIVO. Sirve para dos cosas:
#
#   · que un segundo doble clic ABRA OTRA PESTAÑA en el que ya hay, en vez de
#     levantar un segundo agente con su propio puerto;
#   · y que quede el testigo, para que el navegador pueda pedir.
#
# En `datos/`, que no viaja por git.
FICHA = RAIZ / "datos" / "servidor.json"


def puerto_libre() -> int:
    """Uno que el sistema diga que esta libre. NUNCA uno escrito a mano.

    Un puerto fijo -8000, 5000- choca con lo que ya haya en el equipo, y en un
    PC de oficina hay mas de lo que parece. Con el 0 lo elige el sistema, que
    es el unico que sabe cuales estan tomados.
    """
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


def ficha_viva() -> dict | None:
    """El servidor ya levantado, si lo hay y responde. `None` si no."""
    try:
        d = json.loads(FICHA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    puerto, testigo = d.get("puerto"), d.get("testigo")
    if not puerto or not testigo:
        return None
    try:
        import urllib.request
        with urllib.request.urlopen(
                f"http://127.0.0.1:{puerto}/api/vivo?t={testigo}",
                timeout=1.5) as r:
            if r.status == 200:
                return d
    except Exception:                            # noqa: BLE001
        pass
    # La ficha esta pero nadie contesta: sobra.
    try:
        FICHA.unlink()
    except OSError:
        pass
    return None


# ------------------------------------------------------- el corpus, una vez
#
# SE CARGA UNA SOLA VEZ Y SE COMPARTE. Son 2.504 preceptos y tarda un segundo:
# cargarlo por peticion dejaria el menu tardando un segundo cada vez que se
# abre. Va en un hilo al arrancar, como en la ventana.
_IX = None
_GRAFO = None
_MOTOR = None
_CARGA = threading.Lock()
_YA_CARGANDO = False
# El menu, calculado una vez. Ver `_menu`.
_MENU = None


def _corpus():
    """El indice, o `None` si todavia se esta cargando."""
    return _IX


def cargar_por_detras(motor_nombre: str = "anthropic") -> None:
    """Carga corpus y motor sin bloquear el arranque del servidor.

    LA PAGINA TIENE QUE PODER PINTARSE ANTES. Si se cargara aqui, el navegador
    se abriria contra un servidor que no responde durante un segundo largo, y
    eso se lee como que no ha arrancado.

    ────────────────────────────────────────────────────────────────────────
    UNA SOLA VEZ POR PROCESO. ARREGLADO EL 01/09/2026.
    ────────────────────────────────────────────────────────────────────────

    Antes, cada `arrancar` lanzaba SU carga. Con cuatro servidores en el mismo
    proceso -que es lo que hace la suite- eran cuatro cargas del corpus entero
    en serie sobre el mismo lock, y el proceso DEJABA DE RESPONDER: una
    peticion a `/api/menu` se colgaba mas de 25 segundos.

    Se descubrio porque `prueba_servidor` empezo a dar `TimeoutError` en
    `comprobar_todo` — y NO era cosa de la suite: es que el corpus se recarga
    por cada `arrancar`, y eso es un fallo del servidor. En la oficina hoy no
    se ve porque `main()` no levanta un segundo servidor si ya hay uno vivo,
    pero eso es una guarda de OTRA capa: aqui dentro nada lo impedia.

    `_YA_CARGANDO` corta en seco. No basta con mirar `_IX`: entre que un hilo
    empieza y termina hay segundos, y en esos segundos entrarian todos los
    demas.
    """
    global _YA_CARGANDO
    with _CARGA:
        if _YA_CARGANDO:
            return
        _YA_CARGANDO = True

    def trabajo():
        global _IX, _GRAFO, _MOTOR
        try:
            import fase4
            _IX, _GRAFO = fase4.cargar_corpus()
            motor, _err = fase4.preparar_motor(motor_nombre, silencioso=True)
            _MOTOR = motor
        except Exception:                        # noqa: BLE001
            import traceback
            try:
                (RAIZ / "datos" / "servidor_fallo.txt").write_text(
                    traceback.format_exc(), encoding="utf-8")
            except OSError:
                pass
    threading.Thread(target=trabajo, daemon=True).start()


# ------------------------------------------------------------- el servidor

# ══════════════════════════════════════════════════════════════════════════
# COPIAR EN UNA VUELTA DESFASADA: SE PUEDE, Y LO COPIADO LO DICE.
# ══════════════════════════════════════════════════════════════════════════
#
# Decidido el 01/09/2026. Las tres salidas se miraron:
#
#   APAGARLO ............. es lo que hace la ventana hoy con «escribirlo para
#                          el cliente» cuando falta el expediente, y aqui
#                          seria un error: una vuelta desfasada NO ES FALSA.
#                          Se comprobo, se verifico cita a cita, y sigue
#                          contestando lo que preguntaba. Apagar el boton
#                          obligaria a copiar a mano -seleccionar y Ctrl+C-,
#                          que da el mismo texto SIN la cabecera. Se pierde
#                          justo lo que protege.
#   DEJARLO IGUAL ........ es lo de hoy, y es el fallo silencioso del año por
#                          el camino de salida: la vuelta 1 pegada en un
#                          correo despues de que la 3 la corrigiera.
#   DEJARLO Y ESTAMPARLO . lo que se hace.
#
# LO COPIADO YA LLEVA ejercicio, comunidad y «comprobada el ...». Lo que se
# añade cuando la vuelta esta desfasada es UNA LINEA MAS, la primera, que dice
# en que quedo atras. Va delante del texto y no al pie: quien pega esto en un
# correo lo lee antes que la respuesta.
#
# Y «ESCRIBIRLO PARA EL CLIENTE» SI SE APAGA, que es otra cosa: eso llama al
# modelo para producir un texto NUEVO con la firma del despacho detras, sobre
# una base que ya se sabe superada. Copiar es enseñar lo que hubo; reescribir
# es fabricar algo que nadie comprobo.
AVISO_AL_COPIAR = {
    "otra ley": ("ATENCION: esta respuesta se contesto ANTES de que la "
                 "consulta cambiara de ejercicio o de comunidad. Es de otra "
                 "redaccion de la norma."),
    "otra base": ("ATENCION: una vuelta posterior de esta consulta se apoya "
                  "en otros articulos. Esto sigue valiendo para lo que se "
                  "preguntaba, pero no es la respuesta al caso completo."),
}


PAGINA_MINIMA = """<!doctype html>
<meta charset="utf-8">
<title>Consulta fiscal</title>
<body style="font-family:system-ui;padding:2rem;max-width:40rem">
<h1>Consulta fiscal</h1>
<p id="e">El agente est&aacute; en marcha. Esta p&aacute;gina todav&iacute;a no
tiene interfaz: lo que se est&aacute; probando es que el servidor se cierre
cuando cierres esta pesta&ntilde;a.</p>
<script>
// ── EL LATIDO Y EL ADIOS ───────────────────────────────────────────────
// Dos señales, y el adios es el que de verdad cierra. Ver la nota larga en
// servidor.py.
const T = new URLSearchParams(location.search).get("t") || "";
const YO = Math.random().toString(36).slice(2);
function latir() {
  fetch(`/api/latido?t=${encodeURIComponent(T)}&quien=${encodeURIComponent(YO)}`,
        {method: "POST"}).catch(() => {});
}
latir();
setInterval(latir, %(latido)d);
// `pagehide` y no `beforeunload`: es el que se dispara tambien al cerrar la
// pestaña en movil y al navegar fuera. Y `sendBeacon` porque un `fetch`
// normal se cancela cuando la pagina ya se esta yendo.
addEventListener("pagehide", () => {
  navigator.sendBeacon(
    `/api/adios?t=${encodeURIComponent(T)}&quien=${encodeURIComponent(YO)}`);
});
// Al volver de segundo plano, latir enseguida: el navegador pudo haber
// estrangulado el intervalo mientras estaba oculta.
addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") latir();
});
</script>
</body>
"""


class Manejador(http.server.BaseHTTPRequestHandler):
    """Lo minimo: la pagina, el latido, el adios y el pulso.

    NINGUNA TRAZA DE PYTHON SALE POR AQUI. Es la misma regla 3 de la ventana,
    y en web hace falta decirla otra vez porque el camino es nuevo: un servidor
    que revienta devuelve por defecto un 500 con el fichero, la linea y el
    codigo. Eso es una pantalla que nadie del despacho tiene que ver, y ademas
    puede llevar rutas dentro.
    """

    protocol_version = "HTTP/1.1"

    # -- lo que comparten todas las peticiones (lo pone `arrancar`) --
    vida: Vida = None
    testigo: str = ""

    def log_message(self, *a):
        """Silencio. El log de `http.server` va a stderr y con `pythonw.exe`
        no hay stderr que leer; ademas escupiria cada latido."""

    # ------------------------------------------------------------ ayudantes

    def _autorizado(self) -> bool:
        """EL TESTIGO. `127.0.0.1` deja fuera la red, pero NO deja fuera a los
        demas programas de este mismo equipo: cualquiera que corra aqui puede
        pedir a un puerto local. El testigo es aleatorio, va en la URL que
        abre el navegador y no se guarda en ningun sitio publico."""
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(self.path).query)
        return (q.get("t") or [""])[0] == self.testigo

    def _quien(self) -> str:
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(self.path).query)
        return (q.get("quien") or [""])[0]

    def _responder(self, codigo: int, cuerpo: bytes, tipo="text/html"):
        self.send_response(codigo)
        self.send_header("Content-Type", f"{tipo}; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        # NADA DE ESTO SE GUARDA EN EL NAVEGADOR. Son dudas de clientes: una
        # copia en la cache del disco es una copia mas que nadie vigila.
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    # ------------------------------------------------------------- caminos

    def _json(self, datos, codigo=200):
        self._responder(codigo,
                        json.dumps(datos, ensure_ascii=False).encode("utf-8"),
                        "application/json")

    def do_GET(self):
        ruta = self.path.split("?")[0]
        if not self._autorizado():
            # SIN DECIR POR QUE. Un «testigo incorrecto» le confirma a quien
            # prueba que ha acertado el camino.
            return self._responder(404, b"no")
        if ruta == "/":
            # ────────────────────────────────────────────────────────────
            # EL TESTIGO SE LE PONE A LOS SUBRECURSOS AQUI. 01/09/2026.
            # ────────────────────────────────────────────────────────────
            #
            # EL FALLO: el HTML declaraba `href="/estilo.css"` y
            # `src="/agente.js"` a secas. El navegador pide un subrecurso CON
            # LA RUTA QUE PONE EL ATRIBUTO, no con la de la pagina: no arrastra
            # la query. Asi que llegaban sin `?t=`, `_autorizado` devolvia
            # False y el servidor contestaba 404 a los dos. La pagina salia en
            # crudo -sin estilo y sin JavaScript- y se quedaba en «Abriendo…».
            #
            # Y LA SUITE ESTABA EN VERDE, porque pedia `/estilo.css?t=...`: se
            # comprobaba que el servidor RESPONDE a una ruta, no que la pagina
            # PIDE esa ruta. Son las dos mitades y solo habia una. Ahora la
            # suite saca las rutas DEL PROPIO HTML y las pide tal cual.
            #
            # SE RESUELVE SUSTITUYENDO EL MARCADOR, no con una cookie: una
            # cookie en 127.0.0.1 se comparte por HOST y no por puerto, asi que
            # dos agentes a la vez se pisarian el testigo. Sustituir es
            # explicito y no deja estado en el navegador.
            try:
                pagina = (RAIZ / "web" / "index.html").read_text(
                    encoding="utf-8")
            except OSError:
                return self._responder(404, b"no")
            from urllib.parse import quote
            pagina = pagina.replace("{{T}}", quote(self.testigo, safe=""))
            return self._responder(200, pagina.encode("utf-8"))
        if ruta in ("/estilo.css", "/agente.js"):
            tipo = ("text/css" if ruta.endswith(".css")
                    else "application/javascript")
            return self._servir_fichero(ruta.lstrip("/"), tipo)
        if ruta == "/api/vivo":
            return self._json({"vivo": True})
        # LOS SEIS PASOS, TAL COMO LOS DEFINE `fase4`. La pagina no los escribe:
        # los pide. Es lo mismo que hace la ventana, y por el mismo motivo —si
        # el motor crece, la lista se entera sola—.
        if ruta == "/api/pasos":
            import fase4
            return self._json({
                "pasos": [{"clave": c, "rotulo": r} for c, r in fase4.PASOS],
                "solo_con_criterio": fase4.PASO_SOLO_CON_CRITERIO,
            })
        if ruta == "/api/menu":
            return self._json(self._menu())
        if ruta == "/api/chats":
            from agente_fiscal import expedientes as EX, chat as CH
            filas, _aviso = EX.filas()
            visibles = [f for f in filas if not EX.es_de_prueba(f)]
            chats = CH.de_expedientes(visibles)
            return self._json({"dias": [
                {"dia": dia, "chats": [{
                    "sello": c["sello"], "titulo": c["titulo"],
                    "vueltas": len(c["vueltas"]), "ejercicio": c["ejercicio"],
                    "comunidad": c["comunidad"], "estado": c["estado"],
                } for c in cs]}
                for dia, cs in CH.por_dia(chats)]})
        return self._responder(404, b"no")

    def _servir_fichero(self, nombre: str, tipo: str):
        """Solo de `web/`, y solo por nombre.

        NADA DE RUTAS QUE VENGAN DE FUERA. Se sirve una lista corta de ficheros
        conocidos: un servidor que compone la ruta con lo que pide el navegador
        es un servidor al que se le pide `../../.env`.
        """
        ruta = RAIZ / "web" / nombre
        try:
            cuerpo = ruta.read_bytes()
        except OSError:
            return self._responder(404, b"no")
        self._responder(200, cuerpo, tipo)

    def _menu(self) -> dict:
        """Lo que se enseña al entrar. TODO CONTADO DEL CORPUS, nada escrito.

        SE CALCULA UNA VEZ Y SE GUARDA. `cubierto_por_impuesto` recorre las
        caches enteras de la DGT y del TEAC: 2,4 SEGUNDOS MEDIDOS, en cada
        peticion. El menu se pide al abrir la pagina, asi que eso lo pagaria
        entero quien la abre —y otra vez si recarga—.
        """
        global _MENU
        from agente_fiscal import cobertura as C
        ix = _corpus()
        if ix is None:
            return {"cargando": True}
        if _MENU is not None:
            return _MENU
        _MENU = {
            "titulo": C.titulo(ix),
            "articulos": len(ix.docs),
            "normas": len(ix.rutas),
            # LA BARRA ES PROPORCION, NO VOLUMEN. Ver la nota larga en
            # `cobertura.cubierto_por_impuesto`: por volumen, Patrimonio sale
            # el ultimo y es el MEJOR cubierto de todos.
            "cobertura": [{"nombre": n, "articulos": a, "con_criterio": c,
                           "porcentaje": p}
                          for n, a, c, p in C.cubierto_por_impuesto(ix)],
        }
        return _MENU

    def do_POST(self):
        ruta = self.path.split("?")[0]
        if not self._autorizado():
            return self._responder(404, b"no")
        if ruta == "/api/latido":
            self.vida.late(self._quien())
            return self._responder(200, b'{"ok":true}', "application/json")
        if ruta == "/api/adios":
            self.vida.adios(self._quien())
            return self._responder(200, b'{"ok":true}', "application/json")
        return self._responder(404, b"no")

    def handle_one_request(self):
        """Igual que el de siempre, pero SIN dejar salir una traza.

        `BaseHTTPRequestHandler` responde a un fallo no cogido con un 500 que
        lleva el error dentro. Aqui se corta: al navegador va una frase, y el
        detalle al log del disco, que es lo unico legible sin consola.
        """
        try:
            super().handle_one_request()
        except (BrokenPipeError, ConnectionResetError):
            # El navegador se fue a mitad. Es lo normal al cerrar, no un fallo.
            self.close_connection = True
        except Exception:                        # noqa: BLE001
            import traceback
            try:
                (RAIZ / "datos" / "servidor_fallo.txt").write_text(
                    traceback.format_exc(), encoding="utf-8")
            except OSError:
                pass
            try:
                self._responder(500, "No se ha podido atender la petición. "
                                     "Avisa a Emili.".encode("utf-8"))
            except Exception:                    # noqa: BLE001
                pass
            self.close_connection = True


def arrancar(motor_nombre: str = "anthropic", abrir=True, vida=None,
             al_cerrar=None) -> tuple:
    """Levanta el servidor y devuelve (servidor, vida, url).

    NO BLOQUEA: el que llama decide si espera. Es lo que permite que la suite
    lo levante, le hable y lo cierre sin abrir un navegador.
    """
    vida = vida if vida is not None else Vida()
    testigo = secrets.token_urlsafe(24)
    puerto = puerto_libre()

    manejador = type("ManejadorAtado", (Manejador,),
                     {"vida": vida, "testigo": testigo})
    # ────────────────────────────────────────────────────────────────────
    # 127.0.0.1 Y NUNCA 0.0.0.0. NO ES UN DETALLE: SON DOCE CARACTERES.
    # ────────────────────────────────────────────────────────────────────
    #
    # Atado a `127.0.0.1` el socket solo existe en la interfaz de loopback y
    # el sistema NO ACEPTA la conexion desde ninguna otra: ni desde la IP de
    # este equipo en la red, ni desde otro ordenador. No es un filtro que se
    # pueda saltar, es que no hay donde conectarse.
    #
    # Con `0.0.0.0` -o con `""`, que es lo mismo- las dudas de los clientes
    # quedan servidas en la red del despacho. Comprobado ejecutandolo:
    #
    #     bind 127.0.0.1 -> desde la IP de red: no (URLError)
    #     bind 0.0.0.0   -> desde la IP de red: RESPONDE
    #
    # `prueba_servidor` lo comprueba de las dos maneras -conectandose de
    # verdad desde la IP de red y exigiendo que falle- y ademas lee este
    # fichero y exige el literal. Un error de doce caracteres no puede
    # depender de que nadie lo escriba mal un martes.
    servidor = http.server.ThreadingHTTPServer(("127.0.0.1", puerto), manejador)
    servidor.daemon_threads = True
    cargar_por_detras(motor_nombre)

    url = f"http://127.0.0.1:{puerto}/?t={testigo}"
    threading.Thread(target=servidor.serve_forever, daemon=True).start()

    try:
        FICHA.parent.mkdir(parents=True, exist_ok=True)
        FICHA.write_text(json.dumps({"puerto": puerto, "testigo": testigo,
                                     "pid": os.getpid()}), encoding="utf-8")
    except OSError:
        pass          # sin ficha se sigue: solo se pierde el reuso

    def vigilar():
        while True:
            time.sleep(VIGILANCIA)
            vida.limpiar_callados()
            puede, motivo = vida.se_puede_cerrar()
            if puede:
                vida.motivo_del_cierre = motivo
                break
        try:
            FICHA.unlink()
        except OSError:
            pass
        if al_cerrar is not None:
            al_cerrar(motivo)
        servidor.shutdown()

    threading.Thread(target=vigilar, daemon=True).start()
    if abrir:
        webbrowser.open(url)
    return servidor, vida, url


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description="Servidor local del agente.")
    ap.add_argument("--motor", choices=["anthropic", "ensayo"],
                    default="anthropic")
    args = ap.parse_args(argv)

    # ¿YA HAY UNO? Entonces no se levanta un segundo: se abre otra pestaña en
    # el que hay. Dos servidores serian dos puertos, dos fichas y dos agentes
    # escribiendo en las mismas carpetas.
    ya = ficha_viva()
    if ya:
        webbrowser.open(f"http://127.0.0.1:{ya['puerto']}/?t={ya['testigo']}")
        print("Ya habia un agente abierto: se ha abierto otra pestaña.")
        return 0

    servidor, vida, url = arrancar(args.motor)
    print(f"Agente en marcha: {url}")
    try:
        while servidor.__dict__.get("_BaseServer__shutdown_request") is False \
                or True:
            time.sleep(0.5)
            if not vida.se_puede_cerrar()[0] and vida.motivo_del_cierre:
                break
            if vida.motivo_del_cierre:
                break
    except KeyboardInterrupt:
        pass
    print(f"Cerrado: {vida.motivo_del_cierre or 'a mano'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
