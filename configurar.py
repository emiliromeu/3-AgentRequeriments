#!/usr/bin/env python3
"""EL MANDO. Un solo interruptor para las cuatro piezas.

    python configurar.py --estado          que hay ahora, en cristiano
    python configurar.py --con-criterio    enciende DGT y TEAC, y sus textos
    python configurar.py --solo-ley        los apaga y vuelve a la guia de hoy

CERO LLAMADAS A LA API. Esto solo escribe un fichero de modo y copia la guia
que toca.

----------------------------------------------------------------------------
POR QUE EXISTE
----------------------------------------------------------------------------
Encender las fuentes eran CUATRO cosas coordinadas por la memoria de alguien:
`AGENTE_DGT`, `AGENTE_TEAC`, `AGENTE_DGT_TEXTOS` y cambiar `GUIA.md` a mano. El
dia que se olvidara una, la ventana diria que la DGT esta y la hoja de la mesa
diria que no. Y quien la lea decidira con la que tenga delante.

Aqui se cambian las cuatro o no se cambia ninguna. Y se puede volver atras: los
dos modos son simetricos, no hay ida sin vuelta.

`GUIA.md` PASA A SER UN FICHERO GENERADO. Las versiones que se editan viven en
`guias/`; si alguien toca `GUIA.md` a mano, la comprobacion de arranque lo ve
-pierde la marca- y el agente no abre.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from agente_fiscal import configuracion as C  # noqa: E402

ANCHO = 74

# Lo que cuesta una consulta en cada modo, MEDIDO, no estimado. Sale de las
# trazas reales: la de ley sola es 20260805T221058 y la media con criterio son
# las cuatro de 20260805T2245-2249. Tarifas de Opus 5 (5 / 6,25 / 0,50 / 25
# dolares por millon de tokens de entrada / cache escrita / cache leida /
# salida).
COSTE = {
    C.SOLO_LEY: (0.14, "medido sobre la traza 20260805T221058"),
    C.CON_CRITERIO: (0.24, "media de cuatro consultas reales, 20260805T2245-2249"),
}
EUROS_POR_DOLAR = 0.92


def titulo(t: str) -> None:
    print("\n" + "=" * ANCHO)
    print(f"  {t}")
    print("=" * ANCHO)


def aplicar(modo: str) -> int:
    """Deja las CUATRO piezas en el mismo estado. Todo o nada."""
    origen = C.DIR_GUIAS / f"GUIA.{modo}.md"
    if not origen.is_file():
        print(f"\n  No encuentro {origen}, que es la guia de ese modo.")
        print("  Sin ella no se puede dejar el sistema coherente, asi que no")
        print("  se toca nada.")
        return 1

    anterior = C.modo_guardado()
    titulo(f"CAMBIANDO A MODO: {modo}")
    print(f"\n  modo anterior: {anterior}")
    print()

    # 1 y 2. Las fuentes y los textos: los dos salen del mismo fichero.
    C.guardar_modo(modo)
    print(f"  [1/3] fuentes DGT y TEAC ....... "
          f"{'ENCENDIDAS' if modo == C.CON_CRITERIO else 'apagadas'}")
    print(f"  [2/3] textos de la ventana ..... "
          f"{'los de tres fuentes' if modo == C.CON_CRITERIO else 'los de ley sola'}")

    # 3. La guia, copiada entera. No se parchea: se sustituye.
    shutil.copyfile(origen, C.GUIA)
    print(f"  [3/3] GUIA.md .................. copiada de {origen.name}")

    r = C.revisar()
    print()
    if r.coherente:
        print("  Las cuatro piezas dicen lo mismo. El agente puede abrir.")
    else:
        print("  ATENCION: algo sigue sin cuadrar:")
        for d in r.descuadres:
            print(f"    · {d}")
        print()
        print("  Suele ser una variable de entorno puesta a mano que manda")
        print("  sobre el fichero. Mira `python configurar.py --estado`.")
        return 1

    if modo == C.CON_CRITERIO:
        print()
        print("  Imprime la guia otra vez: la de la mesa ha cambiado, y ahora")
        print("  explica que la doctrina del TEAC, la consulta de la DGT y la")
        print("  resolucion de un TEAR NO obligan a lo mismo.")
    print()
    print(f"  Para volver atras:  python configurar.py --{anterior}")
    return 0


def _cuenta(directorio: Path, patron: str) -> int:
    return len(list(directorio.glob(patron))) if directorio.is_dir() else 0


def estado() -> int:
    from agente_fiscal import dgt as D
    from agente_fiscal import teac as T

    r = C.revisar()
    titulo("COMO ESTA LA HERRAMIENTA AHORA MISMO")

    print(f"\n  MODO: {r.modo}")
    print("  " + ("Solo la ley. Sin criterio de la DGT ni resoluciones."
                  if r.modo == C.SOLO_LEY else
                  "Ley + criterio de la DGT + resoluciones economico-administrativas."))

    print("\n  LAS CUATRO PIEZAS")
    for nombre, valor in r.piezas.items():
        if isinstance(valor, bool):
            valor = "encendida" if valor else "apagada"
        print(f"    {nombre:24s} {valor}")
    print(f"\n  {'COHERENTE' if r.coherente else 'DESCOORDINADO'}: "
          + ("las cuatro dicen lo mismo" if r.coherente
             else "el agente NO abrira"))
    for d in r.descuadres:
        print(f"    · {d}")

    # --- que hay dentro ---
    print("\n  NORMAS CARGADAS")
    try:
        import fase4
        ix, _g = fase4.cargar_corpus()
        for c in ix.normas.cuerpos.values():
            n = sum(1 for d in ix.docs
                    if d.registro.get("cuerpo_clave") == c.clave)
            print(f"    {c.etiqueta:46s} {n:4d} preceptos")
        print(f"    {'TOTAL':46s} {len(ix.docs):4d}")
    except Exception as e:  # noqa: BLE001
        print(f"    (no se ha podido leer el corpus: {type(e).__name__})")

    print("\n  COPIA LOCAL DE CRITERIO")
    consultas = _cuenta(D.DIR_CONSULTAS, "*.json")
    criterios = _cuenta(T.DIR_CRITERIOS, "*.json")
    centrales = regionales = 0
    for c in T.CacheTEAC().todas():
        if c.es_central:
            centrales += 1
        else:
            regionales += 1
    print(f"    consultas de la DGT                            {consultas:4d}")
    print(f"    resoluciones economico-administrativas         {criterios:4d}"
          f"   ({centrales} del TEAC, {regionales} de tribunales regionales)")
    if r.modo == C.SOLO_LEY and (consultas or criterios):
        print("    (estan descargadas, pero en este modo NO se usan)")

    print("\n  LO QUE CUESTA UNA CONSULTA")
    dolares, de_donde = COSTE[r.modo]
    print(f"    aproximadamente  ${dolares:.2f}  ·  {dolares * EUROS_POR_DOLAR:.2f} EUR")
    print(f"    {de_donde}")
    otro = C.CON_CRITERIO if r.modo == C.SOLO_LEY else C.SOLO_LEY
    d2, _ = COSTE[otro]
    print(f"    en modo «{otro}» seria ${d2:.2f} ({d2 * EUROS_POR_DOLAR:.2f} EUR), "
          f"un {abs(d2 - dolares) / dolares:.0%} "
          f"{'mas' if d2 > dolares else 'menos'}")
    print("\n  Son dos llamadas al modelo por consulta. El precio sube si la")
    print("  primera redaccion no pasa el verificador y hay que reintentar.")
    print()
    return 0 if r.coherente else 1


def main(argv: list) -> int:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    grupo = ap.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--estado", action="store_true",
                       help="que hay encendido ahora, y lo que cuesta")
    grupo.add_argument("--con-criterio", dest="con_criterio",
                       action="store_true",
                       help="enciende DGT y TEAC, sus textos y su guia")
    grupo.add_argument("--solo-ley", dest="solo_ley", action="store_true",
                       help="vuelve a la ley sola")
    args = ap.parse_args(argv)

    if args.estado:
        return estado()
    return aplicar(C.CON_CRITERIO if args.con_criterio else C.SOLO_LEY)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
