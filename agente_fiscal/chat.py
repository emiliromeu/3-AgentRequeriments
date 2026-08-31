"""UNA CONSULTA ES UNA CONVERSACION, Y ESTO ES LA CONVERSACION COMO DATO.

Aqui NO se pinta nada y NO se decide nada de una respuesta: se lee lo que hay en
disco y se agrupa en la forma que hace falta para enseñarlo como un chat. Quien
quiera el contenido de una vuelta va a `ver_ejemplo.cargar`, que lo reconstruye
del expediente sin inventarse un dato.

----------------------------------------------------------------------------
QUE ES UN CHAT AQUI, Y QUE NO CAMBIA POR DEBAJO
----------------------------------------------------------------------------
Un chat es UNA CADENA DE EXPEDIENTES: cada vuelta es un expediente propio y
lleva de cual viene (`viene_de`). Eso ya existia y no se toca, porque es lo que
sostiene la regla que no se negocia:

    CADA VUELTA ES UNA CONSULTA ENTERA. Se reanaliza, se vuelve a buscar y se
    verifica de cero contra SU material.

No hay «una conversacion» guardada en ningun sitio: hay expedientes encadenados,
y la conversacion se reconstruye leyendolos. Guardarla como una cosa sola seria
perder que cada respuesta se comprobo contra un material concreto en un momento
concreto, que es lo unico que permite auditarla dentro de seis meses.

Esta medido y no es teorico: sobre 327 vueltas con vuelta anterior localizable,
en 93 -el 28%- el material CAMBIO entre una y la siguiente. Reutilizarlo daria,
una de cada cuatro veces, una respuesta impecable sobre los articulos
equivocados.

----------------------------------------------------------------------------
LO QUE UN CHAT NORMAL NO TIENE, Y AQUI ES EL PRODUCTO
----------------------------------------------------------------------------
En una conversacion corriente todos los mensajes valen igual y el ultimo manda.
Aqui no: cada vuelta trae SU estado, SUS citas y SU material, verificados en
momentos distintos. Dos consecuencias que esta pieza tiene que saber decir:

  · DE QUE VUELTA ES CADA COSA. No basta con el orden: hace falta el numero, la
    hora y con que se contesto.
  · Y SI UNA VUELTA HA QUEDADO SUPERADA por otra posterior. Hasta ahora se
    resolvia por amputacion -se enseñaba solo la ultima-; en un chat conviven,
    y hay texto verificado contra materiales distintos en la misma pantalla.

Ver `desfases`, que es donde vive esa comparacion.
"""

from __future__ import annotations

from . import expedientes as EX

# Cuanto del texto de la primera pregunta se usa como nombre del chat. En la
# barra lateral no cabe mas, y el nombre entero esta en la primera burbuja.
LARGO_TITULO = 60


def _titulo(pregunta: str) -> str:
    """El nombre del chat: su primera pregunta, recortada por una palabra.

    NO SE INVENTA UN TITULO NI SE PIDE AL MODELO. Cortar la pregunta es
    reversible y honesto -quien lo lee reconoce lo que escribio-; un titulo
    generado seria una interpretacion que cuesta una llamada y que puede no
    parecerse a lo que se pregunto.
    """
    limpia = " ".join((pregunta or "").split())
    if not limpia:
        return "(sin pregunta)"
    if len(limpia) <= LARGO_TITULO:
        return limpia
    return limpia[:LARGO_TITULO].rsplit(" ", 1)[0] + "…"


def desfases(vueltas: list) -> dict:
    """Que vueltas han quedado atras, y por que. {sello: motivo}.

    ────────────────────────────────────────────────────────────────────────
    ES COMPUTABLE, NO UNA IMPRESION
    ────────────────────────────────────────────────────────────────────────
    Cada expediente guarda los preceptos que sostienen su respuesta y el
    ejercicio con el que se contesto. Comparar una vuelta con las siguientes
    dice, sin opinar, si lo que hay en pantalla se contesto sobre otra base.

    TRES CASOS, Y NO SE DICEN IGUAL:

      MISMO MATERIAL ......... la vuelta nueva PRECISA. Nada queda atras y no
                               se avisa de nada: un aviso que sale siempre no
                               es un aviso.
      MATERIAL DISTINTO ...... la anterior no esta mal, esta contestada SOBRE
                               OTRA BASE, y puede seguir siendo valida para lo
                               que preguntaba. Se dice, sin tacharla.
      OTRO AÑO O COMUNIDAD ... la anterior esta contestada CON OTRA LEY. Esto
                               si es quedar superada.

    EL TERCERO HOY NO OCURRE NUNCA -0 de 327 vueltas medidas- porque al seguir
    un hilo el año no se puede cambiar. En cuanto la cabecera del chat sea
    editable empezara a ocurrir: es el fallo silencioso del año reapareciendo
    dentro de una conversacion, y por eso esto se escribe ANTES de abrir el
    campo y no despues.

    SOLO SE MIRA HACIA DELANTE. Una vuelta la puede superar una posterior,
    nunca una anterior: el tiempo va en un solo sentido y comparar al reves
    diria que la primera pregunta «supera» a la ultima.
    """
    fuera: dict = {}
    for i, v in enumerate(vueltas[:-1]):
        posteriores = vueltas[i + 1:]
        # 1 · el ejercicio o la comunidad cambiaron: otra ley.
        distinto = [p for p in posteriores
                    if (p.get("ejercicio") or "") != (v.get("ejercicio") or "")
                    or (p.get("comunidad") or "") != (v.get("comunidad") or "")]
        if distinto:
            p = distinto[0]
            trozos = []
            if (p.get("ejercicio") or "") != (v.get("ejercicio") or ""):
                trozos.append(f"el ejercicio pasó de {v.get('ejercicio') or '—'}"
                              f" a {p.get('ejercicio') or '—'}")
            if (p.get("comunidad") or "") != (v.get("comunidad") or ""):
                trozos.append(f"la comunidad pasó de "
                              f"{v.get('comunidad') or 'ninguna'} a "
                              f"{p.get('comunidad') or 'ninguna'}")
            fuera[v["sello"]] = ("otra ley", "Contestada antes de que "
                                 + " y ".join(trozos)
                                 + ": léela sabiendo que es de otra redacción "
                                   "de la norma.")
            continue
        # 2 · el material cambio: contestada sobre otra base.
        #
        # SE COMPARA CONTRA LA SIGUIENTE, no contra la ultima: lo que dice algo
        # es que la base cambio en el paso siguiente. Con la ultima, una
        # conversacion larga marcaria todo lo de en medio por acumulacion.
        sig = posteriores[0]
        mio = set(v.get("preceptos") or [])
        suyo = set(sig.get("preceptos") or [])
        if mio and suyo and mio != suyo:
            fuera[v["sello"]] = (
                "otra base",
                "La vuelta siguiente se apoya en otros artículos: ésta sigue "
                "valiendo para lo que preguntaba, pero no es la respuesta al "
                "caso completo.")
    return fuera


def de_expedientes(filas: list) -> list:
    """Las filas del indice -> la lista de chats, del mas nuevo al mas viejo.

    Cada chat es un dict con lo que necesita la barra lateral y la cabecera:

        sello ....... el de la PRIMERA vuelta. Es la identidad del chat: no
                      cambia al añadir vueltas, asi que sirve para recordar
                      cual estaba abierto.
        titulo ...... la primera pregunta, recortada
        vueltas ..... las filas, de la mas vieja a la mas nueva
        ejercicio ... el del chat. Ver abajo.
        comunidad ... idem
        estado ...... el de la ULTIMA vuelta, que es la que manda
        desfases .... {sello: (clase, motivo)} de las que han quedado atras
        dia, hora ... de la ultima vuelta, para agrupar la lista

    EL AÑO Y LA COMUNIDAD SALEN DE LA ULTIMA VUELTA, NO DE LA PRIMERA. Es lo
    contrario de lo que parece «heredar», y es a proposito: si en la vuelta 3
    se corrigio el año, el chat ES de ese año a partir de ahi, y la cabecera
    tiene que decir con que se esta contestando AHORA. Lo que paso antes no se
    pierde: cada vuelta guarda el suyo, y `desfases` avisa de la que quedo
    detras.
    """
    chats = []
    for cadena in EX.hilos(filas):
        primera, ultima = cadena[0], cadena[-1]
        dia, hora = EX.fecha_de(ultima["sello"])
        chats.append({
            "sello": primera["sello"],
            "titulo": _titulo(primera.get("pregunta", "")),
            "vueltas": cadena,
            "ejercicio": ultima.get("ejercicio") or "",
            "comunidad": ultima.get("comunidad") or "",
            "estado": ultima.get("estado") or "",
            "con_criterio": bool(ultima.get("con_criterio")),
            "desfases": desfases(cadena),
            "dia": dia,
            "hora": hora,
        })
    return chats


def por_dia(chats: list) -> list:
    """[(dia, [chats de ese dia])], en el orden en que se enseñan.

    Se agrupa por dia porque es como se busca una consulta: «la del martes».
    El dia sale del sello de la carpeta, asi que no cuesta abrir nada.
    """
    fuera: list = []
    for c in chats:
        if fuera and fuera[-1][0] == c["dia"]:
            fuera[-1][1].append(c)
        else:
            fuera.append((c["dia"], [c]))
    return fuera
