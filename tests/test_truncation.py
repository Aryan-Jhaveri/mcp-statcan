"""Tests for src/util/truncation.py — shared truncation and summarization helpers."""

import pytest
from src.util.truncation import (
    truncate_response,
    truncate_with_guidance,
    summarize_cube_metadata,
    SUMMARY_MEMBER_LIMIT,
)


# --- truncate_response ---

def _make_rows(n):
    return [{"id": i, "value": f"row_{i}"} for i in range(n)]


def test_no_truncation_when_within_limit():
    """When total rows <= limit and offset == 0, returns the plain list."""
    rows = _make_rows(10)
    result = truncate_response(rows, offset=0, limit=50)
    assert isinstance(result, list)
    assert len(result) == 10
    assert result == rows


def test_truncation_returns_paginated_dict():
    """When rows exceed limit, returns a dict with pagination metadata."""
    rows = _make_rows(120)
    result = truncate_response(rows, offset=0, limit=50)
    assert isinstance(result, dict)
    assert len(result["data"]) == 50
    assert result["total_rows"] == 120
    assert result["offset"] == 0
    assert result["limit"] == 50
    assert result["has_more"] is True
    assert "offset=50" in result["message"]


def test_truncation_last_page():
    """When offset + limit >= total, has_more should be False."""
    rows = _make_rows(80)
    result = truncate_response(rows, offset=50, limit=50)
    assert isinstance(result, dict)
    assert len(result["data"]) == 30
    assert result["has_more"] is False
    assert result["total_rows"] == 80


def test_offset_pagination():
    """Verify offset skips the right rows."""
    rows = _make_rows(120)
    result = truncate_response(rows, offset=50, limit=50)
    assert isinstance(result, dict)
    assert result["data"][0]["id"] == 50
    assert result["data"][-1]["id"] == 99
    assert result["has_more"] is True


def test_empty_rows():
    """Empty input returns empty list."""
    result = truncate_response([], offset=0, limit=50)
    assert isinstance(result, list)
    assert len(result) == 0


def test_offset_beyond_total():
    """Offset past total rows returns empty data slice."""
    rows = _make_rows(10)
    result = truncate_response(rows, offset=20, limit=50)
    assert isinstance(result, dict)
    assert len(result["data"]) == 0
    assert result["total_rows"] == 10


# --- truncate_with_guidance ---

def test_truncate_with_guidance_when_truncated():
    """Guidance key present when truncation kicks in."""
    rows = _make_rows(100)
    guidance = "Call get_code_sets() for labels."
    result = truncate_with_guidance(rows, offset=0, limit=50, guidance=guidance)
    assert isinstance(result, dict)
    assert result["_guidance"] == guidance
    assert len(result["data"]) == 50


def test_truncate_with_guidance_when_not_truncated():
    """Guidance key still present even when data fits within limit."""
    rows = _make_rows(5)
    guidance = "Call get_code_sets() for labels."
    result = truncate_with_guidance(rows, offset=0, limit=50, guidance=guidance)
    assert isinstance(result, dict)
    assert result["_guidance"] == guidance
    assert len(result["data"]) == 5


def test_truncate_with_guidance_empty():
    """Empty rows returns empty list (no guidance wrapper needed)."""
    result = truncate_with_guidance([], offset=0, limit=50, guidance="test")
    assert isinstance(result, list)
    assert len(result) == 0


# --- summarize_cube_metadata ---

def _make_metadata(member_counts):
    """Build a fake metadata dict with dimensions having specified member counts."""
    return {
        "productId": 12345678,
        "cubeTitleEn": "Test Cube",
        "cubeStartDate": "2000-01-01",
        "cubeEndDate": "2024-01-01",
        "frequencyCode": 6,
        "releaseTime": "2024-01-10T08:30",
        "dimension": [
            {
                "dimensionPositionId": i + 1,
                "dimensionNameEn": f"Dimension {i}",
                "dimensionNameFr": f"Dimension FR {i}",
                "hasUom": False,
                "member": [
                    {
                        "memberId": j,
                        "memberNameEn": f"Member {j}",
                        "memberNameFr": f"Membre {j}",
                        "classificationCode": f"CODE{j}",
                        "terminated": 0,
                    }
                    for j in range(count)
                ],
            }
            for i, count in enumerate(member_counts)
        ],
    }


def test_summarize_small_metadata():
    """Dimensions with <= SUMMARY_MEMBER_LIMIT members show all; larger ones are truncated."""
    metadata = _make_metadata([2, SUMMARY_MEMBER_LIMIT, SUMMARY_MEMBER_LIMIT + 1])
    result = summarize_cube_metadata(metadata)
    assert result["_summary"] is True

    dim0 = result["dimension"][0]
    assert dim0["_truncated"] is False
    assert dim0["_member_count"] == 2
    assert len(dim0["member"]) == 2

    dim1 = result["dimension"][1]
    assert dim1["_truncated"] is False
    assert dim1["_member_count"] == SUMMARY_MEMBER_LIMIT

    dim2 = result["dimension"][2]
    assert dim2["_truncated"] is True
    assert dim2["_member_count"] == SUMMARY_MEMBER_LIMIT + 1
    assert len(dim2["member"]) == SUMMARY_MEMBER_LIMIT


def test_summarize_large_metadata():
    """Dimensions with many members are truncated to SUMMARY_MEMBER_LIMIT."""
    metadata = _make_metadata([50, 100, 2])
    result = summarize_cube_metadata(metadata)

    dim0 = result["dimension"][0]
    assert dim0["_truncated"] is True
    assert dim0["_member_count"] == 50
    assert len(dim0["member"]) == SUMMARY_MEMBER_LIMIT

    dim1 = result["dimension"][1]
    assert dim1["_truncated"] is True
    assert dim1["_member_count"] == 100
    assert len(dim1["member"]) == SUMMARY_MEMBER_LIMIT

    dim2 = result["dimension"][2]
    assert dim2["_truncated"] is False
    assert len(dim2["member"]) == 2


def test_summarize_custom_limit():
    """Custom member_limit is respected."""
    metadata = _make_metadata([30])
    result = summarize_cube_metadata(metadata, member_limit=10)
    dim = result["dimension"][0]
    assert len(dim["member"]) == 10
    assert dim["_member_count"] == 30
    assert dim["_truncated"] is True


def test_summarize_strips_noise_fields():
    """Summary strips French fields and low-level codes from members and top level."""
    metadata = _make_metadata([5])
    metadata["cubeTitleFr"] = "Titre FR"
    metadata["archiveStatusEn"] = "CURRENT"
    metadata["nbSeriesCube"] = 9000
    result = summarize_cube_metadata(metadata)

    # Top-level noise stripped
    assert "cubeTitleFr" not in result
    assert "archiveStatusEn" not in result
    assert "nbSeriesCube" not in result

    # Essential top-level kept
    assert result["cubeTitleEn"] == "Test Cube"
    assert result["productId"] == 12345678
    assert result["frequencyCode"] == 6

    # Member noise stripped; essentials kept
    dim = result["dimension"][0]
    member = dim["member"][0]
    assert "memberNameFr" not in member
    assert "classificationCode" not in member
    assert "memberNameEn" in member
    assert "memberId" in member
    assert "terminated" in member

    # Dim noise stripped
    assert "dimensionNameFr" not in dim


def test_summarize_strips_footnotes():
    """Footnotes are replaced with a count string in summary mode."""
    metadata = _make_metadata([3])
    metadata["footnote"] = [
        {"footnoteId": 1, "footnotesEn": "A long note.", "footnotesFr": "Une longue note."},
        {"footnoteId": 2, "footnotesEn": "Another note.", "footnotesFr": "Une autre note."},
    ]
    result = summarize_cube_metadata(metadata)
    assert isinstance(result["footnote"], str)
    assert "2" in result["footnote"]
    assert "omitted" in result["footnote"]


def test_summarize_no_footnotes_omitted():
    """Metadata without footnotes has no footnote key in result."""
    metadata = _make_metadata([3])
    result = summarize_cube_metadata(metadata)
    assert "footnote" not in result


def test_summarize_next_steps_present():
    """Summary always includes _next_steps guidance string."""
    metadata = _make_metadata([5])
    result = summarize_cube_metadata(metadata)
    assert "_next_steps" in result
    assert "get_sdmx_structure" in result["_next_steps"]
    assert "get_series_info" in result["_next_steps"]


def test_summarize_does_not_mutate_original():
    """Original metadata dict is not modified."""
    metadata = _make_metadata([50])
    original_count = len(metadata["dimension"][0]["member"])
    summarize_cube_metadata(metadata)
    assert len(metadata["dimension"][0]["member"]) == original_count
