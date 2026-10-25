"""statcan CLI — entry point and subcommand registration."""

import typer

from .contract import json_mode_requested, state

from .commands.codeset import codeset
from .commands.describe import describe
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
        '  statcan download 18-10-0004-01 --key "1.1.1" --last 12 --output cpi.csv'
    ),
)



@app.callback()
def _root(
    json_mode: bool = typer.Option(
        False,
        "--json",
        help="Machine-readable mode: one JSON envelope on stdout, JSON errors on stderr, "
        "stable exit codes. Also enabled by STATCAN_OUTPUT=json. See 'statcan describe'.",
    ),
) -> None:
    state.json_mode = json_mode_requested(json_mode)


app.command("search")(search)
app.command("metadata")(metadata_cmd)
app.command("download")(download)
app.command("vector")(vector)
app.command("codeset")(codeset)
app.command("describe")(describe)


def main() -> None:
    app()
