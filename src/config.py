# Configuration parameters for the Statistics Canada API MCP Server

import os
import pwd as _pwd

def _real_home() -> str:
    """Return the real user home directory from the OS passwd database.

    Unlike os.path.expanduser("~"), this is immune to HOME env-var manipulation
    by MCP launchers (Claude Desktop, uvx, MCP Inspector) that sandbox or alter
    the subprocess environment.
    """
    try:
        return _pwd.getpwuid(os.getuid()).pw_dir
    except Exception:
        return os.path.expanduser("~")  # last-resort fallback


# Database configuration
# Use an explicit absolute path so the DB works regardless of the MCP server's
# working directory (which varies by client — Claude Desktop, Cursor, etc.).
# STATCAN_DB_FILE env var or --db-path CLI flag override the default.
_default_db_dir = os.path.join(_real_home(), ".statcan-mcp")
_default_db_path = os.path.join(_default_db_dir, "statcan_data.db")
DB_FILE = os.environ.get("STATCAN_DB_FILE", _default_db_path)

# Best-effort directory creation at import time.
# get_db_connection() also does this defensively at connection time.
_db_parent = os.path.dirname(DB_FILE)
if _db_parent:
    try:
        os.makedirs(_db_parent, exist_ok=True)
    except OSError:
        pass  # Will be retried (with a real error) at connection time

# API configuration
BASE_URL = "https://www150.statcan.gc.ca/t1/wds/rest"
TIMEOUT_SMALL = 30.0  # For simple queries
TIMEOUT_MEDIUM = 60.0  # For list endpoints
TIMEOUT_LARGE = 120.0  # For bulk data endpoints
VERIFY_SSL = False  # WARNING: Security risk!

# Coordinate padding configuration
EXPECTED_COORD_DIMENSIONS = 10

# Query limits
MAX_QUERY_ROWS = 500

# Logging configuration
# Control different types of debug/logging output via environment variables
ENABLE_SERVER_DEBUG = False
ENABLE_SSL_WARNINGS = False
ENABLE_SQL_DEBUG = False
ENABLE_DATA_VALIDATION_WARNINGS = False
ENABLE_SEARCH_PROGRESS = False