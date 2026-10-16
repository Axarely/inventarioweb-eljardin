// Gráficos del panel de indicadores (DEDS Fig. 14) con Chart.js. Paleta de El Jardín (D-30).
(function () {
  const nodo = document.getElementById("datos-graficos");
  if (!nodo || typeof Chart === "undefined") return;
  const datos = JSON.parse(nodo.textContent);
  const colores = ["#1F3D2B", "#C77A4A", "#4E8A3E", "#8A4F2A", "#9DBF8E", "#8B95A1"];

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
