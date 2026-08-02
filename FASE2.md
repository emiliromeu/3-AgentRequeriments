# FASE 2 — Buscar y expandir

Estado: **terminada y comprobada**. La consulta de control sale bien.

```
python fase2.py buscar "deducción del IVA de un turismo"
python fase2.py buscar "deducción de un turismo" --ejercicio 2023
python fase2.py diagnostico
```

Opciones: `--tope N` (resultados), `--expandir N` (cuántos se expanden),
`--tope-expansion N` (remisiones por sentido), `--sin-expansion`.

Códigos de salida: `0` correcta · `1` fallo · `3` sin resultados.

## Comprobación exigida

> «le pregunto por la deducción del IVA de un turismo y tiene que salir el
> artículo 95 entre los tres primeros»

```
1. Articulo 95  ·  Limitaciones del derecho a deducir.     <-- primero
2. Articulo 51  ·  Importaciones de documentos de carácter turístico.
3. Articulo 57  ·  Importaciones de carburantes y lubricantes.
```

Con otras formas de preguntar lo mismo: «puedo deducir el IVA de un coche de
empresa» → 2.º; «deducibilidad vehiculos turismo» → 2.º; «limitaciones al
derecho a deducir» → 1.º.

## 1 · Encontrar

Índice invertido en memoria, BM25F. Sin base de datos, sin embeddings, sin IA.

- **Sin acentos, sin mayúsculas, sin palabras vacías.** La lista de vacías son
  sólo palabras gramaticales; términos como *ley*, *cuota* o *impuesto* no se
  filtran a mano: ya los degrada el idf, que sabe cuántas veces salen de verdad.
- **Las palabras raras pesan más.** *turismo* aparece en 7 preceptos y *deduc-*
  en 62: la primera manda.
- **El título pesa más que el cuerpo** (×4). Aviso: en este corpus
  `titulo_bloque` es sólo "Artículo 95"; el epígrafe real está en `rubrica`, y
  es lo que se indexa como título, junto con la referencia, para que buscar
  «artículo 95» también funcione. El `contexto` (Título/Capítulo) entra con
  peso bajo.
- **Lematizado propio** (Snowball ES compacto, librería estándar). Hace falta
  porque quien pregunta escribe «deducción de un vehículo» y la ley dice
  «deducir» y «vehículos». Se añadió una regla para `-ucción/-ucir`, que
  Snowball estándar no une y es justo la familia que más se usa aquí
  (deducir/deducción, producir, reducir).
- **Se indexa la raíz y también la palabra literal** (peso 0,45). Lematizar
  sube el recall pero junta cosas distintas: *importe* e *importación*
  comparten raíz. Con la forma exacta indexada, quien busca «importe» puntúa
  más alto los preceptos que dicen literalmente «importe».

**Lo que no entra en el índice**: `notas_boe` (historial de reformas) y
`notas_editoriales` (avisos del BOE). No son texto promulgado y no pueden
fundamentar nada.

## 2 · Expandir — los dos sentidos

Detección por parseo del texto, sin IA. **653 remisiones**: 578 resueltas
(88,5 %), 72 PENDIENTE por ser de otra norma, 3 PENDIENTE por ambiguas,
**0 sin explicar**.

Sale siempre en su propio apartado y etiquetado — «MENCIONA A» / «LE
MENCIONAN» — nunca mezclado con los resultados de la búsqueda.

Lo que sabe leer:

| forma en la ley | qué hace |
|---|---|
| `artículo 95` | resuelve |
| `artículos 69, 70 y 72` | lista → 3 preceptos |
| `artículos 22, ..., y 27` | lista con coma **y** conjunción |
| `artículos 92 a 114` | rango → los **23** de en medio, incluidos los intercalados |
| `artículo 163 quáter` | sufijos, con y sin tilde |
| `artículo 140 cuarter` | sufijos con errata (los de la fase 1) |
| `artículo 20, apartado uno, número 22.º` | el apartado cuelga del 20, no es otro artículo |
| `artículo 68.Dos.2.º`, `13.2.º` | subdivisiones, idem |
| `disposición adicional tercera` | disposiciones |

**Los sufijos no se validan contra una lista**: se comprueban contra los
artículos que existen de verdad en el corpus. Así las erratas del BOE se
resuelven solas y no hay lista que mantener en dos sitios.

### Lo que NO se resuelve, a propósito

`artículo 95 de esta Ley` → se resuelve.
`artículo 95 del Reglamento` → **PENDIENTE**, siempre, mientras el Reglamento
no esté en el corpus. Una remisión mal resuelta devuelve el artículo
equivocado y el usuario no tiene forma de notarlo: es peor que no devolver
nada.

Se distinguen tres ámbitos:

- **de esta ley** → se resuelve.
- **otra norma nombrada** (`del Reglamento`, `de la Ley 58/2003`, `del Código
  Civil`, `de la Ley Concursal`, `de dicha Ley`) → PENDIENTE, con el nombre de
  la norma para que se pueda comprobar a mano.
- **ambigua** (`en el referido artículo 32`, sin decir de qué norma) →
  PENDIENTE. Son 3 en toda la ley.

Externas detectadas: Ley 58/2003 (10), Ley General Tributaria (7), Ley
Concursal (4), Directiva 2006/112/CE, Reglamento (UE) n.º 282/2011, Código
Civil, Tratado de Funcionamiento… Ninguna se resuelve contra la LIVA.

### El sentido de vuelta

**12 artículos reciben remisiones desde una disposición** — el caso que mata:
se lee el artículo entero, parece cerrado, y la excepción estaba en una
disposición del final.

```
Articulo 20  <- Disposicion adicional sexta
Articulo 22  <- Disposicion transitoria segunda, Disposicion transitoria tercera
Articulo 102 <- Disposicion transitoria quinta
Articulo 111 <- Disposicion transitoria sexta
```

Por eso, al listar «LE MENCIONAN», **las disposiciones van siempre primero** y
marcadas. No es cosmética: el artículo 20 tiene 20 remisiones entrantes y la
disposición adicional sexta se perdía al recortar la lista. Si se corta algo,
se dice cuántas quedan sin mostrar.

El artículo 95 lo encuentra por un **rango**: el artículo 7 dice «artículos 92
a 114», sin nombrarlo. Sin expandir rangos, ese vínculo no existiría.

## 3 · Avisos de fecha

Con `--ejercicio AAAA`. Van **arriba de cada resultado**, marcados `!! AVISO`,
antes del texto. Se usa siempre `fecha_vigencia_efectiva` (la corregida en la
fase 1), nunca el valor crudo con la errata.

| situación | aviso |
|---|---|
| el texto de hoy no es el de entonces | `el texto vigente HOY (desde 2024-12-22) NO es el que aplicaba en 2023; entonces regía la versión del 2023-01-01` |
| cambió a mitad de ejercicio | `CAMBIÓ durante 2023 (…): comprueba la fecha del devengo` |
| caducado | `CADUCADO el 2014-11-28: ya no se aplicaba en 2020` |
| caduca dentro del ejercicio | `CADUCA el 2014-11-28, dentro de 2014` |
| aún no existía | `en 2015 este precepto NO EXISTÍA todavía: entró en vigor el 2021-07-01` |
| cambios posteriores | nota, no aviso: no afectan al caso |

Además, con `--ejercicio` **el fragmento que se muestra es el de la versión que
aplicaba ese año**, no el de hoy. Comprobado con el artículo 91 (41 versiones):
para 2023 elige la 39.ª.

## Un defecto de la fase 1 que salió aquí (corregido)

Al mirar cómo estaban escritas las remisiones aparecieron 179 párrafos de
**aparato editorial del BOE** («Téngase en cuenta que…») dentro del articulado.
El BOE los mete en `<blockquote>` **con atributo `class`** (`soloTexto`,
`siempreSeVe`, `noDesde20160101`…), pero los párrafos de dentro llevan la misma
clase que el articulado (`parrafo`): por la clase del `<p>` no hay forma de
distinguirlos, el único marcador fiable es el contenedor.

Importa porque ahí dentro el BOE llega a reproducir **redacciones
alternativas**: el verificador de la fase 3 podría dar por buena una frase que
en ese ejercicio no era la vigente. Corregido en `parser.py`, reingerido y
reauditado: ahora van a `notas_editoriales` (361 notas en 56 preceptos), fuera
del cuerpo y fuera del índice. Cero fugas. La auditoría de la fase 1 sigue en
verde.

## Dos errores propios, anotados para que no se repitan

- **`patron.match(texto, cursor)` no ancla `^` en `cursor`.** Los patrones de
  conectores y ataduras estaban anclados, así que **ninguna lista ni ningún
  rango se expandía**: «artículos 92 a 114» devolvía sólo el 92. Silencioso y
  con toda la pinta de funcionar. Corregido quitando las anclas.
- **Expandir «IVA» a «impuesto sobre el valor añadido» empeora la búsqueda.**
  Mete tres palabras que están en casi todos los artículos y, como BM25 suma
  por término, adelantan al precepto que casaba las dos raras. Con la expansión
  puesta, el artículo 95 se caía del podio en la consulta de control. Se quitó:
  el corpus entero *es* la ley del IVA, así que «IVA» no distingue nada. Ahora
  se dice «NO APARECEN en el articulado: iva; se ha buscado con el resto».

## Lo que queda para la fase 3

- El verificador debe leer del mismo sitio que el buscador: `texto` de la
  versión aplicable, nunca `notas_boe` ni `notas_editoriales`.
- Las remisiones PENDIENTE son la lista de la compra del Reglamento del IVA:
  en cuanto entre en el corpus, 72 remisiones pasan a resolverse sin tocar el
  código (el ámbito ya está identificado, sólo falta el destino).
- `fase2.py` sólo lee. No ha tocado el JSONL.
