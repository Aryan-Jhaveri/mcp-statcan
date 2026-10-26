"""DB tools (list_tables, get_table_schema, drop_table, query_database) with store views."""

import pytest
import pytest_asyncio
import respx

from src import config
from src.api.composite_tools import register_composite_tools
from src.db.queries import register_db_tools
from src.util.registry import ToolRegistry
from tests.sdmx_fixtures import N_PERIODS, make_data_xml, mock_sdmx


@pytest_asyncio.fixture
async def registry(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_FILE", str(tmp_path / "test.db"))
    reg = ToolRegistry()
    register_composite_tools(reg)
    register_db_tools(reg)
    with respx.mock:
        mock_sdmx(make_data_xml(first_value="0.0"))
        await reg.call_tool("fetch_sdmx_to_database", {"productId": 18100004, "key": "1+2.1", "table_name": "cpi"})
    return reg


@pytest.mark.asyncio
async def test_list_tables_includes_views_and_store(registry):
    result = await registry.call_tool("list_tables", {})
    assert "cpi" in result["tables"] and result["views"] == ["cpi"]
    assert {"_statcan_series", "_statcan_observations"} <= set(result["tables"])
    assert result["store"] == {"series": 2, "observations": 2 * N_PERIODS}


@pytest.mark.asyncio
async def test_schema_and_query_on_view(registry):
    schema = await registry.call_tool("get_table_schema", {"table_name": "cpi"})
    names = [c["name"] for c in schema["schema"]]
    assert names[:2] == ["Geography", "Products"] and "value" in names
    result = await registry.call_tool(
        "query_database", {"sql_query": 'SELECT "Geography", MAX(value) AS m FROM cpi GROUP BY 1 ORDER BY 1'}
    )
    assert result["rows"] == [{"Geography": "Canada", "m": float(N_PERIODS - 1)},
                              {"Geography": "Ontario", "m": float(N_PERIODS - 1)}]


@pytest.mark.asyncio
async def test_drop_view_keeps_store(registry):
    result = await registry.call_tool("drop_table", {"table_name": "cpi"})
    assert result["success"].startswith("View 'cpi'")
    tables = await registry.call_tool("list_tables", {})
    assert "cpi" not in tables["tables"]
    assert tables["store"]["observations"] == 2 * N_PERIODS


@pytest.mark.asyncio
async def test_store_tables_cannot_be_dropped(registry):
    result = await registry.call_tool("drop_table", {"table_name": "_statcan_observations"})
    assert "can't be dropped" in result["error"]
