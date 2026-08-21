#!/usr/bin/env python3
"""LA COLA DE DESCARGA POR DEMANDA. Cero red, cero API.

    python pruebas/prueba_cola.py

NI UNA PETICION A PETETE. La cola sale a la fuente; esta suite NO. Todo lo que
se prueba aqui es el apunte, la deduplicacion, la memoria de los vacios y las
dos cosas que no se negocian. El vaciado se prueba con la fuente doblada.

LAS DOS QUE NO SE NEGOCIAN:

  1. NI UN FICHERO DE `demanda/` ACABA EN GIT. El contenido de una consulta de
     la DGT es publico, pero el CONJUNTO Y LAS FECHAS dicen que pregunto un
     cliente y cuando. Git guarda eso para siempre. Con control negativo:
     quitando la regla, un `git add -A` se lo lleva.
  2. LA COLA NUNCA BLOQUEA. Ni al abrir ni al preguntar. Una mejora de la
     despensa no puede costarle una respuesta a nadie.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from agente_fiscal import cola as C             # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:110]}" if not ok else ""))
    if not ok:
        fallos.append(que)


def cola_de_mentira():
    """Apunta la cola a un temporal. Devuelve el directorio."""
    d = Path(tempfile.mkdtemp())
    C.COLA = d / "cola.json"
    C.DEMANDA = d / "demanda"
    return d


# ==================================== 1. EL APUNTE Y LOS TRES DUPLICADOS
print("\n=== 1. SE APUNTA (cuerpo, articulo), NO LA PREGUNTA ===")
print("  La clave no lleva nada del cliente: un numero de articulo no dice")
print("  quien pregunto ni que.\n")

guardado = (C.COLA, C.DEMANDA)
d = cola_de_mentira()
try:
    C.apuntar([("BOE-A-1992-28740#0", "80")])
    e = C.leer()["entradas"]
    comprobar("una consulta apunta un articulo", len(e) == 1, e)
    k = list(e)[0]
    comprobar("  la clave es cuerpo + articulo, sin rastro de la pregunta",
              k == "BOE-A-1992-28740#0#80", k)
    comprobar("  con veces=1 y fecha", e[k]["veces"] == 1 and e[k]["primera_vez"])

    print("\n    LOS TRES DUPLICADOS, QUE NO SON EL MISMO:")
    C.apuntar([("BOE-A-1992-28740#0", "80")])
    e = C.leer()["entradas"]
    comprobar("(1) dos personas, mismo articulo: UNA entrada, veces=2",
              len(e) == 1 and e[k]["veces"] == 2,
              (len(e), e[k]["veces"]))

    C.apuntar([("BOE-A-1992-28740#0", "91")])
    cob = {("BOE-A-1992-28740#0", "91")}
    pend = C.pendientes(None, cob)
    comprobar("(2) lo que YA tiene criterio no se pide",
              [p["articulo"] for p in pend] == ["80"],
              [p["articulo"] for p in pend])

    C.marcar("BOE-A-1992-28740#0", "80", C.SIN_RESULTADOS)
    pend = C.pendientes(None, set())
    comprobar("(3) lo que se busco y NO habia deja de pedirse",
              "80" not in [p["articulo"] for p in pend],
              [p["articulo"] for p in pend])
    print(f"        y se reintenta a los {C.DIAS_REINTENTO} dias, no antes")
    comprobar("  el plazo esta escrito con su motivo, no suelto",
              C.DIAS_REINTENTO == 90)

    # LO MAS PREGUNTADO PRIMERO.
    C.apuntar([("BOE-A-1992-28740#0", "95")] * 3)
    orden = [p["articulo"] for p in C.pendientes(None, set())]
    comprobar("se pide primero lo mas preguntado", orden[0] == "95", orden)
finally:
    shutil.rmtree(d, ignore_errors=True)
    C.COLA, C.DEMANDA = guardado


# ==================================== 2. NUNCA BLOQUEA
print("\n=== 2. LA COLA NUNCA BLOQUEA, NI AL ABRIR NI AL PREGUNTAR ===")

guardado = (C.COLA, C.DEMANDA)
try:
    # Con la cola ilegible, todo sigue.
    d = cola_de_mentira()
    C.COLA.write_text("{ esto no es json", encoding="utf-8")
    comprobar("una cola ilegible no levanta al leer",
              C.leer()["entradas"] == {})
    comprobar("  ni al apuntar", C.apuntar([("x#0", "1")]) >= 0)
    shutil.rmtree(d, ignore_errors=True)

    # Con el directorio imposible de escribir, tampoco.
    C.COLA = Path("/no/existe/de/ninguna/manera/cola.json")
    comprobar("una cola que no se puede escribir devuelve 0, no revienta",
              C.apuntar([("BOE-A-1992-28740#0", "80")]) == 0)
    comprobar("  y `aviso_de_silencio` tampoco revienta",
              isinstance(C.aviso_de_silencio(), str))
    comprobar("  ni `recien_bajado`", isinstance(C.recien_bajado(), dict))
finally:
    C.COLA, C.DEMANDA = guardado

FASE4 = (RAIZ / "fase4.py").read_text("utf-8")
comprobar("en la consulta, el apunte va dentro de un try que se traga todo",
          "from agente_fiscal import cola as _COLA" in FASE4
          and "except Exception:                            # noqa: BLE001"
          in FASE4)
INTERFAZ = (RAIZ / "interfaz.py").read_text("utf-8")
comprobar("y en la ventana el vaciado va EN UN HILO",
          "threading.Thread(target=trabajar, daemon=True).start()" in INTERFAZ)
comprobar("  y es LO ULTIMO del arranque, con la ventana ya viva",
          INTERFAZ.index("self._vaciar_cola_por_detras()")
          > INTERFAZ.index("self.motor = motor"))


# ==================================== 3. EL GUARDIAN DE GIT
print("\n=== 3. NI UN FICHERO DE demanda/ ACABA EN GIT ===")
print("  El contenido es publico; el conjunto y las fechas dicen que pregunto")
print("  un cliente y cuando, y git lo guarda para siempre.\n")

DEMANDA_REAL = RAIZ / "datos" / "dgt" / "demanda"
DEMANDA_REAL.mkdir(parents=True, exist_ok=True)
testigo = DEMANDA_REAL / "V0000-00.json"
testigo.write_text('{"numero": "V0000-00"}', encoding="utf-8")
try:
    r = subprocess.run(["git", "check-ignore", str(testigo)],
                       capture_output=True, text=True, cwd=str(RAIZ))
    comprobar("git IGNORA lo que baja la cola", r.returncode == 0, r.stdout)
    r2 = subprocess.run(["git", "check-ignore",
                         str(RAIZ / "datos" / "dgt" / "cola.json")],
                        capture_output=True, text=True, cwd=str(RAIZ))
    comprobar("  y tambien la cola, que dice QUE articulos se preguntaron",
              r2.returncode == 0, r2.stdout)

    # QUE UN `git add -A` NO SE LO LLEVE, que es como pasaria de verdad.
    r3 = subprocess.run(["git", "add", "-A", "--dry-run"],
                        capture_output=True, text=True, cwd=str(RAIZ))
    comprobar("un `git add -A` NO se lo lleva",
              "demanda/" not in r3.stdout and "cola.json" not in r3.stdout,
              [l for l in r3.stdout.splitlines() if "demanda" in l][:2])

    # Y QUE LA DESPENSA LO LEA IGUAL: la separacion es de transporte, no de uso.
    from agente_fiscal import dgt as D          # noqa: E402
    comprobar("pero la despensa SI lo lee: dos sitios, una sola despensa",
              any(p.name == "demanda" for p in D.CacheDGT().dirs),
              [p.name for p in D.CacheDGT().dirs])

    # --- CONTROL NEGATIVO: se quita la regla y el testigo entra.
    GI = (RAIZ / ".gitignore")
    original = GI.read_text("utf-8")
    try:
        GI.write_text(original.replace("datos/dgt/demanda/\n", ""),
                      encoding="utf-8")
        r4 = subprocess.run(["git", "check-ignore", str(testigo)],
                            capture_output=True, text=True, cwd=str(RAIZ))
        comprobar("(a) sin la regla, git DEJA de ignorarlo y se lo llevaria",
                  r4.returncode != 0, "sigue ignorado")
    finally:
        GI.write_text(original, encoding="utf-8")
    r5 = subprocess.run(["git", "check-ignore", str(testigo)],
                        capture_output=True, text=True, cwd=str(RAIZ))
    comprobar("(b) restaurada la regla, vuelve a estar protegido",
              r5.returncode == 0)
finally:
    testigo.unlink(missing_ok=True)


# ==================================== 4. EL SILENCIO Y LA PROMESA CUMPLIDA
print("\n=== 4. LA COLA DICE CUANTO LLEVA SIN PODER BAJAR ===")

guardado = (C.COLA, C.DEMANDA)
d = cola_de_mentira()
try:
    from datetime import date, timedelta

    C.apuntar([("BOE-A-1992-28740#0", "80")])
    comprobar("sin intentos todavia, no se avisa de nada",
              C.aviso_de_silencio() == "", C.aviso_de_silencio())

    dd = C.leer()
    dd["ultima_bajada"] = (date.today() - timedelta(days=9)).isoformat()
    C.guardar(dd)
    aviso = C.aviso_de_silencio()
    comprobar("a los 9 dias sin traer nada, lo dice", "9 días" in aviso, aviso)
    comprobar("  y dice a quien avisar", "Emili" in aviso, aviso)

    dd["ultima_bajada"] = date.today().isoformat()
    C.guardar(dd)
    comprobar("recien bajado, no se avisa de silencio",
              C.aviso_de_silencio() == "", C.aviso_de_silencio())

    # LA PROMESA CUMPLIDA.
    C.marcar("BOE-A-1992-28740#0", "80", C.BAJADA, bajadas=3)
    t = C.recien_bajado()
    comprobar("se puede decir que se encontro criterio de lo preguntado",
              t["articulos"] == 1 and t["consultas"] == 3, t)
    comprobar("  y la ventana lo dice al abrir",
              "Encontré criterio sobre" in INTERFAZ)

    # SIN COLA, EL SILENCIO ES NORMAL Y NO SE AVISA.
    dd = C.leer()
    for e in dd["entradas"].values():
        e["estado"] = C.BAJADA
    dd["ultima_bajada"] = (date.today() - timedelta(days=30)).isoformat()
    C.guardar(dd)
    comprobar("sin nada apuntado, 30 dias de silencio NO son un aviso",
              C.aviso_de_silencio() == "", C.aviso_de_silencio())
finally:
    shutil.rmtree(d, ignore_errors=True)
    C.COLA, C.DEMANDA = guardado

# ==================================== 5. «TODAVIA NO» EN VEZ DE «NO LO TENGO»
print("\n=== 5. QUE SE VEA QUE SE ESTA BUSCANDO ===")
print("  La cola ya apuntaba y ya bajaba, pero desde la ventana no se veia:")
print("  la respuesta se leia como «esto no lo sabe» cuando la verdad era")
print("  «esto lo esta buscando».\n")

guardado = (C.COLA, C.DEMANDA)
d = cola_de_mentira()
try:
    C.apuntar([("BOE-A-1992-28740#0", "80")])
    comprobar("un articulo apuntado se reconoce como «se esta buscando»",
              C.apuntados_de([("BOE-A-1992-28740#0", "80")]) == ["80"],
              C.apuntados_de([("BOE-A-1992-28740#0", "80")]))
    comprobar("  y uno que no se apunto, no",
              C.apuntados_de([("BOE-A-1992-28740#0", "999")]) == [])

    # Y LA HONESTIDAD DEL MENSAJE: si ya se busco y no habia, NO se dice que se
    # esta buscando. Seria mentir para quedar bien.
    C.marcar("BOE-A-1992-28740#0", "80", C.SIN_RESULTADOS)
    comprobar("si ya se busco y NO habia, no se dice que se esta buscando",
              C.apuntados_de([("BOE-A-1992-28740#0", "80")]) == [],
              C.apuntados_de([("BOE-A-1992-28740#0", "80")]))

    # EL ESTADO, sin barra de progreso.
    C.apuntar([("BOE-A-1992-28740#0", "91")])
    C.marcar("BOE-A-1992-28740#0", "91", C.BAJADA, bajadas=4)
    C.apuntar([("BOE-A-1992-28740#0", "95")])
    r = C.resumen()
    comprobar("el estado dice cuantos quedan en cola", r["en_cola"] == 1, r)
    comprobar("  cuantos entraron la ultima vez",
              r["ultima_vez_consultas"] == 4, r)
    comprobar("  y cuando", bool(r["cuando"]), r)
    frase = C.frase_de_estado()
    print(f"    «{frase}»")
    comprobar("la frase se puede leer de un vistazo", bool(frase), frase)
finally:
    shutil.rmtree(d, ignore_errors=True)
    C.COLA, C.DEMANDA = guardado

comprobar("NO hay barra de progreso de la cola: avanza a saltos y por detras",
          "barra" not in INTERFAZ.split("_vaciar_cola_por_detras")[1][:900].lower())
comprobar("y en modo ENSAYO la ventana NO sale a la fuente",
          'if not getattr(self.motor, "es_modelo_real", False):' in INTERFAZ)

FASE4b = (RAIZ / "fase4.py").read_text("utf-8")
comprobar("`fase4` dice QUE apunto, para que la ventana no lo recalcule",
          'res["apuntados_en_cola"]' in FASE4b)



# ==================== ATASCO: LA COLA QUE CRECE MAS DE LO QUE BAJA
print("\n=== ATASCO · UNA COLA QUE NO DA ABASTO SE VE IGUAL QUE IR BIEN ===")
print("  Baja de tres en tres por apertura y crece con lo que se pregunta,")
print("  asi que una punta de uso puede acumularla semanas sin que nadie lo")
print("  note. Desde dentro no se distingue de que todo vaya bien.\n")

import shutil as _sh
import tempfile as _tf
from datetime import date as _date, timedelta as _td


def _hace(dias):
    return (_date.today() - _td(days=dias)).isoformat()


_corral = Path(_tf.mkdtemp())
_guardada = C.COLA
C.COLA = _corral / "cola.json"
try:
    comprobar("el umbral son 14 dias, dicho como DECISION",
              C.DIAS_ESPERANDO_AVISO == 14, C.DIAS_ESPERANDO_AVISO)
    comprobar("con la cola vacia no hay nada que decir",
              C.aviso_de_atasco() == "", C.aviso_de_atasco())

    # EN USO NORMAL, CALLADA. Es la mitad del encargo: un aviso que sale
    # siempre deja de leerse a la tercera vez.
    C.apuntar([("c#0", "95"), ("c#0", "96")])
    comprobar("dos articulos apuntados hoy: NO se avisa de nada",
              C.aviso_de_atasco() == "", C.aviso_de_atasco())
    comprobar("  y la espera del mas viejo es de cero dias",
              C.espera_del_mas_viejo() == 0, C.espera_del_mas_viejo())

    # Uno que lleva esperando mas de la cuenta.
    _d = C.leer()
    _d["entradas"][C.clave("c#0", "95")]["primera_vez"] = _hace(20)
    C.guardar(_d)
    comprobar("con el mas viejo a 20 dias, SI se avisa", bool(C.aviso_de_atasco()))
    _av = C.aviso_de_atasco()
    print(f"    «{_av}»")
    comprobar("  y dice cuantos esperan", "2 artículo" in _av, _av)
    comprobar("  cuantos dias lleva el mas viejo", "20 días" in _av, _av)
    comprobar("  QUE SE PUEDE HACER: abrir el agente mas veces",
              "abrirlo más a menudo" in _av, _av)
    comprobar("  y A QUIEN avisar si corre prisa", "Emili" in _av, _av)

    # UN REFRESCO NO ES UNA PROMESA y no puede disparar el aviso: a nadie se le
    # dijo «lo estoy buscando» por algo de lo que YA hay criterio.
    C.COLA = _corral / "cola2.json"
    C.apuntar_refresco([("c#0", "20", _hace(900))])
    _d = C.leer()
    _d["entradas"][C.clave("c#0", "20")]["primera_vez"] = _hace(90)
    C.guardar(_d)
    comprobar("un refresco viejo NO dispara el aviso: no es una deuda con nadie",
              C.aviso_de_atasco() == "", C.aviso_de_atasco())
    comprobar("  aunque si esta en la cola para refrescarse",
              "20" in {e["articulo"] for e in C.pendientes()})
finally:
    C.COLA = _guardada
    _sh.rmtree(_corral, ignore_errors=True)


# Y LA VENTANA ENSEÑA UNO SOLO, con el de la fuente por delante.
_VEN = (Path(__file__).resolve().parent.parent / "interfaz.py").read_text("utf-8")
comprobar("la ventana enseña UN aviso, y el de la fuente manda",
          "_COLA.aviso_de_silencio() or _COLA.aviso_de_atasco()" in _VEN)




# ============================== REFRESCO: LO QUE ENVEJECE, POR DETRAS
print("\n=== REFRESCO · NADA VOLVIA A MIRAR UN ARTICULO YA SEMBRADO ===")
print("  PETETE y DYCTEA publican cada semana, asi que un articulo con")
print("  criterio de agosto se quedaba con el de agosto para siempre.")
print("  El umbral esta MEDIDO: de los 848 articulos con criterio, 480 se")
print("  mueven en 24 meses; refrescando solo esos cada 180 dias, 39 de cada")
print("  100 refrescos traen algo. Cada 30 dias serian 13 de cada 100.\n")

import shutil as _sh
import tempfile as _tf
from datetime import date as _date, timedelta as _td

_corral = Path(_tf.mkdtemp())
_guardada = C.COLA
C.COLA = _corral / "cola.json"
try:
    comprobar("el umbral de refresco es de 180 dias, y esta medido",
              C.DIAS_REFRESCO == 180, C.DIAS_REFRESCO)

    def _hace(dias):
        return (_date.today() - _td(days=dias)).isoformat()

    # Uno con criterio RECIENTE y otro con criterio VIEJO.
    C.apuntar_refresco([("c#0", "95", _hace(10)),
                           ("c#0", "20", _hace(400))])
    ks = {e["articulo"]: e for e in C.leer()["entradas"].values()}
    comprobar("los dos nacen BAJADA: tienen criterio, no hay nada pendiente",
              all(e["estado"] == C.BAJADA for e in ks.values()),
              {k: e["estado"] for k, e in ks.items()})
    comprobar("  y su reloj es LA FECHA DEL CRITERIO, no hoy",
              ks["20"]["buscado"] == _hace(400), ks["20"]["buscado"])

    p = {e["articulo"] for e in C.pendientes()}
    comprobar("el de criterio VIEJO sale a refrescar", "20" in p, p)
    comprobar("  y el RECIENTE no: no hay nada que mirar todavia",
              "95" not in p, p)

    # PRIMERO LO QUE FALTA. Un refresco no puede colarse delante de un
    # articulo del que no hay NADA: quien pregunto por ese se quedaria sin
    # nada mientras se gasta la peticion en mejorar lo que ya se pudo
    # contestar.
    C.apuntar([("c#0", "7")])
    orden = [e["articulo"] for e in C.pendientes()]
    comprobar("lo que FALTA va delante de lo que envejece",
              orden.index("7") < orden.index("20"), orden)

    # Y NO SE VUELVE A PEDIR LO MISMO: la memoria de siempre.
    C.marcar("c#0", "20", C.BAJADA, bajadas=2)
    comprobar("refrescado hoy, no vuelve a salir manana",
              "20" not in {e["articulo"] for e in C.pendientes()})

    # Y APUNTARLO OTRA VEZ NO REINICIA SU RELOJ hacia atras: si lo hiciera,
    # cada consulta lo devolveria a la cola y se pediria sin fin.
    C.apuntar_refresco([("c#0", "20", _hace(400))])
    e = C.leer()["entradas"][C.clave("c#0", "20")]
    comprobar("  y volver a apuntarlo no lo devuelve a la cola",
              "20" not in {x["articulo"] for x in C.pendientes()},
              e)
    comprobar("  aunque si cuenta que se ha preguntado otra vez",
              e.get("veces", 0) >= 2, e.get("veces"))

    comprobar("apuntar_refresco NUNCA levanta, como apuntar",
              C.apuntar_refresco([(None, None, None)]) == 0)
finally:
    C.COLA = _guardada
    _sh.rmtree(_corral, ignore_errors=True)




print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
