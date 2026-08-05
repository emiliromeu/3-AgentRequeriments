# PREPARADO, NO ACTIVO — el texto de los estados para GUIA.md

**Esto no es la guía.** Es el trozo que sustituirá a dos apartados de `GUIA.md`
el día que se enciendan la DGT y el TEAC. Hasta entonces `GUIA.md` se queda
como está.

## Por qué está aparte y no metido ya

La ventana y la hoja impresa **tienen que decir lo mismo, letra por letra**, y
hay una prueba automática que lo comprueba (`prueba_textos_guia`). Si se cambia
uno y no el otro, el profesional lee una cosa en la mesa y otra en pantalla, y
manda la que tiene delante en ese momento. Así que **los dos textos se cambian
a la vez, a mano, el mismo día**:

1. en `interfaz.py`, poner `AGENTE_DGT_TEXTOS=1` (o cambiar el valor por
   defecto), que activa `DISCUTIDO_CON_EJES` y `CLARO_CON_TRES_FUENTES`;
2. en `GUIA.md`, sustituir los dos apartados de abajo;
3. volver a pasar `prueba_textos_guia`, que tiene que salir en verde.

**Se puede esperar sin riesgo.** Con la DGT y el TEAC apagados, el desacuerdo
de fondo solo puede venir de ellos, así que **CRITERIO DISCUTIDO no sale hoy** y
la frase vieja no llega a pantalla.

---

## Sustituye al apartado «⚠️ LO QUE NO HACE»

> ### ⚠️ LO QUE NO HACE
>
> > **No consulta sentencias de los tribunales de justicia.**
> >
> > **Te dice qué dice la ley, qué ha dicho el TEAC y qué criterio tiene la
> > DGT — de lo que hay guardado en la herramienta. No es todo lo que hay.**
>
> La copia de criterio y doctrina es **parcial y de una fecha**: lo que no esté
> guardado, no existe para esto, y no te va a avisar de que falta salvo en el
> bloque «Lo que no se ha podido mirar». Si el asunto depende del criterio
> administrativo, esto es el punto de partida, no la respuesta.

---

## Sustituye al apartado «Los tres estados»

> ### Los tres estados
>
> Salen arriba, en grande. Es lo primero que hay que leer. **El estado habla
> solo de una cosa: si los textos se contradicen entre sí.** No dice si la
> respuesta es buena ni si está completa; para eso está el bloque de abajo.
>
> **CRITERIO CLARO** — *«La ley y el reglamento no se contradicen, y ni la
> doctrina del TEAC ni el criterio de la DGT que hay en la herramienta apuntan
> a otra cosa. NO incluye sentencias de los tribunales de justicia, y el
> criterio puede cambiar: comprueba las citas antes de decidir.»*
>
> **CRITERIO DISCUTIDO** — *«Hay textos que apuntan a soluciones distintas:
> criterio de años distintos sobre el mismo artículo, o un tribunal
> pronunciándose sobre criterio que esta respuesta cita. Lee el desacuerdo de
> arriba y comprueba las citas antes de decidir: aquí no hay un criterio
> único.»*
>
> **NO ENCONTRADO** — *«No hay respaldo suficiente. Abajo tienes los artículos
> encontrados para mirarlos tú.»*
>
> ### Y debajo, dos bloques que no son lo mismo
>
> **DESACUERDO ENTRE LOS TEXTOS.** Solo sale cuando lo hay, y es lo que pone la
> respuesta en DISCUTIDO. Dice qué textos discrepan y cuál manda.
>
> **LO QUE NO SE HA PODIDO MIRAR.** **Sale siempre**, incluso para decir que no
> falta nada. Aquí van los huecos: el artículo cambió después del año del caso,
> remite a una norma que la herramienta no tiene, hay doctrina del TEAC sobre
> ese artículo que nadie ha comprobado que trate de tu supuesto, o una fuente no
> respondía.
>
> **Que un aviso esté aquí abajo no quiere decir que importe menos.** Quiere
> decir que responde a otra pregunta. Arriba: *¿los textos se contradicen?*
> Aquí: *¿qué no he podido mirar?* Un CRITERIO CLARO con cinco avisos de
> cobertura es normal, y hay que leerlos igual.
>
> Antes estas dos cosas iban juntas, y el resultado era que **DISCUTIDO salía en
> 17 de cada 19 consultas**: una etiqueta que sale casi siempre deja de
> informar, y quien la ve por vigésima vez ya no la lee. Medido, no supuesto.
