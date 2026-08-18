#!/usr/bin/env python3
"""¿CUANTO OCUPA Y CUANTO CUESTA UNA ORIENTACION?

    .venv/bin/python medir_orientacion.py                 <- ensayo, NO GASTA
    .venv/bin/python medir_orientacion.py --con-modelo    <- gasta de verdad

LAS DOS PREGUNTAS SON LAS DE VERDAD. Salen de las dos trazas reales que hoy
caen por pertinencia insuficiente, leidas del disco. Y NO SE IMPRIMEN: son
dudas de clientes. Lo que se trae es la cuenta, no las dudas.

QUE SE MIDE, y el primero es el que importa:

  1. TOKENS DE SALIDA de una orientacion, contra los de una redaccion completa.
     SI SALEN PARECIDOS, ES QUE ESTA CONTESTANDO EN VEZ DE ORIENTAR. Una
     orientacion dice que se ha encontrado, donde vive lo que falta y que dato
     hace falta; eso es bastante mas corto que resolver un caso.

  2. EL COSTE REAL de esas dos consultas: lo que costaban -una llamada de
     analisis- y lo que cuestan ahora.

  3. Y CUANTAS PASAN LOS TRES CANDADOS. Una orientacion rechazada tambien se
     paga: si se cae la mitad, el precio por orientacion util es el doble.

SIN FALLBACKS: si una traza no se puede leer, se cuenta como no leida.
"""
import argparse
import io
import json
import contextlib
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import fase4                                     # noqa: E402
from agente_fiscal import modelo as MOD          # noqa: E402

TRAZAS = RAIZ / "datos" / "trazas"
ANCHO = 78
EUROS_POR_DOLAR = 0.92

# La referencia contra la que se compara. Sale de `medir_no_encontrado.py`, que
# la calcula de las llamadas reales que hay en disco.
def salida_de_una_redaccion() -> tuple[float, int]:
    """(media de tokens de salida, cuantas llamadas la sostienen)."""
    sal, n = 0, 0
    for d in sorted(TRAZAS.iterdir()) if TRAZAS.is_dir() else []:
        c = d / "consumo.json"
        if not c.is_file():
            continue
        try:
            con = json.loads(c.read_text("utf-8"))
        except (OSError, ValueError):
            continue
        for l in con.get("llamadas") or []:
            if "claude" in str(l.get("modelo", "")) and "redacc" in l.get("paso", ""):
                sal += int(l.get("salida", 0) or 0)
                n += 1
    return (sal / n if n else 0.0), n


def preguntas_de_esta_rama() -> list[tuple[str, str, int]]:
    """(sello, pregunta, ejercicio) de las trazas que cayeron por pertinencia.

    Se reconocen por lo que dejaron escrito: hay paso de `pertinencia` y NO hay
    ninguna llamada de redaccion. No se adivina por el numero de llamadas.
    """
    salida = []
    for d in sorted(TRAZAS.iterdir()) if TRAZAS.is_dir() else []:
        try:
            con = json.loads((d / "consumo.json").read_text("utf-8"))
            pasos = json.loads((d / "pasos.json").read_text("utf-8"))
            preg = (d / "pregunta.txt").read_text("utf-8").strip()
        except (OSError, ValueError):
            continue
        lineas = con.get("llamadas") or []
        if not any("claude" in str(x.get("modelo", "")) for x in lineas):
            continue
        if any("redacc" in x.get("paso", "") for x in lineas):
            continue
        if not any(p.get("paso") == "pertinencia" for p in pasos):
            continue
        # EL EJERCICIO SE LEE DE LA TRAZA, no se vuelve a resolver. En estas
        # dos lo puso quien pregunto -la pregunta no lo dice- y sin el la
        # consulta se para antes de buscar, que es otro camino y no este.
        try:
            ej = json.loads((d / "resultado.json").read_text("utf-8")).get(
                "ejercicio")
        except (OSError, ValueError):
            continue
        if preg and ej:
            salida.append((d.name, preg, int(ej)))
    return salida


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--con-modelo", action="store_true",
                    help="usa el modelo real. GASTA DINERO.")
    ap.add_argument("--solo-ejemplo", action="store_true",
                    help="solo el ejemplo, sin repetir las dos reales")
    ap.add_argument("--ejemplo", action="store_true",
                    help="añade una consulta INVENTADA y enseña su orientacion "
                         "entera. Cuesta una consulta mas.")
    args = ap.parse_args()

    ref_salida, ref_n = salida_de_una_redaccion()
    casos = preguntas_de_esta_rama()
    if args.solo_ejemplo:
        motor, err = fase4.preparar_motor(
            "anthropic" if args.con_modelo else "ensayo", silencioso=True)
        if motor is None:
            print(f"\n  No se ha podido preparar el motor: {err}")
            return 1
        ix, grafo = fase4.cargar_corpus()
        print(f"  una redaccion completa, media de {ref_n} llamadas reales : "
              f"{ref_salida:.0f} tokens de salida")
        _ejemplo(motor, ix, grafo)
        return 0

    print("=" * ANCHO)
    print("LO QUE HAY QUE MEDIR")
    print("=" * ANCHO)
    print(f"  consultas que hoy caen por pertinencia insuficiente : {len(casos)}")
    print(f"  (sus preguntas NO se imprimen: son de clientes)")
    print(f"  una redaccion completa, media de {ref_n} llamadas reales : "
          f"{ref_salida:.0f} tokens de salida")
    if not casos:
        print("\n  Ninguna traza de esta rama en disco. Nada que medir.")
        return 1

    nombre = "anthropic" if args.con_modelo else "ensayo"
    motor, err = fase4.preparar_motor(nombre, silencioso=True)
    if motor is None:
        print(f"\n  No se ha podido preparar el motor: {err}")
        return 1
    if not args.con_modelo:
        print("\n  MOTOR DE ENSAYO: los tokens son cero y no miden nada. Sirve")
        print("  para ver que el guion hace lo que dice antes de pagarlo.")

    ix, grafo = fase4.cargar_corpus()
    filas = []
    for sello, pregunta, ejercicio in casos:
        antes = len(motor.consumo)
        with contextlib.redirect_stdout(io.StringIO()):
            r = fase4.consultar(pregunta, ejercicio, motor, ix, grafo)
        nuevas = motor.consumo[antes:]
        orient = [x for x in nuevas if x.get("paso") == "orientacion"]
        # POR QUE CAMINO HA IDO ESTA VEZ. No tiene por que ser el mismo: el
        # analisis se rehace, y unos terminos distintos pueden pasar la puerta
        # de pertinencia que la vez anterior no pasaron. Si no vuelve a caer
        # por esta rama, esta consulta NO mide lo que se queria medir, y eso se
        # dice en vez de contarla igual.
        try:
            pasos = json.loads(
                (Path(r["traza"]) / "pasos.json").read_text("utf-8"))
        except (OSError, ValueError):
            pasos = []
        hay = {p.get("paso") for p in pasos}
        if "orientacion" in hay:
            camino = "pertinencia insuficiente (esta rama)"
        elif "verificacion" in hay:
            camino = "OTRA RAMA: el verificador rechazo — no mide esto"
        elif "busqueda" not in hay:
            camino = "OTRA RAMA: se corto antes de buscar — no mide esto"
        else:
            camino = "contesto: esta vez si habia material"
        filas.append({
            "sello": sello, "res": r,
            "salida": sum(int(x.get("salida", 0) or 0) for x in orient),
            "todas": nuevas,
            "camino": camino, "pasos": pasos,
            "acepta": bool(r.get("orientacion")),
            "largo": len(r.get("orientacion") or ""),
        })

    print()
    print("=" * ANCHO)
    print("LO QUE HA SALIDO")
    print("=" * ANCHO)
    for f in filas:
        print(f"\n  de la consulta {f['sello']}")
        print(f"     camino            : {f['camino']}")
        print(f"     orientacion        : "
              f"{'ACEPTADA' if f['acepta'] else 'RECHAZADA (se cae al NO ENCONTRADO)'}")
        print(f"     tokens de salida   : {f['salida']}")
        print(f"     caracteres         : {f['largo']}")
        if not f["acepta"]:
            motivo = next((str(p.get("detalle")) for p in f["pasos"]
                           if p.get("paso") == "orientacion"),
                          "no llego a pedirse: fue por otra rama")
            print(f"     por que            : {motivo[:100]}")

    aceptadas = [f for f in filas if f["acepta"]]
    de_la_rama = [f for f in filas if "esta rama" in f["camino"]]
    if len(de_la_rama) < len(filas):
        print(f"\n  AVISO: {len(filas) - len(de_la_rama)} de {len(filas)} no han")
        print("  vuelto a caer por esta rama. El analisis se rehace, y unos")
        print("  terminos distintos pueden pasar la puerta que antes no pasaron.")
        print("  Esas NO miden lo que se queria medir.")
    print()
    print("=" * ANCHO)
    print("1 · ¿ORIENTA O CONTESTA?")
    print("=" * ANCHO)
    if not aceptadas:
        print("\n  Ninguna ha pasado los candados. Sin ninguna aceptada no se")
        print("  puede decir lo que ocupa una orientacion, y no se estima.")
    else:
        med = sum(f["salida"] for f in aceptadas) / len(aceptadas)
        print(f"\n  orientacion  : {med:.0f} tokens de salida "
              f"(media de {len(aceptadas)})")
        print(f"  redaccion    : {ref_salida:.0f} tokens (media de {ref_n})")
        if ref_salida:
            print(f"  la orientacion ocupa el {100*med/ref_salida:.0f}% de una "
                  f"respuesta completa")
            print()
            if med > ref_salida * 0.7:
                print("  SEÑAL DE ALARMA: ocupa casi lo mismo que contestar.")
                print("  Hay que leerla entera: puede estar contestando.")
            else:
                print("  Es bastante mas corta, que es lo que tiene que ser.")

    print()
    print("=" * ANCHO)
    print("2 · EL COSTE")
    print("=" * ANCHO)
    ks = ("entrada", "salida", "cache_lectura", "cache_escritura")
    for etiqueta, filtro in (("ANTES (solo el analisis)", "analisis"),
                             ("LA ORIENTACION", "orientacion")):
        t = dict.fromkeys(ks, 0)
        for f in filas:
            for x in f["todas"]:
                if filtro in x.get("paso", ""):
                    for k in ks:
                        t[k] += int(x.get(k, 0) or 0)
        d = MOD.dolares(t)
        print(f"  {etiqueta:26s} ${d:.3f}  ·  {d*EUROS_POR_DOLAR:.3f} EUR "
              f"(las {len(filas)} juntas)")
    total = dict.fromkeys(ks, 0)
    for f in filas:
        for x in f["todas"]:
            for k in ks:
                total[k] += int(x.get(k, 0) or 0)
    d = MOD.dolares(total)
    print(f"  {'LAS DOS, AHORA':26s} ${d:.3f}  ·  {d*EUROS_POR_DOLAR:.3f} EUR")
    if filas:
        print(f"  {'por consulta':26s} ${d/len(filas):.3f}  ·  "
              f"{d/len(filas)*EUROS_POR_DOLAR:.3f} EUR")
    print()
    print(f"  3 · pasan los candados: {len(aceptadas)} de {len(filas)}")
    if aceptadas and len(aceptadas) < len(filas):
        print(f"     una rechazada tambien se paga: el precio por orientacion")
        print(f"     UTIL es ${d/len(aceptadas):.3f} · "
              f"{d/len(aceptadas)*EUROS_POR_DOLAR:.3f} EUR")
    print()
    print(f"  Y LA BASE: {len(filas)} consultas. Es poca, y se dice cada vez.")

    if args.ejemplo:
        _ejemplo(motor, ix, grafo)
    return 0


# LA PREGUNTA DEL EJEMPLO ES PUBLICA: es la consulta V0002-20 de la DGT, que
# esta en la despensa. Por eso se puede enseñar entera. Las dos de arriba son
# de clientes: se miden y no se citan.
#
# NO LA HE ESCOGIDO A OJO. La primera vez puse una de Sucesiones inventada por
# mi «para que cayera», y la contesto: el corpus lleva la ley Y el reglamento
# del ISD desde hace dos semanas. Escoger el caso a ojo es como se acaba
# enseñando el unico ejemplo que funciona. Esta sale del barrido de las 1.474
# consultas de la DGT, del grupo que cae por pertinencia.
EJEMPLO = ("Si las rentas que perciba por los servicios contratados por la "
           "Agencia de Naciones Unidas estaran exentas de tributacion en "
           "España por aplicacion de las prerrogativas atribuibles a Naciones "
           "Unidas. En caso de no estar exentas, tipo impositivo que debera "
           "pagar.")


def _ejemplo(motor, ix, grafo) -> None:
    print()
    print("=" * ANCHO)
    print("UNA ORIENTACION ENTERA, PARA JUZGARLA")
    print("=" * ANCHO)
    print(f"\n  Es una consulta PUBLICA de la DGT -por eso se puede enseñar-,")
    print(f"  y sale del barrido de las que caen por pertinencia, no de")
    print(f"  escogerla a ojo hasta que una funcione.")
    print(f"\n  PREGUNTA (consulta V0002-20 de la DGT, publica):")
    print(f"  {EJEMPLO}")
    antes = len(motor.consumo)
    with contextlib.redirect_stdout(io.StringIO()):
        r = fase4.consultar(EJEMPLO, 2024, motor, ix, grafo)
    nuevas = motor.consumo[antes:]
    print(f"\n  estado     : {r.get('estado')}")
    print(f"  llamadas   : {len(nuevas)}  ({[x.get('paso') for x in nuevas]})")
    ks = ("entrada", "salida", "cache_lectura", "cache_escritura")
    tot = {k: sum(int(x.get(k, 0) or 0) for x in nuevas) for k in ks}
    d = MOD.dolares(tot)
    print(f"  salida     : {tot['salida']} tokens")
    print(f"  coste      : ${d:.3f} · {d*EUROS_POR_DOLAR:.3f} EUR")
    texto = r.get("orientacion") or ""
    print()
    if texto:
        print("-" * ANCHO)
        print(texto)
        print("-" * ANCHO)
        print(f"\n  preceptos que ha citado : {r.get('preceptos')}")
        print(f"  recuperados en total    : {r.get('recuperado')}")
    else:
        pasos = json.loads(
            (Path(r["traza"]) / "pasos.json").read_text("utf-8"))
        motivo = next((str(p.get("detalle")) for p in pasos
                       if p.get("paso") == "orientacion"), "(fue por otra rama)")
        print(f"  NO HA SALIDO ORIENTACION: {motivo}")


if __name__ == "__main__":
    sys.exit(main())
