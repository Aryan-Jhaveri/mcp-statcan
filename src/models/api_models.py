from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

DEFAULT_TRUNCATION_LIMIT = 50


class ProductIdInput(BaseModel):
    productId: int

class CubeMetadataInput(BaseModel):
    productId: int
    summary: bool = Field(True, description="When True (default), returns a compact summary: essential cube metadata, dimension names, 3 sample members per dimension, and _next_steps guidance. Set to False only when you need the full raw member list or all API fields.")

class VectorIdInput(BaseModel):
    vectorId: int

class CubeCoordInput(BaseModel):
    productId: int
    coordinate: str = Field(..., description="Coordinate string (e.g., '1.1'). Padding to 10 dimensions is handled automatically.")

class CubeCoordLatestNInput(BaseModel):
    productId: int
    coordinate: str = Field(..., description="Coordinate string (e.g., '1.1'). Padding to 10 dimensions is handled automatically.")
    latestN: int

class VectorLatestNInput(BaseModel):
    vectorId: int
    latestN: int

class VectorRangeInput(BaseModel):
    vectorIds: List[str] # API uses strings for vector IDs here
    startRefPeriod: Optional[str] = None # YYYY-MM-DD
    endReferencePeriod: Optional[str] = None # YYYY-MM-DD
    offset: Optional[int] = Field(0, description="Number of rows to skip (for pagination). Default 0.")
    limit: Optional[int] = Field(None, description=f"Max rows to return. Default {DEFAULT_TRUNCATION_LIMIT}. Set higher to get more rows.")

class BulkVectorRangeInput(BaseModel):
    vectorIds: List[str] # API uses strings for vector IDs here
    startDataPointReleaseDate: Optional[str] = None # YYYY-MM-DDTHH:MM
    endDataPointReleaseDate: Optional[str] = None # YYYY-MM-DDTHH:MM
    offset: Optional[int] = Field(0, description="Number of rows to skip (for pagination). Default 0.")
    limit: Optional[int] = Field(None, description=f"Max rows to return. Default {DEFAULT_TRUNCATION_LIMIT}. Set higher to get more rows.")


class BulkCubeCoordInput(BaseModel):
    items: List[CubeCoordInput] = Field(
        ..., description="List of {productId, coordinate} pairs to fetch series info for in a single batch call."
    )
    offset: Optional[int] = Field(0, description="Number of results to skip (for pagination). Default 0.")
    limit: Optional[int] = Field(None, description=f"Max results to return. Default {DEFAULT_TRUNCATION_LIMIT}.")

class CubeListInput(BaseModel):
    offset: int = Field(0, description="Number of cubes to skip (for pagination). Default 0.")
    limit: int = Field(100, description="Max cubes to return. Default 100.")

class CubeSearchInput(BaseModel):
    search_term: str = Field(..., description="Text to search for in cube titles. Multiple keywords use AND logic.")
    max_results: int = Field(25, description="Max matching cubes to return. Default 25.")

class FullTableDownloadCSVInput(BaseModel):
    productId: int
    lang: str = Field('en', description="Language code ('en' for English, 'fr' for French).")

class FullTableDownloadSDMXInput(BaseModel):
    productId: int
