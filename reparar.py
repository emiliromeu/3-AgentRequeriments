#!/usr/bin/env python3
"""DEJA UNA COPIA EN CONDICIONES DE ACTUALIZARSE. Cero red salvo git. Cero API.

    python reparar.py --revisar   dice como esta la copia, sin tocar nada
    python reparar.py             lo arregla y actualiza

POR QUE EXISTE. El 28/08/2026 varias copias del despacho llevaban semanas sin
poder actualizarse, y la semana de goteo -986 consultas- no llegaba a nadie.
`actualizar` hacia lo que dice que hace: si hay cambios sin guardar, no
actualiza encima. El problema era que los cambios los escribiamos NOSOTROS.

Tres ficheros del repositorio se reescribian en la maquina de destino con solo
usar el agente, y cada uno era un choque seguro en el pull siguiente:

  · `datos/dgt/indice.json`, que la cola por demanda tocaba al bajar algo;
  · `datos/dgt/consultas/*.json`, donde la cola dejaba TAMBIEN lo que bajaba
    por demanda, con el nombre exacto de ficheros que el pull iba a traer;
  · `normas_del_corpus.json`, que el instalador regeneraba con la fecha del dia.

Los tres estan arreglados EN ORIGEN -ver `.gitignore`, `fuente_web` y
`catalogo.regenerar`-, asi que una copia nueva ya no se rompe. Esto es para las
que ya se rompieron: un pull encima no las repara.

Y PARA EL OTRO ROTO, el de Windows: las rutas largas abortaban el checkout a la
mitad y dejaban el arbol con ficheros que faltan. `git status` no lo canta a
gritos y el agente arranca igual, peor y en silencio.

LO QUE NO SE TOCA, NUNCA. Esto no borra la carpeta ni clona de nuevo, que es lo
que costaria la despensa por demanda y la configuracion del equipo:

    .env                      la clave
    datos/dgt/demanda/        lo que ha bajado el departamento preguntando
    datos/dgt/cola.json       las promesas hechas
    datos/trazas/             dudas reales de clientes
    datos/corpus/             el texto del BOE (se rehace, pero tarda)

Y LO QUE NO ENTIENDE, NO LO TIRA. Si aparece un cambio local que no esta en la
lista de derivados de abajo, para y lo enseña: puede ser trabajo de alguien.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ANCHO = 70

# LOS DERIVADOS QUE SE PUEDEN DESCARTAR SIN PERDER NADA.
#
# ESTA LISTA NO CRECE, Y ESO ES LO IMPORTANTE. No es la forma de convivir con
# ficheros que viajan y se reescriben: es la lista de los que YA quedaron asi en
# equipos instalados antes del 28/08/2026. En origen, los tres han dejado de
# estar en los dos sitios a la vez. El dia que no quede ninguna copia vieja,
# esto se borra entero.
#
# Cada uno lleva por que es seguro descartarlo.
DERIVADOS = {
    "datos/dgt/indice.json":
        "es el mapeo numero -> id interno, y se rehace solo de los documentos",
    "normas_del_corpus.json":
        "la lista que viaja; la de GitHub manda y solo crece",
    "GUIA.md":
        "la hoja de la mesa, que se regenera con la copia de este equipo",
}

# LO QUE NO SE TOCA BAJO NINGUN CONCEPTO. Se comprueba antes de cada accion, no
# se confia en que la accion sea la correcta.
INTOCABLE = (".env", "datos/dgt/demanda/", "datos/dgt/cola.json",
             "datos/trazas/", "datos/corpus/", "datos/dgt/goteo.json")


def linea(t: str = "") -> None:
    print(t, flush=True)


def titulo(t: str) -> None:
    linea()
    linea("=" * ANCHO)
    linea(f"  {t}")
    linea("=" * ANCHO)
    linea()


def git(*args, permitir_fallo: bool = True) -> tuple:
    """(codigo, salida). git y nada mas: esto tiene que funcionar en un arbol
    a medias, donde puede faltar cualquier fichero del proyecto."""
    try:
        r = subprocess.run(["git", *args], cwd=str(RAIZ), capture_output=True,
                           text=True, errors="replace")
    except OSError:
        return 127, "no hay git en este equipo"
    if r.returncode != 0 and not permitir_fallo:
        raise SystemExit(f"  git {' '.join(args)} ha fallado:\n{r.stderr[:400]}")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def es_intocable(ruta: str) -> bool:
    return any(ruta == x or ruta.startswith(x) for x in INTOCABLE)


# ------------------------------------------------------------------ mirar


def mirar() -> dict:
    """El estado de la copia. No escribe nada."""
    e = {"repo": False, "faltan": [], "modificados": [], "sin_seguir": [],
         "detras": None, "choques": [], "longpaths": "", "rama": ""}
    if git("rev-parse", "--is-inside-work-tree")[0] != 0:
        return e
    e["repo"] = True
    e["longpaths"] = git("config", "--get", "core.longpaths")[1].strip()

    # FICHEROS QUE FALTAN DEL ARBOL. Es el rastro que deja un checkout abortado
    # a la mitad, y `git ls-files -d` es la pregunta exacta: seguidos por git y
    # ausentes del disco.
    e["faltan"] = [l for l in git("ls-files", "-d")[1].splitlines() if l.strip()]

    for l in git("status", "--porcelain")[1].splitlines():
        if len(l) < 4:
            continue
        estado, ruta = l[:2], l[3:].strip().strip('"')
        if es_intocable(ruta):
            continue
        if estado == "??":
            e["sin_seguir"].append(ruta)
        elif "D" not in estado:
            e["modificados"].append(ruta)

    git("fetch", "--quiet")
    detras = git("rev-list", "--count", "HEAD..@{u}")[1].strip()
    e["detras"] = int(detras) if detras.isdigit() else None
    e["rama"] = git("rev-parse", "--abbrev-ref", "HEAD")[1].strip()

    # CHOQUES DE VERDAD: ficheros sin seguir que el pull TRAE con ese mismo
    # nombre. Un fichero sin seguir cualquiera no estorba; uno que viene en el
    # pull aborta la fusion entera.
    if e["detras"]:
        entrantes = set(git("diff", "--name-only", "HEAD..@{u}")[1].split())
        e["choques"] = sorted(set(e["sin_seguir"]) & entrantes)
    return e


def contar(e: dict) -> int:
    """Codigo de salida: 0 lista, 1 hay que repararla, 2 no es una copia."""
    if not e["repo"]:
        return 2
    hay = (e["faltan"] or e["choques"]
           or [m for m in e["modificados"] if m in DERIVADOS]
           or [m for m in e["modificados"] if m not in DERIVADOS])
    return 1 if hay else 0


def informar(e: dict) -> int:
    titulo("ESTADO DE ESTA COPIA")
    if not e["repo"]:
        linea("  Esta carpeta no es una copia del proyecto.")
        linea("  Avisa a Emili antes de tocar nada.")
        return 2

    linea(f"  rama                  : {e['rama']}")
    linea(f"  rutas largas          : "
          + ("activadas" if e["longpaths"] == "true" else "SIN ACTIVAR"))

    if e["detras"] is None:
        linea("  novedades             : no se ha podido preguntar a GitHub")
    else:
        linea(f"  novedades sin traer   : {e['detras']} cambio(s)")

    if e["faltan"]:
        linea(f"  ARBOL INCOMPLETO      : faltan {len(e['faltan'])} ficheros "
              f"que git da por puestos")
        for f in e["faltan"][:6]:
            linea(f"        - {f}")
        if len(e["faltan"]) > 6:
            linea(f"        ... y {len(e['faltan']) - 6} mas")
    else:
        linea("  arbol                 : completo")

    derivados = [m for m in e["modificados"] if m in DERIVADOS]
    otros = [m for m in e["modificados"] if m not in DERIVADOS]
    if derivados:
        linea(f"  derivados cambiados   : {len(derivados)} (se pueden "
              f"descartar)")
        for m in derivados:
            linea(f"        - {m}: {DERIVADOS[m]}")
    if otros:
        linea(f"  CAMBIOS QUE NO SON MIOS: {len(otros)}")
        for m in otros[:6]:
            linea(f"        - {m}")
        linea("        Esto no se descarta solo. Avisa a Emili.")
    if e["choques"]:
        linea(f"  CHOQUES CON EL PULL   : {len(e['choques'])} fichero(s) que "
              f"ya estan aqui sin seguir")
        for c in e["choques"][:6]:
            linea(f"        - {c}")
        if len(e["choques"]) > 6:
            linea(f"        ... y {len(e['choques']) - 6} mas")

    linea()
    codigo = contar(e)
    if codigo == 0:
        linea("  LISTA. Esta copia puede actualizarse.")
    else:
        linea("  HAY QUE REPARARLA. Ejecuta:  python reparar.py")
    linea()
    return codigo


# --------------------------------------------------------------- reparar


def reparar(e: dict) -> int:
    titulo("REPARANDO LA COPIA")
    linea("  No se borra nada tuyo: ni la clave, ni lo que ha bajado el")
    linea("  departamento preguntando, ni las trazas.")
    linea()

    # 1. RUTAS LARGAS, PRIMERO. Sin esto, en Windows el checkout de mas abajo
    # vuelve a abortar por donde abortó la vez anterior.
    if e["longpaths"] != "true":
        git("config", "core.longpaths", "true")
        linea("  [1] Rutas largas ................. activadas")
    else:
        linea("  [1] Rutas largas ................. ya estaban")

    # 2. LO QUE NO ES NUESTRO, PARA. Un cambio local que no esta en la lista de
    # derivados puede ser trabajo de alguien, y descartarlo por comodidad seria
    # el segundo desastre del dia.
    otros = [m for m in e["modificados"] if m not in DERIVADOS]
    if otros:
        linea("  [2] Cambios que no reconozco ..... LOS HAY, no sigo")
        linea()
        for m in otros:
            linea(f"        {m}")
        linea()
        linea("  Estos no los ha escrito el agente. Avisa a Emili con esta")
        linea("  lista antes de tocarlos.")
        return 1
    linea("  [2] Cambios que no reconozco ..... ninguno")

    # 3. LOS DERIVADOS, DESCARTADOS. Cada uno se rehace solo.
    derivados = [m for m in e["modificados"] if m in DERIVADOS]
    if derivados:
        for m in derivados:
            git("checkout", "--", m)
        linea(f"  [3] Derivados descartados ........ {len(derivados)} "
              f"(se rehacen solos)")
    else:
        linea("  [3] Derivados descartados ........ ninguno hacia falta")

    # 4. LOS CHOQUES, APARTADOS Y NO BORRADOS.
    #
    # Son consultas que la cola bajo POR DEMANDA y que, por el fallo que esto
    # viene a cerrar, cayeron en `consultas/` -que viaja- en vez de en
    # `demanda/` -que no-. El pull trae ese mismo nombre y aborta.
    #
    # SE MUEVEN A `demanda/`, QUE ES SU SITIO: asi el choque desaparece, el
    # documento sigue disponible -`dgt.CacheDGT` lee las dos carpetas- y no se
    # pierde ninguna descarga. Borrarlas seria mas facil y tiraria trabajo.
    if e["choques"]:
        demanda = RAIZ / "datos" / "dgt" / "demanda"
        demanda.mkdir(parents=True, exist_ok=True)
        movidos = otros_choques = 0
        for c in e["choques"]:
            origen = RAIZ / c
            if not origen.is_file():
                continue
            if c.startswith("datos/dgt/consultas/"):
                destino = demanda / origen.name
                if destino.exists():
                    origen.unlink()      # ya esta a salvo en su sitio
                else:
                    origen.replace(destino)
                movidos += 1
            else:
                # Cualquier otro choque se aparta al lado, con otro nombre, en
                # vez de borrarse: no se sabe que es.
                origen.replace(origen.with_suffix(origen.suffix + ".apartado"))
                otros_choques += 1
        linea(f"  [4] Choques resueltos ............ {movidos} consulta(s) "
              f"movidas a demanda/")
        if otros_choques:
            linea(f"      y {otros_choques} fichero(s) apartados con "
                  f"«.apartado» al lado")
    else:
        linea("  [4] Choques resueltos ............ ninguno habia")

    # 5. EL ARBOL, COMPLETO. Con las rutas largas ya activadas, ahora si.
    if e["faltan"]:
        cod, salida = git("checkout", "--", ".")
        quedan = [l for l in git("ls-files", "-d")[1].splitlines() if l.strip()]
        if quedan:
            linea(f"  [5] Arbol completado ............. SIGUEN FALTANDO "
                  f"{len(quedan)}")
            linea()
            for f in quedan[:6]:
                linea(f"        {f}")
            linea()
            linea("  Esto ya no es cosa de las rutas largas. Manda esta lista")
            linea("  a Emili; NO borres la carpeta.")
            return 1
        linea(f"  [5] Arbol completado ............. {len(e['faltan'])} "
              f"fichero(s) recuperados")
    else:
        linea("  [5] Arbol completado ............. ya estaba")

    # 6. Y AHORA SI, EL PULL.
    if not e["detras"]:
        linea("  [6] Actualizar ................... no hay novedades")
        titulo("COPIA REPARADA")
        return 0
    cod, salida = git("pull", "--ff-only")
    if cod != 0:
        linea("  [6] Actualizar ................... NO HA PODIDO")
        linea()
        for l in salida.strip().splitlines()[:8]:
            linea(f"        {l[:64]}")
        linea()
        linea("  La copia esta mejor que antes, pero el pull sigue sin pasar.")
        linea("  Manda estas lineas a Emili.")
        return 1
    linea(f"  [6] Actualizar ................... {e['detras']} cambio(s) "
          f"traidos")
    titulo("COPIA REPARADA Y AL DIA")
    linea("  Cierra esta ventana y abre el agente.")
    linea()
    return 0


def main(argv) -> int:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--revisar", action="store_true",
                    help="dice como esta la copia y no toca nada")
    args = ap.parse_args(argv)

    e = mirar()
    if args.revisar:
        return informar(e)
    if not e["repo"]:
        return informar(e)
    informar(e)
    if contar(e) == 0 and not e["detras"]:
        return 0
    return reparar(e)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        linea()
        linea("  Interrumpido. No se ha borrado nada.")
        sys.exit(1)
