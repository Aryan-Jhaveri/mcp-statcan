# StatCan Web Data Service MCP Server

An MCP (Model Context Protocol) server that provides access to Statistics Canada's Web Data Service, enabling AI assistants to discover, explore, analyze, and cite Canadian statistical data through natural language.

## Features

- 🔍 **Dataset Discovery**: Search and browse StatCan datasets by keywords, themes, or geography
- 📊 **Data Retrieval**: Extract time series data with proper formatting for key vectors
- 📝 **Metadata Exploration**: Access detailed information about dataset structure and content
- 💾 **Persistent Storage**: Store datasets for future use with SQLite backend
- 📊 **Advanced Analysis**: Perform comprehensive statistical analysis, trend detection, seasonality analysis, and forecasting
- 📈 **Visualizations**: Generate data visualizations with integration to Vega-Lite
- 📑 **Citations**: Generate properly formatted citations for StatCan data
- 🖼️ **Figure References**: Track and reference figures created from StatCan data
- 🔄 **API Resilience**: Robust error handling with fallbacks for API limitations

## Current Status

This is a robust implementation of an MCP server for StatCan data, with specific enhancements for API reliability:

- ✅ **API Format Requirements**: Identified correct formats for StatCan WDS API endpoints to resolve 406 errors
- ✅ **Enhanced Error Handling**: Multi-tier fallback system when API endpoints fail or timeout
- ✅ **Local Data Caching**: Comprehensive caching system to reduce API dependency
- ✅ **Metadata Enhancement**: Rich context including units, scalar factors, and frequency descriptions 
- ✅ **Advanced Analysis**: Statistical capabilities including trend analysis, seasonality detection, and forecasting
- ✅ **Data Storage**: SQLite backend for persistent storage and offline analysis
- ✅ **MCP Integrations**: Connections to other MCP servers for enhanced functionality
- ✅ **Documentation**: Comprehensive guides for API connection and integration

### API Limitations

The StatCan WDS API has several limitations that this server addresses:

- Some endpoints still return 406 errors despite correct formatting
- Vector-based queries work better than coordinate-based queries
- Some API calls may timeout for large requests
- Rate limits affect high-volume requests

Our implementation uses caching, local fallbacks, and alternative data paths to provide reliable service despite these limitations.

See [docs/implementation_status.md](docs/implementation_status.md) for detailed development progress.

## Dependencies

```bash
pip install sqlitedict aiohttp mcp pydantic python-dotenv pandas numpy
```

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-statcan.git
cd mcp-statcan

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Start the MCP server (cache and logs directories are created automatically)
python -m src
```

The server now features:
- Persistent storage of datasets using SQLite for faster access and offline analysis
- Advanced statistical analysis including trend detection, seasonality analysis, and forecasting
- Proper citation generation for academic and research use
- Automatic creation of cache and log directories in user's home folder
- Fallback to temporary directories if home directory is not writable
- In-memory operation mode when file system access is restricted
- Robust error handling for filesystem operations

## Testing the API Client

To verify the API client works correctly:

```bash
python scripts/test_api.py
```

This will run a series of tests against the StatCan WDS API to retrieve:
- Recent changed cubes
- Metadata for common datasets (CPI, GDP, Labor Force)
- Time series data for key indicators
- Search results for different keywords

## Usage with Claude Desktop

1. Open Claude Desktop
2. Go to Settings > MCP Servers
3. Add a new server with the following configuration:
   - Name: StatCan Data
   - Command: `path/to/venv/bin/python -m src`
4. Start chatting with Claude and ask about Canadian statistics!

## Example Queries

### Basic Data Discovery and Retrieval
- "Find datasets about housing prices in Canada"
- "Get the unemployment rate for Ontario over the last 5 years"
- "Show me Canada's GDP growth since 2010"
- "What's the latest consumer price index data?"

### Advanced Analysis and Storage
- "Get the CPI data, store it in the database, and run a seasonality analysis"
- "Retrieve GDP data and generate a 6-month forecast"
- "Compare employment and unemployment rates to find correlation"
- "Analyze the trend in housing starts over the past 5 years"

### Citations and References
- "Get a citation for Statistics Canada's Labour Force Survey"
- "Create a figure from the CPI data and track it for my report"
- "Generate an APA citation for the GDP dataset"
- "I need to cite the population estimates table in my paper"

The server handles complex analytical requests, maintains persistent storage of datasets, and provides proper citation support for academic and research use cases.