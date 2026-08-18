#!/usr/bin/env python3
"""REPITE SOLO LA SEGUNDA REDACCION, con el primer intento leido del disco.

    .venv/bin/python reensayar_reintento.py                 <- ensayo, NO GASTA
    .venv/bin/python reensayar_reintento.py --con-modelo    <- gasta de verdad

POR QUE ASI Y NO REPITIENDO LA CONSULTA ENTERA. Lo que ha cambiado es el
MENSAJE DE REINTENTO. Repetir la consulta entera volveria a analizar y a buscar,
y entonces el primer borrador seria otro, el rechazo seria otro y no se sabria
que parte de la diferencia es del cambio. Aqui el primer intento es EL MISMO,
byte a byte: sale del expediente. Lo unico distinto es lo que se le dice para
que lo corrija.

Y cuesta una llamada por consulta en vez de tres.

QUE NECESITA CADA TRAZA para poder reensayarse: `recuperado.json` -para
rehacer el material-, `verificacion_1.json` -para los motivos exactos- y el
ejercicio. Si le falta algo, NO se reensaya y se dice: una traza a medias
contada como reensayada falsearia la comparacion.

NO IMPRIME NINGUNA PREGUNTA: son dudas de clientes.
"""
import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import fase4                                     # noqa: E402
from agente_fiscal import modelo as MOD          # noqa: E402
from agente_fiscal import redactor as RED        # noqa: E402
from agente_fiscal import verificador as VF      # noqa: E402

TRAZAS = RAIZ / "datos" / "trazas"
SALIDA = RAIZ / "datos" / "reensayo_reintento.json"
ANCHO = 78


def candidatas() -> list[dict]:
    """Las que fueron rechazadas en el primer intento y se pueden reensayar."""
    fuera = []
    salida = []
    for d in sorted(TRAZAS.iterdir()) if TRAZAS.is_dir() else []:
        if not (d / "verificacion_1.json").is_file():
            continue
        try:
            con = json.loads((d / "consumo.json").read_text("utf-8"))
        except (OSError, ValueError):
            continue
        if not any("claude" in str(x.get("modelo", ""))
                   for x in con.get("llamadas") or []):
            continue
        try:
            v1 = json.loads((d / "verificacion_1.json").read_text("utf-8"))
        except (OSError, ValueError):
            continue
        if v1.get("veredicto") == "ACEPTADO":
            continue
        falta = [f for f in ("recuperado.json", "resultado.json",
                             "pregunta.txt")
                 if not (d / f).is_file()]
        if falta:
            fuera.append((d.name, f"le falta {', '.join(falta)}"))
            continue
        salida.append({"dir": d, "v1": v1})
    for nombre, por in fuera:
        print(f"  FUERA {nombre}: {por}")
    return salida


def motivos_de(v1: dict) -> list[str]:
    """Los mismos motivos que se le dieron aquel dia, reconstruidos igual.

    Se leen del informe guardado y NO se recalculan: recalcularlos con el
    verificador de hoy meteria en la comparacion cualquier cambio del
    verificador desde entonces.
    """
    ms = [f"cita {i} ({c.get('referencia') or 'sin referencia'}): "
          f"{c.get('motivo')}"
          for i, c in enumerate(v1.get("citas") or [], start=1)
          if c.get("estado") != "VERIFICADA"]
    return ms or [str(v1.get("motivo_global") or "")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--con-modelo", action="store_true",
                    help="usa el modelo real. GASTA DINERO.")
    args = ap.parse_args()

    print("=" * ANCHO)
    print("REENSAYO DEL SEGUNDO INTENTO")
    print("=" * ANCHO)
    casos = candidatas()
    print(f"  consultas rechazadas en el primer intento y reensayables: "
          f"{len(casos)}")
    if not casos:
        return 1

    motor, err = fase4.preparar_motor(
        "anthropic" if args.con_modelo else "ensayo", silencioso=True)
    if motor is None:
        print(f"  No se ha podido preparar el motor: {err}")
        return 1
    if not args.con_modelo:
        print("  MOTOR DE ENSAYO: no mide nada. Sirve para ver que el guion")
        print("  hace lo que dice antes de pagarlo.")

    ix, grafo = fase4.cargar_corpus()
    verificador = VF.Verificador(ix)
    resultados = []

    for c in casos:
        d = c["dir"]
        rec = json.loads((d / "recuperado.json").read_text("utf-8"))
        regs = [ix.por_clave[r["clave"]].registro for r in rec
                if r.get("clave") in ix.por_clave]
        if not regs:
            print(f"  FUERA {d.name}: sus preceptos ya no estan en el corpus")
            continue
        res = json.loads((d / "resultado.json").read_text("utf-8"))
        ejercicio = res.get("ejercicio")
        pregunta = (d / "pregunta.txt").read_text("utf-8").strip()
        motivos = motivos_de(c["v1"])

        material = RED.construir_material(pregunta, ejercicio, regs, grafo,
                                          motivos, normas=ix.normas)
        motor.empezar_consulta()
        try:
            resp = motor.redactar(RED.SISTEMA, material)
        except MOD.ErrorModelo as e:
            print(f"  FUERA {d.name}: fallo del modelo: {e}")
            continue
        informe = verificador.verificar_texto((resp.texto or "").strip(),
                                              ejercicio, exigir_norma=True)
        resultados.append({
            "traza": d.name,
            "antes": c["v1"].get("veredicto"),
            "motivos_del_primero": motivos,
            "ahora": informe.veredicto,
            "informe": informe.a_json(),
            "salida": int((resp.crudo or {}).get("usage", {})
                          .get("output_tokens", 0) or 0),
        })
        print(f"  {d.name}: 1º RECHAZADO -> reensayo {informe.veredicto}")

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(resultados, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(f"\n  escrito en {SALIDA}")
    t = motor.totales()
    d_ = MOD.dolares(t)
    print(f"  gasto: ${d_:.3f} · {d_*0.92:.3f} EUR ({t['llamadas']} llamadas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
