#!/bin/bash
# Doble clic desde el Finder para abrir la ventana de consulta. Mac.
#
# Si algo falla, esta ventana NO se cierra: se queda con la explicacion en
# pantalla. Una terminal negra que se cierra sola no dice nada; una terminal
# negra que se queda abierta sin texto, tampoco. Aqui siempre hay una frase.

cd "$(dirname "$0")" || exit 1

fallar() {
  echo ""
  echo "======================================================================"
  echo "  NO SE HA PODIDO ABRIR EL AGENTE"
  echo "======================================================================"
  echo ""
  echo "  $1"
  echo ""
  echo "  Avisa a Emili y ensenale esta ventana."
  echo ""
  read -r -p "  Pulsa INTRO para cerrar. "
  exit 1
}

PY=".venv/bin/python"
[ -x "$PY" ] || fallar "Falta la instalacion (no existe la carpeta .venv)."

"$PY" -c "import tkinter" 2>/dev/null \
  || fallar "Este Python no puede dibujar ventanas (le falta tkinter)."

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
