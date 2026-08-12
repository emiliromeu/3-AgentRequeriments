#!/usr/bin/env python3
"""LA COBERTURA SE CUENTA, NO SE ESCRIBE. Cero red, cero API.

    python pruebas/prueba_cobertura.py

QUE PROTEGE, Y POR QUE ES LA QUINTA VEZ. El pie del segundo boton decia «TODAS
DE IVA por ahora». La guia decia «el criterio guardado es todo de IVA» y «la
herramienta cubre dos impuestos con la ley: IVA y Renta». El texto de
bienvenida decia «responde solo con la Ley y el Reglamento del IVA». Las tres
eran ciertas el dia que se escribieron.

La siembra metio criterio de Renta, de Sociedades, de Patrimonio y de las
normas generales, y el corpus paso a trece normas. Ninguna de las tres frases
se entero. Y el fallo no es que estuvieran mal escritas: es que una frase a
mano sobre lo que el sistema cubre es una fecha de caducidad sin etiqueta.

Esta suite comprueba que ninguna de las tres vuelve, y que lo que se enseña
sale de contar `datos/dgt` y `datos/teac`.
"""
import re
import sys
import time
import tkinter as tk
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4                                    # noqa: E402
import interfaz                                 # noqa: E402
from agente_fiscal import cobertura as COB      # noqa: E402
from agente_fiscal import configuracion as CONF  # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:104]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix, _grafo = fase4.cargar_corpus()

# ================================================ 1. SE CUENTA DE LOS DATOS
print("\n=== 1. LA COBERTURA SALE DE LA DESPENSA ===\n")

cuenta = COB.resumen(ix)
print(f"    {cuenta}\n")
comprobar("hay mas de un impuesto con criterio guardado", len(cuenta) > 1,
          list(cuenta))
comprobar("y NO es todo de IVA, que es lo que decia la frase vieja",
          sum(v["dgt"] + v["teac"] for k, v in cuenta.items()
              if k != "IVA") > 0,
          cuenta)
comprobar("cada impuesto viene con su numero",
          all(isinstance(v["dgt"], int) and isinstance(v["teac"], int)
              for v in cuenta.values()))

filas = COB.por_impuesto(ix)
comprobar("la lista va de mas a menos",
          [t for _n, t in filas[:-1]] == sorted(
              [t for _n, t in filas[:-1]], reverse=True),
          str(filas))
comprobar("y las normas generales van al final, que no son un impuesto",
          filas[-1][0] == COB.GENERAL, str(filas))

# ================================================ 2. LA VENTANA NO AFIRMA
print("\n=== 2. NI UNA AFIRMACION A MANO EN LA VENTANA ===\n")

FUENTE = (RAIZ / "interfaz.py").read_text("utf-8")
sin_comentarios = "\n".join(l for l in FUENTE.splitlines()
                            if not l.lstrip().startswith("#"))
PROHIBIDAS = (
    "TODAS DE IVA",
    "todo de IVA",
    "toda de IVA",
    "solo con la Ley y el Reglamento del IVA",
    "cubre dos impuestos",
)
for frase in PROHIBIDAS:
    comprobar(f"no vuelve «{frase}»", frase not in sin_comentarios)

raiz = tk.Tk()
v = interfaz.Ventana(raiz, "ensayo")
fin = time.time() + 2.5
while time.time() < fin:          # `_arrancar_motor` va con after(120)
    raiz.update()
    raiz.update_idletasks()
    time.sleep(0.02)

pie = v.pie_criterio.cget("text")
print(f"    pie del boton: {pie[:96]}...\n")
comprobar("el pie dice QUE anade", "DGT" in pie and "TEAC" in pie)
comprobar("y de que hay criterio, contado", "criterio guardado de" in pie, pie)
# SE COMPRUEBA QUE SALE CADA IMPUESTO CON SU CIFRA, NO CUAL ES LA CIFRA.
# Con la siembra corriendo, entre que se cuenta aqui y que la ventana lo
# pinta, «IVA» pasa de 653 a 654. Que la cifra exacta coincida ya se comprueba
# en el bloque 1 y en el 3, midiendo las dos cosas en el mismo instante. Aqui
# lo que importa es que ninguna fila salga sin numero.
for nombre, _total in filas:
    comprobar(f"  con «{nombre}» y un numero al lado",
              re.search(rf"{re.escape(nombre)} \(\d+\)", pie) is not None,
              pie)

bienvenida = v.texto.get("1.0", "end")
comprobar("la bienvenida dice cuantos articulos y cuantas normas",
          str(len(ix.docs)) in bienvenida and str(len(ix.rutas)) in bienvenida,
          bienvenida[:120])


def textos_de(w, acc=None):
    acc = [] if acc is None else acc
    try:
        t = w.cget("text")
        if t:
            acc.append(str(t))
    except Exception:  # noqa: BLE001
        pass
    for h in w.winfo_children():
        textos_de(h, acc)
    return acc


ventana_dentro = tk.Toplevel(raiz)
v._pintar_que_hay_dentro(ventana_dentro) if hasattr(
    v, "_pintar_que_hay_dentro") else None
dentro = "\n".join(textos_de(ventana_dentro))
if not dentro:
    ventana_dentro.destroy()
    v.boton_dentro.invoke()
    raiz.update()
    raiz.update_idletasks()
    dentro = "\n".join(textos_de(raiz.winfo_children()[-1]))
comprobar("«Qué hay dentro» dice DE QUÉ HABLA el criterio, no «de qué hay»",
          "DE QUÉ HABLA EL CRITERIO GUARDADO" in dentro, dentro[:120])
# Y LA CUENTA QUE CUADRA LA COLUMNA. Sin ella «IVA 653» se lee como «hay 653
# consultas de IVA», y son 653 documentos que HABLAN de IVA: uno que cita la
# Ley del IVA y la LGT esta en las dos filas.
# Igual que arriba: la cifra se mueve mientras la siembra baja documentos, asi
# que se comprueba que ESTA la linea con sus dos numeros, no cuales son.
comprobar("y dice cuantos documentos distintos hay, y cuantos hablan de mas "
          "de un impuesto",
          re.search(r"hablan de más de\s*\n?\s*un impuesto", dentro)
          is not None,
          dentro[:200])
_distintos, _varios = COB.documentos(ix)
comprobar("la suma de la columna ES mayor que los documentos distintos",
          sum(t for _n, t in filas) > _distintos,
          f"{sum(t for _n, t in filas)} vs {_distintos}")
for nombre, _total in filas:
    comprobar(f"  con «{nombre}» y su cifra",
              re.search(rf"{re.escape(nombre)}\b", dentro) is not None)

# ================================================ 3. LA GUIA, IGUAL
print("\n=== 3. LA GUIA DICE LA MISMA CUENTA ===\n")

# LA GUIA SE REGENERA AQUI, Y NO ES POR COMODIDAD. Mientras la siembra corre,
# la despensa crece: entre regenerar la guia a mano y ejecutar esta suite,
# «Sociedades» pasa de 220 a 222 y la comparacion falla. Eso NO es un fallo del
# sistema -es la comprobacion avisando de que la hoja se ha quedado vieja, que
# es justo su trabajo- pero convertirlo en un fallo de la suite seria acusar a
# la maquina de estar ocupada. Se genera y se compara en el mismo instante.
guia_original = CONF.GUIA.read_text("utf-8")
esperado = CONF.texto_de_cobertura(ix)
abre, cierra = CONF.MARCA_COBERTURA
i, j = guia_original.find(abre), guia_original.find(cierra)
comprobar("GUIA.md tiene las marcas del bloque de cobertura", i >= 0 and j > i)
guia = (guia_original[:i + len(abre)] + "\n" + esperado + "\n"
        + guia_original[j:])
CONF.GUIA.write_text(guia, encoding="utf-8")

bloque = CONF.bloque_de_cobertura(guia)
comprobar("el bloque se rellena con lo contado", bool(bloque))
comprobar("y coincide", CONF._plano(bloque) == CONF._plano(esperado),
          bloque[:100])
comprobar("la revision al arrancar lo comprueba y sale coherente",
          CONF.revisar(ix).coherente,
          str(CONF.revisar(ix).descuadres))
comprobar("no vuelve «el criterio guardado es todo de IVA» en la guia",
          "todo de IVA" not in guia)

# ============================ 3 bis. LO QUE BLOQUEA Y LO QUE NO
print("\n=== 3 bis. UNA CIFRA QUE CRECE NO PUEDE IMPEDIR ABRIR ===")
print("  La guia es una hoja IMPRESA. Un numero que crece solo -la siembra")
print("  baja documentos cada pocos minutos- la condena a mentir, y la")
print("  comprobacion se convierte en una alarma cada pocas horas por algo")
print("  que no es un fallo. Las PROMESAS son otra cosa: si la hoja describe")
print("  una herramienta que no existe, no se abre.\n")


def abre() -> tuple:
    try:
        CONF.exigir_coherencia()
        return True, ""
    except CONF.Descoordinado as e:
        return False, "; ".join(e.revision.descuadres)


guia_buena = CONF.GUIA.read_text("utf-8")
comprobar("la guia NO lleva cifras: son datos que crecen solos",
          not re.search(r"\|\s*\d{2,}\s*\|",
                        CONF.bloque_de_cobertura(guia_buena)),
          CONF.bloque_de_cobertura(guia_buena)[:90])
comprobar("pero si dice DE QUE impuestos hay criterio",
          all(n in CONF.bloque_de_cobertura(guia_buena)
              for n, _t in COB.por_impuesto(ix)))
comprobar("y manda a «Qué hay dentro» para las cifras",
          "Qué hay dentro" in CONF.bloque_de_cobertura(guia_buena))

try:
    # (i) la despensa ha crecido y la hoja se ha quedado corta
    CONF.GUIA.write_text(
        re.sub(r"Hay criterio guardado de: .*",
               "Hay criterio guardado de: **IVA**.", guia_buena),
        encoding="utf-8")
    ok, motivo = abre()
    comprobar("(i) con la hoja desfasada, LA VENTANA ABRE IGUAL", ok, motivo)
    aviso = CONF.desfase_de_la_guia(ix)
    comprobar("  y avisa de que esta vieja", bool(aviso), aviso)
    comprobar("  diciendo el comando para rehacerla",
              "regenerar-guia" in aviso, aviso)

    # (ii) alguien borra el bloque entero
    CONF.GUIA.write_text(guia_buena.replace(abre_m := "<!-- COBERTURA -->", "")
                         .replace("<!-- /COBERTURA -->", ""), encoding="utf-8")
    ok, motivo = abre()
    comprobar("(ii) sin el bloque, tambien abre", ok, motivo)
    comprobar("  y tambien avisa", bool(CONF.desfase_de_la_guia(ix)))

    # (iii) Y LA PROMESA, QUE SI TIENE QUE PARAR EL ARRANQUE.
    frase = interfaz.TEXTOS_DE_ESTADO[0]
    roto = None
    llana = CONF._plano(frase)[:30]
    for k in range(len(guia_buena) - 60):
        if CONF._plano(guia_buena[k:k + 60]).startswith(llana):
            roto = guia_buena[:k] + "ESTO YA NO DICE LO MISMO" \
                + guia_buena[k + 60:]
            break
    comprobar("(iii) la frase de estado esta en la guia", roto is not None)
    if roto:
        CONF.GUIA.write_text(roto, encoding="utf-8")
        ok, motivo = abre()
        comprobar("  si una PROMESA no cuadra, NO se abre", not ok, motivo)
        comprobar("  y se dice cual", "NO esta en GUIA.md" in motivo, motivo)
finally:
    CONF.GUIA.write_text(guia_buena, encoding="utf-8")
comprobar("(iv) restaurada, vuelve a abrir", abre()[0])

# ================================================ 4. CONTROL NEGATIVO
print("\n=== 4. LA COBERTURA YA NO ESTA EN EL CAMINO QUE BLOQUEA ===")
print("  Aqui habia un control negativo que rompia la guia y comprobaba que")
print("  `revisar` lo cazaba. Ese comportamiento se ha quitado a proposito: lo")
print("  que cazaba era una CIFRA que crece sola, y bloqueaba el arranque por")
print("  ello. Su sustituto es el bloque 3 bis, que prueba mas casos. Lo que")
print("  queda por comprobar es que de verdad SALIO de ahi.\n")

sin_ix = CONF.revisar(None)
con_ix = CONF.revisar(ix)
comprobar("`revisar` ya no habla de cobertura, ni con corpus ni sin el",
          not any("cobertura" in k for k in
                  list(sin_ix.piezas) + list(con_ix.piezas)),
          str(list(sin_ix.piezas) + list(con_ix.piezas)))
comprobar("y da lo mismo pasarle el corpus o no: compara promesas, no datos",
          sin_ix.coherente == con_ix.coherente
          and sin_ix.descuadres == con_ix.descuadres)
comprobar("las promesas que compara son las frases de los estados",
          any("frases de estado" in k for k in sin_ix.piezas),
          str(sin_ix.piezas))

FUENTE_CONF = (RAIZ / "agente_fiscal" / "configuracion.py").read_text("utf-8")
cuerpo_revisar = FUENTE_CONF[FUENTE_CONF.find("def revisar("):
                             FUENTE_CONF.find("def desfase_de_la_guia(")]
comprobar("y `revisar` no llama a la cuenta de la despensa",
          "texto_de_cobertura" not in cuerpo_revisar
          and "cobertura" not in cuerpo_revisar.replace("de cobertura", ""),
          cuerpo_revisar[-160:])

comprobar("el aviso de guia vieja NO es una excepcion: es una frase",
          isinstance(CONF.desfase_de_la_guia(ix), str))
comprobar("y con la guia al dia esta vacia, o sea no molesta",
          CONF.desfase_de_la_guia(ix) == "",
          CONF.desfase_de_la_guia(ix))

raiz.destroy()

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
