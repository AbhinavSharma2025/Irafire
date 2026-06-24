from __future__ import annotations

from typing import Any

from tools.cad_parser import parse_dxf, parse_pdf_floorplan
from pipeline.graph import FireSafetyState


def cad_parser_node(state: FireSafetyState) -> dict[str, Any]:
    file_path = state.get("input_file_path", "")
    file_type = state.get("input_file_type", "").lower()

    if not file_path:
        return {
            "current_agent": "cad_parser",
            "rooms": [],
            "building_summary": {},
            "errors": ["No input file path provided."],
        }

    try:
        if file_type in {"dxf", "dwg"}:
            result = parse_dxf(file_path)
        elif file_type == "pdf":
            result = parse_pdf_floorplan(file_path)
        else:
            # Try DXF first, fall back to PDF
            try:
                result = parse_dxf(file_path)
            except Exception:
                result = parse_pdf_floorplan(file_path)

        return {
            "current_agent": "cad_parser",
            "rooms": result.get("rooms", []),
            "building_summary": result.get("building_summary", {}),
        }

    except Exception as exc:
        return {
            "current_agent": "cad_parser",
            "rooms": [],
            "building_summary": {},
            "errors": [f"CAD parser failed: {exc}"],
        }