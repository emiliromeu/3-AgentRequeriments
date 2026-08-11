"""Indice invertido en memoria sobre el JSONL de la fase 1.

Sin base de datos, sin embeddings, sin IA: diccionarios de Python y BM25F.

Dos decisiones que se notan en los resultados:

1. EL TITULO PESA MAS QUE EL CUERPO. En una ley fiscal el epigrafe del articulo
   es su tema ("Limitaciones del derecho a deducir"). Una coincidencia ahi vale
   mucho mas que una perdida en mitad de un parrafo.
   Ojo: en este corpus `titulo_bloque` es solo "Articulo 95"; el epigrafe de
   verdad esta en `rubrica`. El campo de titulo se arma con las dos cosas, de
   modo que buscar "articulo 95" tambien funcione.

2. SE INDEXA LA RAIZ Y TAMBIEN LA PALABRA EXACTA. Lematizar sube el recall
   (deduccion/deducir) pero junta cosas distintas: "importe" e "importacion"
   comparten raiz. Indexando ademas la forma exacta, quien busca "importe"
   puntua mas alto los articulos que dicen literalmente "importe".

Lo que NUNCA entra en el indice: `notas_boe` (historial de reformas) y
`notas_editoriales` (avisos del BOE). No son texto promulgado y no pueden
fundamentar nada.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from . import texto as T

# Campos indexados y su peso relativo.
PESOS_CAMPO = {"titulo": 4.0, "contexto": 0.8, "cuerpo": 1.0}
# Normalizacion por longitud de campo (b de BM25). Un titulo es corto por
# naturaleza; penalizarlo por longitud como a un parrafo no tiene sentido.
B_CAMPO = {"titulo": 0.35, "contexto": 0.35, "cuerpo": 0.75}
K1 = 1.4
# Cuanto suma coincidir con la palabra literal, ademas de con su raiz.
PESO_EXACTO = 0.45
# Prefijo interno para las formas exactas dentro del mismo indice.
MARCA_EXACTA = "="


class ErrorCorpus(Exception):
    """El corpus no esta donde deberia o no se puede leer."""


@dataclass
class Documento:
    """Un precepto, ya preparado para buscar."""

    registro: dict
    longitudes: dict = field(default_factory=dict)

    @property
    def referencia(self) -> str:
        return self.registro["referencia"]

    @property
    def clave(self) -> str:
        return self.registro["clave"]


@dataclass
class Resultado:
    doc: Documento
    puntuacion: float
    # Que termino de la consulta aporto cuanto: para poder explicar el porque.
    aportes: dict = field(default_factory=dict)
    campos_tocados: set = field(default_factory=set)


class Indice:
    """Indice invertido BM25F sobre los preceptos citables."""

    def __init__(self, origen):
        """`origen` puede ser un fichero JSONL, una lista de ficheros, o el
        DIRECTORIO del corpus: en ese caso se cargan TODAS las normas que
        haya ingeridas, sin saber cuales ni cuantas."""
        self.rutas = self._resolver_origen(origen)
        self.ruta = self.rutas[0] if self.rutas else Path(str(origen))
        self.docs: list[Documento] = []
        self.por_clave: dict[str, Documento] = {}
        # termino -> {indice_doc: {campo: frecuencia}}
        self.postings: dict[str, dict[int, dict[str, int]]] = defaultdict(dict)
        self.df: dict[str, int] = defaultdict(int)
        self.long_media: dict[str, float] = {}
        self._cargar()
        self._indexar()

    # ------------------------------------------------------------ carga

    @staticmethod
    def _resolver_origen(origen) -> list:
        if isinstance(origen, (list, tuple)):
            return [Path(x) for x in origen]
        ruta = Path(origen)
        if ruta.is_dir():
            # Todas las normas ingeridas, en orden estable.
            return sorted(
                f for f in ruta.glob("*.jsonl") if not f.name.endswith(".descartados.jsonl")
            )
        return [ruta]

    def _cargar(self) -> None:
        if not self.rutas:
            raise ErrorCorpus(
                "No hay ninguna norma ingerida.\n"
                "  Ejecuta antes:  python fase1.py ingerir BOE-A-1992-28740"
            )
        for ruta in self.rutas:
            if not ruta.exists():
                raise ErrorCorpus(
                    f"No existe el corpus {ruta}.\n"
                    f"  Ejecuta antes:  python fase1.py ingerir <IDENTIFICADOR>"
                )
            for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
                if not linea.strip():
                    continue
                try:
                    reg = json.loads(linea)
                except json.JSONDecodeError as e:
                    raise ErrorCorpus(f"{ruta} linea {n}: JSON invalido: {e}") from e
                self.docs.append(Documento(reg))

        if not self.docs:
            raise ErrorCorpus(f"El corpus {self.ruta} esta vacio.")

        # EL CORPUS, CONTRA SU SUMA DE CONTROL. Va aqui y no en el arranque de
        # cada programa porque aqui pasan TODOS: la ventana, la terminal, el
        # banco y las pruebas. Un sitio, una regla.
        #
        # MEJOR NO ABRIR QUE ABRIR CON MEDIA LEY. Un corpus truncado en un
        # final de linea carga sin protestar y lo unico que se nota es que
        # empiezan a salir NO ENCONTRADO donde antes habia respuesta. Nadie lo
        # relaciona con el corpus. Ver `sellos`.
        from . import sellos as S
        problemas = S.comprobar(self.rutas)
        if problemas:
            raise ErrorCorpus(
                "El corpus no cuadra con su suma de control. No se abre: con "
                "media ley las respuestas empeoran sin dar ningun error.\n"
                + "\n".join(f"  - {p}" for p in problemas))

        # Registro de normas y cuerpos, derivado de lo que se acaba de cargar.
        from .normas import Registro
        self.normas = Registro(self.docs)

        for d in self.docs:
            # Si dos preceptos compartiesen clave, uno taparia al otro. La
            # fase 1 ya lo audita, pero aqui no se da por supuesto.
            if d.clave in self.por_clave:
                raise ErrorCorpus(
                    f"Clave duplicada en el corpus: {d.clave!r} "
                    f"({self.por_clave[d.clave].referencia} y {d.referencia})"
                )
            self.por_clave[d.clave] = d

    # ------------------------------------------------------------ campos

    @staticmethod
    def campos_de(reg: dict) -> dict[str, str]:
        """Texto de cada campo indexable de un precepto.

        El cuerpo excluye la primera linea, que es el propio encabezado
        ("Articulo 95. Limitaciones...") y ya va en el campo de titulo.
        """
        cuerpo = reg.get("texto_vigente") or ""
        partes = cuerpo.split("\n")
        cuerpo_sin_encabezado = "\n".join(partes[1:]) if len(partes) > 1 else cuerpo
        return {
            "titulo": f"{reg.get('referencia', '')}. {reg.get('rubrica', '')}",
            "contexto": " ".join(reg.get("contexto") or []),
            "cuerpo": cuerpo_sin_encabezado,
        }

    # ------------------------------------------------------------ indexado

    def _indexar(self) -> None:
        acumulado = defaultdict(float)

        for i, doc in enumerate(self.docs):
            campos = self.campos_de(doc.registro)
            terminos_doc: set[str] = set()

            for campo, contenido in campos.items():
                planas = T.tokenizar(contenido, quitar_vacias=True)
                exactas = T.palabras_exactas(contenido)
                doc.longitudes[campo] = len(planas)
                acumulado[campo] += len(planas)

                for termino in planas:
                    self._anotar(termino, i, campo)
                    terminos_doc.add(termino)
                for palabra in exactas:
                    marcado = MARCA_EXACTA + palabra
                    self._anotar(marcado, i, campo)
                    terminos_doc.add(marcado)

            for t in terminos_doc:
                self.df[t] += 1

        n = len(self.docs)
        self.long_media = {c: (acumulado[c] / n if n else 0.0) or 1.0 for c in PESOS_CAMPO}

    def _anotar(self, termino: str, i_doc: int, campo: str) -> None:
        porcampo = self.postings[termino].setdefault(i_doc, {})
        porcampo[campo] = porcampo.get(campo, 0) + 1

    # ------------------------------------------------------------ busqueda

    def _idf(self, termino: str) -> float:
        n = len(self.docs)
        df = self.df.get(termino, 0)
        if df == 0:
            return 0.0
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    def analizar_consulta(self, consulta: str) -> tuple[list[str], list[str], list[str]]:
        """Devuelve (raices, formas_exactas, terminos_sin_resultados).

        El tercer valor es el que impide fallar en silencio: si alguien busca
        una palabra que no esta en el corpus, hay que decirselo.
        """
        raices = T.tokenizar(consulta, quitar_vacias=True)
        exactas = T.palabras_exactas(consulta)
        huerfanos = sorted({r for r in raices if self.df.get(r, 0) == 0})
        return raices, exactas, huerfanos

    def buscar(self, consulta: str, tope: int = 10) -> tuple[list[Resultado], list[str]]:
        raices, exactas, huerfanos = self.analizar_consulta(consulta)

        # termino -> factor con el que entra en la puntuacion
        pesos_termino: dict[str, float] = {}
        for r in raices:
            pesos_termino[r] = max(pesos_termino.get(r, 0.0), 1.0)
        for e in exactas:
            pesos_termino[MARCA_EXACTA + e] = PESO_EXACTO

        if not pesos_termino:
            return [], huerfanos

        acumulados: dict[int, Resultado] = {}
        for termino, factor in pesos_termino.items():
            idf = self._idf(termino)
            if idf <= 0:
                continue
            for i_doc, porcampo in self.postings.get(termino, {}).items():
                doc = self.docs[i_doc]
                tf_tilde = 0.0
                for campo, frec in porcampo.items():
                    largo = doc.longitudes.get(campo, 0)
                    medio = self.long_media.get(campo, 1.0) or 1.0
                    b = B_CAMPO[campo]
                    denom = 1 - b + b * (largo / medio)
                    tf_tilde += PESOS_CAMPO[campo] * frec / (denom or 1.0)

                aporte = factor * idf * tf_tilde / (K1 + tf_tilde)
                if aporte <= 0:
                    continue
                res = acumulados.get(i_doc)
                if res is None:
                    res = acumulados[i_doc] = Resultado(doc, 0.0)
                res.puntuacion += aporte
                visible = termino[1:] if termino.startswith(MARCA_EXACTA) else termino
                res.aportes[visible] = res.aportes.get(visible, 0.0) + aporte
                res.campos_tocados.update(porcampo.keys())

        orden = sorted(
            acumulados.values(),
            # A igualdad de puntuacion, primero el precepto que va antes en la
            # ley: el orden tiene que ser estable entre ejecuciones.
            key=lambda r: (-r.puntuacion, r.doc.registro["posicion"]),
        )
        return orden[:tope], huerfanos
