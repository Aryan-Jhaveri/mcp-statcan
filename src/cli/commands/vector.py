"""statcan vector — download observations for one or more vector IDs via SDMX."""

import asyncio
from typing import Any, Dict, List, Optional

import httpx
import typer
from rich.progress import Progress

from ...config import SDMX_BASE_URL, SDMX_JSON_ACCEPT, TIMEOUT_MEDIUM, VERIFY_SSL
from ...util.sdmx_json import flatten_sdmx_json
from ..output import err_console, normalize_vector_id, write_output


def vector(
    vector_ids: List[str] = typer.Argument(
        ..., help="Vector ID(s) — 'v' prefix optional (e.g. v41690973 or 41690973)"
    ),
    last: Optional[int] = typer.Option(
        None, "--last", "-n", help="Last N observations (mutually exclusive with --start/--end)"
    ),
    start: Optional[str] = typer.Option(None, "--start", help="Start period (e.g. 2020-01 or 2015)"),
    end: Optional[str] = typer.Option(None, "--end", help="End period (e.g. 2024-12)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Write to file"),
    fmt: str = typer.Option("csv", "--format", "-f", help="Output format: csv, json, table"),
) -> None:
    """Download time-series observations for one or more StatCan vector IDs.

    Multiple vector IDs are fetched in parallel and combined into a single output.

    Examples:\n
      statcan vector v41690973\n
      statcan vector v41690973 v41690974 --last 12 --output vectors.csv\n
      statcan vector 41690973 --start 2020-01 --format json
    """
    if last is not None and (start or end):
        err_console.print(
            "[red]Error: --last cannot be used with --start or --end "
            "(StatCan API limitation — returns 406)[/red]"
        )
        raise typer.Exit(1)

    try:
        normalized = [normalize_vector_id(v) for v in vector_ids]
    except ValueError as e:
        err_console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    try:
        asyncio.run(_vector(normalized, last, start, end, fmt, output))
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        if code == 404:
            err_console.print("[red]Error: One or more vectors not found[/red]")
        elif code == 406:
            err_console.print(
                "[red]Error: StatCan rejected the query (406). Check date parameters.[/red]"
            )
        else:
            err_console.print(f"[red]Error: API returned {code}[/red]")
        raise typer.Exit(2)
    except httpx.TimeoutException:
        err_console.print("[red]Error: Request timed out. Try using --last to limit observations.[/red]")
        raise typer.Exit(2)
    except httpx.RequestError:
        err_console.print("[red]Error: Could not reach Statistics Canada API[/red]")
        raise typer.Exit(2)
    except ValueError as e:
        err_console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


async def _fetch_vector(vid: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    url = f"{SDMX_BASE_URL}vector/v{vid}"
    async with httpx.AsyncClient(timeout=TIMEOUT_MEDIUM, verify=VERIFY_SSL) as client:
        response = await client.get(url, params=params, headers={"Accept": SDMX_JSON_ACCEPT})
        response.raise_for_status()
        return flatten_sdmx_json(response.json())


async def _vector(
    vector_ids: List[str],
    last: Optional[int],
    start: Optional[str],
    end: Optional[str],
    fmt: str,
    output: Optional[str],
) -> None:
    params: Dict[str, Any] = {}
    if last is not None:
        params["lastNObservations"] = last
    if start:
        params["startPeriod"] = start
    if end:
        params["endPeriod"] = end

    all_rows: List[Dict[str, Any]] = []

    if len(vector_ids) == 1:
        with err_console.status(f"[bold green]Fetching v{vector_ids[0]}..."):
            all_rows = await _fetch_vector(vector_ids[0], params)
    else:
        with Progress(console=err_console) as progress:
            task = progress.add_task("Downloading vectors...", total=len(vector_ids))

            async def fetch_and_advance(vid: str) -> List[Dict[str, Any]]:
                rows = await _fetch_vector(vid, params)
                progress.advance(task)
                return rows

            results = await asyncio.gather(*[fetch_and_advance(v) for v in vector_ids])
            for rows in results:
                all_rows.extend(rows)

    if not all_rows:
        err_console.print("[yellow]Warning: No observations returned[/yellow]")
        return

    err_console.print(f"[dim]{len(all_rows):,} rows[/dim]")
    write_output(all_rows, fmt, output, title="Vector data")
