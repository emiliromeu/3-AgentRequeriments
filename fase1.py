#!/usr/bin/env python3
"""FASE 1 - Bajar y trocear el corpus consolidado del BOE.

Tres modos:

  inspeccionar  Baja la norma, guarda el crudo y cuenta QUE ha llegado:
                etiquetas, cuantas de cada una y un bloque de ejemplo entero.
                Se ejecuta primero, siempre. La documentacion de una API y lo
                que la API devuelve no son la misma cosa.

  ingerir       Trocea el crudo a JSONL, una linea por precepto.

  verificar     Auditoria del JSONL: recuento por tipo, no reconocidos, sin
                texto, sin fecha, colisiones de referencia y muestra de 5.

Uso:
    python fase1.py inspeccionar BOE-A-1992-28740
    python fase1.py ingerir      BOE-A-1992-28740
    python fase1.py verificar    BOE-A-1992-28740

Por defecto `ingerir` y `verificar` reutilizan el ultimo crudo descargado.
Con --descargar fuerzan una descarga nueva (el crudo anterior no se toca).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from agente_fiscal import boe_api, bloques as B, parser as P

RAIZ = Path(__file__).resolve().parent
DIR_CRUDO = RAIZ / "datos" / "crudo"
DIR_CORPUS = RAIZ / "datos" / "corpus"

ANCHO = 78


# ------------------------------------------------------------------ salida


def titulo(texto: str) -> None:
    print("\n" + "=" * ANCHO)
    print(texto)
    print("=" * ANCHO)


def apartado(texto: str) -> None:
    print("\n" + texto)
    print("-" * len(texto))


def recorta(texto: str, n: int) -> str:
    texto = texto.replace("\n", " ")
    return texto if len(texto) <= n else texto[: n - 1] + "…"


# ------------------------------------------------------------------ comun


def cargar_metadatos(norma_id: str, descargar: bool) -> dict:
    """Metadatos de la norma. Devuelve el dict de `data[0]`."""
    ruta = None if descargar else boe_api.ultimo_crudo(norma_id, DIR_CRUDO, "metadatos")
    if ruta is None:
        r = boe_api.descargar_y_guardar(
            norma_id, "/metadatos", "application/json", DIR_CRUDO, "metadatos"
        )
        crudo = r.cuerpo
        print(f"  [red] metadatos descargados -> {r.ruta.name} ({r.tamano} bytes)")
    else:
        crudo = ruta.read_bytes()
        print(f"  [disco] metadatos reutilizados <- {ruta.name}")

    try:
        datos = json.loads(crudo.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise boe_api.ErrorBOE(
            f"Los metadatos de {norma_id} no son JSON valido: {e}\n"
            f"  Primeros bytes: {crudo[:200]!r}\n"
            f"  Si el identificador no existe, el BOE responde un error en XML.\n"
            f"  Comprueba el identificador y reintenta con --descargar."
        ) from e

    lista = datos.get("data") or []
    if not lista:
        raise boe_api.ErrorBOE(
            f"Los metadatos de {norma_id} vienen sin 'data'. "
            f"Lo mas probable es que ese identificador no exista en el BOE."
        )
    return lista[0]


def cargar_texto(norma_id: str, descargar: bool) -> bytes:
    """XML consolidado completo. OJO: este endpoint solo habla XML."""
    ruta = None if descargar else boe_api.ultimo_crudo(norma_id, DIR_CRUDO, "texto")
    if ruta is None:
        r = boe_api.descargar_y_guardar(
            norma_id, "/texto", "application/xml", DIR_CRUDO, "texto"
        )
        print(f"  [red] texto descargado -> {r.ruta.name} ({r.tamano:,} bytes)")
        return r.cuerpo
    print(f"  [disco] texto reutilizado <- {ruta.name}")
    return ruta.read_bytes()


def ruta_corpus(norma_id: str) -> Path:
    return DIR_CORPUS / f"{norma_id}.jsonl"


def ruta_descartes(norma_id: str) -> Path:
    return DIR_CORPUS / f"{norma_id}.descartados.jsonl"


# ------------------------------------------------------------------ modo 1


def modo_inspeccionar(norma_id: str, descargar: bool) -> int:
    """Baja y describe. No trocea, no interpreta: solo cuenta lo que hay."""
    titulo(f"INSPECCIONAR  {norma_id}")
    print("Objetivo: ver la estructura real antes de escribir ningun troceo.")

    apartado("1. Descarga")
    meta = cargar_metadatos(norma_id, descargar)
    xml_bytes = cargar_texto(norma_id, descargar)

    # El indice y el analisis se guardan en crudo aunque la fase 1 no los use:
    # descargarlos ahora sale gratis y evita volver a pedirlos mas adelante.
    for recurso, etiqueta in (("/texto/indice", "indice"), ("/analisis", "analisis")):
        if descargar or boe_api.ultimo_crudo(norma_id, DIR_CRUDO, etiqueta) is None:
            try:
                r = boe_api.descargar_y_guardar(
                    norma_id, recurso, "application/json", DIR_CRUDO, etiqueta
                )
                print(f"  [red] {etiqueta} guardado -> {r.ruta.name} ({r.tamano:,} bytes)")
            except boe_api.ErrorBOE as e:
                print(f"  [AVISO] no se pudo traer {etiqueta}: {e}")
        else:
            print(f"  [disco] {etiqueta} ya estaba en crudo")

    apartado("2. La norma")
    print(f"  identificador   : {meta.get('identificador')}")
    print(f"  titulo          : {recorta(meta.get('titulo', ''), 60)}")
    print(f"  rango           : {(meta.get('rango') or {}).get('texto')}")
    print(f"  fecha vigencia  : {P.fecha_iso(meta.get('fecha_vigencia'))}")
    print(f"  consolidacion   : {(meta.get('estado_consolidacion') or {}).get('texto')}")
    print(f"  derogada        : {meta.get('estatus_derogacion')}")
    print(f"  ultima actualiz.: {(meta.get('fecha_actualizacion') or '')[:8]}")
    print(f"  HTML BOE        : {meta.get('url_html_consolidada')}")

    import xml.etree.ElementTree as ET

    try:
        raiz = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"\n  [FALLO] el XML no parsea: {e}")
        return 1

    nodos = raiz.findall(".//bloque")

    apartado("3. Que etiquetas trae el XML (y cuantas)")
    etiquetas: Counter = Counter()
    for el in raiz.iter():
        etiquetas[el.tag] += 1
    for tag, n in etiquetas.most_common():
        print(f"  {tag:<14} {n:>7,}")

    apartado("4. Atributos de <bloque> y de <version>")
    at_bloque: Counter = Counter()
    at_version: Counter = Counter()
    for bl in nodos:
        for k in bl.keys():
            at_bloque[k] += 1
        for v in bl.findall("version"):
            for k in v.keys():
                at_version[k] += 1
    print("  bloque :", ", ".join(f"{k}({n})" for k, n in at_bloque.most_common()))
    print("  version:", ", ".join(f"{k}({n})" for k, n in at_version.most_common()))

    apartado("5. Tipos de bloque declarados por el BOE")
    for tipo, n in Counter(b.get("tipo") for b in nodos).most_common():
        print(f"  tipo={tipo!r:<16} {n:>5}")

    apartado("6. Clases de <p> (aqui se ve que es norma y que no)")
    clases: Counter = Counter()
    for p in raiz.iter("p"):
        clases[p.get("class") or "(sin class)"] += 1
    for c, n in clases.most_common():
        marca = "  <-- NO es texto normativo: historial de reformas" if c.startswith("nota_pie") else ""
        print(f"  {c:<22} {n:>7,}{marca}")

    apartado("7. Versiones por bloque")
    n_ver = [len(b.findall("version")) for b in nodos]
    total_ver = sum(n_ver)
    print(f"  bloques                 : {len(nodos)}")
    print(f"  versiones totales       : {total_ver}")
    print(f"  maximo de versiones     : {max(n_ver) if n_ver else 0}")
    print(f"  bloques con 1 sola vers.: {sum(1 for n in n_ver if n == 1)}")
    print(f"  bloques con >1 version  : {sum(1 for n in n_ver if n > 1)}")
    print(f"  bloques con 0 versiones : {sum(1 for n in n_ver if n == 0)}")

    apartado("8. Como clasifica nuestro parser estos bloques")
    resumen: Counter = Counter()
    sin_reconocer = []
    for bl in nodos:
        cls = B.clasificar(bl.get("titulo") or "", bl.get("id") or "", bl.get("tipo") or "")
        resumen[cls.tipo] += 1
        if cls.tipo == B.DESCONOCIDO:
            sin_reconocer.append((bl.get("id"), bl.get("titulo"), cls.motivo))
    for tipo, n in resumen.most_common():
        print(f"  {B.ETIQUETA_TIPO.get(tipo, tipo):<26} {n:>5}")
    if sin_reconocer:
        print(f"\n  [AVISO] {len(sin_reconocer)} bloque(s) sin reconocer:")
        for bid, tit, motivo in sin_reconocer[:10]:
            print(f"    - id={bid!r} titulo={tit!r}: {motivo}")

    apartado("9. Un bloque entero, tal cual llega (art. 95, el de la comprobacion)")
    muestra = None
    for bl in nodos:
        if (bl.get("titulo") or "").strip().lower().startswith("artículo 95"):
            muestra = bl
            break
    if muestra is None:
        muestra = nodos[len(nodos) // 2]
        print("  [AVISO] no aparece el articulo 95; se muestra otro bloque.")

    crudo_bloque = ET.tostring(muestra, encoding="unicode")
    print(f"  id={muestra.get('id')!r} tipo={muestra.get('tipo')!r} "
          f"titulo={muestra.get('titulo')!r}")
    print(f"  versiones: {len(muestra.findall('version'))}")
    for v in muestra.findall("version"):
        print(
            f"    - publicacion={P.fecha_iso(v.get('fecha_publicacion'))} "
            f"vigencia={P.fecha_iso(v.get('fecha_vigencia'))} "
            f"norma_origen={v.get('id_norma')}"
        )
    print("\n  --- XML crudo del bloque (primeros 1.800 caracteres) ---")
    for linea in crudo_bloque[:1800].splitlines():
        print("  " + linea)
    print("  --- fin de la muestra ---")

    apartado("10. Trampas detectadas en este corpus")
    trampas = []
    for bl in nodos:
        bid = bl.get("id") or ""
        tit = (bl.get("titulo") or "").strip()
        cls = B.clasificar(tit, bid, bl.get("tipo") or "")
        if cls.tipo == B.ARTICULO and not cls.es_rango and cls.numero:
            esperado = "a" + cls.numero_norm.replace(" ", "")
            if bid != esperado:
                trampas.append((bid, tit))
    print(f"  Bloques cuyo id NO coincide con su numero de articulo: {len(trampas)}")
    for bid, tit in trampas[:8]:
        print(f"    id={bid!r:<24} es en realidad {tit!r}")
    if trampas:
        print("\n  Conclusion: la referencia canonica se deriva del atributo")
        print("  'titulo', nunca del 'id'. El id solo vale como ancla del enlace.")

    print("\n" + "=" * ANCHO)
    print("Inspeccion terminada. El crudo esta en datos/crudo/ y no se borra.")
    print("Siguiente paso:  python fase1.py ingerir " + norma_id)
    print("=" * ANCHO)
    return 0


# ------------------------------------------------------------------ modo 2


def modo_ingerir(norma_id: str, descargar: bool) -> int:
    titulo(f"INGERIR  {norma_id}")

    apartado("1. Origen")
    meta = cargar_metadatos(norma_id, descargar)
    xml_bytes = cargar_texto(norma_id, descargar)
    norma_titulo = meta.get("titulo", "")
    url_html = meta.get("url_html_consolidada") or (
        f"https://www.boe.es/buscar/act.php?id={norma_id}"
    )

    apartado("2. Troceo por precepto")
    try:
        citables, descartados = P.trocear(xml_bytes, norma_id, norma_titulo, url_html)
    except P.ErrorParseo as e:
        print(f"  [FALLO] {e}")
        return 1

    DIR_CORPUS.mkdir(parents=True, exist_ok=True)
    destino = ruta_corpus(norma_id)
    with destino.open("w", encoding="utf-8") as fh:
        for r in citables:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Lo no citable no se tira: se escribe aparte para poder auditarlo.
    destino_desc = ruta_descartes(norma_id)
    with destino_desc.open("w", encoding="utf-8") as fh:
        for r in descartados:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    por_tipo = Counter(r["tipo"] for r in citables)
    for tipo, n in por_tipo.most_common():
        print(f"  {B.ETIQUETA_TIPO.get(tipo, tipo):<26} {n:>5}")

    n_ver = sum(r["n_versiones"] for r in citables)
    n_notas = sum(len(r["notas_boe"]) for r in citables)
    con_incid = [r for r in citables if r["incidencias"]]

    print(f"\n  preceptos citables      : {len(citables)}")
    print(f"  versiones guardadas     : {n_ver}")
    print(f"  notas del BOE (reformas): {n_notas}")
    print(f"  bloques no citables     : {len(descartados)} "
          f"(encabezados, preambulo, firma)")
    print(f"\n  corpus      -> {destino}")
    print(f"  descartados -> {destino_desc}")

    if con_incid:
        print(f"\n  [AVISO] {len(con_incid)} precepto(s) con incidencias:")
        for r in con_incid[:10]:
            print(f"    - {r['referencia']} (id={r['id_bloque']}): "
                  f"{'; '.join(r['incidencias'])}")
        if len(con_incid) > 10:
            print(f"    ... y {len(con_incid) - 10} mas (se ven todas en 'verificar')")

    print("\nSiguiente paso:  python fase1.py verificar " + norma_id)
    return 0


# ------------------------------------------------------------------ modo 3


def modo_verificar(norma_id: str) -> int:
    titulo(f"VERIFICAR  {norma_id}")

    destino = ruta_corpus(norma_id)
    if not destino.exists():
        print(f"  [FALLO] no existe {destino}")
        print(f"  Ejecuta antes:  python fase1.py ingerir {norma_id}")
        return 1

    registros = [json.loads(l) for l in destino.read_text(encoding="utf-8").splitlines() if l.strip()]
    desc_path = ruta_descartes(norma_id)
    descartados = []
    if desc_path.exists():
        descartados = [
            json.loads(l) for l in desc_path.read_text(encoding="utf-8").splitlines() if l.strip()
        ]

    total_bloques = len(registros) + len(descartados)

    apartado("1. Recuento de bloques")
    print(f"  bloques en el XML de origen : {total_bloques}")
    print(f"  reconocidos como citables   : {len(registros)}")
    print(f"  no citables (por diseno)    : {len(descartados)}")

    apartado("2. Por tipo")
    por_tipo = Counter(r["tipo"] for r in registros)
    n_art = por_tipo.get(B.ARTICULO, 0)
    n_disp = sum(por_tipo.get(t, 0) for t in B.TIPOS_DISPOSICION)
    for tipo, n in por_tipo.most_common():
        print(f"  {B.ETIQUETA_TIPO.get(tipo, tipo):<26} {n:>5}")
    print(f"  {'-' * 26} {'-' * 5}")
    print(f"  {'reconocidos como articulo':<26} {n_art:>5}")
    print(f"  {'reconocidos como disposicion':<26} {n_disp:>5}")

    print("\n  Desglose de los no citables:")
    for tipo, n in Counter(r["tipo"] for r in descartados).most_common():
        print(f"    {B.ETIQUETA_TIPO.get(tipo, tipo):<24} {n:>5}")

    apartado("3. Controles de integridad")
    sin_reconocer = [r for r in registros + descartados if r["tipo"] == B.DESCONOCIDO]
    sin_texto = [r for r in registros if not (r["texto_vigente"] or "").strip()]
    sin_version = [r for r in registros if r["n_versiones"] == 0]
    sin_fecha = [r for r in registros if not all(r["fechas_vigencia"])]
    sin_url = [r for r in registros if "#" not in r["url"]]
    sin_ref = [r for r in registros if not r["referencia"].strip()]
    suprimidos = [r for r in registros if r.get("suprimido")]
    caducados = [r for r in registros if r.get("caducado_desde")]
    con_avisos = [r for r in registros if r.get("avisos")]
    fecha_corregida = [
        r for r in registros if any(v.get("vigencia_corregida") for v in r["versiones"])
    ]

    controles = [
        ("bloques sin reconocer", sin_reconocer, True),
        ("preceptos sin texto", sin_texto, True),
        ("preceptos sin ninguna version", sin_version, True),
        ("preceptos con alguna fecha vacia", sin_fecha, True),
        ("preceptos sin enlace profundo", sin_url, True),
        ("preceptos sin referencia canonica", sin_ref, True),
        ("preceptos suprimidos/derogados", suprimidos, False),
        ("preceptos caducados (con fecha fin)", caducados, False),
        ("preceptos con rarezas anotadas", con_avisos, False),
        ("preceptos con fecha corregida (errata BOE)", fecha_corregida, False),
    ]
    for etiqueta, lista, es_fallo in controles:
        marca = "OK  " if not lista else ("FALLO" if es_fallo else "nota ")
        print(f"  [{marca}] {etiqueta:<40} {len(lista):>5}")

    if caducados:
        print("\n  Preceptos con fecha de caducidad (dejaron de aplicarse):")
        for r in caducados:
            print(f"    - {r['referencia']:<28} caduco el {r['caducado_desde']}")
    if fecha_corregida:
        print("\n  Erratas de fecha en el origen (se conserva el valor crudo):")
        for r in fecha_corregida:
            for v in r["versiones"]:
                if v.get("vigencia_corregida"):
                    print(f"    - {r['referencia']}: BOE dice {v['fecha_vigencia']}, "
                          f"se usa {v['fecha_vigencia_efectiva']} "
                          f"(publicado {v['fecha_publicacion']})")
    if con_avisos:
        print("\n  Rarezas anotadas (reconocidas, pero conviene saberlas):")
        for r in con_avisos:
            for a in r["avisos"]:
                print(f"    - {r['referencia']}: {a}")

    for etiqueta, lista, es_fallo in controles:
        if lista and es_fallo:
            print(f"\n  Detalle de '{etiqueta}':")
            for r in lista[:10]:
                print(f"    - {r['referencia']!r} id={r['id_bloque']!r} "
                      f"{'; '.join(r.get('incidencias') or []) or '(sin detalle)'}")
            if len(lista) > 10:
                print(f"    ... y {len(lista) - 10} mas")

    apartado("4. Colisiones de referencia")
    # Dos preceptos con la misma clave harian que una cita apunte a dos sitios.
    por_clave = defaultdict(list)
    for r in registros:
        por_clave[r["clave"]].append(r)
    colisiones = {k: v for k, v in por_clave.items() if len(v) > 1}
    if not colisiones:
        print("  [OK  ] cada precepto tiene una referencia canonica unica")
    else:
        print(f"  [FALLO] {len(colisiones)} referencia(s) duplicada(s):")
        for k, v in list(colisiones.items())[:10]:
            print(f"    - {k!r} -> {[x['id_bloque'] for x in v]}")

    apartado("5. Cobertura temporal")
    todas = [f for r in registros for f in r["fechas_vigencia"] if f]
    multiv = [r for r in registros if r["n_versiones"] > 1]
    print(f"  versiones guardadas        : {sum(r['n_versiones'] for r in registros)}")
    print(f"  preceptos con >1 version   : {len(multiv)}")
    print(f"  fecha de vigencia mas antigua: {min(todas) if todas else '-'}")
    print(f"  fecha de vigencia mas reciente: {max(todas) if todas else '-'}")
    print(f"  notas de reforma del BOE   : {sum(len(r['notas_boe']) for r in registros)}")

    apartado("6. Muestra de 5 preceptos para leer")
    # Muestra deliberadamente variada: no las 5 primeras, que serian 5 articulos
    # iniciales y no ensenarian nada.
    def busca(pred):
        return next((r for r in registros if pred(r)), None)

    elegidos = [
        busca(lambda r: r["referencia"] == "Articulo 95"),
        busca(lambda r: r["tipo"] == B.DISP_ADICIONAL),
        busca(lambda r: r["tipo"] == B.DISP_TRANSITORIA),
        busca(lambda r: r["n_versiones"] >= 4),
        busca(lambda r: r["id_bloque"] != "a" + r["numero_norm"].replace(" ", "")
              and r["tipo"] == B.ARTICULO and not r["es_rango"]),
    ]
    vistos = set()
    for r in elegidos:
        if r is None or r["id_bloque"] in vistos:
            continue
        vistos.add(r["id_bloque"])
        print(f"\n  {'=' * 70}")
        print(f"  referencia   : {r['referencia']}   [{B.ETIQUETA_TIPO[r['tipo']]}]")
        print(f"  rubrica      : {r['rubrica'] or '(sin epigrafe)'}")
        print(f"  id_bloque    : {r['id_bloque']}")
        print(f"  contexto     : {' > '.join(r['contexto']) or '(raiz)'}")
        print(f"  enlace       : {r['url']}")
        print(f"  versiones    : {r['n_versiones']}  fechas: "
              f"{', '.join(r['fechas_vigencia'])}")
        print(f"  vigente desde: {r['vigente_desde']}")
        print(f"  caracteres   : {len(r['texto_vigente']):,}")
        if r["notas_boe"]:
            print(f"  notas BOE    : {len(r['notas_boe'])}, p.ej. "
                  f"{recorta(r['notas_boe'][0]['texto'], 90)}")
        print("  texto vigente (primeras 3 lineas):")
        for linea in r["texto_vigente"].split("\n")[:3]:
            print(f"    | {recorta(linea, 72)}")

    apartado("7. Veredicto")
    fallos = sum(len(l) for _, l, es_fallo in controles if es_fallo) + len(colisiones)
    if fallos == 0:
        print("  FASE 1 CORRECTA: todos los bloques reconocidos, todos los")
        print("  preceptos con texto, fechas, referencia unica y enlace.")
    else:
        print(f"  ATENCION: {fallos} problema(s). Revisa el detalle de arriba.")
    return 0 if fallos == 0 else 2


# ------------------------------------------------------------------ cli


def main(argv: list[str]) -> int:
    # En consolas de Windows la codificacion por defecto no cubre todo lo que
    # trae el BOE ("«», º, tildes). Sin esto, imprimir un articulo puede
    # reventar el programa por un simple caracter.
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(
        description="Fase 1: descarga y troceo del BOE consolidado.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("modo", choices=["inspeccionar", "ingerir", "verificar"])
    ap.add_argument("norma_id", help="p.ej. BOE-A-1992-28740")
    ap.add_argument(
        "--descargar",
        action="store_true",
        help="fuerza descarga nueva en vez de reutilizar el ultimo crudo",
    )
    args = ap.parse_args(argv)

    try:
        if args.modo == "inspeccionar":
            return modo_inspeccionar(args.norma_id, args.descargar)
        if args.modo == "ingerir":
            return modo_ingerir(args.norma_id, args.descargar)
        return modo_verificar(args.norma_id)
    except boe_api.ErrorBOE as e:
        print(f"\n[FALLO BOE] {e}", file=sys.stderr)
        return 1
    except P.ErrorParseo as e:
        print(f"\n[FALLO DE TROCEO] {e}", file=sys.stderr)
        return 1
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(
            f"\n[FALLO] un fichero crudo esta corrupto o no es lo que se esperaba: {e}\n"
            f"  Revisa datos/crudo/{args.norma_id}/ y vuelve a bajar con --descargar.\n"
            f"  El crudo antiguo no se borra: quedara al lado del nuevo.",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        print("\nInterrumpido.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
