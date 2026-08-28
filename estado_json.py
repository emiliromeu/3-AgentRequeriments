#!/usr/bin/env python3
"""LA ENTRADA DE MAQUINA DEL ESTADO DEL CORPUS. Cero red, cero API.

    .venv/bin/python estado_json.py
    .venv/bin/python estado_json.py --detalle

Contesta cinco preguntas, y ninguna necesita cargar el corpus:

    ¿estas sembrado?          ¿hay corpus, y esta entero?
    ¿cuantas normas?          las que hay frente a las que deberia haber
    ¿hasta cuando llega?      el horizonte, y hasta cuando llega CADA una
    ¿cuando se sembro?        la fecha de la ingesta, la nuestra
    ¿que falta por incorporar? las reformas que el BOE publica y su texto aun no

Existe porque hasta ahora eso solo se podia saber MIRANDO una pantalla -«Que
hay dentro»- y quien necesita saberlo antes de lanzar una tanda es un programa.
Un programa que tiene que decidir si el corpus sirve no puede leer una pantalla,
y si no puede preguntarlo, sigue adelante. Seguir adelante con media ley dentro
es el fallo que no da error.

----------------------------------------------------------------------------
EL CONTRATO. Literalmente el mismo: `agente_fiscal.maquina`
----------------------------------------------------------------------------

No «igual que el de `verificar_json`»: EL MISMO MODULO. Estuvo copiado, y
tres copias de un contrato son tres contratos en cuanto alguien arregle una.

ENTRADA
    Nada. No lee stdin.

SALIDA
    stdout: SOLO el JSON. Un objeto, una linea final, y nada mas. NUNCA otra
            cosa: ni avisos, ni progreso, ni una linea en blanco de mas.
    stderr: el resumen para leer, si se pide con `--humano`. Por defecto, nada.

CODIGOS DE SALIDA
    0   LISTO. Sembrado, completo y cuadrando con sus sellos.
    2   NO LISTO. Hay corpus o no lo hay, pero no se puede confiar en el tal
        cual: sin sembrar, con normas de menos, o con algun fichero que no
        cuadra con su suma de control. NO ES UN FALLO NUESTRO: es una respuesta
        correcta que dice que no.
    otro  FALLO. Y entonces NO HAY JSON DE ESTADO, por contrato: si algo se
          rompe por dentro, lo que sale por stdout es un objeto con `"error"`,
          jamas uno con `"listo": true`. Un informe de estado que ante un fallo
          suyo pudiera decir «listo» es peor que no tenerlo, porque se cree.

PROCEDENCIA
    Siempre, y tambien en los fallos: la version de este contrato y la huella
    del corpus del que se hablo. Un «17 normas» sin eso no dice de que copia.

SOLO LECTURA
    No escribe nada. Lee `datos/corpus/sellos.json` y `normas_del_corpus.json`,
    y ni siquiera abre los `.jsonl` salvo para comprobar su suma de control.

LO QUE NO HACE. No pregunta al BOE. Todo lo que dice sale de lo que la ingesta
dejo escrito en el sello, y por eso «0 reformas pendientes» va SIEMPRE con la
fecha en que se pregunto: sin ella, un cero de hace dos años se lee igual que
el de esta mañana.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
CORPUS = RAIZ / "datos" / "corpus"

# EL CONTRATO VIVE EN `agente_fiscal.maquina`: la version, la huella del
# corpus, lo unico que escribe en stdout y la forma de un fallo. El mismo
# modulo que usan `verificar_json` y `corpus_json`, para que los tres no puedan
# separarse sin que alguien lo note.
from agente_fiscal.maquina import (  # noqa: E402
    Argumentos, ErrorDeUso, escribir as _escribir, fallo as _fallo_de,
    procedencia)

LISTO = 0
NO_LISTO = 2


def _fallo(motivo: str, detalle: str = "") -> int:
    return _fallo_de(motivo, CORPUS, detalle)


def reunir(detalle: bool) -> dict:
    """Todo lo que se sabe del corpus sin tocar la red ni cargar los preceptos."""
    from agente_fiscal import catalogo as CAT
    from agente_fiscal import frescura as FR
    from agente_fiscal import sellos as SELLOS

    # LA LISTA QUE VIAJA SE LEE EN SERIO, Y ESTA ES LA UNICA VEZ QUE SE HACE.
    #
    # `catalogo.del_disco` se traga un `normas_del_corpus.json` ilegible y
    # devuelve la lista vacia, y eso esta bien para sus otros usuarios: nadie
    # quiere que la ventana no abra por un fichero derivado. Pero AQUI vuelve
    # todo del reves. Con la lista vacia no se espera ninguna norma, no falta
    # ninguna, y este programa contesta «listo: true, esperadas: 0» con las
    # diecisiete en `sobran` y codigo 0. Lo destapo la suite del contrato.
    #
    # Ese es exactamente el fallo interno con cara de buena respuesta que el
    # contrato prohibe: no hay nada roto que enseñar, y quien lo consuma
    # empieza una tanda creyendo que el corpus esta comprobado contra una lista
    # que no se ha podido leer. Asi que revienta, y sale por `error`.
    if CAT.LISTA.is_file():
        try:
            json.loads(CAT.LISTA.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError(
                f"{CAT.LISTA.name} no se puede leer: {e}. Sin la lista de "
                f"normas no se puede decir si el corpus esta completo") from e

    rutas = sorted(p for p in CORPUS.glob("*.jsonl")
                   if not p.name.endswith(".descartados.jsonl"))
    esperadas = CAT.del_disco()
    faltan = CAT.faltan()
    sobran = CAT.sobran()

    # LA INTEGRIDAD SE COMPRUEBA DE VERDAD: se releen los ficheros y se
    # rehacen sus sha256. Es lo unico caro que hace este programa y es lo unico
    # que no se puede dar por bueno de memoria.
    problemas = SELLOS.comprobar(rutas)
    est = SELLOS.estado(rutas)

    edad = FR.edad_del_corpus(CORPUS)
    retraso = FR.retraso_de_consolidacion(CORPUS)
    horizonte = FR.horizonte(CORPUS)
    guardados = SELLOS.leer(CORPUS)

    sembrado = bool(rutas)
    completo = not faltan
    cuadra = not problemas
    salida = {
        # LAS TRES SON DISTINTAS Y SE DAN LAS TRES. «Sembrado» es que hay algo;
        # «completo» es que estan todas las de la lista; «cuadra» es que lo que
        # hay es lo que dice ser. Un corpus puede estar sembrado y completo y
        # tener un fichero a medias, que es el caso peligroso.
        "sembrado": sembrado,
        "completo": completo,
        "cuadra": cuadra,
        "listo": sembrado and completo and cuadra,
        "normas": {
            "esperadas": len(esperadas),
            "sembradas": len(rutas),
            "faltan": [{"id": n["id"], "nombre": n.get("nombre", "")}
                       for n in faltan],
            # LO QUE SOBRA NO SE BORRA NI SE CALLA. Casi siempre es una norma
            # recien ingerida que aun no se ha publicado en la lista.
            "sobran": sobran,
        },
        "sellado": {
            "mas_antiguo": (edad["mas_vieja"].isoformat()
                            if edad.get("mas_vieja") else ""),
            "mas_reciente": procedencia(CORPUS)["corpus"]["sellado"],
            "dias": edad.get("dias"),
            "sin_fecha": edad.get("sin_fecha", 0),
        },
        # HASTA DONDE LLEGA. `hasta` es la fecha del eslabon mas corto y
        # `ejercicio_completo` el ultimo año cubierto de enero a diciembre.
        "horizonte": {k: v for k, v in horizonte.items() if k != "por_norma"},
        "reformas_pendientes": {
            "normas_con": retraso["con_reformas"],
            "de": retraso["normas"],
            "preceptos_tocados": retraso["preceptos"],
            # LA FECHA EN QUE SE PREGUNTO, SIEMPRE. Sin ella un cero no dice
            # si es que no hay o es que no se ha mirado.
            "preguntado": retraso["preguntado"],
            "sin_dato": retraso["sin_dato"],
        },
        "integridad": {"problemas": problemas, "forzadas": est.get("forzadas", [])},
        "avisos": [a for a in (FR.aviso_de_consolidacion(CORPUS),
                               FR.aviso_de_edad(CORPUS)) if a],
    }

    if detalle:
        # NORMA A NORMA: cuantos preceptos, cuando se sembro, hasta cuando
        # llega y que reformas le faltan. Es el mismo dato de arriba sin
        # resumir, y va aparte porque son 17 objetos y quien solo quiere saber
        # si puede empezar no los necesita.
        titulos = {n["id"]: n for n in esperadas}
        filas = []
        for norma_id in sorted(set(list(guardados) + [n["id"] for n in esperadas])):
            s = guardados.get(norma_id) or {}
            c = s.get("consolidacion") or {}
            filas.append({
                "id": norma_id,
                "nombre": (titulos.get(norma_id) or {}).get("nombre", ""),
                "sembrada": (CORPUS / f"{norma_id}.jsonl").is_file(),
                "preceptos": s.get("preceptos"),
                "sellado": s.get("sellado", ""),
                "consolidado_hasta": c.get("consolidado_hasta", ""),
                "reformas_pendientes": c.get("reformas_pendientes"),
                "preceptos_tocados": len(c.get("preceptos_tocados") or []),
                "preguntado": c.get("preguntado", ""),
                "forzada": s.get("forzado", ""),
                # UNA A UNA, con lo que el BOE dio de cada una y `falta`
                # diciendo lo que no dio. El recuento dice que la norma esta
                # sin incorporar; no dice CUAL la toca ni desde cuando.
                "reformas": c.get("reformas") or [],
            })
        salida["detalle"] = filas
    return salida


def _humano(d: dict) -> str:
    n = d["normas"]
    h = d["horizonte"]
    r = d["reformas_pendientes"]
    lineas = [
        "",
        "  CORPUS: " + ("LISTO" if d["listo"] else "NO LISTO"),
        f"  normas          : {n['sembradas']} de {n['esperadas']}"
        + (f"  (faltan {len(n['faltan'])})" if n["faltan"] else ""),
        f"  sembrado el     : {d['sellado']['mas_antiguo']} "
        f"-> {d['sellado']['mas_reciente']}"
        + (f"  ({d['sellado']['dias']} dias)"
           if d["sellado"]["dias"] is not None else ""),
        f"  llega hasta     : {h['hasta'] or '(no se sabe)'}"
        + (f"  ({h['norma']}); ejercicio completo {h['ejercicio_completo']}"
           if h["hasta"] else ""),
        f"  sin incorporar  : {r['normas_con']} de {r['de']} normas, "
        f"{r['preceptos_tocados']} precepto(s)"
        + (f"  [preguntado el {r['preguntado']}]" if r["preguntado"] else ""),
        f"  integridad      : "
        + ("cuadra" if d["cuadra"]
           else f"{len(d['integridad']['problemas'])} PROBLEMA(S)"),
    ]
    for p in d["integridad"]["problemas"][:5]:
        lineas.append(f"      - {p}")
    for a in d["avisos"]:
        lineas.append(f"  AVISO: {a}")
    lineas.append("")
    return "\n".join(lineas) + "\n"


def main(argv) -> int:
    ap = Argumentos(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--detalle", action="store_true",
                    help="ademas, norma a norma: preceptos, sello y reformas")
    ap.add_argument("--humano", action="store_true",
                    help="ademas, el resumen legible POR stderr")
    # UNA LLAMADA MAL HECHA ES UN FALLO, NO UN «NO LISTO». Argparse sale con 2
    # y sin JSON, y 2 aqui significa NO LISTO: quien lo consuma creeria que se
    # ha mirado el corpus y no cuadra, cuando nadie lo ha llegado a abrir.
    try:
        args = ap.parse_args(argv)
    except ErrorDeUso as e:
        return _fallo("no se ha entendido la llamada", str(e))

    # TODO ENVUELTO, Y AQUI ES DONDE SE ROMPE SI SE VA A ROMPER: un sellos.json
    # a medias, un `normas_del_corpus.json` que no es JSON, un permiso. Todas
    # esas tienen que salir como fallo y no como estado.
    try:
        estado = reunir(args.detalle)
    except Exception as e:                       # noqa: BLE001
        return _fallo("no se ha podido leer el estado del corpus",
                      f"{type(e).__name__}: {e}")

    estado["procedencia"] = procedencia(CORPUS)

    if args.humano:
        # A stderr, SIEMPRE. Si esto fuera a stdout romperia el contrato, y lo
        # romperia solo cuando alguien pasara `--humano`: el peor momento para
        # descubrirlo.
        try:
            sys.stderr.write(_humano(estado))
        except Exception:                        # noqa: BLE001
            pass          # el resumen legible es un extra: no puede tumbar nada

    _escribir(estado)
    return LISTO if estado["listo"] else NO_LISTO


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
