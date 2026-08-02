# FASE 3 — El verificador

Estado: **terminada. Batería en verde: 19 de 19 casos.**

```
python fase3.py probar casos/bateria.txt
python fase3.py verificar respuesta.txt --ejercicio 2023
python fase3.py verificar respuesta.txt --ejercicio 2023 --json informe.json
```

Determinista: ni IA, ni red, ni azar. Dos ejecuciones dan byte a byte lo mismo.
Solo lee el corpus; no lo toca.

Códigos de salida: `0` ACEPTADO / batería verde · `2` RECHAZADO / batería roja ·
`1` error de uso.

## Los tres estados

| estado | significa |
|---|---|
| **VERIFICADA** | el precepto existe, el fragmento está literalmente en él, y en la versión que aplicaba al ejercicio |
| **NO VERIFICADA** | se ha podido comprobar y no cuadra. Siempre con el motivo exacto |
| **NO VERIFICABLE** | no se puede comprobar: la norma no está en el corpus |

**NO VERIFICABLE no es VERIFICADA.** Es la trampa cómoda de todo verificador:
dar por bueno lo que no se ha mirado. Una remisión al Reglamento del IVA no se
puede comprobar hoy, y arrastra a la respuesta entera.

**Si una sola cita no queda VERIFICADA, el veredicto global es RECHAZADO.** No
hay aprobado parcial.

## Qué comprueba cada cita

1. **La referencia existe.** El art. 999 no existe → NO VERIFICADA.
2. **El sufijo es el que se cita.** El 163 y el 163 bis conviven y son
   distintos: se busca la clave exacta, sin caer nunca al número base.
3. **El fragmento está literalmente** en ese artículo.
4. **En la versión del ejercicio**, no en otra.
5. **No estaba caducado ni sin entrar en vigor** en ese ejercicio.
6. **El enlace apunta al ancla correcta** (`#a95`).

## La regla que viene de las dos fases anteriores

Lo que sale de una nota al pie, del historial de reformas o del aparato
editorial del BOE **no es norma y no puede validar nada**, aunque el texto esté
literalmente ahí. El motivo lo dice con todas las letras:

```
MOTIVO: el texto existe pero NO ES ARTICULADO: sale de nota al pie del BOE
        (historial de reformas) de Articulo 95. Ese material no es texto
        promulgado y no puede fundamentar nada
```

Esto sólo funciona porque la fase 1 los guarda separados (`notas_boe`,
`notas_editoriales`) y la fase 2 los dejó fuera del índice. Es la pieza que
cierra el problema que venía arrastrándose.

## Comparación del texto literal

Se normalizan **espacios, saltos de línea, comillas tipográficas** (`« » “ ” "`)
y guiones raros. **Los acentos NO**: en un texto jurídico son parte de la cita.
Las mayúsculas tampoco.

Cuando falla por poco, se dice por qué en vez de soltar un «no aparece» inútil:

- `coincide salvo por las tildes, que en un texto jurídico son parte de la cita`
- `coincide salvo por mayúsculas/minúsculas, y una cita se copia tal cual`

**Puntos suspensivos**: una cita que une dos trozos no contiguos no es literal.
Se rechaza y se informa del estado de cada trozo por separado, para que se
reescriban como dos citas.

## Formato de cita que entiende

Las dos formas que salen naturales al escribir en castellano jurídico, porque
la fase 4 va a usar ambas:

```
«fragmento literal» (art. 95 LIVA, https://www.boe.es/...#a95)
El artículo 95 LIVA dispone que «fragmento literal»
```

## La batería

19 casos escritos a mano, cada uno con el veredicto que debe dar. Los fragmentos
están copiados del corpus para que un fallo sea del verificador y no una errata
mía.

| caso | esperado | qué prueba |
|---|---|---|
| a | NO VERIFICADA | artículo 999, que no existe |
| b | NO VERIFICADA | artículo real, frase inventada |
| c | NO VERIFICADA | literal, pero de la versión de 1993 |
| **d** | NO VERIFICADA | **texto sacado de una nota al pie** |
| **d2** | NO VERIFICADA | **texto del aparato editorial** |
| e | NO VERIFICABLE | remisión al Reglamento del IVA |
| f | VERIFICADA | comillas rectas, saltos de línea y espacios de más |
| g | NO VERIFICADA | puntos suspensivos uniendo trozos |
| h | NO VERIFICADA | cita al 163 con texto del 163 bis |
| i | NO VERIFICADA | 163 bis en 2020, caducado en 2014 |
| i2 | VERIFICADA | el mismo en 2013, cuando sí aplicaba (control positivo) |
| **j** | RECHAZADO | **cinco citas buenas y una mala** |
| k | ACEPTADO | todo correcto (control positivo del global) |
| l | NO VERIFICADA | enlace que apunta al artículo 94 |
| m | NO VERIFICADA | entrecomillado sin referencia |
| n | NO VERIFICADA | una tilde cambiada |
| o | VERIFICADA | disposición transitoria |
| p | NO VERIFICADA | art. 8 bis en 2015, cuando aún no existía |
| q | RECHAZADO | texto sin ninguna cita |

En el caso (j) las cinco buenas salen VERIFICADAS y sólo la sexta falla; el
global es RECHAZADO igualmente.

## Un fallo mío que la batería cazó

El caso (k) suspendió a la primera, y descubrió algo peor de lo que parecía.
Cuando una cita se cierra sólo con el enlace —`«...» (https://...#a95).`— el
parser seguía leyendo y encontraba el número de artículo de la **frase
siguiente**, atribuyendo la cita a otro precepto.

Lo grave: el caso (j) *pasaba* pese a ello, porque sus seis citas quedaban mal
atribuidas y salía RECHAZADO por los motivos equivocados. Un caso en verde por
el motivo incorrecto es peor que uno en rojo.

Corregido con un orden de preferencia explícito: **(1)** el paréntesis pegado a
la comilla, **(2)** lo que hay justo antes —y de eso, lo más cercano, no lo
primero—, **(3)** lo que sigue, recortado en el punto o en la siguiente comilla.
Comprobado después que en el caso (j) las cinco buenas verifican y la mala es la
sexta.

## Dos cosas que se avisan pero no tumban la cita

- **Fragmento muy corto** (menos de 25 caracteres): es literal, pero por sí solo
  no sostiene una afirmación jurídica. Se hace constar.
- **Norma no indicada**: `art. 95` a secas se entiende de la Ley 37/1992, que es
  la única del corpus. Es razonable, pero es una **suposición**, y queda
  anotada. Con `--exigir-norma` deja de suponerse y pasa a NO VERIFICABLE.
  Es el único camino por el que podría colarse un falso VERIFICADA, así que
  conviene que la fase 4 nombre siempre la norma.

También se listan aparte las **referencias citadas sin fragmento literal**: no
tumban el veredicto por sí solas, pero una afirmación jurídica sin fragmento
literal no está respaldada.

## Salida JSON para la fase 4

Consumible sin parsear texto:

```json
{
  "veredicto": "RECHAZADO",
  "motivo_global": "2 de 3 citas no han quedado VERIFICADAS ...",
  "ejercicio": 2023,
  "resumen": {"total": 3, "verificadas": 1, "no_verificadas": 1,
              "no_verificables": 1, "referencias_sin_literal": 0},
  "citas": [{
      "n": 1, "estado": "NO_VERIFICADA", "motivo": "...",
      "referencia_citada": "art. 95", "referencia_corpus": "Articulo 95",
      "clave": "articulo 95", "norma": "liva",
      "version_usada": {"orden": 1, "fecha_vigencia_efectiva": "1998-01-01",
                        "de_un_total": 2},
      "enlace_citado": "...", "enlace_correcto": "...",
      "comprobaciones": ["..."],
      "hallazgos": [{"referencia": "Articulo 95", "origen": "nota_boe"}]
  }]
}
```

`hallazgos` dice dónde está de verdad el texto citado: es lo que permite decir
«no está en el 163, está en el 163 bis» o «esto sale de una nota al pie».

## Para la fase 4

- Toda salida del modelo pasa por aquí antes de mostrarse. `veredicto !=
  ACEPTADO` → no se enseña.
- La fase 4 debe **nombrar la norma** en cada cita y **no usar puntos
  suspensivos**: son los dos motivos evitables de rechazo.
- El verificador no juzga si la cita *sostiene* lo que se afirma: comprueba que
  existe, que es literal y que es de la versión correcta. Lo otro lo decide la
  persona, que para eso se le deja el expediente montado.
