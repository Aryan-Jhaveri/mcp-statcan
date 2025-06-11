import sys
from ..config import (
    ENABLE_SERVER_DEBUG,
    ENABLE_SSL_WARNINGS,
    ENABLE_SQL_DEBUG,
    ENABLE_DATA_VALIDATION_WARNINGS,
    ENABLE_SEARCH_PROGRESS
)

def log_server_debug(message: str) -> None:
    """Log server debug messages conditionally."""
    if ENABLE_SERVER_DEBUG:
        print(f"--> {message}", file=sys.stderr)

def log_ssl_warning(message: str) -> None:
    """Log SSL warning messages conditionally."""
    if ENABLE_SSL_WARNINGS:
        print(f"Warning: {message}")

def log_sql_debug(message: str) -> None:
    """Log SQL debug messages conditionally."""
    if ENABLE_SQL_DEBUG:
        print(message)

def log_data_validation_warning(message: str) -> None:
    """Log data validation warning messages conditionally."""
    if ENABLE_DATA_VALIDATION_WARNINGS:
        print(f"Warning: {message}")

def log_search_progress(message: str) -> None:
    """Log search progress messages conditionally."""
    if ENABLE_SEARCH_PROGRESS:
        print(message)