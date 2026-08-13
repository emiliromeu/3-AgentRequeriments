#!/usr/bin/env python3
"""EL CORPUS ES UNA FOTO, Y LAS FOTOS ENVEJECEN. Cero API.

Es el unico punto donde el agente puede equivocarse SIN AVISAR. Todo lo demas
que puede fallar se nota: una fuente caida se dice, una cita sin verificar no
se enseña, una consulta sin criterio lo declara. Pero una ley que cambio en
marzo y una copia de febrero dan una respuesta impecable, segura y equivocada.

DOS COMPROBACIONES, Y LA BUENA ES LA EXACTA
-------------------------------------------
1. CON RED, exacta: el BOE dice en los metadatos de cada norma cuando la toco
   por ultima vez. Comparado con la fecha en que nosotros la ingerimos, no hay
   umbral que discutir: o ha cambiado o no.

2. SIN RED, por antigüedad: cuando no se puede preguntar, se avisa si la copia
   pasa de `DIAS_SOSPECHOSO`.

EL UMBRAL SALE DE LOS DATOS, NO DE UN NUMERO REDONDO. Medido el 13/08/2026
sobre las diecisiete normas del corpus, mirando cuando las habia tocado el BOE:

    mediana 135 dias · la mas reciente 10 · la mas antigua 239
    tocadas en los ultimos  90 dias:  7 de 17
    tocadas en los ultimos 180 dias: 13 de 17
    tocadas en los ultimos 365 dias: 17 de 17

A los 180 dias, TRECE DE DIECISIETE normas ya han cambiado al menos una vez, o
sea que un corpus de esa edad esta desactualizado casi con seguridad. A los 90
serian siete: avisar ahi seria avisar cuando aun es probable que no haya pasado
nada, y un aviso que salta antes de tiempo se aprende a ignorar. Al año lo han
hecho las diecisiete, asi que esperar tanto es garantizar el fallo.

Y NO SALTA SIEMPRE, que es la otra mitad: reingerir lo apaga, y la mediana dice
que una copia recien hecha aguanta unos cuatro meses antes de acercarse.
"""
import json
from datetime import date, datetime
from pathlib import Path

DIAS_SOSPECHOSO = 180

# Cuando el aviso pasa de «conviene» a «hay que hacerlo»: al año, TODAS las
# normas medidas habian cambiado.
DIAS_SEGURO_VIEJO = 365


def _fecha(texto: str):
    try:
        return datetime.strptime(str(texto)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def edad_del_corpus(dir_corpus: Path, hoy: date | None = None) -> dict:
    """{normas, mas_vieja, dias, sin_fecha}. Sin red y sin cargar el corpus.

    Se lee de `sellos.json`, que ya guarda cuando se ingirio cada norma: la
    fecha no hay que añadirla, hay que MIRARLA. Estaba ahi desde que existen
    los sellos y nadie la usaba para nada.
    """
    hoy = hoy or date.today()
    ruta = Path(dir_corpus) / "sellos.json"
    if not ruta.is_file():
        return {"normas": 0, "mas_vieja": None, "dias": None, "sin_fecha": 0}
    try:
        sellos = json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"normas": 0, "mas_vieja": None, "dias": None, "sin_fecha": 0}

    fechas, sin_fecha = [], 0
    for clave, valor in sellos.items():
        if clave == "sellado" or not isinstance(valor, dict):
            continue
        f = _fecha(valor.get("sellado"))
        if f is None:
            sin_fecha += 1
        else:
            fechas.append((f, clave))
    if not fechas:
        return {"normas": sin_fecha, "mas_vieja": None, "dias": None,
                "sin_fecha": sin_fecha}
    mas_vieja, cual = min(fechas)
    return {"normas": len(fechas) + sin_fecha, "mas_vieja": mas_vieja,
            "cual": cual, "dias": (hoy - mas_vieja).days,
            "sin_fecha": sin_fecha}


def aviso_de_edad(dir_corpus: Path, hoy: date | None = None) -> str:
    """La frase para la ventana, o cadena vacia si no hay nada que decir.

    TRANQUILA Y NO BLOQUEANTE. Un corpus viejo no es una promesa rota: es un
    dato que envejece. Impedir abrir por eso dejaria a la gestoria sin
    herramienta justo el dia que mas prisa tiene, y la respuesta seguiria
    siendo util para todo lo que no haya cambiado. Lo que no vale es callarse.
    """
    e = edad_del_corpus(dir_corpus, hoy)
    dias = e.get("dias")
    if dias is None or dias < DIAS_SOSPECHOSO:
        return ""
    cuando = e["mas_vieja"].strftime("%d/%m/%Y")
    if dias >= DIAS_SEGURO_VIEJO:
        return (f"La copia de las normas es de hace más de un año "
                f"({cuando}). En ese tiempo TODAS las leyes que usa el agente "
                f"han cambiado al menos una vez: conviene actualizarla antes "
                f"de fiarse de una respuesta. Se hace desde «Qué hay dentro».")
    meses = dias // 30
    return (f"La copia de las normas tiene {meses} meses ({cuando}). Las "
            f"leyes fiscales se reforman varias veces al año, así que puede "
            f"que alguna ya haya cambiado. Se actualiza desde «Qué hay "
            f"dentro»; mientras tanto el agente funciona igual.")
