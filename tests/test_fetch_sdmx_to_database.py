"""Tests for fetch_sdmx_to_database — SDMX fetch stored straight to SQLite."""

import sqlite3

import pytest
import respx

from src import config
from src.api.composite_tools import register_composite_tools
from src.api.sdmx.sdmx_tools import register_sdmx_tools
from src.util.registry import ToolRegistry
from tests.sdmx_fixtures import DATA_URL, N_PERIODS, make_data_xml, mock_sdmx

@pytest.fixture
def registry(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_FILE", str(tmp_path / "test.db"))
    reg = ToolRegistry()
    register_composite_tools(reg)
    register_sdmx_tools(reg)
    return reg


@pytest.mark.asyncio
@respx.mock
async def test_stores_all_rows_and_returns_compact_summary(registry):
    mock_sdmx(make_data_xml())

    result = await registry.call_tool(
        "fetch_sdmx_to_database",
        {"productId": 18100004, "key": "1+2.1", "table_name": "cpi", "sample_size": 3},
    )

    assert result["rows_inserted"] == 2 * N_PERIODS
    assert result["series_count"] == 2
    assert result["period_range"] == ["1700", str(1700 + N_PERIODS - 1)]
    assert len(result["sample"]) == 3
    assert "data" not in result
    assert result["_sdmx_url"].startswith(DATA_URL)

    with sqlite3.connect(config.DB_FILE) as conn:
        (count,) = conn.execute('SELECT COUNT(*) FROM "cpi"').fetchone()
        geos = {g for (g,) in conn.execute('SELECT DISTINCT "Geography" FROM "cpi"')}
    assert count == 2 * N_PERIODS
    assert geos == {"Canada", "Ontario"}


@pytest.mark.asyncio
@respx.mock
async def test_null_first_value_still_gets_numeric_column(registry):
    mock_sdmx(make_data_xml(first_value=None))

    await registry.call_tool(
        "fetch_sdmx_to_database", {"productId": 18100004, "key": "1+2.1", "table_name": "cpi"}
    )

    with sqlite3.connect(config.DB_FILE) as conn:
        cols = {name: ctype for _, name, ctype, *_ in conn.execute('PRAGMA table_info("cpi")')}
        (max_value,) = conn.execute('SELECT MAX("value") FROM "cpi"').fetchone()
    assert cols["value"] == "REAL"
    assert max_value == float(N_PERIODS - 1)


@pytest.mark.asyncio
async def test_last_n_with_period_range_rejected(registry):
    with pytest.raises(ValueError, match="lastNObservations"):
        await registry.call_tool(
            "fetch_sdmx_to_database",
            {"productId": 18100004, "key": "1.1", "table_name": "cpi",
             "lastNObservations": 5, "startPeriod": "2020"},
        )


@pytest.mark.asyncio
@respx.mock
async def test_empty_response_returns_error_without_creating_table(registry):
    mock_sdmx(make_data_xml(empty=True))

    result = await registry.call_tool(
        "fetch_sdmx_to_database", {"productId": 18100004, "key": "1+2.1", "table_name": "cpi"}
    )

    assert "error" in result
    with sqlite3.connect(config.DB_FILE) as conn:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE name='cpi'").fetchall()
    assert tables == []


@pytest.mark.asyncio
async def test_invalid_table_name(registry):
    result = await registry.call_tool(
        "fetch_sdmx_to_database", {"productId": 18100004, "key": "1.1", "table_name": "bad-name"}
    )
    assert "Invalid table name" in result["error"]


@pytest.mark.asyncio
@respx.mock
async def test_get_sdmx_data_still_caps_rows(registry):
    mock_sdmx(make_data_xml())

    result = await registry.call_tool("get_sdmx_data", {"productId": 18100004, "key": "1+2.1"})

    assert result["row_count"] == 2 * N_PERIODS
    assert len(result["data"]) == config.MAX_SDMX_ROWS
    assert result["_truncated"] is True
