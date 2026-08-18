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

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
