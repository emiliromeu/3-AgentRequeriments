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

import re
from dataclasses import dataclass, field

from . import vigencia as V

# Topes de la ficha. El material se paga entero en CADA llamada, y en el
# reintento otra vez: lo que no ayuda a contestar, sobra.
TOPE_AVISOS = 2
TOPE_REMISIONES = 3

# ---------------------------------------------------------------------------
# LA LEY NO PUEDE SER EL 17% DEL MATERIAL
# ---------------------------------------------------------------------------
# Medido sobre las 19 consultas del banco con las tres fuentes encendidas: la
# ley eran 18.100 caracteres de 109.130 de media -el 17%- y en el peor caso el
# 7%. Cuatro de cada cinco caracteres que leia el redactor eran criterio
# administrativo. La causa: se mandaba la CONTESTACION ENTERA de hasta tres
# consultas de la DGT, y una contestacion real ronda de 20 a 78 KB.
#
# La ley es la pata portante. Que vaya primera en el orden no sirve de nada si
# va sepultada en el volumen, porque el orden se ve leyendo y el volumen pesa
# sin que nadie lo lea. Asi que dos reglas, las dos medibles:
#
#   1. DE CADA CONSULTA, SOLO LOS FRAGMENTOS PERTINENTES. Seleccion
#      ESTRUCTURAL: los parrafos que mencionan los articulos en juego y su
#      entorno inmediato. NUNCA resumen ni interpretacion: lo que se manda
#      sigue siendo literal y por tanto verificable letra por letra.
#
#   2. TOPE RELATIVO: el bloque de criterio -TEAC y DGT juntos- no puede pasar
#      del tamaño del bloque de ley. La norma manda, y eso se tiene que ver en
#      el material, no solo en el orden.
#
# Y si al recortar una consulta se queda sin nada pertinente, NO SE MANDA.
# Mejor dos consultas utiles que tres a medias.
#
# Todo lo que se recorta queda contado en `Recorte` y se escribe en la traza:
# el dia que falte un fragmento tiene que poder verse, no adivinarse.

# Parrafos de entorno inmediato que se arrastran a cada lado del que menciona
# el articulo. Existe porque el parrafo siguiente suele ser el que dice «dicho
# precepto debe interpretarse...», y sin el, el fragmento pertinente se queda
# sin su consecuencia.
ENTORNO = 1

# «articulo 80», «articulos 78 y 80», «articulo 80 bis»
_RE_MENCION_ART = re.compile(
    r"\bart[íi]culos?\s+(?P<num>\d+(?:\s*(?:bis|ter|qu[aá]ter|quinquies|"
    r"sexies|septies|octies|nonies|decies))?)", re.IGNORECASE)

# Cuanto se mira DESPUES del numero para ver de que norma es ese articulo.
# «el articulo 80, apartado cuatro, de la Ley 37/1992» cabe de sobra.
VENTANA_NORMA = 30

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


# ------------------------------------------------------- el recorte, y su cuenta


@dataclass
class Recorte:
    """Lo que se ha mandado de una fuente y lo que se ha dejado fuera.

    Existe para que el recorte se pueda AUDITAR. Un sistema que manda menos
    material y no dice cuanto menos es indistinguible de uno que perdio texto
    por un fallo.
    """

    fuente: str                    # «V1601-22» o el numero de resolucion
    completo: int = 0              # caracteres del texto original
    enviado: int = 0               # caracteres del texto mandado
    parrafos: int = 0
    parrafos_enviados: int = 0
    fragmentos: int = 0
    motivo: str = ""               # por que se recorto, o por que no se manda

    @property
    def se_manda(self) -> bool:
        return self.enviado > 0

    def a_json(self) -> dict:
        return {
            "fuente": self.fuente,
            "caracteres_completo": self.completo,
            "caracteres_enviado": self.enviado,
            "parrafos": self.parrafos,
            "parrafos_enviados": self.parrafos_enviados,
            "fragmentos": self.fragmentos,
            "omitido": max(0, self.completo - self.enviado),
            "motivo": self.motivo,
        }


@dataclass
class Plan:
    """El material de criterio ya recortado, con su cuenta al lado."""

    bloques_teac: list = field(default_factory=list)   # doctrina del TEAC
    bloques_dgt: list = field(default_factory=list)
    # Tribunales REGIONALES, en bloque aparte. No es un capricho de formato:
    # un TEAR no vincula a nadie, y presentarlo junto a la doctrina del TEAC
    # es decir que si. Ver BLOQUE_TEAR.
    bloques_tear: list = field(default_factory=list)
    recortes: list = field(default_factory=list)
    # Las consultas de la DGT cuyo texto SI esta en el material. Lo que no esta
    # aqui no se puede nombrar en una señal: la señal y el material no se
    # pueden contradecir, porque el redactor no puede citar lo que no ve.
    enviadas: list = field(default_factory=list)
    ley: int = 0            # tamaño del bloque de ley: el presupuesto
    criterio: int = 0       # lo que ocupa el criterio ya recortado

    @property
    def proporcion_ley(self) -> float:
        total = self.ley + self.criterio
        return (self.ley / total) if total else 1.0

    def a_json(self) -> dict:
        return {
            "caracteres_ley": self.ley,
            "caracteres_criterio": self.criterio,
            "proporcion_ley": round(self.proporcion_ley, 3),
            "presupuesto_criterio": self.ley,
            "consultas_con_texto_en_el_material": list(self.enviadas),
            "fuentes": [r.a_json() for r in self.recortes],
        }


def _objetivo(registros: list) -> tuple:
    """(numeros, cuerpos) de los preceptos que sostienen la respuesta."""
    numeros, cuerpos = set(), set()
    for r in registros or []:
        num = str(r.get("referencia", "")).replace("Articulo ", "").strip().lower()
        if num:
            numeros.add(re.sub(r"\s+", " ", num))
        if r.get("cuerpo_clave"):
            cuerpos.add(r["cuerpo_clave"])
    return numeros, cuerpos


def _es_de_otra_norma(parrafo: str, fin: int, cuerpos: set, normas=None) -> bool:
    """¿El articulo que se acaba de mencionar es de OTRA norma?

    ES LA LECCION DE SIEMPRE, aplicada aqui: «el articulo 80 de la Ley 35/2006»
    no es nuestro articulo 80. Se mira solo la ventana inmediata, porque una
    norma nombrada tres frases despues no califica a este articulo.

    Se descarta el parrafo en dos casos, y solo en dos:
      · la norma nombrada esta cargada y NO es de las nuestras;
      · la norma nombrada NO esta en el corpus (es externa). Que no la
        tengamos no la hace nuestra: «Ley 35/2006» resuelve a «externa», y
        tratar eso como «no se nombro norma» era dejar pasar justo el caso
        que esta funcion existe para parar.

    Cuando la mencion NO nombra norma -«el citado articulo 80», la forma mas
    comun dentro de una contestacion- el parrafo CUENTA. Es deliberado: aqui un
    falso positivo manda un parrafo de mas y un falso negativo tira texto
    pertinente al suelo. Lo primero se paga en caracteres; lo segundo, en una
    respuesta peor. Y esto NO produce ninguna señal: solo elige que se manda.
    """
    from . import dgt as _D

    if normas is None or not cuerpos:
        return False
    cola = parrafo[fin:fin + VENTANA_NORMA]
    m = _D._RE_NORMA_EXPLICITA.search(cola)
    if not m:
        return False        # no se nombra norma: se le da el beneficio
    cuerpo, estado = _D._resolver_designacion(m.group(0), normas)
    if estado == "cargada":
        return cuerpo not in cuerpos
    if estado == "externa":
        return True         # se nombro una norma, y no es ninguna de las nuestras
    return False            # ambiguo: no se descarta por una suposicion


def fragmentos_pertinentes(texto: str, registros: list, normas=None) -> tuple:
    """(fragmentos, n_parrafos, n_enviados). Seleccion estructural, literal.

    Ni una palabra se reescribe: se eligen parrafos enteros y se devuelven tal
    cual. Los parrafos elegidos que iban seguidos se juntan en un fragmento; un
    salto entre fragmentos es un hueco REAL en el documento, y por eso se marca
    en el material, para que el redactor no cite de un lado a otro.
    """
    numeros, cuerpos = _objetivo(registros)
    parrafos = [p.strip() for p in (texto or "").split("\n") if p.strip()]
    if not parrafos or not numeros:
        return [], len(parrafos), 0

    marcados = set()
    for i, p in enumerate(parrafos):
        for m in _RE_MENCION_ART.finditer(p):
            num = re.sub(r"\s+", " ", m.group("num")).strip().lower()
            if num not in numeros:
                continue
            if _es_de_otra_norma(p, m.end(), cuerpos, normas):
                continue          # es ese articulo, pero de otra norma
            marcados.add(i)
            break

    if not marcados:
        return [], len(parrafos), 0

    # El entorno inmediato: sin el, un parrafo que dice «dicho precepto» se
    # queda sin la frase que explica que hace ese precepto.
    con_entorno = set()
    for i in marcados:
        for j in range(i - ENTORNO, i + ENTORNO + 1):
            if 0 <= j < len(parrafos):
                con_entorno.add(j)

    fragmentos, actual = [], []
    for i in sorted(con_entorno):
        if actual and i != actual[-1] + 1:
            fragmentos.append("\n\n".join(parrafos[j] for j in actual))
            actual = []
        actual.append(i)
    if actual:
        fragmentos.append("\n\n".join(parrafos[j] for j in actual))
    return fragmentos, len(parrafos), len(con_entorno)


BLOQUE_TEAC = """
======================================================================
DOCTRINA DEL TEAC (Tribunal Economico-Administrativo Central)
======================================================================

LEE ESTO ANTES DE USARLO:

  Un criterio del TEAC NO ES UNA NORMA, pero cuando SIENTA DOCTRINA VINCULA
  A TODA LA ADMINISTRACION TRIBUTARIA (art. 239.8 de la Ley 58/2003). Pesa
  MAS que una consulta de la DGT, que solo vincula frente a quien consulto,
  y MENOS que la ley, que es la unica que fundamenta.

  NO TODO LO DE AQUI VINCULA. Cada resolucion trae su campo FUERZA, que sale
  de la calificacion que le da la propia fuente. Si dice que no vincula, no
  vincula: no lo presentes como si obligara.

  LA JERARQUIA MANDA EN EL ORDEN DE LA RESPUESTA:

      LEY  ->  doctrina del TEAC  ->  consultas de la DGT  ->  resoluciones
      de tribunales REGIONALES (TEAR)

  Cada bloque en parrafo aparte y etiquetado. Nunca los mezcles: quien lee
  tiene que saber en todo momento si lo que esta leyendo es norma, doctrina
  de un tribunal, criterio administrativo o un caso regional.

  Si un criterio dice UNIFICACION DE CRITERIO, dilo: pesa mas que un
  criterio suelto, porque unifica la doctrina para toda la Administracion.

  FORMATO DE LA CITA DEL TEAC, distinto del de la ley Y del de la DGT:

      «fragmento literal» {Criterio TEAC 00/06614/2024/00/00, de
      21/05/2026, TEAC — https://serviciostelematicosext.hacienda.gob.es/...}

  Llaves. La ley va con parentesis y la DGT con corchetes: tres fuentes,
  tres formas, y no hace falta leer para saber cual es cual.

  Se comprueba igual de estricto: el fragmento tiene que estar LETRA POR
  LETRA en el texto de abajo.
"""

BLOQUE_TEAR = """
======================================================================
RESOLUCIONES DE TRIBUNALES REGIONALES (TEAR)
======================================================================

LEE ESTO ANTES DE USARLO, PORQUE NO ES LO MISMO QUE LO DE ARRIBA:

  UNA RESOLUCION DE UN TEAR NO ES DOCTRINA Y NO VINCULA A NADIE mas que al
  caso que resuelve. No la llames «criterio», no la llames «doctrina» y no
  digas que la Administracion esta obligada a seguirla, porque no lo esta.
  La doctrina la sienta el TEAC; un TEAR resuelve reclamaciones.

  ENTONCES, ¿PARA QUE SIRVE? Para otra cosa, y muy util: es lo mas
  informativo que hay sobre QUE LE VA A PASAR de hecho a un cliente de esta
  provincia, porque es el tribunal que le va a tocar. Valor predictivo, no
  fuerza juridica. Son dos ejes distintos y no se pueden mezclar.

  COMO SE PRESENTA, si la usas: en parrafo aparte, DESPUES de la ley, de la
  doctrina del TEAC y del criterio de la DGT, y diciendo lo que es:
  «el TEAR de Cataluña, en un caso semejante, resolvio que...».

  FORMATO DE LA CITA, con el tribunal DENTRO del rotulo:

      «fragmento literal» {Resolucion del TEAR de Cataluña
      08/02042/2022/00/00, de 21/09/2022 —
      https://serviciostelematicosext.hacienda.gob.es/...}

  Se comprueba igual de estricto que todo lo demas -letra por letra- Y
  ADEMAS se comprueba que el rotulo diga el tribunal que de verdad la
  dicto. Presentar una resolucion regional como criterio del TEAC tumba la
  respuesta entera.
"""


def bloque_criterio_teac(c) -> str:
    """Una resolucion cacheada, para el material. Solo campos del registro.

    El rotulo y la FUERZA salen de `unidad` y `calificacion`, que los pone la
    fuente. Aqui no se afirma que algo vincule si DYCTEA no lo dice.
    """
    partes = [
        "",
        f"[{c.etiqueta.upper()} {c.resolucion}]",
        f"  fecha        : {c.fecha or '(no consta)'}",
        f"  unidad       : {c.unidad or '(no consta)'}",
        f"  calificacion : {c.calificacion or '(no consta)'}",
        f"  FUERZA       : {c.fuerza}",
    ]
    if c.unifica_criterio:
        partes.append("  UNIFICACION DE CRITERIO: si (vincula a toda la Administracion)")
    if c.referencias:
        partes.append("  normativa que cita:")
        for ref in c.referencias:
            partes.append(f"    - {ref.get('norma','')}: "
                          f"{', '.join(ref.get('preceptos') or []) or '(sin precepto)'}")
    if c.consultas_dgt:
        partes.append(f"  consultas de la DGT que cita: {', '.join(c.consultas_dgt)}")
    partes += [
        f"  enlace       : {c.url}",
        f"  COMO SE CITA : {c.cita()}",
        "",
        f"  asunto: {c.asunto}",
        "",
        f"[TEXTO {c.resolucion}]",
        c.criterio,
        f"[FIN {c.resolucion}]",
    ]
    return "\n".join(partes)


BLOQUE_DGT = """
======================================================================
CRITERIO DE LA ADMINISTRACION (consultas de la Direccion General de Tributos)
======================================================================

LEE ESTO ANTES DE USARLO:

  Una consulta de la DGT NO ES UNA NORMA. Es el criterio que la
  Administracion aplica, y vincula a Hacienda frente a quien consulto, pero
  NO FUNDAMENTA POR SI SOLA. Ninguna afirmacion puede sostenerse solo en
  una consulta: primero la ley, y el criterio despues.

  EL ORDEN NO SE NEGOCIA. Primero lo que dice la norma, con sus citas. El
  criterio va DESPUES, en parrafo aparte, presentado como lo que es. Nunca
  mezcles norma y criterio en el mismo parrafo como si pesaran igual.

  FORMATO DE LA CITA DE CRITERIO, distinto del de la ley a proposito:

      «fragmento literal» [Consulta DGT V1601-22, de 01/07/2022 —
      https://petete.tributos.hacienda.gob.es/consultas/?num_consulta=V1601-22]

  Corchetes, el rotulo "Consulta DGT", el numero, la fecha y el enlace. Se
  comprueba igual de estricto que la ley: el fragmento tiene que estar
  LETRA POR LETRA en el texto de abajo.

  Si el criterio de una consulta no encaja con lo que dice la norma, DILO.
  No lo suavices y no elijas tu: quien decide es el profesional que lee.
"""


def bloque_consulta_dgt(c, fragmentos: list | None = None,
                        omitidos: int = 0) -> str:
    """Una consulta cacheada, para el material. Solo campos del registro.

    Con `fragmentos` va la contestacion RECORTADA: solo los trozos que hablan
    de los articulos en juego, literales, y con los huecos marcados. Sin
    `fragmentos` va entera, que es como iba antes del recorte.
    """
    partes = [
        "",
        f"[CONSULTA DGT {c.numero}]",
        f"  fecha      : {c.fecha or '(no consta)'}",
        f"  organo     : {c.organo or '(no consta)'}",
        f"  normativa  : {c.normativa or '(no consta)'}",
        f"  enlace     : {c.url}",
    ]
    if c.cuestion:
        partes += ["  cuestion planteada:", f"    {c.cuestion}"]

    if fragmentos is None:
        partes += [
            "",
            f"[CONTESTACION {c.numero}]",
            c.contestacion,
            f"[FIN CONTESTACION {c.numero}]",
        ]
        return "\n".join(partes)

    partes += [
        "",
        f"[CONTESTACION {c.numero} - FRAGMENTOS, no esta entera]",
        f"  De esta contestacion se te dan SOLO los {len(fragmentos)} "
        f"fragmento(s) que hablan de los articulos en juego"
        + (f"; se han omitido {omitidos} parrafo(s) que van de otra cosa."
           if omitidos else "."),
        "  Cada fragmento es LITERAL y se cita igual de estricto. Lo que NO",
        "  puedes hacer es citar de corrido de un fragmento a otro: entre uno",
        "  y otro falta texto, y esa cita no existe en el documento.",
    ]
    for n, frag in enumerate(fragmentos, 1):
        partes += [
            "",
            f"[FRAGMENTO {n} DE {c.numero}]",
            frag,
            f"[FIN FRAGMENTO {n} DE {c.numero}]",
        ]
    partes.append(f"[FIN CONTESTACION {c.numero}]")
    return "\n".join(partes)


def plan_de_criterio(
    registros: list,
    ejercicio: int | None,
    grafo=None,
    consultas_dgt: list | None = None,
    criterios_teac: list | None = None,
    normas=None,
) -> Plan:
    """Que criterio se manda, ya recortado y dentro del tope. Y que se deja.

    EL TOPE ES RELATIVO AL BLOQUE DE LEY, no un numero fijo de caracteres. Un
    numero fijo se queda corto en una consulta con seis articulos y sobra en
    una de uno solo; lo que hay que garantizar es la PROPORCION, porque de eso
    iba el problema.

    Se llena por jerarquia: primero el TEAC, que vincula a toda la
    Administracion, y con lo que quede la DGT. Si no cabe, lo que se cae es lo
    que menos pesa, y queda escrito en el `Recorte` que se cayo y por que.
    """
    plan = Plan()
    plan.ley = len("\n".join(bloque_precepto(r, ejercicio, grafo)
                             for r in (registros or [])))
    disponible = plan.ley

    # --- el TEAC va entero o no va -------------------------------------
    # El campo «criterio» de una resolucion ya es la doctrina destilada: son
    # unos miles de caracteres y trocearlo lo rompe. Asi que cabe o no cabe.
    #
    # Y SE PARTE EN DOS POR UNIDAD RESOLUTORIA: el TEAC aqui, los tribunales
    # regionales en su propio bloque y DESPUES de la DGT, que es el orden de
    # peso juridico. Mezclarlos era atribuirle a un TEAR la fuerza del
    # articulo 239.8 LGT, que no tiene.
    from . import teac as _T

    centrales = [c for c in (criterios_teac or []) if _T.es_central(c.unidad)]
    regionales = [c for c in (criterios_teac or []) if not _T.es_central(c.unidad)]

    for c in centrales:
        bloque = bloque_criterio_teac(c)
        r = Recorte(fuente=f"TEAC {c.resolucion}", completo=len(c.criterio or ""),
                    parrafos=1, fragmentos=1)
        coste = len(bloque) + (len(BLOQUE_TEAC) if not plan.bloques_teac else 0)
        if coste > disponible:
            r.motivo = ("no cabe en el tope: el criterio no puede ocupar mas "
                        "que la ley")
            plan.recortes.append(r)
            continue
        plan.bloques_teac.append(bloque)
        disponible -= coste
        r.enviado, r.parrafos_enviados = len(c.criterio or ""), 1
        plan.recortes.append(r)

    # --- la DGT, por fragmentos y CON CUOTA -----------------------------
    #
    # EL PRESUPUESTO NO SE LO PUEDE COMER EL PRIMERO. Llenando en orden, la
    # primera consulta se llevaba todo el hueco y las otras dos se quedaban a
    # cero. Y justo aqui eso es lo peor que puede pasar: el valor de esta capa
    # es ver que el criterio ha ido cambiando con los años, y para eso hacen
    # falta las tres, no una larga. Mejor tres fragmentos cortos de tres
    # consultas que uno largo de una.
    candidatas = []
    for c in (consultas_dgt or []):
        r = Recorte(fuente=c.numero, completo=len(c.contestacion or ""))
        frags, total_p, enviados_p = fragmentos_pertinentes(
            c.contestacion, registros, normas)
        r.parrafos = total_p
        if not frags:
            # SIN NADA PERTINENTE, NO SE MANDA. Mejor dos consultas utiles que
            # tres a medias: una consulta que no habla de estos articulos solo
            # aporta volumen y ocasiones de citar lo que no toca.
            r.motivo = ("ningun parrafo trata de los articulos en juego: no se "
                        "manda")
            plan.recortes.append(r)
            continue
        candidatas.append({"c": c, "frags": frags, "total_p": total_p,
                           "enviados_p": enviados_p, "recorte": r})

    if candidatas:
        cabecera = len(BLOQUE_DGT)
        hueco = disponible - cabecera

        # NO HAY PRIORIDAD POR «PAREJA DE AÑOS», Y SE PROBO. La idea era que,
        # al descartar por presupuesto, se cayera antes una consulta suelta que
        # una que forma par de años distintos sobre el mismo precepto -que es
        # la unica señal que este bloque sabe producir-. Medido sobre las 19
        # del banco: NO cambia ni un resultado. Las señales que se pierden no
        # se pierden por presupuesto, sino porque esas consultas no tienen NI
        # UN parrafo que hable del articulo (ver el LEEME, fase 13). Se deja
        # fuera: maquinaria sin efecto medido es maquinaria que engaña al que
        # la lee dentro de seis meses.

        # O SE LE HACE SITIO O NO SE NOMBRA. Se reparte a partes iguales; si
        # con esa cuota alguna no cabe ni con su primer parrafo, se cae la
        # ultima -la de menos prioridad- y se vuelve a repartir entre las que
        # quedan. Asi ninguna consulta acaba nombrada sin texto detras.
        def minimo(cand) -> int:
            primero = cand["frags"][0].split("\n\n")[0]
            return len(bloque_consulta_dgt(cand["c"], [primero],
                                           cand["total_p"]))

        while candidatas:
            cuota = hueco // len(candidatas)
            if all(minimo(x) <= cuota for x in candidatas):
                break
            fuera = candidatas.pop()
            fuera["recorte"].motivo = (
                "no cabe ni con el minimo reservado: no se manda, y por eso "
                "tampoco se nombra")
            plan.recortes.append(fuera["recorte"])

    # El bucle de descarte puede haberlas quitado TODAS: con un articulo corto
    # -y por tanto un presupuesto pequeño- puede no caber ninguna consulta ni
    # con su minimo. Entonces no se manda criterio, que es la respuesta
    # correcta, y no hay nada que repartir.
    if candidatas:
        # Lo que una consulta no gasta pasa a la siguiente: la cuota es un
        # SUELO GARANTIZADO, no un techo que desperdicie hueco. Pero nadie
        # puede gastar el suelo de los que vienen detras -si no, la segunda se
        # come lo que quedaba y la tercera vuelve a quedarse a cero, que es
        # justo el fallo que esto arregla-.
        cuota = hueco // len(candidatas)
        restante, sobra = hueco, 0
        for i, cand in enumerate(candidatas):
            c, frags, total_p = cand["c"], cand["frags"], cand["total_p"]
            r = cand["recorte"]
            reservado = cuota * (len(candidatas) - i - 1)
            tope = max(0, min(cuota + sobra, restante - reservado))

            # SE LLENA POR PARRAFOS, NO POR FRAGMENTOS ENTEROS. Una consulta en
            # la que TODOS los parrafos hablan del articulo produce un unico
            # fragmento gigante; con el tope aplicado al fragmento entero, esa
            # consulta -la mas pertinente que existe- se caia del todo. Un
            # prefijo de parrafos seguidos sigue siendo contiguo y literal.
            #
            # Se mide con el PEOR caso de la cuenta de omitidos -`total_p`, el
            # numero mas largo que puede salir en esa frase-, para que el
            # bloque real nunca sea mayor que el medido. Medir uno y mandar
            # otro es como se sale del tope sin enterarse.
            elegidos, gasto, lleno = [], 0, False
            for frag in frags:
                if lleno:
                    break
                acumulado = []
                for parrafo in frag.split("\n\n"):
                    candidato = len(bloque_consulta_dgt(
                        c, elegidos + ["\n\n".join(acumulado + [parrafo])],
                        total_p))
                    if candidato > tope:
                        lleno = True
                        break
                    acumulado.append(parrafo)
                    gasto = candidato
                if acumulado:
                    elegidos.append("\n\n".join(acumulado))

            # LA GARANTIA, COMPROBADA Y NO SUPUESTA. La cuota esta calculada
            # para que aqui siempre quepa al menos el primer parrafo, pero de
            # eso depende que ninguna señal nombre una consulta sin texto
            # detras. Si algun dia deja de cumplirse, la consulta se cae; lo
            # que no puede pasar es que se nombre en vacio.
            if not elegidos:
                r.motivo = ("no cabe ni con el minimo reservado: no se manda, "
                            "y por eso tampoco se nombra")
                plan.recortes.append(r)
                continue

            r.parrafos_enviados = sum(len(f.split("\n\n")) for f in elegidos)
            omitidos = max(0, total_p - r.parrafos_enviados)
            if r.parrafos_enviados < cand["enviados_p"]:
                r.motivo = (f"{r.parrafos_enviados} de los {cand['enviados_p']} "
                            f"parrafos pertinentes (de {total_p} en total): el "
                            f"resto no cabe en la cuota")
            else:
                r.motivo = (f"{r.parrafos_enviados} de {total_p} parrafos: el "
                            f"resto no habla de los articulos en juego")
            plan.bloques_dgt.append(bloque_consulta_dgt(c, elegidos, omitidos))
            plan.enviadas.append(c.numero)
            restante -= gasto
            sobra = tope - gasto
            r.fragmentos = len(elegidos)
            r.enviado = sum(len(f) for f in elegidos)
            plan.recortes.append(r)

        # Lo que la DGT no ha gastado queda para los regionales. `restante` ya
        # descuenta la cabecera del bloque de la DGT.
        disponible = max(0, restante)

    # --- los TRIBUNALES REGIONALES, al final y con lo que quede ----------
    # Van los ULTIMOS a proposito: pesan menos que la doctrina del TEAC y menos
    # que una consulta de la DGT, y el orden del material es la jerarquia. Que
    # se queden fuera cuando no hay sitio es la consecuencia correcta: lo que
    # no vincula es lo primero que sobra.
    for c in regionales:
        bloque = bloque_criterio_teac(c)
        r = Recorte(fuente=f"{c.unidad} {c.resolucion}",
                    completo=len(c.criterio or ""), parrafos=1, fragmentos=1)
        coste = len(bloque) + (len(BLOQUE_TEAR) if not plan.bloques_tear else 0)
        if coste > disponible:
            r.motivo = ("no cabe en el tope: la ley manda, y lo que no vincula "
                        "es lo primero que sobra")
            plan.recortes.append(r)
            continue
        plan.bloques_tear.append(bloque)
        disponible -= coste
        r.enviado, r.parrafos_enviados = len(c.criterio or ""), 1
        plan.recortes.append(r)

    plan.criterio = (
        (len(BLOQUE_TEAC) if plan.bloques_teac else 0)
        + sum(len(b) for b in plan.bloques_teac)
        + (len(BLOQUE_DGT) if plan.bloques_dgt else 0)
        + sum(len(b) for b in plan.bloques_dgt)
        + (len(BLOQUE_TEAR) if plan.bloques_tear else 0)
        + sum(len(b) for b in plan.bloques_tear)
    )
    return plan


def construir_material(
    pregunta: str,
    ejercicio: int | None,
    registros: list,
    grafo=None,
    motivos_rechazo: list | None = None,
    consultas_dgt: list | None = None,
    criterios_teac: list | None = None,
    normas=None,
    plan: Plan | None = None,
) -> str:
    """El unico contenido que ve el redactor.

    `consultas_dgt` es opcional: con la DGT apagada no se pasa y este material
    sale byte a byte igual que antes de la fase 9B.

    `plan` es el recorte ya calculado. Se pasa desde fuera cuando hace falta
    escribirlo en la traza -que es siempre que hay criterio-; si no se pasa, se
    calcula aqui y sale lo mismo.
    """
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

    # EL ORDEN DEL MATERIAL ES LA JERARQUIA. Lo que se lee primero pesa
    # primero al redactar: ley, luego TEAC, luego DGT. Y el TAMAÑO tambien es
    # jerarquia: el criterio no puede pasar del bloque de ley. Ver `Plan`.
    if plan is None:
        plan = plan_de_criterio(registros, ejercicio, grafo, consultas_dgt,
                                criterios_teac, normas)
    doctrina = ([BLOQUE_TEAC] + plan.bloques_teac) if plan.bloques_teac else []
    criterio = ([BLOQUE_DGT] + plan.bloques_dgt) if plan.bloques_dgt else []
    regional = ([BLOQUE_TEAR] + plan.bloques_tear) if plan.bloques_tear else []

    return "\n".join(cabecera + cuerpo + doctrina + criterio + regional + cola)
