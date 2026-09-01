#!/usr/bin/env python3
"""LAS SUITES MIDEN COMPORTAMIENTO, NO PROSA. Cero red, cero API.

    python pruebas/prueba_suites.py

Esta suite no protege el agente: protege a las suites. Existe porque el mismo
error ha aparecido TRES veces, y las tres se descubrieron por casualidad —al
romper el codigo a proposito y ver que la comprobacion seguia en verde—.

    1. `prueba_version` buscaba la palabra «rev-parse» para saber si alguien
       leia el commit a mano. `reparar.py` la usaba para preguntar la RAMA, asi
       que la suite llevaba dias en rojo por algo que no era el fallo. Y no
       cazaba la forma que de verdad usamos -`git log --format=%h`- porque esa
       no lleva la palabra.

    2. `prueba_otraforma` comprobaba que no hubiera un menu de tres opciones
       buscando «resumelo» en el fuente. La palabra estaba EN EL COMENTARIO que
       explica por que NO se hicieron tres opciones: la prueba fallaba por su
       propia explicacion.

    3. `prueba_instalador` -al escribir la comprobacion que impide que el tope
       vuelva a crecer- salio roja por un «600» que estaba en el comentario que
       explicaba el arreglo. Tenia razon en el fondo y leia mal.

────────────────────────────────────────────────────────────────────────────
LA REGLA: SE PREGUNTA AL ARBOL DE SINTAXIS O SE EJECUTA EL CAMINO.
NO SE BUSCA TEXTO.
────────────────────────────────────────────────────────────────────────────

Buscar una palabra en un fichero mide la PROSA, no el comportamiento. Y falla
en las dos direcciones, que es lo que lo hace tan malo:

    FALSO POSITIVO ... la palabra esta en un comentario, en una docstring o en
                       el propio razonamiento de por que algo no se hace. La
                       suite se pone roja sin que nada este mal, y una roja
                       que se sabe falsa es una que dentro de un mes nadie
                       mira — con ella pasa la roja de verdad.
    FALSO NEGATIVO ... el comportamiento existe escrito de otra forma. La
                       suite se queda en verde sobre un fallo vivo, que es
                       exactamente lo que paso las tres veces.

QUE HACER EN SU LUGAR:

    · ejecutar el camino y mirar el resultado —siempre que se pueda—;
    · preguntar al arbol de sintaxis con `ast`: que argumentos lleva una
      llamada, que se le pasa a que funcion;
    · y si no queda otra que leer el fuente, QUITAR ANTES LOS COMENTARIOS.
      Es lo minimo, y convierte un falso positivo en imposible.

────────────────────────────────────────────────────────────────────────────
POR QUE HAY UNA LINEA BASE Y NO SE EXIGE CERO
────────────────────────────────────────────────────────────────────────────

Medido al escribir esto: hay CUARENTA comprobaciones asi en catorce suites.
Exigir cero pondria esta suite en rojo el primer dia, y una suite roja de
salida no se arregla: se ignora.

Es el mismo criterio que el banco de recuperacion, y por el mismo motivo: no
se juzga por «cero», se juzga por que sean LAS MISMAS. Lo que esta suite
impide es que APAREZCAN NUEVAS. Las cuarenta viejas se iran arreglando cuando
se toque cada suite por otra cosa.

LA LINEA BASE SE GENERA, NO SE ESCRIBE A MANO:

    .venv/bin/python pruebas/prueba_suites.py --guardar

y se commitea. Cambiarla es una decision que queda en el diff.
"""
import ast
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

# Donde vive la lista de las que ya estaban. Al lado de las demas lineas base.
BASE = RAIZ / "casos" / "suites_que_leen_prosa.txt"

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:104]}" if not ok else ""))
    if not ok:
        fallos.append(que)


# ────────────────────────────────────────────────────────────────────────
# EL DETECTOR
# ────────────────────────────────────────────────────────────────────────
#
# SE PREGUNTA AL ARBOL, que es justo lo que esta suite predica: buscar
# `read_text` con un `grep` daria los mismos falsos positivos que esta suite
# existe para cazar.
#
# Lo que se busca es el patron completo, no una pieza:
#
#     X = algo.read_text(...)        <- se lee un fichero de CODIGO
#     comprobar("...", "lit" in X)   <- y se busca texto dentro
#
# Y no cuenta si X viene de haber quitado los comentarios: eso es la salida
# correcta cuando no hay otra.

FICHEROS_DE_CODIGO = (".py", ".js")


def _es_de_codigo(nodo) -> bool:
    """¿La lectura apunta a un fichero de codigo?

    Se mira el volcado del arbol porque la ruta se compone de mil maneras
    -`RAIZ / "x.py"`, `Path(__file__)`, una variable-. Lo que importa es que
    en algun sitio de esa expresion aparezca una extension de codigo.
    """
    volcado = ast.dump(nodo)
    return any(e in volcado for e in FICHEROS_DE_CODIGO)


def _limpia_comentarios(nodo) -> bool:
    """¿Esta expresion quita los comentarios antes de buscar?"""
    volcado = ast.dump(nodo)
    return ("startswith" in volcado
            and any(m in volcado for m in ("'#'", '"#"', "'//'", '"//"')))


def leen_prosa(ruta: Path) -> list:
    """[(etiqueta, variable)] de las comprobaciones que buscan texto en codigo.

    SE IDENTIFICA POR LA ETIQUETA, NO POR EL NUMERO DE LINEA. Arreglado el
    01/09/2026, y el fallo lo cazo esta misma suite el dia que nacio: la linea
    base guardaba `fichero:linea`, y en cuanto una edicion desplazo el fichero
    aparecieron «nuevas» comprobaciones que eran las de siempre movidas.

    Es una version del mismo error que esta suite existe para cazar: medir una
    coordenada VOLATIL -donde esta escrito- en vez de la identidad de lo que se
    comprueba. La etiqueta es lo que identifica una comprobacion: si alguien la
    reescribe, es otra comprobacion y tiene que verse.
    """
    try:
        arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return []
    crudas, limpias = set(), set()
    for n in ast.walk(arbol):
        if not isinstance(n, ast.Assign) or len(n.targets) != 1:
            continue
        destino = n.targets[0]
        if not isinstance(destino, ast.Name):
            continue
        valor = n.value
        if (isinstance(valor, ast.Call)
                and isinstance(valor.func, ast.Attribute)
                and valor.func.attr in ("read_text", "read")
                and _es_de_codigo(valor)):
            crudas.add(destino.id)
        elif _limpia_comentarios(valor):
            limpias.add(destino.id)

    fuera, vistos = [], set()
    for n in ast.walk(arbol):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "comprobar"):
            continue
        # LA ETIQUETA, que es el primer argumento y lo que la identifica. Si no
        # es una constante -se compone con un f-string- se usa la linea, que es
        # lo unico que queda; son pocas y se anota como tal.
        if n.args and isinstance(n.args[0], ast.Constant):
            # `.strip()` DESPUES DE CORTAR, y no es un detalle de estilo:
            # el corte a 70 puede caer en un espacio, y al guardar y releer la
            # linea base ese espacio se pierde —el lector hace `strip()`—.
            # Resultado: la entrada no casaba consigo misma y salia como
            # «nueva» en cada pasada. Una linea base que no se reconoce es
            # peor que no tenerla.
            etiqueta = " ".join(str(n.args[0].value).split())[:70].strip()
        else:
            etiqueta = f"(compuesta, linea {n.lineno})"
        for sub in ast.walk(n):
            if not isinstance(sub, ast.Compare):
                continue
            if not any(isinstance(o, (ast.In, ast.NotIn)) for o in sub.ops):
                continue
            for c in sub.comparators:
                if (isinstance(c, ast.Name) and c.id in crudas
                        and c.id not in limpias
                        and (etiqueta, c.id) not in vistos):
                    vistos.add((etiqueta, c.id))
                    fuera.append((etiqueta, c.id))
    return fuera


def censo() -> set:
    """{«fichero:linea»} de todo lo que hay hoy."""
    fuera = set()
    for f in sorted((RAIZ / "pruebas").glob("prueba_*.py")):
        if f.name == Path(__file__).name:
            continue
        for etiqueta, _var in leen_prosa(f):
            fuera.add(f"{f.name}  ·  {etiqueta}")
    return fuera


def guardadas() -> set:
    if not BASE.is_file():
        return set()
    return {l.strip() for l in BASE.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")}


if "--guardar" in sys.argv:
    hoy = sorted(censo())
    BASE.parent.mkdir(parents=True, exist_ok=True)
    BASE.write_text(
        "# COMPROBACIONES QUE BUSCAN TEXTO EN UN FUENTE, Y QUE YA ESTABAN.\n"
        "# Generado por `prueba_suites.py --guardar`. NO se escribe a mano.\n"
        "# Lo que vigila la suite es que NO APAREZCAN NUEVAS; estas se iran\n"
        "# arreglando cuando se toque cada una por otra cosa. Ver la cabecera\n"
        "# de `prueba_suites.py` para por que hay linea base y no se exige 0.\n"
        + "\n".join(hoy) + "\n", encoding="utf-8")
    print(f"guardadas {len(hoy)} en {BASE.relative_to(RAIZ)}")
    sys.exit(0)


print("\n=== LAS SUITES MIDEN COMPORTAMIENTO, NO PROSA ===")
print("  Tres veces el mismo error: «rev-parse», el «600» de un comentario y")
print("  el «resumelo» que vivia en la explicacion de por que NO se hizo.\n")

hoy = censo()
antes = guardadas()
nuevas = sorted(hoy - antes)
arregladas = sorted(antes - hoy)

print(f"    conocidas: {len(antes)}  ·  ahora: {len(hoy)}")
if arregladas:
    print(f"    se han arreglado {len(arregladas)} (enhorabuena, y actualiza "
          f"la linea base con --guardar):")
    for a in arregladas[:8]:
        print(f"      - {a}")
print()

comprobar("no aparece NINGUNA comprobacion nueva que busque texto en un fuente",
          not nuevas, nuevas)
comprobar("hay linea base guardada, y no vacia", bool(antes), len(antes))

# LA LINEA BASE TIENE QUE RECONOCERSE A SI MISMA. Suena a perogrullada y no lo
# es: la primera version identificaba por `fichero:linea`, y cualquier edicion
# que desplazara el fichero convertia en «nuevas» a las de siempre. La segunda
# truncaba la etiqueta a 70 y podia dejar un espacio final que el fichero
# perdia al releerse. Las dos veces la suite se ponia roja sola.
#
# Es el mismo error que esta suite caza, en otra forma: medir una coordenada
# volatil —donde esta escrito, como quedo cortado— en vez de la identidad.
# LO QUE SE COMPRUEBA ES QUE NO SOBRE NI FALTE NADA EN LOS BORDES, que es lo
# que el lector quita con `strip()`. El separador lleva dos espacios A
# PROPOSITO -«fichero  ·  etiqueta»- y normalizarlos aqui daria roja en todas:
# me paso al escribir esto, y es la misma leccion otra vez —comprobar de mas
# es tan malo como comprobar de menos—.
# SE MIRA EL CENSO, NO LA LINEA BASE. Al escribirlo mire `antes` —lo leido del
# fichero— que YA viene con `strip()` puesto por el lector: la comprobacion no
# podia fallar nunca. Lo que hay que vigilar es lo que se GENERA, que es donde
# nace el espacio de sobra.
comprobar("y lo que se genera sobrevive a guardarlo y releerlo",
          all(e == e.strip() for e in hoy),
          [e for e in hoy if e != e.strip()][:2])

# ────────────────────────────────────────────────────────────────────────
# CONTROL NEGATIVO: ¿el detector sabe decir que si?
# ────────────────────────────────────────────────────────────────────────
print("\n=== CONTROL NEGATIVO: ¿EL DETECTOR MIDE ALGO? ===")
import tempfile  # noqa: E402

MALA = '''
from pathlib import Path
FUENTE = (Path("x") / "interfaz.py").read_text("utf-8")
def comprobar(q, ok, o=""): pass
comprobar("no queda la palabra fea", "resumelo" not in FUENTE)
'''
BUENA_EJECUTA = '''
import interfaz
def comprobar(q, ok, o=""): pass
comprobar("el boton se apaga", interfaz.algo() is False)
'''
BUENA_LIMPIA = '''
from pathlib import Path
FUENTE = (Path("x") / "interfaz.py").read_text("utf-8")
sin_comentarios = "\\n".join(l for l in FUENTE.splitlines()
                            if not l.lstrip().startswith("#"))
def comprobar(q, ok, o=""): pass
comprobar("no queda la palabra fea", "resumelo" not in sin_comentarios)
'''
BUENA_NO_CODIGO = '''
from pathlib import Path
BAT = (Path("x") / "abrir.bat").read_text("utf-8")
def comprobar(q, ok, o=""): pass
comprobar("el bat acaba en pause", "pause" in BAT)
'''
with tempfile.TemporaryDirectory() as d:
    for nombre, codigo, esperado in (
            ("mala", MALA, True),
            ("que ejecuta el camino", BUENA_EJECUTA, False),
            ("que quita los comentarios antes", BUENA_LIMPIA, False),
            ("que lee un .bat, sin comentarios de codigo", BUENA_NO_CODIGO, False)):
        f = Path(d) / "prueba_x.py"
        f.write_text(codigo, encoding="utf-8")
        pillada = bool(leen_prosa(f))
        comprobar(f"{'caza' if esperado else 'deja pasar'} la «{nombre}»",
                  pillada == esperado, f"detectada={pillada}")

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
