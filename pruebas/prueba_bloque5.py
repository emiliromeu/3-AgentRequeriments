#!/usr/bin/env python3
"""EL BLOQUE 5 DEL BANCO CORRE ENTERO. Cero red, cero API.

    python pruebas/prueba_bloque5.py

POR QUE EXISTE. El bloque 5 es la unica comprobacion que mira el sistema de
punta a punta -analizador incluido- y NUNCA SE HA EJECUTADO, porque hace falta
el modelo real y eso cuesta. Un trozo de codigo que nadie ha corrido no es
codigo probado: es codigo escrito.

Y ESTABA ROTO. `bloque_5` y `casos_en_rojo` usaban `grafo` sin recibirlo
-todos sus vecinos lo llevan en la firma, estos dos se quedaron sin el-, asi
que reventaban con un NameError.

DONDE CAE, QUE ES LO QUE IMPORTA PARA EL BOLSILLO: en `casos_en_rojo`, que es
la PRIMERA linea del bloque, antes de pedirle nada al modelo. O sea que no se
habria gastado un euro; simplemente el bloque no habria llegado a correr nunca.
-Lo escribi al reves la primera vez, dando por hecho que la llamada iba antes.
Lo corrigio esta misma prueba, que es para lo que esta.-

COMO SE PRUEBA SIN GASTAR. El bloque llama al modelo por un unico sitio
-`motor.analizar`- y despues es todo determinista: validar el JSON, recuperar,
mirar el puesto. Aqui se le pasa un motor de mentira que dice ser real y
devuelve un analisis valido escrito a mano. El camino que se recorre es el
MISMO, incluida la linea que fallaba.

LO QUE NO PRUEBA, y conviene tenerlo claro: si el analizador de verdad propone
buenos terminos. Eso solo lo dice el modelo real. Esto prueba que cuando los
proponga, el bloque sepa medirlo en vez de romperse.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import banco                                    # noqa: E402
import fase4                                    # noqa: E402
from agente_fiscal import analizador as AN      # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:112]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix, grafo = fase4.cargar_corpus()
casos = banco.leer_casos(banco.CASOS)
rojos = banco.casos_en_rojo(ix, grafo, casos)
print(f"\n  casos del banco: {len(casos)} · en rojo ahora mismo: {len(rojos)}")

# El impuesto se toma de un caso real: el enum del esquema sale del corpus, asi
# que escribir un codigo a mano seria otra invencion mas.
IMPUESTO = (rojos[0].get("impuesto")
            or ix.normas.impuesto_de_cuerpo(rojos[0]["cuerpo"])) if rojos else ""


class MotorFalso:
    """Dice ser real y no llama a nadie. Cuenta las veces que se le pide."""

    es_modelo_real = True

    def __init__(self, terminos):
        self.terminos = terminos
        self.veces = 0
        self.consultas = 0

    def empezar_consulta(self):
        # El bloque 5 tiene que abrir consulta por cada rojo: el tope de
        # llamadas del motor se cuenta por consulta y son quince con un solo
        # motor. Si el doble no lo tuviera, la suite pasaria verde sobre un
        # motor que no se parece al de verdad.
        self.consultas += 1

    def analizar(self, _sistema, consulta, _esquema):
        self.veces += 1
        import types
        return types.SimpleNamespace(datos=analisis_de_mentira(self.terminos))


# LA FORMA SALE DEL ESQUEMA DE VERDAD, NO DE MI CABEZA. La primera version de
# esto llevaba «resumen» y «naturaleza: sustantiva», inventados los dos, y los
# once casos salieron FALLO por JSON invalido. Un doble que no pasa la
# validacion real no prueba el bloque: prueba la validacion.
def analisis_de_mentira(terminos: list) -> dict:
    return {
        "impuesto": IMPUESTO,
        "naturaleza": AN.FONDO,
        "ejercicio": 2023,
        "ejercicio_fundamento": "lo dice la propia pregunta",
        "articulos_sospechados": [],
        "terminos_busqueda": terminos,
        "resumen_duda": "prueba, no sale de ningun modelo",
    }


# ==================================== 1. EL BLOQUE CORRE ENTERO
print("\n=== 1. EL BLOQUE 5 LLEGA AL FINAL SIN REVENTAR ===")
print("  Es lo que no se sabia: nunca se habia ejecutado esta rama.\n")

reg = banco.Registro()
motor = MotorFalso(["transmision", "patrimoniales", "onerosas", "tipo"])

if not rojos:
    comprobar("(omitido) no hay rojos: el bloque no tiene nada que medir", True)
else:
    try:
        banco.bloque_5(reg, ix, grafo, motor, casos)
        comprobar("el bloque 5 corre de principio a fin", True)
    except NameError as e:
        comprobar("el bloque 5 corre de principio a fin", False,
                  f"NameError: {e}  <- la firma no recibe lo que usa")
    except Exception as e:                       # noqa: BLE001
        comprobar("el bloque 5 corre de principio a fin", False,
                  f"{type(e).__name__}: {e}")

    comprobar("pide UNA llamada por caso en rojo, ni una mas",
              motor.veces == len(rojos), f"{motor.veces} para {len(rojos)}")
    anotadas = [f for f in reg.pruebas if f["bloque"] == "5"]
    comprobar("abre una consulta por cada rojo: el tope es POR CONSULTA y "
              "son 15 con un solo motor",
              motor.consultas == len(rojos), motor.consultas)
    comprobar("y anota un resultado por cada rojo",
              len(anotadas) == len(rojos), f"{len(anotadas)}")
    comprobar("ninguno queda sin veredicto",
              all(a["veredicto"] for a in anotadas))

# ==================================== 2. CON MOTOR DE ENSAYO, OMITIDO
print("\n=== 2. SIN MODELO REAL SE OMITE, NO SE DA POR BUENO ===")


class MotorEnsayo:
    es_modelo_real = False

    def empezar_consulta(self):
        pass

    def analizar(self, *a, **k):
        raise AssertionError("no deberia llamarse con motor de ensayo")


reg2 = banco.Registro()
banco.bloque_5(reg2, ix, grafo, MotorEnsayo(), casos)
anot2 = [f for f in reg2.pruebas if f["bloque"] == "5"]
comprobar("con --motor ensayo todo sale OMITIDO",
          all(a["veredicto"] == banco.OMITIDO for a in anot2) if anot2 else True,
          str([a["veredicto"] for a in anot2][:3]))
comprobar("  y NUNCA verde: dar por buena una prueba no ejecutada es lo que "
          "este proyecto evita",
          not any(a["veredicto"] == banco.VERDE for a in anot2))

# ==================================== 3. LA CUENTA DE LLAMADAS
print("\n=== 3. LO QUE VA A COSTAR, ANTES DE GASTARLO ===")
mn, mx = banco.llamadas_previstas({"5"}, len(casos), len(rojos))
print(f"    con {len(rojos)} rojos: entre {mn} y {mx} llamadas")
comprobar("el minimo es una llamada por rojo", mn == len(rojos), mn)
comprobar("el maximo son dos (si el JSON sale mal a la primera)",
          mx == len(rojos) * 2, mx)
comprobar("y el bloque 5 NO redacta: no se cuenta ninguna redaccion",
          mx <= len(rojos) * 2, mx)

# ==================================== 4. CONTROL NEGATIVO
print("\n=== 4. LA PRUEBA SABE PONERSE ROJA ===")
print("  Se le quita `grafo` a la firma, que es exactamente como estaba, y")
print("  se mira si el bloque 1 lo caza.\n")

import types                                     # noqa: E402

FUENTE = (RAIZ / "banco.py").read_text("utf-8")
VIEJO = "def bloque_5(reg: Registro, ix, grafo, motor, casos) -> None:"
if VIEJO not in FUENTE:
    comprobar("la mutacion encaja", False, VIEJO)
else:
    mod = types.ModuleType("banco_roto")
    mod.__file__ = str(RAIZ / "banco.py")
    sys.modules[mod.__name__] = mod
    try:
        exec(compile(FUENTE.replace(
            VIEJO, "def bloque_5(reg: Registro, ix, motor, casos) -> None:", 1),
            mod.__file__, "exec"), mod.__dict__)
    finally:
        del sys.modules[mod.__name__]
    if not rojos:
        comprobar("(omitido) sin rojos la mutacion no se puede ver", True)
    else:
        m2 = MotorFalso(["transmision", "patrimoniales"])
        try:
            mod.bloque_5(mod.Registro(), ix, m2, casos)
            comprobar("(a) sin `grafo` en la firma, el bloque 1 lo caza", False,
                      "no fallo: la mutacion ya no reproduce el defecto")
        except (NameError, TypeError) as e:
            comprobar("(a) sin `grafo` en la firma, el bloque 1 lo caza", True)
            print(f"       ({type(e).__name__}: {str(e)[:70]})")
        # Y DONDE CAE. Revienta en `casos_en_rojo`, que es la primera linea
        # del bloque: NO se llega a pedir nada al modelo. Importa afirmarlo,
        # porque la version anterior de este comentario decia lo contrario y
        # habria dejado creer que el arreglo salvaba dinero.
        comprobar("  y cae ANTES de pedirle nada al modelo: no se gasta nada",
                  m2.veces == 0, m2.veces)

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
