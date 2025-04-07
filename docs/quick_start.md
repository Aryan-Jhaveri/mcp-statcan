# StatCan MCP Server Quick Start Guide

This guide will help you quickly set up and start using the StatCan MCP server with Claude Desktop.

## Installation

### Prerequisites

- Python 3.9 or later
- Claude Desktop app
- Git (optional)

### Step 1: Get the Code

Clone the repository or download it:

```bash
git clone https://github.com/yourusername/mcp-statcan.git
cd mcp-statcan
```

### Step 2: Set Up the Environment

Create and activate a virtual environment:

```bash
# Create a virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

Install the package and dependencies:

```bash
pip install -e .
```

### Step 3: Configure the Server

The default configuration should work for most users. If you want to customize the server:

1. Create a `.env` file in the project root
2. Add configuration values like:

```
# Server configuration
MCP_SERVER_NAME=My StatCan Server
MCP_SERVER_PORT=5001

# Logging
LOG_LEVEL=DEBUG
```

All configuration is optional with sensible defaults.

### Step 4: Start the Server Manually (Optional)

You can run the server manually to test it:

```bash
python -m src
```

The server should start and wait for connections.

### Step 5: Configure Claude Desktop

1. Open Claude Desktop
2. Click on the settings icon (⚙️) in the bottom left
3. Go to the "MCP Servers" section
4. Click "Add Server"
5. Fill in the details:
   - Name: StatCan Data
   - Command: `/path/to/venv/bin/python -m src`
   - Replace `/path/to/venv` with the actual path to your virtual environment
6. Click "Add"
7. Make sure the server is enabled (toggle switch is on)
8. Close the settings

## Using the Server

Now you can chat with Claude and access StatCan data. Try these example queries:

- "Find datasets about housing prices in Canada"
- "Show me information about Canada's population growth"
- "Get data on unemployment rates"
- "What's the latest inflation rate in Canada?"

## Available Tools

The StatCan MCP server provides the following tools:

### Data Discovery and Metadata
- **search_datasets**: Search for datasets by keywords or themes
- **get_dataset_metadata**: Retrieve detailed metadata for a dataset
- **get_recently_updated_datasets**: Find recently updated datasets

### Data Retrieval
- **get_data_series**: Extract time series data for specific vectors
- **get_data_series_by_range**: Get data for a specific date range
- **get_series_from_cube**: Get data from a cube using coordinates
- **get_download_link**: Generate a download link for full datasets

### Data Storage and Analysis
- **store_dataset**: Store a dataset in the persistent database
- **retrieve_dataset**: Retrieve a dataset from storage
- **analyze_dataset**: Run analysis on stored data
- **compare_datasets**: Compare two datasets
- **forecast_dataset**: Generate forecasts
- **list_stored_datasets**: List all stored datasets

### Integration Tools
- **get_dataset_visualization**: Generate visualizations
- **analyze_dataset**: Perform advanced analysis
- **deep_research_dataset**: Get contextual research
- **explore_dataset**: Get data exploration options

## Troubleshooting

If you encounter issues:

1. Check the logs at `./logs/mcp-statcan.log`
2. Ensure your Python version is 3.9 or later
3. Verify that Claude Desktop is properly configured
4. Make sure the server is running when you try to use it

## Next Steps

- Explore more complex queries
- Try combining multiple datasets
- Check out the full documentation for advanced usage