"""«ESCRIBEMELO PARA EL CLIENTE»: LA MISMA RESPUESTA, OTRA REDACCION.

Es la C de las tres cosas que pidio el departamento, y la unica que se
construye por ahora:

    A · precisar la pregunta          -> misma pregunta con mas contexto
    B · preguntar sobre la respuesta  -> pregunta nueva, material nuevo
    C · otra forma                    -> MISMO MATERIAL, solo redaccion

QUE HACE Y QUE NO. No se analiza, no se busca, no se recorta: el material ya
esta escrito en el expediente de la consulta. Se vuelve a redactar con el mismo
texto de la ley delante y una instruccion distinta. UNA llamada, no dos.

----------------------------------------------------------------------------
EL VERIFICADOR PASA ENTERO, Y AQUI ES DONDE ALGUIEN PENSARA QUE NO HACE FALTA
----------------------------------------------------------------------------
El razonamiento tentador es: «el material es el mismo, las citas son las
mismas, ya se verificaron». Y es FALSO, porque lo que se verifica no es el
material: es EL TEXTO.

Una reescritura «para el cliente» invita justo a lo que rompe una cita:

  · quitar el parentesis con la norma para que no corte la lectura;
  · resumir el fragmento entrecomillado en vez de copiarlo;
  · suavizar un «debera» en un «conviene»;
  · juntar dos articulos en una frase y dejar una sola referencia.

Las cuatro producen texto mas legible y CITAS FALSAS. La regla del proyecto no
cambia por ser la segunda version: NUNCA SE ENSEÑA TEXTO QUE EL VERIFICADOR NO
HA ACEPTADO. Si la reescritura no pasa, se dice y se deja la primera, que si
paso.

----------------------------------------------------------------------------
EL MISMO EXPEDIENTE
----------------------------------------------------------------------------
`redaccion_2.txt` al lado de `redaccion_1.txt`, con su verificacion propia.
No es otra consulta: es la misma con otra ropa, y separarlas en dos expedientes
haria perder que salieron del mismo material.

Cada una guarda SU informe: dentro de seis meses tiene que poder verse que las
dos se comprobaron, y contra que.

EL IDIOMA NO SE DECIDE AQUI. Se responde en el idioma de la pregunta, como todo
lo demas: el material lleva la pregunta original y el redactor ya sabe.
"""
from __future__ import annotations

from pathlib import Path

# LO QUE SE LE PIDE DISTINTO, Y NADA MAS.
#
# Se añade AL FINAL del sistema de siempre, no lo sustituye: las reglas de
# citacion son las mismas y no se relajan por ser para el cliente. Lo unico que
# cambia es el registro.
PARA_EL_CLIENTE = """

--- ESTA VEZ, ADEMAS ---

Esta redaccion es para MANDARSELA AL CLIENTE, no para el fiscalista. Cambia el
registro, NO el contenido ni las citas:

  · Explica primero la conclusion practica: que puede hacer y que no.
  · Evita la jerga que solo entiende un profesional; si un termino tecnico es
    imprescindible, explicalo en la misma frase.
  · Frases cortas.

Y NO CAMBIA NADA DE LO OTRO. Las citas van EXACTAMENTE igual que siempre:
literales, entrecomilladas, con su articulo y su norma. No resumas un fragmento
citado, no quites la norma de una referencia para que se lea mejor, y no
suavices lo que la ley dice de forma tajante. Una respuesta mas facil de leer
con una cita retocada no es mas facil: es falsa.
"""


def material_del_expediente(traza: Path | str) -> str:
    """El material que se le puso delante al redactor, tal cual.

    SE LEE DEL EXPEDIENTE Y NO SE RECONSTRUYE. Reconstruirlo seria volver a
    buscar y a recortar, y entonces esto ya no seria «la misma respuesta con
    otra redaccion»: seria otra consulta que casualmente se parece. Lo que
    garantiza que el material es el mismo es que es EL MISMO FICHERO.
    """
    d = Path(traza)
    # El ultimo intento es el que produjo la respuesta que se enseño.
    materiales = sorted(d.glob("material_*.txt"))
    if not materiales:
        raise FileNotFoundError(
            f"el expediente {d.name} no guarda el material: no se puede "
            f"reescribir sin volver a buscar, y eso seria otra consulta")
    return materiales[-1].read_text(encoding="utf-8")


def claves_del_material(traza: Path | str) -> set | None:
    """Los preceptos que se le pusieron delante al redactor AQUEL DIA.

    `None` si el expediente no lo guarda -los anteriores al 30/08/2026 no lo
    llevan-, y `None` quiere decir «no se me ha dicho», no «ninguno»: sin el
    dato no se exige nada. Suponer que el material era el de hoy seria
    exactamente la fuga que este fichero acaba de cerrar.
    """
    import json
    f = Path(traza) / "material_claves.json"
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    claves = d.get("claves")
    return set(claves) if isinstance(claves, list) else None


def puede_reescribirse(traza: Path | str, dictamenes) -> tuple:
    """¿Sigue en pie la ley sobre la que se contesto? (puede, motivo).

    ────────────────────────────────────────────────────────────────────────
    LA PREGUNTA NO ERA CON QUE SE COMPROBO, SINO SI HA CAMBIADO
    ────────────────────────────────────────────────────────────────────────

    Reescribir para el cliente usa el material del expediente -eso ya estaba-
    pero VERIFICA con el corpus de hoy, y no hay forma de arreglarlo por el
    camino evidente: no se guarda una copia de la ley de agosto y
    reconstruirla no es posible.

    Se estuvo a punto de apagar el boton en todas las consultas antiguas. Lo
    que lo evito fue ver que habia DOS preguntas que parecen la misma:

        ¿puedo verificar contra la ley de entonces?   NO. Haria falta
                                                      guardar una copia del
                                                      corpus por consulta.
        ¿HA CAMBIADO la ley de entonces?              SI, y sin guardar nada
                                                      nuevo.

    La segunda se contesta con lo que YA hay en el expediente: `version_usada`
    va por cita en `verificacion_N.json` desde siempre. Comparar la version de
    entonces con la de ahora dice si el corpus se ha movido debajo.

    De las dos, solo una se puede contestar — y resulta que es la que hacia
    falta. Preguntar lo que se puede saber en vez de lo que se querria saber
    es la diferencia entre apagar el boton siempre y apagarlo cuando toca.

    SE COMPARA LA VERSION USADA, NO CUANTAS HAY. Que el corpus haya crecido con
    una consolidacion posterior al ejercicio no toca el texto que sostiene esta
    respuesta, y refusar ahi seria apagar por algo que no afecta.

    SIN VERIFICACION GUARDADA NO SE AFIRMA NADA: se devuelve que si. Un
    expediente que no dice con que versiones se comprobo no puede acusarse de
    haber cambiado, y es el mismo criterio que con el motor y con el material.
    """
    antes = versiones_de_la_primera(traza)
    if not antes:
        return True, ""
    movidos = []
    for d in dictamenes:
        clave = getattr(d, "clave", "")
        if getattr(d, "estado", "") != "VERIFICADA" or clave not in antes:
            continue
        v = getattr(d, "version_usada", None) or {}
        ahora = {"orden": v.get("orden"),
                 "fecha_vigencia_efectiva": v.get("fecha_vigencia_efectiva")}
        if ahora != antes[clave]:
            movidos.append(getattr(d, "referencia_corpus", "") or clave)
    if not movidos:
        return True, ""
    return False, (
        "no se reescribe: desde que se contesto esta consulta ha cambiado el "
        "texto de " + ", ".join(sorted(set(movidos))[:3])
        + ". La respuesta de arriba sigue siendo la que se comprobo aquel dia; "
        "una version «para el cliente» citaria la ley de hoy razonando sobre "
        "la de entonces. Si el caso sigue vivo, haz la consulta de nuevo.")


def versiones_de_la_primera(traza: Path | str) -> dict:
    """Con QUE VERSION de cada precepto se comprobo la respuesta que se enseño.

    Es lo que permite saber si el corpus se ha movido debajo de un expediente:
    `version_usada` va guardada por cita en `verificacion_N.json` desde
    siempre, y comparar la de entonces con la de ahora contesta la pregunta sin
    tener que guardar una copia de la ley.

    Devuelve {clave: {"orden": n, "fecha_vigencia_efectiva": "..."}}.
    """
    import json
    d = Path(traza)
    ultima = None
    for f in sorted(d.glob("verificacion_*.json")):
        if f.name.startswith("verificacion_para_cliente"):
            continue
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if j.get("veredicto") == "ACEPTADO":
            ultima = j
    if not ultima:
        return {}
    fuera = {}
    for c in ultima.get("citas") or []:
        if c.get("estado") != "VERIFICADA" or not c.get("clave"):
            continue
        v = c.get("version_usada") or {}
        fuera[c["clave"]] = {
            "orden": v.get("orden"),
            "fecha_vigencia_efectiva": v.get("fecha_vigencia_efectiva"),
        }
    return fuera
