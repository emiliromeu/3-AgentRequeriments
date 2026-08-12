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

def tecla(k):
    """Pulsa una tecla en la respuesta, con el foco garantizado.

    EL FALLO DE FOCO, CERRADO EN UN SOLO SITIO. Corriendo sin nadie delante la
    ventana no es la activa y el sistema le quita el foco ENTRE tecla y tecla:
    `event_generate` se pierde en silencio y la comprobacion sale roja sin que
    nada este mal. Estaba puesto a mano en unos bloques y no en otros, y por eso
    fallaba una de cada tres ejecuciones, con una tecla distinta cada vez.
    """
    # Se comprueba QUE LA TECLA HA LLEGADO, y si no, se reintenta UNA vez.
    #
    # `focus_force` no basta: el sistema puede quitarle el foco a la ventana
    # entre el force y el evento, y entonces `event_generate` se pierde sin
    # error. Medido: fallaba una de cada tres ejecuciones, con una tecla
    # distinta cada vez, lo que la hacia parecer un fallo del scroll.
    #
    # Se mira la vista antes y despues: si no se ha movido NADA, o el foco no
    # esta donde tiene que estar, se repite. Un solo reintento; si tampoco
    # llega, la comprobacion sale roja, que es lo correcto.
    for intento in (1, 2):
        antes_de = v.lienzo_lectura.yview()
        raiz.focus_force()
        v.texto.focus_set()
        bombear(0.2)
        if str(raiz.focus_get() or "") != str(v.texto):
            continue
        v.texto.event_generate(k, when="now")
        bombear(0.3)
        if v.lienzo_lectura.yview() != antes_de or k in ("<Home>",):
            return


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
# ESTA COMPROBACION ESTABA ATADA A UN LITERAL, Y ERA UN ERROR MIO.
#
# Decia `COLOR[NO_ENCONTRADO] == "#4a4a55"`, que es el gris del modo claro. Al
# pasar la ventana a oscuro habia que elegir entre un gris ilegible sobre negro
# -contraste 2,2:1- o tocar la prueba. Ninguna de las dos, porque el literal no
# era la expectativa: la expectativa es que NO SEA UN COLOR DE ALARMA.
#
# Asi que se comprueba eso y no el hex. Es MAS estricto que antes -pilla un
# rojo, un ambar y un verde, no solo un hex distinto- y sobrevive al siguiente
# cambio de paleta, que es lo que tiene que hacer una prueba de diseño.
def _rgb(hexadecimal):
    h = hexadecimal.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


r, g, b = _rgb(interfaz.COLOR[EST.NO_ENCONTRADO])
croma = max(r, g, b) - min(r, g, b)
comprobar("NO ENCONTRADO va en GRIS: los tres canales casi iguales",
          croma <= 30, f"{interfaz.COLOR[EST.NO_ENCONTRADO]} croma={croma}")
comprobar("y no tira a rojo ni a ambar", not (r > g + 12 and r > b + 12),
          interfaz.COLOR[EST.NO_ENCONTRADO])
# Y QUE SE LEA, que es lo que fallaba: el gris del modo claro sobre el fondo
# oscuro da 159 en esta escala y es ilegible. El umbral esta puesto por encima
# de ese caso a proposito, no al tuntun: si alguien vuelve a poner un color de
# la paleta que no toca, esta linea se pone roja.
contraste = abs(sum(_rgb(interfaz.COLOR[EST.NO_ENCONTRADO]))
                - sum(_rgb(interfaz.PAPEL2)))
comprobar("y se lee: contraste suficiente contra su fondo",
          contraste > 250,
          f"{interfaz.COLOR[EST.NO_ENCONTRADO]} sobre {interfaz.PAPEL2}: "
          f"{contraste}")

# =====================================================================
print("\n=== 3. LOS TRES ESTADOS SE PINTAN, Y CON LA EXPLICACION DE SU BOTON ===")
print("  Desde que hay dos botones, el MISMO estado no significa lo mismo: un")
print("  CRITERIO CLARO de ley sola no ha mirado la doctrina, y tiene que")
print("  decirlo. La explicacion depende del estado Y del boton que se pulso.")
for est in (EST.CLARO, EST.DISCUTIDO, EST.NO_ENCONTRADO):
    for con_criterio in (False, True):
        texto = interfaz.explicacion(est, con_criterio)
        v._pintar_estado(est, texto, est)
        bombear(0.10)
        comprobar(f"«{est}» se pinta con su rotulo",
                  v.etiqueta_estado.cget("text") == est,
                  v.etiqueta_estado.cget("text"))
        comprobar(f"«{est}» lleva explicacion, y no vacia",
                  len(v.etiqueta_explicacion.cget("text")) > 40)
        comprobar(f"«{est}» usa su color en el rotulo",
                  v.etiqueta_estado.cget("fg") == interfaz.COLOR[est])
    comprobar(f"«{est}» NO dice lo mismo con un boton que con el otro",
              interfaz.explicacion(est, False) != interfaz.explicacion(est, True),
              interfaz.explicacion(est, False)[:70])
comprobar("la explicacion de CRITERIO CLARO avisa de lo que NO dice",
          "NO" in interfaz.explicacion(EST.CLARO, True))
comprobar("y con el boton de ley sola dice que la doctrina no se ha mirado",
          "no se ha" in interfaz.explicacion(EST.CLARO, False).lower()
          or "sin mirar" in interfaz.explicacion(EST.CLARO, False).lower(),
          interfaz.explicacion(EST.CLARO, False))

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
              bool(v.panel_avisos.winfo_ismapped()))
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
    # EL ORDEN SE MIDE EN LA PANTALLA, NO EN EL `grid`.
    #
    # Esto comparaba numeros de fila. Valia mientras el estado, el aporte, los
    # avisos y el texto eran cuatro filas de una columna; desde que la banda de
    # arriba va en DOS COLUMNAS, el numero de fila ya no dice quien se lee
    # antes -y encima el aporte no esta ni gestionado por `grid`-.
    #
    # Lo que hay que garantizar no ha cambiado ni un apice: que los avisos se
    # vean ANTES que el texto, porque son lo que puede invalidarlo. Se pregunta
    # por la posicion real en pantalla, que es lo que ve una persona y lo unico
    # que no depende de como este montado por dentro.
    bombear(0.3)
    y_avisos = v.panel_avisos.winfo_rooty()
    y_texto = v.texto.winfo_rooty()
    y_aporte = v.panel_aporte.winfo_rooty()
    comprobar("los avisos se ven ARRIBA, antes del texto",
              y_avisos < y_texto, f"avisos y={y_avisos} texto y={y_texto}")
    comprobar("y el aporte del criterio, tambien antes del texto",
              y_aporte < y_texto, f"aporte y={y_aporte} texto y={y_texto}")
    comprobar("los tres estan en la banda de arriba, no debajo de la respuesta",
              max(y_avisos, y_aporte,
                  v.panel_estado.winfo_rooty()) < y_texto)
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
pegado = raiz.clipboard_get()
comprobar("y el portapapeles la tiene", "PRIMERA RESPUESTA" in pegado,
          pegado[:60])
comprobar("LO COPIADO DICE CON QUE SE HIZO",
          "solo con la ley" in pegado, pegado[:90])
print(f"    lo que se pega:\n      {pegado.splitlines()[0][:78]}")
v._terminar({"codigo": 2, "estado": EST.NO_ENCONTRADO, "fallo": None,
             "senales": [], "cobertura": [], "estructural": "",
             "preceptos": [], "traza": None, "recuperado": [], "respuesta": ""})
bombear(0.3)
comprobar("tras un NO ENCONTRADO, el boton se apaga",
          str(v.boton_copiar["state"]) == "disabled")
comprobar("y la respuesta guardada se borra", not v.respuesta_actual,
          v.respuesta_actual[:40])

# =====================================================================
print("\n=== 8. LOS DOS BOTONES, SIEMPRE EN LA VENTANA ===")
print("  El modo es de CADA consulta y se elige al pulsar. NO depende de")
print("  ningun fichero: si hiciera falta editar algo para que apareciera el")
print("  segundo boton, habria que abrir una consola delante de la gente.\n")
comprobar("el primer boton existe siempre", v.boton is not None)
comprobar("dice que consulta la ley", "ley" in v.boton.cget("text").lower(),
          v.boton.cget("text"))
comprobar("EL SEGUNDO TAMBIEN EXISTE SIEMPRE, sin tocar ficheros",
          v.boton_criterio is not None)
comprobar("dice que anade criterio",
          "criterio" in v.boton_criterio.cget("text").lower(),
          v.boton_criterio.cget("text"))
comprobar("y se explica QUE anade, en cristiano",
          "DGT" in interfaz.PIE_CRITERIO and "TEAC" in interfaz.PIE_CRITERIO)
# EL DINERO NO SALE EN PANTALLA. Antes el pie decia «unos 0,22 € frente a
# 0,13 €», y hacia lo contrario de lo que se pretendia: quien dudaba pulsaba el
# barato aunque necesitara el criterio. El gasto esta asumido, y verlo solo
# sirve para que alguien se autolimite. Se sigue midiendo en la traza y en los
# informes, que es donde le sirve a quien lleva la cuenta.
comprobar("los dos botones se distinguen por LO QUE HACEN, no por el precio",
          not any(x in interfaz.PIE_CRITERIO for x in ("€", "0,13", "0,22")),
          interfaz.PIE_CRITERIO)
comprobar("ni dentro del boton",
          "€" not in v.boton_criterio.cget("text"))
v.caja.delete("1.0", "end"); v.caja.insert("1.0", "duda")
v.ejercicio.set("2023"); v._revisar_boton()
comprobar("los dos se encienden juntos",
          str(v.boton["state"]) == str(v.boton_criterio["state"]) == "normal")
v.ejercicio.set(""); v._revisar_boton()
comprobar("y se apagan juntos",
          str(v.boton["state"]) == str(v.boton_criterio["state"]) == "disabled")

print("\n  Y el estado NO se explica igual segun el boton:")
for est in (EST.CLARO, EST.DISCUTIDO, EST.NO_ENCONTRADO):
    a, b = interfaz.explicacion(est, False), interfaz.explicacion(est, True)
    comprobar(f"«{est}» tiene frase propia para cada boton", a != b and a and b,
              f"{a[:40]!r} == {b[:40]!r}")
comprobar("con la ley sola se dice que NO se ha mirado el criterio",
          "no se ha mirado" in interfaz.explicacion(EST.CLARO, False).lower(),
          interfaz.explicacion(EST.CLARO, False))

print("\n=== 8 ter. LA DESPENSA VACIA NO SE LEE COMO UNA AVERIA ===")
print("  Es lo primero que le va a pasar a cualquiera que pruebe una pregunta")
print("  al azar: 241 consultas no cubren el IVA entero. Si eso se dice con")
print("  las palabras de un fallo, se lee como un fallo.\n")
vacia = interfaz.explicacion(EST.NO_ENCONTRADO, True).lower()
comprobar("dice que TODAVIA no hay criterio guardado, no que falle algo",
          "todavia" in vacia or "todavía" in vacia, vacia)
comprobar("y aclara que no estar no es no existir",
          "no quiere decir que no exista" in vacia, vacia)
for palabra in ("error", "fallo", "averia", "no se ha podido"):
    comprobar(f"no usa la palabra «{palabra}»", palabra not in vacia, vacia)
comprobar("el aviso de la despensa dice lo mismo",
          "no es un fallo" in interfaz.AVISO_DESPENSA.lower(),
          interfaz.AVISO_DESPENSA)

print("\n=== 8 quater. «QUE HAY DENTRO»: LA PANTALLA DE ESTADO ===")
print("  Lo que antes solo daba `configurar.py --estado` en una consola.\n")
comprobar("hay un boton para abrirla", hasattr(v, "_abrir_estado"))
v._abrir_estado()
bombear(0.4)
hijas = [w for w in v.raiz.winfo_children() if isinstance(w, tk.Toplevel)]
comprobar("se abre una ventana", len(hijas) == 1, str(len(hijas)))
if hijas:
    ventana = hijas[0]
    comprobar("y se titula en cristiano", "dentro" in ventana.title().lower(),
              ventana.title())

    def textos(w, acc=None):
        """Lo que se LEE, no lo que existe.

        Se cuenta solo lo que tiene gestor de geometria: desde que la lista de
        normas se pliega, las etiquetas del detalle siguen creadas pero no
        estan puestas. Contarlas seria medir una pantalla que nadie ve.
        """
        acc = [] if acc is None else acc
        try:
            if isinstance(w, tk.Label) and w.winfo_manager():
                acc.append(str(w.cget("text")))
        except tk.TclError:
            pass
        for h in w.winfo_children():
            textos(h, acc)
        return acc

    dentro = "\n".join(textos(ventana))
    comprobar("dice las normas cargadas", "NORMAS CARGADAS" in dentro)
    comprobar("con el total de articulos", "en total" in dentro, dentro[:80])
    comprobar("dice cuantas consultas de la DGT hay guardadas",
              "Dirección General de Tributos" in dentro)
    comprobar("y cuantas resoluciones", "Doctrina del TEAC" in dentro
              and "tribunales regionales" in dentro)
    comprobar("nombra los dos botones",
              interfaz.BOTON_LEY in dentro and interfaz.BOTON_CRITERIO in dentro)
    comprobar("y NO dice lo que cuesta ninguno",
              not any(x in dentro for x in ("€", "0,13", "0,22")),
              [l for l in dentro.splitlines()
               if any(x in l for x in ("€", "0,13", "0,22"))][:3])
    comprobar("y si las fuentes responden ahora mismo (el canario)",
              "LAS FUENTES, AHORA MISMO" in dentro)
    comprobar("avisa de que una fuente caida NO impide consultar",
              "no impide consultar" in dentro)
    comprobar("ni una ruta de fichero ni una variable de entorno",
              "AGENTE_DGT" not in dentro and "/Users" not in dentro
              and ".json" not in dentro, dentro[:120])
    # EL TOPE NO SE SUBE. Es la tercera vez que esta pantalla crece; la
    # respuesta ha sido plegar la lista de normas, no ensanchar el limite ni
    # confiar en que se pueda desplazar. Esta pantalla contesta UNA pregunta
    # -«¿esta mi impuesto dentro?»- y una respuesta que hay que ir a buscar
    # bajando ya no es una respuesta de un vistazo.
    comprobar("y cabe en una pantalla: menos de 40 lineas",
              len([l for l in dentro.splitlines() if l.strip()]) < 40,
              str(len(dentro.splitlines())))

    # Y EL DETALLE NO SE PIERDE, SOLO SE GUARDA. Un pliegue que esconde algo
    # para siempre no es un pliegue: es un recorte.
    comprobar("hay un boton para ver las normas una a una",
              hasattr(v, "boton_pliegue_normas"))
    if hasattr(v, "boton_pliegue_normas"):
        comprobar("  y de entrada esta cerrado, que es lo que hace que quepa",
                  v._normas_abiertas is False)
        rotulo = str(v.boton_pliegue_normas.cget("text"))
        comprobar("  el boton dice cuantas normas hay",
                  any(ch.isdigit() for ch in rotulo), rotulo)
        v.boton_pliegue_normas.invoke()
        bombear(0.2)
        abierto = "\n".join(textos(ventana))
        comprobar("  al abrirlo vuelven los nombres de las normas",
                  len(abierto.splitlines()) > len(dentro.splitlines())
                  and "Ley 37/1992" in abierto,
                  f"{len(dentro.splitlines())} -> {len(abierto.splitlines())}")
        v.boton_pliegue_normas.invoke()
        bombear(0.2)
        comprobar("  y al cerrarlo vuelve a caber",
                  len([l for l in "\n".join(textos(ventana)).splitlines()
                       if l.strip()]) < 40)
    ventana.destroy()
    bombear(0.2)

print("\n=== 8 bis. EL MODO SE VE JUNTO AL ESTADO ===")
for con, marca in ((False, "solo con la ley"), (True, "criterio de la DGT")):
    v._terminar({"codigo": 0, "estado": EST.CLARO, "fallo": None, "senales": [],
                 "cobertura": [], "estructural": "", "preceptos": [],
                 "traza": None, "recuperado": [], "con_criterio": con,
                 "respuesta": "una respuesta"})
    bombear(0.3)
    dice = v.etiqueta_hecha_con.cget("text")
    comprobar(f"con_criterio={con}: se dice arriba", marca in dice, dice)
    v._copiar()
    bombear(0.2)
    comprobar(f"con_criterio={con}: y viaja en lo copiado",
              marca in raiz.clipboard_get(), raiz.clipboard_get()[:70])

print("\n=== 9. LA VENTANA SE NIEGA A ABRIR DESCOORDINADA ===")
print("  Desde que configurar.py no manda, la coherencia es UNA cosa: que")
print("  todas las frases de la ventana esten dentro de GUIA.md.\n")
comprobar("existe la pantalla de descoordinacion",
          hasattr(interfaz, "ventana_de_descoordinacion"))
import agente_fiscal.configuracion as CONF
r = CONF.revisar()
comprobar("y hoy el sistema esta coherente", r.coherente, str(r.descuadres))
comprobar("se comprueban TODAS las frases de estado, las seis",
          len(interfaz.TEXTOS_DE_ESTADO) == 6,
          str(len(interfaz.TEXTOS_DE_ESTADO)))
guia = CONF._plano(CONF.GUIA.read_text("utf-8"))
for frase in interfaz.TEXTOS_DE_ESTADO:
    comprobar(f"«{frase[:34]}...» esta en la guia",
              CONF._plano(frase) in guia)

# =====================================================================
print("\n=== 10. LA PRUEBA SABE PONERSE ROJA ===")
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

# (d) una frase de la ventana que NO esta en la guia
print("\n  (d) se cambia una frase de la ventana sin tocar la guia:")
guardadas = list(interfaz.TEXTOS_DE_ESTADO)
interfaz.TEXTOS_DE_ESTADO.append("Esta frase no esta en ninguna guia del mundo.")
roto = CONF.revisar()
print(f"      coherente={roto.coherente} · {len(roto.descuadres)} descuadre(s)")
comprobar("(d) la comprobacion del bloque 9 lo habria cazado",
          not roto.coherente and any("NO esta en GUIA.md" in d
                                     for d in roto.descuadres),
          str(roto.descuadres))
interfaz.TEXTOS_DE_ESTADO[:] = guardadas
comprobar("(d) y al deshacerlo vuelve a estar coherente", CONF.revisar().coherente)

# =====================================================================
print("\n=== 11. LA RESPUESTA LARGA SE LEE ENTERA ===")
print("  Fue BLOQUEANTE. Con la respuesta del articulo 80 puesta, la columna")
print("  de resultado pedia 604 px y en la pantalla quedaban 322: lo que")
print("  sobraba se dibujaba FUERA y no habia forma de llegar. El texto tenia")
print("  barra propia, pero los avisos no, y los avisos son justo lo que")
print("  puede invalidar la respuesta.")
print("  Se prueba con la respuesta REAL del articulo 80 con las tres")
print("  fuentes, que es la mas larga que ha escrito el redactor.\n")

LARGA = (RAIZ / "casos" / "respuesta_larga.txt").read_text("utf-8")
comprobar("el texto de prueba es largo de verdad, no dos lineas",
          len(LARGA) > 5000, f"{len(LARGA)} caracteres")

LARGO = {"codigo": 0, "estado": EST.DISCUTIDO, "fallo": None,
         "senales": ["sobre el articulo 80 hay criterio de años distintos"],
         "cobertura": ["Articulo 80: hay doctrina del TEAC sin comprobar"],
         "estructural": "", "preceptos": ["Articulo 80"], "traza": None,
         "recuperado": [], "con_criterio": True, "respuesta": LARGA}
raiz.geometry("1180x880")
bombear(0.4)
v._terminar(dict(LARGO))
bombear(0.9)

# QUIEN DESPLAZA ES LA PAGINA, NO EL TEXTO. El `Text` mide lo que mide su
# contenido y va dentro del lienzo; lo que hay que comprobar sigue siendo lo
# mismo -que se puede llegar al final de la respuesta- pero preguntandoselo a
# quien desplaza.
alto = v.resultado.winfo_reqheight()
primero, ultimo = v.lienzo_lectura.yview()
print(f"    la columna entera mide {alto} px · la pagina se ve del "
      f"{primero:.0%} al {ultimo:.0%}")
comprobar("la respuesta cabe entera en el widget, aunque no se vea de una vez",
          int(v.texto.index("end-1c").split(".")[0]) > 25,
          v.texto.index("end-1c"))
comprobar("el texto NO tiene su propio recorte: crece con el contenido",
          v.texto.yview() == (0.0, 1.0), str(v.texto.yview()))
comprobar("y la PAGINA no cabe de una vez: hace falta desplazarse",
          ultimo < 0.99, f"se ve hasta {ultimo:.0%}")
comprobar("la ventana NO pide mas de lo que hay en pantalla",
          raiz.winfo_reqheight() < raiz.winfo_screenheight(),
          f"pide {raiz.winfo_reqheight()} de {raiz.winfo_screenheight()}")

# --- la barra, que ahora es la de la pagina ---
barra = [h for h in v.caja_lectura.winfo_children()
         if h.winfo_class() == "TScrollbar"]
comprobar("hay barra de desplazamiento", len(barra) == 1, str(barra))
comprobar("y esta estilada con la paleta, no la del sistema",
          "Vertical.TScrollbar" in str(barra[0].cget("style")),
          str(barra[0].cget("style")))
comprobar("la barra dice cuanto se ve", barra[0].get()[1] < 0.99,
          str(barra[0].get()))
comprobar("y NO hay dos barras anidadas, que era lo que hacia que la "
          "respuesta pareciera una ventanita",
          not any(h.winfo_class() == "TScrollbar"
                  for h in v.texto.master.winfo_children()),
          [h.winfo_class() for h in v.texto.master.winfo_children()])

# --- la rueda, en los tres sistemas ---
print("\n  LA RUEDA. Son eventos DISTINTOS por sistema y se prueban los tres:")


class Rueda:
    """Un evento de rueda de mentira, que es lo que manda cada sistema."""

    def __init__(self, delta=0, num=0):
        self.delta, self.num = delta, num


def desde(fraccion=0.4):
    """Deja la vista quieta en un punto conocido antes de medir.

    Sin esto la prueba flaquea: un `<Configure>` pendiente recuenta el alto del
    texto y mueve la vista entre el evento y la comprobacion.

    Y los eventos se generan con `when="now"`, que los entrega EN EL ACTO. Con
    el valor de fabrica -"tail"- se encolan, y medido: una de cada cinco veces
    la rueda de la comprobacion anterior llegaba DESPUES de recolocar la vista
    y la empujaba en el sentido contrario (0,404 -> 0,743 cuando tenia que
    bajar). Una prueba que falla una de cada cinco no protege nada: se mira.
    """
    bombear(0.3)
    v.lienzo_lectura.yview_moveto(fraccion)
    bombear(0.15)
    return v.lienzo_lectura.yview()[0]


antes = desde(0.0)
v.texto.event_generate("<MouseWheel>", delta=-3, when="now")
bombear(0.25)
comprobar("Mac/Windows: la rueda baja la vista",
          v.lienzo_lectura.yview()[0] > antes,
          f"{antes:.3f} -> {v.lienzo_lectura.yview()[0]:.3f}")
antes = desde(0.4)
v.texto.event_generate("<MouseWheel>", delta=3, when="now")
bombear(0.25)
comprobar("y hacia arriba la sube", v.lienzo_lectura.yview()[0] < antes,
          f"{antes:.3f} -> {v.lienzo_lectura.yview()[0]:.3f}")

# Linux manda Button-4/5 en vez de delta. Se llama al manejador directamente:
# `event_generate` de un boton arrastraria ademas la seleccion, y lo que se
# prueba aqui es el manejador, no el Tk.
antes = desde(0.0)
v._rueda(Rueda(num=5))
comprobar("Linux: <Button-5> baja", v.lienzo_lectura.yview()[0] > antes,
          f"{antes:.3f} -> {v.lienzo_lectura.yview()[0]:.3f}")
antes = desde(0.4)
v._rueda(Rueda(num=4))
comprobar("Linux: <Button-4> sube", v.lienzo_lectura.yview()[0] < antes,
          f"{antes:.3f} -> {v.lienzo_lectura.yview()[0]:.3f}")

FUENTE = (RAIZ / "interfaz.py").read_text("utf-8")
comprobar("el manejador mira `num` antes que `delta` (Linux no trae delta)",
          "evento.num" in FUENTE)
comprobar("y divide el delta de Windows entre 120", "// 120" in FUENTE)

# LA RUEDA TAMBIEN SOBRE LAS ETIQUETAS. La recibe el widget que esta debajo
# del raton, y debajo del raton casi siempre hay una etiqueta, no el lienzo.
print("\n  Y sobre CADA panel, no solo en los huecos entre ellos:")
for nombre, panel in (("el estado", v.panel_estado),
                      ("el detalle del estado", v.panel_detalle),
                      ("los avisos", v.panel_avisos),
                      ("la respuesta", v.texto)):
    antes = desde(0.0)
    hijo = panel.winfo_children()[0] if panel.winfo_children() else panel
    hijo.event_generate("<MouseWheel>", delta=-3, when="now")
    bombear(0.25)
    comprobar(f"la rueda funciona sobre {nombre}",
              v.lienzo_lectura.yview()[0] > antes,
              f"{antes:.3f} -> {v.lienzo_lectura.yview()[0]:.3f}")

# --- el teclado ---
print("\n  EL TECLADO:")
# `focus_force` NO es un truco de la prueba: sin una ventana ACTIVA, Tk no
# entrega eventos de teclado a nadie, y `event_generate` se pierde. Delante de
# una persona la ventana esta activa por definicion.
raiz.focus_force()
v.texto.focus_set()
bombear(0.4)
comprobar("el lienzo puede recibir el teclado",
          raiz.focus_get() is not None, "nadie tiene el foco")
for pulsacion, sube in (("<Next>", False), ("<Prior>", True), ("<End>", False),
                    ("<Home>", True)):
    v.lienzo_lectura.yview_moveto(0.5)
    antes = v.lienzo_lectura.yview()[0]
    # El `focus_force` va DENTRO del bucle. Corriendo sin nadie delante, la
    # ventana no es la activa y el sistema le quita el foco entre tecla y
    # tecla: medido, `focus_get()` vuelve a None despues de la primera. No es
    # un fallo de la ventana -delante de una persona esta activa- pero sin
    # esto la prueba solo comprobaria la primera tecla y daria las otras por
    # buenas.
    tecla(pulsacion)
    ahora = v.lienzo_lectura.yview()[0]
    comprobar(f"{pulsacion} {'sube' if sube else 'baja'} la vista",
              (ahora < antes) if sube else (ahora > antes),
              f"{antes:.3f} -> {ahora:.3f}")
v.lienzo_lectura.yview_moveto(0.5)
tecla("<Down>")
comprobar("<Down> baja un poco", v.lienzo_lectura.yview()[0] > 0.5,
          str(v.lienzo_lectura.yview()[0]))
tecla("<Up>"); tecla("<Up>")
comprobar("<Up> sube", v.lienzo_lectura.yview()[0] < 0.5,
          str(v.lienzo_lectura.yview()[0]))
# El `focus_force` va pegado a CADA tecla, no una vez arriba: corriendo sin
# nadie delante el sistema le quita el foco a la ventana entre tecla y tecla, y
# `event_generate` se pierde en silencio. Es el mismo fallo de foco de siempre.
tecla("<End>")
comprobar("<End> llega hasta el FINAL DEL TODO",
          v.lienzo_lectura.yview()[1] > 0.999, str(v.lienzo_lectura.yview()))

# --- la respuesta nueva vuelve arriba ---
print("\n  Y LO QUE MAS SE NOTA SI FALLA:")
v.lienzo_lectura.yview_moveto(1.0)
v._terminar({"codigo": 0, "estado": EST.CLARO, "fallo": None, "senales": [],
             "cobertura": [], "estructural": "", "preceptos": ["Articulo 91"],
             "traza": None, "recuperado": [], "con_criterio": False,
             "respuesta": "Una respuesta corta detras de una larga."})
bombear(0.5)
comprobar("una respuesta NUEVA empieza por arriba, no donde quedo la anterior",
          v.lienzo_lectura.yview()[0] == 0.0, str(v.lienzo_lectura.yview()))
# La barra se esconde cuando NO hay nada que desplazar. Se prueba la regla
# directamente: montar una pantalla donde la columna quepa entera exige una
# ventana mas alta que esta pantalla, y entonces no se probaria nada.
# Se comprueba SIN bombear entremedias: el lienzo vuelve a llamar a este mismo
# manejador con sus cifras de verdad en cuanto se procesa la cola, y entonces
# se estaria midiendo el estado real y no la regla.
_barra = v._barra_de[str(v.lienzo_lectura)]
v.lienzo_lectura.cget("yscrollcommand")  # existe
v.lienzo_lectura.tk.call(v.lienzo_lectura.cget("yscrollcommand"), 0.0, 1.0)
comprobar("si cabe entera, la barra se quita de en medio",
          not _barra.grid_info(),
          "la barra sigue ahi sin nada que hacer")
v.lienzo_lectura.tk.call(v.lienzo_lectura.cget("yscrollcommand"), 0.0, 0.4)
comprobar("y en cuanto hay algo debajo, vuelve", bool(_barra.grid_info()))

# --- se puede seleccionar ---
v._terminar(dict(LARGO))
bombear(0.7)
v.texto.tag_add("sel", "1.0", "3.0")
bombear(0.15)
comprobar("se puede seleccionar texto con el raton",
          bool(v.texto.tag_ranges("sel")))
comprobar("y seleccionar NO descoloca la vista", v.texto.yview()[0] == 0.0,
          str(v.texto.yview()))
v.texto.tag_remove("sel", "1.0", "end")

# --- a dos tamaños, y que se lea entera en los dos ---
print("\n  DE ARRIBA A ABAJO, MAXIMIZADA Y SIN MAXIMIZAR:")
for etiqueta, (an, al) in (("sin maximizar", (1180, 880)),
                           ("maximizada", (raiz.winfo_screenwidth(),
                                           raiz.winfo_screenheight() - 60))):
    raiz.geometry(f"{an}x{al}")
    bombear(0.8)
    v.texto.yview_moveto(0.0)
    bombear(0.25)
    vueltas = 0
    while v.texto.yview()[1] < 0.999 and vueltas < 300:
        v.texto.yview_scroll(1, "pages")
        vueltas += 1
    print(f"    {etiqueta:14s} ventana {raiz.winfo_width()}x{raiz.winfo_height()}"
          f" · columna {v.resultado.winfo_reqheight()} px"
          f" · {vueltas} paginas hasta el final")
    comprobar(f"{etiqueta}: se llega al final de la columna",
              v.texto.yview()[1] > 0.999, str(v.texto.yview()))
    comprobar(f"{etiqueta}: los avisos se ven enteros y sin desplazar",
              v.panel_avisos.winfo_height() >= v.panel_avisos.winfo_reqheight(),
              f"{v.panel_avisos.winfo_height()} de "
              f"{v.panel_avisos.winfo_reqheight()} px")
    comprobar(f"{etiqueta}: la ultima linea del texto se dibuja",
              v.texto.dlineinfo("end-2c") is not None,
              "la ultima linea no llega a dibujarse")
    comprobar(f"{etiqueta}: el formulario no esta: la ventana es para leer",
              not v.vista_consulta.winfo_ismapped())

# --- el ancho de lectura NO impide maximizar ---
print("\n  EL ANCHO DE LECTURA NO PUEDE IMPEDIR MAXIMIZAR:")
margenes = []
for an in (1000, 1400, raiz.winfo_screenwidth()):
    raiz.geometry(f"{an}x820")
    bombear(0.55)
    margenes.append((raiz.winfo_width(),
                     int(str(v.texto.tag_cget("columna", "lmargin1") or 0))))
    comprobar(f"la ventana llega a {an} px de ancho",
              abs(raiz.winfo_width() - an) < 40,
              f"pedido {an}, real {raiz.winfo_width()}")
print(f"    ancho de ventana -> margen de la columna: {margenes}")
solo = [m for _a, m in margenes]
comprobar("el margen CRECE con la ventana: el parrafo se queda quieto",
          solo == sorted(solo) and len(set(solo)) > 1, str(margenes))
comprobar("y el ancho de lectura NO entra en lo que el Text PIDE",
          v.texto.winfo_reqwidth() < 300,
          f"pide {v.texto.winfo_reqwidth()} px: volveria a bloquear la ventana")
# EL MINIMO YA NO ES UNA CIFRA ESCRITA A MANO, asi que no se comprueba contra
# otra cifra a mano: se comprueba LA PROPIEDAD. Encogida a su minimo, no puede
# quedar ni un control fuera de la ventana. Estaba fijo en 620 de alto y a esa
# altura el boton «Qué hay dentro» caia en y=691, fuera; y un control fuera de
# la ventana es un control que no existe.
raiz.geometry(f"{raiz.minsize()[0]}x{raiz.minsize()[1]}+0+0")
bombear(0.6)


def _pulsables_fuera(w, acc=None):
    acc = [] if acc is None else acc
    for h in w.winfo_children():
        if h.winfo_ismapped() and h.winfo_class() in ("TButton", "TCombobox",
                                                      "TEntry"):
            x = h.winfo_rootx() - raiz.winfo_rootx()
            y = h.winfo_rooty() - raiz.winfo_rooty()
            if (x < -1 or y < -1
                    or x + h.winfo_width() > raiz.winfo_width() + 1
                    or y + h.winfo_height() > raiz.winfo_height() + 1):
                try:
                    acc.append(f"{h.cget('text')}@({x},{y})")
                except Exception:
                    acc.append(f"{h.winfo_class()}@({x},{y})")
        _pulsables_fuera(h, acc)
    return acc


fuera_min = _pulsables_fuera(raiz)
print(f"    minimo {raiz.minsize()} · real "
      f"{raiz.winfo_width()}x{raiz.winfo_height()}")
comprobar("encogida a su minimo, NADA pulsable queda fuera de la ventana",
          not fuera_min, str(fuera_min))
comprobar("y el minimo no es mayor que la pantalla",
          raiz.minsize()[1] <= raiz.winfo_screenheight(), str(raiz.minsize()))

# =====================================================================
print("\n=== 12. VEINTE LINEAS SIN DESPLAZAR, MAXIMIZADA ===")
print("  El listón: si de la respuesta se ven menos de veinte lineas de una")
print("  vez, sigue apretado por mucho que el cuerpo sea grande.\n")
raiz.geometry(f"{raiz.winfo_screenwidth()}x{raiz.winfo_screenheight() - 80}+0+40")
bombear(0.8)
# Se deja la consulta como estaria de verdad: los bloques de antes vaciaron el
# año a proposito para probar que el boton se apaga, y el eco de la barra de
# arriba tiene que enseñar lo que se pregunto.
v.caja.delete("1.0", "end")
v.caja.insert("1.0", "un cliente no me paga la factura de 2023, "
                     "¿puedo recuperar el IVA que ya ingresé?")
v.ejercicio.set("2023")
v._revisar_boton()
v._terminar(dict(LARGO))
bombear(1.0)
alto_linea = v.fuente_texto.metrics("linespace") + interfaz.INTERLINEA
# LO QUE SE VE ES LO QUE CABE EN LA VENTANA, no lo que mide el widget. Desde
# que el texto crece con su contenido, `v.texto.winfo_height()` es el alto de
# la RESPUESTA ENTERA -miles de pixeles- y dividirlo por el alto de linea daria
# «se ven 108 lineas» con la ventana enseñando diecisiete. Quien recorta es el
# lienzo de la pagina.
util = (v.lienzo_lectura.winfo_height()
        - (v.texto.winfo_rooty() - v.lienzo_lectura.winfo_rooty())
        - 2 * interfaz.RELLENO)
visibles = max(0, util) // alto_linea
print(f"    ventana {raiz.winfo_width()}x{raiz.winfo_height()} · "
      f"banda {v.banda.winfo_height()} px · pagina "
      f"{v.lienzo_lectura.winfo_height()} px")
print(f"    cuerpo {v.fuente_texto.cget('size')} pt · interlinea "
      f"{interfaz.INTERLINEA} px · alto de linea {alto_linea} px")
comprobar(f"se ven {visibles} lineas sin desplazar, y hacen falta 20",
          visibles >= 20, f"{visibles} lineas")
comprobar("y la banda de arriba no se come mas de un cuarto de la ventana",
          v.banda.winfo_height() < raiz.winfo_height() * 0.28,
          f"{v.banda.winfo_height()} px de {raiz.winfo_height()}")

print("\n  LOS TAMAÑOS, QUE SON LO QUE SE PIDIO SUBIR:")
for nombre, fuente, minimo in (("cuerpo de la respuesta", v.fuente_texto, 15),
                               ("citas", v.fuente_cita, 16),
                               ("referencias", v.fuente_referencia, 12),
                               ("rotulo del estado", v.fuente_estado, 18),
                               ("interfaz", v.fuente, 13)):
    comprobar(f"{nombre}: {fuente.cget('size')} pt (minimo {minimo})",
              fuente.cget("size") >= minimo, f"{fuente.cget('size')} pt")
comprobar("la cita es MAS grande que el parrafo",
          v.fuente_cita.cget("size") > v.fuente_texto.cget("size"))
comprobar("hay interlineado dentro del parrafo",
          int(v.texto.cget("spacing2")) >= 6, v.texto.cget("spacing2"))
comprobar("y mas aire ENTRE parrafos que dentro",
          int(v.texto.cget("spacing3")) > int(v.texto.cget("spacing2")))
comprobar("la cita lleva aire de verdad por arriba y por abajo",
          int(v.texto.tag_cget("cita", "spacing1")) >= 20
          and int(v.texto.tag_cget("cita", "spacing3")) >= 20,
          f"{v.texto.tag_cget('cita', 'spacing1')} / "
          f"{v.texto.tag_cget('cita', 'spacing3')}")
comprobar("y el texto no empieza pegado al borde",
          int(v.texto.cget("padx")) >= 20, v.texto.cget("padx"))

# =====================================================================
print("\n=== 13. LA PRUEBA DE LAS VEINTE LINEAS SABE PONERSE ROJA ===")
print("  Se le quita a la respuesta el peso que la hace crecer -que es lo que")
print("  la dejaba en dos lineas- y se comprueba que el bloque 12 lo caza.\n")
v.resultado.rowconfigure(1, weight=0)
bombear(0.8)
roto = max(0, (v.lienzo_lectura.winfo_height()
               - (v.texto.winfo_rooty() - v.lienzo_lectura.winfo_rooty())
               - 2 * interfaz.RELLENO)) // alto_linea
print(f"    sin peso en la fila del texto: {roto} lineas visibles")
comprobar("sin el peso, la respuesta se queda en una rendija",
          roto < 5, f"{roto} lineas: la mutacion no ha roto nada")
comprobar("y el bloque 12 lo habria cazado", not roto >= 20)
v.resultado.rowconfigure(1, weight=1)
bombear(0.8)
_vuelta = max(0, (v.lienzo_lectura.winfo_height()
                  - (v.texto.winfo_rooty() - v.lienzo_lectura.winfo_rooty())
                  - 2 * interfaz.RELLENO)) // alto_linea
comprobar("al deshacerlo vuelve a las veinte", _vuelta >= 20, str(_vuelta))

# =====================================================================
print("\n=== 14. LAS DOS VISTAS ===")
print("  La pregunta y la respuesta ya no comparten pantalla: se estorbaban.\n")
comprobar("al responder se ve la vista de respuesta",
          v.vista_respuesta.winfo_ismapped())
comprobar("y la de consulta NO", not v.vista_consulta.winfo_ismapped())
comprobar("hay un boton para volver", v.boton_volver is not None)
comprobar("y dice que es para una consulta nueva",
          "nueva consulta" in v.boton_volver.cget("text").lower(),
          v.boton_volver.cget("text"))
comprobar("la pregunta se ve mientras se lee la respuesta",
          "cliente" in v.eco_pregunta.cget("text").lower()
          or len(v.eco_pregunta.cget("text")) > 10,
          v.eco_pregunta.cget("text"))
comprobar("y el año, que es de lo que depende media respuesta",
          "2023" in v.eco_pregunta.cget("text"), v.eco_pregunta.cget("text"))

antes_duda = v.caja.get("1.0", "end").strip()
v._nueva_consulta()
bombear(0.5)
comprobar("«Nueva consulta» devuelve a la vista de consulta",
          v.vista_consulta.winfo_ismapped()
          and not v.vista_respuesta.winfo_ismapped())
comprobar("Y RECUPERA LA PREGUNTA ANTERIOR, no la borra",
          v.caja.get("1.0", "end").strip() == antes_duda and antes_duda,
          repr(v.caja.get("1.0", "end").strip()[:40]))
comprobar("con el año puesto, para poder cambiarlo",
          v.ejercicio.get().strip() != "")
comprobar("y el foco en el año, que es lo que mas se cambia",
          str(raiz.focus_get()) == str(v.caja_ejercicio)
          or v.caja_ejercicio.selection_present(),
          str(raiz.focus_get()))

raiz.destroy()
print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
