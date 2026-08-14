#!/usr/bin/env python3
"""LA LISTA DE NORMAS VIAJA, Y EL RESTO LA USA. Cero red, cero API.

    python pruebas/prueba_catalogo.py

EL DEFECTO QUE LA JUSTIFICA, que era bloqueante. En el despacho habia dieciseis
normas y en la oficina trece, y NO HABIA NINGUN CAMINO para que llegaran las
tres que faltaban:

  - `git pull` no las traia: `datos/corpus` esta excluido de git a proposito.
  - El instalador tenia TRES ids escritos a mano, de cuando esto era solo IVA.
  - El boton «actualizar las normas» re-ingeria lo que hubiera EN LOCAL, asi
    que una maquina con trece se ponia al dia de sus trece. Cada equipo
    conservaba su propio agujero y el boton parecia arreglarlo.

Y ninguno de los tres fallaba: una instalacion con trece normas FUNCIONA. Da
peores respuestas, que es distinto, y no avisa.

QUE SE COMPRUEBA:

  1. Que la lista existe, viaja por git y cuadra con el corpus de este equipo.
  2. Que se GENERA de `sellos.json` y no se escribe: si mañana se ingiere una
     norma aqui, tiene que aparecer sola.
  3. EL CICLO DE LA OFICINA, simulado entero: un equipo con trece normas
     descubre que faltan tres y las pide; uno con las dieciseis no vuelve a
     ingerir nada.
  4. Que nadie ha vuelto a escribir la lista a mano en el instalador.

TAXONOMIA: el bloque 3 monta corpus de mentira en carpetas temporales -no toca
el de este equipo-. Los bloques 1 y 2 SI miran el corpus real, porque lo que
afirman es precisamente que la lista y el corpus no se han separado: es
integridad, no contenido.
"""
import json
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from agente_fiscal import catalogo as CAT       # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:112]}" if not ok else ""))
    if not ok:
        fallos.append(que)


# ==================================== 1. LA LISTA VIAJA
print("\n=== 1. LA LISTA EXISTE Y VIAJA POR GIT ===")

comprobar("el fichero de la lista existe", CAT.LISTA.is_file(), CAT.LISTA)
comprobar("y vive FUERA de `datos/`, que esta excluido entero",
          "datos" not in CAT.LISTA.relative_to(RAIZ).parts,
          str(CAT.LISTA.relative_to(RAIZ)))

import subprocess                                # noqa: E402

r = subprocess.run(["git", "check-ignore", str(CAT.LISTA)],
                   capture_output=True, text=True, cwd=str(RAIZ))
comprobar("git NO la ignora: es lo unico del corpus que tiene que viajar",
          r.returncode != 0, "git la ignora")

de_disco = CAT.del_disco()
comprobar("trae normas dentro", len(de_disco) > 0, len(de_disco))
comprobar("cada una con id y nombre legible",
          all(n.get("id") and n.get("nombre") for n in de_disco))

# ==================================== 2. SE GENERA, NO SE ESCRIBE
print("\n=== 2. SALE DE `sellos.json`, NO DE LA MANO DE NADIE ===")
print("  Si hubiera que acordarse de actualizarla, se olvidaria: es")
print("  exactamente lo que le paso a la lista del instalador.\n")

del_corpus = CAT.del_corpus()
comprobar("la lista que viaja CUADRA con el corpus de este equipo",
          {n["id"] for n in de_disco} == {n["id"] for n in del_corpus},
          f"lista {len(de_disco)} vs corpus {len(del_corpus)}")
comprobar("no sobra ninguna ingerida sin publicar", not CAT.sobran(),
          str(CAT.sobran()))
comprobar("aqui no falta ninguna de la lista", not CAT.faltan(),
          str([n["id"] for n in CAT.faltan()]))

# Y QUE SE REGENERA SOLA AL INGERIR: se comprueba que `fase1` la llama.
FASE1 = (RAIZ / "fase1.py").read_text("utf-8")
comprobar("`fase1.py ingerir` la regenera al terminar",
          "catalogo" in FASE1 and "regenerar()" in FASE1)

# ==================================== 3. EL CICLO DE LA OFICINA
print("\n=== 3. EL CICLO REAL: TRECE NORMAS + git pull ===")
print("  Se monta un equipo de mentira con trece de las dieciseis y se mira")
print("  que descubre las tres que le faltan.\n")


def equipo_con(ids, lista_ids):
    """Un corpus de mentira: `ids` ingeridas, `lista_ids` en la lista."""
    tmp = tempfile.mkdtemp()
    d = Path(tmp)
    (d / "datos" / "corpus").mkdir(parents=True)
    for i in ids:
        (d / "datos" / "corpus" / f"{i}.jsonl").write_text(
            json.dumps({"norma_id": i, "norma_titulo": f"Ley de mentira {i}"})
            + "\n", encoding="utf-8")
    (d / "datos" / "corpus" / "sellos.json").write_text(
        json.dumps({i: {"sha256": "x", "preceptos": 1} for i in ids}),
        encoding="utf-8")
    (d / "normas_del_corpus.json").write_text(json.dumps(
        {"normas": [{"id": i, "nombre": f"Ley de mentira {i}", "titulo": ""}
                    for i in lista_ids]}), encoding="utf-8")
    return d


def con_raiz_en(d):
    """Apunta el catalogo a un equipo de mentira, sin tocar el de verdad."""
    CAT.RAIZ, CAT.LISTA = d, d / "normas_del_corpus.json"
    CAT.CORPUS, CAT.SELLOS = (d / "datos" / "corpus",
                              d / "datos" / "corpus" / "sellos.json")


# LOS NUMEROS SALEN DE LA LISTA, NO ESCRITOS. La primera version llevaba «16»
# y «17» a mano y se puso roja el dia que entro el Reglamento del ISD: la
# suite media el tamaño del corpus en vez de medir el mecanismo. Lo que se
# prueba es «faltan TRES», no «hay dieciseis».
REALES = [n["id"] for n in de_disco]
TODAS, MENOS_TRES = REALES, REALES[:-3]
FALTAN_3 = REALES[-3:]
N = len(TODAS)

guardado = (CAT.RAIZ, CAT.LISTA, CAT.CORPUS, CAT.SELLOS)
try:
    # --- el equipo de la oficina: trece ingeridas, dieciseis en la lista
    con_raiz_en(equipo_con(MENOS_TRES, TODAS))
    faltan = CAT.faltan()
    print(f"    equipo con {len(MENOS_TRES)} normas y lista de {N}")
    comprobar("descubre que le faltan exactamente 3", len(faltan) == 3,
              len(faltan))
    comprobar("  y son las que son, no otras",
              {n["id"] for n in faltan} == set(FALTAN_3),
              str([n["id"] for n in faltan]))
    comprobar("  y NO pide re-ingerir las trece que ya tiene",
              all(n["id"] not in MENOS_TRES for n in faltan))

    # --- el equipo al dia: no vuelve a ingerir nada
    con_raiz_en(equipo_con(TODAS, TODAS))
    comprobar(f"un equipo con las {N} no ingiere NADA", not CAT.faltan(),
              str([n["id"] for n in CAT.faltan()]))

    # --- EL DEFECTO DE ANTES, para que se vea la diferencia: mirandose a si
    #     mismo, el equipo de trece se encuentra completo.
    con_raiz_en(equipo_con(MENOS_TRES, MENOS_TRES))
    comprobar("(el defecto viejo) mirando solo lo local, el corto se cree "
              "completo: por eso manda la lista", not CAT.faltan(),
              str(len(CAT.faltan())))

    # --- LA LISTA SOLO CRECE. Es lo que casi rompe el arreglo entero: la
    #     ingesta regenera la lista, y si la regenerara CON EL CORPUS LOCAL, un
    #     equipo atrasado la reescribiria a la baja y se creeria completo. Se
    #     descubrio cortando una ingesta a mitad en el equipo de trece.
    print("\n  Y LA REGENERACION NO PUEDE ENCOGER LA LISTA:")
    d = equipo_con(MENOS_TRES + [FALTAN_3[0]], TODAS)   # ingirio una de las tres
    con_raiz_en(d)
    quedan = CAT.regenerar()
    comprobar(f"tras ingerir UNA de las tres, la lista sigue teniendo {N}",
              len(quedan) == N, len(quedan))
    comprobar("  y el equipo sigue sabiendo que le faltan 2",
              len(CAT.faltan()) == 2, len(CAT.faltan()))
    comprobar("  (si encogiera, se creeria completo y las 2 dejarian de "
              "existir para todos)",
              {n["id"] for n in CAT.faltan()} == set(FALTAN_3[1:]),
              str([n["id"] for n in CAT.faltan()]))

    # Y AL REVES: una norma nueva aqui SI se publica. Si no, la union seria una
    # forma elegante de congelar la lista para siempre.
    d2 = equipo_con(TODAS + ["BOE-A-2099-99999"], TODAS)
    con_raiz_en(d2)
    nueva = CAT.regenerar()
    comprobar("una norma ingerida de nuevas SI aparece sola en la lista",
              len(nueva) == N + 1 and any(n["id"] == "BOE-A-2099-99999"
                                          for n in nueva), len(nueva))
finally:
    CAT.RAIZ, CAT.LISTA, CAT.CORPUS, CAT.SELLOS = guardado

# ==================================== 4. NADIE LA VUELVE A ESCRIBIR
print("\n=== 4. NI EL INSTALADOR NI EL BOTON LLEVAN LA LISTA DENTRO ===")

INSTALAR = (RAIZ / "instalar.py").read_text("utf-8")
INTERFAZ = (RAIZ / "interfaz.py").read_text("utf-8")

import re                                        # noqa: E402

# EL CONTROL QUE PEDISTE: si alguien vuelve a escribir ids del BOE a mano en el
# instalador o en la ventana, esto se pone rojo.
for fich, texto in (("instalar.py", INSTALAR), ("interfaz.py", INTERFAZ)):
    ids = re.findall(r"[\"']BOE-A-\d{4}-\d+[\"']", texto)
    comprobar(f"{fich} NO lleva ids del BOE escritos a mano", not ids,
              str(ids[:4]))

comprobar("el instalador pregunta al catalogo", "catalogo" in INSTALAR)
comprobar("y la ventana TAMBIEN, para el boton de actualizar",
          "catalogo" in INTERFAZ)
comprobar("el boton re-ingiere LA LISTA, no lo que haya en local",
          "CAT.del_disco()" in INTERFAZ or "catalogo.del_disco()" in INTERFAZ)
comprobar("  y ya no recorre `self.ix.rutas` como unica fuente",
          "for nid in sorted({r.stem for r in self.ix.rutas})" not in INTERFAZ)

# ==================================== 5. CONTROL NEGATIVO
print("\n=== 5. LA PRUEBA SABE PONERSE ROJA ===")
print("  Se rompen las dos cosas que tienen que estar protegidas: que la")
print("  lista viaje, y que nadie la lleve escrita.\n")

# (a) LA LISTA DEJA DE VIAJAR
guardado = (CAT.RAIZ, CAT.LISTA, CAT.CORPUS, CAT.SELLOS)
try:
    d = equipo_con(MENOS_TRES, TODAS)
    con_raiz_en(d)
    (d / "normas_del_corpus.json").unlink()      # como si no viajara
    comprobar("(a) sin lista, el equipo corto NO descubre las tres: es el "
              "defecto original, y el bloque 3 lo caza",
              len(CAT.faltan()) == 0, len(CAT.faltan()))
finally:
    CAT.RAIZ, CAT.LISTA, CAT.CORPUS, CAT.SELLOS = guardado

# (b) LA LISTA VUELVE A ESCRIBIRSE A MANO
falso = INSTALAR.replace(
    "def falta_corpus() -> list:",
    'NORMAS = [("BOE-A-1992-28740", "IVA")]\n\n\ndef falta_corpus() -> list:', 1)
ids = re.findall(r"[\"']BOE-A-\d{4}-\d+[\"']", falso)
comprobar("(b) si alguien vuelve a escribir un id a mano, el bloque 4 lo caza",
          bool(ids), str(ids))

# (c) y sin romper nada, todo vuelve
comprobar("(c) sin romper nada, la lista y el corpus siguen cuadrando",
          {n["id"] for n in CAT.del_disco()} == {n["id"] for n in CAT.del_corpus()})

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
