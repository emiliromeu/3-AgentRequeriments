#!/usr/bin/env python3
"""EL CONTRATO DE LA ENTRADA DE MAQUINA. Cero red, cero API.

    python pruebas/prueba_verificar_json.py

`verificar_json.py` existe para que otro programa pregunte «¿esto se sostiene?»
y se fie de la respuesta sin leer una pantalla. Lo que otro programa da por
hecho no son detalles: es el contrato, y esta suite ES el contrato.

  1. stdout SOLO el JSON. Ni una linea de mas, nunca, ni con `--humano`.
  2. Codigos: 0 aceptado, 2 rechazado, otro fallo. Y un fallo interno NUNCA
     emite JSON de aceptacion.
  3. Las caches REALES. Ni una ruta con «prueba» dentro.
  4. Solo lectura: no escribe en el corpus ni en las caches.
  5. Procedencia: contra que corpus se verifico.

SE EJECUTA EL PROGRAMA DE VERDAD, como subproceso, y no se importa su `main`:
lo que se prueba es lo que sale por stdout y el codigo de salida, que es
exactamente lo que vera quien lo llame. Importandolo se probaria otra cosa.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

PY = sys.executable
GUION = RAIZ / "verificar_json.py"
CORPUS = RAIZ / "datos" / "corpus"

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:120]}" if not ok else ""))
    if not ok:
        fallos.append(que)


def correr(texto, *args):
    return subprocess.run([PY, str(GUION), *args], input=texto, text=True,
                          capture_output=True, cwd=str(RAIZ))


def leer_json(salida):
    try:
        return json.loads(salida)
    except (ValueError, TypeError):
        return None


from agente_fiscal.indice import Indice            # noqa: E402
ix = Indice(CORPUS)
art = next(d for d in ix.docs
           if d.registro.get("clave") == "BOE-A-1992-28740#0#articulo 95")
TROZO = art.registro["texto_vigente"].split("\n")[1][:88].strip()
BUENO = (f"El artículo 95 de la Ley 37/1992 dispone que «{TROZO}» "
         f"(https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a95).")
MALO = "En Cataluña la reduccion es del 95 por ciento."

print(f"\n  fragmento literal del corpus: «{TROZO[:56]}...»")


# ==================================== 1. stdout SOLO EL JSON
print("\n=== 1. POR stdout NO SALE NADA MAS QUE EL JSON ===")
print("  Quien lee esto hace json.loads de TODO lo que salga. Un «cargando")
print("  corpus...» delante lo rompe, y lo rompe en el sitio mas tonto.\n")

r = correr(BUENO, "--ejercicio", "2023")
d = leer_json(r.stdout)
comprobar("lo que sale por stdout es JSON valido, entero", d is not None,
          r.stdout[:90])
comprobar("  una sola linea, sin nada delante ni detras",
          len([l for l in r.stdout.splitlines() if l.strip()]) == 1,
          r.stdout[:90])
comprobar("  y por stderr, nada", r.stderr == "", r.stderr[:90])

# CON --humano, el informe va a stderr. Si fuera a stdout romperia el contrato
# SOLO cuando alguien pasara esa opcion: el peor momento para descubrirlo.
rh = correr(BUENO, "--ejercicio", "2023", "--humano")
comprobar("con --humano, stdout SIGUE siendo solo el JSON",
          leer_json(rh.stdout) is not None
          and len([l for l in rh.stdout.splitlines() if l.strip()]) == 1,
          rh.stdout[:90])
comprobar("  y el informe legible sale por stderr", len(rh.stderr) > 40,
          rh.stderr[:90])


# ==================================== 2. LOS CODIGOS DE SALIDA
print("\n=== 2. LOS CODIGOS: 0 ACEPTADO, 2 RECHAZADO, OTRO FALLO ===")
comprobar("un texto con su cita: codigo 0", r.returncode == 0, r.returncode)
comprobar("  y el veredicto lo dice igual", d and d["veredicto"] == "ACEPTADO",
          d and d.get("veredicto"))

r2 = correr(MALO, "--ejercicio", "2023")
d2 = leer_json(r2.stdout)
comprobar("un texto sin ninguna cita: codigo 2", r2.returncode == 2,
          r2.returncode)
comprobar("  RECHAZADO, que es lo correcto y no se toca",
          d2 and d2["veredicto"] == "RECHAZADO", d2 and d2.get("veredicto"))
comprobar("  y dice por que", d2 and "sin fuente no hay respuesta"
          in d2.get("motivo_global", ""), d2 and d2.get("motivo_global"))


# ==================================== 3. UN FALLO NUNCA ES UNA ACEPTACION
print("\n=== 3. UN FALLO INTERNO NUNCA EMITE JSON DE ACEPTACION ===")
print("  Un verificador que ante un fallo suyo pudiera decir «aceptado» no es")
print("  un verificador. Se prueba rompiendo el corpus de dos maneras.\n")

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


guardado = apartar_el_corpus("prueba_verificar_json")

# (a) CORPUS AUSENTE
CORPUS.rename(guardado)
try:
    ra = correr(BUENO, "--ejercicio", "2023")
    da = leer_json(ra.stdout)
    comprobar("sin corpus, el codigo NO es 0 ni 2",
              ra.returncode not in (0, 2), ra.returncode)
    comprobar("  sigue saliendo JSON valido: no se rompe el contrato",
              da is not None, ra.stdout[:90])
    comprobar("  y NO lleva veredicto, de ninguna clase",
              da is not None and "veredicto" not in da, da)
    comprobar("  lleva `error` y dice cual", da is not None
              and "corpus" in str(da.get("error", "")), da)
finally:
    guardado.rename(CORPUS)

# (b) CORPUS ILEGIBLE
uno = CORPUS / "BOE-A-1992-28740.jsonl"
copia = uno.read_bytes()
try:
    uno.write_bytes(b"\x00\x01esto no es json\n")
    rb = correr(BUENO, "--ejercicio", "2023")
    db = leer_json(rb.stdout)
    comprobar("con el corpus ilegible, el codigo NO es 0 ni 2",
              rb.returncode not in (0, 2), rb.returncode)
    comprobar("  y tampoco lleva veredicto",
              db is not None and "veredicto" not in db, db)
finally:
    uno.write_bytes(copia)

comprobar("y despues de romperlo y arreglarlo, sigue aceptando",
          correr(BUENO, "--ejercicio", "2023").returncode == 0)


# ==================================== 4. LAS CACHES REALES
print("\n=== 4. NI UNA RUTA CON «PRUEBA» DENTRO ===")
print("  Las de `casos/dgt_prueba` y `casos/teac_prueba` son SOLO de")
print("  `fase3.py probar`, donde los casos adversarios necesitan criterio")
print("  inventado. Aqui serian falsas en las DOS direcciones: una cita")
print("  autentica saldria NO_VERIFICABLE por no estar en la cache de prueba,")
print("  y una cita a un caso inventado saldria VERIFICADA.\n")

FUENTE = GUION.read_text("utf-8")


def _solo_ordenes(fuente: str) -> str:
    """El codigo sin comentarios NI DOCSTRINGS.

    LOS DOCSTRINGS TAMBIEN SE QUITAN, y es la cuarta vez que hace falta
    aprenderlo: la primera version de esta comprobacion salia roja porque el
    docstring de `verificar_json` NOMBRA `casos/dgt_prueba` para explicar
    POR QUE NO se usa. Leer la frase que explica algo en vez de la que lo hace
    ya nos ha dado un verde falso -«resumelo», «pythonw»- y ahora un rojo
    falso. Se pregunta al arbol de sintaxis, que sabe distinguirlos.
    """
    import ast
    arbol = ast.parse(fuente)
    fuera = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            cuerpo = getattr(nodo, "body", [])
            if (cuerpo and isinstance(cuerpo[0], ast.Expr)
                    and isinstance(cuerpo[0].value, ast.Constant)
                    and isinstance(cuerpo[0].value.value, str)):
                d = cuerpo[0]
                fuera.update(range(d.lineno, (d.end_lineno or d.lineno) + 1))
    return "\n".join(
        l for n, l in enumerate(fuente.splitlines(), start=1)
        if n not in fuera and l.strip() and not l.strip().startswith("#"))


ordenes = _solo_ordenes(FUENTE)
# UNA RUTA, no la palabra suelta: «no se comprueba la version» contiene
# «prueba» y no es una ruta de nada. Se busca el segmento de camino:
# `dgt_prueba`, `teac_prueba`, `prueba/`, `/prueba`.
import re as _re
_RUTA_DE_PRUEBA = _re.compile(r"[\w-]*_prueba\b|\bprueba[\w-]*[/\\]|[/\\]prueba",
                              _re.IGNORECASE)
sospechosas = [l for l in ordenes.splitlines() if _RUTA_DE_PRUEBA.search(l)]
comprobar("el guion no nombra ninguna ruta de prueba en su CODIGO",
          not sospechosas, sospechosas[:2])
# EL CONTROL: el patron tiene que cazar lo que busca, o no comprueba nada.
comprobar("  y el patron caza una ruta de prueba de verdad",
          bool(_RUTA_DE_PRUEBA.search('CacheDGT(RAIZ / "casos" / "dgt_prueba")'))
          and not _RUTA_DE_PRUEBA.search("no se comprueba la version"))
comprobar("  ni construye caches a mano: usa las de por defecto",
          "cache_dgt=" not in ordenes and "cache_teac=" not in ordenes)
# EL CONTROL: que quitar docstrings no haya vaciado el fichero, porque
# entonces la comprobacion de arriba pasaria siempre.
comprobar("  y quedan ordenes que mirar, no un fichero vacio",
          len(ordenes.splitlines()) > 40, len(ordenes.splitlines()))

# Y EN EJECUCION, que es lo que de verdad importa: se le pregunta al proceso
# por los ficheros que ha abierto.
sonda = RAIZ / "datos" / "_sonda_rutas.txt"
codigo = (
    "import builtins, io, sys, json\n"
    "from pathlib import Path\n"
    "_abrir, _o = builtins.open, Path.open\n"
    "vistas = []\n"
    "def espia(f, *a, **k):\n"
    "    vistas.append(str(f)); return _abrir(f, *a, **k)\n"
    "def espia_p(self, *a, **k):\n"
    "    vistas.append(str(self)); return _o(self, *a, **k)\n"
    "builtins.open = espia; Path.open = espia_p\n"
    "sys.argv = ['verificar_json.py', '--ejercicio', '2023']\n"
    "sys.stdin = io.StringIO(TEXTO)\n"
    "import runpy\n"
    "try:\n"
    "    runpy.run_path('verificar_json.py', run_name='__main__')\n"
    "except SystemExit:\n"
    "    pass\n"
    "builtins.open = _abrir; Path.open = _o\n"
    "_abrir(SONDA, 'w').write('\\n'.join(vistas))\n"
).replace("TEXTO", repr(BUENO)).replace("SONDA", repr(str(sonda)))
subprocess.run([PY, "-c", codigo], cwd=str(RAIZ), capture_output=True, text=True)
try:
    rutas = sonda.read_text("utf-8").splitlines() if sonda.is_file() else []
    con_prueba = [x for x in rutas if "prueba" in x.lower()]
    comprobar("y EN EJECUCION no abre ni un fichero con «prueba» en la ruta",
              not con_prueba, con_prueba[:3])
    comprobar("  si abre la cache real de la DGT o el corpus",
              any("datos/corpus" in x for x in rutas), len(rutas))
finally:
    if sonda.is_file():
        sonda.unlink()


# ==================================== 5. SOLO LECTURA
print("\n=== 5. VERIFICAR ES MIRAR: NO ESCRIBE NADA ===")
print("  Un verificador que deja rastro cambia lo que verifica la proxima vez,")
print("  y ademas se puede llamar en paralelo desde varios sitios.\n")


# LO QUE ESCRIBEN OTROS Y CAE EN LA MISMA CARPETA. El goteo guarda su avance
# en `datos/dgt/goteo.json` cada diez articulos, y la cola el suyo: si una
# sesion de goteo esta corriendo mientras pasa la suite -que es lo normal, dura
# hora y media- la foto cambia por su culpa y esto salia rojo culpando al
# verificador. La comprobacion de verdad es la de abajo, que mira lo que abre
# ESTE proceso.
DE_OTROS = {"goteo.json", "cola.json", "visto.json"}


def foto(directorio):
    d = Path(directorio)
    if not d.is_dir():
        return {}
    salida = {}
    for f in sorted(d.rglob("*")):
        if f.is_file() and f.name not in DE_OTROS:
            salida[str(f)] = hashlib.sha256(f.read_bytes()).hexdigest()
    return salida


# LO QUE SE VIGILA: lo que este programa LEE. `datos/dgt/crudo` queda fuera a
# proposito: es el cuaderno de PETETE -HTML en bruto que reescribe quien este
# descargando- y con una sesion de goteo en marcha cambia sola cada pocos
# segundos. Vigilarla hacia esta prueba INTERMITENTE, que es peor que no
# tenerla: una prueba que a veces falla se acaba ignorando.
vigilados = [CORPUS, RAIZ / "datos" / "dgt" / "consultas",
             RAIZ / "datos" / "teac"]
antes = {str(v): foto(v) for v in vigilados}
correr(BUENO, "--ejercicio", "2023")
correr(MALO, "--ejercicio", "2023", "--humano")
despues = {str(v): foto(v) for v in vigilados}
# QUE NO CAMBIE NI DESAPAREZCA NADA DE LO QUE YA ESTABA.
#
# LOS FICHEROS NUEVOS NO SE CUENTAN, y no es una rendicion: `datos/dgt` es
# donde el goteo va dejando lo que baja, y una sesion dura hora y media. Con
# una corriendo, aqui aparecen consultas nuevas cada pocos segundos y la foto
# sale distinta por su culpa. Que ESTE programa no crea ninguno lo prueba la
# comprobacion de mas abajo, que mira con que MODO abre cada fichero y no
# depende de quien mas este corriendo.
#
# Lo que si es suyo y solo suyo es cambiar o borrar algo que ya existia: eso
# ningun otro proceso del proyecto lo hace, asi que aqui no hay carrera.
for v in vigilados:
    k = str(v)
    ido = set(antes[k]) - set(despues[k])
    tocados = [x for x in set(antes[k]) & set(despues[k])
               if antes[k][x] != despues[k][x]]
    comprobar(f"no cambia ni borra nada de {v.name}",
              not ido and not tocados,
              {"ido": list(ido)[:2], "tocados": tocados[:2]})
# Y LA COMPROBACION QUE NO DEPENDE DE QUIEN MAS ESTE CORRIENDO: se le pregunta
# al proceso con que MODO abre cada fichero. Escribir es abrir para escribir;
# esto lo ve aunque el disco entero cambie por detras.
sonda2 = RAIZ / "datos" / "_sonda_modos.txt"
codigo2 = (
    "import builtins, io, sys\n"
    "from pathlib import Path\n"
    "_abrir, _o, _wb, _wt = builtins.open, Path.open, Path.write_bytes, Path.write_text\n"
    "escrituras = []\n"
    "def modo_de(a, k):\n"
    "    m = k.get('mode') or (a[0] if a and isinstance(a[0], str) else 'r')\n"
    "    return m\n"
    "def espia(f, *a, **k):\n"
    "    if any(c in modo_de(a, k) for c in 'wax+'): escrituras.append(str(f))\n"
    "    return _abrir(f, *a, **k)\n"
    "def espia_p(self, *a, **k):\n"
    "    if any(c in modo_de(a, k) for c in 'wax+'): escrituras.append(str(self))\n"
    "    return _o(self, *a, **k)\n"
    "def espia_wb(self, *a, **k):\n"
    "    escrituras.append(str(self)); return _wb(self, *a, **k)\n"
    "def espia_wt(self, *a, **k):\n"
    "    escrituras.append(str(self)); return _wt(self, *a, **k)\n"
    "builtins.open = espia; Path.open = espia_p\n"
    "Path.write_bytes = espia_wb; Path.write_text = espia_wt\n"
    "sys.argv = ['verificar_json.py', '--ejercicio', '2023', '--humano']\n"
    "sys.stdin = io.StringIO(TEXTO)\n"
    "import runpy\n"
    "try:\n"
    "    runpy.run_path('verificar_json.py', run_name='__main__')\n"
    "except SystemExit:\n"
    "    pass\n"
    "builtins.open = _abrir; Path.open = _o\n"
    "Path.write_bytes = _wb; Path.write_text = _wt\n"
    "_abrir(SONDA, 'w').write('\\n'.join(escrituras))\n"
).replace("TEXTO", repr(BUENO)).replace("SONDA", repr(str(sonda2)))
subprocess.run([PY, "-c", codigo2], cwd=str(RAIZ), capture_output=True, text=True)
try:
    escritas = [x for x in (sonda2.read_text("utf-8").splitlines()
                            if sonda2.is_file() else []) if x.strip()]
    comprobar("EN EJECUCION no abre ni un fichero para escribir",
              not escritas, escritas[:3])
finally:
    if sonda2.is_file():
        sonda2.unlink()

comprobar("y el contrato lo dice por escrito, no solo lo cumple",
          "SOLO LECTURA" in FUENTE and "NO ESCRIBE NADA" in FUENTE)


# ==================================== 6. LA PROCEDENCIA
print("\n=== 6. CONTRA QUE CORPUS SE VERIFICO ===")
print("  Un «verificada» sin esto no dice contra que. Dentro de seis meses es")
print("  la diferencia entre poder reconstruir una respuesta y no poder.\n")

p = (d or {}).get("procedencia") or {}
comprobar("el JSON lleva procedencia", bool(p), d and list(d))
comprobar("  con la version del contrato", p.get("contrato") == "1.0",
          p.get("contrato"))
c = p.get("corpus") or {}
comprobar("  cuantas normas", c.get("normas") == 17, c)
comprobar("  el sellado MAS RECIENTE, que identifica la foto",
          bool(c.get("sellado")), c)
comprobar("  y una huella que cambia si cambia un solo sello",
          len(str(c.get("sha256", ""))) >= 12, c)
# Y EN EL FALLO TAMBIEN: saber contra que NO se pudo verificar tambien sirve.
# Se provoca uno de verdad -corpus fuera- en vez de dar la comprobacion por
# buena: un `or True` al final no comprueba nada.
CORPUS.rename(guardado)
try:
    df = leer_json(correr(BUENO).stdout) or {}
finally:
    guardado.rename(CORPUS)
comprobar("los fallos tambien llevan procedencia",
          bool(df.get("procedencia")), df)
comprobar("  con la version del contrato, aunque el corpus no este",
          (df.get("procedencia") or {}).get("contrato") == "1.0", df)

print("\n" + "=" * 74)
if fallos:
    print(f"{len(fallos)} FALLO(S):")
    for f in fallos:
        print(f"   - {f}")
    sys.exit(1)
print("TODO EN VERDE · el contrato se cumple y esta escrito")
sys.exit(0)
