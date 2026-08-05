"""Extraccion de citas de un texto redactado.

Una CITA, para este proyecto, son dos cosas juntas:
  - un fragmento LITERAL entrecomillado, y
  - la referencia del precepto de donde sale (y, si la hay, su enlace).

Sin las dos no hay cita: hay una afirmacion sin respaldo. Esas se detectan
aparte (`referencias_sueltas`) y se cuentan, porque callarselas seria dejar
pasar justo lo que este proyecto quiere impedir.

Se admiten las dos formas de escribir que salen naturales en castellano
juridico, porque la fase 4 va a usar las dos:
    «fragmento literal» (art. 95 LIVA, https://...)
    El articulo 95 LIVA dispone que «fragmento literal»
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# --------------------------------------------------------------- normalizacion

# Comillas tipograficas y espacios raros que cambian segun quien escriba.
# Se unifican SOLO estos: los acentos no se tocan (en un texto juridico
# distinguen palabras) y las mayusculas tampoco.
_COMILLAS = {
    "«": '"', "»": '"',      # « »
    "“": '"', "”": '"',      # “ ”
    "„": '"', "″": '"',
    "‘": "'", "’": "'",      # ‘ ’
    "ʼ": "'", "´": "'",
}
_ESPACIOS = dict.fromkeys(
    [0x00A0, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006, 0x2007, 0x2008,
     0x2009, 0x200A, 0x202F, 0x205F, 0x3000, 0x200B],
    " ",
)
_GUIONES = {"‐": "-", "‑": "-", "‒": "-", "–": "-",
            "—": "-", "−": "-"}

_TABLA = {}
for _origen, _destino in {**_COMILLAS, **_GUIONES}.items():
    _TABLA[ord(_origen)] = _destino
_TABLA.update(_ESPACIOS)

RE_ELIPSIS = re.compile(r"\s*(?:\.\.\.|…)\s*")


def normalizar_literal(texto: str) -> str:
    """Deja el texto listo para comparar palabra por palabra.

    Unifica comillas, guiones y espacios raros, y colapsa los saltos de linea.
    NO toca acentos ni mayusculas: forman parte de la cita.
    """
    if not texto:
        return ""
    # NFC para que "á" compuesta y descompuesta se comparen igual; no quita tildes.
    plano = unicodedata.normalize("NFC", texto).translate(_TABLA)
    return re.sub(r"\s+", " ", plano).strip()


def sin_tildes_min(texto: str) -> str:
    """Solo para diagnosticar diferencias, nunca para dar por buena una cita."""
    d = unicodedata.normalize("NFD", texto)
    return "".join(c for c in d if unicodedata.category(c) != "Mn").lower()


# --------------------------------------------------------------- patrones

# Pares de comillas admitidos. Se buscan sobre el texto ORIGINAL para poder
# senalar la posicion real.
_PARES = [("«", "»"), ("“", "”"), ('"', '"')]

_RE_URL = re.compile(r"https?://[^\s\)\]\},;]+")

# Referencia a un precepto dentro del parentesis o de la frase.
_RE_REF_ARTICULO = re.compile(
    r"\b(?:art[íi]culo|art\.?)\s*(?P<num>\d+)"
    r"(?P<suf>\s+(?:bis|ter|qu[aá]ter|quinquies|sexies|septies|octies|nonies|"
    r"decies|undecies|duodecies|terdecies|quaterdecies|quindecies|"
    r"quinquiesdecies|sexiesdecies|septiesdecies|octiesdecies|noniesdecies|"
    r"vicies|unvicies|duovicies|tervicies|quatervicies|quinvicies|sexvicies|"
    r"septvicies|octovicies|cuarter|quinque|sexvivies))?"
    r"(?P<detalle>[.,]?\s*(?:apartado|n[úu]mero|letra|p[áa]rrafo)[^)\],;]{0,40})?",
    re.IGNORECASE,
)
_RE_REF_DISPOSICION = re.compile(
    r"\bdisposici[óo]n\s+(?P<clase>adicional|transitoria|final|derogatoria)"
    r"\s+(?P<ord>[\wªº]+)",
    re.IGNORECASE,
)

# Como se nombra a la Ley del IVA. Si aparece cualquiera de estas, la cita es
# de esta ley y se puede comprobar.
_RE_NOMBRE_NORMA = re.compile(
    r"\b(?:LIVA|RIVA|L\.I\.V\.A\.|"
    r"(?:Ley|Reglamento|Real\s+Decreto(?:-ley)?|Decreto|C[oó]digo|Tratado|"
    r"Directiva|Orden|Estatuto|Texto\s+Refundido|Convenio)"
    r"(?:\s+(?:Org[aá]nica|General|Concursal|Civil|Tributaria|de\s+Ejecuci[oó]n))*"
    r"(?:\s+\d+/\d+)?"
    r"(?:\s+(?:de|del)\s+(?:la\s+|el\s+)?[A-ZÁÉÍÓÚ][^,.;:()]{0,50})?)",
)

_RE_ES_LIVA_VIEJO = re.compile(
    r"\b(LIVA|L\.I\.V\.A\.|Ley\s+37/1992|BOE-A-1992-28740|"
    r"Ley\s+del\s+(?:IVA|Impuesto\s+sobre\s+el\s+Valor\s+A[ñn]adido)|"
    r"est[ae]\s+Ley|la\s+presente\s+Ley)\b",
    re.IGNORECASE,
)
# Normas que NO estan en el corpus. Si se nombra una de estas, la cita no se
# puede comprobar: no se da por buena, se marca NO VERIFICABLE.
_RE_OTRA_NORMA = re.compile(
    r"\b(RIVA|Reglamento\s+del\s+IVA|Reglamento\s+del\s+Impuesto|Reglamento|"
    r"Real\s+Decreto\s+1624/1992|Real\s+Decreto[\w\-]*\s*\d*/?\d*|"
    r"LGT|Ley\s+58/2003|Ley\s+General\s+Tributaria|Ley\s+\d+/\d+|"
    r"Directiva(?:\s+\d+/\d+(?:/[A-Z]+)?)?|C[óo]digo\s+\w+|Tratado|"
    r"Ley\s+Concursal|TEAC|DGT|Tribunal\s+Supremo)\b",
    re.IGNORECASE,
)

# Una consulta de la DGT. Se escribe siempre con su rotulo delante para que no
# se confunda con nada: "Consulta DGT V1601-22". El numero suelto NO basta.
_RE_REF_DGT = re.compile(
    r"\b(?:Consulta\s+DGT|DGT|consulta\s+vinculante)\s+"
    r"(?P<num>[VC]?\d{3,5}-\d{2})\b",
    re.IGNORECASE,
)

# Un criterio del TEAC. Rotulo delante + numero de resolucion, como la DGT:
# el numero suelto NO basta, porque «00/06614/2024/00/00» a secas podria ser
# cualquier cosa.
# El rotulo se captura APARTE del numero, porque hay que comprobarlo: dice de
# que tribunal es la resolucion, y eso se contrasta contra la copia local. Una
# resolucion del TEAR de Baleares citada como «Criterio TEAC» esta afirmando
# una fuerza vinculante que no tiene.
_RE_REF_TEAC = re.compile(
    r"\b(?P<rotulo>Criterio\s+TEAC"
    r"|Resoluci[oó]n\s+del\s+(?:TEAC|TEAR\s+de[l]?\s+[^,\d]{2,32}"
    r"|Sala\s+Desconc\.?\s+de\s+[^,\d]{2,32})"
    r"|resoluci[oó]n\s+del\s+TEAC"
    r"|TEAC)\s+"
    r"(?P<num>\d{2}/\d{4,5}/\d{4}/\d{2}/\d{1,2}(?:/\d+)?)\b",
    re.IGNORECASE,
)

VENTANA_DESPUES = 220   # cuanto se mira tras la comilla buscando la referencia
VENTANA_ANTES = 200     # cuanto se mira antes (forma "el art. X dispone que ...")


@dataclass
class Referencia:
    """Un precepto nombrado en el texto."""

    bruto: str = ""
    tipo: str = ""            # 'articulo' | 'disposicion_*'
    numero: str = ""          # "95", "163 bis"
    detalle: str = ""         # "apartado uno", si se cito
    norma: str = ""           # 'cargada' | 'externa' | 'asumida' | 'sin_referencia'
    norma_bruta: str = ""     # como se nombro la norma, tal cual
    # Por que el registro de normas no la resolvio. Se guarda porque "externa"
    # tiene DOS causas muy distintas -la norma no esta cargada, o el nombre es
    # ambiguo- y un motivo que no las distinga hace creer que falta del corpus
    # algo que si esta. No decide nada: solo explica.
    motivo_norma: str = ""
    cuerpo: str = ""          # clave del cuerpo, si se pudo determinar
    posicion: int = -1


@dataclass
class Cita:
    """Fragmento literal + referencia. La unidad que se verifica."""

    n: int
    literal: str                 # tal cual se escribio
    literal_norm: str            # normalizado para comparar
    referencia: Referencia
    enlace: str = ""
    trozos: list = field(default_factory=list)   # si venia con puntos suspensivos
    posicion: int = -1
    contexto: str = ""


def _leer_referencia(
    fragmento: str, desplazamiento: int, ultima: bool = False, registro=None
) -> Referencia | None:
    """Extrae una referencia a un precepto de `fragmento`.

    Con `ultima=True` se queda con la ULTIMA, no con la primera. Hace falta
    cuando se mira por delante de la comilla ("... el articulo 90 LIVA fija que
    «...»"): ahi la buena es la mas cercana a la comilla, y si el parrafo
    anterior nombraba otro articulo, la primera seria la equivocada.
    """
    def elegir(patron):
        encontrados = list(patron.finditer(fragmento))
        if not encontrados:
            return None
        return encontrados[-1] if ultima else encontrados[0]

    # -- criterio del TEAC: antes que nada, igual que la DGT --------------
    m_teac = elegir(_RE_REF_TEAC)
    if m_teac:
        return Referencia(
            bruto=m_teac.group(0).strip(),
            tipo="criterio_teac",
            numero=m_teac.group("num"),
            norma="teac",
            norma_bruta=m_teac.group(0).strip(),
            posicion=desplazamiento + m_teac.start(),
        )

    # -- consulta de la DGT: se mira ANTES que nada -----------------------
    # Va primero a proposito. "Consulta DGT V1601-22" no contiene ningun
    # "articulo", asi que no chocaria con los otros patrones, pero el campo
    # normativa que la acompaña SI los nombra ("Ley 37/1992 art. 80"), y sin
    # esta rama una cita de criterio se leeria como una cita de la ley. Eso es
    # exactamente lo que la fase 9B no puede permitir.
    m_dgt = elegir(_RE_REF_DGT)
    if m_dgt:
        return Referencia(
            bruto=m_dgt.group(0).strip(),
            tipo="consulta_dgt",
            numero=m_dgt.group("num").upper(),
            norma="dgt",
            norma_bruta=m_dgt.group(0).strip(),
            posicion=desplazamiento + m_dgt.start(),
        )

    m_art = elegir(_RE_REF_ARTICULO)
    m_disp = elegir(_RE_REF_DISPOSICION)

    if m_art and (
        not m_disp
        or (m_art.start() >= m_disp.start() if ultima else m_art.start() <= m_disp.start())
    ):
        numero = m_art.group("num")
        suf = (m_art.group("suf") or "").strip()
        ref = Referencia(
            bruto=m_art.group(0).strip(),
            tipo="articulo",
            numero=f"{numero} {suf}".strip() if suf else numero,
            detalle=(m_art.group("detalle") or "").strip(" .,"),
            posicion=desplazamiento + m_art.start(),
        )
    elif m_disp:
        clase = sin_tildes_min(m_disp.group("clase"))
        ref = Referencia(
            bruto=m_disp.group(0).strip(),
            tipo=f"disposicion_{clase}",
            numero=m_disp.group("ord"),
            posicion=desplazamiento + m_disp.start(),
        )
    else:
        return None

    # Que norma. Ya no hay una lista escrita a mano: se le pregunta al
    # registro de normas cargadas, que se construye del propio corpus.
    m_nombre = _RE_NOMBRE_NORMA.search(fragmento)
    if m_nombre and registro is not None:
        bruto = re.sub(r"\s+", " ", m_nombre.group(0)).strip(" .,;:")
        clave, porque = registro.resolver(bruto, cola=fragmento[m_nombre.end():])
        if clave:
            ref.norma, ref.norma_bruta, ref.cuerpo = "cargada", bruto, clave
        else:
            ref.norma, ref.norma_bruta = "externa", bruto
            ref.motivo_norma = porque or ""
    elif m_nombre:
        ref.norma, ref.norma_bruta = "externa", m_nombre.group(0)
    else:
        # Sin norma expresa. Con varias normas cargadas esto es AMBIGUO, y
        # quien decide que hacer es el verificador.
        ref.norma, ref.norma_bruta = "asumida", ""
    return ref


_RE_PARENTESIS_PEGADO = re.compile(
    r"^[\s,;:.\-—]{0,6}[\(\[\{](?P<dentro>[^)\]\}]{1,300})[\)\]\}]")
_ABRECOMILLAS = "«“\""


def _parentesis_pegado(despues: str) -> str:
    """El parentesis que va inmediatamente tras la comilla de cierre, si lo hay."""
    m = _RE_PARENTESIS_PEGADO.match(despues)
    return m.group("dentro") if m else ""


def _hasta_fin_de_frase(despues: str) -> str:
    """Recorta en el final de la frase o en la siguiente comilla de apertura.

    Sin esto, la ventana de 220 caracteres se mete en la frase siguiente y
    acaba leyendo la referencia de OTRA cita.
    """
    corte = len(despues)
    profundidad = 0
    for i, ch in enumerate(despues):
        # Las LLAVES cuentan como las otras. La cita del TEAC va entre { }, y
        # sin contarlas la ventana se cortaba en el primer punto de la URL
        # -«https://serviciostelematicosext.»- y el enlace llegaba partido.
        if ch in "([{":
            profundidad += 1
        elif ch in ")]}":
            profundidad = max(0, profundidad - 1)
        elif ch in _ABRECOMILLAS and i > 0:
            corte = i
            break
        elif ch in ".;\n" and profundidad == 0:
            corte = i + 1
            break
    return despues[:corte]


def _recortar_antes(antes: str) -> str:
    """Deja solo lo posterior a la cita anterior.

    Si el parrafo de antes ya llevaba su propia cita, su referencia no puede
    contaminar a esta.
    """
    ultimo = max(antes.rfind("»"), antes.rfind("”"), antes.rfind('"'))
    return antes[ultimo + 1:] if ultimo >= 0 else antes


def _buscar_pares(texto: str):
    """Devuelve (inicio, fin, contenido) de cada fragmento entrecomillado."""
    encontrados = []
    for abre, cierra in _PARES:
        i = 0
        while True:
            a = texto.find(abre, i)
            if a < 0:
                break
            b = texto.find(cierra, a + 1)
            if b < 0:
                break
            contenido = texto[a + 1: b]
            if len(contenido.strip()) >= 3:
                encontrados.append((a, b + 1, contenido))
            i = b + 1
    encontrados.sort()
    # Se descartan los solapados (comillas dentro de comillas).
    limpios = []
    ultimo_fin = -1
    for a, b, c in encontrados:
        if a >= ultimo_fin:
            limpios.append((a, b, c))
            ultimo_fin = b
    return limpios


def extraer(texto: str, registro=None) -> tuple[list[Cita], list[Referencia]]:
    """Texto -> (citas, referencias sueltas sin fragmento literal)."""
    citas: list[Cita] = []
    consumidas: list[tuple[int, int]] = []

    for n, (ini, fin, contenido) in enumerate(_buscar_pares(texto), 1):
        despues = texto[fin: fin + VENTANA_DESPUES]
        antes = _recortar_antes(texto[max(0, ini - VENTANA_ANTES): ini])
        parentesis = _parentesis_pegado(despues)
        suelto = _hasta_fin_de_frase(despues)

        # Orden de preferencia, y el orden importa:
        #   1) el parentesis pegado a la comilla -> «...» (art. 95 LIVA)
        #   2) lo que hay JUSTO ANTES            -> el art. 95 dispone que «...»
        #   3) lo que sigue, hasta el punto
        # Sin esta prioridad, una cita cerrada con solo el enlace se llevaba
        # por delante el numero de articulo de la frase SIGUIENTE, y la cita
        # quedaba atribuida a otro precepto. Eso es justo lo que un
        # verificador no se puede permitir.
        ref = _leer_referencia(parentesis, fin, registro=registro) if parentesis else None
        origen_fin = fin + len(parentesis) + 2 if parentesis else fin
        if ref is None:
            ref = _leer_referencia(antes, max(0, ini - len(antes)), ultima=True,
                                   registro=registro)
            origen_fin = fin
        if ref is None:
            ref = _leer_referencia(suelto, fin, registro=registro)
            origen_fin = fin + len(suelto)

        enlace = ""
        m_url = _RE_URL.search(parentesis or suelto) or _RE_URL.search(antes)
        if m_url:
            enlace = m_url.group(0).rstrip(".,;)")

        if ref is None:
            # Fragmento entrecomillado sin ninguna referencia: no es una cita
            # verificable, y hay que decirlo.
            ref = Referencia(bruto="", tipo="", numero="", norma="sin_referencia")

        literal_norm = normalizar_literal(contenido)
        trozos = [t for t in RE_ELIPSIS.split(literal_norm) if t.strip()]
        citas.append(
            Cita(
                n=n,
                literal=contenido,
                literal_norm=literal_norm,
                referencia=ref,
                enlace=enlace,
                trozos=trozos if len(trozos) > 1 else [],
                posicion=ini,
                contexto=normalizar_literal(texto[max(0, ini - 60): ini])[-60:],
            )
        )
        consumidas.append((max(0, ini - VENTANA_ANTES), min(len(texto), origen_fin)))

    # Referencias que aparecen en el texto sin ningun fragmento literal cerca.
    sueltas: list[Referencia] = []
    for m in _RE_REF_ARTICULO.finditer(texto):
        if any(a <= m.start() < b for a, b in consumidas):
            continue
        r = _leer_referencia(texto[m.start(): m.start() + 160], m.start(),
                             registro=registro)
        if r:
            sueltas.append(r)
    return citas, sueltas
