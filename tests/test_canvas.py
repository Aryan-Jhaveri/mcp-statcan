"""render_view: model-built views over StatCan data (src/api/canvas.py)."""

import json
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest
import respx
from mcp import Client

from src import config
from src.api import canvas
from src.api.canvas import CANVAS_URI, ViewStore, period_to_date, standalone_html, view_store
from src.server import create_server, registry
from tests.sdmx_fixtures import N_PERIODS, mock_sdmx

CPI = {"productId": 18100004, "key": "1+2.1"}


def _fresh_server(http_mode: bool):
    registry._tools.clear()
    registry._handlers.clear()
    return create_server(http_mode=http_mode)


async def _render(args, http_mode=False):
    async with Client(_fresh_server(http_mode)) as client:
        result = await client.call_tool("render_view", args)  # validates structuredContent
    return result


def _payload_from_page(html: str) -> dict:
    m = re.search(r'<script type="application/json" id="statcan-payload">(.*?)</script>', html, re.S)
    assert m, "payload script missing"
    return json.loads(m.group(1))


@pytest.mark.parametrize(
    "period,date",
    [("2024", "2024-01-01"), ("2024-03", "2024-03-01"), ("2024-03-15", "2024-03-15"),
     ("2024-Q3", "2024-07-01"), ("2024-S2", "2024-07-01"), ("2024-W05", None), (None, None)],
)
def test_period_to_date(period, date):
    assert period_to_date(period) == date


@pytest.mark.asyncio
@respx.mock
async def test_local_view_binds_rows_and_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "VIEWS_DIR", str(tmp_path))
    mock_sdmx()

    result = await _render({"title": "CPI: Canada vs Ontario", "html": "<div id=c></div>", "data": {"cpi": CPI}})

    assert result.is_error is False, result.content[0].text
    ds = result.structured_content["datasets"]["cpi"]
    assert ds["row_count"] == 2 * N_PERIODS and not ds["truncated"]
    assert ds["rows"][1]["value"] == 1.0 and ds["rows"][1]["date"] == "1701-01-01"
    assert ds["source_url"].startswith(config.SDMX_BASE_URL)

    # The model gets a summary, not the rows
    text = json.loads(result.content[0].text)
    assert "html" not in text and len(text["datasets"]["cpi"]["sample"]) == 3
    assert text["datasets"]["cpi"]["columns"][:2] == ["Geography", "Products"]

    page = Path(urlparse(result.structured_content["url"]).path)
    assert page.parent == tmp_path and page.name.startswith("cpi-canada-vs-ontario-")
    embedded = _payload_from_page(page.read_text())
    assert embedded["html"] == "<div id=c></div>" and len(embedded["datasets"]["cpi"]["rows"]) == 2 * N_PERIODS
    assert result.structured_content.get("mcp_endpoint") is None


@pytest.mark.asyncio
@respx.mock
async def test_sql_shapes_the_dataset(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "VIEWS_DIR", str(tmp_path))
    mock_sdmx()

    result = await _render({
        "title": "Peaks",
        "vega_lite": {"mark": "bar", "data": {"name": "peaks"}},
        "data": {"peaks": {**CPI, "sql": 'SELECT "Geography", MAX(value) AS peak FROM data GROUP BY 1 ORDER BY 1'}},
    })

    ds = result.structured_content["datasets"]["peaks"]
    assert ds["rows"] == [{"Geography": "Canada", "peak": N_PERIODS - 1.0}, {"Geography": "Ontario", "peak": N_PERIODS - 1.0}]
    assert result.structured_content["vega_lite"]["mark"] == "bar"


@pytest.mark.asyncio
@respx.mock
async def test_hosted_view_is_stored_with_endpoint(monkeypatch):
    monkeypatch.setenv("RENDER_BASE_URL", "https://mcp-statcan.com")
    mock_sdmx()

    result = await _render({"title": "t", "html": "<p>hi</p>", "data": {"cpi": CPI}}, http_mode=True)

    sc = result.structured_content
    assert sc["url"] == f"https://mcp-statcan.com/views/{sc['view_id']}"
    assert sc["mcp_endpoint"] == "https://mcp-statcan.com/mcp"
    assert _payload_from_page(view_store.get(sc["view_id"]))["view_id"] == sc["view_id"]


@pytest.mark.asyncio
async def test_inline_rows_without_fetch(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "VIEWS_DIR", str(tmp_path))
    result = await _render({"title": "t", "html": "x", "data": {"s": {"rows": [{"period": "2025-Q1", "value": "3"}]}}})
    assert result.structured_content["datasets"]["s"]["rows"] == [{"period": "2025-Q1", "value": 3.0, "date": "2025-01-01"}]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "args,message",
    [
        ({"title": "t"}, "exactly one of html or vega_lite"),
        ({"title": "t", "html": "x", "vega_lite": {}}, "exactly one of html or vega_lite"),
        ({"title": "t", "html": "x", "data": {"a": {"productId": 1}}}, "needs a key"),
        ({"title": "t", "html": "x", "data": {"a": {"rows": [], "vectorId": 1}}}, "exactly one of"),
    ],
)
async def test_invalid_input_is_a_tool_error(args, message):
    result = await _render(args)
    assert result.is_error and message in result.content[0].text


@pytest.mark.asyncio
@respx.mock
async def test_bad_sql_names_the_dataset(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "VIEWS_DIR", str(tmp_path))
    mock_sdmx()
    result = await _render({"title": "t", "html": "x", "data": {"cpi": {**CPI, "sql": "SELECT nope FROM data"}}})
    assert result.is_error and "data.cpi: SQL failed" in result.content[0].text


@pytest.mark.asyncio
async def test_canvas_resource_is_served_with_csp():
    async with Client(_fresh_server(True)) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
        assert tools["render_view"].meta["ui"]["resourceUri"] == CANVAS_URI
        resources = (await client.list_resources()).resources
        assert [str(r.uri) for r in resources] == [CANVAS_URI]
        content = (await client.read_resource(CANVAS_URI)).contents[0]
    assert content.mime_type == "text/html;profile=mcp-app"
    assert "https://cdn.jsdelivr.net" in content.meta["ui"]["csp"]["resourceDomains"]
    assert "<head>" in content.text


def test_payload_cannot_close_its_script_tag():
    page = standalone_html({"view_id": "x", "title": "t", "html": "<script>1</script><!-- c -->", "datasets": {}})
    assert _payload_from_page(page)["html"] == "<script>1</script><!-- c -->"


def test_view_store_evicts_by_age_and_size(monkeypatch):
    now = [0.0]
    monkeypatch.setattr(canvas.time, "monotonic", lambda: now[0])
    store = ViewStore(ttl=10, max_views=2, max_bytes=100)
    store.put("a", "x" * 10)
    store.put("b", "x" * 10)
    store.put("c", "x" * 10)
    assert store.get("a") is None and store.get("c")  # over max_views
    store.put("big", "x" * 90)
    assert store.get("b") is None  # over max_bytes
    now[0] = 11
    assert store.get("c") is None and store.get("big") is None  # expired
