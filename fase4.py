#!/usr/bin/env python3
"""FASE 4 - Analizador y redaccion. Las dos unicas llamadas al modelo.

    python fase4.py consultar "texto de la duda" --ejercicio 2023
    python fase4.py credencial                       # comprueba el arranque
    python fase4.py comprobaciones
    python fase4.py consultar "..." --motor ensayo   # sin llamar a ningun modelo

Flujo:
    pregunta -> ANALIZAR (modelo) -> buscar (fase 2) -> REDACTAR (modelo)
             -> VERIFICAR (fase 3) -> mostrar o rechazar

Nada de lo importante lo decide el modelo: el ejercicio se comprueba contra el
texto de la pregunta, el estado lo calculan reglas, y ninguna respuesta se
muestra sin pasar el verificador.

Codigos de salida:
    0  respuesta mostrada (CRITERIO CLARO o DISCUTIDO)
    2  NO ENCONTRADO
    3  falta el ejercicio: hay que indicarlo
    1  error de uso, de corpus, de credencial o del modelo
"""

from __future__ import annotations

import argparse
import sys
import json
from pathlib import Path

from agente_fiscal import analizador as AN
from agente_fiscal import dgt as DGT
from agente_fiscal import estado as EST
from agente_fiscal import modelo as MOD
from agente_fiscal import redactor as RED
from agente_fiscal import referencias as R
from agente_fiscal import teac as TEAC
from agente_fiscal import texto as T
from agente_fiscal import verificador as VF
from agente_fiscal import vigencia as V
from agente_fiscal.indice import ErrorCorpus, Indice
from agente_fiscal.traza import Traza

RAIZ = Path(__file__).resolve().parent
# El corpus es el DIRECTORIO: se cargan todas las normas ingeridas,
# sin saber cuales ni cuantas.
CORPUS = RAIZ / "datos" / "corpus"
DIR_TRAZAS = RAIZ / "datos" / "trazas"
ANCHO = 78

# CUANTOS PRECEPTOS PUEDEN SER CANDIDATOS. NO es cuantos se envian: el corte
# por pertinencia decide despues, y descarta algo en el 62,7% de las consultas
# -medido sobre 984 selecciones reales en disco-. Subir el techo no inunda el
# material: solo ensancha quien puede presentarse, y el umbral sigue mandando.
#
# DE 5 A 6, Y POR QUE. El corte por puesto es fragil y cada norma que entra lo
# empeora: con la LGT se cayo el articulo 89 y con Sociedades el 19 de la
# LIRPF, que es el que enumera los gastos deducibles del trabajo. Con 6 vuelve.
#
# Lo que cuesta, medido sobre el banco y las dos de Renta: 13 consultas de 19
# mandan algun precepto mas, +1.512 tokens de media en esas y +1.034 sobre
# todas, o sea un 14% mas de material y SIETE DECIMAS DE CENTIMO por consulta.
#
# Y OJO CON UNA INTUICION FALSA: no suben solo las que llenaban el tope. El
# corte compara cada precepto contra la cobertura del PRIMERO, no es un
# prefijo, asi que un candidato en el puesto 6 con cobertura alta entra aunque
# el 4o y el 5o se hayan descartado. Por eso hay consultas que pasan de 2 a 3.
TOPE_MATERIAL = 6

# CUANTO PUEDE MEDIR UNA PREGUNTA. No habia tope, y el caso real es evidente:
# alguien pega un requerimiento entero de Hacienda en la caja. Medido con uno
# de 2.750 palabras: 17.000 caracteres, unos 7.700 tokens SOLO en el analisis,
# casi cuatro centimos antes de empezar a buscar nada.
#
# Y no es solo el dinero: una pregunta de 2.750 palabras no es una pregunta,
# son cincuenta, y el analizador tiene que sacar de ahi ocho terminos de
# busqueda. Sale ruido.
#
# 1.200 caracteres son unas 200 palabras: cabe de sobra una duda contada con
# detalle, con fechas e importes. Lo que no cabe es un documento pegado, y ese
# es justo el caso que hay que parar CON UN AVISO, no en silencio.
TOPE_PREGUNTA = 1200
MAX_INTENTOS = 2    # el original y UN reintento con los motivos exactos


def linea_consumo(tr) -> None:
    """El gasto de la consulta, desglosado. Lo mide la API, no se estima."""
    if not tr.consumo:
        return
    t = tr.totales()
    apartado("Consumo de esta consulta (lo que dice la API)")
    for c in tr.consumo:
        cache = {"lectura": "cache LEIDA", "escritura": "cache escrita",
                 "no": "sin cache"}[c["cache"]]
        print(f"   {c['paso']:<14} {c['modelo']:<20} "
              f"entrada {c['entrada']:>6}  salida {c['salida']:>5}  "
              f"cache {c['cache_lectura']:>6}L/{c['cache_escritura']:>5}E  ({cache})")
    print(f"   {'TOTAL':<14} {t['llamadas']} llamada(s)        "
          f"entrada {t['entrada']:>6}  salida {t['salida']:>5}  "
          f"cache {t['cache_lectura']:>6}L/{t['cache_escritura']:>5}E")
    print(f"   entrada procesada en total (pagada + cache): "
          f"{t['entrada_total_procesada']} tokens")


def titulo(t: str) -> None:
    print("\n" + "=" * ANCHO)
    print(t)
    print("=" * ANCHO)


def apartado(t: str) -> None:
    print("\n" + t)
    print("-" * len(t))


def cargar_corpus():
    ix = Indice(CORPUS)
    return ix, R.GrafoRemisiones(ix.docs)


def impuesto_tiene_autonomica(ix, impuesto: str) -> bool:
    """¿Hay preceptos autonomicos de ese impuesto en el corpus?

    Es lo que decide si merece la pena avisar de que falta la comunidad: en una
    consulta de IVA no hay tramo autonomico y el aviso seria ruido.
    """
    if not impuesto:
        return False
    return any(ix.normas.comunidad_de_precepto(d.registro)
               and ix.normas.impuesto_de_precepto(d.registro) == impuesto
               for d in ix.docs)


def recuperar(ix, grafo, consulta: str, impuesto: str,
              tope: int = TOPE_MATERIAL, naturaleza: str = "",
              comunidad: str = ""):
    """LA UNICA FORMA DE BUSCAR. -> (resultados, huerfanos, reserva)

    Existe para que no vuelva a pasar lo que ya ha pasado DOS VECES: un guion
    de medida llamando a una funcion distinta de la que usa el agente, y
    midiendo en silencio un sistema que ya no existe.

    La ultima: `banco.py` seguia con `ix.buscar` a secas despues de que la
    busqueda empezara a filtrar por impuesto. Decia que el articulo 4 de la Ley
    19/1991 no salia -y sale el tercero- y que el 26 de la Ley 27/2014 salia
    quinto -y sale segundo-. Cuatro sitios mas del propio banco estaban igual.
    Los 19 casos de IVA y LGT no lo delataron porque ganan con filtro y sin el;
    hizo falta un impuesto pequeno para que se viera.

    Parchear sitio a sitio es como se llega a cinco sitios distintos. Aqui hay
    uno, y el agente pasa por el mismo: si esto cambia, cambia para todos.
    """
    # QUE PUEDE COMPETIR: el impuesto de la pregunta y las normas generales
    # -la cadena vacia-. `None` si el impuesto no se sabe.
    admitidos = ix.normas.admitidos_para(impuesto)

    # LAS DOS LIGAS. Cuando la duda es DE FONDO y se sabe el impuesto, se busca
    # SOLO en los cuerpos de ese impuesto; las normas generales se quedan
    # fuera de la competicion y entran unicamente por remision, via la reserva.
    #
    # El motivo es de tamano, no de pertinencia: 836 preceptos generales contra
    # 47 de la Ley del Patrimonio. Compitiendo en el mismo ranking, las
    # generales copaban los puestos y los articulos de la ley del impuesto NO
    # LLEGABAN A SER CANDIDATOS. El articulo 37 de la Ley 19/1991 -quien esta
    # obligado a declarar- estaba en el puesto 4 contando solo su ley y en el
    # 25 con las generales dentro.
    #
    # Y SOLO CON LA SEÑAL. Con «procedimiento» o «no_esta_claro» no se separa
    # nada: medido, separar sin señal deja las cuatro preguntas de
    # procedimiento SIN RECUPERAR su articulo -de puesto 1 a no salir- porque
    # su respuesta vive precisamente en una norma general.
    from agente_fiscal import analizador as _AN
    if admitidos is not None and naturaleza == _AN.FONDO:
        admitidos = {impuesto}

    return ix.buscar_del_impuesto(consulta, tope, admitidos, grafo,
                                  comunidad=comunidad)


def _fin(res: dict, tr) -> dict:
    """El ultimo paso de TODA salida de `consultar`: dice si hay expediente.

    Un fallo de disco ya no tira la consulta -ver `Traza`-, pero entonces hay
    que decirlo, porque una respuesta sin expediente no se puede reconstruir
    dentro de seis meses y quien la enseñe tiene derecho a saberlo. Antes esto
    no podia ni plantearse: el `OSError` salia sin coger y lo que se veia era
    una traza de Python.

    Pasa por aqui hasta la salida de exito, a proposito: si algun dia se añade
    un `return` nuevo que no lo haga, el resultado se quedara sin el campo y la
    ventana lo cantara en vez de callarselo.
    """
    res["expediente"] = not tr.roto
    if tr.roto:
        res["aviso_expediente"] = (
            "esta consulta NO ha quedado guardada en el expediente "
            f"({tr.roto}). La respuesta es buena, pero dentro de unos meses no "
            "se va a poder reconstruir: guardala tu si la vas a usar.")
    return res


# ------------------------------------------------------------------ consultar


def otra_forma(traza, ejercicio, motor, ix) -> dict:
    """«Escribemelo para el cliente»: la misma respuesta, otra redaccion.

    NO ANALIZA, NO BUSCA, NO RECORTA. El material sale del expediente, tal
    cual: es lo que garantiza que es LA MISMA respuesta y no otra parecida.
    UNA llamada al modelo, no dos.

    Y EL VERIFICADOR PASA ENTERO SOBRE EL TEXTO NUEVO. Ver `otraforma.py` para
    por que no vale decir «el material es el mismo, ya estaba verificado»: lo
    que se verifica no es el material, es el TEXTO, y una reescritura para el
    cliente invita justo a lo que rompe una cita -resumir el fragmento
    entrecomillado, quitar la norma de la referencia, suavizar un «debera»-.

    Si la reescritura no pasa, NO SE ENSEÑA. Se dice, y se queda la primera,
    que si paso. Una respuesta mas facil de leer con una cita retocada no es
    mas facil: es falsa.
    """
    from agente_fiscal import otraforma as OF

    res = {"respuesta": "", "motivo": "", "veredicto": "", "traza": str(traza),
           "verificacion": {}, "llamadas": 0}
    try:
        material = OF.material_del_expediente(traza)
    except (FileNotFoundError, OSError) as e:
        res["motivo"] = str(e)
        return res

    # El tope se cuenta POR CONSULTA, y esto es una consulta corta: una
    # llamada. Sin esto arrastraria las de la consulta original.
    if hasattr(motor, "empezar_consulta"):
        motor.empezar_consulta()

    try:
        resp = motor.redactar(RED.SISTEMA + OF.PARA_EL_CLIENTE, material)
    except MOD.ErrorModelo as e:
        res["motivo"] = f"fallo del modelo: {e}"
        return res
    res["llamadas"] = 1

    if (resp.crudo or {}).get("stop_reason") == "max_tokens":
        res["motivo"] = ("la reescritura llego cortada por su longitud: no se "
                         "enseña media respuesta")
        return res

    borrador = (resp.texto or "").strip()
    informe = VF.Verificador(ix).verificar_texto(borrador, ejercicio,
                                                exigir_norma=True)
    res["veredicto"] = informe.veredicto
    res["verificacion"] = informe.a_json()

    # SE GUARDA PASE LO QUE PASE, y en el MISMO expediente: al lado de la
    # primera, con su informe propio. Dentro de seis meses tiene que poder
    # verse que las dos se comprobaron y contra que. Tambien la rechazada:
    # sobre todo la rechazada.
    try:
        d = Path(traza)
        n = len(list(d.glob("redaccion_para_cliente_*.txt"))) + 1
        (d / f"redaccion_para_cliente_{n}.txt").write_text(
            borrador, encoding="utf-8")
        (d / f"verificacion_para_cliente_{n}.json").write_text(
            json.dumps(informe.a_json(), ensure_ascii=False, indent=1),
            encoding="utf-8")
    except OSError:
        pass

    if informe.veredicto != VF.ACEPTADO:
        res["motivo"] = ("la reescritura no pasa el verificador: alguna cita "
                         "ha cambiado al reescribirla. Se queda la respuesta "
                         "de antes, que si esta comprobada.")
        return res

    res["respuesta"] = borrador
    return res


def consultar(pregunta: str, ejercicio_cli, motor, ix, grafo,
              progreso=None, con_criterio: bool | None = None,
              comunidad: str = "") -> dict:
    """Resuelve una duda. Imprime el proceso y DEVUELVE el resultado en dict.

    Devolver un dict (y no solo imprimir) es lo que permite que el banco de
    pruebas juzgue por codigo en vez de leer texto por pantalla.

    `progreso` es un aviso opcional de por que paso va (una funcion que recibe
    una frase). Lo usa la ventana de escritorio, que tarda decenas de segundos
    en contestar y necesita ensenar que sigue viva. No decide nada: si nadie lo
    pasa, aqui no cambia absolutamente nada.
    """
    def paso(texto: str) -> None:
        if progreso is not None:
            progreso(texto)

    # LO QUE SE PEGA DE UN PDF LLEGA CON LAS PALABRAS PARTIDAS. Se recomponen
    # aqui, en la entrada, para que las vean igual el modelo y la busqueda: si
    # se arreglara solo para una de las dos, el analisis y el indice estarian
    # leyendo preguntas distintas. Vease `texto.unir_cortes_de_linea`.
    pregunta = T.unir_cortes_de_linea(pregunta)

    # EL MODO ES DE ESTA CONSULTA, NO DEL SISTEMA. Es lo que hace que no haya
    # estado oculto que se descuadre: la respuesta sabe con que se hizo porque
    # se decidio aqui, no en una variable que alguien puso hace tres semanas.
    #
    # `None` = como siempre: lo que digan el entorno o el modo guardado. Lo usa
    # la terminal cuando no se le pasa bandera.
    usar_criterio = DGT.activa() if con_criterio is None else bool(con_criterio)
    res_con_criterio = usar_criterio

    res = {
        "pregunta": pregunta,
        "codigo": 1,
        "estado": None,
        "ejercicio": None,
        "preceptos": [],
        # DOS EJES, DOS LISTAS. `senales` es desacuerdo de fondo y mueve el
        # estado; `cobertura` es lo que no se ha podido mirar y no lo mueve.
        "senales": [],
        "cobertura": [],
        # Los limites permanentes del corpus, ya resumidos en una linea.
        "estructural": "",
        "intentos": 0,
        "reintentos": 0,
        "veredicto": None,
        "motivo": "",
        "analisis": None,
        "recuperado": [],
        # Marca de que la consulta NO llego a evaluarse por un fallo, no por
        # el criterio. El banco la usa para no dar por buena una prueba que en
        # realidad no se ha ejecutado.
        "fallo": None,          # None | "modelo" | "analisis"
        "traza": None,
        # Si el expediente ha quedado escrito en disco. Lo rellena `_fin`.
        "expediente": True,
        "aviso_expediente": "",
        # Que llego al redactor y que se quedo fuera en el corte.
        "preceptos_enviados": [],
        "preceptos_descartados": [],
        # El texto redactado. Se rellena SOLO si supera la verificacion: si
        # aqui hay algo, es porque se puede ensenar. Quien lo lea no tiene que
        # acordarse de mirar antes el codigo.
        "respuesta": "",
        # Si se pidio criterio y la copia local no tenia nada para esta
        # pregunta. Se dice; no se finge que se ha mirado.
        "sin_copia_local": "",
        # Que aporto el criterio: citas de la DGT y resoluciones que han
        # llegado a usarse, y cuantas se le pusieron delante.
        "aporte": {},
        "motor": motor.nombre,
        # Con que se ha hecho ESTA consulta. Viaja al resultado, a la traza y
        # a lo que se copia: quien pegue la respuesta en sus notas tiene que
        # poder saber si llevaba criterio administrativo o no.
        "con_criterio": False,
        # CON QUE COMUNIDAD SE HIZO. Viaja al resultado, a la traza y a lo que
        # se copia: una respuesta pegada en unas notas pierde la pantalla que
        # la explicaba, y sin este dato no se sabe si lleva o no autonomica.
        "comunidad": "",
        # Lo que se pierde por no saber la comunidad, si se pierde algo.
        "cobertura_territorial": "",
        # Tokens de esta consulta. Vacio si no se llego a llamar al modelo.
        "consumo": {},
    }

    # EL TECHO DURO EMPIEZA AQUI, Y SE REINICIA POR CONSULTA. El motor cuenta
    # llamadas y tiempo, y los cuenta POR CONSULTA: tanto el banco como la
    # ventana reutilizan el mismo motor para muchas seguidas. Sin esto, las
    # llamadas de las preguntas anteriores agotaban el tope de la siguiente.
    if hasattr(motor, "empezar_consulta"):
        motor.empezar_consulta()

    # UN FALLO DE DISCO NO TIRA LA CONSULTA, PERO NO PASA EN SILENCIO. Ver
    # `Traza`: el expediente se apunta como roto y sigue. Lo que no puede
    # pasar es ninguna de las dos cosas de antes: ni una traza de Python en la
    # terminal, ni enseñar una respuesta haciendo creer que quedo guardada.
    try:
        DIR_TRAZAS.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"\n[AVISO] no se ha podido preparar {DIR_TRAZAS}: {e}",
              file=sys.stderr)
    tr = Traza(DIR_TRAZAS, pregunta)
    res["traza"] = str(tr.dir)
    res["con_criterio"] = res_con_criterio
    res["comunidad"] = (comunidad or "").strip()

    titulo("CONSULTA FISCAL")
    print(f"pregunta : {pregunta}")
    print(f"corpus   : {len(ix.docs)} preceptos de "
          f"{len(ix.normas)} cuerpo(s): "
          + ", ".join(c.etiqueta for c in ix.normas.cuerpos.values()))
    print(f"motor    : {motor.nombre}", end="")
    if not motor.es_modelo_real:
        print("   <-- MOTOR DE ENSAYO: reglas fijas, NO es un modelo")
    else:
        print()
        print(f"modelos  : analisis {getattr(motor, 'modelo_analisis', '?')} | "
              f"redaccion {getattr(motor, 'modelo_redaccion', '?')}")
    print(f"traza    : {tr.dir}")

    # ---------------------------------------------------- PREGUNTA VACIA
    # Antes de esto, una pregunta vacia gastaba DOS llamadas al modelo para
    # acabar diciendo «no se ha podido determinar de que impuesto es la
    # pregunta», que ademas es falso: el problema no es el impuesto, es que no
    # hay pregunta. Se para aqui, sin gastar nada, y se dice lo que pasa.
    if not any(c.isalnum() for c in (pregunta or "")):
        apartado("PARADA: no hay pregunta")
        print("  No se ha escrito ninguna duda, o lo escrito no tiene ni una")
        print("  letra ni un numero. Escribe la duda en una o dos lineas.")
        res["codigo"] = 3
        res["motivo"] = ("no se ha escrito ninguna pregunta: describe la duda "
                         "en una o dos lineas")
        tr.cerrar({"estado": "SIN PREGUNTA", "caracteres": len(pregunta or "")})
        return _fin(res, tr)

    # ---------------------------------------------------- LONGITUD
    if len(pregunta or "") > TOPE_PREGUNTA:
        apartado("PARADA: la pregunta es demasiado larga")
        print(f"  Son {len(pregunta):,} caracteres y el tope son "
              f"{TOPE_PREGUNTA:,}.")
        print()
        print("  Esto suele pasar al pegar un requerimiento o un escrito")
        print("  entero. Resume la duda en unas lineas: que se pregunta y con")
        print("  que datos. Lo pegado entero no se puede contestar mejor, y")
        print("  cuesta mas.")
        res["codigo"] = 3
        res["motivo"] = (
            f"la pregunta tiene {len(pregunta):,} caracteres y el tope son "
            f"{TOPE_PREGUNTA:,}: resume la duda en unas lineas")
        tr.cerrar({"estado": "PREGUNTA DEMASIADO LARGA",
                   "caracteres": len(pregunta), "tope": TOPE_PREGUNTA})
        return _fin(res, tr)

    # ---------------------------------------------------- LLAMADA 1
    paso("Analizando la pregunta...")
    apartado("1. Analisis de la pregunta (llamada 1 al modelo)")
    analisis = None
    errores: list[str] = []
    for intento in range(1, 3):
        entrada = pregunta
        if errores:
            entrada = f"{pregunta}\n\n{AN.mensaje_reintento(errores)}"
        try:
            resp = motor.analizar(AN.SISTEMA, entrada, AN.esquema_de(ix.normas))
        except MOD.TopeAlcanzado as e:
            return _parada_por_tope(res, tr, motor, e, "analisis")
        except MOD.ErrorModelo as e:
            tr.paso("analisis", f"fallo del modelo: {e}")
            tr.cerrar({"estado": "ERROR", "detalle": str(e)})
            print(f"\n[FALLO DEL MODELO] {e}", file=sys.stderr)
            res["motivo"] = str(e)
            res["fallo"] = "modelo"
            return _fin(res, tr)

        tr.gasto(f"analisis {intento}", resp)
        tr.json(f"analisis_{intento}_crudo.json", resp.crudo)
        tr.escribir(f"analisis_{intento}_texto.json", resp.texto)

        analisis, errores = AN.validar(resp.datos, ix.normas)
        tr.paso("analisis", f"intento {intento}: "
                f"{'valido' if analisis else 'invalido'}", errores=errores)
        if analisis:
            print(f"   intento {intento}: JSON valido")
            break
        print(f"   intento {intento}: JSON RECHAZADO por las reglas:")
        for e in errores:
            print(f"     - {e}")

    if analisis is None:
        apartado("PARADA: el analizador no devuelve un JSON valido")
        print("  Se reintento una vez y volvio a fallar. No se sigue.")
        tr.cerrar({"estado": "ERROR", "detalle": "analisis invalido",
                   "errores": errores})
        res["motivo"] = "; ".join(errores)
        res["fallo"] = "analisis"
        return _fin(res, tr)

    res["analisis"] = {
        "impuesto": analisis.impuesto,
        "ejercicio_propuesto": analisis.ejercicio,
        "terminos_busqueda": analisis.terminos_busqueda,
        "articulos_sospechados": analisis.articulos_sospechados,
    }
    tr.json("analisis.json", res["analisis"])
    print(f"   impuesto : {analisis.impuesto}")
    print(f"   terminos : {', '.join(analisis.terminos_busqueda)}")
    if analisis.articulos_sospechados:
        print(f"   sospechas: art. {', '.join(analisis.articulos_sospechados)}")

    # ---------------------------------------------------- MATERIA
    entra, motivo_materia = EST.puerta_de_materia(analisis.impuesto, ix.normas)
    if not entra:
        apartado("2. Materia")
        print(f"   {motivo_materia}")
        return _sin_respaldo(res, tr, ejercicio_cli, [], None, motor,
                             motivo_materia)

    # ---------------------------------------------------- EJERCICIO
    ejercicio, explicacion = AN.resolver_ejercicio(pregunta, analisis, ejercicio_cli)
    tr.paso("ejercicio", explicacion, ejercicio=ejercicio)
    res["ejercicio"] = ejercicio

    if ejercicio is None:
        apartado("PARADA: falta el ejercicio del caso")
        print(f"  {explicacion}.")
        print()
        print("  No se supone. Un caso de 2023 contestado con la ley de hoy sale")
        print("  impecable y esta mal, y no lo nota nadie.")
        print()
        print(f'  Repite indicandolo:  python fase4.py consultar '
              f'"{pregunta[:40]}..." --ejercicio AAAA')
        tr.cerrar({"estado": "FALTA EJERCICIO", "detalle": explicacion})
        res["codigo"] = 3
        res["estado"] = "FALTA EJERCICIO"
        res["motivo"] = explicacion
        return _fin(res, tr)

    print(f"   ejercicio: {ejercicio}  ({explicacion})")

    # ---------------------------------------------------- BUSQUEDA (fase 2)
    paso("Buscando en la ley y el reglamento...")
    apartado("2. Busqueda en el corpus (fase 2, deterministica)")
    consulta = " ".join(analisis.terminos_busqueda)
    # SE BUSCA EN LA LEY DEL IMPUESTO DE LA PREGUNTA, MAS LAS GENERALES.
    #
    # El corpus ya sabia de que impuesto es cada cuerpo y el analizador ya
    # sabia de que impuesto es la pregunta; lo que faltaba era unirlos. Sin
    # unirlos, una pregunta de Patrimonio con vocabulario compartido -«escala
    # de gravamen», «vivienda habitual»- recuperaba CINCO DE CINCO articulos
    # del IRPF, y el verificador no lo salva: la cita es literal y correcta, lo
    # que falla es que no viene al caso, y eso no lo mira nadie.
    #
    # `admitidos_para` devuelve None si el impuesto no se ha podido determinar,
    # y entonces no se filtra: filtrar con un impuesto equivocado es peor que
    # no filtrar. La reserva mantiene viva la remision entre impuestos.
    resultados, huerfanos, reserva = recuperar(
        ix, grafo, consulta, analisis.impuesto,
        naturaleza=analisis.naturaleza, comunidad=comunidad)
    if ix.normas.admitidos_para(analisis.impuesto) is None:
        print("   busqueda: en TODO el corpus "
              f"(el impuesto quedo en «{analisis.impuesto}»: no se filtra)")
    elif analisis.naturaleza == AN.FONDO:
        print(f"   busqueda: SOLO en preceptos de {analisis.impuesto} "
              f"(duda de fondo; las generales entran por remision)")
    else:
        print(f"   busqueda: en preceptos de {analisis.impuesto} y en normas "
              f"generales (duda de {analisis.naturaleza})")
    if huerfanos:
        print(f"   sin resultados para: {', '.join(huerfanos)}")
    for i, r in enumerate(resultados, 1):
        print(f"   {i}. {r.doc.registro['referencia']:<28} "
              f"{r.doc.registro['rubrica'][:38]}")
    res["recuperado"] = [r.doc.registro["referencia"] for r in resultados]
    tr.json("recuperado.json", [
        {"referencia": r.doc.registro["referencia"], "clave": r.doc.clave,
         "puntuacion": round(r.puntuacion, 4), "url": r.doc.registro["url"]}
        for r in resultados
    ])
    tr.paso("busqueda", f"{len(resultados)} preceptos", consulta=consulta)

    pertinente, razon = EST.pertinencia(ix, consulta, resultados)
    tr.paso("pertinencia", razon, pertinente=pertinente)
    print(f"   pertinencia: {'OK' if pertinente else 'INSUFICIENTE'} — {razon}")

    registros = [r.doc.registro for r in resultados]
    if not pertinente:
        return _sin_respaldo(res, tr, ejercicio, registros, None, motor, razon)

    # ------------------------------------------- CORTE POR PERTINENCIA
    # El tope de arriba es un techo, no una cuota. Lo que decide que se manda
    # a redactar es si el precepto trata de lo que se pregunta, no su puesto.
    # LO QUE CUESTA NO SABER LA COMUNIDAD, DICHO EN VOZ ALTA.
    #
    # No bloquea -ver la nota de `interfaz`- pero no puede pasar en silencio:
    # sin comunidad la respuesta sale SOLO con normativa estatal, y en Renta o
    # Patrimonio eso puede ser la mitad de la respuesta.
    hay_autonomica = bool(ix.normas.comunidades())
    if hay_autonomica and impuesto_tiene_autonomica(ix, analisis.impuesto):
        com = (comunidad or "").strip()
        tenemos = sorted(ix.normas.comunidades())
        if not com:
            res["cobertura_territorial"] = (
                "esta respuesta NO incluye normativa autonomica: no se ha "
                "indicado la comunidad del contribuyente. Si el caso la tiene, "
                "indicala y vuelve a preguntar")
        elif com not in tenemos:
            res["cobertura_territorial"] = (
                f"esta respuesta lleva SOLO normativa estatal: de {com} no hay "
                f"normativa cargada. Ahora mismo solo esta "
                f"{', '.join(tenemos)}")

    seleccion = EST.seleccionar_material(ix, consulta, resultados, grafo,
                                         reserva=reserva,
                                         naturaleza=analisis.naturaleza)
    tr.json("seleccion.json", seleccion.a_json())
    tr.corte(seleccion.a_json())
    tr.paso("corte de material",
            f"{len(seleccion.elegidos)} de {len(resultados)} preceptos "
            f"(umbral {seleccion.umbral:.0%})",
            descartados=[d["referencia"] for d in seleccion.descartados])
    print(f"   corte por pertinencia (umbral "
          f"{seleccion.umbral:.0%} de la cobertura del 1o):")
    for d in seleccion.detalle:
        marca = "->" if d["decision"] == "enviado" else "  "
        print(f"   {marca} {d['referencia']:<28} cobertura {d['cobertura']:.2f} "
              f"({d['relativa']:.0%} del 1o)  {d['decision'].upper()}")
        if d["decision"] == "enviado" and "remite" in d["motivo"]:
            print(f"        ^ entra por remision: {d['motivo']}")
    print(f"   se mandan {len(seleccion.elegidos)} de {len(resultados)} "
          f"preceptos al redactor")
    registros = seleccion.elegidos
    res["preceptos_enviados"] = [r["referencia"] for r in registros]

    # SE APUNTA LO QUE VA AL REDACTOR Y NO TIENE CRITERIO.
    #
    # Aqui y no antes: es el momento en que se sabe QUE preceptos se van a usar
    # de verdad. Apuntar los recuperados y no los enviados llenaria la cola de
    # articulos que el corte descarto.
    #
    # NO BLOQUEA NI PUEDE BLOQUEAR. `cola.apuntar` no levanta nunca -lo dice su
    # docstring y lo prueba su suite-, no sale a la red y no espera a nadie:
    # escribe un JSON pequeño y vuelve. Cambiar la respuesta de un gestor por
    # una mejora de la despensa seria exactamente al reves de lo que hace falta.
    try:
        from agente_fiscal import cola as _COLA
        _cache_cob = DGT.CacheDGT()
        _con_criterio = {(p.cuerpo, p.numero.lower())
                         for c in _cache_cob.todas()
                         for p in c.preceptos(ix.normas) if p.comparable}
        _faltan = [(r.get("cuerpo_clave", ""),
                    r["referencia"].replace("Articulo ", "").strip())
                   for r in registros
                   if (r.get("cuerpo_clave", ""),
                       r["referencia"].replace("Articulo ", "").strip().lower())
                   not in _con_criterio]
        _COLA.apuntar([(c, a) for c, a in _faltan if c and a and a[0].isdigit()])
    except Exception:                            # noqa: BLE001
        pass
    res["preceptos_descartados"] = [d["referencia"] for d in seleccion.descartados]

    # ------------------------------------------------- CRITERIO (fase 9B)
    # Con la DGT apagada -que es lo normal hoy- todo lo de aqui queda en None
    # y el resto del camino es identico al de antes de la fase 9B.
    consultas_dgt = None
    lectura_dgt = None
    if usar_criterio:
        paso("Buscando criterio de la DGT en la copia local...")
        apartado("2 bis. Criterio de la DGT (solo de la copia local)")
        viva, motivo_fuente = DGT.fuente_viva()
        consultas_dgt = DGT.CacheDGT().buscar(pregunta)
        print(f"   consultas en la copia local que vienen al caso: "
              f"{len(consultas_dgt)}")
        for c in consultas_dgt:
            print(f"     · {c.numero} ({c.fecha or 's/f'}) {c.normativa[:40]}")
        if not viva:
            print(f"   [AVISO] la fuente de criterio no responde: {motivo_fuente}")
        res["dgt"] = {
            "activa": True,
            "fuente_viva": viva,
            "motivo_fuente": motivo_fuente,
            "consultas": [c.numero for c in consultas_dgt],
        }

    # ------------------------------------------------ DOCTRINA (fase 11)
    # AL TEAC SE LE PREGUNTA POR PRECEPTO, no por palabras: el buscador acaba
    # de decir que articulos sostienen la respuesta, asi que se le pregunta
    # directamente por esos. Nada de inventar terminos.
    criterios_teac = None
    lectura_teac = None
    if usar_criterio:
        paso("Buscando doctrina del TEAC en la copia local...")
        apartado("2 ter. Doctrina del TEAC (solo de la copia local)")
        pares = [(r.get("cuerpo_clave", ""),
                  r["referencia"].replace("Articulo ", "").lower())
                 for r in registros]
        # LA PREGUNTA VA TAMBIEN: sin ella el filtro solo mira el articulo, y
        # sobre el 80 eso mandaba doctrina del impuesto sobre la electricidad.
        criterios_teac, descartados_teac = TEAC.CacheTEAC().seleccionar(
            pares, ix.normas, consulta=pregunta, indice=ix)
        viva_t, motivo_t = TEAC.fuente_viva()
        print(f"   preceptos consultados: "
              f"{', '.join(n for _c, n in pares) or '(ninguno)'}")
        print(f"   criterios en la copia local que citan esos articulos: "
              f"{len(criterios_teac)}")
        for c in criterios_teac:
            print(f"     · {c.resolucion} ({c.fecha}) {c.unidad}"
                  + ("  [UNIFICACION DE CRITERIO]" if c.unifica_criterio else ""))
        if not viva_t:
            print(f"   [AVISO] la fuente de doctrina no responde: {motivo_t}")
        for cr, motivo in descartados_teac:
            print(f"     · descartado {cr.resolucion}: {motivo}")

        # SI SE PIDIO CRITERIO Y NO HAY NADA EN LA COPIA LOCAL, SE DICE.
        # Callarlo deja creer que se ha mirado y no habia nada, que es muy
        # distinto de que no se haya podido mirar. Alguien ha pulsado el boton
        # caro: como minimo tiene derecho a saber que no le ha comprado nada.
        if not consultas_dgt and not criterios_teac:
            aviso_sin_copia = (
                "se ha consultado con criterio administrativo, pero en la copia "
                "local NO hay ninguna consulta de la DGT ni resolucion sobre "
                f"{', '.join(sorted({n for _c, n in pares})) or 'estos articulos'}: "
                "esta respuesta se sostiene SOLO en la norma")
            print(f"   [AVISO] {aviso_sin_copia}")
            res["sin_copia_local"] = aviso_sin_copia
        res["teac"] = {
            "activa": True, "fuente_viva": viva_t, "motivo_fuente": motivo_t,
            "criterios": [c.resolucion for c in criterios_teac],
            "descartados": [{"resolucion": c.resolucion, "motivo": m}
                            for c, m in descartados_teac],
        }

    # ---------------------------------------------------- LLAMADA 2 + bucle
    apartado("3. Redaccion y verificacion (llamada 2, en bucle cerrado)")
    verificador = VF.Verificador(ix)
    motivos: list[str] = []
    informe = None
    borrador = ""
    intento = 0

    # EL RECORTE DEL CRITERIO, CONTADO ANTES DE MANDAR NADA. Se calcula una vez
    # -no cambia entre intentos- y se escribe en la traza: lo que se deja fuera
    # tiene que poder verse, no adivinarse.
    plan = RED.plan_de_criterio(registros, ejercicio, grafo, consultas_dgt,
                                criterios_teac, ix.normas)
    if plan.recortes:
        tr.json("recorte_criterio.json", plan.a_json())
        print(f"   material: ley {plan.ley} car. · criterio {plan.criterio} car. "
              f"({plan.proporcion_ley:.0%} ley)")
        for r in plan.recortes:
            print(f"     · {r.fuente}: {r.enviado}/{r.completo} car. "
                  f"({r.parrafos_enviados}/{r.parrafos} parrafos) — {r.motivo}")
        res["recorte"] = plan.a_json()

    for intento in range(1, MAX_INTENTOS + 1):
        material = RED.construir_material(
            pregunta, ejercicio, registros, grafo, motivos or None,
            consultas_dgt=consultas_dgt, criterios_teac=criterios_teac,
            normas=ix.normas, plan=plan,
        )
        tr.escribir(f"material_{intento}.txt", material)
        paso(f"Redactando con los articulos encontrados"
             f"{f' (intento {intento})' if intento > 1 else ''}...")
        try:
            resp = motor.redactar(RED.SISTEMA, material)
        except MOD.TopeAlcanzado as e:
            return _parada_por_tope(res, tr, motor, e, "redaccion")
        except MOD.ErrorModelo as e:
            tr.paso("redaccion", f"fallo del modelo: {e}")
            tr.cerrar({"estado": "ERROR", "detalle": str(e)})
            print(f"\n[FALLO DEL MODELO] {e}", file=sys.stderr)
            res["motivo"] = str(e)
            res["fallo"] = "modelo"
            return _fin(res, tr)

        tr.gasto(f"redaccion {intento}", resp)
        tr.json(f"redaccion_{intento}_crudo.json", resp.crudo)
        borrador = resp.texto
        tr.escribir(f"borrador_{intento}.txt", borrador)

        # LA RESPUESTA HA LLEGADO CORTADA. La API lo dice: `stop_reason` es
        # «max_tokens» cuando el modelo se ha quedado sin sitio a mitad de
        # frase. Sin mirarlo, el trozo pasaba al verificador, que lo tumbaba
        # -bien tumbado, porque acaba con una comilla abierta- y la consulta
        # salia como NO ENCONTRADO con el motivo «el texto no contiene ninguna
        # cita con fragmento literal». Es cierto y apunta al sitio equivocado:
        # quien lo lee entiende que la ley no dice nada de su caso, cuando lo
        # que ha pasado es que la respuesta se corto por la mitad.
        #
        # No se reintenta: saldria cortada otra vez por el mismo sitio.
        if (resp.crudo or {}).get("stop_reason") == "max_tokens":
            apartado("PARADA: la respuesta del modelo llego cortada")
            print("  El modelo se quedo sin espacio y la respuesta se corto a")
            print("  mitad. No se enseña un trozo: media respuesta de fiscal")
            print("  es peor que ninguna, porque lo que falta suele ser la")
            print("  excepcion.")
            tr.paso("redaccion", f"intento {intento}: cortada por max_tokens")
            tr.cerrar({"estado": "RESPUESTA CORTADA", "intento": intento})
            res["motivo"] = ("la respuesta del modelo llego cortada por su "
                             "longitud: no se enseña media respuesta")
            res["fallo"] = "modelo"
            return _fin(res, tr)

        paso("Comprobando cada cita contra el texto oficial...")
        informe = verificador.verificar_texto(borrador, ejercicio, exigir_norma=True)
        tr.json(f"verificacion_{intento}.json", informe.a_json())

        r = informe.resumen
        print(f"   intento {intento}: {r['total']} citas -> "
              f"{r['verificadas']} verificadas, {r['no_verificadas']} no verificadas, "
              f"{r['no_verificables']} no verificables  =>  {informe.veredicto}")
        tr.paso("verificacion", f"intento {intento}: {informe.veredicto}", resumen=r)

        if informe.veredicto == VF.ACEPTADO:
            break

        motivos = [
            f"cita {d.n} ({d.referencia_citada or 'sin referencia'}): {d.motivo}"
            for d in informe.dictamenes if d.estado != VF.VERIFICADA
        ] or [informe.motivo_global]
        for m in motivos:
            print(f"      - {m[:96]}")
        if intento < MAX_INTENTOS:
            print("   se reintenta UNA vez, devolviendole los motivos exactos")

    res["intentos"] = intento
    res["reintentos"] = max(0, intento - 1)
    res["veredicto"] = informe.veredicto if informe else None

    # ---------------------------------------------------- ESTADO (reglas)
    paso("Calculando el estado de la respuesta...")
    apartado("4. Estado (lo calcula el codigo, no el modelo)")
    if usar_criterio:
        # Solo cuenta el criterio que HA PASADO el verificador. Una consulta
        # citada y no verificada no puede mover el estado: seria dar peso a
        # algo que no hemos podido comprobar.
        citadas = []
        if informe is not None:
            numeros = {d.referencia_citada for d in informe.dictamenes
                       if d.estado == VF.VERIFICADA and d.norma == "dgt"}
            cache_dgt = DGT.CacheDGT()
            for bruto in numeros:
                m = DGT.RE_NUM_CONSULTA.search(bruto) or DGT.RE_NUM_SUELTO.search(bruto)
                if m:
                    c = cache_dgt.leer(m.group("num"))
                    # SOLO LAS QUE TIENEN TEXTO EN EL MATERIAL. Hoy no puede
                    # colarse otra -para citarla el redactor tendria que
                    # haberla visto- pero la garantia no se deja a que eso siga
                    # siendo verdad: una señal que nombra una consulta cuyo
                    # texto no esta manda a leer algo que no se le ha dado.
                    if c and c.numero in plan.enviadas:
                        citadas.append(c)
        # Las CLAVES, no las referencias: una clave lleva dentro de que norma
        # es el articulo, y comparar por numero suelto es el fallo que la fase
        # 6 ya nos costo una vez.
        claves_verificadas = [d.clave for d in (informe.dictamenes if informe
                                                else [])
                              if d.estado == VF.VERIFICADA and d.clave]
        viva, motivo_fuente = DGT.fuente_viva()
        lectura_dgt = DGT.leer_criterio(citadas, claves_verificadas, ix.normas)
        lectura_dgt.fuente_caida = not viva
        lectura_dgt.motivo_fuente = motivo_fuente

    if usar_criterio:
        # Solo cuenta la doctrina que se ha llegado a citar y verificar, y las
        # consultas de la DGT que esta respuesta cita: la señal fuerte es el
        # cruce de las dos cosas.
        citados_teac = []
        if informe is not None:
            cache_t = TEAC.CacheTEAC()
            for d in informe.dictamenes:
                if d.estado == VF.VERIFICADA and d.norma == "teac":
                    m = TEAC.RE_ID_CRITERIO.search(d.referencia_citada or "")
                    c = cache_t.leer(m.group("id")) if m else None
                    if c:
                        citados_teac.append(c)
        if not citados_teac:
            citados_teac = criterios_teac or []
        nums_dgt = []
        if informe is not None:
            from agente_fiscal import dgt as _D
            for d in informe.dictamenes:
                if d.estado == VF.VERIFICADA and d.norma == "dgt":
                    m = (_D.RE_NUM_CONSULTA.search(d.referencia_citada or "")
                         or _D.RE_NUM_SUELTO.search(d.referencia_citada or ""))
                    if m:
                        nums_dgt.append(m.group("num"))
        pares_v = []
        for c in (claves_verificadas if 'claves_verificadas' in dir() else []):
            if c.count("#") >= 2:
                norma_id, indice, referencia = c.split("#", 2)
                pares_v.append((f"{norma_id}#{indice}",
                                referencia.replace("articulo ", "").strip().lower()))
        viva_t, motivo_t = TEAC.fuente_viva()
        lectura_teac = TEAC.leer_doctrina(citados_teac, pares_v, nums_dgt,
                                          ix.normas, descartados_teac)
        lectura_teac.fuente_caida = not viva_t
        lectura_teac.motivo_fuente = motivo_t

    dictamen = EST.calcular(informe, ix, grafo, ejercicio, len(registros),
                            lectura_dgt=lectura_dgt, lectura_teac=lectura_teac)
    tr.json("estado.json", dictamen.a_json())
    print(f"   {dictamen.estado}")
    for m in dictamen.motivos:
        print(f"     · {m}")

    res["estado"] = dictamen.estado
    res["senales"] = dictamen.senales
    res["cobertura"] = dictamen.cobertura
    if res.get("sin_copia_local"):
        res["cobertura"] = [res["sin_copia_local"]] + list(dictamen.cobertura)
    res["estructural"] = dictamen.linea_estructural
    res["preceptos"] = dictamen.preceptos
    # QUE APORTO EL CRITERIO, en numeros. La ventana lo enseña para que la
    # diferencia entre los dos botones se vea sin leerse las dos respuestas
    # enteras y compararlas a ojo.
    if res["con_criterio"] and informe is not None:
        # DE QUE MATERIA ERA LO QUE SE PUSO DELANTE. Sin esto la ventana no
        # puede distinguir «habia criterio de esta materia y no sostiene la
        # respuesta» de «lo que habia era de otro impuesto», y las dos frases
        # dicen cosas muy distintas a quien las lee.
        cache_dgt = DGT.CacheDGT()
        en_material = list((res.get("dgt") or {}).get("consultas") or [])
        misma, otra = [], []
        for num in en_material:
            c = cache_dgt.leer(num)
            suyos = DGT.impuestos_de(c, ix.normas) if c is not None else set()
            (misma if analisis.impuesto in suyos else otra).append(num)
        res["aporte"] = {
            "consultas_dgt": sorted({d.referencia_citada for d in informe.dictamenes
                                     if d.estado == VF.VERIFICADA and d.norma == "dgt"}),
            "resoluciones": sorted({d.referencia_corpus for d in informe.dictamenes
                                    if d.estado == VF.VERIFICADA and d.norma == "teac"}),
            "consultas_en_material": en_material,
            "resoluciones_en_material": list((res.get("teac") or {}).get("criterios") or []),
            "impuesto": analisis.impuesto,
            "en_material_misma_materia": misma,
            "en_material_otra_materia": otra,
        }

    if dictamen.estado == EST.NO_ENCONTRADO:
        return _sin_respaldo(res, tr, ejercicio, registros, informe, motor,
                             "; ".join(dictamen.motivos))

    # ---------------------------------------------------- RESPUESTA
    titulo(f"RESPUESTA  ·  {dictamen.estado}  ·  ejercicio {ejercicio}")
    # DOS BLOQUES, PORQUE SON DOS EJES. Arriba lo que enfrenta textos entre si
    # -y por eso mueve el estado-; debajo lo que no se ha podido mirar, que se
    # enseña igual de claro y no lo mueve. Ver la cabecera de `estado.py`.
    if dictamen.senales:
        print("DESACUERDO (por esto el criterio no se da por cerrado):")
        for s in dictamen.senales:
            print(f"  !! {s}")
        print("-" * ANCHO)
    # Y la cobertura, partida por lo que se puede HACER con ella: lo accionable
    # entero y arriba; los limites permanentes del corpus, en una linea al
    # final. Un aviso que sale siempre no es un aviso, es decoracion.
    if dictamen.cobertura:
        print("LO QUE NO SE HA PODIDO MIRAR (no cambia el estado, pero lee):")
        for s in dictamen.cobertura:
            print(f"  ·· {s}")
    if dictamen.linea_estructural:
        print(f"  (limite del corpus: {dictamen.linea_estructural})")
    if dictamen.cobertura or dictamen.linea_estructural:
        print("-" * ANCHO)
    res["respuesta"] = borrador.strip()
    print(borrador.strip())
    print("\n" + "-" * ANCHO)
    print(f"Citas verificadas una a una contra el corpus: "
          f"{informe.resumen['verificadas']}/{informe.resumen['total']}")
    print(f"Preceptos que la sostienen: {', '.join(dictamen.preceptos)}")
    print(f"Traza completa: {tr.dir}")
    if not motor.es_modelo_real:
        print("AVISO: redactado por el MOTOR DE ENSAYO, no por un modelo.")

    linea_consumo(tr)
    res["consumo"] = tr.totales()

    tr.json("topes.json", motor.a_json_topes()
            if hasattr(motor, "a_json_topes") else {})
    tr.cerrar({
        "estado": dictamen.estado, "ejercicio": ejercicio,
        "llamadas_al_modelo": getattr(motor, "llamadas", 0),
        "veredicto": informe.veredicto, "intentos": intento,
        "motor": motor.nombre, "con_criterio": res["con_criterio"],
        "modelo": getattr(motor, "modelo", "(ninguno)"),
        "preceptos": dictamen.preceptos, "senales": dictamen.senales,
        "avisos_de_cobertura": dictamen.cobertura,
        "limites_del_corpus": dictamen.linea_estructural,
        # QUE CRITERIO SE LE PUSO DELANTE. Se calculaba, llegaba a la ventana
        # y NO quedaba en el expediente: dentro de seis meses, discutiendo una
        # respuesta, no habria forma de saber que se miro. Es el requisito de
        # la fase 4 -que todo lo que decide una respuesta quede escrito- y no
        # se estaba cumpliendo.
        "aporte": res.get("aporte") or {},
        "dgt": res.get("dgt") or {},
        "teac": res.get("teac") or {},
        "recorte": res.get("recorte") or {},
    })
    res["codigo"] = 0
    return _fin(res, tr)


def _parada_por_tope(res, tr, motor, error, donde: str) -> dict:
    """Se ha llegado al techo. NO es un fallo del modelo, y no se cuenta igual.

    La diferencia importa: «el modelo fallo» manda a mirar la red o la cuenta;
    «se llego al tope» manda a mirar por que hicieron falta tantas llamadas.
    Meterlos en el mismo saco es como se pierde un bucle durante meses.
    """
    topes = motor.a_json_topes() if hasattr(motor, "a_json_topes") else {}
    tr.json("topes.json", topes)
    tr.paso("tope", f"parada en {donde}: {topes.get('motivo_parada', '')}")
    tr.cerrar({"estado": "PARADA POR TOPE", "detalle": str(error), **topes})
    titulo("PARADA POR TOPE")
    print(str(error))
    print()
    print(f"Llamadas hechas: {topes.get('llamadas', '?')} de "
          f"{topes.get('tope_llamadas', '?')} · "
          f"{topes.get('segundos', '?')} s de {topes.get('tope_segundos', '?')}")
    print("No se muestra ninguna respuesta: no ha llegado a completarse.")
    print(f"Traza completa: {tr.dir}")
    res["motivo"] = str(error)
    res["fallo"] = "tope"
    res["topes"] = topes
    res["codigo"] = 1
    return _fin(res, tr)


def _sin_respaldo(res, tr, ejercicio, registros, informe, motor, motivo) -> dict:
    """NO ENCONTRADO. Se ensena lo recuperado en crudo, nunca el borrador."""
    titulo(f"NO ENCONTRADO  ·  ejercicio {ejercicio}")
    print(f"Motivo: {motivo}")
    print()
    print("No se muestra ningun texto redactado: no ha superado la verificacion.")
    print("Ni con aviso, ni en gris, ni a titulo orientativo.")

    if registros:
        apartado(f"Lo que SI se recupero, en crudo, para leerlo a mano "
                 f"({len(registros)} preceptos)")
        for reg in registros:
            print(f"\n· {reg['referencia']} — {reg['rubrica']}")
            print(f"  {reg['url']}")
            v = V.version_aplicable(reg, V.limites(ejercicio)[1]) if ejercicio else None
            texto = (v or {}).get("texto") or reg["texto_vigente"]
            for linea in [l for l in texto.split("\n")[1:] if l.strip()][:3]:
                print(f"    | {linea[:ANCHO - 8]}")
    else:
        print("\nNo se recupero ningun precepto. En el corpus solo hay normativa")
        print("del IVA: ni DGT, ni TEAC, ni jurisprudencia.")

    print(f"\nTraza completa: {tr.dir}")
    linea_consumo(tr)
    res["consumo"] = tr.totales()
    tr.cerrar({
        "estado": EST.NO_ENCONTRADO, "ejercicio": ejercicio,
        "veredicto": informe.veredicto if informe else "(sin redaccion)",
        "motor": motor.nombre, "con_criterio": res["con_criterio"],
        "modelo": getattr(motor, "modelo", "(ninguno)"),
        "motivo": motivo,
    })
    res["codigo"] = 2
    res["estado"] = EST.NO_ENCONTRADO
    res["motivo"] = motivo
    return _fin(res, tr)


# ---------------------------------------------------------------- arranque


def preparar_motor(
    nombre: str,
    silencioso: bool = False,
    modelo_analisis: str = MOD.MODELO_ANALISIS,
    modelo_redaccion: str = MOD.MODELO_REDACCION,
):
    """Crea el motor y, si es el real, comprueba la credencial ANTES de nada.

    Devuelve (motor, mensaje_error). Si hay error, motor es None y el mensaje
    es una frase, no una traza. Se comprueban LOS DOS modelos: tener acceso al
    que redacta no dice nada del que analiza.
    """
    if nombre == "anthropic":
        ok, msg = MOD.comprobar_credencial(modelo_analisis, modelo_redaccion)
        if not ok:
            return None, msg
        if not silencioso:
            print(f"[arranque] {msg}")
    try:
        return MOD.crear_motor(nombre, modelo_analisis, modelo_redaccion), ""
    except MOD.ErrorModelo as e:
        return None, str(e)


def modo_credencial(args) -> int:
    titulo("COMPROBACION DE ARRANQUE")
    ok, msg = MOD.comprobar_credencial()
    print(("[ OK ] " if ok else "[FALLA] ") + msg)
    if not ok:
        print()
        print("Como dejarlo listo (tres ordenes):")
        print("  1) python3 -m venv .venv && .venv/bin/pip install anthropic")
        print("  2) cp .env.ejemplo .env   y pega la clave tras el '=' ")
        print("     (se saca en https://platform.claude.com -> API keys)")
        print("  3) .venv/bin/python fase4.py credencial")
        print()
        print("No hace falta ningun export: el .env se lee solo. Si aun asi")
        print("exportas ANTHROPIC_API_KEY, esa variable manda sobre el .env.")
    return 0 if ok else 1


def modo_esquema(args) -> int:
    """Comprueba el esquema del analizador contra la API. Cuesta 1 llamada."""
    titulo("COMPROBACION DEL ESQUEMA DEL ANALIZADOR")
    ok, msg = MOD.comprobar_credencial()
    if not ok:
        print(f"[FALLA] {msg}", file=sys.stderr)
        return 1
    # El esquema con los codigos del corpus DE VERDAD dentro: es el que va a
    # viajar a la API, asi que es el que hay que comprobar.
    ix, _grafo = cargar_corpus()
    ok, msg = MOD.comprobar_esquema(AN.esquema_de(ix.normas))
    print(("[ OK ] " if ok else "[FALLA] ") + msg)
    if not ok:
        print()
        print("Los structured outputs NO admiten: maxItems, minItems (salvo 0/1),")
        print("minLength, maxLength, minimum, maximum, multipleOf, pattern,")
        print("type como lista (['integer','null'] -> usar anyOf), ni")
        print("additionalProperties distinto de false.")
        print("Esas restricciones se comprueban en codigo, en analizador.validar().")
    return 0 if ok else 1


def _exigir_coherencia_o_parar() -> int:
    """El mismo corte que en la ventana. Ver `interfaz.main`."""
    from agente_fiscal import configuracion as CONF
    try:
        hecho = CONF.asegurar()
        if hecho:
            print(f"  {hecho}")
    except Exception as e:  # noqa: BLE001
        print(f"  No se ha podido rehacer la hoja de instrucciones: {e}")
    try:
        CONF.exigir_coherencia()
    except CONF.Descoordinado as e:
        titulo("LA HERRAMIENTA ESTA A MEDIO CONFIGURAR")
        for l in e.en_cristiano():
            print(l)
        return 1
    return 0


def modo_consultar(args) -> int:
    if _exigir_coherencia_o_parar():
        return 1
    motor, err = preparar_motor(
        args.motor,
        modelo_analisis=args.modelo_analisis,
        modelo_redaccion=args.modelo_redaccion,
    )
    if motor is None:
        print(f"\n[FALLO DE ARRANQUE] {err}", file=sys.stderr)
        return 1
    ix, grafo = cargar_corpus()
    res = consultar(args.pregunta, args.ejercicio, motor, ix, grafo,
                    con_criterio=getattr(args, "con_criterio", None))
    if motor.es_modelo_real:
        print(f"Llamadas al modelo en esta consulta: {motor.llamadas}")
    return res["codigo"]


# ------------------------------------------------------------ comprobaciones


def modo_comprobaciones(args) -> int:
    """Las cuatro comprobaciones exigidas a la fase 4 (con motor de ensayo)."""
    import contextlib
    import io

    titulo("COMPROBACIONES DE LA FASE 4")
    print("Se ejecutan con el MOTOR DE ENSAYO (reglas fijas, sin modelo): lo que")
    print("se comprueba es el andamiaje deterministico, que es donde viven las")
    print("reglas del sistema. La calidad de la redaccion no se prueba aqui.\n")

    ix, grafo = cargar_corpus()

    def ejecutar(pregunta, ejercicio=None, impuesto=None):
        """Una consulta con el motor de ensayo.

        `impuesto` fuerza lo que diria el analizador. Hace falta porque el
        motor de ensayo no analiza: dice «IVA» si la pregunta lleva la palabra
        y «desconocido» en cualquier otro caso. Sin forzarlo no se puede probar
        la puerta de materia, que es una regla del sistema y no del modelo.
        """
        motor = MOD.crear_motor("ensayo")
        if impuesto:
            analizar = motor.analizar

            def analizar_con_impuesto(sistema, preg, esquema):
                r = analizar(sistema, preg, esquema)
                r.datos["impuesto"] = impuesto
                return r

            motor.analizar = analizar_con_impuesto
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            res = consultar(pregunta, ejercicio, motor, ix, grafo)
        return res, buf.getvalue()

    casos = []
    r, s = ejecutar("puedo deducir el IVA de un coche de empresa")
    casos.append(("pregunta sin ejercicio -> PARA y lo pregunta",
                  r["codigo"] == 3, f"codigo {r['codigo']}"))

    r, s = ejecutar("deduccion del IVA de un turismo en el ejercicio 2023")
    casos.append(("el ano escrito en la pregunta se acepta sin --ejercicio",
                  r["ejercicio"] == 2023, f"ejercicio {r['ejercicio']}"))

    # LA PUERTA DE MATERIA. Esta comprobacion usaba una pregunta de IRPF como
    # «tema fuera del corpus», y desde que Renta esta ingerida ya no lo es: la
    # contesta, que es justo lo que se buscaba al ingerirla. Se cambia por un
    # impuesto que sigue fuera.
    #
    # Y se le fuerza el impuesto al analizador a proposito. Sin forzarlo, esta
    # comprobacion era mas floja de lo que parecia: el motor de ensayo dice
    # «desconocido» a todo lo que no lleve la palabra IVA, la puerta deja pasar
    # «desconocido», y lo unico que frenaba era el corte por pertinencia.
    # Medido: antes de Renta, «tipo de gravamen del Impuesto sobre Sociedades»
    # YA salia CRITERIO CLARO con el motor de ensayo. Lo que la paraba de
    # verdad era el caso concreto del IRPF, no la regla.
    # EL IMPUESTO DE FUERA SE PREGUNTA AL CORPUS, NO SE ESCRIBE.
    #
    # Esta comprobacion ha caducado TRES veces por el mismo motivo: se escribia
    # a mano un impuesto «de fuera» -primero IRPF, luego IS- y a la ingesta
    # siguiente estaba dentro. La comprobacion se ponia roja sin que nada se
    # hubiera roto, que es la peor clase de alarma: la que se aprende a ignorar.
    #
    # Ahora se coge el primero del catalogo del analizador que el corpus NO
    # cubra. El dia que se ingiera ITP-AJD, esta linea buscara otro sola.
    fuera = next((x for x in AN.codigos(ix.normas)
                  if x not in AN.SIN_CLASIFICAR
                  and x not in ix.normas.impuestos()), None)
    if fuera is None:
        casos.append(("tema fuera del corpus -> NO ENCONTRADO", True,
                      "el corpus cubre TODOS los impuestos del catalogo: "
                      "no queda ninguno con el que probar la puerta"))
    else:
        r, s = ejecutar(f"una duda de {fuera}", 2023, impuesto=fuera)
        casos.append((f"tema fuera del corpus ({fuera}) -> NO ENCONTRADO",
                      r["codigo"] == 2,
                      f"codigo {r['codigo']}, estado {r['estado']}"))

    r, s = ejecutar('deduccion IVA turismo. FRAGMENTO SOSPECHOSO: el porcentaje '
                    'de deduccion aplicable a los turismos sera siempre del 100 '
                    'por cien', 2023)
    casos.append(("cita falsa inyectada -> NO ENCONTRADO, sin mostrar texto",
                  r["codigo"] == 2 and "RESPUESTA  ·" not in s,
                  f"codigo {r['codigo']}"))

    r1, _ = ejecutar("deduccion del IVA de un turismo", 2023)
    r2, _ = ejecutar("deduccion del IVA de un turismo", 2023)
    casos.append(("misma pregunta dos veces -> mismo estado",
                  r1["estado"] == r2["estado"] and r1["estado"] is not None,
                  f"{r1['estado']!r} vs {r2['estado']!r}"))

    fallos = 0
    for nombre, ok, detalle in casos:
        print(f"{'[ OK ]' if ok else '[FALLA]'} {nombre}")
        print(f"         {detalle}")
        fallos += 0 if ok else 1

    print("\n" + "=" * ANCHO)
    print(f"COMPROBACIONES EN {'ROJO' if fallos else 'VERDE'}: "
          f"{len(casos) - fallos}/{len(casos)} dan lo esperado")
    print("=" * ANCHO)
    return 2 if fallos else 0


# ------------------------------------------------------------------------ cli


def main(argv: list[str]) -> int:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(
        description="Fase 4: analizador y redaccion con verificacion obligatoria.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = ap.add_subparsers(dest="modo", required=True)

    c = sub.add_parser("consultar", help="resuelve una duda fiscal")
    c.add_argument("pregunta")
    # SIN `type=int`: el año lo valida `analizador.leer_ejercicio`, que es
    # quien tambien lo valida cuando viene de la ventana. Con `type=int` aqui,
    # «--ejercicio 23» pasaba por la terminal como el ano 23 y «abc» salia con
    # el mensaje de argparse en ingles; ahora las dos entradas dan la misma
    # explicacion, que es el objetivo: una sola regla del año, un solo mensaje.
    c.add_argument("--ejercicio", default=None)
    c.add_argument("--motor", choices=["anthropic", "ensayo"], default="anthropic")
    # EL MODO ES DE LA CONSULTA. Sin bandera se comporta como siempre (lo que
    # digan el entorno o el modo guardado).
    criterio = c.add_mutually_exclusive_group()
    criterio.add_argument("--con-criterio", dest="con_criterio",
                          action="store_true", default=None,
                          help="anade criterio de la DGT y resoluciones")
    criterio.add_argument("--solo-ley", dest="con_criterio",
                          action="store_false",
                          help="solo la ley y sus reglamentos")
    # El modelo de cada paso se elige aqui, no se cablea en el codigo.
    c.add_argument("--modelo-analisis", default=MOD.MODELO_ANALISIS,
                   dest="modelo_analisis",
                   help=f"modelo de la llamada 1 (por defecto {MOD.MODELO_ANALISIS})")
    c.add_argument("--modelo-redaccion", default=MOD.MODELO_REDACCION,
                   dest="modelo_redaccion",
                   help=f"modelo de la llamada 2 (por defecto {MOD.MODELO_REDACCION})")

    sub.add_parser("credencial", help="comprueba SDK y credencial, y para")
    sub.add_parser("esquema", help="comprueba que la API acepta el esquema (1 llamada)")
    p = sub.add_parser("comprobaciones", help="bateria de la fase 4")
    p.add_argument("--motor", choices=["ensayo"], default="ensayo")

    args = ap.parse_args(argv)

    # EL AÑO SE VALIDA EN UN SOLO SITIO. Aqui habia una segunda comprobacion,
    # de rango y nada mas, escrita aparte de la de `leer_ejercicio`. Dos
    # caminos para una regla es como se descuadran: uno se arregla y el otro
    # no. Este llama al mismo, y por eso da el mismo mensaje que la ventana.
    ejercicio = getattr(args, "ejercicio", None)
    if ejercicio is not None:
        año, motivo = AN.leer_ejercicio(ejercicio)
        if año is None:
            print(f"[FALLO] {motivo}", file=sys.stderr)
            return 1
        args.ejercicio = año

    try:
        if args.modo == "consultar":
            return modo_consultar(args)
        if args.modo == "credencial":
            return modo_credencial(args)
        if args.modo == "esquema":
            return modo_esquema(args)
        return modo_comprobaciones(args)
    except ErrorCorpus as e:
        print(f"\n[FALLO DE CORPUS] {e}", file=sys.stderr)
        return 1
    except MOD.ErrorModelo as e:
        print(f"\n[FALLO DEL MODELO] {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrumpido.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
