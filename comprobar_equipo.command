#!/bin/bash
# Doble clic desde el Finder para comprobar el equipo. Mac.
#
# Aqui la ventana de Terminal SI se queda abierta: es lo que hay que leer. Lo
# que no puede pasar es que se quede abierta y VACIA, asi que pase lo que pase
# se escribe algo antes de salir.
#
# Este fichero solo busca un Python y llama a comprobar_equipo.py, que es donde
# estan las seis comprobaciones. Cero llamadas a la API.

cd "$(dirname "$0")" || {
  echo ""
  echo "  No se ha podido entrar en la carpeta del agente."
  echo ""
  echo "  QUE HAY QUE HACER: avisa a Emili."
  echo ""
  read -r -p "  Pulsa INTRO para cerrar. "
  exit 1
}

sin_python() {
  echo ""
  echo "======================================================================"
  echo "  COMPROBACION DEL EQUIPO"
  echo "======================================================================"
  echo ""
  echo "  [1/6] Python ....................... FALTA"
  echo ""
  echo "    No hay Python en este equipo, que es el programa base que el"
  echo "    agente necesita para funcionar."
  echo ""
  echo "    QUE HAY QUE HACER:"
  echo "    Instalalo desde python.org. En Mac, descarga el instalador del"
  echo "    sitio oficial: el Python que trae el sistema no sirve."
  echo ""
  echo "======================================================================"
  echo "  EL EQUIPO NO ESTA LISTO"
  echo ""
  echo "    Falta esto: python"
  echo ""
  echo "======================================================================"
  echo ""
  read -r -p "  Pulsa INTRO para cerrar. "
  exit 1
}

# El del entorno primero: es el que abre el agente de verdad. Si no esta, se
# prueba con el del sistema, que al menos deja diagnosticar lo que falta.
PY=""
if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  sin_python
fi

if [ ! -f "comprobar_equipo.py" ]; then
  echo ""
  echo "  Falta un fichero del agente y no se puede comprobar el equipo."
  echo ""
  echo "  QUE HAY QUE HACER: avisa a Emili."
  echo ""
  read -r -p "  Pulsa INTRO para cerrar. "
  exit 1
fi

"$PY" comprobar_equipo.py
CODIGO=$?

echo ""
read -r -p "  Pulsa INTRO para cerrar. "
exit $CODIGO
