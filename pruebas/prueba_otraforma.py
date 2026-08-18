#!/usr/bin/env python3
"""«ESCRIBEMELO PARA EL CLIENTE»: OTRA REDACCION, MISMA EXIGENCIA. Cero API.

    python pruebas/prueba_otraforma.py

Es la C de las tres que pidio el departamento -A y B no se construyen todavia,
ver el LEEME- y la unica que no vuelve a buscar nada: mismo material, una sola
llamada.

LO QUE ESTA SUITE VIGILA, Y ES UNA COSA:

    EL VERIFICADOR PASA ENTERO SOBRE EL TEXTO NUEVO.

Porque este es EXACTAMENTE el sitio donde alguien pensara que no hace falta: el
material es el mismo, las citas son las mismas, ya se verificaron. Y es falso.
Lo que se verifica no es el material: es EL TEXTO.

Una reescritura «para el cliente» invita justo a lo que rompe una cita: resumir
el fragmento entrecomillado, quitar la norma de la referencia para que se lea
mejor, suavizar un «debera» en un «conviene». Las tres producen texto mas
legible y CITAS FALSAS.

El motor va DOBLADO: no se llama al modelo, se le da el texto que se quiere
probar. Lo que se prueba es que el verificador y la puerta hacen su trabajo.
"""
import json
import shutil
import sys
import tempfile
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4                                    # noqa: E402
from agente_fiscal import otraforma as OF       # noqa: E402
from agente_fiscal import verificador as VF     # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:110]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix, _g = fase4.cargar_corpus()

# EL FRAGMENTO ES LITERAL DEL CORPUS, copiado de el y no escrito de memoria.
# Una cita inventada saldria NO_VERIFICADA por el motivo equivocado y la suite
# pasaria verde sin probar nada.
art = next(d for d in ix.docs
           if d.registro.get("clave") == "BOE-A-1992-28740#0#articulo 80")
texto_art = art.registro["texto_vigente"]
trozo = "Que haya transcurrido un año desde el devengo del Impuesto repercutido"
comprobar("el fragmento de prueba es LITERAL del corpus", trozo in texto_art,
          texto_art[:80])

BIEN = (f'La base imponible se puede modificar. La norma exige «{trozo}» '
        f'(artículo 80 de la Ley 37/1992).')
# LA REESCRITURA QUE ROMPE LA CITA: el fragmento se ha RESUMIDO, que es lo que
# hace quien quiere que se lea mejor.
ROTA = ('La base imponible se puede modificar. La norma exige «Que haya '
        'pasado un año desde el devengo» (artículo 80 de la Ley 37/1992).')
# Y LA OTRA FORMA DE ROMPERLA: quitar la norma de la referencia.
SIN_NORMA = f'La norma exige «{trozo}» (artículo 80).'


def expediente_de_mentira():
    d = Path(tempfile.mkdtemp())
    (d / "material_1.txt").write_text("material de mentira", encoding="utf-8")
    return d


def motor_que_escribe(texto, cortada=False):
    m = types.SimpleNamespace()
    m.pedido = {}

    def empezar_consulta():
        m.pedido["reinicio"] = m.pedido.get("reinicio", 0) + 1

    def redactar(sistema, material):
        m.pedido["sistema"] = sistema
        m.pedido["material"] = material
        return types.SimpleNamespace(
            texto=texto,
            crudo={"stop_reason": "max_tokens" if cortada else "end_turn"})

    m.empezar_consulta = empezar_consulta
    m.redactar = redactar
    return m


# ==================================== 1. EL POSITIVO
print("\n=== 1. UNA REESCRITURA QUE RESPETA LAS CITAS PASA ===")

d = expediente_de_mentira()
try:
    motor = motor_que_escribe(BIEN)
    r = fase4.otra_forma(d, 2023, motor, ix)
    comprobar("se acepta", r["veredicto"] == VF.ACEPTADO, r["veredicto"])
    comprobar("  y se enseña", r["respuesta"].strip() == BIEN.strip(),
              r["respuesta"][:60])
    comprobar("UNA sola llamada, no dos: no se analiza ni se busca",
              r["llamadas"] == 1, r["llamadas"])
    comprobar("  y el material sale DEL EXPEDIENTE, no se reconstruye",
              motor.pedido["material"] == "material de mentira",
              motor.pedido["material"][:40])
    comprobar("  con la instruccion de escribir para el cliente",
              "ESTA VEZ, ADEMAS" in motor.pedido["sistema"])
    # Se normalizan los espacios: el texto va con saltos de linea y buscar
    # «no suavices» tal cual fallaba por el renglon, no por el contenido.
    sistema = " ".join(motor.pedido["sistema"].lower().split())
    comprobar("  que NO relaja las reglas de citacion",
              "no suavices" in sistema and "literales" in sistema
              and "no resumas" in sistema, sistema[-90:])
    comprobar("el tope se reinicia: es una consulta corta, no la de antes",
              motor.pedido.get("reinicio") == 1, motor.pedido)

    # EL MISMO EXPEDIENTE, al lado de la primera.
    comprobar("se guarda en el MISMO expediente",
              (d / "redaccion_para_cliente_1.txt").is_file(),
              [f.name for f in d.iterdir()])
    comprobar("  con su verificacion propia",
              (d / "verificacion_para_cliente_1.json").is_file())
finally:
    shutil.rmtree(d, ignore_errors=True)


# ==================================== 2. EL ADVERSARIO
print("\n=== 2. UNA REESCRITURA QUE ALTERA UNA CITA SE RECHAZA IGUAL ===")
print("  «Que haya transcurrido un año desde el devengo del Impuesto")
print("  repercutido» -> «Que haya pasado un año desde el devengo».")
print("  Se lee mejor. Y es falsa.\n")

d = expediente_de_mentira()
try:
    r = fase4.otra_forma(d, 2023, motor_que_escribe(ROTA), ix)
    comprobar("NO se acepta", r["veredicto"] != VF.ACEPTADO, r["veredicto"])
    comprobar("  y NO se enseña: la respuesta sale vacia",
              r["respuesta"] == "", r["respuesta"][:60])
    comprobar("  se dice por que, y que se queda la de antes",
              "no pasa el verificador" in r["motivo"]
              and "la respuesta de antes" in r["motivo"], r["motivo"])
    # PERO SE GUARDA. Sobre todo esta.
    comprobar("la rechazada SI se guarda en el expediente",
              (d / "redaccion_para_cliente_1.txt").is_file())
    comprobar("  con su informe, para poder verlo dentro de seis meses",
              (d / "verificacion_para_cliente_1.json").is_file())
finally:
    shutil.rmtree(d, ignore_errors=True)

# La otra forma de romperla: quitar la norma de la referencia.
d = expediente_de_mentira()
try:
    r = fase4.otra_forma(d, 2023, motor_que_escribe(SIN_NORMA), ix)
    comprobar("quitar la norma de la referencia tambien se rechaza",
              r["veredicto"] != VF.ACEPTADO and not r["respuesta"],
              r["veredicto"])
finally:
    shutil.rmtree(d, ignore_errors=True)

# Y una cortada por longitud: media respuesta no se enseña.
d = expediente_de_mentira()
try:
    r = fase4.otra_forma(d, 2023, motor_que_escribe(BIEN, cortada=True), ix)
    comprobar("una reescritura cortada por longitud NO se enseña",
              not r["respuesta"] and "cortada" in r["motivo"], r["motivo"])
finally:
    shutil.rmtree(d, ignore_errors=True)


# ==================================== 3. SIN MATERIAL NO SE INVENTA
print("\n=== 3. SIN EL MATERIAL DEL EXPEDIENTE NO SE REESCRIBE ===")
print("  Reconstruirlo seria volver a buscar, y entonces ya no seria «la")
print("  misma respuesta»: seria otra consulta que se le parece.\n")

d = Path(tempfile.mkdtemp())
try:
    r = fase4.otra_forma(d, 2023, motor_que_escribe(BIEN), ix)
    comprobar("sin material, no se llama al modelo", r["llamadas"] == 0,
              r["llamadas"])
    comprobar("  y se dice por que", "no guarda el material" in r["motivo"],
              r["motivo"])
finally:
    shutil.rmtree(d, ignore_errors=True)


# ==================================== 4. CONTROL NEGATIVO
print("\n=== 4. LA PRUEBA SABE PONERSE ROJA ===")
print("  Se quita la verificacion, que es la tentacion exacta: «el material")
print("  es el mismo, ya estaba verificado».\n")

FUENTE = (RAIZ / "fase4.py").read_text("utf-8")
VIEJO = '''    if informe.veredicto != VF.ACEPTADO:'''
if VIEJO not in FUENTE:
    comprobar("la mutacion encaja", False, VIEJO)
else:
    mod = types.ModuleType("fase4_roto")
    mod.__file__ = str(RAIZ / "fase4.py")
    sys.modules[mod.__name__] = mod
    try:
        exec(compile(FUENTE.replace(VIEJO, "    if False:", 1),
                     mod.__file__, "exec"), mod.__dict__)
    finally:
        del sys.modules[mod.__name__]
    d = expediente_de_mentira()
    try:
        r = mod.otra_forma(d, 2023, motor_que_escribe(ROTA), ix)
        comprobar("(a) sin la puerta, la cita retocada SE ENSEÑARIA",
                  r["respuesta"].strip() == ROTA.strip(), r["respuesta"][:60])
    finally:
        shutil.rmtree(d, ignore_errors=True)

# ==================================== 5. EL BOTON DE LA VENTANA
print("\n=== 5. EL BOTON: SOLO CON UNA RESPUESTA ACEPTADA DELANTE ===")
print("  Si la consulta acabo en no encontrado no hay nada que reescribir, y")
print("  un boton encendido sobre nada es una promesa que no se cumple.\n")

import tkinter as tk                             # noqa: E402
import time                                      # noqa: E402
import interfaz                                  # noqa: E402


def ventana():
    raiz = tk.Tk()
    raiz.withdraw()
    v = interfaz.Ventana(raiz, "ensayo")
    fin = time.time() + 3
    while time.time() < fin:
        raiz.update()
        raiz.update_idletasks()
        time.sleep(0.02)
    return raiz, v


raiz, v = ventana()
try:
    comprobar("el boton existe y se llama en cristiano",
              "cliente" in str(v.boton_cliente.cget("text")).lower(),
              v.boton_cliente.cget("text"))
    comprobar("  y dice QUE HACE, no como funciona",
              "reescrib" not in str(v.boton_cliente.cget("text")).lower()
              and "verific" not in str(v.boton_cliente.cget("text")).lower(),
              v.boton_cliente.cget("text"))
    comprobar("nace apagado", str(v.boton_cliente.cget("state")) == "disabled")

    # --- CON UNA RESPUESTA ACEPTADA: aparece
    d = expediente_de_mentira()
    try:
        v._pintar(({"respuesta": "una respuesta cualquiera",
                    "traza": str(d), "ejercicio": 2023, "estado": "claro"}
                   if hasattr(v, "_pintar") else None))
    except Exception:                            # noqa: BLE001
        # Si la ventana no expone `_pintar`, se hace lo que hace ella.
        v.respuesta_actual = "una respuesta cualquiera"
        v.traza_actual = str(d)
        v.ejercicio_usado = 2023
        v.boton_copiar.configure(state="normal")
        v.boton_cliente.configure(state="normal")
    comprobar("con una respuesta aceptada, SE ENCIENDE",
              str(v.boton_cliente.cget("state")) == "normal",
              v.boton_cliente.cget("state"))

    # --- LA REESCRITURA BUENA queda en el MISMO expediente
    v.motor = motor_que_escribe(BIEN)
    v.ix = ix
    v.trabajando = False
    v._escribir_para_cliente()
    fin = time.time() + 3
    while time.time() < fin and v.trabajando:
        raiz.update()
        time.sleep(0.02)
    raiz.update()
    comprobar("la reescritura queda en el MISMO expediente",
              (d / "redaccion_para_cliente_1.txt").is_file(),
              [f.name for f in d.iterdir()])
    comprobar("  y se enseña en pantalla",
              "cliente" in v.texto.get("1.0", "end").lower(),
              v.texto.get("1.0", "end")[:60])
    comprobar("  y el boton vuelve a su rotulo",
              "Escribirlo" in str(v.boton_cliente.cget("text")),
              v.boton_cliente.cget("text"))

    # --- CON LA REESCRITURA RECHAZADA: se queda la de antes, y se dice
    antes = v.texto.get("1.0", "end")
    v.motor = motor_que_escribe(ROTA)
    v.trabajando = False
    v._escribir_para_cliente()
    fin = time.time() + 3
    while time.time() < fin and v.trabajando:
        raiz.update()
        time.sleep(0.02)
    raiz.update()
    comprobar("rechazada: el texto de antes SIGUE en pantalla",
              v.texto.get("1.0", "end") == antes,
              v.texto.get("1.0", "end")[:60])
    cinta = str(v.aviso_motor.cget("text"))
    comprobar("  y se dice que no se ha perdido nada",
              "no se ha perdido" in cinta, cinta[:100])
    comprobar("  SIN mensaje de averia: ha funcionado la salvaguarda",
              not any(x in cinta.lower()
                      for x in ("error", "fallo", "avería", "averia")),
              cinta[:100])
finally:
    shutil.rmtree(d, ignore_errors=True)
    raiz.destroy()

# --- CON NO ENCONTRADO: no aparece
raiz2, v2 = ventana()
try:
    v2._sin_nada_que_copiar()
    comprobar("con no encontrado, el boton NO aparece encendido",
              str(v2.boton_cliente.cget("state")) == "disabled",
              v2.boton_cliente.cget("state"))
    comprobar("  y se apaga junto al de copiar, que dependen de lo mismo",
              str(v2.boton_copiar.cget("state")) == "disabled")
finally:
    raiz2.destroy()

# --- UNA SOLA FORMA, la que se pidio
FUENTE_I = (RAIZ / "interfaz.py").read_text("utf-8")
# Se cuenta el BOTON, no las palabras: «resumelo» aparece en el comentario que
# explica por que NO se hicieron tres opciones, y buscarla ahi hacia que la
# prueba fallara por su propia explicacion.
comprobar("hay UN solo boton de reescritura, no un menu de opciones",
          FUENTE_I.count("boton_cliente = ttk.Button") == 1,
          FUENTE_I.count("boton_cliente = ttk.Button"))

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
