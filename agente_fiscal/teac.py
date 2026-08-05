"""LA DOCTRINA DEL TEAC, VISTA DESDE EL AGENTE.

Puente entre lo que `teac.py` deja en la cache y el resto del sistema. La
descarga vive alli y aqui no se toca.

----------------------------------------------------------------------------
LA JERARQUIA, QUE AHORA SI SE PUEDE APLICAR
----------------------------------------------------------------------------
        ley y reglamento   >   TEAC   >   DGT

No es una preferencia de estilo. El criterio del TEAC VINCULA A TODA LA
ADMINISTRACION TRIBUTARIA (art. 239.8 LGT); una consulta de la DGT vincula
frente a QUIEN CONSULTO. No pesan igual, y presentarlas igual seria decirle al
profesional una falsedad sobre el valor de lo que esta leyendo.

Por eso, en la respuesta: primero la norma, despues el TEAC, despues la DGT,
cada bloque etiquetado y nunca mezclados en el mismo parrafo. Y dentro del
TEAC, la «unificacion de criterio» pesa mas que un criterio suelto.

----------------------------------------------------------------------------
LA BUSQUEDA ENCAJA SOLA
----------------------------------------------------------------------------
Al TEAC se le pregunta POR PRECEPTO, y el agente ya sabe que preceptos
sostienen la respuesta: se los acaba de traer el buscador. Asi que aqui no se
buscan palabras como en la DGT -que fue lo que obligo a inventar terminos-,
sino que se pregunta directamente «que dice el TEAC sobre estos articulos».

Quien resuelve el nombre de la norma que cita un criterio es
`normas.Registro.resolver`, el mismo de siempre. Aqui no hay resolutor nuevo.

----------------------------------------------------------------------------
DE QUE SE FIA ESTE MODULO
----------------------------------------------------------------------------
Solo de la forma del REGISTRO CACHEADO. Ni una linea de HTML: el troceo vive en
`teac.py` y si cambia, cambia alli.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_CACHE = RAIZ / "datos" / "teac"
DIR_CRITERIOS = DIR_CACHE / "criterios"
MARCA_FUENTE = DIR_CACHE / "estado_fuente.json"

VARIABLE = "AGENTE_TEAC"

# Como se cita. TRES FUENTES, TRES FORMAS, distinguibles a simple vista:
#
#     ley    (articulo 95 de la Ley 37/1992, https://www.boe.es/...)
#     TEAC   {Criterio TEAC 00/06614/2024/00/00, de 21/05/2026 — https://...}
#     DGT    [Consulta DGT V1601-22, de 01/07/2022 — https://petete...]
#
# Parentesis, llaves y corchetes. No hace falta leer para saber cual es cual.
ETIQUETA = "Criterio TEAC"

# ---------------------------------------------------------------------------
# LA UNIDAD RESOLUTORIA. UN TEAR NO ES EL TEAC.
# ---------------------------------------------------------------------------
# EL DEFECTO QUE ESTO ARREGLA, y estaba en produccion apagado: la busqueda de
# DYCTEA manda el filtro de unidad VACIO, asi que devuelve TODOS los tribunales.
# En la copia local de 9 criterios habia dos que no eran del TEAC -uno del TEAR
# de Baleares y otro del de Madrid- y se citaban asi:
#
#     {Criterio TEAC 07/02872/2023/00/00, de 29/04/2025, TEAR de Baleares — ...}
#
# La etiqueta decia TEAC y la unidad decia TEAR, en la misma linea. Y el bloque
# del material les atribuia la fuerza del articulo 239.8 LGT, que un TEAR no
# tiene. Presentar como vinculante lo que no lo es es exactamente el fallo que
# este proyecto existe para no cometer.
#
# LA ETIQUETA SALE DEL REGISTRO. La fuente dice de quien es cada resolucion en
# el campo `unidad`; aqui no se supone nada.
CENTRAL = "TEAC"


def es_central(unidad: str) -> bool:
    """¿Es del TEAC? Solo si la fuente lo dice con ese nombre exacto."""
    return " ".join((unidad or "").split()).upper() == CENTRAL


def etiqueta_de(unidad: str) -> str:
    """Como se nombra una resolucion segun QUIEN la dicto.

        TEAC             -> «Criterio TEAC»
        TEAR de Cataluña -> «Resolucion del TEAR de Cataluña»
        (sin unidad)     -> «Resolucion economico-administrativa»

    El TEAR NUNCA se nombra «criterio»: un criterio es doctrina, y la doctrina
    la sienta el TEAC. Llamar criterio a una resolucion regional es decir que
    obliga a alguien cuando no obliga a nadie mas que al caso que resuelve.
    """
    u = " ".join((unidad or "").split())
    if not u:
        return "Resolucion economico-administrativa"
    if es_central(u):
        return ETIQUETA
    return f"Resolucion del {u}"


# ---------------------------------------------------------------------------
# LA FUERZA SALE DE LA CALIFICACION DE LA FUENTE, NO DE NOSOTROS
# ---------------------------------------------------------------------------
# DYCTEA califica cada resolucion -«Doctrina», «No vinculante»- y esa es la
# fuente de verdad sobre que obliga, igual que el codigo de norma lo era sobre
# que norma es. Aqui no se inventa jerarquia: se lee la suya.
#
# Y se combinan LOS DOS CAMPOS, porque hacen falta los dos: la fuerza del
# articulo 239.8 LGT es del TEAC cuando sienta doctrina. Ni un TEAR con la
# calificacion mas alta la tiene, ni un TEAC «No vinculante».
DOCTRINA = "doctrina"
NO_VINCULANTE = "no vinculante"


def fuerza_de(unidad: str, calificacion: str) -> str:
    """Que se puede AFIRMAR sobre lo que obliga esta resolucion.

    Ante calificacion desconocida NO se afirma nada. Es la regla de siempre:
    callar cuesta una frase, atribuir fuerza de mas cuesta un cliente.
    """
    c = " ".join((calificacion or "").split()).lower()
    central = es_central(unidad)

    if c.startswith(DOCTRINA):
        if central:
            return ("SIENTA DOCTRINA y VINCULA A TODA LA ADMINISTRACION "
                    "TRIBUTARIA (art. 239.8 de la Ley 58/2003)")
        return (f"la fuente la califica de «{calificacion}», pero la dicto un "
                f"tribunal REGIONAL: no vincula a toda la Administracion, que "
                f"es fuerza reservada a la doctrina del TEAC")
    if c.startswith(NO_VINCULANTE):
        return ("NO VINCULA: la propia fuente la califica de «No vinculante». "
                "Resuelve su caso y no obliga en ningun otro")
    if not c:
        return ("la fuente NO dice que fuerza tiene: no se le supone ninguna")
    return (f"la fuente la califica de «{calificacion}», que no sabemos "
            f"traducir a fuerza vinculante: no se le supone ninguna")

RE_ID_CRITERIO = re.compile(r"\b(?P<id>\d{2}/\d{4,5}/\d{4}/\d{2}/\d{1,2}(?:/\d+)?)\b")

# Cuantos criterios se nombran dentro de un aviso agrupado antes de resumir en
# «y N mas». Los que unifican criterio van siempre delante, asi que son los que
# sobreviven al corte. La lista completa esta en el material y en la traza.
TOPE_NOMBRADOS = 4

URL_NAVEGADOR = ("https://serviciostelematicosext.hacienda.gob.es/TEAC/DYCTEA/"
                 "criterio.aspx?id={id}")


def activa() -> bool:
    """Interruptor PROPIO, distinto del de la DGT. Apagado por defecto."""
    return os.environ.get(VARIABLE, "").strip() not in ("", "0", "no", "off")


# ------------------------------------- que norma de DYCTEA es cual de las nuestras
#
# EL PROBLEMA QUE ESTO RESUELVE. DYCTEA nombra al Reglamento del IVA como
# «RD 1624/1992 Reglamento Impuesto sobre el Valor Añadido IVA». Ese nombre
# menciona DOS cosas que en nuestro corpus son dos cuerpos distintos -el Real
# Decreto y el Reglamento que aprueba-, asi que el resolutor no puede decidir y
# devuelve vacio. Hace bien: ante la duda, nada. Pero la consecuencia era que
# TODA la doctrina del TEAC sobre el Reglamento se perdia sin decir nada.
#
# La salida no es adivinar mejor, es dejar de adivinar: DYCTEA identifica cada
# norma con un CODIGO estable, y ese codigo no es ambiguo. Se mapea una vez,
# a mano, y aqui esta a la vista de cualquiera:
MAPA_DYCTEA = {
    # codigo DYCTEA        designacion nuestra, que el resolutor entiende sola
    "02:07:01:00:00": "Ley 37/1992",
    "02:07:02:00:00": "Reglamento del Impuesto sobre el Valor Añadido",
    "01:02:01:00:00": "Ley 58/2003",
}
# Los codigos NO se escriben de memoria: se leen del catalogo que baja
# `teac.py` (`python teac.py buscar --norma "..."` lo deja en
# datos/teac/catalogo.json). La primera version de este mapa llevaba
# 01:01:01:00:00 para la LGT y el real es 01:02:01:00:00.
#
# Se mapea a una DESIGNACION y no a la clave del cuerpo a proposito: la clave
# depende de como este montado el corpus hoy, y la designacion la resuelve
# `normas.resolver`, que es quien sabe de eso. Si manana cambia el corpus, esto
# sigue valiendo.

CATALOGO = DIR_CACHE / "catalogo.json"
_catalogo_nombres: dict | None = None


def _codigo_de(nombre: str) -> str:
    """El codigo DYCTEA de una norma, por su nombre EXACTO.

    La pagina del criterio no trae el codigo, solo el nombre. Pero el catalogo
    de DYCTEA -que baja `teac.py`- empareja codigo y nombre, y el nombre que
    escribe en el criterio es LITERALMENTE el mismo. Asi que esto no es
    interpretar un nombre: es buscarlo en la tabla de la propia fuente. Si no
    coincide exactamente, no se devuelve nada.
    """
    global _catalogo_nombres
    if _catalogo_nombres is None:
        _catalogo_nombres = {}
        if CATALOGO.is_file():
            try:
                cat = json.loads(CATALOGO.read_text(encoding="utf-8"))
                for cod, nom in (cat.get("normas") or {}).items():
                    _catalogo_nombres[" ".join(nom.split())] = cod
            except (json.JSONDecodeError, OSError):
                _catalogo_nombres = {}
    return _catalogo_nombres.get(" ".join((nombre or "").split()), "")


def resolver_norma(nombre: str, normas=None, codigo: str = "") -> tuple:
    """(clave_cuerpo, como_se_resolvio). Cadena vacia si no se puede decidir.

    Se prueba EN ESTE ORDEN:
      1. por CODIGO de DYCTEA, que es el identificador de la fuente y no
         admite dos lecturas;
      2. si no hay codigo mapeado, por NOMBRE, con el resolutor de siempre.
         Si el nombre es ambiguo devuelve vacio, como hasta ahora.

    Un codigo que no este en el mapa NO se intenta adivinar por el nombre: es
    una norma que no tenemos, y decirlo es mejor que acertar por casualidad.
    """
    if normas is None:
        return "", "sin registro de normas"

    cod = codigo or _codigo_de(nombre)
    if cod:
        designacion = MAPA_DYCTEA.get(cod)
        if not designacion:
            return "", f"codigo {cod} no mapeado: es una norma que no tenemos"
        clave, _motivo = normas.resolver(designacion)
        return (clave or ""), f"por codigo {cod}"

    # Sin codigo: el respaldo de siempre, con su regla de siempre.
    from . import dgt as _D
    clave, _estado = _D._resolver_designacion(nombre, normas)
    return clave, ("por nombre" if clave else "el nombre no resuelve")


def clave_resolucion(ident: str) -> tuple:
    """La resolucion a la que pertenece un identificador, comparable.

    DYCTEA usa DOS formas para lo mismo y las mezcla en la misma pagina:

        resolucion   00/06614/2024/00/00
        criterio     00/06614/2024/00/0/1     (la resolucion + el nº de criterio)

    Comparar las cadenas tal cual hace que una cita CORRECTA -que nombra la
    resolucion y enlaza al criterio- salga rechazada, porque «00» y «0» no
    empiezan igual. Se normalizan los cuatro primeros tramos y el quinto como
    numero; el sexto, si esta, es el numero de criterio y no cuenta para saber
    de que resolucion hablamos.
    """
    partes = [x for x in (ident or "").strip().split("/") if x != ""]
    if len(partes) < 5:
        return tuple(partes)
    cabeza = tuple(partes[:4])
    try:
        quinto = int(partes[4])
    except ValueError:
        quinto = partes[4]
    return cabeza + (quinto,)


def mismo_criterio(a: str, b: str) -> bool:
    """¿Dos identificadores apuntan a la misma resolucion del TEAC?"""
    ka, kb = clave_resolucion(a), clave_resolucion(b)
    return bool(ka) and ka == kb


def _plano(texto: str) -> str:
    """Sin tildes y en minusculas, SOLO para comparar rotulos.

    El fragmento citado se sigue comprobando letra por letra, con tildes: eso
    no se toca. Aqui se compara el ROTULO que escribimos nosotros -«TEAR de
    Cataluña»- y exigirle la eñe al modelo seria tumbar una respuesta correcta
    por un problema de teclado.
    """
    import unicodedata

    d = unicodedata.normalize("NFD", texto or "")
    return " ".join("".join(c for c in d
                            if unicodedata.category(c) != "Mn").lower().split())


# Los tres desenlaces de comprobar el rotulo. NO son dos: «no se puede saber»
# es distinto de «esta mal», y meterlos en el mismo saco obliga a elegir entre
# tumbar una cita correcta o dar por buena una atribucion sin comprobar.
ROTULO_OK = "ok"
ROTULO_MAL = "mal"
ROTULO_SIN_UNIDAD = "sin_unidad"


def rotulo_valido(bruto: str, unidad: str) -> tuple:
    """(estado, motivo). ¿El rotulo de la cita dice el tribunal que de verdad es?

    LO QUE ESTO PARA, y estaba pasando: la copia local tenia resoluciones del
    TEAR de Baleares y de Madrid citadas como «Criterio TEAC». El rotulo decia
    un tribunal y el documento era de otro, y con el rotulo iba la fuerza del
    articulo 239.8 LGT, que un TEAR no tiene.

    Se comprueba en los dos sentidos, porque los dos enganan:
      · llamar TEAC a lo que es de un TEAR   -> le da fuerza que no tiene;
      · llamar TEAR a lo que es del TEAC     -> se la quita, y el profesional
        descarta doctrina que si le obliga.
    """
    dice = _plano(bruto)
    real = " ".join((unidad or "").split())

    # SIN UNIDAD EN LA COPIA LOCAL NO SE PUEDE COMPROBAR, y eso no es «vale».
    # Dar el visto bueno seria dejar pasar la atribucion sin mirarla, que es la
    # trampa comoda de todo verificador; rechazarla seria tumbar la respuesta
    # por un hueco NUESTRO. Es el tercer estado, que existe justo para esto.
    if not real:
        return ROTULO_SIN_UNIDAD, (
            "la copia local no dice que tribunal dicto esta resolucion, asi "
            "que no se puede comprobar si la cita se la atribuye bien")

    # «Criterio TEAC 00/...» o «resolucion del TEAC 00/...», pero NO
    # «resolucion del TEAR de ...», que tambien lleva las letras t-e-a.
    dice_central = bool(re.search(r"\b(criterio\s+teac|del\s+teac|^teac)\b", dice))

    if es_central(real):
        if not dice_central:
            return ROTULO_MAL, (
                "la cita no la presenta como criterio del TEAC y lo es: quien "
                "lea esto descartara doctrina que si le vincula")
        return ROTULO_OK, ""

    if dice_central:
        return ROTULO_MAL, (
            f"la cita la presenta como criterio del TEAC y es una "
            f"{etiqueta_de(real).lower()}: un tribunal regional no vincula a "
            f"toda la Administracion")
    if _plano(real) not in dice:
        return ROTULO_MAL, (
            f"la cita no dice que tribunal la dicto, y fue el {real}: sin eso "
            f"no se sabe si obliga a alguien")
    return ROTULO_OK, ""


# ------------------------------------------------------------------ criterio


def _numero_articulo(precepto: str) -> str:
    """«80.4.B)» -> «80». El TEAC cita al nivel de apartado; nosotros tenemos
    el corpus al nivel de articulo, asi que se compara por el articulo."""
    m = re.match(r"\s*(\d+(?:\s+(?:bis|ter|quater|quinquies|sexies|septies|"
                 r"octies|nonies|decies))?)", precepto or "", re.IGNORECASE)
    return re.sub(r"\s+", " ", m.group(1)).strip().lower() if m else ""


@dataclass
class Criterio:
    """Un criterio cacheado. Solo campos del registro, nada de HTML."""

    id: str
    resolucion: str = ""
    fecha: str = ""
    unidad: str = ""
    calificacion: str = ""
    asunto: str = ""
    criterio: str = ""
    referencias: list = field(default_factory=list)
    conceptos: list = field(default_factory=list)
    consultas_dgt: list = field(default_factory=list)
    unifica_criterio: bool = False
    url: str = ""

    @classmethod
    def de_registro(cls, r: dict) -> "Criterio":
        ident = r.get("id") or ""
        return cls(
            id=ident,
            resolucion=r.get("resolucion") or "",
            fecha=r.get("fecha") or "",
            unidad=r.get("unidad") or "",
            calificacion=r.get("calificacion") or "",
            asunto=r.get("asunto") or "",
            criterio=r.get("criterio") or "",
            referencias=r.get("referencias") or [],
            conceptos=r.get("conceptos") or [],
            consultas_dgt=[c.upper() for c in (r.get("consultas_dgt") or [])],
            unifica_criterio=bool(r.get("unifica_criterio")),
            url=r.get("url_navegador") or URL_NAVEGADOR.format(id=ident),
        )

    @property
    def anio(self) -> int | None:
        m = re.search(r"/(\d{4})$", self.fecha)
        return int(m.group(1)) if m else None

    def preceptos(self, normas=None) -> list:
        """[(cuerpo_clave|'', numero)] de lo que cita, POR NORMA.

        Las referencias vienen ya agrupadas por norma desde DYCTEA, asi que
        aqui no se interpreta prosa: solo se resuelve el nombre de la norma
        contra el corpus. Es la diferencia con la DGT, y por eso este modulo
        es la mitad de largo que `dgt.py`.
        """
        salida = []
        for ref in self.referencias:
            # POR CODIGO, no por nombre: ver `resolver_norma`. El nombre solo
            # entra como respaldo cuando la fuente no da codigo.
            cuerpo, _como = resolver_norma(ref.get("norma", ""), normas,
                                           ref.get("codigo", ""))
            for p in ref.get("preceptos") or []:
                num = _numero_articulo(p)
                if num:
                    salida.append((cuerpo, num))
        return salida

    @property
    def es_central(self) -> bool:
        return es_central(self.unidad)

    @property
    def etiqueta(self) -> str:
        """Del registro, nunca fija. Ver `etiqueta_de`."""
        return etiqueta_de(self.unidad)

    @property
    def fuerza(self) -> str:
        return fuerza_de(self.unidad, self.calificacion)

    def cita(self) -> str:
        fecha = f", de {self.fecha}" if self.fecha else ""
        # La unidad ya va DENTRO de la etiqueta de un TEAR («Resolucion del
        # TEAR de Cataluña»); repetirla detras seria decirla dos veces.
        unidad = f", {self.unidad}" if (self.unidad and self.es_central) else ""
        return ("{" + f"{self.etiqueta} {self.resolucion}{fecha}{unidad} — "
                f"{self.url}" + "}")


# ------------------------------------------------------------------ el orden


# Los niveles de peso juridico, de mas a menos. Solo miran unidad y
# calificacion -lo que dice la fuente-, nunca la fecha: la fecha ordena DENTRO
# de un nivel, no entre niveles. Antes se ordenaba solo por unificacion y
# fecha, y por eso una resolucion del TEAR de 2025 adelantaba a doctrina del
# TEAC de 2023: mas nueva, sí; con mas peso, no.
NIVEL_UNIFICACION = 0    # TEAC que unifica criterio: vincula y cierra la discusion
NIVEL_DOCTRINA = 1       # TEAC que sienta doctrina (art. 239.8 LGT)
NIVEL_CENTRAL = 2        # TEAC sin fuerza declarada
NIVEL_REGIONAL = 3       # TEAR y salas desconcentradas: no vinculan


def nivel(criterio) -> int:
    """El peso juridico de una resolucion, segun lo que dice la fuente."""
    if not es_central(criterio.unidad):
        return NIVEL_REGIONAL
    if criterio.unifica_criterio:
        return NIVEL_UNIFICACION
    if " ".join((criterio.calificacion or "").split()).lower().startswith(DOCTRINA):
        return NIVEL_DOCTRINA
    return NIVEL_CENTRAL


def peso(criterio) -> tuple:
    """Clave de orden: primero el peso juridico, dentro de cada nivel la fecha."""
    return (nivel(criterio), -(criterio.anio or 0))


# --------------------------------------------------------------------- cache


class CacheTEAC:
    """Lectura de lo que dejo `teac.py`. Aqui no se descarga."""

    def __init__(self, directorio: Path | None = None):
        self.dir = Path(directorio) if directorio else DIR_CRITERIOS
        self._memo: dict = {}

    def leer(self, ident: str) -> Criterio | None:
        """Por id de criterio o por numero de resolucion, lo que venga."""
        ident = (ident or "").strip()
        if ident in self._memo:
            return self._memo[ident]
        c = None
        f = self.dir / (ident.replace("/", "-").upper() + ".json")
        if f.is_file():
            try:
                c = Criterio.de_registro(json.loads(f.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                c = None
        if c is None:
            # Han dado el numero de RESOLUCION y no el del criterio.
            for otro in self.todas():
                if otro.resolucion == ident or otro.id == ident:
                    c = otro
                    break
        self._memo[ident] = c
        return c

    def tiene(self, ident: str) -> bool:
        return self.leer(ident) is not None

    def todas(self) -> list:
        if not self.dir.is_dir():
            return []
        salida = []
        for f in sorted(self.dir.glob("*.json")):
            try:
                salida.append(Criterio.de_registro(
                    json.loads(f.read_text(encoding="utf-8"))))
            except (json.JSONDecodeError, OSError):
                continue
        return salida

    def por_preceptos(self, preceptos: list, normas=None, tope: int = 3) -> list:
        """LA BUSQUEDA QUE ENCAJA SOLA: por precepto, no por palabras.

        `preceptos` son pares (cuerpo_clave, numero) de lo que sostiene la
        respuesta. Se devuelven los que citan ALGUNO de ellos, ordenados POR
        PESO JURIDICO y, dentro de cada nivel, por fecha. Ver `peso`.
        """
        objetivo = {(c, str(n).lower()) for c, n in (preceptos or []) if n}
        if not objetivo:
            return []
        candidatos = []
        for cr in self.todas():
            suyos = set(cr.preceptos(normas))
            # Solo cuenta si coincide NORMA Y ARTICULO. Un articulo 80 de otra
            # ley no es el nuestro: la leccion de la fase 6, otra vez.
            if suyos & objetivo:
                candidatos.append(cr)
        candidatos.sort(key=peso)
        return candidatos[:tope]


# ------------------------------------------------------- el estado de la fuente


def marcar_fuente(viva: bool, motivo: str = "") -> None:
    from datetime import datetime, timezone
    DIR_CACHE.mkdir(parents=True, exist_ok=True)
    MARCA_FUENTE.write_text(json.dumps({
        "viva": bool(viva), "motivo": motivo,
        "cuando": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def fuente_viva() -> tuple:
    """Si nunca se ha comprobado, se asume CAIDA. Igual que con la DGT."""
    if not MARCA_FUENTE.is_file():
        return False, "la fuente del TEAC no se ha comprobado todavia"
    try:
        d = json.loads(MARCA_FUENTE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False, "no se ha podido leer el estado de la fuente del TEAC"
    return bool(d.get("viva")), d.get("motivo", "")


# --------------------------------------------------------- señales de estado


@dataclass
class Lectura:
    """Lo que la doctrina del TEAC aporta al estado.

    LAS DOS SEÑALES NO SE MEZCLAN, Y AHORA TAMPOCO VAN AL MISMO EJE:

        fuertes  -> `desacuerdo`, y mueve el estado a DISCUTIDO
        debiles  -> `cobertura`, y solo se enseña

    La debil dice «coincide el articulo, pero no se ha comprobado que trate del
    mismo supuesto». Eso es literalmente un hueco, no una contradiccion; que
    moviera el estado era una de las razones por las que DISCUTIDO salia 19 de
    19. Ver la cabecera de `estado.py`.
    """

    criterios: list = field(default_factory=list)
    fuertes: list = field(default_factory=list)
    debiles: list = field(default_factory=list)
    fuente_caida: bool = False
    motivo_fuente: str = ""

    @property
    def desacuerdo(self) -> list:
        """Lo que mueve el estado. Solo la señal fuerte."""
        return list(self.fuertes)

    @property
    def cobertura(self) -> list:
        """Lo que se enseña sin mover el estado. Solo la señal debil."""
        return list(self.debiles)

    @property
    def senales(self) -> list:
        """Las dos juntas, fuertes primero. Para quien quiera enseñarlas todas
        seguidas; el estado NO se calcula con esto."""
        return list(self.fuertes) + list(self.debiles)

    @property
    def hay_discusion(self) -> bool:
        return bool(self.fuertes)


def leer_doctrina(criterios: list, preceptos_verificados: list,
                  consultas_dgt_citadas: list, normas=None) -> Lectura:
    """LAS DOS SEÑALES DE DISCUTIDO, CON PESOS DISTINTOS.

    ── SEÑAL FUERTE (estructural) ────────────────────────────────────────
    El TEAC cita POR NUMERO una consulta de la DGT que nosotros tambien
    estamos citando. No hay que adivinar nada: el propio tribunal ha puesto
    las dos cosas en la misma frase, asi que sabemos que se ha pronunciado
    sobre ESE criterio y no sobre otro parecido. Se da en 4 de cada 9
    criterios reales medidos.

    ── SEÑAL DEBIL (coincidencia de articulos) ───────────────────────────
    Hay criterios del TEAC sobre el mismo articulo. Es una aproximacion: que
    dos textos hablen del articulo 80 no significa que hablen de lo mismo. Se
    dice como lo que es, en condicional.

    Cuando existe la fuerte, MANDA ELLA y la debil no se repite para el mismo
    criterio: decir dos veces lo mismo con distinta seguridad confunde.

    Y una consulta citada por VARIOS criterios sostiene linea doctrinal: pesa
    mas que una mencionada de pasada, y se dice cuantos la citan.
    """
    lectura = Lectura(criterios=list(criterios))
    if not criterios:
        return lectura

    citadas = {c.upper() for c in (consultas_dgt_citadas or [])}
    verificados = set()
    for p in (preceptos_verificados or []):
        if isinstance(p, (tuple, list)) and len(p) == 2:
            verificados.add((p[0], str(p[1]).lower()))

    # Cuantos criterios citan cada consulta: la linea doctrinal.
    veces: dict = {}
    for cr in criterios:
        for num in cr.consultas_dgt:
            veces.setdefault(num, []).append(cr)

    con_fuerte = set()
    for cr in criterios:
        comunes = sorted(set(cr.consultas_dgt) & citadas)
        if not comunes:
            continue
        con_fuerte.add(cr.id)
        # Lo que se puede afirmar sale de la fuente, no de aqui. Antes decia
        # «doctrina» a secas para todo lo que no unificaba, incluidas las
        # resoluciones regionales, que no sientan doctrina ninguna.
        que_pesa = ("de unificacion de criterio, que vincula a toda la "
                    "Administracion" if cr.unifica_criterio
                    else fuerza_de(cr.unidad, cr.calificacion))
        linea = ""
        respaldadas = [n for n in comunes if len(veces.get(n, [])) > 1]
        if respaldadas:
            n = respaldadas[0]
            linea = (f"; {n} la citan {len(veces[n])} criterios distintos, "
                     f"asi que no es una mencion suelta sino linea doctrinal")
        quien = "el TEAC" if es_central(cr.unidad) else f"el {cr.unidad}"
        lectura.fuertes.append(
            f"{quien} se ha pronunciado sobre {', '.join(comunes)}, que es "
            f"criterio que esta respuesta cita: {cr.etiqueta} {cr.resolucion} "
            f"({cr.fecha}), {que_pesa}{linea}. Leelo antes de decidir"
        )

    # --- la debil: hay doctrina sobre el mismo articulo -------------------
    #
    # SE AGRUPA POR ARTICULO, NO POR CRITERIO. Medido sobre el articulo 80:
    # salian SEIS avisos identicos cambiando solo el numero de criterio. Quien
    # lee el primero se salta los otros cinco, asi que seis avisos informan
    # menos que uno. Un aviso por articulo, con la lista de criterios dentro.
    if verificados:
        por_articulo: dict = {}
        for cr in criterios:
            if cr.id in con_fuerte:
                continue     # ya lo ha dicho la fuerte, y mejor
            for cu, n in set(cr.preceptos(normas)):
                if (cu, n) not in verificados:
                    continue
                grupo = por_articulo.setdefault(n, {})
                grupo.setdefault(cr.id, cr)

        for num in sorted(por_articulo, key=_orden_articulo):
            # POR PESO JURIDICO, no por fecha: si solo se lee un nombre de la
            # lista, que sea el que mas pesa. Ver `peso`.
            cs = sorted(por_articulo[num].values(), key=peso)
            nombrados = cs[:TOPE_NOMBRADOS]
            resto = len(cs) - len(nombrados)
            lista = ", ".join(
                f"{c.etiqueta} {c.resolucion} ({c.fecha or 's/f'}"
                + (", UNIFICACION DE CRITERIO" if c.unifica_criterio else "")
                + ")"
                for c in nombrados
            )
            if resto > 0:
                lista += f" y {resto} mas"
            plural = "n" if len(cs) > 1 else ""
            # SE CUENTA POR UNIDAD. Antes decia «N criterio(s) del TEAC»
            # metiendo dentro resoluciones de tribunales regionales, que no son
            # criterios ni son del TEAC.
            lectura.debiles.append(
                f"hay {_cuenta_por_unidad(cs)} sobre el articulo {num}: "
                f"{lista}. Coincide el articulo, PERO no se ha comprobado que "
                f"trate{plural} del mismo supuesto: compruebalo tu"
            )

    # Los que unifican criterio, arriba del bloque de avisos.
    lectura.debiles.sort(key=lambda t: "UNIFICACION DE CRITERIO" not in t)
    return lectura


def _cuenta_por_unidad(criterios: list) -> str:
    """«2 criterios del TEAC y 1 resolucion del TEAR de Baleares».

    Existe porque contarlos todos juntos como «criterios del TEAC» le decia al
    lector que tres tribunales distintos eran uno, y que lo que no obliga a
    nadie tenia la fuerza del articulo 239.8 LGT.
    """
    from collections import Counter

    cuenta: Counter = Counter()
    for c in criterios:
        cuenta[c.unidad or "(unidad no consta)"] += 1

    trozos = []
    for unidad, n in sorted(cuenta.items(), key=lambda x: (not es_central(x[0]),
                                                          x[0])):
        if es_central(unidad):
            trozos.append(f"{n} criterio{'s' if n > 1 else ''} del TEAC")
        else:
            trozos.append(f"{n} resoluci{'ones' if n > 1 else 'on'} del "
                          f"{unidad}")
    if len(trozos) == 1:
        return trozos[0]
    return ", ".join(trozos[:-1]) + " y " + trozos[-1]


def _orden_articulo(num: str) -> tuple:
    """«80» antes que «80 bis» antes que «91». Ordena por numero, no por texto."""
    m = re.match(r"(\d+)(.*)", num or "")
    return (int(m.group(1)), m.group(2)) if m else (10**9, num or "")
