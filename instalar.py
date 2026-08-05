#!/usr/bin/env python3
"""PRIMER ARRANQUE: DEJA EL EQUIPO LISTO. No supone nada.

Lo lanzan `abrir_agente.bat` y `abrir_agente.command` cuando falta algo. Ellos
solo saben hacer dos cosas que Python no puede hacerse a si mismo -encontrar un
Python y crear el entorno virtual-; todo lo demas esta aqui.

POR QUE AQUI Y NO EN EL .bat. Porque escribir esto dos veces, una en `cmd` y
otra en `bash`, es garantizar que dentro de un mes hagan cosas distintas y que
la que se rompa sea la de Windows, que es justo la que no puedo probar. Un solo
sitio, un solo comportamiento, y los dos lanzadores son cuatro lineas.

LAS REGLAS DE LO QUE SALE POR PANTALLA:

  · Una linea por paso, en cristiano: QUE se esta haciendo y POR QUE. Quien
    mire la pantalla tiene que entender que se esta instalando, no que se ha
    colgado.
  · Ningun error tecnico, ninguna traza, ningun codigo. Una frase de persona
    con que pasa y que hacer.
  · Nada de abrir editores ni de pedir que se toque un fichero a mano. Si hace
    falta un dato, se pide por pantalla y se guarda.

    python instalar.py            instala lo que falte
    python instalar.py --revisar  dice que falta, sin tocar nada
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ANCHO = 70

# Las cuatro normas del corpus, en los tres documentos del BOE que las
# contienen: el Real Decreto 1624/1992 trae dos articulados dentro -el suyo y
# el del Reglamento que aprueba-, y por eso son cuatro cuerpos y tres ids.
NORMAS = [
    ("BOE-A-1992-28740", "Ley 37/1992, del IVA"),
    ("BOE-A-1992-28925", "RD 1624/1992 y Reglamento del IVA"),
    ("BOE-A-2003-23186", "Ley 58/2003, General Tributaria"),
]

CORPUS = RAIZ / "datos" / "corpus"
ENV = RAIZ / ".env"
EJEMPLO = RAIZ / ".env.ejemplo"
REQUISITOS = RAIZ / "requisitos.txt"
VARIABLE = "ANTHROPIC_API_KEY"

# Cuantas veces se pide la clave antes de dejarlo estar. No es infinito a
# proposito: si alguien no la tiene a mano, mejor que salga y vuelva con ella
# que no que se quede pegado a una pantalla que le pide lo mismo sin parar.
INTENTOS_CLAVE = 3


# --------------------------------------------------------------- lo que se ve


def linea(texto: str = "") -> None:
    print(texto, flush=True)


def paso(n: int, total: int, texto: str) -> None:
    linea(f"  [{n}/{total}] {texto}")


def ok(texto: str) -> None:
    linea(f"        {texto}")


def titulo(texto: str) -> None:
    linea()
    linea("=" * ANCHO)
    linea(f"  {texto}")
    linea("=" * ANCHO)
    linea()


def parar(frase: str, que_hacer: str = "") -> int:
    """Se acaba aqui, con una frase de persona. Nunca una traza."""
    linea()
    linea("=" * ANCHO)
    linea("  NO SE HA PODIDO TERMINAR LA INSTALACION")
    linea("=" * ANCHO)
    linea()
    linea(f"  {frase}")
    if que_hacer:
        linea()
        for l in que_hacer.split("\n"):
            linea(f"  {l}")
    linea()
    linea("  Si no sabes que hacer, avisa a Emili y ensenale esta ventana.")
    linea()
    return 1


# ------------------------------------------------------------ comprobaciones


def falta_dependencia() -> bool:
    """¿Falta el SDK? Se mira importandolo, que es la unica prueba que vale."""
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return True
    return False


def falta_corpus() -> list:
    """Las normas que no estan ingeridas todavia."""
    return [(i, n) for i, n in NORMAS if not (CORPUS / f"{i}.jsonl").is_file()]


def hay_clave() -> bool:
    """¿Hay clave utilizable? Vale la del entorno o la del .env, con contenido.

    Un .env creado y VACIO no cuenta: es justo el estado en el que quedaba el
    equipo antes, y por eso el agente fallaba en la primera consulta y no en la
    instalacion.
    """
    if os.environ.get(VARIABLE, "").strip():
        return True
    if not ENV.is_file():
        return False
    for l in ENV.read_text(encoding="utf-8", errors="replace").splitlines():
        l = l.strip()
        if l.startswith("#") or "=" not in l:
            continue
        clave, valor = l.split("=", 1)
        if clave.strip() == VARIABLE and valor.strip():
            return True
    return False


def falta_tkinter() -> bool:
    try:
        import tkinter  # noqa: F401
    except Exception:  # noqa: BLE001
        return True
    return False


def que_falta() -> list:
    """La lista de lo que hay que hacer, en orden. Vacia = todo listo."""
    pendiente = []
    if falta_dependencia():
        pendiente.append("dependencias")
    if not hay_clave():
        pendiente.append("clave")
    if falta_corpus():
        pendiente.append("corpus")
    return pendiente


# ------------------------------------------------------------------- 1. pip


def instalar_dependencias() -> int:
    ok("El agente necesita una libreria para hablar con Claude. Se instala")
    ok("dentro del proyecto, no en el sistema: no toca nada de tu PC.")
    orden = [sys.executable, "-m", "pip", "install", "--quiet",
             "-r", str(REQUISITOS)]
    if not REQUISITOS.is_file():
        orden = [sys.executable, "-m", "pip", "install", "--quiet", "anthropic"]
    try:
        r = subprocess.run(orden, cwd=str(RAIZ), capture_output=True, text=True)
    except OSError:
        return parar("No se ha podido ejecutar el instalador de librerias.",
                     "Suele ser que la instalacion de Python esta incompleta.")
    if r.returncode != 0 or falta_dependencia():
        salida = (r.stderr or r.stdout or "").lower()
        if "proxy" in salida or "ssl" in salida or "certificate" in salida:
            return parar(
                "No se ha podido descargar la libreria: la red de la oficina "
                "esta bloqueando la conexion.",
                "Habla con quien lleve la red, o conecta el equipo a otra red "
                "un momento\ny vuelve a abrir el agente.")
        if "network" in salida or "resolve" in salida or "connection" in salida:
            return parar("No se ha podido descargar la libreria: no hay "
                         "conexion a internet.",
                         "Revisa la red y vuelve a abrir el agente.")
        return parar("No se ha podido instalar la libreria que necesita el "
                     "agente.",
                     "Vuelve a intentarlo con el equipo conectado a internet.")
    ok("Listo.")
    return 0


# ------------------------------------------------------------------ 2. clave


TEXTO_CLAVE = """
  El agente habla con Claude, y para eso necesita una CLAVE DE ACCESO.
  Es un texto largo que empieza por  sk-ant-  y se saca asi:

      1. entra en   https://platform.claude.com
      2. menu «API keys»
      3. «Create key», le pones un nombre y la copias

  La clave se guarda SOLO en este equipo, en un fichero que no se comparte
  ni se sube a ningun sitio. Se pega aqui una vez y no vuelve a pedirse.

  (Al pegarla no se vera nada escrito en pantalla. Es normal: pega y pulsa
  INTRO. Si no la tienes a mano, escribe  salir  y vuelve cuando la tengas.)
"""


def pedir_clave_por_pantalla() -> str:
    """La clave, tecleada o pegada. Se oculta al escribir si se puede."""
    import getpass
    import warnings

    try:
        # `getpass` avisa POR STDERR cuando no puede ocultar la escritura, y ese
        # aviso trae la ruta del fichero de Python dentro. Es exactamente lo que
        # no puede salir por pantalla: una traza en medio de la instalacion.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return getpass.getpass("  Pega aqui la clave y pulsa INTRO: ").strip()
    except Exception:  # noqa: BLE001
        # Alguna consola no deja ocultar. Antes que fallar, se pide a la vista
        # y se avisa: una clave visible un momento es mejor que un instalador
        # que se cae y deja el equipo a medias.
        linea("  (esta consola no puede ocultar lo que escribes)")
        return input("  Pega aqui la clave y pulsa INTRO: ").strip()


def guardar_clave(clave: str) -> None:
    """Escribe la clave en el .env, creandolo desde el ejemplo si hace falta.

    Se reescribe SOLO la linea de la clave: si el fichero tuviera algo mas, se
    respeta. Y se crea desde `.env.ejemplo` para que conserve las
    explicaciones, que es lo que hace que dentro de un ano se entienda.
    """
    if not ENV.is_file():
        base = (EJEMPLO.read_text(encoding="utf-8") if EJEMPLO.is_file()
                else f"{VARIABLE}=\n")
        ENV.write_text(base, encoding="utf-8")

    lineas = ENV.read_text(encoding="utf-8", errors="replace").splitlines()
    puesta = False
    for i, l in enumerate(lineas):
        if l.strip().startswith(f"{VARIABLE}="):
            lineas[i] = f"{VARIABLE}={clave}"
            puesta = True
            break
    if not puesta:
        lineas.append(f"{VARIABLE}={clave}")
    ENV.write_text("\n".join(lineas) + "\n", encoding="utf-8")

    # El .env lleva una credencial: que no lo lea todo el mundo. En Windows no
    # existe este permiso y `chmod` no hace nada, y no pasa nada por intentarlo.
    try:
        ENV.chmod(0o600)
    except OSError:
        pass


def comprobar_clave() -> tuple:
    """(vale, frase). Pregunta a la API si la clave sirve. NO gasta tokens.

    Se comprueba AQUI, en la instalacion, y no en la primera consulta: que un
    dato mal pegado se descubra tres dias despues, delante de un cliente, es
    exactamente lo que este script viene a evitar.
    """
    sys.path.insert(0, str(RAIZ))
    for modulo in [m for m in list(sys.modules) if m.startswith("agente_fiscal")]:
        del sys.modules[modulo]
    os.environ.pop(VARIABLE, None)
    try:
        from agente_fiscal import modelo as MOD
        return MOD.comprobar_credencial()
    except Exception:  # noqa: BLE001
        return False, ("No se ha podido comprobar la clave. Suele ser falta de "
                       "conexion a internet.")


def configurar_clave() -> int:
    """La clave, en VENTANA si se puede y en consola si no.

    La ventana es el camino normal, no el adorno. En Windows `getpass` habla
    con la consola por `msvcrt`, saltandose stdout: el prompt puede no verse,
    no se ve nada al escribir y Ctrl+V puede meter un caracter de control
    DENTRO de la clave. Ver `dialogo_clave`.
    """
    import dialogo_clave as D

    if D.hay_entorno_grafico():
        return _clave_en_ventana(D)
    ok("No se ha podido abrir una ventana, asi que se pide aqui.")
    return _clave_en_consola()


def _clave_en_ventana(D) -> int:
    linea("        Se abre una ventana para pedirla. Si no la ves, mira si ha")
    linea("        quedado detras de esta.")
    clave, cancelado = D.pedir_clave(comprobar_clave, guardar_clave)
    if clave:
        ok("La clave funciona. Guardada.")
        return 0
    if cancelado:
        return parar(
            "Instalacion interrumpida: hace falta la clave para terminar.",
            "Vuelve a abrir el agente cuando la tengas y seguira por aqui.\n"
            "Lo que ya se ha instalado NO se pierde.")
    return parar(
        "No se ha podido configurar la clave.",
        "Comprueba en https://platform.claude.com que la clave sigue activa\n"
        "y que la cuenta tiene saldo. Despues vuelve a abrir el agente.")


def _clave_en_consola() -> int:
    linea(TEXTO_CLAVE)
    for intento in range(1, INTENTOS_CLAVE + 1):
        clave = pedir_clave_por_pantalla()
        if clave.lower() in ("salir", "s", "exit", "q"):
            return parar(
                "Instalacion interrumpida: hace falta la clave para terminar.",
                "Vuelve a abrir el agente cuando la tengas y seguira por aqui.\n"
                "Lo que ya se ha instalado NO se pierde.")
        if not clave:
            linea("  No has escrito nada. Prueba otra vez.")
            linea()
            continue
        if not clave.startswith("sk-"):
            linea("  Eso no parece una clave: tienen que empezar por  sk-ant- ")
            linea("  Asegurate de copiarla entera, sin espacios delante.")
            linea()
            continue

        guardar_clave(clave)
        ok("Guardada. Comprobando que funciona de verdad...")
        vale, frase = comprobar_clave()
        if vale:
            ok("La clave funciona.")
            return 0

        linea()
        linea(f"  {frase}")
        if intento < INTENTOS_CLAVE:
            linea(f"  Vamos a probar otra vez ({intento} de {INTENTOS_CLAVE}).")
            linea()

    return parar(
        "La clave no ha funcionado despues de varios intentos.",
        "Comprueba en https://platform.claude.com que la clave sigue activa\n"
        "y que la cuenta tiene saldo. Despues vuelve a abrir el agente.")


# ----------------------------------------------------------------- 3. corpus


class _Resultado:
    """Lo justo de un proceso para decidir y para explicar el fallo."""

    def __init__(self, returncode: int, stderr: str):
        self.returncode = returncode
        self.stderr = stderr


# Cuantas lineas del final se guardan para poder explicar un fallo. La salida
# entera de una ingesta son miles: guardarla toda para ensenar cuatro es
# quedarse con un fichero de log que nadie va a abrir.
COLA_DIAGNOSTICO = 25


def _ingerir_con_progreso(norma_id: str) -> _Resultado:
    """Lanza fase1 ENSENANDO lo que va diciendo, no al terminar.

    Antes iba con `capture_output=True` y la pantalla se quedaba quieta los
    minutos que tarda cada norma: no se perdia nada, pero parecia colgado, que
    es justo lo que el instalador viene a evitar. Ahora se ve el avance Y se
    guarda el final por si hay que explicar un fallo.
    """
    proceso = subprocess.Popen(
        [sys.executable, "fase1.py", "ingerir", norma_id], cwd=str(RAIZ),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        bufsize=1, errors="replace")
    cola: list = []
    for l in proceso.stdout:
        l = l.rstrip()
        cola.append(l)
        del cola[:-COLA_DIAGNOSTICO]
        if l.strip():
            linea(f"          | {l[:76]}")
    proceso.wait()
    return _Resultado(proceso.returncode, "\n".join(cola))


def ingerir_corpus(pendientes: list) -> int:
    ok("El agente trabaja con el texto oficial del BOE, guardado en este")
    ok("equipo. Hay que bajarlo una vez. Tarda unos minutos.")
    linea()
    arranque = time.time()
    for n, (norma_id, nombre) in enumerate(pendientes, 1):
        linea(f"        ({n} de {len(pendientes)}) bajando {nombre}...")
        try:
            r = _ingerir_con_progreso(norma_id)
        except OSError:
            return parar("No se ha podido bajar el texto de las normas.")
        if r.returncode != 0 or not (CORPUS / f"{norma_id}.jsonl").is_file():
            salida = (r.stderr or "").lower()
            if "conexion" in salida or "network" in salida or "urlopen" in salida:
                return parar(
                    "No se ha podido bajar el texto del BOE: no hay conexion.",
                    "Revisa la red y vuelve a abrir el agente. Lo ya bajado no "
                    "se pierde.")
            return parar(
                f"No se ha podido preparar {nombre}.",
                "Vuelve a abrir el agente con el equipo conectado a internet.\n"
                "Lo que ya se haya bajado no se vuelve a bajar.")
        transcurrido = int(time.time() - arranque)
        linea(f"        listo ({transcurrido // 60} min {transcurrido % 60} s "
              f"desde que empezo)")
    ok("Corpus preparado.")
    return 0


# -------------------------------------------------------------------- flujo


def main(argv: list) -> int:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")

    if "--revisar" in argv:
        pendiente = que_falta()
        print("TODO LISTO" if not pendiente else "FALTA: " + ", ".join(pendiente))
        return 0 if not pendiente else 1

    pendiente = que_falta()
    if not pendiente:
        return 0

    titulo("PRIMER ARRANQUE: preparando el agente")
    linea("  Esto pasa UNA VEZ. Las siguientes veces se abre directamente.")
    linea("  No cierres esta ventana: cuando termine se abre el agente solo.")
    linea()

    total = len(pendiente)
    n = 0

    if "dependencias" in pendiente:
        n += 1
        paso(n, total, "Instalando lo que necesita el programa...")
        if instalar_dependencias():
            return 1

    if "clave" in pendiente:
        n += 1
        paso(n, total, "Falta la clave de acceso a Claude.")
        if configurar_clave():
            return 1

    if "corpus" in pendiente:
        n += 1
        paso(n, total, "Falta el texto de las normas.")
        if ingerir_corpus(falta_corpus()):
            return 1

    # tkinter no se instala: viene o no viene con Python. Se mira al final para
    # no dar por buena una instalacion que no va a poder abrir la ventana.
    if falta_tkinter():
        return parar(
            "El Python de este equipo no puede dibujar ventanas.",
            "Hay que reinstalar Python desde python.org marcando la casilla\n"
            "«tcl/tk and IDLE» durante la instalacion.")

    titulo("LISTO. Abriendo el agente...")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        linea()
        linea("  Instalacion interrumpida. Lo ya hecho no se pierde: vuelve a")
        linea("  abrir el agente cuando quieras y seguira por donde iba.")
        sys.exit(1)
