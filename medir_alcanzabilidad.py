#!/usr/bin/env python3
"""LA PUERTA DE ALCANZABILIDAD, APLICADA A LA TANDA DEL GOTEO. Cero red.

    .venv/bin/python medir_alcanzabilidad.py            la tanda sin comprometer
    .venv/bin/python medir_alcanzabilidad.py --todo     ademas, la deuda acumulada

BAJAR Y NO PODER ENCONTRARLO OCUPA DISCO, PARECE COBERTURA Y NO LO ES. Ciento
dieciocho criterios se sembraron asi y se descubrio TRES DIAS DESPUES, mirando
a mano. Desde entonces la cadena de `sembrar.py` mide cada tanda antes de
seguir; EL GOTEO NO MEDIA NINGUNA. Y el goteo es el que esta bajando ahora:
once sesiones y 1.860 articulos mirados.

QUE ES «LA TANDA» AQUI, Y POR QUE SE LA PREGUNTA A GIT. Las consultas viajan
por el repositorio, asi que la tanda que todavia no se ha comprometido es
EXACTAMENTE lo que `git status` ve sin seguir. No hay que llevar ninguna lista
al lado, y una lista al lado se habria quedado atras: en este proyecto ya paso
con los tres identificadores de norma escritos en el instalador.

SE MIDE ANTES DEL COMMIT, que es el unico momento en que sirve. Despues, lo que
no se encuentra ya esta dentro y engorda el repositorio para siempre.

QUE MIDE: de lo bajado, cuanto se puede encontrar por (norma, articulo), que es
como lo busca el agente. Y lo que no, POR CAUSA -`agente_fiscal.causas`-,
porque parar por una deuda ya diagnosticada es gastar la unica señal que
tenemos para lo que no lo es.

CODIGOS DE SALIDA
    0   la tanda se puede encontrar entera, o lo que no cae en causas conocidas
    1   hay material nuevo que no se encuentra Y NO LO EXPLICA NINGUNA CAUSA.
        Eso es lo que esta puerta existe para cazar, y lo que no debe entrar en
        un commit sin mirarlo.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from agente_fiscal import causas as CAU          # noqa: E402
from agente_fiscal import dgt as DGT             # noqa: E402

ANCHO = 78
CONSULTAS = "datos/dgt/consultas/"


def de_la_tanda() -> list:
    """Los numeros de consulta que git ve sin seguir. La tanda sin comprometer.

    `--others --exclude-standard`: lo que no esta en el indice y no esta
    excluido. Ni lo modificado ni lo ya comprometido, que son otra cosa.
    """
    r = subprocess.run(["git", "ls-files", "--others", "--exclude-standard",
                        CONSULTAS], cwd=str(RAIZ), capture_output=True,
                       text=True)
    if r.returncode != 0:
        raise SystemExit(f"  git no ha contestado: {r.stderr.strip()[:200]}")
    return sorted(Path(l).stem for l in r.stdout.splitlines() if l.strip())


def informe(numeros: list, con_deuda: bool) -> int:
    import fase4
    ix, _g = fase4.cargar_corpus()
    N = ix.normas
    cache = DGT.CacheDGT()
    todas = cache.todas()
    por_numero = {c.numero: c for c in todas}

    print()
    print("=" * ANCHO)
    print("  LA TANDA DEL GOTEO, MEDIDA ANTES DE COMPROMETERLA")
    print("=" * ANCHO)
    print()

    de_tanda = [por_numero[n] for n in numeros if n in por_numero]
    perdidas = [n for n in numeros if n not in por_numero]
    if perdidas:
        # Un fichero en disco que la cache no sabe leer no es «alcanzable» ni
        # «inalcanzable»: es que no se ha podido ni abrir, y eso se dice aparte.
        print(f"  [AVISO] {len(perdidas)} fichero(s) que la cache no ha "
              f"cargado: {', '.join(perdidas[:6])}")
        print()

    if not de_tanda:
        print("  No hay tanda sin comprometer: todo lo bajado ya esta dentro.")
        print(f"  (la despensa tiene {len(todas)} consultas)")
        return 0

    # LO MISMO QUE MIDE LA CADENA DE `sembrar.py`, con su misma funcion. Dos
    # formas de contar lo mismo son dos numeros distintos en cuanto una cambie.
    import sembrar
    alc, tot, malas = sembrar.alcanzables_de(de_tanda, N)
    pct = 100 * alc / tot
    print(f"  consultas de la tanda      : {tot}")
    print(f"  ALCANZABLE por (norma, art): {alc} de {tot} ({pct:.1f}%)")
    print(f"  la despensa entera         : {len(todas)} consultas")
    print()

    por_causa = CAU.clasificar(malas, N) if malas else {}
    sin_explicar = por_causa.get("", [])
    if malas:
        print("  De las que NO se encuentran, por causa:")
        for k in sorted(por_causa, key=lambda k: -len(por_causa[k])):
            if not k:
                continue
            print(f"     {len(por_causa[k]):4d}  {k}")
        print()

    if con_deuda:
        # LA DEUDA ACUMULADA, aunque no pare nada: si una causa se dispara hay
        # que verlo, y la tanda sola no lo enseña.
        sin_cuerpo = [c for c in todas
                      if not any(p.cuerpo for p in c.preceptos(N))]
        if sin_cuerpo:
            acum = CAU.clasificar(sin_cuerpo, N)
            print(f"  DEUDA CONOCIDA ACUMULADA: {len(sin_cuerpo)} de "
                  f"{len(todas)} consultas")
            for k in sorted(acum, key=lambda k: -len(acum[k])):
                print(f"     {len(acum[k]):4d}  {k or 'SIN CLASIFICAR'}")
            print()

    if sin_explicar:
        print(f"  [PARADA] {len(sin_explicar)} de las bajadas AHORA no se")
        print("           encuentran Y NO ENCAJAN EN NINGUNA CAUSA CONOCIDA.")
        print("           Para eso existe esta puerta: lo demas es deuda ya")
        print("           diagnosticada. Mirar estas antes del commit:")
        for c in sin_explicar[:10]:
            print(f"             {c.numero}: {(c.normativa or '')[:56]}")
        if len(sin_explicar) > 10:
            print(f"             ... y {len(sin_explicar) - 10} mas")
        print()
        return 1
    if malas:
        print("  Todo lo no alcanzable cae en causas ya diagnosticadas.")
        print("  La tanda se puede comprometer.")
    else:
        print("  Todo lo bajado en esta tanda se puede encontrar.")
    print()
    return 0


def main(argv) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--todo", action="store_true",
                    help="ademas de la tanda, la deuda acumulada de la despensa")
    args = ap.parse_args(argv)
    return informe(de_la_tanda(), args.todo)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
