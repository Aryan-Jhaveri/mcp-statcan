"""Agent canvas: `render_view` lets the model build its own UI over StatCan data.

The model writes the view (any HTML/JS, or a Vega-Lite spec) and names its datasets;
the server fetches those datasets and binds them into the page as `statcan.data`, so
rows never have to pass through the model's context to be drawn.

One renderer (`ui://statcan/canvas.html`, built from `ui/`) serves two surfaces:
  - MCP Apps hosts render it inline; the full payload goes to the view as
    structuredContent and the model gets a short summary.
  - Every client also gets a standalone link: a page on the hosted server
    (`/views/<id>`, in memory, ~1 hour) or a local HTML file in stdio mode.
"""

import asyncio
import json
import os
import re
import secrets
import time
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mcp.server.apps import APP_MIME_TYPE, EXTENSION_ID, client_supports_apps  # noqa: F401 (re-exported)
from mcp.types import Resource, ToolAnnotations

from .. import config
from ..db.ephemeral import run_ephemeral_query
from ..models.canvas_models import RenderViewInput, RenderViewOutput, ViewDataSource
from ..util.registry import ToolRegistry
from ..util.sql_helpers import to_number
from .sdmx.sdmx_tools import _query_slots, fetch_sdmx_rows, fetch_sdmx_vector_rows

CANVAS_URI = "ui://statcan/canvas.html"
_VIEW_FILE = Path(__file__).resolve().parent.parent / "ui_views" / "canvas.html"

# CDNs a view may load libraries from (declared as the resource CSP for MCP Apps hosts)
CDN_DOMAINS = [
    "https://cdn.jsdelivr.net",
    "https://cdnjs.cloudflare.com",
    "https://unpkg.com",
    "https://esm.sh",
]
_RESOURCE_META = {"ui": {"csp": {"resourceDomains": CDN_DOMAINS, "connectDomains": CDN_DOMAINS}}}

MAX_SOURCES = 8
MAX_VIEW_ROWS = 5_000  # per dataset, after any SQL
MAX_INLINE_ROWS = 2_000
MAX_BODY_CHARS = 300_000  # html or serialized vega_lite spec
SAMPLE_ROWS = 3

VIEW_TTL_SECONDS = 3_600
MAX_STORED_VIEWS = 200
MAX_STORED_BYTES = 64 * 1024 * 1024

_PERIOD_RE = re.compile(r"^(\d{4})(?:-(?:(\d{2})(?:-(\d{2}))?|Q([1-4])|S([12])))?$")


def period_to_date(period: Any) -> Optional[str]:
    """ISO date for the start of a StatCan period ("2024" → "2024-01-01", "2024-Q2" → "2024-04-01")."""
    m = _PERIOD_RE.match(str(period or ""))
    if not m:
        return None
    year, month, day, quarter, half = m.groups()
    if quarter:
        month = f"{(int(quarter) - 1) * 3 + 1:02d}"
    elif half:
        month = "01" if half == "1" else "07"
    return f"{year}-{month or '01'}-{day or '01'}"


def _prepare_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Numeric `value` and a parsed `date` column, so views can plot without parsing periods."""
    for row in rows:
        if "value" in row:
            row["value"] = to_number(row["value"])
        if "period" in row and "date" not in row:
            row["date"] = period_to_date(row["period"])
    return rows


def _columns(rows: List[Dict[str, Any]]) -> List[str]:
    cols: Dict[str, None] = {}
    for row in rows[:50]:
        cols.update(dict.fromkeys(row))
    return list(cols)


async def _resolve_source(name: str, src: ViewDataSource) -> Dict[str, Any]:
    source_url: Optional[str] = None
    if src.rows is not None:
        if len(src.rows) > MAX_INLINE_ROWS:
            raise ValueError(f"data.{name}: {len(src.rows):,} inline rows; the limit is {MAX_INLINE_ROWS:,}.")
        rows = [dict(r) for r in src.rows]
    else:
        if src.vectorId is not None:
            rows, source_url = await fetch_sdmx_vector_rows(
                src.vectorId, src.lastNObservations, src.startPeriod, src.endPeriod
            )
        else:
            rows, source_url = await fetch_sdmx_rows(
                src.productId, src.key, src.lastNObservations, src.startPeriod, src.endPeriod
            )
        if not rows:
            raise ValueError(f"data.{name}: StatCan returned no observations ({source_url}). Check the key and period range.")
        if src.sql:
            if len(rows) > config.MAX_EPHEMERAL_ROWS:
                raise ValueError(f"data.{name}: {len(rows):,} rows fetched, above the {config.MAX_EPHEMERAL_ROWS:,}-row SQL limit. Narrow the key or period.")
            for row in rows:
                row["value"] = to_number(row.get("value"))
            # One extra row so truncation is detectable
            async with _query_slots:
                result = await asyncio.to_thread(run_ephemeral_query, rows, src.sql, "data", MAX_VIEW_ROWS + 1)
            if "error" in result:
                cols = ", ".join(result.get("table_columns") or [])
                raise ValueError(f"data.{name}: SQL failed: {result['error']}" + (f" (columns: {cols})" if cols else ""))
            rows = result["rows"]
    rows = _prepare_rows(rows)
    return {
        "columns": _columns(rows),
        "rows": rows[:MAX_VIEW_ROWS],
        "row_count": len(rows),
        "truncated": len(rows) > MAX_VIEW_ROWS,
        "source_url": source_url,
    }


@lru_cache(maxsize=1)
def canvas_html() -> str:
    return _VIEW_FILE.read_text(encoding="utf-8")


def standalone_html(payload: Dict[str, Any]) -> str:
    """The canvas page with the payload embedded, for opening outside an MCP Apps host."""
    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False, default=str)
    data = data.replace("<", "\\u003c")  # can't close the script tag or open a comment
    tag = f'<script type="application/json" id="statcan-payload">{data}</script>'
    html = canvas_html()
    i = html.index("<head>") + len("<head>")
    return html[:i] + tag + html[i:]


class ViewStore:
    """In-memory, size-bounded store for hosted standalone views. Lost on restart."""

    def __init__(self, ttl: float = VIEW_TTL_SECONDS, max_views: int = MAX_STORED_VIEWS, max_bytes: int = MAX_STORED_BYTES):
        self._ttl, self._max_views, self._max_bytes = ttl, max_views, max_bytes
        self._views: "OrderedDict[str, Tuple[float, str]]" = OrderedDict()
        self._bytes = 0

    def put(self, view_id: str, html: str) -> None:
        self._views[view_id] = (time.monotonic(), html)
        self._bytes += len(html)
        self._evict()

    def get(self, view_id: str) -> Optional[str]:
        self._evict()
        entry = self._views.get(view_id)
        return entry[1] if entry else None

    def _evict(self) -> None:
        now = time.monotonic()
        while self._views:
            vid, (created, html) = next(iter(self._views.items()))
            if now - created > self._ttl or len(self._views) > self._max_views or self._bytes > self._max_bytes:
                del self._views[vid]
                self._bytes -= len(html)
            else:
                break


view_store = ViewStore()


def list_view_resources() -> List[Resource]:
    return [
        Resource(
            uri=CANVAS_URI,
            name="StatCan canvas",
            description="Renders views built by the model with render_view (HTML/JS or Vega-Lite over StatCan data).",
            mime_type=APP_MIME_TYPE,
            meta=_RESOURCE_META,
        )
    ]


def read_view(uri: str) -> Optional[str]:
    return canvas_html() if uri == CANVAS_URI else None


def resource_meta() -> Dict[str, Any]:
    return _RESOURCE_META


def summarize_view(result: Dict[str, Any]) -> Dict[str, Any]:
    """What the model sees: where the view is and the shape of each dataset, not every row."""
    return {
        "view_id": result["view_id"],
        "url": result.get("url"),
        "datasets": {
            name: {
                "row_count": ds["row_count"],
                **({"_truncated": f"First {len(ds['rows']):,} rows bound."} if ds["truncated"] else {}),
                "columns": ds["columns"],
                "sample": ds["rows"][:SAMPLE_ROWS],
                **({"_sdmx_url": ds["source_url"]} if ds.get("source_url") else {}),
            }
            for name, ds in result["datasets"].items()
        },
        "_note": (
            "Rendered inline where the client supports MCP Apps; otherwise give the user the url. "
            "Script errors in the view are reported back to you as model context: fix them and call "
            "render_view again. Cite the _sdmx_url sources in your reply."
        ),
    }


def _public_base_url() -> str:
    return os.environ.get("RENDER_BASE_URL", f"http://localhost:{config.PORT}").rstrip("/")


def register_canvas_tools(registry: ToolRegistry, http_mode: bool) -> None:
    """Register render_view. http_mode: hosted links (in-memory store) instead of local files."""

    @registry.tool(
        output_model=RenderViewOutput,
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
        meta={"ui": {"resourceUri": CANVAS_URI}, "ui/resourceUri": CANVAS_URI},
        model_text=summarize_view,
    )
    async def render_view(view_input: RenderViewInput) -> Dict[str, Any]:
        """
        Build your own interactive view of StatCan data — a chart, dashboard, map, table,
        explainer, anything — and show it to the user. You write the UI; the server fetches
        the data you name and binds it into the page, so rows don't need to pass through you.

        Shows inline in clients that support MCP Apps (Claude, ChatGPT, VS Code, Goose) and
        always returns a `url` (hosted page, ~1 hour; or a local file) for any client.

        Pass exactly one of:
          html: body content with <style> and <script>. Load any library from cdn.jsdelivr.net,
            cdnjs.cloudflare.com, unpkg.com or esm.sh (d3, Observable Plot, Plotly, Chart.js,
            Leaflet, ...). Pin versions, e.g. https://cdn.jsdelivr.net/npm/d3@7.9.0.
          vega_lite: a Vega-Lite v6 spec; reference datasets with "data": {"name": "<name>"}.

        data: named datasets. Each is productId + key, or vectorId (with startPeriod/endPeriod or
          lastNObservations, as in get_sdmx_data), optionally with `sql` run server-side over the
          fetched rows (table `data`, as in query_sdmx) to aggregate or reshape first; or `rows`
          you already have. Rows carry the dimension columns, period, value (number), a parsed
          ISO `date` (start of the period), UOM, SCALAR_FACTOR, STATUS, VECTOR_ID. Max 5,000
          rows per dataset: aggregate with sql for more.

        Inside the page, `window.statcan` gives you:
          statcan.data.<name>              rows (array of objects)
          statcan.datasets.<name>          {columns, row_count, truncated, source_url}
          await statcan.query({productId, key, sql, startPeriod?, endPeriod?, lastNObservations?})
                                           live SQL over StatCan data (e.g. on a dropdown change)
          await statcan.fetch({productId, key, ...} | {vectorId, ...})  raw rows (max 500)
          await statcan.call(toolName, args)  any tool on this server
          statcan.send(text)               post a message to the conversation as the user
          statcan.download(filename, text, mimeType?)   save a file (e.g. CSV)
          statcan.toCSV(rows)              CSV string
          statcan.theme ("light"|"dark"), statcan.onThemeChange(fn)
        CSS variables (follow the host theme): --sc-bg --sc-surface --sc-fg --sc-muted --sc-border
          --sc-accent --sc-font --sc-mono and a categorical palette --sc-series-1 … --sc-series-8
          (statcan.palette as an array). The page grows to fit your content.

        A small footer cites the data sources. Errors thrown by your scripts are shown in the
        view and sent back to you as model context.

        Make it good: pick the form that answers the question, label axes with units (UOM,
        SCALAR_FACTOR), title it with the finding, and keep it readable in light and dark.
        """
        if len(view_input.data) > MAX_SOURCES:
            return {"error": f"{len(view_input.data)} datasets; the limit is {MAX_SOURCES}."}
        body = view_input.html if view_input.html is not None else json.dumps(view_input.vega_lite)
        if len(body) > MAX_BODY_CHARS:
            return {"error": f"The view is {len(body):,} characters; the limit is {MAX_BODY_CHARS:,}. Load libraries from a CDN instead of inlining them."}

        names = list(view_input.data)
        try:
            resolved = await asyncio.gather(*(_resolve_source(n, view_input.data[n]) for n in names))
        except ValueError as e:
            return {"error": str(e)}

        view_id = secrets.token_urlsafe(9)
        result: Dict[str, Any] = {
            "view_id": view_id,
            "title": view_input.title,
            "url": None,
            **({"html": view_input.html} if view_input.html is not None else {"vega_lite": view_input.vega_lite}),
            "datasets": dict(zip(names, resolved)),
        }
        if http_mode:
            base = _public_base_url()
            result["mcp_endpoint"] = f"{base}/mcp"
            result["url"] = f"{base}/views/{view_id}"
            view_store.put(view_id, standalone_html(result))
        else:
            views_dir = Path(config.VIEWS_DIR)
            slug = re.sub(r"[^a-z0-9]+", "-", view_input.title.lower()).strip("-")[:48] or "view"
            path = views_dir / f"{slug}-{view_id}.html"
            html = standalone_html({**result, "url": path.as_uri()})
            await asyncio.to_thread(views_dir.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(path.write_text, html, "utf-8")
            result["url"] = path.as_uri()
        return result
