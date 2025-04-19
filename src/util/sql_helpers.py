from typing import Any
import json

def infer_sql_type(value: Any) -> str:
    """Infers a basic SQLite data type from a Python value."""
    if isinstance(value, int):
        return "INTEGER"
    elif isinstance(value, float):
        return "REAL"
    elif isinstance(value, (str, bytes, bool, type(None))): # Treat bool/None as TEXT for simplicity
        return "TEXT"
    else:
        # Store complex types like lists/dicts as JSON strings
        return "TEXT"

def convert_value_for_sql(value: Any) -> Any:
    """Convert Python values to SQL-compatible values."""
    if isinstance(value, (list, dict)):
        try:
            return json.dumps(value)
        except TypeError:
            return str(value)  # Fallback
    return value
