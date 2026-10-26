"""MCP Apps views (extension io.modelcontextprotocol/ui).

Tools that carry `_meta.ui.resourceUri` are rendered by Apps-capable hosts (Claude,
ChatGPT, VS Code, Goose, ...) with an interactive `ui://` view: a sandboxed,
self-contained HTML document built from `ui/` (TypeScript, @modelcontextprotocol/ext-apps)
into `src/ui_views/`.

Why it matters for context: the full result goes to the view as `structuredContent`,
which hosts keep out of the model's context. When the client negotiated Apps, a tool's
text content can be a compact summary instead of every row (see `summarize_rows_result`);
clients without Apps keep receiving the full rows as text.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.apps import APP_MIME_TYPE, EXTENSION_ID, client_supports_apps  # noqa: F401 (re-exported)
from mcp.types import Resource

SERIES_VIEW_URI = "ui://statcan/series-view.html"

_VIEWS_DIR = Path(__file__).resolve().parent.parent / "ui_views"
_VIEWS: Dict[str, Dict[str, str]] = {
    SERIES_VIEW_URI: {
        "file": "series-view.html",
        "name": "StatCan series view",
        "description": "Interactive line chart and table for StatCan observations, with CSV download.",
    },
}
# The view needs no network access (everything is inlined), so no CSP domains are declared.
_RESOURCE_META = {"ui": {"prefersBorder": True}}

MAX_SUMMARY_SERIES = 40


def ui_meta(uri: str) -> Dict[str, Any]:
    """Tool `_meta` linking a tool to a view (plus the deprecated flat key for older hosts)."""
    return {"ui": {"resourceUri": uri}, "ui/resourceUri": uri}


def list_view_resources() -> List[Resource]:
    return [
        Resource(uri=uri, name=v["name"], description=v["description"], mime_type=APP_MIME_TYPE, meta=_RESOURCE_META)
        for uri, v in _VIEWS.items()
    ]


@lru_cache(maxsize=None)
def read_view(uri: str) -> Optional[str]:
    """The view's HTML, or None for an unknown URI."""
    view = _VIEWS.get(uri)
    if view is None:
        return None
    return (_VIEWS_DIR / view["file"]).read_text(encoding="utf-8")


def resource_meta() -> Dict[str, Any]:
    return _RESOURCE_META


def _num(v: Any) -> Optional[float]:
    try:
        return None if v is None or v == "" else float(v)
    except (TypeError, ValueError):
        return None


def summarize_rows_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Compact, model-facing summary of a get_sdmx_data / get_sdmx_vector_data result.

    Per series: label, observation count, first/last/min/max. The full rows are in
    structuredContent, rendered for the user by the series view.
    """
    rows: List[Dict[str, Any]] = result.get("data") or []
    keys = list(rows[0]) if rows else []
    dims = keys[: keys.index("_series_key")] if "_series_key" in keys else []
    varying = [d for d in dims if len({str(r.get(d)) for r in rows}) > 1]
    shared = {d: rows[0].get(d) for d in dims if d not in varying} if rows else {}

    series: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        sid = str(r.get("_series_key", ""))
        s = series.setdefault(sid, {
            "series_key": sid,
            "label": " · ".join(str(r.get(d)) for d in varying) or None,
            "points": [],
        })
        s["points"].append((r.get("period"), _num(r.get("value"))))

    out = []
    for s in series.values():
        pts = sorted(p for p in s["points"] if p[0] is not None)
        vals = [(p, v) for p, v in pts if v is not None]
        entry: Dict[str, Any] = {"series_key": s["series_key"], "observations": len(pts)}
        if s["label"]:
            entry["label"] = s["label"]
        if vals:
            lo = min(vals, key=lambda x: x[1])
            hi = max(vals, key=lambda x: x[1])
            entry.update({
                "first": {"period": vals[0][0], "value": vals[0][1]},
                "last": {"period": vals[-1][0], "value": vals[-1][1]},
                "min": {"period": lo[0], "value": lo[1]},
                "max": {"period": hi[0], "value": hi[1]},
            })
        out.append(entry)

    periods = sorted(r["period"] for r in rows if r.get("period"))
    summary: Dict[str, Any] = {
        "_sdmx_url": result.get("_sdmx_url"),
        "row_count": result.get("row_count", len(rows)),
        "series_count": len(out),
        "period_range": [periods[0], periods[-1]] if periods else None,
        "shared_dimensions": shared,
        "series": out[:MAX_SUMMARY_SERIES],
        "_note": (
            "The full rows are shown to the user in an interactive chart and table (with CSV download). "
            "This summary is what you see. For exact values or calculations use query_sdmx; "
            "for raw rows in your context use get_sdmx_rows."
        ),
    }
    if len(out) > MAX_SUMMARY_SERIES:
        summary["_series_truncated"] = f"First {MAX_SUMMARY_SERIES} of {len(out)} series listed."
    if result.get("_truncated"):
        summary["_truncated"] = True
        summary["_message"] = result.get("_message")
    return summary
