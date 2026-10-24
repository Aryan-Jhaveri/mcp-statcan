"""Tests for src/db/ephemeral.py — per-request in-memory SQL with safety limits."""

import pytest

from src.db.ephemeral import run_ephemeral_query

ROWS = [
    {"Geography": g, "period": str(2000 + i), "value": float(i * (n + 1))}
    for n, g in enumerate(["Canada", "Ontario", "Quebec"])
    for i in range(400)
]  # 1200 rows, above MAX_QUERY_ROWS


def test_aggregate_over_many_rows_returns_small_result():
    result = run_ephemeral_query(
        ROWS, 'SELECT "Geography", MAX(value) AS peak FROM data GROUP BY 1 ORDER BY peak DESC'
    )
    assert result["columns"] == ["Geography", "peak"]
    assert result["rows"][0] == {"Geography": "Quebec", "peak": 399 * 3.0}
    assert len(result["rows"]) == 3
    assert "message" not in result


def test_cte_and_window_functions_allowed():
    sql = """
        WITH ranked AS (
            SELECT "Geography", period, value,
                   value - LAG(value) OVER (PARTITION BY "Geography" ORDER BY period) AS delta
            FROM data
        )
        SELECT "Geography", SUM(delta) AS total FROM ranked GROUP BY 1 ORDER BY 1
    """
    result = run_ephemeral_query(ROWS, sql)
    assert [r["total"] for r in result["rows"]] == [399.0, 798.0, 1197.0]


def test_recursive_cte_allowed():
    result = run_ephemeral_query(
        ROWS, "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM n WHERE x < 3) SELECT x FROM n"
    )
    assert [r["x"] for r in result["rows"]] == [1, 2, 3]


def test_large_result_truncated():
    result = run_ephemeral_query(ROWS, "SELECT * FROM data", max_rows=10)
    assert len(result["rows"]) == 10
    assert "truncated" in result["message"]


@pytest.mark.parametrize(
    "sql",
    [
        "ATTACH DATABASE '/tmp/x.db' AS x",
        "DELETE FROM data",
        "INSERT INTO data VALUES ('x', '1', 1)",
        "DROP TABLE data",
        "CREATE TABLE t (a)",
        "PRAGMA table_info(data)",
        "SELECT load_extension('evil')",
    ],
)
def test_non_select_statements_rejected(sql):
    result = run_ephemeral_query(ROWS, sql)
    assert "error" in result
    assert "rows" not in result


def test_multiple_statements_rejected():
    result = run_ephemeral_query(ROWS, "SELECT 1; SELECT 2")
    assert "error" in result


def test_timeout_interrupts_long_query():
    sql = "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM n) SELECT MAX(x) FROM n"
    result = run_ephemeral_query(ROWS, sql, timeout=0.2)
    assert "time limit" in result["error"]


def test_huge_string_blocked():
    result = run_ephemeral_query(ROWS, "SELECT length(zeroblob(100000000))")
    assert "error" in result


def test_error_includes_table_columns_for_recovery():
    result = run_ephemeral_query(ROWS, "SELECT nope FROM data")
    assert "no such column" in result["error"]
    assert result["table_columns"] == ["Geography", "period", "value"]


def test_oversized_query_text_rejected():
    sql = "SELECT " + " + ".join(["1"] * 60_000)
    result = run_ephemeral_query(ROWS, sql)
    assert "error" in result


def test_typical_analytical_query_within_limits():
    sql = """
        SELECT "Geography",
               CASE WHEN AVG(value) > 500 THEN 'high' WHEN AVG(value) > 200 THEN 'mid' ELSE 'low' END AS band,
               COALESCE(MAX(value), MIN(value), 0) AS v
        FROM data WHERE "Geography" LIKE '%a%' GROUP BY 1
        UNION ALL SELECT 'x', 'y', 1
        UNION ALL SELECT 'x', 'y', 2
        UNION ALL SELECT 'x', 'y', 3
        UNION ALL SELECT 'x', 'y', 4
        ORDER BY 1
    """
    result = run_ephemeral_query(ROWS, sql)
    assert "error" not in result, result
    assert len(result["rows"]) == 6  # Canada, Ontario + 4 UNION rows
