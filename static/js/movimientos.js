// Panel de existencia en bodega para los formularios de entrada y salida (DEDS Fig. 15 y 16).
// Mejora progresiva: el servidor valida siempre; esto solo informa antes de enviar.
(function () {
  const panel = document.getElementById("panel-bodega");
  const form = document.getElementById("form-movimiento");
  if (!panel || !form) return;

  const selProducto = form.querySelector("[name=producto]");
  const inpCantidad = form.querySelector("[name=cantidad]");
  const inpUnidad = document.getElementById("unidad");
  const validarMaximo = form.dataset.validarMaximo === "1";
  const elCantidad = document.getElementById("panel-cantidad");
  const elMinimo = document.getElementById("panel-minimo");
  const elPill = document.getElementById("panel-pill");
  const elMerma = document.getElementById("panel-merma");
  const elEquivalente = document.getElementById("panel-equivalente");
  const selMedida = form.querySelector("[name=medida]");
  const bloqueMedida = document.getElementById("bloque-medida");
  let factor = null; // D-37: unidades por caja o paquete del producto elegido

  function cantidadEnUnidades() {
    const n = leerCantidad(inpCantidad.value);
    return selMedida && selMedida.value === "presentacion" && factor ? n * factor : n;
  }

  function prepararMedida(d) {
    factor = d && d.unidades_por_presentacion ? Number(d.unidades_por_presentacion) : null;
    if (!selMedida) return;
    const opcion = selMedida.querySelector("option[value=presentacion]");
    if (factor) {
      opcion.textContent = d.presentacion.charAt(0).toUpperCase() + d.presentacion.slice(1) +
        " (" + factor + " " + d.unidad + " c/u)";
      if (bloqueMedida) bloqueMedida.hidden = false;
    } else {
      selMedida.value = "unidad";
      if (bloqueMedida) bloqueMedida.hidden = true;
    }
  }
  let disponible = null;

  // D-35: misma lectura que el servidor (config/ui.py): "1.5", "1,5", "1 1/2", "1 y media".
  function leerCantidad(texto) {
    let t = String(texto || "").trim().toLowerCase().replace(/,/g, ".").replace(/\s+/g, " ");
    t = t.replace("tres cuartos", "3/4").replace("media", "1/2").replace("medio", "1/2").replace("cuarto", "1/4");
    t = t.replace(/ y /g, " ");
    if (!t) return NaN;
    const partes = t.split(" ");
    if (partes.length > 2) return NaN;
    let total = 0;
    for (const parte of partes) {
      if (parte.includes("/")) {
        const [n, d] = parte.split("/").map(Number);
        if (!d) return NaN;
        total += n / d;
      } else {
        if (!/^\d*\.?\d+$/.test(parte)) return NaN;
        total += Number(parte);
      }
    }
    return total;
  }

  function pill(nivel, texto) {
    const span = document.createElement("span");
    span.className = "pill pill-" + nivel;
    span.textContent = texto; // color + texto, nunca solo color (Fig. 21)
    return span;
  }

  function revisarCantidad() {
    if (!validarMaximo || disponible === null || !inpCantidad) return;
    const pedida = cantidadEnUnidades();
    elPill.replaceChildren(
      !isNaN(pedida) && pedida > disponible
        ? pill("agotado", "Insuficiente: máximo " + disponible)
        : pill("normal", "Suficiente para el envío")
    );
  }

  async function actualizar() {
    disponible = null;
    elPill.replaceChildren();
    if (elMerma) elMerma.hidden = true;
    if (elEquivalente) elEquivalente.textContent = "";
    if (!selProducto.value) {
      prepararMedida(null);
      elCantidad.textContent = "—";
      elMinimo.textContent = "Seleccione un producto.";
      if (inpUnidad) inpUnidad.value = "";
      return;
    }
    try {
      const resp = await fetch(panel.dataset.url + "?producto=" + encodeURIComponent(selProducto.value), {
        headers: { "Accept": "application/json" },
      });
      if (!resp.ok) throw new Error(resp.status);
      const d = await resp.json();
      disponible = parseFloat(d.cantidad);
      elCantidad.textContent = d.cantidad + " " + d.unidad;
      elMinimo.textContent = "Stock mínimo: " + d.stock_minimo + " " + d.unidad;
      if (elEquivalente) elEquivalente.textContent = d.equivalente ? "= " + d.equivalente : "";
      prepararMedida(d);
      if (inpUnidad) inpUnidad.value = d.unidad;
      if (validarMaximo) {
        if (inpCantidad) inpCantidad.max = d.cantidad;
        revisarCantidad();
      } else {
        elPill.replaceChildren(pill(d.nivel, "Stock " + d.nivel_texto));
        if (elMerma) elMerma.hidden = !d.controla_merma; // D-33
      }
    } catch (e) {
      elCantidad.textContent = "—";
      elMinimo.textContent = "No se pudo consultar la existencia.";
    }
  }

  selProducto.addEventListener("change", actualizar);
  if (inpCantidad) inpCantidad.addEventListener("input", revisarCantidad);
  if (selMedida) selMedida.addEventListener("change", revisarCantidad);
  const usarMaximo = document.getElementById("usar-maximo");
  if (usarMaximo) {
    usarMaximo.addEventListener("click", function () {
      inpCantidad.value = usarMaximo.dataset.cantidad;
      if (selMedida) selMedida.value = "unidad"; // el máximo sugerido está en unidades
      inpCantidad.focus();
      revisarCantidad();
    });
  }
  if (selProducto.value) actualizar();
})();
