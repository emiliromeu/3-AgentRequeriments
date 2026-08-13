#!/usr/bin/env python3
"""UN TEAR NO ES EL TEAC. Cero red, cero API.

AQUI VIVE EL DEFECTO MAS GRAVE QUE SE HA ENCONTRADO EN EL PROYECTO. La busqueda
de DYCTEA manda el filtro de unidad vacio, asi que devuelve TODOS los tribunales.
En la copia local habia dos resoluciones que no eran del TEAC y se citaban asi:

    {Criterio TEAC 07/02872/2023/00/00, de 29/04/2025, TEAR de Baleares — ...}

La etiqueta decia TEAC y la unidad decia TEAR, en la misma linea. Y el bloque
del material les atribuia la fuerza del articulo 239.8 LGT, que un tribunal
regional no tiene.

UNA CITA LITERALMENTE CORRECTA ATRIBUIDA AL TRIBUNAL EQUIVOCADO SALE VERDE, y
eso es peor que una inventada: es comprobable, parece buena y nadie la mira.

    python pruebas/prueba_unidad.py
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase3
import fase4
from agente_fiscal import citas as CIT
from agente_fiscal import configuracion as C
from agente_fiscal import teac as T
from agente_fiscal import verificador as VF

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:110]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix, g = fase4.cargar_corpus()
# LA DESPENSA, SOLO PARA PROPIEDADES UNIVERSALES.
#
# «Ninguna regional se presenta como criterio del TEAC» o «el orden por peso es
# monotono» son ciertas para lo que haya dentro, y cuantos mas documentos haya
# mas fuerte es la comprobacion. Esas se quedan aqui.
#
# Lo que se AFIRMA -«existe un TEAC no vinculante»- va contra fixture: era
# cierto con nueve criterios y lo sigue siendo con novecientos, pero es una
# afirmacion sobre datos que crecen, y esas se pudren en cada siembra.
# `prueba_asunto` se puso roja exactamente asi. Ver `casos/teac_unidad`.
cache_real = T.CacheTEAC()
cache_unidad = T.CacheTEAC(RAIZ / "casos" / "teac_unidad")
por_id = {c.resolucion: c for c in cache_real.todas()}

# La cache de PRUEBA, con criterios inventados. Nunca se mezcla con la de
# verdad: una resolucion inventada en la cache real seria indistinguible de una
# autentica.
cache_prueba = T.CacheTEAC(RAIZ / "casos" / "teac_prueba")
TEAR_PRUEBA = "08/09003/2022/00/00"
# Una resolucion que NO esta en ninguna copia, para probar la rama del
# criterio ausente. Serie 9xxx, como el resto de los fixtures.
TEAR_AUSENTE = "08/09004/2022/00/00"
TEAC_PRUEBA = "00/09001/2024/00/00"

# =============================================== 1. LA ETIQUETA SALE DEL REGISTRO
print("\n=== 1. LA ETIQUETA SALE DE `unidad`, NO DE UN TEXTO FIJO ===")
for unidad, esperado, que in [
        ("TEAC", "Criterio TEAC", "el central"),
        ("TEAR de Cataluña", "Resolucion del TEAR de Cataluña", "uno regional"),
        ("Sala Desconc. de Alicante",
         "Resolucion del Sala Desconc. de Alicante", "una sala"),
        ("", "Resolucion economico-administrativa", "sin unidad")]:
    obtenido = T.etiqueta_de(unidad)
    comprobar(f"«{unidad or '(vacia)'}» ({que}) -> {esperado}",
              obtenido == esperado, obtenido)
comprobar("un TEAR NUNCA se llama «criterio»",
          "Criterio" not in T.etiqueta_de("TEAR de Cataluña"),
          T.etiqueta_de("TEAR de Cataluña"))

# LAS REGIONALES REALES DE LA COPIA. Eran DOS -las que cayeron probando- y al
# sembrar el TEAC pasaron a decenas. El numero exacto no protege nada y caduca
# en cuanto se siembra otra vez; lo que hay que garantizar es que HAYA alguna
# con la que probar, y que NINGUNA se presente como criterio del TEAC.
print("\n  Y las REALES de la copia local, que fueron el defecto:")
# LA PROPIEDAD se comprueba sobre TODA la despensa -es universal y se refuerza
# con cada documento nuevo-, pero NO se imprime una linea por criterio: con
# novecientos, el informe de la suite dejaria de poder leerse.
regionales = [c for c in cache_real.todas() if not c.es_central]
comprobar("hay resoluciones regionales con las que comprobarlo",
          len(regionales) >= 2, str(len(regionales)))
print(f"    {len(regionales)} en la copia; se comprueban TODAS, sin listarlas")
for c in regionales:
    comprobar(f"{c.resolucion}: la cita NO dice «Criterio TEAC»",
              "Criterio TEAC" not in c.cita(), c.cita()[:70])
    comprobar(f"{c.resolucion}: y nombra a SU tribunal",
              c.unidad in c.etiqueta, c.etiqueta)

# ================================= 2. LA FUERZA SALE DE unidad + calificacion
print("\n=== 2. LA FUERZA SALE DE unidad + calificacion, NO DEL NOMBRE ===")
print("  Hacen falta LOS DOS campos: el 239.8 es del TEAC cuando sienta")
print("  doctrina. Ni un TEAR con la calificacion mas alta lo tiene, ni un")
print("  TEAC «No vinculante».\n")
CASOS = [
    ("TEAC", "Doctrina", True, "TEAC que sienta doctrina"),
    ("TEAC", "No vinculante", False, "TEAC NO vinculante"),
    ("TEAR de Cataluña", "Doctrina", False, "TEAR aunque diga Doctrina"),
    ("TEAR de Cataluña", "No vinculante", False, "TEAR no vinculante"),
    ("TEAC", "", False, "sin calificacion"),
    ("TEAC", "Algo que no sabemos traducir", False, "calificacion desconocida"),
]
for unidad, calif, invoca, que in CASOS:
    f = T.fuerza_de(unidad, calif)
    print(f"    {que:34s} -> {f[:58]}")
    comprobar(f"{que}: {'SI' if invoca else 'NO'} invoca el 239.8",
              ("239.8" in f) == invoca, f)
comprobar("un TEAR con «Doctrina» dice expresamente que es REGIONAL",
          "REGIONAL" in T.fuerza_de("TEAR de Cataluña", "Doctrina"))
comprobar("sin calificacion, NO se le supone ninguna fuerza",
          "no se le supone" in T.fuerza_de("TEAC", ""))

# Y en la copia local de verdad.
central_no_vinc = [c for c in cache_unidad.todas()
                   if c.es_central and c.calificacion.lower().startswith("no vinc")]
comprobar("en el fixture HAY un TEAC «No vinculante» (no es hipotetico)",
          bool(central_no_vinc), str(len(central_no_vinc)))
for c in central_no_vinc:
    comprobar(f"{c.resolucion}: siendo del TEAC, NO invoca el 239.8",
              "239.8" not in c.fuerza, c.fuerza)

# ======================================= 3. EL ROTULO, EN LOS DOS SENTIDOS
print("\n=== 3. EL ROTULO SE COMPRUEBA EN LOS DOS SENTIDOS ===")
print("  Enganan los dos: llamar TEAC a un TEAR le da fuerza que no tiene;")
print("  llamar TEAR a un TEAC se la quita, y el profesional descarta")
print("  doctrina que SI le obliga.\n")
CASOS = [
    ("Criterio TEAC 08/09003/2022/00/00", "TEAR de Cataluña", T.ROTULO_MAL,
     "un TEAR presentado como TEAC"),
    ("Resolucion del TEAR de Cataluña 08/09003/2022/00/00", "TEAR de Cataluña",
     T.ROTULO_OK, "un TEAR nombrado como lo que es"),
    ("Resolucion del TEAR de Cataluna 08/09003/2022/00/00", "TEAR de Cataluña",
     T.ROTULO_OK, "lo mismo sin la eñe: no se tumba por un teclado"),
    ("Criterio TEAC 00/09001/2024/00/00", "TEAC", T.ROTULO_OK, "el TEAC como TEAC"),
    ("Resolucion del TEAR de Cataluña 00/09001/2024/00/00", "TEAC",
     T.ROTULO_MAL, "el TEAC degradado a regional"),
    ("Criterio TEAC 08/09003/2022/00/00", "", T.ROTULO_SIN_UNIDAD,
     "sin unidad en la copia local: NO se puede comprobar"),
]
for bruto, unidad, esperado, que in CASOS:
    estado, motivo = T.rotulo_valido(bruto, unidad)
    comprobar(que, estado == esperado, f"estado={estado} · {motivo[:60]}")
comprobar("«sin unidad» NO es lo mismo que «vale»",
          T.ROTULO_SIN_UNIDAD != T.ROTULO_OK)

# ============================ 4. Y EL VERIFICADOR LO APLICA DE VERDAD
print("\n=== 4. LA BATERIA: EL VERIFICADOR TUMBA LA ATRIBUCION FALSA ===")
verificador = VF.Verificador(ix, cache_teac=cache_prueba)
ENLACE = ("https://serviciostelematicosext.hacienda.gob.es/TEAC/DYCTEA/"
          "criterio.aspx?id=")
FRAG = ("el credito debe acreditarse como definitivamente incobrable antes de "
        "rectificar la cuota repercutida")
TEXTOS = [
    (f'La doctrina establece que «{FRAG}» '
     f'{{Criterio TEAC {TEAR_PRUEBA}, de 21/09/2022, TEAC — '
     f'{ENLACE}08/09003/2022/00/0/1}}.',
     VF.NO_VERIFICADA, "TEAR presentado como Criterio TEAC"),
    (f'El tribunal regional resolvio que «{FRAG}» '
     f'{{Resolucion del TEAR de Cataluña {TEAR_PRUEBA}, de 21/09/2022 — '
     f'{ENLACE}08/09003/2022/00/0/1}}.',
     VF.VERIFICADA, "el mismo, nombrando a su tribunal"),
    ('El tribunal regional senala que «La modificacion de la base imponible '
     'exige el cumplimiento de los requisitos» '
     f'{{Resolucion del TEAR de Cataluña {TEAC_PRUEBA}, de 15/03/2025 — '
     f'{ENLACE}00/09001/2024/00/0/1}}.',
     VF.NO_VERIFICADA, "TEAC degradado a resolucion de TEAR"),
]
for texto, esperado, que in TEXTOS:
    inf = verificador.verificar_texto(texto, 2023, exigir_norma=True)
    obtenido = inf.dictamenes[0].estado if inf.dictamenes else "(sin citas)"
    motivo = inf.dictamenes[0].motivo if inf.dictamenes else ""
    comprobar(f"{que} -> {esperado}", obtenido == esperado,
              f"{obtenido}: {motivo[:70]}")
    if esperado == VF.NO_VERIFICADA and obtenido == esperado:
        comprobar(f"  y el motivo habla del tribunal",
                  "TEAC" in motivo or "regional" in motivo or "tribunal" in motivo,
                  motivo[:80])

print("\n  Lo que se rechaza es la ATRIBUCION, no la fuente: la misma")
print("  resolucion, el mismo fragmento y el mismo enlace, valen.")

# ========================================= 5. EL ORDEN POR PESO
print("\n=== 5. PRIMERO EL PESO JURIDICO, DESPUES LA FECHA ===")
print("  Un TEAR de 2025 no puede adelantar a doctrina del TEAC de 2004.\n")
mezcla = sorted(cache_real.todas(), key=T.peso)
print(f"    {len(mezcla)} criterios ordenados; se comprueba el orden entero")
niveles = [T.nivel(c) for c in mezcla]
comprobar("el orden por peso es monotono", niveles == sorted(niveles),
          str(niveles))
comprobar("TODO el TEAC va antes que cualquier regional",
          max(T.nivel(c) for c in mezcla if c.es_central)
          < min(T.nivel(c) for c in mezcla if not c.es_central))
tear_nuevo = [c for c in mezcla if not c.es_central and (c.anio or 0) >= 2025]
teac_viejo = [c for c in mezcla if c.es_central and (c.anio or 0) <= 2010]
if tear_nuevo and teac_viejo:
    comprobar(f"el TEAR de {tear_nuevo[0].anio} va DETRAS del TEAC de "
              f"{teac_viejo[0].anio}",
              mezcla.index(teac_viejo[0]) < mezcla.index(tear_nuevo[0]))
comprobar("dentro del TEAC, la unificacion de criterio va primero",
          T.NIVEL_UNIFICACION < T.NIVEL_DOCTRINA < T.NIVEL_CENTRAL
          < T.NIVEL_REGIONAL)

# ================================= 6. NUNCA COMO DOCTRINA
print("\n=== 6. UN TEAR NUNCA SE PRESENTA COMO DOCTRINA ===")
from agente_fiscal import redactor as RED
tear = por_id[regionales[0].resolucion]
bloque = RED.bloque_criterio_teac(tear)
comprobar("su bloque NO se titula «CRITERIO TEAC»",
          "[CRITERIO TEAC" not in bloque.upper(), bloque[:80])
comprobar("se titula con SU tribunal",
          tear.unidad.upper() in bloque.upper(), bloque[:80])
comprobar("y lleva un campo FUERZA que dice que no vincula",
          "FUERZA" in bloque and "NO VINCULA" in bloque, bloque[:200])
comprobar("el bloque de tribunales regionales dice que NO vincula a nadie",
          "NO VINCULA A NADIE" in RED.BLOQUE_TEAR.upper())
comprobar("y que vale por valor PREDICTIVO", "predictivo" in RED.BLOQUE_TEAR)
comprobar("el bloque del TEAC ya no afirma que TODO vincule",
          "NO TODO LO DE AQUI VINCULA" in RED.BLOQUE_TEAC)

# ======================================= 7. CONTROL NEGATIVO
print("\n=== 7. LA PRUEBA SABE PONERSE ROJA ===")
print("  Se comprueba que una atribucion falsa con texto y enlace CORRECTOS")
print("  seria indistinguible de una buena sin la comprobacion de rotulo.\n")
texto_malo = (f'La doctrina establece que «{FRAG}» '
              f'{{Criterio TEAC {TEAR_PRUEBA}, de 21/09/2022, TEAC — '
              f'{ENLACE}08/09003/2022/00/0/1}}.')
cita = CIT.extraer(texto_malo)[0][0]
criterio = cache_prueba.leer(TEAR_PRUEBA)
cuerpo = CIT.normalizar_literal(" ".join((criterio.criterio, criterio.asunto)))
comprobar("el fragmento SI esta literal en el documento",
          CIT.normalizar_literal(cita.literal_norm) in cuerpo
          or all(t in cuerpo for t in (cita.trozos or [cita.literal_norm])))
comprobar("y el enlace apunta a la resolucion correcta",
          T.mismo_criterio("08/09003/2022/00/0/1", TEAR_PRUEBA))
comprobar("o sea: sin la comprobacion de rotulo, saldria VERIFICADA",
          T.rotulo_valido(cita.referencia.bruto, criterio.unidad)[0] == T.ROTULO_MAL)
print("    (texto correcto + enlace correcto + tribunal equivocado = verde)")

# ============================== 8. UNA SOLA FUNCION NOMBRA LA RESOLUCION
print("\n=== 8. UNA SOLA FUNCION COMPONE LA ETIQUETA ===")
print("  Dos formas de escribir lo mismo divergen siempre. Esta divergio: el")
print("  verificador ponia la constante «Criterio TEAC» y solo la corregia si")
print("  el criterio estaba en la copia local, asi que a una resolucion de un")
print("  TEAR que no tuvieramos guardada la llamaba TEAC.\n")

comprobar("etiqueta_de recibe el NOMBRE de la unidad, no el codigo del numero",
          T.etiqueta_de("TEAR de Baleares") == "Resolucion del TEAR de Baleares",
          T.etiqueta_de("TEAR de Baleares"))
comprobar("y sin unidad NO dice «TEAC»: dice la neutra",
          "TEAC" not in T.etiqueta_de(""), T.etiqueta_de(""))
comprobar("un TEAR nunca se nombra «criterio»",
          "riterio" not in T.etiqueta_de("TEAR de Cataluña"),
          T.etiqueta_de("TEAR de Cataluña"))
comprobar("y el TEAC si", T.etiqueta_de("TEAC") == T.ETIQUETA, T.etiqueta_de("TEAC"))

# El camino del verificador, con el criterio AUSENTE de la copia local: es la
# rama que menos se mira y es justo donde estaba el fallo.
vacia = T.CacheTEAC(RAIZ / "casos" / "no_existe_esta_carpeta")
v = VF.Verificador(ix, cache_teac=vacia)
texto = (f'La doctrina dice que «un fragmento» '
         f'{{Resolucion del TEAR de Cataluña {TEAR_AUSENTE}, de 21/09/2022 — '
         f'{ENLACE}08/09004/2022/00/0/1}}.')
inf = v.verificar_texto(texto, 2023)
dic = [d for d in inf.dictamenes if d.norma == "teac"]
comprobar("se dictamina la cita del TEAR ausente", bool(dic))
if dic:
    d = dic[0]
    print(f"    referencia_corpus: {d.referencia_corpus!r}")
    print(f"    motivo           : {d.motivo[:70]}")
    comprobar("NO la llama «Criterio TEAC» sin saber quien la dicto",
              "Criterio TEAC" not in d.referencia_corpus, d.referencia_corpus)
    comprobar("usa la etiqueta neutra",
              d.referencia_corpus.startswith(T.etiqueta_de("")),
              d.referencia_corpus)
    comprobar("y el motivo tampoco dice «del TEAC»",
              "del TEAC" not in d.motivo, d.motivo[:90])
    comprobar("sigue siendo NO_VERIFICABLE, que es lo que era",
              d.estado == VF.NO_VERIFICABLE, d.estado)

print("\n  Y NO QUEDA NINGUN OTRO SITIO QUE LA COMPONGA A MANO:")
import ast

# QUE SE BUSCA, EXACTAMENTE. Dos formas de acabar con una etiqueta compuesta
# por libre, y solo dos:
#
#   a) escribir «Criterio TEAC» dentro de una f-string, que es como se compone
#      una etiqueta en tiempo de ejecucion;
#   b) usar la constante `teac.ETIQUETA` fuera de `teac.py`, o sea colgarle la
#      etiqueta del TEAC a algo sin preguntar de quien es.
#
# NO cuenta el literal suelto dentro de un texto: `BLOQUE_TEAC` -el trozo de
# prompt que le enseña el formato al modelo- lleva «Criterio TEAC» a proposito,
# y esta bien que lo lleve. La primera version de esta comprobacion lo cazaba y
# era un falso positivo; un falso positivo acaba en que alguien la apaga.


def fstrings_con(ruta, aguja):
    salida = []
    for nodo in ast.walk(ast.parse(ruta.read_text("utf-8"))):
        if not isinstance(nodo, ast.JoinedStr):
            continue
        literal = "".join(v.value for v in nodo.values
                          if isinstance(v, ast.Constant)
                          and isinstance(v.value, str))
        if aguja in literal:
            salida.append((nodo.lineno, literal[:60]))
    return salida


def usa_constante(ruta, modulo, nombre):
    salida = []
    for nodo in ast.walk(ast.parse(ruta.read_text("utf-8"))):
        if (isinstance(nodo, ast.Attribute) and nodo.attr == nombre
                and isinstance(nodo.value, ast.Name)):
            salida.append((nodo.lineno, f"{nodo.value.id}.{nombre}"))
    return salida


for mod in ("verificador", "redactor", "citas", "bloques", "estado", "dgt"):
    ruta = RAIZ / "agente_fiscal" / f"{mod}.py"
    malas = fstrings_con(ruta, "Criterio TEAC")
    comprobar(f"{mod}.py no compone «Criterio TEAC» en ninguna f-string",
              not malas, str(malas[:1]))
    # `D.ETIQUETA` (la de la DGT) es legitima: solo hay una clase de consulta.
    # La del TEAC no, porque hay dos clases de resolucion.
    fuera = [(n, x) for n, x in usa_constante(ruta, "T", "ETIQUETA")
             if x.startswith("T.")]
    comprobar(f"{mod}.py no usa la constante teac.ETIQUETA por su cuenta",
              not fuera, str(fuera[:2]))

# CONTROL NEGATIVO del detector: si alguien lo escribiera a pelo, ¿lo caza?
falso = RAIZ / "casos" / "_detector_de_etiqueta.py"
falso.write_text(
    '"""Un docstring con Criterio TEAC dentro, que NO cuenta."""\n'
    'PROMPT = "formato: {Criterio TEAC 00/06614/2024/00/00}"  # tampoco cuenta\n'
    'def f(numero):\n'
    '    return f"Criterio TEAC {numero}"   # esto SI cuenta\n',
    encoding="utf-8")
try:
    pillado = fstrings_con(falso, "Criterio TEAC")
    comprobar("el detector caza la etiqueta compuesta en una f-string",
              len(pillado) == 1, str(pillado))
    comprobar("y NO se queja del docstring ni del texto del prompt",
              len(pillado) == 1)
finally:
    falso.unlink(missing_ok=True)

print("\n" + "=" * 62)
print(f"FALLOS: {len(fallos)}")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
