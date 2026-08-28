#!/bin/bash
# Doble clic para reparar una copia que no se puede actualizar. Mac.
#
# El gemelo de reparar.bat. Como todos los lanzadores de este proyecto, solo
# hace las dos cosas que Python no puede hacerse a si mismo -encontrar un Python
# y recuperar el fichero si falta-; todo lo demas esta en reparar.py, en un solo
# sitio y con un solo comportamiento.
#
# LO PRIMERO ES RECUPERAR reparar.py, y no es exceso de celo: esto lo ejecuta
# quien tiene el arbol a medias, y un checkout abortado puede haberse llevado
# por delante justo el fichero que viene a arreglarlo.
cd "$(dirname "$0")" || exit 1
echo
echo "======================================================================"
echo "  REPARAR LA COPIA"
echo "======================================================================"
echo

if ! git --version >/dev/null 2>&1; then
  echo "  No hay git en este equipo, y sin git no se puede reparar nada."
  echo "  Avisa a Emili."
  echo
  read -r -p "  Pulsa INTRO para cerrar. "
  exit 1
fi

if [ ! -f "reparar.py" ]; then
  echo "  Falta reparar.py: se recupera de GitHub."
  git fetch --quiet 2>/dev/null
  git checkout FETCH_HEAD -- reparar.py 2>/dev/null || git checkout HEAD -- reparar.py 2>/dev/null
fi
if [ ! -f "reparar.py" ]; then
  echo "  No se ha podido recuperar reparar.py. Avisa a Emili."
  echo
  read -r -p "  Pulsa INTRO para cerrar. "
  exit 1
fi

# El del entorno primero: es el que abre el agente de verdad. Si no esta, el del
# sistema, que para esto vale igual -reparar.py no importa nada del proyecto-.
PY=""
if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
elif command -v python >/dev/null 2>&1; then
  PY="python"
else
  echo "  No hay Python en este equipo. Instalalo desde python.org y vuelve."
  echo
  read -r -p "  Pulsa INTRO para cerrar. "
  exit 1
fi

"$PY" reparar.py "$@"
CODIGO=$?
echo
read -r -p "  Pulsa INTRO para cerrar. "
exit $CODIGO
