# Agente de consulta fiscal — LEEME

Sistema de consulta sobre normativa del IVA para el departamento fiscal de una
gestoría. **No decide: decide la persona.** Busca la norma aplicable, la lee y
devuelve la respuesta con las citas y los enlaces para comprobarla.

## ⚠️ HOY EN PRODUCCIÓN HAY DOS ESTADOS, NO TRES

> **Con la DGT y el TEAC apagados —que es como está hoy— `CRITERIO DISCUTIDO`
> NO PUEDE SALIR NUNCA.** Solo salen `CRITERIO CLARO` y `NO ENCONTRADO`.

No es un fallo, es la consecuencia de separar el estado de la cobertura (fase
12): el estado solo se mueve por **desacuerdo de fondo entre textos**, y el
desacuerdo de fondo solo lo pueden producir las fuentes de criterio. Sin ellas
no hay con qué detectar que dos textos se contradicen — la ley y su reglamento
casi nunca se contradicen por escrito, y de hecho antes de la fase 9B el
DISCUTIDO no había saltado nunca por esa vía.

**Qué hay que decidir, y no es programar:**

- `GUIA.md` describe tres estados y explica uno que hoy no puede pasar. El
  texto de sustitución está escrito y **sin activar** en `GUIA_ESTADOS_NUEVO.md`.
- Las opciones son dos: **encender las fuentes** (y entonces los tres estados
  vuelven a tener sentido y se cambian los textos a la vez), o **quitar
  DISCUTIDO de la guía** mientras sigan apagadas. Lo que no se puede dejar es
  la hoja de la mesa describiendo un estado que la herramienta no produce.
- Mientras tanto no hay riesgo de decir algo falso en pantalla: la frase de
  DISCUTIDO no llega a mostrarse porque el estado no se alcanza.

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

### 5 de agosto de 2026 · «la fuente caída baja el estado»

**Qué decía el criterio.** De la fase 9B: si la fuente de criterio no respondía,
la respuesta bajaba de CRITERIO CLARO a CRITERIO DISCUTIDO, para no contestar
como si tuviéramos criterio cuando no sabemos si lo tenemos.

**Quién lo revoca y con qué argumento.** Emili, en el encargo de separar el
estado de la cobertura. El argumento: **son dos ejes distintos**. Que PETETE no
responda no enfrenta dos textos entre sí; dice que hay un hueco. Meterlo en el
mismo cajón que el desacuerdo de fondo era parte de por qué DISCUTIDO salía en
17 de cada 19 consultas *antes incluso* de encender la DGT y el TEAC, y una
etiqueta que sale casi siempre deja de informar.

**Qué NO cambia, y es lo que importa.** La fuente caída **se sigue diciendo,
igual de clara**, en el bloque «lo que no se ha podido mirar», y se sigue
asumiendo caída si nunca se ha comprobado. No se disimula: cambia de bloque, no
de visibilidad. Lo que se revoca es el automatismo de bajar el estado, no el
deber de avisar.

**Qué habría que ver para volver atrás.** Que alguien lea el bloque de cobertura
como decoración y firme sin mirarlo. Si eso pasa, el problema no se arregla
devolviendo el aviso al estado —volvería la saturación—, sino haciendo que el
bloque pese más en pantalla.

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

## EL DESDOBLAMIENTO DE LA DGT: texto y enlace no vienen del mismo sitio

**Esto hay que entenderlo ANTES de integrar la DGT (fase 9B). Si no queda
claro, el verificador rechazará citas buenas — ya nos pasó con las viñetas.**

Para la ley, el texto y el enlace vienen del mismo sitio: se descarga el BOE, se
trocea, y el enlace apunta al mismo artículo del que salió el texto. Comprobar
una cita es comprobar las dos cosas a la vez.

**Con la DGT no.** La fuente es una aplicación con endpoints internos, y la URL
que sirve a una persona no devuelve el texto al descargarla. Se desdobla:

| | de dónde sale | cómo se comprueba |
|---|---|---|
| **el TEXTO** | del documento **cacheado** en `datos/dgt/` | fragmento literal contra la copia local, igual que la ley |
| **el ENLACE** | `…/consultas/?num_consulta=V1601-22` | que apunte a **la consulta correcta**, y nada más |

**Del enlace NO se comprueba que devuelva el texto al descargarlo.** No lo
devuelve, y no es un fallo: esa URL es un armazón que carga el contenido por
JavaScript. Un verificador que exija «descarga el enlace y busca el fragmento»
daría por falsas todas las citas de la DGT, que serían correctas.

La regla del verificador **no cambia** —fragmento literal más URL que resuelve,
o no existe—; lo que cambia es contra qué se resuelve cada mitad. Una consulta
cacheada es corpus local y se verifica exactamente igual que la Ley del IVA.

Y una tercera cosa, que es de la 9B pero se anota aquí porque nace del mismo
desdoblamiento: **una cita de la DGT nunca puede parecer una cita de la ley.**
En la respuesta tiene que verse que es **criterio**, no **norma**.

## PENDIENTE de la fase 9 (no necesita crédito, no ejecutado)

**El texto de `CRITERIO CLARO` caducará el día que entre la DGT.** Hoy dice, en
la ventana y en `GUIA.md`, que la DGT y los tribunales no están en la
herramienta. En cuanto las consultas vinculantes entren en el corpus, esa frase
pasa a ser falsa y hay que reescribirla **en los dos sitios a la vez**: si se
cambia solo uno, la hoja impresa de la mesa y la pantalla dirán cosas distintas,
que es peor que no cambiar nada.

El reconocimiento de la fuente está hecho y **no se ha ingerido nada**: ver
`FASE9.md`. Resumen de por qué no se siguió adelante: la URL por número no
devuelve datos —es una aplicación con carga por JavaScript— y el buscador
responde a 20 segundos o corta con 504. Ahí está el mapa de campos, los
endpoints reales y el problema de la cadena de certificados.

## Documentación por fases

`FASE1.md` … `FASE6.md` — qué se construyó, qué se rompió y por qué se decidió
cada cosa. `ARRANQUE.md` — instalación y credencial.

## FASE 9B · El criterio de la DGT, integrado y APAGADO

**Está construido y está apagado.** Con la DGT apagada el sistema se comporta
exactamente como antes: batería 29/29, banco 16/19 y comprobaciones de fase 4
5/5, idénticas. El interruptor:

```
AGENTE_DGT=1 python fase4.py consultar "..." --ejercicio 2023
```

**Por qué sigue apagada:** el extractor de PETETE no ha visto todavía un
documento real (ver `FASE9.md`). Mientras eso no ocurra, la DGT no está de
verdad, y encenderla sería prometer criterio que no tenemos.

### La cita de criterio no puede parecer ley

```
ley       «fragmento» (artículo 95 de la Ley 37/1992, https://www.boe.es/…)
criterio  «fragmento» [Consulta DGT V1601-22, de 01/07/2022 — https://petete…]
```

Paréntesis contra corchetes, y el rótulo «Consulta DGT» delante. En la
respuesta, la ley va primero y el criterio después, en párrafo aparte: nunca
mezclados como si pesaran igual. Al redactor se le dice explícitamente que una
consulta **no fundamenta por sí sola**.

### De qué se fía este módulo

`agente_fiscal/dgt.py` **no mira ni una línea de HTML**. Se apoya solo en la
forma del registro cacheado, que es un JSON que escribimos nosotros. Si mañana
cambia el troceo, cambia `petete.py` y esto sigue igual.

### Lo que el código NO puede calcular, y no finge calcular

El encargo decía: «si el criterio de la DGT apunta en otra dirección que la
norma → DISCUTIDO». **Eso es semántica, y aquí no hay quien la lea.** No se ha
implementado un juicio de fondo disfrazado de regla. Lo que se mide son dos
señales **estructurales**, y cada una dice solo lo que sabe:

1. **varias consultas sobre el mismo artículo y de años distintos** → el
   criterio ha podido evolucionar. La más reciente manda y las anteriores se
   citan como antecedente.
2. **una consulta cuyo campo `normativa` no toca ninguno de los preceptos que
   sostienen la respuesta** → el criterio va de otra cosa.

Ninguna afirma que haya contradicción de fondo. Afirman que **no se puede
afirmar que no la haya**, que es lo que corresponde a un sistema que no lee, y
por eso producen DISCUTIDO y no NO ENCONTRADO.

### La fuente caída se dice, pero ya NO baja el estado

**REVOCADO el 5 de agosto de 2026** — ver «Criterios revocados». Si la fuente de
criterio no respondía, se dice en el bloque de **cobertura**, igual de claro, y
el estado no se mueve. Y si nunca se ha comprobado, se sigue asumiendo
**caída**: dar por viva una fuente sin mirarla sería justo el fallo que esta
fase evita.

### El texto de CRITERIO CLARO, en dos versiones

`interfaz.py` tiene ya escritas `CLARO_SIN_DGT` (la de hoy, activa) y
`CLARO_CON_DGT` (la nueva, inactiva). Cambian solas con el interruptor. **Al
encender la DGT hay que actualizar `GUIA.md` a la vez**, que sigue diciendo que
la DGT no está: si se cambia solo uno, la hoja de la mesa y la pantalla dirán
cosas distintas.

## FASE 11 · La doctrina del TEAC, y LAS DOS SEÑALES

**Construida y APAGADA**, con interruptor propio `AGENTE_TEAC=1`, distinto del
de la DGT. Con los dos apagados el sistema se comporta exactamente igual que
antes: batería 34/34, banco 16/19, fase 4 5/5, ocho suites en verde.

### La jerarquía

```
ley y reglamento   >   TEAC   >   DGT
```

No es preferencia de estilo. El criterio del TEAC **vincula a toda la
Administración tributaria** (art. 239.8 LGT); una consulta de la DGT vincula
**frente a quien consultó**. En la respuesta: primero la norma, después el TEAC,
después la DGT, cada bloque etiquetado. El orden del material que ve el redactor
**es** la jerarquía: lo que se lee primero pesa primero.

Tres fuentes, tres formas de cita, distinguibles sin leer:

```
ley    (artículo 95 de la Ley 37/1992, https://www.boe.es/…)
TEAC   {Criterio TEAC 00/06614/2024/00/00, de 21/05/2026, TEAC — https://…}
DGT    [Consulta DGT V1601-22, de 01/07/2022 — https://petete…]
```

### LAS DOS SEÑALES DE DISCUTIDO NO PESAN IGUAL

Esto es lo que hay que tener claro dentro de tres meses, porque si no se
tratarán igual y una de las dos miente.

**SEÑAL FUERTE — estructural.** El TEAC cita **por número** una consulta de la
DGT que esta respuesta también está citando. No hay que adivinar nada: el propio
tribunal ha puesto las dos cosas en la misma frase, así que sabemos que se ha
pronunciado sobre *ese* criterio y no sobre uno parecido. Se da en **4 de cada 9**
criterios reales medidos. El aviso es afirmativo: *«el TEAC se ha pronunciado
sobre V2092-15, que es criterio que esta respuesta cita»*.

**SEÑAL DÉBIL — coincidencia de artículos.** Hay doctrina del TEAC sobre el
mismo artículo. Es una **aproximación**: que dos textos hablen del artículo 80 no
significa que hablen del mismo supuesto. El aviso lo dice en condicional:
*«Coincide el artículo, PERO no se ha comprobado que trate del mismo supuesto:
compruébalo tú»*.

**Cuando existe la fuerte, manda ella** y la débil no se repite para el mismo
criterio: decir dos veces lo mismo con distinta seguridad confunde. Las fuertes
salen primero en la lista de señales.

**Línea doctrinal.** Una consulta citada por **varios** criterios pesa más que una
mencionada de pasada, y se dice cuántos la citan. Medido: `0745-03`, `1010-03` y
`V2092-15` las citan dos criterios distintos (00/03399/2023 y 00/05524/2024).

### La búsqueda encaja sola

Al TEAC se le pregunta **por precepto**, no por palabras: el buscador acaba de
decir qué artículos sostienen la respuesta. Nada de inventar términos como hubo
que hacer con la DGT. Y los criterios se ordenan poniendo delante los de
**unificación de criterio**, que es la jerarquía aplicada ya al elegir.

### Qué norma de DYCTEA es cuál de las nuestras: POR CÓDIGO

DYCTEA nombra al Reglamento del IVA como *«RD 1624/1992 Reglamento Impuesto
sobre el Valor Añadido IVA»*. Ese nombre menciona **dos** cosas que en nuestro
corpus son dos cuerpos distintos —el Real Decreto y el Reglamento que aprueba—,
así que el resolutor no podía decidir y devolvía vacío. Hacía bien: ante la
duda, nada. Pero la consecuencia era que **toda la doctrina del TEAC sobre el
Reglamento se perdía en silencio**.

La salida no fue adivinar mejor, fue dejar de adivinar. DYCTEA identifica cada
norma con un **código estable**, y el código no admite dos lecturas:

```
02:07:01:00:00  ->  Ley 37/1992
02:07:02:00:00  ->  Reglamento del Impuesto sobre el Valor Añadido
01:02:01:00:00  ->  Ley 58/2003
```

El mapa está en `agente_fiscal/teac.py`, a la vista. **Los códigos se leen del
catálogo que baja `teac.py`, no de memoria**: la primera versión de este mapa
llevaba `01:01:01:00:00` para la LGT y el real es `01:02:01:00:00`.

Tres reglas que no cambian:

- Se mapea a una **designación** (`"Ley 37/1992"`), no a la clave del cuerpo:
  la clave depende de cómo esté montado el corpus hoy y la designación la
  resuelve `normas.resolver`, que es quien sabe de eso.
- Un **código no mapeado es norma externa**, y no se intenta adivinar por el
  nombre. Mejor decir «no la tengo» que acertar por casualidad.
- El **nombre sigue como respaldo** para cuando no haya código, con su regla de
  siempre: si es ambiguo, vacío.

La página del criterio no trae el código, solo el nombre; el código se recupera
del catálogo de DYCTEA por coincidencia **exacta** de nombre. No es interpretar
un nombre: es buscarlo en la tabla de la propia fuente.

### El texto de CRITERIO CLARO

`interfaz.py` tiene ya escrita `CLARO_CON_TRES_FUENTES`, **inactiva**. Se
enciende con `AGENTE_DGT_TEXTOS` **a la vez que `GUIA.md`**, nunca sola.

---

# FASE 12 · DOS EJES SEPARADOS, Y LA LEY DE VUELTA AL 83%

Sale de medir las tres fuentes juntas. Los dos números que lo dispararon:
**la ley era el 17% del material** y **DISCUTIDO salía 19 de 19**.

## 1 · El estado y la cobertura son dos ejes, no uno

DISCUTIDO salía **17 de 19 antes de encender la DGT y el TEAC**. La causa no era
el criterio: eran los avisos de vigencia y las remisiones a normas que no
tenemos. Eso no es criterio discutido, es **cobertura incompleta de nuestro
corpus**, y estaba en el mismo cajón.

| | **ESTADO** (`Dictamen.senales`) | **COBERTURA** (`Dictamen.cobertura`) |
|---|---|---|
| Contesta a | ¿los textos se contradicen? | ¿qué no he podido mirar? |
| Mueve el estado | **sí**, a DISCUTIDO | **no**, nunca |
| Qué entra | consultas de la DGT de años distintos sobre el mismo precepto; el TEAC pronunciándose sobre una consulta que citamos | vigencia fuera del ejercicio; remisiones fuera del corpus; disposición del corpus no recogida; fuente caída; doctrina del TEAC sobre el mismo artículo sin comprobar |
| Se enseña | bloque «DESACUERDO ENTRE LOS TEXTOS», solo si lo hay | bloque «LO QUE NO SE HA PODIDO MIRAR», **siempre**, aunque sea para decir que no falta nada |

**Que un aviso no mueva el estado no significa que importe menos**: significa
que responde a otra pregunta. Juntarlas hacía que la primera no se pudiera
contestar.

**Medido sobre las 19 del banco, suponiendo respuesta verificada:**

| | antes | después |
|---|---|---|
| con las capas de criterio | 19 DISCUTIDO · 0 CLARO | **5 DISCUTIDO · 14 CLARO** |
| sin las capas | 17 DISCUTIDO · 2 CLARO | **0 DISCUTIDO · 19 CLARO** |

**Consecuencia que hay que tener presente:** con la DGT y el TEAC **apagados**,
el desacuerdo de fondo solo puede venir de ellos, así que **DISCUTIDO no puede
salir hoy**. En producción hay dos estados, no tres, hasta que se enciendan las
fuentes. Es correcto —sin fuentes de criterio no se puede detectar desacuerdo—
pero no es obvio, y por eso está escrito aquí.

## 2 · El criterio no puede ocupar más que la ley

Se mandaban **contestaciones enteras** de hasta tres consultas, de 20 a 78 KB
cada una. Dos reglas, las dos en `redactor.py`:

- **Selección estructural**, nunca resumen: de cada consulta van solo los
  párrafos que mencionan los artículos en juego **y su entorno inmediato**
  (`ENTORNO = 1`). Lo que se manda sigue siendo **literal y verificable**; hay
  una prueba que busca cada fragmento, letra por letra y con la normalización
  del verificador, dentro del documento cacheado.
- **Tope relativo**: el bloque de criterio (TEAC + DGT) **no puede pasar del
  tamaño del bloque de ley**. Relativo y no fijo, porque lo que hay que
  garantizar es la proporción.

Reglas de detalle que costaron una vuelta cada una:

- **Si al recortar una consulta se queda sin nada pertinente, no se manda.**
  Mejor dos consultas útiles que tres a medias.
- **Se llena por párrafos, no por fragmentos enteros.** Una consulta en la que
  *todos* los párrafos hablan del artículo produce un fragmento único enorme, y
  con el tope aplicado al fragmento entero esa consulta —justo la más
  pertinente que existe— se caía del todo. Un prefijo de párrafos seguidos
  sigue siendo texto contiguo y literal.
- **Se mide el bloque real, con el peor caso de la cuenta de omitidos.** Medir
  uno y mandar otro es como se sale del tope sin enterarse.
- **Los huecos se marcan.** Cada trozo va entre `[FRAGMENTO n DE ...]` y el
  material prohíbe expresamente citar de un fragmento a otro: entre uno y otro
  falta texto y esa cita no existe en el documento. (El verificador lo pararía
  igual —compara contra el documento **entero**— pero avisar ahorra un intento.)
- **La norma, no solo el número.** Un párrafo que dice «el artículo 80 de la Ley
  35/2006» **no** se selecciona. Un párrafo que nombra una norma que no tenemos
  tampoco: que no la tengamos no la hace nuestra. Un «el citado artículo 80» sin
  norma al lado **sí** cuenta, y es deliberado: aquí un falso positivo se paga
  en caracteres y un falso negativo en una respuesta peor. Y esto **no produce
  ninguna señal**, solo elige qué se manda.

**Medido sobre las 19, ley / criterio en caracteres:**

| | ley | criterio | % ley |
|---|---|---|---|
| antes | 331.009 | 1.729.552 | **16%** |
| después | 331.009 | 67.244 | **83%** |

El criterio baja un **96%**. El peor caso pasa del **6%** de ley al **52%**, y
**no queda ninguna consulta por debajo de la mitad**. Todo lo recortado se
cuenta en `Recorte` y se escribe en `recorte_criterio.json` dentro de la traza.

## 3 · Los avisos se agrupan por artículo, no por criterio

Sobre el artículo 80 salían **seis avisos idénticos** cambiando solo el número
de criterio. Quien lee el primero se salta los otros cinco, así que seis avisos
informaban **menos** que uno. Ahora es **un aviso por artículo** con la lista
dentro, los de **unificación de criterio primero** (vinculan a toda la
Administración) y `TOPE_NOMBRADOS = 4` antes de resumir en «y N más».

## Lo que queda cojo y hay que mirar

- **En 5 de las 19 no se manda criterio ninguno**, porque ninguna de las
  consultas que trae el buscador local habla de los artículos en juego. No es un
  fallo del recorte: es el buscador local (`CacheDGT.buscar`, cobertura de
  palabras) trayendo lo que hay en una caché de 130 consultas.
- **El presupuesto se lo come el primero.** En el art. 80, `V0160-23` se lleva
  todo el hueco y `V0053-13` y `V0041-07` se quedan en cero, aunque la señal de
  desacuerdo las nombra. La señal sigue siendo cierta —dice que existen y que
  hay que mirarlas— pero su texto no está en el material. Si molesta, el reparto
  se puede hacer por cuota en vez de por orden.
- **101 avisos de cobertura en 19 consultas** (5,3 de media) con las capas
  encendidas; 44 sin ellas. Son huecos reales, pero conviene vigilar que el
  bloque nuevo no se sature igual que se saturó el estado.

---

# FASE 13 · UN AVISO QUE SALE SIEMPRE NO ES UN AVISO, ES DECORACIÓN

**Ese es el criterio, y vale para todo lo que se enseñe de aquí en adelante.**
Si algo aparece en todas las respuestas, o se resume o se quita: dejarlo entero
solo consigue que se deje de leer lo que está a su lado. No es una cuestión de
estilo, es que un aviso constante entrena a no mirar el sitio donde aparece.

Se aprendió dos veces seguidas, que es como se aprenden estas cosas:

1. `CRITERIO DISCUTIDO` salía **17 de 19** → se separó el estado de la
   cobertura (fase 12) → bajó a 5 de 19.
2. El cajón nuevo salió con **101 avisos en 19 consultas, 5,3 de media** → el
   mismo fallo un piso más abajo.

## La cobertura, partida por lo que se puede HACER

| | **ACCIONABLE** | **ESTRUCTURAL** |
|---|---|---|
| qué es | hay algo concreto que mirar | límite permanente del corpus |
| cambia de una consulta a otra | sí | **no**, es el mapa de lo que tenemos |
| qué entra | doctrina del TEAC sobre este artículo; el artículo cambió después del ejercicio; una disposición que le afecta y no se recogió; una fuente que no respondía; una consulta citada que va de otra cosa | remisiones a normas que no tenemos y no vamos a tener (Ley Concursal, Código Penal, TFUE) |
| cómo se enseña | arriba y **completos** | **una línea** al final, en gris |

**Medido sobre las 19, avisos accionables por consulta:**

| | antes | después |
|---|---|---|
| con las capas de criterio | 5,3 | **2,4** (máximo 5, dos consultas con 0) |
| sin las capas | 2,3 | **1,2** |

Los estructurales son 1,2 por consulta y van en una sola línea, así que aportan
una línea, no una por precepto.

### La mitad de la mejora vino de dejar de avisar sobre lo que no se manda

Del desglose salió que **48 de 75 avisos** (2,5 por consulta) eran del tipo
*«V0123 da criterio sobre otra norma»* — y con el recorte de la fase 12 esas
consultas son **justo las que ya no se mandan** (cero párrafos pertinentes). Se
estaba avisando de un documento que el redactor no ve y no puede citar.

`dgt.leer_criterio` recibe **solo las consultas que tienen texto en el
material** (`redactor.Plan.enviadas`). Pasando todas: 2,5 avisos por consulta de
ese tipo. Pasando solo las mandadas: 0,9.

## El presupuesto no se lo puede comer el primero

Antes se llenaba en orden y la primera consulta se llevaba todo el hueco. Y
aquí eso es lo peor que puede pasar: **el valor de esta capa es ver que el
criterio ha ido cambiando con los años**, y para eso hacen falta las tres, no
una larga.

- **Cuota por consulta**: el hueco se reparte a partes iguales entre las
  consultas con material pertinente. Es un **suelo garantizado**, no un techo:
  lo que una no gasta pasa a la siguiente, pero **nadie puede gastar el suelo
  de las que vienen detrás**.
- **O se le hace sitio o no se nombra.** Si con esa cuota alguna no cabe ni con
  su primer párrafo, se cae la de menos prioridad y se reparte otra vez entre
  las que quedan. `Plan.enviadas` lleva las que sí tienen texto, y una señal no
  puede nombrar nada que no esté ahí: **la señal y el material no se
  contradicen**.

Medido con tres consultas grandes sobre el mismo artículo: antes `2224 / 0 / 0`
caracteres; ahora `2224 / 2595 / 2224`.

**Rectificación de lo que informé la vez anterior:** dije que en el art. 80 la
señal nombraba consultas cuyo texto no estaba en el material. En el camino real
de `fase4` eso no pasaba: la señal se calcula desde las consultas **citadas y
verificadas**, y para citarlas el redactor tiene que haberlas visto. La
contradicción estaba en mi guion de demostración, que pasaba las tres. El
reparto por cuota sí era un problema real y es lo que se ha arreglado; ahora
además la garantía está comprobada en el código y no deducida.

## La caché no cubría procedimiento

En **7 de las 19** consultas del banco no había criterio ninguno *(la vez
anterior informé 5: la cifra era corta)*. Los artículos que faltaban son casi
todos de **procedimiento** —27, 135, 138, 198, 203, 236, 239, 267 de la LGT—, y
la primera siembra solo miró IVA: la despensa estaba vacía **por construcción**,
no por falta de criterio en la fuente.

`sembrar.py` ya no lleva la lista a mano: `articulos_sin_criterio()` la
**calcula**. Para cada consulta del banco corre la búsqueda y el corte de
material —deterministas los dos, ni una llamada al modelo— y mira qué preceptos
acaban en el material sin ninguna consulta cacheada que los cite. Se apunta a lo
que **se manda**, no a lo que el banco espera, porque el recorte compara contra
los preceptos del material. Las disposiciones se saltan: no tienen número que
buscar en PETETE.

## El artículo 4 y las señales de mentirijilla

Al filtrar por «solo lo que está en el material», `CRITERIO DISCUTIDO` bajó de
4 a 2 sobre las 19. Antes de darlo por bueno se miró **qué señales se pierden**,
y el resultado cambia la lectura:

| señal perdida | veces |
|---|---|
| «sobre el **artículo 4** de la Ley 37/1992 hay 2 consultas de años distintos» | 4 |
| lo mismo sobre el **artículo 5** | 1 |
| lo mismo sobre el **artículo 93** | 1 |

Los artículos 4 y 5 son *hecho imponible* y *concepto de empresario*: la DGT los
cita **de oficio en el campo `normativa` de casi cualquier consulta de IVA**.
Que dos consultas de años distintos los mencionen no es evidencia de que el
criterio haya evolucionado; es el encabezado de rigor.

Las tres señales que **sobreviven** son sobre los artículos 99, 8 y 68 —
sustantivas las tres. Así que el filtro no está tapando desacuerdos: está
quitando señales que salían del membrete.

**Nota de método:** la señal se calcula desde el campo `normativa` (metadatos) y
el recorte selecciona por menciones **en la prosa**. Cuando discrepan, gana la
prosa. Es discutible y es la decisión tomada: si la contestación no habla del
artículo, no hay texto que enseñar, y una señal sin texto detrás manda a leer
algo que no se ha dado.

### Lo que se probó y NO se quedó

Se implementó una prioridad al descartar por presupuesto: que se cayera antes
una consulta suelta que una que forma **par de años distintos** sobre el mismo
precepto. **No cambia ni un resultado** sobre las 19 — las señales no se
perdían por presupuesto sino por falta de párrafos pertinentes, que es lo de
arriba. Se quitó: maquinaria sin efecto medido es maquinaria que engaña al que
la lee dentro de seis meses. Queda el comentario en `redactor.py` para que no
se vuelva a intentar sin medir.

## Segunda siembra: la despensa casi se dobla, el agujero baja a la mitad

| | antes | después |
|---|---|---|
| consultas guardadas | 117 | **241** |
| pares (norma, artículo) a norma cargada | — | 650 de 1042 |
| ocupa | — | 13,6 MB |
| artículos del banco sin criterio | 19 | **11** |
| consultas del banco sin criterio en el material | 7 | **6** |

111 descargas nuevas en la pasada, **5 fallidas** por forma inesperada (no se
guardan) y **3 cortes por caída** de los que se retomó solo. Terminó sola, sin
llegar al tope de 300.

**La cobertura por artículo mejora mucho más que el resultado final**, y conviene
entender por qué: que un artículo tenga consultas no basta: hace falta que
alguna **hable de él en la prosa**, no solo que lo cite en el campo `normativa`.
Ahí es donde se queda la diferencia entre 19→11 artículos y 7→6 consultas.

Lo que sigue sin criterio, y son los que hay que mirar si se quiere cerrar el
hueco: RIVA 22, 31, 31 bis y sus dos disposiciones adicionales; LGT 27, 103,
138, 203, 267; LIVA 9 bis. En procedimiento puro (LGT) puede sencillamente no
haber consulta vinculante de la DGT: no es lo suyo, para eso está el TEAC.

---

# FASE 14 · UN TEAR NO ES EL TEAC

Salió de mirar si el TEAR estaba al alcance y encontrar que **ya estaba dentro,
sin filtrar y mal etiquetado**. No es funcionalidad nueva: es un defecto.

## Qué estaba pasando

La búsqueda de DYCTEA manda el filtro de unidad **vacío** (`u=""`), así que
devuelve **todos los tribunales**. En la copia local de 9 criterios había dos
que no eran del TEAC, y se citaban así:

```
{Criterio TEAC 07/02872/2023/00/00, de 29/04/2025, TEAR de Baleares — …}
```

La etiqueta decía TEAC y la unidad decía TEAR, en la misma línea. Y
`BLOQUE_TEAC` le atribuía la fuerza del **art. 239.8 LGT**, que un tribunal
regional no tiene. Una resolución que no obliga a nadie, presentada como
doctrina que obliga a toda la Administración.

Medido: sin filtrar salen **71** resoluciones sobre el art. 80; del TEAC son
**55**. Las otras 16 son regionales, y las tratábamos igual.

## Cuatro reglas, y ninguna la ponemos nosotros

**1 · La etiqueta sale del registro.** `etiqueta_de(unidad)`: `TEAC` →
«Criterio TEAC»; `TEAR de Cataluña` → «Resolución del TEAR de Cataluña». El
TEAR **nunca** se llama «criterio»: un criterio es doctrina, y la doctrina la
sienta el TEAC.

**2 · La fuerza sale de la calificación de la fuente.** DYCTEA ya califica cada
resolución (`Doctrina`, `No vinculante`). `fuerza_de(unidad, calificacion)` lee
esa calificación y **combina los dos campos**, porque hacen falta los dos: la
fuerza del 239.8 es del TEAC **cuando sienta doctrina**. Ni un TEAR con la
calificación más alta la tiene, ni un TEAC «No vinculante». Calificación
desconocida → **no se afirma nada**. Es la regla de siempre: callar cuesta una
frase, atribuir fuerza de más cuesta un cliente.

En la copia local hay un TEAC `00/02189/2021` calificado **«No vinculante»**:
no es una hipótesis, pasa.

**3 · Dos ejes, dos bloques.**

| | peso jurídico | valor predictivo |
|---|---|---|
| doctrina del TEAC | alto, vincula (239.8) | medio |
| consulta de la DGT | vincula frente a quien consultó | medio |
| resolución de un TEAR | **ninguno**, resuelve su caso | **el más alto** para un cliente de esa provincia |

Son ejes distintos y no se pueden mezclar. El orden del material es el del peso
jurídico —`LEY → TEAC → DGT → TEAR`— y el bloque regional dice lo que es: no
vincula a nadie, pero es lo más informativo sobre **qué le va a pasar de hecho**
al cliente, porque es el tribunal que le va a tocar.

**4 · El orden, por peso y luego por fecha.** `teac.peso` y `teac.nivel`:

```
0  TEAC que unifica criterio
1  TEAC que sienta doctrina
2  TEAC sin fuerza declarada
3  TEAR y salas desconcentradas
```

Dentro de cada nivel, la fecha. Antes se ordenaba solo por unificación y fecha,
y por eso **una resolución del TEAR de 2025 adelantaba a doctrina del TEAC de
2023**: más nueva sí, con más peso no.

**Y los avisos cuentan por unidad**: «hay 1 resolución del TEAR de Baleares y 1
resolución del TEAR de Madrid sobre el artículo 95», no «2 criterios del TEAC».

## El rótulo se comprueba, en los dos sentidos

`teac.rotulo_valido` contrasta el rótulo de la cita contra el campo `unidad` de
la copia local, y engañan **los dos sentidos**:

- llamar TEAC a lo que es de un TEAR → le da fuerza que no tiene;
- llamar TEAR a lo que es del TEAC → se la quita, y el profesional descarta
  doctrina que sí le obliga.

Tres desenlaces, no dos: `ok`, `mal` y **`sin_unidad`**. Si la copia local no
dice qué tribunal la dictó, **no se puede comprobar**, y eso es `NO_VERIFICABLE`,
no `NO_VERIFICADA`: dar el visto bueno sería dejar pasar la atribución sin
mirarla, y rechazar sería tumbar la respuesta por un hueco **nuestro**.

La comparación del rótulo ignora tildes —«TEAR de Cataluna» vale— porque es
**nuestro** rótulo, no texto copiado de la fuente. El fragmento citado se sigue
comprobando letra por letra, con tildes. Eso no se toca.

Tres casos nuevos en la batería (37 casos, en verde):

| caso | veredicto |
|---|---|
| `tear-presentado-como-doctrina-del-teac` | NO_VERIFICADA |
| `tear-citado-como-lo-que-es` | VERIFICADA |
| `teac-degradado-a-tribunal-regional` | NO_VERIFICADA |

El segundo importa tanto como el primero: **lo que se rechaza es la atribución
falsa, no la fuente**. La misma resolución y el mismo fragmento, nombrando al
tribunal que la dictó, valen.

## Lo que hay que vigilar

**Lo regional es lo primero que sobra**, por diseño: va el último en el orden de
peso, así que cuando el presupuesto aprieta se cae. Medido sobre las 19 del
banco: **3 llevan bloque regional** al material. Con siete criterios del TEAC
sobre el mismo artículo (arts. 80 y 95 juntos) las dos regionales no entran, y
eso es correcto —lo que no vincula sobra antes— pero significa que **el eje
predictivo solo llega cuando el jurídico deja sitio**. Si algún día se quiere
que una resolución del TEAR de Cataluña llegue siempre a un cliente de aquí,
eso es una **cuota reservada** y es una decisión, no un ajuste.

**El filtro de unidad sigue vacío.** No se ha tocado la descarga: se sigue
bajando de todos los tribunales. Ahora al menos se etiqueta bien lo que entra.

---

# FASE 15 · EL PRIMER ARRANQUE INSTALA. NO SUPONE NADA.

Probado en un Windows real: el `.bat` **no creaba el venv** y **obligaba a
editar el `.env` a mano**. En una oficina eso no lo hace nadie, así que el
agente no llegaba a arrancar.

## Un solo sitio con la lógica

`instalar.py` hace las librerías, la clave y el corpus. Los dos lanzadores solo
saben hacer lo que Python **no puede hacerse a sí mismo**: encontrar un Python y
crear el entorno virtual.

Por qué así: escribir esa lógica dos veces, una en `cmd` y otra en `bash`, es
garantizar que dentro de un mes hagan cosas distintas **y que la que se rompa
sea la de Windows**, que es justo la que no puedo probar.

| paso | quién | si falta |
|---|---|---|
| 1 · Python | lanzador | **para**: es lo único que necesita a una persona |
| 2 · venv | lanzador | lo crea, sin preguntar |
| 3 · librerías | `instalar.py` | `pip install -r requisitos.txt` |
| 4 · clave | `instalar.py` | la **pide por pantalla** y la comprueba |
| 5 · corpus | `instalar.py` | lo ingiere diciendo por dónde va |
| 6 · ventana | lanzador | la abre |

**Arranques siguientes:** cinco comprobaciones de fichero —venv, `.env` con
clave, librería, y las tres normas— sin arrancar Python. Si está todo, abre.

## La clave se pide, no se edita

Se explica qué es, de dónde se saca (`platform.claude.com` → API keys) y que se
queda solo en este equipo. Se teclea oculta, se guarda en el `.env` **conservando
las explicaciones del ejemplo**, y se le pone permiso `600`.

**Y se comprueba antes de seguir**, hasta 3 intentos. Que un dato mal pegado se
descubra tres días después delante de un cliente es exactamente lo que esto
viene a evitar. Un `.env` **creado y vacío** no cuenta como configurado: ese era
el estado en que se quedaba el equipo antes.

## Dos fallos que solo existen en Windows

**1 · `if` con `&&` no se agrupa.** Lo escribí así:

```bat
if not defined BASE python -c "import sys" >nul 2>&1 && set "BASE=python"
```

En `cmd` eso se lee como `(if not defined BASE python …) && (set BASE=python)`:
el `set` corre según el errorlevel **anterior**, aunque el `if` sea falso. El
lanzador elegía `python` aunque `py -3` ya hubiera funcionado. Reescrito sin
`&&` y sin paréntesis, línea a línea.

**2 · `dirname` es un programa externo.** `cd "$(dirname "$0")"` necesita el
PATH para averiguar dónde vive el script. Un lanzador que depende del PATH para
eso se rompe justo en el equipo mal configurado, que es el único donde importa.
Ahora usa expansión del propio shell: `cd "${0%/*}"`.

El linter (`lint_bat.py`) tiene dos comprobaciones nuevas: ningún `if` con `&&`
en la misma línea, y todo `set` con la forma entrecomillada.

## Qué está probado y qué no

**Ejecutado de verdad en Mac**, ocho escenarios sobre copias en temporal:

| escenario | resultado |
|---|---|
| todo correcto | abre sin instalar nada |
| sin venv | lo crea, instala y abre |
| sin `.env` | pide la clave, la guarda y abre |
| `.env` vacío | no lo da por bueno, la pide |
| clave inválida | lo dice, reintenta 3 veces y para |
| sin corpus | lo ingiere diciendo qué y cuánto lleva |
| sin librería | `pip install` **real** y abre |
| sin Python | para con las instrucciones exactas |

**Sustituido por un doble** (y por eso NO probado de verdad): la comprobación de
la clave contra la API, la descarga del BOE y la apertura de la ventana. Los
tres salen a la red; lo que se prueba es la orquestación y los mensajes.

**NO probado en Windows, y hay que decirlo:** no tengo Windows. Del `.bat` solo
está el repaso estático. Lo que ese repaso **no** puede garantizar:

- que `py -3` exista y se comporte igual en ese equipo concreto;
- que `python -m venv` funcione contra el Python que haya instalado;
- que `getpass` oculte la escritura en la consola de Windows (si no puede, el
  instalador lo dice y pide la clave a la vista, en vez de caerse);
- que el antivirus o la política de la empresa no bloqueen `pip`;
- el aspecto real de los acentos en esa consola (por eso el `.bat` es **ASCII
  puro y CRLF**, comprobado).

---

# FASE 16 · LA CLAVE SE PIDE EN UNA VENTANA

## El diagnóstico: NO era pythonw

La sospecha era que `abrir_agente.bat` arrancaba con `pythonw.exe`, sin consola.
No es eso: el `.bat` ya lanza `instalar.py` con **`python.exe`** (línea 99) y
reserva `pythonw.exe` solo para la ventana final (línea 146).

Lo que sí es distinto en Windows es `getpass`. No es una función: son tres
implementaciones y Python elige una al importar. En Windows elige `win_getpass`,
que **no usa stdin ni stdout**:

```python
for c in prompt:
    msvcrt.putwch(c)        # el prompt va DIRECTO a la consola, no a stdout
c = msvcrt.getwch()         # lee DIRECTO del teclado, no de stdin
else: pw = pw + c           # cualquier caracter de control entra en la clave
```

De ahí salen tres fallos, y los tres encajan con «no funciona»:

1. **El prompt puede no verse donde toca.** `putwch` se salta `sys.stdout`, y el
   instalador reconfigura stdout a UTF-8 al arrancar. Son dos canales hacia la
   misma ventana: el texto explicativo por uno y «Pega aquí la clave» por el
   otro. Lo que ve una persona es la explicación y debajo **nada**.
2. **No se ve nada al escribir**, por diseño. Quien pega una clave no sabe si se
   ha pegado. Sumado a lo anterior: una pantalla quieta que parece colgada.
3. **Ctrl+V puede entrar como carácter.** `getwch()` lee teclas crudas. Si la
   consola no tiene el atajo activado, Ctrl+V manda `\x16`, que se añade **dentro
   de la clave**, y el fallo aparece después.

**No se ha podido reproducir**: aquí no hay Windows. Los tres se sostienen
leyendo `Lib/getpass.py` de CPython, no ejecutándolo. Y por eso el arreglo no es
afinar `getpass`, sino **dejar de depender de él**.

## El arreglo: `dialogo_clave.py`

Una ventana de tkinter —garantizado, porque la aplicación *es* tkinter— con el
texto de dónde se saca la clave, un campo oculto con casilla «Mostrar lo que
escribo», pegado nativo y comprobación **antes** de cerrar.

- **Pegar funciona.** Se atan `Ctrl+V`, `Ctrl+Shift+V` y `Cmd+V` a mano y se
  devuelve `"break"`, para que el atajo propio de Tk no pegue una segunda vez.
  Y se limpian espacios y saltos de línea, que es lo que trae una clave copiada
  de una web.
- **Si la clave no vale, lo dice ahí mismo y no se cierra.** Se puede reintentar
  en la misma ventana.
- **Sin entorno gráfico cae a la consola**, como antes. Se comprueba *abriendo*
  una ventana, no suponiendo: que `import tkinter` funcione no dice nada de si
  hay pantalla.

### El fallo que encontró la prueba

La primera versión devolvía el resultado del hilo con `self.raiz.after(0, ...)`.
**Tkinter no es reentrante**: `after` llamado desde un hilo que no es el suyo se
pierde en silencio, y la ventana se queda con «Comprobando...» para siempre.
Ahora el resultado vuelve por una **cola** que sondea el hilo de la ventana —el
mismo patrón que ya usaba `interfaz.py`, y por el mismo motivo.

## El resto del instalador, con la misma lupa

| dónde escribe / pregunta | canal | en Windows |
|---|---|---|
| `linea()`, `paso()`, `ok()`, `parar()` | `print` a stdout | **bien**: hay consola |
| `echo` del propio `.bat` | consola | **bien** |
| instrucciones de «falta Python» | `echo` del `.bat` | **bien** |
| pedir la clave | `msvcrt` | **estaba roto** → ahora ventana |
| progreso de la ingesta | `capture_output=True` | **estaba flojo** → corregido |

**El único canal roto era el de la clave.** Lo demás escribe por stdout con
`flush=True` y se ve.

**Lo flojo, y también corregido:** `ingerir_corpus` lanzaba `fase1.py` con
`capture_output=True`, así que la salida se tragaba y solo se imprimía una línea
*cuando la norma ya había terminado*. Bajar una norma tarda minutos: durante ese
rato la pantalla no se movía. Ahora se lee línea a línea y se va enseñando,
guardando las últimas 25 por si hay que explicar un fallo.

## Qué está probado y qué no

**Ejecutado de verdad en Mac:** el diálogo, manejado por código (8 bloques:
ocultar/mostrar, pegar sin duplicar, aviso de formato, clave buena, clave mala
con reintento en la misma ventana, cancelar) y **diez** escenarios de
instalación, dos de ellos nuevos: con pantalla usa la ventana y no la consola, y
si la persona cierra la ventana el instalador para sin abrir el agente.

**NO probado en Windows, y hay que decirlo:** sigue sin haber Windows aquí. En
concreto no se ha podido comprobar que el diálogo salga al frente sobre la
consola del `.bat`, ni que `Ctrl+V` pegue en esa ventana en ese equipo, ni el
aspecto real de la tipografía. Lo que sí se puede afirmar es que **ya no depende
de `msvcrt`**, que es de donde salían los tres fallos.

---

# FASE 17 · QUE NUNCA HAYA BUCLE, Y GASTAR MENOS

## La regla de proceso, que es donde se fue el dinero

> **Ninguna tarea larga se lanza esperando. Se escribe a fichero y se consulta
> después. Nada de bucles de espera.**

La mayor parte del gasto de este proyecto **no han sido las consultas del
agente**: han sido esperas. Un proceso que tarda veinte minutos y se vigila
mirándolo cuesta muchísimo más que el mismo proceso escribiendo a un `.log` que
se lee cuando ha terminado. Vale para la siembra, para la ingesta del BOE y para
cualquier cosa que tarde: se lanza al fondo, escribe a fichero, y se mira luego.

## 1 · El techo duro

Había un reintento controlado en `fase4`, y está bien. Pero **un tope que vive
en el bucle solo protege mientras ese bucle esté bien escrito**. Ahora hay algo
debajo, en `Motor`, que es el único sitio por el que se pasa siempre:

| | |
|---|---|
| `TOPE_LLAMADAS` | 6 por consulta |
| `TOPE_SEGUNDOS` | 300 por consulta completa |
| `TIMEOUT_LLAMADA` | 120 s por llamada |
| `REINTENTOS_RED` | 3, con espera creciente (la hace el SDK) |

Detalles que importan:

- **Se comprueba ANTES de llamar**, no después: el objetivo es no gastar la
  llamada, no enterarse de que se ha gastado.
- **El reloj se reinicia por consulta.** El banco reutiliza el mismo motor para
  varias seguidas; sin eso, la quinta se pasaría de tiempo por culpa de las
  cuatro anteriores.
- **Vale también para el motor de ensayo.** Un tope que solo actúa cuando cuesta
  dinero no se puede probar el día que hace falta.
- **Una parada por tope NO es un fallo del modelo** y no se cuenta igual:
  `fallo="tope"`, estado `PARADA POR TOPE` y un `topes.json` en la traza con
  cuántas llamadas, cuál era el tope y por qué se paró.
- El cliente se crea con `timeout` y `max_retries` **explícitos**. Sin ellos el
  SDK espera 10 minutos por llamada y reintenta 2 veces por su cuenta: dos
  números que nadie eligió y que se multiplican.

**Demostrado, no afirmado** (`prueba_topes.py`): un modelo que siempre falla, y
se comprueba que para **en** el tope y **no antes**. Las dos mitades:

| tope | llamadas | quién manda |
|---|---|---|
| 1 | 1 | el techo |
| 2 | 2 | el techo |
| 3 | 3 | la lógica (1 análisis + 2 redacciones) |
| 6 (el de hoy) | 3 | la lógica: el techo no se toca |

## 2 · El umbral del corte: medido otra vez, y NO se toca

El desperdicio es real: en las dos trazas con respuesta de un modelo de verdad,
**se mandaron 5 preceptos y se citó 1**. 80%.

Pero **el umbral no es la palanca**, y esto se ha medido con el mismo método que
la primera vez —los términos que propuso el analizador, guardados en las
trazas—, ahora con **91 consultas distintas** en vez de 65:

| umbral | preceptos/consulta | se quedan con 1 |
|---|---|---|
| 0,65 | 4,00 | 3 |
| **0,70** | **3,79** | **5** ← el de hoy |
| 0,71 | 3,71 | 7 |
| 0,73 | 3,62 | 12 |
| 0,75 | 3,44 | 18 |

**El escalón sigue exactamente donde estaba.** Con más del doble de datos, 0,70
sigue siendo el último valor antes de que la curva se dispare. Subirlo a 0,75
dejaría 18 de 91 consultas con un solo precepto, que es el «cortar por puesto
mata casos buenos» que este proyecto ya rechazó una vez.

Y un dato que descarta la otra sospecha: sobre las 19 del banco, **cero
preceptos entran por remisión**. Los 2,9 extra por consulta entran todos por
cobertura. Separarlos era necesario porque el que entra por remisión puede no
citarse y aun así estar bien mandado; aquí no hay ninguno.

**Conclusión: el desperdicio no viene de un umbral flojo, viene de que la
cobertura empata.** Varios preceptos cubren las mismas palabras sin contestar la
pregunta. Eso no se arregla moviendo un número.

## 3 · El modelo no se cubre sobre lo que el código sabe

Reglas nuevas en el prompt del redactor:

- **Regla 11:** la versión que se le da ES la que aplicaba, calculada con las
  fechas del BOE. Prohibido «conviene confirmar que no ha habido modificación
  posterior», «según el material facilitado» o «habría que verificar la
  vigencia». Y los avisos de vigencia, las remisiones que faltan y los límites
  del corpus **los pone el sistema** debajo: repetirlos los saca dos veces.
- **Regla 12:** no enumerar lo que no se usa. La respuesta del turismo gastaba
  un párrafo entero en decir que los artículos 9, 57, 101 y 27 no resolvían la
  duda. Esa frase no le sirve a nadie y se paga por palabra.
- **Estructura:** desaparece el apartado de Advertencias (lo pone el sistema) y
  el Planteamiento baja a una frase que no repita el enunciado.

## 4 · La caché: estaba mal calibrada y se ha medido

La caché de prompt **funciona**, y en la traza se ve:

```
20260802T122131  redaccion 1   entrada 10238  cacheE 2417   <- la escribe
20260802T122234  redaccion 1   entrada 11121  cacheL 2417   <- la lee
20260802T122234  redaccion 2   entrada 11492  cacheL 2417   <- y la relee
```

Pero el estimador que decide si un bloque se marca como cacheable contaba a
**3,5 caracteres por token**, que es lo que se dice para inglés. Contrastado con
lo que contó la propia API:

```
5.373 caracteres  ->  2.417 tokens  =  2,22 caracteres por token
```

Castellano jurídico, con tildes, comillas latinas y palabras largas. Con 3,5 se
contaban **un 58% menos tokens de los que hay**, así que bloques que sí llegaban
al mínimo se marcaban como que no. Es lo que le pasaba al **prompt del
analizador**: 1.466 caracteres, unos 666 tokens, mínimo 512 — cacheable desde
siempre, y sin cachear en cada consulta.

Corregido `CARACTERES_POR_TOKEN = 2.2` y marcado el prompt del analizador. El
riesgo es de un solo lado: si aun así un bloque no llega, la API se lo salta en
silencio y no se cobra nada de más.

## Lo que NO se ha podido medir, y hay que decirlo

**La cuenta no tiene saldo.** La llamada real para medir la salida «después»
devolvió `400: Your credit balance is too low`. Falló en la primera llamada, así
que no se gastó ni un token, pero **el ahorro en tokens de salida de los puntos
3 y 4 está sin medir**: está razonado y no comprobado, que no es lo mismo.

Queda pendiente, en cuanto haya saldo: una consulta del turismo y comparar
contra la traza `20260802T122234` (entrada 25.124, salida 5.433, 4 llamadas).

---

# FASE 19 · LA DOCTRINA, POR ASUNTO Y NO SOLO POR ARTÍCULO

## El fallo

`por_preceptos` elegía por coincidencia de **artículo**. Sobre el artículo 80
—modificación de base imponible por créditos incobrables— mandaba estos tres:

```
00/01298/2004  IVA a la importación. Despacho a libre práctica
00/03399/2023  Impuesto sobre la ELECTRICIDAD. Devolución por impagados
00/05524/2024  Impuesto sobre la ELECTRICIDAD. Devolución por impagados
```

y dejaba fuera **los cuatro que iban justo de la pregunta** (00/02189, 00/03983,
00/05698, 00/06614). No fue mala suerte: el orden por peso ponía delante el de
unificación y los más recientes, y el tope de 3 se comía a los buenos. **Se
elegían los tres peores y se descartaban los cuatro mejores.**

Es la tercera vez que este proyecto tropieza con lo mismo: un aviso que casi
nunca viene al caso se deja de leer.

## El umbral por términos NO funciona, y hay que decirlo

Lo primero que se midió fue cobertura de términos contra `asunto` +
`conceptos`, como se pidió. **No discrimina:** los dos de electricidad puntúan
**1,00**, porque sus conceptos son literalmente «Base imponible: modificación» y
«Crédito incobrable». Tratan exactamente de eso — pero en el Impuesto Especial
sobre la Electricidad.

Lo que los separa no son los términos: es **el impuesto**. Y la fuente lo dice.

## Dos filtros, y el que trabaja es el primero

**1 · MATERIA** (`materia_ajena`). Los `conceptos` son vocabulario controlado de
DYCTEA, no prosa:

```
00/03399, 00/05524 -> ['Impuesto Especial sobre la Electricidad', 'Impuestos Especiales IIEE']
los otros siete    -> ['Impuesto sobre el Valor Añadido IVA']
```

Si el criterio nombra impuestos y **ninguno** es del corpus, fuera. Si **no
nombra ninguno**, se le deja pasar: no se supone lo que la fuente no dice.

**2 · ASUNTO** (`cobertura_asunto`). La misma máquina que para los preceptos,
contra `asunto` + `conceptos`. Esta sí coge al de importación, que es de IVA
pero de otra cosa: cobertura **0,00**.

### El umbral, de los datos

Medido sobre las 7 consultas que traen criterios, con el filtro de materia ya
aplicado. Las coberturas que se dan son {0,00 0,20 0,40 0,50 0,60 0,75 1,00}:

| umbral | criterios/consulta | consultas sin ninguno |
|---|---|---|
| **0,20** | **1,57** | **0** ← último escalón |
| 0,25 | 1,14 | 1 |
| 0,50 | 1,00 | 2 |

`UMBRAL_ASUNTO = 0,20`, el último valor antes de que una consulta se quede sin
nada. **Aviso honesto: son 7 consultas y 9 criterios, que es poco.** El número
que de verdad hace el trabajo es el filtro de materia; este es el ajuste fino y
habrá que remedirlo cuando la copia local crezca.

## El resultado

| consulta | antes | ahora | qué se manda ahora |
|---|---|---|---|
| prorrata | 0 | 0 | — |
| rectificación | 1 | 1 | Rectificación de bases imponibles |
| turismo | 2 | 2 | Alquiler de embarcaciones · Deducibilidad |
| **art. 80** | **3** | **3** | **Modificación BI · Rectificación BI · Modificación BI (plazo)** |

**El número no cambia: cambia el contenido.** En el art. 80 se mandan ahora los
tres que hablan de base imponible, y se descartan los dos de electricidad («va
de otro impuesto») y el de importación («coincide el artículo, no el asunto»),
cada uno con su motivo escrito en la traza.

Contraste con el juicio del propio modelo: en la prueba anterior escribió *«la
doctrina del TEAC incorporada al material se refiere a la devolución en el
Impuesto Especial sobre la Electricidad y no aporta criterio»* — 3 traídos, **0
pertinentes**. Ahora los 3 son del asunto.

## Si no queda ninguno, se dice

> *hay 7 resolución(es) económico-administrativa(s) que citan el artículo 80,
> pero NINGUNA es del mismo asunto que esta consulta: no se manda ninguna.*

Mejor eso que traer una que no viene al caso. Y **solo sobre los artículos que
sostienen la respuesta**: la primera versión sacaba siete avisos nombrando
artículos que nadie había citado, porque un criterio cita varios y la mayoría no
están en juego. De 7 avisos a 2.

## Y el detector de anexos

El artículo 95 define «automóvil de turismo» remitiendo al **anexo del Real
Decreto Legislativo 339/1990**, que no está en el corpus. El escaneo solo
buscaba «artículo N» y disposiciones: un anexo no tiene número de artículo, así
que **no lo cogía nadie**. Lo salvaba el redactor por su cuenta, y eso no puede
ser el plan.

`_RE_ANEXO` exige **designación con número** («339/1990»). Medido: hay 28
menciones de «anexo» en el corpus y solo una es remisión real a otra norma; sin
exigir el número, el título del propio anexo —«ANEXO / REGLAMENTO DEL
IMPUESTO…»— se colaba. Y si la norma está cargada no se emite nada: de las
nuestras tenemos el articulado.

Remisiones: **1704 → 1709** totales, **159 → 164** pendientes externas. Cinco
nuevas en todo el corpus, ninguna de ruido.

---

# FASE 20 · UN SOLO INTERRUPTOR

## El problema

Encender las fuentes eran **cuatro cosas** coordinadas por la memoria de una
persona: `AGENTE_DGT`, `AGENTE_TEAC`, `AGENTE_DGT_TEXTOS` y cambiar `GUIA.md` a
mano. El día que se olvidara una, la ventana diría que la DGT está y la hoja de
la mesa diría que no. **Y quien lea la hoja decidirá con ella.**

## El mando

```
python configurar.py --estado          qué hay ahora, y lo que cuesta
python configurar.py --con-criterio    enciende las fuentes, sus textos y su guía
python configurar.py --solo-ley        vuelve a la ley sola
```

Las cuatro piezas o ninguna. Y los dos modos son **simétricos**: no hay ida sin
vuelta.

**`GUIA.md` pasa a ser un fichero generado.** Las versiones que se editan viven
en `guias/GUIA.solo-ley.md` y `guias/GUIA.con-criterio.md`, cada una con una
marca `<!-- MODO: … -->` dentro. La marca viaja con el texto que describe: un
registro aparte se queda viejo, una marca dentro del fichero no.

### Por qué un fichero y no solo variables de entorno

Una variable vive dentro de un proceso: `configurar.py` no puede dejarla puesta
para el doble clic de mañana. Así que el modo se guarda en `modo.json`.

```
ORDEN DE MANDO:  variable de entorno  >  modo.json  >  apagado
```

El entorno manda **a propósito**: las suites encienden la DGT con `AGENTE_DGT=1`
para una ejecución concreta y no deben depender de cómo esté configurado el
equipo ni dejarlo tocado.

**`modo.json` va al repositorio**, y no es un descuido: `GUIA.md` también está
versionado. Si uno viajara y el otro no, un clon nuevo tendría la guía de un
modo y el modo por defecto del otro — y se negaría a abrir nada más clonarlo.

## Imposible quedarse a medias

`configuracion.revisar()` mira lo que **cada pieza dice de verdad** —no lo que
debería decir— y lo compara con el modo. Si algo no cuadra, ni la ventana ni la
terminal abren:

```
La herramienta esta a medio configurar y NO se abre.

El modo guardado es «solo-ley», pero no todo lo acompana:

  · fuente DGT: esta encendida y el modo «solo-ley» pide que este apagada

Se arregla con UNA orden, que deja las cuatro piezas a la vez:

    python configurar.py --solo-ley

No se abre a medias a proposito: si la ventana dijera que hay criterio de
la DGT y la hoja de la mesa dijera que no, alguien decidiria con la que
tuviera delante.
```

La terminal para **antes de gastar una llamada**. Comprobado rompiendo cada
pieza por separado: guía sin marca, guía del otro modo, fuente encendida a mano
y textos encendidos a mano. Los cuatro se detectan y **los cuatro dicen cuál es**
— «algo va mal» no sirve para arreglarlo.

## La guía dice la verdad en los dos modos

La de `con-criterio` lleva la tabla que faltaba, y es lo más importante de esa
página:

| | qué es | a quién obliga |
|---|---|---|
| Ley y reglamento | la norma | a todos. Es lo único que fundamenta |
| Doctrina del TEAC | criterio del tribunal central | **a toda la Administración** (art. 239.8 LGT) |
| Consulta de la DGT | criterio administrativo | a Hacienda, **frente a quien preguntó** |
| Resolución de un TEAR | un caso resuelto en su región | **a nadie más que a ese caso** |

Con la nota de que un TEAR vale por **valor predictivo**, no por fuerza: es lo
que mejor anticipa qué le va a pasar de hecho a un cliente de esa provincia.

## ⚠️ SE PERDIERON LOS CATORCE BANCOS DE PRUEBAS

El 10 de agosto de 2026 el directorio temporal donde vivían se limpió entre
sesiones. Se perdieron las suites de unidad de las fases 9 a 19: `prueba_9b`,
`prueba_discutido`, `prueba_recorte`, `prueba_topes`, `prueba_dialogo`,
`prueba_unidad`, `prueba_asunto`, `prueba_interfaz`, `prueba_petete`,
`prueba_normativa`, `prueba_no_encontrado`, `prueba_textos_guia`,
`prueba_9b_e2e` y `prueba_instalador`.

**Empezaron siendo guiones de usar y tirar y dejaron de serlo hace mucho**: eran
lo único que decía si un cambio rompía algo. Escribirlos en `/tmp` fue el error,
y se mantuvo por inercia sesión tras sesión.

**Lo que NO se perdió**, porque está en el repositorio: la batería del
verificador (`fase3.py probar`, 37 casos), el banco de recuperación
(`banco.py`), las comprobaciones de la fase 4 y el diagnóstico de remisiones.
Y los **fixtures** (`casos/dgt_prueba/`, `casos/teac_prueba/`) también estaban
versionados, así que reescribir las suites no exige rehacer los datos.

**Regla, a partir de ahora:** si un guion comprueba algo que no queremos que se
rompa, va a `pruebas/` en el repositorio. Un banco de pruebas que se borra solo
no es un banco de pruebas.
