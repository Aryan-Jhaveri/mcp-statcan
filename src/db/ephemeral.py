"""Ephemeral in-memory SQL over a list of row dicts.

Used by query_sdmx so hosted (stateless HTTP) users can aggregate fetched data
server-side without a persistent database. Each call builds a fresh
`:memory:` SQLite database, runs one read-only query, and discards it.

The server is shared and multi-tenant, so the query runs under:
  - an authorizer that only permits SELECT, column reads, CTEs and functions
    (no ATTACH, PRAGMA, writes, or load_extension)
  - PRAGMA query_only
  - a progress-handler timeout (EPHEMERAL_QUERY_TIMEOUT)
  - SQLITE_LIMIT_LENGTH so a query can't build huge strings in memory
"""

import sqlite3
import time
from typing import Any, Dict, List

from ..config import EPHEMERAL_MAX_VALUE_LENGTH, EPHEMERAL_QUERY_TIMEOUT, MAX_QUERY_ROWS
from .schema import build_table_statements

_SQLITE_RECURSIVE = getattr(sqlite3, "SQLITE_RECURSIVE", 33)
_ALLOWED_ACTIONS = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, _SQLITE_RECURSIVE}
_BLOCKED_FUNCTIONS = {"load_extension"}


def _authorizer(action: int, arg1: Any, arg2: Any, db_name: Any, trigger: Any) -> int:
    if action not in _ALLOWED_ACTIONS:
        return sqlite3.SQLITE_DENY
    # For SQLITE_FUNCTION, arg2 is the function name
    if action == sqlite3.SQLITE_FUNCTION and str(arg2).lower() in _BLOCKED_FUNCTIONS:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def run_ephemeral_query(
    rows: List[Dict[str, Any]],
    sql: str,
    table_name: str = "data",
    max_rows: int = MAX_QUERY_ROWS,
    timeout: float = EPHEMERAL_QUERY_TIMEOUT,
) -> Dict[str, Any]:
    """Load rows into an in-memory table and run one read-only query against it.

    Returns {"columns", "rows", "table_columns"} plus "message" when the result was
    truncated, or {"error", "table_columns"} on failure.
    """
    if not rows:
        return {"error": "No rows to query."}

    statements = build_table_statements(table_name, rows)
    if "error" in statements:
        return statements
    table_columns = statements["columns"]

    conn = sqlite3.connect(":memory:")
    try:
        conn.execute(statements["create_sql"])
        conn.executemany(statements["insert_sql"], statements["rows"])
        conn.commit()

        conn.execute("PRAGMA query_only = ON")
        if hasattr(conn, "setlimit"):
            conn.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, EPHEMERAL_MAX_VALUE_LENGTH)
            conn.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
        conn.set_authorizer(_authorizer)
        deadline = time.monotonic() + timeout
        conn.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 10_000)

        cursor = conn.execute(sql)
        columns = [d[0] for d in cursor.description] if cursor.description else []
        fetched = cursor.fetchmany(max_rows + 1)
    except sqlite3.DatabaseError as e:
        msg = str(e)
        if "interrupted" in msg:
            msg = f"Query exceeded the {timeout:g}s time limit. Simplify it or narrow the fetched data."
        elif "not authorized" in msg:
            msg = "Only read-only SELECT queries (including WITH/CTEs) are allowed."
        return {"error": f"SQL error: {msg}", "table_columns": table_columns}
    finally:
        conn.close()

    result: Dict[str, Any] = {
        "columns": columns,
        "rows": [dict(zip(columns, r)) for r in fetched[:max_rows]],
        "table_columns": table_columns,
    }
    if len(fetched) > max_rows:
        result["message"] = f"Result truncated to the first {max_rows} rows. Aggregate or add LIMIT."
    return result
