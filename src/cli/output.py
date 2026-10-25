"""Shared output helpers for the statcan CLI."""

import csv
import io
import json
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table

console = Console()
err_console = Console(stderr=True)

_FORMATS = ("csv", "json", "ndjson", "table")

# StatCan WDS frequencyCode values (from getCodeSets → frequency). These are
# StatCan's own codes, not periods per year: 12 = Annual, 6 = Monthly.
_FREQ_MAP = {
    1: "Daily",
    2: "Weekly",
    4: "Biweekly",
    6: "Monthly",
    7: "Bimonthly",
    9: "Quarterly",
    11: "Semi-annual",
    12: "Annual",
    13: "Every 2 years",
    14: "Every 3 years",
    15: "Every 4 years",
    16: "Every 5 years",
    17: "Every 10 years",
    18: "Occasional",
    19: "Occasional Quarterly",
    20: "Occasional Monthly",
    21: "Occasional Daily",
}


def freq_label(code: Any) -> str:
    """Return a human-readable frequency label from a numeric frequency code."""
    try:
        return _FREQ_MAP.get(int(code), str(code))
    except (TypeError, ValueError):
        return str(code) if code is not None else ""


def format_date(date_str: Any) -> str:
    """Strip the ISO8601 time/timezone component, preserving the full date portion.

    The date precision is kept as returned by the API so that daily, hourly,
    or sub-daily tables are not inadvertently truncated:

      '1914-01-01T05:00:00Z' → '1914-01-01'
      '2024-01-15T12:30:00Z' → '2024-01-15'
      '2024-01'              → '2024-01'      (already period format)
      '2024'                 → '2024'          (annual)
    """
    if not date_str:
        return ""
    s = str(date_str)
    if "T" in s:
        s = s.split("T")[0]
    return s


def normalize_product_id(product_id: str) -> int:
    """Accept '18-10-0004-01' or '18100004', return the 8-digit base product ID as int.

    StatCan product IDs follow the format AA-BB-CCCC (8 digits) with an optional
    -DD revision suffix (e.g. 18-10-0004-01). The revision suffix is stripped.
    """
    normalized = product_id.replace("-", "")
    try:
        _ = int(normalized)
    except ValueError:
        raise ValueError(
            f"'{product_id}' is not a valid product ID. "
            "Expected format: 18-10-0004-01 or 18100004"
        )
    # 10-digit strings include the 2-digit revision suffix — keep only the 8-digit base
    if len(normalized) == 10:
        normalized = normalized[:8]
    return int(normalized)


def normalize_vector_id(vector_id: str) -> str:
    """Strip 'v'/'V' prefix, return bare numeric string."""
    vid = vector_id.strip()
    if vid.lower().startswith("v"):
        vid = vid[1:]
    try:
        int(vid)
        return vid
    except ValueError:
        raise ValueError(
            f"'{vector_id}' is not a valid vector ID. "
            "Expected format: v41690973 or 41690973"
        )


def _filter_internal(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove columns starting with '_' (internal metadata)."""
    if not rows:
        return rows
    internal = {k for k in rows[0] if k.startswith("_")}
    if not internal:
        return rows
    return [{k: v for k, v in r.items() if k not in internal} for r in rows]


def all_columns(rows: List[Dict[str, Any]]) -> List[str]:
    """Union of keys across rows, in first-seen order (SDMX attributes vary per row)."""
    seen: Dict[str, None] = {}
    for row in rows:
        for k in row:
            seen.setdefault(k, None)
    return list(seen)


def rows_to_csv(rows: List[Dict[str, Any]]) -> str:
    """Convert a list of row dicts to a CSV string."""
    if not rows:
        return ""
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=all_columns(rows), restval="")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def summarize_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Shape of an observation result: period range and series count, when present."""
    summary: Dict[str, Any] = {}
    periods = [r["period"] for r in rows if r.get("period")]
    if periods:
        summary["period_range"] = [min(periods), max(periods)]
    # Count series by the (corrected) series key: StatCan's VECTOR_ID attribute
    # indices are unreliable in multi-series SDMX-JSON responses.
    series = {r.get("_series_key") for r in rows if r.get("_series_key") is not None}
    if series:
        summary["series_count"] = len(series)
    return summary


def _write_file(path: str, content: str) -> None:
    with open(path, "w") as f:
        f.write(content)


def _render(rows: List[Dict[str, Any]], fmt: str) -> str:
    if fmt == "json":
        return json.dumps(rows, indent=2, default=str, ensure_ascii=False)
    if fmt == "ndjson":
        return "".join(json.dumps(r, default=str, ensure_ascii=False) + "\n" for r in rows)
    return rows_to_csv(rows)  # csv, and table when written to a file


def write_output(
    rows: List[Dict[str, Any]],
    fmt: str,
    output_path: Optional[str],
    title: str = "",
    filter_internal: bool = True,
    command: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Render rows in the requested format and write to file or stdout.

    Data goes to stdout (or --output file).
    Progress/confirmation messages go to stderr via err_console.

    In JSON mode (--json / STATCAN_OUTPUT=json) stdout gets a single envelope instead:
    {"ok": true, "command", "rows", "columns", ...extra} plus "data" (inline) or
    "path" (when --output is given; the file is still written in --format).
    """
    from .contract import emit_success, state

    if fmt not in _FORMATS:
        raise ValueError(f"Unknown format '{fmt}'. Use one of: {', '.join(_FORMATS)}")
    if filter_internal:
        rows = _filter_internal(rows)
    columns = all_columns(rows)

    if state.json_mode:
        fields: Dict[str, Any] = {"rows": len(rows), "columns": columns, **(extra or {})}
        if output_path:
            file_fmt = "csv" if fmt == "table" else fmt
            _write_file(output_path, _render(rows, file_fmt))
            emit_success(command, path=output_path, format=file_fmt, **fields)
        else:
            emit_success(command, **fields, data=rows)
        return

    if fmt == "table" and not output_path:
        if not rows:
            err_console.print("[yellow]No data to display[/yellow]")
            return
        table = Table(title=title, show_header=True, header_style="bold cyan")
        for col in columns:
            table.add_column(str(col), overflow="fold")
        for row in rows:
            table.add_row(*[str(row[c]) if row.get(c) is not None else "" for c in columns])
        console.print(table)
        return

    # When --output is given with table format, write CSV to file
    content = _render(rows, "csv" if fmt == "table" else fmt)
    if output_path:
        _write_file(output_path, content)
        err_console.print(f"[green]✓ Wrote {len(rows):,} rows to {output_path}[/green]")
    elif fmt == "json":
        print(content)
    else:
        # end="" because csv/ndjson content already ends with a newline
        print(content, end="")
