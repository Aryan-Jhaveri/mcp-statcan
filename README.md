# StatCan Web Data Service MCP Server

An MCP (Model Context Protocol) server that provides access to Statistics Canada's Web Data Service, enabling AI assistants to discover, explore, and analyze Canadian statistical data through natural language.

## Features

- 🔍 **Dataset Discovery**: Search and browse StatCan datasets by keywords, themes, or geography
- 📊 **Data Retrieval**: Extract time series data and specific data points
- 📝 **Metadata Exploration**: Access detailed information about dataset structure and content
- 📈 **Basic Analysis**: Perform simple statistical operations and generate visualizations
- 🔄 **Change Tracking**: Monitor updates to datasets

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-statcan.git
cd mcp-statcan

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

## Quick Start

```bash
# Set up environment variables
cp .env.example .env
# Edit .env with your settings

# Start the MCP server
python -m mcp_statcan
```

## Usage with Claude Desktop

1. Open Claude Desktop
2. Go to Settings > MCP Servers
3. Add a new server with the following configuration:
   - Name: StatCan Data
   - Command: `path/to/venv/bin/python -m mcp_statcan`
4. Start chatting with Claude and ask about Canadian statistics!

## Example Queries

- "Find datasets about housing prices in Canada"
- "Get the unemployment rate for Ontario over the last 5 years"
- "Show me a chart of Canada's GDP growth since 2010"
- "What's the latest population data for major Canadian cities?"
- "Compare inflation rates across provinces for 2022"

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .
ruff check --fix .
```

## Project Status

This project is in early development. See the [CLAUDE.md](CLAUDE.md) file for the development roadmap.

## License

MIT

## Acknowledgements

This project uses Statistics Canada's Web Data Service (WDS). All data retrieved is subject to Statistics Canada's [terms of use](https://www.statcan.gc.ca/en/reference/terms-conditions).