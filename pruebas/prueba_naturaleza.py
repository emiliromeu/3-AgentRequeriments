#!/usr/bin/env python3
"""DE FONDO O DE PROCEDIMIENTO, DICHO Y NO ADIVINADO. Cero red, cero API.

    python pruebas/prueba_naturaleza.py

EL PROBLEMA DE TAMAÑO. 836 preceptos generales -LGT, RGAT, recaudacion,
sancionador, facturacion- contra 47 de la Ley del Patrimonio. Compitiendo en el
mismo ranking, las generales copaban los puestos y los articulos de la ley del
impuesto NO LLEGABAN A SER CANDIDATOS: el articulo 37 de la Ley 19/1991 -quien
esta obligado a declarar- estaba en el puesto 4 contando solo su ley y en el 25
con las generales dentro. No es pertinencia, es tamaño de coleccion.

POR QUE NO BASTABA CON SEPARAR LAS DOS LIGAS. El corte por pertinencia ya tenia
la regla del papel, pero decidia si una consulta era de procedimiento MIRANDO
QUIEN GANABA EL PUESTO 1. Eso funciona con un ranking y deja de funcionar con
dos: la norma general nunca queda la primera en su propia liga, asi que toda
consulta pasaba por «de fondo». Medido: separando sin señal, las cuatro
preguntas de procedimiento pasaban de puesto 1-3 a NO SALIR.

Asi que la señal la da el analizador, que es quien ha leido la pregunta, y la
instruccion es sobre QUE SE PREGUNTA -«cuanto puedo deducir» frente a «que
plazo tengo»- y no sobre que norma lo resuelve.

Y LA REGLA DE SIEMPRE: si no se sabe, no se separa. `no_esta_claro` se comporta
como antes de todo esto.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import banco  # noqa: E402
import fase4  # noqa: E402
from agente_fiscal import analizador as AN  # noqa: E402
from agente_fiscal import estado as EST  # noqa: E402
from agente_fiscal import modelo as MOD  # noqa: E402
from agente_fiscal import referencias as R  # noqa: E402
from agente_fiscal.indice import Indice  # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:100]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix = Indice(RAIZ / "datos" / "corpus")
grafo = R.GrafoRemisiones(ix.docs)
N = ix.normas
ART37 = ("BOE-A-1991-14392#0#articulo 37",
         "con que patrimonio hay obligacion de presentar la declaracion", "IP")


def puesto(res, clave):
    for i, r in enumerate(res, 1):
        if r.doc.clave == clave:
            return i
    return None


def natural_del_caso(cuerpo):
    """Lo que declara el caso al decir donde vive su respuesta."""
    return AN.PROCEDIMIENTO if N.impuesto_de_cuerpo(cuerpo) == "" else AN.FONDO


# =============================================== 1. EL CAMPO EXISTE Y MANDA
print("\n=== 1. EL CAMPO, Y QUE NO SE PUEDE INVENTAR ===")
comprobar("hay tres valores, ni dos ni cuatro", len(AN.NATURALEZAS) == 3,
          AN.NATURALEZAS)
comprobar("uno de ellos es para cuando no se sabe",
          AN.NATURALEZA_DUDOSA in AN.NATURALEZAS)
esquema = AN.esquema_de(ix.normas)
comprobar("va en el esquema que se le manda a la API",
          esquema["properties"]["naturaleza"]["enum"] == list(AN.NATURALEZAS))
comprobar("y es obligatorio: no se puede omitir",
          "naturaleza" in esquema["required"])

BASE = {"impuesto": "IVA", "ejercicio": 2023,
        "ejercicio_fundamento": "lo dice la pregunta",
        "articulos_sospechados": [],
        "terminos_busqueda": ["vehiculo automovil de turismo",
                              "cuota soportada deducible", "bien de inversion"],
        "resumen_duda": "si el IVA de un turismo se deduce entero"}
for valor in AN.NATURALEZAS:
    a, err = AN.validar(dict(BASE, naturaleza=valor), ix.normas)
    comprobar(f"«{valor}» se admite", a is not None and a.naturaleza == valor, err)
a, err = AN.validar(dict(BASE, naturaleza="mixta"), ix.normas)
comprobar("un valor inventado se rechaza", a is None)
comprobar("  y el error dice cuales valen",
          any("no_esta_claro" in e for e in err), err)
a, err = AN.validar({k: v for k, v in BASE.items()}, ix.normas)
comprobar("y si falta el campo, tambien se rechaza", a is None, err)

# =============================================== 2. LA SEPARACION
print("\n=== 2. CON FONDO SE SEPARA; CON LO DEMAS, NO ===")
print("  El articulo 37 de la Ley 19/1991 es el caso que lo destapo: puesto 4")
print("  contando solo su ley, puesto 25 con las 836 generales dentro.\n")

clave, consulta, imp = ART37
por_naturaleza = {}
for nat in (AN.FONDO, AN.PROCEDIMIENTO, AN.NATURALEZA_DUDOSA, ""):
    r, _h, _x = fase4.recuperar(ix, grafo, consulta, imp, tope=30, naturaleza=nat)
    por_naturaleza[nat or "(nada)"] = puesto(r, clave)
    n_gen = sum(1 for x in r[:6]
                if N.impuesto_de_cuerpo(x.doc.registro.get("cuerpo_clave") or "") == "")
    print(f"    naturaleza={nat or '(nada)':<14} puesto del art. 37: "
          f"{por_naturaleza[nat or '(nada)']!s:<8} generales en el top 6: {n_gen}")

comprobar("con «fondo» el articulo 37 llega", por_naturaleza["fondo"] is not None)
comprobar("  y llega arriba, no de milagro", por_naturaleza["fondo"] <= 6,
          por_naturaleza["fondo"])
comprobar("con «procedimiento» NO se separa: se comporta como antes",
          por_naturaleza["procedimiento"] == por_naturaleza["(nada)"],
          (por_naturaleza["procedimiento"], por_naturaleza["(nada)"]))
comprobar("con «no_esta_claro» tampoco: si no se sabe, no se toca",
          por_naturaleza["no_esta_claro"] == por_naturaleza["(nada)"],
          (por_naturaleza["no_esta_claro"], por_naturaleza["(nada)"]))
comprobar("y separar MEJORA el puesto, que es de lo que se trata",
          por_naturaleza["fondo"] < (por_naturaleza["(nada)"] or 10_000),
          (por_naturaleza["fondo"], por_naturaleza["(nada)"]))

r_f, _h, _x = fase4.recuperar(ix, grafo, consulta, imp, tope=6,
                              naturaleza=AN.FONDO)
comprobar("con «fondo» no compite NI UNA general",
          not any(N.impuesto_de_cuerpo(x.doc.registro.get("cuerpo_clave") or "") == ""
                  for x in r_f),
          [x.doc.referencia for x in r_f])

# =============================================== 3. EL CORTE LEE LA SEÑAL
print("\n=== 3. EL CORTE POR PERTINENCIA LEE LA SEÑAL, NO EL RANKING ===")
PROC = "me he retrasado en presentar el modelo 303 del IVA y nadie me lo ha " \
       "reclamado, que recargo me toca"
LGT27 = "BOE-A-2003-23186#0#articulo 27"
res, _h, rsv = fase4.recuperar(ix, grafo, PROC, "IVA", naturaleza=AN.PROCEDIMIENTO)
sel_p = EST.seleccionar_material(ix, PROC, res, grafo, reserva=rsv,
                                 naturaleza=AN.PROCEDIMIENTO)
sel_f = EST.seleccionar_material(ix, PROC, res, grafo, reserva=rsv,
                                 naturaleza=AN.FONDO)
en = lambda s: any(p["clave"] == LGT27 for p in s.elegidos)  # noqa: E731


def generales(sel):
    """Cuantas normas generales acaban en el material."""
    return [p["referencia"] for p in sel.elegidos
            if N.impuesto_de_cuerpo(p.get("cuerpo_clave") or "") == ""]


# OJO CON LA REGLA 1, que no es negociable y es anterior a todo esto: EL
# PRIMERO ENTRA SIEMPRE, pase lo que pase. `es_apoyo` solo se consulta del
# segundo en adelante. Asi que el articulo 27 de la LGT entra con las dos
# naturalezas -es el mejor resultado- y mi primera version de esta prueba
# esperaba lo contrario y acusaba al codigo de algo que hace a proposito.
#
# Lo que la señal cambia es a los DEMAS: con «fondo», las generales que no son
# la primera se quedan de apoyo.
print(f"    con «procedimiento» llegan estas generales: {generales(sel_p)}")
print(f"    con «fondo» (mal clasificada a proposito): {generales(sel_f)}")
comprobar("marcada como procedimiento, las generales SI aportan",
          len(generales(sel_p)) > 1, generales(sel_p))
comprobar("marcada como fondo, solo sobrevive la primera",
          len(generales(sel_f)) == 1, generales(sel_f))
comprobar("  o sea: manda la señal, no quien gano el puesto 1",
          len(generales(sel_p)) != len(generales(sel_f)))
comprobar("y el primero entra con las dos: esa regla no la toca nadie",
          en(sel_p) and en(sel_f))

# =============================================== 4. TODO EL BANCO
print("\n=== 4. TODOS LOS CASOS, Y LAS DE PROCEDIMIENTO NI UN PUESTO ===")
casos = [c for c in banco.leer_casos(banco.CASOS) if N.resolver(c["norma"])[0]]
# EL NUMERO NO SE CLAVA. Aqui ponia «el banco tiene los 31 casos» y se puso
# rojo al añadir los diez de Sucesiones y Transmisiones, sin que nada estuviera
# roto. Es la misma podredumbre que la de las suites que leen la despensa: una
# cifra escrita contra algo que crece a proposito. Lo que importa es que la
# comprobacion mire TODOS los que haya y que haya suficientes para significar
# algo.
comprobar("el banco tiene casos con los que comprobarlo",
          len(casos) >= 31, len(casos))
print(f"    {len(casos)} casos, se comprueban todos")
movidas = []
for c in casos:
    cuerpo, _m = N.resolver(c["norma"])
    if N.impuesto_de_cuerpo(cuerpo) != "":
        continue                       # esta es de fondo
    imp = c.get("impuesto") or ""
    a, _h, _x = fase4.recuperar(ix, grafo, c["consulta"], imp, tope=30,
                                naturaleza=AN.PROCEDIMIENTO)
    b, _h2, _y = ix.buscar_del_impuesto(c["consulta"], 30,
                                        N.admitidos_para(imp), grafo)
    pa = next((i for i, r in enumerate(a, 1)
               if r.doc.registro["referencia"].replace("Articulo ", "")
               in c["aceptables"] and r.doc.registro["cuerpo_clave"] == cuerpo), None)
    pb = next((i for i, r in enumerate(b, 1)
               if r.doc.registro["referencia"].replace("Articulo ", "")
               in c["aceptables"] and r.doc.registro["cuerpo_clave"] == cuerpo), None)
    if pa != pb:
        movidas.append((c["consulta"][:44], pb, pa))
comprobar("NINGUNA de procedimiento se mueve ni un puesto", not movidas, movidas)

# =============================================== 5. CONTROL NEGATIVO
print("\n=== 5. LA PRUEBA SABE PONERSE ROJA ===")
print("  Ninguna prueba se da por buena sin verla fallar cuando debe fallar.\n")

# (a) se quita la señal: se separa siempre, tambien en procedimiento
r_mal, _h, rs_mal = fase4.recuperar(ix, grafo, PROC, "IVA", tope=30,
                                    naturaleza=AN.FONDO)
p_mal = next((i for i, x in enumerate(r_mal, 1) if x.doc.clave == LGT27), None)
print(f"    separando una pregunta de PROCEDIMIENTO como si fuera de fondo, "
      f"el art. 27 LGT queda en: {p_mal or 'NO SALE'}")
comprobar("(a) sin la señal el procedimiento se rompe, y el bloque 4 lo cazaria",
          p_mal is None, p_mal)

# (b) se quita la separacion: el articulo 37 vuelve a caerse
r_sin, _h, _x = fase4.recuperar(ix, grafo, consulta, imp, tope=30,
                                naturaleza=AN.NATURALEZA_DUDOSA)
p_sin = puesto(r_sin, clave)
print(f"    sin separar, el art. 37 vuelve al puesto: {p_sin or 'NO SALE'}")
comprobar("(b) sin separacion el art. 37 se cae, y el bloque 2 lo cazaria",
          p_sin is None or p_sin > 6, p_sin)
comprobar("(b) y con separacion vuelve", por_naturaleza["fondo"] <= 6)

# (c) el corte vuelve a adivinar por el ranking
sel_viejo = EST.seleccionar_material(ix, PROC, res, grafo, reserva=rsv)
print(f"    adivinando por el ranking, el art. 27 LGT llega: {en(sel_viejo)}")
comprobar("(c) sin pasarle la señal, el corte vuelve a la regla vieja",
          en(sel_viejo) == en(sel_p), (en(sel_viejo), en(sel_p)))

# (d) el motor de ensayo tiene que saber decir las dos cosas
m = MOD.crear_motor("ensayo")
naturales = {}
for q in ("deduccion del IVA de un turismo",
          "me he retrasado en presentar el 303"):
    r = m.analizar(AN.SISTEMA, q, AN.esquema_de(ix.normas))
    naturales[q] = (r.datos or {}).get("naturaleza")
comprobar("(d) el motor de ensayo distingue las dos, si no no prueba nada",
          len(set(naturales.values())) == 2, naturales)

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
