# FASE 4 — Analizador y redacción

Estado: **terminada.** Comprobaciones en verde (5/5). Fases 1, 2 y 3 siguen en verde.

```
python fase4.py consultar "texto de la duda" --ejercicio 2023
python fase4.py comprobaciones
python fase4.py consultar "..." --motor ensayo    # sin llamar a ningún modelo
```

Requiere `pip install anthropic` (única dependencia del proyecto, y solo la usa
esta fase). Modelo: `claude-opus-5`.

Códigos de salida: `0` respuesta mostrada · `2` NO ENCONTRADO · `3` falta el
ejercicio · `1` error.

## Dónde está el modelo, y dónde no

`agente_fiscal/modelo.py` es el **único** fichero de todo el sistema que
importa `anthropic`. Dos llamadas y ninguna más. Todo lo demás —troceo,
búsqueda, expansión, verificación, cálculo del estado, filtro de pertinencia—
es determinista.

## Llamada 1 · Analizar

Salida forzada a JSON por la API (`output_config.format` con `json_schema`), y
además **validada por reglas** antes de usarse: el esquema garantiza la forma,
las reglas comprueban que los valores tengan sentido. Si no cuadra, se
reintenta **una** vez con los errores concretos; a la segunda, para.

`additionalProperties: false` hace el trabajo de "no responde a la pregunta":
en el JSON no cabe nada más que los seis campos. Lo que el modelo escriba
fuera de ellos no se lee nunca.

### El ejercicio no se lo cree al modelo

La regla es de código, no de prompt:

> un año solo se acepta si aparece **escrito en la pregunta**

```
modelo dice 2026, la pregunta no lo dice -> ejercicio=None
  el analizador propuso el ejercicio 2026, pero ese año NO aparece escrito
  en la pregunta. No se supone un ejercicio: hay que indicarlo

modelo dice 2021, la pregunta lo dice    -> ejercicio=2021
```

Las instrucciones de un prompt se pueden desobedecer; esta no. Si el modelo
deduce el año en curso, el número no estará en el texto y el sistema para y lo
pregunta.

## Dos filtros antes de gastar la segunda llamada

Los añadí porque la primera versión suspendió su propia comprobación: a una
pregunta de **IRPF** el sistema respondía **CRITERIO CLARO**. Detalle de cómo
pasó, porque es instructivo — cada pieza hizo bien su trabajo:

1. BM25 siempre devuelve algo: encontró el artículo de la Ley del IVA que habla
   de «vivienda».
2. El redactor lo citó **literalmente**.
3. El verificador dio la cita por buena — y lo era: esa frase está en ese
   artículo.
4. El estado, al no ver ninguna señal, dijo CRITERIO CLARO.

Todo correcto pieza a pieza, y el conjunto mal. Es exactamente el fallo que el
proyecto quiere impedir. Dos puertas, ambas **antes** de redactar:

- **Materia**: el corpus es solo la LIVA. Si el analizador clasifica la duda
  como IRPF/IS/otro → NO ENCONTRADO sin buscar.
- **Pertinencia**: se mide por **cobertura de términos**, no por puntuación
  (BM25 no está calibrado y su valor absoluto no compara entre consultas).
  Falla si el mejor resultado cubre menos de la mitad de los términos útiles,
  o si más de la mitad de los términos no existen en toda la ley.

```
'deducción del IVA de un turismo'          -> Articulo 95 cubre 2/2   OK
'retención IRPF alquiler vivienda habitual'-> Articulo 30 cubre 1/3   INSUFICIENTE
   (además, 'irpf' y 'retención' no existen en toda la Ley del IVA)
```

Umbrales en `estado.py` como constantes a la vista (`COBERTURA_MINIMA`,
`AUSENCIA_MAXIMA`), no números escondidos en un `if`.

## Llamada 2 · Redactar

Entrada: **solo** los preceptos recuperados, con la versión que aplicaba al
ejercicio, sus avisos de fecha, sus remisiones en los dos sentidos y sus
remisiones pendientes. Nada más.

El formato de cita exigido es el que sabe leer la fase 3, y **obliga a nombrar
la norma**. No es estilo: una cita sin norma obliga al verificador a suponer
que es de la Ley 37/1992, y esa suposición era el único camino por el que
podía colar un falso VERIFICADA. Por eso la fase 4 llama al verificador con
`exigir_norma=True` y ese camino queda cerrado.

## El estado lo calcula el código

| estado | regla |
|---|---|
| **NO ENCONTRADO** | sin resultados, o materia ajena, o pertinencia insuficiente, o el verificador no acepta, o ninguna cita verificada apunta a un precepto |
| **CRITERIO DISCUTIDO** | todo verificado, pero hay al menos una señal (abajo) |
| **CRITERIO CLARO** | todo verificado y ninguna señal |

Las tres señales, todas comprobadas funcionando:

```
!! Articulo 91: el texto vigente HOY (desde 2024-12-22) NO es el que aplicaba
   en 2015; entonces regía la versión del 2015-01-01
!! Articulo 91 remite a Ley 39/2006, Ley 49/2002 ... que no está en el corpus:
   no se ha podido comprobar qué dice
!! Articulo 102: la Disposicion transitoria quinta lo menciona y la respuesta
   no la recoge; ahí suelen estar las excepciones
```

La tercera es la que cierra el círculo con la fase 2: el artículo parece
cerrado, y la excepción vive en una disposición del final de la ley.

El modelo no elige el estado ni lo influye con su tono. Se le prohíbe además
calificar el resultado ("sin duda", "es evidente").

## Bucle cerrado con el verificador

Toda salida pasa por la fase 3. Si sale RECHAZADO se reintenta **una** vez
devolviéndole los motivos exactos, cita por cita. Si vuelve a salir rechazado
→ NO ENCONTRADO y se muestran los artículos recuperados **en crudo** para que
la persona los lea. Comprobado con una cita falsa inyectada en la pregunta:

```
intento 1: 3 citas -> 2 verificadas, 1 no verificadas  =>  RECHAZADO
   - cita 3 (Articulo 105): el fragmento no aparece en Articulo 105
se reintenta UNA vez, devolviéndole los motivos exactos
intento 2: ... => RECHAZADO

NO ENCONTRADO
No se muestra ningún texto redactado: no ha superado la verificación.
Ni con aviso, ni en gris, ni a título orientativo.
```

## Traza

`datos/trazas/<AAAAMMDDTHHMMSS>/`, una por consulta:

```
pregunta.txt              analisis_N_crudo.json     borrador_N.txt
analisis.json             analisis_N_texto.json     verificacion_N.json
recuperado.json           material_N.txt            estado.json
pasos.json                resultado.json            expediente.md
```

`expediente.md` es el resumen legible: estado final, ejercicio, motor y modelo,
intentos, veredicto, y la secuencia de pasos con su hora. Lo crudo del modelo
se escribe **antes** de parsearlo, igual que en la fase 1 con el BOE.

## Comprobaciones

`python fase4.py comprobaciones` — 5 en verde:

| comprobación | resultado |
|---|---|
| pregunta sin año → PARA y lo pregunta | exit 3 |
| el año escrito en la pregunta se acepta sin `--ejercicio` | exit 0 |
| tema fuera de la LIVA (IRPF) → NO ENCONTRADO | exit 2 |
| cita falsa forzada → NO ENCONTRADO, sin mostrar texto | exit 2 |
| misma pregunta dos veces → mismo estado | CRITERIO CLARO = CRITERIO CLARO |

### Qué se ha probado y qué no — importante

Las comprobaciones corren con `--motor ensayo`: **cuatro reglas fijas, no un
modelo**. Existe porque en esta máquina no hay ni SDK instalado ni credencial,
y porque un caso de prueba cuyo resultado depende de lo que conteste un modelo
ese día no es un caso de prueba.

- **Probado**: que sin ejercicio se para; que un año inventado se rechaza; que
  la materia ajena y la baja pertinencia cortan antes de redactar; que el bucle
  con el verificador se cierra y no muestra nada sin verificar; que el estado
  sale de reglas; que la traza queda completa; que los códigos de salida son
  los que dicen.
- **No probado**: la calidad de la redacción, ni el analizador contra un modelo
  real. Nada de esta fase se ha ejecutado contra la API. En cuanto haya
  credencial, `python fase4.py consultar "..." --ejercicio 2023` es la prueba
  que falta.

Sobre la determinación del estado: es función pura de la evidencia, así que con
la misma evidencia sale el mismo estado. Con un modelo real, los términos de
búsqueda pueden variar entre ejecuciones y arrastrar la evidencia; la traza deja
ver exactamente por qué cambió si cambia.

## Fuera de alcance, no está hecho

DGT, INFORMA, TEAC, jurisprudencia, lectura de PDFs de requerimientos,
interfaz web, base de datos.

## Lo que queda abierto

- **El Reglamento del IVA.** Las 72 remisiones PENDIENTE de la fase 2 son la
  lista de la compra: en cuanto entre en el corpus se resuelven sin tocar
  código, y varias señales de CRITERIO DISCUTIDO se apagarán solas.
- **La jerarquía de fuentes** (TS > TEAC > DGT > INFORMA) sigue sin
  implementar, como se pidió. El registro lleva `norma_id` y `tipo`, que es
  donde colgaría el peso de la fuente.
- **Coste por consulta**: dos llamadas, una corta y una con el articulado
  recuperado. `TOPE_MATERIAL = 5` preceptos; subirlo encarece y diluye.
