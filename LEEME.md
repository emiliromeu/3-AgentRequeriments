# Agente de consulta fiscal — LEEME

Sistema de consulta sobre normativa del IVA para el departamento fiscal de una
gestoría. **No decide: decide la persona.** Busca la norma aplicable, la lee y
devuelve la respuesta con las citas y los enlaces para comprobarla.

## ⚠️ NINGÚN DATO QUE PUEDA PARECER REAL SE ESCRIBE A MANO

> **Lo que se enseña sale de una traza o de la copia local. Nunca de mi cabeza.**
> Un ejemplo inventado en material de demostración **es una cita falsa con otro
> nombre**, y da igual que el texto que lo rodea sea auténtico: quien lo mira no
> distingue una parte de la otra.

Alcance: números de consulta de la DGT, de resolución del TEAC o de un TEAR,
artículos, fechas, importes. En **cualquier** cosa que pueda acabar delante de
una persona — la ventana, `GUIA.md`, los guiones de demostración, este LEEME.

**Cómo se cumple:** un guion de demostración lee el `resultado.json` de un
expediente y pinta lo que hay; **si un campo no está, no se pinta**. Nunca se
rellena a ojo. Si hace falta un ejemplo en documentación, se coge uno que esté
en la copia local y se comprueba que sus datos son los suyos.

**Los fixtures de prueba son otra cosa**, pero tienen que estar marcados en dos
sitios: un `LEEME.txt` en su carpeta diciendo que están inventados, y el propio
número fuera del rango real — la serie `9xxx` (`V9001-22`, `00/09001/2024`).
Viven en `casos/`, nunca en `datos/`: dentro de la caché de verdad serían
indistinguibles de material auténtico.

**Se incumplió el 10 de agosto de 2026** y por eso está escrito aquí arriba. Ver
la fase 25.

### Las dos caras de la misma comprobación

La regla de arriba tiene una hermana que descubrí al incumplirla, y es la misma
equivocación mirada del otro lado.

**Comprobar solo contra la copia local lleva a dos errores opuestos:**

| | qué se hace | qué sale |
|---|---|---|
| **inventar lo que falta** | escribir a mano un dato que no se tiene | una cita falsa con formato de real |
| **negar lo que existe** | leer «no está en mi copia» y escribir «no existe» | una afirmación sobre el mundo que no se puede sostener |

Los dos salen de lo mismo: **confundir nuestro disco con la realidad.** Y el
segundo es más traicionero, porque parece rigor.

**Lo que pasó, con nombres:**

- Escribí en `ver_ejemplo.py` que las consultas **V2759-21** y **V0187-20** «no
  existen en ninguna parte». **Existen las dos** — comprobado en PETETE. Yo solo
  había mirado `datos/dgt/`.
- Escribí que la resolución **08/02042/2022** del TEAR de Cataluña era «un número
  inventado con formato de cita real». **Existe** — está en DYCTEA, de
  21/09/2022, sobre créditos incobrables.
- De las cuatro referencias que declaré inexistentes, la única de la que se
  puede decir algo parecido es **00/02195/2019**, y ni siquiera: lo correcto es
  **«no consta en DYCTEA»**, que solo publica los criterios seleccionados. Una
  resolución puede existir sin criterio publicado.

**Y el error de bulto no era el que yo creía.** Pensaba que el problema del
guion de demostración era enseñar números falsos. Era peor: enseñaba **dos
números de consulta AUTÉNTICOS** pegados a una respuesta que no es la suya. Un
número inventado no lleva a ningún sitio; uno auténtico lleva a un documento
real que no dice lo que se le atribuye, y quien lo abra para comprobar se
encontrará otra cosa.

> **LA REGLA, ENTERA:** para afirmar que algo **existe**, hay que haberlo leído.
> Para afirmar que **no existe**, hay que haber mirado **la fuente** — PETETE o
> DYCTEA—, no nuestra copia. Y si solo se ha mirado la copia, lo que se puede
> decir es exactamente eso: **«no está en nuestra copia»**.

Es la misma frase que la ventana le dice al usuario desde la fase 27. Yo tardé
un día más que el código en aprenderla.

## ⚠️ UN INSTRUMENTO QUE SE EQUIVOCA EN SILENCIO CONTAMINA TODO

> **En los guiones de medición, NADA DE RESPALDOS que devuelvan algo cuando la
> consulta falla.** Que devuelvan cero o que revienten.

Un guion de medición comparaba `decision == "ENVIADO"` y el campo vale
`"enviado"`, en minúsculas. La lista salía **siempre vacía**. Y llevaba esto:

```python
claves = [d["clave"] for d in detalle if d.get("decision") == "ENVIADO"] \
         or [d["clave"] for d in detalle]      # ← el respaldo
```

El `or` convirtió un error de comparación en **un número plausible**: en vez de
medir lo que el corte envía, medía **todos los candidatos**. Salió «19 de 19
consultas mandan 6 preceptos», que contradecía una traza real donde el corte
mandó 3 de 5 — y esa contradicción es lo único que lo destapó.

**Sin el respaldo, la lista habría salido vacía y el error se ve al instante.**

Con ese guion se tomaron tres medidas del coste de subir el tope, y **las tres
eran el techo, no el coste**. Hubo que rehacerlas contra las **984
`seleccion.json` que hay en disco**, que es lo que el corte decidió de verdad y
no lo que un guion cree que decidió.

**Cuando haya datos reales guardados, se leen. Reproducir es el último recurso**,
y si se reproduce, se valida contra los datos reales antes de usarlo para
decidir: la reproducción arreglada da 47,4% de llenado sobre el banco frente al
37,3% real, misma forma, y por eso se pudo usar.

## ⚠️ EL CORTE POR PUESTO ES FRÁGIL, Y CADA NORMA LO EMPEORA

> **Ya ha pasado dos veces, y volverá a pasar.** No es mala suerte: es el
> mecanismo.

El buscador ordena por BM25 y se envían los N primeros. **El puesto de un
artículo no depende solo de él: depende de todos los demás.** Cada norma que
entra cambia el IDF de los términos, y dos documentos separados por décimas
intercambian el sitio.

| cuándo | qué se cayó | por qué |
|---|---|---|
| al ingerir la **LGT** | art. **89** LIVA, del puesto 3 al 5 | 335 preceptos nuevos |
| al ingerir **Sociedades** | art. **19** LIRPF, del 5 al 6 | 298 nuevos; lo desplazó **una disposición de la propia LIRPF**, por 0,2 puntos |

En los dos casos el artículo desplazado era **el que sostenía la respuesta**: el
89 es la rectificación de cuotas repercutidas; el 19, los gastos deducibles del
trabajo.

**SUBIR EL TOPE COMPRA MARGEN, NO RESUELVE LA CAUSA.** De 5 a 6 devuelve el
art. 19 hoy; a la cuarta norma volverá a caerse otro, y el tope no puede subir
indefinidamente sin diluir el material y pagarlo en cada consulta.

**La solución de fondo es la COBERTURA MARGINAL**, analizada y pendiente desde
hace días: en vez de cortar por puesto, seguir añadiendo preceptos mientras cada
uno aporte términos de la consulta que los anteriores no cubren, y parar cuando
el siguiente no añada nada. Un corte por lo que aporta no se mueve porque entre
una ley de otro impuesto.

### Mientras tanto: el tope sube de 5 a 6

**Decisión de Emili, el 11 de agosto de 2026**, y el motivo importa porque
contradice la letra de su propia regla.

La regla que se puso era: *«si el coste real es de unas pocas consultas, se
aplica; si es en todas, no»*. La medición dijo **13 de 19**, o sea dos tercios:
por la letra, no se aplicaba.

**Se aplicó igual, y con razón.** La regla suponía que el coste caería
**concentrado** en unas pocas consultas caras. Lo que la medición enseña es que
cae **repartido y pequeño**: +1.034 tokens de media, un **14%** más de material,
**siete décimas de céntimo** por consulta. Lo que importa es **el coste total
contra lo que compra**, no en cuántas consultas se reparte.

Y lo que compra es que un artículo que sostiene la respuesta deje de caerse: con
el tope a 5 la primera consulta de Renta enviaba **2 preceptos** y el artículo 19
—los gastos deducibles del trabajo, media pregunta— no llegaba; con 6 envía 3 y
entra, con cobertura 0,57.

**El argumento que lo cierra:** el corte descarta algo en el **62,7%** de las
consultas —medido sobre 984 selecciones reales—, así que subir el techo **no
inunda el material**. Solo ensancha **quién puede ser candidato**; el umbral
sigue decidiendo. De hecho ninguna consulta manda 6: la de Renta pasa de 2 a 3.

## ⚠️ LA CONDICIÓN 2 SE REVOCÓ, Y CONVIENE SABER POR QUÉ

Al ingerir Sociedades se puso una condición: *«las dos consultas de Renta siguen
funcionando; si baja, Sociedades no entra»*. **Bajó**, y aun así entró.

**Quien la revocó: Emili**, con el argumento de que la regla apuntaba a
**contaminación** —que artículos de Sociedades se colaran en respuestas de otros
impuestos— y se midió que **no la hubo: cero preceptos de IS en los diez
primeros** de esas consultas. Lo que hubo fue **reordenamiento estadístico**
entre vecinos de la misma norma, que es el mismo mecanismo que ya se aceptó al
ingerir la LGT.

Queda escrito porque una condición revocada sin dejar rastro es una condición
que la próxima vez no se pone. **La regla no era mala: apuntaba a lo que había
que vigilar y lo vigiló.** Lo que hizo falta fue distinguir entre las dos causas
posibles de que un número empeore.

## ⚠️ ABIERTO: LA NORMA QUE VA DETRÁS DE LA REFERENCIA

Anterior a la ingesta de Sociedades, y sin cerrar. **Para septiembre.**

El extractor de remisiones busca el nombre de la norma **delante** de la
referencia. Cuando el texto lo pone **detrás**, no lo encuentra y da la remisión
por interna:

```
«se añade una disposición adicional octava AL TEXTO REFUNDIDO de la Ley
 del Impuesto sobre Sociedades, aprobado por Real Decreto Legislativo 4/2004»
        → resuelve a la disposición adicional octava de la PROPIA LIRPF
```

Son cinco casos conocidos, todos en la disposición final segunda de la LIRPF, y
**estaban así antes de Sociedades** —comprobado contra el corpus de 7 cuerpos—.
Al ingerir el IS pasaron temporalmente a resolverse contra la Ley 27/2014, que
era peor; el arreglo del cualificador las devolvió al error anterior.

**Lo que se sabe:** las disposiciones no pasan por `_ambito`, que es donde vive
la regla de «lo que va delante y lo que va detrás». Hay que encontrar su camino
y aplicarles la misma propiedad. **Ante la duda, nada**: preferible pendiente
que interna falsa.

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

> **De dónde sale `V2092-15`:** no está en nuestra copia de la DGT. Aparece dentro del texto de dos criterios del TEAC que sí tenemos guardados —`00/03399/2023` y `00/05524/2024`—, que la citan. Es dato real de segunda mano, leído del material de trazas reales, no un número inventado. Queda anotado porque, sin esta nota, alguien podría buscarlo en `datos/dgt/` y no encontrarlo.

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

## La tapa del portátil, que es la que corta las tandas largas

La cadena de siembra se lanza así, y el `caffeinate` está a propósito:

```
caffeinate -i nohup ./cadena_siembra.sh 300 7 &
```

**`-i` impide que el Mac se duerma por inactividad. NO impide que se duerma al
cerrar la tapa.** Son dos cosas distintas y es fácil creer que `caffeinate` te
cubre las dos.

El 13 de agosto la tanda 3 arrancó a las 11:52 y a las 20:31 llevaba **87
minutos de trabajo real**: siete horas dormida con la tapa cerrada. No se
perdió nada —la siembra guarda el avance y retoma donde iba, que es para lo que
está—, pero una cadena de siete tandas que debía acabar por la tarde seguía
viva de madrugada.

> **Si dejas una cadena corriendo, deja el portátil ABIERTO.** Con la tapa
> cerrada no hay bandera que valga: `-i` no cubre eso.

Si algún día hace falta cubrirlo de verdad, es `sudo pmset disablesleep 1` —y
hay que acordarse de deshacerlo—. Para lo que hacemos, dejar la tapa abierta es
más simple y no deja el equipo tocado.

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

> **REVERTIDA EN PARTE POR LA FASE 21.** El interruptor global —`--solo-ley` /
> `--con-criterio`, `modo.json`, la guía por modo— **ya no existe**: los dos
> botones están siempre en la ventana y el modo lo elige quien pulsa. Lo que
> sobrevive de esta fase es lo que de verdad valía: que la guía sea un fichero
> generado con marca dentro, y que **si la hoja de la mesa no dice lo mismo que
> la pantalla, el agente no abre**. Se deja escrito entero porque el camino
> importa: el interruptor fue el paso intermedio necesario para descubrir que
> lo que sobraba era el interruptor.

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


---

# FASE 21 · TODO EN LA VENTANA, SIN TERMINAL

Es para enseñar el MVP. **No se puede abrir una consola delante de nadie**: una
herramienta que necesita terminal para algo no está entregada, está en obras.

## 1 · Los dos botones, siempre

En la fase 20 el segundo botón existía solo si `configurar.py --con-criterio`
lo había encendido. La idea era buena —la decisión de gastar es del despacho,
no de quien consulta— pero **el sitio era el equivocado**: para tomarla había
que editar un fichero, y eso es exactamente lo que no se puede hacer delante de
nadie.

Ahora **los dos botones están siempre**, y si el despacho decide que solo se use
la ley, eso se decide **en la propia ventana**: no pulsando el segundo. La
decisión sigue siendo suya; lo que ha cambiado es que ya no hace falta un
informático para ejecutarla.

Lo que se ha ido con ello:

| se va | por qué |
|---|---|
| `modo.json` | un estado global que ya no decidía nada |
| `guardar_modo` · `hay_boton_criterio` · `textos_con_criterio` | lo mismo, en funciones |
| `guias/GUIA.solo-ley.md` · `guias/GUIA.con-criterio.md` | una sola guía: describe los dos botones **siempre** |
| `configurar.py --solo-ley` / `--con-criterio` | no queda nada que encender |
| `AGENTE_DGT_TEXTOS` | los textos ya no dependen de una variable, sino del botón pulsado |

**Se ha quitado, no dejado sin efecto.** Un interruptor que ya no interrumpe
nada es peor que no tenerlo: el siguiente que lo lea creerá que manda.

`configurar.py` se queda, pero solo como mirador: dice qué hay dentro y
regenera la guía. Lo mismo está en la ventana; esto es para Emili.

## 2 · «Qué hay dentro»: la pantalla de estado

Lo que daba `configurar.py --estado` en una consola, ahora en la ventana, en un
botón discreto al lado del de consultar. **Es lo que se enseña para decidir si
se enciende el criterio**, así que cabe de una vez y se lee sin explicaciones:

- **normas cargadas** y cuántos artículos cada una — 722 en total;
- **la copia local**: 241 consultas de la DGT, 7 del TEAC, 2 de tribunales
  regionales;
- **lo que cuesta cada botón**: 0,13 € y 0,22 €, medidos sobre trazas reales;
- **el canario**: si Tributos y DYCTEA responden ahora mismo, con la nota de que
  una fuente caída **no impide consultar** —las respuestas salen siempre de la
  copia local— solo impide ampliarla.

Ni una ruta de fichero, ni una variable de entorno, ni un `.json`. Comprobado en
la suite: si se cuela cualquiera de las tres, sale rojo.

## 3 · Que se vea la diferencia entre los dos botones

Sin esto, comparar los dos botones exige leerse las dos respuestas enteras y
compararlas a ojo, y eso no lo hace nadie. Así que la diferencia se dice, en una
línea y con números, justo debajo del estado:

- **el criterio ha aportado algo** → «Lo que ha añadido el criterio: 2 consultas
  de la DGT y 1 resolución, citadas y comprobadas una a una», con las
  referencias debajo;
- **había criterio delante y no sostiene nada** → «Se le pusieron delante 5
  consultas y 1 resolución, y NINGUNA sostiene la respuesta: esta duda la
  resuelve la ley sola». Es un resultado, no un fallo, y merece decirse: el
  segundo botón ha trabajado y la conclusión es que no hacía falta.

Y el **texto del estado también cambia según el botón**. El código calcula
`CRITERIO CLARO` igual en los dos casos, pero no significa lo mismo: uno hecho
solo con la ley no ha mirado qué opina Hacienda, y **decirlo igual que el otro
sería dar por mirado lo que no se ha mirado**. Son seis frases, dos por estado.

## 4 · La despensa vacía no es una avería

Es lo primero que le va a pasar a cualquiera que pruebe una pregunta al azar:
**241 consultas no cubren el IVA entero**, y hay doscientas mil publicadas. Si
eso se dice con las palabras de un fallo, se lee como un fallo, y el segundo
botón queda marcado como «el que no funciona».

> *«No hay respaldo suficiente en la ley, y en la copia guardada todavía no hay
> criterio sobre esto. La copia se llena poco a poco: que no esté no quiere
> decir que no exista. Abajo tienes los artículos encontrados.»*

La suite comprueba que esa frase **no contiene** «error», «fallo», «avería» ni
«no se ha podido», y que sí dice «todavía» y «no quiere decir que no exista».

## 5 · Qué obliga todavía a abrir una consola

**Para el despacho: nada.** Abrir, instalar en el primer arranque, meter la
clave, consultar con o sin criterio, ver qué hay dentro, copiar la respuesta y
comprobar el equipo cuando algo va raro — los siete tienen doble clic o botón.

**Para Emili sí, y se deja a propósito**, porque son tareas de mantenimiento que
se hacen una vez cada mucho y no delante de nadie:

| tarea | cómo | ¿debería tener ventana? |
|---|---|---|
| llenar la despensa (`sembrar.py`) | terminal | **es la candidata seria**: es lo único de esta lista que cambia lo que ve el despacho |
| reingerir el corpus cuando cambie la ley (`fase1`/`fase2`) | terminal | no: cambia la ley dos veces al año y hay que mirar el diff |
| bancos y suites (`banco.py`, `fase3 probar`, `pruebas/`) | terminal | no: son de desarrollo |
| ver qué hay dentro / regenerar la guía (`configurar.py`) | terminal | ya está en la ventana; esto es el atajo |

**Un caso frontera, dicho porque lo es:** si la credencial caduca, la ventana
dice «Falta la configuración. Avisa a Emili» y ahí se acaba para el despacho.
Eso es deliberado —la clave no la toca el departamento— pero significa que
**arreglarlo es de Emili y hoy no tiene doble clic**. No es un fallo de la
entrega tal como está definida; es una decisión, y queda escrita para poder
cambiarla si estorba.

## 6 · Qué ha cambiado en la coherencia ventana/guía

Esta es la parte que había que rehacer, porque `configurar.py` deja de mandar.

Antes `revisar()` comparaba **cuatro piezas contra un modo**: fuentes, textos,
guía y valor por defecto. Tres de las cuatro han dejado de existir, así que
comparar se quedó sin objeto.

Pero **la coherencia que importaba nunca fue esa**. Era: *¿dice la hoja impresa
lo mismo que la pantalla?* El papel se imprime, se queda en la mesa y no se
entera de que el código ha cambiado. Así que `revisar()` hace ahora **una sola
cosa, y es la que faltaba**: comprobar que **todas** las frases de
`interfaz.TEXTOS_DE_ESTADO` están dentro de `GUIA.md`, letra por letra
—insensible a tildes, porque la ventana va en ASCII y la guía impresa no— y se
ejecuta **al arrancar**, tanto en la ventana como en la terminal.

Eso era justo lo que cubría `prueba_textos_guia`, una de las catorce suites
perdidas, y que estaba anotada como **«nadie comprueba que las frases de la
ventana estén dentro de la guía»**. Ya no es una suite que hay que acordarse de
lanzar: es una condición de arranque.

**Y encontró dos descuadres reales en cuanto se encendió.** Las variantes de
`CRITERIO CLARO` y `CRITERIO DISCUTIDO` para el botón de ley sola no estaban en
la guía: la guía solo describía las de tres fuentes. Alguien con la hoja delante
habría leído una frase distinta de la que tenía en pantalla. Se reescribió la
sección «Los tres estados» para dar **las dos variantes de cada estado, una por
botón**.

## Comprobaciones

```
9 suites .......................... verdes (438 comprobaciones)
fase3.py probar ................... 37/37
fase4.py comprobaciones ........... 5/5
banco.py --motor ensayo ........... 16/19 · los 3 rojos son los de siempre,
                                    de ordenación, sin cambio de veredicto
llamadas a la API de Anthropic .... 0
```

`prueba_configurar` se ha reescrito entera: protegía un interruptor que ya no
existe. Ahora protege que **los dos botones no dependan de ningún fichero** y
que una frase de la ventana fuera de la guía impida abrir. Su control negativo
vacía `TEXTOS_DE_ESTADO` y comprueba que, sin la comprobación, una guía rota
pasaría por buena.

**Y una trampa que casi vuelve a colar:** el control negativo mutaba el módulo
`interfaz` que tenía la prueba en la mano, pero `revisar()` hace `import
interfaz` por dentro y la suite había vaciado `sys.modules` tres veces por el
camino. Eran **dos objetos distintos**: la mutación no llegaba, y la prueba
salía en rojo diciendo «la mutación no ocurrió» — que es exactamente para lo que
se puso ese mensaje. Se coge el módulo de `sys.modules` en el momento de mutar.

---

# FASE 22 · EL MODO OSCURO, Y LO QUE HACÍA QUE LA VENTANA SE VIERA MAL

La maqueta traía tres modos y se había aplicado «papel claro». Se pidió el
**oscuro —negro y lila—** desde el principio. Esta fase lo aplica y, de paso,
arregla lo que hacía que la ventana pareciera vieja aunque los colores fueran
buenos: **no eran los colores, era el espacio.**

## 1 · La paleta

El negro no es negro: `#0F0E13` lleva una gota de violeta. Un `#000000` puro
con texto blanco encima vibra y cansa a los diez minutos, y aquí se leen
párrafos de ley enteros. Las tres superficies se separan **por claridad, no por
bordes**: fondo → panel → campo, cada una un escalón más clara.

```
#0F0E13  fondo de la ventana          #EDECF2  texto principal
#17161D  panel: lectura y respuesta   #A19DB0  texto secundario
#1F1D28  campo: la duda y el año      #8B87A0  rótulos menudos
#2B2937  bordes                       #C0A5FF  el lila: acento y botón
                                      #C8B0FF  enlaces y citas pinchables
```

**Los grises están medidos, no elegidos a ojo.** Sobre negro es muy fácil
pasarse de apagado. El primer `TINTA3` daba **3,8:1** contra el panel y el
mínimo para texto menudo es 4,5:1 — se subió hasta 5,2:1. Los diez pares:

| | contraste | |
|---|---|---|
| texto principal sobre panel | 15,3:1 | |
| titular sobre el fondo | 16,4:1 | |
| texto en la caja de la duda | 14,1:1 | |
| enlace sobre panel | 9,5:1 | el producto: el más legible después del estado |
| tinta sobre el botón lila | 9,0:1 | |
| estado CRITERIO CLARO | 8,6:1 | |
| estado CRITERIO DISCUTIDO | 7,2:1 | |
| texto secundario | 6,8:1 | |
| estado NO ENCONTRADO | 6,3:1 | |
| rótulos menudos | 5,2:1 | era 3,8:1 |

Los tres estados **suben** de claridad respecto al modo claro —sobre negro manda
el claro, no el oscuro— pero la relación entre ellos no cambia: **mismo brillo,
croma decreciente**. Del lila al gris pasando por un lila apagado. Ni un rojo,
ni un ámbar, ni un verde en toda la pantalla.

## 2 · Lo que hacía que se viera mal

### El espacio, que es lo que más se nota

Los huecos estaban elegidos uno a uno —6 aquí, 11 allá, 14 más allá— y la falta
de ritmo se ve aunque no se sepa nombrar. Ahora hay **una escala y todo sale de
ella**: unidad 8, margen exterior 32, entre bloques 24, dentro de un bloque 16,
relleno de tarjeta 24. Los botones pasan de `padx=16 pady=4` a **26×12**: un
botón apretado parece deshabilitado aunque no lo esté.

### La jerarquía: seis tamaños, no dos

```
22 titular  ·  16 estado  ·  15 cita (serif)  ·  12 respuesta
11 interfaz ·  10 referencia (mono)  ·  9 rótulo
```

El titular pasó de 17 a 22 y el estado de 15 a 16, **pero lo que importa es la
distancia entre escalones**. Y la cita sigue siendo lo más grande después del
estado, en serif, porque es el producto.

### Los widgets por defecto

Un botón de tkinter trae relieve biselado, fondo del sistema y borde de tres
píxeles. Se estila todo con `ttk` y se **fuerza el tema `clam`**, que es el
único que deja cambiar fondo y borde de verdad en los tres sistemas: en Mac el
tema `aqua` ignora el color de fondo de los botones —los pinta el sistema— y en
Windows `vista` hace lo mismo. **Sin cambiar de tema, todo esto no habría hecho
nada y no se habría notado hasta verlo en la otra máquina.**

Tres estilos, y la diferencia entre ellos es la jerarquía: `Primario` lila
lleno, `Segundo` con contorno, `Discreto` sin fondo ni borde. Cursor de mano en
todo lo pinchable — es la señal más barata que existe de «esto responde», y
tkinter no la pone sola.

### El tamaño de ventana

Abría en `minsize(880, 640)`, o sea **en el suelo**: enseñaba su peor caso. Ahora
abre en 1180×880 y el mínimo baja a 920×700.

### El ancho de línea

Un párrafo de ley a lo ancho de un monitor de 27 pulgadas es ilegible: el ojo
pierde el renglón al volver. **tkinter no tiene `max-width`**, así que se
calcula: se mide cuánto ocupan 88 caracteres *con la fuente que de verdad se ha
elegido en esta máquina* y lo que sobra se reparte a los lados como margen
interior. La columna se queda quieta y lo que crece son los lados.

| ventana | línea de lectura |
|---|---|
| 900 px | 724 px (la ventana no da para más) |
| 1180 px | **744 px** |
| 1600 px | **744 px** |
| 2200 px | **744 px** |
| 3000 px | **744 px** |

**Dos defectos que solo aparecieron al medirlo**, y que no se habrían visto
mirando la pantalla:

1. La columna salía a **696 px en vez de 744**: no se descontaba el relleno
   propio de la caja, que ya es margen.
2. Había un **tope al margen** (220 px) y en un monitor de 2200 px la línea
   volvía a irse a 1648. Un tope al margen es un tope a lo que se quiere fijar,
   mirado del revés. Se quitó.

## 3 · La expectativa que hubo que tocar, y por qué

Una sola, y la digo entera porque la regla es no tocarlas:

```python
comprobar("NO ENCONTRADO va en gris, no en rojo",
          interfaz.COLOR[EST.NO_ENCONTRADO].lower() in ("#4a4a55", "#4a4a55"))
```

Estaba atada al **hex del modo claro**. Sobre el fondo oscuro ese gris da
**2,2:1**: ilegible. La elección era gris ilegible o tocar la prueba.

Ninguna de las dos, porque **el literal no era la expectativa**. La expectativa
es que no sea un color de alarma. Así que ahora se comprueba eso: que los tres
canales estén casi igualados (croma ≤ 30), que no tire a rojo ni a ámbar, y que
tenga contraste suficiente contra su fondo. Es **más estricto que antes** —caza
un rojo, un ámbar y un verde, no solo un hex distinto— y sobrevive al siguiente
cambio de paleta, que es lo que tiene que hacer una prueba de diseño.

Verificado rompiéndola: con `#CC2222` y con `#E8A317` sale roja; con el gris
viejo `#4A4A55` **también**, por el contraste. El umbral está puesto por encima
de ese caso a propósito.

## 4 · Lo que tkinter NO puede, y no es negociable

Se pide una vez y se deja escrito para no volver a intentarlo:

- **esquinas redondeadas** — no existen en widgets; solo dibujando a mano en un
  Canvas, y entonces deja de ser un widget (sin foco, sin teclado, sin estados);
- **sombras** y **degradados** — no hay;
- **transiciones y animaciones** — solo moviendo a mano con `after()`, y se ve
  a tirones;
- **opacidad por widget** — solo la ventana entera;
- **tipografía fina**: no hay interletraje. Las versalitas del rótulo
  (`D E P A R T A M E N T O   F I S C A L`) están espaciadas **a mano con
  espacios**, que es el único modo;
- **la barra de desplazamiento** se estila pero no se puede adelgazar por
  debajo de lo que dicta el tema.

Lo que sí se ha podido: color de todo, tres superficies, bordes de un píxel,
relieve plano, cursor de mano, tipografía por familia y tamaño, y el ancho de
lectura calculado.

## Comprobaciones

```
9 suites ............... verdes · 440 comprobaciones (136 de la ventana)
fase3.py probar ........ 37/37
fase4.py comprobaciones  5/5
llamadas a la API ...... 0   (todo con --motor ensayo)
```

**No hay captura de pantalla en este informe**, y hay que decir por qué:
`screencapture` en esta sesión devuelve solo el escritorio —le falta el permiso
de Grabación de Pantalla— así que la foto no probaría nada. Lo que sí está
medido es el árbol de widgets ya dibujado: tema `clam` activo, los cuatro
botones con su estilo y su cursor, las siete fuentes resueltas
(Helvetica Neue / Georgia / Menlo en este Mac) y la columna de lectura en las
cinco anchuras de la tabla. Para verlo:

```
python interfaz.py --motor ensayo
```

---

# FASE 23 · LA RESPUESTA NO SE PODÍA LEER

Bloqueante, y lo causó el ancho de lectura de la fase anterior. Se arregla y se
deja medido, porque **ninguno de los tres defectos se veía mirando la pantalla**:
había que preguntarle a los widgets cuánto pedían.

## El diagnóstico

| lo que pasaba | la medida |
|---|---|
| la respuesta se quedaba en **dos líneas** | el `Text` sin medidas pide 80×24 caracteres → **816 px**; la ventana pedía **1608 px** de alto y abría en 880, así que a la respuesta le tocaban **88 px** |
| no había forma de agrandar para verlo | la ventana ya pedía más de lo que cabe en la pantalla |
| el ancho de lectura peleaba con el gestor de ventanas | se hacía con `padx`, y **el relleno cuenta para el tamaño que el widget pide**: más ventana → más margen → más pedía |
| los avisos se dibujaban fuera y sin salida | con el art. 80 puesto, la columna pide **604 px** y quedaban **322**. El texto tenía barra propia; los avisos, no |

Lo último es lo grave: **los avisos son justo lo que puede invalidar la
respuesta**, y estaban donde no se podía llegar.

## Los arreglos

**`width=1, height=1` en el `Text`.** Pidiendo lo mínimo, la ventana pide lo que
ocupa el formulario (1608 → **917 px**) y la respuesta se queda con lo que sobre.

**El ancho de lectura pasa de `padx` a márgenes de etiqueta** (`lmargin1`,
`lmargin2`, `rmargin`). Un margen de etiqueta es solo sangrado de dibujo: no
cuenta para nada. La ventana se maximiza entera y el párrafo se queda quieto.

```
ventana 1000 px → margen 70 px      ventana 1400 px → margen 270 px
ventana 1710 px → margen 425 px     el párrafo, siempre 744 px
```

Y se corrigió un segundo error ahí: el margen se calculaba con
`texto.winfo_width()`, que durante un `<Configure>` devuelve **el ancho de
antes**. Salía 391 px en una ventana de 1000 y 70 px en una de 1400 — al revés.
Ahora se calcula del ancho de la ventana, que ya se sabe.

**Un solo scroll para toda la columna de resultado.** Estado, aporte, avisos y
respuesta van dentro de un lienzo desplazable. No queda nada fuera de alcance, y
lo que se queda quieto es el formulario, que es lo que se pidió. El texto crece
hasta ocupar lo que ocupa: se cuentan las **líneas dibujadas** —no los párrafos,
porque importa cómo ha quedado el ajuste al ancho de ahora— y se le da ese alto.

**Rueda, en los tres sistemas y sobre cada panel.** Mac `<MouseWheel>` con delta
pequeño, Windows `<MouseWheel>` en múltiplos de 120, Linux `<Button-4>/<5>` sin
delta. Y atada a **cada etiqueta**, no solo al lienzo: la rueda la recibe el
widget que está debajo del ratón, y debajo del ratón casi siempre hay una
etiqueta. Sin recorrer los hijos solo habría funcionado en los huecos.

**Teclado**: flechas, AvPág/RePág, Inicio/Fin. **Respuesta nueva vuelve arriba**
—si no, una corta detrás de una larga aparece en blanco y se lee como que no ha
contestado—. **La barra se esconde** cuando no hay nada que desplazar.

## Y los otros dos sitios, que tenían el mismo fallo

Se pidió repasarlos y resultó que no era teoría:

| | pedía | abría a | se salía por |
|---|---|---|---|
| **«Qué hay dentro»** | 949 px | 620 px | **329 px**, sin barra |
| **Descoordinación**, peor caso (las seis frases fuera de la guía) | 643 px | 520 px | **123 px** |

Los dos arreglados con el mismo patrón, sacado a `_desplazable()`. Los tres
tenían en común que **lo que contienen no tiene tamaño fijo**: depende de
cuántos avisos haya, cuántas normas estén cargadas o cuántas frases falten. Un
alto fijo para contenido variable es una apuesta, y se pierde el día que hay uno
más.

## La captura que no hay

`screencapture` en esta sesión devuelve el escritorio, byte a byte idéntico
entre ejecuciones, y `System Events` **no ve ninguna ventana** del proceso de
Python. No es el permiso de grabación: es que la ventana no llega al servidor
gráfico desde aquí. Lo medido sobre el árbol de widgets, maximizada:

```
ventana 1710x1027 · columna de resultado 3723 px · respuesta 101 líneas
párrafo 744 px con 425 px de margen a cada lado
se llega al final en 10 páginas · la última línea se dibuja
el formulario no se mueve: 83 px
```

Para verlo: `python ver_ejemplo.py`, que carga la respuesta real del art. 80 con
las tres fuentes y lo dice en la cinta de arriba —**no es una consulta**, es un
texto que ya pasó el verificador en su día.

## Comprobaciones

```
9 suites ....... verdes · 487 comprobaciones (183 de la ventana)
llamadas a la API .. 0
```

Bloques nuevos: **11**, la respuesta larga de verdad (rueda por sistema y por
panel, teclado, vuelta arriba, selección, de arriba a abajo maximizada y sin
maximizar, y que el ancho de lectura no impida maximizar); y **12**, el control
negativo: se le devuelve al texto el alto de fábrica y se comprueba que la
última línea deja de dibujarse.

**Dos trampas de la propia prueba**, anotadas porque volverán:

1. Sin ventana **activa**, Tk no entrega eventos de teclado a nadie y
   `event_generate` se pierde en silencio. Medido: `focus_get()` vuelve a `None`
   después de la primera tecla. Sin `focus_force()` dentro del bucle, la suite
   habría dado por buenas cinco teclas de seis.
2. Un `<Configure>` pendiente recuenta el alto del texto y **mueve la vista**
   entre el evento y la comprobación. Se dejó la vista en un punto conocido
   antes de cada medida — y de paso se arregló en el código: reajustar guarda
   dónde se estaba leyendo y vuelve, para que arrastrar el borde no dé saltos.

---

# FASE 24 · DOS VISTAS, Y EL CUERPO DE TEXTO DE UNA HERRAMIENTA DE TRABAJO

## 1 · El problema de fondo no era el espaciado

La pregunta y la respuesta compartían pantalla. El formulario ocupaba **380 px
fijos** que la respuesta no podía usar, así que por mucho que se afinaran los
márgenes la respuesta se quedaba en media ventana. **Sobraba una de las dos
cosas en cada momento.**

- **Vista de consulta**: la pregunta, el año y los dos botones. Centrada, con
  aire, y nada más. Como ya no le quita sitio a nadie, la caja de la duda
  recupera sus cuatro líneas.
- **Vista de respuesta**: la ventana entera. Barra fina arriba con «← Nueva
  consulta», la pregunta y el año, y el expediente; debajo, el estado, los
  avisos y el texto.

Las dos viven en la misma celda y se turnan con `grid()`/`grid_remove()`. **Nada
se destruye al cambiar**, y por eso «Nueva consulta» devuelve la pregunta tal
cual con el año seleccionado: casi nunca se cambia la duda entera, se cambia el
año. Devolver la caja en blanco obliga a reescribirla, y quien la reescriba de
memoria no escribirá exactamente lo mismo — con lo cual ya no está comparando
dos respuestas a la misma pregunta.

## 2 · Los tamaños, en puntos

| | antes | ahora |
|---|---|---|
| **cuerpo de la respuesta** | 12 pt | **15 pt** |
| **citas** (serif) | 15 pt | **17 pt** |
| referencias y URL (mono) | 10 pt | **12 pt** |
| rótulo del estado | 16 pt | **19 pt** |
| titular | 22 pt | **24 pt** |
| interfaz (botones, campos) | 11 pt | **13 pt** |
| menuda | 10 pt | **11 pt** |

**Interlineado**, que en texto jurídico denso se nota más que el cuerpo: 7 px
entre líneas del mismo párrafo (`spacing2`), 9 px antes de cada párrafo y 18 px
detrás. Alto de línea real: **31 px** para un cuerpo de 15 pt.

**Aire alrededor de las citas**: 24 px por arriba y por abajo. Una cita pegada
al párrafo siguiente se lee como parte de él, y entonces deja de ser una cita.

**Márgenes**: 24 px de relleno interior en el texto, más el margen de la columna
de lectura, que a pantalla completa son 393 px a cada lado.

## 3 · Medido, no mirado: veinte líneas

El listón era ese, y llegar costó cuatro intentos. Con el art. 80 cargado y la
ventana maximizada a 1710×1027:

```
banda de arriba   249 px   (estado 169 + aporte 70 | avisos 163)
visor del texto   679 px
alto de línea      31 px
LÍNEAS VISIBLES SIN DESPLAZAR:  20
```

Se partía de **12**. Lo que las trajo, en orden de rendimiento:

1. **El estado y los avisos, en dos columnas.** Apilados se comían 392 px de
   alto mientras sobraban 900 px de ancho a los lados del párrafo sin hacer
   nada. En dos columnas —lo encontrado a la izquierda, lo que falta por mirar
   a la derecha— la misma información ocupa la mitad. Por debajo de 1150 px de
   ancho se vuelven a apilar.
2. **El texto con visor propio.** Antes toda la columna se desplazaba junta, así
   que el estado y los avisos se llevaban los primeros 470 px de la vista.
   Ahora el bloque de arriba es fijo —se lee una vez— y el texto se queda con
   lo que sobra.
3. **El expediente a la barra de arriba.** Tuvo fila propia arriba y abajo, y en
   las dos costaba 28 px: una línea entera de respuesta por un dato que se mira
   una vez al mes.

**¿Y si hay muchos avisos?** No queda nada inalcanzable, y está medido: sobre
**864 consultas reales el máximo son cuatro avisos**, y en 820 de ellas ninguno.
Si algún día fueran muchos, el bloque de arriba se queda entero —grid sirve
primero a las filas sin peso— y lo que se encoge es el visor del texto, que
tiene barra.

### Cuatro cosas que solo aparecieron midiendo

- **`uniform` no es decorativo.** Sin él, `weight` reparte solo el *sobrante*
  por encima de lo que cada columna pide, así que la columna que pide poco se
  queda pequeña para siempre: los avisos se envolvían a **209 px** dentro de una
  banda de 1650.
- **El ancho se pregunta, no se calcula.** Tres intentos de deducirlo («la
  columna es el 60 %, menos el relleno, menos el rótulo») y los tres dieron de
  menos: 642 px cuando había 771, y una línea de más. Ahora se le pregunta al
  panel, que ya sabe lo que mide.
- **El rótulo del estado se partía en tres líneas** por un `wraplength` puesto a
  ojo, y eso subía el panel 60 px.
- **Apilado ocupa menos que en horizontal.** Con el rótulo al lado, se come
  320 px de ancho y la explicación se parte en cuatro líneas; con el rótulo
  encima, la explicación tiene la columna entera y se queda en tres. Justo lo
  contrario de lo que parece.

Y la columna de lectura, corregida: la fórmula seguía restando los márgenes de
la vista antigua y daba margen cero, con el párrafo a 837 px en una ventana de
1180. Ahora **821 px fijos** de 1180 a 1710 de ancho.

## 4 · Las expectativas que hubo que reescribir

Tres, todas por la misma razón —comparaban números de fila de `grid`— y las tres
sustituidas por algo **más estricto y que no depende del montaje**:

- «los avisos van arriba, antes del texto» → se compara la **posición real en
  pantalla** (`winfo_rooty`), que es lo que ve una persona;
- «el aporte, entre el estado y los avisos» → igual;
- «el formulario se queda como estaba» → ya no hay formulario en esa vista: se
  comprueba que la vista de consulta **no está**.

Y `prueba_no_encontrado` leía la traza de `v.pie`, que ahora es el pie de la
*otra* vista. Pasa a `v.pie_respuesta`.

**El control negativo también es nuevo**: se le quita a la fila del texto el
peso que la hace crecer —que es lo que la dejaba en dos líneas— y se comprueba
que el bloque de las veinte líneas lo caza. Verificado: sin peso, **1 línea**.

## Comprobaciones

```
9 suites ....... verdes · 510 comprobaciones (206 de la ventana)
fase3 · fase4 .. 37/37 · 5/5
llamadas a la API .. 0
```

```
python ver_ejemplo.py     abre MAXIMIZADA y directamente en la vista de
                          respuesta, con el art. 80 y las tres fuentes
```

**Una piedra que ya llevo tres veces:** el `pady`/`padx` de un *widget* es UNA
distancia, no una pareja. `padx=(0, 24)` en un `Label` revienta con «expected
screen distance but got "0 24"». La pareja va en el `grid`/`pack`, no en el
widget. Está escrito en el código desde la fase 12 y he vuelto a caer.

---

# FASE 25 · UNA CITA FALSA EN EL MATERIAL DE DEMOSTRACIÓN

## Lo que pasó

`ver_ejemplo.py` pintaba el texto **real** del expediente 20260805T224913 —que
sí cita V0160-23 y V0041-07— rodeado de metadatos que **escribí yo a mano**:

| | el ejemplo enseñaba | el expediente dice |
|---|---|---|
| aporte DGT | `V2759-21` | *(no existe esa consulta)* |
| en el material | `V2759-21`, `V0187-20` | V0160-23, V0053-13, V0041-07 |
| resolución | `00/02195/2019` | *(no existe)* |
| señal | «hay criterio de años distintos» | «…**V0160-23** (2023) es la que manda; **V0041-07** es anterior y puede estar superada» |
| preceptos | 80, 89, 24 (Reglamento) | 80, 24 |
| cobertura | una línea sobre doctrina del TEAC | ninguna |

**Tres referencias con formato de cita real, las tres inventadas.** Y de paso
tapaban las dos auténticas: la señal verdadera las nombra, la mía no. De ahí que
pareciera que el criterio de la DGT había dejado de funcionar.

## Lo que NO pasó: no hay regresión

Comprobado entero, sin gastar una llamada:

1. **Las tres siguen en la copia local** (241 consultas): V0160-23, V0053-13,
   V0041-07.
2. **La búsqueda las devuelve en los puestos 1, 2 y 3**, con cobertura 1,00
   (5 de 5 términos). El cuarto baja a 0,80. `buscar(tope=3)` devuelve
   exactamente esas tres.
3. **Nadie las descarta.** Relanzada hoy con `--motor ensayo`, el
   `recorte_criterio.json` dice `consultas_con_texto_en_el_material: V0160-23,
   V0053-13, V0041-07`. Las mismas que el 5 de agosto.
4. **No hay umbral contra el que comparar**: en el camino de la DGT el único
   corte es `tope=3`. `UMBRAL_ASUNTO = 0,20` vive en `teac.py`.

**Y el filtro de materia y asunto nunca tocó la DGT.** El commit que lo
introdujo (`3b963e6`) modificó `modelo.py`, `redactor.py`, `referencias.py`,
`teac.py` y `fase4.py` — `dgt.py` no está en la lista, y no hay ninguna llamada
a `materia_ajena` ni a `cobertura_asunto` fuera de `teac.py`. Como `dgt.py` no
cambió, «antes del filtro» y «ahora» son el mismo código.

## El arreglo

`ver_ejemplo.py` **no escribe ni un dato**. Lee el `resultado.json` del
expediente y pinta lo que hay; si un campo no está, no se pinta y se dice por la
terminal. Lo que el expediente no guardaba se **reconstruye de sus propias
medidas**, no se inventa:

- la **respuesta** ← el último `borrador_N.txt` cuya `verificacion_N.json` diga
  `ACEPTADO`. Si ninguna lo dice, no se enseña texto: la regla de no mostrar
  texto sin verificar vale igual para un ejemplo;
- el **aporte** ← las citas `VERIFICADA` de `verificacion_N.json` y las fuentes
  de `recorte_criterio.json`;
- **con qué se hizo** ← si hubo `recorte_criterio.json`, hubo criterio.

Comprobado: el aporte que se pinta (`V0041-07`, `V0160-23`) coincide **exactamente**
con lo que cita el texto. Y acepta un identificador por argumento, así que sirve
para mirar cualquier expediente.

## La auditoría del resto del proyecto

### Encontrado y arreglado

**`GUIA.md` — la hoja que se imprime y se deja en la mesa.** El ejemplo de
formatos de cita mostraba `{Resolucion del TEAR de Cataluña 08/02042/2022/00/00}`,
que no estaba en nuestra copia local. Sustituida por `07/02872/2023/00/00, de
29/04/2025`, que sí está y por tanto se puede comprobar sin salir a la red.

> **CORRECCIÓN (fase 28).** Aquí escribí que esa resolución **«no existe»**, y
> es falso: **existe**. Es una resolución real del TEAR de Cataluña de
> **21/09/2022** sobre créditos incobrables, y aparece en DYCTEA en cuanto se
> busca por ese concepto. Lo único que comprobé fue que no estaba en nuestra
> copia. **El cambio se queda; la razón era falsa.** Ver «Las dos caras de la
> misma comprobación», al principio de este documento.

Y un defecto de paso: **el sistema no sabe escribir «TEAR de Cataluña»**.
`etiqueta_de` no tiene mapa de unidades y produce «Resolucion del 07». El
ejemplo enseñaba un formato que el propio agente no puede emitir.

**`agente_fiscal/redactor.py`** llevaba la misma cita en un docstring
—era el origen de la de la guía—. Verificado que **no llega al prompt**: no está
en `SISTEMA`, es documentación para quien lea el código. Corregida igual.

### Encontrado y correcto, dicho para que conste

- **`V1601-22`** (petete.py, LEEME, redactor, dgt, citas, FASE9): **existe**, y
  la fecha citada `01/07/2022` es la suya. Es una consulta de IRPF y se usa como
  ejemplo del formato de PETETE. Bien.
- **`00/06614/2024/00/00, de 21/05/2026`** en la guía: existe, fecha correcta.
- **`V0047-24`** en `prueba_normativa`: **es real**, con su normativa real
  (`RIRPF, RD 439/2007, art. 22`). Es el caso que costó la fase 6 y está bien
  que la suite use el de verdad.
- Las cifras de la ventana —241 consultas, 7 del TEAC, 2 regionales, 722
  preceptos, 0,13 € y 0,22 €— salen de contar la copia local y de trazas
  medidas.

### Encontrado, sin arreglar, y por qué

- **`V2092-15`** aparece dos veces en el LEEME. No está en nuestra copia de la
  DGT, pero **sí aparece en el material de trazas reales**: es una consulta que
  citan dos criterios del TEAC, y por eso se usó como ejemplo. Es dato real de
  segunda mano, no invención. Convendría anotar de dónde salió.
- **La serie `9xxx` funciona como marca de fixture sintético** (`V9001-22`,
  `V9999-99`, `00/09001/2024`, `08/09003/2022`) y las carpetas llevan su
  `LEEME.txt` diciendo que están inventadas. **Pero la convención numérica no
  estaba escrita en ninguna parte**: alguien podía añadir un fixture con un
  número realista sin saltarse ninguna regla. Ahora está en la regla de arriba.
- `prueba_recorte` y `prueba_normativa` usan números inventados fuera de la
  serie `9xxx` (`V0001-23`, `V0100-24`…). No salen de la carpeta de pruebas y no
  se enseñan, pero no siguen el convenio. Lo dejo dicho.

## Comprobaciones

```
9 suites .......... verdes
llamadas a la API ... 0
```

Y una trampa de la propia prueba, cazada al repetirla: `event_generate` encola
el evento por defecto (`when="tail"`), así que **una de cada cinco veces** la
rueda de una comprobación llegaba después de recolocar la vista y la empujaba al
revés. Con `when="now"` se entrega en el acto. Seis ejecuciones seguidas en
verde. Una prueba que falla una de cada cinco no protege nada.

---

# FASE 26 · DOS CAMINOS PARA NOMBRAR LO MISMO

## Lo que dije mal

Escribí que `etiqueta_de` no tiene mapa de unidades y produce «Resolucion del
07». **Era mi error de prueba**: le pasé el `07` del número de resolución, y esa
función recibe **el nombre** de la unidad, no el código.

```
etiqueta_de("07")                 -> «Resolucion del 07»              ← lo que probé
etiqueta_de("TEAR de Baleares")   -> «Resolucion del TEAR de Baleares» ← lo que hace el código
```

El nombre sale de `Criterio.unidad`, que viene de **DYCTEA** en el registro, y
por eso el 5 de agosto la cita salió bien. Sobre esa conclusión falsa cambié el
ejemplo de `GUIA.md` a «Resolucion del 07», que es justo lo que **ningún usuario
verá jamás**. Corregido a `{Resolucion del TEAR de Baleares 07/02872/2023/00/00}`,
que es lo que el sistema escribe de verdad.

## Pero la sospecha de fondo era buena: sí había dos caminos

| | quién compone | qué escribe |
|---|---|---|
| **1 · el material** que lee el redactor | `Criterio.cita()` → `etiqueta_de(unidad)` | correcto siempre |
| **2 · el verificador** (`referencia_corpus`) | la constante `T.ETIQUETA`, corregida **solo si** el criterio estaba en la copia local | **«Criterio TEAC» para un TEAR** cuando no lo tenemos guardado |

Es el defecto de la fase 14 —un TEAR etiquetado como TEAC— colándose por la rama
de al lado, la que menos se mira. Y el motivo que se enseña en pantalla llevaba
«del TEAC» escrito a pelo: *«el criterio 08/… **del TEAC** no está en la copia
local»*, dijera lo que dijera la resolución.

**Unificado.** `teac.etiqueta_de` es la única que nombra, y el verificador la usa
también cuando no encuentra el criterio. Ahí la respuesta honrada no es «TEAC»:

```
etiqueta_de("")  ->  «Resolucion economico-administrativa»
```

Atribuir doctrina a quien no la ha dictado es el peor error que puede cometer
este sistema, y sale gratis no cometerlo.

## Qué se escribe hoy si se cita un TEAR de Cataluña

```
en el material   {Resolucion del TEAR de Cataluña 08/…, de …/…/… — https://…}
verificado       Resolucion del TEAR de Cataluña 08/…
si no lo tenemos Resolucion economico-administrativa 08/…   (y NO_VERIFICABLE)
```

Sin tocar nada: el nombre sale de `unidad`, y `unidad` viene de la fuente.

## El candado

`prueba_unidad` gana un bloque 8 que comprueba las dos formas —y solo esas dos—
de acabar con una etiqueta compuesta por libre: **una f-string con «Criterio
TEAC» dentro**, y **usar `teac.ETIQUETA` fuera de `teac.py`**. Más la rama del
criterio ausente, verificada de punta a punta.

La primera versión del detector miraba líneas de texto y **daba un falso
positivo**: `BLOQUE_TEAC` —el trozo de prompt que le enseña el formato al
modelo— lleva «Criterio TEAC» a propósito y está bien que lo lleve. Se rehízo
con `ast`. Un falso positivo acaba en que alguien apaga la comprobación, así que
cuenta como fallo igual que un falso negativo. El bloque lleva su propio control
negativo: un fichero con la etiqueta en un docstring, en un texto de prompt y en
una f-string, y solo la tercera se caza.

## Lo barato que quedaba anotado

- **Los números inventados de `prueba_recorte` y `prueba_normativa` pasan a la
  serie `9xxx`** (`V0001-23` → `V9101-23`, `V0100-24` → `V9140-24`…),
  conservando el año de cada uno porque varias comprobaciones dependen de él.
  Comprobado antes de tocar nada que los nueve números nuevos **no existen** en
  la copia local. Las dos suites llevan ahora la nota de por qué.
- **`V2092-15`**: anotada su procedencia en el LEEME. No está en nuestra copia
  de la DGT; aparece **dentro del texto** de `00/03399/2023` y `00/05524/2024`,
  que sí tenemos. Dato real de segunda mano, no invención.

## Comprobaciones

```
9 suites .......... verdes
fase3 · fase4 ..... 37/37 · 5/5
guía coherente .... sí
llamadas a la API ... 0
```

---

# Fase 30 · Romperlo a propósito: lo que escribe una persona de verdad

Hasta aquí la herramienta solo la habíamos usado nosotros, y siempre con
preguntas bien escritas. Es una gestoría del Penedès: alguien va a preguntar en
catalán, alguien va a poner «23» en el año y alguien va a pegar un requerimiento
entero. **Suite nueva: `pruebas/prueba_entradas.py`**, con control negativo.

## Lo que estaba roto

**1 · El año no se validaba. Nada.** `resolver_ejercicio` aceptaba lo que le
llegara. Medido de punta a punta antes de tocar nada:

| se escribía | salía |
|---|---|
| `abc` | **CRITERIO CLARO**, ejercicio `'abc'` |
| `23` | **CRITERIO CLARO**, ejercicio `'23'` |
| `ejercicio 2023` | **CRITERIO CLARO**, ejercicio `'ejercicio 2023'` |
| `2023-2024` | **CRITERIO CLARO**, ejercicio `'2023-2024'` |

Es el fallo más silencioso que puede tener esto: una consulta contestada con la
ley de otro ejercicio sale impecable, con sus citas y sus enlaces, y está mal.
Arreglado con `analizador.leer_ejercicio`, que devuelve `(año, motivo)` y explica
cada rechazo en cristiano: «*«23» no son cuatro dígitos. Escribe el año entero:
2023, no 23*», «*«2023-2024» son dos ejercicios y cada uno puede tener su
redacción de la ley: consulta uno cada vez*».

**Y había dos validaciones del año, no una.** `main()` llevaba su propia
comprobación de rango, escrita aparte. Dos caminos para una regla es como se
descuadran: uno se arregla y el otro no. Ahora `main()` llama a `leer_ejercicio`,
y por eso la terminal da el mismo mensaje que la ventana. De paso se quitó
`type=int` de `--ejercicio`: con él, `--ejercicio 23` pasaba por la terminal
como el año 23 y `abc` salía con el mensaje de argparse, en inglés.

**2 · No había tope de longitud.** Un requerimiento pegado —2.640 palabras,
15.360 caracteres— entraba entero al análisis. `TOPE_PREGUNTA = 1200`, y **la
comprobación va delante de la primera llamada al modelo**: puesta detrás costaba
una llamada por cada intento de pegar un documento. Verificado: **0 llamadas**.

**3 · Una pregunta vacía costaba DOS llamadas** y acababa diciendo «no se ha
podido determinar de qué impuesto es la pregunta», que además es falso: el
problema no era el impuesto, era que no había pregunta. Ahora para antes de
nada, con cero llamadas, y lo dice.

**4 · Lo pegado de un PDF llegaba partido.** `deduc-\ncion del IVA de un co-\nche`
dejaba al buscador con `deduc`, `cion`, `co`, `che` — que no son palabras de
nada. `texto.unir_cortes_de_linea` recompone **solo** la firma exacta del corte
de renglón (minúscula, guion, salto, minúscula): `Real Decreto-\nLey` y un guion
con espacios alrededor se quedan como están.

**5 · La ventana mentía en dos de cada tres paradas.** Para `código 3` daba una
frase fija: «Falta el año del caso». Con el tope nuevo, a quien pegaba un
requerimiento de 15.000 caracteres se le decía que faltaba el año. Ahora enseña
el motivo que escribe `fase4`, que es distinto para cada caso.

## El catalán: lo que se decidió, y lo que costó

Dos consultas con el modelo real. **El analizador entiende el catalán y propone
los términos en castellano**, que es como está la ley: `modificacion de la base
imponible`, `credito total o parcialmente incobrable`, `requerimiento notarial de
cobro`. Sin tocar nada.

**La decisión, escrita:**

- La respuesta va **en el idioma de la pregunta**.
- El **texto citado** no se traduce jamás: es el de la ley.
- La **referencia** tampoco. «artículo 80 de la Ley 37/1992» entero en
  castellano, porque es el nombre oficial del precepto: el que se escribe en un
  escrito a la Agencia Tributaria y el que se busca en el BOE.
- **En la prosa, en cambio, se habla normal.** «l'article 80 de la Llei» dentro
  de una frase en catalán está bien dicho. La regla es de la referencia —lo que
  va en el paréntesis, con su enlace—, no de cómo se hable.

**Y entonces salió bien y se cayó igual.** El borrador en catalán era correcto:
ocho citas literales, en castellano, sin una palabra traducida. Se quedó en **NO
ENCONTRADO** con «7 de 8 citas no verificadas», y el motivo de las siete era
*«fragmento entrecomillado sin referencia a ningún precepto»*.

El redactor había escrito `(article 80 de la Ley 37/1992, <enlace>)`: dejó el
texto y el nombre de la norma en castellano —que es la regla— y tradujo la
palabra de enlace. `citas._RE_REF_ARTICULO` no conocía «article», así que no veía
referencia ninguna. **Una respuesta impecable tirada por una palabra.**

Se arregló por los dos lados, y el orden importa:

- **El prompt** pide la referencia entera en castellano. Es lo correcto.
- **Pero de eso no se puede depender**, así que el lector de referencias entiende
  también «article». Esto **no afloja la verificación**: la cita se sigue
  comprobando letra a letra contra el precepto. Solo se reconoce una segunda
  forma de escribir el mismo nombre. En el articulado del BOE la palabra no
  aparece nunca, así que en el escaneo del corpus es inerte.

De 7 citas caídas a **1**. Y la que queda enseña otra cosa.

## Las comillas angulares no son comillas

La cita superviviente que fallaba era `«més d'un any»`. No es una cita: es que en
catalán —y en castellano— `« »` son las comillas normales, y el redactor las usó
para repetir las palabras del cliente. Aquí `« »` significa **una sola cosa**:
texto copiado de la ley. Todo lo que va ahí se comprueba contra el corpus, y tres
palabras en catalán no están en la Ley del IVA, claro.

Se arregla en el prompt, no en el verificador. **El verificador tenía razón.**

## Lo que la suite fija, y cómo sabe ponerse roja

El caso del catalán se comprueba **sin gastar nada**, contra el borrador real que
escribió el modelo el 11/08/2026, guardado en `casos/borradores/`. Es una medida,
no un ejemplo escrito por nadie: la regla de la fase 25 vale también aquí.

Cuatro controles negativos, cada uno rompiendo el arreglo que protege:

| se rompe | lo que pasa | quién lo caza |
|---|---|---|
| se quita «article» del lector | 7 citas «sin referencia» | bloque 0 |
| se quita la validación del año | `abc` se acepta | bloque 1 |
| se deja de unir los cortes de renglón | el buscador ve `deduc`, `cion` | bloque 2 |
| se quita el tope de longitud | el requerimiento pegado paga 1 llamada | bloque 2 |

## Lo que se probó y NO estaba roto

- **Temas fuera del corpus** —IBI, plusvalía municipal, herencias, una laboral,
  ITP, impuestos especiales—: todos salen por la puerta de materia, con el
  mensaje que nombra lo que sí cubre la herramienta, sin texto y sin traza.
- **Sin tildes**: `tokenizar` ya las quitaba.
- **Caracteres raros, nulos, secuencias de escape, emojis, dos preguntas
  seguidas**: ninguno revienta ni deja una traza en pantalla.
- **Una palabra suelta** (`prorrata`) se admite. No es un error: es una pregunta
  corta.

## Lo que queda abierto

- **Las faltas de ortografía no se han podido juzgar.** `deducion iva coche` sale
  NO ENCONTRADO, pero con el motor de ensayo, cuyo analizador es un tokenizador
  y no corrige nada. Con el modelo real lo normal es que lo entienda —como
  entendió el catalán—, pero **no está medido**, y lo que no está medido no se
  cuenta como que funciona.
- **La regla nueva de las comillas angulares en catalán no está verificada con el
  modelo real.** Está escrita en el prompt; falta la consulta que lo demuestre.

## Comprobaciones

```
10 suites ......... verdes  (la nueva: prueba_entradas)
fase3 · fase4 ..... 39/39 · 5/5
banco de IVA ...... 16/19, sin cambios de veredicto
llamadas a la API ... 4  (las dos consultas en catalán, autorizadas)
```

---

# Fase 31 · Los fallos de entorno a mitad de consulta

Nunca se habían probado en caliente. Se simulan **durante** una consulta —con el
análisis ya pagado y el material ya buscado—, que es cuando hacen daño.
**Suite nueva: `pruebas/prueba_caidas.py`**, con tres controles negativos.

## Lo que ya estaba bien

Los cuatro fallos de API a mitad —**se va internet, 429, 500, se acaba el
crédito**— ya se manejaban enteros: sin reventar, sin enseñar texto, marcados
como `fallo="modelo"` (no como criterio) y **con el expediente cerrado y
completo**. La traducción a frase de persona sale de `en_cristiano` y no lleva
nada técnico dentro.

## Lo que estaba roto

**1 · El disco lleno reventaba con `OSError`, en los tres momentos.** Al abrir la
traza, a mitad y al cerrar. En la terminal, traza de Python con la ruta del disco
dentro. En la ventana el `except Exception` lo convertía en el mensaje genérico
—«vuelve a intentarlo»—, que con el disco lleno es un consejo inútil: va a fallar
igual.

**La decisión, escrita:** un fallo de disco **no tira la consulta** —la respuesta
ya está verificada y pagada, esconderla no ayuda a nadie— **pero no pasa en
silencio**. `Traza` apunta el primer fallo en `self.roto`, `_fin` lo pasa al
resultado, y la ventana cambia el pie: donde decía «Expediente guardado en …»
—señalando a una carpeta que no existe— ahora avisa de que no ha quedado
guardada. Una respuesta sin expediente no se puede reconstruir dentro de seis
meses, y quien la enseñe tiene derecho a saberlo.

**2 · La respuesta cortada salía como NO ENCONTRADO.** Cuando el modelo se queda
sin espacio (`stop_reason: max_tokens`), el trozo pasaba al verificador, que lo
tumbaba —bien tumbado: acaba con una comilla abierta— y la consulta salía como
**NO ENCONTRADO** con el motivo «el texto no contiene ninguna cita con fragmento
literal». Es cierto y **apunta al sitio equivocado**: quien lo lee entiende que
la ley no dice nada de su caso, cuando lo que ha pasado es que la respuesta se
cortó por la mitad. Ahora se mira el `stop_reason` y se dice. No se reintenta:
saldría cortada otra vez por el mismo sitio.

**3 · Un 500 caía en el mensaje genérico**, que manda a avisar a Emili por algo
que se arregla solo en un minuto. Regla propia para 5xx.

**4 · Y la regla del año tenía una TERCERA copia.** En `interfaz._revisar_boton`,
escrita a mano —`isdigit` y el rango—, aparte de la de `leer_ejercicio` y la que
tenía `fase4.main`. Coincidían hoy, que es lo que hace peligroso este patrón:
**coinciden hasta que alguien arregla una y no las otras.** Y `_lanzar` hacía
`int()` a pelo sobre la caja, fiándose del estado de otro widget.

## Un doble mal puesto tapa justo lo que se quiere probar

La primera versión de la prueba del disco sustituía `Traza.escribir` **entera**,
o sea el método que **contiene** el `try/except`. Con ese doble, cualquier
arreglo dentro de esa función es invisible: la prueba seguía en rojo después de
arreglarlo. Un disco lleno falla en `Path.write_text`, y ahí es donde hay que
romperlo.

**Regla: el doble se pone en la capa que falla de verdad, no en la que la llama.
Si se sustituye la función que contiene la protección, se está probando el doble.**

## El caso que más preocupaba, con números

**Si falla entre el analizador y el redactor, ¿se pierde el análisis?** Sí: no
hay reanudación. `analisis.json` se escribe en el expediente y **no lo lee
nadie** salvo `ver_ejemplo.py`, para enseñar el año.

**Pero lo que se pierde es tres centésimas de céntimo.** Medido sobre 2.660
llamadas reales en disco:

| paso | llamadas | media | total |
|---|---:|---:|---:|
| análisis | 1.160 | 0,03 cts | 40 cts |
| redacción | 1.500 | 0,24 cts | 359 cts |

**El análisis es el 10% del gasto.** Cuando la caída es entre los dos, la mitad
cara —la redacción— todavía no se ha pagado. Construir una reanudación ahorraría
0,03 céntimos por caída. **No se construye.**

## Repaso de entradas sin comprobar

Después de que el año pasara tres semanas sin validarse, se repasó todo lo que
entra de fuera. **Lo que está bien:**

- `ver_ejemplo.py` con `../../etc`, `/etc`, `«no existe; rm -rf»` o vacío: los
  cuatro salen con el mensaje de siempre y código 1.
- `fase3 verificar` con un fichero que no está, `fase1 inspeccionar` con un
  identificador inventado, `petete consulta ../../etc/passwd`: mensaje claro.
- **15 de las 16 lecturas de JSON** del proyecto están protegidas contra fichero
  corrupto.
- El corpus vacío y el corpus **cortado a mitad** se detectan los dos, y el
  segundo dice **en qué línea**.

**Lo que queda anotado, sin arreglar:**

- **`sembrar_teac.py:69`** lee `catalogo.json` sin coger `JSONDecodeError`. Es un
  guion de mantenimiento que ejecuto yo, no el departamento.
- **`ver_ejemplo.py` acepta una ruta absoluta** (`DIR_TRAZAS / "/etc"` da `/etc`
  en pathlib). No revienta y solo lee, pero mira fuera de `datos/trazas/`.
- **La ventana no avisa de la longitud hasta que se pulsa.** El tope funciona y
  no cuesta ni una llamada, pero se descubre después de pegar.
- **Un corpus truncado en un límite de línea válido no se detecta.** Cargaría
  menos preceptos en silencio. Haría falta una suma de control.

## Las dos medidas que faltaban, con modelo real

Cuatro llamadas, dos consultas.

**`deducion iva coche`** —con faltas y sin tildes— sale **CRITERIO CLARO, 7 de 7
citas verificadas**, artículo 95. El analizador lo entiende y propone
`vehiculo automovil de turismo`, `bien de inversion`, `presuncion de afectacion
del cincuenta por ciento`. **No hace falta corregir nada.**

**La regla de las comillas angulares se respeta.** Consulta en catalán sobre la
rectificación de cuotas: 7 aperturas, 7 cierres, y **las siete son texto literal
de la ley en castellano**. Ni una palabra en catalán entrecomillada. Y la
referencia salió entera en castellano dentro de una frase en catalán:
`«…» (articulo 89 de la Ley 37/1992, <enlace>)`. **CRITERIO CLARO, 7/7.**

## Comprobaciones

```
11 suites ......... verdes  (la nueva: prueba_caidas)
fase3 · fase4 ..... 39/39 · 5/5
banco de IVA ...... 16/19, sin cambios de veredicto
llamadas a la API ... 4  (las dos medidas pendientes, autorizadas)
```

---

# Fase 32 · La suma de control del corpus, y el aviso de largo

## 1 · Un corpus incompleto no daba error: daba respuestas peores

Es el peor fallo que hemos encontrado, porque **no deja rastro**. Un fichero del
corpus que se queda a medias —un disco lleno a mitad de `ingerir`, una copia
interrumpida, un `rsync` cortado— se carga sin protestar **si el corte cae en un
final de línea**: cada línea sigue siendo JSON válido, el índice se construye, la
ventana abre y todo parece normal.

Lo que pasa después no se parece a una avería. La búsqueda deja de encontrar
artículos que existen, el corte por pertinencia descarta lo que queda, y salen
**NO ENCONTRADO donde antes había CRITERIO CLARO**. Nadie lo relaciona con el
corpus: se piensa que la pregunta estaba mal escrita, o que la ley no lo dice.

**`agente_fiscal/sellos.py`**: un `sha256` del fichero tal cual está en disco,
apuntado al ingerir y comprobado al cargar. Se guardan además los preceptos y los
bytes, que no hacen falta para detectar nada —el sha256 ya los cubre— pero sí
para el mensaje: no es lo mismo «el fichero no cuadra» que **«faltan 63
preceptos: tiene 180 y debería tener 243»**. Lo segundo se entiende.

```
El corpus no cuadra con su suma de control. No se abre: con media ley
las respuestas empeoran sin dar ningún error.
  - BOE-A-1992-28740 no cuadra con su sello del 2026-08-11: faltan 63
    preceptos: tiene 180 y debería tener 243. Vuelve a ingerirla:
    python fase1.py ingerir BOE-A-1992-28740
```

**Dónde va la comprobación**: en `Indice._cargar`, no en el arranque de cada
programa. Por ahí pasan todos —la ventana, la terminal, el banco y las pruebas—.
Un sitio, una regla.

**El sello se escribe en `fase1.py ingerir`, en la misma función que escribe el
corpus.** Si se sellara aparte habría un momento en que el corpus está escrito y
sin sello, y ese momento es justo el que se quiere hacer imposible.

**Tres estados, no dos.** «Sin sellar» no es «mal»: es el estado de cualquier
corpus de prueba en un directorio temporal. Sin fichero de sellos no se bloquea
nada, pero **tampoco se canta verde** — eso sería la mentira que esto viene a
evitar. La pantalla lo distingue.

**Antes de sellar se auditaron las siete normas** con `fase1.py verificar`: las
siete correctas. El sello certifica algo que pasó la auditoría, no lo que hubiera
en disco.

| norma | preceptos | bytes |
|---|---:|---:|
| BOE-A-1992-28740 (LIVA) | 243 | 5.001.578 |
| BOE-A-1992-28925 (RIVA) | 144 | 2.232.825 |
| BOE-A-2003-23186 (LGT) | 335 | 2.364.474 |
| BOE-A-2006-20764 (LIRPF) | 222 | 3.479.484 |
| BOE-A-2007-6820 (RIRPF) | 170 | 1.915.432 |
| BOE-A-2014-12328 (LIS) | 212 | 2.325.661 |
| BOE-A-2015-7771 (RIS) | 86 | 648.815 |
| | **1.412** | |

**Sólo se sella lo que se carga.** Los `.descartados.jsonl` no entran: no los lee
el motor, son material de auditoría de la fase 1 y un fallo suyo no cambia ni una
respuesta.

**Y se ve en «Qué hay dentro»**, que es la pantalla que se abre justo para dudar
de una respuesta: `✓ Corpus comprobado: las 7 normas cuadran con su suma de
control (2026-08-11).`

## 2 · El aviso de largo, mientras se escribe

Antes sólo se enteraba al pulsar: se pegaba el requerimiento entero, se pulsaba y
llegaba un rechazo. **Tres tramos**, no dos: callado mientras hay sitio de sobra,
un aviso tranquilo al 75% —para que no sorprenda a mitad de pegar— y el motivo
cuando ya no cabe, con el botón apagado.

> Son 1.535 caracteres y caben 1.200. Esto pasa al pegar un requerimiento
> entero: pega solo la parte que pregunta, o resúmela en unas líneas. (Cuando la
> herramienta sepa leer el PDF entero, esto dejará de hacer falta.)

**Esa última frase importa.** El tope no es una manía: es que hoy la pregunta
viaja al modelo tal cual, y un escrito entero cuesta dinero y da peor resultado
que la duda concreta. Cuando lea PDF, desaparece. Sin decirlo parece una
limitación tonta, **y una limitación que parece tonta se salta**.

**Pegar no es escribir.** `<KeyRelease>` no llega cuando se pega con el botón
derecho, y pegar es justo lo que hace alguien con un requerimiento delante. Se
usa `<<Modified>>`, que salta con cualquier cambio venga de donde venga.
Comprobado insertando texto sin tocar una tecla.

## 3 · La cuarta vez con lo mismo

`pady=(12, 0)` en un **widget**. `pady` de un widget es UNA distancia; el par va
en el `pack`/`grid`. Van cuatro. **La cazó `prueba_interfaz` en la misma pasada**,
que es exactamente para lo que está.

## Comprobaciones

```
11 suites ......... verdes
fase3 · fase4 ..... 39/39 · 5/5
fase1 verificar ... las 7 normas correctas antes de sellar
banco de IVA ...... 16/19, sin cambios de veredicto
llamadas a la API ... 0
```

---

# Fase 34 · Los códigos de impuesto salen del corpus

## La pantalla se contradecía a sí misma

Entró la Ley del Patrimonio y el corpus empezó a decir que cubría Patrimonio.
Pero `AN.IMPUESTOS` era un **enum escrito a mano** sin código para Patrimonio, así
que una pregunta de Patrimonio salía como «otro» y se rechazaba con:

> «la consulta es de **otro** y esta herramienta cubre Impuesto sobre Sociedades,
> **Impuesto sobre el Patrimonio**, Impuesto sobre el Valor Añadido y…»

La pantalla decía que cubría Patrimonio y se negaba a contestar de Patrimonio.

**Es la tercera vez con el mismo patrón**: las tres copias de la regla del año y
los dos caminos de la etiqueta del TEAC. **Cuando dos sitios tienen que decir lo
mismo, uno lo dice y el otro lo lee.**

`analizador.codigos(normas)`: los códigos salen de los títulos de las normas
cargadas. Si mañana entra la Ley de Sucesiones, ISD aparece **sin que nadie
escriba nada** — comprobado en la suite con un corpus imaginario.

**`IMPUESTOS_FUERA` no es una lista de cobertura**, y por eso no la abre: es
vocabulario, para que el rechazo pueda decir «la consulta es de ITP-AJD» en vez
de «es de otro». Un rechazo que nombra el impuesto le dice al gestor que le hemos
entendido y que no lo tenemos. Si alguno se ingiere, el corpus manda y `codigos`
lo quita de ahí.

Comprobado: **IP, IRPF, IS e IVA entran**; **ISD e ITP-AJD salen rechazados**
nombrándose y enumerando bien lo que sí se cubre.

## Lo que hay que decidir: la búsqueda no filtra por impuesto

Abrir la puerta a Patrimonio destapa algo que ya estaba: **el `impuesto` del
análisis no filtra la recuperación**. Se usa para la puerta y para el criterio,
nada más. Medido:

| términos de la pregunta | qué sale |
|---|---|
| «patrimonio neto, bienes y derechos, sujeto pasivo» | 5/5 de la Ley 19/1991 ✔ |
| «obligación de declarar patrimonio neto» | 4/5 de la Ley 19/1991 ✔ |
| «escala de gravamen del patrimonio» | **5/5 del IRPF** ✘ |
| «exención de la vivienda habitual en patrimonio» | **5/5 del IRPF** ✘ |

Con vocabulario propio del Patrimonio gana su ley; con vocabulario compartido
—«escala», «vivienda habitual»— gana el IRPF entero. **El verificador no lo
salva**: citar el art. 63 de la Ley 35/2006 verifica bien, porque la cita es
literal y existe; lo que está mal es que no viene al caso, y eso el verificador
no lo mira. Queda abierto y decidido por Emili.

## «Qué hay dentro»: se pliega, no se desplaza

Tercer crecimiento (41 líneas, tope 40). **No se sube el tope** —es la tercera
vez— **y tampoco se resuelve desplazando**, aunque esa ventana ya se desplaza:
esta pantalla contesta UNA pregunta —«¿está mi impuesto dentro?»— y **una
respuesta que hay que ir a buscar bajando ya no es una respuesta de un vistazo**.

Plegada: la lista de normas concretas se esconde tras un botón. Crece **una línea
por impuesto en vez de tres**, y el detalle sigue entero. Medido: **37 plegada, 42
abierta**, y la suite comprueba las dos cosas — que quepa y que al abrirla vuelvan
los nombres. Un pliegue que esconde algo para siempre no es un pliegue: es un
recorte.

El desplazamiento se queda donde debe: de red por si acaso, no como forma de leer.

## Una expectativa que no vuelva a caducar

`prueba_caidas` llevaba «7 normas» escrito. Ahora lee `len(ix.rutas)`: se
comprueba que la pantalla diga **las que hay**, y eso no caduca.

## Comprobaciones

```
11 suites verdes · fase3 39/39 · fase4 5/5 · banco 16/19 sin cambios
1.960 preceptos · 19 cuerpos · 12 normas · sello correcto
llamadas a la API ... 0
```

---

# Fase 35 · La búsqueda filtra por impuesto

El corpus ya sabía de qué impuesto es cada cuerpo —la regla del papel— y el
analizador ya sabía de qué impuesto es la pregunta. **Faltaba unirlos.**

Se recupera de los cuerpos del impuesto de la pregunta **más los generales**
—LGT, RGAT, recaudación, sancionador, facturación—, que aplican a todos. Un
cuerpo que no nombra impuesto es general por definición: no hay lista de normas
generales escrita en ninguna parte.

`normas.impuesto_de_cuerpo` resuelve también el caso del real decreto
aprobatorio: los 8 artículos que aprueban el Reglamento del IRPF **son del
IRPF**, aunque su rótulo no nombre materia ninguna.

## Lo que arregla

| pregunta de Patrimonio | antes | ahora |
|---|---|---|
| «patrimonio neto, bienes y derechos» | 3/5 Ley 19/1991 | **5/6** |
| «obligación de declarar patrimonio neto» | 4/5 | **5/6** |
| **«escala de gravamen»** | **5/5 del IRPF** | 0 del IRPF |
| **«exención de la vivienda habitual»** | **5/5 del IRPF** | **6/6 Ley 19/1991** |

**Y el verificador no salvaba ninguno de esos dos**: citar el artículo 63 de la
Ley 35/2006 verifica bien, porque la cita es literal y el artículo existe. Lo que
falla es que no viene al caso, y eso no lo mira nadie. Salía en pantalla con toda
la seguridad del mundo.

## La reserva: la nota al pie sigue cruzando de impuesto

El pase de remisiones sólo readmitía preceptos **ya recuperados**. Con el filtro,
el artículo de otro impuesto ya no está ahí, y la nota al pie se habría perdido
en silencio. Hay **72 remisiones resueltas que cruzan de impuesto** en el corpus.

**La primera versión de la reserva la llené con «los mejor puntuados de fuera» y
no servía**: el artículo 51 de la Ley 35/2006 no puntúa nada para una pregunta de
patrimonio, y aun así es al que remite el artículo 4 de la Ley 19/1991 cuando
habla de planes de pensiones exentos. **Lo que decide quién está en la reserva es
a quién se le llama, no a quién se parece.** La reserva son los destinos de las
remisiones de los candidatos, y sólo entran si alguien los llama.

Medido de punta a punta: «bienes y derechos exentos… plan de pensiones y
participaciones» → entra el art. 4 de la Ley 19/1991 y, **por remisión**, los
arts. 51, 13 y 68 de la Ley 35/2006, con su motivo escrito en la traza.

## Si el impuesto no se sabe, no se filtra

`cuerpos_para` devuelve `None` con vacío, nulo, `desconocido`, `otro` y con
cualquier impuesto que no esté en el corpus. **Filtrar con un impuesto equivocado
es peor que no filtrar**: sin filtro se compite de más y el corte por pertinencia
hace su trabajo; con el filtro equivocado se pierde la ley que tocaba y no se
nota. El control negativo (c) lo enseña: filtrando una pregunta de patrimonio
como si fuera de IVA, la Ley 19/1991 desaparece entera.

## Lo que cuesta

Medido sobre las 19 preguntas del banco:

```
candidatos   6,0 -> 6,0     el tope se sigue llenando: el corpus da de sobra
enviados     4,0 -> 3,9     el corte por pertinencia trabaja casi igual
material distinto en 8 de 19
```

**El filtro no reduce el conjunto de candidatos** —cambia *cuáles* son los seis,
no cuántos—, así que el corte por pertinencia sigue teniendo con qué trabajar.
Ocho consultas mandan un juego distinto de artículos, con el mismo tamaño.

## Comprobaciones

```
12 suites verdes (la nueva: prueba_filtro, con tres controles negativos)
banco de IVA ...... 16/19, las mismas rojas, sin cambios de veredicto
las dos de Renta .. 3/3 los mismos articulos, las dos
fase3 · fase4 ..... 39/39 · 5/5
llamadas a la API ... 0
```

---

# Fase 36 · La catalana NO entra. La puerta se cerró sola, tres veces

`agente_fiscal/pendientes.py`: lee de los datos del BOE qué le falta a una norma
consolidada por incorporar, y **se niega cuando no se puede saber**.

## Lo primero: «posteriores» no es «pendientes»

`referencias.posteriores` es el **histórico** de todo lo que ha tocado la norma,
incorporado o no. Sobre el Decreto Legislativo 1/2024: **seis de las ocho ya
estaban dentro del texto**. Leerlo como lista de pendientes marcaría 20 preceptos
en vez de 14, y eso también es mentir, sólo que por el otro lado.

Lo que sí está incorporado **se sabe del articulado, no de la prosa**: si una
norma escribió alguna `version`, sus cambios están dentro. Consolidada hasta
**2026-05-23**. Pendientes: **dos, las dos con id del DOGC** —una ley catalana
publicada sólo en el DOGC no la ha recogido el BOE todavía—.

## Tres motivos independientes para no ingerir

**1 · La lista de pendientes sólo existe en prosa, y no se puede verificar.**

La única fuente de qué deroga la Ley 11/2026 es una frase escrita por una
persona. **Para una reforma pendiente no hay texto contra el que contrastarla**:
si lo hubiera, ya estaría incorporada. Y sobre esta misma norma medí que **3 de 8
notas históricas dicen «determinados preceptos»** sin enumerar — prueba de que
esas notas a veces no son exhaustivas por construcción. Un marcado tan completo
como una prosa que no se puede comprobar es un marcado que puede tener agujeros
invisibles: el artículo derogado y no marcado se cita con enlace y con seguridad.

Además, la nota dice «y, **en la forma indicada**, el art. 612-15», y la de
erratas no nombra ni un precepto de esta norma: corrige erratas de otra.

**2 · El troceo no reconoce la numeración del Codi. Diez de ciento sesenta.**

Medido troceando en memoria, sin ingerir: **10 citables y 218 descartados, de los
cuales 151 «SIN RECONOCER»**. `bloques.py` espera «Artículo 12» y el Codi numera
«611-1», «621-2», «641-14». Se ingeriría **una norma vacía con aspecto de norma
ingerida**: entrarían el artículo único, las disposiciones y el anexo, y ni uno
solo de los 160 artículos. (`fase1.py verificar` lo cazaría después, pero la
ingesta habría escrito el fichero y el sello.)

**3 · La regla del papel no sabe decir «de varios impuestos».**

Sus materias salen como `Legislativo 1/2024, de 12 de marzo` y `Código tributario
de Catalunya`; ninguna es materia de impuesto, así que en el corpus real quedaría
clasificada **general** — y una norma general compite en las búsquedas de TODOS
los impuestos. Los artículos catalanes de Sucesiones e ITP aparecerían en
preguntas de IVA. Es justo lo contrario de lo que se quiere.

## Lo que sí se pudo derivar, y es útil para cuando se retome

Aunque la prosa no baste, el **alcance de las erratas sí se deriva del XML**: el
Decreto-ley 21/2025 versionó 11 bloques, así que la errata sólo puede afectar a
esos. Y el reparto por título es tranquilizador:

| título | pendientes Ley 11/2026 | riesgo de erratas |
|---|---:|---:|
| I · IRPF | 3 (**sólo añadidos**) | 0 |
| **II · Patrimonio** | **0** | **0** |
| III · Sucesiones | 3 | 6 |
| IV · ITP-AJD | 5 | 3 |
| VIII · Formales | 1 | 0 |

**El artículo 621-2 —la escala del patrimonio catalán— no está afectado por
nada**, y la DT primera ya está actualizada. De los cinco que la reforma añade,
**ninguno existe todavía** en nuestro texto: no hay nada que citar mal. Los siete
que sí existen y se tocan están todos en Sucesiones, ITP y obligaciones formales.

Es decir: el riesgo real se concentra **en los impuestos que no íbamos a abrir**.
Aun así no se ingiere, porque los motivos 2 y 3 son independientes de eso.

## Lo territorial: mi respuesta

Un aviso al pie de toda respuesta que cite la norma es lo peor de las opciones:
se lee una vez y se deja de ver. **Mejor que el ejercicio y la residencia se
traten igual.** El año es obligatorio y bloquea porque una respuesta con la ley
de otro año sale impecable y está mal; una respuesta con la norma autonómica de
otra comunidad tiene exactamente la misma forma de fallar. Cuando entre normativa
autonómica, lo coherente es **un segundo campo obligatorio junto al año** —la
comunidad del contribuyente— y que la puerta de materia lo use igual que usa el
impuesto: si no se sabe, no se filtra y no se cita autonómico.

## Comprobaciones

```
13 suites verdes (la nueva: prueba_pendientes, con tres controles negativos)
corpus SIN TOCAR: 12 normas · 1.960 preceptos · sello correcto
banco 16/19 sin cambios · fase3 39/39 · fase4 5/5
llamadas a la API ... 0
```

---

# Fase 37 · `fase1.py ingerir` se niega cuando no entiende la norma

La catalana se habría ingerido con **151 bloques sin reconocer y 10 citables**:
una norma vacía con aspecto de ingerida —fichero, sello y resumen, todo
correcto, y ni un artículo dentro—. **Nada lo impedía**: se cazó troceando en
memoria a mano. Y lo peor no es ingerirla: es que después **no da error**. Da
respuestas peores en silencio.

## El umbral sale de los datos, no de una intuición

Troceadas las doce normas del corpus —**2.554 bloques**— el resultado es el mismo
en todas:

| | bloques | sin reconocer |
|---|---:|---:|
| las 12 del corpus | 2.554 | **0 (0,0 %)** |
| la catalana | 228 | **151 (66,2 %)** |

**No hay zona gris que repartir**: lo normal es cero y lo roto es dos tercios.

**Se pone en 5 % y no en 0 % a propósito.** Un bloque raro en una norma de
cuatrocientos no es una norma incomprendida, y una puerta que se cierra por eso
se acaba forzando siempre — que es como se deja de mirar. Lo que tiene que parar
es el caso catastrófico, y cualquier umbral entre 0 y 66 lo para. Cero no se
pierde de vista: **por debajo del 5 % se avisa igual**, con los mismos números.

**Segunda regla, para las normas pequeñas**, donde un porcentaje miente: si hay
**más bloques sin reconocer que citables**, tampoco entra. Con 20 bloques, 4 sin
reconocer son un 20 %; pero 6 citables contra 7 sin reconocer es un articulado
roto aunque el porcentaje salga bajo.

## El mensaje sirve para diagnosticar

```
  reconocidos como precepto citable : 10
  reconocidos como estructura       : 67
  SIN RECONOCER                     : 151 de 228 (66.2%)

  Ejemplos de lo que no se ha entendido:
    - Artículo 611-1
    - Artículo 611-2
    ... y 146 mas

NO SE INGIERE: EL TROCEADOR NO ENTIENDE ESTA NORMA
  ... Casi siempre significa que esta norma numera sus articulos de otra forma.
  Ingerirla ahora escribiria una norma con aspecto de completa y sin
  articulado dentro, y eso no da error mas adelante: da respuestas peores
  sin que nadie sepa por que.
  Si aun asi hace falta:  python fase1.py ingerir BOE-A-2024-6951 --forzar
```

**Con el ejemplo se diagnostica en el momento**: se ve «Artículo 611-1» y ya se
sabe que el problema es la numeración, sin abrir el código.

## Forzar se puede, pero queda escrito

Una puerta sin forma de abrirla acaba borrada el día que estorba; **una que se
abre sin dejar constancia es peor que no tenerla**, porque después nadie sabe que
esa norma entró saltándose la comprobación.

`--forzar` lo anota **en el sello**, que es el sitio que se mira para saber si el
corpus está entero, y la pantalla «Qué hay dentro» lo canta:

```json
"forzado": "ingerida con --forzar: 151 de 228 bloques (66.2%) sin reconocer"
```
> Corpus comprobado: las 13 normas cuadran con su suma de control (2026-08-11).
> **AVISO: 1 entraron forzadas (BOE-A-2024-6951).**

No se llama problema de integridad —su sello cuadra— pero tampoco pasa por
normal. Probado de punta a punta y **deshecho**: el corpus se queda en 12.

## Dos cosas que aprendí arreglando la prueba

- **El rótulo de un bloque no reconocido vive en `referencia`, no en `rubrica`**,
  que viene vacía. Mi prueba miraba `rubrica`, sacaba `a6` y acusaba al código de
  no enseñar ejemplos, que sí los enseñaba.
- **El BOE separa «Artículo» del número con un espacio DURO** (`\xa0`). La
  comparación fallaba por un carácter invisible. Ahora el mensaje lo cambia por
  uno normal **sólo para enseñarlo** —lo que se trocea no se toca—: un rótulo que
  no se puede copiar ni buscar es un mal diagnóstico.
- Y comprobado que **el espacio duro NO era la causa** del no reconocimiento:
  `Artículo\xa012` se reconoce sin problema. La causa es `611-1`, y sólo esa.

## Comprobaciones

```
14 suites verdes (la nueva: prueba_troceo, con dos controles negativos)
las 12 normas reingieren con codigo 0 y cero avisos
la catalana sale con codigo 1 y no escribe nada
banco 16/19 sin cambios · fase3 39/39 · fase4 5/5 · corpus intacto
llamadas a la API ... 0
```

---

# Fase 38 · La naturaleza de la duda, dicha en vez de adivinada

**El problema era de tamaño, no de pertinencia.** 836 preceptos generales —LGT,
RGAT, recaudación, sancionador, facturación— contra 47 de la Ley del Patrimonio.
Compitiendo en el mismo ranking, las generales copaban los puestos y los
artículos de la ley del impuesto **no llegaban a ser candidatos**. El artículo 37
de la Ley 19/1991 —quién está obligado a declarar— estaba en el **puesto 4**
contando solo su ley y en el **25** con las generales dentro.

## Por qué no bastaba con separar las dos ligas

El corte por pertinencia ya tenía la regla del papel, pero decidía si una
consulta era de procedimiento **mirando quién ganaba el puesto 1**. Eso funciona
con un ranking y deja de funcionar con dos: la norma general nunca queda la
primera en su propia liga, así que **toda** consulta pasaba por «de fondo».

Medido, y es lo que descartó el diseño: separando sin señal, las cuatro preguntas
de procedimiento pasaban de **puesto 1-3 a NO SALIR**.

| diseño | banco | art. 37 | procedimiento |
|---|---|---|---|
| solo separar (6/0) | 22/27 | puesto 4 ✔ | **4 de 4 no salen** ✘ |
| reservar puestos (5/1, 4/2, 3/3) | **20/27** ✘ | 5-6 | — |
| dos ligas unidas por cobertura | 22/27 | llega ✔ | 2 de 4 no llegan ✘ |
| **6/0 con la señal** | 24/31 · **material 25/31** | **puesto 4** ✔ | **intacto** ✔ |

## La señal

Campo `naturaleza` en el analizador: `fondo` · `procedimiento` · `no_esta_claro`.
**La instrucción es sobre qué se pregunta, no sobre qué norma lo resuelve**: el
analizador no tiene que saber que existe la Ley General Tributaria, tiene que
distinguir «cuánto puedo deducir» de «qué plazo tengo». Y ante la duda,
`no_esta_claro`, que es un valor legítimo — **si no se sabe, no se separa**, la
misma regla que con el impuesto.

Verificado con el modelo real, 3 llamadas, **3 de 3**:

```
«me he retrasado en presentar el modelo 303…»   procedimiento · IVA
«las participaciones de la empresa familiar…»   fondo         · IP
«cuantos años puede Hacienda revisar la renta»  procedimiento · IRPF
```

## El banco medía un escenario que no ocurre

Las cuatro preguntas de procedimiento declaraban la LGT como norma, de la que se
deducía impuesto GENERAL, y con eso **no se filtraba nada**. En la realidad
«me he retrasado en presentar el 303» la clasifica el analizador como IVA.

**Quinto campo en los casos**: el impuesto que diría el analizador, que no es
dónde vive la respuesta. Y cuatro casos nuevos con el escenario real — **dos ya
salían rojos antes de tocar nada**.

## Y la distinción que hay que no volver a confundir

Las dos rojas de Renta **son [PUENTE], no ahogamiento**: no salen **ni sin
filtrar nada**. La rúbrica del art. 66 LGT es «Plazos de prescripción» y la
pregunta dice «revisar»; la del 122 es «Declaraciones complementarias» y la
pregunta dice «olvidó incluir». Es el puente «coche» → «vehículo automóvil de
turismo», y lo construye el analizador, no el buscador. Anotado en el fichero de
casos con el motivo.

## Dos veces que la prueba acusó al código de lo que hace a propósito

- **`ANALISIS_BUENO` de `prueba_topes`** se quedó sin el campo nuevo, así que el
  análisis se rechazaba antes de llegar a la redacción y la prueba culpaba al
  tope. Un doble incompleto mide otra cosa y lo dice como si fuera esta.
- **La regla 1 del corte —el primero entra siempre, pase lo que pase—** es
  anterior a todo esto y deliberada. Mi prueba esperaba que una norma general
  marcada «fondo» no entrara, y entra si es el mejor resultado. Lo que la señal
  cambia es a **los demás**: con `procedimiento` llegan tres generales al
  material, con `fondo` solo la primera.

## Comprobaciones

```
15 suites verdes (la nueva: prueba_naturaleza, con cuatro controles negativos)
banco 24/31 · las de procedimiento NI UN PUESTO de diferencia
bateria 39/39 · fase4 5/5 · llamadas nuevas a la API ... 0
```

---

# Fase 39 · La catalana entra, y el acotamiento sale de la regla general

`BOE-A-2024-6951`, libro sexto del Codi tributari de Catalunya. **161 preceptos,
152 artículos.** El corpus pasa a **13 normas y 2.121 preceptos**.

## El acotamiento no hizo falta como regla aparte

Sus títulos de Sucesiones, ITP, medios de transporte y residuos se clasifican en
impuestos que **no están en `impuestos()` del corpus**, así que `admitidos_para`
nunca los admite. **Medido, no supuesto:**

| pregunta | catalanes en el top 6 |
|---|---|
| Patrimonio · «mínimo exento y tarifa» | **2** (arts. 621-2 Tarifa y 621-1 Mínimo exento) |
| Patrimonio · «bienes y derechos exentos» | 0 |
| Renta · «deducción autonómica por alquiler» | **4** (612-3, 612-11, 612-4, 613-1) |
| Renta · «gastos deducibles del trabajo» | 0 |
| IVA · «deducción cuotas vehículo turismo» | **0** |
| IVA · «modificación base imponible por incobrable» | **0** |

Salen **junto a los estatales, no en su lugar**: en la de patrimonio, el art.
621-2 catalán el primero y el art. 28 de la Ley 19/1991 el segundo. Y aparecen
sólo cuando la pregunta es autonómica de verdad — «gastos deducibles del trabajo»
no trae ni uno.

## La fecha de consolidación

`consolidado_hasta: 2026-05-23` en cada uno de sus 161 preceptos, sacado de las
versiones del propio articulado. Las otras doce no lo llevan: el BOE las mantiene
al día. Si el ejercicio de la consulta es posterior, `vigencia` emite un aviso de
**cobertura** —NOTA, no GRAVE—: no invalida el precepto, dice que puede haber
reformas no recogidas y manda a mirar el boletín autonómico.

## El mecanismo de no citables: escrito y **activo**, pero sin efecto

Marca **7 preceptos**, no cero como esperaba:

```
Articulo 631-20  ISD       Articulo 641-1   ITPAJD
Articulo 632-1   ISD       Articulo 641-14  ITPAJD
Articulo 632-16  ISD       Articulo 642-1   ITPAJD
                           Articulo 684-2   general
```

**Ninguno en IRPF ni Patrimonio**, que es lo único que se recupera. Así que está
activo y no tiene efecto: exactamente lo que se buscaba, pero por la razón buena
—no hay nada que marcar donde miramos— y no porque esté apagado.

**Cuándo se activa de verdad**: el día que se ingiera una norma cuya reforma
pendiente toque un título que sí recuperamos. `fase1` escribe `no_citable_por` en
esos preceptos —la lista la da `pendientes.leer`— y `vigencia` los caza con un
aviso GRAVE. No hay que acordarse de encender nada.

## Lo que se probó y se revirtió

Las remisiones internas del Codi —«artículo 631-1»— las lee el resolutor como
«artículo 631», que no existe, y **declina**: 52 remisiones perdidas. Probé
extender el patrón a números compuestos, como en el troceador, y **no vale**: en
las normas estatales «art. 10-3» es el apartado 3 del artículo 10, y pasaba a ser
un artículo «10-3». Lo cazó `prueba_normativa` con el campo `normativa` de una
consulta real de la DGT — las cifras agregadas de remisiones no lo veían porque
es otro camino de código.

**Y no se puede decidir ahí**: `leer_numeros` es una función pura de texto, sin
corpus, y lo es a propósito. Sin corpus no hay forma de saber si «631-1» es un
artículo compuesto o el apartado 1 del 631.

Se queda como está, con el motivo escrito. **Declinadas, no mal resueltas**: «ante
la duda, nada» sigue intacto. Y están casi todas en títulos que no recuperamos
—26 en Sucesiones, 13 en Sucesiones, 5 en ITP—, así que en Renta y Patrimonio la
pérdida es casi nula. Si algún día hace falta, la decisión es del resolutor, que
sí tiene corpus: probar el compuesto y caer al plano si no existe.

## Comprobaciones

```
15 suites verdes · bateria 39/39 · fase4 5/5
banco 25/31: el art. 37 de la Ley 19/1991 pasa a verde solo, por el
             reordenamiento estadistico de meter 161 preceptos
los doce sellos anteriores ... IDENTICOS. Trece normas, ninguna forzada
remisiones ... cero mal resueltas (bateria 39/39)
la puerta de bloques sin reconocer ... ya no la rechaza: 0 sin reconocer
llamadas a la API ... 0
```

## Anotado, no construido

**La residencia va como campo junto al año, no como aviso al pie.** Un aviso se
lee una vez y se deja de ver; el año es obligatorio y bloquea porque una
respuesta con la ley de otro ejercicio sale impecable y está mal, y la norma
autonómica de otra comunidad falla exactamente igual. Es lo siguiente.

---

# Fase 40 · Lo que se lanza desatendido se prueba antes en pequeño

## LA REGLA

**Lo que se lanza desatendido se prueba antes con el MISMO comando y el mismo
camino de código, sólo que con tope mínimo. Probar el modo barato no prueba el
caro.**

De dónde sale: al conectar los sembradores al plan cambié `construir_plan()` para
que devolviera el nombre completo de la norma. Probé `sembrar.py plan` —que sólo
imprime— y lancé `sembrar.py sembrar` —que baja durante horas—. **Reventó a los
nueve segundos con un `KeyError` y no descargó nada.** Probé un modo y lancé otro.

## El fallo: tres representaciones de la misma norma

- `NUMERO_NORMA = {"LIVA": "37/1992", …}` — mapa a mano, tres normas
- `DESIGNACION = {"LIVA": "Ley 37/1992", …}` — otro mapa a mano, las mismas tres
- y la fila del plan, que pasó a llevar el nombre completo

`modo_sembrar` buscaba `NUMERO_NORMA[fila['norma']]` y `modo_informe` esperaba un
campo `cuerpo` que no existía. **Es el mismo patrón de los cinco `ix.buscar`
sueltos y de las tres copias de la regla del año.**

Ahora la fila lleva todo lo que necesitan los tres —`cuerpo`, `norma`, `numero`,
`articulo`— y **el número lo da el corpus**, que ya lo sabe: hasta los
reglamentos, que heredan el del real decreto que los aprueba. Fuera los dos
mapas.

## Y un segundo fallo que sólo aparece al probar en pequeño

`--tope 2` **paró antes de bajar nada**: el tope se comparaba contra
`len(av["descargadas"])`, que arrastra lo de pasadas anteriores. Con 228 ya
descargadas, cualquier tope por debajo de 228 era una parada instantánea.

Dos consecuencias, y la segunda es peor: **la prueba en pequeño era imposible por
construcción**, y `--tope 800` no significaba 800 nuevas sino 800 menos lo que ya
hubiera. El sembrador del TEAC ya contaba por tanda; éste no.

Ahora el tope es **de la tanda**, y sólo cuenta lo que se le pide a la fuente:
una consulta que ya estaba en disco se apunta pero no gasta tope, porque el tope
existe para dosificar las peticiones.

## La prueba, con el comando exacto

```
$ python sembrar.py sembrar --tope 2
  [ 1/118] Ley 37/1992 art. 121 5 consulta(s): V0195-26, V2167-24, V2530-23, …
        + V2530-23
        + V1309-23
[tope] 2 consultas en esta tanda: se para aqui
siembra terminada: 2 nuevas en esta pasada, 230 en total
consultas guardadas : 243
```

Verificado en disco: V2530-23 (26 KB, 24.127 caracteres de contestación) y
V1309-23 (16 KB, 15.001). Consultas reales, completas y legibles.

---

# Fase 41 · La residencia es como el año, no como un aviso

Con el Codi tributari de Catalunya dentro, una pregunta de Renta o de Patrimonio
recuperaba artículos catalanes **sin que nadie hubiera dicho dónde vive el
cliente**. Y una deducción autonómica de otra comunidad no es «menos exacta»: es
de otro sitio. La respuesta salía impecable, con su cita literal y su enlace, y
estaba mal para el 84% de España.

## Por qué va donde va el año

**Un aviso al pie se lee una vez y se deja de ver.** El año está en la pregunta
porque es un dato que, si falta, hace que la respuesta salga impecable y
equivocada — y nadie lo nota. La comunidad falla exactamente igual, así que va al
lado, en la pregunta, y no en una nota debajo del texto.

## Por qué NO bloquea, que es la diferencia

**El año no tiene alternativa segura: cualquier año supuesto es un año
equivocado.** La comunidad sí la tiene — contestar sólo con lo estatal — y
entonces lo correcto no es bloquear, es **contestar y declarar lo que falta**.

Y hay una razón de fábrica: **la ventana no sabe de qué impuesto es la pregunta
hasta que el analizador la lee**, o sea después de pulsar. Hacerla obligatoria
«sólo cuando el impuesto tiene tramo autonómico» exigiría saber el impuesto antes
de tener el impuesto. Así que el campo es **siempre opcional**, y quien decide si
su ausencia cuesta algo es `fase4`, donde el impuesto ya se conoce:
`impuesto_tiene_autonomica()`. En una consulta de IVA no salta: un aviso que sale
siempre es decoración.

## La regla

| comunidad | qué se recupera |
|---|---|
| Cataluña | los preceptos catalanes **y** los estatales |
| vacía | **ninguno** autonómico, y se dice |
| Madrid u otra | **ninguno**, y se dice que sólo hay Cataluña cargada |

Medido con «deducción autonómica por alquiler»: con Cataluña salen 4 artículos
del Codi y el 612-3 es **el primero**; sin comunidad y con Madrid, **cero**, y las
dos dan exactamente el mismo resultado estatal.

**Ni por remisión se cuela.** La remisión cruza de impuesto —eso no se negocia—
pero no cruza de comunidad: un precepto catalán no entra en una consulta de
Madrid porque otro lo mencione.

## De dónde sale el dato

Del BOE, no de una lista: sus metadatos traen `ambito: Autonómico` y
`departamento: Comunidad Autónoma de Cataluña`. `parser.comunidad_de` recorta el
preámbulo administrativo y deja «Cataluña», que es lo que escribe una persona. El
día que entre normativa de otra comunidad funciona sin escribir nada.

**La lista de las 19 del desplegable no es una lista de cobertura**: es para
escribir más rápido. Lo que se cubre lo dice el corpus, `normas.comunidades()`, y
hoy es sólo Cataluña.

## La ausencia del campo significa estatal

Las doce normas estatales se ingirieron antes de que existiera `comunidad` y no
lo llevan. Reingerirlas sólo para escribir un campo vacío cambiaría **sus doce
sellos** —la herramienta que avisa de que el corpus se ha movido— a cambio de
nada. Sin comunidad, estatal: que además es el valor seguro.

## Y en la respuesta

La comunidad se ve **en el eco, junto al año y al modo**, y **viaja en lo que se
copia**, con su aviso si lo hubo. Una respuesta de Renta pegada en unas notas no
dice, por sí sola, si llevaba la deducción autonómica catalana o si salió
estatal.

## Un carácter invisible, otra vez

`"autonom" not in "autonómico".lower()` es **True**: la o lleva tilde. La primera
versión devolvía cadena vacía para todas las comunidades y parecía que el dato no
estaba en el BOE. Se pasa por `sin_tildes`, que es lo que hace el resto del
proyecto. Van dos con caracteres que no se ven — el espacio duro del BOE fue la
otra.

## Comprobaciones

```
16 suites verdes (la nueva: prueba_residencia, con tres controles negativos)
banco 25/31 con las mismas rojas · bateria 39/39 · fase4 5/5
llamadas a la API ... 0
```

---

# Fase 42 · El texto que una norma inserta en otra no es texto suyo

## El diagnóstico de partida no era el que había

La sospecha era: «el extractor busca la norma DELANTE de la referencia y hay
textos que la ponen detrás». **Medido, eso ya estaba resuelto.** `_ambito` mira
`texto[fin:fin+VENTANA]`, o sea **después** de la referencia, y desde la fase de
Sociedades tiene la rama `_RE_NORMA_DERIVADA_DELANTE`, que caza «se añade una
disposición adicional octava **al texto refundido** de la Ley del IS» y la deja
en PENDIENTE. Esa rama funciona: es la que produce las entradas
`[pendiente · externa]` que se ven junto a las malas.

## Lo que sí estaba roto

Leyendo el texto de la disposición final segunda de la LIRPF aparece el otro:

> …se añade una disposición adicional octava al texto refundido de la Ley del IS
> … **que quedará redactada de la siguiente manera: «Disposición adicional
> octava. Tipo de gravamen… lo establecido en la disposición adicional novena de
> esta Ley…»**

**El bloque entrecomillado es texto del TRLIS, no de la LIRPF.** Dentro de él,
«artículo 94» es el 94 del texto refundido y «de esta Ley» es el texto refundido.
El escáner lo leía como texto propio y lo resolvía **interno a la LIRPF**:
artículos reales, con texto real, que no son los que tocan — y el verificador los
daría por buenos, porque existen y dicen lo que dicen.

**103 remisiones resueltas a la norma equivocada**: 86 de la Ley del IRPF, 10 de
la del IS, 2 del Reglamento del IVA, 1 de la Ley del Patrimonio.

## La regla, general

`_bloques_ajenos`: los tramos entre « » cuya frase de apertura **nombra otra
norma**. Dentro de ellos no se resuelve nada como interno.

**No todo bloque entrecomillado es ajeno**, y esa es la mitad que evita el falso
positivo: lo normal es que una norma se modifique a sí misma —«se modifica el
artículo 95, que queda redactado así: «…»»— y ahí lo interno es correcto. Se
exige que la cabecera nombre otra norma y que no sea la suya.

Y dentro de un bloque ajeno se distingue: **una designación explícita sigue
valiendo** —«de la Ley 19/1991» es la Ley 19/1991 la cite quien la cite— pero una
autorreferencia —«de esta Ley»— es la norma ajena.

```
              sin la regla  con la regla
total                 5461          5461     <- no cambia: se detectan las mismas
resueltas             3556          3453     <- 103 dejan de resolverse MAL
externas               913          1027
declinadas             151           141
```

**Trece sellos intactos** —esto no toca el troceo—, batería 39/39, banco 25/31 con
las mismas rojas.

## Y una cifra mía que era vieja

Comparé contra un «antes» de 5.479 remisiones apuntado ayer y salía que el total
cambiaba, lo cual era imposible. Era una cifra anterior a la reingesta de la
catalana. Medido antes y después **en el mismo proceso**, el total no se mueve.
Una cifra de ayer no es una medida de hoy.

# El detector de anexos vuelve a tener banco

`pruebas/prueba_anexos.py`. Protege que el artículo 95 de la Ley del IVA remita
al **anexo del RDLeg 339/1990** —la definición de «automóvil de turismo», sin la
cual no se puede decir si el vehículo del cliente lo es— y que esa remisión se
detecte y quede PENDIENTE, con la norma nombrada.

**Los dos controles negativos rompen el código de verdad:**

- **quitar el detector entero**: el artículo 95 pasa de 1 remisión a anexo a **0**.
  Es el estado anterior a la fase 8, cuando el escaneo sólo miraba «artículo N» y
  disposiciones.
- **dejar de exigir el número de la norma**: de 36 remisiones a **45**, y las 9 de
  más son designaciones sin número —`Real Decreto Legislativo`, `Real Decreto`—
  que no identifican nada. Es la versión que colaba el título del propio anexo.

En el corpus: 41 preceptos mencionan «anexo» y sólo 36 son remisiones; ninguna se
da por RESUELTA, porque son normas que no tenemos.

## Comprobaciones

```
17 suites verdes · bateria 39/39 · fase4 5/5 · banco 25/31
trece sellos intactos · llamadas a la API ... 0
```

---

# Fase 43 · Un caso adversario sin su positivo se aprueba estrechando

## LA REGLA

**Cuando una regla puede fallar en dos direcciones, el caso adversario va
acompañado de su positivo.** Si sólo está el adversario, la forma más barata de
aprobarlo es estrechar la regla hasta que no resuelva nada — y eso pasa la prueba
mientras rompe el sistema en silencio.

De dónde sale: el resolutor aprendió a leer «Ley 35/2006 Impuesto sobre la Renta
de las Personas Físicas» —número y materia pegados, como escribe DYCTEA— porque
sin eso **147 criterios del TEAC estaban en la despensa sin poder encontrarse**.
Ese arreglo puede fallar por los dos lados:

| caso | esperado | qué protege |
|---|---|---|
| `u` · «Ley 29/1987 Impuesto sobre Sucesiones» (**no la tenemos**) | NO_VERIFICABLE | que «mande el número» no sea «que encaje con lo que sea» |
| `u2` · «Ley 35/2006 Impuesto sobre la Renta…» (**sí la tenemos**) | VERIFICADA | que arreglar el adversario no sea dejar de leer la designación |

Con sólo `u`, la forma más segura de aprobarlo habría sido revertir el arreglo, y
volverían los 147 inalcanzables. Con sólo `u2`, cualquier aflojamiento pasaría.

**Y el fragmento del positivo lo escribí de memoria y salió NO_VERIFICADA**: el
verificador haciendo su trabajo sobre mi propio caso de prueba. Copiado del
corpus, y anotado dentro del caso para que no se repita.

# La puerta de alcanzabilidad, y por qué mide la tanda

**Bajar y no poder encontrarlo ocupa disco, parece cobertura y no lo es.** 118
criterios se sembraron así y se descubrió **tres días después**, mirando a mano.
Desde ahora, cada tanda dice cuánto de lo bajado se puede encontrar por (norma,
artículo), y si no es el 100% devuelve código 1 y la cadena para.

**Mide la tanda, no el acumulado.** Con el acumulado la cadena pararía siempre
por los 65 que ya sabemos que no se leen —prosa del campo `normativa` de la DGT,
diagnosticada y pendiente—, y **una puerta que salta siempre se acaba
ignorando**. Lo que hay que cazar es material nuevo que se baje y no se encuentre.

# El plan de la segunda tanda

**543 artículos**, tres filtros en este orden:

1. **Sólo lo recuperable** — fuera Sucesiones (72), ITP (26), medios de transporte
   (1) y residuos (1): 100 artículos de golpe, sin perder nada, porque el agente
   no los saca nunca.
2. **Ni el articulado de los decretos aprobatorios.**
3. **Sólo lo que da señal**: 2 o más remisiones entrantes, o presencia en el
   banco. **450 entran por remisiones y 29 sólo por el banco.**

El umbral sale de la distribución: 810 artículos tienen 1+ remisión, 500 tienen
2+, 341 tienen 3+. Con 1 entra casi la mitad del corpus elegible y la cola son
artículos mencionados una vez de pasada.

Es la misma idea que la reserva de las remisiones: **lo que decide es a quién se
le llama, no a quién se parece.**

```
GENERAL 219 · IVA 139 · IRPF 104 · IS 74 · IP 7
```

---

# La despensa viaja por git, y eso caduca

En la oficina no hay USB: se instala con `git pull`. Así que las consultas de
la DGT y las resoluciones del TEAC —62 MB, 2.100 ficheros— están versionadas.
Todo lo demás de `datos/` sigue fuera, y **las trazas especialmente: son dudas
reales de clientes y no salen del despacho**.

De la propia despensa tampoco viaja todo. El HTML tal cual —`datos/dgt/crudo`
y `datos/teac/crudo`— son 67 MB de los 134 y **no los lee nadie en marcha**:
sólo la ingesta, para poder volver a mirarlos. Se quedan aquí.

## LA CONDICIÓN QUE CADUCA, y es la que hay que vigilar

**Esto vale mientras la despensa esté sembrada POR PLAN.** Hoy se siembra
contra una lista de artículos decidida por datos —`plan_siembra.py`—, así que
lo que hay en `datos/dgt` es un catálogo de documentos públicos elegidos por
un criterio, no un rastro de nada.

**El día que exista la cola de descarga por demanda, esto deja de valer.**
Entonces la despensa reflejará *lo que el departamento ha preguntado de
verdad*: qué consultas se bajaron, en qué orden y cuándo. Eso ya no es un
catálogo público, es el historial de trabajo del despacho deducible de los
metadatos —y de las fechas de descarga—, y **no puede viajar por un
repositorio**, ni siquiera privado.

Cuando llegue ese día, las opciones son las de abajo, y hay que elegir antes
de que la primera descarga por demanda entre en un commit.

## Lo que cuesta, medido

| | |
|---|---|
| repositorio sin despensa | 4,1 MB |
| despensa que viaja | 62,4 MB en 2.096 ficheros |
| un clon nuevo, comprimido | 31 MB |
| lo que NO viaja (crudo) | 67 MB |

Git guarda la historia entera: **cada tanda de siembra engorda el repositorio
para siempre**, aunque el fichero cambie o se borre después. Con la siembra
llena —543 artículos por 5 consultas— la despensa tiende a ~2.700 documentos,
y con las resiembras que vengan, el repositorio crece de forma monótona.


---

# Cuando el instrumento no puede medir lo que importa

El banco mide **puesto**: «el artículo X entre los N primeros». Es la vara que
ha servido para todo, y por eso fue la primera que cogí para comprobar el suelo
de estatales.

No servía. **El suelo no garantiza puesto, garantiza presencia**: que en lo que
se le manda al redactor haya base estatal del impuesto de la pregunta. Medido
con la vara del puesto, el suelo es invisible — se aplicó y no movió ni un caso
del bloque 1. Predije que el caso de ISD art. 20 se pondría verde y no se puso,
porque ese artículo ya estaba dentro del corte, en el puesto 4: el suelo
promocionó otro estatal al 6 y no lo tocó.

De ahí salieron dos tentaciones, y las dos habrían sido un error:

- **bajar el listón del caso** de «entre los 3 primeros» a «entre los 6», para
  que el suelo se viera; o
- **dar el suelo por bueno** porque las mediciones sueltas decían que
  funcionaba, aunque ningún caso del banco lo comprobara.

La primera cambia una expectativa para que quepa en el resultado. La segunda
deja viva una salvaguarda que **nadie puede ver fallar**, que es como se acaba
descubriendo tres meses después que llevaba semanas apagada.

> **Cuando el instrumento no puede medir la propiedad que importa, se amplía el
> instrumento. No se ajusta la propiedad para que quepa en el instrumento.**

El bloque 1B es esa ampliación: una clase de caso nueva —«en el material
enviado hay al menos N preceptos estatales del impuesto de la pregunta»— que se
pone verde cuando el suelo funciona y roja cuando se apaga. Comprobado
apagándolo: los dos casos de Sucesiones pasan de 1 a 0.

**Y a la primera encontró algo que no sabíamos**: el tercer caso —el tipo de
gravamen del ITP— sigue en cero *con el suelo puesto*. El suelo mete la ley
estatal en el corte de seis, pero la selección por pertinencia la descarta
después. La salvaguarda llega menos lejos de lo que creíamos, y eso no lo dijo
ningún razonamiento: lo dijo el instrumento nuevo el día que existió.


---

# Pendiente: un término rarísimo que no es del asunto puede llevarse una pregunta

**Qué se vio.** Tras ingerir Sucesiones e ITP, el caso «qué ocurre si Hacienda
no resuelve en el plazo máximo» pasó de verde a rojo sin que nadie tocara la
recuperación. Lo adelanta el artículo 26 del Reglamento del ITP —«Cuentas de
crédito»—, con 8,08 puntos contra 4,23. **De esos 8,08, cinco con nueve vienen
de la palabra «ocurre»**: el artículo dice «como *ocurre* en el caso de las
cuentas de crédito». No comparte con la pregunta ni un término fiscal.

**Por qué.** Esa palabra está en **1 precepto de 2.386**, y ese uno entró con el
Reglamento del ITP; antes había cero. Con cero documentos no aportaba nada al
ranking; con uno, su idf se dispara —es lo que BM25 hace con un término
rarísimo— y ese único documento se lleva la pregunta.

**Cuánto muerde, medido y no supuesto.** Menos de lo que escribí la primera vez.
El artículo correcto **llega al material hasta con la pregunta cruda** (puesto 4
de un corte de 6), y con los términos que el analizador manda en producción
—«plazo de resolución», «silencio administrativo»— sale **el primero**. Así que
la debilidad sólo se manifiesta en el bloque 1 del banco, que puentea el
analizador a propósito.

## La tentación, que es la de siempre

El arreglo evidente es **añadir «ocurre» a la lista de palabras vacías**.

Sería **la sexta lista escrita a mano de la semana** —después de los códigos de
impuesto, el mapa de DYCTEA, las tres normas del lanzador, los precios y las
frases de cobertura—, y tendría el mismo final que todas: **la próxima palabra
tampoco estaría**. Mañana alguien pregunta «¿qué **sucede** si…», o «¿cómo
**afecta** que…», y hay que volver a escribirla.

> Si algún día se ataca, tiene que ser **por una propiedad**: qué distingue una
> palabra del asunto de una palabra de la forma de preguntar. No por una lista.

Alguna dirección posible, para cuando se mire: un término que aparece en **un
solo documento de todo el corpus** no está discriminando entre documentos, está
señalando a uno; y un término que no aparece en **ningún título ni rúbrica** de
ninguna norma difícilmente es del asunto. Las dos son propiedades medibles sobre
el propio corpus, no listas.

## ISD art. 3: pocos términos exclusivos pierden contra muchos compartidos

**Va aquí porque es la otra cara de lo mismo**: aquel caso era un término
rarísimo que se lleva una pregunta que no es suya; éste es un artículo que dice
justo lo que se pregunta y pierde por cubrir *poco*. Los dos son sobre qué
premia BM25F cuando se le da una consulta larga.

**Es la primera evidencia MEDIDA de esto**, y por eso se anota aunque no se
ataque hoy. Hasta ahora era una sospecha razonable; el bloque 5 del 14/08/2026
la convirtió en números.

«Un padre quiere donar dinero a su hijo, ¿tributa?». El analizador propone siete
grupos de términos —donación, adquisición lucrativa inter vivos, sujeto pasivo
donatario, base imponible donación metálico, reducción parentesco descendiente,
devengo, reducción autonómica—, que son **diecisiete raíces**. Y son buenos: no
hay ninguna que no esté en el corpus.

| | toca | de | puntos | rúbrica |
|---|---|---|---|---|
| art. 20 | 13 | 17 | 21,66 | Base liquidable. |
| art. 5 | 8 | 17 | 19,46 | Sujetos pasivos. |
| **art. 3** | **4** | **17** | **7,32** | Hecho imponible. |

**El art. 3 contiene la respuesta literal** —«la adquisición de bienes y derechos
por donación o cualquier otro negocio jurídico a título gratuito, intervivos»—
y se queda en el 34% del primero, puesto 15 de 50.

Lo que le pasa es que **los siete grupos describen el camino entero de la
respuesta** y el art. 3 sólo cubre el primer tramo, el «qué se grava». Cada
tramo restante —quién paga, sobre qué base, qué reducción— tiene su propio
artículo, y cada uno de ésos cubre más raíces que él.

**Dos sospechas descartadas con datos**, que es lo que hace que esto sirva:

- **No es la longitud.** Con `b=0,75` ser corto **multiplica**: el art. 3, con 60
  tokens contra 168 de media, cobra ×1,93 por término, mientras un rival de 290
  cobra ×0,65. Los cortos ya están favorecidos. Tocar la normalización iría en
  la dirección contraria a la que parece.
- **No es el suelo de estatales.** Los seis primeros son todos de la propia Ley
  29/1987: la competencia es dentro del mismo impuesto y no hay ninguna
  autonómica que desplazar.

**Lo que sí se confirmó**: la rúbrica. «Hecho imponible.» comparte **una sola**
raíz con la consulta, y el título pesa 4,0 —el máximo de los tres campos—, así
que no aparecer ahí se paga caro.

> Si algún día se ataca, la pregunta es si **cubrir pocas raíces pero exclusivas**
> debería valer tanto como cubrir muchas compartidas. Hoy no vale, y ésta es la
> primera vez que hay un caso medido para discutirlo.

---

# Pendiente: ISD art. 31 depende de ingerir el Reglamento del ISD

**No es un problema de recuperación y conviene que no se trate como tal.**

«¿Cuánto plazo hay para presentar el impuesto de una herencia?». El artículo que
el banco espera —Ley 29/1987 art. 31— **no tiene la respuesta**. Dice:

> …en los plazos y en la forma que **reglamentariamente se fijen**.

Los seis meses están en el **Reglamento del ISD (RD 1629/1991)**, que **no está
en el corpus**: se quedó fuera porque titula sus artículos «Art 1» y el troceador
no lo reconoce. Se comprobó buscando «seis meses» junto a sucesión, herencia,
fallecimiento o causante en las dieciséis normas: **ningún precepto del corpus da
ese plazo**.

Subir el art. 31 al puesto 1 no arreglaría nada — llevaría al redactor a una
remisión. **Este caso se desbloquea ingiriendo el Reglamento, no tocando el
buscador**, y hasta entonces su rojo es honesto: dice que falta una norma.

Queda emparejado con el pendiente del troceador y la numeración «Art 1».

No se toca hoy.


---

# Una suite que afirma sobre datos que crecen se pudre en cada siembra

`prueba_asunto` estuvo días en rojo sin que nadie tocara el código. Se escribió
cuando la despensa tenía **nueve** criterios del TEAC, y una de sus
comprobaciones era que para una consulta rara **no se seleccionara ninguno**.
La siembra la llevó a **novecientos nueve**, entró una resolución del TEAR de
Valencia sobre el artículo 80, y la comprobación se puso roja.

**El sistema no estaba fallando.** Hacía justo lo correcto: sacar esa
resolución diciendo *«coincide el artículo, PERO no se ha comprobado que trate
del mismo supuesto: compruébalo tú»*. Lo que se había movido eran los datos
debajo de la afirmación.

> **Lo que se AFIRMA va contra un fixture. La caché real sólo vale para
> comprobar FORMA, o propiedades universales que no dependen de qué haya
> dentro.**

## Los tres tipos, que no son lo mismo

| | ejemplo | dónde va |
|---|---|---|
| **afirmación sobre contenido** | «no se selecciona ninguno», «existe un TEAC no vinculante» | **fixture** |
| **propiedad universal** | «ninguna regional se presenta como criterio del TEAC», «el orden por peso es monótono» | caché real: se refuerza con cada documento nuevo |
| **integridad de la despensa** | «todos los fragmentos guardados son literales en su documento» | caché real, por definición |

`prueba_recorte` es del tercer tipo y por eso **sigue leyendo la despensa**: lo
que comprueba es que la copia local sea coherente consigo misma. Si un día se
pone roja, no será podredumbre: será que un documento recién bajado tiene un
fragmento que no está en su original, que es exactamente lo que queremos saber.

## Y los fixtures se copian, nunca se escriben

Los criterios de `casos/teac_asunto` y `casos/teac_unidad` están **copiados tal
cual** de `datos/teac`: número, fecha y texto auténticos. Una resolución
inventada con número de verdad es lo peor que puede entrar en un repositorio
fiscal.

Por eso mismo cada carpeta lleva un LEEME diciendo con todas las letras que
**no es la copia de trabajo**: justo porque son auténticos, por dentro no hay
forma de distinguirlos. Y no se mezclan con `casos/teac_prueba`, donde viven
tres criterios **inventados** (9001, 9002, 9003): en la misma carpeta sería
cuestión de tiempo que alguien citara el 9001 creyendo que existe.

## Una cosa más: el fixture se elige para poder AFIRMAR

En `casos/teac_asunto` **no está** la resolución que rompió la suite
—46/03942/2023—, y no es un descuido. El bloque que comprueba «cuando ninguna
viene al caso, se avisa en vez de callar» no puede comprobarse con ella dentro,
porque siempre habría una que sale. **Meter en el fixture justo el documento
que impide la comprobación sería fijar el accidente en vez del comportamiento.**


---

# Una promoción sin criterio, no dos piezas peleándose

El bloque 1B destapó que el suelo de estatales metía la ley del ITP en el corte
de seis y `seleccionar_material` la descartaba después. Lo escribí como *«una
salvaguarda que otra pieza deshace»*, y al medirlo **el diagnóstico era otro**.

**El suelo promovía por «ser estatal», no por «venir al caso».** Cogía los
mejores estatales que quedaran fuera del corte, sin preguntarse si contestaban.
De siete promociones, el corte tiraba cinco — y lo que metía era relleno:
«responsables subsidiarios» en una pregunta sobre reducciones, «actos
equiparados a hipotecas» en una sobre el tipo de gravamen. El corte hacía bien
su trabajo; el suelo hacía mal el suyo.

## El arreglo evidente, probado y revertido

Que el suelo pregunte antes lo mismo que preguntará el corte. Una línea, y deja
el sistema coherente consigo mismo. Medido sobre veinte preguntas:

```
consultas con material extra : 4 de 20  (6 preceptos)
consultas que pierden algo   : 0
```

Dos de los seis eran los buenos: el art. 9 del ISD (base imponible) y el art. 31
del ITP (documentos notariales). **Los otros cuatro, relleno**: «beneficios
fiscales» y «beneficios generales» en una pregunta sobre el tipo de gravamen, y
arrastrando por remisión el art. 67 de la LGT —cómputo de plazos de
prescripción—, que no pinta nada ahí.

Y el caso del bloque 1B **se puso verde con ese relleno**: había un precepto
estatal de ITP en el material, sí, pero era «beneficios fiscales», no la base.

> **Un verde por relleno es peor que un rojo honesto.** Revertido.

## Lo que queda, y por qué es mejor así

El caso sigue rojo, con el motivo verdadero escrito: para esa pregunta **no hay
base estatal pertinente** en el corte. Los estatales que hay cubren el 40 % de
lo que cubre el primero y el corte pide el 70 %. No es que una pieza deshaga a
la otra: es que esa respuesta, hoy, no tiene base estatal que traer.

Y la lección de método, que es la que se repite: **filtrar por una propiedad
débil no es filtrar**. La cobertura de términos sirve para descartar lo que no
comparte nada con la pregunta; no sirve para decidir qué es la base de un
impuesto. Cambiar el criterio del suelo por otro igual de débil sólo cambia qué
relleno entra.


---

# FASE 34 · UN PLAN SE AGOTA POR LO QUE SE BAJA, NO POR LO QUE QUEDA

La cadena de siembra llevaba once horas corriendo y estaba a punto de hacer
cuatro tandas más. El problema es que no quedaba nada que traer:

```
tanda 1  ·  140 consultas
tanda 2  ·  nada nuevo
tanda 3  ·  nada nuevo
```

Y no era mala suerte. **La tanda 1 bajó 140 con un tope de 300: no llegó al
tope, luego no quedaba cola.** Desde ese momento el trabajo estaba hecho, y las
cuatro tandas restantes eran **unas 2.200 peticiones a un servicio público para
traer cero consultas**.

## Lo que estaba mal no era el número de tandas

La tentación era bajar el 7 a un 3. Habría funcionado hoy y habría vuelto a
fallar la próxima vez, porque el 7 nunca fue el problema: **la cadena terminaba
cuando se acababan las TANDAS, no cuando se acababa el TRABAJO**. Con siete
tandas y trabajo para nueve se queda corta; con siete y trabajo para una,
sobran seis.

Ahora `sembrar.py` devuelve un código propio cuando una tanda entera no baja
nada:

| código | significa | la cadena |
|---|---|---|
| `0` | tanda correcta | sigue |
| `1` | algo bajado no se puede encontrar | **para** (avería) |
| `2` | plan agotado | **termina bien** |

Que sea un código **propio** y no un `0` es el punto. `0` significa «sigue» y
`1` significa «algo va mal»; esto no es ninguna de las dos —es «ya está»— y
quien encadena tiene que poder distinguirlo para terminar limpio en vez de
parecer una avería.

## Y de paso: «sin resultados» no es «forma inesperada»

En el log había **211 avisos de FORMA INESPERADA**, que suena a que la fuente ha
cambiado bajo nuestros pies. Eran **53 artículos, repetidos una vez por
pasada**.

El detector distinguía las dos cosas —el comentario lo decía— pero buscaba
estas tres frases:

```
«sin resultados»  ·  «no se han encontrado»  ·  «0 documentos»
```

Perfectamente plausibles. **Ninguna de las tres es la que dice PETETE**, que
devuelve 123 bytes con:

> La consulta realizada no devuelve resultados.

Así que los 53 artículos sin doctrina salían por la rama del aviso. **Un aviso
que salta 211 veces no avisa**: se ignora, y el día que la plantilla cambie de
verdad se perderá ahí dentro.

**Medido, no supuesto.** `medir_sin_resultados.py` rehizo las 53 búsquedas y
guardó el crudo en `casos/petete_vacias`:

| | |
|---|---|
| artículos remedidos | 53 de 53, sin un solo fallo |
| sin consultas (dato normal) | **53** |
| forma inesperada de verdad | **0** |
| tamaños distintos de página | uno solo: 118 bytes |

Los 53 son la misma página. **De las 211, no queda ninguna.**

El informe de cada tanda ahora los separa: los artículos sin consultas se
cuentan en una línea y ya, y el bloque de aviso solo aparece si hay algo que
avisar. Y el crudo guardado sirve para que `prueba_petete` lo compruebe sin
pedir nada —con un control que impide pasarse de listo: una página **muda**,
que no trae resultados y tampoco dice que no los haya, sigue siendo una rareza.

## La tapa del portátil

Ver la sección de la fase 17. `caffeinate -i` no cubre cerrar la tapa, y por eso
la tanda 3 pasó siete horas dormida.

---

# FASE 35 · «ESCRÍBEMELO PARA EL CLIENTE», Y POR QUÉ NO SE HIZO EL RESTO

Chus pidió poder añadir algo después de preguntar. Al separarlo salieron **tres
cosas distintas**, y sólo se ha construido una:

| | qué es | llamadas | estado |
|---|---|---|---|
| **A** · precisar | misma pregunta con más contexto | 2-3 | **no se hace** |
| **B** · sobre la respuesta | pregunta nueva, material nuevo | 2-3 | **no se hace** |
| **C** · otra forma | mismo material, sólo redacción | **1** | hecha |

## El principio que ordena las tres

**El hilo es de preguntas, no de respuestas.** Cada respuesta se genera entera y
se verifica entera. Nunca se añade texto a una respuesta ya dada, porque
entonces habría texto verificado y sin verificar en la misma pantalla.

De ahí sale que las tres son **consultas nuevas**; lo único que cambia es qué se
reutiliza de la anterior.

## A y B, ya construidas — y por qué se esperó

**La sospecha era que la gente reformula porque no encuentra criterio, no porque
quiera conversar.** Si fuera eso, el hilo sería el *síntoma* y la cobertura la
enfermedad, y construir A y B habría sido **automatizar una frustración**. Por
eso primero se midió.

Y no hizo falta construir la conversación para medirla: **el hilo ya ocurría a
mano**. Alguien pregunta, no le convence, reescribe y vuelve a preguntar, y eso
deja dos trazas seguidas y parecidas. `medir_hilo.py` las cuenta.

La primera medición, con lo poco que había (19 consultas reales de una persona,
del 2 al 11 de agosto):

```
pares de la misma sesión (<15 min) : 12
de esos, REFORMULACIONES           :  1
y de esas, TRAS UNA CONSULTA SIN CRITERIO: 1 de 1
```

**Un caso no decide nada** — se deja escrito para que nadie lo lea como
conclusión. Con esa base tan corta, lo que resolvió fue el departamento
pidiéndolo otra vez, no el número.

`medir_hilo.py` sigue en pie y **ahora mide las dos cosas, en bloques
separados**: los hilos que él *infiere* (umbral de parecido, ventana de quince
minutos) y los que la ventana *declara* en `hilo.json`. No se suman. Son bases
distintas, y mezclar bases entre mediciones es lo que ya nos hizo tomar dos
decisiones malas.

### Cómo funciona una vuelta

Debajo de la respuesta hay una caja: **«Añadir contexto o preguntar algo más»**.
Sólo aparece cuando hay una respuesta aceptada en pantalla — sobre un «no
encontrado» no hay nada que continuar, y para eso ya está la caja de arriba.

Al enviar, **la caja de arriba no se vacía**: la pregunta anterior sigue ahí y
debajo se le añade la línea nueva. Eso es lo que hace que se sienta como seguir
hablando. Y la pregunta compuesta está **a la vista**: si se compusiera por
dentro, quien pregunta no sabría con qué texto se le está contestando. El año y
la comunidad se heredan y **siguen editables**, por si el caso resulta ser de
otro ejercicio.

Al enviar se vuelve a la pantalla de preguntar. No es cosmético: **la barra de
progreso y el «buscando en...» viven ahí**. Lanzando desde la pantalla de leer,
la vuelta correría entera detrás de una respuesta vieja y sin ninguna señal de
que algo está pasando — que es justo lo que el departamento pidió arreglar.

El modo se hereda también: si la primera vuelta se hizo con criterio
administrativo, la segunda también. Es la misma consulta. Y **una consulta nueva
vuelve a la vuelta 1**: sin eso el número se quedaba pegado de la conversación
anterior y una consulta recién empezada se copiaba como «vuelta 4», que es una
etiqueta falsa en un correo que alguien va a leer dentro de meses.

Por debajo, **cada vuelta es una consulta entera**: se reanaliza, se vuelve a
buscar, se redacta y se verifica de cero. **Nunca se reutiliza el material de la
vuelta anterior**, y ésa es la diferencia con un chatbot: si el contexto nuevo
cambia qué artículos aplican — «y si fuera una furgoneta» — reutilizarlos daría
una respuesta *segura* sobre los artículos *equivocados*, que es peor que no
contestar.

Lo único que viaja de una vuelta a otra es contexto para **el analizador**: el
resumen de la duda anterior y los preceptos que se usaron. No la respuesta
entera. **Al redactor no le llega nada del hilo** — recibe el mismo prompt de
siempre y sólo el material recién buscado.

Cada vuelta deja **su propio expediente**, con `viene_de`, `tipo:
continuacion` y su verificación propia. El hilo se reconstruye desde el disco,
que es donde tiene que estar: dentro de seis meses la memoria de la ventana no
existe y el expediente sí.

### El techo de llamadas

El tope de 6 llamadas **protege la consulta, y nadie cuenta la sesión**.
Conversar multiplica las consultas por sesión, que es exactamente el escenario
que ya rompió esto una vez: a partir de la tercera pregunta el agente dejaba de
contestar y no se recuperaba hasta cerrar la ventana.

`pruebas/prueba_hilo.py` corre **seis vueltas seguidas con el mismo motor** —
doce llamadas, el triple del techo — y comprueba que ninguna se queda a medias.
Y lleva su control negativo: con `empezar_consulta` doblado para que no
reinicie, **las vueltas 4, 5 y 6 se caen**. Sin eso, la prueba sería verde por
casualidad.

### Y con el modelo de verdad

Todo lo anterior se construyó con el motor de ensayo, que redacta con reglas
fijas. Eso prueba el andamiaje y **no prueba** lo único que un motor de reglas no
puede tener: si el modelo *entiende* que la pregunta viene de otra.
`medir_hilo_real.py` lo mide (por defecto no gasta; con `--con-modelo` sí).

Dos vueltas: un turismo usado por un comercial, y luego **«¿y si fuera una
furgoneta de reparto?»**.

| | vuelta 1 | vuelta 2 |
|---|---|---|
| impuesto / ejercicio | IVA / 2023 | IVA / 2023 |
| preceptos enviados | 95, 101, 9 | 95 |
| veredicto | ACEPTADO | ACEPTADO |

**Clasifica bien con la pregunta en dos partes.** Mismo impuesto y mismo
ejercicio, sin que la línea añadida lo despiste.

**Los términos recogen el contexto**, no lo repiten. Aparece
`vehiculo mixto transporte de mercancias`, que en la vuelta 1 no existía;
`representante o agente comercial` se mantiene, que es lo que debe mantenerse.

**La respuesta se sostiene sola.** Ni un «como se dijo antes». La vuelta 2
vuelve a resolver el turismo *y* añade la furgoneta, con sus citas propias — que
es lo que tiene que hacer, porque en pantalla sólo está la última.

**Y el resumen de la duda anterior basta.** Se le pasó *«Se pregunta en qué
porcentaje puede deducirse el IVA soportado en la adquisición de un turismo
utilizado por un comercial…»* y entendió *«…y si la respuesta cambia tratándose
de una furgoneta de reparto de mercancías»*. El material **cambió**: de tres
preceptos a uno, el 95, que es donde están las dos reglas.

Coste real de la pasada: 4 llamadas, **$0,247 · 0,23 €**.

### La frontera, que no se afloja porque el formato sea más suelto

Conversar invita a preguntar **«¿y tú qué harías?»**. El sistema aporta
respaldo, no conclusión.

El caso adversario está en la suite, entero. La respuesta que **decide**:

> «Yo en tu caso me acogería a la deducción del 100 por cien: es lo que hace
> todo el mundo y Hacienda no suele entrar.»

se cae con el motivo de siempre — *el texto no contiene ninguna cita con
fragmento literal: sin fuente no hay respuesta* — y no llega a pantalla, ni en
una consulta suelta ni en una continuación. La que **aporta el material sin
decidir** pasa: cita el artículo 95 literal y deja la valoración donde va, en el
expediente y en quien decide.

Lo que sostiene esto no es un filtro nuevo: es que **el hilo no toca el prompt
del redactor**. La suite lo comprueba comparando el sistema que se le pasa en
cada vuelta contra `RED.SISTEMA` — tienen que ser idénticos.

## Y las tres preguntas que quedaban abiertas

- **El hilo en pantalla**: sólo la última respuesta. Lo anterior puede estar
  superado, y mezclar en una pantalla lo vigente con lo descartado es el mismo
  error que mezclar lo verificado con lo que no lo está.
- **Dónde se corta**: no hay hilo que cortar. C reescribe **la respuesta que
  está en pantalla**, y ahí se acaba.
- **El idioma**: C responde en el idioma de la pregunta, como todo lo demás. La
  pregunta va dentro del material, así que el redactor ya lo sabe; no hay nada
  que decidir aparte.

## La siembra no gasta tokens

**Cero llamadas a la API de Anthropic.** La duda vuelve cada pocas semanas, así
que queda escrito aquí.

Sembrar es bajar consultas de la DGT de **PETETE** y resoluciones de **DYCTEA**:
dos servicios públicos, por HTTP, sin modelo de por medio. Lo que cuesta es
**tiempo y respeto a la fuente** — pausa de 10 s entre peticiones, User-Agent que
nos identifica, TLS nunca desactivado— no dinero.

Lo que gasta tokens es **contestar**: analizar la pregunta y redactar la
respuesta. Eso son dos llamadas por consulta y está medido aparte. La despensa
puede crecer toda la noche sin que la cuenta se mueva un céntimo.

## El refresco: lo que envejece, por detrás de lo que falta

Nada volvía a mirar un artículo ya sembrado. PETETE y DYCTEA publican cada
semana, así que un artículo con criterio de agosto se quedaba con el de agosto
para siempre.

### El umbral, medido

Sobre las 1.501 consultas de la despensa y sus fechas. La pregunta: *si refresco
un artículo cada N días, ¿qué proporción de esos refrescos trae algo nuevo?*

De los **848** artículos con criterio, se han movido:

| en los últimos | artículos |
|---|---|
| 6 meses | 342 (40 %) |
| 12 meses | 411 (48 %) |
| 24 meses | 477 (56 %) |

**La mitad no se mueve nunca** — en el percentil 25, su última consulta es de
2020 o antes. Refrescando sólo los 480 que sí se mueven:

| cada | refrescos que traen algo | peticiones/año si se barriera |
|---|---|---|
| 30 días | 13 % | ~5.800 |
| 90 días | 28 % | ~1.900 |
| 120 días | 33 % | ~1.500 |
| **180 días** | **39 %** | ~1.000 |

**180 días.** Cuatro de cada diez refrescos traen algo, que para una cola que va
por detrás de todo lo demás es buena proporción.

### Y sólo lo que se pregunta

La cola **no barre la despensa**: apunta para refrescar únicamente los artículos
que aparecen en una consulta real. Refrescar lo que nadie usa es sembrar a ciegas
por la puerta de atrás, que es justo lo que se decidió no hacer.

### El reloj es la fecha del criterio, no la de hoy

Un artículo se apunta con `buscado` puesto a **la fecha de la consulta más nueva
que tenemos de él**. Si se pusiera hoy, uno cuya última consulta es de 2020
esperaría otros 180 días para que alguien lo mirara: seis años de retraso más
medio año. Con la fecha del criterio, ese sale a refrescar **la primera vez que
alguien pregunta por él**, y uno con criterio de la semana pasada no sale hasta
dentro de seis meses.

### Primero lo que falta

Tres prioridades en la cola: **pendiente** (no hay nada) → **sin resultados**
(se buscó y no había, se reintenta a los 90 días) → **refresco** (hay, pero es
viejo). Sin ese orden, un refresco podría colarse delante de un artículo del que
no hay nada, y quien preguntó por ése se queda sin nada mientras se gasta la
petición en mejorar lo que ya se le pudo contestar.

Los dos controles negativos están en `pruebas/prueba_cola.py`: si el refresco
pierde su prioridad, o si el reloj pasa a ser hoy, la suite se cae.

## El título y los botones: dos frases que envejecieron

**El título decía «Consulta fiscal — IVA» con seis impuestos dentro.** La cuarta
de esta familia. Ahora sale del corpus: `cobertura.titulo(ix)` cuenta los
impuestos cubiertos y da *«Consulta fiscal — 6 impuestos»*.

**Un impuesto cuenta cuando hay un cuerpo dedicado a él**, no cuando aparece un
artículo suelto que habla de él. Contando precepto a precepto salían **nueve**, y
dos con un solo artículo: el 661-1 y el 671-1 del libro sexto del Código
tributario de Catalunya, adaptaciones autonómicas dentro de otra norma. Decir que
el agente «cubre el impuesto sobre determinados medios de transporte» porque
tiene un artículo sobre su tipo de gravamen es la clase de promesa que este
proyecto existe para no hacer. La regla es estructural y da seis.

Barridas también: el titular de la ventana, el «esta herramienta solo tiene la
Ley y el Reglamento del IVA» del no-encontrado, el título de la guía y su
párrafo de «tres normas dentro».

### El botón del criterio pasa a ser el principal — 21/08/2026

**Esto invierte una decisión deliberada, y el motivo viejo se borra entero a
propósito**: dejarlo escrito haría que alguien lo «arreglara» de vuelta en tres
meses leyendo un razonamiento que ya no aplica — como estuvo a punto de pasar con
el orden de los botones.

*Lo que decía antes, y por qué valía:* el de criterio era el caro —0,24 $ contra
0,14 $—, el dinero escaseaba y el precio estaba en pantalla, así que se puso
debajo y en gris para que no se pulsara por inercia. Correcto cuando cada
consulta se pensaba dos veces.

*Lo que vale ahora:* paga el despacho, el gasto está asumido —por eso ya se quitó
el bloque de precios de «Qué hay dentro»— y lo que el departamento quiere es **el
criterio**. La ley sola contesta qué dice la norma; el criterio dice cómo se ha
venido aplicando, que es lo que hace falta para decidir. **Poner el más útil
debajo y en gris es esconder el producto.**

El de la ley no desaparece: baja a secundario, con su pie —*«sin criterio: más
rápido, para dudas de puro texto»*— y sigue primero en el orden de tabulación.

Y un arreglo que hacía falta al invertirlos: **«Consultando...» iba fijo en el
botón de la ley**, así que al subir el de criterio, quien pulsaba arriba veía
cambiar el de abajo. Ahora la señal aparece donde se acaba de hacer clic.

## Cómo se entera la oficina de que hay criterio nuevo

La despensa la llena el Mac y viaja por git, así que en la oficina el criterio
nuevo aparece **de golpe al hacer pull** — y hasta ahora no había nada que lo
dijera ni nada con que traerlo sin terminal. Dos piezas, y **ninguna actualiza
sola**.

### (a) El aviso

Al abrir: *«Han entrado 40 documentos de criterio nuevos desde el 20/08. Ya se
usan al pulsar Consultar también el criterio.»* Compara con la cuenta de la
última apertura, guardada en `datos/dgt/visto.json` — que **no viaja**: es de ese
equipo. No toca git ni la red.

**La primera vez no dice nada**, a propósito: sin marca anterior la única cuenta
honrada sería «hay 2.400», que es un inventario y no una novedad, y el inventario
ya está en «Qué hay dentro».

### (b) `actualizar.bat`, que lo pulsa una persona

El orden de las comprobaciones **es el arreglo**: todo lo que sólo *mira* va
antes de lo que puede *romper*.

1. hay git · 2. es un repositorio · 3. **`core.longpaths`** · 4. **nada sin
guardar** · 5. **`git fetch`**, que no toca el árbol de trabajo · 6. y sólo
entonces `git pull --ff-only`.

- **Si el remoto no contesta** —repositorio privado sin credenciales, red de la
  oficina, contraseña caducada— falla en el paso 5, **sin haber movido nada**, y
  se dice en cristiano: *«No se ha tocado nada: el agente sigue igual que
  antes»*.
- **Si hay cambios sin guardar**, se para y los lista. No decide por nadie.
- **Si el pull falla igualmente**, dice que el agente sigue funcionando con la
  versión que ya tenía, y manda a `diagnostico`.

`--ff-only` a propósito: no inventa una fusión en el equipo de nadie.

### Lo de los nombres largos: no se había hecho, y era esto

**Nueve ficheros de 216 caracteres** en `casos/petete_vacias/`, todos en git.
Windows corta a 260 **contando la carpeta del usuario**, así que `git checkout`
habría abortado a mitad —*«unable to checkout working tree»*— dejando medio árbol
escrito. `actualizar.bat` habría chocado ahí en su primer uso.

Arreglado en los dos sitios: los nueve renombrados (216 → 85) y **el generador
capado**, porque si no volverían a aparecer. Se recorta **por en medio**: lo que
distingue un caso es el número de artículo, que va al final. Ninguna ruta del
repositorio pasa ya de 150.

Los 53 ficheros de esa carpeta son **byte a byte idénticos** —es la misma página
de «sin resultados»—, así que git emparejó los renombrados a ojo por contenido y
el `status` muestra parejas raras (`art_127 -> art_73`). Los nombres en disco son
los correctos; da igual con cuál los emparejara.

## `consolidado_hasta` es del BOE, no nuestro

**Esto se malentendió una vez y va a volver a pasar, así que va escrito.**

- **`consolidado_hasta`** es hasta dónde llega el texto consolidado **que el BOE
  publica**: la fecha del último cambio que el BOE ha incorporado. El Reglamento
  del ITPAJD lo tiene en 2018 y eso **no** son ocho años de retraso nuestro —
  puede ser una norma estable.
- **`sellado`** sí es nuestro, pero mide otra cosa: **el día que ejecutamos la
  ingesta**. Mide nuestra diligencia.
- **El retraso de verdad** es si el BOE lista **reformas posteriores que su
  propio texto todavía no incorpora**. Eso lo calcula `pendientes.leer` al
  ingerir, se guarda ahora en `sellos.json`, y **no tiene umbral que discutir**:
  o hay reformas pendientes o no las hay.

El aviso viejo miraba `sellado`, así que **reingerir lo ponía a cero** aunque no
hubiéramos traído nada nuevo. Por eso no saltaba nunca.

### Los 180 días se quedan, y no sobran

`aviso_de_edad` y `DIAS_SOSPECHOSO = 180` **no se borran aunque lo parezca**. El
aviso exacto necesita que alguien haya preguntado al BOE al ingerir; para un
corpus que llegó copiado de otro equipo, o de una versión anterior a este cambio,
lo único que hay es la edad. Los 180 días están medidos para ese caso —13 de 17
normas ya han cambiado a esa altura— y borrarlos lo dejaría mudo.

### Lo que salió al reingerir las 17

Segundos de red: 4 peticiones por norma y sin pausa fija. **El corpus no cambió
ni un byte** —los 17 sha256 idénticos, 2.504 preceptos antes y después—; lo único
que gana es el dato.

**14 de 17 normas tienen reformas publicadas sin incorporar**, afectando a **82
preceptos**, que ya quedaban marcados como no citables.

| norma | reformas | preceptos | consolidado hasta |
|---|---|---|---|
| Ley del IVA | **25** | 7 | 2026-02-28 |
| Rgto. gestión e inspección | **25** | 8 | 2026-01-01 |
| Rgto. del IVA | **24** | 10 | 2026-02-05 |
| LGT | 14 | 9 | 2024-12-22 |
| Ley del IRPF | 12 | 5 | 2026-04-30 |
| TR del ITPAJD | 11 | 8 | 2026-03-22 |
| Ley del IS | 11 | 6 | 2026-03-22 |
| Rgto. del ITPAJD | 8 | 4 | 2018-11-09 |
| Ley del IP | 7 | 1 | 2023-12-29 |
| Rgto. de Recaudación | 7 | 2 | 2024-02-01 |
| Ley del ISD | 5 | 2 | 2022-12-29 |
| Rgto. del IRPF | 5 | 5 | 2026-02-28 |
| Código trib. Catalunya | 2 | **14** | 2026-05-23 |
| Rgto. del ISD | 1 | 1 | 2023-04-25 |

**Y no se parece en nada a la columna de fechas**, que es exactamente el punto: la
Ley del IVA, consolidada hace 174 días, es la que **más** reformas pendientes
tiene (25); el Reglamento del ISD, con 1.214 días, tiene **una**. Ordenar por
`consolidado_hasta` habría puesto a mirar justo las equivocadas.

## El goteo: el corpus entero, a ratos, desde el Mac

La cola por demanda hace crecer la despensa con lo que se pregunta. El goteo
recorre **todo el corpus** —2.033 artículos, sin el corte de `plan_siembra`— a
ratos, y **corre en el Mac, no en la oficina**.

**Por qué aquí.** Lo que baja viaja por git, igual que la siembra por plan: son
consultas públicas de la DGT, no dicen nada de ningún cliente y cuestan horas
contra un servicio público. Bajarlo una vez y repartirlo es **una** petición; que
lo baje cada equipo son seis, y seis despensas divergiendo. En la oficina sigue
sólo la cola por demanda, que baja a `demanda/` y **no** viaja — sus fechas
dirían qué preguntó un cliente y cuándo.

### El límite es de tiempo: 90 minutos por sesión

Un artículo sin consultas se resuelve en una petición —unos diez segundos— y uno
con cinco necesita seis, o sea un minuto largo. **Con tope por número, dos
sesiones «de cincuenta» duran diez minutos o una hora**, y entonces no se puede
decir cuándo termina ni encajarlo en un hueco.

Noventa minutos es una decisión, no una medida: es un hueco real —se lanza al ir
a comer y ha terminado al volver—, son unas 540 peticiones, y son 6 peticiones
por minuto sostenidas, que para un servicio público es un goteo y no una
descarga. **Si se quisiera ir más deprisa, lo que sube es el número de sesiones,
no el ritmo**: la pausa de 10 s no se toca.

El tiempo se comprueba **antes de empezar cada artículo**, nunca en mitad:
cortar a medias dejaría sus consultas incompletas y habría que decidir si eso
cuenta como buscado.

### Cuánto tarda cubrirlo entero

Quedan **1.186 artículos**. Los 630 del plan dieron 2,4 consultas cada uno, pero
eran los más citados; el tramo que queda es la cola, así que lo probable está
cerca del extremo bajo.

| si cada artículo diera | horas | 1 sesión/día | 2 sesiones/día |
|---|---|---|---|
| 0,3 consultas | 4,3 h | **3 días** | 1 día |
| 1,0 | 6,6 h | **4 días** | 2 días |
| 2,4 (como el plan) | 11,2 h | **7 días** | 4 días |

### El orden y la memoria

Recorre todo, pero **por utilidad**: banco × 12 + remisiones entrantes, la misma
cuenta que `plan_siembra` —extraída a `puntos_del_banco` para que haya una sola—.
Si el goteo se para para siempre a mitad, lo bajado es lo útil.

Los plazos salen de `cola.py` y no se copian: 90 días para reintentar un vacío,
180 para refrescar. Dos copias de una regla son dos reglas en cuanto alguien
cambie una.

### Dos cosas que la primera versión hacía mal

**El ensayo apuntaba.** `--ensayo` marcó los 2.033 artículos como «buscados», y
la sesión de verdad se los habría saltado todos. Una prueba que deja el sistema
creyendo que el trabajo está hecho es peor que no probar. Ahora no escribe nada —
y sí duerme un poco, para que el corte por tiempo se ejercite de verdad: sin
pausa, `--minutos 1 --ensayo` recorría el corpus en un segundo y decía
«terminado», probando el recorrido y no el límite.

**El orden se quedaba a medias en silencio.** Llamaba a `puntos_del_banco` con un
`try/except AttributeError` y, al no existir esa función, caía a cero: el orden
salía sólo por remisiones y nadie se enteraba. Un respaldo que devuelve algo
cuando la consulta falla es exactamente lo que este proyecto no admite.

## Cuando la cola no da abasto

La cola crece con lo que se pregunta y baja **de tres en tres por apertura**. Una
punta de uso puede acumularla durante semanas, y **desde dentro se ve igual que
ir bien**: la ventana avisaba si llevaba cinco días sin poder bajar nada —la
fuente caída— pero no si bajaba menos de lo que entraba.

### La señal: la edad del más viejo pendiente

No el tamaño de la cola, ni si crece. Tres motivos, y el primero manda:

1. **Es la promesa, medida directamente.** Cuando alguien pregunta por un
   artículo que no tenemos, la ventana le dice *«apuntado, lo estoy buscando»*.
   La edad del más viejo es exactamente cuánto lleva esa frase sin cumplirse. El
   tamaño no dice eso: veinte entradas de ayer son una tarde buena, y una sola de
   hace un mes es una promesa rota.
2. **No hace falta guardar nada nuevo.** `primera_vez` ya está en cada entrada.
   Medir si la cola «baja de tamaño» pediría una serie de tamaños diarios: otro
   fichero que mantener y otra cosa que puede quedarse vieja.
3. **Se calla sola.** En cuanto el más viejo se baja, el aviso desaparece sin que
   nadie lo apague. Un aviso de tendencia hay que decidir cuándo dejar de darlo.

Y **sólo cuenta los pendientes**: un refresco no es una promesa. A nadie se le
dijo «lo estoy buscando» por un artículo del que ya tenemos criterio.

### El umbral: 14 días, y es una decisión

**No se puede medir hoy**, y conviene decirlo: haría falta saber cuántas veces al
día se abre el agente en la oficina, y de eso no hay ni un dato — las trazas que
hay son mías probando.

El razonamiento: la cola baja 3 por apertura; con una apertura por día laborable
son ~15 a la semana, ~30 en dos. Si a los catorce días el más viejo sigue
esperando, o la cola es mayor que eso o el agente no se está abriendo. **Las dos
cosas hay que decirlas y las dos tienen la misma respuesta.** Y catorce días es
también el límite de lo que «lo estoy buscando» se sostiene sin sonar a excusa.

Se podrá medir cuando lleguen trazas de la oficina.

### Lo que dice, con qué hacer y a quién avisar

> Hay 2 artículo(s) esperando criterio, y el más antiguo lleva 20 días. Se traen
> tres cada vez que se abre el agente, así que abrirlo más a menudo los va
> sacando. Si tienes prisa, pídele a Emili una tanda de descarga.

**Un aviso, no dos.** Si la fuente está caída y además hay cola, se enseña el de
la fuente: los dos hablan de la cola pero de cosas distintas, y poner al lado un
problema que no se resuelve desde la ventana y otro que sí acaba en que no se
hace ninguna de las dos cosas. Además se solapan — si la fuente lleva dos semanas
muda, el más viejo lleva dos semanas esperando *por eso*, y decir «abre el agente
más veces» sería mandar a alguien a repetir algo que no va a funcionar.

## Las suites llenaban la cola de producción

Encontrado contando la cola para poner el aviso de arriba: **23 pendientes, y las
23 mías**. La ventana ya se negaba a *salir* a PETETE con el motor de ensayo —«la
suite va contra dobles y no toca la fuente»— pero la cola se seguía **llenando**
desde cualquier motor, así que cada pasada de la batería metía entradas.

No es sólo suciedad. La cola apuntada es una promesa hecha a alguien; una promesa
que no le hemos hecho a nadie no puede ocupar el sitio de una que sí, **ni
disparar un aviso de que la cola no da abasto**. Con el ruido dentro, la alarma
recién puesta habría saltado por mi culpa el día que la oficina la estrenara.

Ahora se aplica la misma regla en las dos direcciones: con motor de ensayo, ni se
llena ni se vacía. Y la cola quedó limpia: 38 entradas → 0.

## Medir sobre un histórico mientras el código cambia

**Describe un sistema que ya no existe.** Ha pasado tres veces, y las tres han
costado lo mismo: un diagnóstico entero apuntando a algo ya arreglado.

**1 · «320 artículos con criterio de 630», y luego 830.** Dos mediciones con el
mismo numerador aparente y distinto denominador, porque entre una y otra había
crecido la despensa. Un número que cambia de base entre dos mediciones es
exactamente lo que hace tomar decisiones malas.

**2 · Las cinco pruebas de ITPAJD en rojo imposible.** El banco las nombraba con
el cuerpo `#0` —un artículo— cuando el material estaba en el `#1` —cincuenta y
nueve—. Las expectativas describían un corpus anterior. Y la suite
`prueba_normativa_dgt` tenía la misma constante mal: suite y código equivocados
en la misma dirección durante meses.

**3 · Las tres consultas que «no decían de qué norma es».** Fallaban las tres, y
las tres volvían a fallar en el reintento. Parecía un defecto vivo y daba pie a
rehacer media rama del sistema. Son de la noche del 5 de agosto, **antes de las
23:19**, y a esa hora entró el commit que hace que la ficha diga el nombre del
cuerpo en vez del título del BOE — el arreglo que las causaba. Se descubrió
comparando a mano la hora de las carpetas con `git log`.

### Lo que lo habría evitado, y ahora está puesto

**Cada expediente guarda con qué versión se generó.** `version.json`, escrito al
**crear** la traza y no al cerrarla: una consulta que revienta a la mitad también
tiene que poder decir de qué versión es, porque si no, la única que falta es
justo la de la consulta que reventó.

Lleva el hash, la fecha y **cuántos ficheros había sin guardar**. Sin ese último
dato, una traza generada con cambios locales encima diría ser de un commit que no
contiene lo que de verdad corrió — y en mi Mac eso es casi siempre.

**Las mediciones lo usan.** `medir_reintento.py`, `medir_no_encontrado.py` y
`medir_hilo.py` imprimen de cuántas versiones es la muestra antes de cualquier
media, porque si abarca cuatro versiones la media no describe ninguna de ellas.
`medir_reintento.py` además filtra: `--desde <commit>`.

**Los expedientes viejos no lo llevan, y no pasa nada.** Cuentan como *versión
desconocida*, en su propia fila. Suponer que son de la versión de hoy es
exactamente el error que esto viene a impedir. Un `version.json` ilegible también
cuenta como desconocida, no como un error.

**Y no puede tumbar una consulta.** Sin git, con git lento o con el repositorio a
medias, se apunta «desconocida» y se sigue. Un expediente sin versión es malo; un
expediente que no existe porque git tardó veinte segundos es mucho peor.

**Una sola implementación.** La lectura del commit ya estaba escrita a mano
dentro de `comprobar_equipo`; ahora hay una en `agente_fiscal/version.py` y la
usan la ficha del equipo y las tres mediciones. La suite comprueba que no queda
ninguna lectura suelta — es la séptima vez que un arreglo se queda a medias por
vivir en un solo sitio.

Los tres controles negativos están en `pruebas/prueba_version.py`: si la traza
deja de escribirla, si los viejos se suponen de hoy, o si el fallo de git deja de
estar envuelto, la suite se cae.

## La rama del verificador: lo que se midió, y por qué no se toca

La otra forma de acabar sin respuesta —el verificador rechazó— se dejó fuera de
la orientación. La hipótesis a comprobar era que unos rechazos son de **forma**
(el texto vale, el formato no; ahí el segundo intento funciona) y otros de
**falta de material** (ahí el segundo intento va a fallar igual y orientar sería
mejor).

**No se distinguen, porque no hay ninguno de falta de material.** De 7 consultas
rechazadas en el primer intento, 2 las salvó el segundo y 5 volvieron a caer. Los
doce motivos son de forma: *el fragmento no lleva su referencia pegada* (7) y *la
referencia no dice de qué norma es* (4), más un *ninguna cita con fragmento
literal*. Cero por falta de material. La regla propuesta no se dispararía nunca.

### Y luego, el dato que tira la mitad de la base

Las 3 que caían por «no dice de qué norma» son de la noche del **5 de agosto,
antes de las 23:19**. A esa hora entró el commit `3b963e6`, que hace que la ficha
del material diga el nombre del **cuerpo** (*«Reglamento del Impuesto sobre el
Valor Añadido»*) en vez del título del documento del BOE (*«Real Decreto
1624/1992, de 29 de diciembre, por el que se aprueba…»*, 400 caracteres). Ese
segundo nombre **el verificador no lo acepta**: en el corpus es otro cuerpo.

O sea que a esas tres consultas se les pedía nombrar la norma **enseñándoles un
nombre que no valía**. Su fallo no es un defecto vivo: es un fallo ya arreglado,
tres semanas atrás, la misma noche.

`medir_reintento.py` corta ahora por esa hora y lo dice antes que cualquier otro
reparto. **La base viva es de 3 consultas, de las que cayeron 2** — y las dos por
otra cosa: una por *sin referencia pegada* y otra por *ninguna cita*.

### La chuleta de normas

Se añadió igualmente al mensaje de reintento: para cada precepto del material,
`artículo N → NORMA`, con marca en los números repetidos, más una instrucción de
que ese nombre se copia de ahí y no se deduce. Sólo en el reintento — en el
primer intento cada precepto ya lleva su ficha con la norma, y el prompt ya dice
*«el nombre de la norma se copia de la línea NORMA: de la ficha, tal cual»*. Ese
hueco ya estaba cerrado.

**Su valor está sin medir, y conviene decirlo.** El reensayo de las 7 salió 7 de
7 aceptadas, pero **no separa una cosa de la otra**: usó el material de hoy, que
ya trae el arreglo del 5 de agosto y que además ha cambiado por el crecimiento
del corpus (una traza pasó de 4 preceptos a 6). La comparación que lo diría
—mismo material, con y sin chuleta— no se ha hecho.

### La base, dicha en cada corte

7 casos, en grupos de 3, 3 y 1; base viva de 3. `medir_reintento.py` imprime el
tamaño en cada fila, porque «3 de 3» sin el 3 delante se lee como un porcentaje y
no lo es. Y son números **de mi Mac**, de consultas mías probando: se reconfirman
con las trazas de la oficina cuando lleguen, y no antes.

## El NO ENCONTRADO orienta (y lo que la medición dijo después)

Cuando la búsqueda recupera preceptos pero ninguno resuelve el caso, hasta ahora
se tiraban y se decía que no hay nada. Ahora, en **una llamada más**, se dice qué
se ha encontrado y por qué no basta, **dónde** vive la respuesta, y qué dato
falta para acotar. Sólo en esa rama: la otra forma de acabar sin respuesta —el
verificador rechazó— ya ha pagado dos redacciones y ahí el modelo *ya* intentó
contestar y falló.

**Orientar es decir dónde buscar. Contestar es decir qué dice la ley.**

| | |
|---|---|
| «depende de dónde tuviera la residencia el causante» | orientación |
| «en Cataluña la reducción es del 95 %» | derecho sin cita |
| «el plazo son seis meses» | derecho sin cita |
| «lo regula el artículo 20 de la Ley 29/1987» | derecho sin cita |

Las tres últimas son verdad, probablemente. Y da igual.

### Tres candados, y ninguno se fía del de al lado

1. **El prompt**, con todas las letras. Necesario y no suficiente: un prompt es
   una petición, no una garantía.
2. **El verificador entero**, el de siempre. Una cita inventada tumba la
   orientación como tumba una respuesta. Y aquí, además, **las referencias
   sueltas también tumban** — un «lo regula el artículo 20» sin fragmento
   literal, que en el camino normal sólo se cuenta.
3. **`derecho_sin_cita`**, que es nuevo. El verificador comprueba lo que se
   cita; no comprueba lo que se afirma **sin citar nada**. «En Cataluña la
   reducción es del 95 %» no lleva comillas ni referencia: para el verificador
   no existe. Para este guardián sí.

Cada candado tiene su control negativo. Quitando el 3º pasan el porcentaje y el
plazo; quitando el rechazo por sueltas pasa el artículo de memoria; quitando el
verificador pasa la cita inventada. Los tres son de carga.

Un hueco encontrado por el camino: el patrón de artículo llevaba `iculo` sin
tilde, así que **«artículo 99» —como lo escribe el modelo— se le escapaba
entero**. Sólo lo cazaba el rechazo por sueltas, y eso sólo funciona cuando el
número va con el nombre de la norma al lado.

### Lo que costó, y la sorpresa

| | |
|---|---|
| una redacción completa | 3.773 tokens de salida |
| la orientación medida | **3.064 tokens · el 81 %** |
| coste de la llamada | $0,210 · 0,19 € |

**El 81 % es la señal de alarma que había que vigilar**: si ocupa casi lo mismo
que contestar, puede estar contestando. Leída entera, no lo hace —no dice en
ningún punto qué dice la ley sobre el caso— pero es larga, y la longitud viene
del punto 1, que recorre cuatro preceptos con su cita cada uno. Queda anotado
para apretar si vuelve a salir así.

### Y la rama casi no salta

Las dos consultas reales que motivaron esto son del 2 de agosto, **con trece
normas cargadas**. Hoy hay diecisiete. Al repetirlas con el modelo, **ninguna de
las dos volvió a caer por esta rama**: ahora la búsqueda encuentra material
suficiente y salen por el verificador.

Barriendo las 1.474 consultas de la DGT de la despensa, un **22,2 %** cae por
esta puerta — pero eso usa el texto crudo de la pregunta, no los términos que
escribe el analizador. Cribando seis consultas con el analizador **real** (0,064
$ en análisis sueltos, en vez de pagar consultas enteras a ciegas), **las seis
pasaron la puerta**. El 22,2 % es un techo; el número real es bastante menor.

O sea: lo construido funciona y está probado, pero **se disparará poco**. Donde
hoy se acaba de verdad sin respuesta es en la rama del verificador, que es la
que se dejó fuera a propósito. Eso queda para decidir.

### El rótulo se queda

«NO ENCONTRADO» sigue siendo cierto: no hay respaldo para *contestar*, y la línea
de debajo dice inmediatamente lo que sí hay. Cambiarlo obligaría a tocar el enum,
la guía, las etiquetas del banco y la comprobación de coincidencia, y para un
camino que salta poco. Lo que sí hacía falta: **las dos frases nuevas están en
`TEXTOS_DE_ESTADO`**, así que la comprobación de coincidencia exige que estén
escritas en `GUIA.md`. Ocho frases ahora, no seis.

## Los botones grises de Windows, y por qué el arreglo anterior no bastó

**El síntoma:** en el PC de la oficina los dos botones salen en gris con la
consulta, el año y la comunidad rellenados. Sin una palabra.

Ya se había arreglado una vez: se envolvió el arranque entero para que ninguna
excepción se perdiera, se escribió el detalle a disco, y `prueba_boton.py` se
puso verde. **Y el fallo seguía.**

**La causa real:** `_bloquear` escribía la explicación con `_pintar_estado` y
`_escribir_texto`, y las dos escriben en la vista de **respuesta**. Al arrancar,
la ventana está en la de **consulta** — es donde se escribe la duda — y la otra
está quitada del grid. O sea que el mensaje se escribía entero, correcto y
completo, **en una pantalla que no se ve**. Lo que quedaba delante era el
formulario y dos botones grises.

Y la suite lo daba por bueno porque leía `v.texto` a pelo: la frase *estaba*; no
estaba **a la vista**. Es el mismo error que dar por buena una comprobación que
en realidad lee el comentario que explica por qué algo no se hace — la tercera
vez que ese patrón muerde.

Ahora `_bloquear` lo dice en la **cinta**, que vive en la vista de consulta. Y la
suite lee **sólo la vista que está puesta**: si el mensaje va a la otra, cuenta
como no dicho. Con el arreglo quitado, las cuatro causas salen mudas.

### Las causas, cada una con lo suyo

| causa | lo que se lee en pantalla |
|---|---|
| pull a medias, dependencia que falta | «no ha podido prepararse… haz doble clic en *diagnostico*» |
| no hay credencial | «Falta la configuración. Avisa a Emili» + el diálogo para ponerla |
| la cuenta sin saldo | «La cuenta no tiene saldo. Avisa a Emili» |
| corpus incompleto o sellos que no cuadran | «Falta el texto de las normas. Cierra y vuelve a abrir: se baja solo» |

La causa concreta **manda sobre la genérica**. El mensaje de `_revisar_boton` se
dispara al escribir en la caja — o sea siempre, y después — y borraba la buena en
cuanto el gestor tecleaba la primera letra.

### Los botones nuevos no añaden otro camino mudo

`_seguir` y `_escribir_para_cliente` volvían en silencio con la caja vacía, con
una consulta en marcha, sin motor o sin expediente. **Un botón que se puede
pulsar y se queda quieto es peor que uno apagado**: apagado al menos se ve que no
toca. Los cuatro casos lo dicen ahora.

Y el caso que no existía antes: una respuesta **buena** cuyo expediente no se
pudo escribir — disco lleno. «Escribirlo para el cliente» se apaga, porque el
material vive dentro de la carpeta, y se explica diciendo lo que importa: *la
respuesta de arriba es válida, cópiala antes de cerrar*.

### La línea para la oficina

«Haz doble clic en comprobar_equipo y enséñame lo que salga» pide leer una
ventana negra y copiarla a mano, y por eso **no ha vuelto nunca nada**.
`diagnostico.bat` (y `diagnostico.command` en Mac) ejecuta lo mismo, lo guarda en
`diagnostico.txt` al lado del agente y lo abre en el Bloc de notas. Lo que se
envía es un adjunto.

Incluye el último arranque fallido **con su fecha**, y dice si es de hoy: sin eso
un fallo de hace tres meses ya arreglado se lee igual que el de esta mañana.

## El botón de copiar

Se lleva **la última respuesta**, no el hilo. Lo que se pega en un correo o en
el expediente del cliente tiene que ser **una** respuesta verificada.
