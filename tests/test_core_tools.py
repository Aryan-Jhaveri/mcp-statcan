"""Core toolset (STATCAN_TOOLSET=core, #138), with StatCan mocked by respx.

Calls go through the SDK's in-memory Client, which validates structuredContent
against each tool's outputSchema and raises on a mismatch.
"""

import json

import pytest
import respx
from httpx import Response
from mcp import Client

from src.config import BASE_URL, SDMX_BASE_URL
from src.server import create_server, registry, resolve_toolset
from tests.sdmx_fixtures import DATA_URL, DSD_XML, N_PERIODS, STRUCTURE_URL, make_data_xml, mock_sdmx

WDS = BASE_URL.rstrip("/")
CORE = {"search_cubes_by_title", "get_sdmx_structure", "get_sdmx_data", "get_series_info", "get_changes"}


def _fresh(http_mode: bool = True, toolset=None):
    registry._tools.clear()
    registry._handlers.clear()
    return create_server(http_mode=http_mode, toolset=toolset)


@pytest.fixture
def server():
    yield _fresh(True, "core")
    registry._tools.clear()
    registry._handlers.clear()


async def _call(server, name, args, expect_error=False):
    async with Client(server) as client:
        result = await client.call_tool(name, args)  # raises if structuredContent mismatches
    assert result.is_error is expect_error, result.content[0].text
    if expect_error:
        return result.content[0].text
    return result.structured_content


# ── Toolset selection ──────────────────────────────────────────────────────

def test_env_var_selects_toolset(monkeypatch):
    monkeypatch.setenv("STATCAN_TOOLSET", "core")
    _fresh(True)
    assert {t.name for t in registry.get_tools()} == CORE

    monkeypatch.delenv("STATCAN_TOOLSET")
    _fresh(True)
    names = {t.name for t in registry.get_tools()}
    assert "query_sdmx" in names and "get_changes" not in names  # legacy is the default

    monkeypatch.setenv("STATCAN_TOOLSET", "nope")
    with pytest.raises(ValueError, match="legacy, core"):
        resolve_toolset()


def test_stdio_core_keeps_database_tools():
    _fresh(False, "core")
    names = {t.name for t in registry.get_tools()}
    assert CORE <= names
    assert {"fetch_sdmx_to_database", "query_database"} <= names
    assert not names & {"query_sdmx", "get_sdmx_vector_data", "get_code_sets", "get_cube_metadata"}


def test_core_schemas_are_compact_and_annotated(server):
    for tool in registry.get_tools():
        assert tool.annotations.read_only_hint is True
        text = json.dumps(tool.input_schema)
        assert '"title"' not in text and '"anyOf"' not in text, tool.name
    data = registry.get_tool("get_sdmx_data")
    assert data.input_schema["properties"]["vectorId"] == {
        "type": "integer", "description": "Instead of productId + key: one series.",
    }


# ── get_sdmx_data ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_data_by_key_summarizes_large_results(server):
    mock_sdmx(make_data_xml(first_value="0.0"))
    sc = await _call(server, "get_sdmx_data", {"productId": 18100004, "key": "1+2.1"})
    assert sc["summary"] is True and sc["row_count"] == 2 * N_PERIODS
    assert "sql" in sc["_message"]
    assert sc["_sdmx_url"].startswith(DATA_URL)


@pytest.mark.asyncio
@respx.mock
async def test_data_by_vector_id(server):
    respx.get(STRUCTURE_URL).mock(return_value=Response(200, text=DSD_XML))
    route = respx.get(f"{SDMX_BASE_URL}vector/v41690973").mock(
        return_value=Response(200, text=make_data_xml(first_value="0.0"))
    )
    sc = await _call(server, "get_sdmx_data", {"vectorId": 41690973, "lastNObservations": 3, "full": True})
    assert route.calls[0].request.url.params["lastNObservations"] == "3"
    assert sc["series"][0]["Geography"] == "Canada"
    assert sc["_sdmx_url"].startswith(f"{SDMX_BASE_URL}vector/v41690973")


@pytest.mark.asyncio
@respx.mock
async def test_data_with_sql_runs_over_all_rows(server):
    mock_sdmx(make_data_xml(first_value="0.0"))
    sc = await _call(server, "get_sdmx_data", {
        "productId": 18100004, "key": "1+2.1",
        "sql": 'SELECT "Geography", COUNT(*) AS n FROM data GROUP BY 1 ORDER BY 1',
    })
    assert sc["fetched_row_count"] == 2 * N_PERIODS
    assert sc["rows"] == [{"Geography": "Canada", "n": N_PERIODS}, {"Geography": "Ontario", "n": N_PERIODS}]


@pytest.mark.asyncio
@respx.mock
async def test_data_with_bad_sql_is_an_error_listing_columns(server):
    mock_sdmx(make_data_xml())
    text = await _call(server, "get_sdmx_data", {
        "productId": 18100004, "key": "1+2.1", "sql": "SELECT nope FROM data",
    }, expect_error=True)
    assert "table_columns" in text and "Geography" in text


@pytest.mark.asyncio
@pytest.mark.parametrize("args, match", [
    ({"productId": 18100004}, "key is required"),
    ({}, "productId \\+ key, or vectorId"),
    ({"vectorId": 1, "productId": 18100004, "key": "1.1"}, "not both"),
])
async def test_data_argument_errors_explain_the_fix(server, args, match):
    with pytest.raises(ValueError, match=match):
        await registry.call_tool("get_sdmx_data", args)


@pytest.mark.asyncio
async def test_numeric_key_is_explained(server):
    with pytest.raises(ValueError, match='must be a string such as "2.2"'):
        await registry.call_tool("get_sdmx_data", {"productId": 18100004, "key": 2.2})


@pytest.mark.asyncio
async def test_unknown_argument_is_rejected(server):
    with pytest.raises(ValueError, match="vector_id"):
        await registry.call_tool("get_sdmx_data", {"vector_id": 1})


# ── get_sdmx_structure ──────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_structure_search_finds_codes_by_label(server):
    respx.get(STRUCTURE_URL).mock(return_value=Response(200, text=DSD_XML))
    sc = await _call(server, "get_sdmx_structure", {"productId": 18100004, "search": "ontario; nothing"})
    assert sc["key_template"] == "Geography.Products"
    geo, products = sc["dimensions"]
    assert geo["codes"] == [{"id": "2", "name": "Ontario", "parent": "1"}]
    # No match in Products: its usual preview is shown, flagged
    assert products["_no_match"] is True and products["codes"][0]["name"] == "All-items"


@pytest.mark.asyncio
@respx.mock
async def test_structure_dimension_lists_codes_and_leaf_key(server):
    respx.get(STRUCTURE_URL).mock(return_value=Response(200, text=DSD_XML))
    sc = await _call(server, "get_sdmx_structure", {"productId": 18100004, "dimension": 1})
    assert [d["id"] for d in sc["dimensions"]] == ["Geography"]
    assert sc["leaf_key"] == "2"  # Canada is Ontario's parent

    with pytest.raises(ValueError, match="No dimension at position 5"):
        await registry.call_tool("get_sdmx_structure", {"productId": 18100004, "dimension": 5})


# ── get_series_info ─────────────────────────────────────────────────────────

_CODE_SETS = {"status": "SUCCESS", "object": {
    "frequency": [{"frequencyCode": 6, "frequencyDescEn": "Monthly"}],
    "scalar": [{"scalarFactorCode": 0, "scalarFactorDescEn": "units"}],
    "uom": [{"memberUomCode": 17, "memberUomEn": "2002=100"}],
}}


def _series(vector_id, coordinate):
    return {"status": "SUCCESS", "object": {
        "responseStatusCode": 0, "productId": 18100004, "coordinate": coordinate, "vectorId": vector_id,
        "frequencyCode": 6, "scalarFactorCode": 0, "decimals": 1, "terminated": 0,
        "SeriesTitleEn": "Ontario;All-items", "SeriesTitleFr": "Ontario;Ensemble", "memberUomCode": 17,
    }}


@pytest.mark.asyncio
@respx.mock
async def test_series_info_by_coordinate_and_vector(server, monkeypatch):
    from src.api import metadata_tools

    monkeypatch.setattr(metadata_tools, "_code_sets_cache", None)
    respx.get(f"{WDS}/getCodeSets").mock(return_value=Response(200, json=_CODE_SETS))
    by_coord = respx.post(f"{WDS}/getSeriesInfoFromCubePidCoord").mock(return_value=Response(200, json=[
        _series(41691919, "14.2.0.0.0.0.0.0.0.0"), {"status": "FAILED", "object": "bad coordinate"},
    ]))
    by_vector = respx.post(f"{WDS}/getSeriesInfoFromVector").mock(
        return_value=Response(200, json=[_series(41690973, "2.2.0.0.0.0.0.0.0.0")])
    )

    result = await registry.call_tool("get_series_info", {
        "productId": 18100004, "coordinates": ["14.2", "99.9"], "vectorIds": [41690973],
    })
    assert json.loads(by_coord.calls[0].request.content)[0] == {
        "productId": 18100004, "coordinate": "14.2.0.0.0.0.0.0.0.0",
    }
    assert json.loads(by_vector.calls[0].request.content) == [{"vectorId": 41690973}]
    assert result["series"][0] == {
        "vectorId": 41691919, "productId": 18100004, "key": "14.2", "title": "Ontario;All-items",
        "frequency": "Monthly", "uom": "2002=100", "scalar": "units", "decimals": 1,
    }
    assert result["series"][1]["key"] == "2.2"
    assert result["failures"] == [{"productId": 18100004, "coordinate": "99.9", "error": "bad coordinate"}]


@pytest.mark.asyncio
async def test_series_info_needs_an_input(server):
    with pytest.raises(ValueError, match="coordinates need productId"):
        await registry.call_tool("get_series_info", {"coordinates": ["1.1"]})
    with pytest.raises(ValueError, match="or vectorIds"):
        await registry.call_tool("get_series_info", {"productId": 1})


# ── get_changes ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_changes_by_date_pages_and_adds_titles(server):
    from src.util import cache

    cache.invalidate_cache()
    respx.get(f"{WDS}/getAllCubesList").mock(return_value=Response(200, json=[
        {"productId": 36100478, "cubeTitleEn": "Supply and use tables", "archived": "2", "dimensions": []},
    ]))
    respx.get(f"{WDS}/getChangedCubeList/2026-11-05").mock(return_value=Response(200, json={
        "status": "SUCCESS",
        "object": [{"productId": p, "releaseTime": "2026-11-05T08:30"} for p in (36100478, 1, 2)],
    }))
    try:
        result = await registry.call_tool("get_changes", {"date": "2026-11-05", "limit": 2})
    finally:
        cache.invalidate_cache()
    assert result["total"] == 3 and result["next_offset"] == 2 and result["date"] == "2026-11-05"
    assert result["tables"][0] == {
        "productId": 36100478, "title": "Supply and use tables", "releaseTime": "2026-11-05T08:30",
    }

    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        await registry.call_tool("get_changes", {"date": "Nov 5"})


@pytest.mark.asyncio
@respx.mock
async def test_changes_for_one_series(server):
    respx.post(f"{WDS}/getChangedSeriesDataFromVector").mock(return_value=Response(404))
    none = await registry.call_tool("get_changes", {"vectorId": 41691919})
    assert none["changed"] is False and none["vectorId"] == 41691919

    route = respx.post(f"{WDS}/getChangedSeriesDataFromCubePidCoord").mock(return_value=Response(200, json=[
        {"status": "SUCCESS", "object": {"vectorId": 41691919, "vectorDataPoint": [{"value": 170.3}]}},
    ]))
    changed = await registry.call_tool("get_changes", {"productId": 18100004, "coordinate": "14.2"})
    assert json.loads(route.calls[0].request.content) == [
        {"productId": 18100004, "coordinate": "14.2.0.0.0.0.0.0.0.0"},
    ]
    assert changed["changed"] is True and changed["vectorDataPoint"] == [{"value": 170.3}]


@pytest.mark.asyncio
@respx.mock
async def test_changes_in_one_table_today(server):
    respx.get(f"{WDS}/getChangedSeriesList").mock(return_value=Response(200, json={
        "status": "SUCCESS",
        "object": [{"vectorId": v, "productId": p} for v, p in ((1, 18100004), (2, 14100287), (3, 18100004))],
    }))
    result = await registry.call_tool("get_changes", {"productId": 18100004})
    assert [s["vectorId"] for s in result["series"]] == [1, 3] and result["total"] == 2

    with pytest.raises(ValueError, match="only available for today"):
        await registry.call_tool("get_changes", {"productId": 18100004, "date": "2026-11-05"})
