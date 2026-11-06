"""Core toolset (STATCAN_TOOLSET=core): five tools covering the legacy hosted set.

Built side by side with the legacy tools (#138) and reusing their HTTP and parse
helpers. Guidance lives in parameter descriptions and error messages.
"""

from .tools import register_core_tools

__all__ = ["register_core_tools"]
