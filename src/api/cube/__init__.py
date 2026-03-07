"""Cube-related API tools — discovery, metadata, and series resolution."""

from ...util.registry import ToolRegistry
from .discovery import register_cube_discovery_tools
from .metadata import register_cube_metadata_tools
from .series import register_cube_series_tools


def register_cube_tools(registry: ToolRegistry):
    """Register all cube-related API tools with the MCP server."""
    register_cube_discovery_tools(registry)
    register_cube_metadata_tools(registry)
    register_cube_series_tools(registry)
