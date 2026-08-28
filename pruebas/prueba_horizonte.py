#!/usr/bin/env python3
"""HASTA DONDE LLEGA LA COPIA, Y QUE PASA CUANDO SE PREGUNTA MAS ALLA.

    python pruebas/prueba_horizonte.py

EL FALLO QUE ESTO CIERRA no se parece a una averia. Se pregunta por un
ejercicio POSTERIOR a donde llega el texto consolidado que tenemos, y la
respuesta sale impecable: articulo correcto, norma correcta, enlace correcto,
version fechada. Lo unico que le pasa es que entre esa fecha y el ejercicio del
caso puede haber reformas que esta copia no ha visto nunca. No hay nada roto
que enseñar, y por eso hace falta que lo diga la propia respuesta.

DONDE TIENE QUE IR EL AVISO: DENTRO DEL JSON. Un aviso escrito en el LEEME no
lo lee el programa que consume el JSON, y quien escribio ese programa se fue de
la empresa. Esta suite comprueba que va en la respuesta, y que va en CADA
respuesta del lote y no solo en la cabecera: quien reparte un lote por casos se
lleva cada una por su lado.

Y QUE NO SALTE SIEMPRE, que es la otra mitad. Un aviso que sale en todas las
respuestas se aprende a ignorar en dos dias, y entonces no avisa de nada. Con
un ejercicio que SI cabe dentro del horizonte no tiene que aparecer.

    Horizonte de este corpus, medido: la norma mas atrasada manda.
    Se calcula, no se escribe aqui: si mañana se reingiere y avanza, la suite
    sigue valiendo.
"""
import atexit
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from agente_fiscal import frescura as FR          # noqa: E402

PY_EXE = sys.executable
CORPUS = RAIZ / "datos" / "corpus"

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:140]}" if not ok else ""))
    if not ok:
        fallos.append(que)


def correr(args, entrada=""):
    r = subprocess.run([PY_EXE, str(RAIZ / "corpus_json.py"), *args],
                       input=entrada, text=True, capture_output=True,
                       cwd=str(RAIZ))
    try:
        return r, json.loads(r.stdout)
    except (ValueError, TypeError):
        return r, None


# ==================================== 1. EL HORIZONTE SALE DE LOS SELLOS
print("\n=== 1. HASTA DONDE LLEGA ESTA COPIA ===")
print("  Manda la norma MAS ATRASADA, no la media ni la mas reciente: el")
print("  corpus se usa entero para contestar, asi que llega hasta donde llega")
print("  su eslabon mas corto.\n")

h = FR.horizonte(CORPUS)
print(f"  horizonte: {h['hasta']}  ({h['norma']}), "
      f"ejercicio completo {h['ejercicio_completo']}")

comprobar("hay horizonte y sale de un sello", bool(h["hasta"]), h)
comprobar("  y es el MINIMO de los `consolidado_hasta`",
          h["hasta"] == min(h["por_norma"].values()), h["hasta"])
comprobar("  la norma que lo marca es la que tiene esa fecha",
          h["por_norma"].get(h["norma"]) == h["hasta"], h["norma"])
# EL AÑO NO SE REDONDEA HACIA ARRIBA. Un corpus consolidado el 09/11/2018 no
# cubre 2018: le faltan siete semanas, y una reforma de diciembre es justo la
# que entra en vigor el 1 de enero siguiente.
año = int(h["hasta"][:4])
esperado = año if h["hasta"][5:] >= "12-31" else año - 1
comprobar("  el ejercicio completo NO redondea hacia arriba",
          h["ejercicio_completo"] == esperado,
          f"{h['hasta']} -> {h['ejercicio_completo']}, esperado {esperado}")

DENTRO = h["ejercicio_completo"]
FUERA = h["ejercicio_completo"] + 1
print(f"\n  se probara con {FUERA} (por delante) y con {DENTRO} (dentro)")


# ==================================== 2. LOS BORDES, SIN DEPENDER DEL CORPUS
print("\n=== 2. LOS BORDES DEL CALCULO, CON SELLOS DE MENTIRA ===")
print("  El corpus real solo tiene un horizonte. Los casos que no se pueden")
print("  provocar aqui -el 31 de diciembre justo, una norma sin fecha, ningun")
print("  sello- se montan a mano en un directorio temporal.\n")


# Los corpus de mentira son fixtures de usar y tirar, no un banco de pruebas:
# se borran al salir. Lo que no se puede ir a un temporal es la SUITE, y esta
# vive en el repositorio.
_temporales = []
atexit.register(lambda: [shutil.rmtree(x, ignore_errors=True)
                         for x in _temporales])


def con_sellos(sellos):
    d = Path(tempfile.mkdtemp(prefix="horizonte_"))
    _temporales.append(d)
    if sellos is not None:
        (d / "sellos.json").write_text(json.dumps(sellos), encoding="utf-8")
    return d


def sello(hasta):
    return {"sha256": "x", "bytes": 1, "preceptos": 1, "sellado": "2026-01-01",
            "consolidacion": {"preguntado": "2026-01-01",
                              "consolidado_hasta": hasta,
                              "estado_boe": "", "reformas_pendientes": 0,
                              "preceptos_tocados": [], "reformas": []}}


d = con_sellos({"A": sello("2020-12-31"), "B": sello("2024-06-01")})
hh = FR.horizonte(d)
comprobar("consolidado justo el 31 de diciembre: ese año SI esta cubierto",
          hh["ejercicio_completo"] == 2020 and hh["hasta"] == "2020-12-31", hh)
comprobar("  y un ejercicio de ese mismo año no da aviso",
          FR.aviso_de_horizonte(d, 2020) == "",
          FR.aviso_de_horizonte(d, 2020))
comprobar("  pero el siguiente si", bool(FR.aviso_de_horizonte(d, 2021)))

d2 = con_sellos({"A": sello("2020-12-30"), "B": sello("2024-06-01")})
comprobar("un dia antes, el 30, ese año YA NO esta cubierto",
          FR.horizonte(d2)["ejercicio_completo"] == 2019, FR.horizonte(d2))

# UNA NORMA SIN FECHA NO ES «LLEGA HASTA HOY»: es la que no sabemos, y se
# cuenta aparte para que no desaparezca dentro del minimo.
d3 = con_sellos({"A": sello("2024-06-01"), "B": sello("")})
comprobar("una norma sin fecha se aparta, no se da por buena",
          FR.horizonte(d3)["sin_dato"] == ["B"], FR.horizonte(d3))

# SIN SELLOS NO SE INVENTA UN HORIZONTE, y tampoco se calla: se dice que no se
# sabe. Callarse aqui es lo mismo que decir «llega hasta hoy».
d4 = con_sellos(None)
comprobar("sin fichero de sellos no hay horizonte", FR.horizonte(d4)["hasta"] == "")
comprobar("  y el aviso lo dice, en vez de callarse",
          "No se sabe" in FR.aviso_de_horizonte(d4, 2023),
          FR.aviso_de_horizonte(d4, 2023))
comprobar("  sin ejercicio no hay aviso: no hay nada que comparar",
          FR.aviso_de_horizonte(CORPUS, None) == "")


# ==================================== 3. EL AVISO, DENTRO DEL JSON
print("\n=== 3. UNA FECHA POR DELANTE DEL CORPUS EXIGE EL AVISO ===")
print(f"  Se pregunta por {FUERA}, que cae mas alla de donde llega la copia.\n")

r, d = correr(["buscar", "--ejercicio", str(FUERA), "--tope", "2"],
              "prorrata especial\n")
comprobar("buscar contesta", d is not None and r.returncode == 0, r.stdout[:90])
comprobar("  el horizonte va en la cabecera del JSON",
          (d or {}).get("horizonte", {}).get("hasta") == h["hasta"],
          (d or {}).get("horizonte"))
aviso = (d or {}).get("respuestas", [{}])[0].get("aviso_horizonte", "")
comprobar("  y el aviso va DENTRO de la respuesta", bool(aviso), aviso)
comprobar("  nombrando el ejercicio que se pregunto", str(FUERA) in aviso, aviso)
comprobar("  y hasta donde llega de verdad", h["hasta"] in aviso, aviso)
comprobar("  y por stderr no sale nada: el aviso no es una pantalla",
          r.stderr == "", r.stderr[:90])

r, d = correr(["literal", "--ejercicio", str(FUERA)],
              "BOE-A-1992-28740#0#articulo 95\n")
comprobar("literal tambien lo lleva",
          bool((d or {}).get("respuestas", [{}])[0].get("aviso_horizonte")), d)

# EN CADA RESPUESTA, NO SOLO EN LA CABECERA. Es la comprobacion que justifica
# repetir el aviso: quien reparte un lote por casos se lleva cada respuesta por
# su lado, y una cabecera que se queda atras no acompaña a nada.
lote = "prorrata especial\ndeduccion vivienda\ntipo impositivo reducido\n"
r, d = correr(["buscar", "--ejercicio", str(FUERA), "--tope", "1"], lote)
respuestas = (d or {}).get("respuestas") or []
comprobar("en un lote de tres, las TRES respuestas llevan su aviso",
          len(respuestas) == 3
          and all(x.get("aviso_horizonte") for x in respuestas),
          [bool(x.get("aviso_horizonte")) for x in respuestas])


# ==================================== 4. Y NO SALTA SIEMPRE
print("\n=== 4. Y CON UN EJERCICIO QUE CABE DENTRO, NO SALTA ===")
print("  Un aviso que sale siempre se aprende a ignorar en dos dias, y")
print("  entonces ya no avisa de nada. Si esto no estuviera, la comprobacion")
print("  de arriba pasaria con un `aviso` puesto a pelo en cada respuesta.\n")

r, d = correr(["buscar", "--ejercicio", str(DENTRO), "--tope", "2"],
              "prorrata especial\n")
respuestas = (d or {}).get("respuestas") or []
comprobar(f"con ejercicio {DENTRO} no hay aviso de horizonte",
          respuestas and "aviso_horizonte" not in respuestas[0],
          respuestas[:1])
comprobar("  pero el horizonte SIGUE en la cabecera: el dato no se esconde",
          (d or {}).get("horizonte", {}).get("hasta") == h["hasta"],
          (d or {}).get("horizonte"))

# EL AVISO DE HORIZONTE NO ES EL DE VIGENCIA. Son dos cosas distintas y las
# dos tienen que poder salir: uno dice «esta copia no llega hasta ahi» y el
# otro «el texto que te enseño no es el que regia ese año».
r, d = correr(["literal", "--ejercicio", "2012"],
              "BOE-A-2006-20764#0#articulo 68\n")
uno = ((d or {}).get("respuestas") or [{}])[0]
comprobar("el literal de 2012 da la version de 2012, no la de hoy",
          uno.get("version", {}).get("es_la_de_hoy") is False, uno.get("version"))
comprobar("  y su texto no es el mismo que el de hoy",
          uno.get("texto", "") != (correr(
              ["literal", "--ejercicio", str(DENTRO)],
              "BOE-A-2006-20764#0#articulo 68\n")[1] or {}
          ).get("respuestas", [{}])[0].get("texto", "@"))


# ==================================== CONTROL NEGATIVO
print("\n=== CONTROL NEGATIVO: la suite tiene que ponerse roja ===")
print("  Ninguna prueba se da por buena sin verla fallar cuando debe fallar.\n")

# (a) SI EL AVISO NO SE PUSIERA, la comprobacion 3 tiene que cazarlo. Se
# comprueba con la funcion, que es de donde sale: si devolviera siempre vacio,
# `bool(aviso)` de arriba seria falso.
comprobar("un horizonte que no avisara nunca se cazaria",
          not bool(FR.aviso_de_horizonte(CORPUS, DENTRO))
          and bool(FR.aviso_de_horizonte(CORPUS, FUERA)))

# (b) SI EL AVISO SALTARA SIEMPRE, la comprobacion 4 tiene que cazarlo. Se
# monta un corpus de mentira consolidado hasta ayer y se mira que un ejercicio
# muy anterior no dispara nada.
d5 = con_sellos({"A": sello("2026-08-01")})
comprobar("un horizonte que avisara siempre se cazaria",
          FR.aviso_de_horizonte(d5, 2019) == "",
          FR.aviso_de_horizonte(d5, 2019))

# (c) EL EJERCICIO SIGUE SIENDO OBLIGATORIO EN EL LITERAL, y sin el no sale
# texto ni con aviso ni sin el. Un aviso no es un sustituto de no contestar.
r, d = correr(["literal"], "BOE-A-1992-28740#0#articulo 95\n")
uno = ((d or {}).get("respuestas") or [{}])[0]
comprobar("sin ejercicio, el literal no devuelve texto NI aviso: se rechaza",
          "texto" not in uno and uno.get("error") == "falta el ejercicio", uno)
comprobar("  y el lote sale con 2", r.returncode == 2, r.returncode)


print("\n" + "=" * 74)
if fallos:
    print(f"{len(fallos)} FALLO(S):")
    for f in fallos:
        print(f"   - {f}")
    sys.exit(1)
print("TODO EN VERDE · el horizonte va dentro del JSON y no salta siempre")
sys.exit(0)
