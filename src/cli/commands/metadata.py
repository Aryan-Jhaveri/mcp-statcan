"""statcan metadata — show structure of a StatCan table."""

import asyncio
import json
from typing import Any, Dict, Optional

import httpx
import typer
from rich.panel import Panel
from rich.table import Table

from ...config import BASE_URL, TIMEOUT_MEDIUM, VERIFY_SSL
from ..output import console, err_console, format_date, freq_label, normalize_product_id

_MEMBER_CAP = 10


def metadata_cmd(
    product_id: str = typer.Argument(..., help="Product ID (e.g. 18-10-0004-01 or 18100004)"),
    full: bool = typer.Option(False, "--full", help="Show all dimension members (no cap at 10)"),
    fmt: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Write JSON to file"),
) -> None:
    """Show structure of a StatCan table: dimensions and their members.

    Examples:\n
      statcan metadata 18-10-0004-01\n
      statcan metadata 18100004 --full\n
      statcan metadata 18-10-0004-01 --format json --output meta.json
    """
    try:
        pid = normalize_product_id(product_id)
    except ValueError as e:
        err_console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    try:
        asyncio.run(_metadata(pid, full, fmt, output))
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        if code == 404:
            err_console.print(f"[red]Error: No data found for product {pid}[/red]")
        else:
            err_console.print(f"[red]Error: API returned {code}[/red]")
        raise typer.Exit(2)
    except httpx.RequestError:
        err_console.print("[red]Error: Could not reach Statistics Canada API[/red]")
        raise typer.Exit(2)
    except ValueError as e:
        err_console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


async def _metadata(pid: int, full: bool, fmt: str, output: Optional[str]) -> None:
    with err_console.status(f"[bold green]Fetching metadata for {pid}..."):
        async with httpx.AsyncClient(
            base_url=BASE_URL, timeout=TIMEOUT_MEDIUM, verify=VERIFY_SSL
        ) as client:
            response = await client.post("/getCubeMetadata", json=[{"productId": pid}])
            response.raise_for_status()
            result_list = response.json()

    if not result_list or result_list[0].get("status") != "SUCCESS":
        msg = (
            result_list[0].get("object", "Unknown API error")
            if result_list
            else "Empty response"
        )
        raise ValueError(f"API error for product {pid}: {msg}")

    metadata: Dict[str, Any] = result_list[0].get("object", {})

    if fmt == "json":
        content = json.dumps(metadata, indent=2, default=str)
        if output:
            with open(output, "w") as f:
                f.write(content)
            err_console.print(f"[green]✓ Wrote metadata to {output}[/green]")
        else:
            print(content)
        return

    # Rich table display
    title = metadata.get("cubeTitleEn", f"Product {pid}")
    freq = freq_label(metadata.get("frequencyCode"))
    start = format_date(metadata.get("cubeStartDate"))
    end = format_date(metadata.get("cubeEndDate"))

    console.print(
        Panel(
            f"[bold]{title}[/bold]\n"
            f"Product ID: [cyan]{pid}[/cyan]  |  "
            f"Frequency: [cyan]{freq}[/cyan]  |  "
            f"Period: [cyan]{start}[/cyan] → [cyan]{end}[/cyan]",
            title="[bold blue]Statistics Canada[/bold blue]",
        )
    )

    for dim in metadata.get("dimension", []):
        pos = dim.get("dimensionPositionId", "?")
        dim_name = dim.get("dimensionNameEn", f"Dimension {pos}")
        members = dim.get("member", [])
        total = len(members)
        shown = members if full else members[:_MEMBER_CAP]

        table = Table(
            title=f"[bold]Dim {pos}: {dim_name}[/bold]",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Member ID", style="dim", width=12)
        table.add_column("Name")

        for m in shown:
            table.add_row(str(m.get("memberId", "")), m.get("memberNameEn", ""))

        if not full and total > _MEMBER_CAP:
            table.caption = (
                f"Showing {_MEMBER_CAP} of {total} members. Use --full to see all."
            )

        console.print(table)
