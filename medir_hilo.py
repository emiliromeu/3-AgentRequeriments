#!/usr/bin/env python3
"""¿CUANTAS VECES SE REFORMULA UNA PREGUNTA? Cero red, cero API.

    .venv/bin/python medir_hilo.py

LA PREGUNTA QUE DECIDE SI HACE FALTA LA CONVERSACION. El departamento pidio tres
cosas: precisar la pregunta (A), preguntar sobre la respuesta (B) y pedir otra
forma (C). Solo se construyo la C.

LA SOSPECHA, que hay que confirmar o descartar CON DATOS: que la gente reformule
no porque quiera conversar, sino PORQUE NO ENCUENTRA CRITERIO. Si es eso, el
hilo es el sintoma y no la enfermedad, y arreglar la cobertura lo hace
desaparecer. Construir A y B ahora seria automatizar una frustracion.

NO HACIA FALTA CONSTRUIR LA CONVERSACION PARA MEDIRLA: el hilo ya ocurria a
mano. Alguien pregunta, no le convence, reescribe y vuelve a preguntar. Eso deja
dos trazas seguidas y parecidas, y las trazas ya estan en disco.

Y AHORA HAY LAS DOS COSAS. Construidas A y B, una vuelta deja `hilo.json` con
su `viene_de`: eso es un hilo DECLARADO, no adivinado. Las dos medidas se
enseñan separadas y NO se suman, porque no son lo mismo: una la infiere este
guion con un umbral de parecido y la otra la escribio la ventana. Mezclarlas
seria cambiar la base entre mediciones, que es exactamente lo que ya nos hizo
tomar dos decisiones malas.

QUE MIDE
  · cuantos pares SEGUIDOS y PARECIDOS hay -o sea, reformulaciones-;
  · y sobre todo: QUE PASO EN LA PRIMERA. Si la mayoria de reformulaciones
    vienen detras de una consulta SIN CRITERIO, la sospecha se confirma.

COMO SE LEE DENTRO DE UN MES. Si la proporcion de reformulaciones baja segun
crece la despensa, era el sintoma. Si se mantiene con la cobertura alta, la
gente quiere conversar de verdad y entonces A y B valen la pena.

SE EXCLUYEN LAS PRUEBAS. La mayoria de las trazas del disco son mias -suites,
banco, guiones de medida- y contarlas diria que se reformula constantemente.
Solo cuentan las que llamaron al modelo de verdad Y no son un caso del banco.

NO IMPRIME NINGUNA PREGUNTA ENTERA. Son dudas reales de clientes: se cuentan,
no se citan.
"""
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

TRAZAS = RAIZ / "datos" / "trazas"
# Dos consultas de la misma sesion. Quince minutos: mas que eso ya es otra cosa
# que se pregunta, no la misma reescrita.
MISMA_SESION = 900
# Cuanto vocabulario tienen que compartir para considerarlas la misma pregunta
# reformulada. 0,35 sale de mirar los pares reales: por debajo aparecen
# consultas del mismo impuesto que no tienen nada que ver.
PARECIDO = 0.35


def _es_de_verdad(d: Path) -> bool:
    """¿La hizo una persona con el modelo real, o soy yo probando?"""
    c = d / "consumo.json"
    if not c.is_file():
        return False
    try:
        return "claude" in json.dumps(json.loads(c.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return False


def _sin_criterio(d: Path) -> bool:
    """¿Esa consulta se quedo sin criterio de la DGT?"""
    f = d / "resultado.json"
    if not f.is_file():
        return False
    try:
        j = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    dgt = j.get("dgt") or {}
    return not (dgt.get("consultas") or dgt.get("usadas"))


def _declarados(filas) -> None:
    """LOS HILOS DE VERDAD: los que dejo escritos la ventana, no los inferidos.

    Base distinta a la de arriba y por eso va en su propio bloque: aqui no hay
    umbral de parecido ni ventana de tiempo. O hay `hilo.json` o no lo hay.
    """
    cadenas = {}                      # {traza raiz: nº de vueltas}
    padre = {}
    for f in filas:
        h = f["dir"] / "hilo.json"
        if not h.is_file():
            continue
        try:
            padre[f["dir"].name] = json.loads(
                h.read_text(encoding="utf-8")).get("viene_de", "")
        except (OSError, ValueError):
            continue

    def raiz_de(nombre: str) -> str:
        visto = set()
        while padre.get(nombre) and nombre not in visto:
            visto.add(nombre)
            nombre = padre[nombre]
        return nombre

    for hijo in padre:
        cadenas[raiz_de(hijo)] = cadenas.get(raiz_de(hijo), 1) + 1

    print()
    print("-" * 74)
    print("Y LOS HILOS DECLARADOS (base distinta: los que dejo la ventana)")
    print("-" * 74)
    if not cadenas:
        print("  Ninguno todavia. El boton de seguir es nuevo: vuelve a medir")
        print("  cuando el departamento lo haya usado unas semanas.")
        return
    vueltas = sorted(cadenas.values(), reverse=True)
    print(f"  conversaciones con mas de una vuelta : {len(cadenas)}")
    print(f"  vueltas por conversacion             : "
          f"maxima {vueltas[0]}, media {sum(vueltas)/len(vueltas):.1f}")
    print(f"  reparto: {dict(Counter(vueltas))}   (vueltas: cuantas)")


def main() -> int:
    from agente_fiscal import texto as T
    import banco

    casos = [set(T.tokenizar(c["consulta"], quitar_vacias=True))
             for c in banco.leer_casos(banco.CASOS)]

    filas = []
    for d in sorted(TRAZAS.iterdir()) if TRAZAS.is_dir() else []:
        p = d / "pregunta.txt"
        if not p.is_file() or not _es_de_verdad(d):
            continue
        try:
            cuando = datetime.strptime(d.name[:15], "%Y%m%dT%H%M%S")
        except ValueError:
            continue
        texto = p.read_text(encoding="utf-8", errors="replace").strip()
        raices = set(T.tokenizar(texto, quitar_vacias=True))
        if not raices:
            continue
        # Fuera lo que es un caso del banco: eso soy yo.
        if max((len(raices & b) / len(raices | b) for b in casos if b),
               default=0) >= 0.5:
            continue
        filas.append({"cuando": cuando, "raices": raices, "dir": d,
                      "largo": len(texto)})
    filas.sort(key=lambda f: f["cuando"])

    print("=" * 74)
    print("EL HILO QUE YA OCURRE A MANO")
    print("=" * 74)
    print(f"  consultas de una persona con el modelo real : {len(filas)}")
    if len(filas) < 2:
        print("\n  Todavia no hay bastante para decir nada. Vuelve a correrlo")
        print("  cuando el departamento lleve unas semanas usandolo.")
        return 0
    print(f"  de {filas[0]['cuando']:%d/%m} a {filas[-1]['cuando']:%d/%m}")

    seguidos = reformulaciones = 0
    tras_sin_criterio = 0
    crecen = Counter()
    for a, b in zip(filas, filas[1:]):
        if (b["cuando"] - a["cuando"]).total_seconds() > MISMA_SESION:
            continue
        seguidos += 1
        j = len(a["raices"] & b["raices"]) / len(a["raices"] | b["raices"])
        if j < PARECIDO:
            continue
        # Identicas no son reformulaciones: son la misma lanzada dos veces.
        if j > 0.98 and a["largo"] == b["largo"]:
            continue
        reformulaciones += 1
        crecen["mas larga" if b["largo"] > a["largo"] else "igual o mas corta"] += 1
        if _sin_criterio(a["dir"]):
            tras_sin_criterio += 1

    print()
    print(f"  pares de la misma sesion (<{MISMA_SESION // 60} min) : {seguidos}")
    print(f"  de esos, REFORMULACIONES                  : {reformulaciones}"
          + (f"   ({100 * reformulaciones / seguidos:.0f}%)" if seguidos else ""))
    if reformulaciones:
        print(f"     la segunda es mas larga: {crecen['mas larga']} de "
              f"{reformulaciones}  (mas larga = dar mas contexto, o sea «A»)")
        print()
        print(f"  Y LO QUE DECIDE: reformulaciones que vienen DETRAS de una")
        print(f"  consulta SIN CRITERIO: {tras_sin_criterio} de "
              f"{reformulaciones}"
              + (f"   ({100 * tras_sin_criterio / reformulaciones:.0f}%)"
                 if reformulaciones else ""))
        print()
        if tras_sin_criterio >= reformulaciones * 0.6:
            print("  LECTURA: la mayoria se reformula despues de no encontrar")
            print("  criterio. El hilo parece el SINTOMA, no lo que se quiere:")
            print("  con la despensa mas llena deberia bajar. Vuelve a medir.")
        else:
            print("  LECTURA: se reformula tambien con criterio delante, asi")
            print("  que no es solo falta de cobertura. Ahi A y B empiezan a")
            print("  tener sentido por si mismos.")
    _declarados(filas)
    print()
    print("  NOTA: esto se lee comparando MEDICIONES, no una sola. Lo que")
    print("  importa es si el porcentaje baja segun crece la despensa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
