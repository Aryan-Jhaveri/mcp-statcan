// Turn StatCan tool results (get_sdmx_data / get_sdmx_vector_data / query_sdmx
// structuredContent) into chartable series. Pure functions — no DOM.

export type Row = Record<string, unknown>;

export interface Point {
  period: string;
  t: number; // UTC ms of the period start
  value: number | null;
}

export interface Series {
  id: string;
  label: string;
  points: Point[];
}

export interface Dataset {
  rows: Row[];
  columns: string[];
  series: Series[]; // empty when the rows can't be charted
  constants: string[]; // dimension values shared by every series (shown as a caption)
  valueColumn: string | null;
  sourceUrl: string | null;
  productId: number | null;
  vectorId: number | null;
  truncated: boolean;
  message: string | null;
}

const INTERNAL = new Set(["_series_key"]);

/** Period label -> UTC ms of its start: 2026, 2026-08, 2026-Q2, 2026-S2, 2026-W40, 2026-08-15. */
export function periodToTime(period: string): number | null {
  const p = period.trim();
  let m: RegExpMatchArray | null;
  if ((m = p.match(/^(\d{4})$/))) return Date.UTC(+m[1], 0, 1);
  if ((m = p.match(/^(\d{4})-(\d{2})$/))) return Date.UTC(+m[1], +m[2] - 1, 1);
  if ((m = p.match(/^(\d{4})-(\d{2})-(\d{2})/))) return Date.UTC(+m[1], +m[2] - 1, +m[3]);
  if ((m = p.match(/^(\d{4})-Q([1-4])$/))) return Date.UTC(+m[1], (+m[2] - 1) * 3, 1);
  if ((m = p.match(/^(\d{4})-S([12])$/))) return Date.UTC(+m[1], m[2] === "1" ? 0 : 6, 1);
  if ((m = p.match(/^(\d{4})-W(\d{2})$/))) {
    // ISO week: Monday of week 1 is the Monday on or before Jan 4
    const jan4 = Date.UTC(+m[1], 0, 4);
    const monday = jan4 - (((new Date(jan4).getUTCDay() + 6) % 7) * 86400000);
    return monday + (+m[2] - 1) * 7 * 86400000;
  }
  return null;
}

function toNumber(v: unknown): number | null {
  if (v === null || v === undefined || v === "") return null;
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n : null;
}

/** "18100004" -> "18-10-0004-01" (StatCan's displayed table number). */
export function formatProductId(pid: number): string {
  const s = String(pid).padStart(8, "0");
  return `${s.slice(0, 2)}-${s.slice(2, 4)}-${s.slice(4, 8)}-01`;
}

function productIdFromUrl(url: string | null): number | null {
  const m = url?.match(/DF_(\d{8})/);
  return m ? Number(m[1]) : null;
}

function vectorIdFromUrl(url: string | null): number | null {
  const m = url?.match(/\/vector\/v(\d+)/);
  return m ? Number(m[1]) : null;
}

/** Build a Dataset from a tool's structuredContent. */
export function toDataset(sc: Record<string, unknown> | undefined): Dataset {
  const rows = ((sc?.data ?? sc?.rows) as Row[] | undefined) ?? [];
  const sourceUrl = typeof sc?._sdmx_url === "string" ? sc._sdmx_url : null;
  const columns: string[] = [];
  for (const r of rows) for (const k of Object.keys(r)) if (!columns.includes(k)) columns.push(k);

  const base = {
    rows,
    columns: columns.filter((c) => !INTERNAL.has(c)),
    sourceUrl,
    productId: productIdFromUrl(sourceUrl),
    vectorId: vectorIdFromUrl(sourceUrl),
    truncated: sc?._truncated === true || typeof sc?.message === "string",
    message: (sc?._message as string) ?? (sc?.message as string) ?? null,
  };

  const valueColumn = pickValueColumn(rows, columns);
  const chartable =
    valueColumn !== null && rows.length > 0 && rows.every((r) => typeof r.period === "string" && periodToTime(r.period as string) !== null);
  if (!chartable) return { ...base, series: [], constants: [], valueColumn };

  // Dimension columns: those before _series_key (SDMX rows), else the string columns
  // other than period/value (query_sdmx results).
  const keyIdx = columns.indexOf("_series_key");
  const dims =
    keyIdx >= 0
      ? columns.slice(0, keyIdx)
      : columns.filter((c) => c !== "period" && c !== valueColumn && rows.some((r) => typeof r[c] === "string"));
  const varying = dims.filter((d) => new Set(rows.map((r) => String(r[d] ?? ""))).size > 1);
  const constants = dims.filter((d) => !varying.includes(d)).map((d) => String(rows[0][d] ?? "")).filter(Boolean);

  const byId = new Map<string, Series>();
  for (const r of rows) {
    const label = varying.map((d) => String(r[d] ?? "")).join(" · ") || constants.join(" · ") || valueColumn!;
    const id = keyIdx >= 0 ? String(r._series_key) : label;
    let s = byId.get(id);
    if (!s) byId.set(id, (s = { id, label, points: [] }));
    const period = r.period as string;
    s.points.push({ period, t: periodToTime(period)!, value: toNumber(r[valueColumn!]) });
  }
  const series = [...byId.values()];
  for (const s of series) s.points.sort((a, b) => a.t - b.t);
  return { ...base, series, constants, valueColumn };
}

function pickValueColumn(rows: Row[], columns: string[]): string | null {
  if (columns.includes("value")) return "value";
  const numeric = columns.filter((c) => c !== "period" && rows.length > 0 && rows.every((r) => r[c] === null || toNumber(r[c]) !== null));
  return numeric[0] ?? null;
}

/** RFC 4180 CSV of the rows (internal columns dropped). */
export function toCsv(rows: Row[], columns: string[]): string {
  const cell = (v: unknown) => {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [columns.map(cell).join(","), ...rows.map((r) => columns.map((c) => cell(r[c])).join(","))].join("\n") + "\n";
}
