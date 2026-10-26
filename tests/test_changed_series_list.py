"""Tests for the StatCan changed-series list endpoint."""

import pytest
import respx
from httpx import Response

from src.api.vector import register_vector_tools
from src.config import BASE_URL
from src.util.registry import ToolRegistry

CHANGED_SERIES_LIST_URL = f"{BASE_URL}/getChangedSeriesList"


@pytest.fixture
def registry():
    tool_registry = ToolRegistry()
    register_vector_tools(tool_registry)
    return tool_registry


@pytest.mark.asyncio
@respx.mock
async def test_get_changed_series_list_calls_undated_endpoint(registry):
    route = respx.get(CHANGED_SERIES_LIST_URL).mock(
        return_value=Response(
            200,
            json={
                "status": "SUCCESS",
                "object": [{"vectorId": 41690973, "productId": 18100004}],
            },
        )
    )

    result = await registry.call_tool("get_changed_series_list", {})

    assert route.called
    assert str(route.calls.last.request.url) == CHANGED_SERIES_LIST_URL
    assert result == [{"vectorId": 41690973, "productId": 18100004}]


@pytest.mark.asyncio
@respx.mock
async def test_get_changed_series_list_explains_pre_release_response(registry):
    respx.get(CHANGED_SERIES_LIST_URL).mock(
        return_value=Response(
            409, json={"message": "The product is not released yet"}
        )
    )

    with pytest.raises(ValueError) as exc_info:
        await registry.call_tool("get_changed_series_list", {})

    message = str(exc_info.value)
    assert "No changed series have been released yet today" in message
    assert "08:30 ET" in message
    assert "get_changed_cube_list(date)" in message


def test_get_changed_series_list_has_no_date_argument(registry):
    tool = registry.get_tool("get_changed_series_list")

    assert tool.input_schema["properties"] == {}
    assert tool.input_schema["required"] == []
    assert "updated today" in tool.description
    assert "get_changed_cube_list(date)" in tool.description
