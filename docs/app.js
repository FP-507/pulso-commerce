// Dashboard de Pulso Commerce: lee data.json (generado por pipeline/analisis.py) y dibuja.
const $ = (s) => document.querySelector(s);
const css = (v) => getComputedStyle($(".viz-root")).getPropertyValue(v).trim();
const usd = (n, d = 0) => "$" + n.toLocaleString("es-PA", { maximumFractionDigits: d, minimumFractionDigits: d });
const pct = (n, d = 0) => (n * 100).toFixed(d) + "%";
const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const mesCorto = (m) => `${MESES[+m.slice(5) - 1]} ${m.slice(2, 4)}`;

let DATA;
const charts = {};

function filtrar(anio, canal) {
  return DATA.mensual.filter(
    (r) => (anio === "todo" || r.mes.startsWith(anio)) && (canal === "todos" || r.canal === canal)
  );
}

function sumar(filas) {
  return filas.reduce(
    (a, r) => ({ ventas: a.ventas + r.ventas, margen: a.margen + r.margen, pedidos: a.pedidos + r.pedidos, nuevos: a.nuevos + r.nuevos }),
    { ventas: 0, margen: 0, pedidos: 0, nuevos: 0 }
  );
}

function kpis(anio, canal) {
  const act = sumar(filtrar(anio, canal));
  const prev = anio === "2025" ? sumar(filtrar("2024", canal)) : null;
  const delta = (a, b) => {
    if (!prev || !b) return '<span class="delta">Período completo</span>';
    const d = a / b - 1;
    const cls = d >= 0 ? "up" : "down";
    const flecha = d >= 0 ? "▲" : "▼";
    return `<span class="delta ${cls}">${flecha} ${pct(Math.abs(d))} vs 2024</span>`;
  };
  const items = [
    ["Ventas", usd(act.ventas), delta(act.ventas, prev?.ventas)],
    ["Margen bruto", pct(act.margen / act.ventas, 1), prev ? `<span class="delta">${usd(act.margen)}</span>` : delta()],
    ["Pedidos", act.pedidos.toLocaleString("es-PA"), delta(act.pedidos, prev?.pedidos)],
    ["Ticket promedio", usd(act.ventas / act.pedidos, 2), delta(act.ventas / act.pedidos, prev ? prev.ventas / prev.pedidos : 0)],
    ["Clientes nuevos", act.nuevos.toLocaleString("es-PA"), delta(act.nuevos, prev?.nuevos)],
  ];
  $("#kpis").innerHTML = items
    .map(([l, v, d]) => `<div class="kpi"><div class="label">${l}</div><div class="value">${v}</div>${d}</div>`)
    .join("");
}

function baseOpts() {
  Chart.defaults.font.family = 'system-ui, -apple-system, "Segoe UI", sans-serif';
  Chart.defaults.color = css("--text-muted");
  Chart.defaults.borderColor = css("--grid");
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 350 },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: css("--surface-1"), titleColor: css("--text-primary"), bodyColor: css("--text-secondary"),
        borderColor: css("--border"), borderWidth: 1, padding: 10, cornerRadius: 8, displayColors: true, boxPadding: 4,
      },
    },
  };
}

function ventas(anio, canal) {
  const filas = filtrar(anio, canal);
  const porMes = new Map();
  for (const r of filas) porMes.set(r.mes, (porMes.get(r.mes) || 0) + r.ventas);
  const meses = [...porMes.keys()].sort();
  const opts = baseOpts();
  opts.interaction = { mode: "index", intersect: false };
  opts.plugins.tooltip.callbacks = { title: (it) => mesCorto(meses[it[0].dataIndex]), label: (it) => " Ventas: " + usd(it.parsed.y) };
  opts.scales = {
    x: { grid: { display: false }, border: { color: css("--axis") }, ticks: { callback: (_, i) => mesCorto(meses[i]), maxRotation: 0, autoSkipPadding: 12 } },
    y: { beginAtZero: true, border: { display: false }, ticks: { callback: (v) => "$" + v / 1000 + "k", maxTicksLimit: 5 } },
  };
  charts.ventas?.destroy();
  charts.ventas = new Chart($("#c-ventas"), {
    type: "line",
    data: { labels: meses, datasets: [{ data: meses.map((m) => porMes.get(m)), borderColor: css("--series-1"), borderWidth: 2,
      backgroundColor: css("--series-1") + "1f", fill: true, tension: 0.25, pointRadius: 0, pointHoverRadius: 5,
      pointHoverBorderWidth: 2, pointHoverBorderColor: css("--surface-1"), pointHoverBackgroundColor: css("--series-1") }] },
    options: opts,
    plugins: [crosshair],
  });
  const canalTxt = canal === "todos" ? "todos los canales" : canal;
  $("#sub-ventas").textContent = `Pedidos entregados, USD · ${canalTxt}`;
}

// Línea vertical que sigue al cursor en el gráfico de líneas.
const crosshair = {
  id: "crosshair",
  afterDatasetsDraw(chart) {
    const a = chart.tooltip?.getActiveElements?.();
    if (!a?.length) return;
    const x = a[0].element.x, { top, bottom } = chart.chartArea, ctx = chart.ctx;
    ctx.save(); ctx.strokeStyle = css("--axis"); ctx.lineWidth = 1; ctx.setLineDash([3, 3]);
    ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, bottom); ctx.stroke(); ctx.restore();
  },
};

// Etiquetas directas al final de cada barra horizontal.
const etiquetas = (formato) => ({
  id: "etiquetas",
  afterDatasetsDraw(chart) {
    const ctx = chart.ctx;
    ctx.save(); ctx.fillStyle = css("--text-secondary"); ctx.font = '12px system-ui, sans-serif'; ctx.textBaseline = "middle";
    chart.getDatasetMeta(0).data.forEach((bar, i) => ctx.fillText(formato(i), bar.x + 6, bar.y));
    ctx.restore();
  },
});

function canales(canalSel) {
  const filas = [...DATA.canal_economia].sort((a, b) => b.ltv_cac - a.ltv_cac);
  const opts = baseOpts();
  opts.indexAxis = "y";
  opts.layout = { padding: { right: 40 } };
  opts.plugins.tooltip.callbacks = {
    label: (it) => {
      const r = filas[it.dataIndex];
      return [` LTV:CAC ${r.ltv_cac.toFixed(1)}x`, ` CAC ${usd(r.cac, 2)}`, ` Margen por cliente ${usd(r.margen_por_cliente, 2)}`];
    },
  };
  opts.scales = {
    x: { beginAtZero: true, grid: { color: css("--grid") }, border: { display: false }, ticks: { callback: (v) => v + "x", maxTicksLimit: 6 } },
    y: { grid: { display: false }, border: { color: css("--axis") }, ticks: { color: css("--text-secondary") } },
  };
  const umbral = {
    id: "umbral",
    afterDatasetsDraw(chart) {
      const x = chart.scales.x.getPixelForValue(3), { top, bottom } = chart.chartArea, ctx = chart.ctx;
      ctx.save(); ctx.strokeStyle = css("--text-muted"); ctx.setLineDash([4, 4]); ctx.beginPath();
      ctx.moveTo(x, top); ctx.lineTo(x, bottom); ctx.stroke();
      ctx.fillStyle = css("--text-muted"); ctx.font = "11px system-ui, sans-serif"; ctx.fillText("3x", x + 4, top + 8); ctx.restore();
    },
  };
  const base = css("--series-1");
  charts.canales?.destroy();
  charts.canales = new Chart($("#c-canales"), {
    type: "bar",
    data: { labels: filas.map((r) => r.canal), datasets: [{
      data: filas.map((r) => r.ltv_cac),
      backgroundColor: filas.map((r) => (canalSel === "todos" || r.canal === canalSel ? base : base + "40")),
      borderRadius: 4, borderSkipped: "start", barPercentage: 0.7, categoryPercentage: 0.9,
    }] },
    options: opts,
    plugins: [umbral, etiquetas((i) => filas[i].ltv_cac.toFixed(1) + "x")],
  });
}

function rfm() {
  const s = DATA.segmentos;
  const c1 = css("--series-1"), c2 = css("--series-2");
  $("#lg-rfm").innerHTML = `<span><i style="background:${c1}"></i>% de clientes</span><span><i style="background:${c2}"></i>% de ventas</span>`;
  const opts = baseOpts();
  opts.indexAxis = "y";
  opts.interaction = { mode: "index", axis: "y", intersect: false };
  opts.plugins.tooltip.callbacks = { label: (it) => ` ${it.dataset.label}: ${pct(it.parsed.x)}` };
  opts.scales = {
    x: { beginAtZero: true, border: { display: false }, ticks: { callback: (v) => pct(v), maxTicksLimit: 5 } },
    y: { grid: { display: false }, border: { color: css("--axis") }, ticks: { color: css("--text-secondary") } },
  };
  const comun = { borderRadius: 4, borderSkipped: "start", borderColor: css("--surface-1"), borderWidth: { top: 1, bottom: 1 }, barPercentage: 0.85, categoryPercentage: 0.8 };
  charts.rfm?.destroy();
  charts.rfm = new Chart($("#c-rfm"), {
    type: "bar",
    data: { labels: s.map((r) => r.segmento), datasets: [
      { label: "% de clientes", data: s.map((r) => r.pct_clientes), backgroundColor: c1, ...comun },
      { label: "% de ventas", data: s.map((r) => r.pct_ventas), backgroundColor: c2, ...comun },
    ] },
    options: opts,
  });
}

function categorias() {
  const c = DATA.categorias;
  const opts = baseOpts();
  opts.indexAxis = "y";
  opts.layout = { padding: { right: 70 } };
  opts.plugins.tooltip.callbacks = { label: (it) => [` Ventas ${usd(c[it.dataIndex].ventas)}`, ` Margen ${pct(c[it.dataIndex].margen / c[it.dataIndex].ventas)}`] };
  opts.scales = {
    x: { beginAtZero: true, border: { display: false }, ticks: { callback: (v) => "$" + v / 1000 + "k", maxTicksLimit: 5 } },
    y: { grid: { display: false }, border: { color: css("--axis") }, ticks: { color: css("--text-secondary") } },
  };
  charts.categorias?.destroy();
  charts.categorias = new Chart($("#c-categorias"), {
    type: "bar",
    data: { labels: c.map((r) => r.categoria), datasets: [{ data: c.map((r) => r.ventas), backgroundColor: css("--series-1"), borderRadius: 4, borderSkipped: "start", barPercentage: 0.7 }] },
    options: opts,
    plugins: [etiquetas((i) => `margen ${pct(c[i].margen / c[i].ventas)}`)],
  });
}

function cohortes() {
  const { cohortes: filas, meses, valores } = DATA.cohortes;
  const max = Math.max(...valores.flatMap((f) => f.slice(1)).filter((v) => v != null));
  $("#scale-max").textContent = pct(max);
  const pasos = ["--seq-1", "--seq-2", "--seq-3", "--seq-4", "--seq-5", "--seq-6", "--seq-7"].map(css);
  const color = (v) => pasos[Math.min(pasos.length - 1, Math.floor((v / max) * pasos.length))];
  const head = `<thead><tr><th scope="col">Cohorte</th>${meses.slice(1).map((m) => `<th scope="col">M${m}</th>`).join("")}</tr></thead>`;
  const body = filas.map((coh, i) => {
    const celdas = valores[i].slice(1).map((v, j) => {
      if (v == null) return '<td class="na">·</td>';
      const fondo = color(v);
      const oscuro = pasos.indexOf(fondo) >= 4;
      return `<td style="background:${fondo};color:${oscuro ? "#ffffff" : "#0b0b0b"}" title="${mesCorto(coh)} · mes ${j + 1}: ${pct(v, 1)}">${pct(v)}</td>`;
    }).join("");
    return `<tr><th scope="row">${mesCorto(coh)}</th>${celdas}</tr>`;
  }).join("");
  $("#t-cohortes").innerHTML = head + `<tbody>${body}</tbody>`;
}

function tablaCanales() {
  const f = [...DATA.canal_economia].sort((a, b) => b.ltv_cac - a.ltv_cac);
  $("#t-canales").innerHTML =
    "<thead><tr><th>Canal</th><th>Clientes</th><th>CAC</th><th>Margen/cliente</th><th>LTV:CAC</th></tr></thead><tbody>" +
    f.map((r) => `<tr><td>${r.canal}</td><td>${r.clientes_nuevos.toLocaleString("es-PA")}</td><td>${usd(r.cac, 2)}</td><td>${usd(r.margen_por_cliente, 2)}</td><td>${r.ltv_cac.toFixed(1)}x</td></tr>`).join("") +
    "</tbody>";
}

function hallazgos() {
  const a = sumar(filtrar("2024", "todos")), b = sumar(filtrar("2025", "todos"));
  const ce = [...DATA.canal_economia].sort((x, y) => y.ltv_cac - x.ltv_cac);
  const camp = DATA.segmentos.find((s) => s.segmento === "Campeones");
  const riesgo = DATA.segmentos.find((s) => s.segmento === "En riesgo");
  const m1 = DATA.cohortes.valores.map((f) => f[1]).filter((v) => v != null);
  const ret1 = m1.reduce((x, y) => x + y, 0) / m1.length;
  const items = [
    `Las ventas crecieron <strong>${pct(b.ventas / a.ventas - 1)}</strong> en 2025, hasta ${usd(b.ventas)}.`,
    `<strong>${ce[0].canal}</strong> devuelve ${ce[0].ltv_cac.toFixed(1)}x su costo; <strong>${ce.at(-1).canal}</strong> apenas ${ce.at(-1).ltv_cac.toFixed(1)}x: es el primer candidato a recortar presupuesto.`,
    `Los <strong>Campeones</strong> son el ${pct(camp.pct_clientes)} de los clientes y aportan el ${pct(camp.pct_ventas)} de las ventas.`,
    `<strong>${riesgo.clientes.toLocaleString("es-PA")} clientes en riesgo</strong> compraban seguido y llevan ${Math.round(riesgo.recencia)} días sin volver: una campaña de recuperación tiene alto retorno.`,
    `Solo el <strong>${pct(ret1)}</strong> de una cohorte vuelve al mes siguiente: la segunda compra es el punto a mejorar.`,
  ];
  $("#insights").innerHTML = items.map((t) => `<li>${t}</li>`).join("");
}

function render() {
  const anio = $("#f-anio").value, canal = $("#f-canal").value;
  kpis(anio, canal);
  ventas(anio, canal);
  canales(canal);
}

async function init() {
  DATA = await (await fetch("data.json")).json();
  $("#f-canal").insertAdjacentHTML("beforeend", DATA.canales.map((c) => `<option>${c}</option>`).join(""));
  $("#f-anio").addEventListener("change", render);
  $("#f-canal").addEventListener("change", render);
  render();
  rfm();
  categorias();
  cohortes();
  tablaCanales();
  hallazgos();
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { render(); rfm(); categorias(); cohortes(); });
}

window.addEventListener("DOMContentLoaded", init);
