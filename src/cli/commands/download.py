"""statcan download — download observations for a StatCan product ID via SDMX."""

import asyncio
from typing import Any, Dict, Optional

import httpx
import typer

from ...api.sdmx.sdmx_tools import _fix_or_series_keys
from ...config import SDMX_BASE_URL, SDMX_JSON_ACCEPT, TIMEOUT_MEDIUM, VERIFY_SSL
from ...util.sdmx_json import flatten_sdmx_json
from ..output import err_console, normalize_product_id, write_output


def download(
    product_id: str = typer.Argument(..., help="Product ID (e.g. 18-10-0004-01 or 18100004)"),
    key: str = typer.Option(
        "all",
        "--key",
        help=(
            "SDMX dot-separated dimension key (e.g. '1.1.1'). "
            "Use '.' to wildcard a position. "
            "Use '+' for OR (e.g. '1+2.1.1'). "
            "Default 'all' fetches everything — may be large."
        ),
    ),
    last: Optional[int] = typer.Option(
        None, "--last", "-n", help="Last N observations per series (mutually exclusive with --start/--end)"
    ),
    start: Optional[str] = typer.Option(None, "--start", help="Start period (e.g. 2020-01 or 2015)"),
    end: Optional[str] = typer.Option(None, "--end", help="End period (e.g. 2024-12)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Write to file"),
    fmt: str = typer.Option("csv", "--format", "-f", help="Output format: csv, json, table"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print the SDMX URL that would be fetched, then exit"
    ),
) -> None:
    """Download time-series observations for a StatCan product via SDMX.

    Call 'statcan metadata <product-id>' first to see dimensions and member IDs
    for building the --key filter.

    Examples:\n
      statcan download 18-10-0004-01 --last 12\n
      statcan download 18-10-0004-01 --key "1.1.1" --start 2020-01 --end 2024-12\n
      statcan download 18-10-0004-01 --last 5 --output cpi.csv\n
      statcan download 18-10-0004-01 --key "1.1.1" --dry-run
    """
    try:
        pid = normalize_product_id(product_id)
    except ValueError as e:
        err_console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    if last is not None and (start or end):
        err_console.print(
            "[red]Error: --last cannot be used with --start or --end "
            "(StatCan API limitation — returns 406)[/red]"
        )
        raise typer.Exit(1)

    url = f"{SDMX_BASE_URL}data/DF_{pid}/{key}"
    params: Dict[str, Any] = {}
    if last is not None:
        params["lastNObservations"] = last
    if start:
        params["startPeriod"] = start
    if end:
        params["endPeriod"] = end

    if dry_run:
        query = "?" + "&".join(f"{k}={v}" for k, v in params.items()) if params else ""
        err_console.print(f"[bold]URL:[/bold] {url}{query}")
        return

    try:
        asyncio.run(_download(pid, key, url, params, fmt, output))
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        if code == 404:
            err_console.print(f"[red]Error: No data found for product {pid}[/red]")
        elif code == 406:
            err_console.print(
                "[red]Error: StatCan rejected the query (406). "
                "Check --key syntax or date parameters.[/red]"
            )
        else:
            err_console.print(f"[red]Error: API returned {code}[/red]")
        raise typer.Exit(2)
    except httpx.TimeoutException:
        err_console.print("[red]Error: Request timed out. Try a more specific --key or use --last.[/red]")
        raise typer.Exit(2)
    except httpx.RequestError:
        err_console.print("[red]Error: Could not reach Statistics Canada API[/red]")
        raise typer.Exit(2)
    except ValueError as e:
        err_console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


async def _download(
    pid: int,
    key: str,
    url: str,
    params: Dict[str, Any],
    fmt: str,
    output: Optional[str],
) -> None:
    with err_console.status("[bold green]Fetching data from Statistics Canada..."):
        async with httpx.AsyncClient(timeout=TIMEOUT_MEDIUM, verify=VERIFY_SSL) as client:
            response = await client.get(
                url, params=params, headers={"Accept": SDMX_JSON_ACCEPT}
            )
            response.raise_for_status()
            response_json = response.json()

    # Fix StatCan's non-standard series key encoding for OR-key queries
    if "+" in key:
        _fix_or_series_keys(response_json, key)

    rows = flatten_sdmx_json(response_json)

    if not rows:
        err_console.print("[yellow]Warning: No observations returned for this query[/yellow]")
        return

    err_console.print(f"[dim]{len(rows):,} rows[/dim]")
    write_output(rows, fmt, output, title=f"Product {pid}")
