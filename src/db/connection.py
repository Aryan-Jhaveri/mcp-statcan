import os
import sqlite3
from .. import config

def get_db_connection() -> sqlite3.Connection:
    """Establishes a connection to the SQLite database.

    Ensures the parent directory exists before connecting, so this works
    regardless of whether config.py's import-time makedirs ran successfully
    (e.g. in sandboxed MCP launchers or environments with altered HOME).

    Raises sqlite3.OperationalError with the actual DB path in the message
    so failures are easy to diagnose in MCP tool error responses.
    """
    db_path = config.DB_FILE
    parent_dir = os.path.dirname(db_path)
    if parent_dir:
        try:
            os.makedirs(parent_dir, exist_ok=True)
        except OSError as exc:
            raise sqlite3.OperationalError(
                f"Cannot create database directory '{parent_dir}': {exc}. "
                f"Set STATCAN_DB_FILE env var or use --db-path to override."
            ) from exc
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.OperationalError as exc:
        raise sqlite3.OperationalError(
            f"Cannot open database at '{db_path}': {exc}. "
            f"Set STATCAN_DB_FILE env var or pass --db-path to statcan-mcp-server."
        ) from exc
    conn.row_factory = sqlite3.Row
    return conn
