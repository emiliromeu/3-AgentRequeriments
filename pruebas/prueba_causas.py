#!/usr/bin/env python3
"""LA MARCA DOBLADA, Y QUE LA CAUSA SE COMPRUEBE. Cero red, cero API.

    python pruebas/prueba_causas.py

DOS COSAS QUE SALIERON DE MIRAR 24 CONSULTAS UNA A UNA.

1. LA MARCA DE ARTICULO ESCRITA DOS VECES. «arts. Arts- 7, 31-2 y 57»: la
   plantilla pone el rotulo y encima el redactor escribe el suyo. El lector
   consumia la primera marca, encontraba una palabra donde esperaba un numero y
   perdia la lista entera.

   EL CUIDADO ES TODO EL PROBLEMA: «art. 70-2» es el articulo 70 apartado 2. Un
   patron que se coma el guion detras de la marca convierte el 70-2 en el 70 y
   el 2, que son DOS articulos que nadie cito. Por eso la segunda marca tiene
   que ser una PALABRA «art» de verdad.

2. Y LA GRAVE: LA CLASIFICACION DE CAUSAS ETIQUETABA POR PARECIDO. Bastaba que
   el campo llevara «RDLeg» para llamarlo «abreviatura no reconocida», AUNQUE LA
   ABREVIATURA YA SE LEYERA. Veintiuna de esas 24 llevaban esa etiqueta y
   ninguna fallaba por eso.

   Una etiqueta que no se puede desmentir no clasifica: decora. Y aqui decorar
   es caro, porque la puerta de la cadena decide con ella: lo que tiene causa
   conocida no la para, y lo que no la tiene si. Etiquetar mal es apagar la
   unica señal que queda para lo que no sabemos.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4                                    # noqa: E402
from agente_fiscal import causas as CAU         # noqa: E402
from agente_fiscal import dgt as D              # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:104]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix, _g = fase4.cargar_corpus()
N = ix.normas


def arts(campo):
    return [p.numero for p in D.pares_de_normativa(campo, N) if p.comparable]


# ==================================== 1. EL POSITIVO: LA MARCA VA DOBLADA
print("\n=== 1. «arts. Arts- 7» ES UNA MARCA DOBLADA: SE DESDOBLA ===")

CASOS = [
    ("TRLITPAJD RDLeg 1/1993 arts. Arts- 7, 31-2 y 57", ["7", "31"]),
    ("RITPAJD RD 828/1995 art. Art 70", ["70"]),
    ("Ley 29/1987 arts. - 3, 4 y 30", ["3", "4", "30"]),
    # OJO: aqui se espera SOLO el 3, y no es lo que a uno le gustaria. El
    # desdoblado funciona -deja «arts. 3-a), 5-a)»- pero la lista se corta en el
    # «)» del primer apartado. Es OTRA forma, anterior a esto y sin
    # diagnosticar; se fija aqui como esta para que si algun dia se arregla se
    # entere alguien, en vez de escribir la expectativa que me gustaria.
    ("Ley 29/1987 arts. arts- 3-a), 5-a)", ["3"]),
]
for campo, esperado in CASOS:
    got = arts(campo)
    comprobar(f"«{campo[:44]}» -> {esperado}", got == esperado, got)

# Y LA (a): el «Legislativo» en el patron. Sin el, la abreviatura se caia en
# cuanto llevaba sigla delante, que es como se escribe SIEMPRE el ITPAJD.
comprobar("«Real Decreto Legislativo 1/1993» se extrae del texto",
          D._RE_NORMA_EXPLICITA.findall(
              "TRLITPAJD Real Decreto Legislativo 1/1993") ==
          ["Real Decreto Legislativo 1/1993"])
comprobar("y por eso «TRLITPAJD RDLeg 1/1993 arts. 6, 7 y 8» resuelve",
          arts("TRLITPAJD RDLeg 1/1993 arts. 6, 7 y 8") == ["6", "7", "8"],
          arts("TRLITPAJD RDLeg 1/1993 arts. 6, 7 y 8"))

# ============ 1 bis. EL TROCEADOR TAMBIEN CONOCE LA ABREVIATURA
print("\n=== 1bis. EL PATRON LO USAN OCHO SITIOS: TAMBIEN EL TROCEADOR ===")
print("  Al ponerle «Legislativo» se penso en el resolutor y se quedo fuera el")
print("  troceador, que usa el MISMO patron para decidir donde cortar.\n")

# EL POSITIVO: dos normas, una ajena y otra nuestra, cada una con sus
# articulos. Sin la abreviatura en el patron no se parte, y se pierde entera la
# parte que SI tenemos.
campo = "TRLRHL RD Leg. 2/2004 Artículo 63. Ley 58/2003 Artículo 35."
got = [(p.numero, p.cuerpo or p.estado)
       for p in D.pares_de_normativa(campo, N)]
print(f"    {got}")
comprobar("la parte de la LGT se recupera aunque la otra norma no la tengamos",
          ("35", "BOE-A-2003-23186#0") in got, got)
comprobar("  y el articulo de la norma ajena se queda en «externa», no se "
          "cuelga de la nuestra",
          ("63", "externa") in got, got)

for grafia in ("RD Leg. 2/2004", "RDLeg 2/2004", "RD-Leg 2/2004"):
    comprobar(f"«{grafia}» se reconoce como designacion de norma",
              D._RE_NORMA_EXPLICITA.findall(grafia) == [grafia], grafia)

# EL ADVERSARIO: se parece y es OTRA norma. «RDL» es el Real Decreto-ley.
# Reconocerlo como designacion esta bien -ahi SE NOMBRA una norma- pero no
# puede acabar resolviendo al Real Decreto Legislativo.
comprobar("«RDL 8/2020» se reconoce como norma nombrada",
          D._RE_NORMA_EXPLICITA.findall("RDL 8/2020") == ["RDL 8/2020"])
comprobar("  pero NO se expande: sigue sin resolver",
          D._expandir_abreviatura("RDL 8/2020") == "RDL 8/2020")
comprobar("  y «RDLeg 8/2020» SI se expande, que es la diferencia",
          D._expandir_abreviatura("RDLeg 8/2020")
          == "Real Decreto Legislativo 8/2020")
comprobar("  el `RDL` no se come el `RDLeg`",
          D._RE_NORMA_EXPLICITA.findall("RDLeg 1/1993") == ["RDLeg 1/1993"])

# Y QUE NO SE HA ROTO EL REDACTOR, que es el tercer modulo que usa el patron.
from agente_fiscal import redactor as _R          # noqa: E402
comprobar("el redactor sigue usando el MISMO patron, no una copia",
          "_D._RE_NORMA_EXPLICITA" in
          (RAIZ / "agente_fiscal" / "redactor.py").read_text("utf-8"))

# ==================================== 2. EL ADVERSARIO: ES UN APARTADO
print("\n=== 2. LO QUE PARECE DOBLADO Y ES UN APARTADO ===")
print("  «art. 70-2» es el 70 apartado 2. Partirlo inventa un articulo 2.\n")

INTACTOS = [
    ("Real Decreto 828/1995 art. 70-2", ["70"]),
    ("TRLITPAJD RDLeg 1/1993 art. 7-1-A)", ["7"]),
    ("Real Decreto 1624/1992 art. 62-6", ["62"]),
    ("Ley 37/1992 arts. 80-cuatro", ["80"]),
]
for campo, esperado in INTACTOS:
    got = arts(campo)
    comprobar(f"«{campo[:40]}» sigue dando {esperado}", got == esperado, got)
    comprobar("  y NO aparece el apartado como articulo suelto",
              "2" not in got or esperado == ["2"], got)

comprobar("el desdoblado deja intacto «art. 70-2»",
          D._desdoblar_marca("art. 70-2") == "art. 70-2")
comprobar("  y «art. 45.I.B)-9» tambien",
          D._desdoblar_marca("art. 45.I.B)-9") == "art. 45.I.B)-9")

# ==================================== 3. LA CAUSA SE COMPRUEBA
print("\n=== 3. UNA CAUSA QUE NO SE PUEDE DESMENTIR NO CLASIFICA ===")

nums = CAU.numeros_de(N)

# EL CASO EXACTO QUE LO DESTAPO: lleva «RDLeg» en el texto, y la abreviatura ya
# se lee. La causa NO puede ser la abreviatura.
campo_ok = "TRLITPAJD RDLeg 1/1993 arts. 6, 7 y 8"
comprobar("un campo que RESUELVE no tiene ninguna causa de fallo",
          CAU.causa(campo_ok, nums, N) == "", CAU.causa(campo_ok, nums, N))
comprobar("  (y el viejo lo llamaba «abreviatura», que es lo que se corrige)",
          CAU._RE_ABREV.search(campo_ok) is not None)

# Uno que lleva la abreviatura Y de verdad no resuelve: ahi si es su causa.
campo_mal = "RDLeg 9/9999 art. 1"
comprobar("si lleva la abreviatura y AUN ASI no resuelve, la causa es suya",
          CAU.causa(campo_mal, nums, N) in
          (CAU.ABREVIATURA, CAU.AJENA), CAU.causa(campo_mal, nums, N))

# SIN PODER COMPROBAR NO SE ETIQUETA: es la respuesta honesta, y ademas es la
# que para la puerta.
comprobar("sin `normas` no se clasifica nada: se devuelve vacio",
          CAU.causa(campo_ok, nums, None) == "",
          CAU.causa(campo_ok, nums, None))

# ==================================== 4. CONTROL NEGATIVO
print("\n=== 4. LA PRUEBA SABE PONERSE ROJA ===")

import types                                     # noqa: E402

FUENTE = (RAIZ / "agente_fiscal" / "dgt.py").read_text("utf-8")


def roto(viejo, nuevo):
    if viejo not in FUENTE:
        raise AssertionError(f"la mutacion ya no encaja: {viejo[:60]}")
    mod = types.ModuleType("dgt_roto")
    mod.__package__ = "agente_fiscal"
    mod.__file__ = str(RAIZ / "agente_fiscal" / "dgt.py")
    sys.modules[mod.__name__] = mod
    try:
        exec(compile(FUENTE.replace(viejo, nuevo, 1), mod.__file__, "exec"),
             mod.__dict__)
    finally:
        del sys.modules[mod.__name__]
    return mod


# (a) EL ARREGLO INGENUO, que es el que habria escrito cualquiera con prisa:
#     «arts- 7» lleva guion, luego parto por los guiones. Se demuestra que
#     rompe el apartado, que es por lo que NO se hizo asi. El desdoblado de
#     verdad solo toca lo que hay ENTRE la marca y el primer digito, y por eso
#     no puede llegar al «70-2»: el guion va detras del numero.
import re as _re                                 # noqa: E402


def _ingenuo(t):
    return _re.sub(r"(\d)\s*-\s*(\d)", r"\1, \2", t)


comprobar("(a) el arreglo ingenuo -partir por guiones- convierte «art. 70-2» "
          "en dos articulos", _ingenuo("art. 70-2") != "art. 70-2",
          _ingenuo("art. 70-2"))
comprobar("  y el desdoblado de verdad NO lo toca, que es la diferencia",
          D._desdoblar_marca("art. 70-2") == "art. 70-2")

# (b) se quita el «Legislativo» del patron
# La mutacion apunta a la linea TAL COMO ESTA hoy. Se actualizo el 17/08 al
# ampliar el patron con la abreviatura: una mutacion que ya no encaja no es un
# control, es una excepcion al arrancar la suite.
m2 = roto(r'r"\b(?:Ley\s+Org[aá]nica|Ley|Real\s+Decreto(?:\s+Legislativo|-ley)?|"',
          r'r"\b(?:Ley\s+Org[aá]nica|Ley|Real\s+Decreto(?:-ley)?|"')
# LA MUTACION SE MIDE CON UN CAMPO SIN SIGLA DE NORMA, y ese cambio es del
# 25/08/2026. Antes se medía con `campo_ok` -«TRLITPAJD RDLeg 1/1993»- y
# valia: ninguna de sus designaciones resolvia sola, asi que todo dependia de
# que el patron supiera leer «RDLeg». Desde que los nombres cortos se derivan
# del titulo oficial, «TRLITPAJD» ES un alias del texto refundido y resuelve
# por su cuenta: el campo sigue resolviendo aunque se rompa el patron, y la
# mutacion dejo de demostrar nada.
#
# NO SE HA PERDIDO LA GUARDA: se mide donde sigue siendo la unica via. Un
# campo que solo lleva la sigla del IMPUESTO -«ITPAJD», que no nombra ninguna
# norma- depende entero del patron, y ahi la mutacion tumba la resolucion
# igual que el primer dia.
campo_sin_sigla_de_norma = "ITPAJD RDLeg 1/1993 art. 7"
comprobar("(b) sin «Legislativo», el RDLeg sin sigla de norma deja de resolver "
          "y el bloque 1 lo caza",
          not [p for p in m2.pares_de_normativa(campo_sin_sigla_de_norma, N)
               if p.comparable])
comprobar("  (control) con el patron intacto SI resuelve",
          [p.cuerpo for p in D.pares_de_normativa(campo_sin_sigla_de_norma, N)
           if p.comparable] == [next(c for c in N.cuerpos
                                     if c.endswith("25359#1"))])

# (c) la causa vuelve a etiquetar por parecido
FC = (RAIZ / "agente_fiscal" / "causas.py").read_text("utf-8")
mc = types.ModuleType("causas_roto"); mc.__package__ = "agente_fiscal"
mc.__file__ = str(RAIZ / "agente_fiscal" / "causas.py")
sys.modules[mc.__name__] = mc
try:
    # SE ROMPEN LAS DOS GUARDAS, porque son dos y son independientes: la
    # general -«si resuelve, no hay causa»- y la propia de la abreviatura
    # -«abrela y comprueba que sigue sin resolver»-. Rompiendo solo una, la
    # otra sigue tapando el defecto, que es justo lo que se queria.
    roto_fc = FC.replace(
        "    if normas is not None and _resuelve(t, normas):\n        return \"\"",
        "    if False:\n        return \"\"", 1).replace(
        "        if not _resuelve(_D._expandir_abreviatura(t), normas):\n"
        "            return ABREVIATURA",
        "        return ABREVIATURA", 1)
    exec(compile(roto_fc, mc.__file__, "exec"), mc.__dict__)
finally:
    del sys.modules[mc.__name__]
comprobar("(c) sin la comprobacion, vuelve a llamar «abreviatura» a algo que "
          "resuelve", mc.causa(campo_ok, nums, N) == CAU.ABREVIATURA,
          mc.causa(campo_ok, nums, N))

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
