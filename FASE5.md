# FASE 5 — Segunda norma: el Reglamento del IVA

Estado: **ingerido sin tocar el código de las fases 1 y 2, como se pidió.
Nada arreglado todavía.** Este documento es la lista.

## Identificador: correcto

`BOE-A-1992-28925` = **Real Decreto 1624/1992, de 29 de diciembre, por el que
se aprueba el Reglamento del Impuesto sobre el Valor Añadido**. Vigente desde
1993-01-01, no derogado, consolidación finalizada. Es la norma aprobatoria, no
un decreto modificador. Procedía ingerir.

## Qué entró

```
LEY 37/1992     243 preceptos,  749 versiones
RD 1624/1992    144 preceptos,  412 versiones   (127 artículos + 16 disp. + 1 anexo)
```

Auditoría de la fase 1 sobre el Reglamento: **0 bloques sin reconocer, 0 sin
texto, 0 sin fecha, 0 sin enlace, 0 sin referencia canónica.** El troceo
aguantó una norma con estructura distinta sin cambiar una línea.

---

# LA LISTA: qué se ha roto

## 1. CRÍTICA · El corpus del Reglamento no se puede ni cargar

```
ErrorCorpus -> Clave duplicada en el corpus: 'articulo 1' (Articulo 1 y Articulo 1)
```

Seis colisiones: `articulo 1` … `articulo 6` apuntan cada uno a dos bloques.

**Causa.** Un RD aprobatorio contiene **dos cuerpos normativos con numeración
propia dentro del mismo identificador del BOE**:

| id | referencia | qué es |
|---|---|---|
| `a1` | Artículo 1 | *Aprobación del Reglamento del IVA* — articulado del Real Decreto |
| `a1-2` | Artículo 1 | *Intervención indirecta del vendedor…* — articulado del Reglamento (su anexo) |
| `a5` | Artículo 5 | *Modificación del Real Decreto 1326/1987* |
| `a5-2` | Artículo 5 | *Reconocimiento de exenciones en operaciones interiores* |

La fase 1 dio por supuesto que **una norma = una secuencia de numeración**. Es
falso para todo real decreto que aprueba un reglamento o un texto refundido, que
es un patrón habitualísimo en derecho español. La referencia canónica necesita
un tercer nivel (norma → cuerpo → artículo), no dos.

Detectado por el control de colisiones de la fase 1, que hasta ahora nunca había
saltado. Esa auditoría se ganó el sueldo aquí.

## 2. CRÍTICA · El sistema es de una sola norma a partir de la fase 2

```
fase2.py:32  CORPUS = .../BOE-A-1992-28740.jsonl
fase3.py:35  CORPUS = .../BOE-A-1992-28740.jsonl
fase4.py:41  CORPUS = .../BOE-A-1992-28740.jsonl
```

La fase 1 sí es multinorma (un JSONL por identificador, y ha ingerido las dos).
De la fase 2 en adelante el corpus está cableado a la Ley. No hay forma de
buscar, verificar ni responder sobre las dos normas a la vez. `Indice` carga
**un** fichero; `GrafoRemisiones` se construye sobre **un** conjunto de
documentos; `Verificador` indexa **un** corpus.

## 3. CRÍTICA · Una remisión del Reglamento a la Ley se resuelve contra el propio Reglamento

Lo más grave de la lista, porque falla **en silencio y con apariencia de acierto**:

```
cita     : "artículo 8.Tres de la Ley del Impuesto"     (en el art. 1 del Reglamento)
debería  : artículo 8 de la LEY 37/1992  — Concepto de entrega de bienes
resuelve : Articulo 8   estado=resuelta
apunta a : Articulo 8 del REGLAMENTO — Aplicación de las exenciones en determinadas operaciones
           https://www.boe.es/buscar/act.php?id=BOE-A-1992-28925#a8
```

Otro precepto, otra rúbrica, enlace a la norma equivocada, y marcado
**"resuelta"** sin ninguna señal.

**Causa.** El Reglamento cita a la Ley **113 veces** como *"de la Ley del
Impuesto"*, una forma que `_RE_ES_OTRA_NORMA` no reconoce: sus alternativas son
`Ley` + número, `Ley de` + palabra, o `Ley` + palabra en mayúscula. En «Ley del
Impuesto» lo que sigue es «del», minúscula. Al no reconocerla como externa, cae
en la rama «de esta norma» y se busca dentro del propio Reglamento.

Cuando el número no existe en el Reglamento (arts. > 82) sale NO_ENCONTRADA, que
es ruidoso pero inofensivo: **129 remisiones no encontradas** en el grafo del
Reglamento, frente a 0 en la Ley. Cuando **sí existe**, se resuelve a la norma
equivocada. Ese es el caso peligroso.

## 4. «del presente Reglamento» se marca externa siendo interna

```
'artículo 24 de este Reglamento'      -> resuelta   (bien, por casualidad)
'artículo 24 del presente Reglamento' -> PENDIENTE externa «Reglamento»   (mal)
```

El error contrario al anterior: pierde remisiones internas buenas. «de este
Reglamento» funciona por accidente —«este» no encaja en ningún patrón y cae en
la rama interna—, no porque esté contemplado. Son 46 apariciones entre las tres
formas.

## 5. Tres preceptos con `fecha_vigencia` vacía — y aquí no se rompió nada

Artículos 33 y 74 bis y la DT cuarta traen `fecha_vigencia=''` (cadena vacía) en
alguna versión. En la Ley no había ni un caso. El `revisar_vigencia` de la fase 1
lo absorbió solo, usando la fecha de publicación y dejándolo anotado. Lo apunto
como lo contrario de una rotura: código defensivo escrito para la errata del
artículo 115 que ha servido para otra cosa distinta.

## 6. Clases de párrafo nuevas — sin consecuencias

`cita` (65), `sangrado` (118), `sangrado_2` (22), `sangrado_articulo` (15),
`subseccion` (4), `anexo_num`, `anexo_tit`. Ninguna es aparato editorial;
entraron como cuerpo, que es lo correcto. El filtro de `<blockquote>` con
atributo `class` de la fase 2 siguió valiendo.

---

# Las premisas de la fase, comprobadas

## «Desbloquea las 72 remisiones PENDIENTE» — **NO. Desbloquea cero.**

De las 72 externas, solo 5 nombran «Reglamento», y las cinco son **reglamentos
comunitarios**, no el Reglamento del IVA:

```
2  Reglamento (UE)                 (952/2013, 2015/2447)
1  Reglamento (UE) n.º 282/2011
1  Reglamento 91/1911/CEE          (DT primera, franquicias de viajeros)
1  Reglamento de Ejecución (UE) 2015/2447   (Anexo)
```

El grueso apunta a otro sitio: **Ley 58/2003 (10) · Ley General Tributaria (7) ·
Ley Concursal (4) · Directiva 2006/112/CE (3) · Ley 49/2002 (3) · Real
Decreto-ley 19/2018 (3) · Código Civil (2)**, y una cola de leyes sueltas.

**Antes: 72 externas + 3 ambiguas. Después: 72 + 3. Sin cambio.** Ingerir el
Reglamento no resuelve ninguna, porque la Ley del IVA apenas remite a su propio
reglamento por esa vía.

## «El art. 95 de la ley remite al reglamento» — **NO.**

```
remisiones salientes resueltas : 0
remisiones salientes pendientes: 0
menciones de "reglament" en su texto: NINGUNA
```

El artículo 95 no remite a nada. Su desarrollo reglamentario existe, pero la
Ley no lo enuncia con una remisión explícita en ese artículo.

## «Declaración recapitulativa es vocabulario del reglamento» — **SÍ.**

```
LEY        : 3 preceptos la mencionan  -> art. 9 bis, 25, 164
REGLAMENTO : 5 preceptos la mencionan  -> art. 24, 78, 79, 80, 81
```

Los artículos 78 a 81 del Reglamento son exactamente el desarrollo del plazo y
contenido de la declaración recapitulativa. La premisa era buena; el problema es
que la fase 2 no puede llegar a ellos (roturas 1 y 2).

---

# Lo que sí se ha comprobado después

## Batería de la fase 3 · 21 casos, en verde

Dos casos nuevos, los que pediste para la ambigüedad entre dos normas:

| caso | esperado | resultado |
|---|---|---|
| `r-cita-sin-norma-con-dos-normas-en-juego` | NO_VERIFICADA | ✅ |
| `r-cita-al-reglamento-por-su-nombre` | NO_VERIFICABLE | ✅ |

El primero cita un fragmento **del Reglamento** con un «artículo 71» a secas.
El 71 existe en las dos normas (en la Ley es *Lugar de realización de las
adquisiciones intracomunitarias*; en el Reglamento, *Liquidación del Impuesto*).
El verificador no lo valida contra la que no toca.

Y `--exigir-norma` cubre el caso de raíz:

```
--exigir-norma=False -> NO_VERIFICADA   (el fragmento no está en ese artículo)
--exigir-norma=True  -> NO_VERIFICABLE  (la cita no dice de qué norma es)
```

La fase 4 ya llama al verificador con `exigir_norma=True`.

## Banco · sigue en 5 VERDE · 1 ROJO · 3 OMITIDO

El rojo sigue rojo, y no he tocado ni el caso ni el tope:

```
[ROJO ] «plazo de declaración recapitulativa»
        esperaba : art. 164 o 165 o 166 o 167 entre los 3 primeros
        ha salido: art. 164 en el puesto 5 (fuera del tope 3)
```

Ingerir el Reglamento no lo arregla **porque la fase 2 sigue buscando solo en la
Ley** (rotura 2). Los artículos que contestarían esa consulta —78 a 81 del
Reglamento— están troceados en disco y son inalcanzables.

## Puerta de materia de la fase 4 · correcta sin tocarla

```
IMPUESTOS_EN_CORPUS = ('IVA', 'desconocido')
  IVA -> pasa · desconocido -> pasa · IRPF -> BLOQUEADA · IS -> BLOQUEADA
```

El Reglamento del IVA es IVA: entra por la misma puerta sin abrirla a IRPF. No
hacía falta cambiar nada.

## Regresión · las fases 1 a 4 sobre la Ley, intactas

Auditoría de la fase 1 correcta · art. 95 el primero en la fase 2 · batería de
la fase 3 en verde (21/21) · comprobaciones de la fase 4 en verde (5/5).

---

# Veredicto

**Tenías un script para la Ley del IVA, no un sistema.** Y la línea está en un
sitio muy concreto:

- **La fase 1 sí generaliza.** Ingirió un real decreto con estructura distinta,
  144 preceptos, 0 sin reconocer, y absorbió sola una errata de fecha que no
  existía en la ley. Lo único que no previó es que un identificador pueda
  contener dos numeraciones.
- **De la fase 2 en adelante, no.** El corpus único está cableado, el grafo de
  remisiones supone una sola norma, y el parser de remisiones está escrito en el
  vocabulario de una ley que se llama a sí misma «esta Ley». El Reglamento se
  llama a sí mismo «este Reglamento» y llama a la ley «la Ley del Impuesto», y
  ninguna de las dos formas estaba contemplada.

Las roturas 1, 2 y 3 son el mismo problema visto desde tres sitios: **la
identidad de un precepto es (norma, cuerpo, artículo), y en todo el sistema está
codificada como (artículo)**.

No he arreglado nada, según lo acordado.
