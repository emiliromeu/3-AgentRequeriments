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

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
