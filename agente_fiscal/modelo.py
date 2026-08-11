"""El UNICO modulo de todo el sistema que habla con un modelo de lenguaje.

Todo lo demas (fase 1 troceo, fase 2 busqueda, fase 3 verificacion, y el
calculo del estado de la fase 4) es deterministico y no pasa por aqui.

Dos llamadas y ninguna mas:
    analizar()  clasifica la pregunta y devuelve JSON
    redactar()  redacta con lo recuperado, y solo con lo recuperado

La respuesta cruda de la API se devuelve siempre junto a la parseada, para que
quien llame la guarde en la traza ANTES de interpretarla. Misma regla que en la
fase 1 con el BOE: primero se guarda, luego se parsea.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field

# UN MODELO POR PASO, y ninguno cableado en el codigo que orquesta: se eligen
# aqui o con --modelo-analisis / --modelo-redaccion.
#
# EL ANALIZADOR SE PROBO CON HAIKU Y SE VOLVIO A OPUS. La medida esta hecha
# (`python banco.py --comparar-analizador`) y dice dos cosas a la vez:
#
#   - sobre los 15 casos del banco, Haiku es igual o mejor: encuentra el
#     articulo correcto en 14 de 15, Opus en 13 de 15, y por menos tokens;
#   - pero en la consulta con la cita falsa inyectada -la que existe para que
#     el sistema NO cuele una mentira- Haiku propone cuatro terminos genericos
#     ("deduccion", "vehiculo de turismo", "porcentaje de deduccion",
#     "proporcionalidad"), la puerta de pertinencia los rechaza y la consulta
#     acaba en NO ENCONTRADO. Dos veces de dos. Con Opus sale CRITERIO CLARO
#     con 6 citas verificadas.
#
# Un analizador mas barato que convierte una respuesta buena en NO ENCONTRADO
# no es mas barato: es peor. Se deja Opus de momento, y el cambio a Haiku a un
# flag de distancia para cuando el prompt del analizador exija mas terminos.
MODELO_ANALISIS = "claude-opus-5"
MODELO_REDACCION = "claude-opus-5"
# Compatibilidad: quien pida "el modelo" a secas se refiere al que redacta.
MODELO = MODELO_REDACCION

MAX_TOKENS_ANALISIS = 4000
MAX_TOKENS_REDACCION = 8000

# Minimo de tokens que hay que mandar para que la cache llegue a escribirse.
# Por debajo NO falla: se ignora en silencio, que es peor. Depende del modelo.
MINIMO_CACHE = {
    "claude-opus-5": 512,
    "claude-fable-5": 512,
    "claude-opus-4-8": 1024,
    "claude-sonnet-5": 1024,
    "claude-opus-4-7": 2048,
    "claude-haiku-4-5": 4096,
}
MINIMO_CACHE_POR_DEFECTO = 4096   # si no se conoce el modelo, se supone lo peor

# Caracteres por token, MEDIDO contra lo que conto la API (ver `_cacheable`).
# No es el 3,5 que se dice para ingles: el castellano juridico sale a 2,22.
CARACTERES_POR_TOKEN = 2.2

# `output_config.effort` no lo admiten todos los modelos: en Haiku 4.5 la
# llamada se cae con un 400. Se comprueba, no se supone.
SIN_EFFORT = ("claude-haiku-4-5", "claude-sonnet-4-5")


def admite_effort(modelo: str) -> bool:
    return not modelo.startswith(SIN_EFFORT)


def minimo_cache(modelo: str) -> int:
    return MINIMO_CACHE.get(modelo, MINIMO_CACHE_POR_DEFECTO)


def entorno_limpio(texto: str) -> str:
    """Atajo: ningun mensaje sale de aqui sin pasar el filtro de secretos."""
    from . import entorno
    return entorno.limpiar(texto)


class ErrorModelo(Exception):
    """Fallo al hablar con el modelo. Nunca se traga en silencio."""


@dataclass
class Respuesta:
    """Lo que devuelve una llamada: texto, datos y la respuesta cruda."""

    texto: str = ""
    datos: dict | None = None
    crudo: dict = field(default_factory=dict)
    modelo: str = ""
    motor: str = ""
    uso: dict = field(default_factory=dict)


# --------------------------------------------------------------------- base


def normalizar_uso(uso: dict) -> dict:
    """Los cuatro numeros que importan de una llamada, con nombres estables.

    `entrada` son SOLO los tokens que se han pagado enteros: los que vienen de
    cache van aparte. Sumarlos seria contar dos veces y hacer creer que la
    cache no sirve para nada.
    """
    uso = uso or {}
    return {
        "entrada": uso.get("input_tokens", 0) or 0,
        "salida": uso.get("output_tokens", 0) or 0,
        "cache_lectura": uso.get("cache_read_input_tokens", 0) or 0,
        "cache_escritura": uso.get("cache_creation_input_tokens", 0) or 0,
    }


# ---------------------------------------------------------------------------
# EL TECHO DURO. No depende de que la logica de arriba este bien.
# ---------------------------------------------------------------------------
# Ya hay un reintento controlado en `fase4`, y esta bien. Pero un tope que vive
# en el bucle solo protege mientras ese bucle este bien escrito, y el dia que
# alguien meta otro bucle -o que un `while` no salga por donde deberia- no hay
# nada debajo. Esto es lo de debajo: cuenta las llamadas y el tiempo en el
# MOTOR, que es el unico sitio por el que se pasa siempre.
#
# Vale para todos los motores, tambien el de ensayo: un tope que solo actua
# cuando cuesta dinero no se puede probar el dia que hace falta.
TOPE_LLAMADAS = 6        # analisis (2) + redaccion (2) + margen para un futuro
TOPE_SEGUNDOS = 300      # 5 minutos por consulta completa, de punta a punta

# Nada de esperas indefinidas: si la red se queda colgada, el proceso tambien.
TIMEOUT_LLAMADA = 120.0  # segundos que se espera UNA llamada
REINTENTOS_RED = 3       # reintentos por fallo de red, con espera creciente


class TopeAlcanzado(ErrorModelo):
    """Se ha llegado al techo. No es un fallo del modelo: es la red de seguridad."""


class Motor:
    """Interfaz comun. Permite cambiar de motor sin tocar la orquestacion."""

    nombre = "base"
    es_modelo_real = False

    def __init__(self, tope_llamadas: int = TOPE_LLAMADAS,
                 tope_segundos: float = TOPE_SEGUNDOS):
        # Cuantas llamadas se han hecho. El banco de pruebas lo publica en
        # cada ejecucion: conviene saber lo que cuesta pasar el banco.
        self.llamadas = 0
        # Una linea por llamada: paso, modelo y tokens. Es la unica fuente de
        # la que salen los totales de la traza y del banco. Sin esto,
        # "optimizar el consumo" seria una opinion.
        self.consumo: list[dict] = []
        self.tope_llamadas = tope_llamadas
        self.tope_segundos = tope_segundos
        self.arranque = time.monotonic()
        # Por que se paro, si se paro. Va a la traza: "se paro en el tope" y
        # "el modelo fallo" son cosas distintas y se leen igual si no se dice.
        self.motivo_parada = ""

    # --------------------------------------------------------------- topes

    def reiniciar_reloj(self) -> None:
        """El tiempo se cuenta por CONSULTA, no por vida del motor.

        El banco reutiliza el mismo motor para varias consultas seguidas; sin
        esto, la quinta se pasaria de tiempo por culpa de las cuatro anteriores.
        """
        self.arranque = time.monotonic()
        self.motivo_parada = ""

    @property
    def segundos(self) -> float:
        return time.monotonic() - self.arranque

    def _permiso(self, paso: str) -> None:
        """Se llama ANTES de cada llamada. Si no hay permiso, para y lo dice.

        Se comprueba antes y no despues a proposito: el objetivo es no gastar
        la llamada, no enterarse de que se ha gastado.
        """
        if self.llamadas >= self.tope_llamadas:
            self.motivo_parada = (
                f"tope de {self.tope_llamadas} llamadas al modelo por consulta")
            raise TopeAlcanzado(
                f"Se ha alcanzado el tope de {self.tope_llamadas} llamadas al "
                f"modelo en esta consulta (iba a hacer la {self.llamadas + 1}, "
                f"en el paso «{paso}»). Se para aqui: no se sigue llamando.")
        if self.segundos > self.tope_segundos:
            self.motivo_parada = (
                f"tope de {self.tope_segundos:.0f} s por consulta")
            raise TopeAlcanzado(
                f"Esta consulta lleva {self.segundos:.0f} segundos y el tope "
                f"son {self.tope_segundos:.0f}. Se para aqui.")

    def a_json_topes(self) -> dict:
        """Lo que hay que poder leer en la traza para auditar una parada."""
        return {
            "llamadas": self.llamadas,
            "tope_llamadas": self.tope_llamadas,
            "segundos": round(self.segundos, 1),
            "tope_segundos": self.tope_segundos,
            "motivo_parada": self.motivo_parada,
        }

    # ------------------------------------------------------------- consumo

    def _anotar(self, paso: str, modelo: str, uso: dict) -> dict:
        linea = {"paso": paso, "modelo": modelo, **normalizar_uso(uso)}
        linea["cache"] = (
            "lectura" if linea["cache_lectura"]
            else ("escritura" if linea["cache_escritura"] else "no")
        )
        self.consumo.append(linea)
        return linea

    def totales(self) -> dict:
        """Suma de todo lo gastado por este motor desde que se creo."""
        t = {"llamadas": len(self.consumo), "entrada": 0, "salida": 0,
             "cache_lectura": 0, "cache_escritura": 0}
        for c in self.consumo:
            for k in ("entrada", "salida", "cache_lectura", "cache_escritura"):
                t[k] += c[k]
        # Lo que habria costado sin cache, para poder decir si sirve de algo.
        t["entrada_total_procesada"] = (
            t["entrada"] + t["cache_lectura"] + t["cache_escritura"]
        )
        return t

    def analizar(self, sistema: str, pregunta: str, esquema: dict) -> Respuesta:
        raise NotImplementedError

    def redactar(self, sistema: str, contenido: str) -> Respuesta:
        raise NotImplementedError


# ------------------------------------------------------------ credencial


def comprobar_credencial(*modelos: str) -> tuple[bool, str]:
    """Comprueba que se puede hablar con CADA modelo. Devuelve (ok, mensaje).

    Una frase clara, nunca una traza. Se ejecuta al arrancar, antes de gastar
    nada, porque el SDK NO avisa por su cuenta: `anthropic.Anthropic()` se
    construye tan tranquilo sin credencial (api_key queda a None) y el fallo
    no aparece hasta la primera llamada, disfrazado de error de autenticacion.

    Se comprueban todos los modelos que se vayan a usar, no solo uno: desde
    que el analizador y el redactor son modelos distintos, tener acceso a uno
    no dice nada del otro.
    """
    modelos = modelos or (MODELO_ANALISIS, MODELO_REDACCION)
    from . import entorno

    # 1) variable de entorno  2) .env de la raiz  3) error claro
    origen = entorno.cargar()

    try:
        import anthropic
    except ImportError:
        return False, (
            "Falta el SDK de Anthropic. Instalalo con:  pip install anthropic"
        )

    try:
        cliente = anthropic.Anthropic()
    except Exception as e:  # noqa: BLE001
        return False, f"No se pudo crear el cliente de Anthropic: {e}"

    import os
    from pathlib import Path

    hay_env = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    hay_perfil = (Path.home() / ".config" / "anthropic").is_dir()
    if not hay_env and not hay_perfil and not getattr(cliente, "api_key", None):
        detalle = "; ".join(origen.avisos) if origen.avisos else ""
        return False, (
            "No hay ninguna credencial configurada. Crea un fichero .env en la "
            f"raiz del proyecto con la linea  ANTHROPIC_API_KEY=sk-ant-...  "
            f"(o exporta la variable)."
            + (f" [{detalle}]" if detalle else "")
        )

    # Prueba real y gratuita: consultar el modelo no gasta tokens y verifica
    # de una vez la credencial Y que esta cuenta tiene acceso a ese modelo.
    try:
        for m in modelos:
            cliente.models.retrieve(m)
    except anthropic.AuthenticationError:
        return False, (
            "La credencial existe pero la API la rechaza (401). Revisa que la "
            "clave sea correcta y no este revocada."
        )
    except anthropic.PermissionDeniedError:
        return False, (
            "La credencial es valida pero no tiene permiso para usar la API. "
            "Revisa el espacio de trabajo y los permisos de la clave."
        )
    except anthropic.NotFoundError:
        return False, (
            f"La credencial funciona, pero esta cuenta no tiene acceso a "
            f"alguno de estos modelos: {', '.join(modelos)}."
        )
    except anthropic.APIConnectionError:
        return False, (
            "No hay conexion con la API de Anthropic. Revisa la red o el proxy."
        )
    except Exception as e:  # noqa: BLE001
        return False, entorno.limpiar(
            f"No se pudo comprobar la credencial: {type(e).__name__}: {e}"
        )

    # Se dice DE DONDE ha salido y se ensena solo el principio de la clave.
    clave = os.environ.get(entorno.VARIABLE, "")
    return True, (
        f"credencial correcta ({entorno.enmascarar(clave)}) tomada de "
        f"{origen.descripcion()}; acceso confirmado a: {', '.join(modelos)}"
    )


def comprobar_esquema(esquema: dict, modelo: str = MODELO_ANALISIS) -> tuple[bool, str]:
    """Manda el esquema a la API y comprueba que lo acepta. UNA llamada.

    Existe porque un esquema invalido no falla al escribirlo ni al cargarlo:
    falla en la primera llamada real, con un 400, y tumba la ejecucion entera.
    La primera pasada del banco contra el modelo se perdio asi: 37 llamadas
    para descubrir que `maxItems` no esta soportado.

    Con `max_tokens` al minimo, la comprobacion cuesta calderilla.
    """
    from . import entorno

    entorno.cargar()
    try:
        import anthropic
    except ImportError:
        return False, "falta el SDK de Anthropic"

    salida = {"format": {"type": "json_schema", "schema": esquema}}
    if admite_effort(modelo):
        salida["effort"] = "low"
    try:
        cliente = anthropic.Anthropic()
        cliente.messages.create(
            model=modelo,
            max_tokens=64,
            output_config=salida,
            messages=[{"role": "user", "content": "prueba de esquema"}],
        )
    except anthropic.BadRequestError as e:
        return False, entorno.limpiar(
            f"La API RECHAZA el esquema (400): {getattr(e, 'message', e)}"
        )
    except Exception as e:  # noqa: BLE001
        return False, entorno.limpiar(
            f"no se pudo comprobar el esquema: {type(e).__name__}: {e}"
        )
    return True, f"la API acepta el esquema del analizador en {modelo}"


# ------------------------------------------------------------------ real


class MotorAnthropic(Motor):
    """Llamadas reales a la API de Anthropic."""

    nombre = "anthropic"
    es_modelo_real = True

    def __init__(
        self,
        modelo_analisis: str = MODELO_ANALISIS,
        modelo_redaccion: str = MODELO_REDACCION,
    ):
        super().__init__()
        try:
            import anthropic  # noqa: F401
        except ImportError as e:
            raise ErrorModelo(
                "No esta instalado el SDK de Anthropic.\n"
                "  Instalalo con:  pip install anthropic\n"
                "  Es la unica dependencia de todo el proyecto, y solo la usa "
                "la fase 4."
            ) from e

        import anthropic

        from . import entorno
        entorno.cargar()

        self._anthropic = anthropic
        self.modelo_analisis = modelo_analisis
        self.modelo_redaccion = modelo_redaccion
        # `modelo` sigue existiendo y es el que redacta: es el que sale en la
        # traza cuando se pregunta "quien escribio esto".
        self.modelo = modelo_redaccion
        try:
            # Sin argumentos: coge la credencial del entorno
            # (ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN o el perfil de `ant`).
            # NI UNA ESPERA INDEFINIDA. Sin `timeout` el SDK espera 10
            # minutos por llamada, y sin `max_retries` reintenta 2 veces por su
            # cuenta: dos numeros que nadie eligio y que se multiplican. Aqui
            # se eligen, y la espera entre reintentos la hace el SDK creciente.
            self.cliente = anthropic.Anthropic(
                timeout=TIMEOUT_LLAMADA, max_retries=REINTENTOS_RED)
        except Exception as e:  # noqa: BLE001 - se reenvia con contexto
            raise ErrorModelo(f"No se pudo crear el cliente de Anthropic: {e}") from e

    # -------------------------------------------------------------- comun

    def _llamar(self, **kwargs):
        """Una llamada con los errores traducidos a algo legible.

        Todo mensaje pasa por `entorno.limpiar`: una traza de la API nunca
        debe poder arrastrar la credencial a la pantalla ni al fichero de traza.
        """
        a = self._anthropic
        try:
            return self.cliente.messages.create(**kwargs)
        except a.AuthenticationError as e:
            raise ErrorModelo(
                "Credencial invalida o ausente. Define ANTHROPIC_API_KEY o "
                f"inicia sesion con `ant auth login`. Detalle: {e}"
            ) from e
        except a.NotFoundError as e:
            raise ErrorModelo(
                entorno_limpio(f"El modelo {kwargs.get('model')!r} no existe o no es "
                f"accesible con esta credencial. Detalle: {e}")
            ) from e
        except a.RateLimitError as e:
            raise ErrorModelo(
                entorno_limpio(f"Limite de peticiones alcanzado. Reintenta mas tarde. Detalle: {e}")
            ) from e
        except a.APIConnectionError as e:
            raise ErrorModelo(entorno_limpio(f"No hay conexion con la API: {e}")) from e
        except a.APIStatusError as e:
            raise ErrorModelo(
                entorno_limpio(f"La API respondio {e.status_code}: {getattr(e, 'message', e)}")
            ) from e

    @staticmethod
    def _texto_de(respuesta) -> str:
        return "".join(b.text for b in respuesta.content if b.type == "text")

    # ------------------------------------------------------------ llamada 1

    def analizar(self, sistema: str, pregunta: str, esquema: dict) -> Respuesta:
        """Clasifica la pregunta. La salida viene forzada a JSON por la API.

        Se usa `output_config.format` con json_schema: asi el JSON no depende
        de que el modelo se acuerde de devolver JSON. Aun asi, quien llama lo
        vuelve a validar por reglas: el esquema garantiza la forma, no que los
        valores tengan sentido.
        """
        self._permiso("analisis")
        self.llamadas += 1
        salida = {"format": {"type": "json_schema", "schema": esquema}}
        # El effort no lo admite Haiku: pedirselo es un 400, no una mejora.
        if admite_effort(self.modelo_analisis):
            salida["effort"] = "medium"
        # ESTE PROMPT TAMBIEN SE CACHEA, y no se cacheaba. Es fijo y se repite
        # en cada consulta -lo unico que cambia es la pregunta, que va en el
        # mensaje-, asi que no habia motivo para pagarlo entero cada vez. No se
        # cacheaba porque el estimador contaba los tokens con la constante del
        # ingles y lo daba por corto. Ver `_cacheable`.
        bloque_sistema = {"type": "text", "text": sistema}
        if self._cacheable(sistema, self.modelo_analisis):
            bloque_sistema["cache_control"] = {"type": "ephemeral"}
        r = self._llamar(
            model=self.modelo_analisis,
            max_tokens=MAX_TOKENS_ANALISIS,
            system=[bloque_sistema],
            output_config=salida,
            messages=[{"role": "user", "content": pregunta}],
        )
        texto = self._texto_de(r)
        datos = None
        try:
            datos = json.loads(texto)
        except json.JSONDecodeError:
            # No se lanza: quien llama lo trata como analisis invalido y
            # reintenta. El crudo ya queda guardado en la traza.
            datos = None
        uso = self._uso_de(r)
        self._anotar("analisis", self.modelo_analisis, uso)
        return Respuesta(
            texto=texto,
            datos=datos,
            crudo=r.to_dict() if hasattr(r, "to_dict") else {},
            modelo=self.modelo_analisis,
            motor=self.nombre,
            uso=uso,
        )

    # ------------------------------------------------------------ llamada 2

    def redactar(self, sistema: str, contenido: str) -> Respuesta:
        """Redacta. Las instrucciones van marcadas como cacheables.

        El prompt se arma en orden: primero lo que NUNCA cambia (las reglas de
        redaccion), y despues lo que cambia en cada consulta (el material y la
        pregunta). La cache es un prefijo: si lo variable fuera delante, no
        habria nada que reutilizar. Por eso el material NO va en el bloque
        cacheado, aunque sea lo mas gordo: cambia en cada consulta y escribir
        cache que no se va a leer cuesta un 25% mas, no menos.

        La marca se pone SOLO si el bloque llega al minimo del modelo. Por
        debajo, la API la ignora sin decir nada y uno se queda creyendo que
        tiene cache.
        """
        self._permiso("redaccion")
        self.llamadas += 1
        bloque = {"type": "text", "text": sistema}
        if self._cacheable(sistema, self.modelo_redaccion):
            bloque["cache_control"] = {"type": "ephemeral"}
        r = self._llamar(
            model=self.modelo_redaccion,
            max_tokens=MAX_TOKENS_REDACCION,
            system=[bloque],
            messages=[{"role": "user", "content": contenido}],
        )
        uso = self._uso_de(r)
        self._anotar("redaccion", self.modelo_redaccion, uso)
        return Respuesta(
            texto=self._texto_de(r),
            crudo=r.to_dict() if hasattr(r, "to_dict") else {},
            modelo=self.modelo_redaccion,
            motor=self.nombre,
            uso=uso,
        )

    # ------------------------------------------------------------- apoyo

    @staticmethod
    def _uso_de(r) -> dict:
        u = getattr(r, "usage", None)
        return u.to_dict() if u is not None and hasattr(u, "to_dict") else {}

    @staticmethod
    def _cacheable(texto: str, modelo: str) -> bool:
        """Estimacion prudente de si el bloque llega al minimo de cache.

        LA CONSTANTE ESTABA MAL Y SE HA MEDIDO. Decia 3,5 caracteres por token,
        que es lo que se dice para ingles. En la traza 20260802T122131 la API
        conto 2.417 tokens para un bloque de 5.373 caracteres:

            5373 / 2417 = 2,22 caracteres por token

        Castellano juridico, con tildes, comillas latinas y palabras largas. Con
        3,5 se contaban un 58% menos tokens de los que hay, asi que bloques que
        SI llegaban al minimo se marcaban como que no y no se cacheaban nunca:
        es lo que le pasaba al prompt del analizador (1.466 caracteres, unos 660
        tokens, minimo 512).

        Se deja el 20% de margen: si aun asi el bloque no llega, la API se lo
        salta en silencio y no se cobra nada de mas. El riesgo es de un solo
        lado, y no es el caro.
        """
        aprox = len(texto) / CARACTERES_POR_TOKEN
        return aprox >= minimo_cache(modelo) * 1.2


# ----------------------------------------------------------------- ensayo


_RE_ANNO = re.compile(r"\b(19[9]\d|20\d\d)\b")
_RE_ENTRECOMILLADO = re.compile(r"[«\"“]([^»\"”]{12,400})[»\"”]")


class MotorEnsayo(Motor):
    """Motor de PRUEBA. No es un modelo: son cuatro reglas fijas.

    Existe para poder ejecutar las comprobaciones de la fase 4 sin gastar
    llamadas y, sobre todo, sin que el resultado dependa de lo que conteste un
    modelo ese dia. Lo que se prueba con el es el andamiaje deterministico:
    que sin ejercicio el sistema PARA, que el estado lo calcula el codigo, que
    el bucle con el verificador se cierra y que la traza queda completa.

    NO sirve para juzgar la calidad de la redaccion. Se anuncia en la salida y
    en la traza para que nadie confunda una cosa con la otra.
    """

    nombre = "ensayo"
    es_modelo_real = False

    def analizar(self, sistema: str, pregunta: str, esquema: dict) -> Respuesta:
        self._permiso("analisis")
        self.llamadas += 1
        self._anotar("analisis", "(ninguno)", {})
        from . import texto as T

        m = _RE_ANNO.search(pregunta)
        raices = T.tokenizar(pregunta)
        # LA NATURALEZA, con la misma clase de regla fija que el resto: unas
        # palabras que solo aparecen en preguntas de procedimiento. NO imita al
        # modelo, y no pretende: el motor de ensayo existe para probar el
        # andamiaje, no la calidad de la clasificacion.
        _proc = ("plazo", "prescri", "sancion", "sanción", "recargo",
                 "requerimiento", "extempor", "retras", "presentar",
                 "revisar", "corrige", "corregir", "complementaria")
        datos = {
            "impuesto": "IVA" if "iva" in pregunta.lower() else "desconocido",
            "naturaleza": ("procedimiento"
                           if any(x in pregunta.lower() for x in _proc)
                           else "fondo"),
            "ejercicio": int(m.group(1)) if m else None,
            "ejercicio_fundamento": (
                f"el ano {m.group(1)} aparece escrito en la pregunta"
                if m
                else "la pregunta no menciona ningun ejercicio"
            ),
            "articulos_sospechados": [],
            "terminos_busqueda": [p for p in pregunta.split() if len(p) > 3][:8]
            or raices[:8],
            "resumen_duda": pregunta.strip()[:200],
        }
        return Respuesta(
            texto=json.dumps(datos, ensure_ascii=False),
            datos=datos,
            crudo={"motor": "ensayo", "nota": "salida fabricada por reglas fijas"},
            modelo="(ninguno)",
            motor=self.nombre,
        )

    @staticmethod
    def _leer_material(contenido: str) -> list[tuple[str, str, str, str]]:
        """(referencia, enlace, norma, articulado) de cada precepto.

        Se lee campo A CAMPO, sin depender de en que orden esten en la ficha.
        La version anterior exigia el orden y dejo de casar en silencio el dia
        que la ficha se reordeno: el motor de ensayo se quedo sin citar nada y
        las comprobaciones siguieron en verde, porque comparaban dos vacios.
        Un motor de pruebas que no falla cuando deberia no prueba nada.
        """
        bloques = []
        for trozo in contenido.split("\n### ")[1:]:
            ref = trozo.split("\n", 1)[0].strip()
            m_txt = re.search(
                r"\[ARTICULADO [^\]]*\]\n(.*?)\n\[FIN ARTICULADO", trozo, re.S
            )
            if not m_txt:
                continue
            ficha = trozo[: m_txt.start()]
            def campo(nombre):
                m = re.search(rf"^\s*{nombre}:\s*(.+)$", ficha, re.M)
                return m.group(1).strip() if m else ""
            bloques.append((ref, campo("ENLACE"), campo("NORMA"), m_txt.group(1)))
        return bloques

    def redactar(self, sistema: str, contenido: str) -> Respuesta:
        """Redacta citando literalmente el primer precepto que se le pasa.

        Si en el material aparece un fragmento entrecomillado que NO procede
        del articulado (por ejemplo, uno colado en la pregunta), lo cita
        tambien: asi se puede comprobar que el verificador lo caza y que el
        bucle acaba en NO ENCONTRADO.
        """
        self._permiso("redaccion")
        self.llamadas += 1
        self._anotar("redaccion", "(ninguno)", {})
        bloques = self._leer_material(contenido)
        inyectado = ""
        m = re.search(r"FRAGMENTO SOSPECHOSO: (.+)", contenido)
        if m:
            inyectado = m.group(1).strip()

        if not bloques:
            return Respuesta(
                texto="No hay respaldo suficiente en el material aportado.",
                crudo={"motor": "ensayo"},
                modelo="(ninguno)",
                motor=self.nombre,
            )

        partes = []
        for ref, url, norma, txt in bloques[:2]:
            lineas = [l.strip() for l in txt.strip().split("\n") if l.strip()]
            cuerpo = [l for l in lineas[1:] if len(l) > 40]
            if not cuerpo:
                continue
            partes.append(
                f"En cuanto a la cuestion planteada, el "
                f"{ref} de la {norma} dispone que «{cuerpo[0]}» ({url})."
            )
        if inyectado:
            ref, url, norma = bloques[0][0], bloques[0][1], bloques[0][2]
            partes.append(
                f"Asimismo, el {ref} de la {norma} establece que "
                f"«{inyectado}» ({url})."
            )
        partes.append("En conclusion, procede estar a lo dispuesto en los "
                      "preceptos citados.")
        return Respuesta(
            texto="\n\n".join(partes),
            crudo={"motor": "ensayo", "bloques_usados": len(bloques)},
            modelo="(ninguno)",
            motor=self.nombre,
        )


def crear_motor(
    nombre: str,
    modelo_analisis: str = MODELO_ANALISIS,
    modelo_redaccion: str = MODELO_REDACCION,
) -> Motor:
    if nombre == "anthropic":
        return MotorAnthropic(modelo_analisis, modelo_redaccion)
    if nombre == "ensayo":
        return MotorEnsayo()
    raise ErrorModelo(f"motor desconocido: {nombre!r}")
