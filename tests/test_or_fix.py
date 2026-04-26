"""Tests for _fix_or_series_keys — StatCan OR-query series key patch.

Live observation from table 98-10-0452-01, key "7.3.1.1.1.6+10+15.2":

  dim[5] (NOC) values: [{id:"6",...}, {id:"10",...}, {id:"15",...}]   ← correctly populated
  dim[6] (EI)  values: [{id:"2", name:"With employment income"}]       ← 1 entry

  Series keys returned by StatCan (BUGGY):
    "0.0.0.0.0.0.0"   obs_key=0  → NOC idx=0 (positional, correct)    EI idx=0 (correct)
    "0.0.0.0.0.10.1"  obs_key=1  → NOC idx=10 (memberId, NOT pos. 1)  EI idx=1 (G, not 0)
    "0.0.0.0.0.10.2"  obs_key=2  → NOC idx=10 (same memberId!)         EI idx=2 (G, not 0)

  After _fix_or_series_keys with key "7.3.1.1.1.6+10+15.2" (n_period_vals=1):
    G=0 → NOC pos=0, EI pos=0  → "0.0.0.0.0.0.0"  (unchanged)
    G=1 → NOC pos=1, EI pos=0  → "0.0.0.0.0.1.0"
    G=2 → NOC pos=2, EI pos=0  → "0.0.0.0.0.2.0"

  flatten_sdmx_json then correctly labels all three rows.
"""

from src.api.sdmx.sdmx_tools import _fix_or_series_keys
from src.util.sdmx_json import flatten_sdmx_json


def _make_raw_response(series_data):
    """Build an SDMX-JSON response that mirrors the real StatCan NOC OR-query shape."""
    return {
        "structure": {
            "dimensions": {
                "series": [
                    {"id": "Geography",     "values": [{"id": "7",  "name": "New Brunswick"}]},
                    {"id": "Work_activity", "values": [{"id": "3",  "name": "Worked"}]},
                    {"id": "Age",           "values": [{"id": "1",  "name": "Total - Age"}]},
                    {"id": "Gender",        "values": [{"id": "1",  "name": "Total - Gender"}]},
                    {"id": "Statistics",    "values": [{"id": "1",  "name": "Count"}]},
                    {"id": "NOC", "values": [
                        {"id": "6",  "name": "000 Legislative"},
                        {"id": "10", "name": "100 Specialized"},
                        {"id": "15", "name": "111 Professional finance"},
                    ]},
                    {"id": "EI", "values": [{"id": "2", "name": "With employment income"}]},
                ],
                "observation": [{"id": "TIME_PERIOD", "values": [{"id": "2021"}]}],
            },
            "attributes": {"series": [], "observation": []},
        },
        "dataSets": [{"series": series_data}],
    }


# ---------------------------------------------------------------------------
# Core fix tests
# ---------------------------------------------------------------------------

def test_fix_corrects_noc_and_ei_keys():
    """After fix, all three series have correct positional indices (0, 1, 2)."""
    buggy_series = {
        "0.0.0.0.0.0.0":  {"attributes": [], "observations": {"0": [3495]}},
        "0.0.0.0.0.10.1": {"attributes": [], "observations": {"1": [6030]}},
        "0.0.0.0.0.10.2": {"attributes": [], "observations": {"2": [5195]}},
    }
    data = _make_raw_response(buggy_series)
    _fix_or_series_keys(data, "7.3.1.1.1.6+10+15.2")

    patched_keys = set(data["dataSets"][0]["series"].keys())
    assert patched_keys == {"0.0.0.0.0.0.0", "0.0.0.0.0.1.0", "0.0.0.0.0.2.0"}


def test_fix_produces_correct_labels():
    """flatten_sdmx_json labels all three NOC rows correctly after the fix."""
    buggy_series = {
        "0.0.0.0.0.0.0":  {"attributes": [], "observations": {"0": [3495]}},
        "0.0.0.0.0.10.1": {"attributes": [], "observations": {"1": [6030]}},
        "0.0.0.0.0.10.2": {"attributes": [], "observations": {"2": [5195]}},
    }
    data = _make_raw_response(buggy_series)
    _fix_or_series_keys(data, "7.3.1.1.1.6+10+15.2")
    rows = flatten_sdmx_json(data)

    assert len(rows) == 3
    noc_labels = [r.get("NOC") for r in rows]
    assert noc_labels == ["000 Legislative", "100 Specialized", "111 Professional finance"]

    ei_labels = [r.get("EI") for r in rows]
    assert all(label == "With employment income" for label in ei_labels)

    assert [r["value"] for r in rows] == [3495, 6030, 5195]


def test_no_or_syntax_correct_indices_unchanged():
    """Series keys with all-zero (correct) indices are unchanged for non-OR queries."""
    series = {"0.0.0.0.0.0.0": {"attributes": [], "observations": {"0": [42]}}}
    data = _make_raw_response(series)
    _fix_or_series_keys(data, "7.3.1.1.1.6.2")
    assert "0.0.0.0.0.0.0" in data["dataSets"][0]["series"]


def test_solo_out_of_range_noc_fixed():
    """Bug A: solo NOC=10 query uses series key index 10 but values has 1 entry.

    StatCan encodes the series key using a non-positional index (memberId or
    similar) even for single-code queries where the only valid positional index
    is 0. After _fix_or_series_keys, the index is corrected to 0 so the label
    can be dereferenced.
    """
    # Mirrors the exact raw response for key "7.3.1.1.1.10.2" (solo NOC=10)
    # Series key "0.0.0.0.0.10.0" — NOC index 10 is out of range (values has 1 entry)
    data = {
        "structure": {
            "dimensions": {
                "series": [
                    {"id": "Geography",     "values": [{"id": "7",  "name": "New Brunswick"}]},
                    {"id": "Work_activity", "values": [{"id": "3",  "name": "Worked"}]},
                    {"id": "Age",           "values": [{"id": "1",  "name": "Total - Age"}]},
                    {"id": "Gender",        "values": [{"id": "1",  "name": "Total - Gender"}]},
                    {"id": "Statistics",    "values": [{"id": "1",  "name": "Count"}]},
                    {"id": "NOC",           "values": [{"id": "10", "name": "100 Specialized"}]},
                    {"id": "EI",            "values": [{"id": "2",  "name": "With employment income"}]},
                ],
                "observation": [{"id": "TIME_PERIOD", "values": [{"id": "2021"}]}],
            },
            "attributes": {"series": [], "observation": []},
        },
        "dataSets": [{"series": {
            "0.0.0.0.0.10.0": {"attributes": [], "observations": {"0": [6030]}},
        }}],
    }
    _fix_or_series_keys(data, "7.3.1.1.1.10.2")
    # NOC index 10 should be corrected to 0
    assert "0.0.0.0.0.0.0" in data["dataSets"][0]["series"]

    from src.util.sdmx_json import flatten_sdmx_json
    rows = flatten_sdmx_json(data)
    assert len(rows) == 1
    assert rows[0]["NOC"] == "100 Specialized"
    assert rows[0]["EI"] == "With employment income"
    assert rows[0]["value"] == 6030


def test_fix_multiple_periods():
    """Fix works correctly when lastNObservations > 1 (multiple obs per series)."""
    # 3 NOC codes × 3 periods: obs_keys are global sequential 0-8
    obs_dim_3 = [{"id": "2019"}, {"id": "2020"}, {"id": "2021"}]
    data = {
        "structure": {
            "dimensions": {
                "series": [
                    {"id": "NOC", "values": [
                        {"id": "6",  "name": "000 Legislative"},
                        {"id": "10", "name": "100 Specialized"},
                        {"id": "15", "name": "111 Professional"},
                    ]},
                ],
                "observation": [{"id": "TIME_PERIOD", "values": obs_dim_3}],
            },
            "attributes": {"series": [], "observation": []},
        },
        "dataSets": [{"series": {
            "0":   {"attributes": [], "observations": {"0": [10], "1": [11], "2": [12]}},  # G=0
            "10":  {"attributes": [], "observations": {"3": [20], "4": [21], "5": [22]}},  # G=1
            "10b": {"attributes": [], "observations": {"6": [30], "7": [31], "8": [32]}},  # G=2
        }}],
    }
    _fix_or_series_keys(data, "6+10+15")
    patched = data["dataSets"][0]["series"]
    assert "0" in patched    # G=0 → pos 0 → unchanged
    assert "1" in patched    # G=1 → pos 1
    assert "2" in patched    # G=2 → pos 2


def test_fix_two_or_dimensions():
    """Fix correctly decomposes G for two OR dimensions (right-to-left)."""
    # 2 geographies × 2 NOC codes = 4 series
    # Key: "1+2.6+10" — geo at pos 0, NOC at pos 1
    data = {
        "structure": {
            "dimensions": {
                "series": [
                    {"id": "Geo", "values": [{"id": "1", "name": "Canada"}, {"id": "2", "name": "NB"}]},
                    {"id": "NOC", "values": [{"id": "6", "name": "NOC6"}, {"id": "10", "name": "NOC10"}]},
                ],
                "observation": [{"id": "TIME_PERIOD", "values": [{"id": "2021"}]}],
            },
            "attributes": {"series": [], "observation": []},
        },
        "dataSets": [{"series": {
            "0.0":  {"attributes": [], "observations": {"0": [1]}},  # G=0 → Geo=0, NOC=0
            "0.10": {"attributes": [], "observations": {"1": [2]}},  # G=1 → Geo=0, NOC=1
            "0.10b":{"attributes": [], "observations": {"2": [3]}},  # G=2 → Geo=1, NOC=0
            "0.10c":{"attributes": [], "observations": {"3": [4]}},  # G=3 → Geo=1, NOC=1
        }}],
    }
    _fix_or_series_keys(data, "1+2.6+10")
    patched = set(data["dataSets"][0]["series"].keys())
    # right-to-left: NOC varies fastest (modulo 2), Geo = G // 2
    assert "0.0" in patched   # G=0: Geo=0%2=0, NOC=0%2=0
    assert "0.1" in patched   # G=1: Geo=1//2=0, NOC=1%2=1
    assert "1.0" in patched   # G=2: Geo=2//2=1, NOC=2%2=0
    assert "1.1" in patched   # G=3: Geo=3//2=1, NOC=3%2=1
