#!/usr/bin/env python3
"""LA VENTANA CON UNA RESPUESTA REAL DENTRO, SIN GASTAR NI UNA LLAMADA.

    python ver_ejemplo.py                     el expediente por defecto
    python ver_ejemplo.py 20260805T224913     o el que se le diga

Sirve para mirar la pantalla -el diseño, el desplazamiento, como se lee una
respuesta larga- sin consultar nada.

----------------------------------------------------------------------------
TODO SALE DEL EXPEDIENTE. NADA ESCRITO A MANO.
----------------------------------------------------------------------------
La primera version de este guion llevaba un diccionario escrito por mi con el
estado, los avisos, los preceptos y las consultas de la DGT. Parecia inofensivo
y no lo era: LAS TRES REFERENCIAS QUE ENSEÑABA ME LAS SAQUE DE LA CABEZA y
ninguna es la que ese expediente cita de verdad. Ademas tapaban las dos
autenticas -V0160-23 y V0041-07-, que si estan en el texto.

Y AL COMPROBARLO DESPUES SALIO PEOR DE LO QUE PARECIA. Escribi aqui que esas
tres «no existen en ninguna parte» y solo habia mirado nuestra copia local. En
la fuente: V2759-21 y V0187-20 EXISTEN, son consultas reales de la DGT;
00/02195/2019 no consta en DYCTEA. O sea que la pantalla enseñaba dos numeros de
consulta AUTENTICOS pegados a una respuesta que no es la suya, que es peor que
un numero falso: un numero falso no lleva a ningun sitio, y uno autentico lleva
a un documento que no dice lo que aqui se le atribuye.

Un ejemplo inventado en material de demostracion es una cita falsa con otro
nombre. Asi que aqui NO se escribe ningun dato: se lee el `resultado.json` del
expediente y se pinta lo que hay. SI UN CAMPO NO ESTA, NO SE PINTA.

El `aporte` -que consultas acabaron citadas- no existia cuando se guardo este
expediente, asi que se RECONSTRUYE de dos ficheros de la misma traza:

    verificacion_N.json      las citas que el verificador dio por buenas
    recorte_criterio.json    lo que se le puso delante al redactor

Las dos son medidas de aquella ejecucion, no invenciones de ahora.

CERO LLAMADAS A LA API.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import tkinter as tk  # noqa: E402

import interfaz  # noqa: E402

DIR_TRAZAS = RAIZ / "datos" / "trazas"

# El expediente por defecto: la respuesta mas larga que ha escrito el redactor
# con las tres fuentes encendidas. Es el nombre de una carpeta que esta en
# disco, no un dato inventado: si no existe, este guion no abre.
EXPEDIENTE = "20260805T224913"


def _leer(ruta: Path):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def cargar(expediente: str) -> tuple:
    """El resultado tal cual quedo guardado, mas lo que se pueda reconstruir.

    Devuelve `(res, faltan)`. `faltan` son las cosas que NO se han podido leer,
    para decirlas en voz alta en vez de rellenarlas a ojo.
    """
    # SOLO DE `datos/trazas`, Y SE COMPRUEBA. Cerrado el 29/08/2026.
    #
    # Esto estaba anotado como pendiente sabido -«acepta una ruta absoluta y
    # mira fuera de datos/trazas; solo lee, y es un guion mio»-, y dejo de
    # valer en cuanto la VENTANA empezo a llamar aqui para el historial: ya no
    # es un guion mio, es una pantalla que usa el departamento. Se resuelve el
    # nombre y se exige que el resultado cuelgue de `datos/trazas`, con lo que
    # un «../..» o una ruta absoluta no llegan a abrirse.
    traza = (DIR_TRAZAS / expediente).resolve()
    if traza.parent != DIR_TRAZAS.resolve():
        return None, [f"«{expediente}» no es un expediente de datos/trazas"]
    if not traza.is_dir():
        return None, [f"no existe el expediente {expediente}"]

    res = _leer(traza / "resultado.json")
    if res is None:
        return None, [f"{expediente} no tiene un resultado.json legible"]
    faltan = []

    # LA RESPUESTA. Los expedientes viejos no guardaban el texto en
    # `resultado.json`; el que se enseño es el ultimo borrador que el
    # verificador ACEPTO. Si ninguno fue aceptado no se pinta nada: la regla de
    # no enseñar texto sin verificar vale igual para un ejemplo.
    if not res.get("respuesta"):
        aceptada = None
        for v in sorted(traza.glob("verificacion_*.json")):
            if (_leer(v) or {}).get("veredicto") == "ACEPTADO":
                aceptada = v
        if aceptada is not None:
            n = aceptada.stem.split("_")[-1]
            borrador = traza / f"borrador_{n}.txt"
            if borrador.is_file():
                res["respuesta"] = borrador.read_text(encoding="utf-8")
        if not res.get("respuesta"):
            faltan.append("ningun borrador tiene veredicto ACEPTADO: "
                          "no se enseña texto")

    # EL CODIGO DE SALIDA. Los expedientes anteriores a que existiera no lo
    # guardaban, y `interfaz._terminar` lo exige: sin esto, ver un ejemplo
    # viejo revienta con un KeyError. Solo puede ser 0: un expediente con
    # `estado` y con veredicto llego hasta el final, porque el codigo 3 se
    # devuelve ANTES de mirar nada y no deja ni estado ni veredicto.
    if "codigo" not in res:
        res["codigo"] = 0

    recorte = _leer(traza / "recorte_criterio.json")

    # CON QUE SE HIZO. Los expedientes anteriores a los dos botones no lo
    # guardaban; se deduce de si hubo criterio delante, que si esta medido.
    if res.get("con_criterio") is None:
        res["con_criterio"] = bool(recorte)

    # EL APORTE, reconstruido de las medidas de aquella ejecucion.
    if not res.get("aporte"):
        if recorte is None:
            faltan.append("no hay recorte_criterio.json: no se pinta el aporte")
        else:
            citadas_dgt, citadas_teac = set(), set()
            for v in sorted(traza.glob("verificacion_*.json")):
                d = _leer(v) or {}
                if d.get("veredicto") != "ACEPTADO":
                    continue
                for c in d.get("citas") or []:
                    if c.get("estado") != "VERIFICADA":
                        continue
                    if c.get("norma") == "dgt":
                        citadas_dgt.add(c.get("referencia_citada") or "")
                    elif c.get("norma") == "teac":
                        citadas_teac.add(c.get("referencia_corpus") or "")
            res["aporte"] = {
                "consultas_dgt": sorted(x for x in citadas_dgt if x),
                "resoluciones": sorted(x for x in citadas_teac if x),
                "consultas_en_material": list(
                    recorte.get("consultas_con_texto_en_el_material") or []),
                "resoluciones_en_material": [
                    f.get("fuente", "") for f in recorte.get("fuentes") or []
                    if str(f.get("fuente", "")).startswith("TEAC")],
            }

    # La pregunta y el año, tal cual se escribieron.
    pregunta = traza / "pregunta.txt"
    res["_pregunta"] = (pregunta.read_text(encoding="utf-8").strip()
                        if pregunta.is_file() else "")
    if not res["_pregunta"]:
        faltan.append("no hay pregunta.txt")
    analisis = _leer(traza / "analisis.json") or {}
    res["_ejercicio"] = str(res.get("ejercicio")
                            or analisis.get("ejercicio") or "")
    if not res["_ejercicio"]:
        faltan.append("el expediente no dice de que ejercicio era")

    # ────────────────────────────────────────────────────────────────────
    # LOS DOS NOMBRES QUE NO CUADRABAN. Arreglado el 29/08/2026.
    # ────────────────────────────────────────────────────────────────────
    #
    # `resultado.json` guarda `avisos_de_cobertura` y `limites_del_corpus`.
    # `interfaz._terminar` lee `cobertura` y `estructural`. Como todo se lee
    # con `.get()`, esto NO FALLABA: pintaba la respuesta SIN NINGUN AVISO.
    #
    # Comprobado sobre un expediente real -20260818T140817-, que en disco
    # lleva «Articulo 15: la Disposicion adicional tercera lo menciona y la
    # respuesta no la recoge; ahi suelen estar las excepciones» y se abria
    # diciendo que no habia nada que mirar. Una respuesta vieja leida sin sus
    # avisos es exactamente lo que este proyecto existe para que no pase, y
    # ademas es peor que no poder abrirla.
    if "cobertura" not in res:
        res["cobertura"] = list(res.get("avisos_de_cobertura") or [])
    if "estructural" not in res:
        res["estructural"] = res.get("limites_del_corpus") or ""

    # ────────────────────────────────────────────────────────────────────
    # LO QUE HACE FALTA PARA SEGUIR UNA CONVERSACION ANTIGUA
    # ────────────────────────────────────────────────────────────────────
    #
    # `interfaz._seguir` cuelga la vuelta nueva de la anterior y le pasa el
    # resumen de la duda y los preceptos que la sostenian. Sin esto se podia
    # LEER un expediente viejo pero no continuarlo, que es la mitad de lo que
    # se pidio. Las dos cosas estan en disco desde siempre; solo habia que
    # leerlas.
    res["analisis"] = analisis
    if not res.get("preceptos_enviados"):
        seleccion = _leer(traza / "seleccion.json") or {}
        res["preceptos_enviados"] = [
            p.get("referencia", "") for p in (seleccion.get("preceptos") or [])
            if p.get("decision") == "enviado" and p.get("referencia")]
    # De que vuelta viene esta, para poder armar el hilo hacia atras.
    if not res.get("viene_de"):
        res["viene_de"] = (_leer(traza / "hilo.json") or {}).get("viene_de", "")

    # LA COMUNIDAD, QUE VIAJA EN EL ECO. Los expedientes anteriores al campo no
    # la llevan, y entonces no se pinta: es lo correcto, porque no se sabe.
    res.setdefault("comunidad", "")
    # EL EXPEDIENTE EXISTE -lo acabamos de abrir-, asi que la ventana no puede
    # decir que la consulta no quedo guardada.
    res["expediente"] = True

    res["traza"] = str(traza)
    return res, faltan


def main(argv: list) -> int:
    expediente = argv[0] if argv else EXPEDIENTE
    res, faltan = cargar(expediente)
    if res is None:
        print(f"No se puede abrir el ejemplo: {faltan[0]}")
        print(f"Los expedientes estan en {DIR_TRAZAS}")
        return 1
    for f in faltan:
        print(f"  aviso: {f}")

    raiz = tk.Tk()
    v = interfaz.Ventana(raiz, "ensayo")
    # Maximizada, y DESPUES de construir: `Ventana` fija su tamaño de apertura
    # en el constructor, asi que hacerlo antes queda pisado.
    raiz.geometry(f"{raiz.winfo_screenwidth()}x{raiz.winfo_screenheight() - 80}"
                  f"+0+40")

    def pintar() -> None:
        v.caja.delete("1.0", "end")
        v.caja.insert("1.0", res["_pregunta"])
        v.ejercicio.set(res["_ejercicio"])
        v._revisar_boton()
        v.mostrar_cinta(
            f"EJEMPLO: esto es el expediente {expediente}, guardado en disco. "
            f"No es una consulta nueva, y todo lo que se ve sale de ahi.")
        v._terminar(res)
        # La vista de lectura lo dice tambien: quien mire la respuesta sin
        # haber visto la pantalla anterior tiene que saber de donde sale.
        v.eco_pregunta.configure(
            text=v._eco(res["_pregunta"], res["_ejercicio"])
            + f"    ·    EJEMPLO GUARDADO · expediente {expediente}")

    raiz.after(1400, pintar)
    raiz.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
