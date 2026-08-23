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
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

# LA VERSION DEL CONTRATO, no la del programa. Sube cuando cambie la FORMA de
# lo que sale o el significado de un codigo de salida, no cuando se arregle un
# fallo por dentro. Quien lea esto puede decidir con ella si entiende el resto.
CONTRATO = "1.0"

FALLO = 1
ACEPTADO = 0
RECHAZADO = 2


def _huella_del_corpus() -> dict:
    """{normas, sellado, sha256} del corpus contra el que se verifica.

    EL SELLADO MAS RECIENTE, no el mas antiguo: identifica la foto. Y el sha de
    los sellos, que resume las diecisiete de una vez -si cambia uno solo,
    cambia-. Sin red y sin cargar nada.
    """
    import hashlib

    f = RAIZ / "datos" / "corpus" / "sellos.json"
    if not f.is_file():
        return {"normas": 0, "sellado": "", "sha256": ""}
    crudo = f.read_bytes()
    try:
        sellos = json.loads(crudo.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {"normas": 0, "sellado": "", "sha256": ""}
    fechas = [v.get("sellado", "") for v in sellos.values()
              if isinstance(v, dict) and v.get("sellado")]
    return {"normas": sum(1 for v in sellos.values() if isinstance(v, dict)),
            "sellado": max(fechas) if fechas else "",
            "sha256": hashlib.sha256(crudo).hexdigest()[:16]}


def _escribir(objeto: dict) -> None:
    """LO UNICO QUE ESCRIBE EN stdout EN TODO EL PROGRAMA."""
    json.dump(objeto, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _fallo(motivo: str, detalle: str = "") -> int:
    """Un fallo nuestro. NUNCA lleva veredicto, y por eso no puede confundirse
    con una aceptacion aunque quien llame se olvide de mirar el codigo."""
    _escribir({"error": motivo, "detalle": detalle[:300],
               "procedencia": {"contrato": CONTRATO,
                               "corpus": _huella_del_corpus()}})
    return FALLO


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ejercicio", type=int, default=None,
                    help="el año del caso. Sin el, no se comprueba la version")
    ap.add_argument("--exigir-norma", action="store_true",
                    help="una cita sin nombre de norma no vale")
    ap.add_argument("--humano", action="store_true",
                    help="ademas, el informe legible POR stderr")
    args = ap.parse_args(argv)

    texto = sys.stdin.read()

    # EL CORPUS, Y AQUI ES DONDE SE ROMPE SI SE VA A ROMPER. Se envuelve entero
    # -no existe, ilegible, a medias- porque cualquiera de esas tiene que salir
    # como fallo y no como veredicto.
    try:
        from agente_fiscal.indice import Indice   # noqa: E402
        from agente_fiscal import verificador as VF   # noqa: E402
        ix = Indice(RAIZ / "datos" / "corpus")
        if not getattr(ix, "docs", None):
            return _fallo("corpus vacio o ausente",
                          f"no hay preceptos en {RAIZ / 'datos' / 'corpus'}")
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
    salida["procedencia"] = {"contrato": CONTRATO,
                             "corpus": _huella_del_corpus()}

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
