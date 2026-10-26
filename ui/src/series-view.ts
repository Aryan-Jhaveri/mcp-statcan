// StatCan series view (MCP Apps, ui://statcan/series-view.html).
// Renders get_sdmx_data / get_sdmx_vector_data / query_sdmx results as a line chart
// with a table view. Full rows arrive as structuredContent, which the host keeps out
// of the model's context; the model gets a summary.

import { App, applyDocumentTheme, applyHostStyleVariables } from "@modelcontextprotocol/ext-apps/app-with-deps";
import { LineChart, type ChartSeries } from "./chart";
import { formatProductId, toCsv, toDataset, type Dataset } from "./data";
import "./styles.css";

const MAX_ACTIVE = 8; // categorical palette size: never cycle hues
const PALETTE_SLOTS = 8;

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const el = {
  title: $("title"),
  subtitle: $("subtitle"),
  tabChart: $<HTMLButtonElement>("tab-chart"),
  tabTable: $<HTMLButtonElement>("tab-table"),
  download: $<HTMLButtonElement>("download"),
  source: $<HTMLButtonElement>("source"),
  chartView: $("chart-view"),
  tableView: $("table-view"),
  canvas: $<HTMLCanvasElement>("chart"),
  tooltip: $("tooltip"),
  legend: $("legend"),
  legendNote: $("legend-note"),
  table: $<HTMLTableElement>("table"),
  footer: $("footer"),
  status: $("status"),
};

const app = new App({ name: "StatCan series view", version: "1.0.0" }, {}, { autoResize: true });
const chart = new LineChart(el.canvas, el.tooltip);

let dataset: Dataset | null = null;
const active = new Set<string>(); // visible series ids
const slotOf = new Map<string, number>(); // series id -> palette slot (follows the entity, never its rank)

function colorFor(id: string): string {
  const slot = slotOf.get(id)!;
  return getComputedStyle(document.documentElement).getPropertyValue(`--viz-series-${slot + 1}`).trim();
}

function assignSlot(id: string): void {
  if (slotOf.has(id)) return;
  const used = new Set([...active].map((a) => slotOf.get(a)));
  for (let s = 0; s < PALETTE_SLOTS; s++)
    if (!used.has(s)) {
      slotOf.set(id, s);
      return;
    }
}

function applyHostContext(): void {
  const ctx = app.getHostContext();
  if (ctx?.theme) applyDocumentTheme(ctx.theme);
  if (ctx?.styles?.variables) applyHostStyleVariables(ctx.styles.variables);
}

function render(): void {
  if (!dataset) return;
  const d = dataset;
  el.status.hidden = true;
  document.body.classList.toggle("has-chart", d.series.length > 0);

  const uom = d.rows.length && typeof d.rows[0].UOM === "string" && d.rows.every((r) => r.UOM === d.rows[0].UOM) ? (d.rows[0].UOM as string) : "";
  const bits = [...d.constants];
  if (uom) bits.push(`Unit: ${uom}`);
  el.subtitle.textContent = bits.join(" · ");
  if (!el.title.dataset.fromServer)
    el.title.textContent = d.productId
      ? `Table ${formatProductId(d.productId)}`
      : d.vectorId
        ? `Vector v${d.vectorId}`
        : "Query result";

  const n = d.rows.length;
  const periods = d.series.flatMap((s) => s.points.map((p) => p.period)).sort();
  const parts = ["Source: Statistics Canada"];
  if (d.productId) parts[0] += `, table ${formatProductId(d.productId)}`;
  parts.push(`${n.toLocaleString()} row${n === 1 ? "" : "s"}`);
  if (d.series.length) parts.push(`${d.series.length} series`, `${periods[0]} to ${periods[periods.length - 1]}`);
  if (d.truncated && d.message) parts.push(d.message);
  el.footer.textContent = parts.join(" · ");

  const caps = app.getHostCapabilities();
  el.download.hidden = !caps?.downloadFile || !n;
  el.source.hidden = !caps?.openLinks || !d.sourceUrl;

  renderLegend();
  renderTable();
  el.tabChart.disabled = !d.series.length;
  el.tabChart.title = d.series.length ? "" : "No time periods to chart; showing the table";
  showTab(d.series.length ? "chart" : "table");
  drawChart();
}

function drawChart(): void {
  if (!dataset) return;
  const visible: ChartSeries[] = dataset.series
    .filter((s) => active.has(s.id))
    .map((s) => ({ id: s.id, label: s.label, color: colorFor(s.id), points: s.points }));
  el.canvas.setAttribute(
    "aria-label",
    `Line chart of ${visible.map((s) => s.label).join(", ") || "no series"}. Use left and right arrow keys to read values.`,
  );
  chart.setData(visible, "");
}

function renderLegend(): void {
  const d = dataset!;
  el.legend.replaceChildren();
  el.legend.hidden = d.series.length < 2; // a single series needs no legend; the title names it
  for (const s of d.series) {
    const on = active.has(s.id);
    const b = document.createElement("button");
    b.type = "button";
    b.className = "legend-item";
    b.setAttribute("aria-pressed", String(on));
    const sw = document.createElement("span");
    sw.className = "swatch";
    if (on) sw.style.background = colorFor(s.id);
    const label = document.createElement("span");
    label.textContent = s.label;
    b.append(sw, label);
    b.addEventListener("click", () => toggle(s.id));
    el.legend.append(b);
  }
  el.legendNote.textContent =
    d.series.length > MAX_ACTIVE ? `Showing ${active.size} of ${d.series.length} series. Up to ${MAX_ACTIVE} at once; select in the legend.` : "";
}

function toggle(id: string): void {
  if (active.has(id)) {
    if (active.size === 1) return; // keep at least one line
    active.delete(id);
    slotOf.delete(id); // free the slot; survivors keep their colors
  } else {
    if (active.size >= MAX_ACTIVE) {
      el.legendNote.textContent = `Up to ${MAX_ACTIVE} series at once. Hide one first.`;
      return;
    }
    assignSlot(id);
    active.add(id);
  }
  renderLegend();
  drawChart();
  shareSelection();
}

/** Tell the model which series the user is looking at, for follow-up questions. */
function shareSelection(): void {
  if (!dataset || !app.getHostCapabilities()?.updateModelContext) return;
  const names = dataset.series.filter((s) => active.has(s.id)).map((s) => s.label);
  app
    .updateModelContext({ content: [{ type: "text", text: `The user is viewing these series in the chart: ${names.join("; ")}.` }] })
    .catch(() => undefined);
}

function renderTable(): void {
  const d = dataset!;
  el.table.replaceChildren();
  const thead = el.table.createTHead().insertRow();
  for (const c of d.columns) {
    const th = document.createElement("th");
    th.scope = "col";
    th.textContent = c;
    if (c === d.valueColumn) th.className = "num";
    thead.append(th);
  }
  const body = el.table.createTBody();
  for (const r of d.rows) {
    const tr = body.insertRow();
    for (const c of d.columns) {
      const td = tr.insertCell();
      const v = r[c];
      td.textContent = v === null || v === undefined ? "" : String(v);
      if (c === d.valueColumn) td.className = "num";
    }
  }
}

function showTab(tab: "chart" | "table"): void {
  const chartOn = tab === "chart" && !!dataset?.series.length;
  el.chartView.hidden = !chartOn;
  el.tableView.hidden = chartOn;
  el.tabChart.setAttribute("aria-selected", String(chartOn));
  el.tabTable.setAttribute("aria-selected", String(!chartOn));
  if (chartOn) drawChart();
}

async function fetchTitle(productId: number): Promise<void> {
  if (!app.getHostCapabilities()?.serverTools) return;
  try {
    const res = await app.callServerTool({ name: "get_sdmx_structure", arguments: { productId } });
    const name = (res.structuredContent as { name?: string } | undefined)?.name;
    if (name) {
      el.title.textContent = name;
      el.title.dataset.fromServer = "1";
    }
  } catch {
    // keep the table-number title
  }
}

app.addEventListener("toolresult", (result) => {
  if (result.isError) {
    el.status.hidden = false;
    el.status.textContent = "The tool returned an error; see the conversation for details.";
    return;
  }
  dataset = toDataset(result.structuredContent as Record<string, unknown> | undefined);
  active.clear();
  slotOf.clear();
  for (const s of dataset.series.slice(0, MAX_ACTIVE)) {
    assignSlot(s.id);
    active.add(s.id);
  }
  render();
  if (dataset.productId) void fetchTitle(dataset.productId);
});

app.addEventListener("hostcontextchanged", () => {
  applyHostContext();
  if (dataset) {
    renderLegend();
    drawChart();
  }
});

el.tabChart.addEventListener("click", () => showTab("chart"));
el.tabTable.addEventListener("click", () => showTab("table"));
el.download.addEventListener("click", async () => {
  if (!dataset) return;
  const name = dataset.productId ? `statcan_${dataset.productId}.csv` : "statcan_query.csv";
  await app.downloadFile({
    contents: [{ type: "resource", resource: { uri: `file:///${name}`, mimeType: "text/csv", text: toCsv(dataset.rows, dataset.columns) } }],
  });
});
el.source.addEventListener("click", () => {
  if (dataset?.sourceUrl) void app.openLink({ url: dataset.sourceUrl });
});

await app.connect();
applyHostContext();
