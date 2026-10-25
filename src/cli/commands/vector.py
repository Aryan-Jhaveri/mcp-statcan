"""statcan vector — download observations for one or more vector IDs via SDMX."""

import asyncio
from typing import Any, Dict, List, Optional

import httpx
import typer
from rich.progress import Progress

from ...config import SDMX_BASE_URL, SDMX_JSON_ACCEPT, TIMEOUT_MEDIUM, VERIFY_SSL
from ...util.sdmx_json import flatten_sdmx_json
from ..contract import CLIError, ExitCode, handle_errors
from ..output import err_console, normalize_vector_id, summarize_rows, write_output


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
    fmt: str = typer.Option("csv", "--format", "-f", help="Output format: csv, json, ndjson, table"),
) -> None:
    """Download time-series observations for one or more StatCan vector IDs.

    Multiple vector IDs are fetched in parallel and combined into a single output.

    Examples:\n
      statcan vector v41690973\n
      statcan vector v41690973 v41690974 --last 12 --output vectors.csv\n
      statcan vector 41690973 --start 2020-01 --format json
    """
    with handle_errors(what="Vector", hint_406="Check --start/--end format (e.g. 2020-01 or 2020)."):
        if last is not None and (start or end):
            raise CLIError(
                ExitCode.USAGE,
                "--last cannot be used with --start or --end (StatCan returns 406).",
                "Use --last N for recent data, or --start/--end for a range.",
            )
        normalized = [normalize_vector_id(v) for v in vector_ids]
        asyncio.run(_vector(normalized, last, start, end, fmt, output))


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
        raise CLIError(
            ExitCode.EMPTY,
            "No observations returned for the requested vector(s).",
            "Widen the period (--start/--last) or check the vector IDs with 'statcan metadata'.",
        )

    err_console.print(f"[dim]{len(all_rows):,} rows[/dim]")
    write_output(
        all_rows, fmt, output, title="Vector data", command="vector",
        extra={"vector_ids": [f"v{v}" for v in vector_ids], **summarize_rows(all_rows)},
    )
