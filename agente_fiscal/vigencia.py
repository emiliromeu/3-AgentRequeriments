"""Avisos de fecha: que texto aplicaba en el ejercicio del caso.

Un caso de 2023 se contesta con el texto vigente en 2023. El corpus guarda
todas las versiones (fase 1), asi que aqui solo hay que elegir bien y avisar
cuando lo que se ensena no es lo que aplicaba.

Se usa SIEMPRE `fecha_vigencia_efectiva`, nunca el valor crudo: el BOE trae al
menos una errata (el articulo 115 dice tener vigencia desde el ano 998) y
comparar contra eso daria por vigente en cualquier ejercicio un texto que no lo
estaba.
"""

from __future__ import annotations

from dataclasses import dataclass

# Niveles de aviso. GRAVE significa: lo que se muestra no sirve para ese
# ejercicio sin mirar antes otra cosa.
GRAVE = "GRAVE"
NOTA = "nota"


@dataclass
class Aviso:
    nivel: str
    clave: str      # identificador corto del tipo de aviso
    texto: str


def limites(ejercicio: int) -> tuple[str, str]:
    return f"{ejercicio}-01-01", f"{ejercicio}-12-31"


def version_aplicable(registro: dict, fecha: str) -> dict | None:
    """Ultima version que ya estaba en vigor en `fecha`.

    None si en esa fecha el precepto todavia no existia.
    """
    candidata = None
    for v in registro.get("versiones") or []:
        f = v.get("fecha_vigencia_efectiva") or v.get("fecha_vigencia") or ""
        if f and f <= fecha:
            candidata = v
    return candidata


def avisos(registro: dict, ejercicio: int | None) -> list[Aviso]:
    """Avisos de fecha de un precepto para un ejercicio dado."""
    if ejercicio is None:
        return []

    inicio, fin = limites(ejercicio)
    salida: list[Aviso] = []

    versiones = registro.get("versiones") or []
    fechas = [
        v.get("fecha_vigencia_efectiva") or v.get("fecha_vigencia") or ""
        for v in versiones
    ]
    fechas = [f for f in fechas if f]
    if not fechas:
        salida.append(
            Aviso(GRAVE, "sin_fechas", "el precepto no tiene fechas de vigencia usables")
        )
        return salida

    primera = min(fechas)
    caducado = registro.get("caducado_desde") or ""

    # 1) Todavia no existia
    if primera > fin:
        salida.append(
            Aviso(
                GRAVE,
                "no_existia",
                f"en {ejercicio} este precepto NO EXISTIA todavia: "
                f"entro en vigor el {primera}",
            )
        )
        return salida

    # 2) Caducado antes o durante el ejercicio
    if caducado:
        if caducado <= inicio:
            salida.append(
                Aviso(
                    GRAVE,
                    "caducado",
                    f"CADUCADO el {caducado}: ya no se aplicaba en {ejercicio}",
                )
            )
        elif caducado <= fin:
            salida.append(
                Aviso(
                    GRAVE,
                    "caduca_durante",
                    f"CADUCA el {caducado}, dentro de {ejercicio}: solo se aplico "
                    f"parte del ejercicio",
                )
            )

    # 3) El texto que se muestra no es el que aplicaba
    aplicable = version_aplicable(registro, fin)
    if aplicable is not None and versiones:
        ultima = versiones[-1]
        if aplicable.get("orden") != ultima.get("orden"):
            f_ult = ultima.get("fecha_vigencia_efectiva") or ultima.get("fecha_vigencia")
            f_apl = aplicable.get("fecha_vigencia_efectiva") or aplicable.get(
                "fecha_vigencia"
            )
            salida.append(
                Aviso(
                    GRAVE,
                    "texto_cambiado",
                    f"el texto vigente HOY (desde {f_ult}) NO es el que aplicaba en "
                    f"{ejercicio}; entonces regia la version del {f_apl}",
                )
            )

    # 4) Cambio a mitad de ejercicio: en el mismo ano rigieron dos textos
    dentro = [f for f in fechas if inicio < f <= fin]
    if dentro:
        salida.append(
            Aviso(
                GRAVE,
                "cambio_durante",
                f"el precepto CAMBIO durante {ejercicio} "
                f"({', '.join(sorted(dentro))}): comprueba la fecha del devengo",
            )
        )

    # 5) Cambios posteriores: no afectan al caso, pero conviene saber que los hay
    posteriores = [f for f in fechas if f > fin]
    if posteriores and not any(a.clave == "texto_cambiado" for a in salida):
        salida.append(
            Aviso(
                NOTA,
                "cambio_posterior",
                f"hubo cambios despues de {ejercicio} ({', '.join(sorted(posteriores))})",
            )
        )

    return salida


def resumen_version(registro: dict, ejercicio: int | None) -> str:
    """Una linea con que version se esta mirando."""
    versiones = registro.get("versiones") or []
    if not versiones:
        return "sin versiones"
    if ejercicio is None:
        ultima = versiones[-1]
        f = ultima.get("fecha_vigencia_efectiva") or ultima.get("fecha_vigencia")
        return f"texto vigente hoy (desde {f}), {len(versiones)} version(es)"
    _, fin = limites(ejercicio)
    apl = version_aplicable(registro, fin)
    if apl is None:
        return f"no habia texto en vigor en {ejercicio}"
    f = apl.get("fecha_vigencia_efectiva") or apl.get("fecha_vigencia")
    return (
        f"version aplicable en {ejercicio}: la del {f} "
        f"({apl.get('orden', 0) + 1} de {len(versiones)})"
    )
