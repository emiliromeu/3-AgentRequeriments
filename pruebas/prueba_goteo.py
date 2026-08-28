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

# Y CORTA: con cero minutos no se recorre ni uno.
#
# CONTRA UN CUADERNO EN BLANCO, Y NO CONTRA EL DE ESTE MAC. Esto miraba el
# avance de verdad, y el 28/08/2026 se puso rojo sin que nadie tocara nada: la
# sesion de goteo de esa mañana termino el barrido del dia, «por mirar hoy: 0»,
# y `gotear` salio por «no queda nada por mirar» sin llegar a la linea que esta
# comprobacion busca. La comprobacion era correcta y la respuesta tambien; lo
# que estaba mal era depender de que quedara trabajo pendiente. Una prueba que
# falla los dias que el barrido va al dia se acaba ignorando, y esta suite
# existe justo para lo contrario.
#
# Con un cuaderno inexistente todo esta por mirar, y entonces «cero minutos, ni
# uno recorrido» se puede afirmar siempre.
import io
import contextlib
import tempfile
_antes = gotear.AVANCE
_vacio = Path(tempfile.mkdtemp(prefix="goteo_limpio_"))
try:
    gotear.AVANCE = _vacio / "goteo.json"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        gotear.gotear(minutos=0, ensayo=True)
    salida = buf.getvalue()
    comprobar("con el cuaderno en blanco hay cola que recorrer",
              "por mirar hoy        : 0\n" not in salida, salida[:200])
    comprobar("  y con cero minutos no se recorre ni uno",
              "articulos recorridos : 0" in salida, salida[-160:])
finally:
    gotear.AVANCE = _antes
    shutil.rmtree(_vacio, ignore_errors=True)


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

# ==================================== 6. EL CERROJO Y EL CUADERNO
print("\n=== 6. UNA SESION A LA VEZ, Y EL CUADERNO NO SE PIERDE ===")
print("  Once sesiones de barrido son dieciseis horas de peticiones a un")
print("  servicio publico. Lo que las protege son tres cosas, y ninguna")
print("  existia: el cerrojo, la escritura que no deja a medias, y no dar por")
print("  «primer arranque» un cuaderno que esta ahi y no se puede leer.\n")

import os                                        # noqa: E402
import subprocess                                # noqa: E402
import time                                      # noqa: E402

# ESTA SECCION TOCA EL CUADERNO DE VERDAD, asi que no se puede pasar con una
# sesion de goteo en marcha: le pisaria el fichero mientras trabaja. Se
# pregunta al MISMO cerrojo que se esta probando, que es la forma honrada de
# saberlo, y si esta ocupado NO se salta en silencio: se dice arriba, se dice
# abajo y se cuenta aparte de los OK. Una prueba que se salta callando es peor
# que una que falla.
saltadas = []
en_marcha = gotear._quien_lo_tiene() if gotear.CERROJO.exists() else None
if en_marcha is not None:
    saltadas.append("el cerrojo y el cuaderno del goteo")
    print(f"  SALTADA: hay una sesion de goteo corriendo (pid "
          f"{en_marcha['pid']}, desde las {en_marcha['desde']}).")
    print("  Esta seccion escribe en el cuaderno de verdad y le pisaria el")
    print("  fichero. Para esa sesion y vuelve a lanzar la suite.\n")

if en_marcha is None:
    # (a) DOS SESIONES A LA VEZ: la segunda rebota. Se lanzan de verdad, en ensayo,
    # que no sale a la red. Con dos vivas leen el mismo cuaderno, piden lo mismo y
    # al guardar gana la ultima: el trabajo de la otra no queda en ninguna parte.
    uno = subprocess.Popen([sys.executable, str(RAIZ / "gotear.py"),
                            "--minutos", "1", "--ensayo"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, cwd=str(RAIZ))
    try:
        for _ in range(300):
            if gotear.CERROJO.exists():
                break
            time.sleep(0.05)
        comprobar("una sesion viva pone el cerrojo", gotear.CERROJO.exists())
        dos = subprocess.run([sys.executable, str(RAIZ / "gotear.py"),
                              "--minutos", "1", "--ensayo"],
                             capture_output=True, text=True, cwd=str(RAIZ))
        comprobar("  la segunda no arranca", dos.returncode == 1, dos.returncode)
        comprobar("  y dice quien lo tiene y desde cuando",
                  "pid" in dos.stdout and "desde las" in dos.stdout,
                  dos.stdout[:120])
        # EL ESTADO NO COGE EL CERROJO: esperar noventa minutos para poder
        # preguntar por donde va es lo contrario de para lo que sirve.
        est = subprocess.run([sys.executable, str(RAIZ / "gotear.py"), "--estado"],
                             capture_output=True, text=True, cwd=str(RAIZ))
        comprobar("  pero `--estado` sigue contestando: solo mira",
                  est.returncode == 0, est.returncode)
    finally:
        uno.wait(timeout=240)
    comprobar("  y al terminar lo suelta", not gotear.CERROJO.exists())

    # (b) UN CERROJO DE UN PROCESO MUERTO NO ES UN CERROJO. Es lo que queda cuando
    # se cierra el portatil a mitad de sesion, y hacer volver a alguien a borrar un
    # fichero a mano garantiza que el dia que estorbe se borre sin mirar.
    gotear.CERROJO.write_text(json.dumps({"pid": 999999, "desde": "ayer"}),
                              encoding="utf-8")
    try:
        r = subprocess.run([sys.executable, str(RAIZ / "gotear.py"),
                            "--minutos", "1", "--ensayo"],
                           capture_output=True, text=True, cwd=str(RAIZ))
        comprobar("un cerrojo de un proceso que ya no existe no bloquea",
                  r.returncode == 0, r.returncode)
        comprobar("  y se dice que se retira, no se hace en silencio",
                  "se retira" in r.stdout, r.stdout[:120])
    finally:
        gotear.CERROJO.unlink(missing_ok=True)

    # (c) EL CUADERNO A MEDIAS NO ES UN CUADERNO VACIO. Antes lo era: `leer_avance`
    # se tragaba el JSONDecodeError y devolvia el diccionario vacio, o sea que un
    # `goteo.json` truncado se leia como «no se ha mirado nada todavia» y la sesion
    # siguiente volvia a pedirle a PETETE el corpus entero. Sin un aviso.
    copia = gotear.AVANCE.read_bytes() if gotear.AVANCE.is_file() else None
    try:
        gotear.AVANCE.write_bytes((copia or b'{"articulos": {"a": 1}}')[:40])
        reventado = False
        try:
            gotear.leer_avance()
        except gotear.AvanceIlegible:
            reventado = True
        comprobar("un cuaderno a medias PARA, no se lee como vacio", reventado)
        r = subprocess.run([sys.executable, str(RAIZ / "gotear.py"),
                            "--minutos", "1", "--ensayo"],
                           capture_output=True, text=True, cwd=str(RAIZ))
        comprobar("  y la sesion no arranca", r.returncode == 1, r.returncode)
        comprobar("  diciendo que lo bajado NO se pierde",
                  "NO SE PIERDE" in r.stdout, r.stdout[:200])
        # NO PROMETE UN `git checkout` QUE NO EXISTE: el cuaderno esta excluido de
        # git a proposito -es de este Mac- asi que no hay copia de la que sacarlo,
        # y decir que la hay seria peor que no decir nada.
        comprobar("  y no promete recuperarlo de git, porque no viaja",
                  "git checkout" not in r.stdout, r.stdout[:200])
    finally:
        if copia is None:
            gotear.AVANCE.unlink(missing_ok=True)
        else:
            gotear.AVANCE.write_bytes(copia)

    # (d) LA ESCRITURA NO DEJA EL FICHERO BUENO A MEDIAS. Se escribe al lado y se
    # renombra: el fichero bueno es siempre uno entero, el de antes o el de ahora.
    FUENTE_GOTEO = (RAIZ / "gotear.py").read_text("utf-8")
    comprobar("el avance se guarda renombrando, no escribiendo encima",
              "os.replace(provisional, ruta)" in FUENTE_GOTEO)
    comprobar("  y el cerrojo no viaja por git",
              subprocess.run(["git", "check-ignore", "datos/dgt/goteo.cerrojo"],
                             cwd=str(RAIZ), capture_output=True).returncode == 0)



# ==================================== 7. EL RESUMEN, ABIERTO AL EMPEZAR
print("\n=== 7. UNA SESION CORTADA DEJA RASTRO ===")
print("  El resumen se escribia AL TERMINAR, asi que una sesion cortada no")
print("  aparecia en `sesiones`: se apuntaba lo bajado -eso se guarda cada")
print("  diez articulos- pero las dos horas no habian existido. De las trece")
print("  del goteo de la DGT, dos se cortaron. Lo que no deja rastro no se")
print("  puede diagnosticar.\n")

# CON DOBLES Y SIN RED. El plan de la DGT esta agotado, asi que este camino no
# se puede recorrer de verdad sin pedirle a PETETE cosas que ya tenemos. Se le
# pone una fuente que no sale a ningun sitio y un cuaderno en blanco.
import types                                    # noqa: E402
import petete as _petete                        # noqa: E402


class _FuenteSeca:
    """Contesta sin resultados, y a la N-esima corta como un Ctrl+C."""

    def __init__(self, corta_en):
        self.corta_en, self.veces = corta_en, 0

    def _campos(self, *a, **k):
        return [("VLCMP_3", "")]

    def pedir(self, *a, **k):
        self.veces += 1
        if self.veces >= self.corta_en:
            raise KeyboardInterrupt("cortada a proposito")
        return types.SimpleNamespace(cuerpo="")


corral7 = Path(tempfile.mkdtemp(prefix="sesion_"))
guardado7 = (gotear.AVANCE, _petete.Fuente, _petete.Cache,
             _petete.extraer_resultados, gotear.PAUSA_ENSAYO)
try:
    gotear.AVANCE = corral7 / "goteo.json"
    _petete.Cache = lambda *a, **k: None
    _petete.extraer_resultados = lambda crudo: []
    _petete.PAUSA = 0
    cortada = _FuenteSeca(corta_en=12)
    _petete.Fuente = lambda *a, **k: cortada

    try:
        gotear.gotear(minutos=90, ensayo=False)
    except KeyboardInterrupt:
        pass          # es lo que se esta simulando: alguien la para

    d = json.loads(gotear.AVANCE.read_text(encoding="utf-8"))
    ses = d.get("sesiones") or []
    comprobar("la sesion cortada SI aparece en el cuaderno", len(ses) == 1,
              ses)
    fila = ses[0] if ses else {}
    comprobar("  y esta marcada como no terminada",
              fila.get("terminada") is False, fila)
    comprobar("  con la hora en que empezo, no solo el dia",
              len(str(fila.get("empezada", ""))) >= 16, fila.get("empezada"))
    # LAS CIFRAS SON LAS DE VERDAD, NO CEROS. Una fila con ceros pareceria
    # noventa minutos sin hacer nada, que es peor que no dejarla.
    comprobar("  y con lo que alcanzo a hacer, no con ceros",
              fila.get("articulos", 0) > 0, fila)
    comprobar("  y dice cuanto habia por mirar cuando empezo",
              fila.get("por_mirar_al_empezar", 0) > 0, fila)

    # Y UNA QUE SI TERMINA cierra ESA MISMA fila, no añade otra: dos filas por
    # sesion serian dos sesiones en cuanto alguien las contara.
    gotear.AVANCE.unlink(missing_ok=True)
    _petete.Fuente = lambda *a, **k: _FuenteSeca(corta_en=10**9)
    gotear.gotear(minutos=0, ensayo=False)
    d = json.loads(gotear.AVANCE.read_text(encoding="utf-8"))
    ses = d.get("sesiones") or []
    comprobar("una sesion que termina deja UNA sola fila", len(ses) == 1, ses)
    comprobar("  marcada como terminada",
              ses and ses[0].get("terminada") is True, ses)
finally:
    (gotear.AVANCE, _petete.Fuente, _petete.Cache,
     _petete.extraer_resultados, gotear.PAUSA_ENSAYO) = guardado7
    shutil.rmtree(corral7, ignore_errors=True)

# Y EL ENSAYO SIGUE SIN APUNTAR NADA: la seccion 4 ya lo prueba, y esto no
# puede haberlo cambiado.
FUENTE_G = (RAIZ / "gotear.py").read_text("utf-8")
comprobar("el ensayo sigue sin abrir fila de sesion",
          "sesion = None" in FUENTE_G and "if not ensayo:" in FUENTE_G)
comprobar("y `--estado` marca las cortadas",
          "CORTADA, no llego al final" in FUENTE_G)


# ==================================== CONTROL NEGATIVO
print("\n=== CONTROL NEGATIVO: la suite tiene que ponerse roja ===")
print("  Ninguna prueba se da por buena sin verla fallar cuando debe fallar.\n")

# Sin cerrojo puesto, la comprobacion (a) tiene que dar el resultado contrario:
# si `_quien_lo_tiene` dijera siempre «hay alguien», bloquearia el goteo para
# siempre, y si dijera siempre «no hay nadie», el cerrojo no serviria de nada.
if en_marcha is None:
    gotear.CERROJO.write_text(json.dumps({"pid": os.getpid(),
                                          "desde": "ahora"}), encoding="utf-8")
    try:
        comprobar("un cerrojo de un proceso VIVO si lo reconoce como ocupado",
                  gotear._quien_lo_tiene() is not None)
    finally:
        gotear.CERROJO.unlink(missing_ok=True)
    gotear.CERROJO.write_text("esto no es json", encoding="utf-8")
    try:
        # Un cerrojo ilegible no puede sostener que haya alguien: no sabe de
        # quien es. Bloquear con el dejaria el goteo parado sin poder decir
        # por que.
        comprobar("un cerrojo ilegible no bloquea",
                  gotear._quien_lo_tiene() is None)
    finally:
        gotear.CERROJO.unlink(missing_ok=True)
else:
    # EL CONTROL NEGATIVO SIN CERROJO SI SE PUEDE HACER: no lo toca. El de un
    # proceso vivo es el que hay puesto ahi fuera.
    comprobar("el cerrojo de la sesion en marcha se reconoce como ocupado",
              gotear._quien_lo_tiene() is not None)


print("\n" + "=" * 74)
if fallos:
    print(f"{len(fallos)} FALLO(S):")
    for f in fallos:
        print(f"   - {f}")
    sys.exit(1)
if saltadas:
    print(f"TODO EN VERDE, PERO {len(saltadas)} SECCION(ES) SIN PROBAR:")
    for x in saltadas:
        print(f"   - {x}   (hay una sesion de goteo en marcha)")
    print("\nPara una suite entera: para el goteo y vuelve a lanzarla.")
    sys.exit(0)
print("TODO EN VERDE · el goteo recorre todo, por utilidad y a ratos")
sys.exit(0)
