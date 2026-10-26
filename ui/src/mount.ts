// Mounts a model-written view into the canvas: raw HTML/JS, or a Vega-Lite spec.

import { prepareVegaLite, type Dataset } from "./data";

/**
 * Insert model-written HTML and run its scripts in document order.
 *
 * Scripts parsed by DOMParser never execute, so each one is re-created. External classic
 * scripts are awaited before the next script runs, so `<script src=d3>` then an inline
 * script that uses d3 works as it would in a normal page. <style>/<link> in a <head>
 * go to the document head.
 */
export async function mountHtml(root: HTMLElement, html: string): Promise<void> {
  const doc = new DOMParser().parseFromString(html, "text/html");

  for (const el of [...doc.head.children]) {
    if (el.tagName === "TITLE" || el.tagName === "META" || el.tagName === "BASE") continue;
    if (el.tagName === "SCRIPT") doc.body.prepend(el); // run head scripts first, in order
    else document.head.append(document.adoptNode(el));
  }

  const placeholders: [Comment, HTMLScriptElement][] = [];
  for (const script of [...doc.body.querySelectorAll("script")]) {
    const mark = doc.createComment("script");
    script.replaceWith(mark);
    placeholders.push([mark, script]);
  }
  root.replaceChildren(...[...doc.body.childNodes].map((n) => document.adoptNode(n)));

  for (const [mark, original] of placeholders) {
    const script = document.createElement("script");
    for (const { name, value } of original.attributes) script.setAttribute(name, value);
    script.textContent = original.textContent;
    const blocking = original.src && original.type !== "module" && !original.async && !original.defer;
    const loaded = blocking
      ? new Promise<void>((resolve) => {
          script.addEventListener("load", () => resolve(), { once: true });
          script.addEventListener(
            "error",
            () => {
              reportError(`Failed to load script ${original.src} (allowed CDNs: cdn.jsdelivr.net, cdnjs.cloudflare.com, unpkg.com, esm.sh)`);
              resolve();
            },
            { once: true },
          );
        })
      : null;
    mark.replaceWith(script);
    if (loaded) await loaded;
  }
}

// Pinned, CSP-safe: Vega's expression interpreter avoids eval, which MCP Apps hosts block.
const VEGA_EMBED = "https://cdn.jsdelivr.net/npm/vega-embed@7.3.0/+esm";
const VEGA_INTERPRETER = "https://cdn.jsdelivr.net/npm/vega-interpreter@2.3.2/+esm";

let vegaView: { finalize(): void } | null = null;

export async function mountVegaLite(
  root: HTMLElement,
  spec: Record<string, unknown>,
  datasets: Record<string, Dataset>,
  opts: { dark: boolean; palette: string[]; font: string; text: string; muted: string; grid: string },
): Promise<void> {
  const [{ default: embed }, { expressionInterpreter }] = await Promise.all([
    import(/* @vite-ignore */ VEGA_EMBED),
    import(/* @vite-ignore */ VEGA_INTERPRETER),
  ]);
  vegaView?.finalize();
  const el = document.createElement("div");
  el.className = "sc-vega";
  root.replaceChildren(el);
  const result = await embed(el, prepareVegaLite(spec, datasets), {
    ast: true,
    expr: expressionInterpreter,
    renderer: "svg",
    actions: { export: true, source: false, compiled: false, editor: false },
    config: {
      font: opts.font,
      range: { category: opts.palette },
      axis: { labelColor: opts.muted, titleColor: opts.text, gridColor: opts.grid, domainColor: opts.grid, tickColor: opts.grid },
      legend: { labelColor: opts.text, titleColor: opts.text },
      title: { color: opts.text, subtitleColor: opts.muted },
      view: { stroke: null },
    },
  });
  vegaView = result;
}

type ErrorSink = (message: string) => void;
let sink: ErrorSink = (m) => console.error(m);
export function onMountError(fn: ErrorSink): void {
  sink = fn;
}
function reportError(message: string): void {
  sink(message);
}
