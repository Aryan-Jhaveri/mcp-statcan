"""fetch_vectors_to_database (WDS) writes into the same canonical store as SDMX fetches."""

import sqlite3

import pytest
import respx
from httpx import Response

from src import config
from src.api.composite_tools import register_composite_tools
from src.config import BASE_URL
from src.util.registry import ToolRegistry
from tests.sdmx_fixtures import make_data_xml, mock_sdmx

WDS_URL = f"{BASE_URL}/getDataFromVectorByReferencePeriodRange"


def _wds_response(values):
    return [{
        "status": "SUCCESS",
        "object": {
            "productId": 18100004, "coordinate": "1.1.0.0.0.0.0.0.0.0", "vectorId": 41690973,
            "vectorDataPoint": [
                {"refPer": f"{1700 + i}-01-01", "value": v, "frequencyCode": 12, "statusCode": 0,
                 "symbolCode": 0, "releaseTime": "2026-10-20T08:30"}
                for i, v in enumerate(values)
            ],
        },
    }]


@pytest.fixture
def registry(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_FILE", str(tmp_path / "test.db"))
    reg = ToolRegistry()
    register_composite_tools(reg)
    return reg


@pytest.mark.asyncio
@respx.mock
async def test_wds_fetch_creates_view(registry):
    respx.get(WDS_URL).mock(return_value=Response(200, json=_wds_response([1.0, 2.0, 3.0])))
    result = await registry.call_tool(
        "fetch_vectors_to_database", {"vectorIds": ["41690973"], "table_name": "cpi_vec"}
    )
    assert result["rows_inserted"] == 3 and result["new"] == 3
    with sqlite3.connect(config.DB_FILE) as conn:
        rows = conn.execute("SELECT period, value, VECTOR_ID, release_time FROM cpi_vec ORDER BY period").fetchall()
    assert rows[0] == ("1700", 1.0, 41690973, "2026-10-20T08:30")


@pytest.mark.asyncio
@respx.mock
async def test_wds_and_sdmx_fetches_share_rows(registry):
    # SDMX first: labels + 300 annual periods for series 1.1 (Canada) and 2.1 (Ontario)
    mock_sdmx(make_data_xml(first_value="0.0"))
    await registry.call_tool("fetch_sdmx_to_database", {"productId": 18100004, "key": "1+2.1", "table_name": "cpi"})

    # WDS for the same Canada series: two unchanged values, one revision
    respx.get(WDS_URL).mock(return_value=Response(200, json=_wds_response([0.0, 1.0, 9.9])))
    result = await registry.call_tool(
        "fetch_vectors_to_database", {"vectorIds": ["41690973"], "table_name": "cpi_vec"}
    )
    assert (result["new"], result["revised"], result["unchanged"]) == (0, 1, 2)

    with sqlite3.connect(config.DB_FILE) as conn:
        (series,) = conn.execute("SELECT COUNT(*) FROM _statcan_series").fetchone()
        geo = conn.execute('SELECT DISTINCT "Geography" FROM cpi_vec').fetchall()
    assert series == 2  # no duplicate series from the WDS path
    assert geo == [("Canada",)]  # WDS view picks up SDMX dimension labels


@pytest.mark.asyncio
@respx.mock
async def test_wds_no_points_is_error(registry):
    respx.get(WDS_URL).mock(return_value=Response(200, json=[{"status": "FAILED", "object": "bad vector"}]))
    result = await registry.call_tool("fetch_vectors_to_database", {"vectorIds": ["1"], "table_name": "x"})
    assert "No data points" in result["error"]
