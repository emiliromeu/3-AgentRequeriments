#!/usr/bin/env python3
"""¿ENTIENDE EL MODELO UNA CONTINUACION? Dos vueltas, enteras.

    .venv/bin/python medir_hilo_real.py                 <- ensayo, NO GASTA
    .venv/bin/python medir_hilo_real.py --con-modelo    <- gasta de verdad

TODO EL HILO SE CONSTRUYO Y SE PROBO CON EL MOTOR DE ENSAYO, que redacta con
reglas fijas. Eso prueba el andamiaje -que el tope se reinicia, que cada vuelta
deja su expediente, que el material no se reutiliza- y NO prueba lo unico que
un motor de reglas no puede tener: si el modelo ENTIENDE que la pregunta viene
de otra.

LAS CUATRO PREGUNTAS, y el guion las contesta en este orden:

  1. ¿El analizador clasifica bien el impuesto y el ejercicio cuando la
     pregunta lleva DOS PARTES PEGADAS? La caja de la ventana no se vacia, asi
     que en la vuelta 2 le llega la duda anterior Y la linea nueva, juntas.

  2. ¿Los terminos de la vuelta 2 RECOGEN el contexto añadido, o repiten los de
     la vuelta 1? Si los repite, la continuacion no sirve de nada: buscaria
     otra vez lo mismo y contestaria otra vez lo mismo.

  3. ¿El redactor escribe una respuesta ENTERA, o una que da por sabida la
     anterior? Esto ultimo seria un FALLO, y de los graves: en pantalla solo
     esta la ultima, asi que «como se dijo antes» apunta a un texto que quien
     lee no tiene delante.

  4. Y LA DE «B»: ¿basta el RESUMEN de la duda anterior para entender «y si
     fuera una furgoneta»? Al analizador no se le manda la respuesta entera
     -eso seria arrastrar texto verificado a un sitio donde no se verifica-,
     solo el resumen y los preceptos que se usaron.

LO QUE CUESTA. Dos consultas por el camino de la ley sola, que estan medidas en
$0,14 cada una. Con una redaccion reintentada, tres. El guion IMPRIME EL GASTO
REAL al final, que es el unico numero que vale.

POR DEFECTO NO GASTA. Sin `--con-modelo` corre con el motor de ensayo, mismo
camino de codigo, para poder ver que el guion hace lo que dice antes de pagarlo.
"""
import argparse
import io
import contextlib
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import fase4                                    # noqa: E402
from agente_fiscal import modelo as MOD          # noqa: E402

ANCHO = 78
EUROS_POR_DOLAR = 0.92

# LAS DOS VUELTAS. La segunda es la del diseño -«y si fuera una furgoneta»-
# porque es el caso que decide: una linea que SOLA no significa nada y que
# CAMBIA QUE ARTICULOS APLICAN. Si el sistema la entendiera mal y reutilizara
# el material de la primera, daria una respuesta segura sobre los articulos
# equivocados, que es peor que no contestar.
VUELTA_1 = ("Una empresa compra un turismo en 2023 y lo usa un comercial "
            "para visitar clientes. ¿Que parte del IVA soportado se puede "
            "deducir?")
AÑADIDO_2 = "¿Y si fuera una furgoneta de reparto en vez de un turismo?"
EJERCICIO = 2023


def barra(t: str) -> None:
    print("\n" + "=" * ANCHO)
    print(f"  {t}")
    print("=" * ANCHO)


def contar(motor) -> dict:
    return dict(motor.totales()) if hasattr(motor, "totales") else {}


def enseñar_vuelta(n: int, pregunta: str, res: dict, gasto: dict) -> None:
    barra(f"VUELTA {n}")
    print("\nLO QUE HAY EN LA CAJA (la ventana no la vacia):")
    for linea in pregunta.splitlines():
        print(f"    {linea}" if linea.strip() else "")

    a = res.get("analisis") or {}
    print("\nLO QUE ENTENDIO EL ANALIZADOR")
    print(f"    impuesto   : {a.get('impuesto')}")
    print(f"    ejercicio propuesto por el modelo: "
          f"{a.get('ejercicio_propuesto')}")
    print(f"    ejercicio  : {res.get('ejercicio')}")
    print(f"    resumen    : {a.get('resumen_duda')}")
    print(f"    terminos   : {a.get('terminos_busqueda')}")
    if a.get("articulos_sospechados"):
        print(f"    sospechados: {a.get('articulos_sospechados')}")

    print("\nDE DONDE VIENE")
    print(f"    expediente : {Path(res['traza']).name}")
    print(f"    viene_de   : {res.get('viene_de') or '(nada: es la primera)'}")
    print(f"    tipo       : {res.get('tipo') or 'consulta'}")

    print("\nCON QUE SE CONTESTO")
    print(f"    estado     : {res.get('estado')}")
    print(f"    veredicto  : {res.get('veredicto')}")
    print(f"    preceptos  : {res.get('preceptos_enviados')}")
    print(f"    verificados: {res.get('preceptos')}")

    print("\nLA RESPUESTA, ENTERA")
    print("-" * ANCHO)
    print(res.get("respuesta") or "(no hay: " + str(res.get("motivo")) + ")")
    print("-" * ANCHO)

    if gasto:
        d = MOD.dolares(gasto)
        print(f"\n    gasto de esta vuelta: {gasto.get('llamadas')} llamada(s), "
              f"{gasto.get('entrada', 0)} entrada / {gasto.get('salida', 0)} "
              f"salida  ·  ${d:.3f}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--con-modelo", action="store_true",
                    help="usa el modelo real. GASTA DINERO.")
    args = ap.parse_args()

    nombre = "anthropic" if args.con_modelo else "ensayo"
    motor, err = fase4.preparar_motor(nombre)
    if motor is None:
        print(f"\n  No se ha podido preparar el motor: {err}")
        return 1

    barra("DOS VUELTAS, CON " + ("EL MODELO REAL" if args.con_modelo
                                 else "EL MOTOR DE ENSAYO (no gasta)"))
    if not args.con_modelo:
        print("\n  ESTO NO PRUEBA LO QUE SE QUIERE PROBAR. El motor de ensayo")
        print("  redacta con reglas fijas: sirve para ver que el guion hace lo")
        print("  que dice antes de pagarlo, y para nada mas.")
    else:
        print(f"\n  analisis : {motor.modelo_analisis}")
        print(f"  redaccion: {motor.modelo_redaccion}")

    ix, grafo = fase4.cargar_corpus()

    # --- VUELTA 1 -----------------------------------------------------------
    antes = contar(motor)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r1 = fase4.consultar(VUELTA_1, EJERCICIO, motor, ix, grafo,
                             con_criterio=False)
    enseñar_vuelta(1, VUELTA_1, r1, _delta(antes, contar(motor), motor))

    if r1.get("fallo"):
        print(f"\n  LA PRIMERA VUELTA NO HA LLEGADO A COMPLETARSE "
              f"({r1['fallo']}). No se lanza la segunda: encadenar sobre una "
              f"consulta rota no mide nada.")
        return 1

    # --- VUELTA 2 -----------------------------------------------------------
    # LO QUE HACE LA VENTANA, exactamente: hereda la pregunta y le añade una
    # linea. Y al analizador -solo a el- el resumen de la duda anterior y los
    # preceptos que se usaron.
    pregunta_2 = f"{VUELTA_1}\n\n{AÑADIDO_2}"
    contexto = {"resumen": (r1.get("analisis") or {}).get("resumen_duda", ""),
                "preceptos": r1.get("preceptos_enviados") or []}

    antes = contar(motor)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r2 = fase4.consultar(pregunta_2, EJERCICIO, motor, ix, grafo,
                             con_criterio=False,
                             viene_de=Path(r1["traza"]).name,
                             contexto_anterior=contexto)
    enseñar_vuelta(2, pregunta_2, r2, _delta(antes, contar(motor), motor))

    # --- LAS CUATRO PREGUNTAS ----------------------------------------------
    barra("LAS CUATRO PREGUNTAS")
    a1 = r1.get("analisis") or {}
    a2 = r2.get("analisis") or {}
    t1 = [str(x).lower() for x in (a1.get("terminos_busqueda") or [])]
    t2 = [str(x).lower() for x in (a2.get("terminos_busqueda") or [])]

    print("\n  1 · ¿CLASIFICA BIEN CON LA PREGUNTA EN DOS PARTES?")
    print(f"      vuelta 1: {a1.get('impuesto')} / {r1.get('ejercicio')}")
    print(f"      vuelta 2: {a2.get('impuesto')} / {r2.get('ejercicio')}")
    print(f"      -> {'IGUAL, como debe' if a1.get('impuesto') == a2.get('impuesto') and r1.get('ejercicio') == r2.get('ejercicio') else 'CAMBIA: hay que mirarlo'}")

    print("\n  2 · ¿LOS TERMINOS RECOGEN EL CONTEXTO AÑADIDO?")
    nuevos = [x for x in t2 if x not in t1]
    repetidos = [x for x in t2 if x in t1]
    print(f"      terminos vuelta 1 : {t1}")
    print(f"      terminos vuelta 2 : {t2}")
    print(f"      NUEVOS            : {nuevos or '(ninguno)'}")
    print(f"      repetidos         : {repetidos or '(ninguno)'}")
    print(f"      -> {'RECOGE el contexto' if nuevos else 'REPITE la vuelta 1: la continuacion no aporta'}")

    print("\n  3 · ¿LA RESPUESTA SE SOSTIENE SOLA?")
    # LAS PISTAS DE UNA RESPUESTA QUE DA POR SABIDA LA ANTERIOR. No es un
    # veredicto: es una lista para MIRAR, porque el texto entero esta arriba.
    PISTAS = ("como se dijo", "como se indico", "como ya se", "anteriormente",
              "en la respuesta anterior", "como se señalo", "como vimos",
              "ademas de lo anterior", "en mi respuesta")
    txt = (r2.get("respuesta") or "").lower()
    encontradas = [p for p in PISTAS if p in txt]
    print(f"      giros que apuntan a un texto que no esta en pantalla: "
          f"{encontradas or '(ninguno)'}")
    print(f"      preceptos citados en la vuelta 2: {r2.get('preceptos')}")
    print(f"      -> {'MIRAR EL TEXTO: parece apoyarse en la anterior' if encontradas else 'se sostiene sola'}")

    print("\n  4 · ¿BASTA EL RESUMEN DE LA DUDA ANTERIOR? (la «B»)")
    print(f"      lo que se le paso : «{contexto['resumen']}»")
    print(f"      preceptos pasados : {contexto['preceptos']}")
    print(f"      lo que entendio   : «{a2.get('resumen_duda')}»")
    print(f"      preceptos elegidos: {r2.get('preceptos_enviados')}")
    cambia = set(r2.get("preceptos_enviados") or []) != set(
        r1.get("preceptos_enviados") or [])
    print(f"      -> el material {'CAMBIA' if cambia else 'es el MISMO'} "
          f"respecto a la vuelta 1")

    # --- EL GASTO -----------------------------------------------------------
    barra("EL GASTO REAL DE LA PASADA")
    tot = contar(motor)
    print(f"\n  llamadas al modelo : {tot.get('llamadas')}")
    print(f"  entrada            : {tot.get('entrada')} tokens")
    print(f"  salida             : {tot.get('salida')} tokens")
    print(f"  cache              : {tot.get('cache_lectura')} leidos / "
          f"{tot.get('cache_escritura')} escritos")
    d = MOD.dolares(tot)
    print(f"\n  COSTE: ${d:.3f}  ·  {d * EUROS_POR_DOLAR:.3f} EUR")
    print(f"  (tarifas publicadas de Opus 5, sobre los tokens que dice la API)")
    print(f"\n  expedientes: {Path(r1['traza']).name} -> "
          f"{Path(r2['traza']).name}")
    return 0


def _delta(antes: dict, ahora: dict, motor) -> dict:
    if not ahora:
        return {}
    d = {k: ahora.get(k, 0) - antes.get(k, 0)
         for k in ("llamadas", "entrada", "salida",
                   "cache_lectura", "cache_escritura")}
    return d


if __name__ == "__main__":
    sys.exit(main())
