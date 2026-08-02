# Agente de consulta fiscal — LEEME

Sistema de consulta sobre normativa del IVA para el departamento fiscal de una
gestoría. **No decide: decide la persona.** Busca la norma aplicable, la lee y
devuelve la respuesta con las citas y los enlaces para comprobarla.

## LA REGLA PERMANENTE DE LAS EXPECTATIVAS

> **Una expectativa solo se cambia con evidencia INDEPENDIENTE de la salida del
> sistema. Nunca porque el sistema devolvió otra cosa. Cada cambio, con su
> motivo escrito al lado.**

Evidencia independiente es: la rúbrica del artículo, su texto, el título oficial
de la norma. **No** lo es: «el buscador devuelve el 78 en vez del 164», «sale
rojo», «así pasa el banco».

Por qué esta regla y no otra: un banco de pruebas cuyas expectativas se ajustan
a lo que el sistema devuelve deja de ser un banco de pruebas y pasa a ser un
espejo. Nunca vuelve a estar rojo, y por eso nunca vuelve a servir para nada.

Vale para los tres sitios donde hay expectativas escritas:

| fichero | qué contiene |
|---|---|
| `casos/banco_recuperacion.txt` | consulta → artículo que debe salir |
| `casos/bateria.txt` | texto con citas → veredicto que debe dar el verificador |
| `banco.py` (bloques 2-4) | umbrales de cobertura, estabilidad y reintento |

Cuando una expectativa cambia, el motivo se escribe **en el propio fichero**,
junto al caso. Hay dos ejemplos reales:

- `casos/banco_recuperacion.txt`, «plazo de declaración recapitulativa»:
  corregido de `164-167 de la Ley` a `78-81 del Reglamento`, con la rúbrica de
  cada uno de los siete artículos como prueba.
- `casos/bateria.txt`, los dos casos `r-…`: corregidos al cargar el Reglamento,
  porque la premisa con la que se escribieron («el Reglamento no está en el
  corpus») dejó de ser cierta.

## Cómo se escribe un caso de recuperación

En este orden, y no al revés:

1. se elige un **artículo** del corpus y se lee su rúbrica;
2. se escribe la **consulta que haría un gestor** para llegar a él.

Una consulta copiada de la rúbrica se aprueba sola y no prueba nada.

## Las fases

| fase | qué hace | determinista |
|---|---|---|
| 1 | baja del BOE y trocea por precepto (`fase1.py`) | sí |
| 2 | busca y expande remisiones en los dos sentidos (`fase2.py`) | sí |
| 3 | verifica cada cita contra el corpus (`fase3.py`) | sí |
| 4 | analiza la pregunta y redacta (`fase4.py`) | **las dos únicas llamadas al modelo** |
| — | banco de pruebas (`banco.py`) | sí |

Todo lo que decide algo —el ejercicio, el estado, si una cita vale— es
determinista. El modelo solo clasifica la pregunta y redacta con lo recuperado.

## La identidad de un precepto

```
norma # cuerpo # precepto      BOE-A-1992-28740#0#articulo 8
```

El **cuerpo** existe porque un real decreto aprobatorio contiene dos
articulados: el suyo y el del reglamento que aprueba (su anexo), que vuelve a
empezar por el artículo 1. Se detecta por reinicio de numeración, no por una
lista de normas especiales.

Sin las tres partes, «artículo 8» no identifica nada: es *Concepto de entrega de
bienes* en la Ley y *Aplicación de las exenciones* en el Reglamento.

## Normas cargadas

```
Ley 37/1992 (IVA)                       243 preceptos
Real Decreto 1624/1992                    9 preceptos   (articulado del RD)
Reglamento del IVA                      135 preceptos   (anexo del RD)
```

Añadir una norma es `python3 fase1.py inspeccionar <ID>` → `ingerir` →
`verificar`. Las fases 2, 3 y 4 la recogen solas: el corpus es el directorio.

## Arranque y uso

Ver `ARRANQUE.md` para los pasos exactos. En resumen:

```
python3 -m venv .venv && .venv/bin/pip install anthropic
cp .env.ejemplo .env        # y pegar la clave detrás del '='
.venv/bin/python fase4.py credencial

python3 fase1.py verificar BOE-A-1992-28740   # auditoría del corpus
python3 fase2.py buscar "deducción IVA turismo" --ejercicio 2023
python3 fase3.py probar                       # batería de casos adversarios
python3 banco.py --motor ensayo               # banco sin gastar llamadas
.venv/bin/python fase4.py consultar "..." --ejercicio 2023
```

## La credencial

Va en un fichero **`.env`** en la raíz, con una sola línea:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Orden de búsqueda: **variable de entorno → `.env` de la raíz → error claro.**
Que el entorno mande permite probar otra clave sin editar el fichero. La
comprobación (`fase4.py credencial`) dice siempre de cuál de los dos la ha
sacado.

`.env` está en el `.gitignore`; `.env.ejemplo` sí se versiona, sin valor, para
que se vea qué hace falta. **La clave no se imprime nunca**: ni entera, ni en
una traza de error. Cuando hay que identificarla se enseñan 12 caracteres.

## Qué NO va al repositorio

`datos/` entero queda fuera del control de versiones, pero por dos motivos muy
distintos, y conviene no confundirlos.

### `datos/crudo/` y `datos/corpus/` — se regeneran

Respuestas del BOE tal cual y los JSONL troceados: ~15 MB de texto que no
aportan nada a revisar el código. **En una máquina nueva hay que volver a
ingerir las dos normas** antes de que funcione nada de la fase 2 en adelante:

```
python3 fase1.py ingerir BOE-A-1992-28740    # Ley del IVA
python3 fase1.py ingerir BOE-A-1992-28925    # Reglamento del IVA
```

Sin eso, las fases 2-4 dan `[FALLO DE CORPUS] No hay ninguna norma ingerida`.

### `datos/trazas/` — DATOS DE CLIENTE

**No se versionan porque contienen dudas reales de clientes de la gestoría.**
Cada consulta guarda la pregunta tal como se escribió, y una pregunta fiscal
identifica a menudo al cliente: un requerimiento concreto, una operación, un
importe. Eso no va a un repositorio de código, ni aunque el repositorio sea
privado: un repositorio se clona, se comparte y se sube a sitios donde no
controlas quién mira.

Dos consecuencias, y las dos son deliberadas:

- **Nada las borra.** No hay rotación por antigüedad, ni `--limpiar`, ni purga
  automática en ningún script. Comprobado: en todo el código no existe una sola
  llamada a `rmtree`, `unlink` ni `os.remove`. La clase `Traza` solo crea
  directorio y escribe. Si alguien discute una respuesta dentro de seis meses,
  el expediente sigue ahí. Borrar es siempre una decisión manual.
- **Van en la copia de seguridad, con el resto de datos de clientes.**
  `datos/trazas/` es documentación de trabajo de la gestoría, no caché. Debe
  entrar en el mismo respaldo (y bajo la misma política de conservación y de
  protección de datos) que los expedientes de los clientes. El repositorio no
  las respalda y no está pensado para hacerlo.

### `datos/banco/` — histórico, con línea base versionada

El histórico de ejecuciones del banco tampoco se versiona, pero sí su
resultado de referencia: ver abajo.

## La línea base del banco

`casos/linea_base.json` **sí se versiona**: es el último resultado bueno
conocido. Sin él, en una máquina recién clonada el banco no tendría contra qué
comparar y una regresión pasaría inadvertida.

```
1. datos/banco/  ejecución anterior   (si existe: no se versiona)
2. casos/linea_base.json              (versionada: la red de seguridad)
```

El banco dice siempre con cuál de las dos ha comparado. Solo se comparan los
bloques que se han ejecutado, para que `--bloques 1` no avise en falso de que
han "desaparecido" las pruebas de los demás.

**Actualizarla es un comando explícito y nunca ocurre solo:**

```
python3 banco.py --actualizar-linea-base
```

Antes de escribir nada enseña qué va a congelar, y si hay rojos avisa de que
dejarán de contar como regresión. Que no se actualice automáticamente al final
de cada ejecución es justamente el punto: si lo hiciera, una regresión se
convertiría en la nueva normalidad sin que nadie llegara a verla.

## Reglas del sistema que no se negocian

1. Ninguna afirmación jurídica sin fragmento literal del corpus **y** su enlace.
2. «NO ENCONTRADO» es una respuesta válida y valiosa.
3. El estado (`CRITERIO CLARO` / `CRITERIO DISCUTIDO` / `NO ENCONTRADO`) lo
   calcula el código por reglas, nunca el tono del modelo.
4. El modelo es motor, no fuente. Si una cita no está en el corpus, no existe.
5. Nada falla en silencio.
6. Ante la duda al resolver una remisión, **PENDIENTE**. Una remisión mal
   resuelta devuelve un artículo real que no es el que toca, y el verificador la
   daría por buena.
7. El ejercicio nunca se supone: si no está escrito, el sistema para y pregunta.

## Límites conocidos del buscador

El bloque 1 del banco está en **13 de 15**, y se queda ahí a propósito. Los dos
rojos están medidos, no supuestos.

### Rojo 1 · «un cliente no me paga la factura, puedo recuperar el IVA» → art. 80

No sale entre los diez primeros. Salen el 61 sexiesdecies (Reglamento), el 164,
el 116, el 163 sexvivies, el 4 y el 23 bis. **Causa: vocabulario de la calle.**
La consulta no comparte ni una palabra con el artículo que la resuelve: el 80
habla de «modificación de la base imponible» y de «créditos incobrables», y
quien pregunta dice «no me paga» y «recuperar». No hay peso que arregle eso;
es trabajo del analizador, que para eso existe.

### Rojo 2 · «qué tipo reducido se aplica» → art. 91, en el puesto 5

Puntuación de los cinco primeros, desglosada por campo:

| # | precepto | norma | total | título | cuerpo | rúbrica | \|título\| |
|---|---|---|---|---|---|---|---|
| 1 | Art. 26 bis | Reglamento | 7,357 | 4,990 | 2,040 | «Tipo impositivo reducido.» | 6 |
| 2 | Art. 26 | Reglamento | 6,977 | 6,386 | 0,235 | «Tipo impositivo reducido.» | 5 |
| 3 | D.A. segunda | Reglamento | 5,971 | 2,729 | 3,242 | «Devoluciones a comerciantes…» | 18 |
| 4 | D.T. undécima | Ley | 5,829 | — | 5,829 | «Régimen especial de bienes usados…» | 12 |
| 5 | **Art. 91** | **Ley** | **5,817** | 3,588 | 1,597 | «Tipo**s** impositivo**s** reducido**s**.» | 5 |

El título del art. 91 tiene 5 palabras, **igual que el del art. 26**: no lo
hunde la longitud. Lo hunde el **bono de forma exacta y el número gramatical**.
La consulta trae las formas en singular («tipo», «reducido»); la rúbrica del 91
está en plural, así que el bono —que pesa 4,0 en el campo título— no le entra:

```
art. 26:  =tipo -> {'titulo': 1}                  =reducido -> {'titulo': 1}
art. 91:  =tipo -> {'contexto': 1, 'cuerpo': 7}   =reducido -> {'cuerpo': 1}
```

### Las tres opciones probadas, y por qué se descartaron

| opción | banco | efecto | por qué NO |
|---|---|---|---|
| `b_titulo` 0,35 → 0,75 | 14/15 | art. 91: 5º → 3º; mueve 1 consulta | **Acierta por casualidad.** Subir `b` *aumenta* la ventaja de los títulos cortos; el 91 sube porque el suyo también es corto, y quienes caen son la D.A. segunda (18 palabras) y la D.T. undécima (12). No corrige el sesgo que lo hunde: lo acentúa y esta vez favorece al que queríamos. |
| `PESO_EXACTO` 0,45 → 0,25 | 14/15 | art. 91: 5º → 3º; mueve 3 consultas | Debilita globalmente una señal que funciona —separar la coincidencia real de la que fabrica el lematizador— para arreglar un caso. |
| **Fusión singular/plural en la forma exacta** | 13/15 | art. 91: 5º → **2º**, pero art. 89: 3º → 4º (verde→rojo); corte 62 → 64 preceptos | **Es la correcta conceptualmente** y la única que ataca la causa. Se descarta *por ahora*, no por mala: ver abajo. |

**La opción 3, con sus números, para retomarla.** Se implementó y se midió: el
bono de forma exacta casa también cuando la única diferencia es el número
gramatical. La clave se decide con el vocabulario del corpus, porque la lengua
sola no puede («bases» sale de «base» y «meses» de «mes», y tienen la misma
forma). Resultado sobre el corpus:

- **1.039 pares fusionados** de 2.019 palabras acabadas en -s (763 por `-s`,
  273 por `-es`, 3 por `-ces→z`);
- 978 plurales sin singular en el corpus: no se tocan;
- **2 ambiguos** (`artes → art|arte`, `ordenes → orden|ordene`): no se fusionan,
  y sin ninguna excepción escrita a mano;
- **0 fusiones falsas**, comprobado exigiendo que singular y plural compartan
  raíz. Las 44 que discrepan (`actas/acta`, `regimenes/regimen`,
  `examenes/examen`) son pares correctos: quien falla ahí es el lematizador.

Por qué se cae el art. 89 con ella: la consulta trae «factura», y el art. 63
(«Libro registro de **facturas** expedidas») pasa a cobrar el bono en su título
y adelanta al 89. La rúbrica del 89 es «cuotas impositivas **repercutidas**» y
la consulta dice «repercutido»: ahí la diferencia es de **género**, y ensanchar
a género es exactamente lo que no se hace —por ese camino «importe» e
«importación» vuelven a ser la misma palabra y el bono deja de significar nada.

**Por qué no se elige la que puntúa mejor:** quince casos no distinguen entre
13, 13 y 14. Escoger el camino que mejor sale en un conjunto tan pequeño es
ajustar al banco, no mejorar el buscador. La opción 3 se retoma cuando el banco
sea más grande.

De la opción 3 se conserva `texto.palabras_exactas()`: quita una duplicación
entre el indexado y la consulta y no cambia ningún resultado.

### Antes de volver a tocar pesos: el bloque 5

El bloque 1 **puentea el analizador a propósito**, así que sus rojos dicen «el
buscador solo no llega», no «el sistema falla». El bloque 5 mide lo segundo:
repite los casos en rojo dejando que el analizador proponga los términos.

```
python banco.py --con-modelo --bloques 5     # 2-4 llamadas, no redacta
```

**Está escrito y sin ejecutar: no hay crédito de API.** La hipótesis a comprobar
es que para «qué tipo reducido se aplica» el analizador proponga «tipos
impositivos reducidos» en plural y el art. 91 salga el primero. Si es así, ese
rojo no existe en el sistema real y las tres opciones de arriba estaban
afinando pesos para un fallo que el analizador ya resuelve. El bloque detecta
los rojos él solo, así que no hay lista que se quede vieja.

## El banco de recuperación tiene que crecer

Las quince consultas actuales las escribimos nosotros, y ese es su límite: no
pueden decidir un empate entre 13 y 14, ni justificar tocar un peso. **El banco
debe crecer con los casos reales que mande el departamento fiscal** —las dudas
que llegan de verdad, con el artículo que las resuelve—, que son el único
conjunto con autoridad para estas decisiones. Cada caso nuevo va en
`casos/banco_recuperacion.txt` con el formato de cuatro campos que se explica
más arriba.

## Corte de material (qué se manda a redactar)

La búsqueda devuelve hasta 5 preceptos (`TOPE_MATERIAL`), pero **el tope es un
techo, no una cuota**: se manda solo lo que viene al caso. El corte lo hace
`estado.seleccionar_material` con tres reglas:

1. el primero entra siempre;
2. los demás entran si su cobertura de términos llega al **70 %**
   (`estado.UMBRAL_MATERIAL`) de la del primero;
3. y entran igual, con la cobertura que sea, **si un precepto ya elegido remite
   a ellos**. Esa es la nota al pie, y es justo lo que no se ve leyendo el
   artículo solo.

Se corta por pertinencia y **no por puesto**: en «qué tipo reducido se aplica»
el artículo 91 sale el quinto y es el que contesta —su cobertura es 1,00, así
que sobrevive a cualquier umbral—. Un corte por número lo habría matado.

Cada consulta deja en su traza `seleccion.json` y una tabla en `expediente.md`
con qué entró, qué se descartó, con qué cobertura y contra qué umbral. Si una
respuesta falla por falta de material, se ve ahí; no hay que deducirlo.

### PENDIENTE (necesita crédito de API, no ejecutado)

Queda por comprobar, con **dos consultas reales**, que el veredicto del
verificador no cambia al mandar menos material. Todo lo medido hasta ahora es
local: cuántos preceptos y cuántos tokens, no la calidad de la respuesta.
Cuando haya crédito:

```
python fase4.py consultar "deduccion del IVA de un turismo. FRAGMENTO SOSPECHOSO: \
  el porcentaje de deduccion aplicable a los turismos sera siempre del 100 por cien" \
  --ejercicio 2023
python fase4.py consultar "que tipo reducido se aplica" --ejercicio 2023
```

La primera debe seguir dando `CRITERIO CLARO` con sus citas verificadas (con
todo el material daba 6/6); la segunda es la que tiene el artículo 91 en el
puesto 5 y sirve para confirmar que sigue llegando al redactor.

## Documentación por fases

`FASE1.md` … `FASE6.md` — qué se construyó, qué se rompió y por qué se decidió
cada cosa. `ARRANQUE.md` — instalación y credencial.
