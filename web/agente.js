"use strict";
/* EL AGENTE EN EL NAVEGADOR. Sin librerias: es la misma regla que en Python,
 * una sola dependencia, y aqui ni siquiera esa.
 *
 * ESTA PAGINA NO DECIDE NADA. Pide al servidor y enseña lo que devuelve, igual
 * que la ventana llamaba a `fase4.consultar`. No interpreta, no reordena, no
 * suaviza. Si `respuesta` viene vacia, no hay nada que enseñar.
 */

const T = new URLSearchParams(location.search).get("t") || "";
const YO = Math.random().toString(36).slice(2);

function api(camino, opciones) {
  const sep = camino.includes("?") ? "&" : "?";
  return fetch(`${camino}${sep}t=${encodeURIComponent(T)}`, opciones)
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.status))));
}

/* ── EL LATIDO Y EL ADIOS ────────────────────────────────────────────────
 * Dos señales, y el adios es el que de verdad cierra. Ver la nota larga en
 * servidor.py: la ausencia de noticias no es una noticia.
 */
let intervaloLatido = null;
function latir() {
  fetch(`/api/latido?t=${encodeURIComponent(T)}&quien=${encodeURIComponent(YO)}`,
        {method: "POST"}).catch(() => {});
}
function empezarLatido(ms) {
  if (intervaloLatido) clearInterval(intervaloLatido);
  intervaloLatido = setInterval(latir, ms);
}
latir();
empezarLatido(5000);
addEventListener("pagehide", () => {
  navigator.sendBeacon(
    `/api/adios?t=${encodeURIComponent(T)}&quien=${encodeURIComponent(YO)}`);
});
addEventListener("visibilitychange", () => {
  // Al volver de segundo plano, latir enseguida: el navegador pudo haber
  // estrangulado el intervalo mientras la pestaña estaba oculta.
  if (document.visibilityState === "visible") latir();
});

/* ══════════════════════════════════════════════════════════════════════
 * LOS SEIS PASOS: POR CLAVE, NUNCA POR TEXTO
 * ══════════════════════════════════════════════════════════════════════
 *
 * La lista de pasos NO se escribe aqui: se pide a `/api/pasos`, que la saca de
 * `fase4.PASOS`. Y lo que llega durante la consulta es la CLAVE, no la frase.
 *
 * SI SE EMPAREJARA POR TEXTO, reescribir «Analizando la pregunta...» en fase4
 * dejaria la lista clavada en el primer paso SIN QUE NADA FALLARA. Es el mismo
 * razonamiento que ya esta escrito en fase4 y en la ventana; en la pagina hace
 * falta repetirlo porque es una tercera copia del mismo emparejamiento.
 */
let PASOS = [];
let SOLO_CON_CRITERIO = "criterio";

function pintarPasos(caja, conCriterio) {
  const ul = document.createElement("ul");
  ul.className = "pasos";
  PASOS.forEach((p) => {
    // El paso del criterio SOLO si se va a hacer: un paso en gris que no va a
    // ocurrir es una promesa que no se cumple, y quien espera cuenta.
    if (p.clave === SOLO_CON_CRITERIO && !conCriterio) return;
    const li = document.createElement("li");
    li.dataset.clave = p.clave;
    li.dataset.estado = "pendiente";
    li.innerHTML = `<span class="marca">·</span><span></span>`;
    li.lastElementChild.textContent = p.rotulo;
    ul.appendChild(li);
  });
  caja.appendChild(ul);
  return ul;
}

function marcarPaso(ul, clave, detalle) {
  const filas = [...ul.querySelectorAll("li")];
  const cual = filas.findIndex((li) => li.dataset.clave === clave);
  if (cual < 0) {
    // UNA CLAVE QUE ESTA PAGINA NO CONOCE SE VE. No se queda quieta.
    //
    // Si el motor crece y esta lista no se entera, callarse dejaria la espera
    // muerta en silencio — que es exactamente lo que se decidio evitar
    // mandando claves en vez de frases. Enseñarlo es feo y es correcto: dice
    // que la herramienta esta haciendo algo que la pantalla no sabe nombrar.
    let raro = ul.parentElement.querySelector(".paso-raro");
    if (!raro) {
      raro = document.createElement("p");
      raro.className = "paso-raro";
      ul.parentElement.appendChild(raro);
    }
    raro.textContent =
      `El agente está en un paso que esta pantalla no conoce («${clave}»). ` +
      `La consulta sigue: lo que falta es que esta lista se actualice. ` +
      `Avisa a Emili.`;
    return;
  }
  // SE CIERRAN TODOS LOS ANTERIORES, no solo el de antes: un paso puede
  // saltarse, y dejarlo a medias diria que algo se quedo colgado.
  filas.forEach((li, i) => {
    li.dataset.estado = i < cual ? "hecho" : (i === cual ? "haciendo" : "pendiente");
    li.firstElementChild.textContent =
      i < cual ? "✓" : (i === cual ? "●" : "·");
  });
  if (detalle) {
    const p = ul.parentElement.querySelector(".detalle");
    if (p) p.textContent = detalle;
  }
}

/* ══════════════════════════════════════════════════════════════════════
 * EL MENU DE ENTRADA
 * ══════════════════════════════════════════════════════════════════════ */
function pintarMenu(m) {
  const centro = document.querySelector("#entrada");
  if (m.cargando) {
    centro.innerHTML =
      `<h1>Consulta fiscal</h1><p class="bajada">Cargando la ley…</p>`;
    setTimeout(() => api("/api/menu").then(pintarMenu).catch(() => {}), 700);
    return;
  }
  const tope = Math.max(...m.cobertura.map((c) => c.porcentaje), 1);
  centro.innerHTML = `
    <h1>Contesta dudas fiscales con el texto oficial delante</h1>
    <p class="bajada">Cada respuesta se redacta con los artículos encontrados
    y <strong>cada cita se comprueba una a una</strong> contra el texto del BOE.
    Si no hay respaldo, lo dice: no se enseña nada sin comprobar.</p>
    <div class="bloques">
      <div class="bloque">
        <h2>Cómo trabaja</h2>
        <div class="flujo">${PASOS.map((p) =>
          `<span>${p.rotulo.replace(/^(\w+)/, (x) => x.toLowerCase())}</span>`
        ).join("")}</div>
        <p style="margin-top:12px">Suele tardar cerca de dos minutos.</p>
      </div>
      <div class="bloque">
        <h2>De qué está alimentado</h2>
        <div class="barras"></div>
        <p style="margin-top:12px">${m.articulos.toLocaleString("es")} artículos
        de ${m.normas} normas. La barra es la <strong>proporción de artículos
        con criterio guardado</strong>, no cuántos documentos hay.</p>
      </div>
    </div>
    <div class="limite">
      <b>Lo que no cubre — léelo una vez</b>
      No incluye sentencias de los tribunales de justicia. La copia de criterio
      es <strong>nuestra y parcial</strong>: que no encuentre algo no quiere
      decir que no exista. Y el criterio puede cambiar: comprueba las citas
      antes de decidir.
    </div>`;
  const barras = centro.querySelector(".barras");
  m.cobertura.forEach((c) => {
    const d = document.createElement("div");
    d.className = "barra";
    d.innerHTML = `<span class="n"></span><span class="v"><i></i></span>` +
                  `<span class="c">${c.porcentaje}%</span>`;
    d.firstElementChild.textContent = c.nombre;
    d.title = `${c.con_criterio} de ${c.articulos} artículos tienen criterio guardado`;
    barras.appendChild(d);
    // Crece desde cero. Es la unica animacion del menu, y dice algo cierto:
    // la longitud es la proporcion, no el volumen. Ver la nota en
    // `cobertura.cubierto_por_impuesto`.
    requestAnimationFrame(() =>
      setTimeout(() => {
        d.querySelector("i").style.width = (100 * c.porcentaje / tope) + "%";
      }, 120));
  });
}

/* ══════════════════════════════════════════════════════════════════════
 * LA BARRA LATERAL
 * ══════════════════════════════════════════════════════════════════════ */
function pintarChats(d, filtro) {
  const caja = document.querySelector("#chats");
  caja.innerHTML = "";
  const aguja = (filtro || "").trim().toLowerCase();
  let hubo = false;
  d.dias.forEach((dia) => {
    const suyos = dia.chats.filter((c) =>
      !aguja || c.titulo.toLowerCase().includes(aguja));
    if (!suyos.length) return;
    hubo = true;
    const t = document.createElement("div");
    t.className = "dia";
    t.textContent = dia.dia;
    caja.appendChild(t);
    suyos.forEach((c) => {
      const b = document.createElement("button");
      b.className = "chat";
      b.dataset.sello = c.sello;
      const meta = [c.vueltas > 1 ? `${c.vueltas} vueltas` : null,
                    c.ejercicio, c.comunidad].filter(Boolean).join(" · ");
      b.innerHTML = `<span class="q"></span><span class="meta"></span>`;
      b.firstElementChild.textContent = c.titulo;
      b.lastElementChild.textContent = meta;
      caja.appendChild(b);
    });
  });
  if (!hubo) {
    const p = document.createElement("div");
    p.className = "dia";
    p.textContent = aguja ? "Ninguna coincide" : "Todavía no hay consultas";
    caja.appendChild(p);
  }
}

/* ══════════════════════════════════════════════════════════════════════
 * ARRANQUE
 * ══════════════════════════════════════════════════════════════════════ */
api("/api/pasos").then((d) => {
  PASOS = d.pasos;
  SOLO_CON_CRITERIO = d.solo_con_criterio;
  return api("/api/menu");
}).then(pintarMenu).catch(() => {
  document.querySelector("#entrada").innerHTML =
    `<h1>Consulta fiscal</h1><p class="bajada">No se ha podido hablar con el
     agente. Cierra esta pestaña y vuelve a abrirlo. Si sigue igual, avisa a
     Emili.</p>`;
});

api("/api/chats").then((d) => {
  pintarChats(d, "");
  const buscar = document.querySelector("#buscar");
  buscar.addEventListener("input", () => pintarChats(d, buscar.value));
}).catch(() => {});
