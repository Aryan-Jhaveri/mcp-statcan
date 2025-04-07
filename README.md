 # StatCan Web Data Service MCP Server

<div align="center">
  <img src="./assets/StatCan-Header.png" alt="Statistics Canada Logo" width="600"/>
</div>

A MCP (Model Context Protocol) server that provides access to Statistics Canada's Web Data Service, enabling AI assistants to discover, explore, analyze, and cite Canadian statistical data through natural language.

## Project Overview

This server addresses several technical challenges in accessing Statistics Canada's Web Data Service (WDS) API:

1. **API Format Requirements**: Identified correct formats for StatCan WDS API endpoints to resolve 406 errors
2. **Resilient Data Access**: Implements multi-tier caching and fallbacks for API limitations
3. **Enhanced Metadata**: Provides rich context for statistical interpretation and proper citation
4. **Analysis Capabilities**: Includes statistical analysis, visualization, and forecasting features
5. **MCP Integration**: Connects with other MCP servers for expanded functionality

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

## Current Limitations

The StatCan WDS API has several limitations that this server addresses:

- **Data Retrieval Constraints**: Some API endpoints remain problematic despite correct formatting
- **Format Sensitivity**: Vector IDs must be numeric without the 'v' prefix, and payloads must be in array format
- **Coordinate Access**: Vector-based queries are more reliable than coordinate-based queries
- **Performance Issues**: Some API calls may timeout for large requests or during peak times
- **Rate Limiting**: High-volume queries may be throttled by the StatCan WDS API

The current implementation uses these strategies to work around these limitations:
- Multi-tier caching system at metadata, vector, and cube levels
- Local fallbacks for common statistical indicators
- Automatic format adjustment and retries with exponential backoff
- Graceful degradation to cached data when API endpoints fail

See [docs/implementation_status.md](docs/implementation_status.md) and [docs/api_connection_guide.md](docs/api_connection_guide.md) for details.

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

# Start the MCP server
python -m src
```

### Dependencies

```bash
pip install sqlitedict aiohttp mcp pydantic python-dotenv pandas numpy
```

## Usage with Claude

1. Open Claude Desktop App
2. Go to Settings > MCP Servers
3. Add a new server with the following configuration:
   - Name: StatCan Data
   - Command: `path/to/venv/bin/python -m src`
4. Start chatting with Claude and ask about Canadian statistics!

## Working Example Queries

Here are queries that work reliably with the current implementation:

### Basic Data Discovery
- "Find datasets about consumer prices in Canada"
- "What datasets do you have about employment?"
- "Show me the latest CPI data"

### Vector-Based Data Retrieval
- "Get data for CPI vector 41690973"
- "Retrieve GDP data from vector 21581063"
- "Get the latest values for employment vector 111955426"

### Analysis and Visualization
- "Generate a line chart for CPI data over the last 5 years"
- "Analyze the trend in GDP for the past 10 quarters"
- "Create a visualization of unemployment rate changes"

### Citations
- "Generate a citation for the Consumer Price Index dataset"
- "How should I cite Statistics Canada's GDP data in APA format?"
- "Create a reference for the Labour Force Survey"

## Testing

To verify the API client works correctly:

```bash
python -m tests.api.api_connection_steps
```

This runs step-by-step tests for:
- API connectivity
- Metadata retrieval
- Vector data access
- Format requirements

## Project Structure

- `/src` - Core server implementation
- `/docs` - Documentation and guides
- `/tests` - Test suite for API and functionality
- `/docs/references` - API specifications and code sets

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

This project uses data from [Statistics Canada](https://www.statcan.gc.ca/), accessed via their [Web Data Service API](https://www.statcan.gc.ca/en/developers/wds/user-guide). It is not affiliated with or endorsed by Statistics Canada.

The Statistics Canada logo is used for informational purposes only to indicate the data source.
