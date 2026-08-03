# FASE 9 · Las consultas de la DGT — RECONOCIMIENTO

**Estado: reconocimiento hecho, NADA ingerido, NADA implementado.**
Cero llamadas a la API de Anthropic. Lo de aquí es descarga y lectura.

Crudo guardado en `datos/crudo/dgt/` con su `manifiesto.jsonl` y su sha256,
antes de parsear nada, como en la fase 1.

---

## 1 · Qué es y dónde está

`https://petete.tributos.hacienda.gob.es/consultas/` — Doctrina Tributaria,
consultas 1997-2026. Acceso libre y anónimo, confirmado: no pidió identificación
en ningún momento.

### La identidad de la fuente: comprobada, y con un problema

El certificado es auténtico y conviene dejarlo escrito, porque la IP despista:

```
subject   C=ES, L=MADRID, O=DIRECCION GENERAL DE TRIBUTOS,
          serialNumber=S2826008A, CN=*.tributos.hacienda.gob.es
issuer    C=ES, O=FNMT-RCM, OU=AC Componentes Informáticos
validez   26-09-2025  ->  26-09-2026
```

El host resuelve a `82.223.76.235`, que es **hosting comercial** (Arsys/IONOS),
no un rango de Hacienda. Eso por sí solo no dice nada malo: quien manda es el
certificado, y lo firma la **FNMT** a nombre de la Dirección General de Tributos
con su NIF. La fuente es la buena.

**Pero el servidor envía la cadena incompleta:** manda solo el certificado de
servidor y **no el intermedio de la FNMT**. Consecuencia medida en tres clientes
distintos y en dos redes distintas:

| cliente | resultado |
|---|---|
| `curl` con el almacén de macOS | **200 OK**, verificación correcta |
| Python (`urllib` + certifi) | `CERTIFICATE_VERIFY_FAILED` |
| otra red, cliente estricto | `unable to verify the first certificate` |

Los navegadores y macOS lo suplen con intermedios cacheados; un cliente estricto
no. **Esto hay que resolverlo al implementar, y NO desactivando la verificación**
—eso destruiría lo único que garantiza que el criterio viene de quien dice—
sino **aportando el intermedio de la FNMT** junto a la petición.

**Ojo al calendario: el certificado caduca el 26 de septiembre de 2026.**

---

## 2 · Qué hay dentro. La URL por número NO sirve

Esto invalida la premisa de partida y es el hallazgo principal.

`?num_consulta=V1601-22` devuelve **4,8 KB de armazón**, no la consulta. Es una
aplicación **KnoSys** que carga el formulario por JavaScript («Cargando
formulario…») y trae los datos por AJAX. La URL es estable para un navegador,
pero **no es una URL de datos**: descargarla no da la consulta.

### Los endpoints reales, sacados de su propio `knoweb.js`

```
GET   /consultas/do/form        el formulario           (0,13 s, estático)
GET   /consultas/do/info        panel informativo       (24 s medidos)
POST  /consultas/do/search      buscar   + &tab=N&page=N
POST  /consultas/do/document    un documento  + &doc=<id>&tab=N
```

Sesión por cookie `JSESSIONID`. `tab=1` son las **consultas generales**,
`tab=2` las **vinculantes** (las que empiezan por V).

### Los campos del registro

El formulario los declara con el patrón `NMCMP_n` (qué campo) / `VLCMP_n`
(valor) / `OPCMP_n` (operador). Mapeados:

| parámetro | campo | etiqueta en pantalla |
|---|---|---|
| `NMCMP_1` | `NUM-CONSULTA` | Nº de consulta |
| `NMCMP_2` | `FECHA-SALIDA` | Fecha salida desde / hasta |
| `NMCMP_3` | `NORMATIVA` | Normativa |
| `NMCMP_4` | `CUESTION-PLANTEADA` | Cuestión planteada |
| `NMCMP_5` | `DESCRIPCION-HECHOS` | Descripción de hechos |
| `NMCMP_6` | `FreeText` | Texto libre |
| `NMCMP_7` | `CRITERIO` | Criterio de interés (desde 01-01-2022) |

Operadores: `.Y` / `.O` / `.NO`. Ordenación por `NUM-CONSULTA`, `ORGANO` o
`FECHA-SALIDA`. Existe además `ORGANO` como campo de ordenación aunque no de
búsqueda.

**Son exactamente los campos que hacían falta**: número, fecha, normativa citada,
cuestión planteada y hechos. La contestación no es campo de búsqueda, pero es lo
que devuelve `/do/document`.

### La búsqueda por términos: por formulario, NO por URL

No hay forma de buscar por términos con una URL. Hay que **replicar el POST** a
`/do/search` con el formulario serializado. Es perfectamente automatizable —no
requiere navegador ni JavaScript— pero es un POST con sesión, no un `GET` a una
dirección bonita.

---

## 3 · Cómo se comporta ante volumen. **Mal.**

Medido hoy, 2 de agosto de 2026, con volumen bajo y pausas:

| petición | resultado |
|---|---|
| `/do/form` (estático) | 200 en **0,13 s** |
| `/do/info` | 200 en **24,4 s** |
| `/do/search` búsqueda vacía | 200 en **18,9 s** |
| `/do/search` por nº exacto `V1601-22` | **504** a los 60 s |
| `/do/search` repetida, misma forma que la que fue bien | **504** a los 60 s |

**El backend vive pero va a decenas de segundos**, y nginx corta a los 60. Es
intermitente: la misma consulta que respondió en 19 s falló luego con 504. Lo
estático vuela; todo lo que toca el motor documental se arrastra.

Su propio JavaScript documenta los fallos que esperan, lo que confirma que esto
les pasa de serie:

- **408** «la consulta está tardando demasiado tiempo… acote más los parámetros»
- **400** «sintaxis incorrecta… caracteres no permitidos o solo palabras vacías»
- **500** error al ejecutar

`robots.txt` **existe y está vacío**: no declara ninguna restricción. Eso no es
permiso para apretar; con estos tiempos, apretar sería tumbarles el servicio.

No pidió cabeceras especiales. Basta con `User-Agent` identificativo y aceptar
la cookie de sesión.

### Lo que NO he podido ver, y no lo voy a disimular

**No he conseguido descargar ninguna consulta completa.** Los dos intentos de
búsqueda por número acabaron en 504. Por tanto:

- el mapa de campos de arriba sale del **formulario de búsqueda**, que es
  evidencia sólida de la estructura del registro, pero
- **no he visto el marcado real de una contestación**, y hasta verlo no se puede
  escribir el troceo.

Es el primer trabajo cuando se retome: reintentar en horario de menos carga y
guardar un documento entero.

---

## 4 · DISEÑO ACORDADO (anotado, **no implementado**)

- **La ley sigue siendo la pata portante.** La DGT es enriquecimiento. Si la
  fuente cae, el agente **no se muere**: baja de estado y **lo dice**. Con los
  tiempos medidos arriba, esto deja de ser una precaución teórica y pasa a ser
  el caso normal.
- **Caché permanente.** Toda consulta descargada se guarda y no se vuelve a
  pedir. El corpus de criterio crece con el uso y a los meses se responde casi
  sin tocar la web. Con un backend que tarda 20 s o falla, la caché no es una
  optimización: es lo que hace la función viable.
- **El verificador no cambia de reglas.** Fragmento literal más URL que
  resuelve, o no existe. Una consulta cacheada es corpus local y se verifica
  igual que la ley.
- **Las citas se etiquetan distinto.** Una cita de la DGT nunca puede parecer
  una cita de la ley. En la respuesta tiene que verse que es **criterio**, no
  **norma**.
- **Canario diario:** comprobar que la fuente sigue donde estaba. Si falla, la
  fuente se marca caída, **visible, nunca en silencio**. Debe vigilar también
  **la caducidad del certificado** (26-09-2026) y distinguir «lenta» de «caída»,
  porque lo que se ha medido hoy es lentitud intermitente, no caída.

## 5 · PENDIENTE que esto abre

Cuando la DGT entre de verdad, **el texto de `CRITERIO CLARO` deja de ser
cierto**. Hoy dice, en la ventana y en `GUIA.md`, que la DGT y los tribunales no
están en la herramienta. Habrá que reescribirlo en los dos sitios a la vez.
Anotado, **sin tocar**.

**Fuera de alcance:** INFORMA, TEAC, jurisprudencia, CISS.
