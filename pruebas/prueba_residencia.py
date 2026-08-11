#!/usr/bin/env python3
"""LA NORMATIVA AUTONOMICA SOLO ENTRA SI SE SABE DONDE RESIDE. Cero red, cero API.

    python pruebas/prueba_residencia.py

Con el Codi tributari de Catalunya dentro, una pregunta de Renta o de Patrimonio
puede recuperar articulos catalanes SIN QUE NADIE HAYA DICHO DONDE VIVE EL
CLIENTE. Y una deduccion autonomica de otra comunidad no es «menos exacta»: es
de otro sitio. La respuesta saldria impecable, con su cita literal y su enlace,
y estaria mal para el 84% de España.

ES EL MISMO CASO QUE EL AÑO, y por eso va donde va el año -en la pregunta- y no
en un aviso al pie, que se lee una vez y se deja de ver.

LA DIFERENCIA CON EL AÑO, que es lo que decide que no bloquee: el año NO TIENE
ALTERNATIVA SEGURA -cualquier año supuesto es un año equivocado- y la comunidad
SI la tiene: contestar solo con lo estatal, diciendolo. Ademas la ventana no
sabe de que impuesto es la pregunta hasta que el analizador la lee, o sea
despues de pulsar; exigirla en la ventana obligaria a saberlo antes.
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
from agente_fiscal import parser as P  # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:104]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix, grafo = fase4.cargar_corpus()
N = ix.normas
CAT = "BOE-A-2024-6951"
ALQUILER = "deduccion autonomica por alquiler de vivienda habitual en el IRPF"


def catalanes(res):
    return [r.doc.registro["referencia"] for r in res
            if r.doc.registro["norma_id"] == CAT]


def recupera(consulta, impuesto, comunidad, nat=AN.FONDO, tope=6):
    return fase4.recuperar(ix, grafo, consulta, impuesto, tope=tope,
                           naturaleza=nat, comunidad=comunidad)[0]


# ================================================ 1. DE DONDE SALE EL DATO
print("\n=== 1. LA COMUNIDAD SALE DEL BOE, NO DE UNA LISTA ===")
print("  Sus metadatos ya lo dicen: ambito «Autonómico» y departamento")
print("  «Comunidad Autónoma de Cataluña».\n")

CASOS = {("Autonómico", "Comunidad Autónoma de Cataluña"): "Cataluña",
         ("Autonómico", "Comunidad de Madrid"): "Madrid",
         ("Autonómico", "Comunidad Foral de Navarra"): "Navarra",
         ("Autonómico", "Principado de Asturias"): "Asturias",
         ("Autonómico", "Región de Murcia"): "Murcia",
         ("Estatal", "Jefatura del Estado"): "",
         ("Estatal", "Ministerio de Hacienda"): ""}
for (ambito, depto), esperado in CASOS.items():
    comprobar(f"«{ambito}» + «{depto[:30]}» -> {esperado or 'estatal'}",
              P.comunidad_de(ambito, depto) == esperado,
              P.comunidad_de(ambito, depto))
comprobar("y el acento no se lo come: «autonómico» lleva tilde",
          P.comunidad_de("Autonómico", "Comunidad de Madrid") == "Madrid")

comprobar("el corpus sabe de que comunidades tiene normativa",
          N.comunidades() == {"Cataluña"}, N.comunidades())
n_cat = sum(1 for d in ix.docs if N.comunidad_de_precepto(d.registro))
comprobar(f"y cuantos preceptos son ({n_cat})", n_cat == 161, n_cat)
comprobar("los estatales no llevan el campo, y eso significa estatal",
          all(not N.comunidad_de_precepto(d.registro) for d in ix.docs
              if d.registro["norma_id"] != CAT))

# ================================================ 2. LA REGLA
print("\n=== 2. CON COMUNIDAD SI; SIN COMUNIDAD, NADA ===")
con = recupera(ALQUILER, "IRPF", "Cataluña")
sin = recupera(ALQUILER, "IRPF", "")
otra = recupera(ALQUILER, "IRPF", "Madrid")
print(f"    con Cataluña : {catalanes(con)}")
print(f"    sin comunidad: {catalanes(sin) or '(ninguno)'}")
print(f"    con Madrid   : {catalanes(otra) or '(ninguno)'}")
comprobar("con Cataluña salen los articulos del Codi", bool(catalanes(con)))
comprobar("  y salen ARRIBA, no de relleno",
          con[0].doc.registro["norma_id"] == CAT,
          con[0].doc.registro["referencia"])
comprobar("sin comunidad NO sale ninguno", not catalanes(sin))
comprobar("con otra comunidad tampoco", not catalanes(otra))
comprobar("  y las dos dan lo mismo: sin normativa de Madrid, es estatal",
          [r.doc.clave for r in sin] == [r.doc.clave for r in otra])
comprobar("sin comunidad NO se queda sin respuesta: sale la estatal",
          len(sin) > 0 and all(r.doc.registro["norma_id"] != CAT for r in sin))

# ============================== 3. NI POR REMISION SE CUELA OTRA COMUNIDAD
print("\n=== 3. NI POR REMISION ===")
print("  La remision cruza de impuesto -eso no se negocia- pero NO cruza de")
print("  comunidad: un precepto catalan no puede entrar en una consulta de")
print("  Madrid porque otro lo mencione.\n")
_d, _h, reserva = fase4.recuperar(ix, grafo, ALQUILER, "IRPF", tope=6,
                                  naturaleza=AN.FONDO, comunidad="Madrid")
comprobar("en la reserva no hay ni un precepto catalan",
          not any(r.doc.registro["norma_id"] == CAT for r in reserva),
          [r.doc.referencia for r in reserva])

# ================================================ 4. EL AVISO
print("\n=== 4. LO QUE CUESTA NO SABERLO, DICHO EN VOZ ALTA ===")


def consulta(pregunta, impuesto, comunidad):
    m = MOD.crear_motor("ensayo")
    original = m.analizar

    def con_impuesto(s, p, e):
        r = original(s, p, e)
        r.datos["impuesto"] = impuesto
        r.datos["naturaleza"] = "fondo"
        return r

    m.analizar = con_impuesto
    with contextlib.redirect_stdout(io.StringIO()):
        return fase4.consultar(pregunta, 2023, m, ix, grafo,
                               con_criterio=False, comunidad=comunidad)


r_sin = consulta(ALQUILER, "IRPF", "")
r_con = consulta(ALQUILER, "IRPF", "Cataluña")
r_otra = consulta(ALQUILER, "IRPF", "Madrid")
r_iva = consulta("deduccion de las cuotas de un turismo", "IVA", "")

comprobar("sin comunidad, en Renta, se avisa",
          bool(r_sin.get("cobertura_territorial")))
comprobar("  y el aviso dice QUE HACER, no solo que falta",
          "indicala" in (r_sin.get("cobertura_territorial") or ""),
          r_sin.get("cobertura_territorial"))
comprobar("con Cataluña no se avisa: no falta nada",
          not r_con.get("cobertura_territorial"))
comprobar("con Madrid se avisa, y se dice QUE hay cargado",
          "Cataluña" in (r_otra.get("cobertura_territorial") or ""),
          r_otra.get("cobertura_territorial"))
comprobar("  sin llamarlo error: es una limitacion conocida",
          "error" not in (r_otra.get("cobertura_territorial") or "").lower())
comprobar("EN IVA NO SE AVISA: no hay tramo autonomico y seria ruido",
          not r_iva.get("cobertura_territorial"),
          r_iva.get("cobertura_territorial"))
comprobar("y una de IVA se contesta igual, el campo no estorba",
          r_iva["codigo"] == 0, r_iva.get("estado"))

comprobar("la comunidad viaja en el resultado",
          r_con.get("comunidad") == "Cataluña", r_con.get("comunidad"))
comprobar("  y queda en el expediente",
          (Path(r_con["traza"]) / "resultado.json").is_file())

# ================================================ 5. LA VENTANA
print("\n=== 5. LA VENTANA: AL LADO DEL AÑO, PERO SIN BLOQUEAR ===")
import time  # noqa: E402
import tkinter as tk  # noqa: E402

import interfaz  # noqa: E402

raiz = tk.Tk()
raiz.geometry("1180x900+40+40")
v = interfaz.Ventana(raiz, "ensayo")
fin = time.time() + 120
while v.motor is None and time.time() < fin:
    raiz.update()
    time.sleep(0.02)
comprobar("la ventana carga", v.motor is not None)

comprobar("hay un campo de comunidad", hasattr(v, "comunidad"))
comprobar("  vacio de entrada, y nunca se rellena solo",
          v.comunidad.get() == "", v.comunidad.get())
comprobar("  con las 17 comunidades y las 2 ciudades para elegir",
          len(interfaz.COMUNIDADES) == 20, len(interfaz.COMUNIDADES))
v.ejercicio.set("2023")
v.caja.insert("1.0", ALQUILER)
raiz.update()
comprobar("SIN comunidad se puede consultar: no bloquea como el año",
          str(v.boton["state"]) == "normal", str(v.boton["state"]))
v.ejercicio.set("")
raiz.update()
comprobar("  y sin AÑO no se puede: esa si bloquea",
          str(v.boton["state"]) == "disabled", str(v.boton["state"]))
v.ejercicio.set("2023")
raiz.update()

comprobar("el eco enseña la comunidad con la que se hizo",
          "Cataluña" in v._eco("una duda", "2023", "Cataluña"))
comprobar("  y no la inventa cuando no la hay",
          "·" in v._eco("una duda", "2023", "")
          and v._eco("una duda", "2023", "").count("·") == 1,
          v._eco("una duda", "2023", ""))

v._terminar(r_con)
raiz.update()
v.respuesta_actual = "texto de prueba"
v._copiar()
raiz.update()
copiado = raiz.clipboard_get()
comprobar("lo que se copia lleva la comunidad", "Cataluña" in copiado,
          copiado[:90])
v._terminar(r_sin)
raiz.update()
v.respuesta_actual = "texto de prueba"
v._copiar()
raiz.update()
copiado = raiz.clipboard_get()
comprobar("y si faltaba, lo copiado lleva el aviso",
          "AVISO" in copiado and "autonomica" in copiado, copiado[:110])
raiz.destroy()

# ================================================ 6. CONTROL NEGATIVO
print("\n=== 6. LA PRUEBA SABE PONERSE ROJA ===")
print("  Ninguna prueba se da por buena sin verla fallar cuando debe fallar.\n")

# (a) se quita el filtro territorial
original = N.__class__.comunidad_de_precepto
try:
    N.__class__.comunidad_de_precepto = lambda self, registro: ""
    roto_sin = recupera(ALQUILER, "IRPF", "")
    roto_otra = recupera(ALQUILER, "IRPF", "Madrid")
    print(f"    sin filtro, SIN comunidad salen: {catalanes(roto_sin)}")
    print(f"    sin filtro, con Madrid salen   : {catalanes(roto_otra)}")
    comprobar("(a) sin filtro los catalanes vuelven para todo el mundo, "
              "y el bloque 2 lo cazaria",
              bool(catalanes(roto_sin)) and bool(catalanes(roto_otra)),
              (catalanes(roto_sin), catalanes(roto_otra)))
finally:
    N.__class__.comunidad_de_precepto = original
comprobar("(a) y al deshacerlo vuelven a desaparecer",
          not catalanes(recupera(ALQUILER, "IRPF", "")))

# (b) se deja de avisar
r = consulta(ALQUILER, "IRPF", "")
comprobar("(b) el aviso existe, si no el bloque 4 no probaria nada",
          bool(r.get("cobertura_territorial")))
comprobar("(b) y sin el, una respuesta a medias pareceria completa",
          "NO incluye" in (r.get("cobertura_territorial") or ""),
          r.get("cobertura_territorial"))

# (c) que el aviso no salte donde no toca
comprobar("(c) si saltara siempre seria decoracion: en IVA no salta",
          not consulta("prorrata general", "IVA", "").get("cobertura_territorial"))

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
