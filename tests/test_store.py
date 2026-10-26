"""Tests for src/db/store.py — canonical series/observations store (issue #65)."""

import sqlite3

import pytest

from src.db import store
from src.db.store import (
    OBS_TABLE, SERIES_TABLE, coordinate_to_key, create_series_view, drop_relation, ensure_schema,
    period_to_date, upsert_sdmx_rows, upsert_wds_points, wds_period_label,
)


@pytest.fixture
def conn(tmp_path):
    c = sqlite3.connect(tmp_path / "t.db")
    ensure_schema(c)
    yield c
    c.close()


def _sdmx_rows(values, geo="Canada", key="2.2", periods=("2026-07", "2026-08", "2026-09")):
    return [
        {"Geography": geo, "Products": "All-items", "_series_key": key, "period": p, "value": v,
         "VECTOR_ID": "41690973", "SCALAR_FACTOR": "units", "NB_DECIMAL": "1", "DGUID": "2016A000011124", "UOM": "2002=100"}
        for p, v in zip(periods, values)
    ]


def test_schema_versioned_and_idempotent(conn):
    assert conn.execute("PRAGMA user_version").fetchone()[0] == store.SCHEMA_VERSION
    ensure_schema(conn)  # second call is a no-op
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {SERIES_TABLE, OBS_TABLE} <= names


@pytest.mark.parametrize("label, expected", [
    ("2025", "2025-01-01"), ("2026-08", "2026-08-01"), ("2026-Q2", "2026-04-01"),
    ("2026-S2", "2026-07-01"), ("2026-10-15", "2026-10-15"), ("2026-W01", "2025-12-29"), ("odd", "odd"),
])
def test_period_to_date(label, expected):
    assert period_to_date(label) == expected


@pytest.mark.parametrize("ref, freq, expected", [
    ("2026-08-01", 6, "2026-08"), ("2025-01-01", 12, "2025"), ("2026-04-01", 9, "2026-Q2"),
    ("2026-07-01", 11, "2026-S2"), ("2026-10-15", 1, "2026-10-15"),
])
def test_wds_period_label(ref, freq, expected):
    assert wds_period_label(ref, freq) == expected


def test_coordinate_to_key():
    assert coordinate_to_key("2.2.0.0.0.0.0.0.0.0") == "2.2"
    assert coordinate_to_key("7.3.1.1.1.10.2.0.0.0") == "7.3.1.1.1.10.2"


def test_upsert_counts_inserted_revised_unchanged(conn):
    first = upsert_sdmx_rows(conn, 18100004, _sdmx_rows(["169.9", "169.8", "170.0"]), "u1")
    assert (first["inserted"], first["revised"], first["unchanged"]) == (3, 0, 0)
    assert first["series_ids"] == ["18100004:2.2"]
    assert first["date_range"] == ["2026-07-01", "2026-09-01"]

    again = upsert_sdmx_rows(conn, 18100004, _sdmx_rows(["169.9", "169.8", "170.1"]), "u2")
    assert (again["inserted"], again["revised"], again["unchanged"]) == (0, 1, 2)
    assert conn.execute(f"SELECT COUNT(*) FROM {OBS_TABLE}").fetchone()[0] == 3
    assert conn.execute(f"SELECT value, source_url FROM {OBS_TABLE} WHERE ref_date='2026-09-01'").fetchone() == (170.1, "u2")


def test_series_attributes_and_types(conn):
    upsert_sdmx_rows(conn, 18100004, _sdmx_rows([None, "169.8", "170.0"]), "u")
    vid, uom, attrs = conn.execute(f"SELECT vector_id, uom, attrs_json FROM {SERIES_TABLE}").fetchone()
    assert (vid, uom) == (41690973, "2002=100")
    assert '"DGUID"' in attrs and '"NB_DECIMAL"' in attrs
    # null first value doesn't make the column TEXT: value is REAL by schema
    assert conn.execute(f"SELECT typeof(value) FROM {OBS_TABLE} ORDER BY ref_date").fetchall() == [("null",), ("real",), ("real",)]


def test_census_vector_zero_stored_as_null(conn):
    rows = _sdmx_rows(["1"], periods=("2021",))
    rows[0]["VECTOR_ID"] = "0"
    upsert_sdmx_rows(conn, 98100452, rows, "u")
    assert conn.execute(f"SELECT vector_id FROM {SERIES_TABLE}").fetchone() == (None,)


def test_wds_and_sdmx_share_series_and_rows(conn):
    upsert_sdmx_rows(conn, 18100004, _sdmx_rows(["169.9", "169.8", "170.0"]), "sdmx-url")
    result = upsert_wds_points(conn, [{
        "productId": 18100004, "coordinate": "2.2.0.0.0.0.0.0.0.0", "vectorId": 41690973,
        "vectorDataPoint": [
            {"refPer": "2026-09-01", "value": 170.0, "frequencyCode": 6, "statusCode": 0, "symbolCode": 0,
             "releaseTime": "2026-10-20T08:30"},
            {"refPer": "2026-10-01", "value": 171.2, "frequencyCode": 6, "statusCode": 0, "symbolCode": 0,
             "releaseTime": "2026-11-17T08:30"},
        ],
    }])
    assert (result["inserted"], result["unchanged"]) == (1, 1)
    assert conn.execute(f"SELECT COUNT(*) FROM {SERIES_TABLE}").fetchone()[0] == 1
    # WDS has no labels: SDMX dimension labels survive the WDS upsert
    assert '"Canada"' in conn.execute(f"SELECT dims_json FROM {SERIES_TABLE}").fetchone()[0]
    assert conn.execute(f"SELECT period, release_time FROM {OBS_TABLE} WHERE ref_date='2026-10-01'").fetchone() == ("2026-10", "2026-11-17T08:30")


def test_view_filters_series_and_dates(conn):
    can = upsert_sdmx_rows(conn, 18100004, _sdmx_rows(["169.9", "169.8", "170.0"]), "u")
    upsert_sdmx_rows(conn, 18100004, _sdmx_rows(["172.7", "172.4", "173.0"], geo="Newfoundland and Labrador", key="3.2"), "u")
    # a later, wider fetch of Canada must not leak into the earlier view
    upsert_sdmx_rows(conn, 18100004, _sdmx_rows(["168.0"], periods=("2026-01",)), "u")

    cols = create_series_view(conn, "cpi_canada", can["series_ids"], can["date_range"])
    assert cols[:2] == ["Geography", "Products"]
    rows = conn.execute('SELECT "Geography", period, value, VECTOR_ID, UOM FROM cpi_canada ORDER BY period').fetchall()
    assert rows == [("Canada", "2026-07", 169.9, 41690973, "2002=100"),
                    ("Canada", "2026-08", 169.8, 41690973, "2002=100"),
                    ("Canada", "2026-09", 170.0, 41690973, "2002=100")]


def test_view_replaces_existing_table_but_not_canonical(conn):
    conn.execute("CREATE TABLE cpi (x)")
    r = upsert_sdmx_rows(conn, 18100004, _sdmx_rows(["1", "2", "3"]), "u")
    create_series_view(conn, "cpi", r["series_ids"], r["date_range"])
    assert conn.execute("SELECT type FROM sqlite_master WHERE name='cpi'").fetchone() == ("view",)
    with pytest.raises(ValueError, match="canonical"):
        drop_relation(conn, SERIES_TABLE)


def test_cross_product_join(conn):
    """Acceptance: join two products without per-table schema discovery."""
    upsert_sdmx_rows(conn, 18100004, _sdmx_rows(["169.9", "169.8", "170.0"]), "u")
    upsert_sdmx_rows(conn, 14100287, _sdmx_rows(["6.1", "6.2", "6.3"], key="1.1.1"), "u")
    rows = conn.execute(f"""
        SELECT a.period, a.value AS cpi, b.value AS unemployment
        FROM {OBS_TABLE} a JOIN {OBS_TABLE} b ON a.ref_date = b.ref_date
        WHERE a.series_id = '18100004:2.2' AND b.series_id = '14100287:1.1.1'
        ORDER BY a.ref_date""").fetchall()
    assert rows[0] == ("2026-07", 169.9, 6.1)
