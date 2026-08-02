# ARRANQUE — poner el sistema en marcha (macOS)

Las fases 1, 2 y 3 funcionan sin instalar nada: solo librería estándar. La
fase 4 y el banco necesitan el SDK de Anthropic y una credencial.

---

## Los tres pasos

Abre el Terminal y ve al proyecto:

```
cd /Users/viladot/Documents/agente_requeriments
```

### 1 · Instalar el SDK

```
python3 -m venv .venv
.venv/bin/pip install anthropic
```

A partir de aquí, `.venv/bin/python` en lugar de `python3` para todo lo que
llame al modelo. (Ya está hecho en esta máquina: SDK 0.120.2.)

### 2 · Poner la clave en el .env

```
cp .env.ejemplo .env
open -e .env
```

Se abre el editor de texto. Pega la clave **detrás del `=`**, sin espacios ni
comillas, y guarda (⌘S). El fichero tiene que quedar así:

```
ANTHROPIC_API_KEY=sk-ant-api03-loquesea...
```

La clave se saca en <https://platform.claude.com> → **API keys**.

**Esto es lo único que hay que hacer con la clave.** No hace falta ningún
`export`, ni tocar el `.zshrc`, ni recordar nada entre sesiones.

### 3 · Comprobar que funciona

```
.venv/bin/python fase4.py credencial
```

Cuando está bien, dice **de dónde ha leído la clave** y enseña solo los
12 primeros caracteres:

```
[ OK ] credencial correcta (sk-ant-api0…) tomada de fichero
       /Users/viladot/Documents/agente_requeriments/.env;
       acceso al modelo claude-opus-5 confirmado
```

Es una comprobación gratuita: consulta el modelo, no gasta tokens, y verifica
de una vez que la clave vale **y** que la cuenta tiene acceso a `claude-opus-5`.

---

## De dónde sale la clave, y en qué orden

```
1. variable de entorno ANTHROPIC_API_KEY   (manda siempre)
2. fichero .env de la raíz del proyecto
3. error claro
```

Que el entorno mande sobre el `.env` es a propósito: permite probar otra clave
un momento sin editar el fichero.

```
ANTHROPIC_API_KEY='otra-clave' .venv/bin/python fase4.py credencial
```

La comprobación siempre dice cuál de las dos ha usado.

## Qué dice cuando algo falla

Nunca una traza: una frase. Los cinco casos, comprobados uno a uno:

| situación | mensaje |
|---|---|
| SDK sin instalar | `Falta el SDK de Anthropic. Instalalo con: pip install anthropic` |
| sin `.env` ni variable | `No hay ninguna credencial configurada. Crea un fichero .env en la raiz del proyecto con la linea ANTHROPIC_API_KEY=sk-ant-...` |
| clave rechazada | `La credencial existe pero la API la rechaza (401). Revisa que la clave sea correcta y no este revocada.` |
| sin acceso al modelo | `La credencial funciona, pero esta cuenta no tiene acceso al modelo 'claude-opus-5'.` |
| sin red | `No hay conexion con la API de Anthropic. Revisa la red o el proxy.` |

La comprobación corre **al arrancar** —antes de gastar nada— tanto en
`fase4.py consultar` como en `banco.py`. Hace falta porque el SDK no avisa por
su cuenta: `anthropic.Anthropic()` se construye tan tranquilo sin credencial
(`api_key` queda a `None`) y el fallo no aparecería hasta la primera llamada.

## La clave nunca se imprime

Ni entera, ni dentro de un mensaje de error, ni en la traza de una consulta.
Todo mensaje que sale del módulo del modelo pasa por un filtro que tapa
cualquier `sk-ant-…`. Cuando hace falta identificarla, se enseñan **12
caracteres y corte**.

Comprobado: con una clave falsa en el `.env`, ni `fase4.py credencial` ni una
consulta fallida la muestran en ningún punto de su salida.

---

## Primera consulta real

```
.venv/bin/python fase4.py consultar \
    "puedo deducir el IVA de un turismo de empresa" --ejercicio 2023
```

Gasta 2 llamadas (análisis y redacción), o 3 si el verificador rechaza el
primer borrador. Al terminar dice cuántas ha gastado.

## El banco de pruebas

```
.venv/bin/python banco.py                # los 4 bloques, con el modelo real
python3 banco.py --motor ensayo          # sin gastar llamadas ni SDK
.venv/bin/python banco.py --bloques 1,4  # solo algunos
```

Una pasada completa con el modelo real son **~34 llamadas** (15 casos × 2 en el
bloque 2, 3 puertas, 3 corridas × 2 en el bloque 3, y 1 + 15 × 2 en el bloque 4;
el bloque 1 no gasta ninguna). Con `--bloques 1`, cero.

---

## En una máquina nueva

El repositorio **no lleva los datos**: `datos/` está en el `.gitignore` (son
~15 MB de texto del BOE que se vuelven a bajar). Después de clonar:

```
python3 -m venv .venv && .venv/bin/pip install anthropic
cp .env.ejemplo .env        # y pegar la clave
python3 fase1.py ingerir BOE-A-1992-28740    # Ley del IVA
python3 fase1.py ingerir BOE-A-1992-28925    # Reglamento del IVA
python3 fase1.py verificar BOE-A-1992-28740
python3 fase1.py verificar BOE-A-1992-28925
```

Sin ese paso, las fases 2, 3 y 4 dan `[FALLO DE CORPUS] No hay ninguna norma
ingerida`.

## Comandos de todo el sistema

```
python3 fase1.py inspeccionar BOE-A-1992-28740   # ver qué manda el BOE
python3 fase1.py ingerir      BOE-A-1992-28740   # trocear a JSONL
python3 fase1.py verificar    BOE-A-1992-28740   # auditoría del corpus

python3 fase2.py buscar "deducción IVA turismo" --ejercicio 2023
python3 fase2.py diagnostico

python3 fase3.py probar                          # 23 casos adversarios
python3 fase3.py verificar respuesta.txt --ejercicio 2023

.venv/bin/python fase4.py credencial
.venv/bin/python fase4.py consultar "..." --ejercicio 2023
python3 fase4.py comprobaciones                  # con motor de ensayo

python3 banco.py --motor ensayo
```
