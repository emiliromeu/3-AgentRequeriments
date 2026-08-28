#!/usr/bin/env python3
"""QUE LA COPIA DE LA OFICINA SE PUEDA ACTUALIZAR. Cero red, cero API.

    python pruebas/prueba_pull.py

EL FALLO QUE ESTO CIERRA no daba error en ninguna maquina: daba una semana de
goteo -986 consultas- que no llegaba a nadie. `actualizar` hacia exactamente lo
que dice que hace, negarse a actualizar encima de cambios sin guardar; lo que
pasaba es que los cambios los escribiamos NOSOTROS.

LA REGLA QUE SE VIGILA AQUI, y es una sola:

    UN FICHERO NO PUEDE VIAJAR POR GIT **Y** REESCRIBIRSE EN LA MAQUINA DE
    DESTINO. Una de las dos cosas, nunca las dos.

Las tres salidas son validas y cada fichero tiene la suya:

  · `datos/dgt/indice.json`      NO VIAJA. Es derivado y se rehace del disco.
  · `datos/dgt/consultas/*.json` NO SE REESCRIBE. Lo que baja la demanda cae en
                                 `demanda/`, que no viaja.
  · `normas_del_corpus.json`     NO SE REESCRIBE si no ha cambiado la lista.

Y para las copias que ya se rompieron antes de todo esto, `reparar.py`, que se
prueba de punta a punta: se monta una copia rota de verdad y se comprueba que
queda al dia SIN perder la despensa por demanda.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

PY_EXE = sys.executable
fallos = []


def comprobar(que, ok, obtenido=""):
    print(f"  {'OK  ' if ok else 'FALLO'} {que}"
          + (f"   -> {str(obtenido)[:140]}" if not ok else ""))
    if not ok:
        fallos.append(que)


def git(*args, cwd=None):
    r = subprocess.run(["git", *args], cwd=str(cwd or RAIZ),
                       capture_output=True, text=True, errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# ==================================== 1. QUE VIAJA Y QUE SE ESCRIBE
print("\n=== 1. NADA VIAJA Y SE REESCRIBE A LA VEZ ===")
print("  Cada fichero de esta lista se reescribia en la maquina de destino con")
print("  solo usar el agente, y cada uno era un choque seguro en el pull.\n")

seguidos = set(git("ls-files")[1].split())

comprobar("`datos/dgt/indice.json` ya no viaja",
          "datos/dgt/indice.json" not in seguidos)
comprobar("  y git lo tiene excluido a proposito",
          git("check-ignore", "datos/dgt/indice.json")[0] == 0)
comprobar("`datos/dgt/demanda/` sigue sin viajar: son las fechas del despacho",
          git("check-ignore", "datos/dgt/demanda")[0] == 0)
comprobar("`GUIA.md` sigue sin viajar: se regenera en cada equipo",
          "GUIA.md" not in seguidos
          and git("check-ignore", "GUIA.md")[0] == 0)
# LO QUE SI TIENE QUE VIAJAR. Si esto se pusiera en rojo por un `.gitignore`
# demasiado ancho, la oficina se quedaria sin saber que normas existen.
comprobar("`normas_del_corpus.json` SI viaja: es lo unico del corpus que puede "
          "llegar a otro equipo", "normas_del_corpus.json" in seguidos)
comprobar("y las consultas del barrido SI viajan",
          any(x.startswith("datos/dgt/consultas/") for x in seguidos))


# ==================================== 2. LA DEMANDA NO CAE EN LO QUE VIAJA
print("\n=== 2. LO QUE BAJA LA COLA POR DEMANDA CAE EN `demanda/` ===")
print("  Bajaba con la cache de siempre, asi que cada descarga de la oficina")
print("  caia TAMBIEN en `consultas/`, con el nombre exacto de un fichero que")
print("  el pull iba a traer. Y de paso el historial de lo que pregunta el")
print("  despacho acababa en el repositorio.\n")

import petete                                        # noqa: E402
from agente_fiscal import cola as COLA               # noqa: E402

corral = Path(tempfile.mkdtemp(prefix="pull_"))
try:
    viaja = corral / "consultas"
    no_viaja = corral / "demanda"
    guardado = (petete.DIR_CRUDO, petete.DIR_CONSULTAS, petete.DIR_BUSQUEDAS,
                petete.INDICE)
    petete.DIR_CRUDO = corral / "crudo"
    petete.DIR_CONSULTAS = viaja
    petete.DIR_BUSQUEDAS = corral / "busquedas"
    petete.INDICE = corral / "indice.json"
    viaja.mkdir(parents=True, exist_ok=True)
    (viaja / "V1111-11.json").write_text(
        json.dumps({"numero": "V1111-11", "doc_id": "9", "tab": "2"}),
        encoding="utf-8")

    cache = petete.Cache(dir_escritura=no_viaja)
    cache.guardar_documento("V9999-99", {"numero": "V9999-99"})
    comprobar("un documento nuevo cae en `demanda/`",
              (no_viaja / "V9999-99.json").is_file())
    comprobar("  y NO en la carpeta que viaja",
              not (viaja / "V9999-99.json").is_file())
    # Y SE SIGUE ENCONTRANDO: si al separarlas dejara de verse, la oficina
    # volveria a pedir lo que ya tiene.
    comprobar("  pero se sigue viendo desde la cache", cache.tiene("V9999-99"))
    comprobar("  y lo que ya estaba en la que viaja, tambien",
              cache.tiene("V1111-11") and cache.leer("V1111-11") is not None)

    # EL INDICE SE REHACE DEL DISCO. Es lo que permite que deje de viajar.
    petete.INDICE.unlink(missing_ok=True)
    otra = petete.Cache(dir_escritura=no_viaja)
    comprobar("sin fichero de indice, se rehace de los documentos",
              otra.indice["consultas"].get("V1111-11", {}).get("doc_id") == "9",
              otra.indice["consultas"].get("V1111-11"))
    comprobar("  y se guarda, para no rehacerlo en cada arranque",
              petete.INDICE.is_file())
finally:
    (petete.DIR_CRUDO, petete.DIR_CONSULTAS, petete.DIR_BUSQUEDAS,
     petete.INDICE) = guardado
    shutil.rmtree(corral, ignore_errors=True)

# Y LA COLA LA CONSTRUYE ASI. Lo de arriba prueba que la cache sabe hacerlo;
# esto, que la cola se lo pide.
FUENTE_COLA = (RAIZ / "agente_fiscal" / "cola.py").read_text("utf-8")
comprobar("la cola construye la cache apuntando a `demanda/`",
          "petete.Cache(dir_escritura=DEMANDA)" in FUENTE_COLA)


# ==================================== 3. LA LISTA NO SE REESCRIBE POR NADA
print("\n=== 3. LA LISTA QUE VIAJA NO SE REESCRIBE SI NO HA CAMBIADO ===")
print("  La regenera `fase1 ingerir`, y a `fase1 ingerir` lo llama el")
print("  INSTALADOR: cualquier equipo, el dia que se instalaba, se quedaba con")
print("  el fichero modificado en el `generado` y ya no volvia a actualizarse.\n")

from agente_fiscal import catalogo as CAT            # noqa: E402
antes = CAT.LISTA.read_bytes()
CAT.regenerar()
CAT.regenerar()
comprobar("regenerar dos veces no cambia ni un byte",
          CAT.LISTA.read_bytes() == antes)
comprobar("  y git no ve nada",
          not git("status", "--porcelain", str(CAT.LISTA))[1].strip(),
          git("status", "--porcelain", str(CAT.LISTA))[1])

# EL CONTROL: si de verdad cambia la lista, SI se escribe. Sin esto, «no
# escribe nunca» pasaria esta prueba y romperia la publicacion de normas.
d = json.loads(antes.decode("utf-8"))
d["normas"] = d["normas"][:-1]
CAT.LISTA.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
try:
    CAT.regenerar()
    ahora = json.loads(CAT.LISTA.read_text(encoding="utf-8"))
    comprobar("pero si falta una norma en la lista, SI se vuelve a escribir",
              len(ahora["normas"]) == len(json.loads(antes.decode())["normas"]),
              len(ahora["normas"]))
finally:
    CAT.LISTA.write_bytes(antes)


# ==================================== 4. LAS REGLAS DE LOS .bat
print("\n=== 4. LOS .bat CUMPLEN LAS REGLAS QUE ESTE PROYECTO SE ESCRIBIO ===")
print("  No se pueden ejecutar desde aqui, y eso no es motivo para no mirarlos:")
print("  las reglas estan escritas en sus propias cabeceras.\n")

import re                                            # noqa: E402
for f in sorted(RAIZ.glob("*.bat")):
    texto = f.read_text(encoding="utf-8", errors="replace")
    malos_parentesis, no_ascii, pythonw = [], [], []
    for n, l in enumerate(texto.splitlines(), 1):
        s = l.strip()
        if s.upper().startswith("REM"):
            continue
        if s.lower().startswith("echo"):
            # Escapados con ^ son correctos; sin escapar cierran el bloque.
            limpio = re.sub(r"\^[()]", "", s)
            if "(" in limpio or ")" in limpio:
                malos_parentesis.append(n)
            if any(ord(c) > 127 for c in s):
                no_ascii.append(n)
        if "pythonw" in s.lower():
            pythonw.append(n)
    comprobar(f"{f.name}: ningun parentesis sin escapar en un echo",
              not malos_parentesis, malos_parentesis)
    comprobar(f"  {f.name}: ninguna tilde en un echo", not no_ascii, no_ascii)
    comprobar(f"  {f.name}: acaba en un pause, nunca en blanco",
              "pause" in texto)
    # `abrir_agente.bat` USA pythonw A PROPOSITO: es el unico que quiere
    # esconder la consola. Los demas tienen que enseñarla, que es lo que se lee.
    if f.name != "abrir_agente.bat":
        comprobar(f"  {f.name}: usa python.exe y no pythonw, que no tiene "
                  f"consola", not pythonw, pythonw)

comprobar("existe el gemelo de reparar para Windows",
          (RAIZ / "reparar.bat").is_file() and (RAIZ / "reparar.command").is_file())
comprobar("y `actualizar` deja de ser un callejon: manda a reparar",
          "reparar.bat" in (RAIZ / "actualizar.bat").read_text("utf-8")
          and "reparar.command" in (RAIZ / "actualizar.command").read_text("utf-8"))


# ==================================== 5. UNA COPIA ROTA, DE PUNTA A PUNTA
print("\n=== 5. UNA COPIA ROTA DE VERDAD SE REPARA Y SE ACTUALIZA ===")
print("  Se monta con los cuatro destrozos que hemos visto: el choque de una")
print("  consulta bajada por demanda, los dos derivados cambiados y el arbol a")
print("  medias que deja un checkout abortado por rutas largas.\n")

atras = git("rev-list", "--max-count=8", "HEAD")[1].split()
base = atras[-1] if atras else ""
clon = Path(tempfile.mkdtemp(prefix="copia_rota_")) / "oficina"
try:
    cod, salida = git("clone", "--quiet", str(RAIZ), str(clon))
    if cod != 0 or not base:
        comprobar("se puede montar una copia para probar", False, salida[:120])
    else:
        git("checkout", "--quiet", "-B", "main", base, cwd=clon)
        # el choque: una consulta que el pull va a traer, ya aqui sin seguir
        entrantes = [x for x in git("diff", "--name-only", f"{base}..HEAD")[1].split()
                     if x.startswith("datos/dgt/consultas/")]
        choque = entrantes[0] if entrantes else ""
        if choque:
            (clon / choque).parent.mkdir(parents=True, exist_ok=True)
            (clon / choque).write_text('{"de":"demanda"}', encoding="utf-8")
        # los derivados cambiados
        for rel in ("datos/dgt/indice.json", "normas_del_corpus.json"):
            f = clon / rel
            if f.is_file():
                f.write_text(f.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        # el arbol a medias
        faltan = [x for x in ("interfaz.py", "agente_fiscal/redactor.py")
                  if (clon / x).is_file()]
        for x in faltan:
            (clon / x).unlink()
        shutil.copy2(RAIZ / "reparar.py", clon / "reparar.py")

        r = subprocess.run([PY_EXE, "reparar.py", "--revisar"], cwd=str(clon),
                           capture_output=True, text=True)
        comprobar("el diagnostico ve el arbol incompleto",
                  "ARBOL INCOMPLETO" in r.stdout, r.stdout[-200:])
        comprobar("  ve los derivados que se pueden descartar",
                  "derivados cambiados" in r.stdout)
        comprobar("  ve el choque con el pull",
                  (not choque) or "CHOQUES CON EL PULL" in r.stdout)
        comprobar("  y no toca nada al revisar",
                  not (clon / "interfaz.py").is_file() if faltan else True)

        r = subprocess.run([PY_EXE, "reparar.py"], cwd=str(clon),
                           capture_output=True, text=True)
        comprobar("la reparacion termina bien", r.returncode == 0,
                  r.stdout[-300:])
        comprobar("  el arbol queda completo",
                  not git("ls-files", "-d", cwd=clon)[1].strip(),
                  git("ls-files", "-d", cwd=clon)[1][:120])
        sucio = [l for l in git("status", "--porcelain", cwd=clon)[1].splitlines()
                 if "reparar.py" not in l]
        comprobar("  y sin cambios pendientes", not sucio, sucio[:3])
        comprobar("  y al dia con el origen",
                  git("rev-list", "--count", "HEAD..origin/main",
                      cwd=clon)[1].strip() == "0")
        # LO QUE NO SE PUEDE HABER PERDIDO. Borrar la consulta que choca seria
        # mas facil y tiraria una descarga que costo una peticion.
        if choque:
            comprobar("  la descarga por demanda NO se perdio: esta en demanda/",
                      (clon / "datos" / "dgt" / "demanda"
                       / Path(choque).name).is_file())
            comprobar("  y la del pull ocupa su sitio",
                      (clon / choque).is_file()
                      and "demanda" not in (clon / choque).read_text("utf-8"))
finally:
    shutil.rmtree(clon.parent, ignore_errors=True)


# ==================================== CONTROL NEGATIVO
print("\n=== CONTROL NEGATIVO: la suite tiene que ponerse roja ===")
print("  Ninguna prueba se da por buena sin verla fallar cuando debe fallar.\n")

# (a) UN CAMBIO QUE NO ES NUESTRO NO SE DESCARTA. Es la mitad que impide que
# `reparar` se convierta en «tira todo lo que estorbe».
clon2 = Path(tempfile.mkdtemp(prefix="copia_ajena_")) / "oficina"
try:
    git("clone", "--quiet", str(RAIZ), str(clon2))
    (clon2 / "interfaz.py").write_text("# alguien estaba trabajando aqui\n",
                                       encoding="utf-8")
    shutil.copy2(RAIZ / "reparar.py", clon2 / "reparar.py")
    r = subprocess.run([PY_EXE, "reparar.py"], cwd=str(clon2),
                       capture_output=True, text=True)
    comprobar("un cambio local que no es un derivado PARA la reparacion",
              r.returncode == 1 and "no reconozco" in r.stdout, r.stdout[-200:])
    comprobar("  y no lo descarta",
              (clon2 / "interfaz.py").read_text("utf-8").startswith("# alguien"))
finally:
    shutil.rmtree(clon2.parent, ignore_errors=True)

# (b) EL LINT DE LOS .bat TIENE QUE CAZAR LO QUE BUSCA.
malo = "echo   Novedades: 3 cambio(s)"
comprobar("el lint caza un parentesis sin escapar",
          "(" in re.sub(r"\^[()]", "", malo))
comprobar("  y deja pasar el escapado",
          "(" not in re.sub(r"\^[()]", "", "echo   3 cambio^(s^)"))


print("\n" + "=" * 74)
if fallos:
    print(f"{len(fallos)} FALLO(S):")
    for f in fallos:
        print(f"   - {f}")
    sys.exit(1)
print("TODO EN VERDE · la copia de la oficina se puede actualizar")
sys.exit(0)
