import sqlite3
import json
from typing import List, Dict, Any
from fastmcp import FastMCP
from .connection import get_db_connection
from ..models.db_models import TableDataInput, TableNameInput, QueryInput
from ..util.sql_helpers import convert_value_for_sql
from ..config import MAX_QUERY_ROWS
from .schema import create_table_from_data

def register_db_tools(mcp: FastMCP):
    """Register database tools with the MCP server."""

    # Add create_table_from_data from schema module
    mcp.tool()(create_table_from_data)

    @mcp.tool()
    def insert_data_into_table(table_input: TableDataInput) -> Dict[str, str]:
        """
        Inserts data (list of dictionaries) into an existing SQLite table.
        It dynamically determines columns from the table schema and inserts corresponding
        values from the dictionaries, handling missing keys gracefully. It attempts to
        match sanitized dictionary keys to table columns.

        Args:
            table_input: Object containing table_name and data (list of dicts).

        Returns:
            Dict[str, str]: A dictionary indicating success (with row count) or failure.
        """
        table_name = table_input.table_name
        data = table_input.data

        if not data:
            return {"success": f"No data provided to insert into '{table_name}'"}
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            return {"error": "Input 'data' must be a list of dictionaries."}
        if not table_name.isidentifier():
             return {"error": f"Invalid table name: '{table_name}'. Use alphanumeric characters and underscores."}

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # Get actual column names from the table schema
                cursor.execute(f'PRAGMA table_info("{table_name}")')
                schema_info = cursor.fetchall()
                if not schema_info:
                    return {"error": f"Could not retrieve schema for table '{table_name}'. Does it exist?"}
                table_columns = [row['name'] for row in schema_info]
                table_columns_set = set(table_columns)

                # Prepare data for executemany, matching dict keys to table columns
                rows_to_insert = []
                skipped_keys = set()
                processed_count = 0
                for item_dict in data:
                    row_tuple = []
                    valid_row = True
                    # Sanitize keys from the input dictionary *before* matching
                    sanitized_item_dict = {}
                    original_keys_map = {} # Map sanitized back to original if needed later
                    processed_keys_in_row = set()
                    for key, value in item_dict.items():
                        safe_key = ''.join(c if c.isalnum() or c == '_' else '_' for c in key)
                        if not safe_key or safe_key[0].isdigit() or not safe_key.isidentifier():
                            if key not in skipped_keys:
                                 print(f"Warning: Skipping invalid key '{key}' from input data during insert.")
                                 skipped_keys.add(key)
                            continue
                        # Handle duplicate sanitized keys from the *same input dict* if necessary
                        temp_key = safe_key
                        counter = 1
                        while temp_key in processed_keys_in_row:
                            temp_key = f"{safe_key}_{counter}"
                            counter += 1
                        safe_key = temp_key
                        processed_keys_in_row.add(safe_key)

                        sanitized_item_dict[safe_key] = value
                        original_keys_map[safe_key] = key


                    # Build the tuple based on table_columns order
                    for col_name in table_columns:
                        if col_name in sanitized_item_dict:
                            value = sanitized_item_dict[col_name]
                            # Convert complex types to JSON strings if needed
                            row_tuple.append(convert_value_for_sql(value))
                        else:
                            # Key from table schema not found in (sanitized) input dict
                            row_tuple.append(None) # Insert NULL for missing columns

                    if valid_row:
                        rows_to_insert.append(tuple(row_tuple))
                        processed_count += 1

                if not rows_to_insert:
                     return {"error": f"No data could be prepared for insertion into '{table_name}' (check data format and table schema match after key sanitization). Processed {processed_count}/{len(data)} input items."}

                placeholders = ", ".join(["?"] * len(table_columns))
                quoted_columns = ", ".join([f'"{col}"' for col in table_columns])
                insert_sql = f'INSERT INTO "{table_name}" ({quoted_columns}) VALUES ({placeholders})'

                print(f"Executing INSERT for {len(rows_to_insert)} rows into {table_name}...")
                cursor.executemany(insert_sql, rows_to_insert)
                conn.commit()
                return {"success": f"Inserted {cursor.rowcount} rows into '{table_name}'. Processed {processed_count}/{len(data)} input items."}

        except sqlite3.Error as e:
            # Provide more specific error info if possible
            if "no such table" in str(e).lower():
                 return {"error": f"SQLite error inserting into '{table_name}': Table does not exist. Use 'create_table_from_data' first."}
            elif "has no column named" in str(e).lower():
                 # This error shouldn't happen with PRAGMA approach, but as fallback
                 return {"error": f"SQLite error inserting into '{table_name}': Column mismatch. Check data keys vs table schema."}
            else:
                 return {"error": f"SQLite error inserting into '{table_name}': {e}"}
        except Exception as e:
            return {"error": f"Unexpected error inserting into '{table_name}': {e}"}

    @mcp.tool()
    def list_tables() -> Dict[str, Any]:
        """
        Lists all user-created tables in the SQLite database.

        Returns:
            Dict[str, Any]: Dictionary containing a list of table names or an error message.
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Select names of tables, excluding sqlite system tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                # Fetch all results as dictionaries (due to row_factory)
                tables = [row['name'] for row in cursor.fetchall()]
                return {"tables": tables}
        except sqlite3.Error as e:
            return {"error": f"SQLite error listing tables: {e}"}
        except Exception as e:
            return {"error": f"Unexpected error listing tables: {e}"}

    @mcp.tool()
    def get_table_schema(table_name_input: TableNameInput) -> Dict[str, Any]:
        """
        Retrieves the schema (column names and types) for a specific table.

        Args:
            table_name_input: Object containing the table_name.

        Returns:
            Dict[str, Any]: Dictionary describing the schema or an error message.
        """
        table_name = table_name_input.table_name
        # Basic validation for table name
        if not table_name.isidentifier():
             return {"error": f"Invalid table name: '{table_name}'. Use alphanumeric characters and underscores."}

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Use PRAGMA for schema info, quoting the table name for safety
                cursor.execute(f'PRAGMA table_info("{table_name}")')
                schema_rows = cursor.fetchall()
                # Check if the table exists / has columns
                if not schema_rows:
                     # Verify the table actually exists before saying no columns
                     cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                     if cursor.fetchone():
                          return {"schema": [], "message": f"Table '{table_name}' exists but has no columns defined (or PRAGMA failed)."}
                     else:
                          return {"error": f"Table '{table_name}' not found."}

                # Format the schema information nicely
                schema = [{"name": row['name'], "type": row['type'], "nullable": not row['notnull'], "primary_key": bool(row['pk'])} for row in schema_rows]
                return {"schema": schema}
        except sqlite3.Error as e:
            return {"error": f"SQLite error getting schema for '{table_name}': {e}"}
        except Exception as e:
            return {"error": f"Unexpected error getting schema for '{table_name}': {e}"}

    @mcp.tool()
    def query_database(query_input: QueryInput) -> Dict[str, Any]:
        """
        Executes a read-only SQL query (SELECT or PRAGMA) against the database and returns the results.
        WARNING: Potential security risk! Avoid using this tool with untrusted input
        or queries that modify data (INSERT, UPDATE, DELETE). Prefer more specific tools
        like list_tables or get_table_schema when possible. Results may be truncated.

        Args:
            query_input: Object containing the sql_query string.

        Returns:
            Dict[str, Any]: Dictionary with 'columns', 'rows' (list of dicts), and optionally a 'message', or an error message.
        """
        query = query_input.sql_query.strip()
        # Basic check to prevent obviously harmful commands (can be bypassed)
        # Allow PRAGMA for schema inspection etc.
        if not query.lower().startswith("select") and not query.lower().startswith("pragma"):
             return {"error": "Only SELECT or PRAGMA queries are allowed for safety."}
        # Add a simple check for multiple statements which might indicate injection attempts
        if ';' in query[:-1]: # Check for semicolons anywhere except potentially the very end
            return {"error": "Multiple SQL statements are not allowed in a single query."}


        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                print(f"Executing query: {query}")
                cursor.execute(query)
                results = cursor.fetchall() # Fetch all rows based on conn.row_factory

                # Determine columns even if there are no results for SELECT/PRAGMA
                columns = []
                if cursor.description:
                    columns = [description[0] for description in cursor.description]

                # Convert Row objects to simple dictionaries for the output
                rows = [dict(row) for row in results]

                # Limit the number of rows returned to prevent exceeding limits
                message = None
                if len(rows) > MAX_QUERY_ROWS:
                    print(f"Warning: Query returned {len(rows)} rows. Truncating to {MAX_QUERY_ROWS}.")
                    rows = rows[:MAX_QUERY_ROWS]
                    message = f"Result truncated to the first {MAX_QUERY_ROWS} rows."

                output = {"columns": columns, "rows": rows}
                if message:
                    output["message"] = message
                return output

        except sqlite3.Error as e:
            # Provide potentially more helpful error messages
            error_msg = f"SQLite error executing query: {e}"
            if "no such table" in str(e):
                error_msg += ". Use list_tables() to see available tables."
            elif "no such column" in str(e):
                error_msg += ". Use get_table_schema() to see available columns for the table."
            return {"error": error_msg}
        except Exception as e:
            return {"error": f"Unexpected error executing query: {e}"}
