"""IDENTIDAD DE UN PRECEPTO: (norma, cuerpo, articulo).

Este modulo es el centro de la fase 6. Antes, un precepto se identificaba por
su numero de articulo, y eso basto mientras hubo una sola ley. Con dos normas
deja de bastar, y de tres maneras a la vez:

  - dentro de UNA norma puede haber dos articulados. El Real Decreto 1624/1992
    tiene los suyos (arts. 1-6: aprobar el Reglamento, modificar otros reales
    decretos) y ademas lleva como anexo el REGLAMENTO del IVA, que empieza otra
    vez por el articulo 1. Son dos "cuerpos".
  - entre normas, "articulo 8" es ambiguo: hay uno en la Ley y otro en el
    Reglamento, y no tienen nada que ver.
  - una norma cita a la otra con nombres que hay que reconocer ("de la Ley del
    Impuesto") sin confundirlos con los suyos propios ("de este Reglamento").

EL CUERPO SE DETECTA DE LA ESTRUCTURA, no de una lista de excepciones: se abre
un cuerpo nuevo cuando la numeracion de articulos REINICIA. Comprobado: la Ley
37/1992 tiene 0 reinicios en 215 articulos; el Real Decreto 1624/1992 tiene 1,
justo donde empieza el anexo. Cualquier real decreto aprobatorio o texto
refundido se trocea solo con la misma regla.

LOS NOMBRES Y ALIAS TAMBIEN SALEN DE LOS DATOS: del titulo oficial de la norma
("...por el que se aprueba el Reglamento del Impuesto sobre el Valor Anadido")
y de su rango y numero. No hay ningun diccionario escrito a mano.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import bloques as B

# Rangos que encabezan el nombre de un cuerpo normativo.
_TIPOS = (
    "Reglamento", "Ley Organica", "Ley", "Real Decreto-ley",
    "Real Decreto Legislativo", "Real Decreto", "Texto Refundido",
    "Decreto-ley", "Decreto", "Orden", "Estatuto", "Codigo",
)

_RE_APRUEBA = re.compile(
    r"por el que se aprueban?\s+(?:el|la)\s+(?P<nombre>.+?)"
    r"(?:\s+y se modifica|\s*[,\.]|$)",
    re.IGNORECASE,
)
_RE_NUMERO = re.compile(r"\b(\d+/\d{4})\b")
# "Ley 37/1992, de 28 de diciembre, del Impuesto sobre el Valor Anadido."
_RE_MATERIA = re.compile(
    r"\b(?:de|del|de la|sobre)\s+(?P<materia>[A-ZÁÉÍÓÚ][^,.;]{4,90})\s*$"
)

PALABRAS_VACIAS_MATERIA = {"de", "del", "la", "el", "los", "las", "sobre", "y", "a"}


def _acronimo(materia: str) -> str:
    """'Impuesto sobre el Valor Anadido' -> 'IVA'."""
    iniciales = [
        p[0].upper()
        for p in re.findall(r"[\wÁÉÍÓÚáéíóúñÑ]+", materia)
        if p.lower() not in PALABRAS_VACIAS_MATERIA
    ]
    return "".join(iniciales)


# EL ROTULO DE UN NIVEL ESTRUCTURAL, SIN SU NUMERACION NI SU RANGO.
#
#   «TITULO II. Impuesto sobre el patrimonio (articulo 621-1 - articulo 622-2)»
#        ->  «Impuesto sobre el patrimonio»
#
# Hace falta porque `es_materia_de_impuesto` mira como EMPIEZA la materia -una
# ley de un tributo se titula «Impuesto sobre ...»- y con el «TITULO II.»
# delante no empieza por ahi nunca.
_RE_NIVEL = re.compile(
    r"^(?:libro|titulo|capitulo|seccion|subseccion|parte)\b[^.]*\.\s*",
    re.IGNORECASE)
_RE_RANGO_ROTULO = re.compile(r"\s*\(art[ií]culos?\s[^)]*\)\s*$", re.IGNORECASE)


def _materia_de_rotulo(rotulo: str) -> str:
    t = B.sin_tildes(rotulo or "").strip()
    t = _RE_NIVEL.sub("", t)
    return _RE_RANGO_ROTULO.sub("", t).strip()


@dataclass
class Cuerpo:
    """Un articulado con numeracion propia."""

    norma_id: str
    indice: int                       # 0 = el articulado de la propia norma
    nombre: str = ""                  # "Reglamento del Impuesto sobre el Valor Anadido"
    tipo: str = ""                    # "Reglamento" / "Ley" / "Real Decreto"
    numero: str = ""                  # "37/1992"
    materia: str = ""                 # "Impuesto sobre el Valor Anadido"
    norma_titulo: str = ""
    alias: set = field(default_factory=set)   # todo en minusculas y sin tildes

    @property
    def clave(self) -> str:
        return f"{self.norma_id}#{self.indice}"

    @property
    def etiqueta(self) -> str:
        """Como se nombra en una cita. Es lo que lee el fiscalista."""
        return self.nombre or f"{self.norma_id} (cuerpo {self.indice})"

    def referencia_de(self, referencia_local: str) -> str:
        """'Articulo 8' -> 'Articulo 8 del Reglamento del IVA'."""
        return f"{referencia_local} de {'la ' if self.tipo in ('Ley', 'Orden') else 'el '}{self.etiqueta}".replace(
            "de el ", "del "
        )


def _analizar_nombre(nombre: str) -> tuple[str, str, str]:
    """Nombre de un cuerpo -> (tipo, numero, materia)."""
    plano = re.sub(r"\s+", " ", nombre).strip()
    # Los titulos oficiales encadenan clausulas ("..., por el que se aprueba
    # ..., y se modifica ..."). La materia esta en la PRIMERA; sin cortar, la
    # expresion regular se lleva la cola de la ultima.
    plano = re.split(r",?\s+(?:por el que|por la que|y se modifica|y de)\b",
                     plano, 1)[0]
    tipo = ""
    for t in _TIPOS:
        if B.sin_tildes(plano).startswith(B.sin_tildes(t).lower()):
            tipo = t
            break
    m = _RE_NUMERO.search(plano)
    numero = m.group(1) if m else ""
    materia = ""
    mm = _RE_MATERIA.search(plano.rstrip("."))
    if mm:
        materia = mm.group("materia").strip()
    elif tipo:
        resto = plano[len(tipo):].lstrip(" ,")
        # SE QUITA EL PREAMBULO DE NUMERO Y FECHA. «Ley 35/2006, de 28 de
        # noviembre, del Impuesto sobre la Renta...»: sin quitarlo, la materia
        # salia como «35/2006, de 28 de noviembre, del Impuesto sobre...» y su
        # acronimo era «322NIRPFMPLISRNRP». Con la Ley del IVA no se notaba
        # porque su titulo acaba en la materia y la cogia la otra rama.
        resto = re.sub(
            r"^\d+/\d{4}\s*,?\s*(?:de\s+\d{1,2}\s+de\s+[a-záéíóú]+\s*,?\s*)?",
            "", resto, flags=re.I)
        resto = re.sub(r"^(?:de[l]?\s+|la\s+|el\s+)", "", resto, flags=re.I)
        materia = resto.strip(" .,")
    return tipo, numero, materia


def es_materia_de_impuesto(materia: str) -> bool:
    """¿Esta materia nombra un impuesto?

    Se decide por como se titulan las normas, no por una lista de normas: una
    ley de un tributo se llama «Impuesto sobre ...» -sobre el Valor Anadido,
    sobre la Renta de las Personas Fisicas, sobre Sociedades-. La General
    Tributaria no: se llama «General Tributaria», porque no es de ningun
    impuesto en particular, y ese es exactamente el papel que se quiere
    distinguir.

    Se comprueba el PRINCIPIO de la materia y no si la palabra aparece en algun
    sitio: «Reglamento de los Impuestos Especiales» empieza por impuesto, pero
    «Ley de medidas para la prevencion del fraude en los impuestos» no es la
    ley de ningun impuesto.
    """
    return B.sin_tildes(materia or "").strip().lower().startswith("impuesto")


def _generar_alias(tipo: str, numero: str, materia: str) -> set:
    """Formas con las que el BOE puede nombrar a este cuerpo.

    Se generan del propio nombre, no de una lista. De "Ley 37/1992 ... del
    Impuesto sobre el Valor Anadido" salen "ley 37/1992", "ley del impuesto
    sobre el valor anadido", "ley del impuesto", "ley del iva" y "liva".
    """
    alias: set[str] = set()
    if not tipo:
        return alias
    t = B.sin_tildes(tipo)
    alias.add(t)
    if numero:
        alias.add(f"{t} {numero}")
    if materia:
        m = B.sin_tildes(materia)
        alias.add(f"{t} de {m}")
        alias.add(f"{t} del {m}")
        # Prefijos cada vez mas cortos: "impuesto sobre el valor anadido",
        # "impuesto sobre el valor", ..., "impuesto". Asi encaja el
        # "de la Ley del Impuesto" que usa el Reglamento 113 veces.
        palabras = m.split()
        for n in range(1, len(palabras)):
            corto = " ".join(palabras[:n])
            if corto and corto not in PALABRAS_VACIAS_MATERIA:
                alias.add(f"{t} de {corto}")
                alias.add(f"{t} del {corto}")
        sigla = _acronimo(materia)
        if len(sigla) >= 2:
            s = sigla.lower()
            alias.add(f"{t} de {s}")
            alias.add(f"{t} del {s}")
            alias.add(f"{t[0]}{s}")           # "liva", "riva"
    return alias


def cuerpos_de_norma(norma_titulo: str, norma_id: str, n_cuerpos: int) -> list:
    """Construye los cuerpos de una norma a partir de su titulo oficial."""
    tipo0, numero0, materia0 = _analizar_nombre(norma_titulo)
    nombre0 = f"{tipo0} {numero0}".strip() if numero0 else (tipo0 or norma_id)
    if materia0 and tipo0:
        nombre0 = f"{tipo0} {numero0}".strip()

    cuerpos = [
        Cuerpo(norma_id, 0, nombre0, tipo0, numero0, materia0, norma_titulo,
               _generar_alias(tipo0, numero0, materia0))
    ]

    # Los cuerpos siguientes son lo que la norma APRUEBA, y su nombre esta en
    # el propio titulo oficial: "por el que se aprueba el Reglamento del ...".
    aprobado = _RE_APRUEBA.search(norma_titulo)
    for i in range(1, n_cuerpos):
        if aprobado and i == 1:
            nombre = re.sub(r"\s+", " ", aprobado.group("nombre")).strip()
        else:
            nombre = f"Anexo {i} de {nombre0}"
        t, n, mat = _analizar_nombre(nombre)
        cuerpos.append(
            Cuerpo(norma_id, i, nombre, t, n or numero0, mat, norma_titulo,
                   _generar_alias(t, n, mat))
        )
    return cuerpos


# --------------------------------------------------------------- registro


# Lo que, tras un alias, delata que se habla de OTRA norma: un numero de
# norma, un parentesis de rango comunitario, un "n.º", o un nombre propio
# ("Concursal", "Civil", "General Tributaria").
_RE_DISCRIMINANTE = re.compile(
    r"^\s*(?:\(|n[.º°]|\d+\s*/\s*\d{4}|[A-ZÁÉÍÓÚ][a-záéíóúñ]{2,})"
)

_RE_DEMOSTRATIVO = re.compile(
    r"\b(est[ae]|el\s+presente|la\s+presente|presente)\s+$", re.IGNORECASE
)


class Registro:
    """Todos los cuerpos cargados. Resuelve un nombre a un cuerpo concreto."""

    def __init__(self, docs):
        self.cuerpos: dict[str, Cuerpo] = {}
        # Las comunidades se leen de los preceptos, no de los cuerpos: es un
        # dato del registro, como el impuesto.
        self._comunidades = {c for c in
                             ((d.registro.get("comunidad") or "").strip()
                              for d in docs) if c}
        vistos: dict[str, int] = {}
        for d in docs:
            r = d.registro
            vistos[r["norma_id"]] = max(
                vistos.get(r["norma_id"], 0), r.get("cuerpo_indice", 0)
            )
        titulos = {}
        for d in docs:
            titulos.setdefault(d.registro["norma_id"], d.registro["norma_titulo"])
        for norma_id, maximo in vistos.items():
            for c in cuerpos_de_norma(titulos[norma_id], norma_id, maximo + 1):
                self.cuerpos[c.clave] = c

        # Se deja calculada la lista de materias de impuesto para no rehacerla
        # en cada llamada; `materia_dominante` desaparece porque con dos
        # impuestos dentro la pregunta «cual domina» ya no significa nada.
        self.materias_propias = self.materias_de_impuesto()

    # ------------------------------------------------------------- el papel
    #
    # QUE PAPEL JUEGA CADA NORMA EN ESTE CORPUS. Con una sola ley no hacia
    # falta preguntarselo. Con la General Tributaria dentro, si: la LGT habla
    # de plazos, notificaciones y sanciones EN ABSTRACTO, y su vocabulario
    # encaja con casi cualquier consulta. Sin distinguir papeles, el articulo
    # 55 LGT ("tipo de gravamen") compite de tu a tu con el articulo 91 LIVA
    # en una consulta sobre tipos de IVA, y gana sitio que no le toca.
    #
    # El papel NO se declara en una lista escrita a mano, que es justo lo que
    # este modulo evita en todo lo demas. Se deduce de la materia:
    #
    #   NORMA DEL IMPUESTO   alguno de sus cuerpos trata la materia que este
    #                        corpus tiene como propia (la que comparten mas
    #                        cuerpos: aqui, el Impuesto sobre el Valor Anadido)
    #   NORMA GENERAL        ninguno la trata: esta en el corpus para dar
    #                        apoyo, no para contestar sobre el impuesto
    #
    # El Real Decreto 1624/1992 sale bien parado sin excepciones: su cuerpo 0
    # no declara materia, pero su cuerpo 1 (el Reglamento) si, y el papel se
    # mira POR NORMA, no por cuerpo. Ingerir manana el Reglamento General de
    # Recaudacion lo clasificaria solo, sin tocar esto.

    IMPUESTO = "impuesto"
    GENERAL = "general"

    def materias_de_impuesto(self) -> set:
        """Las materias del corpus que nombran un impuesto. Puede haber varias.

        ANTES ERA UNA SOLA: «la materia dominante», la que mas cuerpos
        compartian. Con una ley de impuesto y unas cuantas generales bastaba.
        Con DOS impuestos dentro deja de tener sentido: el IVA y el IRPF son
        los dos normas de impuesto y solo uno puede ser dominante, asi que el
        otro quedaba clasificado como norma general y competia penalizado.
        """
        return {(c.materia or "").strip().lower()
                for c in self.cuerpos.values()
                if es_materia_de_impuesto(c.materia)}

    def impuestos(self) -> set:
        """Los impuestos que este corpus puede contestar, por sus siglas.

        Salen del titulo de las normas cargadas: «Impuesto sobre el Valor
        Anadido» -> IVA, «Impuesto sobre la Renta de las Personas Fisicas» ->
        IRPF. No hay lista escrita a mano en ninguna parte; si manana se
        ingiere Sociedades, aparece IS sin que nadie lo escriba.
        """
        return {_acronimo(c.materia) for c in self.cuerpos.values()
                if es_materia_de_impuesto(c.materia)}

    def nombres_de_impuesto(self) -> list:
        """Los mismos, con su nombre entero, para poder decirlos en cristiano."""
        vistos, salida = set(), []
        for c in self.cuerpos.values():
            m = (c.materia or "").strip()
            if es_materia_de_impuesto(m) and m.lower() not in vistos:
                vistos.add(m.lower())
                salida.append(m)
        return sorted(salida)

    def papel_de_norma(self, norma_id: str) -> str:
        """IMPUESTO si alguno de sus cuerpos trata la materia de ALGUN impuesto.

        «Alguno», no «el dominante»: ver `materias_de_impuesto`. Y basta con
        que lo sea UNO de sus cuerpos, que es lo que hace que un real decreto
        aprobatorio -cuyo cuerpo 0 no nombra materia ninguna- herede el papel
        del reglamento que aprueba.
        """
        propias = self.materias_de_impuesto()
        if not propias:
            return self.IMPUESTO      # corpus sin impuestos nombrados: todo es propio
        for c in self.cuerpos.values():
            if c.norma_id != norma_id:
                continue
            if (c.materia or "").strip().lower() in propias:
                return self.IMPUESTO
        return self.GENERAL

    def impuesto_de_cuerpo(self, clave_cuerpo: str) -> str:
        """De que impuesto es este cuerpo. Cadena vacia = de ninguno.

        Primero por su propia materia; si no la nombra -el cuerpo 0 de un real
        decreto aprobatorio no la nombra nunca-, por la de sus hermanos de la
        misma norma. Es la regla del papel aplicada al cuerpo: los ocho
        articulos que aprueban el Reglamento del IVA son del IVA aunque su
        rotulo no lo diga.
        """
        c = self.cuerpos.get(clave_cuerpo)
        if c is None:
            return ""
        if es_materia_de_impuesto(c.materia):
            return _acronimo(c.materia)
        for otro in self.cuerpos.values():
            if otro.norma_id == c.norma_id and es_materia_de_impuesto(otro.materia):
                return _acronimo(otro.materia)
        return ""

    def impuesto_de_precepto(self, registro) -> str:
        """De que impuesto es ESTE precepto. Cadena vacia = de ninguno.

        LA UNIDAD DE CLASIFICACION ES EL PRECEPTO, NO LA NORMA. Hasta ahora una
        norma era «de un impuesto» o «general» y bastaba, porque cada norma
        estatal trata de uno. Un CODIGO POR LIBROS no: en el libro sexto del
        Codi tributari de Catalunya cada impuesto es un TITULO, y la misma
        norma tiene dentro Renta, Patrimonio, Sucesiones e ITP. Clasificada
        como «general» competiria en las busquedas de los cuatro impuestos que
        tenemos, y sus articulos de Sucesiones saldrian en preguntas de IVA.

        POR QUE EL PRECEPTO Y NO EL TITULO, que era la otra opcion:

          · el precepto es lo que se recupera, lo que se filtra y lo que se
            cita. Cualquier unidad mas gruesa necesita despues un mapa a
            preceptos, asi que se acaba aqui igual, con un rodeo;
          · la EVIDENCIA si vive en el titulo -«TITULO II. Impuesto sobre el
            patrimonio»- y de ahi se lee; lo que se guarda es la RESPUESTA, y
            esa se pega al precepto;
          · y meter un nivel «titulo» en el modelo obligaria a tocar los
            registros de las doce normas ya ingeridas. Esto no toca ninguno:
            `contexto` ya esta en cada registro desde la fase 1.

        Se lee de los datos, sin lista en ninguna parte. Para Sucesiones e ITP
        el dia que entren no hay que escribir nada: sus titulos ya lo dicen.
        """
        ctx = registro.get("contexto") or []
        if isinstance(ctx, str):
            ctx = [ctx]
        for rotulo in ctx:
            materia = _materia_de_rotulo(str(rotulo))
            if es_materia_de_impuesto(materia):
                return _acronimo(materia)
        return self.impuesto_de_cuerpo(registro.get("cuerpo_clave") or "")

    def comunidad_de_precepto(self, registro) -> str:
        """De que comunidad es este precepto. Cadena vacia = estatal.

        LA AUSENCIA DEL CAMPO SIGNIFICA ESTATAL, y es a proposito: las doce
        normas estatales se ingirieron antes de que existiera y no llevan
        `comunidad`. Volver a ingerirlas solo para escribir un campo vacio
        cambiaria sus doce sellos -la herramienta que avisa de que el corpus se
        ha movido- a cambio de nada. Lo que hay es lo correcto: sin comunidad,
        estatal, que ademas es el valor seguro.
        """
        return (registro.get("comunidad") or "").strip()

    def comunidades(self) -> set:
        """Las comunidades de las que hay normativa cargada."""
        return set(self._comunidades)

    def impuestos_de_norma(self, norma_id: str) -> set:
        """TODOS los impuestos que trata una norma. Puede ser mas de uno.

        Es la regla del papel, pero sin obligar a elegir: una norma de varios
        impuestos ya no tiene que hacerse pasar por general.
        """
        fuera = set()
        for c in self.cuerpos.values():
            if c.norma_id == norma_id and es_materia_de_impuesto(c.materia):
                fuera.add(_acronimo(c.materia))
        return fuera

    def admite(self, registro, impuestos) -> bool:
        """¿Puede este precepto competir en una consulta de esos impuestos?

        `impuestos` es un conjunto de codigos; la cadena vacia dentro significa
        «y tambien las normas generales». `None` = no se filtra.
        """
        if impuestos is None:
            return True
        return self.impuesto_de_precepto(registro) in impuestos

    def admitidos_para(self, impuesto: str):
        """Que impuestos pueden competir en una consulta de ESE impuesto.

        Devuelve codigos, no cuerpos: la cadena vacia significa «y las normas
        generales», que aplican a todos. Antes esto devolvia un conjunto de
        CUERPOS, y valia mientras cada norma tratara de un solo impuesto; con
        un codigo por libros dentro -Renta, Patrimonio, Sucesiones e ITP en el
        mismo cuerpo- el cuerpo dejo de ser la unidad. Ver
        `impuesto_de_precepto`.

        DEVUELVE `None` SI EL IMPUESTO NO SE HA PODIDO DETERMINAR, y esa es la
        regla que no se negocia: filtrar con un impuesto equivocado es peor que
        no filtrar. Sin filtro se compite de mas y el corte por pertinencia
        hace su trabajo; con el filtro equivocado se pierde la ley que tocaba y
        NO SE NOTA, porque la respuesta sale igual de segura citando otra cosa.
        """
        if not impuesto or impuesto not in self.impuestos():
            return None
        return {impuesto, ""}

    def papel(self, clave_cuerpo: str) -> str:
        c = self.cuerpos.get(clave_cuerpo)
        return self.papel_de_norma(c.norma_id) if c else self.IMPUESTO

    def __len__(self) -> int:
        return len(self.cuerpos)

    def por_clave(self, clave: str):
        return self.cuerpos.get(clave)

    def encaja_con_varios(self, designacion: str) -> bool:
        """¿Esta designacion nombra a MAS DE UNA de las normas cargadas?

        Es la diferencia entre «no la tengo» y «no se cual de las que tengo».
        `resolver` ya lo sabe -se niega por eso- pero lo dice dentro de un
        motivo en prosa; aqui se pregunta en limpio para poder decirselo bien
        a quien lee la respuesta.
        """
        _clave, motivo = self.resolver(designacion)
        return "encaja con" in (motivo or "")

    def resolver(self, designacion: str, cuerpo_actual: str = "",
                 cola: str = "") -> tuple:
        """Nombre de norma -> (clave_de_cuerpo, motivo).

        Devuelve (None, motivo) si no se puede decidir. ANTE LA DUDA, NADA:
        una remision sin resolver es un aviso visible; una remision resuelta a
        la norma equivocada es un articulo real, con texto real, que no es el
        que toca, y el verificador la daria por buena.
        """
        if not designacion:
            return None, "sin designacion"
        d = B.sin_tildes(re.sub(r"\s+", " ", designacion)).strip(" .,;:")
        d = re.sub(r"^(?:de[l]?\s+|en\s+)?(?:la|el|los|las)\s+", "", d).strip()
        d = re.sub(r"^(?:est[ae]|presente)\s+", "", d).strip()
        if not d:
            return None, "designacion vacia"

        # La designacion viene recortada de un texto corrido y suele arrastrar
        # cola ("Ley del Impuesto se considerara..."). Se busca el alias MAS
        # LARGO que sea prefijo suyo.
        palabras = d.split()
        candidatos: list = []
        consumidas = 0
        for n in range(len(palabras), 0, -1):
            prefijo = " ".join(palabras[:n])
            candidatos = [c for c in self.cuerpos.values() if prefijo in c.alias]
            if candidatos:
                consumidas = n
                break

        if candidatos:
            # Y AQUI ESTA LA REGLA DE ORO. Lo que queda sin consumir decide:
            # si empieza por un numero de norma, un parentesis o un nombre
            # propio, la designacion es de OTRA norma y acortar seria
            # inventarse la coincidencia. "Ley 58/2003" no es "la Ley";
            # "Reglamento (UE) 282/2011" no es el Reglamento del IVA.
            resto_original = " ".join(
                re.sub(r"\s+", " ", designacion).strip(" .,;:").split()[consumidas:]
            )
            sobra = (resto_original + " " + (cola or "")).strip(" ,;:.")
            if _RE_DISCRIMINANTE.match(sobra):
                # Se dice QUE alias caso y QUE sobro: sin las dos mitades el
                # mensaje parece repetir el nombre y no se entiende por que se
                # rechaza algo que a simple vista encajaba.
                # Del texto ORIGINAL, no de la version normalizada: el motivo
                # lo lee una persona, y «reglamento del iva» en minusculas
                # parece un error de otra cosa.
                alias = " ".join(
                    re.sub(r"\s+", " ", designacion).strip(" .,;:").split()[:consumidas]
                )
                return None, (
                    f"«{alias}» es alias de una norma cargada, pero la "
                    f"designacion sigue con «{sobra[:34]}»: es OTRA norma, "
                    f"no se resuelve"
                )

        if len(candidatos) == 1:
            return candidatos[0].clave, f"designa a {candidatos[0].etiqueta}"
        if len(candidatos) > 1:
            # Un demostrativo desempata a favor del cuerpo en que estamos.
            propio = [c for c in candidatos if c.clave == cuerpo_actual]
            if propio:
                return propio[0].clave, f"designa al propio {propio[0].etiqueta}"
            return None, (
                f"«{designacion.strip()}» encaja con "
                f"{len(candidatos)} cuerpos ({', '.join(c.etiqueta for c in candidatos)}): "
                f"no se resuelve"
            )
        return None, f"«{designacion.strip()}» no corresponde a ninguna norma cargada"
