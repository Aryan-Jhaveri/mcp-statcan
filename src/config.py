"""
Configuration module for the StatCan MCP server.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Server configuration
SERVER_NAME = os.getenv("MCP_SERVER_NAME", "StatCan Data")
SERVER_VERSION = os.getenv("MCP_SERVER_VERSION", "0.1.0")
SERVER_HOST = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "5000"))

# Cache configuration
CACHE_DIRECTORY = Path(os.getenv("CACHE_DIRECTORY", "./cache"))
METADATA_CACHE_MAX_SIZE = int(os.getenv("METADATA_CACHE_MAX_SIZE", "1000"))
DATA_CACHE_MAX_SIZE = int(os.getenv("DATA_CACHE_MAX_SIZE", "500"))
CACHE_EXPIRY_SECONDS = int(os.getenv("CACHE_EXPIRY_SECONDS", "86400"))  # 24 hours

# StatCan WDS API configuration
STATCAN_API_BASE_URL = os.getenv(
    "STATCAN_API_BASE_URL", "https://www150.statcan.gc.ca/t1/wds"
)
STATCAN_API_RATE_LIMIT = int(os.getenv("STATCAN_API_RATE_LIMIT", "25"))
STATCAN_API_TIMEOUT = int(os.getenv("STATCAN_API_TIMEOUT", "30"))

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "./logs/mcp-statcan.log")

# Ensure cache directory exists
CACHE_DIRECTORY.mkdir(parents=True, exist_ok=True)

# Ensure log directory exists
Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

def get_config() -> Dict[str, Any]:
    """Return the current configuration as a dictionary."""
    return {
        "server": {
            "name": SERVER_NAME,
            "version": SERVER_VERSION,
            "host": SERVER_HOST,
            "port": SERVER_PORT,
        },
        "cache": {
            "directory": str(CACHE_DIRECTORY),
            "metadata_max_size": METADATA_CACHE_MAX_SIZE,
            "data_max_size": DATA_CACHE_MAX_SIZE,
            "expiry_seconds": CACHE_EXPIRY_SECONDS,
        },
        "statcan_api": {
            "base_url": STATCAN_API_BASE_URL,
            "rate_limit": STATCAN_API_RATE_LIMIT,
            "timeout": STATCAN_API_TIMEOUT,
        },
        "logging": {
            "level": LOG_LEVEL,
            "file": LOG_FILE,
        },
    }