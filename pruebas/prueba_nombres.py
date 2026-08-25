#!/usr/bin/env python3
"""CADA NORMA DEL CORPUS TIENE QUE SER CITABLE POR SU NOMBRE. Cero red, cero API.

    python3 pruebas/prueba_nombres.py

POR QUE EXISTE ESTA SUITE.

Medido el 25/08/2026, antes de arreglarlo:

  · de las diecisiete designaciones oficiales, DOS no resolvian -«Real Decreto
    Legislativo 1/1993» y «Decreto Legislativo 1/2024»-, porque el patron que
    lee el nombre cortaba en «Real Decreto» y en «Decreto»;
  · de los once cuerpos que las normas APRUEBAN -que es donde vive el
    articulado que se cita-, SEIS no se podian nombrar: el Reglamento General
    de Recaudacion, el RGAT, el del regimen sancionador, el de facturacion, el
    del ITPAJD por su nombre entero y el libro sexto del Codigo tributario de
    Catalunya. Son 704 de los 2043 articulos del corpus;
  · y la Ley 58/2003 no se podia citar como «Ley General Tributaria», que es
    como la llama todo el mundo y como la titula el BOE.

Una respuesta que citara el Reglamento General de Recaudacion por su nombre
salia NO_VERIFICABLE, y como no hay verificacion parcial, la respuesta entera
se caia. El fallo no era del corpus: el articulo estaba, el texto estaba y la
version estaba. Era que el nombre no se sabia leer.

QUE COMPRUEBA, Y POR QUE ASI.

Las formas de nombrar NO SE ESCRIBEN AQUI: se derivan del titulo oficial que
ya guarda el corpus, igual que las deriva el registro. La suite las vuelve a
sacar por su cuenta -del titulo, no llamando al generador de alias- para que
no sea el mismo codigo comprobandose a si mismo.

Y RECORRE LOS CUERPOS QUE HAYA, no diecisiete escritos a mano. El dia que
entre una norma nueva, esta suite dice si el verificador sabe nombrarla sin
que nadie toque este fichero.

LO QUE NO PUEDE PASAR AL ARREGLARLO: que reconocer mas nombres se convierta en
reconocer cualquier cosa. La ultima parte comprueba que las normas de fuera
del corpus siguen saliendo EXTERNAS -que es NO_VERIFICABLE, no verificada- y
que una designacion ambigua se sigue declinando.
"""
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4                                     # noqa: E402
from agente_fiscal import citas as C             # noqa: E402
from agente_fiscal import verificador as VF      # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:110]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix, _g = fase4.cargar_corpus()
N = ix.normas

# --------------------------------------------------------------------------
# Las formas de nombrar, sacadas del titulo oficial. Esto es lo unico que la
# suite sabe hacer: leer un titulo del BOE.
# --------------------------------------------------------------------------

_RE_APRUEBA = re.compile(
    r"por (?:el|la) que se aprueban?\s+(?:el|la)\s+(?P<n>.+?)"
    r"(?:\s+y se modifica|\s*[,\.]|$)", re.IGNORECASE)


def designacion_oficial(titulo: str) -> str:
    """«Ley 58/2003, de 17 de diciembre, General Tributaria.» -> «Ley 58/2003».

    Lo que va delante de la primera coma. Es como se cita una norma en un
    escrito, y como la nombra el propio BOE en sus remisiones.
    """
    return titulo.split(",")[0].strip()


def nombre_aprobado(titulo: str) -> str:
    """Lo que la norma APRUEBA: «...se aprueba el Reglamento General de...»."""
    m = _RE_APRUEBA.search(titulo)
    return re.sub(r"\s+", " ", m.group("n")).strip() if m else ""


def como_se_resuelve(nombre: str):
    """Lo que el verificador entiende cuando lee una cita con ese nombre.

    Se pregunta por la via real -una respuesta redactada, con su fragmento
    entre comillas y su referencia- y no llamando al registro por dentro: el
    defecto medido vivia justo en el trecho entre las dos cosas.
    """
    texto = (f'Segun la norma, «un fragmento literal cualquiera» '
             f'(articulo 3 del {nombre}, https://www.boe.es/x).')
    citas, _sueltas = C.extraer(texto, registro=N)
    return citas[0].referencia


# --------------------------------------------------------------------------
print("\n1. EL NOMBRE OFICIAL DE CADA NORMA DEL CORPUS")
print("   (la designacion con la que se cita: rango y numero)\n")

titulos = {c.norma_id: c.norma_titulo for c in N.cuerpos.values()}
print(f"   {len(titulos)} normas cargadas\n")

for norma_id in sorted(titulos):
    nombre = designacion_oficial(titulos[norma_id])
    ref = como_se_resuelve(nombre)
    comprobar(f"«{nombre}» designa a {norma_id}",
              ref.norma == "cargada" and ref.cuerpo == f"{norma_id}#0",
              f"{ref.norma} {ref.cuerpo} {ref.motivo_norma}")

print("\n2. EL CUERPO QUE LA NORMA APRUEBA, POR SU NOMBRE")
print("   (nueve de las diecisiete son aprobatorias: el articulado que se")
print("    cita no es el suyo, es el del reglamento o texto refundido)\n")

aprobatorias = 0
for clave in sorted(N.cuerpos):
    cuerpo = N.cuerpos[clave]
    if cuerpo.indice != 1:
        continue
    aprobatorias += 1
    nombre = nombre_aprobado(cuerpo.norma_titulo)
    comprobar(f"el titulo de {cuerpo.norma_id} dice que aprueba algo", bool(nombre),
              cuerpo.norma_titulo[:90])
    if not nombre:
        continue
    ref = como_se_resuelve(nombre)
    comprobar(f"«{nombre[:52]}» designa a {clave}",
              ref.norma == "cargada" and ref.cuerpo == clave,
              f"{ref.norma} {ref.cuerpo} {ref.motivo_norma}")

comprobar("hay cuerpos aprobados que comprobar", aprobatorias >= 9, aprobatorias)

print("\n3. EL NOMBRE CON EL QUE EL REGISTRO LO ETIQUETA")
print("   (es el que sale en los motivos y en la respuesta: si el verificador")
print("    nombra una norma de una manera, tiene que saber leerla)\n")

for clave in sorted(N.cuerpos):
    etiqueta = N.cuerpos[clave].etiqueta
    ref = como_se_resuelve(etiqueta)
    comprobar(f"«{etiqueta[:52]}» designa a {clave}",
              ref.norma == "cargada" and ref.cuerpo == clave,
              f"{ref.norma} {ref.cuerpo} {ref.motivo_norma}")

print("\n4. Y DE PUNTA A PUNTA: UNA CITA REAL CONTRA EL CORPUS")
print("   (nombre corto + articulo + literal, por el verificador entero)\n")

V = VF.Verificador(ix)


def literal_de(clave_cuerpo, numero):
    """Un trozo literal del articulo tal cual esta en el corpus."""
    for d in ix.docs:
        r = d.registro
        if r.get("cuerpo_clave") != clave_cuerpo:
            continue
        if str(r.get("numero") or "") != str(numero):
            continue
        texto = (r.get("versiones") or [{}])[-1].get("texto") or ""
        cuerpo = texto.split("\n", 1)[-1].strip()
        return " ".join(cuerpo.split())[:120]
    return ""


# Se prueban de punta a punta los dos casos que se caian entero: un reglamento
# aprobado por real decreto y el texto refundido. El resto de nombres queda
# comprobado arriba, que es donde estaba el defecto.
for clave, numero in (("BOE-A-2005-14803#1", 2), ("BOE-A-1993-25359#1", 1)):
    etiqueta = N.cuerpos[clave].etiqueta
    trozo = literal_de(clave, numero)
    comprobar(f"hay literal del articulo {numero} de {clave}", bool(trozo), trozo)
    if not trozo:
        continue
    informe = V.verificar_texto(
        f'La norma dispone que «{trozo}» (articulo {numero} del {etiqueta}).',
        2024)
    d = informe.dictamenes[0]
    comprobar(f"citado «{etiqueta[:40]}», el articulo {numero} queda VERIFICADO",
              d.estado == VF.VERIFICADA, f"{d.estado}: {d.motivo[:80]}")

print("\n5. LO QUE NO PUEDE AFLOJARSE")
print("   (reconocer mas nombres no es reconocer cualquiera)\n")

ajenas = [
    ("Ley Concursal", "una ley que no esta en el corpus"),
    ("Directiva 2006/112/CE", "una directiva comunitaria"),
    ("Reglamento (UE) 282/2011", "un reglamento comunitario"),
    ("Real Decreto 1234/2020", "un real decreto que no esta cargado"),
    ("Ley 12/2023", "una ley posterior al corpus"),
]
for nombre, que in ajenas:
    ref = como_se_resuelve(nombre)
    comprobar(f"{que}: «{nombre}» sale EXTERNA (= NO VERIFICABLE)",
              ref.norma == "externa", f"{ref.norma} {ref.cuerpo}")

# Una designacion que encaja con varias no se resuelve: ante la duda, nada.
for nombre, que in (("Reglamento", "nueve reglamentos cargados"),
                    ("Ley del Impuesto", "cinco leyes de impuesto")):
    ref = como_se_resuelve(nombre)
    comprobar(f"ambigua ({que}): «{nombre}» no se resuelve",
              ref.norma == "externa" and "encaja con" in ref.motivo_norma,
              f"{ref.norma} {ref.cuerpo} {ref.motivo_norma[:60]}")

print("\n6. EL DIA QUE ENTRE UNA NORMA NUEVA")
print("   (rangos que hoy no estan en el corpus: se comprueban sobre su")
print("    titulo, sin ingerir nada, porque el nombre sale del titulo)\n")

from agente_fiscal import normas as NM                # noqa: E402


class _Doc:
    """Lo minimo que el registro necesita de un documento del corpus."""

    def __init__(self, registro):
        self.registro = registro


def registro_de(titulo, cuerpos=2):
    docs = [_Doc({"norma_id": "BOE-NUEVA", "norma_titulo": titulo,
                  "cuerpo_indice": i, "cuerpo_clave": f"BOE-NUEVA#{i}",
                  "tipo": "articulo", "numero": "1", "numero_norm": "1"})
            for i in range(cuerpos)]
    return NM.Registro(docs)


# El titulo se escribe entero, como lo publica el BOE. Nada mas: de ahi tienen
# que salir las formas de nombrarla.
nuevas = [
    ("Orden HFP/417/2017, de 12 de mayo, por la que se aprueba el Reglamento "
     "del suministro inmediato de informacion.",
     "Orden HFP/417/2017", "Reglamento del suministro inmediato de informacion"),
    ("Real Decreto-ley 8/2020, de 17 de marzo, de medidas urgentes "
     "extraordinarias.", "Real Decreto-ley 8/2020", ""),
    ("Ley Organica 8/2021, de 4 de junio, de proteccion integral a la "
     "infancia.", "Ley Organica 8/2021", ""),
    ("Decreto Legislativo 2/2028, de 3 de marzo, por el que se aprueba el "
     "Texto refundido de la Ley de tributos cedidos.",
     "Decreto Legislativo 2/2028", "Texto refundido de la Ley de tributos cedidos"),
]
for titulo, oficial, aprobado in nuevas:
    reg = registro_de(titulo)
    clave, motivo = reg.resolver(oficial)
    comprobar(f"«{oficial}» se nombra sola desde su titulo",
              clave == "BOE-NUEVA#0", f"{clave} {motivo}")
    if aprobado:
        clave, motivo = reg.resolver(aprobado)
        comprobar(f"y lo que aprueba tambien: «{aprobado[:44]}»",
                  clave == "BOE-NUEVA#1", f"{clave} {motivo}")

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
