#!/bin/bash
# ABRIR EL AGENTE. Doble clic desde el Finder. Mac.
#
# Este fichero solo sabe hacer las dos cosas que Python no puede hacerse a si
# mismo: ENCONTRAR un Python y CREAR el entorno virtual. Todo lo demas -las
# librerias, la clave, el corpus- lo hace instalar.py, que es EL MISMO fichero
# que usa Windows. Un solo sitio, un solo comportamiento.
#
# Si algo falla, esta ventana NO se cierra: lo que salga hay que poder leerlo.

# Con expansion del propio shell y NO con `dirname`: dirname es un programa
# externo, y si el PATH viene raro no esta. Un lanzador que necesita el PATH
# para averiguar donde vive es un lanzador que se rompe justo en el equipo mal
# configurado, que es el unico donde importa.
case "$0" in
  */*) cd "${0%/*}" || exit 1 ;;
esac

PY=".venv/bin/python3"
[ -x "$PY" ] || PY=".venv/bin/python"

fallar() {
  echo ""
  echo "======================================================================"
  echo "  NO SE HA PODIDO ABRIR EL AGENTE"
  echo "======================================================================"
  echo ""
  echo "  $1"
  if [ -n "$2" ]; then
    echo ""
    printf '  %s\n' "$2"
  fi
  echo ""
  echo "  Avisa a Emili y ensenale esta ventana."
  echo ""
  read -r -p "  Pulsa INTRO para cerrar. "
  exit 1
}

# --- CAMINO RAPIDO -----------------------------------------------------
# Si esta todo, se abre y ya. Comprobaciones de fichero, sin arrancar Python:
# en un arranque normal esto no se nota.
listo=1
[ -x "$PY" ] || listo=0
[ -f ".env" ] || listo=0
grep -q '^ANTHROPIC_API_KEY=sk-' .env 2>/dev/null || listo=0
# La libreria tambien: sin ella el agente abre y falla en la primera consulta,
# que es justo el descubrimiento tardio que esto viene a evitar. Es una
# comprobacion de carpeta, no cuesta nada.
ls -d .venv/lib/python*/site-packages/anthropic >/dev/null 2>&1 || listo=0
# EL CORPUS LO DECIDE QUIEN SABE CUANTAS NORMAS HAY, NO ESTE FICHERO.
#
# Aqui habia una lista de TRES normas escrita a mano. Cuando el corpus paso a
# trece, esta lista se quedo igual: con las diez nuevas ausentes el camino
# rapido daba «todo listo», no se ejecutaba el instalador, y la ventana
# bloqueaba con «falta el texto de las normas» sin que nada lo arreglara. Es
# la misma lista a mano que ya nos ha costado cuatro frases en pantalla.
#
# `instalar.py --revisar` son comprobaciones de fichero: no carga el corpus ni
# habla con la red.
if [ "$listo" = "1" ]; then
  "$PY" instalar.py --revisar >/dev/null 2>&1 || listo=0
fi

if [ "$listo" = "0" ]; then
  # --- 1. HAY PYTHON? --------------------------------------------------
  # Es lo unico que necesita a una persona: no se puede instalar Python solo.
  if [ ! -x "$PY" ]; then
    BASE=""
    for c in python3 python; do
      if command -v "$c" >/dev/null 2>&1; then BASE="$c"; break; fi
    done
    if [ -z "$BASE" ]; then
      echo ""
      echo "======================================================================"
      echo "  FALTA PYTHON EN ESTE EQUIPO"
      echo "======================================================================"
      echo ""
      echo "  El agente necesita Python y este equipo no lo tiene. Es lo unico"
      echo "  que hay que instalar a mano; el resto se hace solo."
      echo ""
      echo "    1. Entra en   https://www.python.org/downloads/"
      echo "    2. Descarga la version para macOS y ejecuta el instalador."
      echo "    3. Acepta todo lo que proponga por defecto."
      echo ""
      echo "  Cuando termine, vuelve a hacer doble clic en abrir_agente."
      echo ""
      read -r -p "  Pulsa INTRO para cerrar. "
      exit 1
    fi

    # --- 2. CREAR EL ENTORNO -------------------------------------------
    echo ""
    echo "  Preparando el agente por primera vez. No cierres esta ventana."
    echo ""
    echo "  [1/2] Creando el espacio de trabajo del programa..."
    "$BASE" -m venv .venv
    PY=".venv/bin/python3"
    [ -x "$PY" ] || PY=".venv/bin/python"
    [ -x "$PY" ] || fallar \
      "No se ha podido crear el espacio de trabajo del programa." \
      "Suele ser que la instalacion de Python esta incompleta: reinstalala desde python.org."
    echo "        Listo."
  fi

  # --- 3 a 5. LIBRERIAS, CLAVE Y CORPUS --------------------------------
  "$PY" instalar.py || { echo ""; read -r -p "  Pulsa INTRO para cerrar. "; exit 1; }
fi

# --- 6. ABRIR LA VENTANA -----------------------------------------------
"$PY" -c "import tkinter" 2>/dev/null \
  || fallar "Este Python no puede dibujar ventanas (le falta tkinter)." \
            "Hay que reinstalar Python desde python.org."

# La carpeta tiene que existir ANTES de escribir dentro: si no, falla la propia
# redireccion y el fallo que se ensena es el que no es.
mkdir -p datos

# Se lanza suelta y se cierra la ventana de Terminal: la gente no tiene por que
# ver una consola. Si el programa falla al arrancar, escribe en arranque.log.
nohup "$PY" interfaz.py "$@" >> datos/arranque.log 2>&1 &
SUYO=$!
sleep 2

if ! kill -0 "$SUYO" 2>/dev/null; then
  echo ""
  tail -n 15 datos/arranque.log
  fallar "La ventana se cerro nada mas abrirse (arriba esta el detalle)."
fi

osascript -e 'tell application "Terminal" to close (every window whose name contains "abrir_agente")' >/dev/null 2>&1 &
exit 0
