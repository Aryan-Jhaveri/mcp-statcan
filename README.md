# StatCan Web Data Service MCP Server

An MCP (Model Context Protocol) server that provides access to Statistics Canada's Web Data Service, enabling AI assistants to discover, explore, analyze, and cite Canadian statistical data through natural language.

## Features

- 🔍 **Dataset Discovery**: Search and browse StatCan datasets by keywords, themes, or geography
- 📊 **Data Retrieval**: Extract time series data and specific data points
- 📝 **Metadata Exploration**: Access detailed information about dataset structure and content
- 💾 **Persistent Storage**: Store datasets for future use with SQLite backend
- 📊 **Advanced Analysis**: Perform comprehensive statistical analysis, trend detection, seasonality analysis, and forecasting
- 📈 **Visualizations**: Generate data visualizations with integration to Vega-Lite
- 🔄 **Change Tracking**: Monitor updates to datasets
- 📑 **Citations**: Generate properly formatted citations for StatCan data
- 🖼️ **Figure References**: Track and reference figures created from StatCan data

## Current Status

This is a full-featured implementation of an MCP server for StatCan data. We've completed:

- Enhanced StatCan WDS API client with robust error handling and intelligent search
- Comprehensive data retrieval with statistical analysis and trend detection
- Persistent data storage with SQLite for offline analysis and faster access
- Advanced statistical capabilities including trend analysis, seasonality detection, and forecasting
- Proper citation generation in multiple formats (APA, MLA, Chicago)
- Figure tracking for maintaining references to generated visualizations
- Rich resource formatting with markdown and improved context
- Advanced search capabilities with tokenization and synonym handling
- Multi-level caching system with fallbacks for restricted environments
- Extensive testing framework for verification and validation

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