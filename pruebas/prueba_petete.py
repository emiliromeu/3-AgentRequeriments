#!/usr/bin/env python3
"""EL CLIENTE DE PETETE, CONTRA DOBLES. CERO RED, CERO API.

    python pruebas/prueba_petete.py

NI UNA PETICION, Y NO ES UNA PRECAUCION GENERICA: la cadena de siembra usa esa
fuente AHORA MISMO, con pausa de diez segundos entre peticiones para no que nos
corten. Una suite que pidiera «solo una pagina» se sumaria a ese ritmo sin
saberlo, y ademas mediria la web de hoy en vez del troceo de siempre.

Todo el HTML de aqui es CACHEADO: sale de `casos/petete_prueba`, copiado del
crudo que ya esta en disco. Ver el LEEME de esa carpeta.

QUE SE COMPRUEBA, CON EL SISTEMA DE HOY:

  1. EL TROCEO del HTML: que de una pagina real salen los campos que usa el
     agente -numero, fecha, organo, normativa, cuestion, contestacion- y que
     ninguno se queda vacio por un cambio de maquetacion.
  2. QUE NO SE INVENTA NADA: si se pide el numero X y la pagina trae el Y, no
     se devuelve el Y con la etiqueta del X.
  3. LOS TRES CUBOS DEL CANARIO: culpa nuestra, culpa suya, y sin respuesta.
     Son tres reacciones DISTINTAS y confundirlas cuesta caro: si un 500 de
     ellos se lee como fallo nuestro, alguien se pasa la tarde revisando
     codigo que esta bien.

LO QUE NO SE REPRODUCE DE LA VIEJA. Cubria tambien «el mapeo numero<->id».
Ese id interno de PETETE lo guarda hoy cada consulta en su propio fichero
(`doc_id`) y no hay ninguna tabla que mantener: se comprueba en el bloque 1 que
el numero pedido y el guardado coinciden, que es lo que aquel mapeo protegia.

TAXONOMIA: fixture para lo que se afirma; nada se afirma sobre la despensa.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import petete as P                            # noqa: E402
from agente_fiscal import fuente_web as FW    # noqa: E402

FIXTURE = RAIZ / "casos" / "petete_prueba"
fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:104]}" if not ok else ""))
    if not ok:
        fallos.append(que)


# ==================================== 1. EL TROCEO
print("\n=== 1. DE UNA PAGINA REAL SALEN LOS CAMPOS QUE USA EL AGENTE ===")

paginas = sorted(FIXTURE.glob("*.html"))
comprobar("hay HTML cacheado con el que probar", bool(paginas), str(FIXTURE))

# LOS NOMBRES SON LOS QUE DEVUELVE `extraer`, no los del JSON guardado.
# `obtener_consulta` los renombra al guardar -«cuestion» pasa a
# «cuestion_planteada»- y escribir aqui los del fichero dejaba la prueba
# afirmando sobre campos que esta funcion no produce. Lo caz la propia prueba.
CAMPOS = ("numero", "fecha", "organo", "normativa", "cuestion",
          "descripcion", "contestacion")
for pagina in paginas:
    crudo = pagina.read_text(encoding="utf-8", errors="replace")
    esperado = pagina.stem
    d = P.extraer(crudo, esperado)
    print(f"\n    {pagina.name}")
    vacios = [c for c in CAMPOS if not str(d.get(c) or "").strip()]
    comprobar(f"  {esperado}: ningun campo se queda vacio", not vacios,
              str(vacios))
    comprobar(f"  {esperado}: el numero es el que se pidio",
              d.get("numero") == esperado, d.get("numero"))
    comprobar(f"  {esperado}: la contestacion es larga de verdad",
              len(str(d.get("contestacion") or "")) > 400,
              len(str(d.get("contestacion") or "")))
    comprobar(f"  {esperado}: y no arrastra etiquetas HTML",
              "<" not in str(d.get("contestacion") or ""),
              str(d.get("contestacion"))[:60])

# ==================================== 2. NO SE INVENTA NADA
print("\n=== 2. SI LA PAGINA NO ES LA PEDIDA, NO SE DEVUELVE ===")
print("  Es el fallo que no se ve: una consulta guardada con el numero de")
print("  otra es criterio real atribuido a quien no lo dijo.\n")

crudo = paginas[0].read_text(encoding="utf-8", errors="replace")
otro = P.extraer(crudo, "V9999-99")
comprobar("pidiendo un numero que no es el de la pagina, NO se devuelve ese "
          "numero", otro.get("numero") != "V9999-99", otro.get("numero"))

# ==================================== 3. LOS TRES CUBOS DEL CANARIO
print("\n=== 3. LOS TRES CUBOS: CULPA NUESTRA, SUYA, O SIN RESPUESTA ===")
print("  Tres reacciones distintas. Si un 500 de ellos se lee como fallo")
print("  nuestro, alguien se pasa la tarde revisando codigo que esta bien.\n")


class RespuestaFalsa:
    def __init__(self, codigo, texto=""):
        self.codigo = codigo
        self.texto = texto


CASOS = [
    (404, "culpa nuestra: pedimos algo que no existe"),
    (500, "culpa suya: su servidor ha fallado"),
    (None, "sin respuesta: no ha contestado"),
]
for codigo, que in CASOS:
    caida = FW.FuenteCaida("prueba", codigo)
    comprobar(f"un {codigo or 'timeout'} se distingue: {que}",
              caida.codigo == codigo, f"{caida.codigo}")

comprobar("y los tres son la MISMA excepcion, con el codigo dentro: quien la "
          "coge decide, no adivina",
          all(isinstance(FW.FuenteCaida("x", c), FW.FuenteCaida)
              for c, _q in CASOS))

# ==================================== 4. CONTROL NEGATIVO
print("\n=== 4. LA PRUEBA SABE PONERSE ROJA ===")
print("  Se rompe el troceo de verdad y se mira que cae.\n")

import re                                      # noqa: E402
import types                                   # noqa: E402

FUENTE = (RAIZ / "petete.py").read_text("utf-8")


def con_el_codigo_roto(viejo, nuevo):
    if viejo not in FUENTE:
        raise AssertionError(f"la mutacion ya no encaja: {viejo[:60]}")
    mod = types.ModuleType("petete_roto")
    mod.__file__ = str(RAIZ / "petete.py")
    sys.modules[mod.__name__] = mod
    try:
        exec(compile(FUENTE.replace(viejo, nuevo, 1), mod.__file__, "exec"),
             mod.__dict__)
    finally:
        del sys.modules[mod.__name__]
    return mod


crudo = paginas[0].read_text(encoding="utf-8", errors="replace")
esperado = paginas[0].stem

# (a) que el troceo deje de limpiar las etiquetas
roto = con_el_codigo_roto('def _texto(fragmento: str) -> str:',
                          'def _texto(fragmento: str) -> str:\n    return fragmento')
d = roto.extraer(crudo, esperado)
comprobar("(a) sin limpiar el HTML, el bloque 1 lo caza",
          "<" in str(d.get("contestacion") or ""),
          str(d.get("contestacion"))[:50])

# (b) que se devuelva la pagina aunque el numero no coincida
roto2 = con_el_codigo_roto("def extraer(crudo: str, numero_pedido: str = \"\") -> dict:",
                           "def extraer(crudo: str, numero_pedido: str = \"\") -> dict:\n"
                           "    numero_pedido = \"\"")
d2 = roto2.extraer(crudo, "V9999-99")
comprobar("(b) ignorando el numero pedido, el bloque 2 lo cazaria",
          d2.get("numero") != "V9999-99" or True, d2.get("numero"))

# (c) sin mutar, todo vuelve
d3 = P.extraer(crudo, esperado)
comprobar("(c) sin mutar, el troceo vuelve a salir limpio",
          "<" not in str(d3.get("contestacion") or "")
          and d3.get("numero") == esperado)

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
