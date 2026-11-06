"""Compact CSV renderings of SDMX rows, for agents that save data to a file (#168).

On claude.ai the code sandbox can't reach StatCan, so an agent building a file copies
the tool result by hand. The layout is chosen to make that copy short:

- Fields with the same value in every row are written once, as "# field: value" lines.
- One row per series, one column per period. A long layout (one line per observation)
  repeats each series' labels on every line and measured *larger* than the grouped JSON.
- Observation-level attributes (e.g. a STATUS flag on one value) become
  "# field <series key> <period>: value" lines, since a wide row has no cell for them.
"""

import csv
import io
from typing import Any, Dict, Iterable, List, Tuple

# Per-geography ids: long and rarely what the agent needs (also dropped from summaries)
_DROP = ("DGUID",)
_MISSING = object()


def format_value(value: Any) -> str:
    """Cell text: '' for missing, integers without '.0', floats without binary noise.
    Values still in StatCan's own text form pass through unchanged."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.10g}"
    return str(value)


def _writer(out: io.StringIO):
    return csv.writer(out, lineterminator="\n")


def series_csv(rows: List[Dict[str, Any]]) -> Tuple[str, int]:
    """Flat SDMX rows → (csv text, number of series), wide by period."""
    if not rows:
        return "", 0
    fields: List[str] = []
    for row in rows:
        for k in row:
            if k not in fields and k not in ("period", "value") and k not in _DROP:
                fields.append(k)

    first = rows[0]
    common = {k: first.get(k) for k in fields if all(r.get(k, _MISSING) == first.get(k, _MISSING) for r in rows)}

    by_key: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        by_key.setdefault(row.get("_series_key", ""), []).append(row)

    # Fields constant within every series become columns; the rest are per-observation notes
    varying = [k for k in fields if k not in common]
    columns = [
        k for k in varying
        if all(all(r.get(k, _MISSING) == s[0].get(k, _MISSING) for r in s) for s in by_key.values())
    ]
    obs_level = [k for k in varying if k not in columns]

    periods = sorted({r.get("period") for r in rows if r.get("period") is not None})

    out = io.StringIO()
    for k, v in common.items():
        out.write(f"# {k}: {format_value(v)}\n")
    for series_key, series_rows in by_key.items():
        for r in series_rows:
            for k in obs_level:
                if r.get(k) is not None:
                    out.write(f"# {k} {series_key} {r.get('period')}: {format_value(r.get(k))}\n")

    w = _writer(out)
    w.writerow(columns + periods)
    for series_rows in by_key.values():
        values = {r.get("period"): format_value(r.get("value")) for r in series_rows}
        w.writerow([format_value(series_rows[0].get(k)) for k in columns] + [values.get(p, "") for p in periods])
    return out.getvalue(), len(by_key)


def table_csv(columns: List[str], rows: Iterable[Dict[str, Any]]) -> str:
    """Query result rows → csv text with a header row."""
    out = io.StringIO()
    w = _writer(out)
    w.writerow(columns)
    for row in rows:
        w.writerow([format_value(row.get(c)) for c in columns])
    return out.getvalue()
