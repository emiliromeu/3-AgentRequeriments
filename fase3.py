#!/usr/bin/env python3
"""FASE 3 - Verificador de citas. Deterministico, sin IA.

    python fase3.py verificar respuesta.txt --ejercicio 2023
    python fase3.py verificar respuesta.txt --ejercicio 2023 --json salida.json
    python fase3.py probar casos/bateria.txt

Este script solo juzga. No redacta, no busca, no llama a ningun modelo, y no
escribe en el corpus.

Formato de cita que entiende (las dos formas, que son las que salen naturales
al escribir en castellano juridico):

    «fragmento literal» (art. 95 LIVA, https://www.boe.es/...#a95)
    El articulo 95 LIVA dispone que «fragmento literal»

Codigos de salida:
    0  ACEPTADO (todas las citas VERIFICADAS) / bateria en verde
    2  RECHAZADO / la bateria ha fallado algun caso
    1  error de uso o de corpus
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agente_fiscal import citas as C
from agente_fiscal import verificador as VF
from agente_fiscal.indice import ErrorCorpus, Indice

RAIZ = Path(__file__).resolve().parent
# El corpus es el DIRECTORIO: se cargan todas las normas ingeridas,
# sin saber cuales ni cuantas.
CORPUS = RAIZ / "datos" / "corpus"
ANCHO = 78

MARCA = {
    VF.VERIFICADA: "[ OK ]",
    VF.NO_VERIFICADA: "[FALLA]",
    VF.NO_VERIFICABLE: "[ ??  ]",
}


def _cache_dgt_de_prueba():
    """La copia local de consultas DGT que usa la BATERIA, y solo ella.

    Vive en `casos/dgt_prueba/` y no en `datos/dgt/`: los casos adversarios
    necesitan una consulta contra la que comprobar, y una consulta inventada
    dentro de la cache de verdad seria indistinguible de una autentica el dia
    que alguien mire ahi buscando criterio real.
    """
    from agente_fiscal import dgt as _D
    from pathlib import Path as _P
    return _D.CacheDGT(_P(__file__).resolve().parent / "casos" / "dgt_prueba")


def titulo(t: str) -> None:
    print("\n" + "=" * ANCHO)
    print(t)
    print("=" * ANCHO)


def recorta(s: str, n: int) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


# ------------------------------------------------------------------ verificar


def pinta_informe(informe: VF.Informe, fuente: str) -> None:
    titulo(f"VERIFICACION DE CITAS  ·  {fuente}")
    r = informe.resumen
    print(f"ejercicio del caso : {informe.ejercicio or '(no indicado)'}")
    print(f"citas encontradas  : {r['total']}")
    print(f"  VERIFICADAS      : {r['verificadas']}")
    print(f"  NO VERIFICADAS   : {r['no_verificadas']}")
    print(f"  NO VERIFICABLES  : {r['no_verificables']}")

    for d in informe.dictamenes:
        print("\n" + "-" * ANCHO)
        print(f"{MARCA[d.estado]} cita {d.n}: {d.estado}")
        print(f"   cita     : «{recorta(d.literal, 62)}»")
        print(f"   referida : {d.referencia_citada or '(sin referencia)'}"
              + (f"  ->  {d.referencia_corpus}" if d.referencia_corpus else ""))
        if d.norma == "asumida_liva":
            print("   norma    : no se indico; se ha supuesto la Ley 37/1992")
        if d.version_usada:
            print(f"   version  : {d.version_usada.get('fecha_vigencia_efectiva')} "
                  f"({(d.version_usada.get('orden') or 0) + 1}"
                  f" de {d.version_usada.get('de_un_total')})")
        if d.enlace_correcto:
            print(f"   enlace   : {d.enlace_correcto}")
        for c in d.comprobaciones:
            print(f"     · {c}")
        if d.motivo:
            print(f"   MOTIVO   : {d.motivo}")

    if informe.sueltas:
        print("\n" + "-" * ANCHO)
        print(f"Referencias citadas SIN fragmento literal ({len(informe.sueltas)}):")
        print("  (no tumban el veredicto por si solas, pero una afirmacion")
        print("   juridica sin fragmento literal no esta respaldada)")
        for s in informe.sueltas[:10]:
            print(f"   - {s.bruto}")

    print("\n" + "=" * ANCHO)
    print(f"VEREDICTO GLOBAL: {informe.veredicto}")
    if informe.motivo_global:
        print(f"  {informe.motivo_global}")
    if informe.veredicto == VF.RECHAZADO:
        print("  La respuesta NO se muestra. No hay verificacion parcial.")
    print("=" * ANCHO)


def modo_verificar(args) -> int:
    ruta = Path(args.fichero)
    if not ruta.exists():
        print(f"[FALLO] no existe el fichero {ruta}", file=sys.stderr)
        return 1
    texto = ruta.read_text(encoding="utf-8")

    ix = Indice(CORPUS)
    v = VF.Verificador(ix, cache_dgt=_cache_dgt_de_prueba())
    informe = v.verificar_texto(texto, args.ejercicio, args.exigir_norma)

    pinta_informe(informe, ruta.name)

    if args.json:
        destino = Path(args.json)
        destino.write_text(
            json.dumps(informe.a_json(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nJSON para la fase 4 -> {destino}")
    elif args.json_stdout:
        print(json.dumps(informe.a_json(), ensure_ascii=False, indent=2))

    return 0 if informe.veredicto == VF.ACEPTADO else 2


# --------------------------------------------------------------------- probar


def leer_bateria(ruta: Path) -> list[dict]:
    """Lee el fichero de casos adversarios.

    Formato, pensado para escribirse y leerse a mano:

        --- CASO: identificador
        esperado: NO_VERIFICADA
        ejercicio: 2023
        motivo: por que tiene que fallar
        texto:
        ...el texto con la cita...
        --- FIN
    """
    casos: list[dict] = []
    actual: dict | None = None
    leyendo_texto = False

    for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        if linea.startswith("--- CASO:"):
            actual = {
                "id": linea.split(":", 1)[1].strip(),
                "esperado": "",
                "ejercicio": None,
                "motivo": "",
                "texto": [],
                "linea": n,
            }
            leyendo_texto = False
            continue
        if linea.startswith("--- FIN"):
            if actual is not None:
                actual["texto"] = "\n".join(actual["texto"]).strip()
                casos.append(actual)
            actual, leyendo_texto = None, False
            continue
        if actual is None:
            continue
        if leyendo_texto:
            actual["texto"].append(linea)
            continue
        if linea.strip() == "texto:":
            leyendo_texto = True
            continue
        if ":" in linea:
            clave, valor = linea.split(":", 1)
            clave, valor = clave.strip().lower(), valor.strip()
            if clave == "esperado":
                actual["esperado"] = valor.upper()
            elif clave == "ejercicio":
                actual["ejercicio"] = int(valor) if valor.isdigit() else None
            elif clave == "motivo":
                actual["motivo"] = valor
    return casos


def modo_probar(args) -> int:
    ruta = Path(args.fichero)
    if not ruta.exists():
        print(f"[FALLO] no existe la bateria {ruta}", file=sys.stderr)
        return 1

    casos = leer_bateria(ruta)
    if not casos:
        print(f"[FALLO] la bateria {ruta} no tiene ningun caso", file=sys.stderr)
        return 1

    ix = Indice(CORPUS)
    v = VF.Verificador(ix, cache_dgt=_cache_dgt_de_prueba())

    titulo(f"BATERIA DE CASOS ADVERSARIOS  ·  {ruta.name}")
    print(f"{len(casos)} casos escritos a mano, cada uno con el veredicto que debe dar.\n")

    fallos = []
    for caso in casos:
        informe = v.verificar_texto(caso["texto"], caso["ejercicio"])
        esperado = caso["esperado"]

        # El esperado puede ser un estado de cita o un veredicto global.
        if esperado in (VF.ACEPTADO, VF.RECHAZADO):
            obtenido = informe.veredicto
        else:
            estados = [d.estado for d in informe.dictamenes]
            # Se compara contra el estado PEOR: si una cita falla, eso es lo
            # que define el caso.
            orden = [VF.NO_VERIFICADA, VF.NO_VERIFICABLE, VF.VERIFICADA]
            obtenido = min(estados, key=orden.index) if estados else "SIN_CITAS"

        ok = obtenido == esperado
        if not ok:
            fallos.append((caso, esperado, obtenido, informe))

        print(f"{'[ OK ]' if ok else '[FALLA]'} {caso['id']:<34} "
              f"esperado {esperado:<15} obtenido {obtenido}")
        if caso["motivo"]:
            print(f"         proposito: {caso['motivo']}")
        for d in informe.dictamenes:
            if d.motivo:
                print(f"         cita {d.n} [{d.estado}]: {recorta(d.motivo, 62)}")
        if not ok:
            print(f"         >>> DISCREPANCIA en la linea {caso['linea']} de la bateria")

    print("\n" + "=" * ANCHO)
    if fallos:
        print(f"BATERIA EN ROJO: {len(fallos)} de {len(casos)} casos no dan lo esperado")
        for caso, esp, obt, _ in fallos:
            print(f"  - {caso['id']}: esperado {esp}, obtenido {obt}")
    else:
        print(f"BATERIA EN VERDE: los {len(casos)} casos dan exactamente lo esperado")
    print("=" * ANCHO)
    return 2 if fallos else 0


# ------------------------------------------------------------------------ cli


def main(argv: list[str]) -> int:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(
        description="Fase 3: verificador deterministico de citas.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = ap.add_subparsers(dest="modo", required=True)

    v = sub.add_parser("verificar", help="verifica las citas de un fichero de texto")
    v.add_argument("fichero")
    v.add_argument("--ejercicio", type=int, default=None)
    v.add_argument("--json", default=None, help="escribe el informe JSON en un fichero")
    v.add_argument("--json-stdout", action="store_true", dest="json_stdout",
                   help="saca el informe JSON por pantalla")
    v.add_argument("--exigir-norma", action="store_true", dest="exigir_norma",
                   help="no supone la LIVA cuando la cita no dice de que norma es")

    p = sub.add_parser("probar", help="ejecuta la bateria de casos adversarios")
    p.add_argument("fichero", nargs="?", default=str(RAIZ / "casos" / "bateria.txt"))

    args = ap.parse_args(argv)

    ejercicio = getattr(args, "ejercicio", None)
    if ejercicio is not None and not (1993 <= ejercicio <= 2100):
        print(f"[FALLO] ejercicio fuera de rango: {ejercicio}. "
              f"La Ley del IVA esta en vigor desde 1993.", file=sys.stderr)
        return 1

    try:
        if args.modo == "verificar":
            return modo_verificar(args)
        return modo_probar(args)
    except ErrorCorpus as e:
        print(f"\n[FALLO DE CORPUS] {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrumpido.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
