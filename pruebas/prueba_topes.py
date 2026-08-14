#!/usr/bin/env python3
"""EL TECHO DURO SE CUENTA POR CONSULTA. Cero red, cero API.

    python pruebas/prueba_topes.py

EL DEFECTO QUE LA JUSTIFICA, y es el peor de los que han salido: EL AGENTE
DEJABA DE RESPONDER A MITAD DE LA MAÑANA.

La ventana prepara UN motor al abrirse y lo reutiliza para todas las preguntas
del dia. El motor tiene un techo de seis llamadas «por consulta»... pero el
contador no se reiniciaba entre consultas. Con dos o tres llamadas por
pregunta, a partir de la tercera el agente contestaba:

    Se ha alcanzado el tope de 6 llamadas al modelo EN ESTA CONSULTA

diciendo «esta consulta» cuando eran todas las anteriores juntas. Y no se
recuperaba: quedaba asi hasta cerrar y volver a abrir el agente.

POR QUE NO SE HABIA VISTO. Hacen falta varias preguntas seguidas en la misma
sesion para llegar. O sea que no aparece en una prueba de dos consultas:
aparece un dia de trabajo de verdad, con el cliente delante.

Y SE ENCONTRO SIN GASTAR NADA, mirando por que el bloque 5 -quince llamadas con
un solo motor- iba a chocar con un tope de seis. La misma cuerda.

LO QUE SE REINICIA Y LO QUE NO. El reloj y el contador de llamadas son de la
consulta. `consumo` -los tokens- es de la sesion entera: de ahi salen los
totales del banco y de la traza, y reiniciarlo seria perder la cuenta del
gasto.
"""
import io
import contextlib
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4                                    # noqa: E402
from agente_fiscal import modelo as MOD         # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:112]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix, grafo = fase4.cargar_corpus()

# ==================================== 1. UNA JORNADA ENTERA
print("\n=== 1. DOCE PREGUNTAS SEGUIDAS CON EL MISMO MOTOR ===")
print("  Es lo que hace la ventana: un motor al abrir, y a trabajar.")
print(f"  El tope es de {MOD.TOPE_LLAMADAS} llamadas POR CONSULTA.\n")

motor, _err = fase4.preparar_motor("ensayo", silencioso=True)
sin_respuesta = []
for i in range(1, 13):
    with contextlib.redirect_stdout(io.StringIO()) as s:
        fase4.consultar("que tipo de IVA lleva la reforma de una vivienda",
                        2024, motor, ix, grafo)
    if "PARADA POR TOPE" in s.getvalue():
        sin_respuesta.append(i)

print(f"    llamadas de la ultima consulta : {motor.llamadas}")
print(f"    llamadas de toda la sesion     : {len(motor.consumo)}")
comprobar("las doce contestan", not sin_respuesta,
          f"sin respuesta: {sin_respuesta}")
comprobar("el contador de la consulta NO arrastra las anteriores",
          motor.llamadas <= MOD.TOPE_LLAMADAS, motor.llamadas)
comprobar("y aun asi se han hecho mas llamadas que el tope: la sesion suma "
          "aunque la consulta se reinicie",
          len(motor.consumo) > MOD.TOPE_LLAMADAS, len(motor.consumo))

# ==================================== 2. EL TOPE SIGUE PROTEGIENDO
print("\n=== 2. PERO EL TECHO SIGUE AHI, QUE ES PARA LO QUE ESTA ===")
print("  Reiniciar por consulta no puede convertirse en no tener tope: lo que")
print("  se quiere impedir es un bucle DENTRO de una consulta.\n")

m = MOD.Motor.__new__(MOD.Motor)
MOD.Motor.__init__(m, tope_llamadas=3)
m.empezar_consulta()
salto = None
for i in range(1, 6):
    try:
        m._permiso("analisis")
        m.llamadas += 1
    except MOD.TopeAlcanzado:
        salto = i
        break
comprobar("dentro de UNA consulta el tope salta", salto == 4, salto)
comprobar("  y dice por que se paro", "tope" in m.motivo_parada,
          m.motivo_parada)
m.empezar_consulta()
try:
    m._permiso("analisis")
    comprobar("  y en la consulta siguiente vuelve a haber permiso", True)
except MOD.TopeAlcanzado:
    comprobar("  y en la consulta siguiente vuelve a haber permiso", False,
              "sigue bloqueado")

# ==================================== 3. EL BANCO, POR SU CAMINO
print("\n=== 3. LOS BLOQUES QUE LLAMAN AL MOTOR A PELO TAMBIEN REINICIAN ===")
print("  El bloque 5 hace quince llamadas con un solo motor sin pasar por")
print("  `consultar`. Sin reiniciar, del septimo rojo en adelante habrian")
print("  salido como «fallo de llamada al modelo» sin serlo. Y pagados.\n")

BANCO = (RAIZ / "banco.py").read_text("utf-8")
comprobar("el bloque 5 empieza consulta en cada rojo",
          BANCO.count("motor.empezar_consulta()") >= 1)
comprobar("y el comparador de analizadores tambien",
          BANCO.count("motor.empezar_consulta()") >= 2,
          BANCO.count("motor.empezar_consulta()"))
comprobar("los totales de la pasada salen de `consumo`, no de `llamadas`: "
          "si no, contarian solo la ultima consulta",
          "len(motor.consumo)" in BANCO and
          "motor.llamadas if motor.es_modelo_real" not in BANCO)

# ==================================== 4. CONTROL NEGATIVO
print("\n=== 4. LA PRUEBA SABE PONERSE ROJA ===")
print("  Se deja de reiniciar el contador, que es como estaba, y se mira si")
print("  el bloque 1 lo caza.\n")

import types                                     # noqa: E402

FUENTE = (RAIZ / "agente_fiscal" / "modelo.py").read_text("utf-8")
VIEJO = "        self.arranque = time.monotonic()\n        self.llamadas = 0"
if VIEJO not in FUENTE:
    comprobar("la mutacion encaja", False, VIEJO[:60])
else:
    mod = types.ModuleType("modelo_roto")
    mod.__package__ = "agente_fiscal"
    mod.__file__ = str(RAIZ / "agente_fiscal" / "modelo.py")
    sys.modules[mod.__name__] = mod
    try:
        exec(compile(FUENTE.replace(
            VIEJO, "        self.arranque = time.monotonic()", 1),
            mod.__file__, "exec"), mod.__dict__)
    finally:
        del sys.modules[mod.__name__]

    r = mod.Motor.__new__(mod.Motor)
    mod.Motor.__init__(r, tope_llamadas=6)
    caidas = []
    for i in range(1, 6):                        # cinco «consultas» de 2
        r.empezar_consulta()
        for _ in range(2):
            try:
                r._permiso("analisis")
                r.llamadas += 1
            except mod.TopeAlcanzado:
                caidas.append(i)
                break
    comprobar("(a) sin reiniciar, la sesion se muere a la cuarta consulta: es "
              "el defecto original y el bloque 1 lo caza",
              bool(caidas), f"cayeron en {caidas}")
    print(f"       (dejo de responder en la consulta {caidas[0] if caidas else '-'})")

# (b) sin mutar, no cae ninguna
b = MOD.Motor.__new__(MOD.Motor)
MOD.Motor.__init__(b, tope_llamadas=6)
ok_todas = True
for _ in range(5):
    b.empezar_consulta()
    for _ in range(2):
        try:
            b._permiso("analisis")
            b.llamadas += 1
        except MOD.TopeAlcanzado:
            ok_todas = False
comprobar("(b) sin mutar, las cinco consultas pasan", ok_todas)

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
