// Gráficos del panel de indicadores (DEDS Fig. 14) con Chart.js. Colores de la guía de estilo (Fig. 21).
(function () {
  const nodo = document.getElementById("datos-graficos");
  if (!nodo || typeof Chart === "undefined") return;
  const datos = JSON.parse(nodo.textContent);
  const colores = ["#1F4E79", "#7FA8CB", "#3F8F5F", "#C08A2E", "#B5443E", "#8B95A1"];

  function dibujar(id, tipo, grafico, ejeY) {
    const lienzo = document.getElementById(id);
    if (!lienzo || !grafico) return;
    new Chart(lienzo, {
      type: tipo,
      data: {
        labels: grafico.etiquetas,
        datasets: grafico.series.map((serie, i) => ({
          label: serie.nombre,
          data: serie.datos,
          backgroundColor: colores[i % colores.length],
          borderColor: colores[i % colores.length],
          borderWidth: 2,
          tension: 0.2,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } },
        scales: { y: { beginAtZero: true, title: { display: !!ejeY, text: ejeY || "" } } },
      },
    });
  }

  dibujar("grafico-comparativo", "bar", datos.comparativo, "Cantidad consumida");
  if (datos.diaria) dibujar("grafico-diario", "line", datos.diaria, "Consumo (" + datos.diaria.unidad + ")");
})();
