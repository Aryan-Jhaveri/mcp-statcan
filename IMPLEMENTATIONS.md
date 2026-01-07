# Jan 1 2026
Issues - > 

[] get_bulk_vector gives truncated output, exceeding LLM context. Need to find a better implmentation for LLMs either just read heads of fetched data, or simply always use db tools

[] Create data from table doesnt fill up DB with data, LLM needs to make an additional tool call to manually insert data - causes errors and model runs out of context tokens

[] **Maybe** look into SDMX implementation to allow Claude to create files or exact uris for vector and meta data fetching so a mix of REST and SDMX tools are availbale


[x] Adjust and make more detailed tool prompts to prevent the LLM from making separate calls for finding data and then inputting to database.

[x] Need to add db specific math tools [I am concerned if there is enough relevant math tools available for the database], add additional graph tools if needed.

# Implementations List
List of ideas for future implementations and improvements to the server

## June 3, 2025
[] **Maybe** Look into A2A + MCP (https://arxiv.org/pdf/2506.01804) to create an extended Multi agent system of some sorts?
[] **Maybe** Look into A2A + MCP (https://arxiv.org/pdf/2506.01804) to create an extended Multi agent system of some sorts?

## January 2, 2026 - Refactor Data Retrieval Pipeline

[x] Identify issue with `get_bulk_vector_data_by_range` returning nested JSON incompatible with DB tools.

[x] **Priority** Shift strategy to **Flatten API Response**: Bulk Tool Flattening -> Database Ingestion.
[x] Modify `get_bulk_vector_data_by_range` to return flat list of data points with `vectorId` injected.
[x] Ensure compatibility with `create_table_from_data` for seamless "Fetch -> Store" workflow.
## June 1, 2025
[] add a uv or smithery package installer, to install packages to claude or other LLM clients directly instead of having to adjust working directories

[] Create a setup installation guides for windows.


## Notes 
- Potential use case: Create an scheduled calls for the LLM to create weekly reports for specific data sets.

## Server Architecture & Data Flow
June 1,2025
```mermaid
flowchart TD
    A[Claude/MCP Client] -->|MCP Protocol| B[FastMCP Server]
    
    B --> C{Tool Type}
    C -->|API Tools| D[Statistics Canada API]
    C -->|DB Tools| M[Database Tools]
    C -->|Metadata Tools| F[Code Sets & Classifications]
    
    D --> G[Cube Tools]
    D --> H[Vector Tools]
    D --> I[Metadata Tools]

    E[SQLite Database]
    
    G -->|get_cube_metadata<br/>search_cubes_by_title<br/>get_data_from_cube| J[StatCan WDS API<br/>statcan.gc.ca/t1/wds/rest]
    H -->|get_series_info_from_vector<br/>get_data_from_vectors<br/>get_bulk_vector_data| J
    I -->|get_code_sets<br/>get_changed_cube_list| J
    
    J -->|JSON Response| K[API Response Processing]
    K -->|Structured Data| L{Data Usage}
    L -->|Return to Client| A
    L -->|Store in DB| M[Database Tools]
    
    M --> N[create_table_from_data]
    M --> O[insert_data_into_table] 
    M --> P[query_database]
    M --> Q[list_tables]
    M --> R[get_table_schema]
    
    N --> E
    O --> E
    P --> E
    Q --> E
    R --> E
    
    E --> S[Dynamic Tables]
    
    S -->|SQL Results| T[Formatted Response]
    T -->|MCP Response| A
    
    F -->|get_code_sets| J
    
    style A fill:#210d70
    style B fill:#70190d
    style E fill:#700d49
    style L fill:#450d70
    style T fill:#35700d
    style J fill:#700d1c
    G -->|get_cube_metadata<br/>search_cubes_by_title<br/>get_data_from_cube| J[StatCan WDS API<br/>statcan.gc.ca/t1/wds/rest]
    H -->|get_series_info_from_vector<br/>get_data_from_vectors<br/>get_bulk_vector_data| J
    I -->|get_code_sets<br/>get_changed_cube_list| J
    
    J -->|JSON Response| K[API Response Processing]
    K -->|Flattened Data Points| L{Data Usage}
    
    L -->|Return to Client| A
    L -->|Store in DB| M[Database Tools]
    
    M --> N[create_table_from_data]
    M --> O[insert_data_into_table] 
    M --> P[query_database]
    M --> Q[list_tables]
    M --> R[get_table_schema]


