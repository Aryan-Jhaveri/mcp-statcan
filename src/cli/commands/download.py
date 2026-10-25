"""statcan download — download observations for a StatCan product ID via SDMX."""

import asyncio
from typing import Optional

import typer

from ...api.sdmx.sdmx_tools import fetch_sdmx_rows
from ...config import SDMX_BASE_URL
from ..contract import CLIError, ExitCode, emit_success, handle_errors, state
from ..output import err_console, normalize_product_id, summarize_rows, write_output

_KEY_HINT = (
    "Run 'statcan metadata <product-id>' to see dimension positions and member IDs, "
    "then pass explicit codes, e.g. --key '1.1.1' (use '+' for OR: '1+2.1.1'). "
    "Wildcard (empty) positions are rejected by StatCan."
)


def download(
    product_id: str = typer.Argument(..., help="Product ID (e.g. 18-10-0004-01 or 18100004)"),
    key: Optional[str] = typer.Option(
        None,
        "--key",
        help=(
            "SDMX dot-separated dimension key, e.g. '1.1.1' (required). "
            "Use '+' for OR within a dimension (e.g. '1+2.1.1'). "
            "Run 'statcan metadata <product-id>' first to see dimension positions and member IDs."
        ),
    ),
    last: Optional[int] = typer.Option(
        None, "--last", "-n", help="Last N observations per series (mutually exclusive with --start/--end)"
    ),
    start: Optional[str] = typer.Option(None, "--start", help="Start period (e.g. 2020-01 or 2015)"),
    end: Optional[str] = typer.Option(None, "--end", help="End period (e.g. 2024-12)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Write to file"),
    fmt: str = typer.Option("csv", "--format", "-f", help="Output format: csv, json, ndjson, table"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print the SDMX URL that would be fetched, then exit"
    ),
) -> None:
    """Download time-series observations for a StatCan product via SDMX.

    Call 'statcan metadata <product-id>' first to see dimensions and member IDs
    for building the --key filter.

    Examples:\n
      statcan download 18-10-0004-01 --key "1.1.1" --last 12\n
      statcan download 18-10-0004-01 --key "1.1.1" --start 2020-01 --end 2024-12\n
      statcan download 18-10-0004-01 --key "1.1.1" --last 5 --output cpi.csv\n
      statcan --json download 18-10-0004-01 --key "1.1.1" --last 5 --output cpi.csv\n
      statcan download 18-10-0004-01 --key "1.1.1" --dry-run
    """
    with handle_errors(what="Product", hint_406=_KEY_HINT):
        pid = normalize_product_id(product_id)

        if key is None:
            raise CLIError(ExitCode.USAGE, "--key is required.", _KEY_HINT)
        if last is not None and (start or end):
            raise CLIError(
                ExitCode.USAGE,
                "--last cannot be used with --start or --end (StatCan returns 406).",
                "Use --last N for recent data, or --start/--end for a range.",
            )

        if dry_run:
            params = {"lastNObservations": last, "startPeriod": start, "endPeriod": end}
            query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
            url = f"{SDMX_BASE_URL}data/DF_{pid}/{key}" + (f"?{query}" if query else "")
            if state.json_mode:
                emit_success("download", dry_run=True, source_url=url)
            else:
                err_console.print(f"[bold]URL:[/bold] {url}")
            return

        with err_console.status("[bold green]Fetching data from Statistics Canada..."):
            rows, url = asyncio.run(fetch_sdmx_rows(pid, key, last, start, end))

        if not rows:
            raise CLIError(
                ExitCode.EMPTY,
                f"No observations returned for product {pid} with key '{key}'.",
                "Widen the period (--start/--last) or check the key against 'statcan metadata'.",
            )

        err_console.print(f"[dim]{len(rows):,} rows[/dim]")
        write_output(
            rows, fmt, output, title=f"Product {pid}", command="download",
            extra={"product_id": pid, "key": key, "source_url": url, **summarize_rows(rows)},
        )
