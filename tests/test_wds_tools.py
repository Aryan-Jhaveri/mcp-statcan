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
