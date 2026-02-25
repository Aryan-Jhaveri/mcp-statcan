# Configuration parameters for the Statistics Canada API MCP Server

import os

# Database configuration
# Use an explicit absolute path so the DB works regardless of the MCP server's
# working directory (which varies by client — Claude Desktop, Cursor, etc.).
_default_db_dir = os.path.join(os.path.expanduser("~"), ".statcan-mcp")
_default_db_path = os.path.join(_default_db_dir, "statcan_data.db")
DB_FILE = os.environ.get("STATCAN_DB_FILE", _default_db_path)

# Ensure the directory exists at import time
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

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