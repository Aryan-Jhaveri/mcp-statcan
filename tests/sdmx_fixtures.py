"""Shared StatCan SDMX fixtures: structure-specific XML data + DSD, mocked with respx.

Two geographies (Canada, Ontario) × one product × N_PERIODS annual observations,
mirroring the shape of live responses for DF_18100004.
"""

from typing import Optional, Tuple

import respx
from httpx import Response

from src.config import SDMX_BASE_URL

N_PERIODS = 300  # 2 series × 300 periods = 600 rows, above MAX_SDMX_ROWS
DATA_URL = f"{SDMX_BASE_URL}data/DF_18100004/1+2.1"
STRUCTURE_URL = f"{SDMX_BASE_URL}structure/Data_Structure_18100004"

DSD_XML = """<?xml version="1.0" encoding="UTF-8"?>
<mes:Structure xmlns:mes="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message"
               xmlns:str="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure"
               xmlns:com="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common">
 <mes:Structures>
  <str:Codelists>
   <str:Codelist id="CL_Geography">
    <str:Code id="1"><com:Name xml:lang="en">Canada</com:Name></str:Code>
    <str:Code id="2"><com:Name xml:lang="en">Ontario</com:Name><str:Parent><Ref id="1"/></str:Parent></str:Code>
   </str:Codelist>
   <str:Codelist id="CL_Products">
    <str:Code id="1"><com:Name xml:lang="en">All-items</com:Name></str:Code>
   </str:Codelist>
   <str:Codelist id="CL_UOM"><str:Code id="17"><com:Name xml:lang="en">2002=100</com:Name></str:Code></str:Codelist>
   <str:Codelist id="CL_STATUS_CAN"><str:Code id="1"><com:Name xml:lang="en">.. = not available</com:Name></str:Code></str:Codelist>
  </str:Codelists>
  <str:DataStructures>
   <str:DataStructure id="Data_Structure_18100004"><com:Name xml:lang="en">Consumer Price Index</com:Name>
    <str:DataStructureComponents>
     <str:DimensionList>
      <str:Dimension id="Geography" position="1"><str:LocalRepresentation><str:Enumeration><Ref id="CL_Geography"/></str:Enumeration></str:LocalRepresentation></str:Dimension>
      <str:Dimension id="Products" position="2"><str:LocalRepresentation><str:Enumeration><Ref id="CL_Products"/></str:Enumeration></str:LocalRepresentation></str:Dimension>
      <str:TimeDimension id="TIME_PERIOD" position="3"/>
     </str:DimensionList>
     <str:AttributeList>
      <str:Attribute id="UOM"><str:LocalRepresentation><str:Enumeration><Ref id="CL_UOM"/></str:Enumeration></str:LocalRepresentation></str:Attribute>
      <str:Attribute id="STATUS_CAN"><str:LocalRepresentation><str:Enumeration><Ref id="CL_STATUS_CAN"/></str:Enumeration></str:LocalRepresentation></str:Attribute>
      <str:Attribute id="VECTOR_ID"/>
     </str:AttributeList>
    </str:DataStructureComponents>
   </str:DataStructure>
  </str:DataStructures>
 </mes:Structures>
</mes:Structure>"""

_HEADER = """<?xml version='1.0' encoding='UTF-8'?>
<message:StructureSpecificData xmlns:message="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message"
    xmlns:common="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common">
 <message:Header><message:Structure structureID="StatCan_DF_18100004_1_0" dimensionAtObservation="TIME_PERIOD">
  <common:StructureUsage><Ref agencyID="StatCan" id="DF_18100004" version="1.0"/></common:StructureUsage>
 </message:Structure></message:Header>
"""


def make_data_xml(
    first_value: Optional[str] = None,
    empty: bool = False,
    obs_attr_on: Optional[Tuple[int, int]] = None,
) -> str:
    """Data message for DATA_URL.

    first_value: OBS_VALUE of Canada's first observation (None = missing value).
    obs_attr_on: (series index, obs index) that gets STATUS_CAN="1".
    """
    if empty:
        return _HEADER + " <message:DataSet/>\n</message:StructureSpecificData>"
    parts = [_HEADER, " <message:DataSet>"]
    for g, vector in ((1, "41690973"), (2, "41691244")):
        parts.append(f'  <Series Geography="{g}" Products="1" VECTOR_ID="{vector}" UOM="17">')
        for i in range(N_PERIODS):
            value = str(float(i))
            if g == 1 and i == 0:
                value = first_value
            attrs = f'TIME_PERIOD="{1700 + i}"' + (f' OBS_VALUE="{value}"' if value is not None else "")
            if obs_attr_on == (g - 1, i):
                attrs += ' STATUS_CAN="1"'
            parts.append(f"   <Obs {attrs}/>")
        parts.append("  </Series>")
    parts.append(" </message:DataSet>\n</message:StructureSpecificData>")
    return "\n".join(parts)


def mock_sdmx(data_xml: Optional[str] = None, *, url: str = DATA_URL, status: int = 200, side_effect=None):
    """Register respx routes for a data request and the table's DSD. Call inside @respx.mock."""
    respx.get(STRUCTURE_URL).mock(return_value=Response(200, text=DSD_XML))
    route = respx.get(url)
    if side_effect is not None:
        route.mock(side_effect=side_effect)
    else:
        route.mock(return_value=Response(status, text=data_xml if data_xml is not None else make_data_xml()))
    return route
