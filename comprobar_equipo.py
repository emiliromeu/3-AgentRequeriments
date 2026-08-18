#!/usr/bin/env python3
"""LAS COMPROBACIONES DEL EQUIPO. No lo abras a mano: doble clic en
`comprobar_equipo.bat` (Windows) o `comprobar_equipo.command` (Mac).

Aqui esta el cerebro de los dos. El .bat y el .command solo buscan un Python y
llaman a este fichero. Se hace asi a proposito: meter Python dentro de un .bat
obliga a escapar %, comillas y parentesis, y ahi es donde se cuelan los fallos
que solo aparecen en Windows y que no puedo probar desde un Mac. Escrito una
sola vez, se prueba una sola vez.

NO GASTA NI UNA LLAMADA A LA API. La credencial se mira, no se usa.

Reglas de esta pantalla, que la lee alguien de pie en una oficina:

  · Se para en el PRIMER fallo. Lo que va despues normalmente falla por lo
    mismo, y tres fallos a la vez no se saben leer.
  · Cada fallo es UNA frase de que pasa y UNA de como se arregla. Ni trazas,
    ni codigos, ni nombres de excepcion.
  · Todo en ASCII, sin tildes. La consola de Windows no siempre sabe escribir
    una 'o' con tilde, y un acento mal puesto revienta la linea entera.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

# La consola de Windows suele ir en cp850, no en UTF-8. Si algo se cuela con un
# acento (una ruta, el nombre de una norma), que salga raro pero que NO reviente
# el diagnostico entero.
for flujo in (sys.stdout, sys.stderr):
    try:
        flujo.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass

ANCHO = 70
PASOS = 6

# Version minima. Por debajo no merece la pena afinar el mensaje: se instala una
# actual y ya esta.
PY_MINIMO = (3, 10)


def barra(titulo: str = "") -> None:
    print("=" * ANCHO)
    if titulo:
        print(f"  {titulo}")
        print("=" * ANCHO)


def paso(n: int, nombre: str, detalle: str = "") -> None:
    """Una linea de OK. El detalle es lo que confirma que se ha mirado."""
    puntos = "." * max(2, 30 - len(nombre))
    print(f"  [{n}/{PASOS}] {nombre} {puntos} OK   {detalle}".rstrip())


class Falta(Exception):
    """Un fallo contado como se cuenta a una persona: que pasa y que hacer."""

    def __init__(self, n: int, nombre: str, que_pasa: str, solucion: str):
        self.n = n
        self.nombre = nombre
        self.que_pasa = que_pasa
        self.solucion = solucion
        super().__init__(que_pasa)


def envolver(texto: str, sangria: str = "  ") -> str:
    """Parte en lineas a mano. `textwrap` vale, pero esto deja el control del
    ancho aqui, que es lo unico que importa para que se lea de un vistazo."""
    palabras, lineas, actual = texto.split(), [], sangria
    for p in palabras:
        if len(actual) + len(p) + 1 > ANCHO - 2 and actual.strip():
            lineas.append(actual.rstrip())
            actual = sangria + p + " "
        else:
            actual += p + " "
    if actual.strip():
        lineas.append(actual.rstrip())
    return "\n".join(lineas)


# --------------------------------------------------------------- los 6 pasos


def paso_1_python() -> str:
    v = sys.version_info
    if (v.major, v.minor) < PY_MINIMO:
        raise Falta(
            1, "Python",
            f"Este equipo tiene Python {v.major}.{v.minor}, que es demasiado "
            f"antiguo para el agente.",
            f"Instala Python {PY_MINIMO[0]}.{PY_MINIMO[1]} o mas nuevo desde "
            f"python.org y marca la casilla 'Add Python to PATH' durante la "
            f"instalacion.",
        )
    return f"Python {v.major}.{v.minor}.{v.micro}"


def paso_2_tkinter() -> str:
    try:
        import tkinter
    except ImportError:
        raise Falta(
            2, "tkinter",
            "Este Python no puede dibujar ventanas: le falta tkinter, que es "
            "la pieza que pinta la pantalla del agente.",
            "En Windows: vuelve a instalar Python desde python.org y marca la "
            "casilla 'tcl/tk and IDLE'. En Mac: abre la Terminal y ejecuta "
            "brew install python-tk@3.14",
        )
    return f"Tk {tkinter.TkVersion}"


def paso_3_venv() -> str:
    carpeta = RAIZ / ".venv"
    if not carpeta.is_dir():
        raise Falta(
            3, "Entorno .venv",
            "Falta la carpeta .venv, que es donde vive la instalacion del "
            "agente.",
            "Avisa a Emili: hay que crear el entorno en este equipo. No es "
            "algo que se arregle desde aqui.",
        )

    # Estar DENTRO del entorno es lo que de verdad importa: si el .bat ha
    # arrancado con el Python del sistema, el agente no encontrara sus piezas.
    dentro = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if not dentro:
        raise Falta(
            3, "Entorno .venv",
            "La carpeta .venv existe, pero este equipo no la esta usando: el "
            "agente se estaria abriendo con el Python equivocado.",
            "Avisa a Emili: el entorno esta a medias y hay que rehacerlo.",
        )

    try:
        import anthropic  # noqa: F401
    except ImportError:
        raise Falta(
            3, "Entorno .venv",
            "El entorno existe pero esta incompleto: le falta la pieza que "
            "habla con el servicio.",
            "Avisa a Emili: hay que reinstalar las dependencias del agente.",
        )
    return "instalado y en uso"


def paso_4_credencial() -> str:
    fichero = RAIZ / ".env"
    if not fichero.is_file():
        raise Falta(
            4, "Credencial",
            "No hay fichero .env en la carpeta del agente, que es donde va la "
            "credencial del servicio.",
            "Avisa a Emili y pidele el fichero .env para este equipo. NO lo "
            "copies por correo ni por chat.",
        )

    # Se lee para ver SI hay clave y si tiene pinta de clave. No se imprime, ni
    # entera ni en trozos, ni su longitud: nada que ayude a reconstruirla.
    clave = ""
    try:
        for linea in fichero.read_text(encoding="utf-8", errors="replace").splitlines():
            linea = linea.strip()
            if linea.startswith("#") or "=" not in linea:
                continue
            nombre, _, valor = linea.partition("=")
            if nombre.strip() in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
                clave = valor.strip().strip("'\"")
    except OSError:
        raise Falta(
            4, "Credencial",
            "Existe el fichero .env pero este equipo no puede leerlo.",
            "Avisa a Emili: es un problema de permisos del fichero.",
        )

    if not clave:
        raise Falta(
            4, "Credencial",
            "El fichero .env existe pero no tiene ninguna credencial dentro.",
            "Avisa a Emili y pidele el fichero .env correcto para este equipo.",
        )
    if not clave.startswith("sk-ant-") or len(clave) < 40:
        raise Falta(
            4, "Credencial",
            "El fichero .env tiene una credencial, pero no tiene la forma que "
            "deberia: parece cortada o mal pegada.",
            "Avisa a Emili y pidele el fichero .env de nuevo, sin abrirlo ni "
            "editarlo por el camino.",
        )
    # Ni la clave ni un trozo ni su longitud. Solo que esta.
    return "presente en .env"


def paso_5_corpus() -> str:
    carpeta = RAIZ / "datos" / "corpus"
    if not carpeta.is_dir() or not any(carpeta.glob("*.jsonl")):
        raise Falta(
            5, "Corpus de leyes",
            "Este equipo no tiene la copia de la ley y el reglamento, que es "
            "de donde el agente saca las respuestas.",
            "Avisa a Emili: hay que traer la copia de las normas a este "
            "equipo.",
        )
    try:
        sys.path.insert(0, str(RAIZ))
        import fase4
        ix, _grafo = fase4.cargar_corpus()
    except Exception:
        raise Falta(
            5, "Corpus de leyes",
            "La copia de la ley esta en el equipo pero el agente no consigue "
            "leerla: puede haberse copiado a medias.",
            "Avisa a Emili: hay que volver a traer la copia de las normas.",
        )
    if not ix.docs:
        raise Falta(
            5, "Corpus de leyes",
            "La copia de la ley esta vacia: no tiene ni un articulo dentro.",
            "Avisa a Emili: hay que volver a traer la copia de las normas.",
        )
    nombres = ", ".join(c.etiqueta for c in ix.normas.cuerpos.values())
    # Los nombres van en su propia linea: son lo que deja ver de un vistazo si
    # el equipo tiene lo que toca, o una copia vieja a la que le falta algo.
    return (f"{len(ix.normas)} norma(s), {len(ix.docs)} preceptos", nombres)


def paso_6_ventana() -> str:
    """Abre la ventana de verdad, en modo prueba, y la cierra sola.

    Es la unica comprobacion que prueba el conjunto: si esto sale, el agente
    abre. Va en modo ensayo, asi que no llama al servicio ni gasta nada.
    """
    import tkinter as tk

    sys.path.insert(0, str(RAIZ))
    try:
        import interfaz
    except Exception:
        raise Falta(
            6, "La ventana",
            "El programa de la ventana no arranca en este equipo.",
            "Avisa a Emili y dile que ha fallado la ultima comprobacion, la "
            "de la ventana.",
        )

    try:
        raiz = tk.Tk()
    except Exception:
        raise Falta(
            6, "La ventana",
            "No se puede abrir ninguna ventana en esta sesion de Windows.",
            "Comprueba que has entrado en el equipo con tu usuario normal, no "
            "por escritorio remoto ni como servicio. Si sigue igual, avisa a "
            "Emili.",
        )

    try:
        raiz.title("Comprobacion del equipo")
        # Se aparta de la vista: es una prueba, no algo que haya que tocar.
        raiz.geometry("520x360+40+40")
        ventana = interfaz.Ventana(raiz, "ensayo")

        # Se cierra sola pase lo que pase. El tope es el seguro: si el motor
        # se quedara colgado, esto NO deja el diagnostico parado para siempre.
        estado = {"lista": False}

        def mirar(restan: int) -> None:
            if ventana.motor is not None:
                estado["lista"] = True
                raiz.destroy()
            elif restan <= 0:
                raiz.destroy()
            else:
                raiz.after(200, mirar, restan - 1)

        raiz.after(200, mirar, 150)   # 30 segundos de tope
        raiz.mainloop()
    except Exception:
        try:
            raiz.destroy()
        except Exception:
            pass
        raise Falta(
            6, "La ventana",
            "La ventana del agente se ha abierto pero ha fallado nada mas "
            "empezar.",
            "Avisa a Emili y dile que ha fallado la ultima comprobacion, la "
            "de la ventana.",
        )

    if not estado["lista"]:
        raise Falta(
            6, "La ventana",
            "La ventana se abre pero se queda cargando sin terminar.",
            "Avisa a Emili y dile que ha fallado la ultima comprobacion, la "
            "de la ventana.",
        )
    return "abre y cierra bien"


# ------------------------------------------------------------------- main


COMPROBACIONES = [
    ("Python", paso_1_python),
    ("tkinter", paso_2_tkinter),
    ("Entorno .venv", paso_3_venv),
    ("Credencial", paso_4_credencial),
    ("Corpus de leyes", paso_5_corpus),
    ("La ventana", paso_6_ventana),
]


def ficha() -> None:
    """LA FICHA DEL EQUIPO, DE UN VISTAZO Y PARA COPIAR ENTERA.

    Se imprime SIEMPRE, salga bien o mal la comprobacion, y ANTES de los
    pasos: si algo revienta a la mitad, la ficha ya esta escrita.

    Es lo que hay que poder pegar en un mensaje cuando alguien dice «los
    botones salen en gris». Sin esto, la conversacion son cuatro idas y
    vueltas preguntando en que commit esta el equipo.

    Todo en ASCII y sin salir a la red: la credencial se MIRA, no se usa.
    """
    import subprocess

    barra("FICHA DE ESTE EQUIPO")
    print()

    # --- en que version esta el equipo
    #
    # LO LEE `agente_fiscal.version`, QUE ES EL MISMO QUE ESCRIBE LA TRAZA. Aqui
    # estaba escrito a mano, y entonces la ficha y los expedientes podian decir
    # cosas distintas del mismo equipo: dos lecturas del mismo dato es como se
    # acaba discutiendo cual de las dos vale.
    commit = "(no es un repositorio git)"
    sucio = ""
    try:
        sys.path.insert(0, str(RAIZ))
        from agente_fiscal import version as _V
        v = _V.actual()
        if v.get("commit") != _V.DESCONOCIDA:
            commit = f"{v['commit']} {v.get('fecha', '')[:10]} {v.get('asunto', '')}"[:70]
        if v.get("sucio"):
            sucio = (f"  <-- {v['sucio']} fichero(s) sin guardar: el pull pudo "
                     f"quedarse a medias")
    except Exception:                            # noqa: BLE001
        pass
    print(f"  version   : {commit}{sucio}")

    # --- normas y sellos
    normas = sellos = "?"
    try:
        sys.path.insert(0, str(RAIZ))
        import json
        f = RAIZ / "datos" / "corpus" / "sellos.json"
        if f.is_file():
            normas = str(len({k.split("#")[0] for k in
                              json.loads(f.read_text(encoding="utf-8"))}))
        else:
            normas = "0 (no hay sellos.json)"
        import instalar
        problemas = instalar.corpus_no_cuadra()
        sellos = "cuadran" if not problemas else f"NO CUADRAN ({len(problemas)})"
    except Exception as e:                       # noqa: BLE001
        sellos = f"no se han podido mirar ({type(e).__name__})"
    print(f"  normas    : {normas}")
    print(f"  sellos    : {sellos}")

    # --- credencial: se mira, no se usa
    # SE PREGUNTA AL PASO 4, NO SE VUELVE A ESCRIBIR. La primera version de
    # esta linea llevaba su propia lectura del .env -partir por «=» y mirar que
    # empezara por «sk-»- y decia que la credencial no valia mientras el paso 4
    # decia que si: no toleraba las comillas que el paso 4 si quita. Dos
    # lecturas del mismo fichero que se contradicen en la misma pantalla es
    # peor que no tener ninguna.
    try:
        cred = "correcta " + paso_4_credencial()
    except Falta as f:
        cred = "NO VALE - " + f.que_pasa
    except Exception as e:                       # noqa: BLE001
        cred = f"no se ha podido mirar ({type(e).__name__})"
    print(f"  credencial: {cred}")
    print("              (se mira, NO se usa: esta ficha no gasta nada)")

    # --- POR QUE ESTA EL BOTON APAGADO, que es la pregunta de verdad
    motivo = "no se ha podido saber"
    try:
        import instalar
        pendiente = instalar.que_falta()
        if pendiente:
            motivo = "falta " + ", ".join(pendiente) + " (lo dice el instalador)"
        else:
            import fase4
            _motor, err = fase4.preparar_motor("anthropic", silencioso=True)
            motivo = ("el motor arranca: el boton NO deberia estar apagado"
                      if _motor is not None else f"el motor no arranca: {err}")
    except Exception as e:                       # noqa: BLE001
        motivo = f"{type(e).__name__}: {e}"
    print()
    print("  POR QUE EL BOTON PODRIA ESTAR APAGADO:")
    for linea in envolver(str(motivo)[:400], sangria="    ").splitlines():
        print(linea)

    # --- y el ultimo arranque fallido, si lo hubo
    fallo = RAIZ / "datos" / "arranque_fallido.txt"
    if fallo.is_file():
        # DE CUANDO ES, Y SI ES DE HOY. Este fichero no se borra al arrancar
        # bien -el de ayer puede hacer falta-, asi que sin la edad un fallo ya
        # arreglado se lee igual que el de esta mañana y manda a perseguir algo
        # que no existe.
        from datetime import datetime
        edad = (datetime.now()
                - datetime.fromtimestamp(fallo.stat().st_mtime))
        dias = edad.days
        if dias == 0:
            cuando = "DE HOY"
        elif dias == 1:
            cuando = "de ayer"
        else:
            cuando = f"de hace {dias} dias  <-- puede no ser el fallo de ahora"
        print()
        print(f"  ULTIMO ARRANQUE QUE FALLO, {cuando}:")
        for linea in fallo.read_text(encoding="utf-8",
                                     errors="replace").splitlines()[-12:]:
            print("    " + linea[:110])
    print()


def main() -> int:
    print()
    ficha()
    barra("COMPROBACION DEL EQUIPO")
    print()
    print(envolver("Se mira que este todo lo que el agente necesita para "
                   "funcionar. No se consulta nada y no cuesta nada."))
    print()

    for n, (nombre, comprobacion) in enumerate(COMPROBACIONES, start=1):
        try:
            detalle = comprobacion()
        except Falta as f:
            print()
            puntos = "." * max(2, 30 - len(f.nombre))
            print(f"  [{f.n}/{PASOS}] {f.nombre} {puntos} FALTA")
            print()
            print(envolver(f.que_pasa, sangria="    "))
            print()
            print("    QUE HAY QUE HACER:")
            print(envolver(f.solucion, sangria="    "))
            print()
            barra()
            print("  EL EQUIPO NO ESTA LISTO")
            print()
            print(f"    Falta esto: {f.nombre.lower()}")
            pendientes = [x for x, _ in COMPROBACIONES[f.n:]]
            if pendientes:
                print(envolver("Y no se ha llegado a comprobar: "
                               + ", ".join(p.lower() for p in pendientes)
                               + ". Se miran cuando lo de arriba este "
                                 "resuelto.", sangria="    "))
            print()
            barra()
            return 1
        except Exception:
            # Red de seguridad: ni un fallo imprevisto puede sacar una traza a
            # esta pantalla. Se cuenta como lo que es, sin adornos.
            print()
            print(f"  [{n}/{PASOS}] {nombre} ... FALLO INESPERADO")
            print()
            print(envolver("Algo ha fallado al hacer esta comprobacion y no "
                           "se ha podido averiguar que.", sangria="    "))
            print()
            print("    QUE HAY QUE HACER:")
            print(envolver(f"Avisa a Emili y dile que la comprobacion "
                           f"'{nombre.lower()}' falla en este equipo.",
                           sangria="    "))
            print()
            barra()
            print("  EL EQUIPO NO ESTA LISTO")
            print()
            barra()
            return 1
        else:
            # Una comprobacion puede devolver solo su resumen, o el resumen y
            # una linea extra debajo (el corpus enseña que normas hay).
            extra = ""
            if isinstance(detalle, tuple):
                detalle, extra = detalle
            paso(n, nombre, detalle)
            if extra:
                print(envolver(extra, sangria="          "))

    print()
    barra()
    print("  TODO LISTO")
    print()
    print(envolver("Este equipo puede usar el agente. Para abrirlo, doble clic "
                   "en abrir_agente.", sangria="    "))
    print()
    barra()
    return 0


if __name__ == "__main__":
    sys.exit(main())
