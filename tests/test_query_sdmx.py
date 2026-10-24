"""Tests for query_sdmx — SDMX fetch + ephemeral SQL, available in HTTP mode."""

import pytest
import respx
from httpx import Response

from src import config
from src.api.sdmx.sdmx_tools import register_sdmx_tools
from src.server import create_server, registry as server_registry
from src.util.registry import ToolRegistry
from tests.test_fetch_sdmx_to_database import DATA_URL, N_PERIODS, _make_response


@pytest.fixture
def registry():
    reg = ToolRegistry()
    register_sdmx_tools(reg)
    return reg


@pytest.mark.asyncio
@respx.mock
async def test_aggregates_over_uncapped_rows(registry):
    respx.get(DATA_URL).mock(return_value=Response(200, json=_make_response(first_value="0.0")))

    result = await registry.call_tool(
        "query_sdmx",
        {
            "productId": 18100004,
            "key": "1+2.1",
            "sql": 'SELECT "Geography", COUNT(*) AS n, MAX(value) AS peak FROM data GROUP BY 1 ORDER BY 1',
        },
    )

    assert result["fetched_row_count"] == 2 * N_PERIODS  # above MAX_SDMX_ROWS
    assert result["rows"] == [
        {"Geography": "Canada", "n": N_PERIODS, "peak": float(N_PERIODS - 1)},
        {"Geography": "Ontario", "n": N_PERIODS, "peak": float(N_PERIODS - 1)},
    ]
    assert result["_sdmx_url"].startswith(DATA_URL)


@pytest.mark.asyncio
@respx.mock
async def test_value_is_numeric_not_lexicographic(registry):
    respx.get(DATA_URL).mock(return_value=Response(200, json=_make_response(first_value="0.0")))

    result = await registry.call_tool(
        "query_sdmx",
        {"productId": 18100004, "key": "1+2.1", "sql": "SELECT typeof(value) AS t, MAX(value) AS m FROM data"},
    )

    # As TEXT, MAX would be '99.0'; as REAL it's the true maximum
    assert result["rows"] == [{"t": "real", "m": float(N_PERIODS - 1)}]


@pytest.mark.asyncio
@respx.mock
async def test_bad_sql_returns_table_columns(registry):
    respx.get(DATA_URL).mock(return_value=Response(200, json=_make_response()))

    result = await registry.call_tool(
        "query_sdmx", {"productId": 18100004, "key": "1+2.1", "sql": "SELECT geo FROM data"}
    )

    assert "no such column" in result["error"]
    assert "Geography" in result["table_columns"]
    assert "value" in result["table_columns"]


@pytest.mark.asyncio
@respx.mock
async def test_write_statement_rejected(registry):
    respx.get(DATA_URL).mock(return_value=Response(200, json=_make_response()))

    result = await registry.call_tool(
        "query_sdmx", {"productId": 18100004, "key": "1+2.1", "sql": "DELETE FROM data"}
    )

    assert "error" in result


@pytest.mark.asyncio
@respx.mock
async def test_fetch_above_row_limit_rejected(registry, monkeypatch):
    import src.api.sdmx.sdmx_tools as sdmx_tools

    monkeypatch.setattr(sdmx_tools, "MAX_EPHEMERAL_ROWS", 100)
    respx.get(DATA_URL).mock(return_value=Response(200, json=_make_response()))

    result = await registry.call_tool(
        "query_sdmx", {"productId": 18100004, "key": "1+2.1", "sql": "SELECT 1"}
    )

    assert "row limit" in result["error"]


@pytest.mark.asyncio
async def test_last_n_with_period_range_rejected(registry):
    with pytest.raises(ValueError, match="lastNObservations"):
        await registry.call_tool(
            "query_sdmx",
            {"productId": 18100004, "key": "1.1", "sql": "SELECT 1",
             "lastNObservations": 5, "endPeriod": "2020"},
        )


def test_registered_in_http_mode():
    server_registry._tools.clear()
    server_registry._handlers.clear()
    create_server(http_mode=True)
    names = {t.name for t in server_registry._tools}
    assert "query_sdmx" in names
    assert "fetch_sdmx_to_database" not in names


@pytest.mark.asyncio
@respx.mock
async def test_concurrent_queries_bounded(registry, monkeypatch):
    import asyncio
    import threading
    import src.api.sdmx.sdmx_tools as sdmx_tools

    monkeypatch.setattr(sdmx_tools, "_query_slots", asyncio.Semaphore(2))
    active, peak, lock = 0, 0, threading.Lock()
    real = sdmx_tools.run_ephemeral_query

    def tracked(rows, sql):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            import time
            time.sleep(0.05)
            return real(rows, sql)
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(sdmx_tools, "run_ephemeral_query", tracked)
    respx.get(DATA_URL).mock(return_value=Response(200, json=_make_response()))

    args = {"productId": 18100004, "key": "1+2.1", "sql": "SELECT COUNT(*) AS n FROM data"}
    results = await asyncio.gather(*[registry.call_tool("query_sdmx", args) for _ in range(6)])

    assert all(r["rows"] == [{"n": 2 * N_PERIODS}] for r in results)
    assert peak == 2
