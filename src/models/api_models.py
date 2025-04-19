from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ProductIdInput(BaseModel):
    productId: int

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

class BulkVectorRangeInput(BaseModel):
    vectorIds: List[str] # API uses strings for vector IDs here
    startDataPointReleaseDate: Optional[str] = None # YYYY-MM-DDTHH:MM
    endDataPointReleaseDate: Optional[str] = None # YYYY-MM-DDTHH:MM

class FullTableDownloadCSVInput(BaseModel):
    productId: int
    lang: str = Field('en', description="Language code ('en' for English, 'fr' for French).")

class FullTableDownloadSDMXInput(BaseModel):
    productId: int
