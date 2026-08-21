#!/usr/bin/env python3
"""EL GOTEO: TODO EL CORPUS, A RATOS, Y SIN PISAR NADA. Cero red, cero API.

    python pruebas/prueba_goteo.py

El goteo corre EN EL MAC y lo que baja viaja por git. En la oficina no corre:
alli solo la cola por demanda. Esta suite vigila las cuatro cosas que lo hacen
utilizable, y ninguna es sobre la red -esa no se toca-.

  1. RECORRE TODO, sin el corte de `plan_siembra`, pero POR UTILIDAD: si se
     para para siempre a mitad, lo bajado tiene que ser lo util.
  2. EL LIMITE ES DE TIEMPO y se comprueba ANTES de cada articulo. Uno sin
     consultas tarda segundos y uno con cinco tarda un minuto: con tope por
     numero, dos sesiones «iguales» duran cosas distintas.
  3. LA MEMORIA ES LA DE `cola.py`, no una copia. Dos copias de una regla son
     dos reglas en cuanto alguien cambie una.
  4. EL ENSAYO NO DEJA RASTRO. La primera version apunto los 2.033 articulos
     como «buscados» y la sesion de verdad se los habria saltado todos.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import gotear                                    # noqa: E402
from agente_fiscal import cola as COLA           # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:110]}" if not ok else ""))
    if not ok:
        fallos.append(que)


# ==================================== 1. TODO EL CORPUS, POR UTILIDAD
print("\n=== 1. RECORRE TODO EL CORPUS, Y POR UTILIDAD ===")
print("  Sin el corte de `plan_siembra` -que deja fuera lo que tiene menos de")
print("  dos remisiones entrantes-, pero en orden: si el goteo se para para")
print("  siempre a mitad, lo que habra bajado es lo util.\n")

import fase4                                     # noqa: E402
ix, grafo = fase4.cargar_corpus()
orden = gotear.orden_de_utilidad(ix, grafo)

arts = [d for d in ix.docs if d.registro.get("tipo") == "articulo"
        and str(d.registro.get("numero_norm") or d.registro.get("numero")
                or "").strip()[:1].isdigit()
        and d.registro.get("cuerpo_clave")]
comprobar("entran TODOS los articulos del corpus, sin corte",
          len(orden) == len(arts), f"{len(orden)} de {len(arts)}")

import plan_siembra                              # noqa: E402
del_plan = sum(len(v) for v in plan_siembra.plan().values())
comprobar("  y son muchos mas que los del plan, que si corta",
          len(orden) > del_plan * 2, f"goteo {len(orden)} · plan {del_plan}")

# EL ORDEN: los primeros tienen que puntuar mas que los ultimos.
def puntos(por):
    b = int(por.split("banco ")[1].split(" ")[0])
    r = int(por.split("remisiones ")[1])
    return b * plan_siembra.PESO_BANCO + r

cabeza = [puntos(p) for _c, _a, p in orden[:20]]
cola_ = [puntos(p) for _c, _a, p in orden[-20:]]
comprobar("los primeros puntuan mas que los ultimos",
          min(cabeza) > max(cola_), f"cabeza {min(cabeza)} · cola {max(cola_)}")
comprobar("  y el orden no sube nunca", 
          all(puntos(orden[i][2]) >= puntos(orden[i + 1][2])
              for i in range(len(orden) - 1)))
comprobar("la cuenta del banco es LA MISMA que la del plan, no una copia",
          "plan_siembra.puntos_del_banco" in (RAIZ / "gotear.py").read_text("utf-8"))
# EL CONTROL: que no haya vuelto el respaldo que se tragaba el fallo.
comprobar("  y sin respaldo que siga con la mitad de la señal",
          "except AttributeError" not in (RAIZ / "gotear.py").read_text("utf-8"))


# ==================================== 2. EL LIMITE ES DE TIEMPO
print("\n=== 2. EL LIMITE ES DE TIEMPO, Y CORTA DE VERDAD ===")
print("  Un articulo sin consultas tarda segundos; uno con cinco, un minuto.")
print("  Con tope por numero, dos sesiones «de cincuenta» duran diez minutos")
print("  o una hora, y entonces no se puede encajar en un hueco.\n")

FUENTE = (RAIZ / "gotear.py").read_text("utf-8")
comprobar("la sesion se mide en minutos", "--minutos" in FUENTE)
comprobar("  y el tope por defecto son 90", gotear.MINUTOS_POR_DEFECTO == 90)
comprobar("el tiempo se mira ANTES de empezar cada articulo, no en mitad",
          "if time.monotonic() >= fin:" in FUENTE
          and FUENTE.index("if time.monotonic() >= fin:")
          < FUENTE.index("resultados = petete.extraer_resultados"))

# Y CORTA: una sesion de un minuto no recorre los 2.033.
import io
import contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    gotear.gotear(minutos=0, ensayo=True)
salida = buf.getvalue()
comprobar("con cero minutos no se recorre nada",
          "articulos recorridos : 0" in salida, salida[-160:])


# ==================================== 3. LA MEMORIA ES LA DE LA COLA
print("\n=== 3. LOS PLAZOS SALEN DE `cola.py`, NO SE COPIAN ===")
comprobar("el goteo pregunta a `cola._toca_reintentar`",
          "COLA._toca_reintentar" in FUENTE)
comprobar("  y no reescribe los plazos por su cuenta",
          "DIAS_REINTENTO =" not in FUENTE and "DIAS_REFRESCO =" not in FUENTE)

_g = RAIZ / "datos" / "dgt" / "goteo.json"
_guardado = gotear.AVANCE
corral = Path(tempfile.mkdtemp())
gotear.AVANCE = corral / "goteo.json"
try:
    from datetime import date, timedelta

    def hace(d):
        return (date.today() - timedelta(days=d)).isoformat()

    av = {"articulos": {}, "sesiones": []}
    av["articulos"]["c#0#7"] = {"estado": COLA.SIN_RESULTADOS,
                                "buscado": hace(10)}
    av["articulos"]["c#0#8"] = {"estado": COLA.SIN_RESULTADOS,
                                "buscado": hace(200)}
    av["articulos"]["c#0#9"] = {"estado": COLA.BAJADA, "buscado": hace(10)}
    av["articulos"]["c#0#10"] = {"estado": COLA.BAJADA, "buscado": hace(200)}
    comprobar("un vacio de hace 10 dias NO se repite",
              not gotear.toca(av, "c#0#7", False))
    comprobar("  uno de hace 200 SI: han pasado los 90",
              gotear.toca(av, "c#0#8", False))
    comprobar("uno con criterio de hace 10 dias NO se refresca",
              not gotear.toca(av, "c#0#9", True))
    comprobar("  uno de hace 200 SI: han pasado los 180",
              gotear.toca(av, "c#0#10", True))
    comprobar("y uno que no se ha mirado nunca, siempre toca",
              gotear.toca(av, "c#0#99", False))


    # ============================ 4. EL ENSAYO NO DEJA RASTRO
    print("\n=== 4. EL ENSAYO NO APUNTA NADA ===")
    print("  La primera version apunto los 2.033 como «buscados», y la sesion")
    print("  de verdad se los habria saltado todos. Una prueba que deja el")
    print("  sistema creyendo que el trabajo esta hecho es peor que no probar.\n")
    with contextlib.redirect_stdout(io.StringIO()):
        gotear.gotear(minutos=0, ensayo=True)
    comprobar("tras un ensayo, el fichero de avance NO existe",
              not gotear.AVANCE.is_file(), gotear.AVANCE)
finally:
    gotear.AVANCE = _guardado
    shutil.rmtree(corral, ignore_errors=True)


# ==================================== 5. EN LA OFICINA NO CORRE
print("\n=== 5. EN LA OFICINA EL GOTEO NO CORRE ===")
print("  Alli solo la cola por demanda. El goteo baja a `consultas/`, que")
print("  viaja por git; la cola baja a `demanda/`, que no.\n")
comprobar("el goteo escribe en `consultas/`, que es lo que viaja",
          'DESTINO = RAIZ / "datos" / "dgt" / "consultas"' in FUENTE)
comprobar("  y la cola sigue escribiendo en `demanda/`, que no viaja",
          'DEMANDA = RAIZ / "datos" / "dgt" / "demanda"' in
          (RAIZ / "agente_fiscal" / "cola.py").read_text("utf-8"))
VEN = (RAIZ / "interfaz.py").read_text("utf-8")
comprobar("la ventana NO lanza el goteo: no es cosa de la oficina",
          "gotear" not in VEN, "la ventana llama al goteo")

print("\n" + "=" * 74)
if fallos:
    print(f"{len(fallos)} FALLO(S):")
    for f in fallos:
        print(f"   - {f}")
    sys.exit(1)
print("TODO EN VERDE · el goteo recorre todo, por utilidad y a ratos")
sys.exit(0)
