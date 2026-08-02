"""El ESTADO de una respuesta, calculado por reglas.

    CRITERIO CLARO      norma alineada y vigente en el ejercicio
    CRITERIO DISCUTIDO  hay textos que apuntan a soluciones distintas
    NO ENCONTRADO       no hay respaldo suficiente

Lo decide el codigo mirando la evidencia recuperada y el dictamen del
verificador. El modelo no elige el estado ni lo influye con su tono.

Por que asi: un agente que siempre suena seguro es peor que inutil. La oficina
se calibra con el, deja de comprobarlo, y el dia que se equivoca no lo mira
nadie. El tono es del modelo; el estado, del expediente.
"""

from __future__ import annotations

from dataclasses import dataclass, field

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

# Impuestos que este corpus puede contestar. Hoy solo hay una ley dentro.
IMPUESTOS_EN_CORPUS = ("IVA", "desconocido")


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
                         umbral: float = UMBRAL_MATERIAL) -> Seleccion:
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

    utiles = _raices_utiles(indice, consulta)
    coberturas = [cobertura_de(indice, utiles, r.doc.registro) for r in resultados]
    primera = coberturas[0] or 1e-9

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
        if i == 0:
            linea["decision"], linea["motivo"] = "enviado", "es el mejor resultado"
            elegidos_idx.append(i)
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
    senales: list = field(default_factory=list)   # senales de discusion halladas
    preceptos: list = field(default_factory=list) # referencias que lo sostienen

    def a_json(self) -> dict:
        return {
            "estado": self.estado,
            "motivos": self.motivos,
            "senales_de_discusion": self.senales,
            "preceptos_que_lo_sostienen": self.preceptos,
        }


def calcular(
    informe,
    indice,
    grafo,
    ejercicio: int | None,
    n_resultados: int,
) -> Dictamen:
    """Estado a partir de la evidencia. Ningun texto del modelo entra aqui."""

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

    preceptos = [indice.por_clave[c].registro["referencia"] for c in claves]

    # --- senales de que el criterio no esta cerrado ---
    senales: list[str] = []

    for clave in claves:
        reg = indice.por_clave[clave].registro
        ref = reg["referencia"]

        # 1) el texto no es el del ejercicio, o cambio dentro de el
        for a in V.avisos(reg, ejercicio):
            if a.nivel == V.GRAVE:
                senales.append(f"{ref}: {a.texto}")

        # 2) el precepto remite a algo que no esta en el corpus: la respuesta
        #    podria depender de una norma que no se ha podido consultar
        pendientes = grafo.pendientes_de(clave)
        if pendientes:
            destinos = sorted(
                {r.norma_externa or "norma sin identificar" for r in pendientes}
            )
            senales.append(
                f"{ref} remite a {', '.join(destinos[:3])}, que no esta en el "
                f"corpus: no se ha podido comprobar que dice"
            )

        # 3) una disposicion menciona a este articulo y NO se ha citado.
        #    Es el caso que mas duele: el articulo parece cerrado y la
        #    excepcion vive al final de la ley.
        for rem in grafo.le_mencionan(clave):
            origen = indice.por_clave[rem.origen].registro
            if not origen["tipo"].startswith("disposicion"):
                continue
            if rem.origen in claves:
                continue  # se ha citado, luego se ha tenido en cuenta
            senales.append(
                f"{ref}: la {origen['referencia']} lo menciona y la respuesta "
                f"no la recoge; ahi suelen estar las excepciones"
            )

    if senales:
        return Dictamen(
            DISCUTIDO,
            [
                "las citas estan verificadas, pero hay textos que pueden "
                "llevar a una solucion distinta"
            ],
            senales=sorted(set(senales)),
            preceptos=preceptos,
        )

    return Dictamen(
        CLARO,
        [
            f"{len(verificadas)} cita(s) verificada(s) sobre {len(claves)} "
            f"precepto(s), vigentes en el ejercicio y sin remisiones pendientes"
        ],
        preceptos=preceptos,
    )
