#!/bin/bash
# LA CADENA DE SESIONES DEL GOTEO DEL TEAC. Desatendida, toda la noche.
#
#     ./cadena_teac.sh [minutos-por-sesion] [tope-de-sesiones]
#     ./cadena_teac.sh 5 1      <- la prueba pequeña, MISMO camino
#     ./cadena_teac.sh          <- 90 x 12, que es lo de verdad
#
# LA GEMELA DE `cadena_siembra.sh`, y con sus mismas tres reglas, que no son de
# estilo: cada una salio de algo que paso.
#
# 1. TERMINA POR TRABAJO, NO POR CUENTA. Cuando no queda nada por mirar,
#    `gotear_teac.py` devuelve 2 y la cadena acaba BIEN. Sin eso, la cadena
#    seguiria pidiendo sesiones vacias hasta agotar el numero: en la DGT eso
#    fueron ~2.200 peticiones a un servicio publico para traer nada.
#
# 2. LA PUERTA, AL CERRAR CADA TANDA. Lo bajado AHORA tiene que poder
#    encontrarse por (norma, articulo). Si no llega al 100%, la cadena PARA y
#    lo deja escrito. Bajar y no poder encontrarlo ocupa disco, parece
#    cobertura y no lo es: 118 criterios se sembraron asi y se descubrio tres
#    dias despues, mirando a mano.
#
# 3. SE RESPIRA ENTRE TANDAS. Encadenadas sin pausa son horas de carga
#    sostenida sobre un servicio publico. Cinco minutos no cambian nada para
#    nosotros y parten la carga en trozos.
#
# NO COMMITEA. Lo bajado se queda sin comprometer a proposito: subir es una
# decision de una persona que ha mirado antes. Al final del log queda escrito
# que hay que ejecutar por la mañana.
set -u

MINUTOS="${1:-90}"
TOPE="${2:-12}"

cd "$(dirname "$0")" || exit 1
PY=".venv/bin/python"
LOG="datos/teac/cadena_teac.log"
mkdir -p datos/teac

{
  echo ""
  echo "=================================================================="
  echo "=== CADENA TEAC · inicio $(date '+%d/%m %H:%M:%S')"
  echo "=== hasta ${TOPE} sesiones de ${MINUTOS} min, o hasta que se agote"
  echo "=== para sola si una tanda baja algo que no se puede encontrar"
  echo "=================================================================="
} >> "$LOG"

para_por_la_puerta=0

for ((i = 1; i <= TOPE; i++)); do
  {
    echo ""
    echo "########## TEAC · SESION ${i} de ${TOPE} · $(date '+%d/%m %H:%M:%S')"
  } >> "$LOG"

  "$PY" -u gotear_teac.py --minutos "$MINUTOS" >> "$LOG" 2>&1
  codigo=$?

  # PLAN AGOTADO: se termina AQUI, y bien. No es una averia.
  if [ $codigo -eq 2 ]; then
    {
      echo ""
      echo "PLAN AGOTADO EN LA SESION ${i} de ${TOPE} · $(date '+%d/%m %H:%M:%S')"
      echo "  No queda ni un articulo buscable por mirar. Las sesiones que"
      echo "  faltaban no se hacen porque no hace falta."
    } >> "$LOG"
    break
  fi

  if [ $codigo -ne 0 ]; then
    {
      echo ""
      echo "PARADA EN LA SESION ${i} (codigo ${codigo}) $(date '+%d/%m %H:%M:%S')"
      echo "  La sesion no ha terminado bien. La cadena no encadena mas."
    } >> "$LOG"
    para_por_la_puerta=1
    break
  fi

  # ---- LA PUERTA, AL CERRAR LA TANDA ----
  echo "" >> "$LOG"
  echo "---------- puerta de alcanzabilidad, sesion ${i} ----------" >> "$LOG"
  "$PY" medir_alcanzabilidad_teac.py >> "$LOG" 2>&1
  puerta=$?
  if [ $puerta -ne 0 ]; then
    {
      echo ""
      echo "=================================================================="
      echo "LA PUERTA HA PARADO LA CADENA · sesion ${i} · $(date '+%d/%m %H:%M:%S')"
      echo "=================================================================="
      echo "  Se ha bajado material que NO se puede encontrar por (norma,"
      echo "  articulo). No se encadenan mas sesiones: seguir seria bajar mas"
      echo "  de lo mismo."
      echo ""
      echo "  Lo bajado NO se ha comprometido y no se pierde. Arriba estan los"
      echo "  criterios que no se alcanzan, uno por uno."
      echo ""
      echo "  NO HAGAS git add HASTA MIRAR ESO."
    } >> "$LOG"
    para_por_la_puerta=1
    break
  fi

  if [ "$i" -lt "$TOPE" ]; then
    echo "  (pausa de 5 minutos entre sesiones)" >> "$LOG"
    sleep 300
  fi
done

# ---- LO QUE HAY QUE HACER POR LA MAÑANA, ESCRITO AL FINAL ----
#
# Y ESCRITO AQUI Y NO EN UN LEEME: quien lee esto lo lee a las ocho de la
# mañana, con el log delante y sin acordarse de nada de anoche.
{
  echo ""
  echo "=================================================================="
  echo "=== CADENA TERMINADA · $(date '+%d/%m %H:%M:%S')"
  echo "=================================================================="
  echo ""
  echo "  POR LA MAÑANA, EN ESTE ORDEN:"
  echo ""
  echo "  1. Ver como ha quedado:"
  echo "       .venv/bin/python gotear_teac.py --estado"
  echo ""
  echo "  2. Volver a pasar la puerta sobre TODO lo que no esta subido:"
  echo "       .venv/bin/python medir_alcanzabilidad_teac.py"
  echo ""
  if [ "$para_por_la_puerta" -eq 1 ]; then
    echo "     OJO: la cadena PARO por la puerta o por un fallo. Mira mas"
    echo "     arriba en este log ANTES de subir nada."
    echo ""
  fi
  echo "  3. Si la puerta sale limpia, subir:"
  echo "       git add datos/teac"
  echo "       git commit -m \"Goteo del TEAC: <n> criterios\""
  echo "       git push"
  echo ""
  echo "  Y si quieres ver que articulos NO se pueden buscar, y por que:"
  echo "       .venv/bin/python gotear_teac.py --fuera"
  echo ""
  echo "  El commit NO lo hace esta cadena a proposito: subir es una decision"
  echo "  de alguien que ha mirado antes."
} >> "$LOG"
