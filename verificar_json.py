#!/usr/bin/env python3
"""LA ENTRADA DE MAQUINA DEL VERIFICADOR. Cero llamadas a la API.

    echo "texto con citas" | .venv/bin/python verificar_json.py --ejercicio 2023
    cat respuesta.txt | .venv/bin/python verificar_json.py --ejercicio 2023

Existe para que otro programa pueda preguntar «¿esto se sostiene?» y fiarse de
la respuesta sin leer una pantalla. `fase3.py verificar` es para una persona:
pinta un informe con marcas y colores. Esto es lo mismo por dentro y otra cosa
por fuera.

----------------------------------------------------------------------------
EL CONTRATO. Lo que sigue no son detalles: es lo que otro programa da por hecho
----------------------------------------------------------------------------

ENTRADA
    El texto por la entrada estandar. Nada mas.

SALIDA
    stdout: SOLO el JSON del informe. Un objeto, una linea final, y nada mas.
            NUNCA otra cosa: ni avisos, ni progreso, ni una linea en blanco de
            mas. Quien lee esto hace `json.loads` de todo lo que salga, y un
            «cargando corpus...» delante lo rompe.
    stderr: el informe para leer, si se pide con `--humano`. Por defecto, nada.

CODIGOS DE SALIDA
    0   ACEPTADO
    2   RECHAZADO
    otro  FALLO. Y entonces NO HAY JSON DE ACEPTACION, por contrato:
          si algo se rompe por dentro, lo que sale por stdout es un objeto con
          `"error"`, jamas uno con `"veredicto": "ACEPTADO"`. Un verificador
          que ante un fallo suyo pudiera decir «aceptado» no es un verificador.

QUE MIRA
    Las caches REALES: `datos/dgt` y `datos/teac`. Las de prueba
    -`casos/dgt_prueba`, `casos/teac_prueba`- son SOLO de `fase3.py probar`,
    donde los casos adversarios necesitan criterio inventado contra el que
    comprobar. Aqui serian falsas en las dos direcciones: una cita autentica
    saldria NO_VERIFICABLE por no estar en la cache de prueba, y una cita a un
    caso inventado saldria VERIFICADA.

SOLO LECTURA
    NO ESCRIBE NADA: ni en el corpus, ni en las caches, ni en las trazas, ni en
    la cola. Verificar es mirar. Un verificador que deja rastro cambia lo que
    verifica la proxima vez, y ademas se puede llamar en paralelo desde varios
    sitios. `prueba_verificar_json` lo comprueba con una foto del arbol antes y
    despues.

PROCEDENCIA
    El JSON lleva `procedencia`: la version de este contrato y la huella del
    corpus contra el que se verifico. UN «VERIFICADA» SIN ESO NO DICE CONTRA
    QUE, y dentro de seis meses eso es la diferencia entre poder reconstruir
    una respuesta y no poder.

LO QUE NO CAMBIA
    `verificar_texto` no se toca. RECHAZADO por no llevar ninguna cita se queda
    como esta: es correcto -sin fuente no hay respuesta- y es util tal cual.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
CORPUS = RAIZ / "datos" / "corpus"

# EL CONTRATO VIVE EN `agente_fiscal.maquina`, y con el la version, la huella
# del corpus, lo unico que escribe en stdout y la forma de un fallo. Estuvo
# escrito aqui y copiado en los otros dos, que es como tres cosas que tienen
# que ser iguales dejan de serlo.
from agente_fiscal.maquina import (  # noqa: E402
    Argumentos, ErrorDeUso, escribir as _escribir, fallo as _fallo_de,
    procedencia)

ACEPTADO = 0
RECHAZADO = 2


def _fallo(motivo: str, detalle: str = "") -> int:
    return _fallo_de(motivo, CORPUS, detalle)


def main(argv) -> int:
    ap = Argumentos(description=__doc__,
                    formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ejercicio", type=int, default=None,
                    help="el año del caso. Sin el, no se comprueba la version")
    ap.add_argument("--exigir-norma", action="store_true",
                    help="una cita sin nombre de norma no vale")
    ap.add_argument("--humano", action="store_true",
                    help="ademas, el informe legible POR stderr")
    # UNA LLAMADA MAL HECHA ES UN FALLO, NO UN RECHAZO. Argparse sale con 2 y
    # sin JSON, y 2 aqui significa RECHAZADO: quien lo consuma leeria «no se
    # sostiene» de un texto que nadie ha llegado a mirar.
    try:
        args = ap.parse_args(argv)
    except ErrorDeUso as e:
        return _fallo("no se ha entendido la llamada", str(e))

    texto = sys.stdin.read()

    # EL CORPUS, Y AQUI ES DONDE SE ROMPE SI SE VA A ROMPER. Se envuelve entero
    # -no existe, ilegible, a medias- porque cualquiera de esas tiene que salir
    # como fallo y no como veredicto.
    try:
        from agente_fiscal.indice import Indice   # noqa: E402
        from agente_fiscal import verificador as VF   # noqa: E402
        ix = Indice(CORPUS)
        if not getattr(ix, "docs", None):
            return _fallo("corpus vacio o ausente",
                          f"no hay preceptos en {CORPUS}")
    except Exception as e:                       # noqa: BLE001
        return _fallo("no se ha podido cargar el corpus",
                      f"{type(e).__name__}: {e}")

    try:
        # LAS CACHES REALES: por defecto. Ver el contrato de arriba.
        informe = VF.Verificador(ix).verificar_texto(
            texto, args.ejercicio, args.exigir_norma)
    except Exception as e:                       # noqa: BLE001
        return _fallo("el verificador ha fallado", f"{type(e).__name__}: {e}")

    salida = informe.a_json()
    salida["procedencia"] = procedencia(CORPUS)

    if args.humano:
        # A stderr, SIEMPRE. Si esto fuera a stdout romperia el contrato, y lo
        # romperia solo cuando alguien pasara `--humano`: el peor momento para
        # descubrirlo.
        try:
            import fase3
            import contextlib
            import io
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                fase3.pinta_informe(informe, "(entrada estandar)")
            sys.stderr.write(buf.getvalue())
        except Exception:                        # noqa: BLE001
            pass          # el informe legible es un extra: no puede tumbar nada

    _escribir(salida)
    return ACEPTADO if informe.veredicto == VF.ACEPTADO else RECHAZADO


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
