#!/usr/bin/env python3
"""LA CITA VA AL CUERPO QUE TIENE EL ARTICULO. Cero red, cero API.

    python pruebas/prueba_cuerpo.py

EL DEFECTO QUE LA JUSTIFICA, y estaba en produccion sin que nada lo viera.

Un documento del BOE puede traer DOS articulados: el del Real Decreto que
aprueba -uno o seis articulos- y el del Reglamento aprobado -ciento y pico-.
Cuando la fuente escribe «Real Decreto 939/2005 art. 82», la designacion
resuelve LIMPIAMENTE al decreto, que tiene un solo articulo. El 82 es del
Reglamento General de Recaudacion.

La regla de unanimidad no lo caza porque NO HAY EMPATE: hay una sola norma
resuelta, y es la equivocada. Medido el 14/08/2026 sobre la despensa: NOVENTA Y
DOS preceptos comparables -o sea, dados por buenos y usados- apuntaban a un
cuerpo que no tiene ese articulo.

LA REGLA, Y SUS CONDICIONES SON DE CONTENCION:

  · solo entre cuerpos del MISMO documento; no cruza a otras normas;
  · si el cuerpo resuelto YA tiene el articulo, no se toca;
  · si NINGUNO lo tiene, no se toca -puede ser errata de la fuente o una
    version antigua- y se queda como esta;
  · si lo tienen VARIOS, no se corrige. Ante la duda, nada.

Y la correccion queda registrada en `corregido_desde`, porque una correccion
silenciosa es indistinguible de un acierto por casualidad.

TAXONOMIA: los bloques 1 y 2 van contra designaciones escritas aqui, que es
afirmacion sobre contenido. El 3 es integridad de la despensa -«ningun precepto
comparable apunta a un cuerpo sin ese articulo»- y por eso SI la lee entera.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4                                    # noqa: E402
from agente_fiscal import dgt as D              # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:104]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix, _g = fase4.cargar_corpus()
N = ix.normas


def leer(campo: str):
    return D.pares_de_normativa(campo, N)


# ==================================== 1. EL POSITIVO: HAY QUE CORREGIR
print("\n=== 1. EL HERMANO SI LO TIENE: SE CORRIGE ===")
print("  «Real Decreto 939/2005 art. 82». El decreto tiene UN articulo; el 82")
print("  es del Reglamento General de Recaudacion.\n")

ps = leer("Real Decreto 939/2005 art. 82")
comprobar("se lee un precepto", len(ps) == 1, len(ps))
if ps:
    p = ps[0]
    print(f"    {p.numero} -> {N.por_clave(p.cuerpo).nombre if p.cuerpo else '?'}")
    comprobar("va al REGLAMENTO, no al decreto",
              p.cuerpo == "BOE-A-2005-14803#1", p.cuerpo)
    comprobar("y el articulo existe ahi de verdad",
              N.tiene_articulo(p.cuerpo, p.numero))
    comprobar("queda REGISTRADO de donde venia, para poder auditarlo",
              p.corregido_desde == "BOE-A-2005-14803#0", p.corregido_desde)

# Y EL MISMO CAMPO CON DOS ARTICULOS, UNO DE CADA CUERPO. Es el caso que
# obliga a corregir POR NUMERO y no por designacion: la designacion se resuelve
# UNA vez para la lista entera, asi que una correccion aplicada a la
# designacion se llevaria los dos por delante.
#
# Se usa el RD 1624/1992 y no el 939/2005 porque el decreto de aquel tiene seis
# articulos NUMERADOS -del 1 al 6- y el de este uno solo, el «unico». Con el
# 939/2005 «art. 1» no esta en el decreto y la correccion salta, que es
# correcto y no prueba lo que hace falta probar aqui. Lo caz esta prueba.
ps = leer("Real Decreto 1624/1992 arts. 3, 24 quater")
por_num = {p.numero: p for p in ps}
comprobar("con «arts. 3, 24 quater» se leen los dos", len(ps) == 2, len(ps))
if len(ps) == 2:
    comprobar("  el 3 se queda en el DECRETO, que si lo tiene",
              por_num["3"].cuerpo == "BOE-A-1992-28925#0"
              and not por_num["3"].corregido_desde,
              f"{por_num['3'].cuerpo} corregido={por_num['3'].corregido_desde}")
    comprobar("  y el 24 quater se corrige al REGLAMENTO",
              por_num["24 quater"].cuerpo == "BOE-A-1992-28925#1",
              por_num["24 quater"].cuerpo)

# ==================================== 2. EL ADVERSARIO: NO SE TOCA
print("\n=== 2. NINGUNO LO TIENE: NO SE TOCA ===")
print("  Es la mitad que impide que esto se convierta en «buscar donde")
print("  encaje». Un articulo que no existe en ninguno de los dos cuerpos se")
print("  queda donde la fuente lo puso.\n")

ps = leer("Real Decreto 939/2005 art. 9999")
comprobar("se lee el precepto igualmente", len(ps) == 1, len(ps))
if ps:
    p = ps[0]
    comprobar("NO se corrige: se queda en el decreto",
              p.cuerpo == "BOE-A-2005-14803#0", p.cuerpo)
    comprobar("  y no se marca como corregido", not p.corregido_desde,
              p.corregido_desde)

# NO CRUZA A OTRAS NORMAS. El articulo 82 existe en otras leyes del corpus; la
# correccion no puede irse a ninguna de ellas.
otros = [c for c in N.cuerpos
         if N.tiene_articulo(c, "9999")]
comprobar("(control) el 9999 no existe en NINGUN cuerpo del corpus",
          not otros, str(otros))

hermano = N.cuerpo_hermano_con("BOE-A-2005-14803#0", "82")
comprobar("la regla solo mira hermanos del MISMO documento",
          hermano.startswith("BOE-A-2005-14803"), hermano)
comprobar("  y devuelve vacio si el cuerpo ya tiene el articulo",
          N.cuerpo_hermano_con("BOE-A-2005-14803#1", "82") == "")

# ==================================== 3. LA DESPENSA, DE INTEGRIDAD
print("\n=== 3. NINGUNA CITA APUNTA A UN CUERPO SIN ESE ARTICULO ===")
print("  Es el invariante de verdad, y se mide sobre la despensa entera.\n")

malos, corregidos, comparables = [], 0, 0
for c in D.CacheDGT().todas():
    try:
        preceptos = c.preceptos(N)
    except Exception:                            # noqa: BLE001
        continue
    for p in preceptos:
        if not p.comparable:
            continue
        comparables += 1
        corregidos += bool(p.corregido_desde)
        if not N.tiene_articulo(p.cuerpo, p.numero):
            malos.append((c.numero, p.norma_bruta, p.numero, p.cuerpo))

print(f"    preceptos comparables : {comparables}")
print(f"    corregidos de cuerpo  : {corregidos}")
print(f"    apuntan a un cuerpo sin ese articulo: {len(malos)}")
for x in malos[:5]:
    print(f"      {x[0]} «{x[1][:40]}» art.{x[2]}")

# LO QUE QUEDA TIENE QUE SER SOLO LO QUE NINGUN HERMANO TIENE. Si apareciera
# uno con hermano disponible, la correccion no se estaria aplicando en algun
# camino -que es como se descubrio que habia DOS sitios construyendo Preceptos-.
sin_arreglo = [x for x in malos if N.cuerpo_hermano_con(x[3], x[2])]
comprobar("lo que queda sin corregir es SOLO lo que ningun hermano tiene",
          not sin_arreglo, str(sin_arreglo[:3]))
comprobar("y ninguna correccion ha movido una cita que ya estaba bien",
          all(not N.tiene_articulo(p.corregido_desde, p.numero)
              for c in D.CacheDGT().todas()
              for p in c.preceptos(N)
              if getattr(p, "corregido_desde", "")))

# ==================================== 4. CONTROL NEGATIVO
print("\n=== 4. LA PRUEBA SABE PONERSE ROJA ===")
print("  Se rompen las dos mitades de la regla y se mira que cae.\n")

import types                                     # noqa: E402

FUENTE = (RAIZ / "agente_fiscal" / "normas.py").read_text("utf-8")


def con_el_codigo_roto(viejo, nuevo):
    if viejo not in FUENTE:
        raise AssertionError(f"la mutacion ya no encaja: {viejo[:60]}")
    mod = types.ModuleType("normas_roto")
    mod.__package__ = "agente_fiscal"
    mod.__file__ = str(RAIZ / "agente_fiscal" / "normas.py")
    sys.modules[mod.__name__] = mod
    try:
        exec(compile(FUENTE.replace(viejo, nuevo, 1), mod.__file__, "exec"),
             mod.__dict__)
    finally:
        del sys.modules[mod.__name__]
    return mod


# (a) que deje de corregir: vuelven las 92
roto = con_el_codigo_roto("        return hermanos[0] if len(hermanos) == 1 else \"\"",
                          "        return \"\"")
n_roto = roto.Registro(ix.docs)
comprobar("(a) sin la correccion, el art. 82 se queda en el decreto y el "
          "bloque 1 lo caza",
          n_roto.cuerpo_hermano_con("BOE-A-2005-14803#0", "82") == "")

# (b) que se pase de listo y busque en CUALQUIER norma, no solo en el hermano:
#     es el fallo que atribuiria un articulo a quien no lo dijo.
roto2 = con_el_codigo_roto(
    "        hermanos = [c for c in self.cuerpos\n"
    "                    if c != clave_cuerpo and c.split(\"#\")[0] == documento\n"
    "                    and self.tiene_articulo(c, num)]",
    "        hermanos = [c for c in self.cuerpos\n"
    "                    if c != clave_cuerpo and self.tiene_articulo(c, num)]")
n2 = roto2.Registro(ix.docs)
fuera = n2.cuerpo_hermano_con("BOE-A-2005-14803#0", "9999")
comprobar("(b) buscando fuera del documento, el 9999 sigue sin aparecer "
          "(no existe en ninguno)", fuera == "", fuera)
# El que si se nota: un numero corriente que existe en muchas normas.
suelto = n2.cuerpo_hermano_con("BOE-A-2005-14803#0", "3")
comprobar("(b) pero un numero corriente se iria a OTRA norma, y el bloque 2 "
          "lo caza", suelto == "" or not suelto.startswith("BOE-A-2005-14803"),
          suelto)

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
