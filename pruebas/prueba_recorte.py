#!/usr/bin/env python3
"""EL RECORTE DEL CRITERIO: QUE LO QUE SE MANDA SIGA SIENDO LITERAL.

Cero red, cero API.

LA COMPROBACION QUE NO PUEDE FALLAR es la primera: si un fragmento recortado no
esta letra por letra en el documento cacheado, el verificador tumbara respuestas
CORRECTAS y no habra manera de saber por que. El sintoma seria «una cita buena
rechazada», que es de los peores: parece un fallo del modelo y es del recorte.

    python pruebas/prueba_recorte.py
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4
from agente_fiscal import citas as C
from agente_fiscal import configuracion as CONF
from agente_fiscal import dgt as D
from agente_fiscal import redactor as RED

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


ix, grafo = fase4.cargar_corpus()
N = ix.normas
LIVA = next(c for c in N.cuerpos if "28740" in c)


def registro(numero):
    for d in ix.docs:
        r = d.registro
        if (r.get("cuerpo_clave") == LIVA
                and r["referencia"].lower() == f"articulo {numero}"):
            return r
    raise SystemExit(f"no encuentro el articulo {numero}")


REG80 = [registro(80)]


def consulta(texto, numero="V9999-99"):
    return D.Consulta(numero=numero, fecha="01/01/2023",
                      normativa="Ley 37/1992 art. 80", contestacion=texto,
                      url="http://x")


# ================================================ 1. LA LITERALIDAD
print("\n=== 1. LO QUE SE MANDA SIGUE SIENDO LITERAL ===")
print("  Cada fragmento, buscado letra por letra en el documento entero, con")
print("  la MISMA normalizacion que usa el verificador. Tildes incluidas.\n")
cache = D.CacheDGT()
todas = cache.todas()
print(f"  consultas reales en la copia local: {len(todas)}")

revisados = con_fragmentos = con_tildes = 0
malos = []
for c in todas:
    frags, _t, _e = RED.fragmentos_pertinentes(c.contestacion, REG80, N)
    if not frags:
        continue
    con_fragmentos += 1
    cuerpo = C.normalizar_literal(c.contestacion)
    crudo = c.contestacion
    for f in frags:
        revisados += 1
        if C.normalizar_literal(f) not in cuerpo:
            malos.append((c.numero, C.normalizar_literal(f)[:60]))
        # Y sin normalizar tampoco puede haberse alterado nada: cada parrafo
        # del fragmento tiene que estar TAL CUAL en el original.
        for parrafo in f.split("\n\n"):
            if parrafo.strip() and parrafo not in crudo:
                malos.append((c.numero, "parrafo alterado: " + parrafo[:50]))
            if any(x in parrafo for x in "áéíóúñÁÉÍÓÚÑ«»"):
                con_tildes += 1

print(f"  consultas con fragmentos: {con_fragmentos} · fragmentos: {revisados}")
comprobar("TODOS los fragmentos son literales en su documento", not malos,
          str(malos[:2]))
comprobar("y la prueba ha mirado algo de verdad", revisados > 20, str(revisados))
comprobar("incluidos parrafos con tildes y comillas latinas", con_tildes > 5,
          str(con_tildes))

# ================================== 2. NUNCA SE CITA DE UN FRAGMENTO A OTRO
print("\n=== 2. LOS HUECOS SE MARCAN Y NO SE COSEN ===")
largo = consulta("\n".join([
    "P0 relleno.", "P1 relleno.",
    "P2 habla del articulo 80 de la Ley 37/1992.",
    "P3 dice que dicho precepto se aplica asi.",
    "P4 relleno.", "P5 relleno.", "P6 relleno.",
    "P7 vuelve al articulo 80 de la Ley 37/1992.",
    "P8 relleno."]))
frags, total, enviados = RED.fragmentos_pertinentes(largo.contestacion, REG80, N)
comprobar("dos zonas separadas -> dos fragmentos", len(frags) == 2, str(frags))
comprobar("el hueco NO se cose: P5 no viaja pegado a P3",
          "P5 relleno." not in frags[0], str(frags[0]))
comprobar("arrastra el entorno inmediato (P1 y P3)",
          "P1 relleno." in frags[0] and "P3 dice" in frags[0], str(frags[0]))
comprobar("y no mas: P4 no entra", "P4 relleno." not in frags[0])

bloque = RED.bloque_consulta_dgt(largo, frags, total - enviados)
comprobar("el material avisa de que la contestacion NO va entera",
          "no esta entera" in bloque, bloque[:90])
comprobar("y PROHIBE citar de un fragmento a otro",
          "de un fragmento a otro" in bloque)
comprobar("cada fragmento va delimitado, para que se vea donde acaba",
          bloque.count("[FRAGMENTO") == len(frags))
comprobar("y dice cuantos parrafos se han omitido",
          "omitido" in bloque, bloque[:200])

# ================== 3. UNA CONSULTA TODA PERTINENTE NO SE CAE ENTERA
print("\n=== 3. SI TODO ES PERTINENTE, NO SE CAE ENTERA ===")
print("  Una consulta en la que TODOS los parrafos hablan del articulo produce")
print("  un unico fragmento gigante. Con el tope aplicado al fragmento entero,")
print("  esa consulta -la mas pertinente que existe- se caia del todo.\n")
enorme = consulta("\n".join(
    [f"Parrafo {i} sobre el articulo 80 de la Ley 37/1992. " + "relleno " * 60
     for i in range(200)]), "V9102-23")
plan = RED.plan_de_criterio(REG80, 2023, grafo, [enorme], None, N)
r = plan.recortes[0]
print(f"    ley {plan.ley} · criterio {plan.criterio} ({plan.proporcion_ley:.0%} ley)")
print(f"    {r.fuente}: {r.enviado}/{r.completo} car. "
      f"({r.parrafos_enviados}/{r.parrafos} parrafos)")
comprobar("NO se cae entera: manda algo", r.enviado > 0, str(r.enviado))
# LO QUE SE COMPARA ES EL FRAGMENTO ENTRE SUS DELIMITADORES, no el bloque
# troceado a ojo: las marcas [FIN FRAGMENTO ...] van pegadas al ultimo parrafo
# y comparar eso da un falso rojo. Aqui se saca el fragmento exacto.
import re as _re
_RE_FRAG = _re.compile(r"\[FRAGMENTO \d+ DE [^\]]+\]\n(.*?)\n\[FIN FRAGMENTO",
                       _re.S)
mandados = [m.group(1) for b in plan.bloques_dgt for m in _RE_FRAG.finditer(b)]
comprobar("se han extraido fragmentos para comparar", bool(mandados),
          str(len(mandados)))
comprobar("y lo que manda sigue siendo literal, fragmento a fragmento",
          all(C.normalizar_literal(f) in C.normalizar_literal(enorme.contestacion)
              for f in mandados),
          str([f[:40] for f in mandados[:1]]))
comprobar("el criterio no pasa del bloque de ley", plan.criterio <= plan.ley,
          f"{plan.criterio} > {plan.ley}")
comprobar("la ley no baja de la mitad", plan.proporcion_ley >= 0.5,
          f"{plan.proporcion_ley:.0%}")

# ============ 4. UNA NORMA EXTERNA NOMBRADA NO DESCARTA EL PARRAFO ENTERO
print("\n=== 4. LA NORMA DE LA MENCION, NO LA DEL PARRAFO ===")
otra = consulta("Primer parrafo que no viene al caso.\n"
                "El articulo 80 de la Ley 35/2006, del IRPF, regula otra cosa.\n"
                "Tercer parrafo.")
frags, _t, _e = RED.fragmentos_pertinentes(otra.contestacion, REG80, N)
comprobar("un articulo 80 de OTRA ley no selecciona el parrafo", frags == [],
          str(frags))

# Pero que el parrafo NOMBRE una norma externa por otra cosa no lo descarta:
# lo que se mira es la norma de LA MENCION, no la que aparezca por ahi.
mixto = consulta("Relleno.\n"
                 "Segun el articulo 80 de la Ley 37/1992, y a los efectos del "
                 "Real Decreto 1619/2012, procede la modificacion.\n"
                 "Relleno final.")
frags, _t, _e = RED.fragmentos_pertinentes(mixto.contestacion, REG80, N)
comprobar("un parrafo que nombra una norma externa POR OTRA COSA si entra",
          len(frags) == 1, str(frags))
comprobar("y entra entero, sin recortar la mencion externa",
          "Real Decreto 1619/2012" in frags[0] if frags else False)

suelto = consulta("Relleno.\nComo establece el citado articulo 80, procede.\nFin.")
frags, _t, _e = RED.fragmentos_pertinentes(suelto.contestacion, REG80, N)
comprobar("«el citado articulo 80», sin norma al lado, tambien cuenta",
          len(frags) == 1, str(frags))

# ===================================== 5. LA CUOTA POR CONSULTA
print("\n=== 5. EL PRESUPUESTO NO SE LO COME EL PRIMERO ===")
print("  El valor de esta capa es ver que el criterio ha cambiado con los")
print("  anos, y para eso hacen falta las tres, no una larga.\n")


def gorda(n):
    return consulta("\n".join(
        [f"Parrafo {i} sobre el articulo 80 de la Ley 37/1992. " + "relleno " * 40
         for i in range(120)]), n)


tres = [gorda("V9110-21"), gorda("V9120-22"), gorda("V9130-23")]
plan = RED.plan_de_criterio(REG80, 2023, grafo, tres, None, N)
for r in plan.recortes:
    print(f"    {r.fuente}: {r.enviado:6d} car. ({r.parrafos_enviados} parrafos)")
enviados = [r.enviado for r in plan.recortes if r.enviado]
comprobar("las TRES llevan texto al material", len(plan.enviadas) == 3,
          str(plan.enviadas))
comprobar("NINGUNA nombrada se queda a cero", all(e > 0 for e in enviados),
          str(enviados))
comprobar("el reparto es parejo, no todo para la primera",
          max(enviados) <= 2 * min(enviados), str(enviados))
comprobar("y sigue sin pasarse del tope", plan.criterio <= plan.ley,
          f"{plan.criterio} > {plan.ley}")

# Y la otra mitad: la que no cabe ni con el minimo NO se nombra.
mini = [registro(89)]
plan2 = RED.plan_de_criterio(
    mini, 2023, grafo,
    [consulta("El articulo 89 de la Ley 37/1992 dice. " + "relleno " * 400,
              f"V00{i}0-2{i}") for i in range(1, 6)], None, N)
descartadas = [r for r in plan2.recortes if not r.enviado]
print(f"    con presupuesto de miseria: {len(plan2.enviadas)} enviadas, "
      f"{len(descartadas)} descartadas")
comprobar("la que no cabe ni con el minimo, NO se manda", bool(descartadas))
comprobar("y NO se nombra: `enviadas` solo lleva las que tienen texto",
          len(plan2.enviadas) == len(plan2.bloques_dgt),
          f"{len(plan2.enviadas)} vs {len(plan2.bloques_dgt)}")
comprobar("las descartadas dicen por que",
          all(r.motivo for r in descartadas),
          str([r.motivo[:30] for r in descartadas]))

# ===================================== 6. SIN NADA PERTINENTE, NO SE MANDA
print("\n=== 6. SIN NADA PERTINENTE, NO SE MANDA ===")
nada = consulta("Esto habla del articulo 148 y de nada mas.\nNi rastro.", "V9101-23")
plan3 = RED.plan_de_criterio(REG80, 2023, grafo, [nada], None, N)
comprobar("no genera bloque", plan3.bloques_dgt == [], str(plan3.bloques_dgt))
comprobar("pero queda anotada con su motivo",
          "ningun parrafo" in plan3.recortes[0].motivo, plan3.recortes[0].motivo)
comprobar("y el material no lleva la cabecera de la DGT para nada",
          RED.BLOQUE_DGT not in RED.construir_material(
              "x", 2023, REG80, grafo, consultas_dgt=[nada], normas=N, plan=plan3))

# ===================================== 7. CONTROL NEGATIVO
print("\n=== 7. LA PRUEBA SABE PONERSE ROJA ===")
print("  Se altera un fragmento a mano -como haria un recorte mal hecho- y se")
print("  comprueba que el bloque 1 lo detectaria.\n")
original = todas[0].contestacion if todas else "texto con tildes: modificación"
alterado = original.replace("ó", "o").replace("á", "a")[:200]
cuerpo = C.normalizar_literal(original)
comprobar("un fragmento con las tildes comidas NO pasa la comprobacion",
          alterado and C.normalizar_literal(alterado) not in cuerpo,
          alterado[:60])
recortado = original[:150] + original[200:350] if len(original) > 350 else "xx"
comprobar("y uno cosido de dos trozos, tampoco",
          C.normalizar_literal(recortado) not in cuerpo, recortado[:60])
print("    (las dos alteraciones se detectan: la comprobacion 1 mide de verdad)")

print("\n" + "=" * 62)
print(f"FALLOS: {len(fallos)}")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
