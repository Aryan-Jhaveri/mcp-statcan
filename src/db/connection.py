import sqlite3
from .. import config

def get_db_connection() -> sqlite3.Connection:
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(config.DB_FILE)
    # Return rows as dictionary-like objects
    conn.row_factory = sqlite3.Row
    return conn
