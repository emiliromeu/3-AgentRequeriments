#!/usr/bin/env python3
"""LO QUE HAY DENTRO, desde la terminal. Para Emili, no para el despacho.

    python configurar.py                que hay dentro y lo que cuesta
    python configurar.py --regenerar-guia   vuelve a copiar guias/GUIA.md

CERO LLAMADAS A LA API.

----------------------------------------------------------------------------
YA NO ES UN MANDO, Y ES DELIBERADO
----------------------------------------------------------------------------
Esto nacio para encender y apagar las fuentes: eran cuatro cosas coordinadas
por la memoria de alguien y habia que juntarlas en un sitio.

DESDE QUE LOS DOS BOTONES ESTAN SIEMPRE EN LA VENTANA, no hay nada que
encender. El modo lo elige quien pulsa, consulta a consulta, y la respuesta
dice con cual se hizo. Lo que quedaba de estado global se ha quitado en vez de
mantenerlo: un interruptor que no interrumpe nada es una trampa para el que lo
lea dentro de seis meses.

LO MISMO ESTA EN LA VENTANA, en «Qué hay dentro»: el despacho no tiene que
abrir una consola para nada. Esto se queda porque a mi me sirve para mirar el
corpus y la despensa de un vistazo.

`GUIA.md` SIGUE SIENDO UN FICHERO GENERADO desde `guias/GUIA.md`. Si alguien lo
toca a mano y deja de decir lo que dice la ventana, el agente no abre.
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
    "ley": (0.14, "medido sobre la traza 20260805T221058"),
    "criterio": (0.24, "media de cuatro consultas reales, 20260805T2245-2249"),
}
EUROS_POR_DOLAR = 0.92


def titulo(t: str) -> None:
    print("\n" + "=" * ANCHO)
    print(f"  {t}")
    print("=" * ANCHO)


def aplicar(modo: str = C.UNICO) -> int:
    """Regenera GUIA.md desde guias/. Ya no hay modos que aplicar.

    LOS DOS BOTONES ESTAN SIEMPRE EN LA VENTANA, asi que no hay nada que
    encender ni apagar: lo unico que puede quedarse viejo es la hoja impresa.
    """
    origen = C.DIR_GUIAS / "GUIA.md"
    if not origen.is_file():
        print(f"\n  No encuentro {origen}, que es la guia de ese modo.")
        print("  Sin ella no se puede dejar el sistema coherente, asi que no")
        print("  se toca nada.")
        return 1

    titulo("REGENERANDO LA GUIA")
    # LA COBERTURA SE RELLENA AL COPIAR, contando la copia local. Es el unico
    # sitio donde se escribe, y sale de los datos: la guia no puede decir de
    # que hay criterio por su cuenta, porque eso es lo que ya caduco una vez
    # -«todas de IVA por ahora»- sin que nadie se enterara.
    texto = origen.read_text(encoding="utf-8")
    ix = None
    try:
        import fase4
        ix, _g = fase4.cargar_corpus()
    except Exception as e:  # noqa: BLE001
        print(f"\n  No se ha podido cargar el corpus ({e}).")
        print("  Sin el no se puede contar la despensa, y la guia se quedaria")
        print("  con una cobertura inventada. No se toca nada.")
        return 1
    abre, cierra = C.MARCA_COBERTURA
    i, j = texto.find(abre), texto.find(cierra)
    if i < 0 or j < 0:
        print(f"\n  {origen} no tiene las marcas {abre} / {cierra}.")
        print("  Sin ellas la guia no puede decir de que hay criterio.")
        return 1
    # SIN CIFRAS: solo DE QUE hay. Ver `texto_de_cobertura`.
    texto = (texto[:i + len(abre)] + "\n" + C.texto_de_cobertura(ix) + "\n"
             + texto[j:])
    C.GUIA.write_text(texto, encoding="utf-8")
    print(f"\n  GUIA.md generada de {origen}, con la cobertura contada")

    r = C.revisar(ix)
    print()
    if r.coherente:
        print("  La guia dice lo mismo que la ventana. El agente puede abrir.")
    else:
        print("  ATENCION: algo sigue sin cuadrar:")
        for d in r.descuadres:
            print(f"    · {d}")
        print()
        print("  Suele ser una frase de la ventana que no esta en guias/GUIA.md.")
        print("  Mira `python configurar.py` para verlas.")
        return 1

    print()
    print("  Imprime la guia otra vez si ha cambiado: la de la mesa tiene que")
    print("  decir lo mismo que la ventana.")
    return 0


def _cuenta(directorio: Path, patron: str) -> int:
    return len(list(directorio.glob(patron))) if directorio.is_dir() else 0


def estado() -> int:
    from agente_fiscal import dgt as D
    from agente_fiscal import teac as T

    r = C.revisar()
    titulo("COMO ESTA LA HERRAMIENTA AHORA MISMO")

    print("\n  LA VENTANA TIENE LOS DOS BOTONES. El modo se elige al pulsar.")

    print("\n  LA GUIA DICE LO MISMO QUE LA VENTANA")
    for nombre, valor in r.piezas.items():
        if isinstance(valor, bool):
            valor = "encendida" if valor else "apagada"
        print(f"    {nombre:24s} {valor}")
    print(f"\n  {'COHERENTE' if r.coherente else 'DESCOORDINADO'}: "
          + ("la hoja de la mesa y la pantalla coinciden" if r.coherente
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
    print("\n  LO QUE CUESTA CADA BOTON")
    for cual, etiqueta in (("ley", "Consultar la ley"),
                           ("criterio", "Consultar tambien el criterio")):
        d, de_donde = COSTE[cual]
        print(f"    {etiqueta:34s} ${d:.2f}  ·  {d * EUROS_POR_DOLAR:.2f} EUR")
        print(f"      {de_donde}")
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
    ap.add_argument("--estado", action="store_true", default=True,
                    help="que hay dentro, y lo que cuesta (es lo unico que hace)")
    ap.add_argument("--regenerar-guia", dest="regenerar", action="store_true",
                    help="vuelve a copiar guias/GUIA.md sobre GUIA.md")
    args = ap.parse_args(argv)

    if args.regenerar:
        return aplicar()
    return estado()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
