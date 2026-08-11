#!/usr/bin/env python3
"""LA REMISION A UN ANEXO DE OTRA NORMA. Cero red, cero API.

    python pruebas/prueba_anexos.py

EL CASO QUE LA JUSTIFICA, y es de los que no se ven: el articulo 95 de la Ley
del IVA limita la deduccion de los «automoviles de turismo», y para saber QUE
ES un automovil de turismo remite al ANEXO del Real Decreto Legislativo
339/1990, que no esta en el corpus. Sin esa definicion no se puede decir si el
vehiculo del cliente es un turismo, que es justo lo que se pregunta.

Y el sistema NO AVISABA: el escaneo de remisiones solo buscaba «articulo N» y
disposiciones, y un anexo no tiene numero de articulo. La respuesta se sostenia
porque el redactor lo suplia por su cuenta, y eso no puede ser el plan.

ESTA SUITE SE PERDIO Y NO SE HABIA REESCRITO. Es la unica que protege ese
detector: sin ella, una remision que nadie ve se pierde en silencio y la unica
señal seria que las respuestas empeoran.

LA OTRA MITAD, que costo tanto como la primera: `_RE_ANEXO` EXIGE DESIGNACION
CON NUMERO. Sin exigirlo, el titulo del propio anexo -«ANEXO / REGLAMENTO DEL
IMPUESTO SOBRE EL VALOR AÑADIDO»- se colaba como remision a otra norma. Medido
sobre el corpus: hay 28 menciones de «anexo» y solo UNA es una remision de
verdad.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4  # noqa: E402
from agente_fiscal import referencias as R  # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:104]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix, grafo = fase4.cargar_corpus()
ART95 = "BOE-A-1992-28740#0#articulo 95"

# ================================================ 1. EL CASO REAL
print("\n=== 1. EL ARTICULO 95 REMITE AL ANEXO DEL RDLEG 339/1990 ===")

doc = ix.por_clave.get(ART95)
comprobar("el articulo 95 esta en el corpus", doc is not None)
texto = " ".join((doc.registro.get("texto_vigente") or "").split())
comprobar("y su texto nombra el anexo de otra norma",
          "anexo" in texto.lower() and "339/1990" in texto,
          texto[:120])

anexos = [r for r in grafo.adelante.get(ART95, [])
          if "anexo" in (r.etiqueta_destino or "").lower()]
print(f"    remisiones a anexo detectadas: {len(anexos)}")
for r in anexos:
    print(f"      {r.etiqueta_destino} · {r.estado} · {r.norma_externa}")
comprobar("SE DETECTA la remision al anexo", bool(anexos))
comprobar("  y queda PENDIENTE, no resuelta: esa norma no esta cargada",
          all(r.estado == R.PENDIENTE for r in anexos),
          [r.estado for r in anexos])
comprobar("  con la norma nombrada, para poder ir a buscarla",
          any("339/1990" in (r.norma_externa or "") for r in anexos),
          [r.norma_externa for r in anexos])

# ================================================ 2. LA SEGUNDA MITAD
print("\n=== 2. SE EXIGE DESIGNACION CON NUMERO ===")
print("  Sin exigirlo, el titulo del propio anexo se colaba como remision.\n")

SI = {
    "en los terminos del anexo del Real Decreto Legislativo 339/1990":
        "Real Decreto Legislativo 339/1990",
    "el anexo de la Ley 38/1992": "Ley 38/1992",
    "segun el anexo I de la Directiva 2006/112": "Directiva 2006/112",
}
NO = (
    "ANEXO",
    "ANEXO. REGLAMENTO DEL IMPUESTO SOBRE EL VALOR AÑADIDO",
    "lo previsto en el anexo de esta Ley",
    "el anexo que se acompaña",
    "en el anexo del Reglamento",              # sin numero: no se sabe cual
)
for texto_p, norma in SI.items():
    m = R._RE_ANEXO.search(texto_p)
    comprobar(f"«{texto_p[:46]}…» -> {norma}",
              m is not None and norma.lower() in m.group("norma").lower(),
              m.group("norma") if m else None)
for texto_p in NO:
    m = R._RE_ANEXO.search(texto_p)
    comprobar(f"«{texto_p[:46]}» NO es una remision", m is None,
              m.group(0) if m else None)

# ================================================ 3. EN TODO EL CORPUS
print("\n=== 3. EN EL CORPUS ENTERO ===")
menciones = sum(1 for d in ix.docs
                if "anexo" in (d.registro.get("texto_vigente") or "").lower())
detectadas = [r for lista in grafo.adelante.values() for r in lista
              if "anexo" in (r.etiqueta_destino or "").lower()]
print(f"    preceptos que mencionan «anexo»: {menciones}")
print(f"    remisiones a anexo detectadas  : {len(detectadas)}")
comprobar("se detecta alguna", bool(detectadas))
comprobar("pero NO una por cada mencion: la mayoria no son remisiones",
          len(detectadas) < menciones, f"{len(detectadas)} vs {menciones}")
comprobar("y ninguna se da por RESUELTA: son normas que no tenemos",
          all(r.estado != R.RESUELTA for r in detectadas),
          [(r.etiqueta_destino, r.estado) for r in detectadas
           if r.estado == R.RESUELTA][:3])

# ================================================ 4. CONTROL NEGATIVO
print("\n=== 4. LA PRUEBA SABE PONERSE ROJA ===")
print("  No basta con decir que caza: hay que romper el codigo y verlo caer.\n")

import re  # noqa: E402

original = R._RE_ANEXO

# (a) SE QUITA EL DETECTOR ENTERO. Es lo que habia antes de la fase 8: el
#     escaneo solo miraba «articulo N» y disposiciones.
try:
    R._RE_ANEXO = re.compile(r"(?!x)x")          # no casa nunca
    g2 = R.GrafoRemisiones(ix.docs)
    quedan = [r for r in g2.adelante.get(ART95, [])
              if "anexo" in (r.etiqueta_destino or "").lower()]
    print(f"    sin detector, el art. 95 tiene {len(quedan)} remisiones a anexo")
    comprobar("(a) sin el detector la del art. 95 se pierde, y el bloque 1 "
              "lo cazaria", not quedan, quedan)
finally:
    R._RE_ANEXO = original

# (b) SE AFLOJA: se deja de exigir el numero de la norma. Es la version que
#     tuvimos y que colaba el titulo del propio anexo.
try:
    R._RE_ANEXO = re.compile(
        r"\banexos?\b[^.;:]{0,40}?\b(?P<norma>(?:Real\s+Decreto(?:\s+Legislativo|-ley)?|"
        r"Ley\s+Org[aá]nica|Ley|Reglamento|Directiva|Orden|Decreto))",
        re.IGNORECASE)
    g3 = R.GrafoRemisiones(ix.docs)
    falsas = [r for lista in g3.adelante.values() for r in lista
              if "anexo" in (r.etiqueta_destino or "").lower()]
    print(f"    sin exigir numero, salen {len(falsas)} remisiones a anexo "
          f"(con el numero: {len(detectadas)})")
    comprobar("(b) aflojando la regla salen remisiones de mas, y el bloque 3 "
              "lo cazaria", len(falsas) > len(detectadas),
              f"{len(falsas)} vs {len(detectadas)}")
    colado = [r.norma_externa for r in falsas
              if r.norma_externa and not re.search(r"\d+/\d{2,4}",
                                                   r.norma_externa)]
    comprobar("  y son designaciones SIN numero, que no identifican nada",
              bool(colado), colado[:4])
    print(f"      ejemplos de lo que se cuela: {colado[:3]}")
finally:
    R._RE_ANEXO = original

# (c) y al deshacerlo, todo vuelve a su sitio
g4 = R.GrafoRemisiones(ix.docs)
comprobar("(c) al deshacerlo vuelve el detector bueno",
          len([r for lista in g4.adelante.values() for r in lista
               if "anexo" in (r.etiqueta_destino or "").lower()])
          == len(detectadas))
comprobar("(c) y la del art. 95 sigue ahi",
          any("anexo" in (r.etiqueta_destino or "").lower()
              for r in g4.adelante.get(ART95, [])))

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
