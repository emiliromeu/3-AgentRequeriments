#!/bin/bash
# LA CADENA DE TANDAS DE LA SIEMBRA DE CRITERIO (DGT).
#
#     ./cadena_siembra.sh [tope-por-tanda] [numero-de-tandas]
#     ./cadena_siembra.sh 2 1        <- la prueba pequeña, MISMO camino
#     ./cadena_siembra.sh            <- 300 x 7, que es lo de verdad
#
# POR QUE ES UN GUION Y NO UNA ORDEN SUELTA. La primera vez se lanzo escrita a
# mano en la terminal, y para relanzarla hubo que reconstruirla de memoria
# leyendo el log. Lo que se lanza desatendido se guarda.
#
# LA PUERTA. Cada tanda termina diciendo cuanto de lo que ha bajado AHORA se
# puede encontrar por (norma, articulo). Si no es el 100%, `sembrar.py`
# devuelve 1 y LA CADENA PARA AQUI. Bajar y no poder encontrarlo ocupa disco,
# parece cobertura y no lo es.
#
# Y EL FINAL POR TRABAJO, NO POR CUENTA. Si una tanda entera no baja nada
# nuevo, `sembrar.py` devuelve 2 y la cadena TERMINA BIEN. Antes solo se
# acababa al agotar el numero de tandas: el 13/08 quedaban cuatro por delante
# -unas 2.200 peticiones- cuando ya no habia nada que traer, y hubo que
# cortarla a mano. Un plan se agota por lo que se baja, no por lo que queda.
#
# Y LA PRUEBA PEQUEÑA ANTES DE LA LARGA se hace con ESTE MISMO guion y tope 2,
# no con otra orden parecida: probar el modo barato no prueba el caro.
set -u

TOPE="${1:-300}"
TANDAS="${2:-7}"

cd "$(dirname "$0")" || exit 1
PY=".venv/bin/python"
LOG="datos/siembra/tandas.log"

{
  echo ""
  echo "=== CADENA · inicio $(date '+%d/%m %H:%M:%S') · ${TANDAS} tandas x tope ${TOPE}"
  echo "=== la cadena PARA si una tanda baja algo que no se puede encontrar"
} >> "$LOG"

for ((i = 1; i <= TANDAS; i++)); do
  echo "" >> "$LOG"
  echo "########## DGT · TANDA ${i} · $(date '+%d/%m %H:%M:%S')" >> "$LOG"
  "$PY" sembrar.py sembrar --tope "$TOPE" >> "$LOG" 2>&1
  codigo=$?
  # PLAN AGOTADO: se termina AQUI, y bien. No es una averia.
  if [ $codigo -eq 2 ]; then
    {
      echo ""
      echo "PLAN AGOTADO EN LA TANDA ${i} de ${TANDAS} · $(date '+%d/%m %H:%M:%S')"
      echo "  Una tanda entera sin nada nuevo: no queda nada por sembrar con el"
      echo "  plan de hoy. Las ${TANDAS} tandas no se agotan porque no hace falta."
    } >> "$LOG"
    exit 0
  fi
  # RESPIRAR ENTRE TANDAS. Encadenadas sin pausa son horas de carga sostenida
  # sobre un servicio publico. Cinco minutos no cambian nada para nosotros y
  # parten la carga en trozos.
  if [ $codigo -eq 0 ] && [ "$i" -lt "$TANDAS" ]; then
    echo "  (pausa de 5 minutos entre tandas)" >> "$LOG"
    sleep 300
  fi
  if [ $codigo -ne 0 ]; then
    echo "PARADA EN LA TANDA ${i} (codigo ${codigo}) $(date '+%d/%m %H:%M:%S')" >> "$LOG"
    exit $codigo
  fi
done

echo "" >> "$LOG"
echo "TODO TERMINADO · ${TANDAS} tandas · $(date '+%d/%m %H:%M:%S')" >> "$LOG"
