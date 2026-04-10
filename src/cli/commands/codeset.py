"""statcan codeset — show StatCan code definitions (UOM, frequency, scalar, status)."""

import asyncio
import json
from typing import Any, Dict, List, Optional

import httpx
import typer

from ...api.client import make_get_request
from ..output import err_console, write_output


def codeset(
    type_filter: Optional[str] = typer.Option(
        None, "--type", "-t", help="Filter to one codeset: uom, frequency, scalar, status"
    ),
    fmt: str = typer.Option("table", "--format", "-f", help="Output format: table, csv, json"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Write to file"),
) -> None:
    """Show StatCan code definitions (UOM, frequency, scalar, status).

    Examples:\n
      statcan codeset\n
      statcan codeset --type uom\n
      statcan codeset --type frequency --format json
    """
    try:
        asyncio.run(_codeset(type_filter, fmt, output))
    except httpx.HTTPStatusError as e:
        err_console.print(f"[red]Error: API returned {e.response.status_code}[/red]")
        raise typer.Exit(2)
    except httpx.RequestError:
        err_console.print("[red]Error: Could not reach Statistics Canada API[/red]")
        raise typer.Exit(2)
    except ValueError as e:
        err_console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


async def _codeset(type_filter: Optional[str], fmt: str, output: Optional[str]) -> None:
    with err_console.status("[bold green]Fetching code sets from Statistics Canada..."):
        result = await make_get_request("/getCodeSets")

    if result.get("status") != "SUCCESS":
        raise ValueError(f"API error: {result.get('object', 'Unknown error')}")

    code_sets: Dict[str, Any] = result.get("object", {})

    if type_filter:
        key = next((k for k in code_sets if k.lower() == type_filter.lower()), None)
        if key is None:
            available = ", ".join(str(k) for k in code_sets.keys())
            err_console.print(
                f"[red]Error: Unknown codeset '{type_filter}'. "
                f"Available: {available}[/red]"
            )
            raise typer.Exit(1)
        code_sets = {key: code_sets[key]}

    if fmt == "json":
        content = json.dumps(code_sets, indent=2, default=str)
        if output:
            with open(output, "w") as f:
                f.write(content)
            err_console.print(f"[green]✓ Written to {output}[/green]")
        else:
            print(content)
        return

    # Table/CSV display — render each codeset as its own table
    for cs_name, cs_data in code_sets.items():
        rows = _codeset_to_rows(cs_data)
        write_output(rows, fmt, output, title=cs_name, filter_internal=False)


def _codeset_to_rows(data: Any) -> List[Dict[str, Any]]:
    """Convert a codeset value (list or dict) to a list of row dicts."""
    if isinstance(data, list):
        rows = []
        for item in data:
            if isinstance(item, dict):
                rows.append({k: str(v) for k, v in item.items()})
            else:
                rows.append({"value": str(item)})
        return rows
    if isinstance(data, dict):
        return [{"key": str(k), "value": str(v)} for k, v in data.items()]
    return [{"value": str(data)}]
