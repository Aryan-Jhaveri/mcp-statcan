"""statcan codeset — show StatCan code definitions (UOM, frequency, scalar, status)."""

import asyncio
import json
from typing import Any, Dict, List, Optional

import typer

from ...api.client import make_get_request
from ..contract import CLIError, ExitCode, emit_success, handle_errors, state
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
    with handle_errors(what="Code sets"):
        asyncio.run(_codeset(type_filter, fmt, output))


async def _codeset(type_filter: Optional[str], fmt: str, output: Optional[str]) -> None:
    with err_console.status("[bold green]Fetching code sets from Statistics Canada..."):
        result = await make_get_request("/getCodeSets")

    if result.get("status") != "SUCCESS":
        raise CLIError(ExitCode.UPSTREAM_REJECTED, f"StatCan API error: {result.get('object', 'Unknown error')}")

    code_sets: Dict[str, Any] = result.get("object", {})

    if type_filter:
        key = next((k for k in code_sets if k.lower() == type_filter.lower()), None)
        if key is None:
            available = ", ".join(str(k) for k in code_sets.keys())
            raise CLIError(ExitCode.NOT_FOUND, f"Unknown codeset '{type_filter}'.", f"Available: {available}")
        code_sets = {key: code_sets[key]}

    if state.json_mode:
        if output:
            with open(output, "w") as f:
                f.write(json.dumps(code_sets, indent=2, default=str, ensure_ascii=False))
            emit_success("codeset", path=output, codesets=list(code_sets))
        else:
            emit_success("codeset", codesets=list(code_sets), data=code_sets)
        return

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
