"""Carga del fichero .env. Solo libreria estandar: nada de python-dotenv.

ORDEN DE BUSQUEDA, y es el que se le cuenta al usuario:

    1. variable de entorno ya definida   (manda siempre)
    2. .env de la raiz del proyecto
    3. error claro

Que el entorno mande sobre el .env no es un detalle: permite saltarse el
fichero con un `export` puntual para una prueba, sin editar nada ni arriesgarse
a dejar una clave de pruebas dentro del .env.

LA CLAVE NO SE IMPRIME NUNCA. Ni entera, ni en una traza de error. Si hay que
ensenarla, `enmascarar` deja los 12 primeros caracteres y corta.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

NOMBRE_FICHERO = ".env"
VARIABLE = "ANTHROPIC_API_KEY"

# Cualquier cosa con pinta de credencial se tapa antes de imprimirla.
_RE_SECRETO = re.compile(r"(sk-ant-[A-Za-z0-9_-]{4})[A-Za-z0-9_-]+")


def enmascarar(valor: str, visibles: int = 12) -> str:
    """Deja los primeros caracteres y corta. Para poder decir CUAL se usa."""
    if not valor:
        return "(vacia)"
    return valor[:visibles] + "…" if len(valor) > visibles else valor + "…"


def limpiar(texto: str) -> str:
    """Tapa credenciales dentro de un texto libre (mensajes de error, trazas)."""
    return _RE_SECRETO.sub(r"\1…", texto or "")


@dataclass
class Origen:
    """De donde ha salido la credencial."""

    fuente: str = "ninguno"          # "entorno" | ".env" | "ninguno"
    ruta: str = ""
    cargadas: list = field(default_factory=list)   # claves leidas del .env
    avisos: list = field(default_factory=list)

    @property
    def hay_credencial(self) -> bool:
        return bool(os.environ.get(VARIABLE))

    def descripcion(self) -> str:
        if self.fuente == "entorno":
            return f"variable de entorno {VARIABLE}"
        if self.fuente == ".env":
            return f"fichero {self.ruta}"
        return "ninguna"


def leer_fichero(ruta: Path) -> tuple[dict, list]:
    """Parsea un .env. Devuelve (valores, avisos).

    Formato: una linea por variable, `CLAVE=valor`. Se parte por el PRIMER
    '=' (un valor puede llevar mas). Se ignoran las lineas vacias y las que
    empiezan por '#'. Se admite el prefijo `export ` por comodidad al pegar.
    """
    valores: dict[str, str] = {}
    avisos: list[str] = []
    try:
        contenido = ruta.read_text(encoding="utf-8")
    except OSError as e:
        return {}, [f"no se pudo leer {ruta}: {e}"]

    for n, linea in enumerate(contenido.splitlines(), 1):
        cruda = linea.strip()
        if not cruda or cruda.startswith("#"):
            continue
        if cruda.lower().startswith("export "):
            cruda = cruda[7:].lstrip()
        if "=" not in cruda:
            # Nada falla en silencio: se cuenta, sin ensenar el contenido por
            # si la linea llevara un secreto mal escrito.
            avisos.append(f"{ruta.name}:{n}: linea sin '=' , ignorada")
            continue
        clave, valor = cruda.split("=", 1)
        clave = clave.strip()
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        if not clave:
            avisos.append(f"{ruta.name}:{n}: sin nombre de variable, ignorada")
            continue
        valores[clave] = valor
    return valores, avisos


def cargar(raiz: Path | None = None) -> Origen:
    """Aplica el .env al entorno SIN pisar lo que ya estuviera definido.

    Es idempotente: se puede llamar tantas veces como haga falta.
    """
    raiz = Path(raiz) if raiz else Path(__file__).resolve().parent.parent
    ruta = raiz / NOMBRE_FICHERO
    origen = Origen(ruta=str(ruta))

    ya_en_entorno = bool(os.environ.get(VARIABLE))

    if ruta.is_file():
        valores, avisos = leer_fichero(ruta)
        origen.avisos.extend(avisos)
        for clave, valor in valores.items():
            if os.environ.get(clave):
                continue          # el entorno manda: no se pisa
            os.environ[clave] = valor
            origen.cargadas.append(clave)

    if ya_en_entorno:
        origen.fuente = "entorno"
    elif VARIABLE in origen.cargadas:
        origen.fuente = ".env"
    else:
        origen.fuente = "ninguno"
        if not ruta.is_file():
            origen.avisos.append(f"no existe {ruta}")
    return origen
