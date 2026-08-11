#!/usr/bin/env python3
"""LA PUERTA QUE SE CIERRA SOLA ANTE UNA NORMA A MEDIO CONSOLIDAR.

    python pruebas/prueba_pendientes.py

Cero red, cero API: se lee el crudo del BOE que ya esta en disco.

EL BOE marca algunas normas como «Desactualizado»: estan en la base
consolidada pero hay reformas publicadas sin meter en el texto. Ingerir una asi
es citar articulos derogados CON ENLACE Y CON SEGURIDAD, que es la peor forma
de equivocarse que tiene este sistema: la respuesta sale impecable.

LO QUE NO SE PUEDE PERDER, y por que:

  · QUE «POSTERIORES» NO ES «PENDIENTES». Es el historico de todo lo que ha
    tocado la norma. Medido sobre el Decreto Legislativo 1/2024: SEIS de las
    OCHO ya estaban dentro. Leerlo como lista de pendientes marcaria como no
    citables 30 preceptos que estan perfectamente vigentes, y eso tambien es
    mentir, solo que por el otro lado.

  · QUE LA PUERTA SE CIERRE CUANDO NO SE PUEDE SABER. Una nota que dice «SE
    MODIFICA determinados preceptos» no se convierte en ninguna lista. Creerse
    que si es como se ingiere a medias, y una norma con la mitad de los avisos
    puestos es peor que no tenerla: la mitad que falta se cita igual de segura
    que el resto.

  · QUE EL LECTOR NO INVENTE PRECEPTOS. La primera version leia «arts. 632-1.4»
    y sacaba de ahi un «articulo 632» que no existe, porque mezclaba las dos
    numeraciones. Un marcado con preceptos inventados es ruido con aspecto de
    rigor.
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from agente_fiscal import pendientes as P  # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:104]}" if not ok else ""))
    if not ok:
        fallos.append(que)


# ================================================ 1. LEER LA PROSA
print("\n=== 1. QUE SE PUEDE SACAR DE LA NOTA Y QUE NO ===")

CLARAS = {
    "los arts. 632-1.4, 684-2, SE MODIFICA los arts. 631-20, 641.1":
        {"632-1", "684-2", "631-20", "641-1"},
    "SE MODIFICA la disposición transitoria 1 del libro sexto":
        {"disposicion transitoria 1"},
}
for texto, esperado in CLARAS.items():
    leido = P._preceptos_de(texto)
    comprobar(f"«{texto[:44]}…» -> {sorted(esperado)}", leido == esperado, leido)

comprobar("«641.1» se lee como 641-1, que es el articulo de verdad",
          "641-1" in P._preceptos_de("SE MODIFICA los arts. 631-20, 641.1"))
comprobar("y de «632-1.4» NO sale ningun «632» inventado",
          P._preceptos_de("los arts. 632-1.4") == {"632-1"},
          P._preceptos_de("los arts. 632-1.4"))

VAGAS = {
    "SE MODIFICA y SE AÑADE, con los efectos indicados, determinados preceptos":
        "determinados preceptos",
    "SE MODIFICA la subsección 8 de la sección I del capítulo I del título III":
        "bloque entero",
    "y, en la forma indicada, el art. 612-15": "forma indicada",
    "SE MODIFICA el anexo, por Decreto-ley 3/2026": "anexo",
}
for texto, _que in VAGAS.items():
    comprobar(f"«{texto[:46]}…» se marca como NO convertible",
              bool(P._dudas_de(texto)), P._dudas_de(texto))
comprobar("una correccion de erratas tambien, aunque su texto parezca inocente",
          bool(P._dudas_de("en el Decreto ley 21/2025, de 14 de octubre",
                           "SE CORRIGEN erratas")))

# ================================================ 2. LA NORMA DE VERDAD
print("\n=== 2. EL DECRETO LEGISLATIVO 1/2024, CON EL CRUDO DEL BOE ===")

D = RAIZ / "datos" / "crudo" / "BOE-A-2024-6951"
if not D.is_dir():
    comprobar("el crudo del BOE esta en disco", False,
              "falta datos/crudo/BOE-A-2024-6951: "
              "python fase1.py inspeccionar BOE-A-2024-6951")
else:
    an = json.loads(sorted(f for f in D.glob("analisis_*.json")
                           if not f.name.endswith(".meta.json"))[-1]
                    .read_text(encoding="utf-8"))
    xml = sorted(f for f in D.glob("texto_*.xml")
                 if not f.name.endswith(".meta.json"))[-1].read_bytes()
    inf = P.leer((an.get("data") or [{}])[0], xml, "Desactualizado")

    print(f"    consolidado hasta {inf.consolidado_hasta} · "
          f"{len(inf.reformas)} reformas · {len(inf.pendientes)} pendientes")
    comprobar("se lee hasta cuando esta consolidada",
              inf.consolidado_hasta == "2026-05-23", inf.consolidado_hasta)
    comprobar("«posteriores» NO se confunde con «pendientes»",
              len(inf.reformas) == 8 and len(inf.pendientes) == 2,
              f"{len(inf.reformas)} / {len(inf.pendientes)}")
    incorporadas = [r.id_norma for r in inf.reformas if r.incorporada]
    comprobar("  y las 6 incorporadas se reconocen por el articulado",
              len(incorporadas) == 6, incorporadas)
    comprobar("  las pendientes son las dos del DOGC, que el BOE no ha recogido",
              all(r.id_norma.startswith("DOGC") for r in inf.pendientes),
              [r.id_norma for r in inf.pendientes])

    print("\n  Y LA PUERTA:")
    comprobar("NO se da por fiable: hay una pendiente que no se deja leer",
              inf.fiable is False, inf.fiable)
    comprobar("  y se dice CUAL y POR QUE, no solo que no",
              len(inf.motivos) >= 1
              and all(":" in m for m in inf.motivos), inf.motivos)
    for m in inf.motivos:
        print(f"      · {m.splitlines()[0][:88]}")

# ================================================ 3. CONTROL NEGATIVO
print("\n=== 3. LA PRUEBA SABE PONERSE ROJA ===")
print("  Ninguna prueba se da por buena sin verla fallar cuando debe fallar.\n")

# (a) una norma sin nada pendiente tiene que poder pasar: si la puerta dijera
#     que no SIEMPRE, no seria una puerta, seria un muro.
limpia = P.Informe(consolidado_hasta="2026-05-23", estado="Finalizado")
limpia.reformas = [P.Reforma("BOE-X", "SE MODIFICA", "SE MODIFICA el art. 12",
                             incorporada=True, preceptos={"12"})]
comprobar("(a) una norma con todo incorporado no tiene pendientes",
          not limpia.pendientes)

legible = P.Informe(consolidado_hasta="2026-05-23")
legible.reformas = [P.Reforma("DOGC-Y", "SE DEROGA",
                              "SE DEROGA los arts. 641-14 y 642-1",
                              incorporada=False,
                              preceptos={"641-14", "642-1"}, dudas=[])]
comprobar("(a) y una pendiente que SI enumera se declara fiable",
          legible.fiable is True, legible.fiable)
comprobar("  con su lista de preceptos a marcar",
          legible.preceptos_tocados == {"641-14", "642-1"},
          legible.preceptos_tocados)

# (b) se afloja el lector: deja de detectar la prosa vaga
original = P._VAGO
try:
    P._VAGO = ()
    d = P._dudas_de("SE MODIFICA determinados preceptos")
    print(f"    sin los patrones de prosa vaga, «determinados preceptos» da "
          f"{len(d)} dudas")
    comprobar("(b) sin ellos una nota vaga pasaria por buena, y el bloque 1 "
              "lo cazaria", not d, d)
finally:
    P._VAGO = original
comprobar("(b) y al deshacerlo vuelve a cazarla",
          bool(P._dudas_de("SE MODIFICA determinados preceptos")))

# (c) se lee «posteriores» como si fuera «pendientes»
if D.is_dir():
    todas = [r.id_norma for r in inf.reformas]
    tocados_mal = set()
    for r in inf.reformas:          # sin mirar si estan incorporadas
        tocados_mal |= r.preceptos
    print(f"    leyendo el historico como pendientes se marcarian "
          f"{len(tocados_mal)} preceptos en vez de {len(inf.preceptos_tocados)}")
    comprobar("(c) confundir historico con pendiente marca de mas, y el "
              "bloque 2 lo cazaria",
              len(tocados_mal) > len(inf.preceptos_tocados),
              f"{len(tocados_mal)} vs {len(inf.preceptos_tocados)}")

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
