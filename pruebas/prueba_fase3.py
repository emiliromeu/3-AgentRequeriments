#!/usr/bin/env python3
"""`fase3.py verificar` MIRA LAS CACHES DE VERDAD. Cero red, cero API.

    python pruebas/prueba_fase3.py

EL FALLO QUE ESTO VIGILA YA PASO UNA VEZ. `fase3.py verificar` construia el
verificador inyectandole `casos/dgt_prueba/` y `casos/teac_prueba/`, que son las
caches de criterio INVENTADO que necesita `probar` para sus casos adversarios.
Quien verificara un texto real con ese comando lo comparaba contra material de
mentira, y el resultado era falso EN LAS DOS DIRECCIONES:

  · una cita a una consulta AUTENTICA salia NO_VERIFICABLE, porque esa consulta
    no esta en `casos/dgt_prueba/`;
  · una cita a un caso ADVERSARIO INVENTADO salia VERIFICADA.

Se arreglo, y el arreglo quedo escrito en un comentario dentro de
`modo_verificar`. UN COMENTARIO NO ES UNA PRUEBA: no se pone rojo cuando
alguien vuelve a inyectarlas, y la unica suite que miraba esto -
`prueba_verificar_json`- guarda `verificar_json.py`, que es otro programa.

SE MIDE LO QUE SALE, NO LO QUE PONE EL CODIGO. La comprobacion principal no es
leer el fichero: es ejecutar `fase3.py verificar` de verdad, dos veces, con dos
citas construidas para que el resultado sea el CONTRARIO segun que cache mire.
Si alguien reinyecta las de prueba, las dos se dan la vuelta.

Y LA OTRA MITAD, que hace falta: `probar` TIENE que seguir usando las de
prueba. Sin esa comprobacion, la forma mas segura de aprobar esta suite seria
borrar las caches de prueba, y con ellas la bateria de casos adversarios entera.
"""
import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

PY_EXE = sys.executable
GUION = RAIZ / "fase3.py"
DGT_PRUEBA = RAIZ / "casos" / "dgt_prueba"

fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:140]}" if not ok else ""))
    if not ok:
        fallos.append(que)


def verificar(texto: str, *args):
    """Ejecuta `fase3.py verificar` de verdad sobre un texto. -> (codigo, json)."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as f:
        f.write(texto)
        ruta = f.name
    try:
        r = subprocess.run([PY_EXE, str(GUION), "verificar", ruta,
                            "--json-stdout", *args],
                           capture_output=True, text=True, cwd=str(RAIZ))
        # `--json-stdout` pinta ademas el informe legible: el JSON es lo que
        # empieza por la primera llave.
        i = r.stdout.find("{")
        try:
            return r.returncode, json.loads(r.stdout[i:]) if i >= 0 else None
        except ValueError:
            return r.returncode, None
    finally:
        Path(ruta).unlink(missing_ok=True)


def estados(informe) -> list:
    return [c.get("estado") for c in ((informe or {}).get("citas") or [])]


# ==================================== EL MATERIAL, SACADO DE LAS CACHES
#
# NADA ESCRITO A MANO. La cita autentica se construye leyendo una consulta de
# la despensa de verdad y copiando un trozo literal de su texto; la inventada,
# leyendo una de `casos/dgt_prueba/`. Escribir cualquiera de las dos de memoria
# seria un dato inventado con formato de real, que es la primera regla del
# proyecto -y ya nos costo una vez: el fragmento de un caso positivo escrito de
# memoria salio NO_VERIFICADA-.

from agente_fiscal import dgt as D                   # noqa: E402

_de_prueba = {p.stem.upper() for p in DGT_PRUEBA.glob("*.json")}
_autentica = None
for _c in D.CacheDGT().todas():
    if _c.numero.upper() in _de_prueba:
        continue
    _texto = " ".join((_c.contestacion or "").split())
    if len(_texto) > 500:
        _autentica = (_c.numero.upper(), _texto[200:320], _c.url)
        break
if _autentica is None:
    print("\n  No hay ninguna consulta autentica en la despensa: sin material")
    print("  no se puede probar nada. ¿Falta `git pull`?")
    sys.exit(1)

NUM_REAL, TROZO_REAL, URL_REAL = _autentica
_inv = json.loads(sorted(DGT_PRUEBA.glob("*.json"))[0].read_text(encoding="utf-8"))
NUM_INV = _inv.get("numero", "").upper()
TROZO_INV = " ".join((_inv.get("contestacion") or "").split())[:110]
URL_INV = _inv.get("url") or (
    f"https://petete.tributos.hacienda.gob.es/consultas/?num_consulta={NUM_INV}")


def cita(trozo, numero, url):
    return (f"El criterio administrativo señala que «{trozo}» "
            f"[Consulta DGT {numero} — {url}].")


CITA_REAL = cita(TROZO_REAL, NUM_REAL, URL_REAL)
CITA_INVENTADA = cita(TROZO_INV, NUM_INV, URL_INV)

print(f"\n  consulta autentica de la despensa : {NUM_REAL}")
print(f"  consulta inventada de casos/       : {NUM_INV}")


# ==================================== 1. LAS DOS DIRECCIONES
print("\n=== 1. `verificar` MIRA LA DESPENSA DE VERDAD ===")
print("  Las dos citas de abajo dan resultados OPUESTOS segun que cache se")
print("  mire. Si alguien reinyecta las de prueba, las dos se dan la vuelta.\n")

cod, inf = verificar(CITA_REAL)
comprobar("una cita a una consulta AUTENTICA se verifica",
          estados(inf) == ["VERIFICADA"], (cod, estados(inf), inf))

cod, inf = verificar(CITA_INVENTADA)
comprobar("una cita a una consulta INVENTADA no se da por buena",
          estados(inf) == ["NO_VERIFICABLE"], (cod, estados(inf), inf))
comprobar("  y dice por que: no esta en la copia local",
          "no esta en la copia local" in json.dumps(inf, ensure_ascii=False),
          inf)


# ==================================== 2. `probar` SIGUE CON LAS DE PRUEBA
print("\n=== 2. Y `probar` TIENE QUE SEGUIR USANDO LAS DE PRUEBA ===")
print("  Es la otra mitad, y hace falta: sin ella, la forma mas segura de")
print("  aprobar la comprobacion de arriba seria borrar `casos/dgt_prueba/`,")
print("  y con ella la bateria de casos adversarios entera.\n")

r = subprocess.run([PY_EXE, str(GUION), "probar"], capture_output=True,
                   text=True, cwd=str(RAIZ))
comprobar("la bateria de casos adversarios sigue en verde",
          r.returncode == 0, r.stdout[-200:])
comprobar("  y son los 41 casos, no una bateria vacia",
          "41 casos" in r.stdout, r.stdout[-120:])
comprobar("las caches de prueba siguen existiendo",
          len(list(DGT_PRUEBA.glob("*.json"))) >= 2)


# ==================================== 3. Y EN EJECUCION, QUE FICHEROS ABRE
print("\n=== 3. EN EJECUCION NO ABRE NI UN FICHERO DE `casos/*_prueba` ===")
print("  Lo de arriba mide el resultado; esto mira lo que toca el proceso, que")
print("  es lo que no se puede disimular.\n")

sonda = RAIZ / "datos" / "_sonda_fase3.txt"
with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                 encoding="utf-8") as f:
    f.write(CITA_REAL)
    entrada = f.name
codigo = (
    "import builtins, sys\n"
    "from pathlib import Path\n"
    "_abrir, _o = builtins.open, Path.open\n"
    "vistas = []\n"
    "def espia(f, *a, **k):\n"
    "    vistas.append(str(f)); return _abrir(f, *a, **k)\n"
    "def espia_p(self, *a, **k):\n"
    "    vistas.append(str(self)); return _o(self, *a, **k)\n"
    "builtins.open = espia; Path.open = espia_p\n"
    "sys.argv = ['fase3.py', 'verificar', ENTRADA]\n"
    "import runpy\n"
    "try:\n"
    "    runpy.run_path('fase3.py', run_name='__main__')\n"
    "except SystemExit:\n"
    "    pass\n"
    "builtins.open = _abrir; Path.open = _o\n"
    "_abrir(SONDA, 'w').write('\\n'.join(vistas))\n"
).replace("ENTRADA", repr(entrada)).replace("SONDA", repr(str(sonda)))
subprocess.run([PY_EXE, "-c", codigo], cwd=str(RAIZ), capture_output=True,
               text=True)
try:
    rutas = sonda.read_text("utf-8").splitlines() if sonda.is_file() else []
    con_prueba = [x for x in rutas if "_prueba" in x]
    comprobar("no abre ningun fichero de una cache de prueba",
              not con_prueba, con_prueba[:3])
    comprobar("  y si abre la despensa real de la DGT",
              any("datos/dgt" in x for x in rutas), len(rutas))
    # EL CONTROL de la sonda: si no hubiera visto nada, lo de arriba pasaria
    # sin comprobar nada.
    comprobar("  la sonda ha visto ficheros, no una lista vacia",
              len(rutas) > 20, len(rutas))
finally:
    sonda.unlink(missing_ok=True)
    Path(entrada).unlink(missing_ok=True)


# ==================================== 4. Y EN EL CODIGO, POR SI ACASO
print("\n=== 4. `modo_verificar` NO NOMBRA NINGUNA CACHE DE PRUEBA ===")
print("  Se pregunta al arbol de sintaxis y SOLO por el cuerpo de esa funcion:")
print("  el fichero entero las nombra a proposito, en `probar` y en los")
print("  comentarios que explican por que no van aqui.\n")

arbol = ast.parse(GUION.read_text(encoding="utf-8"))
cuerpo = next((n for n in ast.walk(arbol)
               if isinstance(n, ast.FunctionDef) and n.name == "modo_verificar"),
              None)
comprobar("existe `modo_verificar`", cuerpo is not None)
if cuerpo is not None:
    fuente = ast.unparse(cuerpo)
    sospechas = [x for x in ("dgt_prueba", "teac_prueba", "_de_prueba",
                             "cache_dgt=", "cache_teac=") if x in fuente]
    comprobar("y su codigo no nombra ninguna", not sospechas, sospechas)
    # EL CONTROL: el patron tiene que cazar lo que busca.
    comprobar("  y el patron cazaria una inyeccion de verdad",
              "cache_dgt=" in "v = VF.Verificador(ix, cache_dgt=_cache_dgt_de_prueba())")


# ==================================== CONTROL NEGATIVO
print("\n=== CONTROL NEGATIVO: la suite tiene que ponerse roja ===")
print("  Se reinyectan las caches de prueba EN UNA COPIA y se comprueba que")
print("  las dos citas se dan la vuelta. Sin esto, un verde no dice nada.\n")

copia = RAIZ / "fase3_REINYECTADO_por_la_suite.py"
try:
    fuente = GUION.read_text(encoding="utf-8")
    roto = fuente.replace(
        "    v = VF.Verificador(ix)\n",
        "    v = VF.Verificador(ix, cache_dgt=_cache_dgt_de_prueba(),\n"
        "                       cache_teac=_cache_teac_de_prueba())\n", 1)
    assert roto != fuente, "no se ha podido reinyectar en la copia"
    copia.write_text(roto, encoding="utf-8")

    def con_copia(texto):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as f:
            f.write(texto)
            ruta = f.name
        try:
            r = subprocess.run([PY_EXE, str(copia), "verificar", ruta,
                                "--json-stdout"], capture_output=True,
                               text=True, cwd=str(RAIZ))
            i = r.stdout.find("{")
            return json.loads(r.stdout[i:]) if i >= 0 else None
        finally:
            Path(ruta).unlink(missing_ok=True)

    comprobar("con las de prueba inyectadas, la cita AUTENTICA deja de "
              "verificarse", estados(con_copia(CITA_REAL)) == ["NO_VERIFICABLE"],
              estados(con_copia(CITA_REAL)))
    comprobar("  y la INVENTADA pasa a darse por buena",
              estados(con_copia(CITA_INVENTADA)) == ["VERIFICADA"],
              estados(con_copia(CITA_INVENTADA)))
finally:
    copia.unlink(missing_ok=True)


print("\n" + "=" * 74)
if fallos:
    print(f"{len(fallos)} FALLO(S):")
    for f in fallos:
        print(f"   - {f}")
    sys.exit(1)
print("TODO EN VERDE · `verificar` mira la despensa de verdad, y se nota")
sys.exit(0)
