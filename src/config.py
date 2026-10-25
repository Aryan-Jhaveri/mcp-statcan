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
# Set STATCAN_VERIFY_SSL=false to disable verification on broken trust stores.
VERIFY_SSL = os.environ.get("STATCAN_VERIFY_SSL", "true").lower() != "false"

# SDMX REST API configuration
SDMX_BASE_URL = "https://www150.statcan.gc.ca/t1/wds/sdmx/statcan/rest/"
SDMX_XML_ACCEPT = "application/vnd.sdmx.structure+xml;version=2.1"
# Data is fetched as structure-specific XML: StatCan's SDMX-JSON mis-indexes series
# keys and attributes (issue #90); the XML carries codes and attributes inline.
SDMX_DATA_XML_ACCEPT = "application/vnd.sdmx.structurespecificdata+xml;version=2.1"
SDMX_STRUCTURE_CACHE_TTL = 3600  # seconds; DSDs change only when a table is restructured
MAX_SDMX_ROWS = 500  # Safety cap for flattened SDMX rows

# Coordinate padding configuration
EXPECTED_COORD_DIMENSIONS = 10

# Query limits
MAX_QUERY_ROWS = 500

# Ephemeral (in-memory, per-request) SQL — used by query_sdmx in stdio and HTTP mode
MAX_EPHEMERAL_ROWS = 50_000       # Max fetched rows loaded into the in-memory table
EPHEMERAL_QUERY_TIMEOUT = 2.0     # Seconds before a query is interrupted
EPHEMERAL_MAX_VALUE_LENGTH = 1_000_000  # SQLITE_LIMIT_LENGTH: caps string/blob size a query can build
MAX_CONCURRENT_EPHEMERAL_QUERIES = 4  # Bounds worst-case CPU/memory on the hosted free tier

# HTTP transport configuration (Phase 2)
# TRANSPORT: "stdio" (default, local) or "http" (remote, stateless)
# HOST / PORT: bind address for HTTP mode — PORT is the standard Render env var
TRANSPORT = os.environ.get("STATCAN_TRANSPORT", "stdio")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))

# Logging configuration
# Control different types of debug/logging output via environment variables
ENABLE_SERVER_DEBUG = False
ENABLE_SSL_WARNINGS = False
ENABLE_SQL_DEBUG = False
ENABLE_DATA_VALIDATION_WARNINGS = False
ENABLE_SEARCH_PROGRESS = False