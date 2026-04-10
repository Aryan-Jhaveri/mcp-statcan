"""statcan search — search for StatCan tables by keyword."""

import asyncio
from typing import Optional

import httpx
import typer

from ...config import BASE_URL, TIMEOUT_LARGE, VERIFY_SSL
from ..output import err_console, format_date, freq_label, write_output


def search(
    term: str = typer.Argument(..., help="Search term (multiple words use AND logic)"),
    max_results: int = typer.Option(25, "--max-results", "-n", help="Maximum results to show"),
    fmt: str = typer.Option("table", "--format", "-f", help="Output format: table, csv, json"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Write to file"),
) -> None:
    """Search for StatCan tables by keyword.

    Multiple keywords use AND logic: all terms must appear in the title.

    Examples:\n
      statcan search "consumer price index"\n
      statcan search GDP --max-results 10\n
      statcan search "labour force" --format json
    """
    try:
        asyncio.run(_search(term, max_results, fmt, output))
    except httpx.HTTPStatusError as e:
        err_console.print(f"[red]Error: API returned {e.response.status_code}[/red]")
        raise typer.Exit(2)
    except httpx.RequestError:
        err_console.print("[red]Error: Could not reach Statistics Canada API[/red]")
        raise typer.Exit(2)
    except ValueError as e:
        err_console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


async def _search(term: str, max_results: int, fmt: str, output: Optional[str]) -> None:
    with err_console.status("[bold green]Fetching cube list from Statistics Canada..."):
        async with httpx.AsyncClient(
            base_url=BASE_URL, timeout=TIMEOUT_LARGE, verify=VERIFY_SSL
        ) as client:
            response = await client.get("/getAllCubesListLite")
            response.raise_for_status()
            all_cubes = response.json()

    search_terms = term.lower().split()

    matching = [
        cube
        for cube in all_cubes
        if all(t in (cube.get("cubeTitleEn", "") or "").lower() for t in search_terms)
        or all(t in (cube.get("cubeTitleFr", "") or "").lower() for t in search_terms)
    ]

    total = len(matching)
    if total > max_results:
        err_console.print(
            f"[yellow]Showing {max_results} of {total} matches. "
            "Use --max-results to see more.[/yellow]"
        )
        matching = matching[:max_results]

    if not matching:
        err_console.print(f"[yellow]No tables found matching '{term}'[/yellow]")
        return

    rows = [
        {
            "Product ID": cube.get("productId", ""),
            "Title": cube.get("cubeTitleEn", ""),
            "Frequency": freq_label(cube.get("frequencyCode")),
            "Start": format_date(cube.get("cubeStartDate")),
            "End": format_date(cube.get("cubeEndDate")),
        }
        for cube in matching
    ]

    write_output(rows, fmt, output, title=f'Search: "{term}"', filter_internal=False)
