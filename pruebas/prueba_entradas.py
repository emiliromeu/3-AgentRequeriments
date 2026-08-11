#!/usr/bin/env python3
"""LO QUE ESCRIBE UNA PERSONA DE VERDAD. Cero red, cero API.

Hasta ahora esto solo lo habiamos usado nosotros, y siempre con preguntas bien
escritas. En el departamento van a escribir en catalan, van a pegar un
requerimiento entero, van a poner «23» en el año y van a preguntar por el IBI.

    python pruebas/prueba_entradas.py

LO QUE NO SE PUEDE PERDER, y por que:

  · EL AÑO NO SE PUEDE COLAR MAL INTERPRETADO. Es el fallo mas silencioso del
    sistema: una consulta de 2023 contestada con la ley de hoy sale impecable,
    con sus citas y sus enlaces, y esta mal. Medido antes de esta suite: «abc»
    salia con CRITERIO CLARO y ejercicio 'abc'.
  · UNA PREGUNTA DE 3.000 PALABRAS NO PUEDE COSTAR CUATRO CENTIMOS DE ANALISIS
    antes de que nadie decida nada.
  · UN TEMA QUE NO ESTA sale por la puerta de materia, con su mensaje, y nunca
    con una respuesta inventada ni con una traza de Python.
"""
import contextlib
import io
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4  # noqa: E402
from agente_fiscal import analizador as AN  # noqa: E402
from agente_fiscal import modelo as MOD  # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:96]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix, grafo = fase4.cargar_corpus()
print(f"corpus: {len(ix.docs)} preceptos · {len(ix.normas.cuerpos)} cuerpos")
print(f"impuestos: {', '.join(sorted(ix.normas.impuestos()))}")


def consultar(pregunta, ejercicio=2023, impuesto=None):
    """Una consulta con el motor de ensayo. Devuelve (res, salida, llamadas)."""
    motor = MOD.crear_motor("ensayo")
    if impuesto:
        original = motor.analizar

        def con_impuesto(sistema, preg, esquema):
            r = original(sistema, preg, esquema)
            r.datos["impuesto"] = impuesto
            return r

        motor.analizar = con_impuesto
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        res = fase4.consultar(pregunta, ejercicio, motor, ix, grafo,
                              con_criterio=False)
    return res, buf.getvalue(), motor.llamadas


# ===================================================== 0. CATALAN
print("\n=== 0. CATALAN: LA RESPUESTA EN CATALAN, LAS CITAS EN CASTELLANO ===")
print("  Es una gestoria del Penedes. Alguien va a escribir «un client no em")
print("  paga la factura», y va a ser lo primero que pase, no lo raro.")
print()
print("  LO QUE SE DECIDIO, y aqui queda escrito:")
print("    · la respuesta va en el idioma de la pregunta;")
print("    · el texto citado NO se traduce jamas: es el de la ley;")
print("    · la referencia tampoco -«articulo 80 de la Ley 37/1992» entero en")
print("      castellano-, porque es el nombre oficial del precepto, el que se")
print("      escribe a la Agencia Tributaria y el que se busca en el BOE.")
print()
print("  No se llama al modelo aqui: se comprueba contra el borrador REAL que")
print("  escribio el 11/08/2026 con el modelo de verdad, guardado en")
print("  casos/borradores/. Es una medida, no un ejemplo escrito por nadie.")
print()

from agente_fiscal import verificador as VF  # noqa: E402

CATALAN = (RAIZ / "casos" / "borradores" / "catalan_20260811.txt")
borrador = CATALAN.read_text(encoding="utf-8")
comprobar("el borrador real esta en el repositorio", CATALAN.is_file())
comprobar("la respuesta salio en catalan",
          "s'ha" in borrador or "termini" in borrador or "crèdit" in borrador)
comprobar("y el texto citado NO se tradujo: sigue en castellano",
          "Que haya transcurrido un año desde el devengo" in borrador)
informe = VF.Verificador(ix).verificar_texto(borrador, 2023, exigir_norma=True)
# En la PROSA, «la Llei» en catalan esta bien: es como se habla. Lo que no
# puede traducirse es la REFERENCIA, que es el nombre oficial del precepto.
refs = [d.referencia_citada for d in informe.dictamenes]
comprobar("el nombre de la norma no se tradujo en NINGUNA referencia",
          not any("Llei" in (r or "") or "Reglament " in (r or "") for r in refs),
          refs)
buenas = [d for d in informe.dictamenes if d.estado == "VERIFICADA"]
malas = [d for d in informe.dictamenes if d.estado != "VERIFICADA"]
print(f"    {len(buenas)} de {len(informe.dictamenes)} citas verifican")
comprobar("las citas a la ley se leen aunque digan «article»",
          all(d.estado == "VERIFICADA" for d in informe.dictamenes
              if d.literal.strip().startswith(("Que ", "Cuando ", "La modific"))),
          [d.motivo[:60] for d in malas])
comprobar("ninguna se cae por «sin referencia»",
          not any("sin referencia" in d.motivo for d in informe.dictamenes),
          [d.motivo[:60] for d in malas])
comprobar("ni una sola cita quedo traducida al catalan",
          not any("d'un any" in d.literal and d.estado == "VERIFICADA"
                  for d in informe.dictamenes))

# ===================================================== 1. EL AÑO
print("\n=== 1. EL AÑO: NINGUNO SE CUELA MAL INTERPRETADO ===")
print("  Cada uno se acepta o se rechaza. Lo que no puede pasar es que entre")
print("  y se conteste con la ley de otro ejercicio.\n")

VALIDOS = (2023, "2023", " 2023 ")
INVALIDOS = {
    "": "vacio",
    "   ": "solo espacios",
    "23": "dos digitos: podria ser 1923 o 2023",
    "2.023": "con punto de millar",
    "ejercicio 2023": "con la palabra delante",
    "2023-2024": "dos ejercicios, dos redacciones de la ley",
    "1985": "anterior a la Ley del IVA",
    "abc": "no es un numero",
    "20233": "cinco digitos",
}
for crudo in VALIDOS:
    año, motivo = AN.leer_ejercicio(crudo)
    comprobar(f"«{crudo}» se acepta como {año}", año == 2023, f"{año!r} {motivo}")
for crudo, que in INVALIDOS.items():
    año, motivo = AN.leer_ejercicio(crudo)
    comprobar(f"«{crudo}» se rechaza ({que})", año is None, f"lo acepto como {año!r}")
    comprobar(f"  y lo dice en cristiano, no con un codigo",
              len(motivo) > 25 and "Error" not in motivo and "None" not in motivo,
              motivo)

print("\n  Y DE PUNTA A PUNTA, que es donde importa:")
for crudo in INVALIDOS:
    res, salida, llamadas = consultar("deduccion del IVA de un turismo", crudo)
    comprobar(f"«{crudo}» NO llega a contestarse", res["codigo"] != 0,
              f"codigo {res['codigo']}, estado {res['estado']}")
    comprobar(f"  y no se gasta el modelo con «{crudo}»", llamadas <= 1,
              f"{llamadas} llamadas")
res, _s, _l = consultar("deduccion del IVA de un turismo", 2023)
comprobar("y un año bueno sigue contestando", res["codigo"] == 0, res["estado"])

# ===================================================== 2. LA PREGUNTA
print("\n=== 2. LA PREGUNTA, COMO LA ESCRIBE LA GENTE ===")

LARGA = ("Le comunico que en relacion con el requerimiento de fecha 3 de marzo "
         "sobre las facturas emitidas y recibidas del ejercicio 2023 ") * 120
print(f"  el requerimiento pegado son {len(LARGA):,} caracteres, "
      f"{len(LARGA.split()):,} palabras\n")

res, salida, llamadas = consultar(LARGA)
comprobar("un requerimiento entero pegado NO se contesta", res["codigo"] != 0,
          f"codigo {res['codigo']}")
comprobar("Y NO SE PAGA NI UNA LLAMADA por el", llamadas == 0,
          f"{llamadas} llamadas al modelo")
comprobar("se dice cuanto mide y cuanto cabe",
          f"{fase4.TOPE_PREGUNTA:,}" in (res.get("motivo") or "")
          and f"{len(LARGA):,}" in (res.get("motivo") or ""),
          res.get("motivo"))
comprobar("y se dice que hay que hacer, no solo que esta mal",
          "resume" in (res.get("motivo") or "").lower(), res.get("motivo"))
comprobar("hay tope de longitud declarado", fase4.TOPE_PREGUNTA > 0)
comprobar("y una pregunta larga PERO razonable pasa",
          consultar("Un cliente no me paga una factura de 2023 con IVA "
                    "repercutido de 2.100 euros. Le he mandado dos burofaxes "
                    "y no contesta. Quiero saber si puedo recuperar el IVA "
                    "que ya ingresé y que plazos tengo.")[0]["codigo"] == 0)

print("\n  SIN PREGUNTA. Medido antes de esta suite: una caja vacia gastaba DOS")
print("  llamadas al modelo para acabar diciendo que no sabia de que impuesto")
print("  era -que ademas es falso: no habia pregunta-.\n")
for vacia, que in {"": "vacia", "   \n\t  ": "espacios y saltos",
                   "¿?  ...  --": "solo signos"}.items():
    res, _s, llamadas = consultar(vacia)
    comprobar(f"«{que}» se para", res["codigo"] == 3,
              f"codigo {res['codigo']}, estado {res['estado']}")
    comprobar(f"  «{que}» sin gastar NI UNA llamada", llamadas == 0,
              f"{llamadas} llamadas")
    comprobar(f"  «{que}» y el motivo habla de la pregunta, no del impuesto",
              "pregunta" in (res.get("motivo") or "")
              and "impuesto" not in (res.get("motivo") or ""),
              res.get("motivo"))

print("\n  PEGADO DE UN PDF. Una palabra partida en dos por el renglon deja al")
print("  buscador con trozos que no son palabras de nada.\n")
from agente_fiscal import texto as T  # noqa: E402
comprobar("«deduc-\\ncion» se recompone",
          T.unir_cortes_de_linea("la deduc-\ncion del IVA") == "la deduccion del IVA",
          T.unir_cortes_de_linea("la deduc-\ncion del IVA"))
comprobar("y con espacios al principio del renglon siguiente tambien",
          T.unir_cortes_de_linea("un co-\n   che") == "un coche")
comprobar("un guion de verdad NO se toca (mayuscula detras)",
          T.unir_cortes_de_linea("Real Decreto-\nLey 3/2023") ==
          "Real Decreto-\nLey 3/2023")
comprobar("ni un guion con espacios alrededor",
          T.unir_cortes_de_linea("IVA -\ndeduccion") == "IVA -\ndeduccion")
PDF = "deduc-\ncion del IVA de un co-\nche de empresa"
comprobar("y de punta a punta el buscador ve las palabras enteras",
          "deduccion" in T.palabras_exactas(T.unir_cortes_de_linea(PDF))
          and "coche" in T.palabras_exactas(T.unir_cortes_de_linea(PDF)),
          T.palabras_exactas(T.unir_cortes_de_linea(PDF)))
comprobar("y antes NO las veia (que es el fallo que esto arregla)",
          "deduccion" not in T.palabras_exactas(PDF))

RAROS = {
    "prorrata": "una palabra suelta",
    "deducion iva coche": "con faltas y sin tildes",
    "deduc-\ncion del IVA de un co-\nche": "pegado de un PDF, con guiones",
    "¿puedo deducir el IVA?\n\n¿Y como se calcula la prorrata?": "dos preguntas",
    "IVA \x00\x1b[31m turismo <script>alert(1)</script>": "caracteres raros",
    "IVA " + "😀" * 20: "emojis",
}
print()
for pregunta, que in RAROS.items():
    reventado = None
    try:
        res, salida, _l = consultar(pregunta)
    except Exception as e:  # noqa: BLE001
        reventado = e
    comprobar(f"«{que}» no revienta", reventado is None, repr(reventado))
    if reventado is None:
        comprobar(f"  «{que}» acaba en un estado, no en un limbo",
                  res.get("estado") or res.get("codigo") is not None,
                  str(res)[:60])
        comprobar(f"  «{que}» sin traza de Python en pantalla",
                  "Traceback" not in salida and 'File "' not in salida)

# ===================================================== 3. TEMAS QUE NO ESTAN
print("\n=== 3. TEMAS QUE NO ESTAN: LA PUERTA, NO UNA RESPUESTA INVENTADA ===")
print("  Se fuerza el impuesto porque el motor de ensayo no analiza: lo que se")
print("  prueba es la puerta, que es una regla del sistema.\n")

FUERA = {
    "ITP-AJD": "cuanto se paga de ITP por comprar un piso de segunda mano",
    "IIEE": "impuesto especial sobre el alcohol de una destileria",
    "otro": "el IBI de un local y la plusvalia municipal al venderlo",
}
for impuesto, pregunta in FUERA.items():
    res, salida, _l = consultar(pregunta, 2023, impuesto=impuesto)
    comprobar(f"{impuesto}: no se contesta", res["codigo"] == 2,
              f"codigo {res['codigo']}, estado {res['estado']}")
    comprobar(f"{impuesto}: y NO se muestra ningun texto", not res.get("respuesta"))
    motivo = (res.get("motivo") or "").lower()
    comprobar(f"{impuesto}: el motivo dice que cubre esta herramienta",
              "cubre" in motivo, motivo[:70])
    comprobar(f"{impuesto}: y nombra los impuestos que si estan",
              any(n.lower()[:24] in motivo
                  for n in ix.normas.nombres_de_impuesto()), motivo[:70])

# Una laboral y una de herencias: el analizador de verdad diria "otro".
for pregunta in ("indemnizacion por despido en un ERE: que dice el Estatuto "
                 "de los Trabajadores",
                 "impuesto de sucesiones de una herencia entre hermanos"):
    res, _s, _l = consultar(pregunta, 2023, impuesto="otro")
    comprobar(f"«{pregunta[:40]}...» sale por la puerta", res["codigo"] == 2,
              f"codigo {res['codigo']}")

# ===================================================== 3bis. EN LA VENTANA
print("\n=== 3bis. Y LO QUE SE LEE EN LA VENTANA DICE LA VERDAD ===")
print("  La ventana daba UNA frase fija para los tres motivos de parada:")
print("  «Falta el año del caso». Desde que hay tope de longitud eso es")
print("  mentira: a quien pega un requerimiento se le decia que faltaba el")
print("  año.\n")

import tkinter as tk  # noqa: E402
import interfaz  # noqa: E402

raiz = tk.Tk()
raiz.withdraw()
ventana = interfaz.Ventana(raiz, "ensayo")

print("  Y el largo se avisa MIENTRAS SE ESCRIBE, no al pulsar: alguien va a")
print("  pegar un requerimiento entero y no puede llevarse un rechazo.\n")

visible = tk.Tk()
visible.geometry("1180x900+40+40")
uno = interfaz.Ventana(visible, "ensayo")
espera = 0
while uno.motor is None and espera < 1200:
    visible.update()
    espera += 1
uno.ejercicio.set("2023")


def escribir(n):
    uno.caja.delete("1.0", "end")
    uno.caja.insert("1.0", "x" * n)
    visible.update()
    return (bool(uno.aviso_largo.winfo_manager()),
            str(uno.boton["state"]), uno.aviso_largo.cget("text"))


hay, boton, _t = escribir(40)
comprobar("con una duda corta no hay aviso ninguno", not hay)
comprobar("  y se puede consultar", boton == "normal", boton)

hay, boton, texto = escribir(int(fase4.TOPE_PREGUNTA * 0.85))
comprobar("acercandose SI avisa, antes de que sorprenda", hay)
comprobar("  pero sin impedir nada: es un aviso, no una alarma",
          boton == "normal", boton)
comprobar("  y dice por donde va", "1.200" in texto, texto)

hay, boton, texto = escribir(fase4.TOPE_PREGUNTA + 400)
comprobar("pasado el tope se dice y no se deja pulsar", hay and boton == "disabled",
          boton)
comprobar("  y se dice QUE HACER, no solo que esta mal",
          "pega solo" in texto.lower() or "resúmela" in texto.lower(), texto)
comprobar("  y que esto se va a caer cuando se lean PDF",
          "pdf" in texto.lower(), texto)
comprobar("  sin regañar: ni «error», ni «no puedes»",
          not any(p in texto.lower() for p in ("error", "no puedes", "prohib")),
          texto)

# PEGAR NO ES ESCRIBIR: con el raton no hay `<KeyRelease>` ninguno.
uno.caja.delete("1.0", "end")
visible.update()
uno.caja.insert("1.0", "y" * (fase4.TOPE_PREGUNTA + 800))   # como un pegado
visible.update()
comprobar("y pegando con el raton, sin tocar una tecla, avisa igual",
          bool(uno.aviso_largo.winfo_manager())
          and str(uno.boton["state"]) == "disabled",
          str(uno.boton["state"]))
visible.destroy()

PARADAS = [
    ("sin pregunta", consultar("")[0], "pregunta"),
    ("pregunta larga", consultar(LARGA)[0], "tope"),
    ("año que no vale", consultar("deduccion IVA turismo", "23")[0], "digitos"),
]
for que, res, palabra in PARADAS:
    ventana._terminar(res)
    raiz.update()
    leido = ventana.texto.get("1.0", "end")
    comprobar(f"«{que}»: en pantalla se lee su motivo, no el del año",
              palabra in leido.lower(), leido.strip()[:90])
    comprobar(f"  «{que}»: nada que copiar",
              str(ventana.boton_copiar["state"]) == "disabled")
    comprobar(f"  «{que}»: y ni una traza",
              "Traceback" not in leido and 'File "' not in leido)
comprobar("y las tres frases son DISTINTAS entre si",
          len({p[1].get("motivo") for p in PARADAS}) == 3,
          [p[1].get("motivo") for p in PARADAS])
raiz.destroy()

# ===================================================== 4. CONTROL NEGATIVO
print("\n=== 4. LA PRUEBA SABE PONERSE ROJA ===")
print("  Ninguna prueba se da por buena sin verla fallar cuando debe fallar.\n")

# (0) se deja de reconocer «article»
import re  # noqa: E402
from agente_fiscal import citas as CIT  # noqa: E402
original_art = CIT._RE_REF_ARTICULO
try:
    CIT._RE_REF_ARTICULO = re.compile(
        original_art.pattern.replace("|article", ""), original_art.flags)
    inf = VF.Verificador(ix).verificar_texto(borrador, 2023, exigir_norma=True)
    sin_ref = sum(1 for d in inf.dictamenes if "sin referencia" in d.motivo)
    print(f"    sin «article», {sin_ref} citas se caen por «sin referencia»")
    comprobar("(0) sin reconocer «article» se cae el catalan, y el bloque 0 "
              "lo cazaria", sin_ref >= 5, sin_ref)
finally:
    CIT._RE_REF_ARTICULO = original_art
comprobar("(0) y al deshacerlo vuelven a leerse",
          not any("sin referencia" in d.motivo for d in
                  VF.Verificador(ix).verificar_texto(
                      borrador, 2023, exigir_norma=True).dictamenes))

# (a0) el aviso de largo deja de mirar el tope
original_avisar = interfaz.Ventana._avisar_del_largo
try:
    interfaz.Ventana._avisar_del_largo = lambda self, duda: True
    v2 = tk.Tk()
    v2.geometry("1180x900+40+40")
    w = interfaz.Ventana(v2, "ensayo")
    n = 0
    while w.motor is None and n < 1200:
        v2.update()
        n += 1
    w.ejercicio.set("2023")
    w.caja.insert("1.0", "x" * (fase4.TOPE_PREGUNTA + 400))
    v2.update()
    print(f"    sin el aviso, con {fase4.TOPE_PREGUNTA + 400} caracteres el "
          f"boton queda «{w.boton['state']}»")
    comprobar("(a0) sin el aviso se puede pulsar con la pregunta pasada, "
              "y el bloque 2 lo cazaria",
              str(w.boton["state"]) == "normal"
              and not w.aviso_largo.winfo_manager(), str(w.boton["state"]))
    v2.destroy()
finally:
    interfaz.Ventana._avisar_del_largo = original_avisar

# (a) se quita la validacion del año
original = AN.leer_ejercicio
try:
    AN.leer_ejercicio = lambda crudo: (crudo, "sin validar")
    colado, _m = AN.leer_ejercicio("abc")
    print(f"    sin validacion, «abc» se acepta como {colado!r}")
    comprobar("(a) sin validar, «abc» pasaria y el bloque 1 lo cazaria",
              colado is not None and colado == "abc", repr(colado))
finally:
    AN.leer_ejercicio = original
comprobar("(a) y al deshacerlo vuelve a rechazarse",
          AN.leer_ejercicio("abc")[0] is None)

# (b) se deja de unir los cortes de renglon
original_unir = T.unir_cortes_de_linea
try:
    T.unir_cortes_de_linea = lambda t: t
    roto = T.palabras_exactas(T.unir_cortes_de_linea(PDF))
    print(f"    sin unir cortes, el buscador ve {roto}")
    comprobar("(b) sin unir, «deduccion» se pierde y el bloque 2 lo cazaria",
              "deduccion" not in roto, roto)
finally:
    T.unir_cortes_de_linea = original_unir
comprobar("(b) y al deshacerlo vuelve a verla",
          "deduccion" in T.palabras_exactas(T.unir_cortes_de_linea(PDF)))

# (c) se quita el tope de longitud
tope = fase4.TOPE_PREGUNTA
try:
    fase4.TOPE_PREGUNTA = 10_000_000
    _r, _s, llamadas = consultar(LARGA)
    print(f"    sin tope, el requerimiento pegado gasta {llamadas} llamada(s)")
    comprobar("(c) sin tope se paga el analisis, y el bloque 2 lo cazaria",
              llamadas >= 1, f"{llamadas} llamadas")
finally:
    fase4.TOPE_PREGUNTA = tope
_r, _s, llamadas = consultar(LARGA)
comprobar("(c) y al deshacerlo vuelve a costar cero", llamadas == 0,
          f"{llamadas} llamadas")

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
