#!/usr/bin/env python3
"""TODO, DE UNA VEZ Y EN UNA SOLA SALIDA. Cero red, cero API.

    python3 comprobar_todo.py

Las once suites, la bateria del verificador, las comprobaciones de la fase 4, el
banco de recuperacion y la coherencia entre la guia y la ventana. Es lo que se
mira antes de congelar una version y decir «con esto entrego».

POR QUE ESTE GUION EXISTE Y NO ES UN `for` EN LA TERMINAL:

  · UNA SOLA SALIDA. Doce ordenes sueltas se leen doce veces y se olvida una.
  · EL BANCO NO ES «VERDE O ROJO». Tiene una linea base -16 de 19- y lo que
    importa NO es que no haya rojas, es que sean LAS MISMAS de siempre. Un
    `if codigo != 0` lo daria por roto todos los dias, y una comprobacion que
    esta roja todos los dias es una comprobacion que nadie mira.
  · SE DISTINGUE ROTO DE PENDIENTE. Al final salen las dos listas separadas,
    porque no se entrega igual con una cosa que con la otra.

NO SE PARA EN EL PRIMER FALLO, al reves que `comprobar_equipo.py`. Aquel lo lee
alguien de pie en una oficina y necesita una cosa que arreglar; este lo leo yo
antes de entregar y necesito el mapa entero.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PY = sys.executable
ANCHO = 72

# LO QUE SE SABE QUE ESTA EN ROJO. Una roja conocida no es lo mismo que una
# recien rota, y lo que no puede pasar es que cambie sin que nadie se entere.
#
# SE COMPARA EL CONJUNTO, NO EL RECUENTO, Y ESO ES EL ARREGLO DEL 14/08/2026.
# Aqui habia dos numeros escritos a mano -«16 de 19»- de cuando el banco tenia
# diecinueve casos. Con cuarenta y cuatro, el guion llevaba dias diciendo «el
# banco da 27 y se esperaban 16» sin que eso significara nada: la novena lista
# escrita a mano del proyecto, en forma de numero.
#
# Y ademas medía lo que no dice medir. Dos lineas mas abajo el propio guion
# avisa: «no se juzga por cero rojas, se juzga por que sean LAS MISMAS». Un
# recuento no puede ver eso: si una roja se arregla y otra se rompe, el numero
# no se mueve y el guion da verde.
#
# LA LINEA BASE SE GENERA, NO SE ESCRIBE. Sale del propio JSON del banco:
#
#     .venv/bin/python comprobar_todo.py --guardar-rojas
#
# y se commitea. Cambiarla es una decision deliberada que queda en el diff, que
# es justo lo que un numero a mano no dejaba ver.
ROJAS_CONOCIDAS = RAIZ / "casos" / "banco_rojas_conocidas.txt"


def rojas_del_ultimo_banco() -> set:
    """Los identificadores de las pruebas en rojo de la ultima pasada."""
    import json
    pasadas = sorted((RAIZ / "datos" / "banco").glob("banco_*.json"))
    if not pasadas:
        return set()
    d = json.loads(pasadas[-1].read_text(encoding="utf-8"))
    # LA CONSTANTE, NO LA CADENA. Escribi "rojo" en minusculas y no cazaba
    # ninguna: la linea base habria salido vacia y el guion en verde para
    # siempre. Preguntandole al banco no se puede fallar.
    sys.path.insert(0, str(RAIZ))
    import banco
    return {p["id"] for p in d.get("pruebas", [])
            if p.get("veredicto") == banco.ROJO}


def leer_rojas_conocidas() -> set:
    if not ROJAS_CONOCIDAS.is_file():
        return set()
    return {l.strip() for l in ROJAS_CONOCIDAS.read_text(encoding="utf-8")
            .splitlines() if l.strip() and not l.startswith("#")}


def titulo(t: str) -> None:
    print("\n" + "=" * ANCHO)
    print(t)
    print("=" * ANCHO)


def correr(orden: list, nombre: str) -> tuple:
    """Ejecuta y devuelve (codigo, salida, segundos). No imprime nada."""
    t0 = time.monotonic()
    r = subprocess.run([PY] + orden, capture_output=True, text=True, cwd=RAIZ)
    return r.returncode, (r.stdout or "") + (r.stderr or ""), time.monotonic() - t0


def main() -> int:
    rotos: list = []
    pendientes: list = []

    titulo("COMPROBACION COMPLETA")
    print(f"python : {sys.version.split()[0]}")
    print(f"raiz   : {RAIZ}")

    # ------------------------------------------------------------- suites
    titulo("1. SUITES")
    suites = sorted((RAIZ / "pruebas").glob("prueba_*.py"))
    print(f"{len(suites)} suites en pruebas/\n")
    for s in suites:
        codigo, salida, seg = correr([str(s)], s.name)
        # El recuento, no la ultima linea: `prueba_caidas` simula un disco
        # lleno y acaba escribiendo un [AVISO] por stderr, que es correcto y
        # no es su resultado.
        cuenta = [l for l in salida.splitlines()
                  if l.startswith(("FALLOS:", "COMPROBACIONES:"))]
        resumen = (cuenta[-1].strip() if cuenta
                   else ([l for l in salida.splitlines() if l.strip()] or
                         ["(sin salida)"])[-1].strip())
        marca = "[VERDE]" if codigo == 0 else "[ROJO ]"
        print(f"  {marca} {s.name:<28} {seg:>5.1f}s   {resumen[:34]}")
        if codigo != 0:
            rotos.append(f"{s.name}: {resumen[:60]}")
            for linea in salida.splitlines():
                if linea.strip().startswith(("FALLO", "  FALLO", "  - ")):
                    print(f"          {linea.strip()[:76]}")

    # ------------------------------------------------- bateria y fase 4
    titulo("2. BATERIA DEL VERIFICADOR Y COMPROBACIONES DE LA FASE 4")
    for orden, nombre in ((["fase3.py", "probar"], "bateria (casos adversarios)"),
                          (["fase4.py", "comprobaciones"], "fase 4")):
        codigo, salida, seg = correr(orden, nombre)
        clave = [l for l in salida.splitlines()
                 if "EN VERDE" in l or "ROJO" in l or "FALLO" in l]
        print(f"  {'[VERDE]' if codigo == 0 else '[ROJO ]'} {nombre:<28} "
              f"{seg:>5.1f}s   {(clave[-1].strip() if clave else '')[:34]}")
        if codigo != 0:
            rotos.append(f"{nombre}: {(clave[-1] if clave else '')[:60]}")

    # ------------------------------------------------------------- banco
    titulo("3. BANCO DE RECUPERACION")
    print("  No se juzga por «cero rojas»: se juzga por que sean LAS MISMAS.\n")
    codigo, salida, seg = correr(["banco.py"], "banco")
    total = [l for l in salida.splitlines() if "TOTAL:" in l]
    linea = total[-1].strip() if total else ""

    ahora = rojas_del_ultimo_banco()
    conocidas = leer_rojas_conocidas()
    nuevas = sorted(ahora - conocidas)
    arregladas = sorted(conocidas - ahora)
    igual = not nuevas and not arregladas

    print(f"  {'[VERDE]' if igual else '[ROJO ]'} {linea[:60]}   ({seg:.1f}s)")
    print(f"          rojas conocidas: {len(conocidas)} · ahora: {len(ahora)}")
    if nuevas:
        print(f"          SE HAN ROTO {len(nuevas)}:")
        for i in nuevas[:8]:
            print(f"            + {i[:64]}")
    if arregladas:
        print(f"          SE HAN ARREGLADO {len(arregladas)} "
              f"(enhorabuena, y actualiza la linea base):")
        for i in arregladas[:8]:
            print(f"            - {i[:64]}")
    if not igual:
        rotos.append(
            f"el conjunto de rojas del banco ha cambiado: "
            f"{len(nuevas)} nueva(s), {len(arregladas)} arreglada(s). "
            f"Si es a mejor: comprobar_todo.py --guardar-rojas")
    elif conocidas:
        print("          las mismas de siempre, ni una nueva")

    # -------------------------------------------------- guia y ventana
    titulo("4. LA GUIA Y LA VENTANA DICEN LO MISMO")
    sys.path.insert(0, str(RAIZ))
    try:
        from agente_fiscal import configuracion as CONF
        r = CONF.revisar()
        for pieza, valor in r.piezas.items():
            print(f"  {pieza:<34} {valor}")
        if r.coherente:
            print("\n  [VERDE] la hoja de la mesa describe esta herramienta")
        else:
            print("\n  [ROJO ] no cuadran:")
            for d in r.descuadres:
                print(f"          - {d[:70]}")
            rotos.append("la guia y la ventana no dicen lo mismo")
    except Exception as e:  # noqa: BLE001
        print(f"  [ROJO ] no se ha podido comprobar: {e}")
        rotos.append(f"no se ha podido comprobar la guia: {e}")

    # --------------------------------------------------- corpus sellado
    titulo("5. EL CORPUS, CONTRA SU SUMA DE CONTROL")
    try:
        import fase4
        from agente_fiscal import sellos as SL
        ix, _g = fase4.cargar_corpus()
        est = SL.estado(ix.rutas)
        print(f"  {len(ix.docs)} preceptos · {len(ix.normas.cuerpos)} cuerpos · "
              f"{len(ix.rutas)} normas")
        print(f"  {'[VERDE]' if est['sellado'] and not est['problemas'] else '[ROJO ]'}"
              f" {est['frase'][:62]}")
        for p in est["problemas"]:
            print(f"          - {p[:70]}")
            rotos.append(f"corpus: {p[:60]}")
    except Exception as e:  # noqa: BLE001
        print(f"  [ROJO ] {e}")
        rotos.append(f"el corpus no carga: {e}")

    # ------------------------------------------------------ lo que queda
    titulo("6. CON QUE SE ENTREGA")
    pendientes += [
        "sembrar_teac.py:69 lee catalogo.json sin coger JSONDecodeError. "
        "Guion de mantenimiento, no lo usa el despacho.",
        "ver_ejemplo.py acepta una ruta absoluta y mira fuera de "
        "datos/trazas/. Solo lee, y es un guion mio.",
        "Si el modelo se cae ENTRE el analizador y el redactor, el analisis "
        "se vuelve a pagar. Son 0,03 centimos: no se construyo reanudacion.",
        "El criterio de la DGT y del TEAC solo cubre IVA. Renta y Sociedades "
        "van solo con la ley.",
        # EL NUMERO SALE DE LA LINEA BASE, no escrito: decia «las 3 rojas»
        # cuando hay diecisiete. Es el mismo defecto que se acaba de quitar
        # doce lineas mas arriba, y estaba a dos dedos.
        f"Las {len(leer_rojas_conocidas())} rojas del banco estan en "
        f"{ROJAS_CONOCIDAS.name} con su motivo al lado en el fichero de casos.",
    ]

    if rotos:
        print(f"\n  ROTO ({len(rotos)}):")
        for x in rotos:
            print(f"    · {x}")
    else:
        print("\n  ROTO: nada.")
    print(f"\n  PENDIENTE, sabido y anotado ({len(pendientes)}):")
    for x in pendientes:
        print(f"    · {x}")

    titulo("TODO EN VERDE" if not rotos else f"{len(rotos)} COSA(S) ROTAS")
    return 1 if rotos else 0


def guardar_rojas() -> int:
    """Reescribe la linea base con las rojas de la ULTIMA pasada del banco.

    NO CORRE EL BANCO: lee su JSON. Asi la linea base sale de una pasada que
    alguien ha mirado, y no de una que se lanza justo para hacerla cuadrar.
    """
    rojas = rojas_del_ultimo_banco()
    if not rojas:
        print("No hay ninguna pasada del banco guardada. Corre antes:")
        print("    .venv/bin/python banco.py")
        return 1
    antes = leer_rojas_conocidas()
    ROJAS_CONOCIDAS.parent.mkdir(parents=True, exist_ok=True)
    ROJAS_CONOCIDAS.write_text(
        "# LAS ROJAS CONOCIDAS DEL BANCO, por identificador.\n"
        "# SE GENERA, NO SE ESCRIBE:\n"
        "#     .venv/bin/python comprobar_todo.py --guardar-rojas\n"
        "# `comprobar_todo` compara el CONJUNTO contra esto. Si cambia, avisa\n"
        "# de cuales se han roto y cuales se han arreglado, que es lo que un\n"
        "# recuento no puede ver: con una arreglada y otra rota, el numero no\n"
        "# se mueve.\n"
        + "\n".join(sorted(rojas)) + "\n", encoding="utf-8")
    print(f"  linea base: {len(antes)} -> {len(rojas)} rojas")
    for i in sorted(rojas - antes):
        print(f"    + {i}")
    for i in sorted(antes - rojas):
        print(f"    - {i}")
    print(f"  guardada en {ROJAS_CONOCIDAS.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    if "--guardar-rojas" in sys.argv:
        sys.exit(guardar_rojas())
    sys.exit(main())
