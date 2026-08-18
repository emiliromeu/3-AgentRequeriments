#!/usr/bin/env python3
"""¿CUANTO CUESTA HOY UN «NO ENCONTRADO», Y CUANTO COSTARIA ORIENTAR?
Cero red, cero API. Se lee de las trazas que ya estan en disco.

    .venv/bin/python medir_no_encontrado.py

LA PREGUNTA QUE DECIDE. Se quiere que el NO ENCONTRADO deje de ser un callejon:
que diga que SI se ha encontrado y por que no basta, que oriente sobre donde
vive la respuesta y que pida el dato que falta. Eso lo escribe el redactor, asi
que antes de tocar el prompt hay que saber una cosa:

    ¿HOY SE LLAMA AL REDACTOR EN ESE CAMINO, O SE CORTA ANTES?

Si ya se llama, es cambiar el prompt y cuesta cero. Si se corta antes, cuesta
UNA LLAMADA MAS por consulta sin material, y eso se decide, no se cuela.

Y RESULTA QUE NO HAY UN «NO ENCONTRADO»: HAY DOS, y cuestan cosas distintas.
Por eso este guion los separa y NO da una media de los dos juntos. Una media
sobre dos poblaciones distintas es exactamente el numero que ya nos hizo tomar
dos decisiones malas.

    · PERTINENCIA INSUFICIENTE — se busco, salieron preceptos, y el mejor no
      cubre bastante de lo que se pregunta. Se corta ANTES de redactar.
      Es el caso del que habla el encargo: «tira los articulos recuperados».

    · EL VERIFICADOR RECHAZO — el redactor escribio, alguna cita no quedo
      VERIFICADA, se reintento y volvio a fallar. Aqui la redaccion YA SE PAGO,
      dos veces.

    · Y un tercero que casi no aparece: la PUERTA DE MATERIA, que corta antes
      de buscar. Ahi no hay preceptos que enseñar, asi que no hay nada que
      orientar con citas.

SOLO CUENTAN LAS TRAZAS DEL MODELO DE VERDAD. Las de ensayo no cuestan nada y
meterlas bajaria la media a base de ceros.

NO IMPRIME NINGUNA PREGUNTA. Son dudas reales: se cuentan, no se citan.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from agente_fiscal import modelo as MOD          # noqa: E402
from agente_fiscal import version as VER         # noqa: E402

TRAZAS = RAIZ / "datos" / "trazas"
ANCHO = 78
EUROS_POR_DOLAR = 0.92

# El paso que delata cada camino, leido de `pasos.json`. No se adivina por el
# numero de llamadas: dos llamadas pueden ser muchas cosas.
CAMINOS = {
    "pertinencia insuficiente": "corta ANTES de redactar",
    "el verificador rechazo": "la redaccion YA se pago",
    "puerta de materia": "corta antes de buscar",
    "(otro)": "",
}


def leer(d: Path):
    """Una traza, o None si no se puede leer. SIN RESPALDOS: una traza que no
    se lee se cuenta como no leida, no como una de cero tokens."""
    try:
        res = json.loads((d / "resultado.json").read_text("utf-8"))
        con = json.loads((d / "consumo.json").read_text("utf-8"))
    except (OSError, ValueError):
        return None
    lineas = con.get("llamadas") or []
    if not any("claude" in str(x.get("modelo", "")) for x in lineas):
        return None                      # ensayo: no cuesta y no cuenta
    try:
        pasos = json.loads((d / "pasos.json").read_text("utf-8"))
    except (OSError, ValueError):
        pasos = []
    try:
        rec = json.loads((d / "recuperado.json").read_text("utf-8"))
    except (OSError, ValueError):
        rec = []
    return {"dir": d, "estado": res.get("estado", "?"), "lineas": lineas,
            "pasos": pasos, "recuperados": len(rec)}


def camino_de(t) -> str:
    detalles = {p.get("paso", ""): str(p.get("detalle", "")) for p in t["pasos"]}
    hay = {p.get("paso", "") for p in t["pasos"]}
    if any("RECHAZADO" in str(p.get("detalle", ""))
           for p in t["pasos"] if p.get("paso") == "verificacion"):
        return "el verificador rechazo"
    if "pertinencia" in hay and not any(
            "redacc" in x.get("paso", "") for x in t["lineas"]):
        return "pertinencia insuficiente"
    if "materia" in hay and "busqueda" not in hay:
        return "puerta de materia"
    _ = detalles
    return "(otro)"


def suma(lineas, filtro=None) -> dict:
    ks = ("entrada", "salida", "cache_lectura", "cache_escritura")
    t = dict.fromkeys(ks, 0)
    for x in lineas:
        if filtro and filtro not in x.get("paso", ""):
            continue
        for k in ks:
            t[k] += int(x.get(k, 0) or 0)
    return t


def media(dicts) -> dict:
    if not dicts:
        return {}
    ks = dicts[0].keys()
    return {k: sum(d[k] for d in dicts) / len(dicts) for k in ks}


def main() -> int:
    if not TRAZAS.is_dir():
        print("\n  No hay trazas en disco. Nada que medir.")
        return 1

    todas = [t for t in (leer(d) for d in sorted(TRAZAS.iterdir()) if d.is_dir())
             if t]
    print("=" * ANCHO)
    print("LO QUE HAY EN DISCO")
    print("=" * ANCHO)
    print(f"  consultas hechas con el modelo de verdad : {len(todas)}")
    if not todas:
        return 1
    # DE CUANTAS VERSIONES DEL CODIGO. Va antes que ninguna media: si la
    # muestra abarca varias, la media no describe ninguna de ellas.
    rep = VER.reparto([t["dir"] for t in todas])
    print(f"  y son de {len(rep)} version(es) del codigo:")
    for etiqueta, n in rep.items():
        cola = ("  <- expedientes viejos, no lo guardaban; aparte, que es mas "
                "honesto que suponer" if etiqueta == VER.DESCONOCIDA else "")
        print(f"     {n:>3}  {etiqueta}{cola}")

    por_estado = defaultdict(list)
    for t in todas:
        por_estado[t["estado"]].append(t)
    print(f"  {'estado':24s} {'n':>3}  {'llamadas':>8}  {'salida med':>10}")
    for est, filas in sorted(por_estado.items()):
        n = len(filas)
        print(f"  {est:24s} {n:>3}  "
              f"{sum(len(f['lineas']) for f in filas)/n:>8.2f}  "
              f"{sum(suma(f['lineas'])['salida'] for f in filas)/n:>10.0f}")

    sin = [t for t in todas if "NO ENCONTRADO" in t["estado"]]
    print()
    print("=" * ANCHO)
    print("NO HAY UN «NO ENCONTRADO»: HAY DOS, Y CUESTAN COSAS DISTINTAS")
    print("=" * ANCHO)
    print(f"  consultas sin respuesta: {len(sin)} de {len(todas)}")

    por_camino = defaultdict(list)
    for t in sin:
        por_camino[camino_de(t)].append(t)

    # POR LLAMADA, NO POR TRAZA. Una consulta que reintenta tiene DOS
    # redacciones; sumarlas y llamar a eso «una llamada» inflaba el precio un
    # 25% -de $0,175 a $0,218- y ese numero era justo el que decide si el
    # cambio se aplica o no.
    llamadas_red = [x for t in todas for x in t["lineas"]
                    if "redacc" in x.get("paso", "")]
    coste_redaccion = media([
        {k: int(x.get(k, 0) or 0) for k in
         ("entrada", "salida", "cache_lectura", "cache_escritura")}
        for x in llamadas_red])

    for camino, filas in sorted(por_camino.items()):
        n = len(filas)
        sal = sum(suma(f["lineas"])["salida"] for f in filas) / n
        lla = sum(len(f["lineas"]) for f in filas) / n
        rec = sum(f["recuperados"] for f in filas) / n
        d = MOD.dolares(media([suma(f["lineas"]) for f in filas]))
        print()
        print(f"  {camino.upper()}  ({CAMINOS.get(camino, '')})")
        print(f"     consultas                  : {n}")
        print(f"     llamadas al modelo         : {lla:.2f}")
        print(f"     tokens de salida           : {sal:.0f}")
        print(f"     preceptos recuperados      : {rec:.1f}  "
              f"<- los que HOY se tiran" if rec else "")
        print(f"     coste medio de una asi     : ${d:.3f}  ·  "
              f"{d*EUROS_POR_DOLAR:.3f} EUR")
        for f in filas:
            print(f"       {f['dir'].name}  {len(f['lineas'])} llamada(s), "
                  f"{suma(f['lineas'])['salida']} de salida, "
                  f"{f['recuperados']} preceptos")

    print()
    print("=" * ANCHO)
    print("LO QUE COSTARIA ORIENTAR")
    print("=" * ANCHO)
    if not coste_redaccion:
        print("\n  No hay ninguna llamada de redaccion medida. Sin ese numero")
        print("  no se puede decir lo que cuesta una mas, y no se estima.")
        return 0
    d_red = MOD.dolares(coste_redaccion)
    print(f"\n  UNA llamada de redaccion, media de las {len(llamadas_red)} "
          f"reales que hay en disco:")
    print(f"     entrada {coste_redaccion['entrada']:.0f} · "
          f"salida {coste_redaccion['salida']:.0f} · "
          f"cache {coste_redaccion['cache_lectura']:.0f}L/"
          f"{coste_redaccion['cache_escritura']:.0f}E")
    print(f"     ${d_red:.3f}  ·  {d_red*EUROS_POR_DOLAR:.3f} EUR")

    n_corta = len(por_camino.get("pertinencia insuficiente", []))
    n_paga = len(por_camino.get("el verificador rechazo", []))
    print()
    print(f"  DONDE SE CORTA ANTES ({n_corta} de {len(sin)} sin respuesta):")
    print(f"     orientar cuesta UNA LLAMADA MAS: "
          f"+${d_red:.3f} · +{d_red*EUROS_POR_DOLAR:.3f} EUR por consulta")
    print(f"  DONDE LA REDACCION YA SE PAGO ({n_paga} de {len(sin)}):")
    print(f"     ahi ya hay dos redacciones pagadas. Si la orientacion se")
    print(f"     escribe EN VEZ del segundo intento, cuesta CERO; si se añade")
    print(f"     encima, cuesta otra: +${d_red:.3f}.")
    print()
    print(f"  Y LA BASE, que hay que decir cada vez: {len(sin)} consultas sin")
    print(f"  respuesta de {len(todas)} reales. Es poca. El reparto entre los")
    print(f"  dos caminos puede cambiar con mas uso, y el coste de la decision")
    print(f"  cambia con el.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
