#!/usr/bin/env python3
"""LA DOCTRINA, FILTRADA POR MATERIA Y ASUNTO. Cero red, cero API.

EL CASO REAL. Sobre el articulo 80 -modificacion de base imponible por creditos
incobrables- se mandaban estos tres:

    00/01298/2004  IVA a la importacion. Despacho a libre practica
    00/03399/2023  Impuesto sobre la ELECTRICIDAD. Devolucion por impagados
    00/05524/2024  Impuesto sobre la ELECTRICIDAD. Devolucion por impagados

y se descartaban los CUATRO que iban justo de la pregunta. No fue mala suerte:
el orden por peso ponia delante el de unificacion y los mas recientes, y el tope
de 3 se comia a los buenos. Se elegian los tres peores.

Y EL FALLO ES SILENCIOSO: una respuesta con doctrina que no viene al caso no
parece rota. Parece una respuesta con doctrina.

LO QUE HAY QUE ENTENDER, y por eso esta suite empieza por ahi: los dos de
electricidad puntuan 1,00 de cobertura de terminos, porque sus conceptos son
literalmente «Base imponible: modificacion» y «Credito incobrable». POR TERMINOS
NO SE DISTINGUEN. Lo que los separa es el IMPUESTO, y eso lo dice la fuente.

    python pruebas/prueba_asunto.py
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4
from agente_fiscal import configuracion as CONF
from agente_fiscal import estado as EST
from agente_fiscal import teac as T

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:110]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix, g = fase4.cargar_corpus()
N = ix.normas

# LO QUE SE AFIRMA VA CONTRA EL FIXTURE, NO CONTRA LA DESPENSA.
#
# Esta suite leia `datos/teac`. Se escribio con NUEVE criterios guardados y una
# de sus comprobaciones era que para una consulta rara no se seleccionara
# ninguno. La siembra llevo la despensa a NOVECIENTOS NUEVE, entro una
# resolucion del TEAR de Valencia sobre el articulo 80, y la comprobacion se
# puso roja sin que nadie tocara el codigo.
#
# No fallaba el sistema: hacia lo correcto -sacarla diciendo «coincide el
# articulo, PERO no se ha comprobado que trate del mismo supuesto»-. Lo que se
# habia movido eran los datos debajo de la afirmacion.
#
# Los ocho del fixture estan COPIADOS de la cache real, con su numero y su
# texto autenticos. Ver `casos/teac_prueba/LEEME.txt`.
FIXTURE = RAIZ / "casos" / "teac_asunto"
cache = T.CacheTEAC(FIXTURE)
por_id = {c.resolucion: c for c in cache.todas()}

ART80 = "modificacion de la base imponible por creditos incobrables"
ELECTRICIDAD = ("00/03399/2023/00/00", "00/05524/2024/00/00")
IMPORTACION = "00/01298/2004/00/00"
DEL_ASUNTO = ("00/02189/2021/00/00", "00/03983/2023/00/00",
              "00/05698/2023/00/00", "00/06614/2024/00/00")

# ============================ 1. POR TERMINOS NO SE DISTINGUEN
print("\n=== 1. LA COBERTURA DE TERMINOS NO SIRVE PARA ESTO ===")
print("  Es la medida que uno probaria primero, y se midio antes de")
print("  descartarla. Los de electricidad puntuan 1,00.\n")
for r in ELECTRICIDAD:
    c = por_id[r]
    cob = T.cobertura_asunto(c, ART80, ix)
    print(f"    {r}  cobertura={cob:.2f}  «{c.asunto[:46]}»")
    comprobar(f"{r}: la cobertura de terminos NO lo distingue", cob >= 0.9,
              f"{cob:.2f}")
print("    (sus conceptos son «Base imponible: modificacion» y «Credito")
print("     incobrable»: tratan de eso, pero en OTRO impuesto)")

# ==================================== 2. EL FILTRO QUE TRABAJA: LA MATERIA
print("\n=== 2. EL FILTRO DE MATERIA, QUE ES EL QUE TRABAJA ===")
print("  `conceptos` es vocabulario controlado de la fuente, no prosa.\n")
for r in ELECTRICIDAD:
    c = por_id[r]
    print(f"    {r}  {[x for x in c.conceptos if 'mpuesto' in x]}")
    comprobar(f"{r}: se descarta por materia", T.materia_ajena(c))
for r in (IMPORTACION,) + DEL_ASUNTO:
    comprobar(f"{r}: es de IVA, NO se descarta por materia",
              not T.materia_ajena(por_id[r]))
# LA PREMISA DE ESTE BUCLE CADUCO AL SEMBRAR EL TEAC.
#
# Decia «todas las regionales de la copia son de IVA, ninguna se descarta», y
# era cierto cuando la copia tenia nueve resoluciones caidas probando. Al
# sembrar los articulos de PROCEDIMIENTO de la LGT entraron resoluciones de
# Sociedades y de IRPF -la LGT es de todos los impuestos- y el filtro empezo a
# descartarlas, que es su trabajo.
#
# Asi que ya no se comprueba contra una suposicion sobre la copia, sino contra
# LOS DATOS DE CADA CRITERIO: se descarta si -y solo si- sus `conceptos` no
# nombran ninguno de los impuestos que cubre el corpus. Eso sigue valiendo
# cuando la copia crezca otra vez.
regionales = [c for c in cache.todas() if not c.es_central]
print(f"    {len(regionales)} resoluciones regionales en la copia")
# LA REGLA ENTERA, que son dos mitades y la segunda se me olvido al primer
# intento: se descarta si nombra un impuesto Y ninguno es de los que cubrimos.
# Si NO nombra ninguno -«Prescripcion», «Procedimiento de inspeccion»- se deja
# pasar, porque no se infiere lo que la fuente no dice. Es lo que comprueba el
# bloque 3, y sin esa mitad esta comprobacion pedia lo contrario.
for c in regionales:
    bajos = [x.lower() for x in c.conceptos]
    nombra_impuesto = any("impuesto" in x or "iva" in x.split() for x in bajos)
    es_de_iva = any("valor añadido" in x or x.strip() == "iva" for x in bajos)
    esperado = nombra_impuesto and not es_de_iva
    comprobar(f"{c.resolucion} ({c.unidad}): el filtro coincide con sus conceptos",
              T.materia_ajena(c) == esperado,
              f"materia_ajena={T.materia_ajena(c)} esperado={esperado} "
              f"conceptos={c.conceptos[:3]}")
# ============================ 3. LO QUE LA FUENTE CALLA NO SE INFIERE
print("\n=== 3. SI NO NOMBRA IMPUESTO, SE LE DEJA PASAR ===")
print("  No se infiere lo que la fuente no dice. Es la regla de siempre.\n")


class SinImpuesto:
    conceptos = ["Plazos", "Prueba", "Acreditacion"]
    asunto = "Plazo para el ejercicio del derecho"


class SinConceptos:
    conceptos = []
    asunto = "algo"


comprobar("sin ningun impuesto nombrado, NO se descarta",
          not T.materia_ajena(SinImpuesto()))
comprobar("sin conceptos, tampoco", not T.materia_ajena(SinConceptos()))


class SoloOtro:
    conceptos = ["Impuesto sobre Sociedades", "Plazos"]
    asunto = "algo"


comprobar("pero si nombra impuestos y NINGUNO es del corpus, fuera",
          T.materia_ajena(SoloOtro()))


class UnoDeCada:
    conceptos = ["Impuesto sobre Sociedades",
                 "Impuesto sobre el Valor Añadido IVA"]
    asunto = "algo"


comprobar("y si nombra el nuestro entre varios, se queda",
          not T.materia_ajena(UnoDeCada()))

# ==================================== 4. EL FILTRO DE ASUNTO
print("\n=== 4. MISMO IMPUESTO, OTRO ASUNTO: LO COGE LA COBERTURA ===")
c = por_id[IMPORTACION]
cob = T.cobertura_asunto(c, ART80, ix)
print(f"    {IMPORTACION}  «{c.asunto[:52]}»  cobertura={cob:.2f}")
comprobar("«IVA a la importacion» no cubre nada de esta consulta", cob < 0.05,
          f"{cob:.2f}")
comprobar("y cae por debajo del umbral", cob < T.UMBRAL_ASUNTO,
          f"{cob:.2f} vs {T.UMBRAL_ASUNTO}")
for r in DEL_ASUNTO:
    cob = T.cobertura_asunto(por_id[r], ART80, ix)
    comprobar(f"{r}: el que SI va del asunto pasa ({cob:.2f})",
              cob >= T.UMBRAL_ASUNTO, f"{cob:.2f}")
comprobar("el umbral es un numero a la vista, no escondido en un if",
          0 < T.UMBRAL_ASUNTO < 1, str(T.UMBRAL_ASUNTO))

# ==================================== 5. EL CASO DE ORIGEN, CON DATOS REALES
print("\n=== 5. EL CASO DE ORIGEN: EL ARTICULO 80 ===")
res, _ = ix.buscar(ART80, tope=5)
sel = EST.seleccionar_material(ix, ART80, res, g)
pares = [(r.get("cuerpo_clave", ""),
          r["referencia"].replace("Articulo ", "").lower())
         for r in sel.elegidos]
antes, _ = cache.seleccionar(pares, N)                       # sin consulta
ahora, desc = cache.seleccionar(pares, N, consulta=ART80, indice=ix)
print(f"    antes (solo por articulo): {[c.resolucion for c in antes]}")
print(f"    ahora (materia + asunto) : {[c.resolucion for c in ahora]}")
comprobar("se siguen mandando 3: el tope no cambia", len(ahora) == 3,
          str(len(ahora)))
comprobar("NINGUNO de los dos de electricidad",
          not any(c.resolucion in ELECTRICIDAD for c in ahora),
          str([c.resolucion for c in ahora]))
comprobar("ni el de importacion",
          IMPORTACION not in [c.resolucion for c in ahora])
comprobar("los tres que se mandan son DEL ASUNTO",
          all(c.resolucion in DEL_ASUNTO for c in ahora),
          str([c.resolucion for c in ahora]))
comprobar("y todos hablan de base(s) imponible(s)",
          all("base" in c.asunto.lower() and "imponible" in c.asunto.lower()
              for c in ahora), str([c.asunto[:36] for c in ahora]))

motivos = {m for _c, m in desc}
print(f"    motivos de descarte: {sorted(motivos)}")
comprobar("los descartados dicen POR QUE", all(m for _c, m in desc))
comprobar("con motivos DISTINTOS, no uno para todo",
          {"va de otro impuesto", "coincide el articulo, no el asunto"} <= motivos,
          str(motivos))
for r in ELECTRICIDAD:
    comprobar(f"{r}: descartado por IMPUESTO",
              any(c.resolucion == r and m == "va de otro impuesto"
                  for c, m in desc), str(desc))
comprobar(f"{IMPORTACION}: descartado por ASUNTO",
          any(c.resolucion == IMPORTACION
              and m == "coincide el articulo, no el asunto" for c, m in desc))

# ============ 6. EL ORDEN NO SE COME A LOS PERTINENTES
print("\n=== 6. EL ORDEN POR PESO YA NO SE COME A LOS PERTINENTES ===")
print("  El tope de 3 sigue existiendo. Lo que cambia es QUE tres.\n")
pertinentes = [c for c in cache.todas()
               if not T.materia_ajena(c)
               and T.cobertura_asunto(c, ART80, ix) >= T.UMBRAL_ASUNTO
               and set(c.preceptos(N)) & {(a, b) for a, b in pares if b}]
print(f"    pertinentes en total: {len(pertinentes)} · se mandan {len(ahora)}")
comprobar("hay mas pertinentes que hueco: el tope sigue mordiendo",
          len(pertinentes) >= len(ahora), f"{len(pertinentes)} vs {len(ahora)}")
comprobar("pero los que se mandan salen TODOS de los pertinentes",
          all(c.resolucion in {x.resolucion for x in pertinentes} for c in ahora))
comprobar("y los que sobran se descartan por el TOPE, no por asunto",
          any(m == "no cabe en el tope" for _c, m in desc)
          or len(pertinentes) == len(ahora), str(motivos))
ordenados = sorted(ahora, key=T.peso)
comprobar("y van ordenados por peso juridico",
          [c.resolucion for c in ahora] == [c.resolucion for c in ordenados],
          str([c.resolucion for c in ahora]))

# ==================================== 7. SI NO QUEDA NINGUNO, SE DICE
print("\n=== 7. SI NINGUNO VIENE AL CASO, EL AVISO LO DICE ===")
print("  Mejor eso que traer uno que no viene al caso. Callarlo deja creer")
print("  que no hay doctrina, que es distinto de que no venga al caso.\n")
RARA = "notificacion electronica y representacion del obligado tributario"
ninguno, desc2 = cache.seleccionar(pares, N, consulta=RARA, indice=ix)
lec = T.leer_doctrina(ninguno, pares, [], N, desc2)
for s in lec.debiles:
    print(f"    {s[:132]}")
comprobar("no se manda ninguno", ninguno == [], str(ninguno))
comprobar("pero hay aviso", bool(lec.debiles), str(lec.debiles))
comprobar("dice CUANTAS hay", any("resolucion(es)" in s for s in lec.debiles))
comprobar("y que NINGUNA es del mismo asunto",
          any("NINGUNA es del mismo asunto" in s for s in lec.debiles),
          str(lec.debiles)[:120])
comprobar("solo sobre los articulos EN JUEGO, no sobre todos los que citan",
          len(lec.debiles) <= len({b for _a, b in pares}),
          f"{len(lec.debiles)} avisos para {len({b for _a, b in pares})} articulos")

# ==================================== 8. SIN CONSULTA, COMPATIBLE
print("\n=== 8. SIN CONSULTA NO SE FILTRA POR ASUNTO (compatibilidad) ===")
comprobar("por_preceptos sigue devolviendo una lista",
          isinstance(cache.por_preceptos(pares, N), list))
sin_consulta, _ = cache.seleccionar(pares, N)
comprobar("sin consulta, el filtro de ASUNTO no actua",
          len(sin_consulta) == len(antes))
comprobar("pero el de MATERIA actua SIEMPRE",
          not any(T.materia_ajena(c) for c in sin_consulta),
          str([c.resolucion for c in sin_consulta]))

# ==================================== 9. CONTROL NEGATIVO
print("\n=== 9. LA PRUEBA SABE PONERSE ROJA ===")
print("  Se selecciona a mano SIN filtro de materia -como estaba antes- y se")
print("  comprueba que entra la doctrina de electricidad.\n")
objetivo = {(a, b) for a, b in pares if b}
solo_articulo = sorted(
    [c for c in cache.todas() if set(c.preceptos(N)) & objetivo], key=T.peso)[:3]
print(f"    solo por articulo: {[c.resolucion for c in solo_articulo]}")
colados = [c.resolucion for c in solo_articulo if c.resolucion in ELECTRICIDAD]
comprobar("sin el filtro de materia se cuela la electricidad", bool(colados),
          str(colados))
comprobar("y el bloque 5 lo habria cazado",
          any(c.resolucion in ELECTRICIDAD for c in solo_articulo))
print("    (con el filtro puesto no entra ninguno: la prueba mide de verdad)")

print("\n" + "=" * 62)
print(f"FALLOS: {len(fallos)}")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
