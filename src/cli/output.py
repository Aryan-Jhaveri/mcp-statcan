"""Shared output helpers for the statcan CLI."""

import csv
import io
import json
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table

console = Console()
err_console = Console(stderr=True)

_FREQ_MAP = {
    1: "Annual",
    2: "Semi-annual",
    4: "Quarterly",
    12: "Monthly",
    52: "Weekly",
    365: "Daily",
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


def rows_to_csv(rows: List[Dict[str, Any]]) -> str:
    """Convert a list of row dicts to a CSV string."""
    if not rows:
        return ""
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def write_output(
    rows: List[Dict[str, Any]],
    fmt: str,
    output_path: Optional[str],
    title: str = "",
    filter_internal: bool = True,
) -> None:
    """Render rows in the requested format and write to file or stdout.

    Data goes to stdout (or --output file).
    Progress/confirmation messages go to stderr via err_console.
    """
    if filter_internal:
        rows = _filter_internal(rows)

    if fmt == "json":
        content = json.dumps(rows, indent=2, default=str)
        if output_path:
            with open(output_path, "w") as f:
                f.write(content)
            err_console.print(f"[green]✓ Wrote {len(rows):,} rows to {output_path}[/green]")
        else:
            print(content)

    elif fmt == "csv":
        content = rows_to_csv(rows)
        if output_path:
            with open(output_path, "w") as f:
                f.write(content)
            err_console.print(f"[green]✓ Wrote {len(rows):,} rows to {output_path}[/green]")
        else:
            # end="" because rows_to_csv already includes a trailing newline
            print(content, end="")

    else:  # table
        if not rows:
            err_console.print("[yellow]No data to display[/yellow]")
            return
        table = Table(title=title, show_header=True, header_style="bold cyan")
        for col in rows[0]:
            table.add_column(str(col), overflow="fold")
        for row in rows:
            table.add_row(*[str(v) if v is not None else "" for v in row.values()])
        if output_path:
            # When --output is given with table format, write CSV to file
            content = rows_to_csv(rows)
            with open(output_path, "w") as f:
                f.write(content)
            err_console.print(f"[green]✓ Wrote {len(rows):,} rows to {output_path}[/green]")
        else:
            console.print(table)
