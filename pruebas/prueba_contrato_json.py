#!/usr/bin/env python3
"""EL CONTRATO DE LAS TRES ENTRADAS DE MAQUINA. Cero red, cero API.

    python pruebas/prueba_contrato_json.py

`verificar_json`, `estado_json` y `corpus_json` existen para que otro programa
pregunte y se fie de la respuesta sin leer una pantalla. Lo que ese programa da
por hecho no son detalles: es el contrato, y esta suite ES el contrato, aplicado
A LOS TRES CON LAS MISMAS COMPROBACIONES.

  1. stdout SOLO el JSON. Un objeto, una linea, nada delante ni detras.
  2. stderr vacio por defecto.
  3. Los codigos significan lo que dicen: 0 el si, 2 el no, otro un fallo.
  4. UN FALLO INTERNO NUNCA DEVUELVE ALGO QUE PAREZCA UNA BUENA RESPUESTA.
  5. Una llamada mal hecha es un fallo, no un «no». Y sale con JSON.
  6. Procedencia siempre, tambien en los fallos.
  7. Solo lectura: verificar, mirar el estado y leer el corpus no dejan rastro.

POR QUE LOS TRES EN UNA SUITE Y NO TRES SUITES. Porque lo que se prueba es que
son EL MISMO contrato. Tres suites separadas pasarian en verde el dia que uno
de los tres se fuera por su lado, que es exactamente lo que hay que cazar.

SE EJECUTAN LOS PROGRAMAS DE VERDAD, como subprocesos, y no se importan sus
`main`: lo que se prueba es lo que sale por stdout, lo que sale por stderr y el
codigo de salida, que es lo que vera quien los llame. Importandolos se probaria
otra cosa.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

PY_EXE = sys.executable
CORPUS = RAIZ / "datos" / "corpus"

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:140]}" if not ok else ""))
    if not ok:
        fallos.append(que)


def correr(guion, args, entrada=""):
    return subprocess.run([PY_EXE, str(RAIZ / guion), *args], input=entrada,
                          text=True, capture_output=True, cwd=str(RAIZ))


def solo_un_json(salida):
    """(es_un_json_y_una_linea, objeto). LA COMPROBACION QUE MAS SE ROMPE.

    No vale con que `json.loads` trague: un `print` de mas antes del objeto lo
    rompe, y uno DESPUES tambien. Se exige una unica linea con contenido.
    """
    lineas = [l for l in salida.splitlines() if l.strip()]
    if len(lineas) != 1:
        return False, None
    try:
        d = json.loads(salida)
    except (ValueError, TypeError):
        return False, None
    return isinstance(d, dict), d


# La cita buena que usa `verificar_json`, sacada del propio corpus para que no
# envejezca escrita a mano.
from agente_fiscal.indice import Indice            # noqa: E402
ix = Indice(CORPUS)
art = next(d for d in ix.docs
           if d.registro.get("clave") == "BOE-A-1992-28740#0#articulo 95")
TROZO = art.registro["texto_vigente"].split("\n")[1][:88].strip()
CITA = (f"El artículo 95 de la Ley 37/1992 dispone que «{TROZO}» "
        f"(https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a95).")
SIN_CITA = "En Cataluña la reduccion es del 95 por ciento."
del ix

# QUE ES UN «SI» Y QUE ES UN «NO» EN CADA UNO. La llamada que tiene que salir
# con 0 y la que tiene que salir con 2, y ademas la clave que un fallo NO puede
# traer nunca -la que hace que una respuesta parezca buena-.
LOS_TRES = [
    {"guion": "verificar_json.py", "clave_buena": "veredicto",
     "si": (["--ejercicio", "2023"], CITA),
     "no": (["--ejercicio", "2023"], SIN_CITA)},
    {"guion": "estado_json.py", "clave_buena": "listo",
     "si": ([], ""),
     # El «no» de este se provoca abajo, quitando una norma de la lista: aqui
     # no hay ninguna llamada que lo produzca, y eso es correcto.
     "no": None},
    {"guion": "corpus_json.py", "clave_buena": "respuestas",
     "si": (["literal", "--ejercicio", "2023"],
            "BOE-A-1992-28740#0#articulo 95\n"),
     "no": (["literal", "--ejercicio", "2023"], "inventada#0#articulo 1\n")},
]


# ==================================== 1 y 2. STDOUT SOLO EL JSON, STDERR NADA
print("\n=== 1. POR stdout NO SALE NADA MAS QUE EL JSON ===")
print("  Quien lee esto hace json.loads de TODO lo que salga. Un «cargando")
print("  corpus...» delante lo rompe, y lo rompe en el sitio mas tonto.\n")

for caso in LOS_TRES:
    args, entrada = caso["si"]
    r = correr(caso["guion"], args, entrada)
    caso["r_si"] = r
    ok, d = solo_un_json(r.stdout)
    caso["d_si"] = d
    comprobar(f"{caso['guion']}: un objeto JSON y una sola linea", ok,
              r.stdout[:90])
    comprobar(f"  y por stderr, nada", r.stderr == "", r.stderr[:90])


# ==================================== 3. LOS CODIGOS
print("\n=== 2. LOS CODIGOS: 0 EL SI, 2 EL NO, OTRO UN FALLO ===")

for caso in LOS_TRES:
    comprobar(f"{caso['guion']}: el caso bueno sale con 0",
              caso["r_si"].returncode == 0, caso["r_si"].returncode)
    comprobar(f"  y trae `{caso['clave_buena']}`",
              caso["clave_buena"] in (caso["d_si"] or {}),
              list(caso["d_si"] or {}))
    if caso["no"] is None:
        continue
    args, entrada = caso["no"]
    rn = correr(caso["guion"], args, entrada)
    ok, dn = solo_un_json(rn.stdout)
    comprobar(f"  el caso negativo sale con 2", rn.returncode == 2,
              rn.returncode)
    comprobar(f"  y sigue siendo un solo JSON", ok, rn.stdout[:90])

# EL «NO» DE `estado_json` SE PROVOCA DE VERDAD: se añade a la lista que viaja
# una norma que este equipo no tiene. Es exactamente lo que pasa en la oficina
# cuando aqui se ingiere una norma nueva y alla todavia no ha llegado.
lista = RAIZ / "normas_del_corpus.json"
copia_lista = lista.read_bytes()
try:
    d = json.loads(copia_lista.decode("utf-8"))
    d["normas"].append({"id": "BOE-A-1000-1", "nombre": "Norma que no esta",
                        "titulo": "Norma que no esta"})
    lista.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    rn = correr("estado_json.py", [], "")
    ok, dn = solo_un_json(rn.stdout)
    comprobar("estado_json.py: con una norma de la lista sin sembrar, sale 2",
              rn.returncode == 2, rn.returncode)
    comprobar("  y lo dice: `listo` en false y la norma en `faltan`",
              ok and dn.get("listo") is False
              and any(n["id"] == "BOE-A-1000-1"
                      for n in dn["normas"]["faltan"]), dn)
finally:
    lista.write_bytes(copia_lista)


# ==================================== 4. UN FALLO NO PARECE UNA BUENA RESPUESTA
print("\n=== 3. UN FALLO INTERNO NUNCA PARECE UNA BUENA RESPUESTA ===")
print("  Se rompe el corpus DE VERDAD -se aparta entero- y se mira que ninguno")
print("  de los tres conteste algo que pueda confundirse con haber mirado.\n")

def apartar_el_corpus(nombre: str):
    """Aparta `datos/corpus` para provocar un fallo, y NUNCA borra un respaldo.

    LA LINEA QUE ESTO SUSTITUYE BORRO EL CORPUS ENTERO. Decia:

        if guardado.exists():
            shutil.rmtree(guardado)

    y parecia prudente -limpiar los restos de una ejecucion anterior-. Pero un
    respaldo que ya existe NO son restos: es el corpus, apartado ahora mismo por
    otra ejecucion de la suite que todavia no lo ha devuelto. Dos suites de este
    banco apartan el corpus, `comprobar_todo` las lanza a las dos, y el 28/08/2026
    dos ejecuciones solapadas hicieron exactamente eso: la segunda «limpio los
    restos» de la primera y las diecisiete normas desaparecieron del disco.

    No se perdio nada irrecuperable -el corpus se rehace del crudo en cinco
    segundos, para eso esta excluido de git- pero el banco se quedo en rojo
    culpando a cuatro cosas que no tenian nada roto, que es el peor rojo que
    existe: el que hace desconfiar de la prueba en vez de del codigo.

    Ahora, si el respaldo existe, NO SE TOCA y la suite para diciendo que hacer.
    Y cada suite usa SU nombre, para que dos que corran a la vez no se confundan
    el respaldo de la otra con el suyo.
    """
    guardado = Path(f"{CORPUS}.apartado_por_{nombre}")
    if guardado.exists():
        raise SystemExit(
            f"\n  NO SE EJECUTA: ya existe {guardado.name}.\n"
            f"  Eso es el corpus apartado, no un resto que se pueda borrar:\n"
            f"  o hay otra ejecucion de esta suite en marcha -espera a que\n"
            f"  termine- o una murio a medias y hay que devolverlo a mano:\n"
            f"      mv {guardado.name} {Path(CORPUS).name}\n")
    return guardado


guardado = apartar_el_corpus("prueba_contrato_json")

# QUITAR EL CORPUS NO ES EL MISMO FALLO PARA LOS TRES, y esto lo aprendio esta
# suite poniendose roja. Para `verificar_json` y `corpus_json` es una averia:
# sin corpus no se puede verificar ni dar un literal, y contestar cualquier cosa
# seria mentir. Para `estado_json` NO: «no hay corpus» es LA RESPUESTA, y es
# justo la que da un equipo recien instalado. Exigirle un fallo ahi seria pedir
# que se rompiera al hacer bien su trabajo.
CORPUS.rename(guardado)
try:
    for caso in LOS_TRES:
        args, entrada = caso["si"]
        r = correr(caso["guion"], args, entrada)
        ok, d = solo_un_json(r.stdout)
        if caso["guion"] == "estado_json.py":
            comprobar("estado_json.py: sin corpus contesta, no revienta: "
                      "sale con 2", r.returncode == 2, r.returncode)
            comprobar("  y dice lo que ha visto: `sembrado` en false",
                      ok and d.get("sembrado") is False and d.get("listo") is False,
                      d)
            continue
        caso["d_roto"] = d
        comprobar(f"{caso['guion']}: sin corpus, el codigo NO es 0 ni 2",
                  r.returncode not in (0, 2), r.returncode)
        comprobar("  sigue saliendo un solo JSON: el contrato no se rompe",
                  ok, r.stdout[:90])
        # LA CLAVE QUE NO PUEDE ESTAR. No en `false`, no en `[]`: AUSENTE. Un
        # `false` se parece a «he mirado y no», que es lo que no ha pasado.
        comprobar(f"  y NO lleva `{caso['clave_buena']}` de ninguna forma",
                  ok and caso["clave_buena"] not in d, d)
        comprobar("  lleva `error` y dice cual",
                  ok and "corpus" in str(d.get("error", "")), d)
finally:
    guardado.rename(CORPUS)

# EL FALLO INTERNO DE `estado_json` ES OTRO, Y ESTA SUITE LO ENCONTRO. Se
# estropea la lista que viaja -`normas_del_corpus.json`-, que es contra lo que
# compara para decir si el corpus esta completo. Antes de esto contestaba
# «listo: true, esperadas: 0» con las diecisiete en `sobran` y codigo 0: un
# fallo nuestro con cara de buena respuesta, que es lo unico que el contrato
# prohibe del todo. Quien lo consumiera empezaba una tanda creyendo el corpus
# comprobado contra una lista que no se habia podido leer.
copia_lista = lista.read_bytes()
try:
    lista.write_text("esto no es json\n", encoding="utf-8")
    r = correr("estado_json.py", [], "")
    ok, d = solo_un_json(r.stdout)
    for c in LOS_TRES:
        if c["guion"] == "estado_json.py":
            c["d_roto"] = d
    comprobar("estado_json.py: con la lista de normas ilegible, NO sale 0 ni 2",
              r.returncode not in (0, 2), r.returncode)
    comprobar("  sigue saliendo un solo JSON", ok, r.stdout[:90])
    comprobar("  y NO lleva `listo` de ninguna forma, ni en false",
              ok and "listo" not in d, d)
    comprobar("  lleva `error` y nombra el fichero",
              ok and "normas_del_corpus" in str(d.get("detalle", "")), d)
finally:
    lista.write_bytes(copia_lista)

comprobar("y despues de romperlo y arreglarlo, los tres vuelven a contestar",
          all(correr(c["guion"], c["si"][0], c["si"][1]).returncode == 0
              for c in LOS_TRES))


# ==================================== 5. UNA LLAMADA MAL HECHA ES UN FALLO
print("\n=== 4. UNA LLAMADA MAL HECHA ES UN FALLO, NO UN «NO» ===")
print("  Argparse, tal cual viene, escribe el modo de empleo por stderr y sale")
print("  con 2. Y 2 significa RECHAZADO, NO LISTO o ALGUNA SIN CONTESTAR: tres")
print("  respuestas correctas de algo que nadie ha llegado a mirar. Ademas")
print("  dejaria stdout vacio, que rompe el json.loads de quien llame.\n")

for caso in LOS_TRES:
    r = correr(caso["guion"], ["--esta-opcion-no-existe"], "")
    ok, d = solo_un_json(r.stdout)
    comprobar(f"{caso['guion']}: no sale con 0 ni con 2",
              r.returncode not in (0, 2), r.returncode)
    comprobar("  y aun asi sale un JSON con `error`",
              ok and "error" in d, r.stdout[:90] or "(stdout vacio)")
    comprobar("  sin escribir el modo de empleo por stderr", r.stderr == "",
              r.stderr[:90])

# EL CONTROL: `--help` lo pide una persona en una consola, no un programa, y
# tiene que seguir funcionando como siempre.
rh = correr("corpus_json.py", ["--help"], "")
comprobar("pero `--help` sigue siendo para personas: sale con 0 y explica",
          rh.returncode == 0 and "buscar" in rh.stdout, rh.returncode)


# ==================================== 6. LA PROCEDENCIA
print("\n=== 5. CONTRA QUE CORPUS SE CONTESTO ===")
print("  Una respuesta sin esto no dice de que copia salio. Dentro de seis")
print("  meses es la diferencia entre poder reconstruirla y no poder.\n")

for caso in LOS_TRES:
    p = (caso["d_si"] or {}).get("procedencia") or {}
    c = p.get("corpus") or {}
    comprobar(f"{caso['guion']}: lleva procedencia", bool(p),
              list(caso["d_si"] or {}))
    comprobar("  con la version del contrato", p.get("contrato") == "1.0",
              p.get("contrato"))
    comprobar("  cuantas normas", c.get("normas") == 17, c)
    comprobar("  el sellado, que identifica la foto", bool(c.get("sellado")), c)
    comprobar("  y una huella que cambia si cambia un solo sello",
              len(str(c.get("sha256", ""))) >= 12, c)
    # Y EN EL FALLO TAMBIEN: saber contra que NO se pudo contestar tambien sirve.
    pf = (caso.get("d_roto") or {}).get("procedencia") or {}
    comprobar("  y los fallos tambien la llevan",
              pf.get("contrato") == "1.0", caso.get("d_roto"))

# LOS TRES HABLAN DE LA MISMA FOTO. Si uno calculara la huella por su cuenta y
# se desviara, esto se pone rojo: es la razon de que el contrato viva en un
# modulo y no copiado tres veces.
huellas = {c["guion"]: ((c["d_si"] or {}).get("procedencia") or {}).get("corpus")
           for c in LOS_TRES}
comprobar("los tres dan EXACTAMENTE la misma huella del corpus",
          len({json.dumps(h, sort_keys=True) for h in huellas.values()}) == 1,
          huellas)


# ==================================== 7. SOLO LECTURA
print("\n=== 6. PREGUNTAR ES MIRAR: NINGUNO ESCRIBE NADA ===")

# Lo que escriben OTROS y cae en la misma carpeta: el goteo guarda su avance
# cada pocos articulos y una sesion dura hora y media. Vigilarlo haria esta
# prueba INTERMITENTE, que es peor que no tenerla.
DE_OTROS = {"goteo.json", "cola.json", "visto.json"}


def foto(directorio):
    d = Path(directorio)
    if not d.is_dir():
        return {}
    return {str(f): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(d.rglob("*"))
            if f.is_file() and f.name not in DE_OTROS}


vigilados = [CORPUS, RAIZ / "datos" / "dgt" / "consultas", RAIZ / "datos" / "teac"]
antes = {str(v): foto(v) for v in vigilados}
for caso in LOS_TRES:
    correr(caso["guion"], caso["si"][0], caso["si"][1])
despues = {str(v): foto(v) for v in vigilados}
for v in vigilados:
    k = str(v)
    ido = set(antes[k]) - set(despues[k])
    tocados = [x for x in set(antes[k]) & set(despues[k])
               if antes[k][x] != despues[k][x]]
    comprobar(f"no cambia ni borra nada de {v.name}", not ido and not tocados,
              {"ido": list(ido)[:2], "tocados": tocados[:2]})

# Y LA COMPROBACION QUE NO DEPENDE DE QUIEN MAS ESTE CORRIENDO: se le pregunta
# a cada proceso con que MODO abre cada fichero. Escribir es abrir para
# escribir, y esto lo ve aunque el disco entero cambie por detras.
ESPIA = '''
import builtins, io, sys
from pathlib import Path
_abrir, _o, _wb, _wt = builtins.open, Path.open, Path.write_bytes, Path.write_text
escrituras = []
def modo_de(a, k):
    return k.get("mode") or (a[0] if a and isinstance(a[0], str) else "r")
def espia(f, *a, **k):
    if any(c in modo_de(a, k) for c in "wax+"): escrituras.append(str(f))
    return _abrir(f, *a, **k)
def espia_p(self, *a, **k):
    if any(c in modo_de(a, k) for c in "wax+"): escrituras.append(str(self))
    return _o(self, *a, **k)
def espia_wb(self, *a, **k):
    escrituras.append(str(self)); return _wb(self, *a, **k)
def espia_wt(self, *a, **k):
    escrituras.append(str(self)); return _wt(self, *a, **k)
builtins.open = espia; Path.open = espia_p
Path.write_bytes = espia_wb; Path.write_text = espia_wt
sys.argv = ARGV
sys.stdin = io.StringIO(ENTRADA)
import runpy
try:
    runpy.run_path(GUION, run_name="__main__")
except SystemExit:
    pass
builtins.open = _abrir; Path.open = _o
Path.write_bytes = _wb; Path.write_text = _wt
_abrir(SONDA, "w").write("\\n".join(escrituras))
'''
sonda = RAIZ / "datos" / "_sonda_contrato.txt"
for caso in LOS_TRES:
    args, entrada = caso["si"]
    codigo = (ESPIA.replace("ARGV", repr([caso["guion"], *args]))
              .replace("ENTRADA", repr(entrada))
              .replace("GUION", repr(caso["guion"]))
              .replace("SONDA", repr(str(sonda))))
    subprocess.run([PY_EXE, "-c", codigo], cwd=str(RAIZ), capture_output=True,
                   text=True)
    try:
        escritas = [x for x in (sonda.read_text("utf-8").splitlines()
                                if sonda.is_file() else []) if x.strip()]
    finally:
        if sonda.is_file():
            sonda.unlink()
    comprobar(f"{caso['guion']}: EN EJECUCION no abre nada para escribir",
              not escritas, escritas[:3])


# ==================================== CONTROL NEGATIVO
print("\n=== CONTROL NEGATIVO: la suite tiene que ponerse roja ===")
print("  Ninguna prueba se da por buena sin verla fallar cuando debe fallar.")
print("  Se rompe el contrato A PROPOSITO, en una COPIA, y se comprueba que la")
print("  comprobacion de arriba lo caza. Sin esto, un verde no dice nada.\n")

copia = RAIZ / "estado_json_ROTO_por_la_suite.py"
try:
    fuente = (RAIZ / "estado_json.py").read_text(encoding="utf-8")
    # El fallo clasico y el motivo de que esta comprobacion exista: una linea
    # de progreso delante del JSON.
    roto = fuente.replace('    _escribir(estado)',
                          '    print("cargando corpus...")\n    _escribir(estado)')
    assert roto != fuente, "no se ha podido romper la copia"
    copia.write_text(roto, encoding="utf-8")
    r = correr(copia.name, [], "")
    ok, _ = solo_un_json(r.stdout)
    comprobar("con un `print` delante del JSON, la comprobacion 1 se pone roja",
              not ok, r.stdout[:90])

    # Y el otro fallo, el que de verdad importa: un fallo que contesta `listo`.
    roto2 = fuente.replace(
        '    return _fallo_de(motivo, CORPUS, detalle)',
        '    _escribir({"listo": True, "error": motivo})\n    return 1')
    assert roto2 != fuente, "no se ha podido romper la copia (2)"
    copia.write_text(roto2, encoding="utf-8")
    CORPUS.rename(guardado)
    try:
        r2 = correr(copia.name, [], "")
    finally:
        guardado.rename(CORPUS)
    ok2, d2 = solo_un_json(r2.stdout)
    comprobar("y un fallo que dijera `listo` tambien se pondria rojo",
              ok2 and "listo" in d2, d2)
finally:
    if copia.is_file():
        copia.unlink()


print("\n" + "=" * 74)
if fallos:
    print(f"{len(fallos)} FALLO(S):")
    for f in fallos:
        print(f"   - {f}")
    sys.exit(1)
print("TODO EN VERDE · los tres cumplen el MISMO contrato")
sys.exit(0)
