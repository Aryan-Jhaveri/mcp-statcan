// Pure helpers shared by the canvas bridge and its tests (no DOM, no host).

export type Row = Record<string, unknown>;

export interface Dataset {
  columns: string[];
  rows: Row[];
  row_count: number;
  truncated: boolean;
  source_url?: string | null;
}

/** structuredContent of render_view (see RenderViewOutput in src/models/canvas_models.py). */
export interface Payload {
  view_id: string;
  title: string;
  url?: string | null;
  html?: string;
  vega_lite?: Record<string, unknown>;
  datasets: Record<string, Dataset>;
  mcp_endpoint?: string | null;
}

const PERIOD = /^(\d{4})(?:-(?:(\d{2})(?:-(\d{2}))?|Q([1-4])|S([12])))?$/;

/** ISO date for the start of a StatCan period; mirrors period_to_date in src/api/canvas.py. */
export function periodToDate(period: unknown): string | null {
  const m = PERIOD.exec(String(period ?? ""));
  if (!m) return null;
  const [, year, month, day, quarter, half] = m;
  let mm = month ?? "01";
  if (quarter) mm = String((Number(quarter) - 1) * 3 + 1).padStart(2, "0");
  else if (half) mm = half === "1" ? "01" : "07";
  return `${year}-${mm}-${day ?? "01"}`;
}

/** Numeric value and parsed date, matching the rows the server binds into statcan.data. */
export function prepareRows(rows: Row[]): Row[] {
  for (const r of rows) {
    if (typeof r.value === "string" && r.value.trim() !== "" && !Number.isNaN(Number(r.value))) r.value = Number(r.value);
    if ("period" in r && !("date" in r)) r.date = periodToDate(r.period);
  }
  return rows;
}

export function toCSV(rows: Row[], columns?: string[]): string {
  const cols = columns ?? [...new Set(rows.slice(0, 50).flatMap((r) => Object.keys(r)))];
  const cell = (v: unknown) => {
    if (v === null || v === undefined) return "";
    const s = typeof v === "object" ? JSON.stringify(v) : String(v);
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [cols.map(cell).join(","), ...rows.map((r) => cols.map((c) => cell(r[c])).join(","))].join("\n");
}

/** "Table 18-10-0004-01" or "Vector v41690973" from an SDMX request URL. */
export function describeSource(url: string): string {
  const table = /\/DF_(\d{8})\//.exec(url);
  if (table) {
    const p = table[1];
    return `Table ${p.slice(0, 2)}-${p.slice(2, 4)}-${p.slice(4)}-01`;
  }
  const vector = /\/vector\/v(\d+)/.exec(url);
  return vector ? `Vector v${vector[1]}` : "StatCan SDMX";
}

interface ToolResultLike {
  isError?: boolean;
  structuredContent?: unknown;
  content?: { type: string; text?: string }[];
}

/** A tool result's data (structuredContent, else parsed text); throws on a tool error. */
export function unwrapToolResult(result: ToolResultLike): any {
  const text = (result.content ?? []).filter((c) => c.type === "text").map((c) => c.text ?? "").join("\n");
  if (result.isError) {
    let msg = text;
    try {
      const parsed = JSON.parse(text);
      msg = [parsed.error, parsed.hint].filter(Boolean).join(" ") || text;
    } catch {}
    throw new Error(msg || "Tool call failed");
  }
  if (result.structuredContent !== undefined && result.structuredContent !== null) return result.structuredContent;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

/** The JSON-RPC response in a Streamable HTTP body (SSE `data:` lines or plain JSON). */
export function parseRpcBody(body: string, contentType: string): any {
  if (!contentType.includes("text/event-stream")) return JSON.parse(body);
  let last: any = null;
  for (const line of body.split(/\r?\n/)) {
    if (!line.startsWith("data:")) continue;
    const msg = JSON.parse(line.slice(5).trim());
    if ("result" in msg || "error" in msg) last = msg;
  }
  if (!last) throw new Error("No response from the StatCan server");
  return last;
}

/** Vega-Lite spec with the bound datasets, a schema, and full-width layout unless the spec says otherwise. */
export function prepareVegaLite(spec: Record<string, any>, datasets: Record<string, Dataset>): Record<string, any> {
  const out: Record<string, any> = { ...spec };
  out.$schema ??= "https://vega.github.io/schema/vega-lite/v6.json";
  out.datasets = { ...(spec.datasets ?? {}) };
  for (const [name, ds] of Object.entries(datasets)) out.datasets[name] = ds.rows;
  const composite = ["hconcat", "vconcat", "concat", "facet", "repeat"].some((k) => k in spec);
  if (!composite && spec.width === undefined) out.width = "container";
  if (out.background === undefined) out.background = "transparent";
  return out;
}
