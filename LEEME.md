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

## CRITERIOS REVOCADOS

Un umbral que se mueve sin dejar rastro es como se lavan los resultados: se baja
el listón, se declara verde y nadie puede reconstruir después que el listón
estaba más alto. Por eso, cuando un criterio se revoca, **se queda escrito aquí
con quién lo revocó y con qué argumento**, no se borra del sitio donde estaba.

### 2 de agosto de 2026 · el mínimo de 13/15 del banco, bloque 1

**Qué decía el criterio.** Al ingerir la Ley General Tributaria (fase 8) se
fijó por adelantado: si el bloque 1 del banco baja de 13/15 sobre las quince
consultas originales, la LGT no se queda.

**Qué pasó.** Bajó a 12/15. Una sola consulta cruzó el umbral: «he repercutido
IVA de mas en una factura, como lo corrijo», donde el artículo 89 LIVA pasó del
puesto 3 al 5.

**Quién lo revocó.** Emili, el 2 de agosto de 2026, tras ver la medición.

**Con qué argumento.** Dos razones, y las dos por escrito:

1. El criterio era **inconsistente con lo ya decidido** en el caso del artículo
   91 (ver «Límites conocidos del buscador» más abajo): allí se aceptó
   convivir con un rojo de puesto antes que tocar los pesos del buscador.
   Aplicar 13/15 aquí y no allí es medir con dos varas.
2. Quince casos **no distinguen 12 de 13**. Un banco de ese tamaño no tiene
   resolución para que un caso decida la suerte de una norma entera.

**Con qué evidencia se decidió, y por qué es independiente del banco.** La
prueba a favor de la LGT no sale del banco, que es justo lo que estaba en
discusión, sino de medidas que el banco no toca:

- **+506 remisiones resueltas** (966 → 1472).
- **20 remisiones IVA→LGT**, con **cero mal resueltas**, verificadas contra el
  texto; 14 de ellas en el caso ambiguo de verdad (el número de artículo existe
  también en la norma de origen).
- Una consulta de procedimiento que antes no tenía respuesta pasa a tenerla:
  «plazo para contestar un requerimiento» va de `NO ENCONTRADO` a
  `CRITERIO DISCUTIDO`.

**Qué NO se hizo.** No se tocó ninguna expectativa del banco para que saliera
verde. Las tres consultas en rojo siguen en rojo y siguen contadas como rojo.
La regla permanente de las expectativas queda intacta: lo que se revocó fue un
umbral de decisión sobre una norma, no la expectativa de ningún caso.

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
Ley 37/1992 (IVA)                       243 preceptos   norma del impuesto
Real Decreto 1624/1992                    9 preceptos   (articulado del RD)
Reglamento del IVA                      135 preceptos   (anexo del RD)
Ley 58/2003 (General Tributaria)        335 preceptos   norma general
                                        ---
                                        722 preceptos
```

Añadir una norma es `python3 fase1.py inspeccionar <ID>` → `ingerir` →
`verificar`. Las fases 2, 3 y 4 la recogen solas: el corpus es el directorio.
La LGT (`BOE-A-2003-23186`) entró así, **sin tocar una línea de código**: es la
tercera norma seguida, y con tres ya no es casualidad.

### El papel de cada norma (fase 8)

No todas las normas del corpus juegan el mismo papel, y desde que está la LGT
hay que distinguirlo. La LGT habla de plazos, notificaciones y sanciones **en
abstracto**, así que su vocabulario encaja con casi cualquier consulta: sin
distinguir papeles, el artículo 55 LGT («tipo de gravamen») compite de tú a tú
con el 91 LIVA en una pregunta sobre tipos de IVA, y le quita sitio.

```
NORMA DEL IMPUESTO   alguno de sus cuerpos trata la materia propia del corpus
NORMA GENERAL        ninguno la trata: está para dar apoyo, no para contestar
                     sobre el impuesto
```

El papel **no se declara en una lista escrita a mano**: se deduce de la materia
del título oficial, comparándola con la que más cuerpos comparten (aquí,
«Impuesto sobre el Valor Añadido»). Se mira **por norma, no por cuerpo**, y por
eso el Real Decreto 1624/1992 sale bien clasificado sin excepciones: su cuerpo 0
no declara materia, pero el Reglamento que aprueba sí. Ingerir mañana el
Reglamento General de Recaudación lo clasificaría solo.

La regla que se aplica en el corte, en una línea:

> Una norma **general** solo aporta material cuando la consulta es suya —su
> precepto es el mejor resultado— o cuando un precepto ya elegido la llama por
> remisión.

Medido sobre las 19 consultas del banco: consultas con material de la LGT,
**6 → 4**. Las cuatro que quedan son las cuatro de procedimiento, que deben
tenerlo. En consultas que no son de procedimiento, la contaminación pasa de
**2 a 0**. Los puestos no se mueven: la regla actúa después del buscador.

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

### La regla 6, en la práctica: el precio que se paga por cumplirla

Al cargar la LGT, **siete remisiones del RIVA a la LIVA dejaron de resolverse**.
No es un fallo: frases genéricas como «la Ley de este Impuesto» o «la Ley
reguladora del tributo» encajaban con una sola Ley mientras solo había una
cargada. Con dos, encajan con dos, y el resolutor **se niega a adivinar**.

Se pierden siete enlaces. A cambio, **cero remisiones mal resueltas**. Es la
regla 6 funcionando, no rompiéndose, y conviene tenerlo escrito porque en la
tabla de números parece una regresión.

### El extractor de disposiciones exige un ordinal de verdad (fase 8)

El patrón de remisiones capturaba lo que hubiera detrás de «disposición
adicional» y lo tomaba por ordinal. En un texto corriente («las disposiciones
adicionales **se** aplicarán…», «la disposición final **y** el anexo…») eso
fabricaba remisiones a preceptos que no existen en ninguna norma.

Ahora lo que sigue tiene que ser un ordinal: palabra del vocabulario
(`primera`, `vigesimosegunda`, `unica`), ordinal partido en dos
(`vigésimo segunda`) o número. Efecto medido en las tres normas:

| | antes | después |
|---|---|---|
| remisiones detectadas | 1718 | 1704 |
| no encontradas | 43 | **29** |
| **resueltas** | 1472 | **1472** |

**14 remisiones falsas desaparecen** —13 en la LGT y 1 en el RD/RIVA— y las
resueltas no se mueven ni una: no se ha perdido ninguna remisión legítima. Era
ruido preexistente que la LGT solo hizo visible, porque usa mucho esa
construcción. Las 2 que quedan en el RD/RIVA son referencias reales a
disposiciones que no existen en el cuerpo de destino, no falsos positivos.

## Límites conocidos del buscador

El bloque 1 del banco está en **16 de 19**, y se queda ahí a propósito. Los tres
rojos están medidos, no supuestos.

Desglose, porque el total solo no dice nada: **12 de las 15 originales** de IVA
y **4 de 4** de las de procedimiento que añadió la fase 8. Las 15 originales
estaban en 13 antes de cargar la LGT; la tercera en rojo es el artículo 89, y
por qué cayó está explicado en el «Rojo 3» de aquí abajo.

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

### Rojo 3 · «he repercutido IVA de mas…» → art. 89, del puesto 3 al 5

Apareció al cargar la LGT (fase 8). **No es contaminación de la LGT**: se
midió antes de tocar nada, y en esa consulta **ningún precepto de la LGT entra
en el top 6**. El reordenamiento ocurre entre preceptos del IVA.

Lo que pasó es que crecer el corpus cambia las **estadísticas globales** de
BM25, que son compartidas por todos los documentos:

| | 2 normas | 3 normas | |
|---|---|---|---|
| longitud media del cuerpo | 185,78 | 164,11 | **−11,7 %** |
| idf de `factur` | 1,88 | 2,17 | +15,8 % |
| idf de `iva` | 4,71 | 5,33 | +13,2 % |
| idf de `repercut` | 2,76 | 3,04 | +10,1 % |

Los artículos de la LGT son más cortos, así que la longitud media baja y la
normalización **penaliza más a los documentos largos**. El art. 89 es largo y
su fuerza está en `repercut` (10 veces en el cuerpo), justo el término cuyo idf
menos sube. Sus rivales son más cortos y viven de `factur` e `iva`, que son los
que más suben. Puntuaciones: el 89 pasa de 3,927 a 4,227 —**sube**—, pero el
142 sube de 3,865 a 4,338 y el 63 de 3,884 a 4,283, y lo adelantan los dos.

**Es un reordenamiento legítimo, no un fallo**, y no lo arregla la regla de
papel de las normas: esa regla decide qué se manda al redactor, no en qué orden
busca BM25. Se deja en rojo, medido y explicado, igual que los otros dos. Nótese
que este caso ya se sabía frágil: la opción 3 de arriba también lo movía de 3º
a 4º, por otra causa distinta.

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

## PENDIENTES QUE NECESITAN CRÉDITO DE API

Los tres, juntos, para que no se pierda ninguno. Ninguno está ejecutado.

**1 · El veredicto del verificador con menos material.** El de aquí arriba: dos
consultas reales para confirmar que recortar el material no cambia el veredicto.

**2 · La calidad de la redacción con el modelo real.** Todo lo que se ha medido
del banco es el andamiaje determinista (bloque 1) con el motor de ensayo. La
redacción y el análisis con el modelo real solo se prueban con crédito.

**3 · La fuga de la puerta de materia (fase 8, anotado y NO ejecutado).**
La consulta «cómo tributa en el IRPF la venta de acciones» devuelve
`CRITERIO CLARO` cuando debería ser `NO ENCONTRADO`. Medido antes y después de
ingerir la LGT: **la fuga ya existía con dos normas**, la LGT no la abre.

Es, casi con seguridad, un **artefacto del motor de ensayo**: `MotorEnsayo`
clasifica `impuesto="IVA"` solo si la palabra «iva» aparece literalmente en la
pregunta, y en cualquier otro caso pone `"desconocido"` — que la puerta de la
fase 4 deja pasar, porque `IMPUESTOS_EN_CORPUS = ("IVA", "desconocido")`. Con
el analizador real la pregunta debería clasificarse como IRPF y parar ahí.

Lo que la LGT sí cambió es **qué** se filtra: antes citaba el artículo 13 LIVA,
ahora los artículos 180 y 183 LGT, que son de sanciones. La otra consulta de
IRPF de control («retención del IRPF de un alquiler») sigue dando
`NO ENCONTRADO` correctamente, ahí la corta el filtro de pertinencia.

Cuando haya crédito:

```
python fase4.py consultar "como tributa en el IRPF la venta de acciones" --ejercicio 2023
```

Debe dar `NO ENCONTRADO`. Si diera `CRITERIO CLARO`, la fuga es real y no del
motor de ensayo, y entonces hay que endurecer la puerta de materia: hoy la
única defensa cuando el analizador dice `"desconocido"` es el filtro de
pertinencia, y este caso demuestra que no siempre basta.

## Documentación por fases

`FASE1.md` … `FASE6.md` — qué se construyó, qué se rompió y por qué se decidió
cada cosa. `ARRANQUE.md` — instalación y credencial.
