import sqlite3
import json
from typing import List, Dict, Any
from .connection import get_db_connection
from ..util.sql_helpers import infer_sql_type
from ..models.db_models import TableDataInput
from ..util.logger import log_data_validation_warning, log_sql_debug

def create_table_from_data(table_input: TableDataInput) -> Dict[str, str]:
    """
    Creates a new SQLite table based on the structure of the provided data.
    Infers column names and types from the first item in the data list.
    WARNING: Overwrites the table if it already exists! Use with caution.

    Args:
        table_input: Object containing table_name and data (list of dicts).

    Returns:
        Dict[str, str]: A dictionary indicating success or failure.

    IMPORTANT: The database is persistent and does NOT clean itself automatically. 
    You should clean the database (e.g., list_tables() then DROP TABLE via query_database or rely on this tool overwriting same-named tables) 
    at the beginning or end of your workflow to ensure a fresh state. This tool overwrites the table if it exists.
    """
    table_name = table_input.table_name
    data = table_input.data

    if not data:
        return {"error": "Cannot create table from empty data list."}
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
         return {"error": "Input 'data' must be a list of dictionaries."}
    if not table_name.isidentifier():
         return {"error": f"Invalid table name: '{table_name}'. Use alphanumeric characters and underscores, and cannot be a keyword."}

    # Infer columns and types from the first data item
    columns_def = []
    first_item = data[0]
    valid_column_names = set() # Keep track of valid names added
    for col_name, value in first_item.items():
        # Basic sanitization/validation for column names
        safe_col_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in col_name)
        if not safe_col_name or safe_col_name[0].isdigit() or not safe_col_name.isidentifier():
            log_data_validation_warning(f"Skipping column with potentially invalid original name: '{col_name}' -> '{safe_col_name}'")
            continue
        # Ensure uniqueness after sanitization
        temp_name = safe_col_name
        counter = 1
        while temp_name in valid_column_names:
             temp_name = f"{safe_col_name}_{counter}"
             counter += 1
        safe_col_name = temp_name

        sql_type = infer_sql_type(value)
        columns_def.append(f'"{safe_col_name}" {sql_type}') # Quote column names
        valid_column_names.add(safe_col_name)


    if not columns_def:
        return {"error": "No valid columns found in the first data item after validation."}

    create_sql = f'CREATE TABLE "{table_name}" ({", ".join(columns_def)})'
    drop_sql = f'DROP TABLE IF EXISTS "{table_name}"' # Drop existing table first

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            log_sql_debug(f"Executing: {drop_sql}")
            cursor.execute(drop_sql)
            log_sql_debug(f"Executing: {create_sql}")
            cursor.execute(create_sql)
            conn.commit()
        return {"success": f"Table '{table_name}' created successfully with {len(columns_def)} columns."}
    except sqlite3.Error as e:
        return {"error": f"SQLite error creating table '{table_name}': {e}"}
    except Exception as e:
        return {"error": f"Unexpected error creating table '{table_name}': {e}"}
