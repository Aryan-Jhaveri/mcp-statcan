"""statcan describe — machine-readable description of the CLI for agents."""

import json
from typing import Any, Dict, List

import click
import typer

from ..contract import contract_description

_WORKFLOW = [
    "statcan --json search '<keywords>'                     # find a productId",
    "statcan --json metadata <productId>                    # dimension positions + member IDs",
    "statcan --json download <productId> --key <k> --last 12 -o data.csv   # file + summary envelope",
    "statcan --json vector <vectorId>... --last 12          # when you already know vector IDs",
]


def _param(p: click.Parameter) -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "name": p.name,
        "kind": p.param_type_name,  # "argument" or "option" (Typer's classes aren't click.Option subclasses)
        "type": p.type.name,
        "required": p.required,
        "multiple": bool(getattr(p, "multiple", False) or p.nargs == -1),
    }
    if p.param_type_name == "option":
        info["flags"] = p.opts + p.secondary_opts
        info["is_flag"] = p.is_flag
        info["help"] = p.help
    if p.default is not None and not callable(p.default):
        info["default"] = p.default
    return info


def describe_cli(root: click.Group) -> Dict[str, Any]:
    commands: List[Dict[str, Any]] = []
    for name, cmd in sorted(root.commands.items()):
        commands.append({
            "name": name,
            "summary": (cmd.help or "").strip().splitlines()[0] if cmd.help else "",
            "params": [_param(p) for p in cmd.params if p.name != "help"],
        })
    return {
        "name": "statcan",
        "global_options": [_param(p) for p in root.params if p.name != "help"],
        "workflow": _WORKFLOW,
        "contract": contract_description(),
        "commands": commands,
    }


def describe(ctx: typer.Context) -> None:
    """Print commands, options, exit codes and JSON envelopes as JSON (for agents).

    Always prints JSON, with or without --json.
    """
    root = ctx.find_root().command
    print(json.dumps(describe_cli(root), indent=2, default=str))
