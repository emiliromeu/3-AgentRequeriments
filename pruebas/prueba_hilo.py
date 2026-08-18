#!/usr/bin/env python3
"""LA CONVERSACION: SEGUIR HABLANDO SIN AFLOJAR NADA. Cero API, cero red.

    python pruebas/prueba_hilo.py

Son la A y la B que pidio el departamento -precisar la pregunta y preguntar
sobre la respuesta-. Por fuera se siente como un chat. Por dentro NO LO ES, y
esta suite existe para vigilar exactamente las tres formas en que dejaria de
no serlo:

  1. QUE UNA VUELTA SE QUEDE A MEDIAS. El tope de llamadas protege LA CONSULTA,
     y nadie cuenta la sesion. Conversar multiplica las consultas por sesion,
     que es justo el escenario que ya rompio esto una vez -a partir de la
     tercera pregunta el agente dejaba de contestar y no se recuperaba hasta
     cerrar la ventana-. Aqui se prueban SEIS VUELTAS SEGUIDAS.

  2. QUE SE REUTILICE EL MATERIAL DE LA VUELTA ANTERIOR. Es lo comodo y es lo
     que hace un chatbot: ya se busco, ya se verifico, para que otra vez. Y es
     falso, porque el contexto nuevo puede cambiar QUE ARTICULOS APLICAN -«y si
     fuera una furgoneta»- y entonces se contesta con seguridad sobre los
     articulos equivocados. Cada vuelta se analiza, se busca, se redacta y se
     verifica DE CERO.

  3. QUE LA FRONTERA SE AFLOJE PORQUE EL FORMATO ES MAS SUELTO. Conversar
     invita a «¿y tu que harias?». El sistema aporta respaldo, no conclusion.
     El caso adversario esta abajo, entero.

El motor va DOBLADO. `MotorEnsayo` no es un modelo -son cuatro reglas fijas-
pero SI trae los topes de verdad: `_permiso`, `llamadas` y `empezar_consulta`
son los mismos que usa el motor real. Lo que se prueba con el es el andamiaje,
que es lo que puede romperse aqui.
"""
import io
import json
import contextlib
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4                                    # noqa: E402
from agente_fiscal import modelo as MOD         # noqa: E402
from agente_fiscal import redactor as RED       # noqa: E402
from agente_fiscal import verificador as VF     # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:120]}" if not ok else ""))
    if not ok:
        fallos.append(que)


def callado(f, *a, **k):
    """La fase 4 imprime la consulta entera. Aqui estorba."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = f(*a, **k)
    return r, buf.getvalue()


ix, grafo = fase4.cargar_corpus()

# LA PREGUNTA DE ARRANQUE. Se elige una que LLEGA A REDACTAR con el motor de
# ensayo -dos llamadas- porque con una sola no se probaria el tope: seis
# vueltas de una llamada caben en el techo aunque no se reiniciara nunca, y la
# suite pasaria verde sobre el fallo que quiere impedir.
PRIMERA = "Se puede deducir el IVA soportado en la adquisicion de un vehiculo turismo"

# Las cinco lineas que se van añadiendo, como las escribiria alguien del
# departamento: se precisa (A) y se pregunta sobre lo contestado (B).
AÑADIDOS = [
    "Es para un comercial que lo usa tambien los fines de semana",
    "Y si fuera una furgoneta de reparto",
    "Entonces que pasa con el 50 por ciento",
    "El vehiculo se compro en 2022 pero se afecto en 2023",
    "Y si la empresa se lo cede al empleado por su trabajo",
]


# ============================================================ 1. SEIS VUELTAS
print("\n=== 1. SEIS VUELTAS SEGUIDAS, CON EL MISMO MOTOR ===")
print(f"  El tope son {MOD.TOPE_LLAMADAS} llamadas POR CONSULTA. Seis vueltas")
print("  con dos llamadas cada una son doce: el triple del techo.\n")

motor = MOD.MotorEnsayo()          # UNO SOLO, como hace la ventana al abrirse
vueltas, pregunta, viene_de, contexto = [], PRIMERA, "", None

for n in range(1, 7):
    r, _ = callado(fase4.consultar, pregunta, 2023, motor, ix, grafo,
                   viene_de=viene_de, contexto_anterior=contexto)
    vueltas.append(r)
    print(f"    vuelta {n} · {r.get('estado'):16s} "
          f"llamadas de la vuelta: {motor.llamadas}  "
          f"viene_de: {r.get('viene_de') or '-'}")
    # La ventana hereda la pregunta y le añade una linea. Aqui igual.
    if n <= len(AÑADIDOS):
        pregunta = f"{pregunta}\n\n{AÑADIDOS[n - 1]}"
    viene_de = Path(r["traza"]).name
    contexto = {"resumen": (r.get("analisis") or {}).get("resumen_duda", ""),
                "preceptos": r.get("preceptos_enviados") or []}

print()
a_medias = [i + 1 for i, r in enumerate(vueltas) if r.get("fallo") == "tope"]
comprobar("NINGUNA VUELTA SE QUEDA A MEDIAS por el tope de llamadas",
          not a_medias, f"se quedaron a medias las vueltas {a_medias}")
comprobar("  ninguna muere por otro fallo del motor",
          not [r for r in vueltas if r.get("fallo")],
          [r.get("fallo") for r in vueltas])
comprobar("  las seis tienen expediente propio",
          len({r["traza"] for r in vueltas}) == 6,
          len({r["traza"] for r in vueltas}))
comprobar("  la primera NO es continuacion de nada",
          not vueltas[0].get("viene_de"), vueltas[0].get("viene_de"))
comprobar("  las otras cinco SI, y encadenadas",
          all(vueltas[i].get("viene_de") == Path(vueltas[i - 1]["traza"]).name
              for i in range(1, 6)),
          [r.get("viene_de") for r in vueltas])
comprobar("  y marcadas como continuacion",
          all(r.get("tipo") == "continuacion" for r in vueltas[1:]),
          [r.get("tipo") for r in vueltas])

# EL HILO SE RECONSTRUYE DESDE EL DISCO, que es donde tiene que estar: dentro
# de seis meses la memoria de la ventana no existe y el expediente si.
hilos = [json.loads((Path(r["traza"]) / "hilo.json").read_text("utf-8"))
         for r in vueltas[1:]]
comprobar("el hilo queda escrito en cada expediente (hilo.json)",
          all(h.get("viene_de") for h in hilos), hilos)


# ================================================ 2. EL CONTROL NEGATIVO
print("\n=== 2. Y SI EL TOPE NO SE REINICIARA, ESTO TENDRIA QUE FALLAR ===")
print("  Se dobla `empezar_consulta` para que NO reinicie el contador, que es")
print("  exactamente el fallo que tuvo el sistema. Sin esto, la seccion 1")
print("  seria verde por casualidad.\n")


class MotorQueNoReinicia(MOD.MotorEnsayo):
    def empezar_consulta(self):
        pass                        # el reloj y el contador se quedan como estan


roto = MotorQueNoReinicia()
mudas, preg2 = [], PRIMERA
for n in range(1, 7):
    r, _ = callado(fase4.consultar, preg2, 2023, roto, ix, grafo)
    mudas.append(r)
    if n <= len(AÑADIDOS):
        preg2 = f"{preg2}\n\n{AÑADIDOS[n - 1]}"

cortadas = [i + 1 for i, r in enumerate(mudas) if r.get("fallo") == "tope"]
print(f"    vueltas que se quedan a medias sin el reinicio: {cortadas}")
comprobar("SIN EL REINICIO, alguna vuelta se queda a medias (la prueba puede "
          "fallar)", bool(cortadas), "ninguna fallo: la seccion 1 no prueba nada")


# =========================================== 3. NADA SE REUTILIZA ENTRE VUELTAS
print("\n=== 3. CADA VUELTA SE BUSCA Y SE VERIFICA DE CERO ===")

espia = {"analisis": [], "redaccion": []}


class MotorEspia(MOD.MotorEnsayo):
    def analizar(self, sistema, pregunta, esquema):
        espia["analisis"].append(pregunta)
        return super().analizar(sistema, pregunta, esquema)

    def redactar(self, sistema, contenido):
        espia["redaccion"].append((sistema, contenido))
        return super().redactar(sistema, contenido)


m3 = MotorEspia()
r1, _ = callado(fase4.consultar, PRIMERA, 2023, m3, ix, grafo)
r2, _ = callado(fase4.consultar, f"{PRIMERA}\n\n{AÑADIDOS[0]}", 2023, m3, ix,
                grafo, viene_de=Path(r1["traza"]).name,
                contexto_anterior={
                    "resumen": (r1.get("analisis") or {}).get("resumen_duda", ""),
                    "preceptos": r1.get("preceptos_enviados") or []})

comprobar("la segunda vuelta VUELVE A ANALIZAR (no reusa el analisis)",
          len(espia["analisis"]) >= 2, len(espia["analisis"]))
comprobar("  y VUELVE A REDACTAR sobre material buscado de nuevo",
          len(espia["redaccion"]) >= 2, len(espia["redaccion"]))
# La verificacion propia se comprueba EN EL DISCO: es la que quedara dentro de
# seis meses, y es la unica prueba de que la vuelta se comprobo por si misma.
verif2 = sorted(Path(r2["traza"]).glob("verificacion_*.json"))
comprobar("  y con su propia verificacion, escrita en SU expediente",
          bool(verif2), [f.name for f in Path(r2["traza"]).iterdir()])

ultimo_analisis = espia["analisis"][-1]
comprobar("AL ANALIZADOR le llega el contexto de la vuelta anterior",
          "ESTO VIENE DE UNA CONSULTA ANTERIOR" in ultimo_analisis,
          ultimo_analisis[:80])
comprobar("  con el RESUMEN de la duda, no la respuesta entera",
          "Antes se pregunto:" in ultimo_analisis
          and (r1.get("respuesta") or "zzz")[:60] not in ultimo_analisis)
comprobar("  y con los preceptos que se usaron",
          "Y se contesto sobre estos articulos:" in ultimo_analisis)
comprobar("  diciendole que analice LA PREGUNTA DE AHORA",
          "LA PREGUNTA DE AHORA" in ultimo_analisis)

if espia["redaccion"]:
    sistemas = [s for s, _c in espia["redaccion"]]
    comprobar("AL REDACTOR NO le llega nada del hilo: mismo prompt de siempre",
              all(s == RED.SISTEMA for s in sistemas),
              "el prompt del redactor cambia entre vueltas")
    materiales = [c for _s, c in espia["redaccion"]]
    comprobar("  y el material NO arrastra el de la vuelta anterior",
              all("ESTO VIENE DE UNA CONSULTA ANTERIOR" not in c
                  for c in materiales))


# ================================================== 4. LA FRONTERA
print("\n=== 4. EL CASO ADVERSARIO: UNA PREGUNTA QUE PIDE UNA DECISION ===")
print('  «Tenemos las dos opciones sobre la mesa. ¿Y tu que harias?»')
print("  El sistema aporta respaldo, NO conclusion. Y conversar no cambia eso.\n")

comprobar("el prompt del redactor dice que NO decide",
          "Tu\nno decides" in RED.SISTEMA or "no decides" in RED.SISTEMA,
          RED.SISTEMA[:120])
comprobar("  y dice quien decide: el profesional",
          "es quien decide" in RED.SISTEMA)

# LOS DOS TEXTOS SE MIDEN CONTRA EL VERIFICADOR DE VERDAD, y el fragmento es
# LITERAL del corpus: una cita inventada saldria rechazada por el motivo
# equivocado y la suite pasaria verde sin probar nada.
art95 = next(d for d in ix.docs
             if d.registro.get("clave") == "BOE-A-1992-28740#0#articulo 95")
texto95 = art95.registro["texto_vigente"]
trozo = "Los empresarios o profesionales no podrán deducir las cuotas soportadas"
comprobar("el fragmento del caso es LITERAL del corpus", trozo in texto95,
          texto95[:90])

DECIDE = ("Yo en tu caso me acogeria a la deduccion del 100 por cien: es lo "
          "que hace todo el mundo y Hacienda no suele entrar. Te recomiendo "
          "esa opcion.")
RESPALDA = (f"La regla general es que «{trozo}» (artículo 95 de la Ley "
            f"37/1992, https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a95). "
            f"Que porcentaje de afectacion se acredita en este caso es una "
            f"valoracion del expediente.")

ver = VF.Verificador(ix)
i_decide = ver.verificar_texto(DECIDE, 2023, exigir_norma=True)
i_respalda = ver.verificar_texto(RESPALDA, 2023, exigir_norma=True)

comprobar("LA QUE DECIDE SIN MATERIAL se cae: no hay nada que enseñar",
          i_decide.veredicto == VF.RECHAZADO, i_decide.veredicto)
print(f"        motivo: {i_decide.motivo_global}")
comprobar("LA QUE APORTA EL MATERIAL SIN DECIDIR pasa",
          i_respalda.veredicto == VF.ACEPTADO,
          f"{i_respalda.veredicto} · {i_respalda.motivo_global}")

# Y LA MISMA PUERTA, EN UNA VUELTA DE VERDAD: la pregunta que pide decision
# entra como continuacion, y el redactor devuelve el consejo. Se comprueba que
# NO llega a pantalla.
class MotorQueAconseja(MOD.MotorEnsayo):
    def redactar(self, sistema, contenido):
        self._permiso("redaccion")
        self.llamadas += 1
        self._anotar("redaccion", "(ninguno)", {})
        return MOD.Respuesta(texto=DECIDE, datos=None, crudo={"stop_reason": "end_turn"})


m4 = MotorQueAconseja()
base, _ = callado(fase4.consultar, PRIMERA, 2023, MOD.MotorEnsayo(), ix, grafo)
r4, _ = callado(fase4.consultar,
                f"{PRIMERA}\n\nTenemos las dos opciones sobre la mesa, y tu que harias",
                2023, m4, ix, grafo, viene_de=Path(base["traza"]).name,
                contexto_anterior={"resumen": "deduccion del IVA del turismo",
                                   "preceptos": base.get("preceptos_enviados") or []})

comprobar("EN UNA CONTINUACION, el consejo sin respaldo tampoco sale",
          r4.get("veredicto") != VF.ACEPTADO
          and DECIDE[:40] not in (r4.get("respuesta") or ""),
          f"{r4.get('veredicto')} · {(r4.get('respuesta') or '')[:60]}")
comprobar("  y la vuelta acaba entera, no a medias",
          r4.get("fallo") != "tope", r4.get("fallo"))


# ================================================== 5. LA VENTANA
print("\n=== 5. LO QUE HACE LA VENTANA ===")
VEN = (RAIZ / "interfaz.py").read_text("utf-8")
# Se miran las ORDENES, no los comentarios: dos veces se ha dado por buena una
# comprobacion que en realidad leia la frase que explicaba por que NO se hacia.
ordenes = "\n".join(l for l in VEN.splitlines()
                    if l.strip() and not l.strip().startswith("#"))

comprobar("existe el boton de seguir", "boton_seguir" in ordenes)
comprobar("  y hace algo cuando se pulsa", "def _seguir" in ordenes)
comprobar("LA CAJA DE ARRIBA NO SE VACIA: la pregunta anterior sigue ahi",
          'self.caja.insert("1.0", f"{anterior}' in ordenes)
comprobar("  y la caja de añadir SI, para la siguiente",
          'self.caja_seguir.delete("1.0", "end")' in ordenes)
comprobar("SOLO CON RESPUESTA: la caja de seguir se esconde si no hay",
          "self.marco_seguir.grid_remove()" in ordenes)
comprobar("EN PANTALLA SE VE QUE ES UNA CONTINUACION",
          'if res.get("viene_de"):' in ordenes and "Vuelta {" in ordenes)
comprobar("EL COPIAR LLEVA LA VUELTA",
          "vuelta {self.vuelta} de la consulta" in ordenes)
# El cuerpo de `_seguir`, solo: que no toque el año ni la comunidad. Se
# heredan porque NADIE LOS CAMBIA, no porque se copien a mano, y asi siguen
# editables por si el caso resulta ser de otro ejercicio.
cuerpo_seguir = ordenes.split("def _seguir")[1].split("\n    def ")[0]
comprobar("al seguir NO se tocan el año ni la comunidad: quedan editables",
          "self.ejercicio.set(" not in cuerpo_seguir
          and "self.comunidad.set(" not in cuerpo_seguir, cuerpo_seguir[:90])
comprobar("y el hilo se apunta por NOMBRE de expediente, no por camino",
          "Path(self.traza_actual).name" in cuerpo_seguir)
comprobar("y el modo -con criterio o sin el- se hereda: es la misma consulta",
          "self._lanzar(self.con_criterio)" in cuerpo_seguir)

# ============================== 5bis. DOS VUELTAS NO SE PISAN EL EXPEDIENTE
print("\n=== 5bis. DOS CONSULTAS EN EL MISMO SEGUNDO NO COMPARTEN CARPETA ===")
print("  El sello va al segundo. Antes la carpeta se creaba con `exist_ok`,")
print("  asi que la segunda escribia ENCIMA: misma pregunta.txt, mismo")
print("  analisis.json. El expediente de la primera desaparecia. Con la")
print("  conversacion dejo de ser raro: una vuelta que acaba en NO ENCONTRADO")
print("  tarda decimas y la siguiente va detras.\n")

import shutil
import tempfile
from agente_fiscal.traza import Traza            # noqa: E402

corral = Path(tempfile.mkdtemp())
try:
    trazas = [Traza(corral, f"la duda numero {i}") for i in range(4)]
    comprobar("cuatro trazas seguidas, cuatro carpetas",
              len({t.dir for t in trazas}) == 4, [t.sello for t in trazas])
    comprobar("  y cada una conserva SU pregunta",
              [(t.dir / "pregunta.txt").read_text("utf-8") for t in trazas]
              == [f"la duda numero {i}" for i in range(4)])
    comprobar("  el sello sigue empezando por la fecha y la hora",
              all(t.sello[:15] == trazas[0].sello[:15] for t in trazas),
              [t.sello for t in trazas])
finally:
    shutil.rmtree(corral, ignore_errors=True)


print("\n=== 6. Y LA VENTANA DE VERDAD, PULSANDO EL BOTON ===")
print("  El grep de arriba dice que el codigo esta escrito. Esto dice que")
print("  hace lo que dice: la caja no se vacia y la vuelta sube.\n")

import time
import tkinter as tk
import interfaz                                  # noqa: E402

raiz = tk.Tk()
raiz.withdraw()
try:
    v = interfaz.Ventana(raiz, "ensayo")
    fin = time.time() + 3
    while time.time() < fin:
        raiz.update(); raiz.update_idletasks(); time.sleep(0.02)

    # La ventana va oculta en la suite, asi que `winfo_ismapped` da 0 para
    # todo. Lo que distingue puesta de quitada es `grid_info`.
    comprobar("al abrir, la caja de seguir NO se ve: aun no hay respuesta",
              not v.marco_seguir.grid_info(), v.marco_seguir.grid_info())

    # Se simula la respuesta aceptada tal como llega del hilo de trabajo, por
    # la cola de avisos, que es el camino real.
    r = dict(vueltas[0])
    v.avisos.put(("hecho", r))
    with contextlib.redirect_stdout(io.StringIO()):
        v._vaciar_avisos()
    raiz.update(); raiz.update_idletasks()
    comprobar("con respuesta aceptada, la caja de seguir aparece",
              bool(v.marco_seguir.grid_info()), v.marco_seguir.grid_info())
    comprobar("  y va DEBAJO de la respuesta, no encima",
              int(v.marco_seguir.grid_info().get("row", -1))
              > int(v.resultado.grid_info().get("row", 99)),
              v.marco_seguir.grid_info().get("row"))
    comprobar("  y se guarda de que preceptos iba, para la vuelta siguiente",
              v.preceptos_actuales == (r.get("preceptos_enviados") or []),
              v.preceptos_actuales)

    v.caja.delete("1.0", "end")
    v.caja.insert("1.0", PRIMERA)
    v.ejercicio.set("2023")
    v.caja_seguir.insert("1.0", AÑADIDOS[0])

    lanzado = {}
    v._lanzar = lambda con_criterio=None: lanzado.update(
        pregunta=v.caja.get("1.0", "end").strip(),
        ejercicio=v.ejercicio.get(),
        viene_de=v.hilo_viene_de, contexto=v.hilo_contexto, vuelta=v.vuelta)
    v._seguir()

    comprobar("al seguir, la pregunta anterior SIGUE en la caja",
              lanzado.get("pregunta", "").startswith(PRIMERA),
              lanzado.get("pregunta", "")[:60])
    comprobar("  con la linea nueva añadida debajo",
              lanzado.get("pregunta", "").endswith(AÑADIDOS[0]),
              lanzado.get("pregunta", "")[-60:])
    comprobar("  el año se hereda y sigue siendo editable",
              lanzado.get("ejercicio") == "2023"
              and str(v.ejercicio_caja.cget("state")) != "disabled"
              if hasattr(v, "ejercicio_caja") else
              lanzado.get("ejercicio") == "2023", lanzado.get("ejercicio"))
    comprobar("  va marcada como continuacion de la anterior, POR NOMBRE",
              lanzado.get("viene_de") == Path(r["traza"]).name,
              lanzado.get("viene_de"))
    comprobar("  con el resumen y los preceptos de la anterior",
              (lanzado.get("contexto") or {}).get("preceptos")
              == (r.get("preceptos_enviados") or []), lanzado.get("contexto"))
    comprobar("  y es la vuelta 2", lanzado.get("vuelta") == 2,
              lanzado.get("vuelta"))
    # LA BARRA DE PROGRESO VIVE EN LA PANTALLA DE PREGUNTAR. Si la vuelta se
    # lanzara desde la de leer, correria entera sin que se viera nada.
    comprobar("  y se vuelve a la pantalla donde SE VE que esta buscando",
              bool(v.vista_consulta.grid_info()),
              "la vuelta corre detras de la respuesta vieja, sin señal")
    comprobar("la caja de añadir queda vacia para la siguiente",
              v.caja_seguir.get("1.0", "end").strip() == "",
              v.caja_seguir.get("1.0", "end"))

    # Y UNA CONSULTA NUEVA EMPIEZA POR LA VUELTA 1. Esto se prueba con el
    # `_lanzar` DE VERDAD -el doblado de arriba se salta justo la linea que
    # reinicia la cuenta-, mirando lo que se llevaria el boton de copiar.
    del v._lanzar                      # vuelve el metodo de la clase
    v.vuelta = 4
    v.hilo_viene_de = ""
    v.caja.delete("1.0", "end")
    v.caja.insert("1.0", "una duda nueva que no viene de nada")
    v.ejercicio.set("2023")
    v.motor = None                     # que no llegue a lanzar el hilo de fondo
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            v._lanzar(False)
    except Exception:
        pass
    comprobar("UNA CONSULTA NUEVA vuelve a la vuelta 1, no hereda la cuenta",
              v.vuelta == 1, v.vuelta)
    v.trabajando = False

    # SIN NADA ESCRITO NO PASA NADA: pulsar por error no lanza una consulta.
    lanzado.clear()
    v._seguir()
    comprobar("con la caja de añadir vacia, el boton no hace nada", not lanzado)
finally:
    raiz.destroy()


print("\n" + "=" * 74)
if fallos:
    print(f"{len(fallos)} FALLO(S):")
    for f in fallos:
        print(f"   - {f}")
    sys.exit(1)
print("TODO EN VERDE · se puede seguir hablando, y no se ha aflojado nada")
sys.exit(0)
