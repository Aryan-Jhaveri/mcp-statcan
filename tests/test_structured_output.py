"""Tests for outputSchema / structuredContent / _meta / annotations in ToolRegistry + server.

Uses the SDK's in-memory Client, so the real client-side outputSchema validation runs.
"""

import json
from typing import Any, Dict, List, Optional

import pytest
from mcp import Client
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

from src.server import create_server, registry


class _EchoOutput(BaseModel):
    model_config = ConfigDict(extra="allow")
    url: str = Field(alias="_url")
    count: int
    items: List[Dict[str, Any]]
    note: Optional[str] = None


@pytest.fixture
def server():
    registry._tools.clear()
    registry._handlers.clear()
    srv = create_server(http_mode=True)

    @registry.tool(
        output_model=_EchoOutput,
        meta={"ui": {"resourceUri": "ui://test/view"}},
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    def echo_structured(count: int) -> Dict[str, Any]:
        """Return a structured payload."""
        if count < 0:
            return {"error": "count must be >= 0"}
        return {"_url": "https://example.test", "count": count, "items": [{"i": i} for i in range(count)]}

    @registry.tool()
    def echo_plain(count: int) -> Dict[str, Any]:
        """Return a plain payload."""
        return {"count": count}

    @registry.tool(output_model=_EchoOutput)
    def echo_wrong_shape() -> Dict[str, Any]:
        """Return a payload that violates its schema."""
        return {"count": "not-an-int"}

    yield srv
    registry._tools.clear()
    registry._handlers.clear()


@pytest.mark.asyncio
async def test_list_tools_publishes_schema_meta_annotations(server):
    async with Client(server) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}

    tool = tools["echo_structured"]
    assert tool.output_schema["type"] == "object"
    assert "_url" in tool.output_schema["properties"]
    assert set(tool.output_schema["required"]) == {"_url", "count", "items"}
    assert tool.meta == {"ui": {"resourceUri": "ui://test/view"}}
    assert tool.annotations.read_only_hint is True
    assert tools["echo_plain"].output_schema is None


@pytest.mark.asyncio
async def test_structured_content_returned_and_validated(server):
    async with Client(server) as client:
        await client.list_tools()
        result = await client.call_tool("echo_structured", {"count": 2})

    assert result.is_error is False
    assert result.structured_content == {
        "_url": "https://example.test", "count": 2, "items": [{"i": 0}, {"i": 1}],
    }
    assert json.loads(result.content[0].text) == result.structured_content  # text fallback carries the same data
    assert '"count":2' in result.content[0].text  # compact JSON


@pytest.mark.asyncio
async def test_tool_without_schema_has_no_structured_content(server):
    async with Client(server) as client:
        result = await client.call_tool("echo_plain", {"count": 1})

    assert result.structured_content is None
    assert result.is_error is False


@pytest.mark.asyncio
async def test_error_dict_flagged_as_tool_error(server):
    async with Client(server) as client:
        await client.list_tools()
        result = await client.call_tool("echo_structured", {"count": -1})

    assert result.is_error is True
    assert result.structured_content is None
    assert "count must be >= 0" in result.content[0].text


@pytest.mark.asyncio
async def test_schema_mismatch_is_caught_by_client(server):
    """Guards the contract: a wrong output_model breaks real clients, not just tests."""
    async with Client(server) as client:
        await client.list_tools()
        with pytest.raises(RuntimeError, match="Invalid structured content"):
            await client.call_tool("echo_wrong_shape", {})
