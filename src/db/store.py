"""Canonical long-format store for StatCan observations.

Every fetch tool writes into two tables instead of creating an ad-hoc table per call:

  _statcan_series        one row per series, keyed by "<productId>:<SDMX key>"
                         (e.g. "18100004:2.2"); dimension labels, vector ID, UOM, ...
  _statcan_observations  one row per (series, period start date), with value,
                         status/symbol, provenance (source, URL, release and fetch time)

Series are keyed by product + SDMX key rather than vectorId because some tables
(e.g. Census) have no vectors, and a WDS coordinate reduces to the same key
("2.2.0.0.0.0.0.0.0.0" -> "2.2"), so SDMX and WDS fetches of one series share rows.

Periods are stored twice: ref_date (ISO start date, the key both sources agree on)
and period (the SDMX-style label shown to users: "2026", "2026-Q2", "2026-08").

Writes are upserts; a fetch reports how many observations were new, revised
(value changed) or unchanged. The caller's table_name becomes a VIEW over the
store filtered to the series and date range it fetched.
"""

import json
import re
import sqlite3
from datetime import date, datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

SCHEMA_VERSION = 1
SERIES_TABLE = "_statcan_series"
OBS_TABLE = "_statcan_observations"
CANONICAL_TABLES = (SERIES_TABLE, OBS_TABLE)

_DDL = f"""
CREATE TABLE IF NOT EXISTS {SERIES_TABLE} (
    series_id     TEXT PRIMARY KEY,      -- '<product_id>:<sdmx key>'
    product_id    INTEGER NOT NULL,
    series_key    TEXT NOT NULL,         -- SDMX key, e.g. '2.2'
    vector_id     INTEGER,
    dims_json     TEXT,                  -- {{"Geography": "Canada", ...}} (labels)
    uom           TEXT,
    scalar_factor TEXT,
    attrs_json    TEXT,                  -- other series attributes (DGUID, NB_DECIMAL, ...)
    updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_statcan_series_product ON {SERIES_TABLE}(product_id);
CREATE INDEX IF NOT EXISTS idx_statcan_series_vector ON {SERIES_TABLE}(vector_id);

CREATE TABLE IF NOT EXISTS {OBS_TABLE} (
    series_id    TEXT NOT NULL,
    ref_date     TEXT NOT NULL,          -- ISO start date of the period
    period       TEXT NOT NULL,          -- label: '2026', '2026-Q2', '2026-08'
    value        REAL,                   -- NULL = missing/suppressed
    status       TEXT,
    symbol       TEXT,
    release_time TEXT,                   -- WDS only
    source       TEXT NOT NULL,          -- 'sdmx' | 'wds'
    source_url   TEXT,
    fetched_at   TEXT NOT NULL,
    PRIMARY KEY (series_id, ref_date)
) WITHOUT ROWID;
"""

_SDMX_SERIES_ATTRS = {"VECTOR_ID", "UOM", "SCALAR_FACTOR"}
_SDMX_OBS_ATTRS = {"STATUS_CAN": "status", "SYMBOL": "symbol"}


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create or migrate the canonical tables (versioned with PRAGMA user_version)."""
    (version,) = conn.execute("PRAGMA user_version").fetchone()
    if version >= SCHEMA_VERSION:
        return
    conn.executescript(_DDL)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()


# ── Periods ──────────────────────────────────────────────────────────────────

_QUARTER = re.compile(r"^(\d{4})-Q([1-4])$")
_HALF = re.compile(r"^(\d{4})-S([12])$")
_WEEK = re.compile(r"^(\d{4})-W(\d{2})$")


def period_to_date(period: str) -> str:
    """ISO start date for an SDMX period label; unknown formats are returned unchanged."""
    p = period.strip()
    if re.fullmatch(r"\d{4}", p):
        return f"{p}-01-01"
    if re.fullmatch(r"\d{4}-\d{2}", p):
        return f"{p}-01"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p):
        return p
    if m := _QUARTER.match(p):
        return f"{m.group(1)}-{(int(m.group(2)) - 1) * 3 + 1:02d}-01"
    if m := _HALF.match(p):
        return f"{m.group(1)}-{'01' if m.group(2) == '1' else '07'}-01"
    if m := _WEEK.match(p):
        return date.fromisocalendar(int(m.group(1)), int(m.group(2)), 1).isoformat()
    return p


def wds_period_label(ref_per: str, frequency_code: Optional[int]) -> str:
    """SDMX-style label for a WDS refPer date, from StatCan's frequencyCode."""
    d = ref_per[:10]
    if frequency_code == 12:  # Annual
        return d[:4]
    if frequency_code == 9:  # Quarterly
        return f"{d[:4]}-Q{(int(d[5:7]) - 1) // 3 + 1}"
    if frequency_code == 11:  # Semi-annual
        return f"{d[:4]}-S{1 if int(d[5:7]) <= 6 else 2}"
    if frequency_code in (6, 7):  # Monthly, bimonthly
        return d[:7]
    return d


# ── Upserts ──────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _vector_id(value: Any) -> Optional[int]:
    try:
        vid = int(value)
    except (TypeError, ValueError):
        return None
    return vid or None  # StatCan uses 0 for "no vector" (e.g. Census tables)


def _upsert(
    conn: sqlite3.Connection,
    series: Dict[str, Dict[str, Any]],
    observations: List[Dict[str, Any]],
) -> Dict[str, int]:
    """Write series + observations; return inserted/revised/unchanged observation counts."""
    now = _now()
    conn.executemany(
        f"""INSERT INTO {SERIES_TABLE}
              (series_id, product_id, series_key, vector_id, dims_json, uom, scalar_factor, attrs_json, updated_at)
            VALUES (:series_id, :product_id, :series_key, :vector_id, :dims_json, :uom, :scalar_factor, :attrs_json, :updated_at)
            ON CONFLICT(series_id) DO UPDATE SET
              vector_id     = COALESCE(excluded.vector_id, vector_id),
              dims_json     = COALESCE(excluded.dims_json, dims_json),
              uom           = COALESCE(excluded.uom, uom),
              scalar_factor = COALESCE(excluded.scalar_factor, scalar_factor),
              attrs_json    = COALESCE(excluded.attrs_json, attrs_json),
              updated_at    = excluded.updated_at""",
        [{**s, "updated_at": now} for s in series.values()],
    )

    # Compare against stored values to classify each observation
    existing: Dict[Tuple[str, str], Optional[float]] = {}
    ids = list(series)
    for i in range(0, len(ids), 500):
        chunk = ids[i : i + 500]
        marks = ",".join("?" * len(chunk))
        for sid, ref_date, value in conn.execute(
            f"SELECT series_id, ref_date, value FROM {OBS_TABLE} WHERE series_id IN ({marks})", chunk
        ):
            existing[(sid, ref_date)] = value

    counts = {"inserted": 0, "revised": 0, "unchanged": 0}
    for o in observations:
        key = (o["series_id"], o["ref_date"])
        if key not in existing:
            counts["inserted"] += 1
        elif existing[key] != o["value"]:
            counts["revised"] += 1
        else:
            counts["unchanged"] += 1

    conn.executemany(
        f"""INSERT INTO {OBS_TABLE}
              (series_id, ref_date, period, value, status, symbol, release_time, source, source_url, fetched_at)
            VALUES (:series_id, :ref_date, :period, :value, :status, :symbol, :release_time, :source, :source_url, :fetched_at)
            ON CONFLICT(series_id, ref_date) DO UPDATE SET
              period       = excluded.period,
              value        = excluded.value,
              status       = excluded.status,
              symbol       = excluded.symbol,
              release_time = COALESCE(excluded.release_time, release_time),
              source       = excluded.source,
              source_url   = excluded.source_url,
              fetched_at   = excluded.fetched_at""",
        [{**o, "fetched_at": now} for o in observations],
    )
    conn.commit()
    return counts


def upsert_sdmx_rows(
    conn: sqlite3.Connection, product_id: int, rows: Iterable[Dict[str, Any]], source_url: str
) -> Dict[str, Any]:
    """Store rows from fetch_sdmx_rows (util/sdmx_xml.py shape).

    Dimension columns are the keys before "_series_key" in each row.
    Returns counts plus the series_ids and ref_date range written.
    """
    series: Dict[str, Dict[str, Any]] = {}
    observations: List[Dict[str, Any]] = []
    for row in rows:
        keys = list(row)
        split = keys.index("_series_key")
        dims = {k: row[k] for k in keys[:split]}
        attrs = {k: row[k] for k in keys[split + 3 :]}  # after _series_key, period, value
        sid = f"{product_id}:{row['_series_key']}"
        if sid not in series:
            extra = {k: v for k, v in attrs.items() if k not in _SDMX_SERIES_ATTRS and k not in _SDMX_OBS_ATTRS}
            series[sid] = {
                "series_id": sid,
                "product_id": product_id,
                "series_key": row["_series_key"],
                "vector_id": _vector_id(attrs.get("VECTOR_ID")),
                "dims_json": json.dumps(dims, ensure_ascii=False),
                "uom": attrs.get("UOM"),
                "scalar_factor": attrs.get("SCALAR_FACTOR"),
                "attrs_json": json.dumps(extra, ensure_ascii=False) if extra else None,
            }
        observations.append({
            "series_id": sid,
            "ref_date": period_to_date(row["period"]),
            "period": row["period"],
            "value": _to_float(row.get("value")),
            "status": attrs.get("STATUS_CAN"),
            "symbol": attrs.get("SYMBOL"),
            "release_time": None,
            "source": "sdmx",
            "source_url": source_url,
        })
    return _finish(conn, series, observations)


def coordinate_to_key(coordinate: str) -> str:
    """WDS coordinate -> SDMX key: '2.2.0.0.0.0.0.0.0.0' -> '2.2' (0 is padding)."""
    parts = coordinate.split(".")
    while parts and parts[-1] == "0":
        parts.pop()
    return ".".join(parts)


def upsert_wds_points(
    conn: sqlite3.Connection, vectors: Iterable[Dict[str, Any]], source_url: Optional[str] = None
) -> Dict[str, Any]:
    """Store WDS getDataFromVectorByReferencePeriodRange objects (one per vector).

    WDS gives no dimension labels, so existing labels from SDMX fetches are kept.
    """
    series: Dict[str, Dict[str, Any]] = {}
    observations: List[Dict[str, Any]] = []
    for obj in vectors:
        product_id = obj.get("productId")
        coordinate = obj.get("coordinate")
        if product_id is None or not coordinate:
            continue
        key = coordinate_to_key(coordinate)
        sid = f"{product_id}:{key}"
        series[sid] = {
            "series_id": sid,
            "product_id": product_id,
            "series_key": key,
            "vector_id": _vector_id(obj.get("vectorId")),
            "dims_json": None,
            "uom": None,
            "scalar_factor": None,
            "attrs_json": None,
        }
        for point in obj.get("vectorDataPoint") or []:
            ref_per = point.get("refPer")
            if not ref_per:
                continue
            status, symbol = point.get("statusCode"), point.get("symbolCode")
            observations.append({
                "series_id": sid,
                "ref_date": ref_per[:10],
                "period": wds_period_label(ref_per, point.get("frequencyCode")),
                "value": _to_float(point.get("value")),
                "status": str(status) if status else None,  # WDS codes; 0 = normal
                "symbol": str(symbol) if symbol else None,
                "release_time": point.get("releaseTime"),
                "source": "wds",
                "source_url": source_url,
            })
    return _finish(conn, series, observations)


def _finish(conn: sqlite3.Connection, series: Dict[str, Dict[str, Any]], observations: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = _upsert(conn, series, observations) if observations else {"inserted": 0, "revised": 0, "unchanged": 0}
    dates = [o["ref_date"] for o in observations]
    return {
        **counts,
        "series_ids": list(series),
        "date_range": [min(dates), max(dates)] if dates else None,
    }


# ── Views ────────────────────────────────────────────────────────────────────

def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def drop_relation(conn: sqlite3.Connection, name: str) -> None:
    """Drop a user table or view called name (never a canonical table)."""
    if name in CANONICAL_TABLES:
        raise ValueError(f"'{name}' is a canonical store table and can't be replaced.")
    row = conn.execute("SELECT type FROM sqlite_master WHERE name = ? AND type IN ('table', 'view')", (name,)).fetchone()
    if row:
        conn.execute(f"DROP {row[0].upper()} {_quote_ident(name)}")


def create_series_view(
    conn: sqlite3.Connection, name: str, series_ids: List[str], date_range: Optional[List[str]]
) -> List[str]:
    """(Re)create VIEW name over the store for these series and dates; return its columns.

    Columns: one per dimension label, then series_key, period, ref_date, value, VECTOR_ID,
    UOM, SCALAR_FACTOR, STATUS, SYMBOL, release_time, product_id, fetched_at.
    """
    if not series_ids:
        raise ValueError("No series to create a view over.")
    dim_names: Dict[str, None] = {}
    marks = ",".join("?" * len(series_ids))
    for (dims_json,) in conn.execute(
        f"SELECT dims_json FROM {SERIES_TABLE} WHERE series_id IN ({marks}) AND dims_json IS NOT NULL", series_ids
    ):
        for k in json.loads(dims_json):
            dim_names.setdefault(k, None)

    dim_cols = [
        f"json_extract(s.dims_json, {_quote_literal('$.' + _quote_ident(d))}) AS {_quote_ident(d)}" for d in dim_names
    ]
    fixed_cols = [
        "s.series_key AS series_key", "o.period AS period", "o.ref_date AS ref_date", "o.value AS value",
        "s.vector_id AS VECTOR_ID", "s.uom AS UOM", "s.scalar_factor AS SCALAR_FACTOR",
        "o.status AS STATUS", "o.symbol AS SYMBOL", "o.release_time AS release_time",
        "s.product_id AS product_id", "o.fetched_at AS fetched_at",
    ]
    where = [f"o.series_id IN ({','.join(_quote_literal(s) for s in series_ids)})"]
    if date_range:
        where.append(f"o.ref_date BETWEEN {_quote_literal(date_range[0])} AND {_quote_literal(date_range[1])}")

    drop_relation(conn, name)
    conn.execute(
        f"CREATE VIEW {_quote_ident(name)} AS SELECT {', '.join(dim_cols + fixed_cols)} "
        f"FROM {OBS_TABLE} o JOIN {SERIES_TABLE} s ON s.series_id = o.series_id "
        f"WHERE {' AND '.join(where)}"
    )
    conn.commit()
    return list(dim_names) + [c.rsplit(" AS ", 1)[1] for c in fixed_cols]
