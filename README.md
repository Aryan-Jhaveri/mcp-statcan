# StatCan Web Data Service MCP Server

An MCP (Model Context Protocol) server that provides access to Statistics Canada's Web Data Service, enabling AI assistants to discover, explore, and analyze Canadian statistical data through natural language.

## Features

- 🔍 **Dataset Discovery**: Search and browse StatCan datasets by keywords, themes, or geography
- 📊 **Data Retrieval**: Extract time series data and specific data points
- 📝 **Metadata Exploration**: Access detailed information about dataset structure and content
- 📈 **Basic Analysis**: Perform simple statistical operations and generate visualizations
- 🔄 **Change Tracking**: Monitor updates to datasets

## Current Status

This is a prototype implementation of an MCP server for StatCan data. We've completed:

- Working StatCan WDS API client with proper error handling and response normalization
- Project structure and architecture design
- Support for basic data retrieval and search functionality

See [CLAUDE.md](CLAUDE.md) for the full development roadmap and plans.

## Dependencies

```bash
pip install sqlitedict aiohttp mcp pydantic python-dotenv
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

# Create logs directory
mkdir -p logs

# Start the MCP server
python -m src
```

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

- "Find datasets about housing prices in Canada"
- "Get the unemployment rate for Ontario over the last 5 years"
- "Show me a chart of Canada's GDP growth since 2010"
- "What's the latest population data for major Canadian cities?"
- "Compare inflation rates across provinces for 2022"