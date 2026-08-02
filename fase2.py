#!/usr/bin/env python3
"""FASE 2 - Buscar en el corpus y expandir por remisiones.

    python fase2.py buscar "deduccion del IVA de un turismo"
    python fase2.py buscar "deduccion de un turismo" --ejercicio 2023
    python fase2.py diagnostico

Que hace:
  1. Busca por palabras (indice invertido BM25F, sin IA y sin base de datos).
     El titulo pesa mas que el cuerpo. Las notas del BOE no se indexan.
  2. Expande por remisiones EN LOS DOS SENTIDOS, en su propio apartado:
     "menciona a" y "le mencionan". Nunca mezcladas con lo encontrado.
  3. Con --ejercicio, avisa arriba si el texto que se ensena no es el que
     aplicaba en ese ano.

Solo lee. No toca el JSONL de la fase 1.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from agente_fiscal import referencias as R
from agente_fiscal import texto as T
from agente_fiscal import vigencia as V
from agente_fiscal.indice import ErrorCorpus, Indice

RAIZ = Path(__file__).resolve().parent
# El corpus es el DIRECTORIO: se cargan todas las normas ingeridas,
# sin saber cuales ni cuantas.
CORPUS = RAIZ / "datos" / "corpus"
ANCHO = 78

# SOBRE LAS ABREVIATURAS (aqui hubo un intento fallido, queda escrito para que
# no se repita): se probo a expandir "IVA" -> "impuesto sobre el valor anadido".
# Sale mal. Mete tres palabras que estan en casi todos los articulos, y como
# BM25 suma por termino, un precepto que casa esas tres comunes adelanta al que
# casa las dos raras que de verdad importaban ("deduc", "turism"). Con la
# expansion activada, el articulo 95 se caia del podio en la consulta de
# control. Ademas no aporta nada: el corpus entero ES la ley del IVA, asi que
# "IVA" no distingue un articulo de otro. Se prefiere decir que la palabra no
# aparece y buscar con el resto.


def titulo(t: str) -> None:
    print("\n" + "=" * ANCHO)
    print(t)
    print("=" * ANCHO)


def apartado(t: str) -> None:
    print("\n" + t)
    print("-" * len(t))


def recorta(s: str, n: int) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def fragmento(registro: dict, raices: set[str], ejercicio: int | None) -> list[str]:
    """Las dos lineas del precepto que mas palabras de la consulta contienen.

    Con --ejercicio se recorta sobre la version que aplicaba ese ano, no sobre
    la de hoy: es la que hay que leer.
    """
    if ejercicio is not None:
        v = V.version_aplicable(registro, V.limites(ejercicio)[1])
        cuerpo = (v or {}).get("texto", "") or registro.get("texto_vigente", "")
    else:
        cuerpo = registro.get("texto_vigente", "")

    lineas = [l for l in cuerpo.split("\n")[1:] if l.strip()]
    if not lineas:
        lineas = [l for l in cuerpo.split("\n") if l.strip()]

    puntuadas = []
    for i, l in enumerate(lineas):
        tocados = set(T.tokenizar(l)) & raices
        if tocados:
            puntuadas.append((len(tocados), -i, l))
    puntuadas.sort(reverse=True)
    elegidas = [l for _, _, l in puntuadas[:2]] or lineas[:1]
    return [recorta(l, ANCHO - 6) for l in elegidas]


def _es_disposicion(registro: dict) -> bool:
    return registro["tipo"].startswith("disposicion")


def pinta_avisos(avisos, sangria: str = "   ") -> None:
    """Los avisos van arriba y se ven. Nunca en una nota al final."""
    for a in avisos:
        marca = "!! AVISO" if a.nivel == V.GRAVE else "-  nota "
        print(f"{sangria}{marca}: {a.texto}")


# ------------------------------------------------------------------ buscar


def modo_buscar(args) -> int:
    ix = Indice(CORPUS)
    grafo = R.GrafoRemisiones(ix.docs)

    consulta = args.consulta
    resultados, huerfanos = ix.buscar(consulta, tope=args.tope)
    raices, _, _ = ix.analizar_consulta(consulta)
    raices_set = set(raices)

    titulo(f"CONSULTA: {args.consulta}")
    print(f"corpus      : {len(ix.docs)} preceptos de {len(ix.normas)} cuerpo(s) normativo(s):")
    for _c in ix.normas.cuerpos.values():
        print(f"              · {_c.etiqueta}")
    print(f"terminos    : {', '.join(raices) or '(ninguno)'}")
    if args.ejercicio:
        print(f"ejercicio   : {args.ejercicio}")
    if huerfanos:
        # Nada falla en silencio: si una palabra no esta, se dice. Y se aclara
        # si la busqueda ha seguido con el resto, para que "no aparece IVA" no
        # se lea como "no ha encontrado nada".
        utiles = [r for r in raices if r not in huerfanos]
        cola = (f"; se ha buscado con el resto ({', '.join(utiles)})"
                if utiles else "; no queda ningun termino con el que buscar")
        print(f"NO APARECEN en el articulado: {', '.join(huerfanos)}{cola}")

    if not resultados:
        apartado("SIN RESULTADOS")
        if not raices:
            # Distinto problema y distinta solucion: aqui no es que no se
            # encuentre, es que no se ha llegado a buscar nada.
            print("  La consulta solo contiene palabras vacias (de, la, que...),")
            print("  que no se indexan. Escribe algun termino con contenido.")
        else:
            print("  Ninguna palabra de la consulta aparece en el articulado.")
            print("  Recuerda lo que hay cargado: " + ", ".join(
                c.etiqueta for c in ix.normas.cuerpos.values()))
            print("  Ni consultas de la DGT, ni TEAC, ni jurisprudencia.")
        return 3

    apartado(f"RESULTADOS DIRECTOS ({len(resultados)})")
    for i, res in enumerate(resultados, 1):
        reg = res.doc.registro
        avisos = V.avisos(reg, args.ejercicio)

        print(f"\n{i}. {reg['referencia']}  ·  {reg['rubrica'] or '(sin epigrafe)'}")
        print(f"   puntuacion {res.puntuacion:.3f}   "
              f"[{'+'.join(sorted(res.campos_tocados))}]")
        # Los avisos, antes del texto.
        pinta_avisos(avisos)
        print(f"   {V.resumen_version(reg, args.ejercicio)}")
        if reg["contexto"]:
            print(f"   en: {' > '.join(reg['contexto'])}")
        print(f"   {reg['url']}")
        for linea in fragmento(reg, raices_set, args.ejercicio):
            print(f"     | {linea}")

    if args.sin_expansion:
        return 0

    # ---------------------------------------------------------- expansion
    cuantos = min(args.expandir, len(resultados))
    apartado(
        f"EXPANSION POR REMISIONES (primeros {cuantos})"
    )
    print("Esto NO son resultados de la busqueda: son preceptos ligados a ellos.")
    print("Van aparte y etiquetados a proposito.")

    for res in resultados[:cuantos]:
        reg = res.doc.registro
        clave = res.doc.clave
        print(f"\n· {reg['referencia']}")

        hacia = grafo.menciona_a(clave)
        ocultos_ida = max(0, len(hacia) - args.tope_expansion)
        print(f"   MENCIONA A ({len(hacia)}):")
        if not hacia:
            print("     (ninguno dentro de esta ley)")
        for rem in hacia[: args.tope_expansion]:
            d = ix.por_clave[rem.destino].registro
            marca = _marca_fecha(d, args.ejercicio)
            print(f"     -> {d['referencia']:<30} {recorta(d['rubrica'], 30):<32}{marca}")
        if ocultos_ida:
            print(f"     ... y {ocultos_ida} mas sin mostrar "
                  f"(sube --tope-expansion para verlas todas)")

        # El sentido que se olvida y el que mas duele.
        # Las disposiciones van SIEMPRE primero: son las que meten la
        # excepcion, y son justo las que se perdian al recortar la lista.
        # En el articulo 20, con 20 remisiones entrantes, la disposicion
        # adicional sexta quedaba fuera del corte.
        atras = sorted(
            grafo.le_mencionan(clave),
            key=lambda r: (
                0 if _es_disposicion(ix.por_clave[r.origen].registro) else 1,
                ix.por_clave[r.origen].registro["posicion"],
            ),
        )
        ocultos = max(0, len(atras) - args.tope_expansion)
        print(f"   LE MENCIONAN ({len(atras)}):")
        if not atras:
            print("     (nadie dentro de esta ley)")
        for rem in atras[: args.tope_expansion]:
            o = ix.por_clave[rem.origen].registro
            marca = _marca_fecha(o, args.ejercicio)
            aviso = "  <-- DISPOSICION: aqui suele estar la excepcion" if _es_disposicion(o) else ""
            print(f"     <- {o['referencia']:<30} \"{recorta(rem.texto, 26):<28}\""
                  f"{marca}{aviso}")
        if ocultos:
            print(f"     ... y {ocultos} mas sin mostrar "
                  f"(sube --tope-expansion para verlas todas)")

        pendientes = grafo.pendientes_de(clave)
        if pendientes:
            print(f"   PENDIENTES ({len(pendientes)}) - fuera del corpus, sin resolver:")
            vistos = set()
            for rem in pendientes:
                etiqueta = (rem.etiqueta_destino, rem.norma_externa)
                if etiqueta in vistos:
                    continue
                vistos.add(etiqueta)
                destino = rem.norma_externa or "norma no identificada"
                print(f"     ?? {rem.etiqueta_destino} de {destino}: {rem.motivo}")

    return 0


def _marca_fecha(registro: dict, ejercicio: int | None) -> str:
    """Marca corta para no repetir el bloque de avisos en cada linea."""
    if ejercicio is None:
        return ""
    avisos = V.avisos(registro, ejercicio)
    graves = [a for a in avisos if a.nivel == V.GRAVE]
    return f"  !! {graves[0].clave}" if graves else ""


# ------------------------------------------------------------- diagnostico


def modo_diagnostico(args) -> int:
    """Estado del indice y del grafo. Lo que no se resuelve, contado."""
    ix = Indice(CORPUS)
    grafo = R.GrafoRemisiones(ix.docs)
    s = grafo.stats

    titulo("DIAGNOSTICO DE LA FASE 2")

    apartado("Indice")
    print(f"  preceptos indexados      : {len(ix.docs)}")
    print(f"  terminos distintos       : {len(ix.postings):,}")
    for campo, media in ix.long_media.items():
        print(f"  longitud media '{campo}'  : {media:.1f} palabras")
    print("  NO se indexan: notas_boe (historial) ni notas_editoriales.")

    apartado("Remisiones detectadas")
    print(f"  total                    : {s.total}")
    print(f"  resueltas en esta ley    : {s.resueltas}")
    print(f"  PENDIENTE (otra norma)   : {s.pendientes_externas}")
    print(f"  PENDIENTE (ambiguas)     : {s.pendientes_ambiguas}")
    print(f"  no encontradas           : {s.no_encontradas}")
    cobertura = 100 * s.resueltas / s.total if s.total else 0
    print(f"  cobertura                : {cobertura:.1f}%")

    apartado("Normas externas citadas (todas PENDIENTE, ninguna resuelta)")
    for norma, n in sorted(s.normas_externas.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>4}  {norma}")

    if s.sin_resolver:
        apartado("Remisiones sin resolver")
        for rem in s.sin_resolver:
            print(f"  - {rem.etiqueta_destino} (en {rem.origen}): {rem.motivo}")
    else:
        apartado("Remisiones sin resolver")
        print("  ninguna: toda remision o se resuelve o se marca PENDIENTE.")

    apartado("Preceptos mas citados por otros (donde miran todos)")
    ranking = Counter({c: len(grafo.le_mencionan(c)) for c in grafo.atras})
    for clave, n in ranking.most_common(10):
        reg = ix.por_clave[clave].registro
        print(f"  {n:>3} <- {reg['referencia']:<28} {recorta(reg['rubrica'], 40)}")

    apartado("Preceptos sin ninguna remision entrante ni saliente")
    sueltos = [
        d for d in ix.docs
        if not grafo.adelante.get(d.clave) and not grafo.atras.get(d.clave)
    ]
    print(f"  {len(sueltos)} de {len(ix.docs)}")
    for d in sueltos[:8]:
        print(f"    - {d.registro['referencia']}")
    return 0


# ------------------------------------------------------------------- cli


def main(argv: list[str]) -> int:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(
        description="Fase 2: busqueda y expansion por remisiones sobre el corpus.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = ap.add_subparsers(dest="modo", required=True)

    b = sub.add_parser("buscar", help="busca en el articulado")
    b.add_argument("consulta")
    b.add_argument("--ejercicio", type=int, default=None,
                   help="ano del caso (p.ej. 2023): activa los avisos de fecha")
    b.add_argument("--tope", type=int, default=5, help="resultados directos")
    b.add_argument("--expandir", type=int, default=3,
                   help="cuantos resultados se expanden por remisiones")
    b.add_argument("--tope-expansion", type=int, default=8, dest="tope_expansion",
                   help="maximo de remisiones que se listan por sentido")
    b.add_argument("--sin-expansion", action="store_true",
                   help="solo los resultados directos")

    sub.add_parser("diagnostico", help="estado del indice y del grafo")

    args = ap.parse_args(argv)

    # 'diagnostico' no tiene --ejercicio: se consulta con getattr.
    ejercicio = getattr(args, "ejercicio", None)
    if ejercicio is not None and not (1993 <= ejercicio <= 2100):
        print(f"[FALLO] ejercicio fuera de rango: {ejercicio}. "
              f"La Ley del IVA esta en vigor desde 1993.", file=sys.stderr)
        return 1

    try:
        if args.modo == "buscar":
            return modo_buscar(args)
        return modo_diagnostico(args)
    except ErrorCorpus as e:
        print(f"\n[FALLO DE CORPUS] {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrumpido.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
