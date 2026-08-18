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
