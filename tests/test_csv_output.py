"""Compact CSV output (#168): the renderer, and core get_sdmx_data(format="csv")."""

import csv
import io

import pytest
import respx

from src.config import MAX_SDMX_ROWS
from src.util.csv_output import format_value, series_csv, table_csv
from tests.sdmx_fixtures import N_PERIODS, make_data_xml, mock_sdmx
from tests.test_core_tools import _call, server  # noqa: F401  (fixture)


def _row(lang, stat, period, value, **extra):
    return {
        "Geography": "Ontario",
        "First_official_language_spoken": lang,
        "Statistics": stat,
        "_series_key": f"7.{lang[:1]}.{stat[:1]}",
        "VECTOR_ID": f"v-{lang}-{stat}",
        "DGUID": "2016A000235",
        "UOM": "Number" if stat == "Number" else "Percent",
        "period": period,
        "value": value,
        **extra,
    }


def _data_lines(text):
    return [line for line in text.splitlines() if not line.startswith("#")]


def test_format_value():
    assert format_value(None) == ""
    assert format_value(488918.0) == "488918"
    assert format_value(0.1 + 0.2) == "0.3"
    assert format_value(8306.5) == "8306.5"
    assert format_value("8306.5") == "8306.5"  # StatCan's own text passes through


def test_common_fields_once_series_wide_by_period():
    rows = [
        _row("French", "Number", "1971", "488918"),
        _row("French", "Number", "2021", "484425"),
        _row("French", "Percentage", "1971", "6.3"),
        _row("French", "Percentage", "2021", "3.4"),
    ]
    text, n_series = series_csv(rows)
    assert n_series == 2
    assert "# Geography: Ontario\n" in text and "# First_official_language_spoken: French\n" in text
    assert "DGUID" not in text
    table = list(csv.reader(io.StringIO("\n".join(_data_lines(text)))))
    assert table[0] == ["Statistics", "_series_key", "VECTOR_ID", "UOM", "1971", "2021"]
    assert table[1][-2:] == ["488918", "484425"]
    assert table[2][-2:] == ["6.3", "3.4"]


def test_labels_with_commas_are_quoted():
    rows = [
        _row("Total, first official language spoken", "Number", "2021", "14099790"),
        _row("French", "Number", "2021", "484425"),
    ]
    text, _ = series_csv(rows)
    assert '"Total, first official language spoken"' in text
    table = list(csv.reader(io.StringIO("\n".join(_data_lines(text)))))
    assert table[1][0] == "Total, first official language spoken"


def test_ragged_periods_leave_blank_cells_and_missing_values_are_empty():
    rows = [
        _row("French", "Number", "2016", "504130"),
        _row("French", "Number", "2021", None),
        _row("English", "Number", "2021", "13179540"),
    ]
    text, _ = series_csv(rows)
    table = list(csv.reader(io.StringIO("\n".join(_data_lines(text)))))
    assert table[0][-2:] == ["2016", "2021"]
    assert table[1][-2:] == ["504130", ""]
    assert table[2][-2:] == ["", "13179540"]


def test_observation_level_attribute_becomes_a_note():
    rows = [
        _row("French", "Number", "2016", "504130", STATUS="E"),
        _row("French", "Number", "2021", "484425"),
    ]
    text, _ = series_csv(rows)
    assert "# STATUS 7.F.N 2016: E\n" in text
    assert "STATUS" not in _data_lines(text)[0]


def test_empty_rows():
    assert series_csv([]) == ("", 0)


def test_table_csv():
    text = table_csv(["Geography", "avg"], [{"Geography": "A, B", "avg": 2 / 3}])
    assert text == 'Geography,avg\n"A, B",0.6666666667\n'


# ── Through the tool ──────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_tool_csv_returns_rows_not_a_summary_capped(server):  # noqa: F811
    mock_sdmx(make_data_xml(first_value="0.0"))
    sc = await _call(server, "get_sdmx_data", {"productId": 18100004, "key": "1+2.1", "format": "csv"})
    assert sc["format"] == "csv" and "summary" not in sc
    assert sc["row_count"] == 2 * N_PERIODS and sc["_truncated"] is True
    assert str(MAX_SDMX_ROWS) in sc["_message"]
    lines = _data_lines(sc["csv"])
    assert len(lines) == 1 + 2  # header + one row per series
    header = next(csv.reader([lines[0]]))
    assert header[:3] == ["Geography", "_series_key", "VECTOR_ID"]
    cells = sum(1 for line in lines[1:] for c in next(csv.reader([line]))[3:] if c != "")
    assert cells == MAX_SDMX_ROWS
    assert "# UOM: 2002=100" in sc["csv"]


@pytest.mark.asyncio
@respx.mock
async def test_tool_csv_with_sql_renders_the_query_result(server):  # noqa: F811
    mock_sdmx(make_data_xml(first_value="0.0"))
    sc = await _call(server, "get_sdmx_data", {
        "productId": 18100004, "key": "1+2.1", "format": "csv",
        "sql": 'SELECT "Geography", COUNT(*) AS n FROM data GROUP BY 1 ORDER BY 1',
    })
    assert sc["csv"] == f"Geography,n\nCanada,{N_PERIODS}\nOntario,{N_PERIODS}\n"
    assert "rows" not in sc and sc["fetched_row_count"] == 2 * N_PERIODS


@pytest.mark.asyncio
@respx.mock
async def test_tool_csv_bad_sql_is_still_an_error(server):  # noqa: F811
    mock_sdmx(make_data_xml(first_value="0.0"))
    text = await _call(server, "get_sdmx_data", {
        "productId": 18100004, "key": "1+2.1", "format": "csv", "sql": "SELECT nope FROM data",
    }, expect_error=True)
    assert "nope" in text


@pytest.mark.asyncio
@respx.mock
async def test_csv_reaches_the_model_unescaped_in_its_own_block(server):  # noqa: F811
    from mcp import Client

    mock_sdmx(make_data_xml(first_value="0.0"))
    async with Client(server) as client:
        result = await client.call_tool(
            "get_sdmx_data", {"productId": 18100004, "key": "1+2.1", "format": "csv", "lastNObservations": 2}
        )
    meta, table = (c.text for c in result.content)
    assert '"csv":' not in meta and '"series_count":2' in meta
    assert table == result.structured_content["csv"] and "\\n" not in table
    assert table.splitlines()[0] == "# Products: All-items"
