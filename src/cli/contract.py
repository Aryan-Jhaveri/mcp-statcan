"""Machine-readable contract for the statcan CLI: exit codes, JSON envelopes, errors.

Agents with a shell (Claude Code, sandboxes, scripts) should be able to rely on:

  - Stable exit codes (ExitCode) — branch on failure type without parsing text
  - JSON mode (--json or STATCAN_OUTPUT=json):
      success → stdout: {"ok": true, "command": ..., ...}
      failure → stderr: {"ok": false, "error": {"code", "exit_code", "message", "hint"}}
  - Data on stdout, progress and human messages on stderr

`statcan describe` prints this contract plus every command's options as JSON.
"""

import json
import os
import sys
from contextlib import contextmanager
from enum import IntEnum
from typing import Any, Dict, Iterator, Optional

import httpx
import typer


class ExitCode(IntEnum):
    OK = 0
    ERROR = 1                 # unexpected failure
    USAGE = 2                 # bad arguments/options (matches Click's usage-error code)
    NOT_FOUND = 3             # product, vector or codeset does not exist
    UPSTREAM_REJECTED = 4     # StatCan rejected the request (4xx other than 404)
    UPSTREAM_UNAVAILABLE = 5  # network error, timeout, or StatCan 5xx
    EMPTY = 6                 # request succeeded but returned no rows


EXIT_CODE_DOCS = {
    ExitCode.OK: "success",
    ExitCode.ERROR: "unexpected error",
    ExitCode.USAGE: "invalid arguments or options; fix the command",
    ExitCode.NOT_FOUND: "product, vector or codeset not found",
    ExitCode.UPSTREAM_REJECTED: "StatCan rejected the request (bad key or period); see hint",
    ExitCode.UPSTREAM_UNAVAILABLE: "network error, timeout or StatCan 5xx; safe to retry",
    ExitCode.EMPTY: "no rows for this query; widen the key or period",
}


class _State:
    json_mode: bool = False  # set by the root callback from --json / STATCAN_OUTPUT


def json_mode_requested(flag: bool) -> bool:
    return flag or os.environ.get("STATCAN_OUTPUT", "").lower() == "json"


state = _State()


class CLIError(Exception):
    """A failure with a stable exit code and an actionable hint."""

    def __init__(self, exit_code: ExitCode, message: str, hint: Optional[str] = None):
        super().__init__(message)
        self.exit_code = exit_code
        self.message = message
        self.hint = hint


def emit_success(command: str, **fields: Any) -> None:
    """Print the JSON success envelope to stdout (JSON mode only)."""
    print(json.dumps({"ok": True, "command": command, **fields}, default=str, ensure_ascii=False))


def emit_error(err: CLIError) -> None:
    """Report an error on stderr — JSON envelope in JSON mode, readable text otherwise."""
    if state.json_mode:
        payload = {
            "ok": False,
            "error": {
                "code": err.exit_code.name.lower(),
                "exit_code": int(err.exit_code),
                "message": err.message,
                "hint": err.hint,
            },
        }
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
    else:
        from .output import err_console

        err_console.print(f"[red]Error: {err.message}[/red]", highlight=False)
        if err.hint:
            err_console.print(f"[yellow]Hint: {err.hint}[/yellow]", highlight=False)


def http_error(exc: httpx.HTTPError, *, what: str, hint_406: Optional[str] = None) -> CLIError:
    """Map an httpx error to a CLIError with a stable exit code and hint."""
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code == 404:
            return CLIError(ExitCode.NOT_FOUND, f"{what} not found (HTTP 404)",
                            "Check the ID with 'statcan search <term>'.")
        if code == 406:
            return CLIError(ExitCode.UPSTREAM_REJECTED, "StatCan rejected the query (HTTP 406)",
                            hint_406 or "Check the key and period options.")
        if code == 400:
            return CLIError(ExitCode.UPSTREAM_REJECTED, "StatCan rejected the request (HTTP 400)",
                            hint_406 or "Check the key and period options.")
        if code >= 500 or code == 429:
            return CLIError(ExitCode.UPSTREAM_UNAVAILABLE, f"StatCan returned HTTP {code}",
                            "Temporary upstream failure; retry shortly.")
        return CLIError(ExitCode.UPSTREAM_REJECTED, f"StatCan returned HTTP {code}")
    if isinstance(exc, httpx.TimeoutException):
        return CLIError(ExitCode.UPSTREAM_UNAVAILABLE, "Request to StatCan timed out",
                        "Retry, or narrow the request (more specific --key, or --last N).")
    return CLIError(ExitCode.UPSTREAM_UNAVAILABLE, "Could not reach the Statistics Canada API",
                    "Check network access to www150.statcan.gc.ca and retry.")


@contextmanager
def handle_errors(*, what: str = "Resource", hint_406: Optional[str] = None) -> Iterator[None]:
    """Convert failures inside a command into the contract's error output + exit code."""
    try:
        yield
    except typer.Exit:
        raise
    except CLIError as err:
        emit_error(err)
        raise typer.Exit(int(err.exit_code))
    except httpx.HTTPError as exc:
        err = http_error(exc, what=what, hint_406=hint_406)
        emit_error(err)
        raise typer.Exit(int(err.exit_code))
    except ValueError as exc:
        # Input validation (product/vector ID format, --last with --start, unknown --format)
        err = CLIError(ExitCode.USAGE, str(exc))
        emit_error(err)
        raise typer.Exit(int(err.exit_code))
    except Exception as exc:  # noqa: BLE001 — still report through the contract
        err = CLIError(ExitCode.ERROR, f"Unexpected error: {exc}",
                       "Please report this at https://github.com/Aryan-Jhaveri/mcp-statcan/issues")
        emit_error(err)
        raise typer.Exit(int(err.exit_code))


def contract_description() -> Dict[str, Any]:
    """The contract itself, for `statcan describe`."""
    return {
        "json_mode": "Pass --json (before the subcommand) or set STATCAN_OUTPUT=json.",
        "success_envelope": {"ok": True, "command": "<name>", "...": "command-specific fields"},
        "error_envelope": {
            "ok": False,
            "error": {"code": "<exit code name>", "exit_code": "<int>", "message": "<str>", "hint": "<str|null>"},
        },
        "streams": "stdout = data or success envelope; stderr = progress, messages, error envelope",
        "exit_codes": {str(int(c)): {"name": c.name.lower(), "meaning": EXIT_CODE_DOCS[c]} for c in ExitCode},
    }
