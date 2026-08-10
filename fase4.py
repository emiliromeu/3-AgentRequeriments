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
from pathlib import Path

from agente_fiscal import analizador as AN
from agente_fiscal import dgt as DGT
from agente_fiscal import estado as EST
from agente_fiscal import modelo as MOD
from agente_fiscal import redactor as RED
from agente_fiscal import referencias as R
from agente_fiscal import teac as TEAC
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

TOPE_MATERIAL = 5   # cuantos preceptos ve el redactor. Mas no es mejor: diluye.
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


# ------------------------------------------------------------------ consultar


def consultar(pregunta: str, ejercicio_cli, motor, ix, grafo,
              progreso=None) -> dict:
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
        # Que llego al redactor y que se quedo fuera en el corte.
        "preceptos_enviados": [],
        "preceptos_descartados": [],
        # El texto redactado. Se rellena SOLO si supera la verificacion: si
        # aqui hay algo, es porque se puede ensenar. Quien lo lea no tiene que
        # acordarse de mirar antes el codigo.
        "respuesta": "",
        "motor": motor.nombre,
        # Tokens de esta consulta. Vacio si no se llego a llamar al modelo.
        "consumo": {},
    }

    # EL TECHO DURO EMPIEZA AQUI. El motor cuenta llamadas y tiempo por
    # consulta; el banco reutiliza el mismo motor para varias seguidas, asi que
    # sin esto la quinta se pasaria de tiempo por culpa de las cuatro de antes.
    if hasattr(motor, "reiniciar_reloj"):
        motor.reiniciar_reloj()

    DIR_TRAZAS.mkdir(parents=True, exist_ok=True)
    tr = Traza(DIR_TRAZAS, pregunta)
    res["traza"] = str(tr.dir)

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
            resp = motor.analizar(AN.SISTEMA, entrada, AN.ESQUEMA)
        except MOD.TopeAlcanzado as e:
            return _parada_por_tope(res, tr, motor, e, "analisis")
        except MOD.ErrorModelo as e:
            tr.paso("analisis", f"fallo del modelo: {e}")
            tr.cerrar({"estado": "ERROR", "detalle": str(e)})
            print(f"\n[FALLO DEL MODELO] {e}", file=sys.stderr)
            res["motivo"] = str(e)
            res["fallo"] = "modelo"
            return res

        tr.gasto(f"analisis {intento}", resp)
        tr.json(f"analisis_{intento}_crudo.json", resp.crudo)
        tr.escribir(f"analisis_{intento}_texto.json", resp.texto)

        analisis, errores = AN.validar(resp.datos)
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
        return res

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
    if analisis.impuesto not in EST.IMPUESTOS_EN_CORPUS:
        apartado("2. Materia")
        print(f"   la duda es de {analisis.impuesto} y el corpus solo cubre el IVA")
        return _sin_respaldo(
            res, tr, ejercicio_cli, [], None, motor,
            f"la consulta es de {analisis.impuesto} y este corpus solo cubre el IVA",
        )

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
        return res

    print(f"   ejercicio: {ejercicio}  ({explicacion})")

    # ---------------------------------------------------- BUSQUEDA (fase 2)
    paso("Buscando en la ley y el reglamento...")
    apartado("2. Busqueda en el corpus (fase 2, deterministica)")
    consulta = " ".join(analisis.terminos_busqueda)
    resultados, huerfanos = ix.buscar(consulta, tope=TOPE_MATERIAL)
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
    seleccion = EST.seleccionar_material(ix, consulta, resultados, grafo)
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
    res["preceptos_descartados"] = [d["referencia"] for d in seleccion.descartados]

    # ------------------------------------------------- CRITERIO (fase 9B)
    # Con la DGT apagada -que es lo normal hoy- todo lo de aqui queda en None
    # y el resto del camino es identico al de antes de la fase 9B.
    consultas_dgt = None
    lectura_dgt = None
    if DGT.activa():
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
    if TEAC.activa():
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
            return res

        tr.gasto(f"redaccion {intento}", resp)
        tr.json(f"redaccion_{intento}_crudo.json", resp.crudo)
        borrador = resp.texto
        tr.escribir(f"borrador_{intento}.txt", borrador)

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
    if DGT.activa():
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

    if TEAC.activa():
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
    res["estructural"] = dictamen.linea_estructural
    res["preceptos"] = dictamen.preceptos

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
        "motor": motor.nombre, "modelo": getattr(motor, "modelo", "(ninguno)"),
        "preceptos": dictamen.preceptos, "senales": dictamen.senales,
        "avisos_de_cobertura": dictamen.cobertura,
        "limites_del_corpus": dictamen.linea_estructural,
    })
    res["codigo"] = 0
    return res


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
    return res


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
        "motor": motor.nombre, "modelo": getattr(motor, "modelo", "(ninguno)"),
        "motivo": motivo,
    })
    res["codigo"] = 2
    res["estado"] = EST.NO_ENCONTRADO
    res["motivo"] = motivo
    return res


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
    ok, msg = MOD.comprobar_esquema(AN.ESQUEMA)
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
    res = consultar(args.pregunta, args.ejercicio, motor, ix, grafo)
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

    def ejecutar(pregunta, ejercicio=None):
        motor = MOD.crear_motor("ensayo")
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

    r, s = ejecutar("retencion del IRPF de un alquiler de vivienda habitual", 2023)
    casos.append(("tema fuera de la Ley del IVA -> NO ENCONTRADO",
                  r["codigo"] == 2, f"codigo {r['codigo']}, estado {r['estado']}"))

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
    c.add_argument("--ejercicio", type=int, default=None)
    c.add_argument("--motor", choices=["anthropic", "ensayo"], default="anthropic")
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

    ejercicio = getattr(args, "ejercicio", None)
    if ejercicio is not None and not (
        AN.EJERCICIO_MINIMO <= ejercicio <= AN.EJERCICIO_MAXIMO
    ):
        print(f"[FALLO] ejercicio fuera de rango: {ejercicio}. "
              f"La Ley del IVA esta en vigor desde {AN.EJERCICIO_MINIMO}.",
              file=sys.stderr)
        return 1

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
