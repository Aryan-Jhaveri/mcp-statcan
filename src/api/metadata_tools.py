import time
from typing import Any, Dict, List, Optional, Tuple

from ..models.api_models import CodeSetsInput
from ..util.registry import READ_ONLY, ToolRegistry
from .client import make_get_request

# Code sets rarely change; cache them like the cube list (1 hour)
_CODE_SETS_TTL_SECONDS = 3600.0
_code_sets_cache: Optional[Tuple[float, Dict[str, List[Dict[str, Any]]]]] = None

# Sets with more entries than this are summarized unless requested by name
_SUMMARY_MAX_ENTRIES = 25


async def _fetch_code_sets() -> Dict[str, List[Dict[str, Any]]]:
    global _code_sets_cache
    if _code_sets_cache and time.monotonic() - _code_sets_cache[0] < _CODE_SETS_TTL_SECONDS:
        return _code_sets_cache[1]
    result = await make_get_request("/getCodeSets")
    if result.get("status") != "SUCCESS":
        api_message = result.get("object", "Unknown API Error")
        raise ValueError(f"API did not return SUCCESS status: {api_message}")
    code_sets = result.get("object", {})
    _code_sets_cache = (time.monotonic(), code_sets)
    return code_sets


def _matches(entry: Dict[str, Any], search: str) -> bool:
    needle = search.casefold()
    return any(needle in str(v).casefold() for v in entry.values() if v is not None)


def register_metadata_tools(registry: ToolRegistry):
    """Register metadata-related API tools with the MCP server."""

    @registry.tool(annotations=READ_ONLY)
    async def get_code_sets(code_sets_input: CodeSetsInput) -> Dict[str, Any]:
        """
        Decode StatCan WDS numeric codes (e.g. frequencyCode 6 = Monthly, scalarFactorCode 0 = units).
        Corresponds to: GET /getCodeSets

        Without arguments, returns a summary: small code sets (scalar, frequency, symbol,
        status, ...) in full, and only entry counts for large ones (uom, survey, subject,
        classificationType). Request a large set with code_set, and narrow it with search:
          get_code_sets(code_set="uom", search="percent")

        Returns:
            Dict[str, Any]: {code_set_name: [entries]} for the returned sets, plus
            "_large_code_sets" {name: entry count} in the summary.
        Raises:
            ValueError: If code_set is unknown or the API response is not SUCCESS.

        IMPORTANT: In your final response to the user, you MUST cite the source of your data.
        For code sets, this means specifying which code set table or definition is being used.
        """
        code_sets = await _fetch_code_sets()
        name = code_sets_input.code_set
        search = code_sets_input.search

        if name is None:
            if search:
                raise ValueError("search requires code_set (e.g. code_set='uom').")
            summary: Dict[str, Any] = {}
            large: Dict[str, int] = {}
            for set_name, entries in code_sets.items():
                if len(entries) > _SUMMARY_MAX_ENTRIES:
                    large[set_name] = len(entries)
                else:
                    summary[set_name] = entries
            summary["_large_code_sets"] = large
            summary["_hint"] = (
                "Large sets are omitted. Call get_code_sets(code_set=<name>, search=<text or code>) "
                "to look up entries, e.g. code_set='uom', search='percent'."
            )
            return summary

        if name not in code_sets:
            raise ValueError(f"Unknown code_set '{name}'. Available: {', '.join(code_sets)}")
        entries = code_sets[name]
        if search:
            entries = [e for e in entries if _matches(e, search)]
        return {name: entries, "count": len(entries)}
