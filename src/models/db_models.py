from pydantic import BaseModel, Field
from typing import List, Dict, Any

class TableDataInput(BaseModel):
    table_name: str = Field(..., description="Name for the SQL table (alphanumeric and underscores recommended).")
    data: List[Dict[str, Any]] = Field(..., description="Data to insert, as a list of dictionaries.")

class TableNameInput(BaseModel):
    table_name: str = Field(..., description="Name of the SQL table.")

class QueryInput(BaseModel):
    sql_query: str = Field(..., description="The SQL query to execute.")
