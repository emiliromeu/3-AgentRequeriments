#!/bin/bash
# El gemelo de actualizar.bat, para el Mac. Mismo orden de comprobaciones y
# por los mismos motivos: lo que puede romper el arbol va SIEMPRE despues de
# lo que solo mira.
cd "$(dirname "$0")" || exit 1
echo
echo "======================================================================"
echo "  ACTUALIZAR EL AGENTE"
echo "======================================================================"
echo
git --version >/dev/null 2>&1 || { echo "  No hay git en este equipo."; read -r -p "  Enter para cerrar. "; exit 1; }
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "  Esta carpeta no es una copia del proyecto."; read -r -p "  Enter para cerrar. "; exit 1; }

if [ "$(git config --get core.longpaths)" = "true" ]; then
  echo "  [1/4] Rutas largas ................. ya estaban"
else
  echo "  [1/4] Rutas largas ................. activandolas"
  git config core.longpaths true
fi

if [ -n "$(git status --porcelain)" ]; then
  echo "  [2/4] Cambios sin guardar .......... LOS HAY"
  echo
  git status --short
  echo
  echo "  No se actualiza encima: el pull podria pararse a mitad o borrarlos."
  read -r -p "  Enter para cerrar. "; exit 1
fi
echo "  [2/4] Cambios sin guardar .......... ninguno"

echo "  [3/4] Hablando con GitHub .........."
if ! git fetch --quiet; then
  echo "        NO se puede"
  echo
  echo "  No se ha podido conectar. NO se ha tocado nada."
  echo "  Suele ser permisos, red o una contrasena caducada. Avisa a Emili."
  read -r -p "  Enter para cerrar. "; exit 1
fi
echo "        se puede"

N=$(git rev-list --count HEAD..@{u} 2>/dev/null) || { echo "  Esta copia no esta enlazada con GitHub."; read -r -p "  Enter para cerrar. "; exit 1; }
if [ "$N" = "0" ]; then
  echo "  [4/4] Novedades .................... ninguna"
  echo; echo "  Ya tienes la ultima version."
  read -r -p "  Enter para cerrar. "; exit 0
fi
echo "  [4/4] Novedades .................... $N cambio(s)"
if ! git pull --ff-only; then
  echo
  echo "  NO SE HA PODIDO ACTUALIZAR. Mira la linea de arriba: es lo que dice git."
  echo "  El agente sigue funcionando con la version que ya tenias."
  read -r -p "  Enter para cerrar. "; exit 1
fi
echo; echo "  ACTUALIZADO. Cierra esta ventana y abre el agente."
read -r -p "  Enter para cerrar. "
