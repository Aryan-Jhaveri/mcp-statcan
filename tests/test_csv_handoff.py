"""Experimental CSV handoff (#169): STATCAN_CSV_HANDOFF=off|embedded|embedded+text|link."""

import pytest
import respx
from mcp import Client
from mcp.types import EmbeddedResource, ResourceLink, TextContent

from src.server import create_server, registry
from src.util.csv_handoff import csv_uri, handoff_mode, parse_csv_uri
from tests.sdmx_fixtures import make_data_xml, mock_sdmx

ARGS = {"productId": 18100004, "key": "1+2.1", "format": "csv", "lastNObservations": 3}


def _server(monkeypatch, mode=None):
    if mode is None:
        monkeypatch.delenv("STATCAN_CSV_HANDOFF", raising=False)
    else:
        monkeypatch.setenv("STATCAN_CSV_HANDOFF", mode)
    registry._tools.clear()
    registry._handlers.clear()
    return create_server(http_mode=True, toolset="core")


@pytest.fixture(autouse=True)
def _clean_registry():
    yield
    registry._tools.clear()
    registry._handlers.clear()


async def _call(server, args=ARGS):
    async with Client(server) as client:
        result = await client.call_tool("get_sdmx_data", args)  # validates structuredContent
    assert result.is_error is False, result.content[0].text
    return result


def test_uri_round_trip():
    assert csv_uri(ARGS) == "statcan://csv/18100004/1+2.1?lastNObservations=3"
    assert parse_csv_uri(csv_uri(ARGS)) == ARGS
    vec = {"vectorId": 2063945, "startPeriod": "2025-01", "sql": "SELECT * FROM data WHERE value > 1", "format": "csv"}
    assert parse_csv_uri(csv_uri(vec)) == vec
    wild = {"productId": 15100032, "key": "7...", "format": "csv"}
    assert csv_uri(wild) == "statcan://csv/15100032/7..."
    assert parse_csv_uri(csv_uri(wild)) == wild


def test_unknown_mode_is_rejected(monkeypatch):
    monkeypatch.setenv("STATCAN_CSV_HANDOFF", "nope")
    with pytest.raises(ValueError, match="off, embedded"):
        handoff_mode()


@pytest.mark.asyncio
@respx.mock
async def test_off_is_unchanged(monkeypatch):
    mock_sdmx(make_data_xml(first_value="0.0"))
    result = await _call(_server(monkeypatch))
    assert [type(c) for c in result.content] == [TextContent, TextContent]
    assert result.content[1].text == result.structured_content["csv"]
    async with Client(_server(monkeypatch)) as client:
        assert client.server_capabilities.resources is None  # no resources off


@pytest.mark.asyncio
@respx.mock
async def test_embedded_sends_a_resource_and_no_raw_text(monkeypatch):
    mock_sdmx(make_data_xml(first_value="0.0"))
    result = await _call(_server(monkeypatch, "embedded"))
    assert [type(c) for c in result.content] == [TextContent, EmbeddedResource]
    res = result.content[1].resource
    assert res.mime_type == "text/csv"
    assert res.uri == "statcan://csv/18100004/1+2.1?lastNObservations=3"
    assert res.text == result.structured_content["csv"]
    assert '"format":"csv"' in result.content[0].text


@pytest.mark.asyncio
@respx.mock
async def test_embedded_plus_text_sends_both(monkeypatch):
    mock_sdmx(make_data_xml(first_value="0.0"))
    result = await _call(_server(monkeypatch, "embedded+text"))
    assert [type(c) for c in result.content] == [TextContent, EmbeddedResource, TextContent]
    assert result.content[2].text == result.content[1].resource.text


@pytest.mark.asyncio
@respx.mock
async def test_json_results_are_untouched_by_the_flag(monkeypatch):
    mock_sdmx(make_data_xml(first_value="0.0"))
    result = await _call(_server(monkeypatch, "embedded"), {**ARGS, "format": "json"})
    assert [type(c) for c in result.content] == [TextContent]


@pytest.mark.asyncio
@respx.mock
async def test_link_is_readable_statelessly(monkeypatch):
    mock_sdmx(make_data_xml(first_value="0.0"))
    server = _server(monkeypatch, "link")
    async with Client(server) as client:
        result = await client.call_tool("get_sdmx_data", ARGS)
        assert [type(c) for c in result.content] == [TextContent, ResourceLink]
        link = result.content[1]
        assert link.mime_type == "text/csv" and link.uri.startswith("statcan://csv/18100004/")
        assert link.size == len(result.structured_content["csv"].encode("utf-8"))
        read = await client.read_resource(link.uri)  # re-fetches; nothing stored
        assert read.contents[0].text == result.structured_content["csv"]
        assert read.contents[0].mime_type == "text/csv"
        templates = await client.list_resource_templates()
        assert {t.name for t in templates.resource_templates} == {"sdmx_csv", "vector_csv"}
        assert (await client.list_resources()).resources == []
        assert client.server_capabilities.resources is not None
