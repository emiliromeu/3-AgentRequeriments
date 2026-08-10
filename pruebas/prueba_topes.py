#!/usr/bin/env python3
"""EL TECHO DURO: que NUNCA se quede en bucle. Cero red, cero API.

Es una GARANTIA DE SEGURIDAD, no una funcionalidad. Si se rompe en silencio
nadie se entera hasta que una consulta se queda dando vueltas gastando dinero.

No basta con afirmar que hay un tope: se monta un modelo que SIEMPRE falla y se
comprueba que el sistema para EN el tope y NO ANTES. Las dos mitades importan:
parar antes seria tirar consultas buenas, y no parar es la averia.

    python pruebas/prueba_topes.py
"""
import contextlib
import io
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4
from agente_fiscal import modelo as MOD

fallos = []

# Un analisis VALIDO, para que la prueba llegue a la redaccion. Si el analisis
# tambien falla, fase4 se rinde a los dos intentos por su cuenta y NUNCA se
# llega a probar el techo: la primera version de esta prueba medía eso.
ANALISIS_BUENO = {
    "impuesto": "IVA",
    "ejercicio": 2023,
    "ejercicio_fundamento": "lo dice la pregunta",
    "articulos_sospechados": [],
    "terminos_busqueda": ["deduccion", "vehiculo", "turismo"],
    "resumen_duda": "si el IVA de un turismo se deduce al 100 por cien",
}


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {obtenido}" if not ok else ""))
    if not ok:
        fallos.append(que)


class MotorQueSiempreFalla(MOD.Motor):
    """Analisis valido, redaccion sin ni una cita. El verificador la tumba y
    fase4 reintenta: el peor caso que puede darse sin que nada este roto."""

    nombre = "siempre-falla"
    es_modelo_real = False

    def analizar(self, sistema, pregunta, esquema):
        self._permiso("analisis")
        self.llamadas += 1
        self._anotar("analisis", "(falso)", {})
        return MOD.Respuesta(texto="{}", datos=dict(ANALISIS_BUENO),
                             modelo="falso", motor=self.nombre)

    def redactar(self, sistema, contenido):
        self._permiso("redaccion")
        self.llamadas += 1
        self._anotar("redaccion", "(falso)", {})
        return MOD.Respuesta(texto="Esto no lleva ni una cita.",
                             modelo="falso", motor=self.nombre)


class MotorQueTarda(MotorQueSiempreFalla):
    """Cada llamada tarda mas que el tope de tiempo."""

    nombre = "tarda"

    def analizar(self, sistema, pregunta, esquema):
        r = super().analizar(sistema, pregunta, esquema)
        time.sleep(0.35)
        return r

    def redactar(self, sistema, contenido):
        r = super().redactar(sistema, contenido)
        time.sleep(0.35)
        return r


ix, g = fase4.cargar_corpus()
PREGUNTA = "deduccion de cuotas soportadas en vehiculos turismo"


def correr(motor):
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        r = fase4.consultar(PREGUNTA, 2023, motor, ix, g)
    return r, buf.getvalue()


# ---------------------------------------------------- 1. EL TOPE DE LLAMADAS
print("\n=== 1. UN MODELO QUE SIEMPRE FALLA NO PUEDE HACER BUCLE ===")
motor = MotorQueSiempreFalla()
res, _ = correr(motor)
print(f"     llamadas: {motor.llamadas} (tope {motor.tope_llamadas})")
comprobar("para: no se queda dando vueltas",
          motor.llamadas <= motor.tope_llamadas,
          f"{motor.llamadas} > {motor.tope_llamadas}")
comprobar("y termina", res is not None)

print("\n  Para EN el tope, y cuando el tope sobra no se mete.")
print("  Con analisis valido, fase4 pide 3 llamadas en el peor caso.")
for tope, llamadas, quien in ((1, 1, "tope"), (2, 2, "tope"),
                              (3, 3, "la logica"), (6, 3, "la logica")):
    m = MotorQueSiempreFalla(tope_llamadas=tope)
    r, _ = correr(m)
    print(f"     tope {tope}: {m.llamadas} llamada(s), fallo={r.get('fallo')!r} "
          f"(manda {quien})")
    comprobar(f"con tope {tope} hace exactamente {llamadas} llamada(s)",
              m.llamadas == llamadas, f"{m.llamadas}")
    comprobar(f"con tope {tope} para por {quien}",
              (r.get("fallo") == "tope") == (quien == "tope"),
              f"fallo={r.get('fallo')!r}")

# ------------------------------------------------------ 2. EL TOPE DE TIEMPO
print("\n=== 2. EL TOPE DE TIEMPO TAMBIEN PARA ===")
m = MotorQueTarda(tope_llamadas=99, tope_segundos=0.5)
arranque = time.monotonic()
res, _ = correr(m)
tardado = time.monotonic() - arranque
print(f"     {m.llamadas} llamada(s) en {tardado:.1f} s (tope 0,5 s)")
comprobar("para por tiempo, no por llamadas", m.llamadas < 99, f"{m.llamadas}")
comprobar("y no se pasa de largo", tardado < 5, f"{tardado:.1f} s")
comprobar("lo dice como parada por tope", res.get("fallo") == "tope",
          str(res.get("fallo")))
comprobar("y el motivo nombra el tiempo", "s por consulta" in m.motivo_parada,
          m.motivo_parada)

# ------------------------------------------- 3. EL RELOJ ES POR CONSULTA
print("\n=== 3. EL RELOJ SE CUENTA POR CONSULTA, NO POR VIDA DEL MOTOR ===")
print("  El banco reutiliza el mismo motor para varias seguidas; sin esto la")
print("  quinta se pasaria de tiempo por culpa de las cuatro anteriores.")
m = MotorQueSiempreFalla(tope_segundos=2)
correr(m)
primera = m.llamadas
time.sleep(2.2)
correr(m)
comprobar("la segunda consulta vuelve a tener su tiempo entero",
          m.llamadas > primera, f"{primera} -> {m.llamadas}")

# ------------------------------------------------ 4. QUEDA EN LA TRAZA
print("\n=== 4. LA TRAZA DICE CUANTAS LLAMADAS Y POR QUE SE PARO ===")
m = MotorQueSiempreFalla(tope_llamadas=2)
res, _ = correr(m)
traza = Path(res["traza"])
topes = traza / "topes.json"
comprobar("hay un topes.json", topes.is_file(), str(traza))
if topes.is_file():
    d = json.loads(topes.read_text("utf-8"))
    print(f"     {d}")
    comprobar("dice cuantas llamadas", d.get("llamadas") == 2, str(d.get("llamadas")))
    comprobar("dice cual era el tope", d.get("tope_llamadas") == 2)
    comprobar("y POR QUE se paro", "tope" in (d.get("motivo_parada") or ""),
              str(d.get("motivo_parada")))
    comprobar("y cuanto tiempo llevaba",
              isinstance(d.get("segundos"), (int, float)))
cierre = traza / "resultado.json"
if cierre.is_file():
    d = json.loads(cierre.read_text("utf-8"))
    comprobar("el resultado lo marca como PARADA POR TOPE",
              d.get("estado") == "PARADA POR TOPE", str(d.get("estado")))

# --------------------------------- 5. PARADA NO ES FALLO DEL MODELO
print("\n=== 5. PARADA POR TOPE Y FALLO DEL MODELO NO SE CUENTAN IGUAL ===")
print("  «el modelo fallo» manda a mirar la red o la cuenta; «se llego al")
print("  tope» manda a mirar por que hicieron falta tantas llamadas.")
comprobar("la parada se marca como «tope»", res.get("fallo") == "tope",
          str(res.get("fallo")))
comprobar("y NO se ensena ninguna respuesta", not res.get("respuesta"))

# ------------------------------------------------- 6. EL MOTOR DE ENSAYO
print("\n=== 6. EL MOTOR DE ENSAYO PASA POR EL MISMO TECHO ===")
print("  Un tope que solo actua cuando cuesta dinero no se puede probar el")
print("  dia que hace falta.")
m = MOD.crear_motor("ensayo")
m.tope_llamadas = 1
res, _ = correr(m)
comprobar("el tope vale tambien sin gastar", m.llamadas == 1, f"{m.llamadas}")
comprobar("y para por tope", res.get("fallo") == "tope", str(res.get("fallo")))

# --------------------------------- 7. NI UNA ESPERA INDEFINIDA
print("\n=== 7. NI UNA ESPERA INDEFINIDA EN LA RED ===")
print(f"     timeout por llamada : {MOD.TIMEOUT_LLAMADA} s")
print(f"     reintentos de red   : {MOD.REINTENTOS_RED}")
comprobar("hay timeout por llamada, y es finito",
          0 < MOD.TIMEOUT_LLAMADA < 600)
comprobar("hay tope de reintentos de red", 0 < MOD.REINTENTOS_RED <= 5)
fuente = (RAIZ / "agente_fiscal" / "modelo.py").read_text("utf-8")
comprobar("el cliente se crea CON timeout y CON tope de reintentos",
          "timeout=TIMEOUT_LLAMADA" in fuente
          and "max_retries=REINTENTOS_RED" in fuente)

# ----------------------------- 8. CONTROL NEGATIVO: VERLA FALLAR
print("\n=== 8. LA PRUEBA SABE PONERSE ROJA ===")
print("  Ninguna prueba se da por buena sin verla fallar cuando debe fallar.")
print("  Se quita el techo a un motor y se comprueba que ESTA prueba lo pilla.\n")


class MotorSinTecho(MotorQueSiempreFalla):
    """El techo desactivado a proposito: es lo que pasaria si alguien borra
    la llamada a `_permiso`. Tiene que salir ROJO."""

    nombre = "sin-techo"

    def _permiso(self, paso):
        return None


m = MotorSinTecho(tope_llamadas=1)
res, _ = correr(m)
paso_el_techo = m.llamadas > m.tope_llamadas
print(f"     motor sin techo, tope 1: hizo {m.llamadas} llamadas")
comprobar("con el techo quitado se salta el tope (si no, esta prueba no probaria nada)",
          paso_el_techo, f"{m.llamadas} <= {m.tope_llamadas}")
comprobar("y la comprobacion del bloque 1 lo habria cazado",
          not (m.llamadas <= m.tope_llamadas))

print("\n" + "=" * 62)
print(f"FALLOS: {len(fallos)}")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
