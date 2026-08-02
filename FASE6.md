# FASE 6 — Multinorma

Estado: **hecho como un solo cambio de identidad.** Batería 23/23 en verde,
fase 4 en verde, fase 1 sin fallos en las dos normas.

## El cambio, en una línea

```
antes:   clave = "articulo 8"
ahora:   clave = "BOE-A-1992-28740#0#articulo 8"   (norma # cuerpo # precepto)
```

Todo lo demás sale de ahí. No son cuatro parches: es un módulo nuevo
(`normas.py`) que define la identidad, y el resto del sistema pasa a usarla.

```
"articulo 8" existe en 2 cuerpos, y cada uno tiene su clave:
      BOE-A-1992-28740#0#articulo 8    (Ley,        Concepto de entrega de bienes)
      BOE-A-1992-28925#1#articulo 8    (Reglamento, Aplicación de las exenciones…)
```

## 1 · El cuerpo se detecta de la estructura

Un cuerpo nuevo se abre cuando **la numeración de artículos reinicia**. Nada
más. No hay lista de normas especiales.

```
LEY 37/1992    215 artículos, 0 reinicios  -> 1 cuerpo
RD 1624/1992   127 artículos, 1 reinicio   -> 2 cuerpos
                 (posición 14, id a1-2: tras la firma y el encabezado ANEXO)
```

Los **nombres** también salen de los datos, del título oficial de la norma:

| cuerpo | nombre | de dónde sale |
|---|---|---|
| `28740#0` | Ley 37/1992 | rango + número oficial |
| `28925#0` | Real Decreto 1624/1992 | rango + número oficial |
| `28925#1` | Reglamento del Impuesto sobre el Valor Añadido | «…**por el que se aprueba el** Reglamento del Impuesto sobre el Valor Añadido» |

Y los **alias** para reconocer citas se generan de ese nombre: de «Ley 37/1992
… del Impuesto sobre el Valor Añadido» salen `ley 37/1992`, `ley del impuesto
sobre el valor añadido`, `ley del impuesto`, `ley del iva`, `liva`. Por eso
encaja el «de la Ley del Impuesto» que el Reglamento usa 113 veces, sin
haberlo escrito en ningún sitio.

Cualquier RD aprobatorio o texto refundido entra solo con la misma regla.

## 2 · Descableado

`CORPUS` ya no apunta a una norma: es el **directorio**. `Indice` carga todos
los `*.jsonl` que haya, construye el registro de cuerpos y lo publica. Las
fases 2, 3 y 4 no saben cuántas normas hay ni cuáles.

```
corpus: 387 preceptos de 3 cuerpo(s) normativo(s):
          · Ley 37/1992
          · Real Decreto 1624/1992
          · Reglamento del Impuesto sobre el Valor Añadido
```

## 3 · Las remisiones entre normas

Cada remisión se resuelve **contra un cuerpo**, no contra «el corpus».

| forma real del BOE | resultado |
|---|---|
| `de la Ley del Impuesto` (y `de la ley del impuesto`) | → la Ley |
| `de este Reglamento` / `del presente Reglamento` | → interna, por diseño |
| `artículo 71` a secas | → interno a **su** cuerpo |
| `de dicha Ley`, `del citado Reglamento` | → PENDIENTE (norma nombrada antes) |
| `de esta misma Ley` | → interna (el demostrativo manda sobre «misma») |
| `de la Ley 58/2003`, `de la Ley Concursal`, `del Reglamento (UE) 282/2011` | → PENDIENTE |

La regla de oro está implementada, no prometida: tras encajar un alias, si lo
que sobra empieza por un número de norma, un paréntesis o un nombre propio, **no
se resuelve**. «Ley 58/2003» no se acorta a «Ley» para que cuadre con la LIVA.

## 4 · Comprobaciones

### Los dos corpus cargan juntos

387 preceptos, 3 cuerpos, **0 colisiones**. La fase 1 audita las dos normas sin
fallos.

### Las 129 no encontradas del Reglamento

```
ANTES (identidad vieja, Reglamento solo)
   492 remisiones · 100 resueltas · 154 no encontradas

AHORA (multinorma)
   485 remisiones · 323 resueltas — de ellas 176 CRUZADAS a la Ley
                  ·  74 pendientes
                  ·  88 no encontradas
```

Las 88 que siguen sin encontrarse son casi todas del **cuerpo 0** (el Real
Decreto, que solo tiene 6 artículos): son referencias que aparecen dentro del
texto de *otros* reales decretos que el RD modifica y transcribe. Apuntan a la
norma transcrita, no al RD. Quedan visibles como NO ENCONTRADA, que es el
comportamiento seguro.

### Cero mal resueltas

Auditoría por ocurrencia, no por número (la primera versión de esta auditoría
agrupaba por número y daba 60 falsos positivos):

```
"artículo N … de la Ley del Impuesto"  ->  LEY: 118   MAL: 0
"artículo N … de este Reglamento"      ->  REGL:  36  MAL: 0

invariante interna (destino en el mismo cuerpo) : 663 casos, 0 violaciones
invariante cruzada (destino en otro cuerpo)     : 267 casos, 0 violaciones
```

Llegar a 0 costó tres fallos encadenados, todos reales:

1. **El sufijo se validaba contra el cuerpo de origen.** «8 bis» no existe en el
   Reglamento, así que el escáner cortaba ahí y se perdía el «de la Ley del
   Impuesto» que venía detrás → el artículo 8 se resolvía contra el Reglamento.
   El sufijo es una propiedad *léxica* de la cita; a qué norma apunta se decide
   después. (14 mal resueltas)
2. **`^` anclado otra vez.** `_RE_DESIGNACION` empezaba por `^` y se usaba con
   `.search()`, así que solo miraba la posición 0. El BOE intercala texto:
   «artículo 22, apartados uno a siete **de la Ley del Impuesto**». (4 más)
3. **Enumeración con designación compartida**: «artículo 9 y en el apartado 2º
   del artículo 16 **de la Ley del Impuesto**» — dos remisiones y un solo
   nombre al final. Se hereda, pero acotado: solo si el hueco es corto y no
   nombra otra norma. (1 más)

### Caso adversario obligatorio · en la batería

```
[ OK ] s-remision-cruzada-lleva-a-la-LEY          esperado VERIFICADA    obtenido VERIFICADA
[ OK ] s2-el-mismo-nombre-pero-el-texto-del-reglamento  esperado NO_VERIFICADA  obtenido NO_VERIFICADA
```

El primero cita «artículo 8 de la Ley del Impuesto» con el texto literal del
artículo 8 **de la Ley**: si el sistema lo resolviera contra el Reglamento, el
literal no estaría y saldría rojo. El segundo es la cara B: mismo nombre de
norma, texto del artículo 8 **del Reglamento** → NO VERIFICADA.

### Dos expectativas corregidas, y por qué

Los dos casos que añadí en la fase 5 se escribieron cuando el Reglamento **no
estaba cargado**. Esa premisa ya es falsa:

| caso | antes | ahora | por qué |
|---|---|---|---|
| `r-cita-sin-norma-con-dos-normas-en-juego` | NO_VERIFICADA | **NO_VERIFICABLE** | antes suponía la Ley y fallaba el literal: veredicto correcto por el motivo equivocado. Ahora detecta que «artículo 71» existe en dos cuerpos y no elige |
| `r-cita-al-reglamento-por-su-nombre` | NO_VERIFICABLE | **VERIFICADA** | la norma ya está cargada y la cita es literal y correcta |

### El caso rojo del banco: sigue rojo, y ahora sé por qué

**No he tocado el caso ni el tope.** Lo que ha cambiado es que la recuperación
ha mejorado tanto que el caso se ha quedado obsoleto:

```
  1. Articulo 81   Reglamento del IVA   Lugar, forma y plazos de presentación de la declaración recapitulativa
  2. Articulo 80   Reglamento del IVA   Contenido de la declaración recapitulativa
  3. Articulo 78   Reglamento del IVA   Declaración recapitulativa
  4. Articulo 79   Reglamento del IVA   Obligación de presentar la declaración recapitulativa
 ...
 10. Articulo 164  Ley 37/1992          Obligaciones de los sujetos pasivos
```

Los cuatro primeros son exactamente los artículos que contestan la pregunta —
los que predijiste. El caso pide `164, 165, 166, 167`, que son de la **Ley**, y
ahora salen los 10.º porque la respuesta correcta los ha desplazado.

El caso no es que «no llegue»: es que **pide los artículos equivocados**, y el
fichero de casos no tiene columna para la norma. Esa columna es el siguiente
paso, y es consecuencia directa del multinorma. Decide tú si se añade.

### Regresión sobre la LEY SOLA

```
                    antes      ahora
  total             653        653
  resueltas         578        566
  externas           72         67
  ambiguas            3         20
  no encontradas      0          0
```

La prueba decisiva, que es la que importa:

```
remisiones que dicen "de esta Ley": 252 | sin resolver: 0
resueltas que apuntan fuera de la Ley: 0
```

**Ninguna remisión interna se ha perdido.** Las 12 que dejan de resolverse son
todas anafóricas y apuntan fuera: `de dicha Ley` (Ley 49/2002, LGT), `del citado
Reglamento (UE) 282/2011`, `de dicho Real Decreto-ley 19/2018`, `de la Ley de
Contratos del Sector Público`. Antes se resolvían **contra la Ley del IVA**, que
era exactamente la clase de error que esta fase venía a eliminar. Pasan a
PENDIENTE: es un apriete, no una regresión.

Durante la revisión sí apareció una regresión de verdad, y está corregida:
`«artículo 107 de esta misma Ley»` se marcaba ambigua por la palabra «misma».
Causa: en `(?P<det>(…)\s+){0,3}` Python devuelve solo la **última** repetición
(«misma»), perdiendo el «esta» que decide. El grupo repetido va ahora dentro del
grupo con nombre.

### El resto, en verde

```
FASE 1  las dos normas, sin fallos, 0 colisiones
FASE 2  art. 95 el primero en la consulta de control
FASE 3  batería 23/23
FASE 4  comprobaciones 5/5
BANCO   5 verde · 1 rojo (el de arriba) · 3 omitido
```

La puerta de materia de la fase 4 no ha necesitado cambios: el Reglamento del
IVA es IVA, entra por la misma puerta, y el IRPF sigue bloqueado.

## Lo que queda abierto

- **El fichero de casos del banco necesita columna de norma.** Sin ella no se
  puede expresar «art. 78-81 del Reglamento».
- **Las 88 no encontradas del cuerpo 0**: referencias dentro de texto transcrito
  de otras normas. Se resolverían marcando los bloques transcritos, que la
  fase 1 ya distingue (`cita_con_pleca`, blockquote con clase).
- **Nada se ha ejecutado contra el modelo real** todavía: sigue sin credencial.
