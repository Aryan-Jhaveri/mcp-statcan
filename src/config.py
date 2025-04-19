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