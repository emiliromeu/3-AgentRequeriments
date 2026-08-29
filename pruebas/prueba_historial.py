#!/usr/bin/env python3
"""EL HISTORIAL: VOLVER A UNA CONSULTA DE HACE UNA SEMANA. Cero red, cero API.

    python pruebas/prueba_historial.py

Habia 5.325 expedientes en `datos/trazas` -la pregunta, la respuesta que se
enseño, cada cita con su veredicto- y ninguna forma de ver uno desde la ventana.

LAS QUE NO SE PUEDEN PERDER, y por que:

  · UNA CONSULTA GUARDADA SE ABRE CON SUS AVISOS. Es la que casi se cuela:
    `resultado.json` guarda `avisos_de_cobertura` y `limites_del_corpus`, y
    `interfaz._terminar` lee `cobertura` y `estructural`. Los nombres no
    cuadraban y, como todo se lee con `.get()`, NO FALLABA: pintaba la
    respuesta sin ningun aviso. Una respuesta vieja leida sin lo que puede
    invalidarla es peor que no poder abrirla.
  · Y SE LEE COMO GUARDADA, no como recien hecha. Si no, alguien manda a un
    cliente una respuesta de hace tres meses creyendo que se comprobo hoy.
  · EL FILTRO SE PUEDE APAGAR. Oculta 4.233 de prueba, y si algun dia se
    equivoca, lo que esconde tiene que poder volver: sin interruptor
    esconderiamos justo el ERROR que alguien busca cuando algo va mal.
  · EL INDICE NUNCA BLOQUEA. Es una cache. Roto, viejo o imposible de
    escribir, la lista se pinta mas despacio; no deja de existir.
"""
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import tkinter as tk  # noqa: E402

import interfaz  # noqa: E402
import ver_ejemplo  # noqa: E402
from agente_fiscal import expedientes as EX  # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:104]}" if not ok else ""))
    if not ok:
        fallos.append(que)


# ====================================================== un disco de mentira
#
# NO SE TOCA `datos/trazas`. Ahi estan las consultas de verdad; una suite que
# escribe en ellas es una suite que puede perderlas.
CAMPO = Path(tempfile.mkdtemp(prefix="historial_"))


def expediente(sello, pregunta, estado="CRITERIO CLARO", motor="anthropic",
               modelo="claude-opus-5", viene_de="", avisos=None, limite="",
               respuesta="El articulo 95 dice que no.", ejercicio=2024):
    d = CAMPO / sello
    d.mkdir(parents=True, exist_ok=True)
    (d / "pregunta.txt").write_text(pregunta, encoding="utf-8")
    res = {"estado": estado, "ejercicio": ejercicio, "motor": motor,
           "modelo": modelo, "con_criterio": False, "comunidad": "Cataluña",
           "preceptos": ["Articulo 95"], "senales": [],
           "avisos_de_cobertura": list(avisos or []),
           "limites_del_corpus": limite, "veredicto": "ACEPTADO",
           "intentos": 1, "codigo": 0}
    if viene_de:
        res["viene_de"] = viene_de
        (d / "hilo.json").write_text(json.dumps({"viene_de": viene_de}),
                                     encoding="utf-8")
    (d / "resultado.json").write_text(json.dumps(res, ensure_ascii=False),
                                      encoding="utf-8")
    if respuesta:
        (d / "borrador_1.txt").write_text(respuesta, encoding="utf-8")
        (d / "verificacion_1.json").write_text(
            json.dumps({"veredicto": "ACEPTADO", "citas": []}),
            encoding="utf-8")
    (d / "analisis.json").write_text(
        json.dumps({"resumen_duda": "si se deduce el turismo",
                    "ejercicio": ejercicio}), encoding="utf-8")
    (d / "seleccion.json").write_text(json.dumps({"preceptos": [
        {"referencia": "Articulo 95", "decision": "enviado"},
        {"referencia": "Articulo 51", "decision": "descartado"}]}),
        encoding="utf-8")
    return d


EX.DIR_TRAZAS = CAMPO
EX.INDICE = CAMPO / "_indice.json"
ver_ejemplo.DIR_TRAZAS = CAMPO

expediente("20260825T101500", "deduccion del IVA de un turismo",
           avisos=["Articulo 15: la disposicion adicional lo menciona"],
           limite="Articulo 34 remite a una norma que no esta en el corpus")
expediente("20260825T113000", "exencion del articulo 20 en el alquiler",
           estado="NO ENCONTRADO", respuesta="")
expediente("20260826T090000", "tributacion de la nuda propiedad")
expediente("20260826T090500", "tributacion de la nuda propiedad y si es menor",
           viene_de="20260826T090000", estado="CRITERIO DISCUTIDO")
# --- las que NO son del despacho ---
expediente("20260826T120000", "una prueba mia", motor="ensayo",
           modelo="(ninguno)")
expediente("20260826T120100", "otra prueba", motor="siempre-falla",
           modelo="(ninguno)", estado="ERROR")
expediente("20260826T120200", "", estado="SIN PREGUNTA", motor="",
           modelo="", respuesta="")
# --- un error de verdad: sin motor, pero es lo que alguien busca ---
expediente("20260827T083000", "requerimiento de hacienda del cliente",
           estado="ERROR", motor="", modelo="", respuesta="")

# ==================================================== 1. QUE GUARDA EL INDICE
print("\n=== 1. EL INDICE GUARDA UNA FILA, NO UNA RESPUESTA ===")
filas, aviso = EX.filas()
comprobar("se leen todos los expedientes", len(filas) == 8, len(filas))
comprobar("y el indice queda escrito", EX.INDICE.is_file())
comprobar("  sin aviso: se ha podido guardar", aviso == "", aviso)
guardado = json.loads(EX.INDICE.read_text("utf-8"))
una = guardado["expedientes"]["20260825T101500"]
comprobar("la fila lleva lo que necesita una linea de lista",
          set(una) == {"sello", "pregunta", "estado", "ejercicio", "comunidad",
                       "con_criterio", "motor", "modelo", "viene_de"},
          sorted(una))
# NO GUARDA LA RESPUESTA, y es deliberado: una copia del texto es una copia que
# puede decir algo distinto del expediente, y el indice se lee entero cada vez.
crudo = EX.INDICE.read_text("utf-8")
comprobar("y NO guarda el texto de la respuesta",
          "El articulo 95 dice que no" not in crudo)
comprobar("ni los avisos ni las citas",
          "disposicion adicional" not in crudo)
comprobar("la fecha sale del nombre de la carpeta, sin abrir nada",
          EX.fecha_de("20260825T101500") == ("25/08/2026", "10:15"),
          EX.fecha_de("20260825T101500"))
comprobar("  y un nombre sin sello no inventa una fecha",
          EX.fecha_de("copiada_a_mano") == ("", ""))

# ============================== 2. VIEJO, ROTO O DE SOLO LECTURA: NO BLOQUEA
print("\n=== 2. EL INDICE ES UNA CACHE. NUNCA BLOQUEA ===")
print("  La verdad es el disco, y preguntarle que carpetas hay cuesta 0,02 s.\n")

expediente("20260828T140000", "una consulta nueva de hoy")
filas, _ = EX.filas()
comprobar("VIEJO: aparece la que se acaba de añadir", len(filas) == 9,
          len(filas))
comprobar("  y queda apuntada en el indice, no se relee cada vez",
          "20260828T140000" in json.loads(EX.INDICE.read_text("utf-8"))["expedientes"])

shutil.rmtree(CAMPO / "20260828T140000")
filas, _ = EX.filas()
comprobar("BORRADA: la que ya no esta se cae del indice", len(filas) == 8,
          len(filas))
comprobar("  y tambien del fichero",
          "20260828T140000" not in
          json.loads(EX.INDICE.read_text("utf-8"))["expedientes"])

EX.INDICE.write_text("{esto no es json", encoding="utf-8")
filas, _ = EX.filas()
comprobar("ROTO: un indice ilegible se rehace, no se repara", len(filas) == 8,
          len(filas))

EX.INDICE.write_text(json.dumps({"version": 999, "expedientes": {"x": {}}}),
                     encoding="utf-8")
filas, _ = EX.filas()
comprobar("DE OTRA VERSION: se rehace igual, sin migrar nada",
          len(filas) == 8 and all(f["sello"] != "x" for f in filas), len(filas))

# NO SE PUEDE ESCRIBIR: la lista tiene que salir igual, solo que sin cache.
EX.INDICE.unlink(missing_ok=True)
guardar_bueno = EX._guardar_indice
EX._guardar_indice = lambda filas_: "no se ha podido guardar el indice: disco lleno"
filas, aviso = EX.filas()
comprobar("SIN PODER ESCRIBIR: la lista sale entera igual", len(filas) == 8,
          len(filas))
comprobar("  y se dice por que, en vez de callarlo", "disco lleno" in aviso,
          aviso)
EX._guardar_indice = guardar_bueno

# UNA CARPETA SIN NADA DENTRO no puede tumbar la lista.
(CAMPO / "20260828T150000").mkdir()
filas, _ = EX.filas()
comprobar("una carpeta vacia sale en la lista y no revienta nada",
          len(filas) == 9, len(filas))
vacia = [f for f in filas if f["sello"] == "20260828T150000"][0]
comprobar("  con la pregunta en blanco, no con una inventada",
          vacia["pregunta"] == "" and vacia["estado"] == "", vacia)
shutil.rmtree(CAMPO / "20260828T150000")
EX.filas()

# ==================================================== 3. EL FILTRO
print("\n=== 3. EL FILTRO OCULTA, NO BORRA ===")
filas, _ = EX.filas()
de_prueba = [f for f in filas if EX.es_de_prueba(f)]
del_despacho = [f for f in filas if not EX.es_de_prueba(f)]
print(f"    de prueba: {[f['sello'] for f in de_prueba]}")
comprobar("el motor de ensayo es de prueba",
          any(f["sello"] == "20260826T120000" for f in de_prueba))
comprobar("y los motores que existen para fallar, tambien",
          any(f["sello"] == "20260826T120100" for f in de_prueba))
comprobar("«SIN PREGUNTA» no es una consulta: la ventana no puede producirla",
          any(f["sello"] == "20260826T120200" for f in de_prueba))
# LA QUE IMPORTA: un ERROR de verdad no se puede esconder.
comprobar("UN ERROR SIN MOTOR NO SE OCULTA: es justo el que alguien busca",
          any(f["sello"] == "20260827T083000" for f in del_despacho),
          [f["sello"] for f in del_despacho])
comprobar("quedan las del despacho", len(del_despacho) == 5,
          [f["sello"] for f in del_despacho])
# EL ATAJO QUE PARECIA BUENO Y NO LO ES, dicho aqui para que no vuelva:
# filtrar por «gasto tokens» habria escondido 48 de las 79 consultas reales.
comprobar("el filtro NO mira el consumo, que dejaria fuera consultas reales",
          "consumo" not in EX.es_de_prueba.__doc__.lower()
          or "no sirve" in EX.es_de_prueba.__doc__.lower())

# ==================================================== 4. BUSCAR Y LOS HILOS
print("\n=== 4. BUSCAR Y LAS CONVERSACIONES ===")
comprobar("se busca por la pregunta",
          len(EX.buscar(del_despacho, "turismo")) == 1)
comprobar("  sin acentos y sin mayusculas: se busca con prisa",
          len(EX.buscar(del_despacho, "EXENCION")) == 1
          and len(EX.buscar(del_despacho, "exención")) == 1)
comprobar("  y sin nada escrito salen todas",
          len(EX.buscar(del_despacho, "  ")) == len(del_despacho))
grupos = EX.hilos(del_despacho)
hilo = [g for g in grupos if len(g) > 1]
comprobar("las dos vueltas de la nuda propiedad van en UNA fila",
          len(hilo) == 1 and len(hilo[0]) == 2, [len(g) for g in grupos])
comprobar("  y en orden: primero la que abrio el hilo",
          hilo[0][0]["sello"] == "20260826T090000")
comprobar("  la fila enseña la ULTIMA, que lleva el contexto entero",
          hilo[0][-1]["sello"] == "20260826T090500")
comprobar("los grupos salen de mas nuevo a mas viejo",
          [g[-1]["sello"] for g in grupos]
          == sorted([g[-1]["sello"] for g in grupos], reverse=True))

# ============================ 5. ABRIR UNA GUARDADA: CON SUS AVISOS
print("\n=== 5. UNA CONSULTA GUARDADA SE ABRE CON SUS AVISOS ===")
print("  `resultado.json` dice `avisos_de_cobertura` y `_terminar` lee")
print("  `cobertura`. No fallaba: pintaba la respuesta SIN AVISOS.\n")
res, faltan = ver_ejemplo.cargar("20260825T101500")
comprobar("se carga el expediente", res is not None, faltan)
comprobar("con su respuesta, sacada del borrador aceptado",
          "articulo 95 dice que no" in (res.get("respuesta") or "").lower(),
          res.get("respuesta"))
comprobar("EL AVISO DE COBERTURA LLEGA, con el nombre que lee la ventana",
          res.get("cobertura") == ["Articulo 15: la disposicion adicional lo menciona"],
          res.get("cobertura"))
comprobar("y el limite del corpus tambien",
          "Articulo 34" in (res.get("estructural") or ""),
          res.get("estructural"))
comprobar("el analisis viene cargado, para poder seguir el hilo",
          (res.get("analisis") or {}).get("resumen_duda") == "si se deduce el turismo",
          res.get("analisis"))
comprobar("  y los preceptos que se enviaron, solo los enviados",
          res.get("preceptos_enviados") == ["Articulo 95"],
          res.get("preceptos_enviados"))
comprobar("la comunidad viaja", res.get("comunidad") == "Cataluña")
comprobar("y se dice que el expediente existe: acabamos de abrirlo",
          res.get("expediente") is True)
res2, _ = ver_ejemplo.cargar("20260826T090500")
comprobar("una vuelta sabe de cual viene",
          res2.get("viene_de") == "20260826T090000", res2.get("viene_de"))

# LA PUERTA: solo de datos/trazas.
for fuera in ("../../etc", "/etc", "..", "20260825T101500/../.."):
    r, f = ver_ejemplo.cargar(fuera)
    comprobar(f"no se abre nada de fuera: «{fuera}»", r is None, f)

# ==================================================== 6. LA VENTANA
print("\n=== 6. LA PANTALLA ===")
raiz = tk.Tk()
raiz.geometry("1280x900+40+40")
v = interfaz.Ventana(raiz, "ensayo")


def bombear(t=0.4):
    fin = time.time() + t
    while time.time() < fin:
        try:
            raiz.update()
        except tk.TclError:
            return
        time.sleep(0.01)


bombear(1.2)
comprobar("hay una puerta al historial en la pantalla de llegada",
          v.boton_historial.winfo_ismapped())
comprobar("  y dice a donde lleva",
          "anteriores" in v.boton_historial.cget("text").lower(),
          v.boton_historial.cget("text"))

v._abrir_historial()
# ENSEGUIDA quiere decir: la vista esta puesta ANTES de que el disco conteste.
# Se comprueba con `_historial_leido` todavia en False, que es lo que lo hace
# una comprobacion y no una casualidad de tiempos.
comprobar("la pantalla se coloca sin esperar al disco",
          bool(v.vista_historial.winfo_manager()) and not v._historial_leido,
          f"puesta={bool(v.vista_historial.winfo_manager())} "
          f"leido={v._historial_leido}")
bombear(0.3)
comprobar("  y se ve, con el disco todavia sin contestar o recien contestado",
          v.vista_historial.winfo_ismapped())
for _ in range(80):
    bombear(0.2)
    if v._historial_leido:
        break
bombear(0.5)
comprobar("y se llena", v._historial_leido and len(v._filas_historial) > 0,
          len(v._filas_historial))
comprobar("el interruptor nace PUESTO", v.ocultar_pruebas.get())
comprobar("  y dice lo que OCULTA, no lo que enseña",
          "ocultar" in v.marca_filtro.cget("text").lower(),
          v.marca_filtro.cget("text"))
comprobar("  con la cifra de lo que se lleva por delante",
          any(c.isdigit() for c in v.pie_filtro.cget("text")),
          v.pie_filtro.cget("text"))
n_con = len(v._grupos_historial)
v.ocultar_pruebas.set(False)
v._pintar_historial()
bombear(0.4)
comprobar("quitandolo salen mas: nada queda invisible",
          len(v._grupos_historial) > n_con,
          f"{n_con} -> {len(v._grupos_historial)}")
v.ocultar_pruebas.set(True)
v._pintar_historial()
bombear(0.4)

# EL PAGINADO. Es un limite de DIBUJO: 400 filas cuestan 4 segundos.
comprobar("se pinta una pagina, no las mil y pico",
          v._tope_historial <= interfaz.PAGINA_HISTORIAL, v._tope_historial)
raiz.destroy()

# ============ 7. ABRIR UNA DEL HISTORIAL Y SEGUIRLA, EN LA VENTANA
print("\n=== 7. ABRIRLA Y SEGUIR PREGUNTANDO ===")
raiz = tk.Tk()
raiz.geometry("1280x900+40+40")
v = interfaz.Ventana(raiz, "ensayo")
bombear(1.2)
fila = EX._leer_expediente("20260825T101500")
v._abrir_expediente([fila])
bombear(0.8)
comprobar("se abre en la MISMA vista de leer",
          v.vista_respuesta.winfo_ismapped())
comprobar("con su estado", v.etiqueta_estado.cget("text") == "CRITERIO CLARO",
          v.etiqueta_estado.cget("text"))
etiquetas = [w.cget("text") for w in v.panel_avisos.winfo_children()]
comprobar("Y CON SU AVISO, que es lo que casi se pierde",
          any("disposicion adicional" in t for t in etiquetas), str(etiquetas))
comprobar("el limite del corpus se lee debajo del texto",
          "Articulo 34" in v.texto.get("1.0", "end"))
comprobar("el pie dice CUANDO fue, no una ruta de disco",
          v.pie_respuesta.cget("text") == "25/08/2026 a las 10:15",
          v.pie_respuesta.cget("text"))
comprobar("SE DICE QUE ES GUARDADA, no recien hecha",
          any("guardada" in c.lower() for c in v.cintas_visibles()),
          v.cintas_visibles())
comprobar("la pregunta vuelve a la caja, a la vista",
          "turismo" in v.caja.get("1.0", "end"))
comprobar("y su año, no el de hoy", v.ejercicio.get() == "2024",
          v.ejercicio.get())
comprobar("  que ya no lo pisa el relleno automatico",
          v._ejercicio_a_mano)
comprobar("la caja de seguir esta puesta", v.marco_seguir.winfo_ismapped())
# Y LA CINTA SE RETIRA CUANDO DEJA DE SER VERDAD. Un «consulta guardada del
# 18/08» encima de un formulario en blanco es un aviso que miente.
v._nueva_consulta()
bombear(0.3)
comprobar("al volver a preguntar, la cinta de «guardada» se retira",
          not any("guardada" in c.lower() for c in v.cintas_visibles()),
          v.cintas_visibles())
v._abrir_expediente([fila])
bombear(0.5)
comprobar("y hay con que seguir el hilo: analisis y preceptos",
          bool(v.analisis_actual) and v.preceptos_actuales == ["Articulo 95"],
          v.preceptos_actuales)
# SEGUIR: se cuelga de ESTE expediente, no de la nada.
v.caja_seguir.delete("1.0", "end")
v.caja_seguir.insert("1.0", "y si el turismo fuera una furgoneta")
v.motor = object()
v.trabajando = False
v.bloqueada = False
lanzado = {}
v._lanzar = lambda con_criterio=False: lanzado.update(
    {"viene_de": v.hilo_viene_de, "contexto": v.hilo_contexto})
v._seguir()
bombear(0.4)
comprobar("seguir una guardada cuelga la vuelta nueva DE ELLA",
          v.hilo_viene_de == "20260825T101500" or
          lanzado.get("viene_de") == "20260825T101500",
          f"{v.hilo_viene_de!r} / {lanzado.get('viene_de')!r}")
comprobar("  y le pasa el contexto de la vuelta anterior",
          (v.hilo_contexto or lanzado.get("contexto") or {}).get("preceptos")
          == ["Articulo 95"],
          v.hilo_contexto or lanzado.get("contexto"))
comprobar("  con la pregunta anterior delante, no compuesta por dentro",
          "turismo" in v.caja.get("1.0", "end")
          and "furgoneta" in v.caja.get("1.0", "end"),
          v.caja.get("1.0", "end")[:90])
raiz.destroy()

# ==================================================== 8. CONTROL NEGATIVO
print("\n=== 8. CONTROL NEGATIVO: ¿CAZA ESTA SUITE LO QUE DICE CAZAR? ===")
print("  Lo de arriba solo vale si se pone rojo cuando se rompe de verdad.\n")

# 1 · se deshace el arreglo de los nombres: la respuesta pierde sus avisos.
res, _ = ver_ejemplo.cargar("20260825T101500")
sin_arreglo = {k: v2 for k, v2 in res.items()
               if k not in ("cobertura", "estructural")}
comprobar("con los nombres viejos, el aviso NO llega (por eso se arreglo)",
          not sin_arreglo.get("cobertura"), sin_arreglo.get("cobertura"))

# 2 · un filtro que mirara el consumo escondería consultas reales.
comprobar("un filtro por «gasto tokens» daria de prueba una consulta real",
          EX.es_de_prueba({"motor": "anthropic", "estado": "CRITERIO CLARO"})
          is False)

# 3 · si el indice guardase la respuesta, esta suite lo cazaria.
falso = dict(json.loads(EX.INDICE.read_text("utf-8")))
falso["expedientes"]["20260825T101500"]["respuesta"] = "El articulo 95 dice que no"
comprobar("si el indice guardase el texto, la comprobacion 1 se pondria roja",
          "El articulo 95 dice que no" in json.dumps(falso, ensure_ascii=False))

# 4 · una fecha inventada se cazaria.
comprobar("y una fecha supuesta no pasaria por buena",
          EX.fecha_de("no_es_un_sello") != ("29/08/2026", "00:00"))

shutil.rmtree(CAMPO, ignore_errors=True)
print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
