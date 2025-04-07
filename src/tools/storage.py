"""
MCP tools for StatCan data storage and analysis.

NOTE: This file is kept for reference but is no longer actively used.
The functionality has been migrated to function-based tools directly in the server.py file.

The tools have been refactored to use the modern MCP API with function decorators
instead of class-based tools, which ensures compatibility with the latest
MCP SDK version.

See the implementation in src/server.py in the _register_tools method:
- store_dataset
- retrieve_dataset
- analyze_dataset
- compare_datasets
- forecast_dataset
- list_stored_datasets

The storage functionality itself is implemented in src/integrations/data_storage.py.
"""

import logging
import json
from typing import Dict, Any, List, Optional
import asyncio

# Import class references were replaced with function decorators in server.py

from src.integrations.data_storage import DataStorageIntegration

logger = logging.getLogger(__name__)

class StoreDatasetConfig(BaseModel):
    """Configuration for the store_dataset tool."""
    
    series_id: str = Field(..., description="Unique identifier for the series (vector ID or custom ID)")
    data: List[Dict[str, Any]] = Field(..., description="List of data points with date and value")
    metadata: Dict[str, Any] = Field(..., description="Metadata for the series")

class StoreDatasetTool(BaseTool[StoreDatasetConfig]):
    """Tool for storing a dataset in the persistent database."""
    
    name = "store_dataset"
    description = "Store a dataset in the persistent database for future use"
    config_model = StoreDatasetConfig
    
    async def execute(self, config: StoreDatasetConfig) -> RenderableResponse:
        """Execute the store_dataset tool."""
        storage = DataStorageIntegration()
        
        try:
            result = storage.store_time_series(
                series_id=config.series_id,
                data=config.data,
                metadata=config.metadata
            )
            
            if result:
                return RenderableResponse(
                    content=f"Successfully stored dataset '{config.series_id}' with {len(config.data)} data points.",
                    media_type="text/plain"
                )
            else:
                return RenderableResponse(
                    content=f"Failed to store dataset '{config.series_id}'.",
                    media_type="text/plain"
                )
        except Exception as e:
            logger.error(f"Error in store_dataset tool: {e}")
            return RenderableResponse(
                content=f"Error storing dataset: {str(e)}",
                media_type="text/plain"
            )
        finally:
            storage.close()


class RetrieveDatasetConfig(BaseModel):
    """Configuration for the retrieve_dataset tool."""
    
    series_id: str = Field(..., description="Unique identifier for the series")

class RetrieveDatasetTool(BaseTool[RetrieveDatasetConfig]):
    """Tool for retrieving a dataset from the persistent database."""
    
    name = "retrieve_dataset"
    description = "Retrieve a dataset from the persistent database"
    config_model = RetrieveDatasetConfig
    
    async def execute(self, config: RetrieveDatasetConfig) -> RenderableResponse:
        """Execute the retrieve_dataset tool."""
        storage = DataStorageIntegration()
        
        try:
            data, metadata = storage.retrieve_time_series(config.series_id)
            
            if not data:
                return RenderableResponse(
                    content=f"Dataset '{config.series_id}' not found in the database.",
                    media_type="text/plain"
                )
            
            result = {
                "metadata": metadata,
                "data": data[:10],  # Only return the first 10 data points to avoid overwhelming the response
                "total_points": len(data)
            }
            
            return RenderableResponse(
                content=json.dumps(result, indent=2),
                media_type="application/json"
            )
        except Exception as e:
            logger.error(f"Error in retrieve_dataset tool: {e}")
            return RenderableResponse(
                content=f"Error retrieving dataset: {str(e)}",
                media_type="text/plain"
            )
        finally:
            storage.close()


class AnalyzeDatasetConfig(BaseModel):
    """Configuration for the analyze_dataset tool."""
    
    series_id: str = Field(..., description="Unique identifier for the series")
    analysis_type: str = Field("summary", description="Type of analysis to perform (summary, trends, seasonal, forecast, correlation)")
    params: Optional[Dict[str, Any]] = Field(None, description="Additional parameters for the analysis")

class AnalyzeDatasetTool(BaseTool[AnalyzeDatasetConfig]):
    """Tool for analyzing a dataset from the persistent database."""
    
    name = "analyze_dataset"
    description = "Analyze a dataset from the persistent database"
    config_model = AnalyzeDatasetConfig
    
    async def execute(self, config: AnalyzeDatasetConfig) -> RenderableResponse:
        """Execute the analyze_dataset tool."""
        storage = DataStorageIntegration()
        
        try:
            params = config.params or {}
            
            # Run the analysis
            result = storage.run_analysis(
                series_id=config.series_id,
                analysis_type=config.analysis_type,
                params=params
            )
            
            if "error" in result:
                return RenderableResponse(
                    content=f"Analysis error: {result['error']}",
                    media_type="text/plain"
                )
            
            return RenderableResponse(
                content=json.dumps(result, indent=2),
                media_type="application/json"
            )
        except Exception as e:
            logger.error(f"Error in analyze_dataset tool: {e}")
            return RenderableResponse(
                content=f"Error analyzing dataset: {str(e)}",
                media_type="text/plain"
            )
        finally:
            storage.close()


class CompareDatasetConfig(BaseModel):
    """Configuration for the compare_datasets tool."""
    
    primary_series_id: str = Field(..., description="Unique identifier for the primary series")
    secondary_series_id: str = Field(..., description="Unique identifier for the secondary series")
    comparison_type: str = Field("correlation", description="Type of comparison to perform (correlation, difference, ratio)")
    
class CompareDatasetsTool(BaseTool[CompareDatasetConfig]):
    """Tool for comparing two datasets from the persistent database."""
    
    name = "compare_datasets"
    description = "Compare two datasets from the persistent database"
    config_model = CompareDatasetConfig
    
    async def execute(self, config: CompareDatasetConfig) -> RenderableResponse:
        """Execute the compare_datasets tool."""
        storage = DataStorageIntegration()
        
        try:
            # For correlation analysis, we can use the existing correlation function
            if config.comparison_type == "correlation":
                result = storage.run_analysis(
                    series_id=config.primary_series_id,
                    analysis_type="correlation",
                    params={"compare_with": config.secondary_series_id}
                )
                
                if "error" in result:
                    return RenderableResponse(
                        content=f"Comparison error: {result['error']}",
                        media_type="text/plain"
                    )
                
                return RenderableResponse(
                    content=json.dumps(result, indent=2),
                    media_type="application/json"
                )
            else:
                # For other comparison types, we would need to implement custom logic
                return RenderableResponse(
                    content=f"Comparison type '{config.comparison_type}' not yet implemented.",
                    media_type="text/plain"
                )
        except Exception as e:
            logger.error(f"Error in compare_datasets tool: {e}")
            return RenderableResponse(
                content=f"Error comparing datasets: {str(e)}",
                media_type="text/plain"
            )
        finally:
            storage.close()


class ForecastDatasetConfig(BaseModel):
    """Configuration for the forecast_dataset tool."""
    
    series_id: str = Field(..., description="Unique identifier for the series")
    periods: int = Field(6, description="Number of periods to forecast")
    method: str = Field("exponential_smoothing", description="Forecasting method (exponential_smoothing, naive)")
    params: Optional[Dict[str, Any]] = Field(None, description="Additional parameters for the forecast")

class ForecastDatasetTool(BaseTool[ForecastDatasetConfig]):
    """Tool for forecasting a dataset from the persistent database."""
    
    name = "forecast_dataset"
    description = "Generate a forecast for a dataset from the persistent database"
    config_model = ForecastDatasetConfig
    
    async def execute(self, config: ForecastDatasetConfig) -> RenderableResponse:
        """Execute the forecast_dataset tool."""
        storage = DataStorageIntegration()
        
        try:
            params = config.params or {}
            params["periods"] = config.periods
            
            # Run the forecast analysis
            result = storage.run_analysis(
                series_id=config.series_id,
                analysis_type="forecast",
                params=params
            )
            
            if "error" in result:
                return RenderableResponse(
                    content=f"Forecast error: {result['error']}",
                    media_type="text/plain"
                )
            
            return RenderableResponse(
                content=json.dumps(result, indent=2),
                media_type="application/json"
            )
        except Exception as e:
            logger.error(f"Error in forecast_dataset tool: {e}")
            return RenderableResponse(
                content=f"Error forecasting dataset: {str(e)}",
                media_type="text/plain"
            )
        finally:
            storage.close()


class ListStoredDatasetsConfig(BaseModel):
    """Configuration for the list_stored_datasets tool."""
    pass

class ListStoredDatasetsTool(BaseTool[ListStoredDatasetsConfig]):
    """Tool for listing all stored datasets in the database."""
    
    name = "list_stored_datasets"
    description = "List all datasets stored in the persistent database"
    config_model = ListStoredDatasetsConfig
    
    async def execute(self, config: ListStoredDatasetsConfig) -> RenderableResponse:
        """Execute the list_stored_datasets tool."""
        storage = DataStorageIntegration()
        
        try:
            conn = storage.connect()
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT id, title, start_date, end_date, last_updated 
            FROM time_series
            ORDER BY last_updated DESC
            """)
            
            datasets = []
            for row in cursor.fetchall():
                series_id, title, start_date, end_date, last_updated = row
                
                # Get count of data points
                cursor.execute("SELECT COUNT(*) FROM data_points WHERE series_id = ?", (series_id,))
                count = cursor.fetchone()[0]
                
                datasets.append({
                    "id": series_id,
                    "title": title,
                    "start_date": start_date,
                    "end_date": end_date,
                    "last_updated": last_updated,
                    "data_points": count
                })
            
            if not datasets:
                return RenderableResponse(
                    content="No datasets found in the database.",
                    media_type="text/plain"
                )
            
            return RenderableResponse(
                content=json.dumps({"datasets": datasets}, indent=2),
                media_type="application/json"
            )
        except Exception as e:
            logger.error(f"Error in list_stored_datasets tool: {e}")
            return RenderableResponse(
                content=f"Error listing datasets: {str(e)}",
                media_type="text/plain"
            )
        finally:
            storage.close()