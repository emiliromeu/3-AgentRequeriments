#!/usr/bin/env python3
"""LA IDENTIDAD DE UN PRECEPTO ES (NORMA, CUERPO, ARTICULO). Cero red, cero API.

Nunca un numero suelto. Es la leccion de la fase 6 y la que mas caro sale: una
consulta de la DGT que cita «RIRPF, RD 439/2007, art. 22» comparada con nuestro
articulo 22 de la Ley del IVA inventa una señal de discusion que no existe, y
un profesional lee «criterio discutido» donde no hay discusion ninguna.

Perder una señal es barato. Inventarsela, no.

    python pruebas/prueba_normativa.py
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4
from agente_fiscal import configuracion as C
from agente_fiscal import dgt as D
from agente_fiscal import teac as T

fallos = []

# LOS NUMEROS DE CONSULTA DE ESTA SUITE SON INVENTADOS, Y VAN EN LA SERIE 9xxx.
# Es la marca que impide que un dato de prueba se confunda con criterio real si
# alguien lo ve fuera de contexto -en una traza, en un pantallazo, en un
# informe-. Ver la regla de arriba del LEEME. Antes iban en el rango normal
# (V0001-23, V0100-24...) y no habia forma de saber a simple vista que no
# existian.


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:110]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix, g = fase4.cargar_corpus()
N = ix.normas
LIVA = next(c for c in N.cuerpos if "28740" in c)
# Las dos de Renta, desde que se ingirieron: la ley y su reglamento. Se buscan
# por identificador del BOE y no se escriben a mano, para que la suite siga
# valiendo si cambia el indice del cuerpo.
LIRPF = next(c for c in N.cuerpos if "20764" in c)
RIRPF = next(c for c in N.cuerpos if "6820" in c and c.endswith("#1"))
RIVA = next(c for c in N.cuerpos if c.endswith("28925#1"))
LGT = next(c for c in N.cuerpos if "23186" in c)


def consulta(numero, normativa, fecha="01/01/2023"):
    return D.Consulta(numero=numero, fecha=fecha, normativa=normativa,
                      contestacion="texto de prueba")


def clave(cuerpo, num):
    return f"{cuerpo}#articulo {num}"


# ================================================== 1. EL CASO DE ORIGEN
print("\n=== 1. EL CASO QUE COSTO CARO: MISMO NUMERO, OTRA NORMA ===")
print("  Una consulta sobre el articulo 22 del REGLAMENTO DEL IRPF, contra una")
print("  respuesta que se apoya en el articulo 22 de la Ley del IVA.\n")
otra = consulta("V0047-24", "RIRPF, RD 439/2007, art. 22")
lec = D.leer_criterio([otra], [clave(LIVA, 22)], N)
print(f"    señales: {lec.senales}")
print(f"    cobertura: {lec.cobertura}")
comprobar("NO dispara ninguna señal de desacuerdo", not lec.hay_discusion,
          str(lec.senales))
# LA PREMISA DE ESTE BLOQUE CAMBIO AL INGERIR RENTA, Y PARA BIEN.
#
# Cuando se escribio, el Reglamento del IRPF NO estaba en el corpus: el
# articulo 22 del RIRPF era una norma «externa» y lo que se comprobaba era que
# no se confundiera con el 22 de la Ley del IVA por no poder leerlo.
#
# Ahora el RIRPF esta dentro, asi que ese precepto se lee, es «cargada» y es
# comparable. La leccion de la fase 6 no ha desaparecido: se ha vuelto MAS
# exigente. Antes bastaba con no resolver; ahora hay que resolver AL SITIO
# CORRECTO teniendo los dos articulos 22 delante.
preceptos = D.pares_de_normativa("RIRPF, RD 439/2007, art. 22", N)
comprobar("el articulo 22 del RIRPF ahora se lee: esta en el corpus",
          preceptos and preceptos[0].estado == "cargada",
          str([(p.numero, p.estado) for p in preceptos]))
comprobar("Y RESUELVE AL REGLAMENTO DEL IRPF, no a la Ley del IVA",
          preceptos[0].clave[0] == RIRPF, str(preceptos[0].clave))
comprobar("o sea: NO es el articulo 22 del IVA, que es el que costo la fase 6",
          preceptos[0].clave != (LIVA, "22"), str(preceptos[0].clave))
comprobar("la cobertura dice que va de otro precepto, sin llamarlo desacuerdo",
          all("22 de la Ley 37" not in c for c in lec.cobertura),
          str(lec.cobertura))

# ================================================== 2. LOS DOS ESPEJOS
print("\n=== 2. LOS DOS ESPEJOS: LA MISMA NORMA SI SE COMPARA ===")
nuestra_otro = consulta("V9140-24", "Ley 37/1992 art. 91")
lec2 = D.leer_criterio([nuestra_otro], [clave(LIVA, 22)], N)
print(f"    misma norma, otro articulo -> cobertura: {lec2.cobertura}")
comprobar("misma norma y OTRO articulo: SI se entera", bool(lec2.cobertura),
          str(lec2.cobertura))
comprobar("y lo dice como hueco, no como desacuerdo", not lec2.hay_discusion,
          str(lec2.senales))

# Misma norma y MISMO articulo: comparable, y sin señal de desalineacion.
nuestra_igual = consulta("V9150-24", "Ley 37/1992 art. 22")
lec3 = D.leer_criterio([nuestra_igual], [clave(LIVA, 22)], N)
comprobar("misma norma y MISMO articulo: no hay desalineacion",
          not lec3.cobertura and not lec3.senales,
          f"{lec3.senales} {lec3.cobertura}")
p22 = D.pares_de_normativa("Ley 37/1992 art. 22", N)[0]
comprobar("y ese si es comparable", p22.comparable)
comprobar("y su clave lleva la NORMA dentro, no solo el numero",
          p22.clave == (LIVA, "22"), str(p22.clave))

# Dos anos distintos sobre el MISMO precepto: eso si es desacuerdo.
lec4 = D.leer_criterio([consulta("V9160-13", "Ley 37/1992 art. 80", "01/01/2013"),
                        consulta("V9170-23", "Ley 37/1992 art. 80", "01/01/2023")],
                       [clave(LIVA, 80)], N)
comprobar("dos consultas de anos distintos sobre el mismo precepto: DESACUERDO",
          lec4.hay_discusion, str(lec4.senales))
comprobar("y la señal nombra la norma, no solo el articulo",
          any("Ley 37/1992" in s for s in lec4.senales), str(lec4.senales))

# ============================ 3. EL CAMPO «NORMATIVA» EN SUS FORMATOS REALES
print("\n=== 3. EL CAMPO «NORMATIVA», EN SUS FORMATOS REALES ===")
print("  Formas vistas en la copia local, incluidas las de 2026.\n")
CASOS = [
    ("Ley 37/1992 art. 95, 130", [(LIVA, "95"), (LIVA, "130")], "lista"),
    ("Ley 37/1992 arts. 75, 78, 80-cuatro",
     [(LIVA, "75"), (LIVA, "78"), (LIVA, "80")], "plural y apartado pegado"),
    # Antes daba [] porque la Ley del IRPF no estaba en el corpus. Ahora esta,
    # y el rango se resuelve a SUS articulos: es lo que tiene que pasar. Lo que
    # no puede pasar -y lo comprueba el bloque 1- es que un «articulo 33» acabe
    # en la ley que no toca.
    ("LIRPF, Ley 35/2006, Art. 33 a 36.",
     [(LIRPF, "33"), (LIRPF, "34"), (LIRPF, "35"), (LIRPF, "36")],
     "rango de otra norma, que ahora SI esta cargada"),
    ("Ley 38/1992;Ley 37/1992", [], "dos normas, sin articulos"),
    ("LIVA, Ley 37/1992, Art. 27.\n\n LIVA, Ley 37/1992, Art. 95.",
     [(LIVA, "27"), (LIVA, "95")], "SALTO DE LINEA (2026)"),
    ("Ley 37/1992 art. 10-3", [(LIVA, "10")], "apartado con guion y numero"),
    ("Ley 37/1992 art. 93.Cuatro", [(LIVA, "93")], "apartado con punto"),
    ("Ley 37/1992 art. 94.Uno.1º", [(LIVA, "94")], "apartado anidado y ordinal"),
    ("Ley 58/2003 art. 66", [(LGT, "66")], "otra norma NUESTRA"),
]
for texto, esperado, que in CASOS:
    pares = [p.clave for p in D.pares_de_normativa(texto, N) if p.comparable]
    comprobar(f"«{texto[:44]}» ({que})", pares == esperado,
              f"{pares} != {esperado}")

print("\n  Y lo que NO se sabe leer se DICE, no se pierde en silencio:")
a = D.analizar_normativa("Ley 37/1992 arts. 8-Bis, 8-Tres y 68-Uno", N)
print(f"    sin reconocer: {a.sin_reconocer}")
comprobar("una forma nueva deja aviso", a.hay_formas_nuevas, str(a.sin_reconocer))
comprobar("el aviso dice que se leyo y que quedo fuera",
          any("quedo sin leer" in s for s in a.sin_reconocer),
          str(a.sin_reconocer))

# ==================================== 4. ANTE LA DUDA, NADA
print("\n=== 4. SI LA NORMA NO RESUELVE, NO SE COMPARA CON NADA ===")
for texto, que in [
        ("Norma rarisima que no existe, art. 22", "norma inventada"),
        ("Ley 37/1992 Ley 58/2003 art. 22", "DOS normas nuestras en el trozo"),
        ("art. 22", "sin norma ninguna")]:
    pares = [p for p in D.pares_de_normativa(texto, N)]
    comparables = [p for p in pares if p.comparable]
    comprobar(f"«{texto[:40]}» ({que}): ninguno comparable",
              not comparables, str([(p.numero, p.estado) for p in comparables]))

cuerpo, estado = D._resolver_designacion("Ley 37/1992 Ley 58/2003", N)
comprobar("dos normas cargadas en el mismo trozo: no se elige ninguna",
          cuerpo == "" and estado == "sin_norma", f"{cuerpo} {estado}")
cuerpo, estado = D._resolver_designacion("LIVA Ley 37/1992", N)
comprobar("pero «LIVA Ley 37/1992» -alias + norma- SI resuelve, es la misma",
          cuerpo == LIVA, f"{cuerpo} {estado}")

# ==================================== 5. EL CODIGO DE DYCTEA
print("\n=== 5. EL MAPEO POR CODIGO DE DYCTEA ===")
print("  DYCTEA llama al Reglamento «RD 1624/1992 Reglamento Impuesto sobre el")
print("  Valor Añadido IVA»: ese nombre menciona DOS cuerpos nuestros y el")
print("  resolutor no puede decidir. Por eso se resuelve por CODIGO.\n")
for codigo, esperado, que in [
        ("02:07:01:00:00", LIVA, "Ley del IVA"),
        ("02:07:02:00:00", RIVA, "Reglamento del IVA"),
        ("01:02:01:00:00", LGT, "Ley General Tributaria")]:
    clave_, como = T.resolver_norma("cualquier nombre", N, codigo)
    comprobar(f"codigo {codigo} -> {que}", clave_ == esperado,
              f"{clave_} ({como})")
    comprobar(f"  y dice que fue POR CODIGO", "por codigo" in como, como)

# UN CODIGO NO MAPEADO YA NO SE DA POR PERDIDO: SE MIRA EL NOMBRE.
#
# Esta prueba exigia lo contrario -«NO se intenta adivinar por el nombre»- y
# era lo correcto mientras `MAPA_DYCTEA` cubriera el corpus. Con tres entradas
# y trece normas dejo de serlo: 118 criterios del TEAC se guardaron y NO HABIA
# FORMA DE ENCONTRARLOS, y 147 de sus referencias eran a la Ley 35/2006, al RD
# 439/2007 y a la Ley 19/1991, que estan cargadas.
#
# Esa es la evidencia independiente que cambia la expectativa. Lo que NO
# cambia, y por eso siguen las dos comprobaciones de abajo: el nombre se
# resuelve con el resolutor de siempre, que tiene su regla de oro y devuelve
# vacio si duda.
clave_, como = T.resolver_norma("Impuesto sobre Sucesiones", N, "09:99:99:00:00")
print(f"    codigo no mapeado, nombre que no tenemos -> {clave_!r} · {como}")
comprobar("un codigo no mapeado con nombre que NO tenemos sigue sin resolver",
          clave_ == "", clave_)

clave_, como = T.resolver_norma(
    "Ley 35/2006 Impuesto sobre la Renta de las Personas Físicas", N,
    "09:99:99:00:00")
print(f"    codigo no mapeado, nombre que SI tenemos -> {clave_!r} · {como}")
comprobar("pero si el nombre es una norma nuestra, AHORA si se encuentra",
          clave_ == "BOE-A-2006-20764#0", f"{clave_} ({como})")
comprobar("  y dice que fue por nombre, no por codigo", "nombre" in como, como)

# SE CAMBIO LA NORMA DEL CASO, NO LA EXPECTATIVA. Aqui ponia la Ley 29/1987,
# que se ingirio el 12/08/2026: en cuanto entro en el corpus, este caso dejo de
# probar lo que se escribio para probar -una norma que NO tenemos-. Se
# sustituye por los Impuestos Especiales, que sigue fuera. Lo que se comprueba
# es identico.
clave_, como = T.resolver_norma("Ley 38/1992 Impuestos Especiales",
                                N, "09:99:99:00:00")
comprobar("y la MISMA forma con una norma que no tenemos NO se resuelve: "
          "que mande el numero no es que encaje con lo que sea",
          clave_ == "", f"{clave_} ({como})")

# =================================== 6. CONTROL NEGATIVO
print("\n=== 6. LA PRUEBA SABE PONERSE ROJA ===")
print("  Se compara a mano por NUMERO SUELTO -el fallo de la fase 6- y se")
print("  comprueba que da el falso positivo que esta suite existe para cazar.\n")
otra = consulta("V0047-24", "RIRPF, RD 439/2007, art. 22")
numeros_sueltos = {p.numero for p in otra.preceptos(N)}
comprobar("por numero suelto, el 22 del IRPF «coincide» con el 22 del IVA",
          "22" in numeros_sueltos, str(numeros_sueltos))
comprobar("pero por (norma, articulo) NO coincide",
          (LIVA, "22") not in {p.clave for p in otra.preceptos(N)},
          str({p.clave for p in otra.preceptos(N)}))
print("    (si el codigo comparase por numero, el bloque 1 saldria en rojo)")

print("\n" + "=" * 62)
print(f"FALLOS: {len(fallos)}")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
