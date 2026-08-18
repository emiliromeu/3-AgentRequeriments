#!/bin/bash
# Doble clic para recoger el diagnostico. Mac.
#
# El gemelo de diagnostico.bat. Aqui la terminal se abre sola y se ve
# todo, pero se guarda el fichero IGUAL: lo que hace falta enviar es un
# adjunto, no una captura de pantalla.
cd "$(dirname "$0")" || exit 1
PY=".venv/bin/python"
[ -x "$PY" ] || PY="python3"
rm -f diagnostico.txt
"$PY" comprobar_equipo.py > diagnostico.txt 2>&1
cat diagnostico.txt
echo
echo "  ------------------------------------------------------------------"
echo "  Guardado en: $(pwd)/diagnostico.txt"
echo "  Enviaselo a Emili tal cual."
echo
read -r -p "  Pulsa Enter para cerrar. "
