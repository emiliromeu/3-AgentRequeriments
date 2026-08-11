"""QUE LE FALTA POR INCORPORAR A UNA NORMA CONSOLIDADA DEL BOE.

El BOE marca algunas normas como «Desactualizado»: estan en la base
consolidada, pero hay reformas publicadas que todavia no se han metido en el
texto. Ingerir una asi sin mas es citar articulos derogados CON ENLACE Y CON
SEGURIDAD, que es la peor forma de equivocarse que tiene este sistema.

    pendientes.leer(metadatos, analisis, xml)  ->  Informe

LO QUE HACE Y LO QUE NO HACE, y la diferencia importa:

  · NO se fia de `referencias.posteriores`. Esa lista es el HISTORICO de todo
    lo que ha tocado la norma, incorporado o no; medido sobre el Decreto
    Legislativo 1/2024, SEIS de las OCHO ya estaban dentro del texto. Lo que
    esta incorporado se sabe mirando los `id_norma` de las versiones del
    articulado: si una norma aparece ahi, sus cambios ya estan.

  · La lista de preceptos afectados viene EN PROSA, en un solo campo de texto.
    Se intenta convertir en lista, y LO IMPORTANTE ES QUE SE SEPA CUANDO NO SE
    PUEDE. Una nota que dice «SE MODIFICA determinados preceptos» no se puede
    convertir en nada, y creerse que si es como se ingiere a medias.

LA PUERTA SE CIERRA SOLA. `Informe.fiable` es False en cuanto UNA reforma
pendiente no se deja leer entera. Quien llame no debe ingerir en ese caso: es
mejor no tener la norma que tenerla con la mitad de los avisos.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Como se numeran los articulos del Codi tributari: 621-2, 632-16, 641-14.
# Se admite el punto ademas del guion porque la nota del BOE mezcla los dos
# -«631-20, 632-16, 641.1, 641-14»- y leer solo el guion se dejaria el 641-1
# fuera, que es justo un articulo modificado.
_RE_ART_CODI = re.compile(r"\b(\d{3})[-.](\d{1,2})\b")

# Numeracion clasica, «articulo 12», por si esto se usa con otra norma.
_RE_ART_CLASICO = re.compile(r"\barts?\.?\s+(\d{1,3})\b", re.IGNORECASE)

_RE_DISP = re.compile(
    r"\bdisposici[oó]n(?:es)?\s+(adicional|transitoria|final|derogatoria)\s+"
    r"([\wªº]+)", re.IGNORECASE)

# LO QUE HACE QUE UNA NOTA NO SE PUEDA CONVERTIR EN LISTA. Cada una de estas
# significa «hay mas y no te digo cuales».
_VAGO = (
    (r"determinad[oa]s?\s+preceptos", "dice «determinados preceptos» sin decir cuales"),
    (r"en la forma indicada", "dice «en la forma indicada»: el alcance no esta en la nota"),
    (r"\bdiversos\b|\bvarios\b", "habla de varios preceptos sin enumerarlos"),
    (r"subsecci[oó]n|secci[oó]n|cap[ií]tulo|t[ií]tulo\s+[IVXLC]",
     "afecta a un bloque entero (seccion, capitulo o titulo), no a articulos sueltos"),
    (r"SE CORRIGEN?\s+erratas",
     "es una correccion de erratas de OTRA norma ya incorporada: no dice que\n      preceptos de esta quedan afectados"),
    (r"\bel anexo\b", "afecta al anexo, que no se trocea como articulo"),
)


@dataclass
class Reforma:
    """Una norma posterior que toca a esta."""

    id_norma: str
    relacion: str
    texto: str
    incorporada: bool
    preceptos: set = field(default_factory=set)
    dudas: list = field(default_factory=list)

    @property
    def legible(self) -> bool:
        """¿Se ha podido convertir su nota en una lista de preceptos?"""
        return not self.dudas and bool(self.preceptos)


@dataclass
class Informe:
    consolidado_hasta: str = ""        # ISO. La ultima version del articulado.
    estado: str = ""                   # lo que dice el BOE: Finalizado / ...
    reformas: list = field(default_factory=list)

    @property
    def pendientes(self) -> list:
        return [r for r in self.reformas if not r.incorporada]

    @property
    def preceptos_tocados(self) -> set:
        s = set()
        for r in self.pendientes:
            s |= r.preceptos
        return s

    @property
    def fiable(self) -> bool:
        """¿Se puede ingerir con marcado?

        SOLO si TODAS las reformas pendientes se dejan leer enteras. Una sola
        que no, y no se sabe que hay que marcar: se ingeriria una norma con la
        mitad de los avisos puestos, que es peor que no tenerla, porque la
        media que falta se cita con la misma seguridad que el resto.
        """
        return bool(self.pendientes) and all(r.legible for r in self.pendientes)

    @property
    def motivos(self) -> list:
        fuera = []
        for r in self.pendientes:
            for d in r.dudas:
                fuera.append(f"{r.id_norma}: {d}")
        return fuera


def _preceptos_de(texto: str) -> set:
    """Los preceptos que la nota nombra. Solo los que nombra.

    Las dos numeraciones NO se mezclan. «arts. 632-1.4» tiene dentro un «632»
    que el patron clasico lee como el articulo 632, que no existe: la primera
    version de esto devolvia 612, 631 y 632 de mas, inventados por el propio
    lector. Si el texto usa la numeracion del Codi, se usa solo esa.
    """
    codi = _RE_ART_CODI.findall(texto)
    s = {f"{a}-{b}" for a, b in codi}
    if not codi:
        s |= set(_RE_ART_CLASICO.findall(texto))
    for clase, ordinal in _RE_DISP.findall(texto):
        s.add(f"disposicion {clase.lower()} {ordinal.lower()}")
    return s


def _dudas_de(texto: str, relacion: str = "") -> list:
    """Por que esta nota NO se deja convertir en una lista.

    Se mira tambien la RELACION, no solo el texto: «SE CORRIGEN erratas» viene
    ahi, y su texto no nombra ni un precepto de esta norma -corrige erratas de
    OTRA-, asi que sin mirar la relacion el motivo se quedaba en «no nombra
    ninguno», que es verdad pero no explica nada.
    """
    junto = f"{relacion} {texto}"
    return [motivo for patron, motivo in _VAGO
            if re.search(patron, junto, re.IGNORECASE)]


def leer(analisis: dict, xml_bytes: bytes, estado: str = "") -> Informe:
    """`/analisis` + `/texto` del BOE -> que falta por incorporar."""
    import xml.etree.ElementTree as ET

    raiz = ET.fromstring(xml_bytes)
    fechas = sorted(v.get("fecha_vigencia") for v in raiz.iter("version")
                    if v.get("fecha_vigencia"))
    # QUE ESTA YA DENTRO. No se pregunta a la lista de posteriores -que es el
    # historico- sino al articulado: si una norma escribio alguna version, sus
    # cambios estan incorporados.
    dentro = {v.get("id_norma") for v in raiz.iter("version") if v.get("id_norma")}

    informe = Informe(
        consolidado_hasta=(f"{fechas[-1][:4]}-{fechas[-1][4:6]}-{fechas[-1][6:8]}"
                           if fechas else ""),
        estado=estado,
    )
    bloques = (((analisis or {}).get("referencias") or {}).get("posteriores") or [])
    for bloque in bloques:
        for r in (bloque.get("posterior") or []):
            texto = r.get("texto") or ""
            informe.reformas.append(Reforma(
                id_norma=r.get("id_norma") or "(sin id)",
                relacion=((r.get("relacion") or {}).get("texto") or ""),
                texto=texto,
                incorporada=(r.get("id_norma") in dentro),
                preceptos=_preceptos_de(texto),
                dudas=_dudas_de(texto, (r.get('relacion') or {}).get('texto') or ''),
            ))
    return informe
