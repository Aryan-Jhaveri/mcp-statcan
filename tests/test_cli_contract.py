"""Tests for the statcan CLI's machine-readable contract (src/cli/contract.py).

Exit codes, JSON envelopes on stdout/stderr, and actionable hints — StatCan mocked by respx.
"""

import csv
import io
import json

import httpx
import pytest
import respx
from httpx import Response
from typer.testing import CliRunner

from src.cli.contract import ExitCode, state
from src.cli.main import app
from src.config import BASE_URL, SDMX_BASE_URL
from tests.test_fetch_sdmx_to_database import DATA_URL, N_PERIODS, _make_response

runner = CliRunner()
CUBES_URL = f"{BASE_URL}/getAllCubesListLite"
CUBES = [
    {"productId": 18100004, "cubeTitleEn": "Consumer Price Index, monthly", "frequencyCode": 6,
     "cubeStartDate": "1914-01-01", "cubeEndDate": "2026-09-01"},
    {"productId": 36100102, "cubeTitleEn": "GDP by industry, annual", "frequencyCode": 12,
     "cubeStartDate": "1926-01-01", "cubeEndDate": "1960-01-01"},
]


@pytest.fixture(autouse=True)
def reset_json_mode(monkeypatch):
    monkeypatch.delenv("STATCAN_OUTPUT", raising=False)
    state.json_mode = False
    yield
    state.json_mode = False


def _err(result):
    return json.loads(result.stderr.strip().splitlines()[-1])["error"]


@respx.mock
def test_download_json_inline_envelope():
    respx.get(DATA_URL).mock(return_value=Response(200, json=_make_response(first_value="0.0")))
    result = runner.invoke(app, ["--json", "download", "18-10-0004-01", "--key", "1+2.1"])

    assert result.exit_code == ExitCode.OK
    env = json.loads(result.stdout)
    assert env["ok"] is True and env["command"] == "download"
    assert env["rows"] == len(env["data"]) == 2 * N_PERIODS
    assert env["series_count"] == 2
    assert env["period_range"] == ["1700", str(1700 + N_PERIODS - 1)]
    assert env["source_url"].startswith(DATA_URL)
    assert "_series_key" not in env["columns"]


@respx.mock
def test_download_json_with_output_writes_file_and_summarizes(tmp_path):
    respx.get(DATA_URL).mock(return_value=Response(200, json=_make_response(first_value="0.0")))
    out = tmp_path / "cpi.csv"
    result = runner.invoke(app, ["--json", "download", "18100004", "--key", "1+2.1", "-o", str(out)])

    env = json.loads(result.stdout)
    assert env["path"] == str(out) and env["format"] == "csv"
    assert "data" not in env
    assert len(list(csv.DictReader(out.open()))) == 2 * N_PERIODS


def test_env_var_enables_json_mode():
    result = runner.invoke(app, ["download", "18100004"], env={"STATCAN_OUTPUT": "json"})
    assert result.exit_code == ExitCode.USAGE
    assert _err(result)["code"] == "usage"


@respx.mock
def test_csv_handles_rows_with_different_attributes():
    """StatCan attributes vary per row; CSV must use the union of columns, not crash."""
    data = _make_response(first_value="0.0")
    data["structure"]["attributes"]["observation"] = [{"id": "NB_DECIMAL", "values": [{"id": "1"}]}]
    data["dataSets"][0]["series"]["1.0"]["observations"]["300"] = ["0.0", 0]  # only this obs has NB_DECIMAL
    respx.get(DATA_URL).mock(return_value=Response(200, json=data))

    result = runner.invoke(app, ["download", "18100004", "--key", "1+2.1"])

    assert result.exit_code == ExitCode.OK, result.stderr
    rows = list(csv.DictReader(io.StringIO(result.stdout)))
    assert "NB_DECIMAL" in rows[0]
    assert len(rows) == 2 * N_PERIODS


@respx.mock
def test_ndjson_format():
    respx.get(DATA_URL).mock(return_value=Response(200, json=_make_response(first_value="0.0")))
    result = runner.invoke(app, ["download", "18100004", "--key", "1+2.1", "-f", "ndjson"])

    lines = result.stdout.strip().splitlines()
    assert len(lines) == 2 * N_PERIODS
    assert json.loads(lines[0])["Geography"] == "Canada"


@pytest.mark.parametrize(
    "args, code, fragment",
    [
        (["download", "18100004"], ExitCode.USAGE, "--key is required"),
        (["download", "18100004", "--key", "1.1", "--last", "3", "--start", "2020"], ExitCode.USAGE, "--last"),
        (["download", "not-an-id", "--key", "1.1"], ExitCode.USAGE, "not a valid product ID"),
        (["download", "18100004", "--key", "1.1", "-f", "xml", "--dry-run"], ExitCode.OK, None),
    ],
)
def test_usage_errors(args, code, fragment):
    result = runner.invoke(app, ["--json", *args])
    assert result.exit_code == code
    if fragment:
        err = _err(result)
        assert err["code"] == "usage" and fragment in err["message"]


@respx.mock
@pytest.mark.parametrize(
    "status, code",
    [(404, ExitCode.NOT_FOUND), (406, ExitCode.UPSTREAM_REJECTED), (400, ExitCode.UPSTREAM_REJECTED),
     (503, ExitCode.UPSTREAM_UNAVAILABLE)],
)
def test_upstream_status_mapping(status, code, monkeypatch):
    monkeypatch.setattr("src.api.client.asyncio.sleep", _no_sleep)  # skip retry backoff
    respx.get(DATA_URL).mock(return_value=Response(status))
    result = runner.invoke(app, ["--json", "download", "18100004", "--key", "1+2.1"])

    assert result.exit_code == code
    err = _err(result)
    assert err["exit_code"] == code
    if status == 406:
        assert "statcan metadata" in err["hint"]


@respx.mock
def test_network_error_is_unavailable():
    respx.get(DATA_URL).mock(side_effect=httpx.ConnectError("boom"))
    result = runner.invoke(app, ["--json", "download", "18100004", "--key", "1+2.1"])
    assert result.exit_code == ExitCode.UPSTREAM_UNAVAILABLE


@respx.mock
def test_empty_result_exit_code():
    empty = _make_response()
    empty["dataSets"] = [{"series": {}}]
    respx.get(DATA_URL).mock(return_value=Response(200, json=empty))
    result = runner.invoke(app, ["--json", "download", "18100004", "--key", "1+2.1"])

    assert result.exit_code == ExitCode.EMPTY
    assert _err(result)["code"] == "empty"


def test_human_mode_error_has_hint():
    result = runner.invoke(app, ["download", "18100004"])
    assert result.exit_code == ExitCode.USAGE
    assert "Error: --key is required" in result.stderr
    assert "Hint:" in result.stderr


def test_dry_run_json():
    result = runner.invoke(app, ["--json", "download", "18100004", "--key", "1.1", "--last", "3", "--dry-run"])
    env = json.loads(result.stdout)
    assert env["dry_run"] is True
    assert env["source_url"] == f"{SDMX_BASE_URL}data/DF_18100004/1.1?lastNObservations=3"


@respx.mock
def test_search_json_and_frequency_labels():
    respx.get(CUBES_URL).mock(return_value=Response(200, json=CUBES))
    result = runner.invoke(app, ["--json", "search", "index"])

    env = json.loads(result.stdout)
    assert env["total_matches"] == 1 and env["truncated"] is False
    assert env["data"][0]["Frequency"] == "Monthly"

    result = runner.invoke(app, ["--json", "search", "annual"])
    assert json.loads(result.stdout)["data"][0]["Frequency"] == "Annual"  # code 12, not Monthly


@respx.mock
def test_search_no_matches_is_empty():
    respx.get(CUBES_URL).mock(return_value=Response(200, json=CUBES))
    result = runner.invoke(app, ["--json", "search", "zzzz"])
    assert result.exit_code == ExitCode.EMPTY


async def _no_sleep(_seconds):
    return None
