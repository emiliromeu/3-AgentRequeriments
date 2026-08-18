#!/usr/bin/env python3
"""LA MEDICION DEL USO SE PUEDE MANDAR SIN MANDAR NADA DE NADIE. Cero red, API.

    python pruebas/prueba_uso.py

POR QUE EXISTE `medir_uso`. Las decisiones sobre que sembrar se estaban tomando
con los numeros del Mac del despacho, donde casi todo son pruebas de IVA. Las
consultas de verdad pasan en el PC de la oficina y ESAS TRAZAS NO VIAJAN: son
dudas de clientes y se quedan donde se hicieron. Asi que la medicion tiene que
poder ejecutarse alli y traerse SOLO LOS NUMEROS.

LO QUE ESTA SUITE VIGILA, Y ES UNA COSA:

    QUE NO SE ESCAPE NI UNA PREGUNTA.

Lo que se copia y se manda por un canal cualquiera -un correo, un WhatsApp- no
puede llevar la duda de un cliente. Se cuentan articulos de la ley, que son
referencias publicas; no lo que preguntaron.

Se comprueba SEMBRANDO UNA PREGUNTA RECONOCIBLE en una traza de mentira y
mirando que no sale por ningun sitio.
"""
import io
import contextlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:110]}" if not ok else ""))
    if not ok:
        fallos.append(que)


# La frase va con datos que se reconocen a la legua: si aparece uno solo de
# estos trozos en la salida, es que se esta filtrando la duda.
SECRETO = ("Mi cliente PEPITO PEREZ, NIF 12345678Z, se ha vendido el piso de "
           "la calle Mayor por 340.000 euros")


def traza_de_mentira(base: Path, nombre: str) -> None:
    d = base / nombre
    d.mkdir(parents=True)
    (d / "pregunta.txt").write_text(SECRETO, encoding="utf-8")
    (d / "consumo.json").write_text(
        json.dumps({"por_modelo": {"claude-opus-5": {"llamadas": 2}}}),
        encoding="utf-8")
    (d / "seleccion.json").write_text(json.dumps({"preceptos": [
        {"referencia": "Articulo 80", "decision": "enviado",
         "clave": "BOE-A-1992-28740#0#articulo 80"},
        {"referencia": "Articulo 9999", "decision": "enviado",
         "clave": "BOE-A-1992-28740#0#articulo 9999"},
    ]}), encoding="utf-8")
    (d / "resultado.json").write_text(
        json.dumps({"pregunta": SECRETO}), encoding="utf-8")


# ==================================== 1. NI UNA PREGUNTA
print("\n=== 1. LA SALIDA NO LLEVA NI UNA PREGUNTA ===")
print("  Se siembra una duda con nombre, NIF e importe en una traza de")
print("  mentira, y se mira que no sale por ningun sitio.\n")

import medir_uso                                 # noqa: E402

tmp = Path(tempfile.mkdtemp())
original = medir_uso.RAIZ
try:
    # Se le monta un equipo de mentira con SU traza dentro.
    (tmp / "datos").mkdir()
    shutil.copytree(RAIZ / "datos" / "corpus", tmp / "datos" / "corpus")
    traza_de_mentira(tmp / "datos" / "trazas", "20260818T101010")
    medir_uso.RAIZ = tmp

    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        medir_uso.main()
    texto = salida.getvalue()

    for trozo in ("PEPITO", "PEREZ", "12345678Z", "calle Mayor", "340.000",
                  "vendido"):
        comprobar(f"«{trozo}» NO aparece en la salida", trozo not in texto,
                  [l for l in texto.splitlines() if trozo in l][:1])
    comprobar("y la pregunta entera tampoco", SECRETO not in texto)

    # Y SI LLEVA LO QUE TIENE QUE LLEVAR: las cuentas.
    comprobar("pero SI dice cuantas consultas hay",
              "CONSULTAS HECHAS EN ESTE EQUIPO" in texto)
    comprobar("  y cuantos articulos se pidieron",
              "articulos distintos pedidos" in texto, texto[:60])
    comprobar("  y cuales NO tenian criterio",
              "SIN criterio" in texto)
    comprobar("  y de que impuesto son",
              "LOS QUE FALTAN, por impuesto" in texto)
    comprobar("  y cuantos hay en cola", "LA COLA DE DESCARGA" in texto)
    comprobar("dice al principio QUE lleva y que no",
              "NO LLEVA" in texto and "ni una pregunta" in texto)
finally:
    medir_uso.RAIZ = original
    shutil.rmtree(tmp, ignore_errors=True)


# ==================================== 2. SE PUEDE COPIAR DE UN TIRON
print("\n=== 2. SE PUEDE COPIAR ENTERA ===")
print("  La consola de Windows no siempre va en UTF-8: una tilde mal")
print("  codificada estropea la linea y quien la pega no lo nota.\n")

salida = io.StringIO()
with contextlib.redirect_stdout(salida):
    medir_uso.main()
texto = salida.getvalue()
no_ascii = sorted({c for c in texto if ord(c) > 127})
comprobar("la salida es ASCII: se pega sin estropearse",
          not no_ascii, no_ascii[:8])
comprobar("y dice donde acaba, para saber que se ha copiado todo",
          "Fin." in texto, texto[-80:])


# ==================================== 3. SE PUEDE EJECUTAR ALLI
print("\n=== 3. SE EJECUTA CON DOBLE CLIC, COMO comprobar_equipo ===")

for lanzador in ("medir_uso.bat", "medir_uso.command"):
    f = RAIZ / lanzador
    comprobar(f"existe {lanzador}", f.is_file())
    if f.is_file():
        t = f.read_text(encoding="utf-8", errors="replace")
        comprobar(f"  {lanzador} llama a medir_uso.py", "medir_uso.py" in t)
        comprobar(f"  y no arrastra nada de comprobar_equipo",
                  "comprobar_equipo" not in t)
comprobar("el de Mac es ejecutable",
          (RAIZ / "medir_uso.command").stat().st_mode & 0o111)

# En Windows la consola se cierra sola si no se para: la ventana se quedaria
# en blanco y no habria nada que copiar.
bat = (RAIZ / "medir_uso.bat").read_text(encoding="utf-8", errors="replace")
comprobar("el .bat espera antes de cerrarse, que si no no se lee nada",
          "pause" in bat)
# SE MIRAN LAS ORDENES, NO LOS COMENTARIOS. «pythonw» aparece en el REM que
# explica POR QUE no se usa, y buscarlo a secas hacia que la prueba fallara por
# su propia explicacion. Es la segunda vez que caigo en esto -la primera fue
# «resumelo» en interfaz.py-: al comprobar que algo NO esta, hay que mirar
# donde importa, no en todo el fichero.
ordenes = [l for l in bat.splitlines()
           if l.strip() and not l.strip().upper().startswith("REM")]
comprobar("y usa python.exe, NO pythonw: pythonw no tiene consola",
          not any("pythonw" in l for l in ordenes),
          [l for l in ordenes if "pythonw" in l][:1])

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f_ in fallos:
    print("  -", f_)
sys.exit(1 if fallos else 0)
