"""Acceso a la API de datos abiertos de legislacion consolidada del BOE.

Regla de oro de este modulo: la respuesta cruda se escribe en disco ANTES de
que nadie la parsee, y no se borra nunca. Si mas adelante cambia el troceo,
se reprocesa desde el crudo sin volver a descargar.

Cada descarga deja tres cosas:
  - el fichero crudo, tal cual llego (bytes sin tocar)
  - un sidecar .meta.json con url, codigo, cabeceras, sha256 y tamano
  - una linea en manifiesto.jsonl (append-only, historico de descargas)

Nota de content-negotiation, comprobada contra el servidor real:
  /metadatos, /indice, /analisis  -> aceptan application/json
  /texto, /texto/bloque/{id}      -> SOLO application/xml (con json dan 400)
"""

from __future__ import annotations

import hashlib
import json
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://www.boe.es/datosabiertos/api/legislacion-consolidada/id"

# El BOE responde sin User-Agent, pero identificarse es de buena educacion
# y evita que un filtro anti-bot nos corte sin avisar.
USER_AGENT = "agente-fiscal-gestoria/1.0 (uso interno; python-urllib)"

TIEMPO_ESPERA = 60          # segundos por intento
REINTENTOS = 3
PAUSA_ENTRE_REINTENTOS = 2  # segundos, se duplica en cada intento


class ErrorBOE(Exception):
    """Fallo al hablar con la API del BOE. Nunca se traga en silencio."""


@dataclass
class Respuesta:
    """Una respuesta cruda ya persistida en disco."""

    url: str
    codigo: int
    cuerpo: bytes
    cabeceras: dict
    ruta: Path
    sha256: str

    @property
    def tamano(self) -> int:
        return len(self.cuerpo)


def _ahora_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _descargar(url: str, accept: str) -> tuple[int, bytes, dict]:
    """Un GET con reintentos. Devuelve (codigo, cuerpo, cabeceras).

    Los errores HTTP 4xx no se reintentan: si el servidor dice que la peticion
    esta mal, repetirla igual no la va a arreglar.
    """
    peticion = urllib.request.Request(
        url,
        headers={"Accept": accept, "User-Agent": USER_AGENT},
        method="GET",
    )
    contexto = ssl.create_default_context()
    ultimo_error: Exception | None = None

    for intento in range(1, REINTENTOS + 1):
        try:
            with urllib.request.urlopen(
                peticion, timeout=TIEMPO_ESPERA, context=contexto
            ) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            cuerpo = e.read()
            if 400 <= e.code < 500:
                # Error del cliente: devolvemos el cuerpo para poder mostrarlo.
                return e.code, cuerpo, dict(e.headers)
            ultimo_error = e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            ultimo_error = e

        if intento < REINTENTOS:
            time.sleep(PAUSA_ENTRE_REINTENTOS * intento)

    raise ErrorBOE(
        f"No se pudo descargar {url} tras {REINTENTOS} intentos. "
        f"Ultimo error: {ultimo_error!r}"
    )


def descargar_y_guardar(
    norma_id: str,
    recurso: str,
    accept: str,
    dir_crudo: Path,
    etiqueta: str,
) -> Respuesta:
    """Descarga un recurso y lo persiste en crudo antes de devolverlo.

    `recurso` es el sufijo tras el identificador: "", "/metadatos",
    "/texto", "/texto/indice", "/analisis".
    """
    url = f"{BASE}/{norma_id}{recurso}"
    codigo, cuerpo, cabeceras = _descargar(url, accept)

    destino_dir = dir_crudo / norma_id
    destino_dir.mkdir(parents=True, exist_ok=True)

    sello = _ahora_utc()
    extension = "xml" if "xml" in accept else "json"
    # Una respuesta fallida tambien se guarda (hace falta para diagnosticar),
    # pero con otro nombre: si se llamase igual que una buena, la siguiente
    # ejecucion la reutilizaria como si fuera el corpus. Ya paso una vez: un
    # 404 en XML acabo entrando por donde se esperaba el JSON de metadatos.
    prefijo = etiqueta if codigo == 200 else f"fallo-{etiqueta}"
    ruta = destino_dir / f"{prefijo}_{sello}.{extension}"

    # Escritura primero. Si el parseo revienta despues, el crudo ya esta a salvo.
    ruta.write_bytes(cuerpo)
    sha = hashlib.sha256(cuerpo).hexdigest()

    sidecar = {
        "url": url,
        "codigo_http": codigo,
        "accept": accept,
        "descargado_utc": sello,
        "bytes": len(cuerpo),
        "sha256": sha,
        "cabeceras": cabeceras,
        "fichero": ruta.name,
    }
    ruta.with_suffix(ruta.suffix + ".meta.json").write_text(
        json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    manifiesto = destino_dir / "manifiesto.jsonl"
    with manifiesto.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(sidecar, ensure_ascii=False) + "\n")

    if codigo != 200:
        raise ErrorBOE(
            f"El BOE respondio {codigo} a {url}\n"
            f"  Accept enviado: {accept}\n"
            f"  Crudo guardado en: {ruta}\n"
            f"  Cuerpo: {cuerpo[:400].decode('utf-8', 'replace')}"
        )

    return Respuesta(url, codigo, cuerpo, cabeceras, ruta, sha)


def ultimo_crudo(norma_id: str, dir_crudo: Path, etiqueta: str) -> Path | None:
    """Ruta al crudo mas reciente de ese recurso, o None si no hay ninguno.

    Permite reprocesar sin volver a pedirle nada al BOE.
    """
    destino_dir = dir_crudo / norma_id
    if not destino_dir.is_dir():
        return None
    candidatos = [
        p
        for p in destino_dir.iterdir()
        if p.name.startswith(etiqueta + "_") and not p.name.endswith(".meta.json")
    ]

    # Cinturon y tirantes: ademas del nombre, se comprueba en el sidecar que
    # aquella descarga fue realmente un 200.
    def fue_correcta(p: Path) -> bool:
        sidecar = p.with_suffix(p.suffix + ".meta.json")
        if not sidecar.exists():
            return True  # crudo antiguo sin sidecar: se acepta
        try:
            return json.loads(sidecar.read_text(encoding="utf-8")).get("codigo_http") == 200
        except (json.JSONDecodeError, OSError):
            return False

    validos = [p for p in candidatos if fue_correcta(p)]
    if not validos:
        return None
    # El sello temporal va en el nombre, asi que ordenar por nombre basta.
    return sorted(validos, key=lambda p: p.name)[-1]
