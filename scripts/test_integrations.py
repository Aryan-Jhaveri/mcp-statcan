#!/usr/bin/env python3
"""
Script to test the MCP server integrations.

This script tests the integration with other MCP servers.

Run with: python scripts/test_integrations.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.server import statcan_server
from src.integrations.data_exploration import DataExplorationIntegration
from src.integrations.sql_analyzer import SQLAnalyzerIntegration
from src.integrations.deep_research import DeepResearchIntegration
from src.integrations.vectorize import VectorizeIntegration
from src.integrations.integrations import MCPIntegrations

# Configure logging to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
    ]
)

logger = logging.getLogger(__name__)

# Sample data for testing
SAMPLE_DATA = [
    {"date": "2023-01-01", "value": "100.0"},
    {"date": "2023-02-01", "value": "102.5"},
    {"date": "2023-03-01", "value": "103.8"},
    {"date": "2023-04-01", "value": "101.2"},
    {"date": "2023-05-01", "value": "105.7"}
]

SAMPLE_DATASET_INFO = {
    "pid": "1810000401",
    "title": "Consumer Price Index",
    "description": "The Consumer Price Index (CPI) is an indicator of changes in consumer prices.",
    "time_range": "2018-01-01 to 2023-05-01",
    "frequency": "Monthly",
    "dimensions": ["Geography", "Products and product groups"]
}

async def test_data_exploration_integration():
    """Test the data exploration integration."""
    print("\n=== Testing Data Exploration Integration ===")
    
    # Test CSV data preparation
    print("\nTesting CSV data preparation...")
    csv_data = DataExplorationIntegration.prepare_csv_data(SAMPLE_DATA, "CPI")
    if "date,value" in csv_data and "2023-01-01" in csv_data:
        print("✅ CSV data preparation successful")
        print(f"Preview: {csv_data[:100]}...")
    else:
        print("❌ CSV data preparation failed")
    
    # Test prompt generation
    print("\nTesting prompt generation...")
    prompt = DataExplorationIntegration.get_data_exploration_prompt("csv", "CPI", "trends")
    if "Analyze this csv dataset" in prompt and "focusing specifically on trends" in prompt:
        print("✅ Prompt generation successful")
        print(f"Preview: {prompt[:100]}...")
    else:
        print("❌ Prompt generation failed")
    
    # Test exploration command generation
    print("\nTesting exploration command generation...")
    command = DataExplorationIntegration.get_exploration_command(SAMPLE_DATA, "CPI", "trends")
    if "View result from explore_data from mcp-data-exploration" in command:
        print("✅ Exploration command generation successful")
        print(f"Preview: {command[:100]}...")
    else:
        print("❌ Exploration command generation failed")

async def test_sql_analyzer_integration():
    """Test the SQL analyzer integration."""
    print("\n=== Testing SQL Analyzer Integration ===")
    
    # Test SQL data preparation
    print("\nTesting SQL data preparation...")
    sql_script = SQLAnalyzerIntegration.prepare_sql_data(SAMPLE_DATA, "cpi_data")
    if "CREATE TABLE cpi_data" in sql_script and "INSERT INTO cpi_data" in sql_script:
        print("✅ SQL data preparation successful")
        print(f"Preview: {sql_script[:100]}...")
    else:
        print("❌ SQL data preparation failed")
    
    # Test analysis query generation
    print("\nTesting analysis query generation...")
    query = SQLAnalyzerIntegration.generate_analysis_query("trends", "cpi_data")
    if "Analyze trends" in query and "GROUP BY year" in query:
        print("✅ Analysis query generation successful")
        print(f"Preview: {query[:100]}...")
    else:
        print("❌ Analysis query generation failed")
    
    # Test SQL analysis command generation
    print("\nTesting SQL analysis command generation...")
    command = SQLAnalyzerIntegration.get_sql_analysis_command(SAMPLE_DATA, "trends", "cpi_data")
    if "View result from analyze_sql from mcp-sql-analyzer" in command:
        print("✅ SQL analysis command generation successful")
        print(f"Preview: {command[:100]}...")
    else:
        print("❌ SQL analysis command generation failed")

async def test_deep_research_integration():
    """Test the deep research integration."""
    print("\n=== Testing Deep Research Integration ===")
    
    # Test dataset context formatting
    print("\nTesting dataset context formatting...")
    context = DeepResearchIntegration.format_dataset_context(
        SAMPLE_DATASET_INFO["title"],
        SAMPLE_DATASET_INFO["description"],
        SAMPLE_DATASET_INFO["time_range"],
        SAMPLE_DATASET_INFO["dimensions"]
    )
    if "# Consumer Price Index" in context and "## Description" in context:
        print("✅ Dataset context formatting successful")
        print(f"Preview: {context[:100]}...")
    else:
        print("❌ Dataset context formatting failed")
    
    # Test research questions generation
    print("\nTesting research questions generation...")
    questions = DeepResearchIntegration.generate_research_questions(
        SAMPLE_DATASET_INFO["title"],
        "inflation"
    )
    if len(questions) > 0 and "inflation" in questions[0]:
        print("✅ Research questions generation successful")
        print(f"Example question: {questions[0]}")
    else:
        print("❌ Research questions generation failed")
    
    # Test deep research command generation
    print("\nTesting deep research command generation...")
    command = DeepResearchIntegration.get_deep_research_command(
        SAMPLE_DATASET_INFO,
        SAMPLE_DATA,
        "inflation"
    )
    if "View result from research from mcp-deep-research" in command:
        print("✅ Deep research command generation successful")
        print(f"Preview: {command[:100]}...")
    else:
        print("❌ Deep research command generation failed")

async def test_vectorize_integration():
    """Test the vectorize integration."""
    print("\n=== Testing Vectorize Integration ===")
    
    # Test dataset formatting for indexing
    print("\nTesting dataset formatting for indexing...")
    document = VectorizeIntegration.format_dataset_for_indexing(
        SAMPLE_DATASET_INFO["pid"],
        SAMPLE_DATASET_INFO["title"],
        SAMPLE_DATASET_INFO["description"],
        SAMPLE_DATASET_INFO["time_range"],
        SAMPLE_DATASET_INFO["frequency"],
        SAMPLE_DATASET_INFO["dimensions"]
    )
    if "id" in document and "text" in document and "metadata" in document:
        print("✅ Dataset formatting for indexing successful")
        print(f"Document ID: {document['id']}")
        print(f"Text preview: {document['text'][:100]}...")
    else:
        print("❌ Dataset formatting for indexing failed")
    
    # Test search configuration generation
    print("\nTesting search configuration generation...")
    config = VectorizeIntegration.generate_search_config("inflation", {"frequency": "Monthly"})
    if "index_name" in config and "query" in config and "filter" in config:
        print("✅ Search configuration generation successful")
        print(f"Query: {config['query']}")
    else:
        print("❌ Search configuration generation failed")
    
    # Test index command generation
    print("\nTesting index command generation...")
    command = VectorizeIntegration.get_index_datasets_command([SAMPLE_DATASET_INFO])
    if "View result from create_or_update_index from vectorize" in command:
        print("✅ Index command generation successful")
        print(f"Preview: {command[:100]}...")
    else:
        print("❌ Index command generation failed")
    
    # Test search command generation
    print("\nTesting search command generation...")
    command = VectorizeIntegration.get_search_datasets_command("inflation", {"frequency": "Monthly"})
    if "View result from search from vectorize" in command:
        print("✅ Search command generation successful")
        print(f"Preview: {command[:100]}...")
    else:
        print("❌ Search command generation failed")

async def test_mcp_integrations():
    """Test the main MCP integrations class."""
    print("\n=== Testing Main MCP Integrations ===")
    
    # Test visualization suggestions generation
    print("\nTesting visualization suggestions generation...")
    suggestions = MCPIntegrations.generate_visualization_suggestions(
        SAMPLE_DATASET_INFO,
        SAMPLE_DATA
    )
    if "line_chart" in suggestions and "data_exploration" in suggestions:
        print("✅ Visualization suggestions generation successful")
        print(f"Suggestion types: {', '.join(suggestions.keys())}")
    else:
        print("❌ Visualization suggestions generation failed")
    
    # Test analysis suggestions generation
    print("\nTesting analysis suggestions generation...")
    suggestions = MCPIntegrations.generate_analysis_suggestions(
        SAMPLE_DATASET_INFO,
        SAMPLE_DATA
    )
    if "trends" in suggestions and "growth_rates" in suggestions:
        print("✅ Analysis suggestions generation successful")
        print(f"Suggestion types: {', '.join(suggestions.keys())}")
    else:
        print("❌ Analysis suggestions generation failed")
    
    # Test dataset summary formatting
    print("\nTesting dataset summary formatting...")
    summary = MCPIntegrations.format_dataset_summary(
        SAMPLE_DATASET_INFO,
        SAMPLE_DATA,
        include_integrations=True
    )
    if "# Consumer Price Index" in summary and "## Available Integrations" in summary:
        print("✅ Dataset summary formatting successful")
        print(f"Preview: {summary[:100]}...")
    else:
        print("❌ Dataset summary formatting failed")

async def test_server_integration_tools():
    """Test the server integration tools through the integrations module."""
    print("\n=== Testing Server Integration Tools ===")
    
    # Create a dataset info object for testing
    dataset_info = {
        "pid": "1810000401",  # CPI dataset
        "title": "Consumer Price Index",
        "description": "The Consumer Price Index (CPI) is an indicator of changes in consumer prices.",
        "time_range": "2018-01-01 to 2023-05-01",
        "frequency": "Monthly",
        "dimensions": ["Geography", "Products and product groups"]
    }
    
    # Create sample data points
    data_points = SAMPLE_DATA
    
    # Test dataset visualization integration
    print("\nTesting dataset visualization integration...")
    try:
        # Directly use the integration class
        viz_suggestions = statcan_server.integrations.generate_visualization_suggestions(
            dataset_info, data_points
        )
        
        if "line_chart" in viz_suggestions and "```" in viz_suggestions["line_chart"]:
            print("✅ Dataset visualization integration successful")
            print(f"Command preview: {viz_suggestions['line_chart'][:100]}...")
        else:
            print("❌ Dataset visualization integration failed")
    except Exception as e:
        print(f"❌ Error testing dataset visualization integration: {e}")
    
    # Test dataset analysis integration
    print("\nTesting dataset analysis integration...")
    try:
        # Directly use the integration class
        analysis_suggestions = statcan_server.integrations.generate_analysis_suggestions(
            dataset_info, data_points
        )
        
        if "trends" in analysis_suggestions and "sql" in analysis_suggestions["trends"]:
            print("✅ Dataset analysis integration successful")
            print(f"Available analysis types: {', '.join(analysis_suggestions.keys())}")
        else:
            print("❌ Dataset analysis integration failed")
    except Exception as e:
        print(f"❌ Error testing dataset analysis integration: {e}")
    
    # Test deep research integration
    print("\nTesting deep research integration...")
    try:
        # Directly use the deep research integration
        from src.integrations.deep_research import DeepResearchIntegration
        result = DeepResearchIntegration.get_deep_research_command(
            dataset_info, data_points, "inflation"
        )
        
        if "research from mcp-deep-research" in result:
            print("✅ Deep research integration successful")
            print(f"Command preview: {result[:100]}...")
        else:
            print("❌ Deep research integration failed")
    except Exception as e:
        print(f"❌ Error testing deep research integration: {e}")
    
    # Test dataset summary formatting
    print("\nTesting dataset summary formatting...")
    try:
        # Directly use the integration class
        summary = statcan_server.integrations.format_dataset_summary(
            dataset_info, data_points, include_integrations=True
        )
        
        if "# Consumer Price Index" in summary and "## Available Integrations" in summary:
            print("✅ Dataset summary formatting successful")
            print(f"Summary preview: {summary[:100]}...")
        else:
            print("❌ Dataset summary formatting failed")
    except Exception as e:
        print(f"❌ Error testing dataset summary formatting: {e}")

async def main():
    """Run all tests."""
    print("Starting MCP server integrations tests...")
    
    try:
        # Test individual integrations
        await test_data_exploration_integration()
        await test_sql_analyzer_integration()
        await test_deep_research_integration()
        await test_vectorize_integration()
        
        # Test main integrations class
        await test_mcp_integrations()
        
        # Test server integration tools
        await test_server_integration_tools()
        
        print("\n✅ All integration tests completed!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ Error during testing: {e}")
        return 1
    finally:
        # Clean up WDS client connections
        await statcan_server.wds_client.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))