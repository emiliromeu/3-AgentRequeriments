"""Verificador de citas. Deterministico: ni IA, ni red, ni azar.

Tres estados y solo tres:

  VERIFICADA      el precepto existe, el fragmento esta LITERALMENTE en el, y
                  ademas en la version que aplicaba al ejercicio del caso.
  NO_VERIFICADA   se ha podido comprobar y NO cuadra. Siempre con el motivo.
  NO_VERIFICABLE  no se puede comprobar porque la norma no esta en el corpus.

NO_VERIFICABLE NO ES VERIFICADA. Es la trampa comoda de todo verificador: dar
por bueno lo que no se ha mirado. Una remision al Reglamento del IVA no se
puede comprobar hoy, y por eso arrastra a la respuesta entera.

Y una regla que viene de haberla sufrido dos fases seguidas: el historial de
reformas y el aparato editorial del BOE NO SON NORMA. Si un fragmento casa
contra ese material, la cita es NO_VERIFICADA por mucho que el texto este ahi.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import bloques as B
from . import citas as C
from . import vigencia as V

VERIFICADA = "VERIFICADA"
NO_VERIFICADA = "NO_VERIFICADA"
NO_VERIFICABLE = "NO_VERIFICABLE"

ACEPTADO = "ACEPTADO"
RECHAZADO = "RECHAZADO"

# De donde puede salir un fragmento encontrado en el corpus.
ARTICULADO = "articulado"
NOTA_BOE = "nota_boe"
NOTA_EDITORIAL = "nota_editorial"

ETIQUETA_ORIGEN = {
    ARTICULADO: "articulado",
    NOTA_BOE: "nota al pie del BOE (historial de reformas)",
    NOTA_EDITORIAL: "aparato editorial del BOE",
}


@dataclass
class Hallazgo:
    """Donde aparece un fragmento dentro del corpus."""

    clave: str
    referencia: str
    origen: str
    orden_version: int | None = None
    fecha_version: str = ""


@dataclass
class Dictamen:
    """Resultado de verificar UNA cita."""

    n: int
    estado: str
    motivo: str = ""
    literal: str = ""
    referencia_citada: str = ""
    clave: str = ""
    referencia_corpus: str = ""
    norma: str = ""
    version_usada: dict = field(default_factory=dict)
    enlace_citado: str = ""
    enlace_correcto: str = ""
    hallazgos: list = field(default_factory=list)
    comprobaciones: list = field(default_factory=list)

    def a_json(self) -> dict:
        return {
            "n": self.n,
            "estado": self.estado,
            "motivo": self.motivo,
            "literal": self.literal,
            "referencia_citada": self.referencia_citada,
            "referencia_corpus": self.referencia_corpus,
            "clave": self.clave,
            "norma": self.norma,
            "version_usada": self.version_usada,
            "enlace_citado": self.enlace_citado,
            "enlace_correcto": self.enlace_correcto,
            "comprobaciones": self.comprobaciones,
            "hallazgos": [
                {
                    "referencia": h.referencia,
                    "origen": h.origen,
                    "orden_version": h.orden_version,
                    "fecha_version": h.fecha_version,
                }
                for h in self.hallazgos
            ],
        }


@dataclass
class Informe:
    veredicto: str
    ejercicio: int | None
    dictamenes: list
    sueltas: list = field(default_factory=list)
    motivo_global: str = ""

    @property
    def resumen(self) -> dict:
        return {
            "total": len(self.dictamenes),
            "verificadas": sum(1 for d in self.dictamenes if d.estado == VERIFICADA),
            "no_verificadas": sum(
                1 for d in self.dictamenes if d.estado == NO_VERIFICADA
            ),
            "no_verificables": sum(
                1 for d in self.dictamenes if d.estado == NO_VERIFICABLE
            ),
            "referencias_sin_literal": len(self.sueltas),
        }

    def a_json(self) -> dict:
        return {
            "veredicto": self.veredicto,
            "motivo_global": self.motivo_global,
            "ejercicio": self.ejercicio,
            "resumen": self.resumen,
            "citas": [d.a_json() for d in self.dictamenes],
            "referencias_sin_literal": [
                {"referencia": r.bruto, "norma": r.norma} for r in self.sueltas
            ],
        }


class Verificador:
    """Comprueba citas contra el corpus de la fase 1."""

    def __init__(self, indice):
        self.ix = indice
        # Indice de textos normalizados, uno por version, para buscar literales.
        # Se construye una vez: son ~750 versiones.
        self._articulado: list[tuple[str, int, str, str]] = []
        self._notas: list[tuple[str, str, str]] = []
        for d in indice.docs:
            reg = d.registro
            for v in reg.get("versiones") or []:
                self._articulado.append(
                    (
                        d.clave,
                        v.get("orden", 0),
                        v.get("fecha_vigencia_efectiva") or v.get("fecha_vigencia", ""),
                        C.normalizar_literal(v.get("texto", "")),
                    )
                )
            for nota in reg.get("notas_boe") or []:
                self._notas.append(
                    (d.clave, NOTA_BOE, C.normalizar_literal(nota.get("texto", "")))
                )
            for nota in reg.get("notas_editoriales") or []:
                self._notas.append(
                    (d.clave, NOTA_EDITORIAL, C.normalizar_literal(nota))
                )

    # ------------------------------------------------------------ localizar

    def localizar(self, literal: str) -> list[Hallazgo]:
        """Donde aparece ese fragmento en TODO el corpus, articulado o no.

        Sirve para dar motivos utiles: "no esta en el 163, pero si en el
        163 bis", o "esto sale de una nota al pie, que no es norma".
        """
        if not literal:
            return []
        salida = []
        for clave, orden, fecha, texto in self._articulado:
            if literal in texto:
                salida.append(
                    Hallazgo(
                        clave,
                        self.ix.por_clave[clave].registro["referencia"],
                        ARTICULADO,
                        orden,
                        fecha,
                    )
                )
        for clave, origen, texto in self._notas:
            if literal in texto:
                salida.append(
                    Hallazgo(
                        clave,
                        self.ix.por_clave[clave].registro["referencia"],
                        origen,
                    )
                )
        return salida

    def _buscar_clave(self, ref: C.Referencia) -> tuple:
        """Clave del precepto citado dentro del cuerpo indicado.

        Devuelve (clave, candidatos). `candidatos` lista los cuerpos donde
        existe ese precepto cuando la cita no dice de que norma es: si hay mas
        de uno, la cita es ambigua y NO se valida contra ninguno.

        El sufijo se respeta: el 163 y el 163 bis son preceptos distintos y
        conviven. Se busca la clave exacta, sin caer al numero base.
        """
        if ref.tipo == "articulo":
            local = "articulo " + B.normalizar(ref.numero)
        elif ref.tipo.startswith("disposicion"):
            local = f"{ref.tipo} {B.normalizar(ref.numero)}"
        else:
            return "", []

        encontrados = []
        for clave, doc in self.ix.por_clave.items():
            reg = doc.registro
            if reg.get("clave_local") == local:
                encontrados.append(clave)
            elif (
                ref.tipo.startswith("disposicion")
                and reg["tipo"] == ref.tipo
                and str(reg.get("ordinal") or "") == B.normalizar(ref.numero)
            ):
                encontrados.append(clave)

        if ref.cuerpo:
            enel = [c for c in encontrados
                    if self.ix.por_clave[c].registro.get("cuerpo_clave") == ref.cuerpo]
            return (enel[0] if enel else ""), encontrados
        return ("" if len(encontrados) != 1 else encontrados[0]), encontrados

    # ------------------------------------------------------------ verificar

    # Por debajo de esto un "fragmento literal" no sostiene nada: la palabra
    # esta en el articulo, si, pero no demuestra lo que se afirma. No invalida
    # la cita (existe y es literal), pero se hace constar.
    MINIMO_SUSTANCIA = 25

    def verificar_cita(
        self, cita: C.Cita, ejercicio: int | None, exigir_norma: bool = False
    ) -> Dictamen:
        ref = cita.referencia
        d = Dictamen(
            n=cita.n,
            estado=NO_VERIFICADA,
            literal=cita.literal_norm,
            referencia_citada=ref.bruto,
            norma=ref.norma,
            enlace_citado=cita.enlace,
        )

        # -- 0. sin referencia: no es una cita, es una frase entrecomillada --
        if ref.norma == "sin_referencia" or not ref.tipo:
            d.estado = NO_VERIFICADA
            d.motivo = (
                "fragmento entrecomillado sin referencia a ningun precepto: "
                "no se puede comprobar contra nada"
            )
            return d

        # -- 1. norma fuera del corpus -> NO VERIFICABLE, nunca verificada --
        if ref.norma == "externa":
            d.estado = NO_VERIFICABLE
            d.motivo = (
                f"la cita remite a {ref.norma_bruta}, que no esta entre las normas "
                f"cargadas. No se puede comprobar, asi que no se da por buena"
            )
            d.comprobaciones.append("norma citada: fuera del corpus")
            return d

        # -- 1 bis. norma no indicada --
        # El corpus solo tiene la Ley 37/1992, asi que "art. 95" a secas se
        # entiende de ella. Es razonable, pero es una SUPOSICION: si alguien
        # queria decir "art. 5 del Reglamento" y no lo escribio, se validaria
        # contra el articulo equivocado. Queda siempre anotado, y con
        # --exigir-norma se convierte en no verificable.
        if ref.norma == "asumida":
            if exigir_norma:
                d.estado = NO_VERIFICABLE
                d.motivo = (
                    "la cita no dice de que norma es el precepto; con "
                    "--exigir-norma no se supone ninguna"
                )
                return d
            d.comprobaciones.append(
                "norma: no se indico en la cita"
            )

        # -- 2. el precepto existe, y en un solo sitio --
        clave, candidatos = self._buscar_clave(ref)
        if not clave and len(candidatos) > 1:
            # Con varias normas cargadas, "articulo 71" a secas designa dos
            # preceptos distintos. Validar contra cualquiera de ellos seria
            # elegir al azar: NO VERIFICABLE.
            donde = ", ".join(
                self.ix.normas.por_clave(
                    self.ix.por_clave[c].registro["cuerpo_clave"]
                ).etiqueta for c in candidatos
            )
            d.estado = NO_VERIFICABLE
            d.motivo = (
                f"la cita no dice de que norma es, y ese precepto existe en "
                f"{len(candidatos)}: {donde}. No se valida contra ninguna"
            )
            return d
        if not clave:
            d.estado = NO_VERIFICADA
            etiqueta = (
                f"articulo {ref.numero}"
                if ref.tipo == "articulo"
                else f"{ref.tipo.replace('_', ' ')} {ref.numero}"
            )
            d.motivo = f"no existe el {etiqueta} en las normas cargadas"
            # Si el fragmento esta en otro sitio, se dice donde.
            otros = self.localizar(cita.literal_norm)
            if otros:
                d.hallazgos = otros[:5]
                d.motivo += (
                    f"; el fragmento si aparece en: "
                    f"{', '.join(sorted({h.referencia for h in otros[:5]}))}"
                )
            return d

        reg = self.ix.por_clave[clave].registro
        d.clave = clave
        d.referencia_corpus = reg["referencia"]
        d.enlace_correcto = reg["url"]
        d.comprobaciones.append(f"precepto localizado: {reg['referencia']}")

        # -- 3. vigencia en el ejercicio del caso --
        avisos_fecha = V.avisos(reg, ejercicio)
        graves = [a for a in avisos_fecha if a.nivel == V.GRAVE]
        bloqueantes = [
            a for a in graves if a.clave in ("no_existia", "caducado", "sin_fechas")
        ]
        if bloqueantes:
            d.estado = NO_VERIFICADA
            d.motivo = f"{reg['referencia']}: {bloqueantes[0].texto}"
            d.comprobaciones.append("vigencia: NO aplicable en el ejercicio")
            return d

        # -- 4. version aplicable --
        versiones = reg.get("versiones") or []
        if ejercicio is None:
            version = versiones[-1] if versiones else None
        else:
            version = V.version_aplicable(reg, V.limites(ejercicio)[1])
        if version is None:
            d.estado = NO_VERIFICADA
            d.motivo = f"{reg['referencia']} no tenia texto en vigor en {ejercicio}"
            return d
        d.version_usada = {
            "orden": version.get("orden"),
            "fecha_vigencia_efectiva": version.get("fecha_vigencia_efectiva"),
            "de_un_total": len(versiones),
        }
        d.comprobaciones.append(
            f"version usada: la del {version.get('fecha_vigencia_efectiva')} "
            f"({(version.get('orden') or 0) + 1} de {len(versiones)})"
        )

        # -- 5. puntos suspensivos: no es una cita literal --
        if cita.trozos:
            estados = []
            cuerpo = C.normalizar_literal(version.get("texto", ""))
            for t in cita.trozos:
                estados.append(f"{'si' if t in cuerpo else 'NO'}: «{t[:40]}…»")
            d.estado = NO_VERIFICADA
            d.motivo = (
                "la cita une trozos no contiguos con puntos suspensivos, asi que "
                "tal como esta escrita no es literal; hay que citarlos por "
                f"separado ({'; '.join(estados)})"
            )
            return d

        # -- 6. el fragmento, literal, en esa version --
        cuerpo = C.normalizar_literal(version.get("texto", ""))
        if cita.literal_norm and cita.literal_norm in cuerpo:
            d.comprobaciones.append("fragmento: literal en el articulado")
            # -- 7. el enlace --
            if cita.enlace and not self._enlace_ok(cita.enlace, reg):
                d.estado = NO_VERIFICADA
                d.motivo = (
                    f"el fragmento es correcto pero el enlace apunta a otro sitio: "
                    f"citado {cita.enlace} , correcto {reg['url']}"
                )
                return d
            d.comprobaciones.append(
                "enlace: correcto" if cita.enlace else "enlace: no se aporto"
            )
            d.estado = VERIFICADA
            d.motivo = ""
            if len(cita.literal_norm) < self.MINIMO_SUSTANCIA:
                d.comprobaciones.append(
                    f"atencion: el fragmento es muy corto ({len(cita.literal_norm)} "
                    f"caracteres); es literal, pero por si solo no sostiene una "
                    f"afirmacion juridica"
                )
            # Un cambio posterior no invalida la cita, pero se anota.
            posterior = [a for a in graves if a.clave in ("texto_cambiado",
                                                          "cambio_durante")]
            if posterior:
                d.comprobaciones.append(f"aviso: {posterior[0].texto}")
            return d

        # -- el fragmento NO esta en esa version: hay que decir por que --
        return self._diagnosticar_fallo(d, cita, reg, version, ejercicio)

    # ------------------------------------------------------------ diagnostico

    def _diagnosticar_fallo(
        self, d: Dictamen, cita: C.Cita, reg: dict, version: dict, ejercicio
    ) -> Dictamen:
        """El fragmento no esta donde se dijo. Se busca donde SI esta."""
        d.estado = NO_VERIFICADA
        hallazgos = self.localizar(cita.literal_norm)
        d.hallazgos = hallazgos[:6]

        propios = [h for h in hallazgos if h.clave == d.clave]
        articulado_propio = [h for h in propios if h.origen == ARTICULADO]
        notas_propias = [h for h in propios if h.origen != ARTICULADO]
        ajenos = [
            h for h in hallazgos if h.clave != d.clave and h.origen == ARTICULADO
        ]
        notas_ajenas = [
            h for h in hallazgos if h.clave != d.clave and h.origen != ARTICULADO
        ]

        # (d) el caso importante: casa contra material que no es norma.
        if notas_propias or (not articulado_propio and not ajenos and notas_ajenas):
            fuente = (notas_propias or notas_ajenas)[0]
            d.motivo = (
                f"el texto existe pero NO ES ARTICULADO: sale de "
                f"{ETIQUETA_ORIGEN[fuente.origen]} de {fuente.referencia}. "
                f"Ese material no es texto promulgado y no puede fundamentar nada"
            )
            return d

        # (c) literal, pero de otra version del mismo articulo.
        if articulado_propio:
            otra = articulado_propio[0]
            d.motivo = (
                f"el fragmento es de OTRA VERSION de {reg['referencia']}: consta en "
                f"la version del {otra.fecha_version}, y en {ejercicio} regia la "
                f"del {version.get('fecha_vigencia_efectiva')}"
            )
            return d

        # (h) literal, pero de otro precepto (163 vs 163 bis).
        if ajenos:
            donde = sorted({h.referencia for h in ajenos})
            d.motivo = (
                f"el fragmento NO esta en {reg['referencia']}; el texto citado es "
                f"de {', '.join(donde)}"
            )
            return d

        # (b) no esta en ninguna parte del corpus.
        laxo = self._parecido(cita.literal_norm, version.get("texto", ""))
        d.motivo = (
            f"el fragmento no aparece en {reg['referencia']} "
            f"(version del {version.get('fecha_vigencia_efectiva')})"
        )
        if laxo:
            d.motivo += f"; {laxo}"
        return d

    @staticmethod
    def _parecido(literal: str, texto: str) -> str:
        """Explica un fallo por poco: tildes o mayusculas.

        No valida nada: solo evita el mensaje inutil de "no aparece" cuando la
        diferencia es una tilde que en un texto juridico si importa.
        """
        cuerpo = C.normalizar_literal(texto)
        if literal.lower() in cuerpo.lower():
            return "coincide salvo por mayusculas/minusculas, y una cita se copia tal cual"
        if C.sin_tildes_min(literal) in C.sin_tildes_min(cuerpo):
            return "coincide salvo por las tildes, que en un texto juridico son parte de la cita"
        return ""

    @staticmethod
    def _enlace_ok(enlace: str, reg: dict) -> bool:
        """El enlace tiene que llevar al ancla de ESE precepto."""
        esperado = reg["url"]
        if enlace.rstrip("/") == esperado.rstrip("/"):
            return True
        # Se admite el enlace de la API al mismo bloque.
        if enlace.rstrip("/") == (reg.get("url_api") or "").rstrip("/"):
            return True
        ancla = "#" + reg["id_bloque"]
        return enlace.endswith(ancla) and "BOE-A-1992-28740" in enlace

    # ------------------------------------------------------------ informe

    def verificar_texto(
        self, texto: str, ejercicio: int | None, exigir_norma: bool = False
    ) -> Informe:
        lista, sueltas = C.extraer(texto, registro=self.ix.normas)
        dictamenes = [
            self.verificar_cita(c, ejercicio, exigir_norma) for c in lista
        ]

        if not dictamenes:
            return Informe(
                RECHAZADO,
                ejercicio,
                dictamenes,
                sueltas,
                "el texto no contiene ninguna cita con fragmento literal: "
                "sin fuente no hay respuesta",
            )

        malas = [d for d in dictamenes if d.estado != VERIFICADA]
        if malas:
            # No existe el aprobado parcial: una sola cita que no queda
            # VERIFICADA tumba la respuesta entera.
            return Informe(
                RECHAZADO,
                ejercicio,
                dictamenes,
                sueltas,
                f"{len(malas)} de {len(dictamenes)} citas no han quedado "
                f"VERIFICADAS (no hay verificacion parcial)",
            )
        return Informe(ACEPTADO, ejercicio, dictamenes, sueltas, "")
