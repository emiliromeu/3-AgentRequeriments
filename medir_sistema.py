#!/usr/bin/env python3
"""POR QUE NO SALEN LOS TRES [SISTEMA]. Cero red, cero API.

    .venv/bin/python medir_sistema.py

Los tres los etiqueto el bloque 5 el 14/08/2026: el analizador propone
vocabulario CORRECTO y el articulo que contesta no sale. No falta puente, falta
recuperacion. Esto mira por que.

  IRPF art. 122   autoliquidacion complementaria
  ISD  art.   3   donacion de dinero de padre a hijo
  ISD  art.  31   plazo de presentacion de la herencia

LOS TERMINOS NO SE ESCRIBEN AQUI: se leen del JSON que dejo el bloque 5. Son
los que propuso el modelo de verdad, ya pagados. Escribirlos a mano seria medir
otra cosa y creer que se mide esta.

QUE ENSEÑA, para cada uno:

  1. Que sale por delante, con la puntuacion DESGLOSADA POR CAMPO. El indice
     puntua tres campos con pesos distintos -titulo 4.0, contexto 0.8, cuerpo
     1.0- y el desglose es lo unico que dice si un articulo gana por su rubrica
     o por su texto.
  2. Que puntua el que deberia salir, y contra que pierde.
  3. Las tres sospechas, medidas: longitud, rubrica, y las puertas
     -filtro por impuesto y suelo de estatales-.

SIN FALLBACKS: si un termino no esta en el indice se dice, no se sustituye.
"""
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import banco                                    # noqa: E402
import fase4                                    # noqa: E402
from agente_fiscal import analizador as AN      # noqa: E402
from agente_fiscal import indice as IX          # noqa: E402
from agente_fiscal import texto as T           # noqa: E402

ANCHO = 96

# Los tres, por su consulta exacta tal como esta en el fichero de casos.
TRES = [
    "mi cliente olvido incluir unos rendimientos en la renta, como se corrige",
    "un padre quiere donar dinero a su hijo, tributa",
    "cuanto plazo hay para presentar el impuesto de una herencia",
]


def terminos_del_bloque5() -> dict:
    """Lo que propuso el modelo, leido del JSON del banco. No se inventa."""
    bancos = sorted(Path("datos/banco").glob("banco_*.json"))
    for ruta in reversed(bancos):
        d = json.loads(ruta.read_text(encoding="utf-8"))
        salida = {}
        for p in d.get("pruebas", []):
            if p.get("bloque") != "5" or "«" not in p.get("nombre", ""):
                continue
            m = re.search(r"terminos: (.+)$", p.get("obtenido", ""))
            if m:
                salida[p["nombre"].split("«")[1].rstrip("»")] = m.group(1)
        if len(salida) >= len(TRES):
            print(f"  terminos leidos de {ruta.name}\n")
            return salida
    raise SystemExit("No hay ningun banco con el bloque 5 ejecutado. Sin eso no "
                     "se puede medir: haria falta inventarse los terminos.")


def desglose(ix, doc, terminos: str) -> dict:
    """La puntuacion de un documento, campo a campo, con la formula del indice.

    Se recalcula aqui en vez de leerla de `Resultado` porque `Resultado` guarda
    el aporte POR TERMINO y lo que hace falta es POR CAMPO: es la unica forma
    de ver si un articulo gana por la rubrica o por el cuerpo.
    """
    raices = T.tokenizar(terminos, quitar_vacias=True)
    exactas = T.palabras_exactas(terminos)
    pesos = {r: 1.0 for r in raices}
    for e in exactas:
        pesos[IX.MARCA_EXACTA + e] = IX.PESO_EXACTO

    i_doc = ix.docs.index(doc)
    porcampo = {c: 0.0 for c in IX.PESOS_CAMPO}
    total = 0.0
    detalle = {}
    for termino, factor in pesos.items():
        idf = ix._idf(termino)
        if idf <= 0:
            continue
        post = ix.postings.get(termino, {}).get(i_doc)
        if not post:
            continue
        tf_tilde = 0.0
        trozo = {}
        for campo, frec in post.items():
            largo = doc.longitudes.get(campo, 0)
            medio = ix.long_media.get(campo, 1.0) or 1.0
            b = IX.B_CAMPO[campo]
            denom = 1 - b + b * (largo / medio)
            parte = IX.PESOS_CAMPO[campo] * frec / (denom or 1.0)
            tf_tilde += parte
            trozo[campo] = parte
        if tf_tilde <= 0:
            continue
        aporte = factor * idf * tf_tilde / (IX.K1 + tf_tilde)
        total += aporte
        for campo, parte in trozo.items():
            porcampo[campo] += aporte * parte / tf_tilde
        visible = termino[1:] if termino.startswith(IX.MARCA_EXACTA) else termino
        detalle[visible] = detalle.get(visible, 0.0) + aporte
    return {"total": total, "campos": porcampo, "terminos": detalle}


def etiqueta(ix, doc) -> str:
    rg = doc.registro
    cu = ix.normas.por_clave(rg["cuerpo_clave"])
    return f"{rg['referencia'].replace('Articulo ', 'art. '):22s} {(cu.nombre if cu else '?')[:26]:26s}"


def main() -> int:
    props = terminos_del_bloque5()
    ix, grafo = fase4.cargar_corpus()
    casos = {c["consulta"]: c for c in banco.leer_casos(banco.CASOS)}

    resumen = []
    for consulta in TRES:
        c = casos[consulta]
        terminos = props[consulta]
        cuerpo, _ = ix.normas.resolver(c["norma"])
        quiero = c["aceptables"]

        print("=" * ANCHO)
        print(f"{c.get('impuesto')} art. {'/'.join(quiero)}   «{consulta}»")
        print("=" * ANCHO)
        print(f"  terminos del analizador: {terminos}")

        # --- que termino existe siquiera en el corpus
        raices = T.tokenizar(terminos, quitar_vacias=True)
        huerfanos = sorted({r for r in raices if ix.df.get(r, 0) == 0})
        print(f"  terminos que NO estan en el corpus: {huerfanos or 'ninguno'}")

        # --- el documento que deberia salir
        objetivo = None
        for d in ix.docs:
            rg = d.registro
            if (rg["cuerpo_clave"] == cuerpo
                    and rg["referencia"].replace("Articulo ", "") in quiero):
                objetivo = d
                break
        if objetivo is None:
            print("  [!] el articulo esperado NO ESTA en el corpus")
            continue

        # --- 1. QUE SALE POR DELANTE
        res, _h, _r = fase4.recuperar(ix, grafo, terminos, c.get("impuesto") or "",
                                      tope=10, naturaleza=AN.FONDO)
        print(f"\n  LO QUE SALE (puntuacion desglosada por campo)")
        print(f"    {'#':>2} {'precepto':50s} {'total':>7} {'titulo':>7} "
              f"{'contxt':>7} {'cuerpo':>7}  rubrica")
        for i, r in enumerate(res[:6], 1):
            dg = desglose(ix, r.doc, terminos)
            cs = dg["campos"]
            print(f"    {i:>2} {etiqueta(ix, r.doc):50s} {dg['total']:>7.3f} "
                  f"{cs['titulo']:>7.3f} {cs['contexto']:>7.3f} {cs['cuerpo']:>7.3f}"
                  f"  {(r.doc.registro.get('rubrica') or '')[:30]}")

        # --- 2. QUE PUNTUA EL QUE DEBERIA SALIR
        dgo = desglose(ix, objetivo, terminos)
        cs = dgo["campos"]
        print(f"\n  EL QUE DEBERIA SALIR")
        print(f"       {etiqueta(ix, objetivo):50s} {dgo['total']:>7.3f} "
              f"{cs['titulo']:>7.3f} {cs['contexto']:>7.3f} {cs['cuerpo']:>7.3f}"
              f"  {(objetivo.registro.get('rubrica') or '')[:30]}")
        if dgo["terminos"]:
            top = sorted(dgo["terminos"].items(), key=lambda x: -x[1])[:5]
            print(f"       de donde saca lo poco que saca: "
                  + ", ".join(f"{k} {v:.2f}" for k, v in top))
        else:
            print("       NO PUNTUA NADA: ningun termino de la consulta le toca")

        primero = desglose(ix, res[0].doc, terminos)["total"] if res else 0.0
        print(f"       se queda en el {dgo['total'] / primero:.0%} del primero"
              if primero else "")

        # --- 3. LAS TRES SOSPECHAS
        print(f"\n  LAS SOSPECHAS, MEDIDAS")
        lo = objetivo.longitudes
        largos = [(r.doc.longitudes.get("cuerpo", 0)) for r in res[:5]]
        media = sum(largos) / len(largos) if largos else 0
        print(f"    longitud   objetivo cuerpo={lo.get('cuerpo', 0):>4} tokens · "
              f"titulo={lo.get('titulo', 0):>2} · media de los 5 primeros="
              f"{media:>6.1f}")
        rub = (objetivo.registro.get("rubrica") or "")
        raices_rub = set(T.tokenizar(rub, quitar_vacias=True))
        comunes = sorted(set(raices) & raices_rub)
        print(f"    rubrica    «{rub[:56]}»")
        print(f"               comparte con la consulta: {comunes or 'NADA'}")
        print(f"    contexto   {objetivo.registro.get('contexto')}")

        # las puertas
        sin_filtro, _h2 = ix.buscar(terminos, tope=200)
        puesto_libre = next((i for i, r in enumerate(sin_filtro, 1)
                             if r.doc is objetivo), None)
        con_filtro = next((i for i, r in enumerate(res, 1)
                           if r.doc is objetivo), None)
        print(f"    puertas    sin filtro de impuesto: puesto "
              f"{puesto_libre or 'fuera de 200'} · con filtro y suelo: "
              f"{con_filtro or 'fuera de 10'}")
        admitidos = ix.normas.admitidos_para(c.get("impuesto") or "")
        print(f"               el filtro DEJA DENTRO su cuerpo: "
              f"{'si' if admitidos is None or c.get('impuesto') in (admitidos or set()) else 'NO'}")

        resumen.append({
            "caso": f"{c.get('impuesto')} {'/'.join(quiero)}",
            "punt": dgo["total"], "primero": primero,
            "toca": bool(dgo["terminos"]),
            "rubrica_comparte": bool(comunes),
            "cuerpo": lo.get("cuerpo", 0), "media_rivales": media,
            "sin_filtro": puesto_libre, "con_filtro": con_filtro,
        })
        print()

    # ------------------------------------------------ ¿mismo mecanismo?
    print("=" * ANCHO)
    print("¿ES EL MISMO MECANISMO EN LOS TRES?")
    print("=" * ANCHO)
    print(f"  {'caso':14s} {'punt':>6} {'%1º':>5} {'toca?':>6} {'rubr?':>6} "
          f"{'largo':>6} {'rivales':>8} {'libre':>6} {'filtrado':>9}")
    for r in resumen:
        print(f"  {r['caso']:14s} {r['punt']:>6.2f} "
              f"{(r['punt'] / r['primero'] if r['primero'] else 0):>5.0%} "
              f"{'si' if r['toca'] else 'NO':>6} "
              f"{'si' if r['rubrica_comparte'] else 'NO':>6} "
              f"{r['cuerpo']:>6} {r['media_rivales']:>8.0f} "
              f"{str(r['sin_filtro'] or '-'):>6} {str(r['con_filtro'] or 'fuera'):>9}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
