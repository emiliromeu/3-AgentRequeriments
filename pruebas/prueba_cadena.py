#!/usr/bin/env python3
"""LA CADENA TERMINA POR TRABAJO, NO POR CUENTA. Cero red, cero API.

    python pruebas/prueba_cadena.py

EL DEFECTO QUE LA JUSTIFICA. El 13/08 la cadena iba a hacer cuatro tandas mas
-unas 2.200 peticiones a un servicio publico- para bajar CERO consultas. No era
mala suerte: la tanda 1 bajo 140 con tope 300, o sea que no llego al tope y no
quedaba cola. El trabajo estaba hecho desde ahi, pero la cadena solo sabia
terminar cuando se acababan las TANDAS. Hubo que cortarla a mano.

LA TENTACION ERA BAJAR EL 7 A UN 3. Habria funcionado ese dia y habria vuelto a
fallar al siguiente, porque el 7 nunca fue el problema.

LOS TRES CODIGOS, Y POR QUE SON TRES:

    0  tanda correcta          -> la cadena sigue
    1  algo bajado no se halla -> la cadena PARA (averia)
    2  plan agotado            -> la cadena TERMINA BIEN

Que el 2 sea propio y no un 0 es el punto entero: 0 significa «sigue» y 1
significa «algo va mal». «Ya esta» no es ninguna de las dos.

TAXONOMIA: dobles. `informe_de_tanda` se llama con listas construidas aqui, y
el guion de la cadena se prueba con un `sembrar.py` de mentira que devuelve el
codigo que se le pida. Nada de red, nada de despensa.
"""
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import sembrar                                  # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:104]}" if not ok else ""))
    if not ok:
        fallos.append(que)


# ==================================== 1. EL CODIGO DE «YA ESTA»
print("\n=== 1. UNA TANDA VACIA ES «PLAN AGOTADO», NO «TODO BIEN» ===")

comprobar("PLAN_AGOTADO existe y no se confunde con 0 ni con 1",
          sembrar.PLAN_AGOTADO not in (0, 1), sembrar.PLAN_AGOTADO)
comprobar("una tanda que no bajo nada devuelve PLAN_AGOTADO",
          sembrar.informe_de_tanda([]) == sembrar.PLAN_AGOTADO,
          sembrar.informe_de_tanda([]))

# Y CON ALGO BAJADO NO SE AGOTA. Se usan numeros que no estan en la despensa a
# proposito: lo que se prueba es que la rama del «nada nuevo» NO se toma, no
# cuantas consultas hay guardadas.
comprobar("con algo bajado NO dice plan agotado",
          sembrar.informe_de_tanda(["V0002-21"]) != sembrar.PLAN_AGOTADO,
          sembrar.informe_de_tanda(["V0002-21"]))

# ==================================== 2. LA CADENA OBEDECE AL CODIGO
print("\n=== 2. EL GUION DE LA CADENA HACE CASO ===")
print("  Se le pone un `sembrar.py` de mentira que devuelve lo que se le")
print("  pida, y se mira cuantas tandas llega a hacer.\n")

GUION = (RAIZ / "cadena_siembra.sh").read_text("utf-8")


def cadena_con(codigo: int, tandas: int = 4) -> tuple:
    """Corre el guion DE VERDAD con un sembrar.py falso. Devuelve (salida, n)."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "datos" / "siembra").mkdir(parents=True)
        (d / ".venv" / "bin").mkdir(parents=True)
        # El «python» falso: cuenta la llamada y devuelve el codigo pedido.
        py = d / ".venv" / "bin" / "python"
        py.write_text(f'#!/bin/bash\necho x >> "{d}/veces"\nexit {codigo}\n')
        py.chmod(py.stat().st_mode | stat.S_IEXEC)
        (d / "sembrar.py").write_text("")
        guion = d / "cadena_siembra.sh"
        # EL GUION ES EL DE VERDAD, sin tocar: si cambia, esto se entera.
        guion.write_text(GUION.replace("sleep 300", "sleep 0"))
        guion.chmod(guion.stat().st_mode | stat.S_IEXEC)
        r = subprocess.run(["bash", str(guion), "2", str(tandas)],
                           capture_output=True, text=True, cwd=str(d))
        veces = (d / "veces").read_text().count("x") if (d / "veces").is_file() else 0
        log = (d / "datos" / "siembra" / "tandas.log")
        return r.returncode, veces, (log.read_text() if log.is_file() else "")


sal, veces, log = cadena_con(sembrar.PLAN_AGOTADO, tandas=4)
comprobar("con PLAN AGOTADO hace UNA sola tanda de las 4", veces == 1, veces)
comprobar("  y termina BIEN, no como averia", sal == 0, sal)
comprobar("  y lo dice en el log", "PLAN AGOTADO" in log, log[-160:])

sal, veces, log = cadena_con(0, tandas=4)
comprobar("con 0 hace las 4 tandas", veces == 4, veces)
comprobar("  y acaba diciendo TODO TERMINADO", "TODO TERMINADO" in log,
          log[-160:])

sal, veces, log = cadena_con(1, tandas=4)
comprobar("con 1 -averia- para en la primera", veces == 1, veces)
comprobar("  y sale con error, que es lo que la distingue del agotado",
          sal != 0, sal)
comprobar("  y lo dice como PARADA, no como agotado",
          "PARADA EN LA TANDA" in log and "PLAN AGOTADO" not in log, log[-160:])

# ==================================== 3. CONTROL NEGATIVO
print("\n=== 3. LA PRUEBA SABE PONERSE ROJA ===")
print("  Se rompe el guion de verdad: se quita la rama del plan agotado y se")
print("  mira si el bloque 2 lo caza.\n")

VIEJO = "  if [ $codigo -eq 2 ]; then"
if VIEJO not in GUION:
    comprobar("la mutacion encaja en el guion", False, VIEJO)
else:
    roto = GUION.replace(VIEJO, "  if [ $codigo -eq 99 ]; then", 1)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "datos" / "siembra").mkdir(parents=True)
        (d / ".venv" / "bin").mkdir(parents=True)
        py = d / ".venv" / "bin" / "python"
        py.write_text(f'#!/bin/bash\necho x >> "{d}/veces"\nexit 2\n')
        py.chmod(py.stat().st_mode | stat.S_IEXEC)
        (d / "sembrar.py").write_text("")
        g = d / "c.sh"
        g.write_text(roto.replace("sleep 300", "sleep 0"))
        g.chmod(g.stat().st_mode | stat.S_IEXEC)
        subprocess.run(["bash", str(g), "2", "4"], capture_output=True,
                       text=True, cwd=str(d))
        veces = (d / "veces").read_text().count("x")
    # Sin la rama, el 2 cae en «codigo distinto de 0» y se lee como AVERIA:
    # la cadena para igual, pero mintiendo. Lo que el bloque 2 caza es que ya
    # no dice PLAN AGOTADO ni sale con 0.
    comprobar("(a) sin la rama del 2, el plan agotado se lee como averia",
              veces == 1, veces)

# Y el otro lado: que el 2 se tratara como «sigue» seria peor todavia, porque
# haria las cuatro tandas vacias que originaron todo esto.
roto2 = GUION.replace("  if [ $codigo -eq 2 ]; then\n", "  if false; then\n", 1)
roto2 = roto2.replace("if [ $codigo -ne 0 ]; then", "if false; then", 1)
with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp)
    (d / "datos" / "siembra").mkdir(parents=True)
    (d / ".venv" / "bin").mkdir(parents=True)
    py = d / ".venv" / "bin" / "python"
    py.write_text(f'#!/bin/bash\necho x >> "{d}/veces"\nexit 2\n')
    py.chmod(py.stat().st_mode | stat.S_IEXEC)
    (d / "sembrar.py").write_text("")
    g = d / "c.sh"
    g.write_text(roto2.replace("sleep 300", "sleep 0"))
    g.chmod(g.stat().st_mode | stat.S_IEXEC)
    subprocess.run(["bash", str(g), "2", "4"], capture_output=True, text=True,
                   cwd=str(d))
    veces = (d / "veces").read_text().count("x")
comprobar("(b) si el agotado se leyera como «sigue», volverian las 4 tandas "
          "vacias", veces == 4, veces)

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
