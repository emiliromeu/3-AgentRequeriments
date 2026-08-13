#!/usr/bin/env python3
"""BANCO DE PRUEBAS del agente fiscal.

    python banco.py                  # SOLO el bloque 1: cero llamadas, cero gasto
    python banco.py --con-modelo     # ademas los bloques 2-5, contra el modelo
    python banco.py --bloques 1,5    # los que se pidan (2-5 exigen --con-modelo)

Por defecto el banco NO gasta: corre el bloque 1, que es deterministico y caza
la mayoria de las regresiones (si el buscador deja de encontrar el articulo,
todo lo demas da igual). Los bloques que llaman al modelo hay que pedirlos a
mano, y antes de arrancar se dice cuantas llamadas van a salir.

El banco NO modifica nada: lee el corpus, ejecuta consultas y juzga. No toca
el JSONL de la fase 1 ni los casos.

Cada prueba imprime QUE ESPERABA, QUE SALIO y VERDE o ROJO. Al final, un
recuento y un veredicto de una linea. No hay nada que interpretar.

Bloques:
  1 · Recuperacion   sin llamadas: el buscador encuentra el articulo correcto
  2 · Analizador     con modelo: propone terminos DEL ARTICULADO, y las
                     puertas (sin ano / con ano / materia ajena) funcionan
  3 · Estabilidad    con modelo: la misma pregunta 3 veces da el MISMO estado
                     y los MISMOS articulos, aunque cambie el texto
  4 · Bucle          la cita falsa acaba en NO ENCONTRADO, y cuantas veces se
                     entra en el bucle de reintento
  5 · Rojos de extremo a extremo: los casos que el bloque 1 no recupera se
                     repiten dejando que el analizador proponga los terminos.
                     El bloque 1 puentea el analizador a proposito, asi que sus
                     rojos dicen "el buscador SOLO no llega", no "el sistema
                     falla". Esto mide lo segundo. Cuesta 1 llamada por rojo.

Los bloques 2 y 3 necesitan el modelo real. Con --motor ensayo salen como
OMITIDO, nunca como VERDE: dar por buena una prueba que no se ha ejecutado es
justo lo que este proyecto intenta evitar.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from datetime import datetime
from pathlib import Path

import fase4
from agente_fiscal import analizador as AN
from agente_fiscal import estado as EST
from agente_fiscal import modelo as MOD
from agente_fiscal import texto as T

RAIZ = Path(__file__).resolve().parent
CASOS = RAIZ / "casos" / "banco_recuperacion.txt"
CASOS_MATERIAL = RAIZ / "casos" / "banco_material.txt"
DIR_BANCO = RAIZ / "datos" / "banco"
# La linea base SI se versiona: es el ultimo resultado bueno conocido, y es lo
# unico contra lo que comparar en una maquina recien clonada, donde datos/ no
# existe todavia.
LINEA_BASE = RAIZ / "casos" / "linea_base.json"
ANCHO = 78

VERDE, ROJO, OMITIDO = "VERDE", "ROJO", "OMITIDO"
# Un fallo de llamada al modelo NO es que la prueba no pase: es que la prueba
# NO SE HA EJECUTADO. Tiene estado propio y cuenta como rojo.
#
# De donde sale esto: en la primera pasada real, las tres corridas del bloque 3
# fallaron (estado=None, preceptos=[]) y la prueba salio VERDE, porque
# "siempre el mismo estado" se cumple cuando el estado es siempre None. Un
# sistema roto del todo es perfectamente estable. El banco mintio en verde.
FALLO = "FALLO DEL MODELO"

# Estados que cuentan como no superados.
NO_SUPERADOS = (ROJO, FALLO)


def sin_respuesta(*resultados) -> str:
    """Motivo por el que NO se puede evaluar el criterio, o cadena vacia.

    Se llama ANTES de mirar el criterio en toda prueba que dependa del modelo.
    Sin respuesta valida no hay nada que juzgar.
    """
    for i, r in enumerate(resultados, 1):
        if r is None:
            return f"la corrida {i} no devolvio resultado"
        if r.get("fallo") == "modelo":
            return (f"fallo de llamada al modelo en la corrida {i}: "
                    f"{(r.get('motivo') or '')[:90]}")
        if r.get("fallo") == "analisis":
            return (f"el analizador no devolvio un JSON valido en la corrida "
                    f"{i}: {(r.get('motivo') or '')[:90]}")
    return ""

# Umbral del bloque 2: que parte de los terminos propuestos debe existir en el
# articulado. Por debajo, el analizador esta repitiendo la pregunta.
COBERTURA_TERMINOS_MINIMA = 0.6
# Umbral del bloque 4: si se entra en el bucle de reintento en mas de la mitad
# de las redacciones, el prompt del redactor esta mal.
TASA_REINTENTO_MAXIMA = 0.5

# Bloques que llaman al modelo. Solo se ejecutan con --con-modelo.
BLOQUES_CON_MODELO = {"2", "3", "4", "5"}
BLOQUES_GRATIS = {"1"}


def llamadas_previstas(bloques: set[str], n_casos: int,
                       n_rojos: int = 0) -> tuple[int, int]:
    """(minimo, maximo) de llamadas al modelo, para avisar ANTES de gastar.

    Se cuenta lo que hace cada consulta: 1 analisis (2 si el JSON sale mal) y
    entre 1 y 2 redacciones (la segunda solo si el verificador rechaza). Las
    consultas que paran antes -sin ejercicio, materia ajena- no redactan.
    """
    minimo = maximo = 0
    if "2" in bloques:
        minimo += n_casos * 2 + 3        # n consultas completas + 3 puertas
        maximo += n_casos * 4 + 7
    if "3" in bloques:
        minimo += 3 * 2
        maximo += 3 * 4
    if "4" in bloques:
        minimo += (n_casos + 1) * 2
        maximo += (n_casos + 1) * 4
    if "5" in bloques:
        # Una llamada por caso en rojo (dos si el JSON sale mal). No redacta.
        minimo += n_rojos
        maximo += n_rojos * 2
    return minimo, maximo


# ---------------------------------------------------------------- utilidades


def titulo(t: str) -> None:
    print("\n" + "=" * ANCHO)
    print(t)
    print("=" * ANCHO)


def bloque(t: str) -> None:
    print("\n" + "-" * ANCHO)
    print(t)
    print("-" * ANCHO)


class Registro:
    """Acumula resultados y hace el recuento. Nadie interpreta nada."""

    def __init__(self):
        self.pruebas: list[dict] = []

    def anota(self, bloque: str, nombre: str, esperado: str, obtenido: str,
              veredicto: str, extra: dict | None = None, ident: str = "") -> None:
        self.pruebas.append({
            "id": ident or nombre,
            "bloque": bloque, "nombre": nombre, "esperado": esperado,
            "obtenido": obtenido, "veredicto": veredicto, **(extra or {}),
        })
        marca = {VERDE: "[VERDE]", ROJO: "[ROJO ]", OMITIDO: "[OMIT ]",
                 FALLO: "[FALLO]"}[veredicto]
        print(f"{marca} {nombre}")
        print(f"        esperaba : {esperado}")
        print(f"        ha salido: {obtenido}")

    def cuenta(self, veredicto: str) -> int:
        return sum(1 for p in self.pruebas if p["veredicto"] == veredicto)


def leer_casos(ruta: Path) -> list[dict]:
    """Casos de recuperacion. Cuatro campos:

        consulta | norma | articulos aceptables | puesto maximo

    La NORMA es obligatoria desde que hay dos cargadas: "articulo 75" existe
    en la Ley (Devengo del impuesto) y en el Reglamento (Supuestos de
    aplicacion), y sin decir cual no se identifica nada.
    """
    casos = []
    for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        partes = [p.strip() for p in linea.split("|")]
        if len(partes) not in (4, 5, 6):
            raise SystemExit(
                f"{ruta}:{n}: se esperaban 4, 5 o 6 campos (consulta | norma | "
                f"articulos | tope [| impuesto [| comunidad]]), hay "
                f"{len(partes)}"
            )
        casos.append({
            "consulta": partes[0],
            "norma": partes[1],
            # EL QUINTO CAMPO: LO QUE DIRIA EL ANALIZADOR, que no es lo mismo
            # que donde vive la respuesta.
            #
            # Las cuatro preguntas de procedimiento tenian como norma la LGT,
            # de la que se deducia impuesto GENERAL, y con eso no se filtraba
            # nada: el banco medía un escenario que no ocurre. En la realidad
            # «me he retrasado en presentar el 303» la clasifica el analizador
            # como IVA, y entonces si se filtra.
            #
            # Vacio = el de la norma, que es lo normal en una pregunta de
            # fondo: quien pregunta por el articulo 95 de la Ley del IVA
            # pregunta de IVA.
            "impuesto": partes[4] if len(partes) > 4 else "",
            # EL SEXTO CAMPO: LA COMUNIDAD.
            #
            # Hace falta desde que hay normativa autonomica cargada. En
            # Sucesiones y en Transmisiones la respuesta CAMBIA con ella -la
            # autonomica fija reducciones y tarifa- y medir esos casos sin
            # comunidad seria medir un escenario que en la gestoria no ocurre:
            # el gestor sabe donde vive su cliente.
            #
            # Vacia = no se dice, que es lo normal en IVA o en Sociedades.
            "comunidad": partes[5] if len(partes) > 5 else "",
            "aceptables": [a.strip() for a in partes[2].split(",") if a.strip()],
            "tope": int(partes[3]),
            "linea": n,
        })
    return casos


def ejecutar_consulta(pregunta, ejercicio, motor, ix, grafo):
    """Lanza una consulta y se traga la salida: aqui solo importa el dict."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        res = fase4.consultar(pregunta, ejercicio, motor, ix, grafo)
    return res, buf.getvalue()


# ------------------------------------------------------------------ bloque 1


def cargar_material(ruta: Path) -> list:
    """consulta | impuesto | comunidad | minimo de estatales."""
    casos = []
    for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        partes = [p.strip() for p in linea.split("|")]
        if len(partes) != 4:
            raise SystemExit(f"{ruta}:{n}: se esperaban 4 campos, hay "
                             f"{len(partes)}")
        casos.append({"consulta": partes[0], "impuesto": partes[1],
                      "comunidad": partes[2], "minimo": int(partes[3]),
                      "linea": n})
    return casos


def bloque_1b(reg: Registro, ix, grafo, casos) -> None:
    """La BASE ESTATAL llega al redactor. Presencia, no puesto.

    El bloque 1 no puede ver funcionar el suelo de estatales porque mide otra
    cosa. Ampliar el instrumento, no ajustar la propiedad.
    """
    from agente_fiscal import estado as EST
    bloque("BLOQUE 1B · LA BASE ESTATAL EN EL MATERIAL  (no gasta llamadas)")
    print("Con la comunidad puesta, lo autonomico no puede dejar fuera la "
          "ley estatal.\n")
    for caso in casos:
        docs, _h, reserva = fase4.recuperar(
            ix, grafo, caso["consulta"], caso["impuesto"],
            tope=fase4.TOPE_MATERIAL, naturaleza=AN.FONDO,
            comunidad=caso["comunidad"])
        sel = EST.seleccionar_material(ix, caso["consulta"], docs, grafo,
                                       reserva=reserva, naturaleza=AN.FONDO)
        estatales = [e for e in sel.elegidos
                     if not ix.normas.comunidad_de_precepto(e)
                     and ix.normas.impuesto_de_precepto(e) == caso["impuesto"]]
        veredicto = VERDE if len(estatales) >= caso["minimo"] else ROJO
        cuales = ", ".join(str(e.get("referencia_corta")) for e in estatales)
        reg.anota("1B", f"«{caso['consulta']}»",
                  f"al menos {caso['minimo']} precepto(s) estatales de "
                  f"{caso['impuesto']} en el material",
                  f"{len(estatales)} de {len(sel.elegidos)} enviados"
                  + (f": {cuales}" if cuales else ""),
                  veredicto, {"linea_caso": caso["linea"]},
                  ident=f"b1b:{caso['impuesto']}:{caso['linea']}")


def bloque_1(reg: Registro, ix, grafo, casos) -> None:
    bloque("BLOQUE 1 · RECUPERACION  (no gasta llamadas)")
    print("El buscador de la fase 2 tiene que encontrar el articulo correcto.\n")

    for caso in casos:
        cuerpo_esperado, motivo = ix.normas.resolver(caso["norma"])
        if cuerpo_esperado is None:
            reg.anota("1", f"«{caso['consulta']}»",
                      f"norma {caso['norma']!r}",
                      f"esa norma no esta cargada: {motivo}", ROJO,
                      {"linea_caso": caso["linea"]},
                      ident=f"b1:{caso['norma']}:{','.join(caso['aceptables'])}")
            continue
        etiqueta_norma = ix.normas.por_clave(cuerpo_esperado).etiqueta

        # SE BUSCA COMO BUSCA EL AGENTE, NO DE OTRA FORMA. Aqui habia un
        # `ix.buscar` a secas, y desde que la busqueda filtra por impuesto eso
        # media un sistema que ya no existe: decia que el articulo 4 de la Ley
        # 19/1991 no salia -y sale el tercero- y que el 26 de la Ley 27/2014
        # salia quinto -y sale segundo-. Los 19 casos de IVA y LGT no lo
        # delataron porque ganan igual con filtro o sin el; hizo falta un
        # impuesto pequeno para que se viera.
        #
        # El impuesto sale de la NORMA que declara el caso, que es un dato del
        # propio caso y no una suposicion de aqui.
        # El caso puede declarar el impuesto que diria el analizador; si no
        # lo declara, el de su norma. Ver el quinto campo en `leer_casos`.
        impuesto = (caso.get("impuesto")
                    or ix.normas.impuesto_de_cuerpo(cuerpo_esperado))
        # LA NATURALEZA, del propio caso: si el articulo que se espera vive en
        # una norma general, la duda es de procedimiento. No es una suposicion,
        # es lo que el caso declara al decir donde esta su respuesta.
        #
        # El bloque 1 mide la recuperacion DADA una clasificacion correcta.
        # Que el analizador acierte la clasificacion lo mide el bloque 5, con
        # el modelo de verdad; son dos preguntas distintas y se miden aparte.
        naturaleza = (AN.PROCEDIMIENTO
                      if ix.normas.impuesto_de_cuerpo(cuerpo_esperado) == ""
                      else AN.FONDO)
        resultados, _h, _reserva = fase4.recuperar(
            ix, grafo, caso["consulta"], impuesto,
            tope=max(caso["tope"], 10), naturaleza=naturaleza,
            comunidad=caso.get("comunidad", ""))
        salieron = []
        puesto = None
        for i, r in enumerate(resultados, 1):
            rg = r.doc.registro
            num = rg["referencia"].replace("Articulo ", "")
            corto = ix.normas.por_clave(rg["cuerpo_clave"]).etiqueta.split()[0]
            salieron.append(f"{num} ({corto})")
            # Tiene que coincidir el articulo Y la norma.
            if puesto is None and num in caso["aceptables"] \
                    and rg["cuerpo_clave"] == cuerpo_esperado:
                puesto = i

        ok = puesto is not None and puesto <= caso["tope"]
        if puesto is None:
            obtenido = (f"NO sale en los 10 primeros. Salieron: "
                        f"{', '.join(salieron[:6])}")
        else:
            obtenido = f"art. {caso['aceptables'][0]} de {etiqueta_norma} en el puesto {puesto}"
            if not ok:
                obtenido += f" (fuera del tope {caso['tope']})"
        reg.anota(
            "1", f"«{caso['consulta']}»",
            f"art. {' o '.join(caso['aceptables'])} de {etiqueta_norma} "
            f"entre los {caso['tope']} primeros",
            obtenido, VERDE if ok else ROJO,
            {"puesto": puesto, "top": salieron[:6], "linea_caso": caso["linea"],
             "norma": caso["norma"]},
            # El identificador es el OBJETIVO (norma + articulos), no el texto
            # de la consulta: reescribir la consulta no crea una prueba nueva.
            ident=f"b1:{cuerpo_esperado}:{','.join(caso['aceptables'])}",
        )


# ------------------------------------------------------------------ bloque 2


def bloque_2(reg: Registro, ix, grafo, casos, motor) -> None:
    bloque("BLOQUE 2 · ANALIZADOR  (necesita el modelo real)")
    if not motor.es_modelo_real:
        reg.anota("2", "analizador contra el modelo real",
                  "terminos del articulado y puertas de entrada",
                  "OMITIDO: se ha ejecutado con --motor ensayo, que no es un "
                  "modelo", OMITIDO, ident="b2:analizador")
        return

    print("Los terminos que propone, ¿son del articulado o repiten la pregunta?")
    print("Se mide: cuantos de sus terminos existen en el corpus, y cuantos")
    print("aportan algo que no estaba ya en la pregunta.\n")

    for caso in casos:
        res, _ = ejecutar_consulta(caso["consulta"] + " (ejercicio 2023)",
                                   2023, motor, ix, grafo)
        ident = f"b2:terminos:{caso['norma']}:{','.join(caso['aceptables'])}"
        fallo = sin_respuesta(res)
        if fallo:
            reg.anota("2", f"terminos para «{caso['consulta']}»",
                      f"al menos el {int(COBERTURA_TERMINOS_MINIMA * 100)}% de "
                      f"los terminos existe en el articulado",
                      fallo, FALLO, ident=ident)
            continue

        analisis = res.get("analisis") or {}
        terminos = analisis.get("terminos_busqueda") or []
        if not terminos:
            reg.anota("2", f"terminos para «{caso['consulta']}»",
                      "al menos 3 terminos del articulado",
                      f"ninguno: {res.get('motivo') or 'el analisis no dio terminos'}",
                      ROJO, ident=ident)
            continue

        en_corpus = [t for t in terminos
                     if any(ix.df.get(r, 0) > 0 for r in T.tokenizar(t))]
        raices_pregunta = set(T.tokenizar(caso["consulta"]))
        nuevos = [t for t in terminos
                  if not set(T.tokenizar(t)) <= raices_pregunta]
        cobertura = len(en_corpus) / len(terminos)
        ok = cobertura >= COBERTURA_TERMINOS_MINIMA

        reg.anota(
            "2", f"terminos para «{caso['consulta']}»",
            f"al menos el {int(COBERTURA_TERMINOS_MINIMA * 100)}% de los "
            f"terminos existe en el articulado",
            f"{len(en_corpus)}/{len(terminos)} en el corpus "
            f"({cobertura:.0%}), {len(nuevos)} aportan vocabulario nuevo: "
            f"{', '.join(terminos)}",
            VERDE if ok else ROJO,
            {"terminos": terminos, "cobertura": round(cobertura, 3),
             "nuevos": nuevos},
            ident=ident,
        )

    # --- las tres puertas de entrada ---
    res, _ = ejecutar_consulta("puedo deducir el IVA de un coche de empresa",
                               None, motor, ix, grafo)
    fallo = sin_respuesta(res)
    reg.anota("2", "pregunta SIN ano -> para y lo pregunta",
              "codigo 3 (falta el ejercicio)",
              fallo or f"codigo {res['codigo']}, estado {res['estado']}",
              FALLO if fallo else (VERDE if res["codigo"] == 3 else ROJO),
              ident="b2:puerta-sin-ano")

    res, _ = ejecutar_consulta(
        "requerimiento de la AEAT del ejercicio 2021 sobre la deduccion del "
        "IVA de un turismo", None, motor, ix, grafo)
    fallo = sin_respuesta(res)
    reg.anota("2", "pregunta CON ano escrito -> lo coge",
              "ejercicio 2021 tomado de la pregunta",
              fallo or f"ejercicio {res['ejercicio']}",
              FALLO if fallo else (VERDE if res["ejercicio"] == 2021 else ROJO),
              ident="b2:puerta-con-ano")

    res, _ = ejecutar_consulta(
        "retencion del IRPF de un alquiler de vivienda habitual", 2023,
        motor, ix, grafo)
    fallo = sin_respuesta(res)
    reg.anota("2", "pregunta de IRPF -> la puerta de materia la para",
              "NO ENCONTRADO (codigo 2)",
              fallo or f"codigo {res['codigo']}, estado {res['estado']}",
              FALLO if fallo else (VERDE if res["codigo"] == 2 else ROJO),
              ident="b2:puerta-materia")


# ------------------------------------------------------------------ bloque 3


def bloque_3(reg: Registro, ix, grafo, motor, veces: int = 3) -> None:
    bloque("BLOQUE 3 · ESTABILIDAD  (necesita el modelo real)")
    if not motor.es_modelo_real:
        reg.anota("3", "misma pregunta 3 veces",
                  "mismo estado y mismos articulos en las 3",
                  "OMITIDO: con --motor ensayo la respuesta es fija por "
                  "construccion y no prueba nada", OMITIDO,
                  ident="b3:estabilidad")
        return

    pregunta = "deduccion del IVA soportado en la compra de un turismo"
    print(f"Pregunta: «{pregunta}»  ·  ejercicio 2023  ·  {veces} ejecuciones")
    print("El texto puede cambiar. El estado y los articulos citados, no.\n")

    corridas = []
    for i in range(1, veces + 1):
        res, _ = ejecutar_consulta(pregunta, 2023, motor, ix, grafo)
        corridas.append(res)
        print(f"   corrida {i}: estado={res['estado']!r} "
              f"preceptos={res['preceptos']}")

    esperado = "un unico estado y un unico conjunto de articulos, no vacios"
    extra = {"corridas": [{"estado": c["estado"], "preceptos": c["preceptos"]}
                          for c in corridas]}

    # 1) Sin respuesta valida no se evalua la estabilidad.
    fallo = sin_respuesta(*corridas)
    if fallo:
        reg.anota("3", f"misma pregunta {veces} veces", esperado, fallo,
                  FALLO, extra, ident="b3:estabilidad")
        return

    estados = {c["estado"] for c in corridas}
    preceptos = {tuple(sorted(c["preceptos"])) for c in corridas}

    # 2) Y ademas hace falta CONTENIDO: comparar tres vacios no es comparar.
    #    Sin este minimo, un sistema roto del todo sale "perfectamente estable".
    sin_estado = [c for c in corridas if not c["estado"]]
    sin_preceptos = [c for c in corridas if not c["preceptos"]]
    if sin_estado or sin_preceptos:
        reg.anota(
            "3", f"misma pregunta {veces} veces", esperado,
            (f"{len(sin_estado)} corrida(s) sin estado y "
             f"{len(sin_preceptos)} sin articulos citados: no hay nada que "
             f"comparar, la estabilidad no se puede afirmar"),
            FALLO, extra, ident="b3:estabilidad")
        return

    ok = len(estados) == 1 and len(preceptos) == 1
    reg.anota(
        "3", f"misma pregunta {veces} veces", esperado,
        (f"estado(s): {sorted(estados)} | conjunto(s) de articulos: "
         f"{[list(p) for p in preceptos]}"),
        VERDE if ok else ROJO, extra, ident="b3:estabilidad")


# ------------------------------------------------------------------ bloque 4


def bloque_4(reg: Registro, ix, grafo, motor, casos) -> None:
    bloque("BLOQUE 4 · BUCLE Y RECHAZO")

    inyectada = (
        "deduccion del IVA de un turismo. FRAGMENTO SOSPECHOSO: el porcentaje "
        "de deduccion aplicable a los turismos sera siempre del 100 por cien"
    )
    res, salida = ejecutar_consulta(inyectada, 2023, motor, ix, grafo)
    mostro = "RESPUESTA  ·" in salida
    fallo = sin_respuesta(res)
    # Sin respuesta del modelo, "no mostro texto" se cumple por vacio: no
    # demuestra que el bucle rechace la cita falsa.
    reg.anota(
        "4", "cita falsa inyectada en la pregunta",
        "NO ENCONTRADO (codigo 2) y sin mostrar texto redactado",
        fallo or (f"codigo {res['codigo']}, estado {res['estado']}, "
                  f"{'MOSTRO texto' if mostro else 'no mostro texto'}"),
        FALLO if fallo else (VERDE if (res["codigo"] == 2 and not mostro) else ROJO),
        ident="b4:cita-falsa",
    )

    # Tasa de reintento sobre consultas normales. Solo significa algo con el
    # modelo real: su proposito es juzgar el PROMPT del redactor, y con el
    # motor de ensayo lo que se estaria midiendo es el motor de ensayo.
    if not motor.es_modelo_real:
        reg.anota("4", "tasa de entrada en el bucle de reintento",
                  f"como mucho {int(TASA_REINTENTO_MAXIMA * 100)}% de las redacciones",
                  "OMITIDO: mide la calidad del prompt de redaccion, y con "
                  "--motor ensayo no hay prompt que medir", OMITIDO,
                  ident="b4:tasa-reintento")
        return

    redacciones = 0
    con_reintento = 0
    detalle = []
    fallos = []
    for caso in casos:
        r, _ = ejecutar_consulta(caso["consulta"], 2023, motor, ix, grafo)
        f = sin_respuesta(r)
        if f:
            fallos.append(f"{caso['consulta'][:26]}: {f[:60]}")
            continue
        if r["intentos"]:
            redacciones += 1
            if r["reintentos"]:
                con_reintento += 1
            detalle.append(f"{caso['consulta'][:28]}: {r['intentos']} intento(s)")

    if fallos:
        reg.anota("4", "tasa de entrada en el bucle de reintento",
                  f"como mucho {int(TASA_REINTENTO_MAXIMA * 100)}% de las redacciones",
                  f"{len(fallos)} consulta(s) fallaron antes de redactar: "
                  f"{fallos[0]}", FALLO, {"fallos": fallos},
                  ident="b4:tasa-reintento")
        return
    if redacciones == 0:
        reg.anota("4", "tasa de entrada en el bucle de reintento",
                  f"menos del {int(TASA_REINTENTO_MAXIMA * 100)}% de las redacciones",
                  "ninguna consulta llego a redactar: no hay nada que medir",
                  FALLO, ident="b4:tasa-reintento")
        return

    tasa = con_reintento / redacciones
    ok = tasa <= TASA_REINTENTO_MAXIMA
    reg.anota(
        "4", "tasa de entrada en el bucle de reintento",
        f"como mucho {int(TASA_REINTENTO_MAXIMA * 100)}% "
        f"(si se supera, el prompt del redactor esta mal)",
        f"{con_reintento} de {redacciones} redacciones reintentaron ({tasa:.0%})",
        VERDE if ok else ROJO,
        {"detalle": detalle, "tasa": round(tasa, 3)},
        ident="b4:tasa-reintento",
    )


# ------------------------------------------------- comparar dos analizadores


def comparar_analizador(ix, casos, modelos: list[str]) -> int:
    """Los mismos casos, el mismo prompt, distinto modelo. Se comparan.

    Bajar el analizador a un modelo pequeno no se da por bueno porque suene
    razonable: se mide. Y se mide lo que importa, que no es si los terminos
    suenan bien, sino DOS cosas comprobables:

      1. cuantos de los terminos que propone existen de verdad en el
         articulado (si no existen, el buscador no los va a encontrar);
      2. si buscando con esos terminos sigue saliendo el articulo correcto,
         y en que puesto.

    Lo segundo es lo unico que decide. Un analizador es bueno si lo que
    propone hace que la fase 2 encuentre el precepto que resuelve la duda.
    Solo se llama a `analizar`: no se redacta, que es donde esta el gasto.
    """
    titulo("COMPARACION DE ANALIZADORES")
    print("Mismo prompt y mismos casos, cambiando solo el modelo de la llamada 1.")
    print("No se redacta: se compara lo que propone el analizador.\n")
    print(f"Modelos: {', '.join(modelos)}")
    print(f"Casos  : {len(casos)}  ->  {len(casos) * len(modelos)} llamadas en total\n")

    resumen: dict[str, dict] = {}
    detalle: dict[str, list] = {}

    for nombre_modelo in modelos:
        motor, err = fase4.preparar_motor(
            "anthropic", silencioso=True, modelo_analisis=nombre_modelo,
        )
        if motor is None:
            print(f"[FALLO DE ARRANQUE] {err}")
            return 1

        bloque(f"ANALIZADOR: {nombre_modelo}")
        filas = []
        for caso in casos:
            pregunta = caso["consulta"] + " (ejercicio 2023)"
            try:
                resp = motor.analizar(AN.SISTEMA, pregunta, AN.esquema_de(ix.normas))
            except MOD.ErrorModelo as e:
                print(f"  [FALLO] «{caso['consulta'][:40]}»: {e}")
                filas.append({"caso": caso, "fallo": str(e)})
                continue

            analisis, errores = AN.validar(resp.datos, ix.normas)
            if analisis is None:
                print(f"  [JSON RECHAZADO] «{caso['consulta'][:40]}»: "
                      f"{'; '.join(errores)[:70]}")
                filas.append({"caso": caso, "fallo": "json invalido"})
                continue

            terminos = analisis.terminos_busqueda
            en_corpus = [t for t in terminos
                         if any(ix.df.get(r, 0) > 0 for r in T.tokenizar(t))]
            cobertura = len(en_corpus) / len(terminos) if terminos else 0.0

            # Lo que de verdad importa: con esos terminos, ¿sale el articulo?
            cuerpo, _ = ix.normas.resolver(caso["norma"])
            resultados, _h, _r = fase4.recuperar(
                ix, grafo, " ".join(terminos),
                ix.normas.impuesto_de_cuerpo(cuerpo), tope=10,
                naturaleza=analisis.naturaleza)
            puesto = None
            for i, r in enumerate(resultados, 1):
                rg = r.doc.registro
                num = rg["referencia"].replace("Articulo ", "")
                if num in caso["aceptables"] and rg["cuerpo_clave"] == cuerpo:
                    puesto = i
                    break
            dentro = puesto is not None and puesto <= caso["tope"]
            print(f"  {'OK ' if dentro else 'NO '} «{caso['consulta'][:38]:<38}» "
                  f"puesto {str(puesto or '-'):>2}/{caso['tope']}  "
                  f"cobertura {cobertura:.0%}  ({len(terminos)} terminos)")
            filas.append({
                "caso": caso, "terminos": terminos, "cobertura": cobertura,
                "puesto": puesto, "dentro": dentro,
                "tokens": resp.uso.get("input_tokens", 0),
            })

        buenos = [f for f in filas if f.get("dentro")]
        validos = [f for f in filas if "fallo" not in f]
        # El denominador son TODOS los casos, no solo los que dieron un JSON
        # valido: un analisis rechazado tampoco encuentra el articulo. Contarlo
        # aparte seria maquillar el resultado del modelo que mas falla.
        resumen[nombre_modelo] = {
            "encuentra": len(buenos),
            "casos": len(filas),
            "evaluados": len(validos),
            "fallos": len(filas) - len(validos),
            "cobertura": (sum(f["cobertura"] for f in validos) / len(validos)
                          if validos else 0.0),
            "consumo": motor.totales(),
        }
        detalle[nombre_modelo] = filas

    # ------------------------------------------------------------- veredicto
    titulo("RESULTADO DE LA COMPARACION")
    print(f"{'modelo':<24} {'encuentra el art.':>18} {'cobertura':>10} "
          f"{'JSON malo':>10} {'entrada':>9} {'salida':>8}")
    for m, r in resumen.items():
        c = r["consumo"]
        print(f"{m:<24} {r['encuentra']:>7}/{r['casos']:<10} "
              f"{r['cobertura']:>9.0%} {r['fallos']:>10} "
              f"{c['entrada']:>9} {c['salida']:>8}")

    if len(modelos) == 2:
        a, b = modelos
        ra, rb = resumen[a], resumen[b]
        print()
        # Caso por caso, para poder ensenar EN QUE se diferencian.
        peores, mejores = [], []
        for fa, fb in zip(detalle[a], detalle[b]):
            if fa.get("dentro") and not fb.get("dentro"):
                peores.append((fa, fb))
            elif fb.get("dentro") and not fa.get("dentro"):
                mejores.append((fa, fb))
        def pinta(f):
            """Un lado de la comparacion. Puede no haber terminos: si el JSON
            se rechazo, no hay nada que ensenar y hay que decirlo asi."""
            if "fallo" in f:
                return f"NO EVALUADO ({f['fallo'][:60]})"
            return f"puesto {f.get('puesto') or '-'} -> {', '.join(f['terminos'])}"

        if peores:
            print(f"CASOS QUE {b} EMPEORA respecto de {a}:")
            for fa, fb in peores:
                print(f"  «{fa['caso']['consulta']}»")
                print(f"     {a}: {pinta(fa)}")
                print(f"     {b}: {pinta(fb)}")
        if mejores:
            print(f"CASOS QUE {b} MEJORA respecto de {a}:")
            for fa, fb in mejores:
                print(f"  «{fa['caso']['consulta']}»")
                print(f"     {a}: {pinta(fa)}")
                print(f"     {b}: {pinta(fb)}")
        if not peores and not mejores:
            print(f"Ningun caso cambia de lado: los dos encuentran los mismos "
                  f"articulos dentro del tope.")

        print()
        if rb["encuentra"] < ra["encuentra"]:
            print(f"VEREDICTO: {b} encuentra MENOS articulos que {a} "
                  f"({rb['encuentra']} contra {ra['encuentra']} de "
                  f"{ra['casos']}). No se cambia el modelo por defecto sin "
                  f"mirar los casos de arriba.")
            return 2
        print(f"VEREDICTO: {b} encuentra {rb['encuentra']} de {rb['casos']} "
              f"articulos y {a} encuentra {ra['encuentra']}. No hay perdida "
              f"de calidad medible en estos casos.")
    return 0


# ------------------------------------------------------------------ bloque 5


def casos_en_rojo(ix, grafo, casos) -> list[dict]:
    """Los casos que el bloque 1 no recupera dentro de su tope.

    Se recalcula aqui, sin depender de que el bloque 1 se haya ejecutado: es
    deterministico y no cuesta nada. Asi el bloque 5 sigue a los rojos solos,
    sin una lista escrita a mano que se quede vieja.
    """
    rojos = []
    for caso in casos:
        cuerpo, _ = ix.normas.resolver(caso["norma"])
        if cuerpo is None:
            continue
        resultados, _h, _r = fase4.recuperar(
            ix, grafo, caso["consulta"],
            caso.get("impuesto") or ix.normas.impuesto_de_cuerpo(cuerpo),
            tope=max(caso["tope"], 10),
            naturaleza=(AN.PROCEDIMIENTO
                        if ix.normas.impuesto_de_cuerpo(cuerpo) == ""
                        else AN.FONDO))
        puesto = None
        for i, r in enumerate(resultados, 1):
            rg = r.doc.registro
            if (rg["referencia"].replace("Articulo ", "") in caso["aceptables"]
                    and rg["cuerpo_clave"] == cuerpo):
                puesto = i
                break
        if puesto is None or puesto > caso["tope"]:
            rojos.append({**caso, "puesto_directo": puesto, "cuerpo": cuerpo})
    return rojos


def bloque_5(reg: Registro, ix, grafo, motor, casos) -> None:
    """Los rojos del bloque 1, PERO pasando por el analizador.

    Por que existe: el bloque 1 busca con la consulta tal cual, puenteando el
    analizador a proposito, porque asi mide el buscador solo. Eso esta bien
    para localizar un fallo, y es enganoso para juzgar el sistema: en una
    consulta real nadie busca con las palabras del usuario, se busca con los
    terminos que propone la llamada 1.

    Un rojo del bloque 1 dice "el buscador solo no llega". Este bloque dice si
    el SISTEMA llega. Son dos preguntas distintas y hasta ahora solo se medía
    la primera.

    Cuesta una llamada por caso en rojo (dos, si el JSON sale mal a la
    primera). Cuantos hay se calcula, no se escribe aqui: la version anterior
    de esta linea decia «hoy son 2 casos» y hoy son otros.

    ESTE BLOQUE ESTUVO ROTO DESDE QUE SE ESCRIBIO y nadie lo supo, porque
    necesita el modelo real y nunca se ejecuto. El y `casos_en_rojo` usaban
    `grafo` sin recibirlo -todos sus vecinos lo llevan en la firma-, asi que
    reventaban con un NameError en la PRIMERA linea, antes de pedirle nada al
    modelo: no habria costado dinero, simplemente no habria corrido jamas. Lo cubre `pruebas/prueba_bloque5.py`, que
    recorre esta misma rama con un motor de mentira: el modelo se llama por un
    solo sitio y todo lo de despues es determinista, asi que se puede probar
    entero sin gastar.
    """
    bloque("BLOQUE 5 · LOS ROJOS, DE EXTREMO A EXTREMO  (necesita el modelo)")
    rojos = casos_en_rojo(ix, grafo, casos)
    if not rojos:
        print("No hay ningun caso en rojo en el bloque 1: nada que reintentar.\n")
        return
    print(f"{len(rojos)} caso(s) que el buscador solo no recupera. Se repiten "
          f"dejando que el analizador proponga los terminos.\n")

    if not motor.es_modelo_real:
        for caso in rojos:
            reg.anota("5", f"de extremo a extremo: «{caso['consulta']}»",
                      f"art. {' o '.join(caso['aceptables'])} entre los "
                      f"{caso['tope']} primeros con los terminos del analizador",
                      "OMITIDO: hace falta el modelo real; con --motor ensayo "
                      "los terminos son fijos y no prueban nada", OMITIDO,
                      ident=f"b5:{caso['cuerpo']}:{','.join(caso['aceptables'])}")
        return

    for caso in rojos:
        ident = f"b5:{caso['cuerpo']}:{','.join(caso['aceptables'])}"
        esperado = (f"art. {' o '.join(caso['aceptables'])} entre los "
                    f"{caso['tope']} primeros con los terminos del analizador")
        try:
            resp = motor.analizar(AN.SISTEMA, caso["consulta"] + " (ejercicio 2023)",
                                  AN.esquema_de(ix.normas))
        except MOD.ErrorModelo as e:
            reg.anota("5", f"de extremo a extremo: «{caso['consulta']}»",
                      esperado, f"fallo de llamada al modelo: {e}", FALLO,
                      ident=ident)
            continue

        analisis, errores = AN.validar(resp.datos, ix.normas)
        if analisis is None:
            reg.anota("5", f"de extremo a extremo: «{caso['consulta']}»",
                      esperado,
                      f"el analizador no devolvio un JSON valido: "
                      f"{'; '.join(errores)[:80]}", FALLO, ident=ident)
            continue

        consulta = " ".join(analisis.terminos_busqueda)
        resultados, _h, _r = fase4.recuperar(
            ix, grafo, consulta, analisis.impuesto,
            tope=max(caso["tope"], 10), naturaleza=analisis.naturaleza)
        puesto, salieron = None, []
        for i, r in enumerate(resultados, 1):
            rg = r.doc.registro
            salieron.append(rg["referencia"].replace("Articulo ", ""))
            if (puesto is None
                    and rg["referencia"].replace("Articulo ", "") in caso["aceptables"]
                    and rg["cuerpo_clave"] == caso["cuerpo"]):
                puesto = i
        ok = puesto is not None and puesto <= caso["tope"]
        directo = caso["puesto_directo"]
        obtenido = (
            f"puesto {puesto if puesto else 'fuera de los 10'} "
            f"(con la consulta cruda era {directo if directo else 'fuera'}); "
            f"terminos: {', '.join(analisis.terminos_busqueda)}"
        )
        reg.anota("5", f"de extremo a extremo: «{caso['consulta']}»",
                  esperado, obtenido, VERDE if ok else ROJO,
                  {"terminos": analisis.terminos_busqueda, "puesto": puesto,
                   "puesto_con_consulta_cruda": directo, "top": salieron[:6]},
                  ident=ident)


# --------------------------------------------------------------- historico


def cargar_referencia() -> tuple[dict | None, str]:
    """Contra que se compara esta ejecucion.

    Primero la ejecucion anterior (datos/banco/, que NO se versiona); si no
    hay ninguna —maquina recien clonada—, la LINEA BASE versionada.
    """
    DIR_BANCO.mkdir(parents=True, exist_ok=True)
    previos = sorted(DIR_BANCO.glob("banco_*.json"))
    if previos:
        try:
            return json.loads(previos[-1].read_text(encoding="utf-8")), \
                   f"ejecucion anterior ({previos[-1].name})"
        except (json.JSONDecodeError, OSError):
            pass
    if LINEA_BASE.is_file():
        try:
            return json.loads(LINEA_BASE.read_text(encoding="utf-8")), \
                   f"linea base ({LINEA_BASE.name})"
        except (json.JSONDecodeError, OSError) as e:
            return None, f"linea base ilegible: {e}"
    return None, "nada con que comparar (ni ejecucion anterior ni linea base)"


def comparar(actual: dict) -> tuple[list[str], str]:
    """Avisa de lo que se ha puesto rojo respecto de la referencia."""
    referencia, origen = cargar_referencia()
    if referencia is None:
        return [], origen

    # Solo se comparan los bloques que se han ejecutado. Si no, correr
    # `--bloques 1` avisaria de que "han desaparecido" las pruebas de los
    # bloques 2-4, que es una falsa alarma — y un banco que da falsas alarmas
    # acaba ignorandose.
    bloques_corridos = {p["bloque"] for p in actual["pruebas"]}
    # Se casa por ID ESTABLE, no por el nombre visible. Renombrar una prueba
    # (o reescribir la consulta de un caso) no puede parecer "18 pruebas
    # nuevas y 1 desaparecida": ese ruido ahoga el aviso que importa.
    # Las referencias antiguas no traen id; entonces se cae al nombre.
    def clave(p):
        return p.get("id") or p["nombre"]

    antes = {
        clave(p): p
        for p in referencia.get("pruebas", [])
        if p.get("bloque") in bloques_corridos
    }

    avisos = []
    renombradas = 0
    for p in actual["pruebas"]:
        previo = antes.get(clave(p))
        if previo is None:
            avisos.append(f"nueva: {p['nombre']}")
            continue
        if previo.get("nombre") != p["nombre"]:
            renombradas += 1
        antes_v, ahora_v = previo["veredicto"], p["veredicto"]
        if antes_v == ahora_v:
            continue
        if antes_v == VERDE and ahora_v == ROJO:
            avisos.append(f"REGRESION: {p['nombre']} estaba en VERDE y ahora ROJO")
        elif antes_v == VERDE and ahora_v == FALLO:
            avisos.append(
                f"NO EJECUTADA: {p['nombre']} estaba en VERDE y ahora no ha "
                f"llegado a evaluarse ({FALLO})"
            )
        elif ahora_v == VERDE and antes_v in NO_SUPERADOS:
            avisos.append(f"arreglado: {p['nombre']} estaba en {antes_v} y ahora VERDE")
        else:
            avisos.append(f"cambio: {p['nombre']} de {antes_v} a {ahora_v}")
    ahora_claves = {clave(p) for p in actual["pruebas"]}
    for k, previo in antes.items():
        if k not in ahora_claves:
            avisos.append(f"desaparecida: {previo['nombre']}")
    if renombradas:
        avisos.append(
            f"({renombradas} prueba(s) renombradas, reconocidas por su "
            f"identificador; no son nuevas)"
        )
    return avisos, origen


def escribir_linea_base(resultado: dict) -> None:
    """Congela el resultado actual como linea base. NUNCA se llama solo.

    Que sea un comando explicito es la unica salvaguarda que hay: si la linea
    base se actualizara automaticamente al final de cada ejecucion, una
    regresion pasaria a ser la nueva normalidad sin que nadie la viera.
    """
    base = {
        "_que_es_esto": (
            "Ultimo resultado bueno CONOCIDO del banco. Se versiona a "
            "proposito: en una maquina recien clonada datos/banco/ no existe "
            "y esto es lo unico contra lo que comparar."
        ),
        "_como_se_actualiza": "python banco.py --actualizar-linea-base",
        "_cuidado": (
            "Actualizarla congela lo que haya AHORA, rojos incluidos. Revisa "
            "la lista de abajo antes de dar por buena una actualizacion."
        ),
        "fecha": resultado["fecha"],
        "motor": resultado["motor"],
        "bloques": resultado["bloques"],
        "resumen": resultado["resumen"],
        "pruebas": [
            {
                "id": p.get("id") or p["nombre"],
                "bloque": p["bloque"],
                "nombre": p["nombre"],
                "veredicto": p["veredicto"],
                "esperado": p["esperado"],
                "obtenido": p["obtenido"],
            }
            for p in resultado["pruebas"]
        ],
    }
    LINEA_BASE.parent.mkdir(parents=True, exist_ok=True)
    LINEA_BASE.write_text(
        json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ------------------------------------------------------------------- main


def main(argv: list[str]) -> int:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="Banco de pruebas del agente fiscal.")
    ap.add_argument("--motor", choices=["anthropic", "ensayo"], default="anthropic")
    ap.add_argument("--con-modelo", action="store_true", dest="con_modelo",
                    help="habilita los bloques 2-4, que SI llaman al modelo. "
                         "Sin esto solo corre el bloque 1, que no gasta nada.")
    ap.add_argument("--bloques", default=None,
                    help="cuales ejecutar, p.ej. 1,4. Por defecto: 1 (o 1,2,3,4 "
                         "con --con-modelo)")
    ap.add_argument("--casos", default=str(CASOS))
    ap.add_argument(
        "--comparar-analizador", nargs="*", dest="comparar_analizador",
        metavar="MODELO",
        help="compara dos modelos en la llamada 1 sobre los casos y para. "
             "Sin argumentos compara opus contra haiku. Gasta 1 llamada por "
             "caso y modelo; no redacta.",
    )
    ap.add_argument("--modelo-analisis", default=MOD.MODELO_ANALISIS,
                    dest="modelo_analisis",
                    help="modelo de la llamada 1 (comparable entre pasadas)")
    ap.add_argument("--modelo-redaccion", default=MOD.MODELO_REDACCION,
                    dest="modelo_redaccion", help="modelo de la llamada 2")
    ap.add_argument(
        "--actualizar-linea-base", action="store_true", dest="actualizar_base",
        help="congela ESTE resultado como linea base (casos/linea_base.json). "
             "Nunca ocurre solo.",
    )
    args = ap.parse_args(argv)

    # Modo aparte: comparar analizadores y parar. No toca la linea base ni el
    # historico; es una medida, no una prueba con veredicto verde/rojo.
    if args.comparar_analizador is not None:
        modelos = args.comparar_analizador or [MOD.MODELO_REDACCION,
                                               MOD.MODELO_ANALISIS]
        try:
            casos = leer_casos(Path(args.casos))
        except OSError as e:
            print(f"[FALLO] no se pueden leer los casos: {e}")
            return 1
        ix, _ = fase4.cargar_corpus()
        return comparar_analizador(ix, casos, modelos)

    # Por defecto, barato: solo el bloque 1.
    if args.bloques:
        pedidos = {b.strip() for b in args.bloques.split(",") if b.strip()}
    else:
        pedidos = ({"1", "2", "3", "4", "5"} if args.con_modelo
                   else set(BLOQUES_GRATIS))

    # Un bloque de pago pedido a mano sin --con-modelo NO se ejecuta a
    # escondidas: se dice que se descarta y por que. Gastar por descuido es
    # justo lo que este cambio viene a evitar.
    descartados = sorted(pedidos & BLOQUES_CON_MODELO) if not args.con_modelo else []
    if descartados:
        pedidos -= set(descartados)
    arranque = datetime.now()

    titulo("BANCO DE PRUEBAS · AGENTE FISCAL")
    print(f"fecha  : {arranque.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"motor  : {args.motor}")
    print(f"bloques: {', '.join(sorted(pedidos)) or '(ninguno)'}")
    print(f"casos  : {args.casos}")
    if descartados:
        print(f"\n[AVISO] los bloques {', '.join(descartados)} llaman al modelo "
              f"y NO se ejecutan sin --con-modelo.")
        print("        Repite con:  python banco.py --con-modelo "
              f"--bloques {args.bloques}")
    if not pedidos:
        print("\nNo queda ningun bloque que ejecutar. No se hace nada.")
        return 1

    # Si no hay ningun bloque de pago, ni se crea el motor real: no hay nada
    # que preguntarle a la API, ni credencial que comprobar.
    necesita_modelo = bool(pedidos & BLOQUES_CON_MODELO)
    nombre_motor = args.motor if necesita_modelo else "ensayo"

    motor, err = fase4.preparar_motor(
        nombre_motor, silencioso=True,
        modelo_analisis=args.modelo_analisis,
        modelo_redaccion=args.modelo_redaccion,
    )
    if motor is None:
        print(f"\n[FALLO DE ARRANQUE] {err}")
        print("\nEl banco no puede seguir. Comprueba el arranque con:")
        print("    python fase4.py credencial")
        return 1
    if motor.es_modelo_real:
        print(f"arranque: credencial y acceso comprobados")
        print(f"modelos : analisis {motor.modelo_analisis} | "
              f"redaccion {motor.modelo_redaccion}")
    elif necesita_modelo:
        print("arranque: motor de ensayo, no se llama a ningun modelo")
    else:
        print("arranque: no se llama a ningun modelo (bloque 1: deterministico)")

    try:
        casos = leer_casos(Path(args.casos))
    except OSError as e:
        print(f"\n[FALLO] no se pueden leer los casos: {e}")
        return 1
    print(f"corpus : {args.casos} con {len(casos)} casos de recuperacion")

    # AVISO DE GASTO, antes de la primera llamada. Cuantas van a ser y de que.
    if necesita_modelo and motor.es_modelo_real:
        minimo, maximo = llamadas_previstas(
            pedidos, len(casos), len(casos_en_rojo(ix, grafo, casos))
        )
        print()
        print("-" * ANCHO)
        print(f"ESTA PASADA VA A HACER ENTRE {minimo} Y {maximo} LLAMADAS AL MODELO.")
        print(f"  bloques de pago: {', '.join(sorted(pedidos & BLOQUES_CON_MODELO))}")
        print(f"  el rango sale de los reintentos: cada consulta redacta 1 o 2")
        print(f"  veces segun lo que diga el verificador.")
        print("  Para no gastar: python banco.py   (bloque 1, cero llamadas)")
        print("-" * ANCHO)

    ix, grafo = fase4.cargar_corpus()
    reg = Registro()

    if "1" in pedidos:
        bloque_1(reg, ix, grafo, casos)
        bloque_1b(reg, ix, grafo, cargar_material(CASOS_MATERIAL))
    if "2" in pedidos:
        bloque_2(reg, ix, grafo, casos, motor)
    if "3" in pedidos:
        bloque_3(reg, ix, grafo, motor)
    if "4" in pedidos:
        bloque_4(reg, ix, grafo, motor, casos)
    if "5" in pedidos:
        bloque_5(reg, ix, grafo, motor, casos)

    # ------------------------------------------------------------ recuento
    verdes, rojos, omitidos, fallos = (
        reg.cuenta(VERDE), reg.cuenta(ROJO), reg.cuenta(OMITIDO), reg.cuenta(FALLO)
    )
    total = len(reg.pruebas)
    duracion = (datetime.now() - arranque).total_seconds()

    resultado = {
        "fecha": arranque.isoformat(timespec="seconds"),
        "motor": args.motor,
        "modelo": getattr(motor, "modelo", "(ninguno)"),
        "bloques": sorted(pedidos),
        "llamadas_al_modelo": motor.llamadas if motor.es_modelo_real else 0,
        "consumo": motor.totales() if motor.es_modelo_real else {},
        "consumo_por_llamada": motor.consumo if motor.es_modelo_real else [],
        "segundos": round(duracion, 1),
        "resumen": {"total": total, "verde": verdes, "rojo": rojos,
                    "fallo_del_modelo": fallos, "omitido": omitidos},
        "pruebas": reg.pruebas,
    }
    avisos, origen_referencia = comparar(resultado)

    titulo("RECUENTO")
    for b in sorted({p["bloque"] for p in reg.pruebas}):
        del_bloque = [p for p in reg.pruebas if p["bloque"] == b]
        v = sum(1 for p in del_bloque if p["veredicto"] == VERDE)
        r = sum(1 for p in del_bloque if p["veredicto"] == ROJO)
        o = sum(1 for p in del_bloque if p["veredicto"] == OMITIDO)
        f = sum(1 for p in del_bloque if p["veredicto"] == FALLO)
        print(f"  bloque {b}: {v} verde, {r} rojo, {f} fallo del modelo, "
              f"{o} omitido")
    print(f"\n  TOTAL: {verdes} VERDE · {rojos} ROJO · {fallos} FALLO DEL MODELO "
          f"· {omitidos} OMITIDO (de {total})")
    print(f"  llamadas al modelo: "
          f"{motor.llamadas if motor.es_modelo_real else 0}")
    print(f"  duracion: {duracion:.1f} s")

    if motor.es_modelo_real and motor.consumo:
        t = motor.totales()
        por_modelo: dict[str, dict] = {}
        for c in motor.consumo:
            m = por_modelo.setdefault(
                c["modelo"], {"llamadas": 0, "entrada": 0, "salida": 0,
                              "cache_lectura": 0, "cache_escritura": 0})
            m["llamadas"] += 1
            for k in ("entrada", "salida", "cache_lectura", "cache_escritura"):
                m[k] += c[k]
        print("\n  GASTO DE ESTA PASADA (tokens, segun la API):")
        for m, v in sorted(por_modelo.items()):
            print(f"    {m:<22} {v['llamadas']:>3} llamada(s)  "
                  f"entrada {v['entrada']:>7}  salida {v['salida']:>6}  "
                  f"cache {v['cache_lectura']:>7}L/{v['cache_escritura']:>6}E")
        print(f"    {'TOTAL':<22} {t['llamadas']:>3} llamada(s)  "
              f"entrada {t['entrada']:>7}  salida {t['salida']:>6}  "
              f"cache {t['cache_lectura']:>7}L/{t['cache_escritura']:>6}E")
        leidos = t["cache_lectura"]
        procesada = t["entrada_total_procesada"] or 1
        print(f"    entrada procesada en total: {procesada} tokens, "
              f"de los que {leidos} ({leidos / procesada:.0%}) salieron de cache")

    if fallos:
        print("\n  NO EJECUTADAS por fallo del modelo (cuentan como no superadas):")
        for p in reg.pruebas:
            if p["veredicto"] == FALLO:
                print(f"    - [bloque {p['bloque']}] {p['nombre']}")
                print(f"      {p['obtenido']}")
    if rojos:
        print("\n  En ROJO:")
        for p in reg.pruebas:
            if p["veredicto"] == ROJO:
                print(f"    - [bloque {p['bloque']}] {p['nombre']}")
                print(f"      ha salido: {p['obtenido']}")
    if omitidos:
        print("\n  OMITIDAS (no se han ejecutado, no cuentan como aprobadas):")
        for p in reg.pruebas:
            if p["veredicto"] == OMITIDO:
                print(f"    - [bloque {p['bloque']}] {p['nombre']}")

    print(f"\n  Comparado con: {origen_referencia}")
    if avisos:
        for a in avisos:
            print(f"    {a}")
    else:
        print("    sin cambios de veredicto")

    DIR_BANCO.mkdir(parents=True, exist_ok=True)
    destino = DIR_BANCO / f"banco_{arranque.strftime('%Y%m%dT%H%M%S')}.json"
    destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=2),
                       encoding="utf-8")

    if args.actualizar_base:
        print("\n" + "-" * ANCHO)
        print("ACTUALIZANDO LA LINEA BASE. Se congela lo siguiente:")
        for p in reg.pruebas:
            print(f"    [{p['veredicto']:<7}] {p['nombre']}")
        if rojos:
            print(f"\n  ATENCION: se estan congelando {rojos} prueba(s) en ROJO.")
            print("  A partir de ahora dejaran de contar como regresion.")
        escribir_linea_base(resultado)
        print(f"\n  linea base escrita en {LINEA_BASE}")

    print("\n" + "=" * ANCHO)
    if fallos:
        veredicto = (f"BANCO EN ROJO: {fallos} prueba(s) NO SE HAN EJECUTADO "
                     f"(fallo del modelo)"
                     + (f" y {rojos} no dan lo esperado" if rojos else ""))
    elif rojos:
        veredicto = f"BANCO EN ROJO: {rojos} prueba(s) no dan lo esperado"
    elif omitidos:
        veredicto = (f"BANCO EN VERDE en lo ejecutado ({verdes}/{verdes}), "
                     f"pero {omitidos} prueba(s) NO se han ejecutado")
    else:
        veredicto = f"BANCO EN VERDE: las {verdes} pruebas dan lo esperado"
    print(veredicto)
    print(f"guardado en {destino}")
    print("=" * ANCHO)
    return 2 if (rojos or fallos) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
