# Implementations List
List of ideas for future implementations and improvements to the server

## June 1, 2025
[] add a uv or smithery package installer, to install packages to claude or other LLM clients directly instead of having to adjust working directories

[] Create a setup installation guides for windows.

[] Adjust and make more detailed tool prompts to prevent the LLM from making separate calls for finding data and then inputting to database.

[] Need to add db specific math tools [I am concerned if there is enough relevant math tools available for the database], add additional graph tools if needed.


## Notes 
- Potential use case: Create an scheduled calls for the LLM to create weekly reports for specific data sets.

## Server Architecture & Data Flow
June 1,2025
```mermaid
flowchart TD
    A[Claude/MCP Client] -->|MCP Protocol| B[FastMCP Server]
    
    B --> C{Tool Type}
    C -->|API Tools| D[Statistics Canada API]
    C -->|DB Tools| E[SQLite Database]
    C -->|Metadata Tools| F[Code Sets & Classifications]
    
    D --> G[Cube Tools]
    D --> H[Vector Tools]
    D --> I[Metadata Tools]
    
    G -->|get_cube_metadata<br/>search_cubes_by_title<br/>get_data_from_cube| J[StatCan WDS API<br/>statcan.gc.ca/t1/wds/rest]
    H -->|get_series_info_from_vector<br/>get_data_from_vectors<br/>get_bulk_vector_data| J
    I -->|get_code_sets<br/>get_changed_cube_list| J
    
    J -->|JSON Response| K[API Response Processing]
    K -->|Structured Data| L[Data Transformation]
    
    L --> M{Storage Decision}
    M -->|Store Data| N[create_table_from_data]
    M -->|Query Data| O[insert_data_into_table]
    M -->|Analyze Data| P[query_database]
    
    N --> E
    O --> E
    P --> E
    
    E --> Q[Dynamic Tables]
    E --> R[Metadata Cache]
    
    Q -->|SQL Results| S[Formatted Response]
    R -->|Cached Metadata| S
    
    S -->|MCP Response| A
    
    F --> T[Local Code Sets<br/>- frequency_codes.json<br/>- uom_codes.json<br/>- subject_codes.json<br/>- etc.]
    T -->|Reference Data| S
    
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style E fill:#fff3e0
    style J fill:#e8f5e8
    style Q fill:#fff8e1
    style R fill:#fce4ec
```


