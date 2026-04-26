"""Tests for src/util/sdmx_json.py — SDMX-JSON flattener and series key fixer."""

from src.util.sdmx_json import flatten_sdmx_json
from src.api.sdmx.sdmx_tools import _fix_or_series_keys


def _make_response(series_dims, obs_dim_values, series_data, series_attrs=None, obs_attrs=None):
    """Build a minimal SDMX-JSON response dict."""
    return {
        "structure": {
            "dimensions": {
                "series": series_dims,
                "observation": [{"id": "TIME_PERIOD", "values": obs_dim_values}],
            },
            "attributes": {
                "series": series_attrs or [],
                "observation": obs_attrs or [],
            },
        },
        "dataSets": [{"series": series_data}],
    }


# --- Bug 1: period format for sub-annual (monthly) data ---

def test_annual_period_uses_id():
    """Annual data with unique IDs uses the id field directly."""
    obs_vals = [
        {"id": "2023", "name": "2023"},
        {"id": "2024", "name": "2024"},
        {"id": "2025", "name": "2025"},
    ]
    data = _make_response(
        series_dims=[{"id": "Geography", "values": [{"id": "1", "name": "Canada"}]}],
        obs_dim_values=obs_vals,
        series_data={"0": {"attributes": [], "observations": {"0": [100], "1": [200], "2": [300]}}},
    )
    rows = flatten_sdmx_json(data)
    assert [r["period"] for r in rows] == ["2023", "2024", "2025"]


def test_monthly_period_uses_start_field():
    """Monthly data: StatCan sets id to bare year; start field has correct YYYY-MM."""
    obs_vals = [
        {"id": "2024", "name": "2024", "start": "2024-01-01T00:00:00"},
        {"id": "2024", "name": "2024", "start": "2024-02-01T00:00:00"},
        {"id": "2024", "name": "2024", "start": "2024-03-01T00:00:00"},
    ]
    data = _make_response(
        series_dims=[{"id": "Geography", "values": [{"id": "1", "name": "Canada"}]}],
        obs_dim_values=obs_vals,
        series_data={"0": {"attributes": [], "observations": {"0": [4.7], "1": [4.9], "2": [5.1]}}},
    )
    rows = flatten_sdmx_json(data)
    assert [r["period"] for r in rows] == ["2024-01", "2024-02", "2024-03"]


def test_monthly_mixed_years_uses_start_field():
    """Monthly data spanning year boundary uses start field, not duplicate IDs."""
    obs_vals = [
        {"id": "2025", "name": "2025", "start": "2025-11-01T00:00:00"},
        {"id": "2025", "name": "2025", "start": "2025-12-01T00:00:00"},
        {"id": "2026", "name": "2026", "start": "2026-01-01T00:00:00"},
    ]
    data = _make_response(
        series_dims=[{"id": "Geography", "values": [{"id": "1", "name": "Canada"}]}],
        obs_dim_values=obs_vals,
        series_data={"0": {"attributes": [], "observations": {"0": [6.5], "1": [6.8], "2": [7.0]}}},
    )
    rows = flatten_sdmx_json(data)
    assert [r["period"] for r in rows] == ["2025-11", "2025-12", "2026-01"]


# --- Bug 3 (period): global obs_key encoding for OR-key queries ---

def test_or_query_global_obs_keys_period():
    """StatCan OR-key: obs_keys are globally sequential; period wraps via modulo."""
    # 2 geographies × 3 monthly periods = 6 global obs (keys 0-5)
    # TIME_PERIOD has 3 entries (indices 0-2)
    obs_vals = [
        {"id": "2024", "name": "2024", "start": "2024-01-01T00:00:00"},
        {"id": "2024", "name": "2024", "start": "2024-02-01T00:00:00"},
        {"id": "2024", "name": "2024", "start": "2024-03-01T00:00:00"},
    ]
    series_data = {
        "0.0": {"attributes": [], "observations": {"0": [4.7], "1": [4.9], "2": [5.0]}},
        "0.3": {"attributes": [], "observations": {"3": [6.1], "4": [6.3], "5": [6.4]}},
    }
    data = _make_response(
        series_dims=[
            {"id": "Geography", "values": [{"id": "1", "name": "Quebec"}, {"id": "2", "name": "Ontario"}]},
            {"id": "Data_type", "values": [{"id": "1", "name": "SA"}]},
        ],
        obs_dim_values=obs_vals,
        series_data=series_data,
    )
    rows = flatten_sdmx_json(data)
    periods = [r["period"] for r in rows]
    # All 6 rows should have correct YYYY-MM periods (no missing period)
    assert len(rows) == 6
    assert all(p is not None for p in periods)
    assert periods[:3] == ["2024-01", "2024-02", "2024-03"]
    assert periods[3:] == ["2024-01", "2024-02", "2024-03"]


# --- General correctness ---

def test_obs_attributes_decoded():
    """Observation-level attributes (SCALAR_FACTOR, VECTOR_ID) are decoded."""
    data = _make_response(
        series_dims=[{"id": "Geography", "values": [{"id": "1", "name": "Canada"}]}],
        obs_dim_values=[{"id": "2025", "name": "2025"}],
        series_data={
            "0": {
                "attributes": [],
                "observations": {"0": [100, 0, 1]},
            }
        },
        obs_attrs=[
            {"id": "SCALAR_FACTOR", "values": [{"id": "0", "name": "units"}, {"id": "6", "name": "millions"}]},
            {"id": "VECTOR_ID", "values": [{"id": "466670", "name": "466670"}, {"id": "466671", "name": "466671"}]},
        ],
    )
    rows = flatten_sdmx_json(data)
    assert rows[0]["SCALAR_FACTOR"] == "units"
    assert rows[0]["VECTOR_ID"] == "466671"


def test_series_attr_merged_obs_takes_priority():
    """Series attributes are merged; obs-level value wins on name collision."""
    data = _make_response(
        series_dims=[{"id": "Geography", "values": [{"id": "1", "name": "Canada"}]}],
        obs_dim_values=[{"id": "2025"}],
        series_data={"0": {"attributes": [0], "observations": {"0": [100, 1]}}},
        series_attrs=[{"id": "UOM", "values": [{"id": "persons", "name": "Persons"}]}],
        obs_attrs=[{"id": "UOM", "values": [{"id": "thousands", "name": "Thousands"}, {"id": "millions", "name": "Millions"}]}],
    )
    rows = flatten_sdmx_json(data)
    # obs-level UOM (index 1 = "Millions") should win over series-level ("Persons")
    assert rows[0]["UOM"] == "Millions"


def test_null_obs_value_preserved():
    """Suppressed data value (null/None) is preserved as None in output."""
    data = _make_response(
        series_dims=[{"id": "Geography", "values": [{"id": "1", "name": "Canada"}]}],
        obs_dim_values=[{"id": "2025"}],
        series_data={"0": {"attributes": [], "observations": {"0": [None]}}},
    )
    rows = flatten_sdmx_json(data)
    assert rows[0]["value"] is None


# --- Bug 2: series dimension labels missing for OR-key queries ---

def test_or_query_out_of_range_series_index_drops_label():
    """flatten_sdmx_json silently drops labels when series key index exceeds values length.

    This tests the raw behaviour of the flattener with malformed series keys
    (index out of range). The upstream fix (_fix_or_series_keys) corrects the
    keys before this function is called; this test documents the fallback behaviour.
    """
    data = _make_response(
        series_dims=[
            {"id": "Geography", "values": [{"id": "13", "name": "New Brunswick"}]},
            {"id": "NOC", "values": [{"id": "6", "name": "Sales support"}]},  # 1 entry, indices 1+ OOB
        ],
        obs_dim_values=[{"id": "2021", "name": "2021"}],
        series_data={
            "0.0": {"attributes": [], "observations": {"0": [100]}},  # NOC idx 0 → labeled
            "0.1": {"attributes": [], "observations": {"0": [200]}},  # NOC idx 1 → out of range → None
        },
    )
    rows = flatten_sdmx_json(data)
    assert len(rows) == 2
    assert rows[0]["NOC"] == "Sales support"
    assert rows[0]["_series_key"] == "0.0"
    assert rows[1].get("NOC") is None        # label dropped — index 1 OOB
    assert rows[1]["_series_key"] == "0.1"


def test_series_key_always_present():
    """_series_key is present in every row, including single-series queries."""
    data = _make_response(
        series_dims=[{"id": "Geography", "values": [{"id": "1", "name": "Canada"}]}],
        obs_dim_values=[{"id": "2025"}],
        series_data={"0": {"attributes": [], "observations": {"0": [42]}}},
    )
    rows = flatten_sdmx_json(data)
    assert rows[0]["_series_key"] == "0"


# --- _fix_or_series_keys Bug A: single-code dim uses memberId as index ---

def _make_sdmx_data(series_dims, obs_values, series):
    """Build a minimal raw SDMX-JSON response dict for _fix_or_series_keys."""
    return {
        "structure": {
            "dimensions": {
                "series": series_dims,
                "observation": [{"id": "TIME_PERIOD", "values": obs_values}],
            },
        },
        "dataSets": [{"series": series}],
    }


def test_fix_bug_a_out_of_range_index_reset_to_zero():
    """Bug A: StatCan uses memberId (e.g. 10) as the series key index instead of 0.
    Any index >= len(values) for a single-value dim must be reset to 0."""
    key = "1.10"
    data = _make_sdmx_data(
        series_dims=[
            {"id": "Geography", "values": [{"id": "1", "name": "Canada"}]},
            {"id": "NOC", "values": [{"id": "10", "name": "Some occupation"}]},
        ],
        obs_values=[{"id": "2024", "name": "2024"}],
        series={"0.10": {"attributes": [], "observations": {"0": [100]}}},
    )
    _fix_or_series_keys(data, key)
    series = data["dataSets"][0]["series"]
    assert "0.0" in series, "out-of-range index 10 should be reset to 0"
    assert "0.10" not in series, "original malformed key should be removed"


def test_fix_bug_a_in_range_index_unchanged():
    """Bug A: indices already within range are not modified."""
    key = "1.2"
    data = _make_sdmx_data(
        series_dims=[
            {"id": "Geography", "values": [{"id": "1", "name": "Canada"}]},
            {"id": "Sex", "values": [{"id": "1", "name": "Male"}, {"id": "2", "name": "Female"}, {"id": "3", "name": "Both"}]},
        ],
        obs_values=[{"id": "2024", "name": "2024"}],
        series={"0.2": {"attributes": [], "observations": {"0": [200]}}},
    )
    _fix_or_series_keys(data, key)
    series = data["dataSets"][0]["series"]
    assert "0.2" in series, "in-range index 2 (3 values, 0-indexed) should be unchanged"


# --- _fix_or_series_keys Bug B: OR-query positional index derivation ---

def test_fix_bug_b_or_query_three_codes():
    """Bug B: OR-query with 3 codes — each gets correct positional index via G = min(obs_key) // n_periods."""
    key = "1.6+10+15"  # 2 dims, second has 3 OR codes
    # 3 codes × 2 periods = 6 global obs (keys 0-5)
    # code 6  → G=0, positional idx 0 → key "0.0"
    # code 10 → G=1, positional idx 1 → key "0.1" (StatCan emits "0.10" — wrong)
    # code 15 → G=2, positional idx 2 → key "0.2" (StatCan emits "0.15" — wrong)
    data = _make_sdmx_data(
        series_dims=[
            {"id": "Geography", "values": [{"id": "1", "name": "Canada"}]},
            {"id": "NOC", "values": [
                {"id": "6", "name": "Occ A"},
                {"id": "10", "name": "Occ B"},
                {"id": "15", "name": "Occ C"},
            ]},
        ],
        obs_values=[{"id": "2024"}, {"id": "2025"}],
        series={
            "0.0":  {"attributes": [], "observations": {"0": [10], "1": [11]}},
            "0.10": {"attributes": [], "observations": {"2": [20], "3": [21]}},
            "0.15": {"attributes": [], "observations": {"4": [30], "5": [31]}},
        },
    )
    _fix_or_series_keys(data, key)
    series = data["dataSets"][0]["series"]
    assert "0.0" in series
    assert "0.1" in series, "0.10 should be corrected to 0.1"
    assert "0.2" in series, "0.15 should be corrected to 0.2"
    assert "0.10" not in series
    assert "0.15" not in series
