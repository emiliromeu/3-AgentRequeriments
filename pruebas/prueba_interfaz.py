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
from tkinter import ttk

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
print("\n=== 1. EL ANO DEL CASO ES OBLIGATORIO, Y VIENE PUESTO ===")
print("  Obligatorio sigue igual. Lo que cambia es que se llega con el")
print("  campo relleno y DICIENDO de donde salio el año.")
#
# ────────────────────────────────────────────────────────────────────────
# ESTAS DOS COMPROBACIONES DECIAN LO CONTRARIO. CAMBIADO EL 29/08/2026.
# ────────────────────────────────────────────────────────────────────────
#
# Decian «el campo del ejercicio empieza VACIO» y «y no trae el ano en curso»,
# y eran la regla 2 de la cabecera de `interfaz.py` escrita como prueba. La
# regla se ha invertido a proposito -ver la nota larga junto al campo- y estas
# dos comprobaciones se reescriben con ella.
#
# LO QUE NO SE PUEDE PERDER AL CAMBIARLAS, y es lo que se comprueba ahora:
# el ano nunca puede estar mal EN SILENCIO. Vacio, eso se conseguia obligando
# a teclear; relleno, se consigue con tres cosas, y las tres se prueban aqui:
#
#   1. sigue siendo obligatorio: si se vacia, los botones se apagan;
#   2. el campo dice DE DONDE salio lo que lleva dentro;
#   3. y esa marca desaparece en cuanto una persona teclea, para que un ano
#      puesto por el programa no se pueda confundir con uno elegido.
#
# UNA PRUEBA QUE SE CAMBIA PARA QUE PASE NO PRUEBA NADA. Por eso el bloque de
# CONTROL NEGATIVO del final rompe el relleno a proposito y comprueba que esta
# suite lo caza.
import datetime
EN_CURSO = str(datetime.date.today().year)
comprobar("el campo del ejercicio llega RELLENO", v.ejercicio.get().strip() != "",
          repr(v.ejercicio.get()))
comprobar("con el año natural en curso", v.ejercicio.get().strip() == EN_CURSO,
          v.ejercicio.get())
comprobar("y el campo dice de donde ha salido",
          v.marca_ejercicio.cget("text") == interfaz.MARCA_EN_CURSO,
          v.marca_ejercicio.cget("text"))
comprobar("el aviso dice QUE PASA si el año esta mal, no que es obligatorio",
          "de otra ley" in interfaz.AVISO_EJERCICIO.lower()
          and "obligatorio" not in interfaz.AVISO_EJERCICIO.lower(),
          interfaz.AVISO_EJERCICIO)

# --- de donde saca el año: los tres casos ---
v.caja.delete("1.0", "end")
v.caja.insert("1.0", "deduccion del IVA de un turismo comprado en 2019")
v._proponer_ejercicio()
comprobar("si la pregunta dice UN año, se pone ese",
          v.ejercicio.get() == "2019", v.ejercicio.get())
comprobar("y se dice que lo dice la pregunta",
          v.marca_ejercicio.cget("text") == interfaz.MARCA_DE_LA_PREGUNTA,
          v.marca_ejercicio.cget("text"))
v.caja.delete("1.0", "end")
v.caja.insert("1.0", "cambio de criterio entre 2019 y 2021, cual aplico")
v._proponer_ejercicio()
comprobar("si la pregunta dice VARIOS, NO se elige por nadie",
          v.marca_ejercicio.cget("text") == interfaz.MARCA_VARIOS,
          v.marca_ejercicio.cget("text"))
# LO TECLEADO MANDA, Y NO SE PISA NUNCA MAS.
# COMO LO HACE UNA PERSONA: el foco en el campo y una tecla de verdad. Sin
# `focus_force` la ligadura no llega -corriendo sin nadie delante la ventana no
# es la activa-, que es el mismo motivo por el que existe el ayudante `tecla()`
# de mas abajo.
v.caja_ejercicio.focus_force()
bombear(0.15)
v.caja_ejercicio.event_generate("<KeyRelease-2>", when="now")
bombear(0.15)
comprobar("en cuanto se teclea en el campo, la marca desaparece",
          v.marca_ejercicio.cget("text") == "",
          v.marca_ejercicio.cget("text"))
v.ejercicio.set("2015")
v.caja.delete("1.0", "end")
v.caja.insert("1.0", "una duda del ejercicio 2022")
v._proponer_ejercicio()
comprobar("y un año puesto A MANO ya no lo pisa la pregunta",
          v.ejercicio.get() == "2015", v.ejercicio.get())
v._ejercicio_a_mano = False

v.caja.delete("1.0", "end")
v.caja.insert("1.0", "una duda cualquiera")
v.ejercicio.set("")
v._revisar_boton()
comprobar("sin ano, el boton de consultar esta APAGADO",
          not v.lo_que_se_puede_hacer()["consultar"],
          v.lo_que_se_puede_hacer())
v.ejercicio.set("2023")
v._revisar_boton()
comprobar("con ano y con duda, se enciende",
          v.lo_que_se_puede_hacer()["consultar"], v.lo_que_se_puede_hacer())
v.caja.delete("1.0", "end")
v._revisar_boton()
comprobar("sin duda tampoco se enciende, aunque haya ano",
          not v.lo_que_se_puede_hacer()["consultar"])
for malo in ("abc", "20", "0", "12345"):
    v.caja.delete("1.0", "end")
    v.caja.insert("1.0", "duda")
    v.ejercicio.set(malo)
    v._revisar_boton()
    comprobar(f"un ano invalido «{malo}» no enciende el boton",
              not v.lo_que_se_puede_hacer()["consultar"],
              v.lo_que_se_puede_hacer())

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

# LOS TRES, A LA MISMA CLARIDAD Y CON EL CROMA BAJANDO. Es lo que impide que se
# lean como un semaforo, y es una propiedad de la RELACION entre los tres: da
# igual si la paleta es clara u oscura.
def _croma(hexa):
    r_, g_, b_ = _rgb(hexa)
    return max(r_, g_, b_) - min(r_, g_, b_)


cromas = [_croma(interfaz.COLOR[e])
          for e in (EST.CLARO, EST.DISCUTIDO, EST.NO_ENCONTRADO)]
comprobar("el croma baja del criterio claro al no encontrado",
          cromas[0] > cromas[1] > cromas[2], cromas)

# ======================================================================
print("\n=== 2 bis. LOS CONTRASTES SE CALCULAN, NO SE ESCRIBEN ===")
print("  Una tabla de contrastes en un comentario es una tabla que se queda")
print("  vieja el dia que alguien toca un hex. Se recalculan aqui.\n")


def _luminancia(hexa):
    def canal(v):
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r_, g_, b_ = (canal(c) for c in _rgb(hexa))
    return 0.2126 * r_ + 0.7152 * g_ + 0.0722 * b_


def contra(a, b):
    la, lb = _luminancia(a), _luminancia(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


I = interfaz
# CADA PAR ES TEXTO SOBRE SU FONDO DE VERDAD, no una combinacion cualquiera:
# lo que se mide es lo que se lee. El minimo de la norma para texto es 4,5:1.
PARES = [
    ("texto principal sobre panel", I.TINTA, I.PAPEL2),
    ("titular sobre el fondo", I.TINTA, I.PAPEL),
    ("texto en la caja de la duda", I.TINTA, I.ELEVADO),
    ("texto secundario sobre panel", I.TINTA2, I.PAPEL2),
    ("texto secundario sobre el fondo", I.TINTA2, I.PAPEL),
    ("rotulos menudos sobre panel", I.TINTA3, I.PAPEL2),
    ("rotulos menudos sobre el fondo", I.TINTA3, I.PAPEL),
    ("rotulos menudos sobre campo", I.TINTA3, I.ELEVADO),
    ("enlace sobre panel", I.ENLACE, I.PAPEL2),
    ("tinta sobre el boton lila", I.LILA_TINTA, I.LILA),
    ("tinta sobre el boton lila al pasar", I.LILA_TINTA, I.LILA_VIVO),
    ("estado CRITERIO CLARO", I.COLOR[EST.CLARO], I.PAPEL2),
    ("estado CRITERIO DISCUTIDO", I.COLOR[EST.DISCUTIDO], I.PAPEL2),
    ("estado NO ENCONTRADO", I.COLOR[EST.NO_ENCONTRADO], I.PAPEL2),
    ("texto seleccionado con el raton", I.TINTA, I.SELECCION),
]
for nombre, tinta, fondo in PARES:
    r = contra(tinta, fondo)
    comprobar(f"{nombre}: {r:.2f}:1", r >= 4.5, f"{tinta} sobre {fondo}")

# EL BOTON APAGADO TAMBIEN SE TIENE QUE LEER. No es texto corriente -la norma
# lo exime- pero un boton gris ilegible es el «boton gris en silencio» que
# `prueba_arranque` existe para impedir. Apagado no quiere decir invisible.
r = contra(I.APAGADO_TINTA, I.APAGADO)
comprobar(f"el texto de un boton apagado se lee: {r:.2f}:1", r >= 3.0,
          f"{I.APAGADO_TINTA} sobre {I.APAGADO}")

# NI UN COLOR ESCRITO A MANO DENTRO DE `_estilos`.
#
# Habia SEIS, y son el fallo de la fase 22 del reves: un hex atado al modo que
# tocaba entonces. Sobre el fondo contrario quedan como manchas, y nada avisa.
import re as _re  # noqa: E402
_fuente = (RAIZ / "interfaz.py").read_text("utf-8")
_estilos = _fuente[_fuente.index("def _estilos"):_fuente.index("def _desplazable")]
_sueltos = _re.findall(r'"#[0-9A-Fa-f]{6}"',
                       "\n".join(l for l in _estilos.splitlines()
                                  if not l.lstrip().startswith("#")))
comprobar("ni un color escrito a mano en los estilos: todos de la paleta",
          not _sueltos, _sueltos)

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
        # SE LE PREGUNTA A LA VENTANA. Antes esto leia `etiqueta_estado` y
        # `etiqueta_explicacion` a pelo: dos widgets que con el chat pasan a
        # ser uno por vuelta. Lo que se protege -que el estado se pinta con SU
        # rotulo y su explicacion- no cambia por eso.
        en_pantalla = v.estado_en_pantalla()
        comprobar(f"«{est}» se pinta con su rotulo",
                  en_pantalla["rotulo"] == est, en_pantalla["rotulo"])
        comprobar(f"«{est}» lleva explicacion, y no vacia",
                  len(en_pantalla["explicacion"]) > 40)
        # EL COLOR SI SE MIRA EN EL WIDGET, y es correcto: lo que se protege
        # aqui es la MAQUETA -que cada estado use su color y que no sea un
        # semaforo-, y el color no tiene otra forma de mirarse. Preguntar por
        # el seria inventar una pregunta que solo significa lo que ya dice el
        # widget.
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
    # SE LE PREGUNTA A LA VENTANA. Antes esto recorria los hijos del panel y
    # leia su `text`: para saber si un aviso salia habia que saber que los
    # avisos son etiquetas dentro de un `Frame` y que empiezan por «•». Con el
    # chat eso pasa a ser un bloque por vuelta, y ninguna de esas dos cosas
    # sobrevive. Lo que se protege -que los dos ejes salen, separados, y con
    # sus avisos enteros- no depende de como se pinten.
    avisos = v.avisos_en_pantalla()
    etiquetas = [w.cget("text") for w in v.panel_avisos.winfo_children()]
    comprobar("el panel de avisos queda visible",
              bool(v.panel_avisos.winfo_ismapped()))
    comprobar("sale el eje del DESACUERDO", bool(avisos["desacuerdo"]), avisos)
    comprobar("y el de LO QUE NO SE HA PODIDO MIRAR, aparte",
              bool(avisos["sin_mirar"]), avisos)
    comprobar("cada aviso va en SU eje, no todos revueltos",
              avisos["desacuerdo"] == SENALES
              and avisos["sin_mirar"] == COBERTURA, avisos)
    # EL ORDEN SE MIRA EN LA PANTALLA: es una propiedad de la maqueta -el
    # desacuerdo se lee antes- y no la puede contestar una pregunta que
    # devuelve dos listas.
    comprobar("el desacuerdo va ANTES que la cobertura",
              [t for t in etiquetas if "DESACUERDO" in t
               or "NO SE HA PODIDO MIRAR" in t][0].startswith("DESACUERDO"))
    comprobar("salen los tres avisos con su texto",
              len(avisos["desacuerdo"]) + len(avisos["sin_mirar"]) == 3,
              avisos)
    # El limite del corpus ya no vive aqui: se comprueba mas abajo, debajo
    # del texto, que es donde se ha movido.
    comprobar("el limite del corpus NO ocupa sitio entre los avisos",
              ESTRUCTURAL not in str(v.avisos_en_pantalla()),
              v.avisos_en_pantalla())
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
    # CON LA COLUMNA AL LADO, «ANTES» YA NO ES «MAS ARRIBA». El aporte esta a
    # la derecha, a la altura de las primeras lineas del texto, y eso se ve
    # igual de bien -o mejor- que encima. Lo que hay que garantizar sigue
    # siendo lo mismo: que se VEA SIN DESPLAZAR, y que los avisos vayan por
    # delante del aporte, porque son lo que puede invalidar la respuesta.
    alto_v = raiz.winfo_height() + raiz.winfo_rooty()
    comprobar("y el aporte del criterio se ve sin desplazar",
              y_aporte < alto_v, f"aporte y={y_aporte} ventana hasta {alto_v}")
    comprobar("los avisos van por delante del aporte",
              y_avisos <= y_aporte, f"avisos {y_avisos} aporte {y_aporte}")
    comprobar("y ninguno queda debajo del final de la respuesta",
              max(y_avisos, y_aporte) < v.texto.winfo_rooty()
              + v.texto.winfo_height())
    comprobar("con respuesta verificada SI hay algo que copiar",
              v.lo_que_se_puede_hacer()["copiar"], v.lo_que_se_puede_hacer())

# ────────────────────────────────────────────────────────────────────────
# SIN NADA QUE AVISAR, NO HAY BLOQUE. CAMBIADO EL 29/08/2026.
# ────────────────────────────────────────────────────────────────────────
#
# Aqui se comprobaba lo contrario: «sin nada que avisar, el bloque de cobertura
# SIGUE saliendo» y «dice expresamente que no falta nada». El razonamiento era
# que leer «no falta nada por mirar» es informacion.
#
# LO TUMBA LA CUENTA: sobre las 79 consultas hechas con el motor de verdad,
# 73 no tienen ni un aviso. El bloque salia diciendo «Nada que mirar» en el 92%
# de las respuestas, y un bloque que casi siempre dice que no hay nada deja de
# leerse — justo antes del dia en que si tiene algo que decir.
#
# LO QUE HAY QUE SEGUIR PROTEGIENDO, y se comprueba abajo: cuando SI hay algo,
# sale entero, con su rotulo y por delante del texto.
v._terminar({"codigo": 0, "estado": EST.CLARO, "fallo": None, "senales": [],
             "cobertura": [], "estructural": "", "preceptos": ["Articulo 91"],
             "traza": None, "recuperado": [], "respuesta": "Sale al 21%."})
bombear(0.3)
comprobar("sin nada que avisar, no hay ni un aviso en pantalla",
          v.avisos_en_pantalla() == {"desacuerdo": [], "sin_mirar": []},
          v.avisos_en_pantalla())
comprobar("  y el panel no se pinta: un marco vacio sigue ocupando alto",
          not v.panel_avisos.winfo_ismapped())

# CON UN SOLO AVISO DE COBERTURA VUELVE A SALIR, entero y con su rotulo.
v._terminar({"codigo": 0, "estado": EST.CLARO, "fallo": None, "senales": [],
             "cobertura": ["Articulo 91: el texto cambio dentro del ejercicio"],
             "estructural": "", "preceptos": ["Articulo 91"],
             "traza": None, "recuperado": [], "respuesta": "Sale al 21%."})
bombear(0.3)
comprobar("con algo que avisar, el bloque vuelve",
          v.panel_avisos.winfo_ismapped()
          and bool(v.avisos_en_pantalla()["sin_mirar"]),
          v.avisos_en_pantalla())
comprobar("sin desacuerdo, ese eje viene vacio",
          not v.avisos_en_pantalla()["desacuerdo"], v.avisos_en_pantalla())

# --- EL LIMITE DEL CORPUS: FUERA DE LOS AVISOS, PERO NO PERDIDO ---
#
# Sale en 1.626 de 4.933 expedientes y no hay nada que hacer con el, asi que
# ya no compite por el sitio con los avisos accionables. Pero tiene que
# SEGUIR ESTANDO: dice de que no puede hablar esta respuesta.
LIMITE = "Articulo 80 remite a Ley 22/2003, que no esta en el corpus"
v._terminar({"codigo": 0, "estado": EST.CLARO, "fallo": None, "senales": [],
             "cobertura": [], "estructural": LIMITE,
             "preceptos": ["Articulo 80"], "traza": None, "recuperado": [],
             "respuesta": "Sale al 21%."})
bombear(0.3)
comprobar("el limite del corpus ya NO va con los avisos",
          LIMITE not in str(v.avisos_en_pantalla()), v.avisos_en_pantalla())
comprobar("pero se sigue leyendo, debajo del texto",
          LIMITE in v.lo_que_se_lee(), v.lo_que_se_lee()[-200:])
comprobar("y va DESPUES de la respuesta, no antes",
          v.lo_que_se_lee().index(LIMITE)
          > v.lo_que_se_lee().index("Sale al 21%"))

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
          v.estado_en_pantalla()["rotulo"] != "")
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
          all(vale for nombre, vale in v.lo_que_se_puede_hacer().items()
              if nombre.startswith("consultar")),
          v.lo_que_se_puede_hacer())
v.ejercicio.set(""); v._revisar_boton()
comprobar("y se apagan juntos",
          not any(vale for nombre, vale in v.lo_que_se_puede_hacer().items()
                  if nombre.startswith("consultar")),
          v.lo_que_se_puede_hacer())

# ────────────────────────────────────────────────────────────────────
# EL MATIZ QUE VIENE DE `prueba_boton` -HOY `prueba_arranque`-, Y QUE AQUI
# NO ESTABA.
# ────────────────────────────────────────────────────────────────────
#
# Aquel §3 existe porque `_bloquear` apagaba SOLO el primero: la
# ventana decia «no se puede consultar» y dejaba el segundo pulsable sobre un
# motor que no hay. Al mudar la comprobacion se descubrio que aqui NO estaba
# cubierta — rompiendo `_bloquear` a proposito, esta suite seguia en verde.
# Lo caza el control negativo, que para eso esta.
#
# Y NO SE MUDA COMO ESTABA. Alli enumeraba los dos botones por su nombre, y
# enumerar por nombre es justo lo que dejo pasar el segundo. Se pregunta por
# TODOS los caminos de consulta: el dia que haya un tercero entra solo, y el
# dia que quede uno la comprobacion sigue significando lo mismo.
# CON LOS BOTONES ENCENDIDOS ANTES, si no esto no prueba nada: la linea de
# arriba los deja apagados por falta de año, y `_bloquear` sobre algo ya
# apagado no demuestra que lo apague. Es la trampa de siempre —una
# comprobacion que pasa por el estado previo y no por lo que dice medir— y
# aqui se cayo: rompiendo `_bloquear` a proposito, seguia en verde.
v.ejercicio.set("2023")
v._revisar_boton()
bombear(0.2)
comprobar("(partimos de los dos encendidos)",
          all(vale for nombre, vale in v.lo_que_se_puede_hacer().items()
              if nombre.startswith("consultar")),
          v.lo_que_se_puede_hacer())
v._bloquear("una causa cualquiera")
bombear(0.25)
comprobar("bloqueada, no queda NINGUN camino de consulta vivo",
          not any(vale for nombre, vale in v.lo_que_se_puede_hacer().items()
                  if nombre.startswith("consultar")),
          v.lo_que_se_puede_hacer())
# Y NO SE REENCIENDE AL ESCRIBIR, que es como se descubrio que faltaba: una
# ventana bloqueada que vuelve a encender el boton en cuanto alguien teclea
# ofrece consultar sobre un arranque que fallo a medias.
v.caja.delete("1.0", "end")
v.caja.insert("1.0", "una duda cualquiera")
v.ejercicio.set("2023")
v._revisar_boton()
bombear(0.25)
comprobar("  y escribir NO lo vuelve a encender",
          not any(vale for nombre, vale in v.lo_que_se_puede_hacer().items()
                  if nombre.startswith("consultar")),
          v.lo_que_se_puede_hacer())

# Se deja como estaba para lo que viene detras.
v.bloqueada = False
v._arranque_terminado = True
v.limpiar_cintas()
v.caja.delete("1.0", "end")
v.caja.insert("1.0", "una duda cualquiera")
v.ejercicio.set("2023")
v._revisar_boton()
bombear(0.25)

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

        Se cuenta solo lo que se VE: desde que la lista de normas se pliega,
        las etiquetas del detalle siguen creadas pero no estan puestas.
        Contarlas seria medir una pantalla que nadie ve.

        SE PREGUNTA `winfo_ismapped`, NO `winfo_manager`. Cambiado el
        29/08/2026 al plegarse tambien el bloque de mantenimiento: aquel
        pliegue quita las etiquetas UNA A UNA y este quita el marco que las
        contiene. Una etiqueta dentro de un marco retirado sigue teniendo
        gestor -es hija de algo con `pack`- y `winfo_manager` la daba por
        visible. `winfo_ismapped` mira la cadena entera hasta la ventana, que
        es lo que decide si un ojo la ve.
        """
        acc = [] if acc is None else acc
        try:
            if isinstance(w, tk.Label) and w.winfo_ismapped():
                acc.append(str(w.cget("text")))
        except tk.TclError:
            pass
        for h in w.winfo_children():
            textos(h, acc)
        return acc

    def _todos(w, acc=None):
        acc = [] if acc is None else acc
        acc.append(w)
        for h in w.winfo_children():
            _todos(h, acc)
        return acc

    dentro = "\n".join(textos(ventana))
    comprobar("dice las normas cargadas", "NORMAS CARGADAS" in dentro)
    comprobar("con el total de articulos", "en total" in dentro, dentro[:80])
    comprobar("nombra los dos botones",
              interfaz.BOTON_LEY in dentro and interfaz.BOTON_CRITERIO in dentro)
    comprobar("y NO dice lo que cuesta ninguno",
              not any(x in dentro for x in ("€", "0,13", "0,22")),
              [l for l in dentro.splitlines()
               if any(x in l for x in ("€", "0,13", "0,22"))][:3])

    # ────────────────────────────────────────────────────────────────────
    # LA TELEMETRIA SE PLIEGA. CAMBIADO EL 29/08/2026.
    # ────────────────────────────────────────────────────────────────────
    #
    # Aqui se exigia que la primera pantalla dijera cuantas consultas de la
    # DGT hay, cuantas resoluciones y si las fuentes responden. Las tres son
    # ciertas y ninguna cambia lo que hace quien viene a preguntar «¿esta mi
    # impuesto dentro?»: son de quien CUIDA la herramienta.
    #
    # LA DIFERENCIA ENTRE ESCONDER Y PLEGAR ES SI SE PUEDE LLEGAR, asi que lo
    # que se comprueba ahora son las dos cosas: que NO ocupan la pantalla de
    # llegada, y que estan enteras a UN CLIC. Sin la segunda mitad, esta
    # reescritura seria un recorte disfrazado.
    comprobar("el mantenimiento tiene su sitio, y esta plegado",
              "MANTENIMIENTO" in dentro
              and "Dirección General de Tributos" not in dentro,
              dentro[:120])
    comprobar("y no gasta la pantalla de llegada en si las fuentes responden",
              # Se busca el ROTULO del canario, no la palabra «DYCTEA»:
              # `AVISO_DESPENSA` la nombra tambien, y ahi dice DONDE MIRAR,
              # que es otra cosa y si tiene que estar.
              "Tributos (consultas de la DGT)" not in dentro
              and "no impide consultar" not in dentro,
              [l for l in dentro.splitlines()
               if "Tributos (consultas" in l or "no impide consultar" in l][:2])

    plegables = [w for w in _todos(ventana)
                 if isinstance(w, ttk.Button)
                 and "estado de la herramienta" in str(w.cget("text"))]
    comprobar("hay un boton para abrirlo", len(plegables) == 1,
              str(len(plegables)))
    if plegables:
        plegables[0].invoke()
        bombear(0.3)
        abierto = "\n".join(textos(ventana))
        comprobar("abierto, dice cuantas consultas de la DGT hay guardadas",
                  "consulta(s) de la DGT" in abierto, abierto[-300:])
        comprobar("y cuantas resoluciones", "resolución(es)" in abierto)
        comprobar("y si las fuentes responden ahora mismo (el canario)",
                  "Tributos (consultas de la DGT)" in abierto
                  and "DYCTEA" in abierto)
        comprobar("y que el corpus esta entero",
                  "sello" in abierto.lower() or "íntegr" in abierto.lower()
                  or "corpus" in abierto.lower(), abierto[-300:])
        comprobar("avisa de que una fuente caida NO impide consultar",
                  "no impide consultar" in abierto)
        # LO QUE HAY DENTRO DE MANTENIMIENTO, comprobado una a una: son las
        # cuatro cosas que se movieron aqui, y si alguna se cae por el camino
        # nadie lo notaria — nadie mira este panel a diario.
        comprobar("y cuando se bajaron las normas del BOE",
                  "Bajada el" in abierto or "días" in abierto, abierto[-200:])
        comprobar("el bloque se puede volver a cerrar",
                  "Ocultar" in plegables[0].cget("text"),
                  plegables[0].cget("text"))
        plegables[0].invoke()      # se deja como estaba, cerrado
        bombear(0.3)
        cerrado = "\n".join(textos(ventana))
        comprobar("  y cerrado vuelve a no ocupar la pantalla de llegada",
                  "Tributos (consultas de la DGT)" not in cerrado,
                  [l for l in cerrado.splitlines()
                   if "Tributos (consultas" in l][:1])
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
    dice = v.estado_en_pantalla()["hecha_con"]
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
# Ocho desde que el NO ENCONTRADO puede orientar: el titulo de la orientacion
# y su pie tambien son frases que se leen en pantalla, y por tanto tienen que
# estar en la hoja que hay encima de la mesa.
comprobar("se comprueban TODAS las frases de estado, las ocho",
          len(interfaz.TEXTOS_DE_ESTADO) == 8,
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
# LO QUE TIENE QUE QUEDARSE QUIETO ES LA MEDIDA DE LECTURA, no el margen.
# Mientras la banda iba encima, «margen creciente» y «medida constante» eran
# lo mismo. Con la columna al lado ya no: al pasar de 1.290 a 1.310 px
# aparecen 400 px de columna y el margen BAJA, y sin embargo el parrafo mide
# exactamente igual. Se comprueba la medida, que es lo que se decidio.
medidas = []
for an in (1000, 1400, raiz.winfo_screenwidth()):
    raiz.geometry(f"{an}x820")
    bombear(0.55)
    izq = int(str(v.texto.tag_cget("columna", "lmargin1") or 0))
    medidas.append(v.texto.winfo_width() - 2 * izq - 2 * interfaz.RELLENO)
print(f"    ancho de ventana -> medida de lectura: {medidas}")
comprobar("la MEDIDA de lectura no cambia con el ancho de la ventana",
          max(medidas) - min(medidas) <= 40, str(medidas))
comprobar("y es la que se decidio, no la que sobra",
          abs(max(medidas)
              - v.fuente_texto.measure("0" * interfaz.COLUMNA_MAXIMA)) < 60,
          f"{medidas} vs {v.fuente_texto.measure('0' * interfaz.COLUMNA_MAXIMA)}")
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
# LO QUE NO PUEDE ES COMERSE EL ALTO DE LA RESPUESTA. Al lado, la banda mide
# lo que quiera -esta en espacio que antes estaba en blanco- y lo que hay que
# mirar es donde EMPIEZA el texto. Encima, es lo mismo de siempre.
arriba_del_texto = v.texto.winfo_rooty() - v.lienzo_lectura.winfo_rooty()
print(f"    lateral={v._lateral} · encima del texto quedan "
      f"{arriba_del_texto} px")
comprobar("lo que va antes de la respuesta no se come mas de un cuarto de "
          "la ventana", arriba_del_texto < raiz.winfo_height() * 0.28,
          f"{arriba_del_texto} px de {raiz.winfo_height()}")

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
print("  Se rompe lo que hace crecer al texto y se comprueba que el 12 lo caza.")
print("  Antes se le quitaba el peso a su fila del `grid`; desde que el texto")
print("  mide lo que mide su contenido, quitarle el peso ya no le hace nada:")
print("  lo que lo dejaria en una rendija es que no se le ajuste el alto.\n")
_ajustar = interfaz.Ventana._ajustar_alto_del_texto
try:
    interfaz.Ventana._ajustar_alto_del_texto = lambda self: None
    v.texto.configure(height=1)
    bombear(0.8)
    roto = max(0, (v.lienzo_lectura.winfo_height()
                   - (v.texto.winfo_rooty() - v.lienzo_lectura.winfo_rooty())
                   - 2 * interfaz.RELLENO)) // alto_linea
    roto = min(roto, int(v.texto.cget("height")))
    print(f"    sin ajustar el alto: {roto} lineas visibles")
    comprobar("sin el ajuste, la respuesta se queda en una rendija",
              roto < 5, f"{roto} lineas: la mutacion no ha roto nada")
    comprobar("y el bloque 12 lo habria cazado", not roto >= 20)
finally:
    interfaz.Ventana._ajustar_alto_del_texto = _ajustar
v._ajustar_alto_del_texto()
bombear(0.8)
_vuelta = max(0, (v.lienzo_lectura.winfo_height()
                  - (v.texto.winfo_rooty() - v.lienzo_lectura.winfo_rooty())
                  - 2 * interfaz.RELLENO)) // alto_linea
comprobar("al deshacerlo vuelve a las veinte", _vuelta >= 20, str(_vuelta))

# =====================================================================
print("\n=== 13 bis. LA DISPOSICION LA DECIDE EL LARGO, Y NO BAILA ===")
print("  Al lado gana con respuestas largas y PIERDE con las cortas: medido,")
print("  una de 10 lineas deja 293 px en blanco apilada y 489 al lado, que es")
print("  la queja original. Asi que decide el largo, no solo el ancho.\n")

raiz.geometry(f"{raiz.winfo_screenwidth()}x{raiz.winfo_screenheight() - 80}+0+40")
bombear(0.6)

v._terminar(dict(LARGO))
bombear(1.0)
print(f"    respuesta larga: {v._lineas_de_respuesta} lineas · "
      f"larga={v._respuesta_larga} · lateral={v._lateral}")
comprobar("una respuesta larga se declara larga", v._respuesta_larga)
comprobar("y la banda se va al lado", v._lateral)
comprobar("  de verdad: la banda esta a la derecha del texto",
          v.banda.winfo_rootx() > v.texto.winfo_rootx() + 100,
          f"banda x={v.banda.winfo_rootx()} texto x={v.texto.winfo_rootx()}")

CORTA = dict(LARGO)
CORTA["respuesta"] = "Sí, con los requisitos del artículo 80."
v._terminar(CORTA)
bombear(1.0)
print(f"    respuesta corta: {v._lineas_de_respuesta} lineas · "
      f"larga={v._respuesta_larga} · lateral={v._lateral}")
comprobar("una respuesta corta NO se declara larga",
          not v._respuesta_larga, str(v._lineas_de_respuesta))
comprobar("y la banda vuelve encima, que es lo que llena el alto",
          not v._lateral)

# Y LO QUE NO PUEDE PASAR: que cambie de disposicion al arrastrar el borde.
v._terminar(dict(LARGO))
bombear(1.0)
decisiones = []
for an in (1638, 1400, 1330, 1301, 1300, 1299, 1290, 1400, 1638):
    raiz.geometry(f"{an}x900+0+0")
    bombear(0.25)
    decisiones.append((raiz.winfo_width(), v._lateral, v._respuesta_larga))
largos = {g for _a, _l, g in decisiones}
print(f"    al redimensionar: {[(a, l) for a, l, _g in decisiones]}")
comprobar("el LARGO se decide una vez y no cambia al redimensionar",
          largos == {True}, str(decisiones))
cambios = sum(1 for i in range(1, len(decisiones))
              if decisiones[i][1] != decisiones[i - 1][1])
comprobar("y la disposicion solo cambia al cruzar el umbral de ancho, "
          "una vez por cruce", cambios == 2, f"{cambios} cambios: {decisiones}")
comprobar("  por debajo del umbral, apilado aunque la respuesta sea larga",
          not [l for a, l, _g in decisiones if a < interfaz.ANCHO_LATERAL and l],
          str(decisiones))

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

# =====================================================================
print("\n=== 14 bis. LA ESPERA, EN SEIS PASOS ===")
print("  Una consulta real tarda 102 s de mediana. Los seis pasos ya se")
print("  emitian uno a uno; la ventana los pisaba en una sola linea.\n")
import fase4 as _F4  # noqa: E402

# LA QUE IMPIDE QUE ESTO SE MUERA EN SILENCIO.
#
# Si la ventana emparejara los pasos por su TEXTO, reescribir un mensaje en
# `fase4` dejaria la lista clavada en el primer paso sin que nada fallara. Se
# emparejan por CLAVE, y aqui se comprueba que las dos partes hablan de las
# mismas: las que emite el motor y las que tiene la ventana.
_fuente_f4 = (RAIZ / "fase4.py").read_text("utf-8")
# SIN EL PUNTO DELANTE. `fase4` tiene DOS `paso(`: la funcion local que avisa a
# la ventana, y `tr.paso(...)`, que apunta un hito en el expediente. Son cosas
# distintas con el mismo nombre, y contar las dos daba «busqueda», «ejercicio»,
# «pertinencia», «tope» y «orientacion» como pasos de pantalla que no lo son.
_emitidas = set(re.findall(r'(?<![.\w])paso\(\s*"([a-z]+)"', _fuente_f4))
comprobar("todo paso que emite el motor esta declarado en fase4.PASOS",
          _emitidas <= set(_F4.CLAVES_DE_PASO),
          sorted(_emitidas - set(_F4.CLAVES_DE_PASO)))
comprobar("y todo paso declarado se llega a emitir: ninguno es decoracion",
          set(_F4.CLAVES_DE_PASO) <= _emitidas,
          sorted(set(_F4.CLAVES_DE_PASO) - _emitidas))
comprobar("la ventana tiene una fila por cada paso del motor",
          set(v.filas_paso) == set(_F4.CLAVES_DE_PASO),
          sorted(set(v.filas_paso) ^ set(_F4.CLAVES_DE_PASO)))
comprobar("son seis, no una linea", len(_F4.PASOS) == 6, len(_F4.PASOS))


def _puestos():
    return [c for c, _r in _F4.PASOS if v.filas_paso[c][0].winfo_manager()]


def _marca(c):
    return v.filas_paso[c][1].cget("text")


v._armar_pasos(False)
v.marco_pasos.pack(fill="x")
bombear(0.3)
comprobar("solo con la ley NO se enseña el paso del criterio",
          _F4.PASO_SOLO_CON_CRITERIO not in _puestos(), _puestos())
comprobar("  y quedan cinco: un paso que no va a ocurrir no se promete",
          len(_puestos()) == 5, _puestos())
v._armar_pasos(True)
bombear(0.3)
comprobar("con criterio se enseñan los seis", len(_puestos()) == 6, _puestos())
comprobar("  y todos empiezan pendientes",
          all(_marca(c) == "·" for c in _puestos()),
          [_marca(c) for c in _puestos()])
for clave in ("analisis", "ley", "criterio"):
    v._marcar_paso(clave)
bombear(0.3)
comprobar("lo hecho queda marcado como hecho",
          _marca("analisis") == "✓" and _marca("ley") == "✓",
          [_marca("analisis"), _marca("ley")])
comprobar("  el de ahora se distingue de los hechos y de los que faltan",
          _marca("criterio") == "·"
          and v.filas_paso["criterio"][2].cget("fg") == interfaz.TINTA
          and v.filas_paso["estado"][2].cget("fg") == interfaz.TINTA3,
          v.filas_paso["criterio"][2].cget("fg"))
# UN PASO SALTADO NO DEJA LA LISTA A MEDIAS. Se cierra todo lo anterior, no
# solo el paso justo anterior.
v._armar_pasos(True)
v._marcar_paso("verificacion")
bombear(0.3)
comprobar("saltando pasos, los de atras quedan cerrados y no colgando",
          all(_marca(c) == "✓" for c in ("analisis", "ley", "criterio",
                                         "redaccion")),
          [_marca(c) for c in ("analisis", "ley", "criterio", "redaccion")])
# NI UN PORCENTAJE: no hay forma de saber cuanto falta, y fingirlo es mentir.
comprobar("la barra sigue siendo indeterminada, sin porcentaje falso",
          str(v.barra.cget("mode")) == "indeterminate", v.barra.cget("mode"))
# Y UNA CLAVE DESCONOCIDA NO TUMBA LA VENTANA.
reventado = None
try:
    v._marcar_paso("un-paso-que-no-existe")
except Exception as exc:  # noqa: BLE001
    reventado = exc
comprobar("una clave que la ventana no conoce no revienta nada",
          reventado is None, repr(reventado))
v.marco_pasos.pack_forget()

# =====================================================================
print("\n=== 14 ter. NINGUNA PULSACION MUDA ===")
print("  Viene de `prueba_boton` §3bis -aquella suite es hoy")
print("  `prueba_arranque`, con lo que si era suyo-. Un boton que")
print("  se puede pulsar y se queda quieto es PEOR que uno apagado: apagado")
print("  al menos se ve que no toca.")
print("  SIN VENTANA PROPIA: alli abria una quinta Tk para esto; aqui usa la")
print("  que ya hay. Cinco ventanas menos por pasada es cinco robos de foco")
print("  menos, que es de donde salian las rojas intermitentes.\n")
import contextlib as _ctx  # noqa: E402
import io as _io  # noqa: E402

_guardado = (v.traza_actual, v.trabajando, v.bloqueada, v.motor)
v.motor = object()
v.bloqueada = False


def pulsar(f, *a):
    """Pulsa y devuelve lo que se ve DESPUES.

    La cinta se limpia antes para no dar por bueno un mensaje que ya estaba
    puesto, y se PREGUNTA a la ventana lo que se ve: desde que los avisos se
    apilan, `aviso_motor` es solo la fila de «ahora».
    """
    v.limpiar_cintas()
    with _ctx.redirect_stdout(_io.StringIO()):
        f(*a)
    bombear(0.2)
    return "  ".join(v.cintas_visibles())


# A · SEGUIR sin nada escrito.
v.traza_actual = "/una/traza"
v.trabajando = False
v.caja_seguir.delete("1.0", "end")
dicho = pulsar(v._seguir)
comprobar("seguir con la caja vacia lo DICE", bool(dicho), "no dice nada")
comprobar("  y manda a escribir algo", "Escribe primero" in dicho, dicho[:80])

# B · SEGUIR con una consulta en marcha.
v.caja_seguir.insert("1.0", "y si fuera una furgoneta")
v.trabajando = True
dicho = pulsar(v._seguir)
comprobar("seguir con una consulta en marcha lo DICE", bool(dicho),
          "no dice nada")
v.trabajando = False

# C · SEGUIR sin expediente: el disco lleno.
v.traza_actual = ""
dicho = pulsar(v._seguir)
comprobar("seguir sin expediente lo DICE", bool(dicho), "no dice nada")
comprobar("  y dice la causa probable", "disco lleno" in dicho, dicho[:90])
v.traza_actual = "/una/traza"

# D · SEGUIR con el agente sin preparar.
v.motor = None
dicho = pulsar(v._seguir)
comprobar("seguir con el agente sin preparar lo DICE", bool(dicho),
          "no dice nada")
comprobar("  y manda al diagnostico, que deja un fichero que se envia",
          "diagnostico" in dicho, dicho[:90])
v.motor = object()

# E · REESCRIBIR en las mismas cuatro situaciones.
v.traza_actual = ""
dicho = pulsar(v._escribir_para_cliente)
comprobar("reescribir sin expediente lo DICE", bool(dicho), "no dice nada")
v.traza_actual = "/una/traza"
v.trabajando = True
dicho = pulsar(v._escribir_para_cliente)
comprobar("reescribir con algo en marcha lo DICE", bool(dicho), "no dice nada")
v.trabajando = False
v.motor = None
dicho = pulsar(v._escribir_para_cliente)
comprobar("reescribir sin motor lo DICE", bool(dicho), "no dice nada")
comprobar("  y manda al diagnostico, que deja un fichero que se envia",
          "diagnostico" in dicho, dicho[:90])
v.motor = object()

# F · UNA RESPUESTA BUENA SIN EXPEDIENTE. El disco lleno: la respuesta vale,
# pero no hay carpeta de donde reescribir.
v.limpiar_cintas()
with _ctx.redirect_stdout(_io.StringIO()):
    v._terminar({"estado": EST.CLARO, "respuesta": "un texto cualquiera",
                 "traza": "", "expediente": False, "preceptos": [],
                 "preceptos_enviados": [], "analisis": {}, "senales": [],
                 "cobertura": [], "con_criterio": False, "codigo": 0,
                 "motor": "anthropic", "ejercicio": 2023, "aporte": {},
                 "estructural": "", "recuperado": [], "fallo": None})
bombear(0.3)
comprobar("con respuesta pero SIN expediente, reescribir queda apagado",
          not v.lo_que_se_puede_hacer()["cliente"], v.lo_que_se_puede_hacer())
visible = "  ".join(v.cintas_visibles())
comprobar("  y se explica en vez de quedarse gris en silencio",
          "expediente" in visible, visible[:110])
comprobar("  diciendo que la respuesta de arriba SI vale",
          "válida" in visible, visible[:110])

v.traza_actual, v.trabajando, v.bloqueada, v.motor = _guardado
v.limpiar_cintas()

# =====================================================================
print("\n=== 15. CONTROL NEGATIVO: ¿CAZA ESTA SUITE LO QUE DICE CAZAR? ===")
print("  Tres comprobaciones de arriba se REESCRIBIERON el 29/08/2026 al")
print("  invertir decisiones. Una prueba que se cambia para que pase no")
print("  prueba nada, asi que aqui se rompe el codigo de verdad y se mira")
print("  que los predicados de arriba se pongan en rojo.\n")

raiz.destroy()
raiz2 = tk.Tk()

# --- 1 · se rompe el relleno del año: el campo vuelve a nacer vacio ---
interfaz.Ventana._proponer_ejercicio_bueno = interfaz.Ventana._proponer_ejercicio
interfaz.Ventana._proponer_ejercicio = lambda self: None
vn = interfaz.Ventana(raiz2, "ensayo")
fin = time.time() + 1.0
while time.time() < fin:
    raiz2.update()
    time.sleep(0.01)
comprobar("roto el relleno, la suite lo caza (el campo sale vacio)",
          not (vn.ejercicio.get().strip() != ""), repr(vn.ejercicio.get()))
comprobar("y tambien caza que el campo deje de decir de donde salio",
          not (vn.marca_ejercicio.cget("text") == interfaz.MARCA_EN_CURSO),
          vn.marca_ejercicio.cget("text"))
interfaz.Ventana._proponer_ejercicio = interfaz.Ventana._proponer_ejercicio_bueno

# --- 2 · se rompe el ocultado: el bloque vacio vuelve a pintarse ---
vn._pintar_avisos(["algo"], ["algo"])
fin = time.time() + 0.4
while time.time() < fin:
    raiz2.update()
    time.sleep(0.01)
comprobar("con avisos de verdad el panel SI se pinta (si no, la de arriba "
          "seria verde por accidente)",
          vn.panel_avisos.winfo_ismapped())

# --- 3 · se rompe el traslado del limite: se quita de debajo del texto ---
interfaz.Ventana._escribir_limite_bueno = interfaz.Ventana._escribir_limite
interfaz.Ventana._escribir_limite = lambda self, res: None
vn._terminar({"codigo": 0, "estado": EST.CLARO, "fallo": None, "senales": [],
              "cobertura": [], "estructural": LIMITE, "preceptos": [],
              "traza": None, "recuperado": [], "respuesta": "Sale al 21%."})
fin = time.time() + 0.4
while time.time() < fin:
    raiz2.update()
    time.sleep(0.01)
comprobar("roto el traslado del limite, la suite lo caza (ya no se lee)",
          not (LIMITE in vn.texto.get("1.0", "end")))
interfaz.Ventana._escribir_limite = interfaz.Ventana._escribir_limite_bueno

raiz2.destroy()
print("\n" + "=" * 62)
print(f"COMPROBACIONES: {len(fallos)} fallos")
for f in fallos:
    print("  -", f)
sys.exit(1 if fallos else 0)
