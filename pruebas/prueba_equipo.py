#!/usr/bin/env python3
"""LA FICHA QUE SE MANDA CUANDO ALGO FALLA EN LA OFICINA. Cero red, cero API.

    python pruebas/prueba_equipo.py

Cuando en el despacho algo no va, lo que llega aqui es la salida de
`comprobar_equipo.ficha()`. Si esa ficha no dice lo que hace falta, el
diagnostico empieza con una conversacion de ida y vuelta que puede durar dias
—y quien la manda esta bloqueado mientras tanto—.

VIVIA DENTRO DE `prueba_boton`, Y NO ERA SU SITIO. Estaba ahi porque cuando se
escribio era el fichero que habia abierto: `prueba_boton` es de la VENTANA y
esto es de OTRO PROGRAMA, uno de consola. Al disolver aquella suite —ver LEEME
fase 43— estas tres comprobaciones se quedaban sin casa, y perderlas habria
dejado sin vigilar lo unico que se manda cuando algo falla alli.

CERO VENTANAS. Es la otra mitad de por que se separa: `prueba_boton` abria
CINCO ventanas Tk y esto no necesita ninguna. Una comprobacion de consola
metida en una suite de ventana paga el precio de la ventana sin usarla, y las
ventanas son la causa de las rojas intermitentes por robo de foco.

LA QUE MAS IMPORTA de las tres es la ultima: LA FICHA NO PUEDE GASTAR. Se
ejecuta cuando algo va mal, y a veces lo que va mal ES el saldo. Una ficha de
diagnostico que consume una llamada al modelo para comprobar que la credencial
vale puede ser justo lo que agote lo que quedaba.
"""
import contextlib
import io
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import comprobar_equipo as CE  # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:104]}" if not ok else ""))
    if not ok:
        fallos.append(que)


print("\n=== LA FICHA DICE POR QUE, SIN QUE HAYA QUE PREGUNTAR ===")
print("  Es lo que llega desde la oficina cuando algo no va.\n")

salida = io.StringIO()
with contextlib.redirect_stdout(salida):
    CE.ficha()
f = salida.getvalue()

for que, marca in (("el commit del equipo", "version"),
                   ("cuantas normas tiene", "normas"),
                   ("si los sellos cuadran", "sellos"),
                   ("si la credencial vale", "credencial"),
                   ("y POR QUE esta el boton apagado", "BOTON")):
    comprobar(f"la ficha dice {que}", marca in f, f[:80])
comprobar("avisa si el pull se quedo a medias",
          "sin guardar" in f or "version" in f)
comprobar("y NO gasta: la credencial se mira, no se usa",
          "NO se usa" in f)

# =====================================================================
print("\n=== CONTROL NEGATIVO: ¿SABE PONERSE ROJA? ===")
print("  Una ficha que no dice nada tendria que caerse aqui.\n")

vacia = ""
comprobar("con una ficha vacia, las cinco de arriba se pondrian rojas",
          not any(m in vacia for m in ("version", "normas", "sellos",
                                       "credencial", "BOTON")))
# Y LA DE NO GASTAR, QUE ES LA QUE IMPORTA: si alguien quitara la frase que
# promete que la credencial no se usa, esta suite tiene que notarlo. Se
# comprueba contra una ficha de mentira que dice lo contrario.
gastona = f.replace("NO se usa", "se usa una llamada para comprobarla")
comprobar("si la ficha dejara de prometer que no gasta, se cazaria",
          "NO se usa" not in gastona)

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for x in fallos:
    print("  -", x)
sys.exit(1 if fallos else 0)
