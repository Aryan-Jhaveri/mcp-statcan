from pydantic import BaseModel, Field
from typing import Optional


class SDMXStructureInput(BaseModel):
    productId: int


class SDMXDataInput(BaseModel):
    productId: int
    key: str = Field(
        ...,
        description=(
            "Dot-separated dimension codes in position order (e.g. '1.2.1'). "
            "Use '+' for OR ('1+2.2.1' = Geography 1 or 2). "
            "Omit a value for wildcard ('.2.1' = all geographies, Gender=2, Age=1). "
            "Code numbers match WDS memberIds — no translation needed. "
            "Call get_sdmx_structure first to see dimension positions and valid codes."
        ),
    )
    startPeriod: Optional[str] = Field(
        None, description="Start period in YYYY or YYYY-MM format."
    )
    endPeriod: Optional[str] = Field(
        None, description="End period in YYYY or YYYY-MM format."
    )
    lastNObservations: Optional[int] = Field(
        None,
        description="Return only the last N observations per series (e.g. 12 for one year of monthly data).",
    )


class SDMXVectorInput(BaseModel):
    vectorId: int
    startPeriod: Optional[str] = Field(
        None, description="Start period in YYYY or YYYY-MM format."
    )
    endPeriod: Optional[str] = Field(
        None, description="End period in YYYY or YYYY-MM format."
    )
    lastNObservations: Optional[int] = Field(
        None,
        description="Return only the last N observations (e.g. 5 for last 5 periods).",
    )
