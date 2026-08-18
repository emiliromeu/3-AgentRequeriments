#!/usr/bin/env python3
"""LA REMISION VA AL CUERPO QUE TIENE EL ARTICULO. Cero red, cero API.

    python pruebas/prueba_remisiones.py

LA MISMA REGLA QUE YA CORREGIA LAS CITAS DE LA DGT, y que el grafo no llamaba.

Un documento del BOE puede traer dos articulados: el del Real Decreto que
aprueba -uno o seis articulos- y el del Reglamento aprobado -ciento y pico-. El
texto cita «el articulo 22 del Real Decreto 439/2007», la designacion resuelve
limpiamente al DECRETO y el 22 vive en el Reglamento.

NO HAY DOS COPIAS DE LA REGLA: `cuerpo_hermano_con` vive en `normas.py` y es la
unica que hay. Lo que faltaba no era la regla, era el SEGUNDO CONSUMIDOR. Es la
misma leccion que el patron de norma compartido por ocho sitios: al escribir una
regla, la pregunta no es donde ponerla, sino quien mas deberia preguntarla.

Y AQUI NO HABIA DEFECTO SILENCIOSO, al reves que en la DGT -donde eran 92 citas
dadas por buenas-. El grafo busca el articulo DENTRO del inventario del cuerpo,
asi que una remision resuelta nunca apunta a un articulo que no existe. Lo que
se gana sale de «no encontrada», no de citas malas que pasaban por buenas.
"""
import json
import shutil
import sys
import tempfile
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4                                    # noqa: E402
from agente_fiscal import referencias as R      # noqa: E402
from agente_fiscal.indice import Indice         # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:110]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix, g = fase4.cargar_corpus()
N = ix.normas

# ==================================== 1. EL CORPUS DE VERDAD
print("\n=== 1. EL INVARIANTE, QUE AQUI ES ESTRUCTURAL ===")
print("  El grafo busca el articulo DENTRO del inventario del cuerpo, asi que")
print("  una remision resuelta no puede apuntar a un articulo inexistente.\n")

malas = [r for rems in g.adelante.values() for r in rems
         if r.estado == R.RESUELTA and r.destino and r.destino not in ix.por_clave]
comprobar("ninguna remision resuelta apunta a un precepto que no existe",
          not malas, len(malas))
print(f"    resueltas {g.stats.resueltas} · no encontradas "
      f"{g.stats.no_encontradas}")
comprobar("quedan menos de 70 sin resolver (eran 115)",
          g.stats.no_encontradas < 70, g.stats.no_encontradas)

# ==================================== 2. EL CORPUS DE MENTIRA
print("\n=== 2. EL POSITIVO Y EL ADVERSARIO ===")
print("  Un decreto de un articulo y su reglamento de varios. La cita al 22")
print("  tiene que ir al reglamento; la del 1, que SI existe en el decreto,")
print("  tiene que quedarse donde esta.\n")


def _p(norma, cu, num, ref, texto, titulo, pos):
    return {"norma_id": norma, "cuerpo_indice": cu,
            "cuerpo_clave": f"{norma}#{cu}", "norma_titulo": titulo,
            "tipo": "articulo", "tipo_boe": "precepto", "referencia": ref,
            "referencia_corta": ref, "clave": f"{norma}#{cu}#{ref.lower()}",
            "clave_local": ref.lower(), "numero": num, "numero_norm": num,
            "contexto": [], "rubrica": "", "es_rango": False,
            "suprimido": False, "caducado_desde": "", "incidencias": [],
            "avisos": [], "vigente_desde": "1999-01-01",
            "fechas_vigencia": ["1999-01-01"], "n_versiones": 1,
            "versiones": [], "notas_boe": [], "texto_vigente": texto,
            "posicion": pos}


TITULO = "Real Decreto 9/1999, por el que se aprueba el Reglamento de mentira"


def corpus_de_mentira():
    d = Path(tempfile.mkdtemp())
    filas = [
        # El decreto que aprueba: UN articulo.
        _p("BOE-A-9999-3", 0, "1", "Articulo 1",
           "Articulo 1. Aprobacion.\nSe aprueba el Reglamento adjunto.",
           TITULO, 1),
        # El reglamento: varios, y uno de ellos remite al 22 nombrando el RD.
        _p("BOE-A-9999-3", 1, "5", "Articulo 5",
           "Articulo 5. Remite.\nSe aplicara lo previsto en el articulo 22 "
           "del Real Decreto 9/1999.", TITULO, 2),
        _p("BOE-A-9999-3", 1, "22", "Articulo 22",
           "Articulo 22. Destino.\nTexto llano.", TITULO, 3),
        # Y otra que remite al 1, que SI existe en el decreto.
        _p("BOE-A-9999-3", 1, "6", "Articulo 6",
           "Articulo 6. Otra.\nSegun el articulo 1 del Real Decreto 9/1999.",
           TITULO, 4),
        # Una norma AJENA que tambien tiene un articulo 22: la correccion no
        # puede irse ahi.
        _p("BOE-A-9999-4", 0, "22", "Articulo 22",
           "Articulo 22. De otra ley.\nTexto.", "Ley de mentira 2/1999", 1),
    ]
    for norma in ("BOE-A-9999-3", "BOE-A-9999-4"):
        (d / f"{norma}.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n"
                    for r in filas if r["norma_id"] == norma),
            encoding="utf-8")
    return d


def resolver_con(modulo):
    d = corpus_de_mentira()
    try:
        gg = modulo.GrafoRemisiones(Indice(d).docs)
        return {r.origen.split("#")[-1] + " -> " + r.texto.strip():
                (r.estado, r.destino) for rems in gg.adelante.values()
                for r in rems}
    finally:
        shutil.rmtree(d, ignore_errors=True)


hoy = resolver_con(R)
for k, v in sorted(hoy.items()):
    print(f"    {k:42s} {v[0]:14s} {v[1] or '-'}")

clave22 = next((v[1] for k, v in hoy.items() if "articulo 22" in k), "")
comprobar("EL POSITIVO: el 22 se resuelve al REGLAMENTO, no al decreto",
          clave22 == "BOE-A-9999-3#1#articulo 22", clave22)
comprobar("  y NO se va a la otra norma, que tambien tiene un 22",
          not clave22.startswith("BOE-A-9999-4"), clave22)
clave1 = next((v[1] for k, v in hoy.items() if "articulo 1" in k), "")
comprobar("EL ADVERSARIO: el 1 SI existe en el decreto y se queda alli",
          clave1 == "BOE-A-9999-3#0#articulo 1", clave1)

# ==================================== 3. CONTROL NEGATIVO, LAS DOS MITADES
print("\n=== 3. LA PRUEBA SABE PONERSE ROJA, POR LOS DOS LADOS ===")

FUENTE = (RAIZ / "agente_fiscal" / "referencias.py").read_text("utf-8")


def roto(viejo, nuevo, fuente=None):
    fuente = fuente or FUENTE
    if viejo not in fuente:
        raise AssertionError(f"la mutacion ya no encaja: {viejo[:70]}")
    mod = types.ModuleType("agente_fiscal.ref_roto")
    mod.__package__ = "agente_fiscal"
    mod.__file__ = str(RAIZ / "agente_fiscal" / "referencias.py")
    sys.modules[mod.__name__] = mod
    try:
        exec(compile(fuente.replace(viejo, nuevo, 1), mod.__file__, "exec"),
             mod.__dict__)
    finally:
        del sys.modules[mod.__name__]
    return mod


# (a) SIN LA LLAMADA: vuelven las 56.
sin_llamada = roto("        if not clave and self.normas is not None:",
                   "        if False:")
r_a = resolver_con(sin_llamada)
c22 = next((v for k, v in r_a.items() if "articulo 22" in k), ("", ""))
comprobar("(a) sin la llamada, el 22 vuelve a no encontrarse",
          c22[0] == R.NO_ENCONTRADA, c22)
g_a = sin_llamada.GrafoRemisiones(ix.docs)
print(f"       y en el corpus de verdad: {g_a.stats.no_encontradas} sin "
      f"resolver (con la llamada, {g.stats.no_encontradas})")
comprobar("  con las 56 perdidas otra vez",
          g_a.stats.no_encontradas >= g.stats.no_encontradas + 50,
          g_a.stats.no_encontradas)

# (b) SIN LA CONTENCION DEL MISMO DOCUMENTO: el 22 se va a la otra norma.
FN = (RAIZ / "agente_fiscal" / "normas.py").read_text("utf-8")
mod_n = types.ModuleType("agente_fiscal.normas_roto")
mod_n.__package__ = "agente_fiscal"
mod_n.__file__ = str(RAIZ / "agente_fiscal" / "normas.py")
VIEJO_N = ("        hermanos = [c for c in self.cuerpos\n"
           "                    if c != clave_cuerpo and c.split(\"#\")[0] == documento\n"
           "                    and self.tiene_articulo(c, num)]")
NUEVO_N = ("        hermanos = [c for c in self.cuerpos\n"
           "                    if c != clave_cuerpo and self.tiene_articulo(c, num)]")
comprobar("la contencion del mismo documento esta en `normas.py`",
          VIEJO_N in FN)
if VIEJO_N in FN:
    sys.modules[mod_n.__name__] = mod_n
    try:
        exec(compile(FN.replace(VIEJO_N, NUEVO_N, 1), mod_n.__file__, "exec"),
             mod_n.__dict__)
    finally:
        del sys.modules[mod_n.__name__]
    # HACE FALTA OTRO CORPUS, y el motivo es que la regla tiene DOS guardas.
    # Con el de arriba, quitar la contencion del documento no enseña nada: el
    # articulo 22 esta en el reglamento Y en la ley ajena, asi que la otra
    # guarda -«si lo tienen varios, no se corrige»- lo declina igual. Para ver
    # el peligro hace falta que SOLO lo tenga la norma ajena.
    d = Path(tempfile.mkdtemp())
    try:
        filas = [
            _p("BOE-A-9999-5", 0, "1", "Articulo 1",
               "Articulo 1. Aprobacion.\nSe aprueba el Reglamento.", TITULO, 1),
            _p("BOE-A-9999-5", 1, "5", "Articulo 5",
               "Articulo 5. Remite.\nSe aplicara el articulo 22 del Real "
               "Decreto 9/1999.", TITULO, 2),
            _p("BOE-A-9999-6", 0, "22", "Articulo 22",
               "Articulo 22. De otra ley.\nTexto.", "Ley de mentira 2/1999", 1),
        ]
        for norma in ("BOE-A-9999-5", "BOE-A-9999-6"):
            (d / f"{norma}.jsonl").write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n"
                        for r in filas if r["norma_id"] == norma),
                encoding="utf-8")
        ixf = Indice(d)

        def destinos_con(registro):
            gg = R.GrafoRemisiones(ixf.docs, registro)
            return {r.texto.strip(): r.destino
                    for rems in gg.adelante.values() for r in rems}

        from agente_fiscal import normas as _NM
        bien = destinos_con(_NM.Registro(ixf.docs))
        mal_ = destinos_con(mod_n.Registro(ixf.docs))
        comprobar("CON la contencion, el 22 NO se resuelve: ninguna norma "
                  "hermana lo tiene", not bien.get("articulo 22"), bien)
        comprobar("(b) sin la contencion, se va a OTRA norma",
                  (mal_.get("articulo 22") or "").startswith("BOE-A-9999-6"),
                  mal_)
    finally:
        shutil.rmtree(d, ignore_errors=True)

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
