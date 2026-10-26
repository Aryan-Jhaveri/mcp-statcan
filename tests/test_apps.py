"""MCP Apps (io.modelcontextprotocol/ui): view resource, tool binding, summary-for-model."""

import json
import re

import pytest
import respx
from mcp import Client
from mcp.client.extension import ClientExtension

from src.api.apps import APP_MIME_TYPE, EXTENSION_ID, SERIES_VIEW_URI, summarize_rows_result
from src.server import create_server, registry
from tests.sdmx_fixtures import N_PERIODS, make_data_xml, mock_sdmx


class AppsCapableClient(ClientExtension):
    """What an Apps host (e.g. Claude) advertises in initialize."""

    identifier = EXTENSION_ID

    def settings(self):
        return {"mimeTypes": [APP_MIME_TYPE]}


@pytest.fixture
def server():
    registry._tools.clear()
    registry._handlers.clear()
    registry._app_summaries.clear()
    yield create_server(http_mode=True)
    registry._tools.clear()
    registry._handlers.clear()
    registry._app_summaries.clear()


@pytest.mark.asyncio
async def test_view_resource_listed_and_readable(server):
    async with Client(server) as client:
        assert EXTENSION_ID in (client.server_capabilities.extensions or {})
        resources = (await client.list_resources()).resources
        view = next(r for r in resources if str(r.uri) == SERIES_VIEW_URI)
        assert view.mime_type == APP_MIME_TYPE
        contents = (await client.read_resource(SERIES_VIEW_URI)).contents[0]

    assert contents.mime_type == APP_MIME_TYPE
    html = contents.text
    assert html.lstrip().lower().startswith("<!doctype html")
    # Self-contained: the default MCP Apps CSP blocks all network access
    assert not re.search(r'<(script|link)[^>]+(src|href)="https?://', html)
    assert "<script" in html and "<style" in html


@pytest.mark.asyncio
async def test_unknown_resource_is_error(server):
    async with Client(server) as client:
        with pytest.raises(Exception):
            await client.read_resource("ui://statcan/nope.html")


@pytest.mark.asyncio
async def test_tools_bound_to_view(server):
    async with Client(server) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
    for name in ("get_sdmx_data", "get_sdmx_vector_data", "query_sdmx"):
        assert tools[name].meta["ui"]["resourceUri"] == SERIES_VIEW_URI
    assert tools["get_sdmx_rows"].meta is None  # rows-for-the-model tool has no view


@pytest.mark.asyncio
@respx.mock
async def test_apps_client_gets_summary_text_and_full_structured(server):
    mock_sdmx(make_data_xml(first_value="0.0"))
    async with Client(server, extensions=[AppsCapableClient()]) as client:
        await client.list_tools()
        result = await client.call_tool("get_sdmx_data", {"productId": 18100004, "key": "1+2.1"})

    text = json.loads(result.content[0].text)
    assert "data" not in text  # rows are not in the model's text
    assert text["series_count"] == 2 and text["row_count"] == 2 * N_PERIODS
    assert {s["label"] for s in text["series"]} == {"Canada", "Ontario"}
    assert len(result.structured_content["data"]) == 500  # the view gets the rows
    assert len(result.content[0].text) < len(json.dumps(result.structured_content)) / 10


@pytest.mark.asyncio
@respx.mock
async def test_plain_client_still_gets_full_text(server):
    mock_sdmx(make_data_xml(first_value="0.0"))
    async with Client(server) as client:
        await client.list_tools()
        result = await client.call_tool("get_sdmx_data", {"productId": 18100004, "key": "1+2.1"})
    assert len(json.loads(result.content[0].text)["data"]) == 500


@pytest.mark.asyncio
@respx.mock
async def test_query_sdmx_keeps_result_text_for_apps_clients(server):
    mock_sdmx(make_data_xml(first_value="0.0"))
    async with Client(server, extensions=[AppsCapableClient()]) as client:
        await client.list_tools()
        result = await client.call_tool(
            "query_sdmx", {"productId": 18100004, "key": "1+2.1", "sql": "SELECT COUNT(*) AS n FROM data"}
        )
    assert json.loads(result.content[0].text)["rows"] == [{"n": 2 * N_PERIODS}]  # the answer stays visible


def test_summary_per_series_stats():
    rows = [
        {"Geography": g, "Products": "All-items", "_series_key": k, "period": p, "value": v, "UOM": "2002=100"}
        for g, k, vals in (("Canada", "2.2", ["169.9", "169.8", "170.0"]), ("Ontario", "6.2", ["171.0", None, "172.5"]))
        for p, v in zip(("2026-07", "2026-08", "2026-09"), vals)
    ]
    s = summarize_rows_result({"_sdmx_url": "u", "row_count": 6, "data": rows, "_truncated": False})
    assert s["shared_dimensions"] == {"Products": "All-items"}
    can = next(x for x in s["series"] if x["label"] == "Canada")
    assert can["last"] == {"period": "2026-09", "value": 170.0}
    assert can["min"] == {"period": "2026-08", "value": 169.8}
    ont = next(x for x in s["series"] if x["label"] == "Ontario")
    assert ont["observations"] == 3 and ont["max"]["value"] == 172.5
