"""LO QUE COMPARTEN LAS ENTRADAS DE MAQUINA. El contrato, en un solo sitio.

`verificar_json`, `estado_json` y `corpus_json` prometen lo mismo: por stdout
sale UN objeto JSON y nada mas, siempre con procedencia, y un fallo nuestro
jamas produce algo con aspecto de buena respuesta. Eso estuvo escrito tres
veces, con las mismas palabras y por triplicado, que es como empiezan a
separarse: en este proyecto ya paso con los tres identificadores de norma
copiados en el instalador, que se quedaron en tres mientras el corpus crecia a
dieciseis, sin que nada avisara.

Aqui no hay ninguna decision nueva. Es el mismo contrato de siempre, escrito
una vez, para que arreglarlo en un sitio lo arregle en los tres.

LO QUE NO ESTA AQUI, a proposito: los codigos de salida. `0` significa
ACEPTADO en uno, LISTO en otro y TODAS CONTESTADAS en el tercero, y `2` la
negativa de cada uno. Fingir que son el mismo numero llamandolos igual seria
mentir sobre lo unico que cada guion tiene que explicar por su cuenta.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# LA VERSION DEL CONTRATO, no la de ningun programa. Sube cuando cambie la
# FORMA de lo que sale o el significado de un codigo de salida, no cuando se
# arregle un fallo por dentro. Quien lea el JSON puede decidir con ella si
# entiende el resto.
CONTRATO = "1.0"

# El unico codigo que significa lo mismo en los tres: se rompio algo nuestro.
FALLO = 1


class ErrorDeUso(Exception):
    """Han llamado al guion mal. Un verbo que no existe, una opcion que no es.

    NO ES UNA RESPUESTA NEGATIVA, y por eso no puede salir por el codigo `2`.
    Argparse, tal cual viene, escribe el modo de empleo por stderr y sale con
    2: quien consuma esto leeria «rechazado» o «no listo» -una respuesta
    correcta que dice que no- cuando lo que ha pasado es que le han llamado
    mal, y ademas se encontraria stdout VACIO, que rompe el `json.loads` de
    todo lo que salga.
    """


class Argumentos(argparse.ArgumentParser):
    """Argparse que no se salta el contrato cuando la llamada viene mal."""

    def error(self, mensaje):        # noqa: D102
        raise ErrorDeUso(mensaje)

    def exit(self, status=0, message=None):   # noqa: D102
        # `--help` sigue saliendo por donde sale siempre: lo pide una persona
        # en una consola, no un programa leyendo stdout.
        if status == 0 and message is None:
            raise SystemExit(0)
        raise ErrorDeUso(message or f"salida {status}")


def huella_del_corpus(dir_corpus: Path) -> dict:
    """{normas, sellado, sha256} del corpus del que se esta hablando.

    EL SELLADO MAS RECIENTE, no el mas antiguo: identifica la foto. Y el sha de
    los sellos, que resume las diecisiete de una vez -si cambia uno solo,
    cambia-. Sin red y sin cargar nada.

    UN «VERIFICADA», UN «LISTO» O UN LITERAL SIN ESTO NO DICEN CONTRA QUE, y
    dentro de seis meses eso es la diferencia entre poder reconstruir una
    respuesta y no poder.
    """
    f = Path(dir_corpus) / "sellos.json"
    if not f.is_file():
        return {"normas": 0, "sellado": "", "sha256": ""}
    try:
        crudo = f.read_bytes()
        sellos = json.loads(crudo.decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {"normas": 0, "sellado": "", "sha256": ""}
    fechas = [v.get("sellado", "") for v in sellos.values()
              if isinstance(v, dict) and v.get("sellado")]
    return {"normas": sum(1 for v in sellos.values() if isinstance(v, dict)),
            "sellado": max(fechas) if fechas else "",
            "sha256": hashlib.sha256(crudo).hexdigest()[:16]}


def procedencia(dir_corpus: Path) -> dict:
    return {"contrato": CONTRATO, "corpus": huella_del_corpus(dir_corpus)}


def escribir(objeto: dict) -> None:
    """LO UNICO QUE PUEDE ESCRIBIR EN stdout. Un objeto, una linea, nada mas.

    Ni avisos, ni progreso, ni una linea en blanco de mas. Quien lee esto hace
    `json.loads` de todo lo que salga, y un «cargando corpus...» delante lo
    rompe en el sitio mas tonto.
    """
    json.dump(objeto, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.stdout.flush()


def fallo(motivo: str, dir_corpus: Path, detalle: str = "") -> int:
    """Un fallo nuestro. NUNCA lleva veredicto, ni estado, ni respuestas.

    Y NO LOS LLEVA EN FALSO: no lleva la clave. Un `"listo": false` o un
    `"respuestas": []` se parecen a «he mirado y no hay nada», que es justo lo
    que no ha pasado. Quien consuma esto se queda con `None` y no puede
    confundirlo con una respuesta.
    """
    escribir({"error": motivo, "detalle": str(detalle)[:300],
              "procedencia": procedencia(dir_corpus)})
    return FALLO
