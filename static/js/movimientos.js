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
  let disponible = null;

  function pill(nivel, texto) {
    const span = document.createElement("span");
    span.className = "pill pill-" + nivel;
    span.textContent = texto; // color + texto, nunca solo color (Fig. 21)
    return span;
  }

  function revisarCantidad() {
    if (!validarMaximo || disponible === null || !inpCantidad) return;
    const pedida = parseFloat(inpCantidad.value);
    elPill.replaceChildren(
      !isNaN(pedida) && pedida > disponible
        ? pill("agotado", "Insuficiente: máximo " + disponible)
        : pill("normal", "Suficiente para el envío")
    );
  }

  async function actualizar() {
    disponible = null;
    elPill.replaceChildren();
    if (!selProducto.value) {
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
      if (inpUnidad) inpUnidad.value = d.unidad;
      if (validarMaximo) {
        if (inpCantidad) inpCantidad.max = d.cantidad;
        revisarCantidad();
      } else {
        elPill.replaceChildren(pill(d.nivel, "Stock " + d.nivel_texto));
      }
    } catch (e) {
      elCantidad.textContent = "—";
      elMinimo.textContent = "No se pudo consultar la existencia.";
    }
  }

  selProducto.addEventListener("change", actualizar);
  if (inpCantidad) inpCantidad.addEventListener("input", revisarCantidad);
  const usarMaximo = document.getElementById("usar-maximo");
  if (usarMaximo) {
    usarMaximo.addEventListener("click", function () {
      inpCantidad.value = usarMaximo.dataset.cantidad;
      inpCantidad.focus();
      revisarCantidad();
    });
  }
  if (selProducto.value) actualizar();
})();
