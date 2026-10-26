"""WDS tool request/response handling, with StatCan mocked by respx."""

import json

import httpx
import pytest
import respx
from httpx import Response

from src.config import BASE_URL
from src.server import create_server, registry

WDS = BASE_URL.rstrip("/")


@pytest.fixture
def server():
    registry._tools.clear()
    registry._handlers.clear()
    yield create_server(http_mode=True)
    registry._tools.clear()
    registry._handlers.clear()


@pytest.mark.asyncio
@respx.mock
async def test_bulk_vector_range_posts_documented_body(server):
    route = respx.post(f"{WDS}/getBulkVectorDataByRange").mock(
        return_value=Response(200, json=[{
            "status": "SUCCESS",
            "object": {
                "productId": 18100004, "coordinate": "2.2.0.0.0.0.0.0.0.0", "vectorId": 41690973,
                "vectorDataPoint": [{"refPer": "2026-09-01", "value": 170.0, "releaseTime": "2026-10-19T08:30"}],
            },
        }])
    )
    result = await registry.call_tool("get_bulk_vector_data_by_range", {
        "vectorIds": [41690973, 41691244],
        "startDataPointReleaseDate": "2026-10-01T08:30",
        "endDataPointReleaseDate": "2026-10-25T08:30",
    })

    assert json.loads(route.calls.last.request.content) == {
        "vectorIds": ["41690973", "41691244"],
        "startDataPointReleaseDate": "2026-10-01T08:30",
        "endDataPointReleaseDate": "2026-10-25T08:30",
    }
    assert result[0]["vectorId"] == 41690973 and result[0]["value"] == 170.0


@pytest.mark.asyncio
@respx.mock
async def test_changed_series_from_vector_404_means_no_change_today(server):
    respx.post(f"{WDS}/getChangedSeriesDataFromVector").mock(return_value=Response(404))
    result = await registry.call_tool("get_changed_series_data_from_vector", {"vectorId": 41690973})
    assert result["changed"] is False
    assert "08:30 ET" in result["message"]


@pytest.mark.asyncio
@respx.mock
async def test_changed_series_from_coord_404_means_no_change_today(server):
    respx.post(f"{WDS}/getChangedSeriesDataFromCubePidCoord").mock(return_value=Response(404))
    result = await registry.call_tool(
        "get_changed_series_data_from_cube_pid_coord", {"productId": 18100004, "coordinate": "2.2"}
    )
    assert result == {
        "productId": 18100004,
        "coordinate": "2.2.0.0.0.0.0.0.0.0",
        "changed": False,
        "message": result["message"],
    }


@pytest.mark.asyncio
@respx.mock
async def test_empty_network_error_names_exception_type(server):
    respx.post(f"{WDS}/getChangedSeriesDataFromVector").mock(side_effect=httpx.ReadTimeout(""))
    with pytest.raises(Exception, match="ReadTimeout"):
        await registry.call_tool("get_changed_series_data_from_vector", {"vectorId": 41690973})


@pytest.mark.parametrize("http_mode", [True, False])
def test_every_tool_has_annotations(http_mode):
    registry._tools.clear()
    registry._handlers.clear()
    create_server(http_mode=http_mode)
    missing = [t.name for t in registry.get_tools() if t.annotations is None]
    assert missing == []
    wds_read_only = {"search_cubes_by_title", "get_cube_metadata", "get_series_info", "get_code_sets"}
    assert all(registry.get_tool(n).annotations.read_only_hint for n in wds_read_only)


def _cube(pid, title, archived):
    return {
        "productId": pid, "cansimId": "x", "cubeTitleEn": title, "cubeTitleFr": "titre " + title,
        "cubeStartDate": "2000-01-01", "cubeEndDate": "2026-09-01", "frequencyCode": 6,
        "releaseTime": "2026-10-21T12:30", "archived": archived, "subjectCode": ["18"],
        "surveyCode": ["2301"], "corrections": [{"note": "long correction text"}],
    }


@pytest.mark.asyncio
@respx.mock
async def test_search_is_slim_current_first_and_always_an_envelope(server):
    from src.util import cache

    cache.invalidate_cache()
    respx.get(f"{WDS}/getAllCubesListLite").mock(return_value=Response(200, json=[
        _cube(1, "Consumer Price Index, old", "1"),
        _cube(2, "Consumer Price Index, monthly", "2"),
        _cube(3, "Labour force", "2"),
    ]))
    try:
        result = await registry.call_tool("search_cubes_by_title", {"search_term": "consumer price"})
        assert result["total_matches"] == 2 and result["showing"] == 2
        assert [c["productId"] for c in result["data"]] == [2, 1]
        assert result["data"][1] == {
            "productId": 1, "cubeTitleEn": "Consumer Price Index, old", "cubeStartDate": "2000-01-01",
            "cubeEndDate": "2026-09-01", "frequencyCode": 6, "releaseTime": "2026-10-21T12:30", "archived": True,
        }

        # French titles still match; no matches is an envelope too
        assert (await registry.call_tool("search_cubes_by_title", {"search_term": "titre labour"}))["showing"] == 1
        empty = await registry.call_tool("search_cubes_by_title", {"search_term": "zzz"})
        assert empty == {"data": [], "total_matches": 0, "showing": 0}
    finally:
        cache.invalidate_cache()


_CODE_SETS = {
    "status": "SUCCESS",
    "object": {
        "frequency": [{"frequencyCode": 6, "frequencyDescEn": "Monthly"}],
        "uom": [{"memberUomCode": i, "memberUomEn": "Percent" if i == 239 else f"Unit {i}"} for i in range(230, 260)],
    },
}


@pytest.mark.asyncio
@respx.mock
async def test_code_sets_summary_named_set_and_search(server, monkeypatch):
    from src.api import metadata_tools

    monkeypatch.setattr(metadata_tools, "_code_sets_cache", None)
    route = respx.get(f"{WDS}/getCodeSets").mock(return_value=Response(200, json=_CODE_SETS))

    summary = await registry.call_tool("get_code_sets", {})
    assert summary["frequency"] == _CODE_SETS["object"]["frequency"]
    assert "uom" not in summary and summary["_large_code_sets"] == {"uom": 30}

    found = await registry.call_tool("get_code_sets", {"code_set": "uom", "search": "percent"})
    assert found == {"uom": [{"memberUomCode": 239, "memberUomEn": "Percent"}], "count": 1}
    assert (await registry.call_tool("get_code_sets", {"code_set": "uom"}))["count"] == 30

    with pytest.raises(ValueError, match="Available: frequency, uom"):
        await registry.call_tool("get_code_sets", {"code_set": "nope"})
    assert route.call_count == 1  # cached
