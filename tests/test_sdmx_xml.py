"""Tests for src/util/sdmx_xml.py — structure-specific SDMX-ML parsing (issue #90).

Fixtures mirror live StatCan responses for DF_18100004 (CPI), key "2+3.2".
"""

from src.util.sdmx_xml import dataflow_id, flatten_sdmx_xml, parse_dsd_labels

DSD_XML = """<?xml version="1.0" encoding="UTF-8"?>
<mes:Structure xmlns:mes="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message"
               xmlns:str="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure"
               xmlns:com="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common">
 <mes:Structures>
  <str:Codelists>
   <str:Codelist id="CL_Geography">
    <str:Code id="2"><com:Name xml:lang="fr">Canada (fr)</com:Name><com:Name xml:lang="en">Canada</com:Name></str:Code>
    <str:Code id="3"><com:Name xml:lang="en">Newfoundland and Labrador</com:Name></str:Code>
   </str:Codelist>
   <str:Codelist id="CL_Products_and_product_groups">
    <str:Code id="2"><com:Name xml:lang="en">All-items</com:Name></str:Code>
   </str:Codelist>
   <str:Codelist id="CL_UOM"><str:Code id="17"><com:Name xml:lang="en">2002=100</com:Name></str:Code></str:Codelist>
   <str:Codelist id="CL_SCALAR_FACTOR"><str:Code id="0"><com:Name xml:lang="en">units</com:Name></str:Code></str:Codelist>
   <str:Codelist id="CL_STATUS_CAN"><str:Code id="1"><com:Name xml:lang="en">.. = not available</com:Name></str:Code></str:Codelist>
  </str:Codelists>
  <str:DataStructures>
   <str:DataStructure id="Data_Structure_18100004">
    <str:DataStructureComponents>
     <str:DimensionList>
      <str:Dimension id="Products_and_product_groups" position="2"><str:LocalRepresentation><str:Enumeration><Ref id="CL_Products_and_product_groups"/></str:Enumeration></str:LocalRepresentation></str:Dimension>
      <str:Dimension id="Geography" position="1"><str:LocalRepresentation><str:Enumeration><Ref id="CL_Geography"/></str:Enumeration></str:LocalRepresentation></str:Dimension>
      <str:TimeDimension id="TIME_PERIOD" position="3"/>
     </str:DimensionList>
     <str:AttributeList>
      <str:Attribute id="UOM"><str:LocalRepresentation><str:Enumeration><Ref id="CL_UOM"/></str:Enumeration></str:LocalRepresentation></str:Attribute>
      <str:Attribute id="SCALAR_FACTOR"><str:LocalRepresentation><str:Enumeration><Ref id="CL_SCALAR_FACTOR"/></str:Enumeration></str:LocalRepresentation></str:Attribute>
      <str:Attribute id="STATUS_CAN"><str:LocalRepresentation><str:Enumeration><Ref id="CL_STATUS_CAN"/></str:Enumeration></str:LocalRepresentation></str:Attribute>
      <str:Attribute id="VECTOR_ID"/>
     </str:AttributeList>
    </str:DataStructureComponents>
   </str:DataStructure>
  </str:DataStructures>
 </mes:Structures>
</mes:Structure>"""

DATA_XML = """<?xml version='1.0' encoding='UTF-8'?>
<message:StructureSpecificData xmlns:message="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message"
    xmlns:common="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common">
 <message:Header>
  <message:Structure structureID="StatCan_DF_18100004_1_0" dimensionAtObservation="TIME_PERIOD">
   <common:StructureUsage><Ref agencyID="StatCan" id="DF_18100004" version="1.0"/></common:StructureUsage>
  </message:Structure>
 </message:Header>
 <message:DataSet>
  <Series Geography="2" Products_and_product_groups="2" VECTOR_ID="41690973" SCALAR_FACTOR="0" NB_DECIMAL="1" DGUID="2016A000011124" UOM="17">
   <Obs TIME_PERIOD="2026-08" OBS_VALUE="169.8"/>
   <Obs TIME_PERIOD="2026-09" OBS_VALUE="170.0"/>
  </Series>
  <Series Geography="3" Products_and_product_groups="2" VECTOR_ID="41691244" SCALAR_FACTOR="0" NB_DECIMAL="1" DGUID="2016A000210" UOM="17">
   <Obs TIME_PERIOD="2026-08" OBS_VALUE="172.4"/>
   <Obs TIME_PERIOD="2026-09" STATUS_CAN="1"/>
  </Series>
 </message:DataSet>
</message:StructureSpecificData>"""


def test_dsd_dimension_order_and_labels():
    dsd = parse_dsd_labels(DSD_XML)
    assert dsd["dimensions"] == ["Geography", "Products_and_product_groups"]  # by position, not document order
    assert dsd["labels"]["Geography"]["2"] == "Canada"  # English name preferred
    assert dsd["labels"]["UOM"]["17"] == "2002=100"
    assert "VECTOR_ID" not in dsd["labels"]  # uncoded attribute


def test_rows_have_correct_per_series_attributes():
    rows = flatten_sdmx_xml(DATA_XML, parse_dsd_labels(DSD_XML))
    assert len(rows) == 4
    canada = [r for r in rows if r["Geography"] == "Canada"]
    nl = [r for r in rows if r["Geography"] == "Newfoundland and Labrador"]
    # The JSON bug gave Canada two different VECTOR_IDs and both series NL's DGUID
    assert {r["VECTOR_ID"] for r in canada} == {"41690973"}
    assert {r["VECTOR_ID"] for r in nl} == {"41691244"}
    assert {r["DGUID"] for r in canada} == {"2016A000011124"}
    assert all(r["UOM"] == "2002=100" and r["SCALAR_FACTOR"] == "units" and r["NB_DECIMAL"] == "1" for r in rows)


def test_row_shape_matches_json_flattener():
    row = flatten_sdmx_xml(DATA_XML, parse_dsd_labels(DSD_XML))[0]
    assert list(row)[:5] == ["Geography", "Products_and_product_groups", "_series_key", "period", "value"]
    assert row["_series_key"] == "2.2"  # real SDMX key, usable in a follow-up query
    assert row["period"] == "2026-08" and row["value"] == "169.8"


def test_missing_value_and_observation_attribute():
    rows = flatten_sdmx_xml(DATA_XML, parse_dsd_labels(DSD_XML))
    last = rows[-1]
    assert last["value"] is None
    assert last["STATUS_CAN"] == ".. = not available"


def test_unknown_codes_fall_back_to_code():
    data = DATA_XML.replace('Geography="3"', 'Geography="99"')
    rows = flatten_sdmx_xml(data, parse_dsd_labels(DSD_XML))
    assert rows[-1]["Geography"] == "99"


def test_dataflow_id_from_header():
    assert dataflow_id(DATA_XML) == "DF_18100004"


def test_empty_dataset():
    data = DATA_XML.split("<message:DataSet>")[0] + "<message:DataSet/></message:StructureSpecificData>"
    assert flatten_sdmx_xml(data, parse_dsd_labels(DSD_XML)) == []


def test_dimension_ids_with_hyphens_match_data_attributes():
    """DSD id 'Occupation_-_Minor' appears as 'Occupation___Minor' in data XML (live: DF_98100452)."""
    dsd = DSD_XML.replace('id="Products_and_product_groups"', 'id="Products_-_and_groups"')
    data = DATA_XML.replace('Products_and_product_groups="2"', 'Products___and_groups="2"')
    rows = flatten_sdmx_xml(data, parse_dsd_labels(dsd))
    assert rows[0]["Products___and_groups"] == "All-items"  # labelled as a dimension
    assert rows[0]["_series_key"] == "2.2"


def test_dimensions_outside_dimension_list_ignored():
    """<str:Dimension> elements elsewhere (e.g. constraints) must not become key slots."""
    extra = '<str:Constraints><str:ContentConstraint><str:Dimension/></str:ContentConstraint></str:Constraints>'
    dsd = DSD_XML.replace("<str:DataStructures>", extra + "<str:DataStructures>")
    assert parse_dsd_labels(dsd)["dimensions"] == ["Geography", "Products_and_product_groups"]


def test_statcan_malformed_empty_result_parses_as_empty():
    """Live (DF_18100006, unmatched key): StatCan closes a <Series> it never opened."""
    data = DATA_XML.split("<message:DataSet>")[0] + (
        '<message:DataSet ss:dataScope="DataStructure"></Series> </message:DataSet> </message:StructureSpecificData>'
    ).replace(' ss:dataScope="DataStructure"', "")
    assert flatten_sdmx_xml(data, parse_dsd_labels(DSD_XML)) == []
    assert dataflow_id(data) == "DF_18100004"
