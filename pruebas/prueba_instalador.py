#!/usr/bin/env python3
"""EL PRIMER ARRANQUE, ROMPIENDO EL EQUIPO A PROPOSITO. Cero API de Anthropic.

Es lo PRIMERO que pasa en un PC de la oficina. Si se rompe, no hay agente: no
hay respuesta mala que revisar, hay una ventana que no abre.

Diez escenarios, cada uno sobre una COPIA en un directorio temporal. Nunca se
toca el proyecto de verdad: un banco que puede estropear lo que prueba no se
ejecuta cuando hace falta, que es la unica vez que importa.

TRES PIEZAS SE SUSTITUYEN POR UN DOBLE, y las tres por el mismo motivo -salen
a la red-:
  · `agente_fiscal/modelo.comprobar_credencial` -> responde lo que diga el
    escenario, para poder probar la clave buena Y la mala;
  · `fase1.py`      -> escribe los .jsonl sin bajar del BOE;
  · `interfaz.py`   -> no abre ventana, solo deja constancia;
  · `dialogo_clave` -> hace de persona que rellena la ventana, o dice que no
    hay pantalla para probar el camino de consola.

Lo que SI se ejecuta de verdad: el lanzador entero, la creacion del venv y el
`pip install`. Ahi no hay doble que valga.

    python pruebas/prueba_instalador.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
# Id y nombre, como los da el catalogo: el instalador enseña el NOMBRE
# mientras baja, y con el id a secas la pantalla diria «bajando
# BOE-A-1992-28740...», que no le dice nada a nadie. El nombre sale del
# `norma_titulo` del corpus, asi que aqui se escriben los de verdad.
NORMAS_CON_NOMBRE = [
    ("BOE-A-1992-28740", "Ley 37/1992"),
    ("BOE-A-1992-28925", "Real Decreto 1624/1992"),
    ("BOE-A-2003-23186", "Ley 58/2003, General Tributaria"),
]
NORMAS = [i for i, _n in NORMAS_CON_NOMBRE]
CLAVE = "sk-ant-de-mentira-para-la-prueba"

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"    {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:90]}" if not ok else ""))
    if not ok:
        fallos.append(que)


FASE1_DOBLE = '''#!/usr/bin/env python3
"""DOBLE de fase1.py: escribe el corpus sin bajar del BOE."""
import sys
from pathlib import Path
d = Path(__file__).resolve().parent / "datos" / "corpus"
d.mkdir(parents=True, exist_ok=True)
(d / (sys.argv[2] + ".jsonl")).write_text('{"prueba": true}\\n', encoding="utf-8")
print("ingerido (doble de prueba)")
sys.exit(0)
'''

# El doble de la ventana TIENE QUE SEGUIR VIVO unos segundos: el lanzador
# comprueba a los 2 que el proceso no se ha muerto -es lo que detecta un
# programa que revienta al arrancar- asi que un doble que sale al instante se
# ve como una caida. Y hace bien en verse asi.
INTERFAZ_DOBLE = '''"""DOBLE de interfaz.py: no abre ventana, deja constancia."""
import time
from pathlib import Path
d = Path(__file__).resolve().parent / "datos"
d.mkdir(exist_ok=True)
(d / "ventana_abierta.txt").write_text("si")
time.sleep(6)
'''


def dialogo_doble(ventana: bool) -> str:
    """En el banco no hay nadie que rellene una ventana: o se dice que no hay
    pantalla -y se prueba el camino de consola- o se hace de persona."""
    if not ventana:
        return ('def hay_entorno_grafico():\n    return False\n'
                'def pedir_clave(c, g):\n    return "", True\n')
    return (f'def hay_entorno_grafico():\n    return True\n'
            f'def pedir_clave(comprobador, guardar):\n'
            f'    guardar({CLAVE!r})\n'
            f'    vale, _ = comprobador()\n'
            f'    return ({CLAVE!r} if vale else ""), False\n')


def modelo_doble(vale: bool) -> str:
    frase = ("credencial correcta (sk-ant-...prueba)" if vale else
             "La credencial existe pero la API la rechaza (401). Revisa que la "
             "clave sea correcta y no este revocada.")
    return ('"""DOBLE de modelo.py: no sale a la red."""\n'
            'def comprobar_credencial(*m):\n'
            f'    return {vale!r}, {frase!r}\n')


def preparar(nombre, con_venv=True, con_env=True, env_vacio=False,
             con_corpus=True, con_dependencia=True, clave_vale=True,
             ventana=False) -> Path:
    """Una copia del proyecto, rota exactamente por donde diga el escenario."""
    destino = Path(tempfile.mkdtemp(prefix=f"agente_{nombre}_"))
    for f in ("instalar.py", "requisitos.txt", ".env.ejemplo",
              "abrir_agente.command", "abrir_agente.bat"):
        shutil.copy2(RAIZ / f, destino / f)
    (destino / "abrir_agente.command").chmod(0o755)

    (destino / "fase1.py").write_text(FASE1_DOBLE, encoding="utf-8")
    (destino / "interfaz.py").write_text(INTERFAZ_DOBLE, encoding="utf-8")
    (destino / "dialogo_clave.py").write_text(dialogo_doble(ventana),
                                              encoding="utf-8")
    (destino / "agente_fiscal").mkdir()
    (destino / "agente_fiscal" / "__init__.py").write_text("", encoding="utf-8")
    (destino / "agente_fiscal" / "modelo.py").write_text(
        modelo_doble(clave_vale), encoding="utf-8")
    # EL CATALOGO VA DE VERDAD, NO DOBLADO. Es de quien depende ahora el
    # instalador para saber que normas existen, y es pura lectura de ficheros:
    # doblarlo seria probar mi doble en vez de la pieza. Sin el, el instalador
    # revienta al importar y los escenarios fallan por donde no toca -que es
    # como se descubrio que faltaba-.
    shutil.copy2(RAIZ / "agente_fiscal" / "catalogo.py",
                 destino / "agente_fiscal" / "catalogo.py")

    if con_venv:
        subprocess.run([sys.executable, "-m", "venv", str(destino / ".venv")],
                       capture_output=True)
        if con_dependencia:
            # Se copia el paquete ya instalado en vez de bajarlo: lo que se
            # prueba aqui es que el instalador NO lo reinstale.
            import anthropic
            origen = Path(anthropic.__file__).resolve().parent.parent
            libs = list((destino / ".venv" / "lib").glob("python*/site-packages"))
            if libs:
                for paquete in origen.glob("*"):
                    if paquete.name.startswith((
                            "anthropic", "httpx", "httpcore", "anyio", "distro",
                            "jiter", "pydantic", "sniffio", "certifi", "idna",
                            "h11", "typing_ext", "typing_inspection",
                            "annotated_types", "docstring_parser")):
                        d = libs[0] / paquete.name
                        if paquete.is_dir():
                            shutil.copytree(paquete, d, dirs_exist_ok=True)
                        else:
                            shutil.copy2(paquete, d)

    if con_env:
        (destino / ".env").write_text(
            "ANTHROPIC_API_KEY=\n" if env_vacio
            else f"ANTHROPIC_API_KEY={CLAVE}\n", encoding="utf-8")

    # LA LISTA QUE VIAJA, TAMBIEN EN EL MUNDO DE MENTIRA. Desde que el
    # instalador pregunta al catalogo en vez de llevar tres ids escritos, un
    # equipo de prueba sin lista se cree que le faltan las dieciseis del
    # despacho y se pone a bajar el BOE en mitad de la suite. La lista es parte
    # del equipo, como el .env: si no esta, no es un equipo realista.
    import json
    (destino / "normas_del_corpus.json").write_text(json.dumps(
        {"normas": [{"id": i, "nombre": n, "titulo": n}
                    for i, n in NORMAS_CON_NOMBRE]}), encoding="utf-8")

    if con_corpus:
        (destino / "datos" / "corpus").mkdir(parents=True)
        for n in NORMAS:
            (destino / "datos" / "corpus" / f"{n}.jsonl").write_text(
                '{"prueba": true}\n', encoding="utf-8")
    return destino


def lanzar(destino: Path, entrada: str = "", entorno=None) -> tuple:
    e = entorno if entorno is not None else dict(os.environ)
    e.pop("ANTHROPIC_API_KEY", None)
    e.pop("VIRTUAL_ENV", None)
    r = subprocess.run(["/bin/bash", "abrir_agente.command"], cwd=str(destino),
                       input=entrada, capture_output=True, text=True,
                       timeout=600, env=e)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def ver(salida: str, cuantas: int = 24) -> None:
    print("    " + "-" * 66)
    for l in [x for x in salida.splitlines() if x.strip()][:cuantas]:
        print(f"    | {l[:74]}")
    print("    " + "-" * 66)


print("\n" + "=" * 72)
print("  DIEZ ESCENARIOS, CON LA SALIDA QUE VERIA UNA PERSONA")
print("=" * 72)

# --- 1 -----------------------------------------------------------------
print("\n### 1. TODO CORRECTO: abre y ya, sin instalar nada ###\n")
d = preparar("ok")
codigo, salida = lanzar(d)
ver(salida)
comprobar("sale bien", codigo == 0, f"codigo {codigo}")
comprobar("NO dice que este instalando", "PRIMER ARRANQUE" not in salida)
comprobar("la ventana se ha abierto",
          (d / "datos" / "ventana_abierta.txt").is_file())
comprobar("y no ha tardado: ni una linea de instalacion",
          "Instalando" not in salida and "bajando" not in salida)
shutil.rmtree(d, ignore_errors=True)

# --- 2 -----------------------------------------------------------------
print("\n### 2. SIN VENV: lo crea sin preguntar ###\n")
d = preparar("sinvenv", con_venv=False)
codigo, salida = lanzar(d)
ver(salida)
comprobar("sale bien", codigo == 0, f"codigo {codigo}")
comprobar("dice que esta preparando el agente", "Preparando el agente" in salida)
comprobar("crea el entorno", (d / ".venv" / "bin").is_dir())
comprobar("instala la libreria que falta", "Instalando" in salida)
comprobar("y acaba abriendo la ventana",
          (d / "datos" / "ventana_abierta.txt").is_file())
comprobar("sin pedir que se edite nada a mano",
          "edita" not in salida.lower() and "editor" not in salida.lower())
shutil.rmtree(d, ignore_errors=True)

# --- 3 -----------------------------------------------------------------
print("\n### 3. SIN .env: pide la clave por consola y la guarda ###\n")
d = preparar("sinenv", con_env=False)
codigo, salida = lanzar(d, entrada=CLAVE + "\n")
ver(salida, 28)
comprobar("sale bien", codigo == 0, f"codigo {codigo}")
comprobar("explica que es la clave y de donde se saca",
          "platform.claude.com" in salida and "API keys" in salida)
comprobar("dice que se queda en este equipo",
          "SOLO en este equipo" in salida)
comprobar("crea el .env", (d / ".env").is_file())
comprobar("con la clave dentro", CLAVE in (d / ".env").read_text("utf-8"))
comprobar("conserva las explicaciones del ejemplo",
          "platform.claude.com" in (d / ".env").read_text("utf-8"))
comprobar("comprueba que funciona ANTES de seguir", "funciona" in salida)
comprobar("y abre la ventana", (d / "datos" / "ventana_abierta.txt").is_file())
shutil.rmtree(d, ignore_errors=True)

# --- 4 -----------------------------------------------------------------
print("\n### 4. .env CREADO PERO VACIO: el estado en el que se quedaba antes ###\n")
d = preparar("envvacio", env_vacio=True)
codigo, salida = lanzar(d, entrada=CLAVE + "\n")
ver(salida, 12)
comprobar("un .env vacio NO cuenta como configurado",
          "clave de acceso" in salida.lower())
comprobar("la pide y la guarda", CLAVE in (d / ".env").read_text("utf-8"))
comprobar("sale bien", codigo == 0, f"codigo {codigo}")
shutil.rmtree(d, ignore_errors=True)

# --- 5 -----------------------------------------------------------------
print("\n### 5. CLAVE QUE NO VALE: lo dice y vuelve a pedirla ###\n")
d = preparar("clavemala", con_env=False, clave_vale=False)
codigo, salida = lanzar(d, entrada=(CLAVE + "\n") * 4)
ver(salida, 30)
comprobar("dice que la API la rechaza", "rechaza" in salida)
comprobar("y vuelve a pedirla", salida.count("Pega aqui la clave") >= 2,
          f"{salida.count('Pega aqui la clave')} veces")
comprobar("acaba parando, no en bucle infinito", codigo != 0, f"codigo {codigo}")
comprobar("dice que hacer", "platform.claude.com" in salida)
comprobar("NO abre la ventana con la clave mala",
          not (d / "datos" / "ventana_abierta.txt").is_file())
comprobar("y se descubre AQUI, no en la primera consulta",
          "Comprobando que funciona" in salida)
shutil.rmtree(d, ignore_errors=True)

# --- 6 -----------------------------------------------------------------
print("\n### 6. SIN CORPUS: lo ingiere diciendo por donde va ###\n")
d = preparar("sincorpus", con_corpus=False)
codigo, salida = lanzar(d)
ver(salida, 18)
comprobar("sale bien", codigo == 0, f"codigo {codigo}")
comprobar("avisa de que tarda", "tarda" in salida.lower())
comprobar("dice QUE esta bajando, norma por norma",
          "Ley 37/1992" in salida and "General Tributaria" in salida)
comprobar("y CUANTO lleva", "min" in salida and "desde que empezo" in salida)
comprobar("deja las tres normas",
          all((d / "datos" / "corpus" / f"{n}.jsonl").is_file() for n in NORMAS))
comprobar("y abre la ventana", (d / "datos" / "ventana_abierta.txt").is_file())
shutil.rmtree(d, ignore_errors=True)

# --- 7 -----------------------------------------------------------------
print("\n### 7. SIN LA LIBRERIA: la instala de verdad (pip real) ###\n")
d = preparar("sindep", con_dependencia=False)
codigo, salida = lanzar(d)
ver(salida, 14)
comprobar("sale bien", codigo == 0, f"codigo {codigo}")
comprobar("dice que la instala dentro del proyecto",
          "no toca nada de tu PC" in salida)
comprobar("y la libreria queda instalada de verdad",
          bool(list((d / ".venv" / "lib").glob("python*/site-packages/anthropic"))))
comprobar("y abre la ventana", (d / "datos" / "ventana_abierta.txt").is_file())
shutil.rmtree(d, ignore_errors=True)

# --- 8 -----------------------------------------------------------------
print("\n### 8. SIN PYTHON: es lo unico que necesita a una persona ###\n")
d = preparar("sinpython", con_venv=False)
vacio = d / "sinpython"
vacio.mkdir()
entorno = dict(os.environ)
entorno["PATH"] = str(vacio)       # lo mas parecido a un PC recien sacado de la caja
codigo, salida = lanzar(d, entrada="\n", entorno=entorno)
ver(salida, 16)
comprobar("para, no sigue a ciegas", codigo != 0, f"codigo {codigo}")
comprobar("dice que falta Python", "FALTA PYTHON" in salida)
comprobar("da la direccion exacta", "python.org/downloads" in salida)
comprobar("dice que es lo unico que hay que hacer a mano", "lo unico" in salida)
comprobar("y que hacer despues", "vuelve a hacer doble clic" in salida)
comprobar("sin una sola traza de python",
          "Traceback" not in salida)
shutil.rmtree(d, ignore_errors=True)

# --- 9 -----------------------------------------------------------------
print("\n### 9. CON PANTALLA: la clave se pide en VENTANA, no en la consola ###\n")
d = preparar("ventana", con_env=False, ventana=True)
codigo, salida = lanzar(d)
ver(salida, 12)
comprobar("sale bien", codigo == 0, f"codigo {codigo}")
comprobar("avisa de que se abre una ventana", "ventana" in salida.lower())
comprobar("y dice donde mirar si no la ve", "detras de esta" in salida)
comprobar("NO cae a la consola", "Pega aqui la clave" not in salida)
comprobar("la clave queda guardada", CLAVE in (d / ".env").read_text("utf-8"))
comprobar("y abre el agente", (d / "datos" / "ventana_abierta.txt").is_file())
shutil.rmtree(d, ignore_errors=True)

# --- 10 ----------------------------------------------------------------
print("\n### 10. LA PERSONA CIERRA EL DIALOGO: para y no abre ###\n")
d = preparar("cancela", con_env=False, ventana=True, clave_vale=False)
codigo, salida = lanzar(d)
ver(salida, 10)
comprobar("para, no sigue sin clave", codigo != 0, f"codigo {codigo}")
comprobar("y NO abre el agente",
          not (d / "datos" / "ventana_abierta.txt").is_file())
comprobar("dice que se puede volver luego", "vuelve a abrir el agente" in salida)
shutil.rmtree(d, ignore_errors=True)

# --- CONTROL NEGATIVO ---------------------------------------------------
print("\n### 11. LA PRUEBA SABE PONERSE ROJA ###")
print("  Se rompe el lanzador a proposito y se comprueba que el escenario 1")
print("  lo detecta. Si no, esta prueba no estaria midiendo nada.\n")
d = preparar("roto")
lanzador = d / "abrir_agente.command"
lanzador.write_text(lanzador.read_text("utf-8").replace(
    'nohup "$PY" interfaz.py "$@"', 'true # ROTO A PROPOSITO: no abre nada\n#'),
    encoding="utf-8")
codigo, salida = lanzar(d)
abrio = (d / "datos" / "ventana_abierta.txt").is_file()
print(f"    lanzador roto: ¿abrio la ventana? {abrio}")
comprobar("con el lanzador roto NO se abre (y el escenario 1 lo cazaria)",
          not abrio)
shutil.rmtree(d, ignore_errors=True)

print("\n" + "=" * 72)
print(f"FALLOS: {len(fallos)}")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
