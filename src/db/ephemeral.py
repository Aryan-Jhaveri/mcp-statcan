"""Ephemeral in-memory SQL over a list of row dicts.

Used by query_sdmx so hosted (stateless HTTP) users can aggregate fetched data
server-side without a persistent database. Each call builds a fresh
`:memory:` SQLite database, runs one read-only query, and discards it.

The server is shared and multi-tenant, so the query follows SQLite's guidance for
untrusted SQL (https://sqlite.org/security.html) and Datasette's approach:
  - an authorizer that only permits SELECT, column reads, CTEs and functions
    (no ATTACH, PRAGMA, writes, or load_extension)
  - PRAGMA query_only, trusted_schema=OFF, and SQLITE_DBCONFIG_DEFENSIVE where available
  - a progress-handler timeout (EPHEMERAL_QUERY_TIMEOUT), checked every 1000 VM ops
  - lowered sqlite3_limit() values (_QUERY_LIMITS) against oversized strings/queries
Each call uses its own connection, so one request's timeout can't cancel another's.
"""

import sqlite3
import time
from typing import Any, Dict, List

from ..config import EPHEMERAL_MAX_VALUE_LENGTH, EPHEMERAL_QUERY_TIMEOUT, MAX_QUERY_ROWS
from .schema import build_table_statements

_SQLITE_RECURSIVE = getattr(sqlite3, "SQLITE_RECURSIVE", 33)
_ALLOWED_ACTIONS = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, _SQLITE_RECURSIVE}
_BLOCKED_FUNCTIONS = {"load_extension"}

# Lowered from SQLite defaults, following https://sqlite.org/security.html. Some are
# looser than that page's "high-security" values so ordinary analytical SQL
# (nested CASE, multi-way UNION, COALESCE with many args) still works.
_QUERY_LIMITS = {
    sqlite3.SQLITE_LIMIT_LENGTH: EPHEMERAL_MAX_VALUE_LENGTH,
    sqlite3.SQLITE_LIMIT_SQL_LENGTH: 100_000,
    sqlite3.SQLITE_LIMIT_COLUMN: 200,
    sqlite3.SQLITE_LIMIT_EXPR_DEPTH: 100,
    sqlite3.SQLITE_LIMIT_COMPOUND_SELECT: 20,
    sqlite3.SQLITE_LIMIT_VDBE_OP: 100_000,
    sqlite3.SQLITE_LIMIT_FUNCTION_ARG: 32,
    sqlite3.SQLITE_LIMIT_ATTACHED: 0,
    sqlite3.SQLITE_LIMIT_LIKE_PATTERN_LENGTH: 200,
    sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER: 10,
    sqlite3.SQLITE_LIMIT_TRIGGER_DEPTH: 10,
}


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
        conn.execute("PRAGMA trusted_schema = OFF")
        # setlimit/setconfig were added in Python 3.11/3.12; older versions rely on
        # the authorizer, timeout and row cap alone.
        if hasattr(conn, "setconfig"):
            conn.setconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True)
        if hasattr(conn, "setlimit"):
            for limit, value in _QUERY_LIMITS.items():
                conn.setlimit(limit, value)
        conn.set_authorizer(_authorizer)
        deadline = time.monotonic() + timeout
        conn.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 1000)

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
