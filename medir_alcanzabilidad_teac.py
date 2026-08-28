#!/usr/bin/env python3
"""LA PUERTA DE ALCANZABILIDAD DE LA DOCTRINA. Cero red, cero API.

    .venv/bin/python medir_alcanzabilidad_teac.py

El gemelo de `medir_alcanzabilidad.py`, para el TEAC. Bajar y no poder
encontrarlo ocupa disco, parece cobertura y no lo es.

QUE ES «LA TANDA» AQUI, Y POR QUE SE LA PREGUNTA A GIT. Los criterios viajan
por el repositorio, asi que lo que todavia no se ha comprometido es
EXACTAMENTE lo que `git status` ve sin seguir. No hay que llevar ninguna lista
al lado, y una lista al lado se habria quedado atras.

SE MIDE ANTES DEL COMMIT, que es el unico momento en que sirve. Despues, lo
que no se encuentra ya esta dentro y engorda el repositorio para siempre.

ESTO ESTUVO CORRIENDOSE A MANO, pegado en la terminal cada vez, y ese es
justo el estado que este proyecto no deja pasar: una comprobacion que solo
existe mientras alguien se acuerde de ella. Ahora la ejecuta la cadena.

CODIGOS DE SALIDA
    0   la tanda se puede encontrar entera
    1   hay material que no se alcanza. La cadena PARA aqui.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

CRITERIOS = "datos/teac/criterios/"
ANCHO = 74


def de_la_tanda() -> set:
    r = subprocess.run(["git", "ls-files", "--others", "--exclude-standard",
                        CRITERIOS], cwd=str(RAIZ), capture_output=True,
                       text=True)
    if r.returncode != 0:
        raise SystemExit(f"  git no ha contestado: {r.stderr.strip()[:200]}")
    return {Path(l).stem for l in r.stdout.splitlines() if l.strip()}


def main() -> int:
    import fase4
    from agente_fiscal import teac as TC

    nuevos = de_la_tanda()
    ix, _g = fase4.cargar_corpus()
    N = ix.normas
    todos = TC.CacheTEAC().todas()

    print()
    print("=" * ANCHO)
    print("  LA TANDA DEL TEAC, MEDIDA ANTES DE COMPROMETERLA")
    print("=" * ANCHO)
    print()

    # El fichero de cada criterio se nombra con su `id`, cambiando las barras.
    tanda = [c for c in todos if str(c.id).replace("/", "-") in nuevos]
    if not tanda:
        print("  No hay tanda sin comprometer: todo lo bajado ya esta dentro.")
        print(f"  (la despensa tiene {len(todos)} criterios)")
        return 0

    def inalcanzable(c) -> bool:
        # LO MISMO QUE MIRA `sembrar_teac.alcanzables`: que al menos una de sus
        # referencias caiga en un cuerpo del corpus. Un criterio que no apunta a
        # ninguno no se puede recuperar por (norma, articulo), que es como lo
        # busca el agente.
        return not any(N.por_clave(k) for k, _n in c.preceptos(N))

    malos = [c for c in tanda if inalcanzable(c)]
    alc, tot = len(tanda) - len(malos), len(tanda)
    print(f"  criterios de la tanda        : {tot}")
    print(f"  ALCANZABLES por (norma, art.): {alc} de {tot} "
          f"({100 * alc / tot:.1f}%)")
    print(f"  la despensa entera           : {len(todos)} criterios")

    sin_cuerpo = [c for c in todos if inalcanzable(c)]
    print(f"  deuda acumulada              : {len(sin_cuerpo)} de {len(todos)}")
    print()

    if malos:
        print(f"  [PARADA] {len(malos)} criterio(s) bajados AHORA no se pueden")
        print("           encontrar por (norma, articulo). Para eso existe esta")
        print("           puerta: mirar estos antes de comprometer la tanda.")
        for c in malos[:12]:
            refs = ", ".join(str(r.get("norma"))[:44]
                             for r in (c.referencias or [])[:2])
            print(f"             {c.resolucion}: {refs or '(sin referencias)'}")
        if len(malos) > 12:
            print(f"             ... y {len(malos) - 12} mas")
        print()
        return 1

    print("  Todo lo bajado en esta tanda se puede encontrar.")
    print("  La tanda se puede comprometer.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
