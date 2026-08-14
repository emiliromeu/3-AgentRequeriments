#!/usr/bin/env python3
"""¿DESEMPATA EL NUMERO DE ARTICULO ENTRE EL RD Y EL REGLAMENTO QUE APRUEBA?
Cero red, cero API.

    .venv/bin/python medir_desempate.py

LA DEUDA. La abreviatura `RD` / `RDLeg` es la mayor que queda: 68 consultas de
128 no se pueden encontrar por ella. Expandirla esta MEDIDO y DECIDIDO desde
hace semanas -recupera 152 y pierde 96- asi que no se aplica: perder 96 citas
bien resueltas para ganar 152 no es un cambio, es una permuta.

EL ANGULO QUE NO SE HABIA PROBADO. Ese empate no es sobre QUE NORMA: es sobre
QUE CUERPO del mismo documento. Al expandir «RD 439/2007» la designacion apunta
al decreto -cuerpo #0- y la sigla RIRPF al reglamento -cuerpo #1-; como no hay
unanimidad, `_resolver_designacion` declina. Pero un RD aprobatorio tiene UNOS
POCOS articulos -a veces uno, el «unico»- y el reglamento que aprueba tiene
decenas. Asi que «RD 439/2007 art. 22» solo puede ser el reglamento.

QUE MIDE, y en este orden porque el ultimo es el que manda:

  1. Cuantas de las 96 que hoy se pierden salva el desempate.
  2. Cuantas quedan ambiguas DE VERDAD: el numero existe en los dos cuerpos.
  3. LA FOTO DE SIEMPRE: de las que hoy resuelven, cuantas cambian. Tiene que
     ser CERO.
  4. Cero mal resueltas: ninguna cita apuntando a un cuerpo donde ese articulo
     no existe.

NO APLICA NADA. Solo mide, sobre la despensa de este disco y con el mismo
`preceptos()` que usa el agente.

SIN FALLBACKS: si una consulta no se puede leer, se cuenta como no leida.
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import fase4                                    # noqa: E402
from agente_fiscal import dgt as D              # noqa: E402

ANCHO = 92


def articulos_por_cuerpo(ix) -> dict:
    """{clave_cuerpo: {numeros de articulo}} leido del corpus."""
    salida = defaultdict(set)
    for d in ix.docs:
        r = d.registro
        if r.get("tipo") == "articulo":
            salida[r["cuerpo_clave"]].add(str(r.get("numero_norm") or
                                              r.get("numero") or "").strip())
    return salida


def hermanos(ix) -> dict:
    """{norma_id: [claves de sus cuerpos]}. Los documentos con mas de uno."""
    porn = defaultdict(list)
    for c in ix.normas.cuerpos:
        porn[c.split("#")[0]].append(c)
    return {k: sorted(v) for k, v in porn.items() if len(v) > 1}


def main() -> int:
    ix, _g = fase4.cargar_corpus()
    N = ix.normas
    arts = articulos_por_cuerpo(ix)
    duo = hermanos(ix)

    print("=" * ANCHO)
    print("LOS DOCUMENTOS CON DOS CUERPOS, que son donde vive el empate")
    print("=" * ANCHO)
    print(f"  {'documento':22s} {'cuerpo':24s} {'arts':>5}  nombre")
    for nid, claves in sorted(duo.items()):
        for c in claves:
            cu = N.por_clave(c)
            print(f"  {nid:22s} {c.split('#')[1]:24s} {len(arts.get(c, set())):>5}"
                  f"  {(cu.nombre if cu else '?')[:44]}")

    # EL DESEMPATE, tal como se aplicaria: entre cuerpos DEL MISMO documento,
    # se queda el que tiene ese numero de articulo. Si lo tienen los dos o
    # ninguno, no se desempata.
    def desempatar(claves: set, numero: str) -> str:
        docs = {c.split("#")[0] for c in claves}
        if len(docs) != 1:
            return ""                    # normas distintas: esto no lo toca
        num = str(numero).strip()
        tienen = [c for c in claves if num in arts.get(c, set())]
        return tienen[0] if len(tienen) == 1 else ""

    # LA EXPANSION, SIMULADA. Hoy «RD 439/2007» NO resuelve -se comprobo-, asi
    # que el empate de las 96 no existe todavia: aparece EN CUANTO se expande.
    # Medir solo lo de hoy contestaria otra pregunta.
    import re
    _RE_RDLEG = re.compile(r"\bRD\s*-?\s*Leg\.?\s*(\d+/\d{4})", re.I)
    _RE_RD = re.compile(r"\bRD\.?\s+(\d+/\d{4})", re.I)

    def expandir(texto: str) -> str:
        texto = _RE_RDLEG.sub(r"Real Decreto Legislativo \1", texto)
        return _RE_RD.sub(r"Real Decreto \1", texto)

    def resuelve(desig: str, con_expansion: bool) -> set:
        d = expandir(desig) if con_expansion else desig
        cands = [d] + D._RE_NORMA_EXPLICITA.findall(d)
        cands += [x.strip() for x in d.split(",") if x.strip()]
        out = set()
        for cand in cands:
            clave, _m = N.resolver(cand)
            if clave:
                out.add(clave)
        return out

    cache = D.CacheDGT()
    todas = cache.todas()
    print(f"\n  consultas en la despensa: {len(todas)}")

    # ------------------------------------------------ el barrido
    hoy_resuelve = hoy_pierde = 0
    salvadas, ambiguas, cambian, malas = [], [], [], []
    otro_documento = 0

    gana_expansion = pierde_expansion = 0
    for c in todas:
        try:
            preceptos = c.preceptos(N)
        except Exception:                        # noqa: BLE001
            continue
        for p in preceptos:
            desig = getattr(p, "norma_bruta", "") or ""
            numero = str(getattr(p, "numero", "") or "").strip()
            if not numero:
                continue

            hoy = resuelve(desig, False)          # A · como esta el sistema
            exp = resuelve(desig, True)           # B · con la abreviatura leida

            if len(hoy) == 1:
                hoy_resuelve += 1

            # B: que hace la expansion SOLA, que es lo ya medido (152/96).
            if len(hoy) != 1 and len(exp) == 1:
                gana_expansion += 1
            if len(hoy) == 1 and len(exp) != 1:
                pierde_expansion += 1

            # C: expansion MAS desempate.
            if len(exp) == 1:
                final = next(iter(exp))
            elif len(exp) > 1:
                final = desempatar(exp, numero)
            else:
                final = ""

            # LA FOTO: lo que hoy resuelve no puede cambiar de cuerpo.
            if len(hoy) == 1:
                antes = next(iter(hoy))
                if final and final != antes:
                    cambian.append((c.numero, desig, numero, antes, final))
                continue

            if len(exp) < 2:
                continue                          # no hay empate que romper

            hoy_pierde += 1
            docs = {x.split("#")[0] for x in exp}
            if len(docs) != 1:
                otro_documento += 1
                continue
            if final:
                if numero in arts.get(final, set()):
                    salvadas.append((c.numero, desig, numero, final))
                else:
                    malas.append((c.numero, desig, numero, final))
            else:
                en_ambos = [x for x in exp if numero in arts.get(x, set())]
                ambiguas.append((c.numero, desig, numero,
                                 "en los dos" if len(en_ambos) > 1
                                 else "en ninguno"))

    print("\n" + "=" * ANCHO)
    print("LOS NUMEROS")
    print("=" * ANCHO)
    print(f"  preceptos que HOY resuelven                            "
          f": {hoy_resuelve}")
    print(f"\n  B · SOLO EXPANDIENDO LA ABREVIATURA (lo ya medido)")
    print(f"      gana                                               "
          f": {gana_expansion}")
    print(f"      PIERDE (empate cuerpo #0 / #1)                     "
          f": {pierde_expansion}")
    print(f"\n  C · EXPANSION + DESEMPATE POR NUMERO DE ARTICULO")
    print(f"      empates a romper                                   "
          f": {hoy_pierde}")
    print(f"    de esos, empate entre DOCUMENTOS distintos "
          f"(no los toca)      : {otro_documento}")
    print(f"    SALVADOS por el desempate                              "
          f": {len(salvadas)}")
    print(f"    siguen AMBIGUOS de verdad                              "
          f": {len(ambiguas)}")
    if ambiguas:
        m = Counter(x[3] for x in ambiguas)
        print(f"       por que: {dict(m)}")

    print(f"\n  DE LAS QUE HOY RESUELVEN, CUANTAS CAMBIAN : {len(cambian)}"
          + ("   <-- TIENE QUE SER CERO" if cambian else "   (cero, como debe)"))
    for x in cambian[:10]:
        print(f"       {x[0]} «{x[1][:34]}» art.{x[2]}  {x[3]} -> {x[4]}")

    print(f"  MAL RESUELTAS (articulo que no existe ahi): {len(malas)}"
          + ("   <-- INVARIANTE ROTO" if malas else "   (cero)"))
    for x in malas[:10]:
        print(f"       {x[0]} «{x[1][:34]}» art.{x[2]} -> {x[3]}")

    if salvadas:
        print(f"\n  MUESTRA DE LAS SALVADAS")
        for x in salvadas[:12]:
            cu = N.por_clave(x[3])
            print(f"    {x[0]:10s} «{x[1][:36]:38s}» art.{x[2]:>6s} -> "
                  f"{(cu.nombre if cu else x[3])[:34]}")

    print("\n" + "=" * ANCHO)
    total_empate = len(salvadas) + len(ambiguas)
    if total_empate:
        print(f"EL DESEMPATE RESUELVE {len(salvadas)} de {total_empate} "
              f"({100*len(salvadas)/total_empate:.0f}%) de los empates "
              f"dentro del mismo documento")
    else:
        print("NO HAY NINGUN EMPATE DENTRO DEL MISMO DOCUMENTO EN LA DESPENSA")
    print("=" * ANCHO)
    return 0


if __name__ == "__main__":
    sys.exit(main())
