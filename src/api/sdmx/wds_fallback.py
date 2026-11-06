"""A stand-in table structure (DSD) built from WDS metadata (#175).

StatCan sometimes serves a table's SDMX structure cut short (e.g. 14100287 at exactly
64 KiB, every time, for hours). Data rows are labelled from the structure, so without
it every data call for that table fails. WDS getCubeMetadata has the same dimensions,
member ids (equal to the SDMX codes), names and parents, and getCodeSets has the
attribute codes (UOM, scalar factor, status, symbol...). This module writes them out
as SDMX 2.1 structure XML, so every consumer (parse_dsd_labels, _parse_structure_xml,
the key check) works unchanged.
"""

import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from ..client import extract_success_object, make_post_request
from ..metadata_tools import _fetch_code_sets

_MES = "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message"
_STR = "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure"
_COM = "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common"
_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

ET.register_namespace("mes", _MES)
ET.register_namespace("str", _STR)
ET.register_namespace("com", _COM)

FALLBACK_MARKER = "<!-- statcan-mcp: structure built from WDS getCubeMetadata (#175) -->"


def _component_id(name: str) -> str:
    """WDS dimension name → SDMX component id, as in search's key_template (#136)."""
    return re.sub(r"[^0-9A-Za-z_]", "_", name or "")


def _described(code: Any, representation: Optional[str], desc: Optional[str]) -> str:
    """The DSD's label for coded flags: '<symbol> = <description>', e.g. 'p = preliminary'."""
    return f"{representation or code} = {desc or ''}".rstrip(" =") or str(code)


def _attribute_codelists(code_sets: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, str]]:
    """Attribute id → {code: label}, matching the labels in StatCan's own DSDs."""
    def table(name: str, code_key: str, label) -> Dict[str, str]:
        return {str(e.get(code_key)): label(e) for e in code_sets.get(name, []) if e.get(code_key) is not None}

    return {
        "UOM": table("uom", "memberUomCode", lambda e: e.get("memberUomEn") or str(e.get("memberUomCode"))),
        "SCALAR_FACTOR": table("scalar", "scalarFactorCode", lambda e: e.get("scalarFactorDescEn") or ""),
        "SYMBOL": table(
            "symbol", "symbolCode",
            lambda e: _described(e["symbolCode"], e.get("symbolRepresentationEn"), e.get("symbolDescEn")),
        ),
        "STATUS_CAN": table(
            "status", "statusCode",
            lambda e: _described(e["statusCode"], e.get("statusRepresentationEn"), e.get("statusDescEn")),
        ),
        "SECURITY_LEVEL": table(
            "securityLevel", "securityLevelCode",
            lambda e: _described(
                e["securityLevelCode"], e.get("securityLevelRepresentationEn"), e.get("securityLevelDescEn")
            ),
        ),
        "TERMINATED": table(
            "terminated", "codeId",
            lambda e: _described(e["codeId"], e.get("displayCodeEn"), e.get("codeTextEn")),
        ),
    }


def _name(parent: ET.Element, text: str) -> None:
    el = ET.SubElement(parent, f"{{{_COM}}}Name")
    el.set(_XML_LANG, "en")
    el.text = text


def _codelist(parent: ET.Element, cl_id: str, name: str, codes: List[Dict[str, Any]]) -> None:
    cl = ET.SubElement(parent, f"{{{_STR}}}Codelist", {"id": cl_id})
    _name(cl, name)
    for c in codes:
        code = ET.SubElement(cl, f"{{{_STR}}}Code", {"id": c["id"]})
        _name(code, c["name"])
        if c.get("parent"):
            ref_parent = ET.SubElement(code, f"{{{_STR}}}Parent")
            ET.SubElement(ref_parent, "Ref", {"id": c["parent"]})


def _component(parent: ET.Element, tag: str, comp_id: str, cl_id: str, position: Optional[int] = None) -> None:
    attrs = {"id": comp_id}
    if position is not None:
        attrs["position"] = str(position)
    comp = ET.SubElement(parent, f"{{{_STR}}}{tag}", attrs)
    enum = ET.SubElement(ET.SubElement(comp, f"{{{_STR}}}LocalRepresentation"), f"{{{_STR}}}Enumeration")
    ET.SubElement(enum, "Ref", {"id": cl_id})


def build_structure_xml(product_id: int, cube: Dict[str, Any], code_sets: Dict[str, List[Dict[str, Any]]]) -> str:
    """SDMX 2.1 structure XML for one table from getCubeMetadata's object + getCodeSets."""
    root = ET.Element(f"{{{_MES}}}Structure")
    structures = ET.SubElement(root, f"{{{_MES}}}Structures")
    codelists = ET.SubElement(structures, f"{{{_STR}}}Codelists")

    dims = sorted(cube.get("dimension", []), key=lambda d: int(d.get("dimensionPositionId", 0)))
    dim_entries = []
    for d in dims:
        comp_id = _component_id(d.get("dimensionNameEn", ""))
        cl_id = f"CL_{comp_id}"
        codes = [
            {
                "id": str(m["memberId"]),
                "name": m.get("memberNameEn") or str(m["memberId"]),
                "parent": str(m["parentMemberId"]) if m.get("parentMemberId") is not None else None,
            }
            for m in d.get("member", [])
        ]
        _codelist(codelists, cl_id, d.get("dimensionNameEn", comp_id), codes)
        dim_entries.append((comp_id, cl_id, int(d.get("dimensionPositionId", 0))))

    attributes = _attribute_codelists(code_sets)
    for attr_id, codes in attributes.items():
        _codelist(codelists, f"CL_{attr_id}", attr_id, [{"id": k, "name": v} for k, v in codes.items()])

    ds = ET.SubElement(
        ET.SubElement(structures, f"{{{_STR}}}DataStructures"),
        f"{{{_STR}}}DataStructure",
        {"id": f"Data_Structure_{product_id}"},
    )
    _name(ds, f"Data Structure of {cube.get('cubeTitleEn', product_id)}")
    components = ET.SubElement(ds, f"{{{_STR}}}DataStructureComponents")
    dim_list = ET.SubElement(components, f"{{{_STR}}}DimensionList")
    for comp_id, cl_id, position in dim_entries:
        _component(dim_list, "Dimension", comp_id, cl_id, position)
    attr_list = ET.SubElement(components, f"{{{_STR}}}AttributeList")
    for attr_id in attributes:
        _component(attr_list, "Attribute", attr_id, f"CL_{attr_id}")

    return FALLBACK_MARKER + ET.tostring(root, encoding="unicode")


def is_fallback_structure(xml_text: str) -> bool:
    return xml_text.startswith(FALLBACK_MARKER)


async def fetch_wds_structure_xml(product_id: int) -> str:
    """Build the stand-in structure for a table from WDS (two requests; code sets are cached)."""
    result = await make_post_request("/getCubeMetadata", [{"productId": product_id}])
    cube = extract_success_object(result)
    if not cube.get("dimension"):
        raise ValueError(f"WDS metadata for table {product_id} has no dimensions.")
    return build_structure_xml(product_id, cube, await _fetch_code_sets())
