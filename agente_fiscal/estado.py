"""El ESTADO de una respuesta, calculado por reglas.

    CRITERIO CLARO      nada de lo consultado apunta a una solucion distinta
    CRITERIO DISCUTIDO  hay DESACUERDO DE FONDO entre los textos
    NO ENCONTRADO       no hay respaldo suficiente

Lo decide el codigo mirando la evidencia recuperada y el dictamen del
verificador. El modelo no elige el estado ni lo influye con su tono.

Por que asi: un agente que siempre suena seguro es peor que inutil. La oficina
se calibra con el, deja de comprobarlo, y el dia que se equivoca no lo mira
nadie. El tono es del modelo; el estado, del expediente.

----------------------------------------------------------------------------
DOS EJES, DOS CAJONES. LA CORRECCION QUE TRAJO LA MEDICION DE LAS TRES FUENTES
----------------------------------------------------------------------------
Medido sobre las 19 consultas del banco, DISCUTIDO salia 17 de 19 ANTES de
encender la DGT y el TEAC. Con las capas de criterio, 19 de 19. Una señal que
sale siempre no informa de nada: quien la lee deja de mirarla, y el dia que
hay discusion de verdad se lee igual que los otros dieciocho dias.

La causa no era el criterio: eran los avisos de vigencia y las remisiones a
normas que no tenemos. Eso NO es criterio discutido. Es COBERTURA INCOMPLETA
DE NUESTRO CORPUS, que es un eje distinto, y estaba en el mismo cajon.

    ESTADO ................ SOLO por desacuerdo de fondo entre textos:
                            · varias consultas de la DGT de años distintos
                              sobre el mismo precepto
                            · el TEAC pronunciandose sobre una consulta que
                              esta respuesta cita
                            Nada mas. Ver `Dictamen.senales`.

    AVISOS DE COBERTURA ... lo que NO SE HA PODIDO MIRAR. Se enseñan IGUAL DE
                            CLAROS y NO tocan el estado.

Que un aviso de cobertura no mueva el estado NO significa que importe menos:
significa que responde a otra pregunta. El estado dice «¿los textos se
contradicen?»; la cobertura dice «¿que no he podido mirar?». Juntarlas hacia
que la primera no se pudiera contestar.

----------------------------------------------------------------------------
Y LA COBERTURA, PARTIDA OTRA VEZ: UN AVISO QUE SALE SIEMPRE ES DECORACION
----------------------------------------------------------------------------
Separar el estado de la cobertura arreglo el estado y traslado el problema un
piso mas abajo: 101 avisos en 19 consultas, 5,3 de media. Un bloque asi se deja
de leer exactamente igual que se dejaba de leer el DISCUTIDO.

Se parten por lo que el lector PUEDE HACER con ellos, que es la unica division
que le sirve a quien lo lee:

    ACCIONABLE ..... hay algo CONCRETO que mirar, y cambia de una consulta a
                     otra: doctrina del TEAC sobre este articulo, el articulo
                     cambio despues del ejercicio, una disposicion que le
                     afecta y no se recogio, una fuente que no respondia, una
                     consulta citada que va de otra cosa.
                     Van ARRIBA y COMPLETOS. Ver `Dictamen.cobertura`.

    ESTRUCTURAL .... limites PERMANENTES del corpus: remisiones a normas que
                     no tenemos y que no vamos a tener (Ley Concursal, Codigo
                     Penal). Son los mismos hoy que dentro de un año, no
                     dependen de la consulta y no hay nada que hacer con
                     ellos, pero ocupaban el mismo sitio que los importantes.
                     Van RESUMIDOS EN UNA LINEA al final.
                     Ver `Dictamen.estructural` y `Dictamen.linea_estructural`.

EL CRITERIO, PARA LA PROXIMA VEZ: un aviso que sale siempre no es un aviso, es
decoracion. Si algo aparece en todas las respuestas, o se resume o se quita;
dejarlo entero solo consigue que se deje de leer lo que esta a su lado.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import referencias as R
from . import verificador as VF
from . import vigencia as V

CLARO = "CRITERIO CLARO"
DISCUTIDO = "CRITERIO DISCUTIDO"
NO_ENCONTRADO = "NO ENCONTRADO"

# Umbrales del filtro de pertinencia (ver `pertinencia`). Son constantes a la
# vista y ajustables, no numeros escondidos en un if.
COBERTURA_MINIMA = 0.5   # que parte de la consulta cubre el mejor resultado
AUSENCIA_MAXIMA = 0.5    # que parte de la consulta no existe en todo el corpus

# Umbral del corte de material (ver `seleccionar_material`): que fraccion de la
# cobertura del PRIMER precepto tiene que alcanzar un precepto para que se le
# mande al redactor.
#
# De donde sale el 0,70, medido sobre 65 consultas reales (los terminos que
# propuso el analizador, guardados en las trazas):
#
#     umbral   preceptos/consulta   consultas que se quedan con 1
#      0.65          3.95                        3
#      0.70          3.74                        3     <-- ultimo escalon plano
#      0.71          3.63                        5
#      0.73          3.46                       10
#      0.75          3.26                       15
#      0.80          2.95                       19
#
# Hasta 0,70 el corte quita ruido; a partir de 0,71 empieza a quitar preceptos
# de verdad, y la curva se dispara: de 3 consultas con un solo precepto a 15 en
# cinco centesimas. Se elige el ultimo valor antes del salto.
#
# Y lo que no cambia: en las 15 consultas del banco NINGUN umbral, ni siquiera
# 1,00, deja fuera el articulo que la consulta busca. El caso que daba miedo
# -«que tipo reducido se aplica», con el articulo 91 en el puesto 5- sobrevive
# a cualquier umbral, porque su cobertura es 1,00: identica a la del primero.
# Cortar por pertinencia no es cortar por puesto, y esa es justo la diferencia.
UMBRAL_MATERIAL = 0.70

# LA PUERTA DE MATERIA SE COMPONE DE LAS NORMAS CARGADAS.
#
# Era una tupla escrita a mano -("IVA", "desconocido")- y tenia los dos fallos
# que tiene siempre una lista a mano: se queda vieja el dia que entra otra
# norma, y nadie se entera porque no falla, solo miente.
#
# Y «DESCONOCIDO» YA NO PASA. Pasaba, y era la puerta abierta a todo: si el
# analizador no sabe de que impuesto es la pregunta, dejarla entrar significa
# que lo unico que la para es el corte por pertinencia, que no esta para eso.
# Medido antes de decidirlo: en las 66 consultas hechas con el modelo de verdad
# NO HAY NI UNA «desconocido» -65 IVA y 1 IRPF-, asi que cerrar la puerta no
# cuesta ninguna consulta legitima. El 29,6% de «desconocido» que aparecia en
# las trazas venia del motor de ensayo, cuyo analizador es un tocon de una
# linea que responde «IVA» si la pregunta lleva esa palabra.
DESCONOCIDO = "desconocido"


def impuestos_en_corpus(normas) -> set:
    """Los impuestos que se pueden contestar, sacados de las normas cargadas."""
    return set(normas.impuestos()) if normas is not None else set()


def puerta_de_materia(impuesto: str, normas) -> tuple:
    """¿Entra esta consulta? Devuelve (entra, motivo_en_cristiano).

    El motivo se compone de las normas que hay dentro. Nada de frases fijas:
    la frase «este corpus solo cubre el IVA» era verdad el dia que se escribio.
    """
    dentro = impuestos_en_corpus(normas)
    nombres = normas.nombres_de_impuesto() if normas is not None else []
    if len(nombres) > 1:
        lista = ", ".join(nombres[:-1]) + " y " + nombres[-1]
    else:
        lista = nombres[0] if nombres else "ninguna norma de impuesto"

    if impuesto == DESCONOCIDO or not impuesto:
        return False, (
            "no se ha podido determinar de que impuesto es la pregunta. Esta "
            f"herramienta cubre {lista}: dilo en la pregunta y se vuelve a "
            "intentar")
    if impuesto not in dentro:
        return False, (
            f"la consulta es de {impuesto} y esta herramienta cubre {lista}")
    return True, ""


def pertinencia(indice, consulta: str, resultados) -> tuple[bool, str]:
    """Comprueba que lo recuperado va DE VERDAD sobre lo que se pregunta.

    Existe porque un buscador siempre devuelve algo. Con una pregunta de IRPF,
    BM25 encuentra el articulo de la Ley del IVA que habla de "vivienda", el
    redactor lo cita literalmente, el verificador da la cita por buena (lo es:
    esa frase esta en ese articulo) y sale un CRITERIO CLARO sobre una pregunta
    que este corpus no puede contestar. Todo correcto pieza a pieza y mal en
    conjunto.

    Se mide por cobertura de terminos, no por puntuacion: BM25 no esta
    calibrado y su valor absoluto no significa nada comparable entre consultas.
    """
    from . import texto as T

    if not resultados:
        return False, "la busqueda no devolvio ningun precepto"

    raices = T.tokenizar(consulta)
    if not raices:
        return False, "la consulta no deja ningun termino con contenido"

    ausentes = [r for r in raices if indice.df.get(r, 0) == 0]
    utiles = [r for r in raices if r not in ausentes]
    if not utiles:
        return False, (
            f"ninguna palabra de la consulta aparece en el corpus "
            f"({', '.join(sorted(set(ausentes)))})"
        )

    proporcion_ausente = len(ausentes) / len(raices)
    if proporcion_ausente > AUSENCIA_MAXIMA:
        return False, (
            f"{len(ausentes)} de {len(raices)} terminos no existen en toda la "
            f"Ley del IVA ({', '.join(sorted(set(ausentes)))}): la pregunta "
            f"parece de otra materia"
        )

    mejor = resultados[0]
    campos = indice.campos_de(mejor.doc.registro)
    presentes = set(T.tokenizar(" ".join(campos.values())))
    cubiertos = [r for r in utiles if r in presentes]
    cobertura = len(cubiertos) / len(utiles)

    if cobertura < COBERTURA_MINIMA:
        faltan = sorted(set(utiles) - set(cubiertos))
        return False, (
            f"el mejor resultado ({mejor.doc.referencia}) solo cubre "
            f"{len(cubiertos)} de {len(utiles)} terminos de la consulta; "
            f"no trata de {', '.join(faltan)}"
        )

    return True, (
        f"{mejor.doc.referencia} cubre {len(cubiertos)}/{len(utiles)} terminos"
    )


def _raices_utiles(indice, consulta: str) -> list[str]:
    """Terminos de la consulta que existen en el corpus. Los demas no miden."""
    from . import texto as T

    return [r for r in T.tokenizar(consulta) if indice.df.get(r, 0) > 0]


def cobertura_de(indice, utiles: list[str], registro: dict) -> float:
    """Que parte de la consulta trata ESTE precepto. La misma cuenta que usa
    `pertinencia`, pero por precepto en vez de solo para el primero."""
    from . import texto as T

    if not utiles:
        return 0.0
    presentes = set(T.tokenizar(" ".join(indice.campos_de(registro).values())))
    return sum(1 for r in utiles if r in presentes) / len(utiles)


@dataclass
class Seleccion:
    """Que se le manda al redactor y que se deja fuera, con el porque."""

    elegidos: list = field(default_factory=list)      # registros
    detalle: list = field(default_factory=list)       # una linea por candidato
    umbral: float = UMBRAL_MATERIAL

    @property
    def descartados(self) -> list:
        return [d for d in self.detalle if d["decision"] == "descartado"]

    def a_json(self) -> dict:
        return {
            "umbral": self.umbral,
            "enviados": len(self.elegidos),
            "candidatos": len(self.detalle),
            "preceptos": self.detalle,
        }


def seleccionar_material(indice, consulta: str, resultados, grafo=None,
                         umbral: float = UMBRAL_MATERIAL,
                         reserva=None, naturaleza=None) -> Seleccion:
    """Que preceptos de los recuperados llegan al redactor.

    El tope de 5 sigue siendo el techo (lo aplica la busqueda), pero no es una
    cuota: nada obliga a llenarlo. Se corta por PERTINENCIA, no por puesto,
    porque cortar por puesto mata casos buenos -el articulo 91 sale el quinto
    en «que tipo reducido se aplica» y es el que contesta-.

    Tres reglas:

      1. el primero entra siempre, pase lo que pase;
      2. los demas entran si su cobertura llega al `umbral` de la del primero;
      3. y entran IGUAL, con la cobertura que sea, si un precepto ya elegido
         remite a ellos. Esa es la nota al pie: la excepcion que no se ve
         leyendo el articulo solo, y por la que existe medio proyecto.
    """
    seleccion = Seleccion(umbral=umbral)
    if not resultados:
        return seleccion

    # LA RESERVA: preceptos que NO compiten pero que la pasada 2 puede llamar.
    #
    # Desde que la busqueda filtra por impuesto, el precepto de OTRO impuesto
    # al que remite uno elegido ya no aparece entre los recuperados, y la
    # pasada 2 solo sabia readmitir de ahi. Sin esto, el articulo 4 de la Ley
    # del Patrimonio -bienes exentos- dejaria de traer los articulos del IRPF
    # a los que remite, que es exactamente la nota al pie por la que existe
    # medio proyecto.
    #
    # La reserva la calcula quien llama (`fase4`) y son LOS DESTINOS DE LAS
    # REMISIONES de los candidatos, no «los mejor puntuados de fuera». Se
    # probaron las dos: por puntuacion no servia -el articulo 51 de la Ley
    # 35/2006 no puntua para una pregunta de patrimonio, y aun asi es al que
    # remite el articulo 4-. Lo que decide quien esta en la reserva es a quien
    # se le llama, no a quien se parece.
    #
    # Se pegan al final y se marcan: mas simple que llevar dos listas por todo
    # el recorrido, y no puede descuadrarse.
    n_propios = len(resultados)
    ya = {r.doc.clave for r in resultados}
    resultados = list(resultados) + [r for r in (reserva or [])
                                     if r.doc.clave not in ya]

    utiles = _raices_utiles(indice, consulta)
    coberturas = [cobertura_de(indice, utiles, r.doc.registro) for r in resultados]
    primera = coberturas[0] or 1e-9

    # --- de que va la consulta, y por tanto quien puede contestarla --------
    #
    # La cobertura mide cuantas palabras de la consulta trata un precepto. No
    # sabe de que va la consulta, y por eso deja que una norma general compita
    # de tu a tu con la del impuesto: el articulo 55 LGT ("tipo de gravamen")
    # cubre "tipo" igual de bien que el 91 LIVA, y se cuela en una pregunta
    # sobre tipos de IVA que no va de procedimiento.
    #
    # La regla, por PAPEL de la norma y no por lista de articulos:
    #
    #   una norma GENERAL solo aporta material cuando la consulta es suya
    #   -su precepto es el mejor resultado- o cuando un precepto ya elegido
    #   la llama por remision.
    #
    # Es decir: la LGT entra como APOYO, no compitiendo, salvo que la consulta
    # sea suya. La excepcion por remision de la pasada 2 sigue intacta, que es
    # la que trae la nota al pie que no se ve.
    #
    # QUIEN DECIDE QUE LA CONSULTA ES DE PROCEDIMIENTO. Antes se ADIVINABA:
    # se miraba quien ganaba el PUESTO 1 de la busqueda. Funcionaba mientras
    # hubiera un solo ranking, y dejo de funcionar en cuanto la busqueda se
    # separo en dos ligas: la norma general nunca queda la primera en su
    # propia liga, asi que TODA consulta pasaba por «de fondo» y el
    # procedimiento se rompia por construccion, con cualquier reparto.
    #
    # Ahora lo dice el analizador, que es quien ha leido la pregunta. Ver
    # `analizador.NATURALEZAS`. Y si no lo sabe -o nadie lo pasa- se vuelve a
    # la regla vieja: sin senal no se cambia nada, que es la misma regla que
    # con el impuesto.
    from . import analizador as AN
    papel = getattr(indice.normas, "papel", None)
    if naturaleza == AN.PROCEDIMIENTO:
        manda_general = True
    elif naturaleza == AN.FONDO:
        manda_general = False
    else:
        manda_general = False
        if papel is not None and resultados:
            primero = resultados[0].doc.registro
            manda_general = papel(primero.get("cuerpo_clave") or "") == \
                indice.normas.GENERAL

    def es_apoyo(registro) -> bool:
        """Este precepto es de una norma general en una consulta que no lo es."""
        if papel is None or manda_general:
            return False
        return papel(registro.get("cuerpo_clave") or "") == indice.normas.GENERAL

    # --- pasada 1: el primero y los que llegan al umbral -------------------
    elegidos_idx: list[int] = []
    lineas = []
    for i, (r, c) in enumerate(zip(resultados, coberturas)):
        relativa = c / primera
        linea = {
            "referencia": r.doc.registro["referencia"],
            "clave": r.doc.clave,
            "puesto": i + 1,
            "cobertura": round(c, 3),
            "relativa": round(relativa, 3),
            "decision": "",
            "motivo": "",
        }
        if i >= n_propios:
            # De la reserva: otro impuesto. Solo puede entrar por remision.
            linea["decision"] = "descartado"
            linea["motivo"] = ("es de otro impuesto: solo entraria si un "
                               "precepto elegido lo remite")
        elif i == 0:
            linea["decision"], linea["motivo"] = "enviado", "es el mejor resultado"
            elegidos_idx.append(i)
        elif es_apoyo(r.doc.registro):
            # Fuera por PAPEL, aunque la cobertura le diera de sobra. Puede
            # volver a entrar en la pasada 2 si alguien la remite.
            linea["decision"] = "descartado"
            linea["motivo"] = (
                "norma general de apoyo: esta consulta no es de procedimiento, "
                "asi que solo entraria si un precepto elegido la remite"
            )
        elif relativa >= umbral:
            linea["decision"] = "enviado"
            linea["motivo"] = (f"cubre el {relativa:.0%} de lo que cubre el "
                               f"primero (umbral {umbral:.0%})")
            elegidos_idx.append(i)
        else:
            linea["decision"] = "descartado"
            linea["motivo"] = (f"solo cubre el {relativa:.0%} de lo que cubre "
                               f"el primero (umbral {umbral:.0%})")
        lineas.append(linea)

    # --- pasada 2: la excepcion por remision, que no se negocia ------------
    # Se repite hasta que no entre nadie nuevo: si A remite a B y B a C, y las
    # dos vienen al caso, las dos entran. Un solo barrido dejaria fuera a C.
    if grafo is not None:
        cambiado = True
        while cambiado:
            cambiado = False
            apuntados = set()
            for i in elegidos_idx:
                clave = resultados[i].doc.clave
                apuntados.update(r.destino for r in grafo.menciona_a(clave))
            for i, r in enumerate(resultados):
                if i in elegidos_idx or r.doc.clave not in apuntados:
                    continue
                origen = next(
                    (resultados[j].doc.registro["referencia"] for j in elegidos_idx
                     if any(x.destino == r.doc.clave
                            for x in grafo.menciona_a(resultados[j].doc.clave))),
                    "otro precepto pertinente",
                )
                lineas[i]["decision"] = "enviado"
                lineas[i]["motivo"] = (
                    f"cobertura baja ({lineas[i]['relativa']:.0%}), pero "
                    f"{origen} remite a el: puede traer la excepcion"
                )
                elegidos_idx.append(i)
                cambiado = True

    seleccion.detalle = lineas
    seleccion.elegidos = [resultados[i].doc.registro for i in sorted(elegidos_idx)]
    return seleccion


@dataclass
class Dictamen:
    estado: str
    motivos: list = field(default_factory=list)   # por que ese estado
    # DESACUERDO DE FONDO. Estas SI mueven el estado a DISCUTIDO.
    senales: list = field(default_factory=list)
    # LO QUE NO SE HA PODIDO MIRAR Y SE PUEDE HACER ALGO AL RESPECTO. Se enseña
    # igual de claro y NO mueve el estado. Un CRITERIO CLARO con avisos de
    # cobertura es normal: los textos no se contradicen, pero hay huecos.
    cobertura: list = field(default_factory=list)
    # LIMITES PERMANENTES DEL CORPUS. Cada uno es {"referencia", "normas"}. No
    # cambian de una consulta a otra, asi que se resumen en una linea.
    estructural: list = field(default_factory=list)
    preceptos: list = field(default_factory=list) # referencias que lo sostienen

    @property
    def linea_estructural(self) -> str:
        """Los limites del corpus, en UNA linea. «» si no hay ninguno.

        Se resume porque es siempre lo mismo: que el articulo 80 remita a la
        Ley Concursal no es una novedad de esta consulta, es el mapa del
        corpus. Entero ocupaba tanto como los avisos que si hay que leer.
        """
        if not self.estructural:
            return ""
        refs = sorted({e["referencia"] for e in self.estructural})
        normas = sorted({n for e in self.estructural for n in e["normas"]})
        ambiguas = sorted({n for e in self.estructural
                           for n in e.get("ambiguas") or []})
        cuantos = f"{len(refs)} de los preceptos citados" if len(refs) > 1 \
            else refs[0]
        partes = []
        if normas:
            corte = normas[:4]
            resto = len(normas) - len(corte)
            partes.append(
                f"{cuantos} remite" + ("n" if len(refs) > 1 else "") + " a "
                + ", ".join(corte)
                + (f" y {resto} norma(s) mas" if resto else "")
                + ", que no estan en el corpus")
        if ambiguas:
            corte = ambiguas[:3]
            resto = len(ambiguas) - len(corte)
            comillas = ", ".join(f"«{x}»" for x in corte)
            partes.append(
                ("y tambien" if partes else f"{cuantos} remite"
                 + ("n" if len(refs) > 1 else ""))
                + f" a {comillas}"
                + (f" y {resto} mas" if resto else "")
                + ", que NO identifica cual de las normas cargadas: no se ha "
                  "podido resolver")
        if not partes:
            return ""
        return "; ".join(partes) + (
            ". Es un limite permanente de la herramienta, no algo de esta "
            "consulta")

    def a_json(self) -> dict:
        return {
            "estado": self.estado,
            "motivos": self.motivos,
            "senales_de_discusion": self.senales,
            "avisos_de_cobertura": self.cobertura,
            "limites_del_corpus": self.estructural,
            "linea_estructural": self.linea_estructural,
            "preceptos_que_lo_sostienen": self.preceptos,
        }


def calcular(
    informe,
    indice,
    grafo,
    ejercicio: int | None,
    n_resultados: int,
    lectura_dgt=None,
    lectura_teac=None,
) -> Dictamen:
    """Estado a partir de la evidencia. Ningun texto del modelo entra aqui.

    `lectura_dgt` es lo que aporta el criterio de la DGT, ya masticado por
    `dgt.leer_criterio`. Es OPCIONAL a proposito: si no se pasa -que es lo que
    ocurre con la DGT apagada- esta funcion hace exactamente lo mismo que hacia
    antes de la fase 9B, linea por linea.
    """

    # --- NO ENCONTRADO: los tres casos en que no hay respaldo ---
    if n_resultados == 0:
        return Dictamen(
            NO_ENCONTRADO,
            ["la busqueda no devolvio ningun precepto del corpus"],
        )

    if informe is None or informe.veredicto != VF.ACEPTADO:
        motivo = (
            informe.motivo_global
            if informe is not None and informe.motivo_global
            else "la redaccion no supero la verificacion de citas"
        )
        return Dictamen(NO_ENCONTRADO, [motivo])

    verificadas = [d for d in informe.dictamenes if d.estado == VF.VERIFICADA]
    claves = sorted({d.clave for d in verificadas if d.clave})
    if not claves:
        return Dictamen(
            NO_ENCONTRADO,
            ["ninguna cita verificada apunta a un precepto del corpus"],
        )

    # CON SU NORMA, y por la MISMA funcion que usa el verificador.
    #
    # Salia «Articulo 30, Articulo 30» -uno de la Ley y otro del Reglamento- y
    # la linea no decia cual era cual. El nombrador correcto ya existia y su
    # docstring dice «todo mensaje que nombre un precepto pasa por aqui, sin
    # excepciones»: esta linea era la excepcion.
    preceptos = [VF.nombre_de(indice, c) for c in claves]

    # LOS DOS CAJONES. Ver la cabecera del modulo: uno mueve el estado y el
    # otro no, y por eso no pueden compartir lista.
    desacuerdo: list[str] = []   # -> DISCUTIDO
    cobertura: list[str] = []    # -> se enseña entero, no mueve nada
    estructural: list[dict] = [] # -> se resume en una linea al final
    motivos: list[str] = []

    for clave in claves:
        reg = indice.por_clave[clave].registro
        ref = reg["referencia"]

        # --- COBERTURA 1) el texto no es el del ejercicio, o cambio dentro ---
        # Que un articulo se reformara en 2024 no enfrenta a dos textos: dice
        # que el nuestro puede no ser el que aplicaba. Es un hueco, no una
        # discusion.
        for a in V.avisos(reg, ejercicio):
            if a.nivel == V.GRAVE:
                cobertura.append(f"{ref}: {a.texto}")

        # --- ESTRUCTURAL) remite a una norma que no esta en el corpus -------
        # Esto NO es accionable: no hay nada que el lector pueda mirar, porque
        # la norma no esta y no va a estar. Y es el aviso que mas salia: en las
        # 19 del banco era casi la mitad de todos los avisos de cobertura. Va
        # resumido al final, no repetido articulo por articulo arriba.
        # AUSENCIA Y AMBIGUEDAD NO SON LO MISMO, Y HASTA AHORA SE DECIAN
        # IGUAL. «Remite a la Ley del Impuesto, que no esta en el corpus» era
        # falso: la Ley del Impuesto SI esta -dos veces, la del IVA y la del
        # IRPF- y por eso no se resuelve. Decir «no la tengo» cuando lo que
        # pasa es «no se cual de las que tengo» manda a buscar fuera lo que
        # esta dentro.
        pendientes = grafo.pendientes_de(clave)
        if pendientes:
            fuera = sorted({r.norma_externa or "norma sin identificar"
                            for r in pendientes if r.ambito != R.AMBIGUA})
            dudosas = sorted({r.norma_externa or r.texto
                              for r in pendientes if r.ambito == R.AMBIGUA})
            estructural.append({"referencia": ref, "normas": fuera,
                                "ambiguas": dudosas})

        # --- COBERTURA 3) una disposicion lo menciona y no se ha citado -----
        # El articulo parece cerrado y la excepcion vive al final de la ley.
        # Tampoco es desacuerdo: es material del corpus que la respuesta no ha
        # mirado, que es exactamente la definicion del otro eje.
        for rem in grafo.le_mencionan(clave):
            origen = indice.por_clave[rem.origen].registro
            if not origen["tipo"].startswith("disposicion"):
                continue
            if rem.origen in claves:
                continue  # se ha citado, luego se ha tenido en cuenta
            cobertura.append(
                f"{ref}: la {origen['referencia']} lo menciona y la respuesta "
                f"no la recoge; ahi suelen estar las excepciones"
            )

    # --- la doctrina del TEAC -------------------------------------------
    # LAS DOS SEÑALES NO PESAN IGUAL, NO SE PRESENTAN IGUAL Y AHORA TAMPOCO
    # VAN AL MISMO CAJON.
    #
    #   FUERTE  el TEAC cita POR NUMERO una consulta que esta respuesta usa.
    #           No hay que adivinar: el tribunal ha puesto las dos cosas en la
    #           misma frase. Es DESACUERDO DE FONDO y mueve el estado.
    #   DEBIL   coincidencia de articulo. No afirma que haya discusion; afirma
    #           que hay doctrina sin comprobar. Es COBERTURA.
    #
    # Ver `teac.leer_doctrina` y el LEEME.
    if lectura_teac is not None:
        desacuerdo.extend(lectura_teac.desacuerdo)
        cobertura.extend(lectura_teac.cobertura)
        if lectura_teac.desacuerdo:
            motivos.append(
                "el TEAC se ha pronunciado expresamente sobre criterio que "
                "esta respuesta cita")
        # La fuente caida NO se disimula, pero tampoco es una discusion: es un
        # hueco declarado, y ese es su sitio.
        if lectura_teac.fuente_caida:
            cobertura.append(
                "no se ha podido consultar la doctrina del TEAC"
                + (f" ({lectura_teac.motivo_fuente})"
                   if lectura_teac.motivo_fuente else "")
                + ": puede haber doctrina de tribunales que no se ha visto")

    # --- el criterio de la DGT ------------------------------------------
    if lectura_dgt is not None:
        desacuerdo.extend(lectura_dgt.senales)
        cobertura.extend(lectura_dgt.cobertura)
        if lectura_dgt.senales:
            motivos.append(
                "hay consultas de la DGT de años distintos sobre el mismo "
                "precepto: el criterio ha podido cambiar")
        if lectura_dgt.fuente_caida:
            cobertura.append(
                "no se ha podido consultar el criterio de la DGT"
                + (f" ({lectura_dgt.motivo_fuente})"
                   if lectura_dgt.motivo_fuente else "")
                + ": esta respuesta se sostiene SOLO en la norma, y puede "
                  "haber criterio administrativo que no se ha visto"
            )

    cobertura = sorted(set(cobertura))

    if desacuerdo:
        return Dictamen(
            DISCUTIDO,
            motivos or [
                "las citas estan verificadas, pero hay textos que apuntan a "
                "una solucion distinta"
            ],
            senales=sorted(set(desacuerdo)),
            cobertura=cobertura,
            estructural=estructural,
            preceptos=preceptos,
        )

    return Dictamen(
        CLARO,
        [
            f"{len(verificadas)} cita(s) verificada(s) sobre {len(claves)} "
            f"precepto(s), y ningun texto de los consultados apunta a una "
            f"solucion distinta"
            + (f" (quedan {len(cobertura)} aviso(s) de cobertura, que no "
               f"cambian el estado)" if cobertura else "")
        ],
        cobertura=cobertura,
        estructural=estructural,
        preceptos=preceptos,
    )
