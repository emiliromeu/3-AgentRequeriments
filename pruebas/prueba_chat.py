#!/usr/bin/env python3
"""UNA CONSULTA ES UNA CONVERSACION, Y CADA VUELTA SIGUE SIENDO SUYA.

    python pruebas/prueba_chat.py

Cero red, cero API. Trabaja sobre una lista de filas escrita a mano: esta pieza
no toca el disco, solo agrupa lo que el indice ya leyo.

LO QUE PROTEGE, Y POR QUE:

  · UN CHAT ES UNA CADENA DE EXPEDIENTES, no una conversacion guardada. Si
    algun dia se guardara como una cosa sola, se perderia que cada respuesta se
    verifico contra un material concreto en un momento concreto — que es lo
    unico que la hace auditable dentro de seis meses.
  · EL AÑO Y LA COMUNIDAD DEL CHAT SON LOS DE LA ULTIMA VUELTA. Es lo contrario
    de lo que suena «heredar», y es deliberado: si en la vuelta 3 se corrigio el
    año, la cabecera tiene que decir con que se esta contestando AHORA.
  · Y LO QUE UN CHAT NORMAL NO TIENE: que se vea cuando una vuelta ha quedado
    atras. En una conversacion corriente el ultimo mensaje manda y ya; aqui hay
    texto verificado contra materiales distintos conviviendo en la pantalla, y
    quien copie la vuelta 1 despues de que la 3 la corrigiera se lleva la
    respuesta equivocada a un correo.

EL CASO QUE MANDA ES EL DEL AÑO. Hoy no puede ocurrir -al seguir un hilo el año
no se puede cambiar, 0 de 327 vueltas medidas- y por eso se escribe ahora: en
cuanto la cabecera del chat sea editable, sera el fallo silencioso del año
dentro de una conversacion.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from agente_fiscal import chat as CH  # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:104]}" if not ok else ""))
    if not ok:
        fallos.append(que)


def motivo_de(d, sello):
    """El motivo de un desfase, o «(no hay)». NUNCA lanza.

    UN BANCO QUE SE MUERE A MITAD NO SIRVE PARA DIAGNOSTICAR, y esta suite se
    moria: las comprobaciones leian `d[sello][1]` directamente, asi que en
    cuanto la primera fallaba -porque el desfase no estaba- el `KeyError`
    tumbaba el guion entero y las demas no llegaban a ejecutarse.

    Se vio rompiendo el codigo a proposito: quitando la comparacion del año
    salia UN fallo y una traza, cuando lo correcto son TRES fallos y el resto
    de la suite corriendo. Un banco que solo cuenta el primer problema obliga a
    arreglar de uno en uno y esconde si hay mas.
    """
    par = d.get(sello)
    return par[1] if par else "(no hay desfase para ese sello)"


def clase_de(d, sello):
    par = d.get(sello)
    return par[0] if par else "(no hay desfase para ese sello)"


def fila(sello, pregunta="una duda", viene_de="", ejercicio="2024",
         comunidad="Cataluña", preceptos=None, estado="CRITERIO CLARO"):
    return {"sello": sello, "pregunta": pregunta, "viene_de": viene_de,
            "ejercicio": ejercicio, "comunidad": comunidad,
            "estado": estado, "con_criterio": False,
            "preceptos": preceptos if preceptos is not None else ["Articulo 95"]}


# ==================================================== 1. LA FORMA
print("\n=== 1. UN CHAT ES UNA CADENA DE EXPEDIENTES ===")
UNA = fila("20260830T100000", "deduccion del IVA de un turismo")
DOS = fila("20260830T101500", "y si esta a nombre de la sociedad",
           viene_de="20260830T100000")
TRES = fila("20260830T103000", "y si lo usa un comercial",
            viene_de="20260830T101500")
SUELTA = fila("20260829T090000", "exencion del articulo 20")

chats = CH.de_expedientes([UNA, DOS, TRES, SUELTA])
comprobar("tres vueltas encadenadas son UN chat, no tres",
          len(chats) == 2, len(chats))
largo = [c for c in chats if len(c["vueltas"]) == 3][0]
comprobar("  con sus vueltas en orden, de la primera a la ultima",
          [v["sello"] for v in largo["vueltas"]]
          == [UNA["sello"], DOS["sello"], TRES["sello"]],
          [v["sello"] for v in largo["vueltas"]])
comprobar("la identidad del chat es la PRIMERA vuelta: no cambia al añadir",
          largo["sello"] == UNA["sello"], largo["sello"])
comprobar("  y el titulo es la primera pregunta, no la ultima",
          "turismo" in largo["titulo"], largo["titulo"])
comprobar("el estado que se enseña es el de la ULTIMA vuelta",
          largo["estado"] == TRES["estado"])
comprobar("los chats salen del mas nuevo al mas viejo",
          [c["sello"] for c in chats] == sorted(
              [c["sello"] for c in chats], reverse=True),
          [c["sello"] for c in chats])

# EL TITULO NO SE INVENTA NI SE PIDE AL MODELO: se recorta.
largo_de_verdad = fila("20260830T110000", "a" * 200)
uno = CH.de_expedientes([largo_de_verdad])[0]
comprobar("un titulo largo se recorta, y se ve que esta recortado",
          len(uno["titulo"]) <= CH.LARGO_TITULO + 2 and uno["titulo"].endswith("…"),
          uno["titulo"])
vacio = CH.de_expedientes([fila("20260830T120000", "")])[0]
comprobar("  y sin pregunta NO se inventa un nombre",
          vacio["titulo"] == "(sin pregunta)", vacio["titulo"])

# ==================================================== 2. LA CABECERA
print("\n=== 2. EL AÑO DEL CHAT ES EL DE LA ULTIMA VUELTA ===")
print("  Suena al reves de «heredar», y es deliberado: si en la vuelta 3 se")
print("  corrigio el año, la cabecera tiene que decir con que se contesta HOY.\n")
A = fila("20260830T200000", "una duda", ejercicio="2026")
B = fila("20260830T201000", "es de 2023", viene_de="20260830T200000",
         ejercicio="2023")
c = CH.de_expedientes([A, B])[0]
comprobar("el chat dice el año de la ultima vuelta",
          c["ejercicio"] == "2023", c["ejercicio"])
comprobar("  y no el de la primera", c["ejercicio"] != "2026")
comprobar("cada vuelta conserva el SUYO: no se pierde lo que paso antes",
          [v["ejercicio"] for v in c["vueltas"]] == ["2026", "2023"],
          [v["ejercicio"] for v in c["vueltas"]])

# ==================================================== 3. LO QUE QUEDA ATRAS
print("\n=== 3. QUE VUELTAS HAN QUEDADO ATRAS, Y POR QUE ===")

# (a) MISMO MATERIAL: la vuelta nueva precisa. No se avisa de nada.
P = fila("20260831T100000", "una duda", preceptos=["Articulo 95"])
Q = fila("20260831T101000", "y si...", viene_de="20260831T100000",
         preceptos=["Articulo 95"])
d = CH.desfases([P, Q])
comprobar("MISMO MATERIAL: no se avisa de nada",
          d == {}, d)

# (b) MATERIAL DISTINTO: contestada sobre otra base, sin tacharla.
R = fila("20260831T110000", "una duda", preceptos=["Articulo 95"])
S = fila("20260831T111000", "y si...", viene_de="20260831T110000",
         preceptos=["Articulo 95", "Articulo 97"])
d = CH.desfases([R, S])
comprobar("MATERIAL DISTINTO: se marca la anterior",
          R["sello"] in d, d)
comprobar("  y se dice que SIGUE VALIENDO para lo que preguntaba",
          "sigue valiendo" in motivo_de(d, R["sello"]), motivo_de(d, R["sello"]))
comprobar("  sin llamarla error ni equivocada",
          not any(x in motivo_de(d, R["sello"]).lower()
                  for x in ("error", "mal", "incorrect")),
          motivo_de(d, R["sello"]))
comprobar("la ULTIMA nunca queda atras: no hay nada despues",
          S["sello"] not in d, d)

# (c) OTRO AÑO: esto SI es quedar superada. Es el caso que manda.
T = fila("20260831T120000", "una duda", ejercicio="2026")
U = fila("20260831T121000", "es de 2023", viene_de="20260831T120000",
         ejercicio="2023")
d = CH.desfases([T, U])
comprobar("OTRO AÑO: la anterior queda superada", T["sello"] in d, d)
comprobar("  y se dice que es de OTRA REDACCION de la norma",
          "otra redacción" in motivo_de(d, T["sello"]), motivo_de(d, T["sello"]))
comprobar("  con los dos años, para poder mirarlo",
          "2026" in motivo_de(d, T["sello"]) and "2023" in motivo_de(d, T["sello"]),
          motivo_de(d, T["sello"]))
comprobar("  y se distingue del caso del material",
          clase_de(d, T["sello"]) == "otra ley", clase_de(d, T["sello"]))

# La comunidad, igual que el año.
V = fila("20260831T130000", "una duda", comunidad="Cataluña")
W = fila("20260831T131000", "vive en Madrid", viene_de="20260831T130000",
         comunidad="Madrid")
d = CH.desfases([V, W])
comprobar("OTRA COMUNIDAD: tambien supera", V["sello"] in d, d)
comprobar("  y dice de cual a cual",
          "Cataluña" in motivo_de(d, V["sello"]) and "Madrid" in motivo_de(d, V["sello"]),
          motivo_de(d, V["sello"]))

# EL AÑO MANDA SOBRE EL MATERIAL: si cambian los dos, se dice el que importa.
X = fila("20260831T140000", "una duda", ejercicio="2026",
         preceptos=["Articulo 95"])
Y = fila("20260831T141000", "es de 2023", viene_de="20260831T140000",
         ejercicio="2023", preceptos=["Articulo 20"])
d = CH.desfases([X, Y])
comprobar("si cambian AÑO y material, manda el año: es lo grave",
          clase_de(d, X["sello"]) == "otra ley", d.get(X["sello"]))

# SOLO HACIA DELANTE. Una vuelta la supera una posterior, nunca una anterior.
comprobar("el tiempo va en un solo sentido: la primera no supera a la ultima",
          Y["sello"] not in d, d)

# UNA CONVERSACION LARGA NO SE MARCA ENTERA POR ACUMULACION.
L1 = fila("20260831T150000", "a", preceptos=["Articulo 95"])
L2 = fila("20260831T150100", "b", viene_de="20260831T150000",
          preceptos=["Articulo 95"])
L3 = fila("20260831T150200", "c", viene_de="20260831T150100",
          preceptos=["Articulo 97"])
d = CH.desfases([L1, L2, L3])
comprobar("se compara con la SIGUIENTE, no con la ultima",
          L1["sello"] not in d and L2["sello"] in d, d)

# ==================================================== 4. AGRUPAR POR DIA
print("\n=== 4. LA LISTA SE AGRUPA POR DIA ===")
print("  Es como se busca una consulta: «la del martes».\n")
hoy1 = fila("20260831T090000", "de hoy")
hoy2 = fila("20260831T080000", "tambien de hoy")
ayer = fila("20260830T090000", "de ayer")
dias = CH.por_dia(CH.de_expedientes([hoy1, hoy2, ayer]))
comprobar("los de un mismo dia van juntos",
          [d_[0] for d_ in dias] == ["31/08/2026", "30/08/2026"],
          [d_[0] for d_ in dias])
comprobar("  y no se repite el dia dos veces",
          len(dias) == 2 and len(dias[0][1]) == 2, [(a, len(b)) for a, b in dias])

# ==================================================== 5. CONTROL NEGATIVO
print("\n=== 5. CONTROL NEGATIVO: ¿CAZA LO QUE DICE CAZAR? ===")
print("  Se rompe la comparacion a proposito y se mira que las de arriba")
print("  se pondrian rojas.\n")

# (a) si `desfases` no mirara nunca el año, el caso grave pasaria callando.
bueno = CH.desfases
CH.desfases = lambda vueltas: {}
d = CH.desfases([T, U])
comprobar("con la comparacion rota, el cambio de año NO se avisa",
          T["sello"] not in d, d)
CH.desfases = bueno
comprobar("  y con la buena vuelve a cazarse", T["sello"] in CH.desfases([T, U]))

# (b) si el chat cogiera el año de la PRIMERA vuelta -el error facil- la
#     cabecera diria 2026 sobre una conversacion que ya va por 2023.
c = CH.de_expedientes([A, B])[0]
comprobar("coger el año de la primera vuelta se cazaria",
          c["ejercicio"] != c["vueltas"][0]["ejercicio"],
          f"{c['ejercicio']} vs {c['vueltas'][0]['ejercicio']}")

# (c) y si el titulo saliera de la ultima pregunta, el chat cambiaria de nombre
#     al seguir hablando.
comprobar("sacar el titulo de la ultima vuelta se cazaria",
          "turismo" in largo["titulo"]
          and "comercial" not in largo["titulo"], largo["titulo"])

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
