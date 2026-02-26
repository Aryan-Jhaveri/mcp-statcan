"""Shared truncation and summarization helpers for large API responses."""

from typing import List, Dict, Any, Union
import copy


DEFAULT_MEMBER_LIMIT = 10


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
    metadata: Dict[str, Any], member_limit: int = DEFAULT_MEMBER_LIMIT
) -> Dict[str, Any]:
    """Summarize cube metadata by truncating dimension member lists.

    Keeps dimension IDs, names, and member counts. Truncates each dimension's
    member list to member_limit entries and appends a count message.
    """
    result = copy.deepcopy(metadata)
    dimensions = result.get("dimension", [])

    for dim in dimensions:
        members = dim.get("member", [])
        total_members = len(members)
        if total_members > member_limit:
            dim["member"] = members[:member_limit]
            dim["_member_count"] = total_members
            dim["_truncated"] = True
            dim["_message"] = (
                f"Showing first {member_limit} of {total_members} members. "
                f"This dimension occupies position {dim.get('dimensionPositionId', '?')} in the coordinate string. "
                "Each member's memberId is its value at that position (e.g., memberId=3 → coordinate position value 3). "
                "To browse all members without flooding context, use store_cube_metadata(productId) — "
                "it stores the full member list in SQLite and returns a compact summary you can query. "
                "To resolve a specific coordinate to its vectorId and series name, use "
                "get_series_info_from_cube_pid_coord(productId, coordinate)."
            )
        else:
            dim["_member_count"] = total_members
            dim["_truncated"] = False

    # Strip footnotes — they are long bilingual methodology notes that bloat the
    # response without helping with navigation. Replace with a count.
    footnotes = result.get("footnote", [])
    if footnotes:
        result["footnote"] = f"[{len(footnotes)} footnotes omitted. Set summary=False to include them.]"

    result["_summary"] = True
    return result
