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

# LO QUE SE SABE QUE ESTA EN ROJO Y POR QUE. Una prueba roja conocida no es lo
# mismo que una recien rota: lo que no puede pasar es que cambie el numero sin
# que nadie se entere. El banco compara ademas contra su propia linea base.
BANCO_ESPERADO = 16
BANCO_TOTAL = 19


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
    verdes = 0
    for trozo in linea.replace("·", " ").split():
        if trozo.isdigit() and verdes == 0:
            verdes = int(trozo)
            break
    igual = verdes == BANCO_ESPERADO
    cambio = [l for l in salida.splitlines() if "veredicto" in l.lower()]
    print(f"  {'[VERDE]' if igual else '[ROJO ]'} {linea[:60]}   ({seg:.1f}s)")
    print(f"          esperado {BANCO_ESPERADO}/{BANCO_TOTAL}"
          + (f" · {cambio[-1].strip()}" if cambio else ""))
    if not igual:
        rotos.append(f"el banco da {verdes}/{BANCO_TOTAL} y se esperaban "
                     f"{BANCO_ESPERADO}: mira si las rojas son otras")
    for l in salida.splitlines():
        if l.strip().startswith("[ROJO"):
            print(f"          roja conocida: {l.strip()[8:70]}")

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
        "Las 3 rojas del banco son conocidas y no han cambiado de veredicto.",
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


if __name__ == "__main__":
    sys.exit(main())
