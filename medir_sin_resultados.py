#!/usr/bin/env python3
"""DE LAS «FORMA INESPERADA», CUANTAS SON DE VERDAD. Cero API de Anthropic.

    .venv/bin/python medir_sin_resultados.py --tope 2    <- la prueba pequeña
    .venv/bin/python medir_sin_resultados.py             <- las 53

EL PROBLEMA QUE MIDE. `extraer_resultados` levanta `FormaInesperada` cuando la
pagina no trae ningun `viewDocument`, y en el mensaje dice ella misma que puede
ser dos cosas MUY distintas:

  - que ese articulo no tenga consultas de la DGT, que es un dato NORMAL; o
  - que hayan cambiado la plantilla del buscador, que es un AVISO.

Hoy se cuentan juntas, y juntas no sirven: 53 articulos «raros» por pasada no
se miran, y si un dia la plantilla cambia de verdad se pierde entre ellos.

QUE HACE. Rehace la busqueda de los articulos que fallaron y GUARDA EL CRUDO en
`casos/petete_vacias/`. Guardarlo es el punto: con el HTML en disco, el
detector se escribe contra lo que la fuente dice de verdad -no contra lo que yo
me imagine que dice- y la suite lo prueba despues sin pedir nada.

PETICIONES. Una por articulo, con la pausa de siempre. La cadena de siembra
esta PARADA cuando esto se ejecuta; si estuviera corriendo, esto se sumaria a
su ritmo. Se comprueba al arrancar.

SIN FALLBACKS: si una busqueda falla, se apunta como fallo y no se sustituye
por nada. Un numero que sale igual cuando la consulta no responde no es una
medicion.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import petete                                   # noqa: E402
import sembrar                                  # noqa: E402

DESTINO = RAIZ / "casos" / "petete_vacias"

# Cuanto puede medir el nombre de un caso guardado. 60 deja la ruta relativa
# en unos 85 caracteres, que con la carpeta del usuario de Windows por delante
# sigue lejos de los 260.
TOPE_NOMBRE = 60


def _nombre_de_fichero(etiqueta: str) -> str:
    """`Ley 27/2014 art. 15 bis` -> `Ley_27_2014_art_15_bis.html`, con tope.

    LA COLA IMPORTA MAS QUE LA CABEZA: lo que distingue dos casos es el numero
    de articulo, que va al final. Asi que si hay que recortar se recorta por
    en medio, no por el final.
    """
    import re as _re
    limpio = _re.sub(r"[^A-Za-z0-9]+", "_", etiqueta).strip("_")
    if len(limpio) <= TOPE_NOMBRE:
        return limpio + ".html"
    cola = limpio[-24:].lstrip("_")
    cabeza = limpio[:TOPE_NOMBRE - len(cola) - 3].rstrip("_")
    return f"{cabeza}__{cola}.html"
PAUSA = 10          # la de la cadena: no se acelera porque esto sea corto
SALIDA = RAIZ / "datos" / "siembra" / "medicion_sin_resultados.json"


def main() -> int:
    # EL MISMO CAMINO EN PEQUEÑO. `--tope 2` recorre exactamente este codigo,
    # no otro parecido: probar el modo barato no prueba el caro.
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--tope", type=int, default=0, help="0 = todas")
    args = p.parse_args()

    # LA CADENA NO PUEDE ESTAR CORRIENDO. Dos cosas pidiendo a la vez a PETETE
    # es el doble de ritmo sin que ninguna de las dos lo sepa.
    viva = subprocess.run(["pgrep", "-f", "sembrar.py sembrar"],
                          capture_output=True, text=True).stdout.strip()
    if viva:
        print("LA CADENA DE SIEMBRA ESTA CORRIENDO. No se mide encima de ella.")
        return 1

    av = sembrar.leer_avance()
    fallidas = {k: v for k, v in av.get("fallidas", {}).items()
                if "forma inesperada" in str(v)}
    print(f"articulos con FORMA INESPERADA guardados: {len(fallidas)}")

    filas = {f"{f['norma']} art. {f['articulo']}": f
             for f in sembrar.construir_plan()}
    objetivo = [(k, filas[k]) for k in sorted(fallidas) if k in filas]
    if args.tope:
        objetivo = objetivo[:args.tope]
        print(f"  (--tope {args.tope}: prueba pequeña)")
    print(f"de los que se pueden rehacer:            {len(objetivo)}")
    print(f"una peticion cada {PAUSA}s -> unos {len(objetivo) * PAUSA // 60} min\n")

    DESTINO.mkdir(parents=True, exist_ok=True)
    fuente = petete.Fuente(silencioso=True)
    filas_out = []

    for n, (etiqueta, fila) in enumerate(objetivo, 1):
        consulta = f"{fila['numero']} {fila['articulo']}"
        try:
            campos = fuente._campos("", "", petete.TAB_VINCULANTES, 1)
            campos = [(k, consulta if k == "VLCMP_3" else v) for k, v in campos]
            crudo = fuente.pedir("/do/search", campos).cuerpo
        except Exception as e:                   # noqa: BLE001
            # SIN FALLBACK: se apunta el fallo, no se rellena con nada.
            print(f"  [{n:2d}/{len(objetivo)}] {etiqueta:38s} FALLO: {e}")
            filas_out.append({"etiqueta": etiqueta, "consulta": consulta,
                              "error": str(e)})
            time.sleep(PAUSA)
            continue

        # EL NOMBRE, CON TOPE. Sin el salieron nueve ficheros de 216
        # caracteres -el Reglamento General de gestion e inspeccion tiene un
        # titulo de 200- y en Windows el limite de ruta son 260 CONTANDO la
        # carpeta del usuario: `git checkout` aborta a medias con «unable to
        # checkout working tree» y deja el arbol roto. El nombre aqui es una
        # etiqueta para mirar a mano, no un identificador: se recorta y ya.
        nombre = _nombre_de_fichero(etiqueta)
        (DESTINO / nombre).write_text(crudo, encoding="utf-8")
        tiene_doc = "viewDocument" in crudo
        print(f"  [{n:2d}/{len(objetivo)}] {etiqueta:38s} "
              f"{len(crudo):>7} bytes  viewDocument={tiene_doc}")
        filas_out.append({"etiqueta": etiqueta, "consulta": consulta,
                          "fichero": nombre, "bytes": len(crudo),
                          "viewDocument": tiene_doc})
        time.sleep(PAUSA)

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(filas_out, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    ok = [f for f in filas_out if "error" not in f]
    print(f"\nrehechas sin fallo: {len(ok)} de {len(objetivo)}")
    print(f"con viewDocument:   {sum(1 for f in ok if f['viewDocument'])}"
          "   <- si sale >0, la busqueda AHORA si trae resultados")
    print(f"crudo guardado en:  {DESTINO}")
    print(f"medicion en:        {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
