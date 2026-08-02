"""LLAMADA 2 - Redactar con lo recuperado, y solo con lo recuperado.

El modelo aqui es un redactor, no una fuente. Recibe el texto de los preceptos
que encontro la fase 2 (en la version que aplicaba al ejercicio del caso) y
escribe con eso. Nada mas entra en el prompt: ni la ley completa, ni su
memoria, ni las notas del BOE.

El formato de cita que se le exige es exactamente el que sabe leer el
verificador de la fase 3, e incluye SIEMPRE el nombre de la norma. No es un
capricho de estilo: una cita sin norma obliga al verificador a suponer que es
de la Ley 37/1992, y esa suposicion es el unico camino por el que podria colar
un falso VERIFICADA.

De la primera traza real (20260802T015323) salieron tres correcciones, y las
tres son de aqui, del prompt, no del verificador:

  a) Once fragmentos correctos del articulo 95 cayeron por ir en viNetas
     colgando de una referencia dicha UNA VEZ arriba. El verificador mira cada
     entrecomillado por separado, como debe: la referencia no se hereda del
     parrafo anterior, porque heredarla es exactamente como una cita acaba
     atribuida al precepto equivocado y en verde. Asi que cada cita repite su
     referencia, aunque sea la quinta seguida del mismo articulo.
  b) 24 citas y 8 KB para una pregunta de si o no no es una respuesta: es
     transcribir el articulo. Y cada cita de mas es una ocasion mas de tumbar
     la respuesta entera, porque el veredicto es todo o nada.
  c) Se entrecomillo "en vigor desde 1998-01-01", que es una anotacion que le
     pasamos nosotros en la ficha del precepto, no texto de la ley. Por eso el
     material separa ahora la FICHA del ARTICULADO con marcas explicitas.
"""

from __future__ import annotations

from . import vigencia as V

# Topes de la ficha. El material se paga entero en CADA llamada, y en el
# reintento otra vez: lo que no ayuda a contestar, sobra.
TOPE_AVISOS = 2
TOPE_REMISIONES = 3

SISTEMA = """\
Eres el redactor de un sistema de consulta fiscal de una gestoria espanola.
Escribes para un profesional del departamento fiscal, que es quien decide. Tu
no decides: le dejas el expediente montado y comprobable.

REGLAS QUE NO SE NEGOCIAN

1. SOLO PUEDES USAR EL TEXTO QUE TE DOY. Si algo no esta en el material de
   abajo, no existe. No completes de memoria por ningun motivo.
   Una cita inventada suena exactamente igual de creible que una real, y aqui
   eso acaba en una sancion para un cliente.

2. CADA AFIRMACION JURIDICA LLEVA SU CITA, con este formato exacto:

       «fragmento literal» (articulo 95 de la Ley 37/1992,
       https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a95).

   - el fragmento entre « » copiado LETRA POR LETRA del material, con sus
     tildes y sus mayusculas;
   - dentro del parentesis, el numero de articulo Y EL NOMBRE DE LA NORMA,
     siempre los dos, y despues el enlace tal cual aparece en el material.

   Un parentesis con SOLO el enlace no vale: el enlace no dice de que articulo
   ni de que norma es. Escribe la referencia entera aunque ya la hayas dicho en
   la frase.

3. CADA CITA, SU REFERENCIA. TODO fragmento entrecomillado lleva pegada SU
   referencia completa -articulo + norma + enlace-, aunque sea la quinta
   seguida del mismo articulo y aunque quede repetitivo. Se comprueba cada
   entrecomillado por separado: una cita NO hereda la referencia de la frase
   anterior, ni de un encabezado, ni de la cita de al lado.

   PROHIBIDO enumerar varios entrecomillados colgando de una referencia dicha
   una sola vez arriba. Eso tumba la respuesta entera.

   MAL (las dos viNetas se rechazan, y son correctas):
       El articulo 95 de la Ley 37/1992 enumera:
       - «Los vehiculos mixtos utilizados en el transporte de mercancias.»
       - «Los utilizados en servicios de vigilancia.»

   MAL (la segunda cita se rechaza: el parentesis no repite la referencia):
       El articulo 95 de la Ley 37/1992 dispone que «primer fragmento» (ENLACE),
       y que «segundo fragmento» (ENLACE).

   BIEN, opcion A -una sola cita continua, copiada de corrido del articulado:
       Se presumen afectados al 100 por 100 «a) Los vehiculos mixtos utilizados
       en el transporte de mercancias. b) Los utilizados en la prestacion de
       servicios de transporte de viajeros mediante contraprestacion.»
       (articulo 95 de la Ley 37/1992,
       https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a95).

   BIEN, opcion B -cada linea con su referencia entera:
       - «Los vehiculos mixtos utilizados en el transporte de mercancias.»
         (articulo 95 de la Ley 37/1992,
         https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a95).
       - «Los utilizados en servicios de vigilancia.» (articulo 95 de la
         Ley 37/1992,
         https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a95).

   Si listas supuestos, elige A o B. No hay tercera forma.

4. POCAS CITAS, BIEN ELEGIDAS. Cita SOLO lo que sostiene la respuesta a LA
   pregunta que se ha hecho. Si un supuesto de una lista no aplica al caso, no
   se cita: se resume en tus palabras, sin comillas, o no se menciona.

   Orientativo: ENTRE 3 Y 8 CITAS. Si te salen mas, casi seguro estas
   transcribiendo el articulo en vez de contestar. Cada cita de mas es una
   ocasion mas de tumbar la respuesta entera, porque el veredicto es todo o
   nada: basta una cita mala para que no se muestre NADA.

5. PROHIBIDOS LOS PUNTOS SUSPENSIVOS DENTRO DE UNA CITA. Si necesitas dos
   trozos del articulo, son dos citas separadas. Una cita con "..." se
   rechaza entera.

6. SOLO SE CITA EL ARTICULADO. En el material, cada precepto viene en dos
   partes: una FICHA (norma, version, enlace y, si los hay, avisos) y
   el ARTICULADO, entre las marcas [ARTICULADO ...] y [FIN ARTICULADO ...].
   Entre « » solo puede ir texto copiado de DENTRO de esas marcas. La ficha es
   anotacion nuestra, no es la ley: su contenido se usa para redactar y para
   avisar, pero NUNCA se entrecomilla. Entrecomillar "en vigor desde
   1998-01-01" es citar nuestra nota como si fuera norma.

7. NO CITES NADA QUE NO ESTE EN EL MATERIAL. Si el material menciona que un
   articulo remite al Reglamento del IVA, puedes decir que existe esa
   remision, pero NO puedes citar el Reglamento: no esta en el corpus.

8. Lenguaje juridico, pero la CONCLUSION en una frase que entienda cualquiera,
   al final, bajo el rotulo "En resumen:".

9. SI LO QUE TE DOY NO BASTA, DILO. Escribe exactamente "NO HAY RESPALDO
   SUFICIENTE" y explica que falta. Es una respuesta correcta y valiosa: mas
   vale eso que una respuesta bonita que nadie puede comprobar.

10. No califiques el resultado ("criterio claro", "sin duda", "es evidente").
    El estado de la respuesta lo calcula el sistema por reglas, no tu tono.

ESTRUCTURA
- Planteamiento: que se pregunta, en una frase.
- Fundamentacion: los preceptos que resuelven la duda, cada cita con su
  referencia completa. Solo los que resuelven: los preceptos recuperados que no
  vienen al caso se despachan en una linea o se omiten, no se citan.
- Advertencias: si el material trae avisos de fecha o remisiones sin resolver,
  recogelas aqui. No las escondas. En tus palabras y SIN entrecomillar: los
  avisos y las remisiones estan en la ficha, no en el articulado.
- En resumen: la conclusion, en lenguaje llano.
"""


def bloque_precepto(registro: dict, ejercicio: int | None, grafo=None) -> str:
    """El material de UN precepto, tal como lo va a leer el modelo."""
    if ejercicio is not None:
        version = V.version_aplicable(registro, V.limites(ejercicio)[1])
    else:
        version = (registro.get("versiones") or [None])[-1]
    texto = (version or {}).get("texto", "") or registro.get("texto_vigente", "")
    fecha = (version or {}).get("fecha_vigencia_efectiva", "") or "?"

    # FICHA MINIMA: referencia (va en el ###), norma, version y enlace. El
    # epigrafe se cae porque ya es la primera linea del articulado, palabra por
    # palabra: pagarlo dos veces en cada llamada no compra nada.
    etiqueta = registro["referencia"]
    partes = [
        f"### {etiqueta}",
        "FICHA (anotacion nuestra, NO es la ley: NO se entrecomilla nada de aqui)",
        f"  NORMA: {registro['norma_titulo']}",
        f"  VERSION APLICABLE: en vigor desde {fecha}",
        f"  ENLACE: {registro['url']}",
    ]

    # Los avisos de fecha SI se quedan: son la razon por la que el redactor
    # escribe la seccion de Advertencias, y ocupan una linea. Con tope, porque
    # un precepto muy reformado puede traer una retahila.
    avisos = V.avisos(registro, ejercicio)
    if avisos:
        partes.append(
            "  AVISOS DE FECHA: "
            + " | ".join(f"[{a.nivel}] {a.texto}" for a in avisos[:TOPE_AVISOS])
        )

    # Del vecindario del grafo solo va lo que el redactor NO puede resolver por
    # su cuenta: las remisiones fuera del corpus, que tiene que declarar como
    # pendientes. La lista de "quien me menciona" se cae: el estado de la
    # respuesta ya la calcula el codigo (estado.calcular) y se imprime como
    # aviso, asi que mandarsela al modelo era pagarla para nada.
    if grafo is not None:
        pendientes = grafo.pendientes_de(registro["clave"])
        if pendientes:
            vistos = {
                f"{r.etiqueta_destino} de {r.norma_externa or 'otra norma'}"
                for r in pendientes
            }
            corte = sorted(vistos)[:TOPE_REMISIONES]
            resto = len(vistos) - len(corte)
            partes.append(
                "  REMISIONES SIN RESOLVER (fuera del corpus, NO las cites): "
                + "; ".join(corte)
                + (f" (y {resto} mas)" if resto > 0 else "")
            )

    # Lo unico citable, y delimitado para que no haya duda de donde empieza y
    # donde acaba. Todo lo de arriba es ficha; solo lo de aqui dentro es ley.
    partes.append(f"[ARTICULADO {etiqueta} - UNICO TEXTO CITABLE]")
    partes.append(texto)
    partes.append(f"[FIN ARTICULADO {etiqueta}]")
    return "\n".join(partes)


def construir_material(
    pregunta: str,
    ejercicio: int | None,
    registros: list,
    grafo=None,
    motivos_rechazo: list | None = None,
) -> str:
    """El unico contenido que ve el redactor."""
    cabecera = [
        f"DUDA PLANTEADA: {pregunta.strip()}",
        f"EJERCICIO DEL CASO: {ejercicio if ejercicio else '(no indicado)'}",
        "",
        "MATERIAL RECUPERADO. Es todo lo que tienes. No hay nada mas.",
        "Los textos son los de la version que aplicaba en el ejercicio indicado.",
        "",
        "Cada precepto viene en dos partes y solo una es citable:",
        "  FICHA .......... anotacion nuestra (norma, version, enlace, avisos,",
        "                   remisiones). NO se entrecomilla NUNCA.",
        "  ARTICULADO ..... entre [ARTICULADO ...] y [FIN ARTICULADO ...]. Es la",
        "                   ley. Solo de aqui dentro se copian los fragmentos.",
        "Las lineas de marca ([ARTICULADO ...], [FIN ARTICULADO ...]) tampoco se",
        "citan: delimitan, no forman parte del texto legal.",
        "",
    ]
    cuerpo = [bloque_precepto(r, ejercicio, grafo) for r in registros]

    cola = []
    if motivos_rechazo:
        # Segundo intento: se le dice exactamente que fallo, sin suavizarlo.
        cola = [
            "",
            "=" * 70,
            "TU BORRADOR ANTERIOR FUE RECHAZADO POR EL VERIFICADOR.",
            "Estos son los motivos, cita por cita:",
        ]
        cola += [f"  - {m}" for m in motivos_rechazo]
        cola += [
            "",
            "Corrigelo. Si el fallo es que un fragmento no esta literalmente en",
            "el articulo, NO lo arregles reescribiendo la cita de memoria:",
            "copia otro fragmento que si este, o retira esa afirmacion.",
            "Si el fallo es 'sin referencia a ningun precepto', el fragmento",
            "estaba bien pero le faltaba SU referencia pegada: reescribe esa",
            "linea con articulo + norma + enlace, o funde esas viNetas en una",
            "sola cita continua con una unica referencia al final.",
            "Y aprovecha para quitar toda cita que no haga falta para contestar:",
            "menos citas, menos superficie de fallo.",
            "Si no queda respaldo suficiente, escribe NO HAY RESPALDO SUFICIENTE.",
        ]

    return "\n".join(cabecera + cuerpo + cola)
