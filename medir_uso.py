#!/usr/bin/env python3
"""EL USO DE ESTE EQUIPO, EN NUMEROS. No lo abras a mano: doble clic en
`medir_uso.bat` (Windows) o `medir_uso.command` (Mac).

    .venv/bin/python medir_uso.py

POR QUE EXISTE. Las mediciones de uso se estaban haciendo sobre el Mac del
despacho, y ahi casi todo son pruebas mias de IVA. Las consultas que motivaron
el feedback -«a la segunda ya no encuentran criterio»- pasaron en el PC de la
oficina, y esas trazas NO VIAJAN: son dudas reales de clientes y se quedan
donde se hicieron. Sin poder ejecutar la medicion alli, cualquier decision
sobre que sembrar se toma sobre el uso de mi maquina.

NO IMPRIME NI UNA PREGUNTA. Es la misma regla que `medir_hilo`: lo que se trae
es LA CUENTA, no las dudas. Aqui se cuentan articulos de la ley -«art. 80 de la
Ley 37/1992»- que son referencias publicas, no lo que preguntaron los clientes.
Aun asi la salida dice al principio que contiene y que no, para que quien la
copie sepa lo que esta mandando.

SALIDA DE UN TIRON, en ASCII y sin tildes: se selecciona entera con el raton y
se pega en un mensaje. La consola de Windows no siempre va en UTF-8 y una tilde
mal codificada estropea la linea.

CERO RED Y CERO API. Solo lee ficheros de este disco.
"""
from __future__ import annotations

import io
import json
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

ANCHO = 68

# La consola de Windows suele ir en cp850. Se fuerza a que no reviente por un
# caracter raro en vez de perder la medicion entera.
try:
    sys.stdout.reconfigure(errors="replace")
except Exception:                                # noqa: BLE001
    pass


def barra(t: str = "") -> None:
    print("=" * ANCHO)
    if t:
        print(f"  {t}")
        print("=" * ANCHO)


def main() -> int:
    barra("USO DE ESTE EQUIPO")
    print()
    print("  Esto se puede copiar entero y mandarselo a Emili.")
    print()
    print("  LLEVA   : cuentas, y numeros de articulo de la ley.")
    print("  NO LLEVA: ni una pregunta, ni nada de ningun cliente.")
    print()

    try:
        import fase4
        from agente_fiscal import dgt as D
        from agente_fiscal import cola as C
        ix, _g = fase4.cargar_corpus()
        N = ix.normas
    except Exception as e:                       # noqa: BLE001
        print(f"  No se ha podido leer el corpus: {type(e).__name__}")
        print("  Avisa a Emili y mandale esta ventana.")
        return 1

    cobertura = {(p.cuerpo, p.numero.lower())
                 for c in D.CacheDGT().todas()
                 for p in c.preceptos(N) if p.comparable}

    # ------------------------------------------------ las consultas de aqui
    trazas = RAIZ / "datos" / "trazas"
    pedidos: Counter = Counter()
    consultas = con_modelo = 0
    primera = ultima = ""
    for d in sorted(trazas.iterdir()) if trazas.is_dir() else []:
        sel = d / "seleccion.json"
        con = d / "consumo.json"
        if not sel.is_file():
            continue
        consultas += 1
        real = False
        if con.is_file():
            try:
                real = "claude" in json.dumps(
                    json.loads(con.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                real = False
        if not real:
            continue
        con_modelo += 1
        primera = primera or d.name[:8]
        ultima = d.name[:8]
        try:
            j = json.loads(sel.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for r in (j.get("preceptos") or []):
            if r.get("decision") != "enviado":
                continue
            clave = r.get("clave") or ""
            if "#" not in clave:
                continue
            cuerpo, _, local = clave.rpartition("#")
            pedidos[(cuerpo, local.replace("articulo ", "").strip())] += 1

    def fecha(s: str) -> str:
        return f"{s[6:8]}/{s[4:6]}/{s[0:4]}" if len(s) == 8 else "-"

    print("-" * ANCHO)
    print("  CONSULTAS HECHAS EN ESTE EQUIPO")
    print("-" * ANCHO)
    print(f"    en total (con pruebas incluidas) : {consultas}")
    print(f"    de verdad, con el modelo         : {con_modelo}")
    if con_modelo:
        print(f"    de {fecha(primera)} a {fecha(ultima)}")

    if not pedidos:
        print()
        print("    Todavia no hay consultas de verdad en este equipo, asi que")
        print("    no hay nada que medir. Vuelve a ejecutarlo dentro de unas")
        print("    semanas de uso.")
        print()
        barra()
        return 0

    con_crit = sum(1 for k in pedidos if k in cobertura)
    sin_crit = [k for k in pedidos if k not in cobertura]
    print()
    print("-" * ANCHO)
    print("  QUE ARTICULOS SE PIDIERON, Y CUANTOS TENIAN CRITERIO")
    print("-" * ANCHO)
    print(f"    articulos distintos pedidos : {len(pedidos)}")
    print(f"    CON criterio guardado       : {con_crit}"
          f"   ({100 * con_crit / len(pedidos):.0f}%)")
    print(f"    SIN criterio                : {len(sin_crit)}")

    if sin_crit:
        print()
        print("    LOS QUE FALTAN, por impuesto:")
        por_imp: dict = {}
        for cu, art in sorted(sin_crit, key=lambda k: -pedidos[k]):
            imp = N.impuesto_de_cuerpo(cu) or "GENERAL"
            por_imp.setdefault(imp, []).append((cu, art))
        for imp, lista in sorted(por_imp.items(),
                                 key=lambda x: -len(x[1])):
            print(f"      {imp}  ({len(lista)})")
            for cu, art in lista[:10]:
                nombre = N.por_clave(cu)
                print(f"        art. {art:<12s} {(nombre.nombre if nombre else cu)[:34]}"
                      f"   pedido {pedidos[(cu, art)]} vez(ces)")
            if len(lista) > 10:
                print(f"        ... y {len(lista) - 10} mas")

    # ------------------------------------------------------------ la cola
    print()
    print("-" * ANCHO)
    print("  LA COLA DE DESCARGA")
    print("-" * ANCHO)
    try:
        pend = C.pendientes(N, cobertura)
        r = C.resumen()
        print(f"    articulos apuntados esperando : {len(pend)}")
        if pend:
            for imp, v in Counter(
                    N.impuesto_de_cuerpo(e["cuerpo"]) or "GENERAL"
                    for e in pend).most_common():
                print(f"      {imp:10s} {v}")
        print(f"    la ultima vez entraron        : "
              f"{r['ultima_vez_consultas']} consulta(s) sobre "
              f"{r['ultima_vez_articulos']} articulo(s)")
        print(f"    cuando                        : {r['cuando'] or '-'}")
        if r["sin_bajar"] is not None:
            print(f"    dias sin traer nada           : {r['sin_bajar']}")
    except Exception as e:                       # noqa: BLE001
        print(f"    no se ha podido leer la cola: {type(e).__name__}")

    # --------------------------------------------------------- la despensa
    print()
    print("-" * ANCHO)
    print("  LA DESPENSA DE ESTE EQUIPO")
    print("-" * ANCHO)
    todas = D.CacheDGT().todas()
    print(f"    consultas guardadas : {len(todas)}")
    print(f"    articulos con criterio : {len(cobertura)}")
    print()
    barra()
    print("  Fin. Copia todo lo de arriba y mandaselo a Emili.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
