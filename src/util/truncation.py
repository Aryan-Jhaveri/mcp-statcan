"""Shared truncation and summarization helpers for large API responses."""

from typing import List, Dict, Any, Union
import copy


DEFAULT_MEMBER_LIMIT = 10
SUMMARY_MEMBER_LIMIT = 3  # Members shown per dimension in summary mode

# Top-level fields kept in summary mode — everything else is stripped.
_SUMMARY_TOP_LEVEL = {
    "productId", "cansimId", "cubeTitleEn",
    "cubeStartDate", "cubeEndDate", "frequencyCode", "releaseTime",
    "dimension", "footnote",
}

# Member fields kept in summary mode — strips Fr translations and low-level codes.
_SUMMARY_MEMBER_FIELDS = {"memberId", "memberNameEn", "terminated"}


def truncate_response(
    rows: List[Dict[str, Any]], offset: int, limit: int
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """Apply offset/limit truncation and return guidance if there are more rows."""
    total = len(rows)
    sliced = rows[offset : offset + limit]

    if total <= limit and offset == 0:
        return sliced

    has_more = (offset + limit) < total
    return {
        "data": sliced,
        "total_rows": total,
        "offset": offset,
        "limit": limit,
        "has_more": has_more,
        "message": (
            f"Showing {len(sliced)} of {total} rows (offset={offset})."
            + (
                f" Call again with offset={offset + limit} to get more."
                if has_more
                else ""
            )
            + " To understand this data, call get_code_sets() for unit/scalar definitions,"
            " or get_series_info_from_vector / get_series_info_from_cube_pid_coord_bulk for series metadata."
        ),
    }


def truncate_with_guidance(
    rows: List[Dict[str, Any]], offset: int, limit: int, guidance: str
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """Like truncate_response but injects a _guidance key into the result."""
    result = truncate_response(rows, offset, limit)
    if isinstance(result, dict):
        result["_guidance"] = guidance
    elif len(rows) > 0:
        # Even when not truncated, wrap to include guidance
        return {
            "data": result,
            "total_rows": len(rows),
            "_guidance": guidance,
        }
    return result


def summarize_cube_metadata(
    metadata: Dict[str, Any], member_limit: int = SUMMARY_MEMBER_LIMIT
) -> Dict[str, Any]:
    """Return a compact cube metadata summary safe for LLM context windows.

    Strips French translations, low-level codes, and noisy top-level fields.
    Keeps at most member_limit members per dimension (default 3) for orientation;
    strips per-member noise fields (Fr name, classification codes, geo level, etc.).
    Footnotes are replaced with a count.

    Adds _next_steps guidance so the LLM knows how to get full member lists
    or resolve coordinates to vectorIds without another large fetch.
    """
    # ── 1. Keep only essential top-level fields ─────────────────────────────
    result: Dict[str, Any] = {
        k: copy.deepcopy(v)
        for k, v in metadata.items()
        if k in _SUMMARY_TOP_LEVEL
    }

    # ── 2. Slim each dimension ───────────────────────────────────────────────
    slim_dims = []
    for dim in result.get("dimension", []):
        members = dim.get("member", [])
        total_members = len(members)

        slim_members = [
            {f: m[f] for f in _SUMMARY_MEMBER_FIELDS if f in m}
            for m in members[:member_limit]
        ]

        slim_dim: Dict[str, Any] = {
            "dimensionPositionId": dim.get("dimensionPositionId"),
            "dimensionNameEn": dim.get("dimensionNameEn"),
            "hasUom": dim.get("hasUom"),
            "member": slim_members,
            "_member_count": total_members,
            "_truncated": total_members > member_limit,
        }
        slim_dims.append(slim_dim)

    result["dimension"] = slim_dims

    # ── 3. Replace footnotes with a count ────────────────────────────────────
    footnotes = result.get("footnote", [])
    if isinstance(footnotes, list) and footnotes:
        result["footnote"] = f"[{len(footnotes)} footnotes omitted — set summary=False to include]"
    elif not footnotes:
        result.pop("footnote", None)

    # ── 4. Guidance ──────────────────────────────────────────────────────────
    pid = metadata.get("productId", "?")
    result["_next_steps"] = (
        f"Showing {member_limit} sample members per dimension. "
        "To browse full member lists and build SDMX keys, call get_sdmx_structure(productId). "
        "To resolve a specific coordinate to a vectorId, call "
        f"get_series_info(items=[{{\"productId\": {pid}, \"coordinate\": \"1.1.1...\"}}]). "
        "To see all raw API fields and full member lists, call get_cube_metadata(summary=False)."
    )

    result["_summary"] = True
    return result
