"""
Configuration module for the StatCan MCP server.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List

from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Server configuration
SERVER_NAME = os.getenv("MCP_SERVER_NAME", "StatCan Data")
SERVER_VERSION = os.getenv("MCP_SERVER_VERSION", "0.1.0")
SERVER_HOST = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "5000"))

# Cache configuration
# Use a directory inside the user's home folder to ensure write permissions
CACHE_DIRECTORY = Path(os.getenv("CACHE_DIRECTORY", os.path.expanduser("~/statcan_cache")))
METADATA_CACHE_MAX_SIZE = int(os.getenv("METADATA_CACHE_MAX_SIZE", "1000"))
DATA_CACHE_MAX_SIZE = int(os.getenv("DATA_CACHE_MAX_SIZE", "500"))
CACHE_EXPIRY_SECONDS = int(os.getenv("CACHE_EXPIRY_SECONDS", "86400"))  # 24 hours

# Helper function to parse comma-separated environment variables
def _parse_list_env_var(var_name: str, default: List[str] = None) -> List[str]:
    """Parse a comma-separated environment variable into a list.
    
    Args:
        var_name: Name of the environment variable
        default: Default list if environment variable is not set
        
    Returns:
        List of strings
    """
    if default is None:
        default = []
    
    value = os.getenv(var_name)
    if not value:
        return default
    
    # Split by comma and strip whitespace
    return [item.strip() for item in value.split(",") if item.strip()]

# Enhanced cache configuration for specialized data types
SEARCH_CACHE_MAX_SIZE = int(os.getenv("SEARCH_CACHE_MAX_SIZE", "200"))
SEARCH_CACHE_EXPIRY_SECONDS = int(os.getenv("SEARCH_CACHE_EXPIRY_SECONDS", "172800"))  # 48 hours

VECTOR_CACHE_MAX_SIZE = int(os.getenv("VECTOR_CACHE_MAX_SIZE", "300"))
VECTOR_CACHE_EXPIRY_SECONDS = int(os.getenv("VECTOR_CACHE_EXPIRY_SECONDS", "43200"))  # 12 hours

CUBE_CACHE_MAX_SIZE = int(os.getenv("CUBE_CACHE_MAX_SIZE", "150"))
CUBE_CACHE_EXPIRY_SECONDS = int(os.getenv("CUBE_CACHE_EXPIRY_SECONDS", "604800"))  # 7 days

# Tiered caching strategy configuration
HOT_CACHE_VECTORS = _parse_list_env_var("HOT_CACHE_VECTORS", ["v41690973", "v21581063", "v111955426"])  # CPI, GDP, Employment
HOT_CACHE_CUBES = _parse_list_env_var("HOT_CACHE_CUBES", ["1810000401", "3610043402"])  # CPI, GDP tables
PRELOAD_HOT_CACHE = os.getenv("PRELOAD_HOT_CACHE", "true").lower() == "true"

# StatCan WDS API configuration
STATCAN_API_BASE_URL = os.getenv(
    "STATCAN_API_BASE_URL", "https://www150.statcan.gc.ca/t1/wds/rest"
)
STATCAN_API_RATE_LIMIT = int(os.getenv("STATCAN_API_RATE_LIMIT", "25"))
STATCAN_API_TIMEOUT = int(os.getenv("STATCAN_API_TIMEOUT", "30"))
STATCAN_API_RETRIES = int(os.getenv("STATCAN_API_RETRIES", "3"))
STATCAN_API_RETRY_DELAY = float(os.getenv("STATCAN_API_RETRY_DELAY", "1.5"))  # seconds

# Scalar factor descriptions
SCALAR_FACTOR_CODES = {
    0: "Units",
    1: "Tens",
    2: "Hundreds", 
    3: "Thousands",
    4: "Tens of thousands",
    5: "Hundreds of thousands",
    6: "Millions",
    7: "Tens of millions",
    8: "Hundreds of millions",
    9: "Billions",
    10: "Trillions"
}

# Frequency descriptions
FREQUENCY_CODES = {
    1: "Annual",
    2: "Semi-annual",
    4: "Quarterly",
    6: "Monthly",
    7: "Bimonthly",
    8: "Weekly",
    9: "Daily",
    12: "Semi-monthly",
    13: "Every 2 years",
    18: "Occasional",
    19: "Every 5 years",
    50: "Variable"
}

# Units of measurement codes with standardized labels
UOM_CODES = {
    # Common economic indicators
    17: "Index (2002=100)",  # CPI
    21: "Index (2018=100)",  # Updated CPI base year
    223: "Persons",  # Employment
    304: "Jobs",      # Employment (alternate measure)
    428: "Thousands of persons",  # Labour force
    429: "Millions of persons",   # Population measures
    
    # Financial and economic indicators
    0: "Units",
    205: "Dollars",
    206: "Thousands of dollars",
    207: "Millions of dollars",
    208: "Billions of dollars",
    209: "Dollars per capita",
    237: "Percent",
    238: "Percentage points",
    280: "Ratio",
    
    # Trade and production
    272: "Dollars (USD)",
    289: "Cubic metres",
    290: "Square metres",
    288: "Tonnes",
    291: "Kilograms", 
    295: "Hectares",
    296: "Square kilometers",
    
    # Time-based measures
    301: "Hours",
    302: "Hours per week",
    
    # Other common units
    320: "Petajoules",
    321: "Gigajoules",
    334: "Megawatts",
    350: "Degrees Celsius",
    
    # Housing and construction
    370: "Housing units",
    371: "Housing starts",
    
    # Special units for specific datasets
    400: "Current dollars",
    401: "Constant dollars",
    402: "Chained (2017) dollars",
}

# Symbol codes for data point interpretation
SYMBOL_CODES = {
    0: "",  # Regular value
    1: "x",  # Suppressed for confidentiality
    2: "...",  # Data not available
    3: "F",  # Too unreliable to be published
    4: "..",  # Not applicable
    5: "r",  # Revised
    6: "p",  # Preliminary
    7: "e",  # Estimated
    8: "E",  # Use with caution
    9: "c",  # Confidential
    10: "D",  # Withheld for data quality reasons
}

# Status codes
STATUS_CODES = {
    0: "Normal",
    1: "Preliminary",
    2: "Revised",
    3: "Discontinued"
}

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "mcp-statcan.log"))
LOG_FORMAT = os.getenv(
    "LOG_FORMAT", 
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
ENABLE_REQUEST_LOGGING = os.getenv("ENABLE_REQUEST_LOGGING", "false").lower() == "true"

# Ensure directories exist with error handling
try:
    # Ensure cache directory exists
    CACHE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    
    # Ensure log directory exists
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
except OSError as e:
    import sys
    print(f"Error creating directories: {e}", file=sys.stderr)
    # Fall back to temporary directory if needed
    import tempfile
    temp_dir = Path(tempfile.gettempdir()) / "statcan_mcp"
    print(f"Falling back to temporary directory: {temp_dir}", file=sys.stderr)
    
    # Update paths
    CACHE_DIRECTORY = temp_dir / "cache"
    LOG_FILE = str(temp_dir / "logs" / "mcp-statcan.log")
    
    # Try again with temp directory
    try:
        CACHE_DIRECTORY.mkdir(parents=True, exist_ok=True)
        Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    except OSError as e2:
        print(f"Failed to create temporary directories: {e2}", file=sys.stderr)
        # Last resort - use in-memory only, no logging to file
        print("WARNING: Operating in memory-only mode with no persistent cache", file=sys.stderr)

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
            "search_max_size": SEARCH_CACHE_MAX_SIZE,
            "search_expiry_seconds": SEARCH_CACHE_EXPIRY_SECONDS,
            "vector_max_size": VECTOR_CACHE_MAX_SIZE,
            "vector_expiry_seconds": VECTOR_CACHE_EXPIRY_SECONDS,
            "cube_max_size": CUBE_CACHE_MAX_SIZE,
            "cube_expiry_seconds": CUBE_CACHE_EXPIRY_SECONDS,
            "hot_cache_vectors": HOT_CACHE_VECTORS,
            "hot_cache_cubes": HOT_CACHE_CUBES,
            "preload_hot_cache": PRELOAD_HOT_CACHE,
        },
        "statcan_api": {
            "base_url": STATCAN_API_BASE_URL,
            "rate_limit": STATCAN_API_RATE_LIMIT,
            "timeout": STATCAN_API_TIMEOUT,
            "retries": STATCAN_API_RETRIES,
            "retry_delay": STATCAN_API_RETRY_DELAY,
        },
        "metadata": {
            "scalar_factors": SCALAR_FACTOR_CODES,
            "frequencies": FREQUENCY_CODES,
            "units_of_measure": UOM_CODES,
            "symbols": SYMBOL_CODES,
            "statuses": STATUS_CODES,
        },
        "logging": {
            "level": LOG_LEVEL,
            "file": LOG_FILE,
            "format": LOG_FORMAT,
            "enable_request_logging": ENABLE_REQUEST_LOGGING,
        },
    }