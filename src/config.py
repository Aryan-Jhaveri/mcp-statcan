# Configuration parameters for the Statistics Canada API MCP Server

import os

# Database configuration
DB_FILE = os.environ.get("STATCAN_DB_FILE", "temp_statcan_data.db")

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
ENABLE_SERVER_DEBUG = os.environ.get("STATCAN_SERVER_DEBUG", "false").lower() == "true"
ENABLE_SSL_WARNINGS = os.environ.get("STATCAN_SSL_WARNINGS", "false").lower() == "true"
ENABLE_SQL_DEBUG = os.environ.get("STATCAN_SQL_DEBUG", "false").lower() == "true"
ENABLE_DATA_VALIDATION_WARNINGS = os.environ.get("STATCAN_DATA_VALIDATION_WARNINGS", "false").lower() == "true"
ENABLE_SEARCH_PROGRESS = os.environ.get("STATCAN_SEARCH_PROGRESS", "false").lower() == "true"