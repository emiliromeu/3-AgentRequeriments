# FASE 1 — Bajar y trocear el BOE

Estado: **terminada y verificada** sobre BOE-A-1992-28740 (Ley 37/1992, IVA).

```
python fase1.py inspeccionar BOE-A-1992-28740   # primero, siempre
python fase1.py ingerir      BOE-A-1992-28740
python fase1.py verificar    BOE-A-1992-28740
```

`ingerir` y `verificar` trabajan sobre el crudo ya descargado. Para volver a
bajar: `--descargar`. Comprobado que el reproceso funciona con la red cortada.

## Qué hay en disco

```
datos/crudo/BOE-A-1992-28740/     respuestas tal cual llegaron. No se borran.
  texto_<sello>.xml               5,4 MB, el corpus entero
  metadatos_<sello>.json          título, rango, ELI, URL consolidada
  indice_<sello>.json             listado de bloques
  analisis_<sello>.json           referencias y materias (aún sin usar)
  *.meta.json                     url, código HTTP, sha256, tamaño, cabeceras
  manifiesto.jsonl                histórico de descargas, append-only
  fallo-*.json                    respuestas de error, guardadas aparte

datos/corpus/BOE-A-1992-28740.jsonl              243 preceptos citables
datos/corpus/BOE-A-1992-28740.descartados.jsonl   64 bloques no citables
```

## Lo que se aprendió mirando la API (no estaba en la documentación)

1. **`/texto` y `/texto/bloque/…` sólo hablan XML.** Con
   `Accept: application/json` devuelven **400**. `/metadatos`, `/texto/indice`
   y `/analisis` sí dan JSON. Esto por sí solo justifica el modo `inspeccionar`.

2. **Una sola petición trae toda la ley**: `/texto` devuelve los 307 bloques con
   sus 822 versiones en 1,6 s. No hacen falta 307 llamadas.

3. **Cada bloque trae TODAS sus versiones**, con `fecha_publicacion`,
   `fecha_vigencia` e `id_norma` (la norma que introdujo el cambio). Es
   exactamente lo que hace falta para contestar un caso de 2023 con el texto de
   2023. Máximo observado: 41 versiones en un mismo bloque.

4. **El `id` del bloque NO es el número de artículo.** Trampa seria:

   | id            | es en realidad          |
   |---------------|-------------------------|
   | `a1-2`        | Artículo 163 quinvicies |
   | `a8-2`        | Artículo 8 bis          |
   | `a2-2`        | Artículo 20 bis         |

   24 bloques en esta ley. La referencia canónica se deriva **siempre** del
   atributo `titulo`; el `id` sólo vale como ancla del enlace (`…#a95`,
   comprobado que resuelve en el HTML del BOE).

5. **`<p class="nota_pie">` no es texto normativo**: es el historial de
   reformas ("Se modifica el apartado 2 por el art. 1.1 de la Ley 28/2014").
   Son 3.413 párrafos de 23.460. Van en `notas_boe`, **separados del cuerpo**,
   por dos motivos:
   - si se mezclasen, la búsqueda daría positivos sobre texto que no es norma;
   - el verificador de la fase 3 podría dar por buena una cita literal contra
     una frase que el legislador nunca promulgó.

   Además sirven de insumo directo para el aviso de "esto cambió después del
   ejercicio": 661 notas, 607 con fecha de norma y 606 con su `BOE-A-…`.

6. **`fecha_caducidad`** (atributo de `<bloque>`, 7 casos) marca preceptos que
   dejaron de aplicarse: arts. 163 bis/ter/quáter caducaron el 28-11-2014. Para
   un caso de 2013 eran aplicables; para uno de 2023, no.

## Dos erratas del propio BOE, tratadas sin taparlas

- **Artículo 115**: declara `fecha_vigencia="09980101"` (año 998) habiendo sido
  publicado el 31-12-1997. Se conserva el valor crudo en `fecha_vigencia` y se
  calcula aparte `fecha_vigencia_efectiva` (la de publicación), dejando
  constancia en `incidencias`. Corregirlo en silencio sería tapar un error del
  origen; dejarlo tal cual haría que ese texto pareciese vigente desde la Edad
  Media al filtrar por ejercicio.

- **Sufijos latinos con errata**: `140 cuarter`, `140 quinque`, `163 sexvivies`.
  El sufijo **se conserva siempre**, se reconozca o no, y se anota como aviso.
  Descartar un sufijo desconocido fusionaría el "163 quáter" con el "163", que
  son preceptos distintos y ambos existen. La tilde tampoco decide nada: todo se
  compara sin tildes.

## Esquema de cada línea del JSONL

| campo | qué es |
|---|---|
| `referencia`, `referencia_corta`, `clave` | cita canónica, derivada del título |
| `tipo` | `articulo`, `disposicion_adicional/transitoria/derogatoria/final`, `anexo` |
| `numero`, `numero_norm`, `ordinal` | "8 bis" / "8 bis" / nº de la disposición |
| `rubrica` | epígrafe ("Limitaciones del derecho a deducir.") |
| `contexto` | Título y Capítulo en que vive (vacío en disposiciones: penden de la ley) |
| `texto_vigente`, `vigente_desde` | última versión consolidada |
| `versiones[]` | `texto`, `fecha_publicacion`, `fecha_vigencia`, `fecha_vigencia_efectiva`, `id_norma_origen`, `suprimido` |
| `fechas_vigencia` | todas las fechas efectivas, en orden |
| `caducado_desde` | fecha en que dejó de aplicarse, si la hay |
| `notas_boe[]` | `accion`, `norma_citada`, `fecha_norma`, `refs_boe` |
| `url`, `url_api` | enlace profundo al HTML del BOE y al bloque en la API |
| `incidencias`, `avisos` | todo lo raro, por escrito |

## Resultado de la auditoría

```
bloques en el XML          307
citables                   243   (216 artículos + 26 disposiciones + 1 anexo)
no citables                 64   (60 encabezados, 2 preámbulo, 1 firma, 1 metadato)
versiones guardadas        749
notas de reforma           661
sin reconocer                0
sin texto / sin fecha        0
referencias duplicadas       0
cobertura        1993-01-01 … 2026-02-28
```

## Decisiones que conviene no deshacer

- Se trocea **por precepto**, nunca por longitud. Un artículo largo se queda
  entero; dos cortos no se juntan.
- Las disposiciones son ciudadanas de primera: mismo tratamiento que los
  artículos, porque ahí viven las excepciones.
- Lo no citable **no se tira**: va a `.descartados.jsonl` para poder auditarlo.
- El crudo se escribe **antes** de parsear nada, y las respuestas de error se
  guardan con prefijo `fallo-` para que nunca se reutilicen como si fueran
  buenas (ya ocurrió una vez en pruebas: un 404 en XML entró por donde se
  esperaba el JSON de metadatos).

## Lo que queda abierto para las fases siguientes

- El campo `notas_boe[].refs_boe` da los `BOE-A-…` de las normas modificadoras:
  es la base del aviso de la fase 2 ("este artículo cambió después de 2023").
- `analisis.json` ya está descargado y sin usar: trae referencias normativas a
  nivel de norma, útiles si más adelante se encadenan leyes (LIVA ↔ RIVA).
- El troceo no depende de la ley: `python fase1.py inspeccionar <ID>` sirve para
  cualquier norma consolidada. Los identificadores los das tú.
- La jerarquía de fuentes (TS > TEAC > DGT > INFORMA) no está implementada, pero
  el registro lleva `norma_id` y `tipo`, que es donde colgaría el peso de fuente.
