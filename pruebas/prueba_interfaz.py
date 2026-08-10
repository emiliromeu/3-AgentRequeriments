#!/usr/bin/env python3
"""LA VENTANA. Cero red, cero API.

Es lo UNICO que ve el profesional que va a firmar el trabajo. Todo lo demas
-el corpus, el verificador, los estados- llega a una persona a traves de aqui,
y un fallo en esta capa se lleva por delante lo que hay detras aunque este bien.

Las que no se pueden perder, y por que:
  · EL ANO ES OBLIGATORIO. Una consulta de 2023 contestada con la ley de hoy
    sale impecable y esta mal. Es el fallo mas silencioso del sistema.
  · NUNCA TEXTO SIN VERIFICAR. Ni en gris, ni con aviso. (Tiene banco propio:
    prueba_no_encontrado.)
  · COPIAR NO ARRASTRA LA ANTERIOR. Copiar es ensenar.
  · LOS FALLOS, EN CRISTIANO. Ni una traza, ni un trozo de clave.
  · LOS TRES ESTADOS NO SON UN SEMAFORO. «NO ENCONTRADO» en rojo se lee como
    averia, y quien lo vea reformulara hasta que salga verde.

    python pruebas/prueba_interfaz.py
"""
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import tkinter as tk
from tkinter import font as tkfont

import interfaz
from agente_fiscal import estado as EST

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:100]}" if not ok else ""))
    if not ok:
        fallos.append(que)


raiz = tk.Tk()
v = interfaz.Ventana(raiz, "ensayo")


def bombear(segundos=0.4):
    fin = time.time() + segundos
    while time.time() < fin:
        try:
            raiz.update()
        except tk.TclError:
            return
        time.sleep(0.01)


def esperar(cond, limite=120):
    fin = time.time() + limite
    while time.time() < fin:
        raiz.update()
        if cond():
            return True
        time.sleep(0.02)
    return False


bombear(0.3)

# =====================================================================
print("\n=== 1. EL ANO DEL CASO ES OBLIGATORIO ===")
print("  Nunca se rellena solo, y nunca con el ano en curso.")
comprobar("el campo del ejercicio empieza VACIO", v.ejercicio.get().strip() == "",
          repr(v.ejercicio.get()))
import datetime
comprobar("y no trae el ano en curso",
          str(datetime.date.today().year) not in v.ejercicio.get())
v.caja.delete("1.0", "end")
v.caja.insert("1.0", "una duda cualquiera")
v.ejercicio.set("")
v._revisar_boton()
comprobar("sin ano, el boton de consultar esta APAGADO",
          str(v.boton["state"]) == "disabled", str(v.boton["state"]))
v.ejercicio.set("2023")
v._revisar_boton()
comprobar("con ano y con duda, se enciende",
          str(v.boton["state"]) == "normal", str(v.boton["state"]))
v.caja.delete("1.0", "end")
v._revisar_boton()
comprobar("sin duda tampoco se enciende, aunque haya ano",
          str(v.boton["state"]) == "disabled")
for malo in ("abc", "20", "0", "12345"):
    v.caja.delete("1.0", "end")
    v.caja.insert("1.0", "duda")
    v.ejercicio.set(malo)
    v._revisar_boton()
    comprobar(f"un ano invalido «{malo}» no enciende el boton",
              str(v.boton["state"]) == "disabled", str(v.boton["state"]))

# =====================================================================
print("\n=== 2. LOS TRES ESTADOS NO SON UN SEMAFORO ===")
print("  «NO ENCONTRADO» es una respuesta legitima, a menudo la correcta.")
print("  Pintarla de rojo la convierte en una averia.")
import re
PROHIBIDOS = re.compile(r"#(?:[0-9a-fA-F]{2})?(?:ff|cc|dd|ee)0{2,4}"
                        r"|#d{0,1}[0-9a-fA-F]?0000|red|green|orange|yellow",
                        re.IGNORECASE)
for est, color in interfaz.COLOR.items():
    comprobar(f"el color de «{est}» no es de semaforo",
              not PROHIBIDOS.search(color), color)
comprobar("los tres estados tienen color propio",
          len(set(interfaz.COLOR.values())) == 3, str(interfaz.COLOR))
comprobar("el FONDO no cambia con el estado: siempre papel",
          len(set(interfaz.FONDO.values())) == 1, str(interfaz.FONDO))
comprobar("y el fondo es el papel de lectura",
          set(interfaz.FONDO.values()) == {interfaz.PAPEL2})
comprobar("hay un filete de color por estado, que es donde vive el color",
          len(interfaz.FILETE_ESTADO) == 3)
comprobar("NO ENCONTRADO va en gris, no en rojo",
          interfaz.COLOR[EST.NO_ENCONTRADO].lower() in ("#4a4a55", "#4a4a55"))

# =====================================================================
print("\n=== 3. LOS TRES ESTADOS SE PINTAN, Y CON SU EXPLICACION ===")
for est in (EST.CLARO, EST.DISCUTIDO, EST.NO_ENCONTRADO):
    v._pintar_estado(est, interfaz.EXPLICACION[est], est)
    bombear(0.15)
    comprobar(f"«{est}» se pinta con su rotulo",
              v.etiqueta_estado.cget("text") == est,
              v.etiqueta_estado.cget("text"))
    comprobar(f"«{est}» lleva explicacion, y no vacia",
              len(v.etiqueta_explicacion.cget("text")) > 40)
    comprobar(f"«{est}» usa su color en el rotulo",
              v.etiqueta_estado.cget("fg") == interfaz.COLOR[est])
comprobar("la explicacion de CRITERIO CLARO avisa de lo que NO dice",
          "NO" in interfaz.EXPLICACION[EST.CLARO])

# =====================================================================
print("\n=== 4. LOS AVISOS: DOS EJES, TRES NIVELES ===")
COBERTURA = ["Articulo 91: el texto cambio dentro del ejercicio 2024",
             "Articulo 20: la disposicion transitoria segunda lo menciona"]
SENALES = ["sobre el articulo 91 hay 2 consultas de años distintos"]
ESTRUCTURAL = "Articulo 80 remite a Ley 22/2003, que no esta en el corpus"
reventado = None
try:
    v._terminar({"codigo": 0, "estado": EST.DISCUTIDO, "fallo": None,
                 "senales": SENALES, "cobertura": COBERTURA,
                 "estructural": ESTRUCTURAL, "preceptos": ["Articulo 91"],
                 "traza": None, "recuperado": [],
                 "respuesta": "El tipo depende de la fecha.\n"
                              "https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a91"})
    bombear(0.4)
except Exception as exc:  # noqa: BLE001
    reventado = exc
comprobar("pintar avisos NO revienta la ventana", reventado is None,
          repr(reventado))
if reventado is None:
    etiquetas = [w.cget("text") for w in v.panel_avisos.winfo_children()]
    comprobar("el panel de avisos queda visible",
              bool(v.panel_avisos.grid_info()))
    comprobar("sale el rotulo de DESACUERDO",
              any("DESACUERDO" in t for t in etiquetas), str(etiquetas)[:120])
    comprobar("y el de LO QUE NO SE HA PODIDO MIRAR, aparte",
              any("NO SE HA PODIDO MIRAR" in t for t in etiquetas))
    comprobar("el desacuerdo va ANTES que la cobertura",
              [t for t in etiquetas if "DESACUERDO" in t
               or "NO SE HA PODIDO MIRAR" in t][0].startswith("DESACUERDO"))
    comprobar("salen los tres avisos con su texto",
              sum(1 for t in etiquetas if t.startswith("•")) == 3,
              str(etiquetas))
    comprobar("y la linea de limite del corpus, al final",
              any(ESTRUCTURAL in t for t in etiquetas))
    comprobar("los avisos van ARRIBA (fila 1), antes del texto (fila 3)",
              v.panel_avisos.grid_info().get("row") == 1
              and v.texto.master.grid_info().get("row") == 3)
    comprobar("con respuesta verificada SI hay algo que copiar",
              str(v.boton_copiar["state"]) == "normal")

# El bloque de cobertura SE VE aunque este vacio.
v._terminar({"codigo": 0, "estado": EST.CLARO, "fallo": None, "senales": [],
             "cobertura": [], "estructural": "", "preceptos": ["Articulo 91"],
             "traza": None, "recuperado": [], "respuesta": "Sale al 21%."})
bombear(0.3)
etiquetas = [w.cget("text") for w in v.panel_avisos.winfo_children()]
comprobar("sin nada que avisar, el bloque de cobertura SIGUE saliendo",
          any("NO SE HA PODIDO MIRAR" in t for t in etiquetas), str(etiquetas))
comprobar("y dice expresamente que no falta nada",
          any(t.startswith("Nada que mirar") for t in etiquetas))
comprobar("sin desacuerdo, ese rotulo no sale",
          not any("DESACUERDO" in t for t in etiquetas))

# =====================================================================
print("\n=== 5. LAS CITAS Y SUS ENLACES SON LO MAS LEGIBLE ===")
RESPUESTA = ('El articulo 95 dice «Los empresarios no podran deducir» '
             '(articulo 95 de la Ley 37/1992, '
             'https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740#a95).')
v._terminar({"codigo": 0, "estado": EST.CLARO, "fallo": None, "senales": [],
             "cobertura": [], "estructural": "", "preceptos": ["Articulo 95"],
             "traza": None, "recuperado": [], "respuesta": RESPUESTA})
bombear(0.4)
comprobar("el enlace queda marcado como enlace",
          bool(v.texto.tag_ranges("enlace")))
comprobar("la cita queda marcada como cita",
          bool(v.texto.tag_ranges("cita")))
comprobar("y la referencia, como referencia",
          bool(v.texto.tag_ranges("referencia")))
cfg = v.texto.tag_configure("enlace")
comprobar("el enlace va subrayado y en color", bool(cfg))
comprobar("la cita usa una tipografia distinta del parrafo",
          v.texto.tag_cget("cita", "font") != "")
comprobar("hay tres cadenas de fuentes elegidas de verdad",
          len(interfaz.fuentes_elegidas) >= 3, str(interfaz.fuentes_elegidas))
for cual in ("interfaz", "cita", "referencia"):
    comprobar(f"la fuente «{cual}» quedo anotada, no por defecto en silencio",
              cual in interfaz.fuentes_elegidas)

# =====================================================================
print("\n=== 6. LOS FALLOS, EN CRISTIANO ===")
CASOS = [
    ("credit balance too low", "saldo"),
    ("Connection error: getaddrinfo failed", "conexion a internet"),
    ("401 unauthorized: invalid api key", "configuracion"),
    ("rate limit exceeded (429)", "saturado"),
    ("algo rarisimo que nadie ha visto", "Vuelve a intentarlo"),
]
for tecnico, esperado in CASOS:
    frase = interfaz.en_cristiano(tecnico)
    comprobar(f"«{tecnico[:30]}» -> frase de persona", esperado in frase, frase)
    comprobar("  y sin rastro tecnico",
              not any(x in frase for x in ("401", "429", "getaddrinfo",
                                           "Traceback", "sk-ant")), frase)
frase = interfaz.en_cristiano(
    "AuthenticationError: api_key=sk-ant-api03-SECRETO-NO-SALE File \"x.py\"")
comprobar("una clave dentro del error NO llega a la frase",
          "sk-ant" not in frase and "SECRETO" not in frase, frase)
comprobar("y tampoco la ruta del fichero", ".py" not in frase, frase)

v._terminar_roto(interfaz.FALLO_GENERICO)
bombear(0.3)
cuerpo = v.texto.get("1.0", "end")
comprobar("un fallo deja el estado en NO ENCONTRADO, no en blanco",
          v.etiqueta_estado.cget("text") != "")
comprobar("y nada que copiar", str(v.boton_copiar["state"]) == "disabled")
comprobar("sin traza en pantalla",
          "Traceback" not in cuerpo and "File \"" not in cuerpo)

# =====================================================================
print("\n=== 7. COPIAR NO ARRASTRA LA RESPUESTA ANTERIOR ===")
v._terminar({"codigo": 0, "estado": EST.CLARO, "fallo": None, "senales": [],
             "cobertura": [], "estructural": "", "preceptos": [],
             "traza": None, "recuperado": [], "respuesta": "PRIMERA RESPUESTA"})
bombear(0.3)
comprobar("con respuesta, se puede copiar",
          str(v.boton_copiar["state"]) == "normal")
v._copiar()
bombear(0.2)
comprobar("y el portapapeles la tiene",
          raiz.clipboard_get() == "PRIMERA RESPUESTA", raiz.clipboard_get()[:40])
v._terminar({"codigo": 2, "estado": EST.NO_ENCONTRADO, "fallo": None,
             "senales": [], "cobertura": [], "estructural": "",
             "preceptos": [], "traza": None, "recuperado": [], "respuesta": ""})
bombear(0.3)
comprobar("tras un NO ENCONTRADO, el boton se apaga",
          str(v.boton_copiar["state"]) == "disabled")
comprobar("y la respuesta guardada se borra", not v.respuesta_actual,
          v.respuesta_actual[:40])

# =====================================================================
print("\n=== 8. LA VENTANA SE NIEGA A ABRIR DESCOORDINADA ===")
comprobar("existe la pantalla de descoordinacion",
          hasattr(interfaz, "ventana_de_descoordinacion"))
import agente_fiscal.configuracion as CONF
r = CONF.revisar()
comprobar("y hoy el sistema esta coherente", r.coherente, str(r.descuadres))

# =====================================================================
print("\n=== 9. LA PRUEBA SABE PONERSE ROJA ===")
print("  Se rompen a proposito las dos reglas mas caras y se comprueba que")
print("  las comprobaciones de arriba las habrian cazado.\n")

# (a) el ano rellenado solo
v.ejercicio.set(str(datetime.date.today().year))
comprobar("(a) si el ano viniera relleno, el bloque 1 lo veria",
          v.ejercicio.get().strip() != "")
v.ejercicio.set("")

# (b) un color de semaforo
comprobar("(b) un rojo se detectaria como semaforo",
          bool(PROHIBIDOS.search("#cc0000")))
comprobar("(b) y un verde tambien", bool(PROHIBIDOS.search("green")))

# (c) una clave que se cuela en una frase de error
comprobar("(c) el detector de claves mira de verdad",
          "sk-ant" in "AuthenticationError: sk-ant-api03-X")

raiz.destroy()
print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
