"""SUMA DE CONTROL DEL CORPUS. Que no se pueda arrancar con media ley.

EL FALLO QUE ESTO CIERRA es el peor de los que hemos encontrado, porque no da
error. Un fichero del corpus que se queda a medias -un disco lleno a mitad de
`ingerir`, una copia interrumpida, un rsync a medias- se carga sin protestar
si el corte cae en un final de linea: el JSON de cada linea sigue siendo
valido, el indice se construye, la ventana abre y todo parece normal.

Lo que pasa despues no se parece a una averia. La busqueda deja de encontrar
articulos que existen, el corte por pertinencia descarta lo que queda, y salen
NO ENCONTRADO donde antes habia CRITERIO CLARO. Nadie relaciona eso con el
corpus: se piensa que la pregunta estaba mal escrita, o que la ley no lo dice.
Es exactamente el tipo de fallo que mas nos ha costado cazar en todo el
proyecto, y aqui no habria nada que cazar, porque no deja rastro.

    sellos.sellar(ruta)        despues de ingerir: apunta lo que ha quedado
    sellos.comprobar(rutas)    al arrancar: lista de problemas, vacia si bien

LO QUE SE SELLA es lo que se CARGA: los `.jsonl` de preceptos citables. Los
`.descartados.jsonl` no entran, porque no los lee el motor: son material de
auditoria de la fase 1 y un fallo suyo no cambia ni una respuesta.

EL SELLO ES DE BYTES, no de contenido interpretado. Un sha256 del fichero tal
cual esta en disco. Se guardan ademas los preceptos y los bytes, que no hacen
falta para detectar nada -el sha256 ya los cubre- pero SI para el mensaje: no
es lo mismo decir «el fichero no cuadra» que «tiene 180 preceptos y deberia
tener 243». Lo segundo se entiende y lo primero no.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

# El fichero de sellos vive DENTRO del corpus, al lado de lo que sella. Si
# alguien se lleva la carpeta a otro equipo, se lleva las dos cosas.
NOMBRE = "sellos.json"


class Desellado(Exception):
    """El corpus no cuadra con su sello, o no lo tiene."""


def _norma_de(ruta: Path) -> str:
    """`BOE-A-1992-28740.jsonl` -> `BOE-A-1992-28740`."""
    return ruta.name[: -len(".jsonl")] if ruta.name.endswith(".jsonl") else ruta.name


def medir(ruta: Path) -> dict:
    """Lo que hay AHORA en ese fichero. No mira ningun sello."""
    crudo = ruta.read_bytes()
    lineas = [l for l in crudo.decode("utf-8").splitlines() if l.strip()]
    return {
        "sha256": hashlib.sha256(crudo).hexdigest(),
        "bytes": len(crudo),
        "preceptos": len(lineas),
    }


def ruta_de_sellos(directorio: Path) -> Path:
    return Path(directorio) / NOMBRE


def leer(directorio: Path) -> dict:
    """Los sellos guardados. `{}` si no hay fichero o no se puede leer."""
    ruta = ruta_de_sellos(directorio)
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def sellar(ruta: Path, hoy: str | None = None, forzado: str = "",
           informe=None) -> dict:
    """Apunta el estado de UNA norma recien ingerida. Devuelve su sello.

    `forzado` es por que se salto la puerta del troceo, si se salto. Se guarda
    EN EL SELLO a proposito, que es el sitio que se mira para saber si el
    corpus esta entero: una norma que entro saltandose una comprobacion tiene
    que poder verse meses despues sin acordarse de nada.

    `informe` es lo que dijo el BOE sobre la consolidacion de esa norma
    -`pendientes.leer`-. SE CALCULABA AL INGERIR Y SE TIRABA, y era el unico
    dato que sabe si nuestra copia va atrasada DE VERDAD:

        `consolidado_hasta` NO ES NUESTRO RETRASO. Es hasta donde llega el
        texto consolidado QUE EL BOE PUBLICA, o sea la fecha del ultimo cambio
        que el BOE ha incorporado. Una norma estable puede llevar ocho años
        sin tocarse y estar perfectamente al dia. Lo que dice si vamos
        atrasados es OTRA cosa: si el BOE lista reformas posteriores que su
        propio texto todavia no incorpora.

    Guardarlo aqui cuesta cero -ya esta calculado dos lineas mas arriba- y es
    lo que permite que el aviso de frescura deje de medir nuestra diligencia.
    """
    ruta = Path(ruta)
    directorio = ruta.parent
    sellos = leer(directorio)
    sello = medir(ruta)
    sello["sellado"] = hoy or date.today().isoformat()
    if forzado:
        sello["forzado"] = forzado
    if informe is not None:
        # CON LA FECHA EN QUE SE PREGUNTO. Sin ella, «0 reformas pendientes»
        # de hace dos años se lee igual que el de esta mañana, que es el mismo
        # error que ya costo un diagnostico entero con `arranque_fallido.txt`.
        sello["consolidacion"] = {
            "preguntado": hoy or date.today().isoformat(),
            "consolidado_hasta": getattr(informe, "consolidado_hasta", "") or "",
            "estado_boe": getattr(informe, "estado", "") or "",
            "reformas_pendientes": len(getattr(informe, "pendientes", []) or []),
            "preceptos_tocados": sorted(
                str(x) for x in (getattr(informe, "preceptos_tocados", set())
                                 or set())),
        }
    sellos[_norma_de(ruta)] = sello
    ruta_de_sellos(directorio).write_text(
        json.dumps(sellos, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    return sello


def comprobar(rutas: list) -> list[str]:
    """Los `.jsonl` cargados contra sus sellos. Lista de problemas, en cristiano.

    Vacia = todo cuadra. Devuelve texto y no excepciones porque quien llama
    decide que hacer con ello: el arranque no abre, y la pantalla de estado lo
    enseña.

    SIN FICHERO DE SELLOS NO SE BLOQUEA NADA. Un corpus sin sellar no esta
    corrupto: esta sin sellar, que es el estado de cualquier corpus de prueba
    montado en un directorio temporal y el de cualquier copia anterior a esta
    comprobacion. Lo que NO se hace es cantar verde: `estado()` lo distingue.
    """
    rutas = [Path(r) for r in rutas]
    if not rutas:
        return []
    sellos = leer(rutas[0].parent)
    if not sellos:
        return []

    problemas = []
    for ruta in rutas:
        norma = _norma_de(ruta)
        guardado = sellos.get(norma)
        if guardado is None:
            problemas.append(
                f"{norma} esta en el corpus pero no tiene sello. Vuelve a "
                f"ingerirla:  python fase1.py ingerir {norma}")
            continue
        try:
            ahora = medir(ruta)
        except OSError as e:
            problemas.append(f"{norma} no se puede leer: {e}")
            continue
        if ahora["sha256"] == guardado.get("sha256"):
            continue
        # NO CUADRA. Se dice en que se nota, que es lo que permite entender si
        # falta media norma o si es que se ha reingerido y no se sello.
        falta = guardado.get("preceptos", 0) - ahora["preceptos"]
        if falta > 0:
            detalle = (f"faltan {falta} preceptos: tiene {ahora['preceptos']} "
                       f"y deberia tener {guardado['preceptos']}")
        elif falta < 0:
            detalle = (f"tiene {-falta} preceptos de mas: {ahora['preceptos']} "
                       f"frente a {guardado['preceptos']}")
        else:
            detalle = (f"el mismo numero de preceptos pero el contenido ha "
                       f"cambiado ({ahora['bytes']:,} bytes frente a "
                       f"{guardado.get('bytes', 0):,})")
        problemas.append(
            f"{norma} no cuadra con su sello del {guardado.get('sellado', '?')}: "
            f"{detalle}. Vuelve a ingerirla:  python fase1.py ingerir {norma}")
    return problemas


def estado(rutas: list) -> dict:
    """Para enseñar en pantalla: `{sellado, normas, problemas, frase}`.

    Tres estados, no dos. «Sin sellar» no es «mal», y presentarlo como verde
    seria justo la mentira que esto viene a evitar.
    """
    rutas = [Path(r) for r in rutas]
    sellos = leer(rutas[0].parent) if rutas else {}
    if not sellos:
        return {"sellado": False, "normas": 0, "problemas": [],
                "frase": "Sin sello: no se ha podido comprobar que el corpus "
                         "este entero."}
    problemas = comprobar(rutas)
    if problemas:
        return {"sellado": True, "normas": len(rutas), "problemas": problemas,
                "frase": f"AVISO: {len(problemas)} norma(s) no cuadran con su "
                         f"sello."}
    fechas = [s.get("sellado", "") for s in sellos.values() if s.get("sellado")]
    # UNA NORMA FORZADA NO ES UN PROBLEMA DE INTEGRIDAD -su sello cuadra- PERO
    # TAMPOCO ES NORMAL. Se dice en la misma linea, porque quien mira esta
    # pantalla lo hace justo para saber si puede fiarse de una respuesta.
    forzadas = sorted(n for n, s in sellos.items() if s.get("forzado"))
    frase = (f"Corpus comprobado: las {len(rutas)} normas cuadran con su suma "
             f"de control" + (f" ({min(fechas)})" if fechas else "") + ".")
    if forzadas:
        frase += (f" AVISO: {len(forzadas)} entraron forzadas "
                  f"({', '.join(forzadas)}).")
    return {"sellado": True, "normas": len(rutas), "problemas": [],
            "forzadas": forzadas, "frase": frase}
