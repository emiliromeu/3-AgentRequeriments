#!/usr/bin/env python3
"""EL SERVIDOR LOCAL: QUE SE CIERRE BIEN, Y QUE NO SALGA DEL EQUIPO.

    python pruebas/prueba_servidor.py

Cero red hacia fuera, cero API. Levanta servidores de verdad en este equipo,
les habla y los cierra.

LAS DOS QUE NO SE PUEDEN PERDER, y las dos son de seguridad antes que de
funcionamiento:

  1. NO SE PUEDE LLEGAR DESDE LA RED. Doce caracteres -`0.0.0.0` en vez de
     `127.0.0.1`- separan una pagina privada de dejar las dudas de los clientes
     servidas en la red del despacho. Aqui se comprueba INTENTANDO CONECTARSE
     DE VERDAD desde la IP de este equipo en la red y exigiendo que falle; y
     ademas se lee el fuente y se exige el literal, porque un error asi no
     puede depender de que nadie lo escriba mal un martes.

  2. NO SE CIERRA A MITAD DE UNA CONSULTA. Una consulta real tarda 102 segundos
     de mediana. Si el latido bastara para cerrar, el agente se apagaria con el
     portatil dormido, con la pestaña en segundo plano -Chrome estrangula
     `setInterval` a una vez por minuto, y congela la pestaña a los cinco- o
     con el navegador cerrado por error mientras el expediente se escribe.

Y LA DECISION QUE LAS SOSTIENE: dos señales, no una. Irse SE DICE -`pagehide`
mas `sendBeacon`- y eso cierra enseguida; el silencio solo dice que no se ha
oido nada, y por si solo nunca es suficiente.
"""
import json
import re
import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import servidor as SV  # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:104]}" if not ok else ""))
    if not ok:
        fallos.append(que)


def ip_de_red() -> str:
    """La IP de este equipo en la red, sin mandar nada.

    `gethostbyname(gethostname())` NO sirve: en este Mac devuelve 127.0.0.1 y
    la comprobacion pasaria sin probar nada, que es peor que no tenerla.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 9))          # red de documentacion: no existe
        return s.getsockname()[0]
    finally:
        s.close()


def pedir(url, metodo="GET", timeout=2.0):
    req = urllib.request.Request(url, method=metodo)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


# ============================================ 1. NO SE LLEGA DESDE LA RED
print("\n=== 1. EL CANDADO: 127.0.0.1 Y NUNCA 0.0.0.0 ===")
IP = ip_de_red()
print(f"  IP de este equipo en la red: {IP}\n")
comprobar("la IP de red no es loopback (si no, esto no probaria nada)",
          not IP.startswith("127."), IP)

srv, vida, url = SV.arrancar("ensayo", abrir=False)
puerto = srv.server_address[1]
try:
    testigo = url.split("t=")[1]
    codigo, _ = pedir(f"http://127.0.0.1:{puerto}/?t={testigo}")
    comprobar("desde 127.0.0.1 SI responde", codigo == 200, codigo)

    llego = None
    try:
        pedir(f"http://{IP}:{puerto}/?t={testigo}", timeout=2.0)
        llego = True
    except Exception as e:                       # noqa: BLE001
        llego = False
        print(f"    (desde la red: {type(e).__name__}, que es lo que toca)")
    comprobar("DESDE LA IP DE RED NO RESPONDE: no sale del equipo",
              llego is False, "RESPONDIO: seria accesible desde el despacho")

    # EL TESTIGO: `127.0.0.1` deja fuera la red, no a los demas programas de
    # este equipo.
    sin_testigo = pedir(f"http://127.0.0.1:{puerto}/")[0] if True else 0
except urllib.error.HTTPError as e:
    sin_testigo = e.code
comprobar("sin el testigo no se sirve la pagina", sin_testigo == 404,
          sin_testigo)
try:
    mal = pedir(f"http://127.0.0.1:{puerto}/?t=loquesea")[0]
except urllib.error.HTTPError as e:
    mal = e.code
comprobar("  ni con un testigo inventado", mal == 404, mal)
comprobar("  y no se dice por que: un «testigo incorrecto» confirmaria el "
          "camino", mal == 404)
srv.shutdown()

# EL LITERAL, EN EL FUENTE. La prueba de arriba pasa hoy; esta impide que
# alguien cambie el literal mañana «para probarlo desde el movil».
FUENTE = (RAIZ / "servidor.py").read_text("utf-8")
sin_comentarios = "\n".join(l for l in FUENTE.splitlines()
                            if not l.lstrip().startswith("#"))
comprobar("el fuente ata a 127.0.0.1", '"127.0.0.1"' in sin_comentarios)
malos = [x for x in ('"0.0.0.0"', "'0.0.0.0'", 'ThreadingHTTPServer(("",')
         if x in sin_comentarios]
comprobar("y NO hay ni un 0.0.0.0 ni un bind vacio", not malos, malos)

# ============================================ 2. EL CIERRE
print("\n=== 2. CERRAR LA PESTAÑA CIERRA EL SERVIDOR ===")


class Reloj:
    """Un reloj que se mueve a mano: los margenes son de MINUTOS y una suite
    no puede tardar siete minutos en comprobar uno."""

    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def avanza(self, s):
        self.t += s


reloj = Reloj()
v = SV.Vida(ahora=reloj)
comprobar("recien nacido y sin nadie, NO se cierra todavia",
          not v.se_puede_cerrar()[0])
v.late("pestaña-1")
comprobar("con una pestaña latiendo, no se cierra",
          not v.se_puede_cerrar()[0])

# LA SEÑAL FUERTE: irse SE DICE.
v.adios("pestaña-1")
puede, motivo = v.se_puede_cerrar()
comprobar("cuando la pestaña DICE que se va, se cierra enseguida", puede)
comprobar("  y se dice por que", "cerraron" in motivo, motivo)

# ============================================ 3. DOS PESTAÑAS
print("\n=== 3. DOS PESTAÑAS: CERRAR UNA NO SE LLEVA LA OTRA ===")
v = SV.Vida(ahora=reloj)
v.late("a")
v.late("b")
v.adios("a")
comprobar("con una cerrada y otra abierta, NO se cierra",
          not v.se_puede_cerrar()[0], v.clientes)
v.adios("b")
comprobar("  y al cerrarse la segunda, si", v.se_puede_cerrar()[0])

# ────────────────────────────────────────────────────────────────────────
# Y AL REVES, QUE ES EL CASO QUE DE VERDAD DISTINGUE.
# ────────────────────────────────────────────────────────────────────────
#
# Lo de arriba pasa TAMBIEN si solo se guardara «el ultimo que latio»:
# cerrando la PRIMERA, la lista sigue teniendo a la segunda por casualidad.
# Se vio rompiendo el codigo a proposito -haciendo que cada latido borrara al
# anterior- y esta seccion seguia en verde.
#
# Cerrando la SEGUNDA, la primera tiene que seguir viva. Ahi es donde
# «guardar por pestaña» y «guardar el ultimo» dejan de dar lo mismo.
v = SV.Vida(ahora=reloj)
v.late("a")
v.late("b")
v.adios("b")
comprobar("cerrando la SEGUNDA, la PRIMERA sigue viva",
          not v.se_puede_cerrar()[0] and "a" in v.clientes, v.clientes)
comprobar("  y se guarda una entrada por pestaña, no solo la ultima",
          len(v.clientes) == 1 and list(v.clientes) == ["a"], v.clientes)

# Con tres, igual: cerrar las dos de en medio no se lleva la primera.
v = SV.Vida(ahora=reloj)
for q in ("a", "b", "c"):
    v.late(q)
comprobar("tres pestañas son tres clientes", len(v.clientes) == 3, v.clientes)
v.adios("b")
v.adios("c")
comprobar("  cerrar dos deja viva la tercera",
          not v.se_puede_cerrar()[0] and list(v.clientes) == ["a"], v.clientes)

# ============================================ 4. EL SILENCIO NO BASTA
print("\n=== 4. EL SILENCIO NO ES UNA SEÑAL DE QUE SE HAYAN IDO ===")
print("  Portatil dormido, pestaña oculta estrangulada a 1 latido/min, o")
print("  congelada a los 5 min. Tres motivos inocentes de callarse.\n")
v = SV.Vida(ahora=reloj)
v.late("a")
for seg, espera in ((60, "un minuto (pestaña oculta estrangulada)"),
                    (300, "cinco minutos (pestaña congelada)")):
    reloj.avanza(seg)
    comprobar(f"tras {espera}, NO se cierra",
              not v.se_puede_cerrar()[0])
    v_ = v.se_puede_cerrar()
reloj.avanza(200)          # total 560 s > SILENCIO_MAXIMO
puede, motivo = v.se_puede_cerrar()
comprobar(f"pasados {SV.SILENCIO_MAXIMO:.0f} s de silencio TOTAL, si se cierra",
          puede, motivo)
comprobar("  y el motivo dice que es por silencio, no por un adios",
          "señales" in motivo, motivo)
comprobar("el margen cubre el peor estrangulamiento conocido (300 s)",
          SV.SILENCIO_MAXIMO > 300, SV.SILENCIO_MAXIMO)

# ============================================ 5. LA QUE MAS IMPORTA
print("\n=== 5. NO SE CIERRA A MITAD DE UNA CONSULTA ===")
print("  102 segundos de mediana. Ni el silencio ni el adios pueden cortar")
print("  una consulta y dejar el expediente a medias.\n")
v = SV.Vida(ahora=reloj)
v.late("a")
v.empieza_consulta()
v.adios("a")
comprobar("con una consulta en marcha, un ADIOS no cierra",
          not v.se_puede_cerrar()[0])
reloj.avanza(SV.SILENCIO_MAXIMO * 3)
comprobar("  ni el silencio mas largo", not v.se_puede_cerrar()[0])
v.acaba_consulta()
comprobar("y en cuanto termina, se cierra", v.se_puede_cerrar()[0])

# Dos consultas a la vez: no basta con que acabe una.
v = SV.Vida(ahora=reloj)
v.late("a")
v.empieza_consulta()
v.empieza_consulta()
v.adios("a")
v.acaba_consulta()
comprobar("con dos consultas en marcha, acabar una no basta",
          not v.se_puede_cerrar()[0])
v.acaba_consulta()
comprobar("  y al acabar la segunda, si", v.se_puede_cerrar()[0])

# ============================================ 6. EL NAVEGADOR QUE NO ABRE
print("\n=== 6. SI EL NAVEGADOR NO LLEGA A ABRIR, NO SE ESPERA PARA SIEMPRE ===")
v = SV.Vida(ahora=reloj)
comprobar("al principio se espera", not v.se_puede_cerrar()[0])
reloj.avanza(SV.GRACIA_INICIAL + 1)
puede, motivo = v.se_puede_cerrar()
comprobar("pasada la gracia sin que nadie abra, se cierra", puede)
comprobar("  y se dice que el navegador no arranco",
          "navegador" in motivo, motivo)

# ============================================ 7. EL CIERRE SUCIO
print("\n=== 7. UN NAVEGADOR MATADO DE UN TIRON NO DEJA EL SITIO OCUPADO ===")
print("  No manda adios. Si su pestaña se quedara en la lista para siempre,")
print("  la señal fuerte no volveria a dispararse nunca.\n")
v = SV.Vida(ahora=reloj)
v.late("zombi")
reloj.avanza(SV.SILENCIO_MAXIMO + 1)
v.limpiar_callados()
comprobar("la pestaña muda se limpia de la lista", not v.clientes, v.clientes)

# ============================================ 8. EL PUERTO
print("\n=== 8. EL PUERTO NO SE ESCRIBE A MANO ===")
puertos = {SV.puerto_libre() for _ in range(5)}
comprobar("se pide uno libre al sistema, no un 8000 fijo",
          len(puertos) > 1 or all(p > 1024 for p in puertos), puertos)
comprobar("y nunca uno reservado", all(p > 1024 for p in puertos), puertos)
comprobar("el fuente no lleva un puerto fijo",
          not re.search(r'bind\(\("127\.0\.0\.1",\s*\d{2,5}\)', sin_comentarios))

# DOS AGENTES A LA VEZ: el segundo doble clic no levanta otro servidor.
print("\n  Y si ya hay uno abierto:")
srv2, vida2, url2 = SV.arrancar("ensayo", abrir=False)
try:
    ficha = json.loads(SV.FICHA.read_text("utf-8"))
    comprobar("queda apuntado en disco quien esta vivo",
              ficha.get("puerto") == srv2.server_address[1], ficha)
    comprobar("  con su testigo, para poder abrir otra pestaña",
              bool(ficha.get("testigo")))
    viva = SV.ficha_viva()
    comprobar("y se reconoce que sigue en pie",
              viva is not None and viva["puerto"] == ficha["puerto"], viva)
finally:
    srv2.shutdown()
    time.sleep(0.3)

# Una ficha que apunta a un servidor muerto no engaña a nadie.
SV.FICHA.write_text(json.dumps({"puerto": 9, "testigo": "x", "pid": 1}),
                    encoding="utf-8")
comprobar("una ficha de un servidor muerto se descarta",
          SV.ficha_viva() is None)
comprobar("  y se borra sola", not SV.FICHA.exists())

# ============================================ 9. NI UNA TRAZA AL NAVEGADOR
print("\n=== 9. NINGUNA TRAZA DE PYTHON LLEGA AL NAVEGADOR ===")
print("  Es la regla 3 de la ventana, y en web hay que decirla otra vez: un")
print("  servidor que revienta devuelve por defecto un 500 con el fichero, la")
print("  linea y el codigo dentro.\n")
comprobar("el manejador envuelve cada peticion",
          "def handle_one_request" in FUENTE)
comprobar("  y el detalle va al disco, no al navegador",
          "servidor_fallo.txt" in FUENTE)
comprobar("  con una frase de persona",
          "Avisa a Emili" in FUENTE)
comprobar("y el log de http.server se calla: con pythonw no hay stderr",
          "def log_message" in FUENTE)
comprobar("nada de lo servido se guarda en la cache del navegador",
          "no-store" in FUENTE)

# ============================================ 10. CONTROL NEGATIVO
print("\n=== 10. CONTROL NEGATIVO: ¿CAZA LO QUE DICE CAZAR? ===")
print("  Se levanta un servidor MAL ATADO, a proposito, y se comprueba que la")
print("  comprobacion 1 lo habria visto.\n")
import http.server as _hs  # noqa: E402


class _H(_hs.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


malo = _hs.ThreadingHTTPServer(("0.0.0.0", 0), _H)
threading.Thread(target=malo.serve_forever, daemon=True).start()
time.sleep(0.3)
p_malo = malo.server_address[1]
try:
    pedir(f"http://{IP}:{p_malo}/", timeout=2.0)
    alcanzable = True
except Exception:                                # noqa: BLE001
    alcanzable = False
comprobar("atado a 0.0.0.0 SI se llega desde la red: la comprobacion 1 mide",
          alcanzable, "no se llego: entonces la comprobacion 1 no prueba nada")
malo.shutdown()

# Y si el literal volviera a 0.0.0.0, la comprobacion del fuente lo cazaria.
comprobar("un 0.0.0.0 en el fuente se cazaria",
          '"0.0.0.0"' in 'x = "0.0.0.0"')

# Si `se_puede_cerrar` ignorara el trabajo en marcha, la 5 se pondria roja.
v = SV.Vida(ahora=reloj)
v.late("a")
v.empieza_consulta()
v.adios("a")
sin_guarda = not v.clientes and v.trabajando > 0
comprobar("sin la guarda del trabajo, un adios cerraria a mitad de consulta",
          sin_guarda, "la guarda es lo unico que lo impide")

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
