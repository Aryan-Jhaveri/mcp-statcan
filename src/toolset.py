"""Toolset selection (STATCAN_TOOLSET), shared by the server and the MCP prompts."""

import os
from typing import Optional

TOOLSETS = ("legacy", "core")


def resolve_toolset(toolset: Optional[str] = None) -> str:
    """The toolset to serve: the argument, else STATCAN_TOOLSET, else 'core'."""
    name = (toolset or os.environ.get("STATCAN_TOOLSET") or "core").strip().lower()
    if name not in TOOLSETS:
        raise ValueError(f"Unknown STATCAN_TOOLSET {name!r}; use one of: {', '.join(TOOLSETS)}.")
    return name
