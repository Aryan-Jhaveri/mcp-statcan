"""statcan metadata — show structure of a StatCan table."""

import asyncio
import json
from typing import Any, Dict, Optional

import httpx
import typer
from rich.panel import Panel
from rich.table import Table

from ...config import BASE_URL, TIMEOUT_MEDIUM, VERIFY_SSL
from ..contract import CLIError, ExitCode, emit_success, handle_errors, state
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
    with handle_errors(what="Product"):
        pid = normalize_product_id(product_id)
        asyncio.run(_metadata(pid, full, fmt, output))


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
        raise CLIError(
            ExitCode.NOT_FOUND,
            f"StatCan returned no metadata for product {pid}: {msg}",
            "Check the product ID with 'statcan search <term>'.",
        )

    metadata: Dict[str, Any] = result_list[0].get("object", {})

    if state.json_mode:
        dims = [
            {
                "position": d.get("dimensionPositionId"),
                "name": d.get("dimensionNameEn"),
                "member_count": len(d.get("member", [])),
                "members": [
                    {"id": m.get("memberId"), "name": m.get("memberNameEn"), "parent_id": m.get("parentMemberId")}
                    for m in (d.get("member", []) if full else d.get("member", [])[:_MEMBER_CAP])
                ],
            }
            for d in metadata.get("dimension", [])
        ]
        fields: Dict[str, Any] = {
            "product_id": pid,
            "title": metadata.get("cubeTitleEn"),
            "frequency": freq_label(metadata.get("frequencyCode")),
            "period_range": [format_date(metadata.get("cubeStartDate")), format_date(metadata.get("cubeEndDate"))],
            "members_truncated": not full and any(d["member_count"] > _MEMBER_CAP for d in dims),
            "dimensions": dims,
            "key_template": ".".join("<" + str(d["position"]) + ">" for d in dims),
        }
        if output:
            with open(output, "w") as f:
                f.write(json.dumps(metadata, indent=2, default=str, ensure_ascii=False))
            fields["path"] = output
        emit_success("metadata", **fields)
        return

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
