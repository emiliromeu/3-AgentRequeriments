"""Traza de cada consulta. Si alguien discute una respuesta dentro de seis
meses, tiene que poder reconstruirse entera.

Se guarda todo y en el orden en que ocurrio: la pregunta, la respuesta CRUDA
del analizador (antes de parsearla), el JSON ya validado, que preceptos se
recuperaron y con que version, cada borrador, cada veredicto del verificador,
y el estado final con el porque.

Misma regla que en la fase 1: lo crudo se escribe ANTES de interpretarlo. Si
el parseo revienta, el material sigue en disco.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class Traza:
    """El expediente de una consulta.

    NO PUEDE TIRAR LA CONSULTA. Antes, cualquier fallo de disco -el disco
    lleno, el directorio sin permiso, la carpeta borrada a mitad- salia de aqui
    como un `OSError` sin coger, y eso acababa en una traza de Python en la
    terminal. Medido: reventaba en los tres momentos, al abrir, a mitad y al
    cerrar. Y en la ventana salia el mensaje generico, «vuelve a intentarlo»,
    que con el disco lleno es un consejo inutil: va a fallar igual.

    Pero TAMPOCO PUEDE FALLAR EN SILENCIO. Una respuesta sin expediente no se
    puede reconstruir dentro de seis meses, y quien la enseñe tiene derecho a
    saberlo. Asi que se apunta -`self.roto`- y quien llama lo enseña.

    Se guarda el PRIMER fallo, no el ultimo: con el disco lleno vienen doce
    seguidos y el que explica lo que paso es el primero.
    """

    def __init__(self, raiz: Path, pregunta: str, sello: str | None = None):
        self.sello = sello or datetime.now().strftime("%Y%m%dT%H%M%S")
        self.dir = raiz / self.sello
        # Por que no se ha podido guardar el expediente. Vacio = todo bien.
        self.roto: str = ""
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.roto = f"no se ha podido crear {self.dir}: {e}"
        self.pasos: list[dict] = []
        # Una linea por llamada al modelo: que paso, que modelo y que tokens.
        # Va aparte de los pasos porque se suma, y porque el expediente tiene
        # que poder decir lo que costo esta consulta sin interpretar nada.
        self.consumo: list[dict] = []
        # El corte de material: que se mando a redactar y que se dejo fuera.
        # Si un dia una respuesta falla por falta de material, tiene que verse
        # aqui, en el expediente, y no deducirse.
        self.seleccion: dict | None = None
        self.escribir("pregunta.txt", pregunta)

    # --------------------------------------------------------------- basico

    def escribir(self, nombre: str, contenido: str) -> Path | None:
        """Escribe un fichero del expediente. `None` si no se ha podido."""
        ruta = self.dir / nombre
        try:
            ruta.write_text(contenido, encoding="utf-8")
        except OSError as e:
            if not self.roto:
                self.roto = f"no se ha podido escribir {nombre}: {e}"
            return None
        return ruta

    def json(self, nombre: str, datos) -> Path | None:
        return self.escribir(nombre, json.dumps(datos, ensure_ascii=False, indent=2))

    def paso(self, nombre: str, detalle: str = "", **extra) -> None:
        """Anota un hito con su hora. El orden es el del expediente."""
        self.pasos.append(
            {
                "hora": datetime.now().strftime("%H:%M:%S"),
                "paso": nombre,
                "detalle": detalle,
                **extra,
            }
        )

    # ------------------------------------------------------------- consumo

    def gasto(self, paso: str, respuesta) -> None:
        """Anota lo que ha costado UNA llamada, tal como lo dice la API.

        Se guarda el detalle por llamada, no solo el total: si un dia la cache
        deja de leerse, hay que poder ver en que llamada dejo de leerse.
        """
        from . import modelo as MOD

        uso = MOD.normalizar_uso(getattr(respuesta, "uso", None) or {})
        uso["cache"] = (
            "lectura" if uso["cache_lectura"]
            else ("escritura" if uso["cache_escritura"] else "no")
        )
        self.consumo.append(
            {"paso": paso, "modelo": getattr(respuesta, "modelo", "?"), **uso}
        )

    def corte(self, seleccion: dict) -> None:
        """Guarda el corte de material para que salga en el expediente."""
        self.seleccion = seleccion

    def totales(self) -> dict:
        t = {"llamadas": len(self.consumo), "entrada": 0, "salida": 0,
             "cache_lectura": 0, "cache_escritura": 0}
        for c in self.consumo:
            for k in ("entrada", "salida", "cache_lectura", "cache_escritura"):
                t[k] += c[k]
        t["entrada_total_procesada"] = (
            t["entrada"] + t["cache_lectura"] + t["cache_escritura"]
        )
        return t

    # ------------------------------------------------------------- cierre

    def cerrar(self, resultado: dict) -> Path:
        self.json("resultado.json", resultado)
        self.json("pasos.json", self.pasos)

        t = self.totales()
        if self.consumo:
            self.json("consumo.json", {"llamadas": self.consumo, "totales": t})

        lineas = [
            f"# Consulta {self.sello}",
            "",
            f"- estado final: **{resultado.get('estado')}**",
            f"- ejercicio: {resultado.get('ejercicio')}",
            f"- motor: {resultado.get('motor')} / modelo {resultado.get('modelo')}",
            f"- intentos de redaccion: {resultado.get('intentos')}",
            f"- veredicto del verificador: {resultado.get('veredicto')}",
            "",
        ]
        if self.seleccion:
            s = self.seleccion
            lineas += [
                "## Material enviado a redactar",
                "",
                f"Corte por pertinencia: un precepto entra si cubre al menos el "
                f"{s['umbral']:.0%} de lo que cubre el primero. "
                f"Entraron {s['enviados']} de {s['candidatos']}.",
                "",
                "| puesto | precepto | cobertura | % del 1º | decision | motivo |",
                "|---:|---|---:|---:|---|---|",
            ]
            for p in s["preceptos"]:
                lineas.append(
                    f"| {p['puesto']} | {p['referencia']} | {p['cobertura']:.2f} | "
                    f"{p['relativa']:.0%} | **{p['decision']}** | {p['motivo']} |"
                )
            fuera = [p for p in s["preceptos"] if p["decision"] == "descartado"]
            if fuera:
                lineas += [
                    "",
                    "Si a esta respuesta le falto material, empieza por aqui: "
                    + ", ".join(f"{p['referencia']} ({p['relativa']:.0%})"
                                for p in fuera),
                ]
            lineas.append("")

        if self.consumo:
            lineas += [
                "## Consumo",
                "",
                "| paso | modelo | entrada | salida | cache leida | cache escrita |",
                "|---|---|---:|---:|---:|---:|",
            ]
            for c in self.consumo:
                lineas.append(
                    f"| {c['paso']} | {c['modelo']} | {c['entrada']} | "
                    f"{c['salida']} | {c['cache_lectura']} | {c['cache_escritura']} |"
                )
            lineas += [
                f"| **TOTAL ({t['llamadas']} llamadas)** | | **{t['entrada']}** | "
                f"**{t['salida']}** | **{t['cache_lectura']}** | "
                f"**{t['cache_escritura']}** |",
                "",
                f"Entrada procesada en total (pagada entera + cache): "
                f"{t['entrada_total_procesada']} tokens.",
                "",
            ]
        lineas += [
            "## Pasos",
        ]
        for p in self.pasos:
            lineas.append(f"- {p['hora']}  {p['paso']}"
                          + (f" — {p['detalle']}" if p["detalle"] else ""))
        lineas += ["", "## Ficheros", ""]
        try:
            for f in sorted(self.dir.iterdir()):
                lineas.append(f"- `{f.name}` ({f.stat().st_size} bytes)")
        except OSError as e:
            if not self.roto:
                self.roto = f"no se ha podido listar {self.dir}: {e}"
            lineas.append("- (no se ha podido listar el directorio)")
        self.escribir("expediente.md", "\n".join(lineas) + "\n")
        return self.dir
