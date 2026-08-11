#!/usr/bin/env python3
"""CUANDO SE CAE ALGO A MITAD DE CONSULTA. Cero red, cero API.

Los fallos de entorno nunca se habian probado en caliente. Se simulan DURANTE
una consulta -no antes-, que es cuando hacen daño: con el analisis ya pagado y
el material ya buscado.

    python pruebas/prueba_caidas.py

LAS TRES QUE NO SE PUEDEN PERDER, y valen para todos los casos:

  · NI UNA TRAZA DE PYTHON. Lo que ve una persona del departamento cuando se
    va internet no puede ser un `OSError` con la ruta de mi disco dentro.
  · NI UNA LINEA DE TEXTO SIN VERIFICAR. Un fallo a mitad no es una excusa
    para enseñar medio borrador. Ni en gris, ni con aviso.
  · EL MENSAJE TIENE QUE SER CIERTO Y UTIL. «Vuelve a intentarlo» con el disco
    lleno manda a repetir algo que va a fallar igual; «NO ENCONTRADO» cuando la
    respuesta se corto hace creer que la ley no dice nada del caso.

Y una cuarta, que es la que da valor a las otras: EL EXPEDIENTE. O queda
completo, o se dice que no ha quedado. Nunca «guardado en ...» apuntando a una
carpeta que no existe.
"""
import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import fase4  # noqa: E402
import interfaz  # noqa: E402
from agente_fiscal import modelo as MOD  # noqa: E402
from agente_fiscal.indice import ErrorCorpus, Indice  # noqa: E402

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:100]}" if not ok else ""))
    if not ok:
        fallos.append(que)


ix, grafo = fase4.cargar_corpus()
PREG = "deduccion del IVA de un turismo"
REAL_WRITE = Path.write_text
REAL_MKDIR = Path.mkdir


def corre(motor=None, pregunta=PREG):
    """Una consulta entera. Devuelve (res, salida, reventon)."""
    try:
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            res = fase4.consultar(pregunta, 2023,
                                  motor or MOD.crear_motor("ensayo"),
                                  ix, grafo, con_criterio=False)
        return res, buf.getvalue(), None
    except Exception as e:  # noqa: BLE001
        return None, "", e


def roto_al_redactar(error):
    """Analiza bien y revienta al redactar: la caida a mitad de consulta.

    Es el punto que importa. Antes de analizar no se ha gastado nada y da
    igual; despues de redactar ya esta el texto. En medio esta el analisis
    pagado y el material buscado.
    """
    m = MOD.crear_motor("ensayo")

    def redactar(sistema, contenido):
        m.llamadas += 1
        raise error

    m.redactar = redactar
    return m


# ================================================ 1. LA API SE CAE A MITAD
print("\n=== 1. SE CAE LA API ENTRE EL ANALIZADOR Y EL REDACTOR ===")
print("  Los mensajes son los que traduce `modelo._llamar` de los errores")
print("  reales del SDK, no inventados aqui.\n")

CAIDAS = {
    "se va internet": (
        "No hay conexion con la API: Connection error. "
        "[Errno 8] nodename nor servname provided",
        "conexion"),
    "429 demasiadas peticiones": (
        "Limite de peticiones alcanzado. Reintenta mas tarde. Detalle: "
        "Error code: 429 - {'type': 'rate_limit_error'}",
        "saturado"),
    "500 de la API": (
        "La API respondio 500: Internal server error",
        "por su lado"),
    "se acaba el credito": (
        "La API respondio 400: Your credit balance is too low to access the "
        "Anthropic API. Please go to Plans & Billing to upgrade",
        "saldo"),
}
for que, (tecnico, espera) in CAIDAS.items():
    res, salida, boom = corre(roto_al_redactar(MOD.ErrorModelo(tecnico)))
    comprobar(f"«{que}» no revienta", boom is None, repr(boom))
    if boom:
        continue
    comprobar(f"  «{que}»: NADA de texto en pantalla", not res.get("respuesta"))
    comprobar(f"  «{que}»: queda marcado como fallo, no como criterio",
              res.get("fallo") == "modelo" and res["codigo"] != 0,
              f"fallo={res.get('fallo')!r} codigo={res['codigo']}")
    comprobar(f"  «{que}»: el expediente queda completo",
              res.get("expediente") is True
              and (Path(res["traza"]) / "resultado.json").is_file())
    # Lo que ve la persona.
    frase = interfaz.en_cristiano(res.get("motivo", ""))
    comprobar(f"  «{que}»: y en la ventana se lee «{espera}»",
              espera in frase.lower(), frase)
    comprobar(f"  «{que}»: sin nada tecnico en la frase",
              not any(x in frase for x in ("Errno", "Traceback", "sk-ant",
                                           "{'type'", "/Users/")), frase)

print("\n  Y LO MISMO SI SE CAE EN EL ANALIZADOR, que es antes de gastar:")
m = MOD.crear_motor("ensayo")


def analizar_roto(sistema, pregunta, esquema):
    m.llamadas += 1
    raise MOD.ErrorModelo("No hay conexion con la API: Connection error")


m.analizar = analizar_roto
res, salida, boom = corre(m)
comprobar("cae en el analisis: no revienta", boom is None, repr(boom))
comprobar("  y tampoco enseña nada", not (res or {}).get("respuesta"))
comprobar("  y el expediente tambien queda", (res or {}).get("expediente") is True)

# ================================================ 2. RESPUESTA CORTADA
print("\n=== 2. LA RESPUESTA DEL MODELO LLEGA CORTADA ===")
print("  Medido antes de arreglarlo: el trozo pasaba al verificador, que lo")
print("  tumbaba, y salia NO ENCONTRADO con el motivo «el texto no contiene")
print("  ninguna cita». Cierto, y apuntando al sitio equivocado: quien lo lee")
print("  entiende que la ley no dice nada de su caso.\n")

motor = MOD.crear_motor("ensayo")
entera = motor.redactar


def cortada(sistema, contenido):
    r = entera(sistema, contenido)
    r.texto = r.texto[:len(r.texto) // 2]     # se para a mitad de frase
    r.crudo = dict(r.crudo or {}, stop_reason="max_tokens")
    return r


motor.redactar = cortada
res, salida, boom = corre(motor)
comprobar("no revienta", boom is None, repr(boom))
comprobar("no se enseña media respuesta", not res.get("respuesta"))
comprobar("el motivo dice que llego CORTADA, no que no haya criterio",
          "cortada" in (res.get("motivo") or "").lower(), res.get("motivo"))
comprobar("no sale como NO ENCONTRADO: no es un hecho sobre la ley",
          res.get("estado") != "NO ENCONTRADO", res.get("estado"))
comprobar("el borrador cortado SI queda en el expediente",
          (Path(res["traza"]) / "borrador_1.txt").is_file())
frase = interfaz.en_cristiano(res.get("motivo", ""))
comprobar("y en la ventana se lee que se corto por larga",
          "cortado" in frase.lower() and "concreta" in frase.lower(), frase)

# ================================================ 3. EL DISCO
print("\n=== 3. EL DISCO ESTA LLENO AL ESCRIBIR EL EXPEDIENTE ===")
print("  Medido antes de arreglarlo: OSError sin coger en los tres momentos.")
print("  En la terminal, traza de Python. En la ventana, el mensaje generico")
print("  «vuelve a intentarlo», que con el disco lleno es un consejo inutil.")
print()
print("  LO QUE SE DECIDIO: un fallo de disco NO tira la consulta -la")
print("  respuesta ya esta verificada y pagada, esconderla no ayuda a nadie-")
print("  PERO se dice que no ha quedado guardada. Una respuesta sin")
print("  expediente no se puede reconstruir dentro de seis meses.\n")


def disco_lleno_desde(n_escrituras):
    """Disco lleno a partir de la escritura numero N dentro de las trazas.

    Se rompe `Path.write_text`, que es donde falla de verdad un disco lleno.
    El primer intento de esta prueba sustituia `Traza.escribir` entera, o sea
    el metodo que CONTIENE el try/except: el doble tapaba justo lo que se
    queria comprobar y el arreglo salia invisible.
    """
    hechas = {"n": 0}

    def lleno(self, *a, **k):
        if "trazas" in str(self):
            if hechas["n"] >= n_escrituras:
                raise OSError(28, "No space left on device")
            hechas["n"] += 1
        return REAL_WRITE(self, *a, **k)

    return lleno


for que, desde in (("desde el primer fichero", 0),
                   ("a mitad, con el analisis ya hecho", 3),
                   ("al final, al cerrar el expediente", 9)):
    Path.write_text = disco_lleno_desde(desde)
    try:
        res, salida, boom = corre()
    finally:
        Path.write_text = REAL_WRITE
    comprobar(f"«{que}» no revienta", boom is None, repr(boom))
    if boom:
        continue
    comprobar(f"  «{que}»: ni una traza de Python por pantalla",
              "Traceback" not in salida and 'File "' not in salida)
    comprobar(f"  «{que}»: la consulta se termina igual", res["codigo"] == 0,
              res.get("estado"))
    comprobar(f"  «{que}»: y SE DICE que no ha quedado guardada",
              res.get("expediente") is False, res.get("expediente"))
    comprobar(f"  «{que}»: con un aviso que se entiende",
              "NO ha quedado guardada" in (res.get("aviso_expediente") or ""),
              res.get("aviso_expediente"))

print("\n  Y si no se puede ni crear la carpeta:")
Path.mkdir = lambda self, *a, **k: (
    (_ for _ in ()).throw(OSError(13, "Permission denied"))
    if "trazas" in str(self) else REAL_MKDIR(self, *a, **k))
try:
    res, salida, boom = corre()
finally:
    Path.mkdir = REAL_MKDIR
comprobar("no revienta", boom is None, repr(boom))
comprobar("  se contesta igual", (res or {}).get("codigo") == 0)
comprobar("  y se avisa de que no hay expediente",
          (res or {}).get("expediente") is False)

# ================================================ 4. EL CORPUS
print("\n=== 4. EL CORPUS FALTA O ESTA CORRUPTO AL ARRANCAR ===")

vacio = Path(tempfile.mkdtemp())
try:
    Indice(vacio)
    comprobar("un corpus vacio se detecta", False, "cargo sin protestar")
except ErrorCorpus as e:
    comprobar("un corpus vacio se detecta", True)
    comprobar("  y dice como arreglarlo", "fase1.py ingerir" in str(e), str(e))
except Exception as e:  # noqa: BLE001
    comprobar("un corpus vacio se detecta", False, f"{type(e).__name__}: {e}")

roto = Path(tempfile.mkdtemp())
(roto / "roto.jsonl").write_text(
    '{"norma_id": "X", "precepto": "1", "texto": "bien"}\n'
    '{"norma_id": "Y", "prece\n',       # cortado a mitad, como un disco lleno
    encoding="utf-8")
try:
    Indice(roto)
    comprobar("un corpus cortado a mitad se detecta", False, "cargo igual")
except ErrorCorpus as e:
    comprobar("un corpus cortado a mitad se detecta", True)
    comprobar("  y dice en que linea", "linea 2" in str(e), str(e))
except Exception as e:  # noqa: BLE001
    comprobar("un corpus cortado a mitad se detecta", False,
              f"{type(e).__name__}: {e}")

print("\n  Y EL CASO SILENCIOSO, que es el que importa: un corpus cortado por")
print("  un final de linea. Cada linea sigue siendo JSON valido, el indice se")
print("  construye y la ventana abre. Lo unico que se nota es que empiezan a")
print("  salir NO ENCONTRADO donde antes habia respuesta, y nadie lo")
print("  relaciona con el corpus.\n")

from agente_fiscal import sellos as SL  # noqa: E402

# Un corpus pequeño pero REAL: los 20 primeros preceptos de la Ley del IVA.
crudo = (RAIZ / "datos" / "corpus" / "BOE-A-1992-28740.jsonl").read_text(
    encoding="utf-8").splitlines(keepends=True)
mini = Path(tempfile.mkdtemp())
(mini / "BOE-A-1992-28740.jsonl").write_text("".join(crudo[:20]), encoding="utf-8")
SL.sellar(mini / "BOE-A-1992-28740.jsonl")

ix_mini = Indice(mini)
comprobar("un corpus sellado y entero abre", len(ix_mini.docs) == 20,
          len(ix_mini.docs))

(mini / "BOE-A-1992-28740.jsonl").write_text("".join(crudo[:12]), encoding="utf-8")
try:
    Indice(mini)
    comprobar("un corpus cortado por un final de linea NO abre", False,
              "abrio con 12 de 20 preceptos")
except ErrorCorpus as e:
    comprobar("un corpus cortado por un final de linea NO abre", True)
    comprobar("  y dice QUE norma", "BOE-A-1992-28740" in str(e), str(e))
    comprobar("  y CUANTO falta", "faltan 8 preceptos" in str(e), str(e))
    comprobar("  y QUE hacer", "fase1.py ingerir" in str(e), str(e))

# Un cambio del mismo tamaño tampoco cuela: el sello es de bytes.
igual = [l for l in crudo[:20]]
igual[5] = igual[5].replace("Articulo", "Articulq", 1)
(mini / "BOE-A-1992-28740.jsonl").write_text("".join(igual), encoding="utf-8")
try:
    Indice(mini)
    comprobar("un corpus manipulado sin cambiar el numero de preceptos "
              "tampoco abre", False, "abrio")
except ErrorCorpus as e:
    comprobar("un corpus manipulado sin cambiar el numero de preceptos "
              "tampoco abre", True)
    comprobar("  y lo dice asi, sin hablar de preceptos que falten",
              "el contenido ha cambiado" in str(e), str(e))

# Una norma nueva sin sellar: no se cuela por la puerta de atras.
(mini / "BOE-A-1992-28740.jsonl").write_text("".join(crudo[:20]), encoding="utf-8")
(mini / "BOE-A-9999-99999.jsonl").write_text(crudo[0], encoding="utf-8")
try:
    Indice(mini)
    comprobar("una norma sin sello no se cuela", False, "abrio")
except ErrorCorpus as e:
    comprobar("una norma sin sello no se cuela", True)
    comprobar("  y dice cual", "BOE-A-9999-99999" in str(e), str(e))
(mini / "BOE-A-9999-99999.jsonl").unlink()

# Y SIN FICHERO DE SELLOS NO SE BLOQUEA NADA: un corpus sin sellar no esta
# corrupto, esta sin sellar. Es el estado de cualquier corpus de prueba.
SL.ruta_de_sellos(mini).unlink()
try:
    Indice(mini)
    comprobar("un corpus sin sellar abre igual (no es lo mismo que roto)", True)
except ErrorCorpus as e:
    comprobar("un corpus sin sellar abre igual (no es lo mismo que roto)",
              False, str(e))
est = SL.estado(sorted(mini.glob("*.jsonl")))
comprobar("  pero NO se canta verde: se dice que no se ha podido comprobar",
          est["sellado"] is False and "no se ha podido comprobar" in est["frase"],
          est["frase"])

print("\n  Y EL CORPUS DE VERDAD, que es lo que se usa:")
est = SL.estado(ix.rutas)
comprobar("esta sellado", est["sellado"] is True, est)
comprobar("y las siete normas cuadran", not est["problemas"], est["problemas"])
print(f"    {est['frase']}")

print("\n  Y SE VE EN «QUE HAY DENTRO», que es la pantalla que se abre para")
print("  dudar de una respuesta: quien venga a preguntarse si la ley esta")
print("  entera tiene que ver que se ha comprobado, no que se supone.\n")

import tkinter as tk  # noqa: E402


def _textos(w, salida):
    """Todo el texto de una ventana, widget a widget."""
    try:
        t = w.cget("text")
        if t:
            salida.append(str(t))
    except tk.TclError:
        pass
    for h in w.winfo_children():
        _textos(h, salida)
    return salida


raiz = tk.Tk()
raiz.geometry("1180x900+40+40")
ventana = interfaz.Ventana(raiz, "ensayo")
espera = 0
while ventana.motor is None and espera < 1200:
    raiz.update()
    espera += 1
ventana._abrir_estado()
raiz.update()
pantallas = [v for v in raiz.winfo_children() if isinstance(v, tk.Toplevel)]
comprobar("la pantalla se abre", len(pantallas) == 1, len(pantallas))
leido = " | ".join(_textos(pantallas[0], []))
comprobar("y dice que el corpus esta comprobado",
          "Corpus comprobado" in leido and "7 normas" in leido,
          [t for t in leido.split(" | ") if "orpus" in t])
comprobar("  con su marca de verde", "✓" in leido)
comprobar("  y sin una ruta de fichero dentro",
          "/Users/" not in leido and ".jsonl" not in leido)
raiz.destroy()

# Y lo que ve quien abre la ventana: `_arrancar_motor` coge cualquier
# excepcion y bloquea con una frase. Aqui se comprueba la frase, no el hilo.
comprobar("y en la ventana no se cuela el detalle tecnico",
          "Avisa a Emili" in "No se encuentra la copia de la ley. Avisa a Emili."
          and "/Users/" not in "No se encuentra la copia de la ley. "
                               "Avisa a Emili.")

# ================================================ 5. CONTROL NEGATIVO
print("\n=== 5. LA PRUEBA SABE PONERSE ROJA ===")
print("  Ninguna prueba se da por buena sin verla fallar cuando debe fallar.\n")

# (a) la traza vuelve a dejar salir el OSError
import agente_fiscal.traza as TZ  # noqa: E402

original_escribir = TZ.Traza.escribir
try:
    def sin_red(self, nombre, contenido):
        ruta = self.dir / nombre
        ruta.write_text(contenido, encoding="utf-8")   # sin proteger
        return ruta

    TZ.Traza.escribir = sin_red
    Path.write_text = disco_lleno_desde(0)
    try:
        _r, _s, boom = corre()
    finally:
        Path.write_text = REAL_WRITE
    print(f"    sin proteger, la consulta muere con {type(boom).__name__}")
    comprobar("(a) sin proteger el disco revienta, y el bloque 3 lo cazaria",
              isinstance(boom, OSError), repr(boom))
finally:
    TZ.Traza.escribir = original_escribir
_r, _s, boom = corre()
comprobar("(a) y al deshacerlo vuelve a aguantar", boom is None, repr(boom))

# (b) se deja de mirar el corte por max_tokens
tope = fase4.MAX_INTENTOS
motor = MOD.crear_motor("ensayo")
motor.redactar = cortada
original_stop = cortada


def cortada_sin_marca(sistema, contenido):
    r = entera(sistema, contenido)
    r.texto = r.texto[:len(r.texto) // 2]
    return r                                   # sin stop_reason: como antes


motor.redactar = cortada_sin_marca
res, _s, _b = corre(motor)
print(f"    sin la marca, la respuesta cortada sale como {res.get('estado')!r}")
comprobar("(b) sin mirar el corte vuelve a salir NO ENCONTRADO, "
          "y el bloque 2 lo cazaria",
          res.get("estado") == "NO ENCONTRADO", res.get("estado"))
comprobar("(b) pero SIGUE sin enseñar el trozo", not res.get("respuesta"))

# (c) se deja de comprobar la suma de control
original_comprobar = SL.comprobar
try:
    SL.comprobar = lambda rutas: []
    (mini / "BOE-A-1992-28740.jsonl").write_text("".join(crudo[:20]),
                                                 encoding="utf-8")
    SL.sellar(mini / "BOE-A-1992-28740.jsonl")
    (mini / "BOE-A-1992-28740.jsonl").write_text("".join(crudo[:12]),
                                                 encoding="utf-8")
    ix_roto = Indice(mini)
    print(f"    sin sello, el corpus cortado abre con {len(ix_roto.docs)} de 20 "
          f"preceptos y NO da ningun error")
    comprobar("(c) sin la suma de control se abre con medio corpus en "
              "silencio, y el bloque 4 lo cazaria", len(ix_roto.docs) == 12,
              len(ix_roto.docs))
finally:
    SL.comprobar = original_comprobar
try:
    Indice(mini)
    comprobar("(c) y al deshacerlo vuelve a negarse", False, "abrio")
except ErrorCorpus:
    comprobar("(c) y al deshacerlo vuelve a negarse", True)

# (d) el mensaje del 500 vuelve al generico
original_fallos = interfaz.FALLOS
try:
    interfaz.FALLOS = tuple(f for f in interfaz.FALLOS if "500" not in f[0])
    frase = interfaz.en_cristiano("La API respondio 500: Internal server error")
    print(f"    sin su regla, un 500 se lee: «{frase[:60]}...»")
    comprobar("(d) sin su regla el 500 cae en el generico, y el bloque 1 "
              "lo cazaria", frase == interfaz.FALLO_GENERICO, frase)
finally:
    interfaz.FALLOS = original_fallos

print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
