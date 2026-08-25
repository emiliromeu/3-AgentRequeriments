#!/usr/bin/env python3
"""LA REGLA DEL CUERPO HERMANO LA PREGUNTAN TODOS. Cero red, cero API.

    python3 pruebas/prueba_hermano.py

LA REGLA. Un documento del BOE puede traer dos articulados: el del Real
Decreto que aprueba -uno o seis articulos- y el del Reglamento aprobado
-ciento y pico-. Quien escribe «articulo 82 del Real Decreto 939/2005» esta
nombrando bien la norma; el 82 vive en el Reglamento General de Recaudacion,
que ese real decreto aprueba. `normas.cuerpo_hermano_con` corrige eso, con sus
contenciones dentro, y es la UNICA implementacion que hay.

POR QUE ESTA SUITE NO PRUEBA LA REGLA, SINO QUIEN LA PREGUNTA.

Que la regla funciona ya lo prueba `prueba_cuerpo.py`. Lo que se ha roto dos
veces es otra cosa: que un modulo nuevo resuelva una norma y busque el
articulo por su cuenta, sin preguntarla. Paso con el grafo de remisiones
-estaba en la DGT y no en el grafo- y ha vuelto a pasar con el verificador,
que era el consumidor que faltaba y el mas caro de todos.

MEDIDO EL 25/08/2026, con el verificador todavia sin la regla:

  · 1174 de los 2043 articulos del corpus -el 57%- viven en un cuerpo aprobado
    por otro, y no se podian citar por el numero de su decreto;
  · en las trazas guardadas, 328 citas de 31 consultas reales; cinco acabaron
    en NO ENCONTRADO sin ningun otro motivo que este;
  · y de esas 1174, novecientas cincuenta y tres salian con el motivo «la cita
    no dice de que norma es», que es FALSO: la cita lo decia con nombre y
    numero. Ver el LEEME: un motivo equivocado es peor que un fallo.

Al buscar los consumidores aparecio un CUARTO -`teac.Criterio.preceptos`- que
tampoco la preguntaba. Hoy no muerde (cero pares mal atribuidos en los 909
criterios cacheados, porque DYCTEA nombra el reglamento y no el real decreto),
pero la via lo permitia.

LO QUE HACE ESTA SUITE, ENTONCES:

  1. cada consumidor resuelve bien un caso que SOLO sale con la regla;
  2. sin la regla, los cuatro se caen -si uno no se cae, es que no la
     preguntaba y el caso pasaba por otro sitio-;
  3. y el inventario: quien resuelve designaciones contra el registro esta
     clasificado, o consumidor o excepcion razonada. El dia que aparezca un
     quinto, esta suite se pone roja hasta que alguien decida cual es.
"""
import glob
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4                                     # noqa: E402
from agente_fiscal import dgt as D               # noqa: E402
from agente_fiscal import normas as NM           # noqa: E402
from agente_fiscal import referencias as R       # noqa: E402
from agente_fiscal import teac as T              # noqa: E402
from agente_fiscal import verificador as VF      # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:110]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix, _g = fase4.cargar_corpus()
N = ix.normas
V = VF.Verificador(ix)

# El caso patron, y se busca en el corpus en vez de escribirlo: un cuerpo
# aprobado por otro, y un articulo que solo existe en el aprobado.
RGR = next(c for c in N.cuerpos if c.endswith("14803#1"))
DECRETO = RGR.split("#")[0] + "#0"
ART = "82"
assert N.tiene_articulo(RGR, ART) and not N.tiene_articulo(DECRETO, ART)


def literal_de(clave_cuerpo, numero):
    """Un trozo literal del articulo, tal cual esta en el corpus."""
    for d in ix.docs:
        r = d.registro
        if (r.get("cuerpo_clave") == clave_cuerpo
                and str(r.get("numero") or "") == str(numero)):
            texto = (r.get("versiones") or [{}])[-1].get("texto") or ""
            return " ".join(texto.split("\n", 1)[-1].split())[:120]
    return ""


LITERAL = literal_de(RGR, ART)


# --------------------------------------------------------------------------
# Los cuatro consumidores. Cada comprobacion se escribe como una funcion para
# poder repetirla luego con la regla desactivada: si una pasa las dos veces,
# no estaba preguntando nada.
# --------------------------------------------------------------------------

def consumidor_verificador():
    """Una cita que nombra el REAL DECRETO y cita un articulo del reglamento."""
    informe = V.verificar_texto(
        f'La norma dispone que «{LITERAL}» '
        f'(articulo {ART} del {N.cuerpos[DECRETO].etiqueta}).', 2024)
    return informe.dictamenes[0].estado == VF.VERIFICADA


def consumidor_dgt():
    """El campo «normativa» de una consulta, que la fuente escribe asi."""
    pares = D.pares_de_normativa(
        f"{N.cuerpos[DECRETO].etiqueta} art. {ART}", N)
    return bool(pares) and pares[0].cuerpo == RGR


def consumidor_teac():
    """Las referencias de un criterio, agrupadas por norma."""
    criterio = T.Criterio.de_registro({
        "id": "00/09999/2026/00/0/1",
        "referencias": [{"norma": N.cuerpos[DECRETO].etiqueta,
                         "codigo": "", "preceptos": [ART]}],
    })
    return criterio.preceptos(N) == [(RGR, ART)]


def consumidor_grafo():
    """El grafo de remisiones, sobre el corpus entero."""
    grafo = R.GrafoRemisiones(ix.docs, N)
    return sum(1 for rems in grafo.adelante.values() for r in rems
               if r.estado == R.RESUELTA)


CONSUMIDORES = {
    "verificador.py": consumidor_verificador,
    "dgt.py": consumidor_dgt,
    "teac.py": consumidor_teac,
    "referencias.py": consumidor_grafo,
}

print("\n1. CADA CONSUMIDOR RESUELVE EL CASO QUE NECESITA LA REGLA")
print(f"   (articulo {ART}: no esta en {N.cuerpos[DECRETO].etiqueta}, "
      f"esta en\n    {N.cuerpos[RGR].etiqueta})\n")

comprobar("hay literal del articulo para la prueba de punta a punta",
          bool(LITERAL), LITERAL)
comprobar("verificador: la cita queda VERIFICADA", consumidor_verificador())
comprobar("dgt: el par apunta al reglamento", consumidor_dgt())
comprobar("teac: el par apunta al reglamento", consumidor_teac())
resueltas_con = consumidor_grafo()
comprobar("grafo: hay remisiones resueltas", resueltas_con > 0, resueltas_con)

# Ademas de resolver bien, el verificador tiene que DECIRLO. Una correccion
# que no se ve es una correccion a espaldas de quien audita el expediente.
informe = V.verificar_texto(
    f'La norma dispone que «{LITERAL}» '
    f'(articulo {ART} del {N.cuerpos[DECRETO].etiqueta}).', 2024)
comprobaciones = " · ".join(informe.dictamenes[0].comprobaciones)
comprobar("y el verificador deja constancia de que leyo en el cuerpo hermano",
          "que aquel aprueba" in comprobaciones, comprobaciones[:120])


print("\n2. SIN LA REGLA, LOS CUATRO SE CAEN")
print("   (si alguno sigue en verde, es que no la preguntaba)\n")

original = NM.Registro.cuerpo_hermano_con
try:
    NM.Registro.cuerpo_hermano_con = lambda self, cuerpo, numero: ""
    comprobar("verificador: sin la regla, la cita ya no queda VERIFICADA",
              not consumidor_verificador())
    comprobar("dgt: sin la regla, el par ya no apunta al reglamento",
              not consumidor_dgt())
    comprobar("teac: sin la regla, el par ya no apunta al reglamento",
              not consumidor_teac())
    resueltas_sin = consumidor_grafo()
    comprobar("grafo: sin la regla se pierden remisiones",
              resueltas_sin < resueltas_con,
              f"con={resueltas_con} sin={resueltas_sin}")
    print(f"      (el grafo pasa de {resueltas_con} a {resueltas_sin} resueltas)")
finally:
    NM.Registro.cuerpo_hermano_con = original

comprobar("y la regla queda como estaba al terminar",
          NM.Registro.cuerpo_hermano_con is original)
comprobar("(control) con la regla restaurada, el verificador vuelve a verde",
          consumidor_verificador())


print("\n3. EL INVENTARIO: NADIE RESUELVE NORMAS POR SU CUENTA")
print("   (el dia que aparezca un quinto, esto se pone rojo)\n")

# Quien convierte una designacion en un cuerpo. Se lee del codigo, no de una
# lista de memoria: es lo unico que puede enterarse de un modulo nuevo.
_RE_RESUELVE = re.compile(
    r"\.resolver\(|\.nombrar\(|resolver_norma\(|_resolver_designacion\(")

# Los que resuelven y NO localizan preceptos. Cada uno con su razon, que es lo
# que hay que rehacer el dia que el modulo cambie de trabajo.
SIN_PRECEPTO = {
    "normas.py": "es donde vive la regla",
    "citas.py": "resuelve el NOMBRE de la norma de una cita y para ahi; "
                "quien busca el precepto es el verificador, que si la pregunta",
    "redactor.py": "resuelve para decidir si un parrafo del material es de "
                   "OTRA norma. No localiza ningun precepto ni produce "
                   "señal: equivocarse manda un parrafo de menos, nunca da "
                   "por buena una cita",
}

encontrados = set()
for ruta in sorted(glob.glob(str(RAIZ / "agente_fiscal" / "*.py"))):
    fuente = Path(ruta).read_text(encoding="utf-8")
    nombre = os.path.basename(ruta)
    if _RE_RESUELVE.search(fuente) or "cuerpo_hermano_con" in fuente:
        encontrados.add(nombre)

clasificados = set(CONSUMIDORES) | set(SIN_PRECEPTO)
nuevos = encontrados - clasificados
comprobar("no hay ningun modulo sin clasificar", not nuevos,
          f"sin clasificar: {sorted(nuevos)}")
sobran = clasificados - encontrados
comprobar("y no queda ninguno declarado que ya no resuelva nada", not sobran,
          f"declarados de mas: {sorted(sobran)}")

for modulo in sorted(CONSUMIDORES):
    fuente = (RAIZ / "agente_fiscal" / modulo).read_text(encoding="utf-8")
    comprobar(f"{modulo} pregunta la regla, no lleva copia propia",
              "cuerpo_hermano_con" in fuente
              and "def cuerpo_hermano_con" not in fuente)

fuente_normas = (RAIZ / "agente_fiscal" / "normas.py").read_text(encoding="utf-8")
comprobar("y la implementacion sigue siendo UNA sola",
          fuente_normas.count("def cuerpo_hermano_con") == 1
          and sum(Path(r).read_text(encoding="utf-8").count(
              "def cuerpo_hermano_con")
              for r in glob.glob(str(RAIZ / "agente_fiscal" / "*.py"))) == 1)

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
