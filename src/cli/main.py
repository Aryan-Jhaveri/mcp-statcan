"""statcan CLI — entry point and subcommand registration."""

import typer

from .commands.codeset import codeset
from .commands.download import download
from .commands.metadata import metadata_cmd
from .commands.search import search
from .commands.vector import vector

app = typer.Typer(
    name="statcan",
    no_args_is_help=True,
    help=(
        "Statistics Canada data CLI — search, explore, and download StatCan tables "
        "without an LLM client.\n\n"
        "Quick start:\n\n"
        "  statcan search 'consumer price index'\n\n"
        "  statcan metadata 18-10-0004-01\n\n"
        "  statcan download 18-10-0004-01 --last 12 --output cpi.csv"
    ),
)

app.command("search")(search)
app.command("metadata")(metadata_cmd)
app.command("download")(download)
app.command("vector")(vector)
app.command("codeset")(codeset)


def main() -> None:
    app()
