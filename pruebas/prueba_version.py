#!/usr/bin/env python3
"""CADA EXPEDIENTE DICE CON QUE VERSION DEL CODIGO SE GENERO. Cero red, cero API.

    python pruebas/prueba_version.py

POR QUE, con el caso entero: tres consultas fallaban con el mismo motivo -«la
cita no dice de que norma es»- y las tres volvian a fallar en el reintento.
Parecia un defecto vivo y daba pie a rehacer media rama del sistema. No lo era:
las tres son de la noche del 5 de agosto ANTES de las 23:19, y a esa hora entro
el arreglo que las causaba. Se descubrio comparando a mano la hora de las
carpetas con `git log`.

Es la tercera vez que medir sobre un historico mientras el codigo cambia
describe un sistema que ya no existe.

LO QUE ESTA SUITE VIGILA:

  1. Que la version se escriba, y AL CREAR el expediente, no al cerrarlo: una
     consulta que revienta a la mitad tambien tiene que decir de que version es.
  2. Que NO PUEDA TUMBAR UNA CONSULTA. Sin git, con git lento o con el
     repositorio a medias, se apunta «desconocida» y se sigue. Un expediente sin
     version es malo; un expediente que no existe porque git tardo es peor.
  3. Que los viejos -que no la llevan- se cuenten APARTE y no se supongan de la
     version de hoy, que es exactamente el error que esto viene a impedir.
  4. Que haya UNA implementacion, no una por guion.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from agente_fiscal import version as VER         # noqa: E402
from agente_fiscal.traza import Traza            # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:110]}" if not ok else ""))
    if not ok:
        fallos.append(que)


# ==================================== 1. SE ESCRIBE, Y AL CREAR
print("\n=== 1. LA VERSION SE ESCRIBE AL CREAR EL EXPEDIENTE ===")
print("  Al crear y no al cerrar: una consulta que revienta a la mitad")
print("  tambien tiene que poder decir de que version es. Si no, la unica")
print("  que falta es justo la de la consulta que reviento.\n")

corral = Path(tempfile.mkdtemp())
try:
    tr = Traza(corral, "una duda cualquiera")
    f = tr.dir / "version.json"
    comprobar("existe version.json nada mas crear la traza", f.is_file(),
              sorted(x.name for x in tr.dir.iterdir()))
    d = json.loads(f.read_text("utf-8"))
    comprobar("  y lleva el commit", bool(d.get("commit")), d)
    comprobar("  y la fecha, para poder ordenar sin volver a preguntar a git",
              bool(d.get("fecha")), d)
    comprobar("  y CUANTOS FICHEROS HABIA SIN GUARDAR",
              "sucio" in d,
              "sin esto, una traza hecha con cambios locales encima dice ser "
              "de un commit que no contiene lo que corrio")
    comprobar("se lee de vuelta con la misma pieza que lo escribio",
              VER.de_expediente(tr.dir).get("commit") == d.get("commit"))
finally:
    shutil.rmtree(corral, ignore_errors=True)


# ==================================== 2. NUNCA TUMBA UNA CONSULTA
print("\n=== 2. SI GIT NO CONTESTA, LA CONSULTA SIGUE ===")
print("  Un expediente sin version es malo. Un expediente que NO EXISTE")
print("  porque git tardo veinte segundos es mucho peor.\n")

corral = Path(tempfile.mkdtemp())
guardado = VER._git
try:
    def revienta(*a, **k):
        raise OSError("git no esta instalado en este equipo")
    VER._git = revienta
    VER.actual(recargar=True)
    v = VER.actual(recargar=True)
    comprobar("sin git, `actual` devuelve «desconocida» y no lanza",
              v.get("commit") == VER.DESCONOCIDA, v)
    tr = Traza(corral, "otra duda")
    comprobar("  y la traza se crea igual, con su pregunta dentro",
              (tr.dir / "pregunta.txt").read_text("utf-8") == "otra duda")
finally:
    VER._git = guardado
    VER.actual(recargar=True)
    shutil.rmtree(corral, ignore_errors=True)


# ==================================== 3. LOS VIEJOS, APARTE
print("\n=== 3. LOS EXPEDIENTES VIEJOS NO SE SUPONEN ===")
print("  No lo llevan, y no pasa nada: cuentan como «desconocida». Suponer")
print("  que son de la version de hoy es el error que esto viene a impedir.\n")

corral = Path(tempfile.mkdtemp())
try:
    viejo = corral / "20260802T120000"
    viejo.mkdir()
    (viejo / "pregunta.txt").write_text("de antes", encoding="utf-8")
    nuevo = Traza(corral, "de ahora")
    comprobar("un expediente sin version.json sale «desconocida»",
              VER.de_expediente(viejo).get("commit") == VER.DESCONOCIDA,
              VER.de_expediente(viejo))
    rep = VER.reparto([viejo, nuevo.dir])
    comprobar("  y el reparto los separa, no los junta",
              len(rep) == 2 and rep.get(VER.DESCONOCIDA) == 1, rep)
    # UN version.json ROTO tampoco se supone: se cuenta como desconocida.
    roto = corral / "20260803T120000"
    roto.mkdir()
    (roto / "version.json").write_text("{esto no es json", encoding="utf-8")
    comprobar("un version.json ilegible tambien es «desconocida», no un error",
              VER.de_expediente(roto).get("commit") == VER.DESCONOCIDA)
finally:
    shutil.rmtree(corral, ignore_errors=True)


# ==================================== 4. LA ETIQUETA DICE LO SUCIO
print("\n=== 4. «+N SIN GUARDAR» VIAJA CON EL HASH ===")
comprobar("con cambios locales, la etiqueta lo dice",
          "sin guardar" in VER.etiqueta({"commit": "abc1234", "sucio": 3}),
          VER.etiqueta({"commit": "abc1234", "sucio": 3}))
comprobar("y sin ellos, no estorba",
          VER.etiqueta({"commit": "abc1234", "sucio": 0}) == "abc1234")


# ==================================== 5. UNA SOLA IMPLEMENTACION
print("\n=== 5. UNA PIEZA, NO UNA POR GUION ===")
print("  Es la septima vez que un arreglo se queda a medias por vivir en un")
print("  solo sitio. La lectura del commit ya estaba escrita a mano dentro")
print("  de comprobar_equipo; ahora hay una y las mediciones la usan.\n")
usan = []
for nombre in ("medir_reintento.py", "medir_no_encontrado.py", "medir_hilo.py",
               "comprobar_equipo.py"):
    f = RAIZ / nombre
    # Por el import del modulo, no por el alias: `comprobar_equipo` lo trae
    # como `_V` y el nombre del alias no es lo que se esta comprobando.
    if f.is_file() and "import version as" in f.read_text("utf-8"):
        usan.append(nombre)
comprobar("las mediciones y la ficha usan el modulo, no su propia copia",
          len(usan) == 4, usan)
comprobar("y las mediciones dicen de cuantas versiones es la muestra",
          all("reparto(" in (RAIZ / n).read_text("utf-8")
              for n in usan if n.startswith("medir_")), usan)
# EL CONTROL: que no quede ninguna lectura del hash escrita a mano por ahi.
sueltas = [f.name for f in RAIZ.glob("*.py")
           if "git" in f.read_text("utf-8")
           and "rev-parse" in f.read_text("utf-8")]
comprobar("y no queda ninguna lectura del commit a mano",
          not sueltas, sueltas)

print("\n" + "=" * 74)
if fallos:
    print(f"{len(fallos)} FALLO(S):")
    for f in fallos:
        print(f"   - {f}")
    sys.exit(1)
print("TODO EN VERDE · cada expediente dice de que version es")
sys.exit(0)
