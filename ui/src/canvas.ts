// StatCan canvas (ui://statcan/canvas.html): renders views the model builds with render_view.
//
// Two ways in:
//   - MCP Apps host: the render_view result arrives as structuredContent (ontoolresult).
//   - Standalone page (hosted /views/<id> or a local file): the same payload is embedded
//     in <script id="statcan-payload">, and tool calls go straight to the hosted /mcp.
// Either way the model's code gets window.statcan (data, query, send, download, theme).

import { App, applyDocumentTheme, applyHostStyleVariables } from "@modelcontextprotocol/ext-apps/app-with-deps";
import { describeSource, parseRpcBody, prepareRows, toCSV, unwrapToolResult, type Payload, type Row } from "./data";
import { mountHtml, mountVegaLite, onMountError } from "./mount";
import "./styles.css";

interface Transport {
  call(name: string, args: Record<string, unknown>): Promise<any>;
  send(text: string): Promise<boolean>;
  download(filename: string, text: string, mimeType: string): Promise<void>;
  openLink(url: string): void;
  reportToModel(text: string): void;
}

const $ = (id: string) => document.getElementById(id) as HTMLElement;
const statusEl = $("sc-status");
const errorsEl = $("sc-errors");
const root = $("sc-root");
const footer = $("sc-footer");

let payload: Payload | null = null;
let transport: Transport | null = null;

// ── Errors: shown in the view and reported to the model so it can fix its code ──
const reported = new Set<string>();
function showError(message: string, toModel = true): void {
  if (reported.has(message) || reported.size >= 10) return;
  reported.add(message);
  errorsEl.hidden = false;
  const item = document.createElement("div");
  item.textContent = message;
  errorsEl.append(item);
  if (toModel) transport?.reportToModel(`render_view ${payload?.view_id ?? ""} ("${payload?.title ?? ""}") error in the view: ${message}`);
}
onMountError(showError);
window.addEventListener("error", (e) => {
  const where = e.filename && !e.filename.startsWith("data:") ? ` (${e.filename.split("/").pop()}:${e.lineno})` : e.lineno ? ` (line ${e.lineno})` : "";
  showError(`${e.message || "Script error"}${where}`);
});
window.addEventListener("unhandledrejection", (e) => {
  showError(`Unhandled promise rejection: ${e.reason instanceof Error ? e.reason.message : String(e.reason)}`);
});

// ── Theme ──
const themeListeners: ((theme: "light" | "dark") => void)[] = [];
function currentTheme(): "light" | "dark" {
  const attr = document.documentElement.dataset.theme;
  if (attr === "light" || attr === "dark") return attr;
  return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
function palette(): string[] {
  return Array.from({ length: 8 }, (_, i) => cssVar(`--sc-series-${i + 1}`));
}
function themeChanged(): void {
  const theme = currentTheme();
  for (const fn of themeListeners) {
    try {
      fn(theme);
    } catch (e) {
      showError(e instanceof Error ? e.message : String(e));
    }
  }
  if (payload?.vega_lite) void renderVega();
}
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", themeChanged);

// ── The API the model's code uses ──
function createStatcan(p: Payload) {
  const t = () => {
    if (!transport) throw new Error("Not connected");
    return transport;
  };
  const data: Record<string, Row[]> = {};
  const datasets: Record<string, Omit<Payload["datasets"][string], "rows">> = {};
  for (const [name, ds] of Object.entries(p.datasets)) {
    data[name] = ds.rows;
    const { rows: _rows, ...meta } = ds;
    datasets[name] = meta;
  }
  return {
    title: p.title,
    viewId: p.view_id,
    url: p.url ?? null,
    data,
    datasets,
    get theme() {
      return currentTheme();
    },
    get palette() {
      return palette();
    },
    onThemeChange(fn: (theme: "light" | "dark") => void) {
      themeListeners.push(fn);
    },
    /** Live SQL over StatCan data (query_sdmx); resolves to the result rows. */
    async query(args: Record<string, unknown>): Promise<Row[]> {
      const r = await t().call("query_sdmx", args);
      return prepareRows(r.rows ?? []);
    },
    /** Raw observation rows (get_sdmx_rows, or get_sdmx_vector_data for a vectorId); max 500. */
    async fetch(args: Record<string, unknown>): Promise<Row[]> {
      const r = await t().call("vectorId" in args ? "get_sdmx_vector_data" : "get_sdmx_rows", args);
      return prepareRows(r.data ?? []);
    },
    /** Any tool on this server; resolves to its structured result. */
    call(name: string, args: Record<string, unknown> = {}) {
      return t().call(name, args);
    },
    /** Post a message to the conversation as the user. False where unsupported. */
    send(text: string) {
      return t().send(text);
    },
    download(filename: string, text: string, mimeType = "text/plain") {
      return t().download(filename, text, mimeType);
    },
    openLink(url: string) {
      t().openLink(url);
    },
    toCSV,
  };
}

// ── Footer: data sources + a way out to the full page ──
function renderFooter(p: Payload): void {
  footer.replaceChildren();
  // One link per table/vector, even when several datasets come from the same one
  const sources = new Map<string, string>();
  for (const ds of Object.values(p.datasets)) {
    if (ds.source_url && !sources.has(describeSource(ds.source_url))) sources.set(describeSource(ds.source_url), ds.source_url);
  }
  const parts: (string | HTMLElement)[] = [];
  if (sources.size) {
    const cite = document.createElement("span");
    cite.append("Source: Statistics Canada, ");
    [...sources].forEach(([label, url], i) => {
      if (i) cite.append(", ");
      cite.append(link(label, url));
    });
    parts.push(cite);
  }
  const names = Object.keys(p.datasets);
  if (names.length) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = "Download data";
    b.addEventListener("click", () => {
      for (const name of names) {
        const ds = p.datasets[name];
        void transport?.download(`${name}.csv`, toCSV(ds.rows, ds.columns), "text/csv");
      }
    });
    parts.push(b);
  }
  if (p.url && !document.getElementById("statcan-payload")) parts.push(link("Open full page ↗", p.url));
  if (document.getElementById("statcan-payload")) {
    // Standalone pages are model-written HTML on our domain: say so
    const note = document.createElement("span");
    note.textContent = "AI-generated view, not an official Statistics Canada page";
    parts.push(note);
  }
  footer.append(...parts);
  footer.hidden = parts.length === 0;
}

function link(text: string, href: string): HTMLElement {
  const a = document.createElement("a");
  a.href = href;
  a.textContent = text;
  a.target = "_blank";
  a.rel = "noopener";
  a.addEventListener("click", (e) => {
    e.preventDefault();
    transport?.openLink(href);
  });
  return a;
}

// ── Render ──
async function renderVega(): Promise<void> {
  if (!payload?.vega_lite) return;
  await mountVegaLite(root, payload.vega_lite, payload.datasets, {
    dark: currentTheme() === "dark",
    palette: palette(),
    font: cssVar("--sc-font"),
    text: cssVar("--sc-fg"),
    muted: cssVar("--sc-muted"),
    grid: cssVar("--sc-border"),
  });
}

async function render(p: Payload): Promise<void> {
  if (payload) return; // one view per tool call
  payload = p;
  document.title = p.title;
  (window as any).statcan = createStatcan(p);
  statusEl.hidden = true;
  renderFooter(p);
  try {
    if (p.vega_lite) await renderVega();
    else await mountHtml(root, p.html ?? "");
  } catch (e) {
    showError(e instanceof Error ? e.message : String(e));
  }
}

// ── Standalone page ──
function standaloneTransport(endpoint: string | null | undefined): Transport {
  let id = 0;
  return {
    async call(name, args) {
      if (!endpoint)
        throw new Error("Live queries need the hosted server or an MCP Apps client; bind the data with render_view instead.");
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json, text/event-stream" },
        body: JSON.stringify({ jsonrpc: "2.0", id: ++id, method: "tools/call", params: { name, arguments: args } }),
      });
      if (!res.ok) throw new Error(`StatCan server returned HTTP ${res.status}`);
      const msg = parseRpcBody(await res.text(), res.headers.get("content-type") ?? "");
      if (msg.error) throw new Error(msg.error.message ?? "Tool call failed");
      return unwrapToolResult(msg.result);
    },
    async send(text) {
      try {
        await navigator.clipboard.writeText(text);
      } catch {}
      return false;
    },
    async download(filename, text, mimeType) {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([text], { type: mimeType }));
      a.download = filename;
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    },
    openLink(url) {
      window.open(url, "_blank", "noopener");
    },
    reportToModel() {},
  };
}

// ── MCP Apps host ──
function appTransport(app: App): Transport {
  return {
    async call(name, args) {
      return unwrapToolResult(await app.callServerTool({ name, arguments: args }));
    },
    async send(text) {
      const r = await app.sendMessage({ role: "user", content: [{ type: "text", text }] });
      return !r?.isError;
    },
    async download(filename, text, mimeType) {
      if (app.getHostCapabilities()?.downloadFile) {
        await app.downloadFile({ contents: [{ type: "resource", resource: { uri: `file:///${filename}`, mimeType, text } }] });
      } else {
        await standaloneTransport(null).download(filename, text, mimeType);
      }
    },
    openLink(url) {
      void app.openLink({ url });
    },
    reportToModel(text) {
      void app.updateModelContext({ content: [{ type: "text", text }] }).catch(() => {});
    },
  };
}

const embedded = document.getElementById("statcan-payload");
if (embedded) {
  const p = JSON.parse(embedded.textContent ?? "{}") as Payload;
  transport = standaloneTransport(p.mcp_endpoint);
  void render(p);
} else {
  const app = new App({ name: "StatCan canvas", version: "1.0.0" }, {}, { autoResize: true });
  transport = appTransport(app);
  const applyHost = () => {
    const ctx = app.getHostContext();
    if (ctx?.theme) applyDocumentTheme(ctx.theme);
    if (ctx?.styles?.variables) applyHostStyleVariables(ctx.styles.variables);
  };
  app.ontoolinputpartial = (params) => {
    const title = (params.arguments as { title?: unknown } | undefined)?.title;
    if (!payload && typeof title === "string") statusEl.textContent = `Building “${title}”…`;
  };
  app.ontoolinput = () => {
    if (!payload) statusEl.textContent = "Fetching data from Statistics Canada…";
  };
  app.ontoolresult = (result) => {
    if (result.isError) {
      statusEl.hidden = true;
      const text = (result.content ?? []).map((c) => ("text" in c ? c.text : "")).join(" ");
      showError(text || "render_view failed", false); // the model already has this result
      return;
    }
    void render(result.structuredContent as unknown as Payload);
  };
  app.ontoolcancelled = () => {
    if (!payload) statusEl.textContent = "Cancelled.";
  };
  app.onhostcontextchanged = () => {
    applyHost();
    themeChanged();
  };
  void app.connect().then(applyHost);
}
