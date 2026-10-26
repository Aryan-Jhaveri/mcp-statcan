// Canvas line chart: time on x, one y axis, 2px lines, recessive grid, crosshair that
// snaps to the nearest period with a tooltip listing every visible series, and direct
// labels at line ends when <= 4 series are shown. Colors come from CSS custom properties
// so host theme changes only need a redraw.

import type { Point } from "./data";

export interface ChartSeries {
  id: string;
  label: string;
  color: string;
  points: Point[];
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DIRECT_LABEL_MAX = 4;

function cssVar(el: Element, name: string, fallback: string): string {
  return getComputedStyle(el).getPropertyValue(name).trim() || fallback;
}

export function formatValue(v: number | null, digits: number): string {
  if (v === null) return "n/a";
  return v.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

/** Decimal places used in the data (so 169.8 stays 169.8, 382660 stays 382,660). */
export function decimalsOf(series: ChartSeries[]): number {
  let d = 0;
  for (const s of series)
    for (const p of s.points)
      if (p.value !== null) d = Math.max(d, (String(p.value).split(".")[1] ?? "").length);
  return Math.min(d, 4);
}

export function niceTicks(min: number, max: number, count = 5): number[] {
  if (min === max) {
    const pad = Math.abs(min) * 0.05 || 1;
    min -= pad;
    max += pad;
  }
  const raw = (max - min) / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw)!;
  // First tick at or below min, last at or above max, so no line leaves the plot
  const ticks: number[] = [];
  for (let v = Math.floor(min / step) * step; ; v += step) {
    ticks.push(+v.toFixed(10));
    if (v >= max - step * 1e-9) break;
  }
  return ticks;
}

function timeTicks(t0: number, t1: number): { t: number; label: string }[] {
  const y0 = new Date(t0).getUTCFullYear();
  const y1 = new Date(t1).getUTCFullYear();
  const years = y1 - y0;
  if (years >= 3) {
    const step = [1, 2, 5, 10, 20, 25, 50].find((s) => years / s <= 7) ?? 100;
    const out = [];
    for (let y = Math.ceil(y0 / step) * step; y <= y1; y += step) {
      const t = Date.UTC(y, 0, 1);
      if (t >= t0 && t <= t1) out.push({ t, label: String(y) });
    }
    return out;
  }
  const months = (y1 - y0) * 12 + new Date(t1).getUTCMonth() - new Date(t0).getUTCMonth();
  const step = [1, 2, 3, 6, 12].find((s) => months / s <= 7) ?? 12;
  const out = [];
  const start = new Date(t0);
  for (let i = 0; ; i += step) {
    const d = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + i, 1));
    if (d.getTime() > t1) break;
    if (d.getTime() >= t0)
      out.push({ t: d.getTime(), label: `${MONTHS[d.getUTCMonth()]} '${String(d.getUTCFullYear()).slice(2)}` });
  }
  return out;
}

export class LineChart {
  private series: ChartSeries[] = [];
  private times: number[] = []; // union of all periods, sorted
  private hoverIdx: number | null = null;
  private digits = 0;
  private unit = "";
  private layout = { left: 0, right: 0, top: 12, bottom: 28, width: 0, height: 0 };
  private x = (t: number) => t;
  private y = (v: number) => v;

  private canvas: HTMLCanvasElement;
  private tooltip: HTMLElement;

  constructor(canvas: HTMLCanvasElement, tooltip: HTMLElement) {
    this.canvas = canvas;
    this.tooltip = tooltip;
    canvas.addEventListener("pointermove", (e) => this.hoverAt(e.offsetX));
    canvas.addEventListener("pointerleave", () => this.setHover(null));
    canvas.addEventListener("keydown", (e) => this.onKey(e));
    canvas.addEventListener("blur", () => this.setHover(null));
    new ResizeObserver(() => this.draw()).observe(canvas.parentElement!);
  }

  setData(series: ChartSeries[], unit: string): void {
    this.series = series;
    this.unit = unit;
    this.digits = decimalsOf(series);
    this.times = [...new Set(series.flatMap((s) => s.points.map((p) => p.t)))].sort((a, b) => a - b);
    this.hoverIdx = null;
    this.draw();
  }

  draw(): void {
    const { canvas } = this;
    const dpr = window.devicePixelRatio || 1;
    const width = canvas.parentElement!.clientWidth;
    const height = Math.max(220, Math.min(360, Math.round(width * 0.5)));
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    const ctx = canvas.getContext("2d")!;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);

    const values = this.series.flatMap((s) => s.points.map((p) => p.value)).filter((v): v is number => v !== null);
    if (!values.length || !this.times.length) return;

    const text2 = cssVar(canvas, "--viz-text-secondary", "#52514e");
    const text1 = cssVar(canvas, "--viz-text-primary", "#0b0b0b");
    const grid = cssVar(canvas, "--viz-grid", "#e6e5e1");
    const surface = cssVar(canvas, "--viz-surface", "#fcfcfb");
    const font = cssVar(canvas, "--font-sans", "system-ui, sans-serif");
    ctx.font = `12px ${font}`;

    const yTicks = niceTicks(Math.min(...values), Math.max(...values));
    const yLabels = yTicks.map((v) => formatValue(v, this.digits && Math.max(0, this.digits - 1)));
    const direct = this.series.length >= 2 && this.series.length <= DIRECT_LABEL_MAX;
    const L = this.layout;
    L.width = width;
    L.height = height;
    L.left = Math.ceil(Math.max(...yLabels.map((s) => ctx.measureText(s).width))) + 12;
    L.right = direct
      ? Math.min(160, Math.ceil(Math.max(...this.series.map((s) => ctx.measureText(s.label).width))) + 26)
      : 12;

    const t0 = this.times[0];
    const t1 = this.times[this.times.length - 1];
    const plotW = width - L.left - L.right;
    const plotH = height - L.top - L.bottom;
    const [v0, v1] = [yTicks[0], yTicks[yTicks.length - 1]];
    this.x = (t) => L.left + (t1 === t0 ? plotW / 2 : ((t - t0) / (t1 - t0)) * plotW);
    this.y = (v) => L.top + plotH - ((v - v0) / (v1 - v0)) * plotH;

    // Grid + y labels
    ctx.textBaseline = "middle";
    ctx.textAlign = "right";
    ctx.lineWidth = 1;
    yTicks.forEach((v, i) => {
      const yy = Math.round(this.y(v)) + 0.5;
      ctx.strokeStyle = grid;
      ctx.beginPath();
      ctx.moveTo(L.left, yy);
      ctx.lineTo(L.left + plotW, yy);
      ctx.stroke();
      ctx.fillStyle = text2;
      ctx.fillText(yLabels[i], L.left - 8, yy);
    });

    // X labels
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillStyle = text2;
    const xt = this.times.length === 1 ? [{ t: t0, label: this.series[0].points[0].period }] : timeTicks(t0, t1);
    for (const tick of xt) {
      // Keep edge labels inside the canvas
      const half = ctx.measureText(tick.label).width / 2;
      const xx = Math.min(Math.max(this.x(tick.t), half + 1), width - half - 1);
      ctx.fillText(tick.label, xx, L.top + plotH + 8);
    }

    // Lines (gaps at missing values)
    const markers = this.times.length <= 12;
    for (const s of this.series) {
      ctx.strokeStyle = s.color;
      ctx.lineWidth = 2;
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      ctx.beginPath();
      let open = false;
      for (const p of s.points) {
        if (p.value === null) {
          open = false;
          continue;
        }
        const [px, py] = [this.x(p.t), this.y(p.value)];
        if (open) ctx.lineTo(px, py);
        else ctx.moveTo(px, py);
        open = true;
      }
      ctx.stroke();
      if (markers || s.points.filter((p) => p.value !== null).length === 1)
        for (const p of s.points) if (p.value !== null) this.dot(ctx, this.x(p.t), this.y(p.value), s.color, surface);
    }

    if (direct) this.drawDirectLabels(ctx, text1, plotW);

    // Crosshair
    if (this.hoverIdx !== null) {
      const t = this.times[this.hoverIdx];
      const xx = Math.round(this.x(t)) + 0.5;
      ctx.strokeStyle = text2;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(xx, L.top);
      ctx.lineTo(xx, L.top + plotH);
      ctx.stroke();
      for (const s of this.series) {
        const p = s.points.find((q) => q.t === t);
        if (p && p.value !== null) this.dot(ctx, xx, this.y(p.value), s.color, surface);
      }
    }
  }

  private dot(ctx: CanvasRenderingContext2D, x: number, y: number, color: string, ring: string): void {
    ctx.beginPath();
    ctx.arc(x, y, 5, 0, Math.PI * 2); // 8px mark + 2px surface ring
    ctx.fillStyle = ring;
    ctx.fill();
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
  }

  private drawDirectLabels(ctx: CanvasRenderingContext2D, ink: string, plotW: number): void {
    const L = this.layout;
    const labels = this.series
      .map((s) => {
        const last = [...s.points].reverse().find((p) => p.value !== null);
        return last ? { s, y: this.y(last.value!) } : null;
      })
      .filter((v): v is { s: ChartSeries; y: number } => v !== null)
      .sort((a, b) => a.y - b.y);
    for (let i = 1; i < labels.length; i++) labels[i].y = Math.max(labels[i].y, labels[i - 1].y + 15); // de-collide
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    for (const { s, y } of labels) {
      const x0 = L.left + plotW + 6;
      ctx.fillStyle = s.color;
      ctx.fillRect(x0, y - 1, 10, 2);
      ctx.fillStyle = ink;
      let text = s.label;
      while (text.length > 4 && ctx.measureText(text).width > L.right - 20) text = text.slice(0, -2) + "…";
      ctx.fillText(text, x0 + 14, y);
    }
  }

  private hoverAt(px: number): void {
    if (!this.times.length) return;
    let best = 0;
    for (let i = 1; i < this.times.length; i++)
      if (Math.abs(this.x(this.times[i]) - px) < Math.abs(this.x(this.times[best]) - px)) best = i;
    this.setHover(best);
  }

  private onKey(e: KeyboardEvent): void {
    if (!this.times.length) return;
    const last = this.times.length - 1;
    if (e.key === "ArrowRight") this.setHover(this.hoverIdx === null ? last : Math.min(last, this.hoverIdx + 1));
    else if (e.key === "ArrowLeft") this.setHover(this.hoverIdx === null ? last : Math.max(0, this.hoverIdx - 1));
    else if (e.key === "Home") this.setHover(0);
    else if (e.key === "End") this.setHover(last);
    else if (e.key === "Escape") this.setHover(null);
    else return;
    e.preventDefault();
  }

  private setHover(idx: number | null): void {
    this.hoverIdx = idx;
    this.draw();
    this.renderTooltip();
  }

  private renderTooltip(): void {
    const tip = this.tooltip;
    if (this.hoverIdx === null) {
      tip.hidden = true;
      return;
    }
    const t = this.times[this.hoverIdx];
    tip.replaceChildren();
    const head = document.createElement("div");
    head.className = "tip-head";
    head.textContent = this.series.flatMap((s) => s.points).find((p) => p.t === t)?.period ?? "";
    tip.append(head);
    const rows = this.series
      .map((s) => ({ s, p: s.points.find((q) => q.t === t) }))
      .sort((a, b) => (b.p?.value ?? -Infinity) - (a.p?.value ?? -Infinity));
    for (const { s, p } of rows) {
      const row = document.createElement("div");
      row.className = "tip-row";
      const sw = document.createElement("span");
      sw.className = "swatch";
      sw.style.background = s.color;
      const name = document.createElement("span");
      name.className = "tip-name";
      name.textContent = s.label;
      const val = document.createElement("span");
      val.className = "tip-value";
      val.textContent = formatValue(p?.value ?? null, this.digits) + (this.unit && p?.value != null ? ` ${this.unit}` : "");
      row.append(sw, name, val);
      tip.append(row);
    }
    tip.hidden = false;
    const xx = this.x(t);
    const w = tip.offsetWidth;
    tip.style.left = `${xx + 12 + w > this.layout.width ? Math.max(0, xx - 12 - w) : xx + 12}px`;
    tip.style.top = `${this.layout.top}px`;
  }
}
