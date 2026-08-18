#!/usr/bin/env python3
"""¿SIRVE EL SEGUNDO INTENTO DE REDACCION, Y CUANDO? Cero red, cero API.

    .venv/bin/python medir_reintento.py

LA PREGUNTA. La otra forma de acabar sin respuesta -el verificador rechazo- se
dejo fuera de la orientacion porque ahi el modelo YA intento contestar y fallo.
La hipotesis a comprobar era esta:

    · a veces el rechazo es de FORMA -el texto vale, el formato no-, y ahi el
      segundo intento funciona y no hay que tocarlo;
    · a veces NO HAY MATERIAL para sostener lo que se queria decir, y ahi el
      segundo intento va a fallar igual y orientar seria estrictamente mejor.

Si se distinguen, la orientacion va EN VEZ del segundo intento SOLO en el
segundo caso: no cuesta nada y no renuncia a la segunda oportunidad donde esa
oportunidad funciona.

QUE SE MIDE, sobre las trazas del modelo real que hay en disco:

  1. cuantas llegaron a la segunda redaccion, y cuantas la pasaron;
  2. de las que volvieron a caer, QUE decia el motivo;
  3. y si el motivo del PRIMER rechazo predice que el segundo va a fallar,
     que es lo unico que serviria para decidir ANTES de pagarlo.

SOLO EL MODELO DE VERDAD. Las trazas de ensayo no cuestan y no fallan igual.
NO IMPRIME NINGUNA PREGUNTA: son dudas de clientes.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

TRAZAS = RAIZ / "datos" / "trazas"
ANCHO = 78

# LAS CLASES SALEN DE LOS MOTIVOS QUE HAY, no de una lista escrita antes de
# mirar. Se leyeron primero los motivos reales y estas son las familias que
# aparecen; si sale uno nuevo, cae en «(otro)» y se ve, que es lo que tiene que
# pasar.
def clase_de(motivo: str) -> str:
    m = (motivo or "").lower()
    if "sin referencia a ningun precepto" in m:
        return "el fragmento no lleva su referencia pegada"
    if "no dice de que norma es" in m:
        return "la referencia no dice de que norma es"
    if "no esta literalmente" in m or "no aparece" in m:
        return "el fragmento NO esta en el material"
    if "no esta en el corpus" in m or "no cargada" in m:
        return "la norma no esta en el corpus"
    return "(otro)"


# Y LA LECTURA DE CADA CLASE: ¿es un fallo de FORMA -el texto valia y estaba mal
# escrito- o es que NO HABIA MATERIAL con que sostenerlo? Esta columna es una
# INTERPRETACION y va marcada como tal: lo que mide el guion es el motivo.
LECTURA = {
    "el fragmento no lleva su referencia pegada": "FORMA",
    "la referencia no dice de que norma es": "FORMA",
    "el fragmento NO esta en el material": "MATERIAL",
    "la norma no esta en el corpus": "MATERIAL",
    "(otro)": "?",
}


def leer(d: Path):
    try:
        con = json.loads((d / "consumo.json").read_text("utf-8"))
    except (OSError, ValueError):
        return None
    if not any("claude" in str(x.get("modelo", ""))
               for x in con.get("llamadas") or []):
        return None
    informes = []
    for n in (1, 2, 3):
        f = d / f"verificacion_{n}.json"
        if not f.is_file():
            break
        try:
            informes.append(json.loads(f.read_text("utf-8")))
        except (OSError, ValueError):
            return None
    if not informes:
        return None
    try:
        estado = json.loads((d / "resultado.json").read_text("utf-8")).get("estado")
    except (OSError, ValueError):
        estado = "?"
    return {"dir": d, "informes": informes, "estado": estado}


def clases_de(informe) -> list[str]:
    return [clase_de(c.get("motivo")) for c in informe.get("citas") or []
            if c.get("estado") != "VERIFICADA"] or (
        ["ninguna cita con fragmento literal"]
        if "ninguna cita" in str(informe.get("motivo_global")) else [])


def main() -> int:
    if not TRAZAS.is_dir():
        print("\n  No hay trazas. Nada que medir.")
        return 1
    todas = [t for t in (leer(d) for d in sorted(TRAZAS.iterdir()) if d.is_dir())
             if t]
    con_dos = [t for t in todas if len(t["informes"]) >= 2]

    print("=" * ANCHO)
    print("1 · ¿CUANTAS LLEGAN AL SEGUNDO INTENTO, Y CUANTAS LO PASAN?")
    print("=" * ANCHO)
    print(f"  consultas con verificacion en disco      : {len(todas)}")
    print(f"  rechazadas en el PRIMER intento          : {len(con_dos)}")
    if not con_dos:
        print("\n  Ninguna ha llegado al segundo intento. Sin base no se decide.")
        return 0
    paso = [t for t in con_dos if t["informes"][1].get("veredicto") == "ACEPTADO"]
    cayo = [t for t in con_dos if t not in paso]
    print(f"  de esas, el SEGUNDO intento la salvo     : {len(paso)}")
    print(f"  volvieron a caer                         : {len(cayo)}")

    print()
    print("=" * ANCHO)
    print("2 · DE LAS QUE VOLVIERON A CAER, ¿DE QUE HABLA EL MOTIVO?")
    print("=" * ANCHO)
    print("  La columna de la derecha es una LECTURA mia, no una medida.")
    print("  Lo que mide el guion es el motivo que escribio el verificador.\n")
    cuenta = Counter()
    for t in cayo:
        for c in clases_de(t["informes"][1]):
            cuenta[c] += 1
    for clase, n in cuenta.most_common():
        print(f"   {n:>3}x  {clase:46s} -> {LECTURA.get(clase, '?')}")
    material = sum(n for c, n in cuenta.items() if LECTURA.get(c) == "MATERIAL")
    print(f"\n   citas que fallan por FALTA DE MATERIAL: {material}")

    print()
    print("=" * ANCHO)
    print("3 · ¿PREDICE EL PRIMER MOTIVO LO QUE VA A PASAR EN EL SEGUNDO?")
    print("=" * ANCHO)
    print("  Es lo unico que serviria para decidir ANTES de pagar el segundo\n")
    por_clase = defaultdict(lambda: [0, 0])   # clase -> [salvadas, caidas]
    for t in con_dos:
        cs = set(clases_de(t["informes"][0]))
        salvo = t["informes"][1].get("veredicto") == "ACEPTADO"
        for c in cs:
            por_clase[c][0 if salvo else 1] += 1
    print(f"  {'motivo del PRIMER rechazo':46s} {'salva':>6} {'cae':>5}")
    for c, (s, f) in sorted(por_clase.items(), key=lambda x: -sum(x[1])):
        print(f"  {c:46s} {s:>6} {f:>5}")

    print()
    print("=" * ANCHO)
    print("Y EL MISMO MOTIVO, ¿SE REPITE?")
    print("=" * ANCHO)
    for t in con_dos:
        a = Counter(clases_de(t["informes"][0]))
        b = Counter(clases_de(t["informes"][1]))
        salvo = t["informes"][1].get("veredicto") == "ACEPTADO"
        igual = (a == b)
        print(f"  {t['dir'].name}  {'SALVADA' if salvo else 'cayo   '}  "
              f"{'MISMO motivo, mismo numero' if igual and not salvo else ''}")
        print(f"      1º: {dict(a) or 'sin citas'}")
        print(f"      2º: {dict(b) or 'sin citas'}")

    print()
    print("=" * ANCHO)
    print(f"LA BASE: {len(con_dos)} consultas llegaron al segundo intento. Es MUY")
    print("poca. Cualquier reparto de aqui puede darse la vuelta con diez mas.")
    print("=" * ANCHO)
    return 0


if __name__ == "__main__":
    sys.exit(main())
