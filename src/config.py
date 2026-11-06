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
# Fail fast on a stall (#161). StatCan sometimes accepts a request and then sends nothing
# for 20-30 s; an identical retry usually answers in under a second. httpx applies these
# per phase: connect, and each wait for bytes (not the whole download), so large
# responses that stream steadily still load. Measured 6 Nov 2026: WDS lookups and SDMX
# data answer in <1 s (broad SDMX wildcards up to ~3 s, gaps between chunks <0.6 s).
# One stall now costs ~FIRST_BYTE + 1 s before the retry; all 3 attempts stalling ~33 s.
HTTP_CONNECT_TIMEOUT = 5.0
HTTP_FIRST_BYTE_TIMEOUT = 10.0
# Set STATCAN_VERIFY_SSL=false to disable verification on broken trust stores.
VERIFY_SSL = os.environ.get("STATCAN_VERIFY_SSL", "true").lower() != "false"

# SDMX REST API configuration
SDMX_BASE_URL = "https://www150.statcan.gc.ca/t1/wds/sdmx/statcan/rest/"
SDMX_XML_ACCEPT = "application/vnd.sdmx.structure+xml;version=2.1"
# Data is fetched as structure-specific XML: StatCan's SDMX-JSON mis-indexes series
# keys and attributes (issue #90); the XML carries codes and attributes inline.
SDMX_DATA_XML_ACCEPT = "application/vnd.sdmx.structurespecificdata+xml;version=2.1"
SDMX_STRUCTURE_CACHE_TTL = 3600  # seconds; DSDs change only when a table is restructured
# httpx applies this per phase (connect, and each wait for bytes), not to the whole
# download. A stalled DSD sends no headers for ~30 s, so it fails here and is retried;
# the largest DSDs (98100023 is 37 MB, ~25 s) start in ~0.1 s and stream steadily (#145).
SDMX_STRUCTURE_TIMEOUT = 8.0
SDMX_STRUCTURE_ATTEMPTS = 3  # tries when StatCan returns a truncated DSD as HTTP 200
MAX_SDMX_ROWS = 500  # Safety cap for flattened SDMX rows
# Above this many observations, get_sdmx_data returns a summary unless full=true (#139)
SDMX_SUMMARY_THRESHOLD = 100
SDMX_SUMMARY_MAX_SERIES = 10

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