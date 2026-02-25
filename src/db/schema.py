import sqlite3
import json
from typing import List, Dict, Any
from .connection import get_db_connection
from ..util.sql_helpers import infer_sql_type, convert_value_for_sql
from ..models.db_models import TableDataInput
from ..util.logger import log_data_validation_warning, log_sql_debug

def create_table_from_data(table_input: TableDataInput) -> Dict[str, Any]:
    """
    Creates a new SQLite table from the provided data AND immediately inserts all rows.
    Infers column names and types from the first item in the data list.
    WARNING: Overwrites the table if it already exists.

    Use this as a single step to store fetched API data — no need to call
    insert_data_into_table afterwards. Use insert_data_into_table only to
    append more rows to an already-existing table.

    Args:
        table_input: Object containing table_name and data (list of dicts).

    Returns:
        Dict[str, Any]: A summary with table name, columns created, and rows inserted.

    IMPORTANT: The database is persistent and does NOT clean itself automatically.
    This tool overwrites the table if it exists, giving you a clean slate each call.
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
    valid_column_names = []  # Ordered list of sanitized column names
    seen_names = set()
    first_item = data[0]
    for col_name, value in first_item.items():
        safe_col_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in col_name)
        if not safe_col_name or safe_col_name[0].isdigit() or not safe_col_name.isidentifier():
            log_data_validation_warning(f"Skipping column with potentially invalid original name: '{col_name}' -> '{safe_col_name}'")
            continue
        # Deduplicate after sanitization
        temp_name = safe_col_name
        counter = 1
        while temp_name in seen_names:
            temp_name = f"{safe_col_name}_{counter}"
            counter += 1
        safe_col_name = temp_name
        seen_names.add(safe_col_name)

        sql_type = infer_sql_type(value)
        columns_def.append(f'"{safe_col_name}" {sql_type}')
        valid_column_names.append(safe_col_name)

    if not columns_def:
        return {"error": "No valid columns found in the first data item after validation."}

    create_sql = f'CREATE TABLE "{table_name}" ({", ".join(columns_def)})'
    drop_sql = f'DROP TABLE IF EXISTS "{table_name}"'

    # Build insert placeholders based on the columns we defined
    placeholders = ", ".join(["?"] * len(valid_column_names))
    quoted_columns = ", ".join([f'"{c}"' for c in valid_column_names])
    insert_sql = f'INSERT INTO "{table_name}" ({quoted_columns}) VALUES ({placeholders})'

    # Pre-process all rows: sanitize keys and align to column order
    rows_to_insert = []
    for item in data:
        sanitized = {}
        seen_in_row: set = set()
        for key, val in item.items():
            skey = ''.join(c if c.isalnum() or c == '_' else '_' for c in key)
            if not skey or skey[0].isdigit() or not skey.isidentifier():
                continue
            t = skey
            n = 1
            while t in seen_in_row:
                t = f"{skey}_{n}"
                n += 1
            skey = t
            seen_in_row.add(skey)
            sanitized[skey] = val

        row_tuple = tuple(
            convert_value_for_sql(sanitized.get(col)) for col in valid_column_names
        )
        rows_to_insert.append(row_tuple)

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            log_sql_debug(f"Executing: {drop_sql}")
            cursor.execute(drop_sql)
            log_sql_debug(f"Executing: {create_sql}")
            cursor.execute(create_sql)
            log_sql_debug(f"Inserting {len(rows_to_insert)} rows into '{table_name}'...")
            cursor.executemany(insert_sql, rows_to_insert)
            conn.commit()
        return {
            "success": f"Table '{table_name}' created with {len(valid_column_names)} columns and {len(rows_to_insert)} rows inserted.",
            "table": table_name,
            "columns": valid_column_names,
            "rows_inserted": len(rows_to_insert),
        }
    except sqlite3.Error as e:
        return {"error": f"SQLite error creating table '{table_name}': {e}"}
    except Exception as e:
        return {"error": f"Unexpected error creating table '{table_name}': {e}"}
