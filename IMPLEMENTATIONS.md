# Implementations List
List of ideas for future implementations and improvements to the server

## Database Architecture

```mermaid
erDiagram
    STATCAN_API ||--o{ API_CALLS : fetches
    API_CALLS ||--o{ DYNAMIC_TABLES : creates
    
    STATCAN_API {
        string base_url "https://www150.statcan.gc.ca/t1/wds/rest"
        string endpoints "various_api_endpoints"
        json response_format "JSON"
    }
    
    API_CALLS {
        string endpoint_type "cube/vector/metadata"
        datetime timestamp "request_time"
        json parameters "query_params"
        json response_data "api_response"
    }
    
    DYNAMIC_TABLES {
        string table_name "user_defined"
        datetime created_at "table_creation"
        json schema_info "column_definitions"
        int row_count "data_rows"
    }
    
    SQLITE_DB ||--o{ DYNAMIC_TABLES : contains
    SQLITE_DB ||--o{ METADATA_CACHE : stores
    
    SQLITE_DB {
        string file_path "temp_statcan_data.db"
        string connection_type "sqlite3"
        boolean row_factory "sqlite3.Row"
    }
    
    METADATA_CACHE {
        string vector_id "PK"
        string cube_id "product_id"
        json metadata "series_info"
        datetime last_updated "cache_timestamp"
        string status "active/expired"
    }
    
    MCP_TOOLS ||--|| SQLITE_DB : manages
    MCP_TOOLS {
        string create_table_from_data "schema_creation"
        string insert_data_into_table "data_insertion"
        string query_database "sql_execution"
        string list_tables "table_discovery"
        string get_table_schema "schema_inspection"
    }
    
    CLIENT_REQUESTS ||--o{ MCP_TOOLS : uses
    CLIENT_REQUESTS {
        string tool_name "mcp_function"
        json parameters "function_args"
        json response "function_result"
        string status "success/error"
    }
```

## June 1, 2025
[] add a uv or smithery package installer, to install packages to claude or other LLM clients directly instead of having to adjust working directories

[] Create a setup installation guides for windows.

[] Adjust and make more detailed tool prompts to prevent the LLM from making separate calls for finding data and then inputting to database.

[] Need to add db specific math tools [I am concerned if there is enough relevant math tools available for the database], add additional graph tools if needed.


## Notes 
- Potential use case: Create an scheduled calls for the LLM to create weekly reports for specific data sets.
