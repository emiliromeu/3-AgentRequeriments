#!/usr/bin/env python3
"""LA BUSQUEDA MIRA EN LA LEY DEL IMPUESTO DE LA PREGUNTA. Cero red, cero API.

    python pruebas/prueba_filtro.py

El corpus ya sabia de que impuesto es cada cuerpo -la regla del papel- y el
analizador ya sabia de que impuesto es la pregunta. Faltaba unirlos.

POR QUE ESTO IMPORTA MAS DE LO QUE PARECE. Sin filtro, una pregunta de
Patrimonio con vocabulario compartido -«escala de gravamen», «vivienda
habitual»- recuperaba CINCO DE CINCO articulos del IRPF. Y EL VERIFICADOR NO LO
SALVA: la cita del articulo 63 de la Ley 35/2006 es literal y correcta, existe y
dice lo que se dice que dice. Lo que falla es que no viene al caso, y eso no lo
mira nadie. Es un fallo que sale en pantalla con toda la seguridad del mundo.

LAS DOS SALVEDADES, que aqui se comprueban una por una:

  · LAS REMISIONES SIGUEN CRUZANDO DE IMPUESTO. Si un precepto elegido remite a
    uno de otro impuesto, ese entra. Es la nota al pie, y medio proyecto existe
    para no perderla.
  · SI EL IMPUESTO NO SE HA PODIDO DETERMINAR, NO SE FILTRA. Filtrar con un
    impuesto equivocado es peor que no filtrar: sin filtro se compite de mas y
    el corte por pertinencia hace su trabajo; con el filtro equivocado se
    pierde la ley que tocaba y no se nota.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4  # noqa: E402
from agente_fiscal import estado as EST  # noqa: E402
from agente_fiscal import referencias as R  # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:104]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix, grafo = fase4.cargar_corpus()
N = ix.normas
TOPE = fase4.TOPE_MATERIAL
LIP, LIRPF, RIRPF = "BOE-A-1991-14392", "BOE-A-2006-20764", "BOE-A-2007-6820"
print(f"corpus: {len(ix.docs)} preceptos · {len(N.cuerpos)} cuerpos · "
      f"impuestos {sorted(N.impuestos())}")


def buscar(consulta, impuesto):
    return ix.buscar_del_impuesto(consulta, TOPE,
                                  N.admitidos_para(impuesto), grafo)


def normas_de(resultados):
    return [r.doc.registro["norma_id"] for r in resultados]


# ================================================ 1. DE QUE ES CADA CUERPO
print("\n=== 1. CADA CUERPO SABE DE QUE IMPUESTO ES ===")
print("  Incluido el cuerpo 0 de un real decreto aprobatorio, que no nombra")
print("  materia ninguna: es del impuesto del reglamento que aprueba.\n")

comprobar("la Ley 19/1991 es de Patrimonio",
          N.impuesto_de_cuerpo(f"{LIP}#0") == "IP", N.impuesto_de_cuerpo(f"{LIP}#0"))
comprobar("el Reglamento del IRPF es de Renta",
          N.impuesto_de_cuerpo(f"{RIRPF}#1") == "IRPF")
comprobar("y los 8 articulos que lo aprueban TAMBIEN, aunque no lo digan",
          N.impuesto_de_cuerpo(f"{RIRPF}#0") == "IRPF",
          N.impuesto_de_cuerpo(f"{RIRPF}#0"))
comprobar("la LGT no es de ningun impuesto: es general",
          N.impuesto_de_cuerpo("BOE-A-2003-23186#0") == "")
comprobar("y el RGAT tampoco", N.impuesto_de_cuerpo("BOE-A-2007-15984#1") == "")

# ================================================ 2. DONDE SE BUSCA
print("\n=== 2. SE BUSCA EN EL IMPUESTO Y EN LAS GENERALES ===")
# `admitidos_para` devuelve CODIGOS DE IMPUESTO, no cuerpos: la unidad de
# clasificacion es el precepto desde que hay codigos por libros con varios
# impuestos dentro del mismo cuerpo. Ver `normas.impuesto_de_precepto`.
for imp in sorted(N.impuestos()):
    cu = N.admitidos_para(imp)
    comprobar(f"{imp}: entra el suyo y entran las generales",
              cu == {imp, ""}, cu)
    dentro = [d for d in ix.docs if N.admite(d.registro, cu)]
    otros = {N.impuesto_de_precepto(d.registro) for d in dentro} - {imp, ""}
    comprobar(f"  {imp}: y NI UN PRECEPTO de otro impuesto", not otros,
              sorted(otros))
    print(f"      {imp}: {len(dentro)} preceptos de {len(ix.docs)} pueden competir")

# ================================================ 3. LOS CUATRO MEDIDOS
print("\n=== 3. LOS CUATRO CASOS QUE DESTAPARON ESTO ===")
print("  Los dos ultimos traian CINCO DE CINCO articulos del IRPF para una")
print("  pregunta de Patrimonio.\n")

CASOS = {
    "vocabulario propio del patrimonio":
        "minimo exento patrimonio neto base imponible bienes y derechos de "
        "contenido economico",
    "quien esta obligado a declarar":
        "obligacion de declarar patrimonio neto sujeto pasivo por obligacion "
        "personal",
    "LA ESCALA (traia 5/5 del IRPF)":
        "escala de gravamen base liquidable patrimonio neto cuota integra",
    "LA VIVIENDA HABITUAL (traia 5/5 del IRPF)":
        "exencion vivienda habitual del contribuyente patrimonio neto",
}
for que, consulta in CASOS.items():
    sin_filtro, _h = ix.buscar(consulta, tope=TOPE)
    con_filtro, _h2, _r = buscar(consulta, "IP")
    irpf_antes = sum(1 for n in normas_de(sin_filtro) if n in (LIRPF, RIRPF))
    irpf_ahora = sum(1 for n in normas_de(con_filtro) if n in (LIRPF, RIRPF))
    lip_ahora = sum(1 for n in normas_de(con_filtro) if n == LIP)
    print(f"  «{que}»")
    print(f"      del IRPF: {irpf_antes} -> {irpf_ahora}   "
          f"de la Ley 19/1991: {lip_ahora}/{len(con_filtro)}")
    comprobar(f"  ni un articulo del IRPF compitiendo", irpf_ahora == 0,
              [r.doc.referencia for r in con_filtro if
               r.doc.registro["norma_id"] in (LIRPF, RIRPF)])
    comprobar(f"  y si de la Ley del Patrimonio", lip_ahora > 0)

# ============================== 4. LA REMISION SIGUE CRUZANDO DE IMPUESTO
print("\n=== 4. LA REMISION CRUZA DE IMPUESTO. NO SE NEGOCIA ===")
print("  El articulo 4 de la Ley 19/1991 -bienes y derechos exentos- remite a")
print("  articulos de la Ley 35/2006 cuando habla de planes de pensiones y de")
print("  participaciones en entidades. Esos tienen que entrar aunque sean de")
print("  otro impuesto y aunque no puntuen nada en esta pregunta.\n")

cruces = 0
for origen, lista in grafo.adelante.items():
    do = ix.por_clave.get(origen)
    if do is None:
        continue
    io = N.impuesto_de_cuerpo(do.registro.get("cuerpo_clave") or "")
    for rem in lista:
        dd = ix.por_clave.get(getattr(rem, "destino", "") or "")
        if dd is None:
            continue
        idd = N.impuesto_de_cuerpo(dd.registro.get("cuerpo_clave") or "")
        if io and idd and io != idd:
            cruces += 1
comprobar(f"el corpus tiene remisiones que cruzan de impuesto ({cruces})",
          cruces > 0, cruces)

CONSULTA = ("bienes y derechos exentos del impuesto sobre el patrimonio: plan "
            "de pensiones y participaciones en entidades")
dentro, _h, reserva = buscar(CONSULTA, "IP")
comprobar("la reserva NO esta vacia: alguien a quien llamar",
          bool(reserva), len(reserva))
comprobar("  y son de OTRO impuesto, que es de lo que se trata",
          all(N.impuesto_de_cuerpo(r.doc.registro.get("cuerpo_clave") or "")
              not in ("", "IP") for r in reserva),
          [r.doc.referencia for r in reserva])

sel = EST.seleccionar_material(ix, CONSULTA, dentro, grafo, reserva=reserva)
enviados = [(d["referencia"], d["motivo"]) for d in sel.detalle
            if d["decision"] == "enviado"]
claves = {p["clave"] if isinstance(p, dict) else "" for p in []}
por_remision = [(ref, m) for ref, m in enviados if "remite a el" in m]
de_otro = [p for p in sel.elegidos if p["norma_id"] in (LIRPF, RIRPF)]
print(f"    se mandan {len(sel.elegidos)}: "
      + ", ".join(f"{p['referencia']} ({p['norma_id'][-9:]})"
                  for p in sel.elegidos))
comprobar("entran preceptos DE OTRO IMPUESTO", bool(de_otro),
          [p["referencia"] for p in sel.elegidos])
comprobar("  y entran POR REMISION, no por parecerse", bool(por_remision),
          enviados)
comprobar("  el motivo lo dice, para que se pueda auditar",
          any("remite a el" in m for _r, m in por_remision), por_remision)
comprobar("  y NO entran por cobertura: la reserva no compite",
          all(d["decision"] == "descartado"
              or "remite a el" in d["motivo"]
              for d in sel.detalle
              if d["referencia"] not in [r.doc.referencia for r in dentro]))

# ============================ 5. SIN IMPUESTO NO SE FILTRA
print("\n=== 5. SI EL IMPUESTO NO SE SABE, NO SE FILTRA ===")
print("  Filtrar con un impuesto equivocado es peor que no filtrar: se pierde")
print("  la ley que tocaba y la respuesta sale igual de segura citando otra.\n")

for valor, que in (("", "vacio"), (None, "nulo"), ("desconocido", "desconocido"),
                   # ISD estaba aqui como «impuesto que no tenemos» hasta que
                   # se ingirio el 12/08/2026. Se cambia por uno que siga
                   # fuera; lo que se comprueba no cambia.
                   ("otro", "otro"), ("IIEE", "un impuesto que no tenemos")):
    comprobar(f"con «{que}» no se filtra", N.admitidos_para(valor) is None,
              N.admitidos_para(valor))
sin, _h, res_sin = ix.buscar_del_impuesto("escala de gravamen base liquidable",
                                          TOPE, None, grafo)
todo, _h2 = ix.buscar("escala de gravamen base liquidable", tope=TOPE)
comprobar("y sin filtrar sale exactamente lo de siempre",
          [r.doc.clave for r in sin] == [r.doc.clave for r in todo])
comprobar("  con la reserva vacia: no hay a quien reservar", not res_sin)

# ============================ 6. LO QUE NO SE PUEDE MOVER
print("\n=== 6. LO QUE NO SE PUEDE MOVER ===")
DOS_DE_RENTA = {
    "20260810T221943": ["Articulo 12", "Articulo 7", "Articulo 19"],
    "20260810T222047": ["Articulo 30", "Articulo 30", "Articulo 28"],
}
import json  # noqa: E402

for sello, esperados in DOS_DE_RENTA.items():
    d = RAIZ / "datos" / "trazas" / sello
    if not (d / "analisis.json").is_file():
        comprobar(f"la traza {sello} sigue en disco", False, "no esta")
        continue
    an = json.loads((d / "analisis.json").read_text(encoding="utf-8"))
    # Lo que se envio aquel dia se LEE de la traza, no se escribe aqui.
    sel_dia = json.loads((d / "seleccion.json").read_text(encoding="utf-8"))
    envio = [p["referencia"] for p in sel_dia["preceptos"]
             if p["decision"] == "enviado"]
    comprobar(f"{sello}: la traza y lo esperado coinciden", envio == esperados,
              f"{envio} vs {esperados}")
    c = " ".join(an["terminos_busqueda"])
    ahora, _h, _r = buscar(c, an["impuesto"])
    refs = [r.doc.referencia for r in ahora]
    comprobar(f"  {sello}: siguen saliendo los {len(envio)} que se enviaron",
              all(e in refs for e in envio), refs)

# ============================ 7. CONTROL NEGATIVO
print("\n=== 7. LA PRUEBA SABE PONERSE ROJA ===")
print("  Ninguna prueba se da por buena sin verla fallar cuando debe fallar.\n")

# (a) se quita el filtro
original = N.__class__.admitidos_para
try:
    N.__class__.admitidos_para = lambda self, impuesto: None
    roto, _h, _r = buscar(CASOS["LA VIVIENDA HABITUAL (traia 5/5 del IRPF)"], "IP")
    del_irpf = sum(1 for n in normas_de(roto) if n in (LIRPF, RIRPF))
    print(f"    sin filtro, la pregunta de patrimonio trae {del_irpf} de "
          f"{len(roto)} articulos del IRPF")
    comprobar("(a) sin filtro vuelven los del IRPF, y el bloque 3 lo cazaria",
              del_irpf > 0, del_irpf)
finally:
    N.__class__.admitidos_para = original
roto, _h, _r = buscar(CASOS["LA VIVIENDA HABITUAL (traia 5/5 del IRPF)"], "IP")
comprobar("(a) y al deshacerlo vuelven a desaparecer",
          not any(n in (LIRPF, RIRPF) for n in normas_de(roto)))

# (b) se quita la reserva: la remision deja de cruzar
sel_sin = EST.seleccionar_material(ix, CONSULTA, dentro, grafo, reserva=None)
otro_sin = [p for p in sel_sin.elegidos if p["norma_id"] in (LIRPF, RIRPF)]
print(f"    sin reserva, entran {len(otro_sin)} preceptos de otro impuesto")
comprobar("(b) sin reserva se pierde la nota al pie, y el bloque 4 lo cazaria",
          not otro_sin, [p["referencia"] for p in otro_sin])
comprobar("(b) y con reserva vuelve", bool(de_otro))

# (c) se filtra SIEMPRE, tambien sin impuesto: el error que se quiso evitar
try:
    N.__class__.admitidos_para = lambda self, impuesto: {"IVA", ""}
    mal, _h, _r = buscar("escala de gravamen base liquidable patrimonio neto",
                         "desconocido")
    print(f"    filtrando con el impuesto equivocado, sale: "
          f"{', '.join(r.doc.referencia for r in mal[:4])}")
    comprobar("(c) con un impuesto equivocado se pierde la ley que tocaba, "
              "y por eso `admitidos_para` devuelve None cuando no se sabe",
              not any(n == LIP for n in normas_de(mal)), normas_de(mal))
finally:
    N.__class__.admitidos_para = original

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
