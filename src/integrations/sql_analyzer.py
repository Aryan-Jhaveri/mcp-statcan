"""
Integration with the j4c0bs/mcp-server-sql-analyzer MCP server.

This module provides functionality for advanced SQL queries and transformations
using the j4c0bs/mcp-server-sql-analyzer MCP server.
"""

import logging
import json
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

class SQLAnalyzerIntegration:
    """Integration with the j4c0bs/mcp-server-sql-analyzer MCP server."""
    
    @staticmethod
    def prepare_sql_data(data: List[Dict[str, Any]], table_name: str = "statcan_data") -> str:
        """
        Convert time series data to CREATE TABLE and INSERT statements for SQL analysis.
        
        Args:
            data: List of data points
            table_name: Name of the SQL table to create
            
        Returns:
            SQL CREATE TABLE and INSERT statements
        """
        if not data:
            return f"CREATE TABLE {table_name} (date TEXT, value REAL);"
        
        # Determine columns based on first data point
        sample = data[0]
        columns = []
        
        # Standard mapping for common field names
        field_mapping = {
            "refPer": ("date", "TEXT"),
            "date": ("date", "TEXT"),
            "value": ("value", "REAL"),
            "vectorId": ("vector_id", "TEXT"),
            "SeriesTitleEn": ("title", "TEXT"),
            "decimals": ("decimals", "INTEGER"),
            "scalarFactorCode": ("scalar_factor", "INTEGER"),
            "symbolCode": ("symbol_code", "INTEGER")
        }
        
        # Create columns list
        for key in sample.keys():
            if key in field_mapping:
                col_name, col_type = field_mapping[key]
                columns.append((col_name, col_type))
            else:
                # For unknown fields, infer type
                value = sample[key]
                if isinstance(value, (int, float)):
                    columns.append((key.lower(), "REAL"))
                else:
                    columns.append((key.lower(), "TEXT"))
        
        # Create CREATE TABLE statement
        create_stmt = f"CREATE TABLE {table_name} (\n"
        create_stmt += ",\n".join([f"    {col_name} {col_type}" for col_name, col_type in columns])
        create_stmt += "\n);"
        
        # Create INSERT statements
        insert_stmts = []
        for item in data:
            values = []
            for key, _ in columns:
                # Map from original field name to column name
                orig_key = next((k for k, (n, _) in field_mapping.items() if n == key), key)
                
                value = item.get(orig_key, None)
                
                if value is None:
                    values.append("NULL")
                elif isinstance(value, (int, float)):
                    values.append(str(value))
                else:
                    # Escape single quotes in strings
                    value_str = str(value).replace("'", "''")
                    values.append(f"'{value_str}'")
            
            insert_stmt = f"INSERT INTO {table_name} VALUES ({', '.join(values)});"
            insert_stmts.append(insert_stmt)
        
        # Combine all statements
        sql_script = create_stmt + "\n\n" + "\n".join(insert_stmts)
        
        return sql_script
    
    @staticmethod
    def generate_analysis_query(query_type: str, table_name: str = "statcan_data") -> str:
        """
        Generate SQL query for analysis based on query type.
        
        Args:
            query_type: Type of analysis (trends, aggregation, etc.)
            table_name: Name of the SQL table
            
        Returns:
            SQL query for the requested analysis
        """
        queries = {
            "trends": f"""
-- Analyze trends in the time series data
SELECT 
    strftime('%Y', date) AS year,
    AVG(value) AS avg_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    (MAX(value) - MIN(value)) AS range_value
FROM {table_name}
GROUP BY year
ORDER BY year;
""",
            "growth_rates": f"""
-- Calculate growth rates between periods
WITH ordered_data AS (
    SELECT 
        date,
        value,
        LAG(value) OVER (ORDER BY date) AS prev_value
    FROM {table_name}
)
SELECT 
    date,
    value,
    prev_value,
    CASE 
        WHEN prev_value = 0 OR prev_value IS NULL THEN NULL
        ELSE ROUND((value - prev_value) / prev_value * 100, 2) 
    END AS percent_change
FROM ordered_data
WHERE prev_value IS NOT NULL
ORDER BY date;
""",
            "moving_average": f"""
-- Calculate 3-period moving average
WITH value_series AS (
    SELECT 
        date,
        value,
        AVG(value) OVER (
            ORDER BY date
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS moving_avg_3
    FROM {table_name}
)
SELECT 
    date,
    value,
    ROUND(moving_avg_3, 2) AS moving_avg_3
FROM value_series
ORDER BY date;
""",
            "seasonality": f"""
-- Analyze potential seasonality by month
SELECT 
    strftime('%m', date) AS month,
    AVG(value) AS avg_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    COUNT(*) AS count
FROM {table_name}
GROUP BY month
ORDER BY month;
""",
            "percentiles": f"""
-- Calculate percentiles for the data
WITH ordered_values AS (
    SELECT 
        value,
        ROW_NUMBER() OVER (ORDER BY value) AS row_num,
        COUNT(*) OVER () AS total_count
    FROM {table_name}
)
SELECT 
    MIN(value) AS min_value,
    MAX(CASE WHEN row_num <= CAST(total_count * 0.25 AS INTEGER) THEN value END) AS p25,
    MAX(CASE WHEN row_num <= CAST(total_count * 0.5 AS INTEGER) THEN value END) AS median,
    MAX(CASE WHEN row_num <= CAST(total_count * 0.75 AS INTEGER) THEN value END) AS p75,
    MAX(value) AS max_value,
    AVG(value) AS mean_value
FROM ordered_values;
""",
            "outliers": f"""
-- Identify potential outliers using Z-score
WITH stats AS (
    SELECT 
        AVG(value) AS mean_value,
        SQRT(AVG(value * value) - AVG(value) * AVG(value)) AS std_dev
    FROM {table_name}
),
z_scores AS (
    SELECT 
        date,
        value,
        (value - stats.mean_value) / CASE WHEN stats.std_dev = 0 THEN 1 ELSE stats.std_dev END AS z_score
    FROM {table_name}, stats
)
SELECT 
    date,
    value,
    ROUND(z_score, 2) AS z_score,
    CASE 
        WHEN ABS(z_score) > 2 THEN 'Potential outlier'
        ELSE 'Normal'
    END AS status
FROM z_scores
WHERE ABS(z_score) > 2
ORDER BY ABS(z_score) DESC;
"""
        }
        
        # Return the requested query or a basic analysis if not found
        return queries.get(query_type.lower(), f"SELECT * FROM {table_name} ORDER BY date;")
    
    @staticmethod
    def generate_sql_analyzer_config(
        data: List[Dict[str, Any]], 
        query_type: str = "trends",
        table_name: str = "statcan_data"
    ) -> Dict[str, Any]:
        """
        Generate configuration for the SQL analyzer MCP server.
        
        Args:
            data: List of data points
            query_type: Type of analysis to perform
            table_name: Name of the SQL table
            
        Returns:
            Configuration for the SQL analyzer MCP server
        """
        # Prepare the data as SQL script
        sql_setup = SQLAnalyzerIntegration.prepare_sql_data(data, table_name)
        
        # Generate the analysis query
        analysis_query = SQLAnalyzerIntegration.generate_analysis_query(query_type, table_name)
        
        # Combine setup and analysis
        full_sql = sql_setup + "\n\n" + analysis_query
        
        # Create the configuration
        config = {
            "sql": full_sql,
            "provider": "sqlite"
        }
        
        return config
    
    @staticmethod
    def get_sql_analysis_command(
        data: List[Dict[str, Any]], 
        query_type: str = "trends",
        table_name: str = "statcan_data"
    ) -> str:
        """
        Generate a command for using the SQL analyzer MCP server.
        
        Args:
            data: List of data points
            query_type: Type of analysis to perform
            table_name: Name of the SQL table
            
        Returns:
            Command string for using the SQL analyzer MCP server
        """
        config = SQLAnalyzerIntegration.generate_sql_analyzer_config(data, query_type, table_name)
        
        # Create a JSON-formatted string (pretty-printed for readability)
        config_json = json.dumps(config, indent=2)
        
        # Generate the command
        command = (
            f"View result from analyze_sql from mcp-sql-analyzer (j4c0bs/mcp-server-sql-analyzer) "
            f"{config_json}"
        )
        
        return command