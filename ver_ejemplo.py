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
y no lo era: DE LAS TRES REFERENCIAS QUE ENSEÑABA, LAS TRES ESTABAN INVENTADAS
-las consultas V2759-21 y V0187-20 y la resolucion 00/02195/2019 no existen en
ninguna parte- y ademas tapaban las dos que el texto SI cita de verdad. Alguien
mirando la pantalla habria visto un numero de consulta con toda la pinta de ser
real al lado de una respuesta autentica.

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
    traza = DIR_TRAZAS / expediente
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
