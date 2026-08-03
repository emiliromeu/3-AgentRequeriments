"""EL CRITERIO DE LA DGT, VISTO DESDE EL AGENTE.

Este modulo es el puente entre lo que `petete.py` deja en la cache y el resto
del sistema. Nada mas. Aqui se decide como se cita una consulta, como se
comprueba y que dice del estado; la descarga vive en `petete.py` y no se toca.

----------------------------------------------------------------------------
DE QUE SE FIA ESTE MODULO, Y DE QUE NO
----------------------------------------------------------------------------
EL EXTRACTOR DE HTML NUNCA HA VISTO UN DOCUMENTO REAL DE PETETE. La fuente
llevaba caida todo el reconocimiento (fase 9 y 9A), asi que el troceo del HTML
esta escrito contra las etiquetas del formulario y sin confirmar.

Por eso aqui NO se mira ni una linea de HTML. Este modulo se apoya UNICAMENTE
en la forma del REGISTRO CACHEADO, que es un JSON que escribimos nosotros:

    numero  fecha  organo  normativa  cuestion_planteada
    descripcion_hechos  contestacion  doc_id  url_navegador  descargado

Si manana el troceo cambia, cambia `petete.py` y este modulo sigue igual. Y si
un campo viene vacio, aqui se trata como ausente, nunca se adivina.

----------------------------------------------------------------------------
CRITERIO NO ES NORMA
----------------------------------------------------------------------------
Una consulta de la DGT vincula a la Administracion frente al consultante, pero
NO es una norma. No fundamenta por si sola. Todo lo de aqui esta hecho para que
esa diferencia se vea a simple vista: el formato de cita, el orden en la
respuesta y lo que se le dice al redactor.

----------------------------------------------------------------------------
EL INTERRUPTOR
----------------------------------------------------------------------------
Con la DGT APAGADA el sistema se comporta EXACTAMENTE como antes de la fase 9B.
Esta apagada por defecto, y seguira apagada hasta que el extractor haya visto un
documento real: mientras eso no pase, la DGT no esta de verdad.

    AGENTE_DGT=1 python fase4.py consultar ...     la enciende
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_CACHE = RAIZ / "datos" / "dgt"
DIR_CONSULTAS = DIR_CACHE / "consultas"
MARCA_FUENTE = DIR_CACHE / "estado_fuente.json"

VARIABLE = "AGENTE_DGT"

# Como se cita. El formato es distinto del de la ley A PROPOSITO: quien lee la
# respuesta tiene que ver sin esfuerzo que esto es criterio y no norma.
ETIQUETA = "Consulta DGT"

# "DGT V1601-22", "consulta V1601-22", "consulta vinculante V1601-22"
RE_NUM_CONSULTA = re.compile(
    r"\b(?:DGT|consulta(?:\s+vinculante)?)\s+(?P<num>[VC]?\d{3,5}-\d{2})\b",
    re.IGNORECASE,
)
RE_NUM_SUELTO = re.compile(r"\b(?P<num>V\d{3,5}-\d{2})\b")

URL_NAVEGADOR = ("https://petete.tributos.hacienda.gob.es/consultas/"
                 "?num_consulta={num}")

# Un articulo nombrado dentro del campo 'normativa' de una consulta.
_SUFIJOS = (r"bis|ter|qu[aá]ter|quinquies|sexies|septies|octies|nonies|decies|"
            r"undecies|duodecies|terdecies|quaterdecies|quindecies|"
            r"quinquiesdecies|sexiesdecies|septiesdecies|octiesdecies|"
            r"noniesdecies|vicies")
_RE_PRECEPTO = re.compile(
    r"\bart(?:[íi]culos?)?\.?\s*(?P<num>\d+(?:\s+(?:" + _SUFIJOS + r"))?)",
    re.IGNORECASE,
)


def activa() -> bool:
    """Si la DGT participa. Apagada por defecto: ver la cabecera."""
    return os.environ.get(VARIABLE, "").strip() not in ("", "0", "no", "off")


# --------------------------------------------------------------- la consulta


@dataclass
class Consulta:
    """Una consulta cacheada. Solo campos del registro, nada de HTML."""

    numero: str
    fecha: str = ""
    organo: str = ""
    normativa: str = ""
    cuestion: str = ""
    hechos: str = ""
    contestacion: str = ""
    url: str = ""
    descargado: str = ""

    @classmethod
    def de_registro(cls, r: dict) -> "Consulta":
        return cls(
            numero=(r.get("numero") or "").upper(),
            fecha=r.get("fecha") or "",
            organo=r.get("organo") or "",
            normativa=r.get("normativa") or "",
            cuestion=r.get("cuestion_planteada") or "",
            hechos=r.get("descripcion_hechos") or "",
            contestacion=r.get("contestacion") or "",
            url=r.get("url_navegador") or URL_NAVEGADOR.format(
                num=(r.get("numero") or "").upper()),
            descargado=r.get("descargado") or "",
        )

    @property
    def anio(self) -> int | None:
        """El año de la consulta. Sale del numero (V1601-**22**), y si no, de
        la fecha. El numero es mas fiable: la fecha la escribe la plantilla."""
        m = re.search(r"-(\d{2})$", self.numero)
        if m:
            n = int(m.group(1))
            return 2000 + n if n < 80 else 1900 + n
        m = re.search(r"(\d{4})", self.fecha)
        return int(m.group(1)) if m else None

    @property
    def preceptos_citados(self) -> set:
        """Que articulos nombra el campo 'normativa'. Sin inventar nada: si el
        campo viene vacio, el conjunto es vacio y no se supone nada.

        Reconoce las dos formas, porque el campo las mezcla sin criterio:
        «Ley 37/1992 art. 80» y «articulo 80». El sufijo latino solo se admite
        de una lista cerrada: con `\\w+` se tragaba la palabra siguiente y
        «art. 80 de la Ley» acababa siendo el articulo «80 de».
        """
        salida = set()
        for m in _RE_PRECEPTO.finditer(self.normativa or ""):
            salida.add(re.sub(r"\s+", " ", m.group("num")).strip().lower())
        return salida

    def cita(self) -> str:
        """El formato de cita. Numero, fecha y enlace de navegador."""
        fecha = f", de {self.fecha}" if self.fecha else ""
        return f"[{ETIQUETA} {self.numero}{fecha} — {self.url}]"


# ------------------------------------------------------------------- la cache


class CacheDGT:
    """Lectura de lo que dejo `petete.py`. Solo lectura: aqui no se descarga."""

    def __init__(self, directorio: Path | None = None):
        self.dir = Path(directorio) if directorio else DIR_CONSULTAS
        self._memo: dict[str, Consulta | None] = {}

    def leer(self, numero: str) -> Consulta | None:
        numero = (numero or "").upper()
        if numero in self._memo:
            return self._memo[numero]
        f = self.dir / f"{numero}.json"
        consulta = None
        if f.is_file():
            try:
                consulta = Consulta.de_registro(
                    json.loads(f.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                consulta = None
        self._memo[numero] = consulta
        return consulta

    def tiene(self, numero: str) -> bool:
        return self.leer(numero) is not None

    def todas(self) -> list:
        if not self.dir.is_dir():
            return []
        salida = []
        for f in sorted(self.dir.glob("*.json")):
            c = self.leer(f.stem)
            if c:
                salida.append(c)
        return salida

    def buscar(self, terminos: str, tope: int = 3) -> list:
        """Busqueda LOCAL sobre lo cacheado. No sale a la red jamas.

        Es deliberadamente simple -cobertura de palabras- porque su trabajo no
        es rankear: es traer criterio que ya tenemos para que el redactor lo
        vea. Lo que decide la respuesta sigue siendo la ley.
        """
        from . import texto as T

        raices = set(T.tokenizar(terminos))
        if not raices:
            return []
        puntuadas = []
        for c in self.todas():
            campos = " ".join((c.cuestion, c.hechos, c.normativa,
                               c.contestacion))
            presentes = set(T.tokenizar(campos))
            comunes = raices & presentes
            if not comunes:
                continue
            puntuadas.append((len(comunes) / len(raices), c.anio or 0, c))
        # Mas cobertura primero; a igualdad, la mas reciente. La fecha manda.
        puntuadas.sort(key=lambda x: (-x[0], -x[1]))
        return [c for _, _, c in puntuadas[:tope]]


# ------------------------------------------------------- el estado de la fuente


def marcar_fuente(viva: bool, motivo: str = "") -> None:
    """Deja escrito si la fuente respondia la ultima vez. Lo escribe el canario."""
    DIR_CACHE.mkdir(parents=True, exist_ok=True)
    MARCA_FUENTE.write_text(json.dumps({
        "viva": bool(viva),
        "motivo": motivo,
        "cuando": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def fuente_viva() -> tuple[bool, str]:
    """(viva, motivo). Si nunca se ha comprobado, se asume CAIDA.

    Asumir que esta viva sin haberlo comprobado seria justo el fallo que la
    fase 9B viene a evitar: responder como si tuvieramos criterio cuando no
    sabemos si lo tenemos.
    """
    if not MARCA_FUENTE.is_file():
        return False, "la fuente no se ha comprobado todavia"
    try:
        d = json.loads(MARCA_FUENTE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False, "no se ha podido leer el estado de la fuente"
    return bool(d.get("viva")), d.get("motivo", "")


# --------------------------------------------------------- señales de estado


@dataclass
class Lectura:
    """Lo que la DGT aporta a una respuesta, ya masticado para el estado."""

    consultas: list = field(default_factory=list)   # Consulta, verificadas
    senales: list = field(default_factory=list)     # motivos de discusion
    antecedentes: list = field(default_factory=list)
    fuente_caida: bool = False
    motivo_fuente: str = ""

    @property
    def hay_discusion(self) -> bool:
        return bool(self.senales)


def _agrupar_por_precepto(consultas: list) -> dict:
    grupos: dict = {}
    for c in consultas:
        for p in (c.preceptos_citados or {"(sin precepto)"}):
            grupos.setdefault(p, []).append(c)
    return grupos


def leer_criterio(consultas: list, preceptos_verificados: list) -> Lectura:
    """Convierte las consultas citadas en señales de estado. LO CALCULA EL CODIGO.

    IMPORTANTE, y conviene no engañarse: el codigo NO puede leer si un criterio
    «apunta en otra direccion» que la norma. Eso es semantica y aqui no hay
    quien la juzgue. Lo que si se puede medir son señales ESTRUCTURALES, que es
    lo que se hace, y cada una dice exactamente lo que sabe:

      1. varias consultas sobre el MISMO precepto y de años distintos
         -> el criterio ha podido evolucionar. La mas reciente manda y las
            anteriores se citan como antecedente.
      2. una consulta cuyo campo 'normativa' NO toca ninguno de los preceptos
         que sostienen la respuesta
         -> el criterio va de otra cosa: no se puede dar por alineado.

    Ninguna de las dos afirma que haya contradiccion de fondo. Afirman que NO
    se puede afirmar que no la haya, que es lo que corresponde a un sistema que
    no lee, y por eso el estado que producen es DISCUTIDO y no NO ENCONTRADO.
    """
    lectura = Lectura(consultas=list(consultas))
    if not consultas:
        return lectura

    verificados = {re.sub(r"^articulo\s+", "", p.lower()).strip()
                   for p in (preceptos_verificados or [])}

    # --- 1. el tiempo: la mas reciente manda ---------------------------
    for precepto, grupo in _agrupar_por_precepto(consultas).items():
        if len(grupo) < 2:
            continue
        anios = {c.anio for c in grupo if c.anio}
        if len(anios) < 2:
            continue
        ordenadas = sorted(grupo, key=lambda c: c.anio or 0, reverse=True)
        reciente, previas = ordenadas[0], ordenadas[1:]
        lectura.senales.append(
            f"sobre el articulo {precepto} hay {len(grupo)} consultas de años "
            f"distintos: la mas reciente es {reciente.numero} "
            f"({reciente.anio}) y es la que manda; "
            f"{', '.join(c.numero for c in previas)} "
            f"{'son' if len(previas) > 1 else 'es'} anterior"
            f"{'es' if len(previas) > 1 else ''} y puede estar superad"
            f"{'as' if len(previas) > 1 else 'a'}"
        )
        lectura.antecedentes.extend(previas)

    # --- 2. criterio que no habla de lo que sostiene la respuesta -------
    if verificados:
        for c in consultas:
            citados = c.preceptos_citados
            if citados and not (citados & verificados):
                lectura.senales.append(
                    f"{c.numero} da criterio sobre {c.normativa or 'otra norma'}, "
                    f"que no es lo que sostiene esta respuesta: no se puede dar "
                    f"por alineado con la lectura de la norma"
                )

    return lectura
