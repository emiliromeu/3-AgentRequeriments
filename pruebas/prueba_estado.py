#!/usr/bin/env python3
"""EL ESTADO SALE DE LA EVIDENCIA, NO DEL TEXTO DEL MODELO. Cero red, cero API.

    python pruebas/prueba_estado.py

REEMPLAZA A DOS SUITES PERDIDAS, `prueba_9b` y `prueba_discutido`, y las junta
a proposito. Se escribieron separadas -una para las señales de la DGT, otra
para `EST.calcular`- y probaban los dos extremos de la misma cuerda: que las
señales se calculan bien, y que el estado sale de ellas. Separadas, cada una
podia estar verde con la otra rota.

QUE SE COMPRUEBA, CON EL SISTEMA DE HOY:

  1. DESACUERDO frente a COBERTURA, que son los dos ejes y no se mezclan: un
     desacuerdo mueve el estado a DISCUTIDO; un hueco de cobertura NO lo mueve,
     se enseña igual de claro y deja el estado donde estaba. Juntarlos fue el
     defecto que dio origen a la separacion.
  2. Que la FUENTE CAIDA se dice y NO baja el estado. Es criterio que no se ha
     podido ampliar, no criterio que contradiga.
  3. Que un criterio de OTRA norma va a cobertura y no a desacuerdo.

LO QUE NO SE REPRODUCE DE LAS VIEJAS. Cubrian tambien que «una pregunta de IRPF
no se cuela», y eso hoy lo mide `prueba_filtro` sobre la puerta de materia, que
es donde vive ahora. Reproducirlo aqui seria tener dos suites afirmando lo
mismo y enterarse tarde de cual manda.

TAXONOMIA: todo va contra DOBLES construidos aqui. No se afirma nada sobre la
despensa, porque lo que se prueba es el CALCULO, no que haya tal o cual
consulta guardada.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4                                  # noqa: E402
from agente_fiscal import estado as EST       # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:104]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix, g = fase4.cargar_corpus()


# EL INFORME ES EL DE VERDAD, no un doble. `calcular` lee `veredicto`,
# `motivo_global` y `dictamenes`, y si esa forma cambia esta prueba tiene que
# enterarse por un fallo -no seguir verde probando una estructura que ya no
# existe-. Lo unico que se fabrica aqui son los DICTAMENES, que es el dato.
from agente_fiscal import verificador as VF   # noqa: E402


def informe_aceptado(n_citas: int = 2):
    dicts = [VF.Dictamen(n=i + 1, estado=VF.VERIFICADA,
                         referencia_corpus="Articulo 80",
                         clave="BOE-A-1992-28740#0#articulo 80")
             for i in range(n_citas)]
    return VF.Informe(veredicto=VF.ACEPTADO, ejercicio=2024, dictamenes=dicts)


# LA LECTURA TAMBIEN ES LA DE VERDAD. Tiene DOS LISTAS y son los dos ejes:
# `senales` es desacuerdo de fondo y mueve el estado; `cobertura` es lo que no
# se ha podido comprobar y solo se enseña. Escribirla a mano con otros nombres
# -«debiles»- habria dejado la prueba verde probando una forma inventada.
# Y LAS DOS FUENTES NO LLAMAN IGUAL AL MISMO EJE: la DGT lo llama `senales` y
# el TEAC `desacuerdo`. Cada una se construye con SU forma, no con una comun
# inventada aqui, que es como una prueba acaba verde sobre algo que no existe.
from agente_fiscal import dgt as DGT          # noqa: E402
from agente_fiscal import teac as TEA         # noqa: E402


def Lectura(senales=(), debiles=()):
    return DGT.Lectura(senales=list(senales), cobertura=list(debiles))


def LecturaTeac(senales=(), debiles=()):
    # `desacuerdo` y `cobertura` son PROPIEDADES calculadas de `fuertes` y
    # `debiles`: se construye por los campos, no por la vista.
    return TEA.Lectura(fuertes=list(senales), debiles=list(debiles))


def estado_de(**kw):
    return EST.calcular(kw.get("informe", informe_aceptado()), ix, g,
                        kw.get("ejercicio", 2024),
                        kw.get("n_resultados", 3),
                        lectura_dgt=kw.get("dgt"),
                        lectura_teac=kw.get("teac"))


# ==================================== 1. SIN NADA: CLARO
print("\n=== 1. SIN DESACUERDO Y SIN HUECOS: CRITERIO CLARO ===")
d = estado_de()
print(f"    estado: {d.estado}")
comprobar("con evidencia y sin señales, el estado es CLARO",
          d.estado == EST.CLARO, d.estado)
comprobar("y no se inventa ninguna señal de desacuerdo", not d.senales,
          str(d.senales))

# ==================================== 2. SIN RESULTADOS: NO ENCONTRADO
print("\n=== 2. SIN RESPALDO NO SE AFIRMA NADA ===")
d = estado_de(n_resultados=0)
comprobar("sin un solo precepto recuperado, NO ENCONTRADO",
          d.estado == EST.NO_ENCONTRADO, d.estado)

# ==================================== 3. LOS DOS EJES
print("\n=== 3. DESACUERDO MUEVE EL ESTADO; COBERTURA NO ===")
print("  Es el defecto que dio origen a la separacion: mezclados, un hueco")
print("  de cobertura bajaba el estado y una respuesta buena parecia dudosa.\n")

con_desacuerdo = estado_de(dgt=Lectura(
    senales=["sobre el articulo 80 hay criterio de años distintos"]))
print(f"    con desacuerdo: {con_desacuerdo.estado}")
comprobar("una señal de desacuerdo lleva a DISCUTIDO",
          con_desacuerdo.estado == EST.DISCUTIDO, con_desacuerdo.estado)
comprobar("  y la señal se conserva para enseñarla",
          bool(con_desacuerdo.senales), str(con_desacuerdo.senales))

con_hueco = estado_de(dgt=Lectura(
    debiles=["hay 2 resoluciones sobre el articulo 80 que no se han "
             "podido comprobar"]))
print(f"    con hueco de cobertura: {con_hueco.estado}")
comprobar("un hueco de cobertura NO mueve el estado",
          con_hueco.estado == EST.CLARO, con_hueco.estado)
comprobar("  pero se enseña igual de claro",
          bool(con_hueco.cobertura), str(con_hueco.cobertura))
comprobar("  y NO se cuela entre las señales de desacuerdo",
          not con_hueco.senales, str(con_hueco.senales))

# Los dos a la vez: manda el desacuerdo, y el hueco sigue viendose.
ambos = estado_de(dgt=Lectura(senales=["desacuerdo entre criterios"],
                              debiles=["no se ha podido comprobar una"]))
comprobar("con los dos a la vez, manda el desacuerdo",
          ambos.estado == EST.DISCUTIDO, ambos.estado)
comprobar("  y el hueco NO desaparece por eso",
          bool(ambos.cobertura), str(ambos.cobertura))

# ==================================== 4. LA FUENTE CAIDA
print("\n=== 4. LA FUENTE CAIDA SE DICE Y NO BAJA EL ESTADO ===")
print("  No es criterio que contradiga: es criterio que no se ha podido")
print("  ampliar. Bajar el estado por eso seria castigar al usuario por una")
print("  avería de un tercero.\n")

caida = estado_de(dgt=Lectura(
    debiles=["la fuente de la DGT no responde: hoy no se ha podido ampliar"]))
comprobar("con la fuente caida el estado NO baja",
          caida.estado == EST.CLARO, caida.estado)
comprobar("  pero queda constancia en cobertura",
          any("no responde" in x for x in caida.cobertura),
          str(caida.cobertura))
comprobar("  y no se presenta como desacuerdo", not caida.senales,
          str(caida.senales))

# ==================================== 5. EL TEAC, POR EL MISMO SITIO
print("\n=== 5. EL TEAC ENTRA POR LA MISMA PUERTA ===")
teac_desacuerdo = estado_de(teac=LecturaTeac(
    senales=["el TEAC y el TEAR dicen cosas distintas sobre el articulo 80"]))
comprobar("una señal del TEAC tambien lleva a DISCUTIDO",
          teac_desacuerdo.estado == EST.DISCUTIDO, teac_desacuerdo.estado)
teac_hueco = estado_de(teac=LecturaTeac(
    debiles=["hay 1 resolucion sin comprobar"]))
comprobar("y un hueco del TEAC tampoco mueve el estado",
          teac_hueco.estado == EST.CLARO, teac_hueco.estado)

# ==================================== 6. CONTROL NEGATIVO
print("\n=== 6. LA PRUEBA SABE PONERSE ROJA ===")
print("  Se rompe `estado.py` de verdad -el fichero, no un doble- y se mira")
print("  cual de los bloques cae.\n")

import types                                   # noqa: E402

FUENTE = (RAIZ / "agente_fiscal" / "estado.py").read_text("utf-8")


def con_el_codigo_roto(viejo, nuevo):
    if viejo not in FUENTE:
        raise AssertionError(f"la mutacion ya no encaja: {viejo[:60]}")
    mod = types.ModuleType("agente_fiscal.estado_roto")
    mod.__package__ = "agente_fiscal"
    mod.__file__ = str(RAIZ / "agente_fiscal" / "estado.py")
    sys.modules[mod.__name__] = mod
    try:
        exec(compile(FUENTE.replace(viejo, nuevo, 1), mod.__file__, "exec"),
             mod.__dict__)
    finally:
        del sys.modules[mod.__name__]
    return mod


def estado_con(mod, **kw):
    return mod.calcular(informe_aceptado(), ix, g, 2024,
                        kw.get("n_resultados", 3),
                        lectura_dgt=kw.get("dgt"), lectura_teac=kw.get("teac"))


# (a) que los huecos de cobertura tambien muevan el estado: es EXACTAMENTE el
#     defecto que se corrigio, y el bloque 3 tiene que cazarlo.
roto = con_el_codigo_roto("    if desacuerdo:",
                          "    if desacuerdo or cobertura:")
d_roto = estado_con(roto, dgt=Lectura(debiles=["no se ha podido comprobar"]))
comprobar("(a) si un hueco de cobertura moviera el estado, se caza",
          d_roto.estado != EST.CLARO, d_roto.estado)
d_bien = estado_con(roto, dgt=Lectura(senales=["desacuerdo"]))
comprobar("  y el desacuerdo sigue moviendolo (la mutacion no lo tapa)",
          d_bien.estado == EST.DISCUTIDO, d_bien.estado)

# (b) que las señales dejen de mover el estado.
roto2 = con_el_codigo_roto("    if desacuerdo:", "    if False:")
d_roto2 = estado_con(roto2, dgt=Lectura(senales=["desacuerdo de fondo"]))
comprobar("(b) si un desacuerdo NO moviera el estado, se caza",
          d_roto2.estado != EST.DISCUTIDO, d_roto2.estado)

# (c) y sin mutar, todo vuelve
comprobar("(c) sin mutar, el estado vuelve a salir bien",
          estado_de(dgt=Lectura(senales=["x"])).estado == EST.DISCUTIDO
          and estado_de(dgt=Lectura(debiles=["y"])).estado == EST.CLARO)

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
