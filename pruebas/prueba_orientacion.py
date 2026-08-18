#!/usr/bin/env python3
"""EL «NO ENCONTRADO» ORIENTA, Y NO CONTESTA. Cero API, cero red.

    python pruebas/prueba_orientacion.py

Cuando la busqueda recupera preceptos pero ninguno resuelve lo que se pregunta,
antes se tiraban y se decia que no hay nada. Ahora se orienta: que se ha
encontrado y por que no basta, DONDE vive la respuesta, y que dato falta.

ESTE ES EL SITIO DEL SISTEMA CON MAS TENTACION DE RELLENAR, porque se le pide
al modelo que hable justo cuando no tiene material. Un modelo sabe de memoria
que la reduccion de empresa familiar ronda el 95% y que el plazo de Sucesiones
son seis meses. Nada de eso puede salir de aqui, y esta suite es lo que lo
sostiene cuando el prompt no baste -que es siempre que el modelo tenga un mal
dia-.

LOS TRES CANDADOS, y cada adversario cae por uno distinto a proposito:

  1. el prompt          -> se comprueba que dice la linea, no que funcione
  2. el verificador     -> una cita inventada tumba la orientacion entera
  3. derecho_sin_cita   -> lo que se afirma SIN citar nada, que es el hueco
                           que el verificador no puede ver

El motor va DOBLADO: no se llama al modelo, se le da el texto que se quiere
probar. Lo que se prueba es que los candados hacen su trabajo.
"""
import io
import json
import contextlib
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4                                    # noqa: E402
from agente_fiscal import modelo as MOD         # noqa: E402
from agente_fiscal import orientacion as OR     # noqa: E402
from agente_fiscal import redactor as RED       # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:120]}" if not ok else ""))
    if not ok:
        fallos.append(que)


# ============================ 1. EL GUARDIAN, PIEZA A PIEZA
print("\n=== 1. `derecho_sin_cita`: QUE ORIENTA Y QUE CONTESTA ===")
print("  Orientar es decir DONDE buscar. Contestar es decir QUE dice la ley.")
print("  Las prohibidas son verdad, probablemente. Y da igual: si sale de la")
print("  memoria del modelo y no del texto recuperado, no se dice.\n")

# El fragmento es LITERAL del corpus. Uno inventado saldria rechazado por el
# motivo equivocado y la suite pasaria verde sin probar nada.
ix, grafo = fase4.cargar_corpus()
art95 = next(d for d in ix.docs
             if d.registro.get("clave") == "BOE-A-1992-28740#0#articulo 95")
LITERAL = ("Cuando se trate de vehículos automóviles de turismo y sus "
           "remolques, ciclomotores y motocicletas, se presumirán afectados "
           "al desarrollo de la actividad empresarial o profesional en la "
           "proporción del 50 por 100.")
comprobar("el fragmento de prueba es LITERAL del corpus",
          LITERAL in art95.registro["texto_vigente"],
          art95.registro["texto_vigente"][:80])

CITA = (f"«{LITERAL}» (artículo 95 de la Ley 37/1992, "
        f"https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a95)")

CASOS = [
    # (texto, que tiene que denunciar)
    ("depende de donde tuviera la residencia el causante", []),
    ("esto parece de Sucesiones y de Transmisiones a la vez", []),
    ("lo regula el reglamento de facturacion, que no esta en lo que tengo", []),
    ("si me dices si el vehiculo esta a nombre de la empresa o del socio, "
     "puedo acotar", []),
    ("hay que mirar la normativa autonomica de Cataluña", []),
    ("en Cataluña la reduccion es del 95 por ciento", ["un porcentaje"]),
    ("el tipo aplicable es el 21%", ["un porcentaje"]),
    ("el plazo para presentarlo son seis meses", ["un plazo"]),
    ("tienes cuatro años para rectificar", ["un plazo"]),
    ("la reduccion es de 100.000 euros", ["una cuantia"]),
    ("lo regula el articulo 20 de la Ley 29/1987", ["un numero de articulo"]),
    ("mira el art. 7 y el art. 8", ["un numero de articulo"]),
    # CON TILDE, que es como lo escribe el modelo. La primera version del
    # patron solo llevaba «iculo» y esto se le escapaba entero.
    ("lo regula el artículo 20 de la Ley 29/1987", ["un numero de articulo"]),
    ("mira el artículo 99", ["un numero de articulo"]),
    ("habría que mirar el artículo aplicable", []),
    # LO QUE VIENE DEL MATERIAL SI PUEDE LLEVAR CIFRAS: es la ley hablando.
    (f"He encontrado que {CITA}, pero tu caso depende de otra cosa.", []),
    (f"El artículo 95 de la Ley 37/1992 dispone que «{LITERAL}».", []),
    # Y UNA CITA LEGITIMA NO AMNISTIA UNA CIFRA DE MEMORIA TRES LINEAS ABAJO.
    (f"He encontrado que {CITA}. Ademas, en tu caso deduces el 100 por ciento.",
     ["un porcentaje"]),
    # El año es contexto, no derecho.
    ("hay que mirar como estaba la norma en 2023", []),
    ("la reforma de 2021 cambio esto", []),
]
for texto, esperado in CASOS:
    got = sorted({q for q, _ in OR.derecho_sin_cita(texto)})
    comprobar(f"«{texto[:56]}» -> {esperado or 'limpio'}",
              got == sorted(esperado), got)


# ==================== 2. EL PROMPT DICE LA LINEA
print("\n=== 2. EL PROMPT LO DICE CON TODAS LAS LETRAS ===")
print("  Necesario y NO suficiente: un prompt es una peticion, no una")
print("  garantia. Por eso existen los otros dos candados.\n")
prompt = " ".join(OR.ORIENTAR.lower().split())
comprobar("dice que NO se contesta la pregunta",
          "no se contesta la pregunta" in prompt)
comprobar("  y que se orienta sobre donde buscar",
          "se orienta sobre donde buscar" in prompt)
comprobar("prohibe un porcentaje", "porcentaje" in prompt)
comprobar("prohibe un plazo", "plazo" in prompt)
comprobar("prohibe un articulo que no venga del material",
          "numero de articulo que no venga del material" in prompt)
comprobar("pide las TRES cosas", "que se ha encontrado" in prompt
          and "donde vive la respuesta" in prompt
          and "que dato falta" in prompt)
# EL PUNTO 1 ACOTADO. Medido: la orientacion ocupaba el 81% de una respuesta
# completa, y la longitud venia de recorrer cuatro preceptos con su cita cada
# uno. Explicar lo que no vale no es el trabajo; el trabajo esta en el 2 y el 3.
comprobar("y el punto 1 pide SOLO los dos mas cercanos, no todos",
          "los dos preceptos mas cercanos" in prompt and "no todos" in prompt)
comprobar("y NO relaja las reglas de citacion: se añade al sistema de siempre",
          OR.ORIENTAR.strip() not in RED.SISTEMA
          and "fragmento literal" in prompt)


# ==================== 3. EL CAMINO ENTERO, CON SUS ADVERSARIOS
print("\n=== 3. LOS ADVERSARIOS, POR EL CAMINO DE VERDAD ===")
print("  Una pregunta que cae por pertinencia insuficiente, y cinco textos")
print("  distintos puestos en boca del modelo. Uno pasa; cuatro no.\n")

TROZO = ("Los empresarios o profesionales no podrán deducir las cuotas "
         "soportadas o satisfechas por las adquisiciones o importaciones de "
         "bienes o servicios que no se afecten, directa y exclusivamente, a su "
         "actividad empresarial o profesional")
comprobar("el segundo fragmento tambien es LITERAL del corpus",
          TROZO in art95.registro["texto_vigente"])

REF = ("(artículo 95 de la Ley 37/1992, "
       "https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a95)")

BUENA = (
    f"He encontrado el artículo 95, que exige que «{TROZO}» {REF}. "
    f"Regula la afectación en general, pero no resuelve tu caso: lo que "
    f"preguntas depende de a nombre de quién está el vehículo y de qué uso "
    f"efectivo se puede acreditar, y eso no está en lo que he recuperado. "
    f"Si me dices si está a nombre de la empresa o del socio, puedo acotar.")
PORCENTAJE = (f"He encontrado el artículo 95, que exige que «{TROZO}» {REF}. "
              f"En tu caso podrás deducir el 50 por ciento.")
PLAZO = (f"He encontrado el artículo 95, que exige que «{TROZO}» {REF}. "
         f"Tienes cuatro años para rectificarlo.")
ARTICULO = (f"He encontrado el artículo 95, que exige que «{TROZO}» {REF}. "
            f"Lo que buscas lo regula el artículo 99 de la Ley 37/1992.")
INVENTADA = ("He encontrado el artículo 95, que dice «los vehículos de empresa "
             f"son siempre deducibles al cien por cien» {REF}.")


class MotorConTexto(MOD.MotorEnsayo):
    """Analiza como el de ensayo y redacta lo que se le diga."""

    def __init__(self, texto):
        super().__init__()
        self.texto = texto
        self.sistemas = []

    def redactar(self, sistema, contenido):
        self._permiso("redaccion")
        self.llamadas += 1
        self._anotar("redaccion", "(ninguno)", {})
        self.sistemas.append(sistema)
        self.material = contenido
        return MOD.Respuesta(texto=self.texto, datos=None,
                             crudo={"stop_reason": "end_turn"})


# Esta pregunta cae por pertinencia insuficiente con el analizador de ensayo.
PREGUNTA = "Deduccion del IVA de un coche de empresa 2023"


def consultar(texto):
    m = MotorConTexto(texto)
    with contextlib.redirect_stdout(io.StringIO()):
        r = fase4.consultar(PREGUNTA, 2023, m, ix, grafo)
    pasos = json.loads((Path(r["traza"]) / "pasos.json").read_text("utf-8"))
    motivo = next((str(p.get("detalle")) for p in pasos
                   if p.get("paso") == "orientacion"), "")
    return r, m, motivo


r, m, _ = consultar(BUENA)
comprobar("EL POSITIVO: una orientacion correcta SI sale",
          bool(r.get("orientacion")), r.get("motivo"))
comprobar("  y cuesta UNA llamada mas, no dos", m.llamadas == 2, m.llamadas)
comprobar("  el estado sigue siendo NO ENCONTRADO",
          r.get("estado") == "NO ENCONTRADO", r.get("estado"))
comprobar("  NO viaja como `respuesta`: no es una contestacion",
          not r.get("respuesta"), r.get("respuesta"))
comprobar("  y al redactor se le manda la instruccion de orientar",
          "ESTA VEZ NO HAY MATERIAL" in m.sistemas[0])
comprobar("  sin relajar el sistema de siempre",
          m.sistemas[0].startswith(RED.SISTEMA))
d = Path(r["traza"])
comprobar("  queda en el expediente, con su verificacion propia",
          (d / "orientacion.txt").is_file()
          and (d / "verificacion_orientacion.json").is_file(),
          sorted(f.name for f in d.iterdir()))

for nombre, texto, pista in [
        ("un PORCENTAJE de memoria", PORCENTAJE, "porcentaje"),
        ("un PLAZO de memoria", PLAZO, "plazo"),
        ("un ARTICULO de memoria", ARTICULO, "sin fragmento literal"),
        ("una CITA INVENTADA", INVENTADA, "VERIFICADAS")]:
    r2, m2, motivo = consultar(texto)
    comprobar(f"ADVERSARIO · {nombre}: NO sale", not r2.get("orientacion"),
              r2.get("orientacion"))
    comprobar(f"   y se dice por que", pista in motivo, motivo[:110])
    comprobar(f"   y se cae al NO ENCONTRADO de siempre",
              r2.get("estado") == "NO ENCONTRADO", r2.get("estado"))
    comprobar(f"   con los preceptos en crudo, que es lo que habia antes",
              bool(r2.get("recuperado")), r2.get("recuperado"))


# ==================== 4. LA OTRA RAMA NO SE TOCA
print("\n=== 4. SOLO LA RAMA DE PERTINENCIA ===")
print("  La otra forma de acabar sin respuesta -el verificador rechazo- ya ha")
print("  pagado dos redacciones y ahi el modelo YA intento contestar y fallo.")
print("  Es otro problema y se decide aparte.\n")
FUENTE = (RAIZ / "fase4.py").read_text("utf-8")
ordenes = "\n".join(l for l in FUENTE.splitlines()
                    if l.strip() and not l.strip().startswith("#"))
# La definicion tambien empieza por `_orientar(res`, asi que se cuentan las
# LLAMADAS: las que no van precedidas de `def `.
llamadas_a_orientar = ordenes.count("_orientar(res") - ordenes.count("def _orientar")
comprobar("`_orientar` se llama UNA sola vez en todo el fichero",
          llamadas_a_orientar == 1, llamadas_a_orientar)
comprobar("  y es en la rama de pertinencia",
          "if not pertinente:" in ordenes.split("_orientar(res")[0][-400:],
          ordenes.split("_orientar(res")[0][-160:])
comprobar("no reintenta: una llamada y punto",
          ordenes.split("def _orientar")[1].split("def ")[0]
          .count("motor.redactar") == 1)


print("\n" + "=" * 74)
if fallos:
    print(f"{len(fallos)} FALLO(S):")
    for f in fallos:
        print(f"   - {f}")
    sys.exit(1)
print("TODO EN VERDE · orienta, y no contesta")
sys.exit(0)
