#!/usr/bin/env python3
"""LA ENTRADA DE MAQUINA DEL CORPUS. Cero red, cero API.

    printf 'deduccion vivienda habitual\\nprorrata especial\\n' \\
      | .venv/bin/python corpus_json.py buscar --ejercicio 2023

    printf 'BOE-A-1992-28740#0#articulo 95\\n' \\
      | .venv/bin/python corpus_json.py literal --ejercicio 2023

UN VERBO EN LA ORDEN Y EL LOTE POR LA ENTRADA ESTANDAR, y esa es toda la
gracia: el corpus se carga UNA VEZ y se contestan las peticiones que hagan
falta. Cargarlo son 2.504 preceptos y su indice invertido; hacerlo cien veces
para cien preguntas es cien veces el mismo trabajo, y es lo que pasaba cuando
la unica forma de preguntar era abrir la ventana o lanzar un proceso por
consulta.

LOS VERBOS
    buscar    una consulta por linea -> los preceptos que mejor encajan
    literal   una clave por linea    -> el texto EXACTO que regia ese ejercicio

----------------------------------------------------------------------------
EL CONTRATO. Literalmente el mismo: `agente_fiscal.maquina`
----------------------------------------------------------------------------

El mismo MODULO que `verificar_json` y `estado_json`, no una copia con las
mismas palabras. La suite `prueba_contrato_json` prueba los tres a la vez
justo por eso: tres suites separadas seguirian verdes el dia que uno se
fuera por su lado.

ENTRADA
    Una peticion POR LINEA en la entrada estandar. Una linea que empieza por
    `{` se lee como objeto JSON; cualquier otra es el texto pelado -la consulta
    en `buscar`, la clave en `literal`- y hereda lo que se haya puesto en la
    orden. Las lineas vacias se saltan.

SALIDA
    stdout: SOLO el JSON. UN objeto, UNA linea final, y nada mas. Las
            respuestas van dentro, en `respuestas`, EN EL ORDEN DE ENTRADA y
            con su `n`: quien manda un lote de cien tiene que poder casar cada
            respuesta con su peticion sin adivinar.
    stderr: nada, nunca. Ni progreso ni avisos.

CODIGOS DE SALIDA
    0   TODAS CONTESTADAS.
    2   ALGUNA NO. No encontrada, o rechazada por venir sin ejercicio. NO ES UN
        FALLO NUESTRO: es una respuesta correcta que dice que no. Cual es se
        ve peticion a peticion; el codigo solo ahorra tener que mirarlas.
    otro  FALLO. Y entonces NO HAY RESPUESTAS, por contrato: lo que sale por
          stdout es un objeto con `"error"` y sin `respuestas`, jamas un lote
          a medias con aspecto de lote entero. Un lote corto es lo que no se
          puede devolver: quien pidio cien y recibe sesenta buenas no tiene
          como saber que las cuarenta que faltan no eran «no encontrado».

EL EJERCICIO ES OBLIGATORIO EN `literal`
    Sin año no se devuelve texto. NUNCA, ni el de hoy «por defecto».

    El corpus guarda TODAS las versiones de cada precepto. Dar la de hoy para
    un caso de 2019 no da error, no se nota y es la respuesta equivocada mejor
    presentada que existe: articulo correcto, norma correcta, enlace correcto
    y la redaccion de otro año. Por eso una peticion sin ejercicio se rechaza
    con `error` y SIN el campo `texto`, en vez de contestarse con una nota al
    pie que nadie lee.

    En `buscar` no lo es: buscar es encontrar de que articulo se habla, y para
    eso el año no hace falta. Si se pone, cada resultado viene con sus avisos
    de vigencia.

EL HORIZONTE VA DENTRO DEL JSON
    Hasta donde llega esta copia -y el aviso de si el ejercicio que se pregunta
    cae MAS ALLA- van en la respuesta, no en este comentario. Un aviso que hay
    que venir a leer aqui no lo lee el programa que consume el JSON. Ver
    `frescura.aviso_de_horizonte`.

SOLO LECTURA
    No escribe nada: ni en el corpus, ni en las caches, ni en las trazas. Se
    puede llamar en paralelo desde varios sitios.

PROCEDENCIA
    Siempre, y tambien en los fallos: la version de este contrato y la huella
    del corpus del que salio cada literal.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
CORPUS = RAIZ / "datos" / "corpus"

# EL CONTRATO VIVE EN `agente_fiscal.maquina`: la version, la huella del
# corpus, lo unico que escribe en stdout y la forma de un fallo. El mismo
# modulo que usan `verificar_json` y `estado_json`, para que los tres no puedan
# separarse sin que alguien lo note.
from agente_fiscal.maquina import (  # noqa: E402
    Argumentos, ErrorDeUso, escribir as _escribir, fallo as _fallo_de,
    procedencia)

TODAS = 0
ALGUNA_NO = 2


def _fallo(motivo: str, detalle: str = "") -> int:
    return _fallo_de(motivo, CORPUS, detalle)


VERBOS = ("buscar", "literal")

# Cuantos preceptos devuelve `buscar` por consulta si no se dice otra cosa. El
# mismo tope que usa la ventana: no es un numero de este fichero.
TOPE = 8

# Cuanto texto se enseña de cada resultado de `buscar`. Es un ANTICIPO para
# decidir, no una cita: quien quiera citar pide el `literal`, que da el texto
# entero de la version que tocaba.
ANTICIPO = 300


# ------------------------------------------------------------------- entrada


def leer_peticiones(entrada: str, verbo: str, ejercicio, tope: int) -> list:
    """Las lineas de stdin, ya normalizadas a dicts. Sin tocar el corpus.

    Se hace ANTES de cargar nada: una linea mal formada se caza en un
    milisegundo en vez de despues de veinte segundos de indice.
    """
    campo = "consulta" if verbo == "buscar" else "clave"
    peticiones = []
    for n, cruda in enumerate(entrada.splitlines()):
        linea = cruda.strip()
        if not linea:
            continue
        if linea.startswith("{"):
            try:
                p = json.loads(linea)
            except ValueError as e:
                peticiones.append({"n": n, "error": "la linea no es JSON valido",
                                   "detalle": str(e)[:120]})
                continue
            if not isinstance(p, dict):
                peticiones.append({"n": n, "error": "la linea no es un objeto"})
                continue
        else:
            p = {campo: linea}
        # LO DE LA ORDEN ES EL DEFECTO Y LO DE LA LINEA MANDA. Asi un lote de
        # un solo ejercicio se manda en texto pelado, y uno con casos de años
        # distintos trae el suyo en cada linea sin lanzar un proceso por año.
        p.setdefault("ejercicio", ejercicio)
        p.setdefault("tope", tope)
        p["n"] = n
        peticiones.append(p)
    return peticiones


def _ejercicio_de(peticion: dict):
    """El año de la peticion, o None. Un año que no es un año es None."""
    valor = peticion.get("ejercicio")
    if valor in (None, ""):
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------- verbos


def _del_registro(reg: dict) -> dict:
    """Los datos de identidad de un precepto. Lo que hace falta para citarlo."""
    return {"clave": reg.get("clave", ""),
            "referencia": reg.get("referencia", ""),
            "norma": reg.get("norma_id", ""),
            "norma_titulo": reg.get("norma_titulo", ""),
            "url": reg.get("url", ""),
            "consolidado_hasta": reg.get("consolidado_hasta", "")}


def _avisos(reg: dict, ejercicio) -> list:
    from agente_fiscal import vigencia as VG
    return [{"nivel": a.nivel, "clave": a.clave, "texto": a.texto}
            for a in VG.avisos(reg, ejercicio)]


def hacer_buscar(ix, peticion: dict) -> dict:
    from agente_fiscal import vigencia as VG

    consulta = str(peticion.get("consulta") or "").strip()
    ejercicio = _ejercicio_de(peticion)
    if not consulta:
        return {"n": peticion["n"], "error": "peticion sin consulta",
                "encontrado": False}
    try:
        tope = max(1, int(peticion.get("tope") or TOPE))
    except (TypeError, ValueError):
        tope = TOPE

    resultados, huerfanos = ix.buscar(consulta, tope)
    salida = []
    for r in resultados:
        reg = r.doc.registro
        fila = _del_registro(reg)
        fila["puntuacion"] = round(r.puntuacion, 4)
        # UN ANTICIPO, NO UNA CITA. Recortado y marcado como recortado, para
        # que a nadie se le ocurra pegarlo entre comillas en una respuesta.
        texto = str(reg.get("texto_vigente") or "")
        fila["anticipo"] = texto[:ANTICIPO]
        fila["anticipo_recortado"] = len(texto) > ANTICIPO
        fila["version"] = VG.resumen_version(reg, ejercicio)
        fila["avisos"] = _avisos(reg, ejercicio)
        salida.append(fila)
    return {"n": peticion["n"], "consulta": consulta, "ejercicio": ejercicio,
            "encontrado": bool(salida), "resultados": salida,
            # Los terminos de la consulta que no estan en ninguna norma. Es lo
            # que explica un «no encontrado» sin tener que adivinar.
            "sin_correspondencia": huerfanos}


def _buscar_registro(ix, clave: str):
    """El precepto de esa clave. `None` si no esta.

    Se admite la clave entera -`NORMA#cuerpo#precepto`, que es la que devuelve
    `buscar`- y tambien `NORMA#precepto` sin el indice de cuerpo, que es como
    la escribe una persona. Lo segundo solo vale si no hay ambigüedad: si dos
    cuerpos de la misma norma tienen ese precepto, no se elige uno.
    """
    doc = ix.por_clave.get(clave)
    if doc is not None:
        return doc.registro, ""
    if clave.count("#") == 1:
        norma, precepto = clave.split("#")
        candidatos = [d for d in ix.docs
                      if d.registro.get("norma_id") == norma
                      and d.registro.get("clave_local") == precepto]
        if len(candidatos) == 1:
            return candidatos[0].registro, ""
        if len(candidatos) > 1:
            return None, ("la clave es ambigua: " + ", ".join(
                sorted(c.registro["clave"] for c in candidatos)[:6]))
    return None, ""


def hacer_literal(ix, peticion: dict) -> dict:
    from agente_fiscal import vigencia as VG

    clave = str(peticion.get("clave") or "").strip()
    ejercicio = _ejercicio_de(peticion)
    if not clave:
        return {"n": peticion["n"], "error": "peticion sin clave",
                "encontrado": False}

    # EL EJERCICIO, ANTES QUE NADA Y SIN TEXTO. Ver el contrato de arriba: dar
    # la redaccion de hoy para un caso de 2019 es la respuesta equivocada mejor
    # presentada que existe, asi que aqui no se devuelve texto de ninguna clase.
    if ejercicio is None:
        return {"n": peticion["n"], "clave": clave, "encontrado": False,
                "error": "falta el ejercicio",
                "detalle": "el corpus guarda todas las versiones de cada "
                           "precepto: sin año no se sabe cual pedir, y la de "
                           "hoy puede no ser la que regia"}

    reg, ambigua = _buscar_registro(ix, clave)
    if reg is None:
        return {"n": peticion["n"], "clave": clave, "ejercicio": ejercicio,
                "encontrado": False,
                "error": ambigua or "no hay ningun precepto con esa clave"}

    fila = _del_registro(reg)
    fila.update({"n": peticion["n"], "ejercicio": ejercicio, "encontrado": True})

    version = VG.version_aplicable(reg, f"{ejercicio}-12-31")
    if version is None:
        # EN ESE AÑO NO EXISTIA. Se dice, y no se devuelve texto: el de la
        # primera version seria de despues del caso.
        fila.update({"encontrado": False,
                     "error": f"en {ejercicio} este precepto no existia",
                     "avisos": _avisos(reg, ejercicio)})
        return fila

    todas = reg.get("versiones") or []
    fila["texto"] = version.get("texto", "")
    fila["version"] = {
        "orden": version.get("orden"),
        "de": len(todas),
        # ES LA QUE REGIA EN EL EJERCICIO PEDIDO, no la de hoy. Se dice con las
        # dos fechas para que quien lo lea pueda comprobarlo sin fiarse.
        "vigente_desde": (version.get("fecha_vigencia_efectiva")
                          or version.get("fecha_vigencia") or ""),
        "es_la_de_hoy": bool(todas) and version.get("orden") == todas[-1].get("orden"),
        "resumen": VG.resumen_version(reg, ejercicio),
    }
    fila["avisos"] = _avisos(reg, ejercicio)
    return fila


# -------------------------------------------------------------------- flujo


def main(argv) -> int:
    ap = Argumentos(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("verbo", choices=VERBOS, help="que hacer con cada linea")
    ap.add_argument("--ejercicio", type=int, default=None,
                    help="el año del caso. OBLIGATORIO en `literal`, salvo que "
                         "cada linea traiga el suyo")
    ap.add_argument("--tope", type=int, default=TOPE,
                    help=f"cuantos preceptos por consulta en `buscar` ({TOPE})")
    # UNA LLAMADA MAL HECHA ES UN FALLO, NO UN «ALGUNA NO». Argparse sale con 2
    # y sin JSON, y 2 aqui significa que alguna peticion no se ha podido
    # contestar: un verbo que no existe no es eso, y ademas dejaria stdout
    # vacio, que rompe el `json.loads` de quien llame.
    try:
        args = ap.parse_args(argv)
    except ErrorDeUso as e:
        return _fallo("no se ha entendido la llamada", str(e))

    peticiones = leer_peticiones(sys.stdin.read(), args.verbo,
                                 args.ejercicio, args.tope)

    # EL CORPUS, Y AQUI ES DONDE SE ROMPE SI SE VA A ROMPER. Se envuelve entero
    # -no existe, ilegible, a medias- porque cualquiera de esas tiene que salir
    # como fallo y no como un lote de respuestas vacias.
    try:
        from agente_fiscal.indice import Indice     # noqa: E402
        ix = Indice(CORPUS)
        if not getattr(ix, "docs", None):
            return _fallo("corpus vacio o ausente",
                          f"no hay preceptos en {CORPUS}")
    except Exception as e:                          # noqa: BLE001
        return _fallo("no se ha podido cargar el corpus",
                      f"{type(e).__name__}: {e}")

    try:
        from agente_fiscal import frescura as FR
        horizonte = FR.horizonte(CORPUS)
    except Exception as e:                          # noqa: BLE001
        return _fallo("no se ha podido leer el horizonte del corpus",
                      f"{type(e).__name__}: {e}")

    hacer = hacer_buscar if args.verbo == "buscar" else hacer_literal
    respuestas = []
    try:
        for peticion in peticiones:
            if peticion.get("error") and "n" in peticion:
                # Una linea que ya venia mal de la entrada: se contesta con lo
                # que se sabe de ella y se sigue con el lote.
                respuestas.append({**peticion, "encontrado": False})
                continue
            r = hacer(ix, peticion)
            # EL AVISO DEL HORIZONTE, EN CADA RESPUESTA Y NO SOLO EN LA
            # CABECERA. Quien reparte las respuestas del lote por casos se
            # lleva cada una por su lado, y el aviso tiene que ir pegado a la
            # que le toca, no en un sitio del que se puede separar.
            aviso = FR.aviso_de_horizonte(CORPUS, _ejercicio_de(peticion))
            if aviso:
                r["aviso_horizonte"] = aviso
            respuestas.append(r)
    except Exception as e:                          # noqa: BLE001
        # UN LOTE A MEDIAS NO SE DEVUELVE. Ver el contrato: quien pidio cien y
        # recibe sesenta no puede distinguir «no encontrado» de «se rompio».
        return _fallo("el corpus ha fallado contestando el lote",
                      f"{type(e).__name__}: {e}")

    _escribir({
        "verbo": args.verbo,
        "peticiones": len(peticiones),
        # HASTA DONDE LLEGA LA COPIA, en la cabecera y sin que nadie lo pida.
        "horizonte": {k: v for k, v in horizonte.items() if k != "por_norma"},
        "respuestas": respuestas,
        "procedencia": procedencia(CORPUS),
    })
    return TODAS if all(r.get("encontrado") for r in respuestas) else ALGUNA_NO


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
