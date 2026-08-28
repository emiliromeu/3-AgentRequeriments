#!/usr/bin/env python3
"""EL CRONOMETRO DE LA SIEMBRA DEL CORPUS. Antes de escribir ningun tiempo.

QUE MIDE. Una instalacion LIMPIA: crudo vacio y corpus vacio, las normas de
`normas_del_corpus.json` una detras de otra, contando cada peticion al BOE y
cronometrando cada norma. Es lo que hace el instalador en un equipo nuevo, sin
nada reutilizado de este.

POR QUE EXISTE. El instalador tuvo escrito «un par de minutos cada una». Era un
numero inventado, y los numeros inventados se notan justo cuando no se cumplen:
quien mira una pantalla que prometio dos minutos y lleva seis, la cierra. La
regla de la casa es que un tiempo escrito en pantalla sale de un cronometro o
no se escribe. Este es el cronometro.

    python medir_siembra.py                 las 17, en un directorio temporal
    python medir_siembra.py --normas 3      solo las tres primeras, para probar
    python medir_siembra.py --destino DIR   deja el resultado ahi y no lo borra

LO QUE NO SE PUEDE MEDIR AQUI es la red de la oficina. Esto mide la de este
equipo, hoy. Por eso el instalador no promete minutos aunque esta tabla exista:
enseña «norma 4 de 17», que es verdad en cualquier red.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import shutil
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from agente_fiscal import boe_api, catalogo as CAT   # noqa: E402
import fase1                                          # noqa: E402

ANCHO = 78


class Contador:
    """Cada peticion al BOE, con su recurso, su tamaño y su tiempo de red."""

    def __init__(self):
        self.peticiones: list = []
        self._original = boe_api._descargar

    def __enter__(self):
        def espiado(url: str, accept: str):
            t = time.perf_counter()
            try:
                codigo, cuerpo, cabeceras = self._original(url, accept)
            except Exception:
                self.peticiones.append({"recurso": _recurso(url), "codigo": 0,
                                        "bytes": 0,
                                        "segundos": time.perf_counter() - t})
                raise
            self.peticiones.append({"recurso": _recurso(url), "codigo": codigo,
                                    "bytes": len(cuerpo),
                                    "segundos": time.perf_counter() - t})
            return codigo, cuerpo, cabeceras
        boe_api._descargar = espiado
        return self

    def __exit__(self, *_):
        boe_api._descargar = self._original
        return False

    def corte(self) -> int:
        return len(self.peticiones)


def _recurso(url: str) -> str:
    """`.../id/BOE-A-1992-28740/texto` -> `texto`. El id no interesa aqui."""
    cola = url.split("/legislacion-consolidada/id/", 1)[-1]
    trozos = cola.split("/", 1)
    return trozos[1] if len(trozos) > 1 else "(norma)"


def _mmss(segundos: float) -> str:
    return f"{int(segundos) // 60}m {int(segundos) % 60:02d}s"


def medir(normas: list, destino: Path) -> dict:
    """Siembra las normas en `destino` y devuelve la tabla. Nada de red falsa.

    Se apunta a un crudo y un corpus VACIOS a proposito: reutilizar el crudo de
    este equipo mediria una instalacion que ya esta hecha, que es justo la que
    no tarda.
    """
    crudo = destino / "crudo"
    corpus = destino / "corpus"
    crudo.mkdir(parents=True, exist_ok=True)
    corpus.mkdir(parents=True, exist_ok=True)

    # Se desvia TODO lo que escribe: el crudo, el corpus, los sellos y la
    # lista. Una medicion que ensucia lo que mide no se puede repetir.
    fase1.DIR_CRUDO, fase1.DIR_CORPUS = crudo, corpus
    CAT.CORPUS, CAT.SELLOS = corpus, corpus / "sellos.json"
    CAT.LISTA = destino / "normas_del_corpus.json"
    shutil.copyfile(RAIZ / "normas_del_corpus.json", CAT.LISTA)

    filas = []
    arranque = time.perf_counter()
    with Contador() as contador:
        for n, norma in enumerate(normas, 1):
            nombre = norma.get("nombre") or norma["id"]
            print(f"  [{n:>2} de {len(normas)}] {nombre:<32} ", end="", flush=True)
            antes = contador.corte()
            t = time.perf_counter()
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    codigo = fase1.modo_ingerir(norma["id"], descargar=False)
            except Exception as e:                       # noqa: BLE001
                codigo, buf = 1, io.StringIO(f"{type(e).__name__}: {e}")
            tardo = time.perf_counter() - t
            hechas = contador.peticiones[antes:]
            preceptos = 0
            ruta = corpus / f"{norma['id']}.jsonl"
            if ruta.is_file():
                preceptos = sum(1 for l in ruta.read_text(encoding="utf-8").splitlines()
                                if l.strip())
            filas.append({"id": norma["id"], "nombre": nombre, "codigo": codigo,
                          "peticiones": len(hechas), "preceptos": preceptos,
                          "segundos": tardo,
                          "bytes": sum(p["bytes"] for p in hechas),
                          "red": sum(p["segundos"] for p in hechas),
                          "recursos": Counter(p["recurso"] for p in hechas)})
            print(f"{len(hechas):>4} pet.  {tardo:>7.1f}s  "
                  f"{preceptos:>5} preceptos" + ("" if codigo == 0 else "   FALLO"))
            if codigo != 0:
                print("        " + buf.getvalue().strip().splitlines()[-1][:64])
    total = time.perf_counter() - arranque
    return {"filas": filas, "total_segundos": total,
            "peticiones": contador.peticiones}


def informe(datos: dict, normas: list) -> None:
    filas = datos["filas"]
    print()
    print("=" * ANCHO)
    print("  LA SIEMBRA DEL CORPUS, MEDIDA")
    print("=" * ANCHO)
    print()
    print(f"  normas sembradas        : {sum(1 for f in filas if f['codigo'] == 0)}"
          f" de {len(normas)}")
    print(f"  peticiones al BOE       : {sum(f['peticiones'] for f in filas)}")
    print(f"  preceptos               : {sum(f['preceptos'] for f in filas):,}")
    print(f"  descargado              : "
          f"{sum(f['bytes'] for f in filas) / 1e6:.1f} MB")
    print(f"  TIEMPO TOTAL            : {_mmss(datos['total_segundos'])}")
    print(f"  esperando al BOE        : {_mmss(sum(f['red'] for f in filas))}")
    print()

    por_recurso = Counter()
    for p in datos["peticiones"]:
        por_recurso[p["recurso"]] += 1
    print("  Peticiones por recurso:")
    for recurso, n in por_recurso.most_common():
        print(f"    {recurso:<20} {n:>5}")
    print()

    lentas = sorted(filas, key=lambda f: -f["segundos"])[:5]
    print("  Las cinco que mas tardan:")
    for f in lentas:
        print(f"    {f['nombre']:<34} {f['segundos']:>7.1f}s  "
              f"{f['peticiones']:>3} pet.  {f['preceptos']:>5} preceptos")
    print()
    if filas:
        peor = max(f["segundos"] for f in filas)
        media = datos["total_segundos"] / len(filas)
        print(f"  Por norma: {media:.1f}s de media, {peor:.1f}s la peor.")
        print("  LA MEDIA NO SE PUEDE ENSEÑAR EN EL INSTALADOR: la peor es "
              f"{peor / media:.1f} veces")
        print("  la media, y quien espera no vive en la media, vive en la suya.")
    print()


def main(argv) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--normas", type=int, default=0,
                    help="medir solo las N primeras (0 = todas)")
    ap.add_argument("--destino", default="",
                    help="donde sembrar. Por defecto, un temporal que se borra")
    ap.add_argument("--json", default="",
                    help="ademas, la tabla en bruto a este fichero")
    args = ap.parse_args(argv)

    normas = CAT.del_disco()
    if not normas:
        print("No hay lista de normas: falta normas_del_corpus.json")
        return 1
    if args.normas:
        normas = normas[:args.normas]

    temporal = not args.destino
    destino = Path(args.destino) if args.destino else Path(tempfile.mkdtemp(
        prefix="medir_siembra_"))
    print()
    print(f"  Sembrando {len(normas)} normas EN LIMPIO en {destino}")
    print(f"  Crudo vacio: no se reutiliza nada de este equipo.")
    print()
    try:
        datos = medir(normas, destino)
        informe(datos, normas)
        if args.json:
            Path(args.json).write_text(json.dumps(
                {"filas": [{k: (dict(v) if isinstance(v, Counter) else v)
                            for k, v in f.items()} for f in datos["filas"]],
                 "total_segundos": datos["total_segundos"]},
                ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            print(f"  Tabla en bruto -> {args.json}")
    finally:
        if temporal:
            shutil.rmtree(destino, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
