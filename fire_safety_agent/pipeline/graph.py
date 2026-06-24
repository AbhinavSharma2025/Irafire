from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph


class FireSafetyState(TypedDict, total=False):
    # Input
    input_file_path: str
    input_file_type: str

    # CAD Parser output
    rooms: list[dict]
    building_summary: dict

    # Fire & Safety Agent output
    occupancy_classification: dict
    hazard_map: list[dict]

    # Code Agent output
    code_analysis: list[dict]

    # System Design Agent output
    system_design: list[dict]

    # Hydraulic Agent output
    hydraulic_design: dict

    # Code Compliance Agent output
    compliance_report: dict

    # Report Agent output
    report_path: str

    # Pipeline control
    current_agent: str
    errors: list[str]
    warnings: list[str]


def get_pipeline():
    # Import here to avoid circular imports
    from agents.fire_safety_agent import fire_safety_agent
    from agents.code_agent import code_agent
    from agents.system_design_agent import system_design_agent
    from agents.hydraulic_agent import hydraulic_agent
    from agents.compliance_agent import compliance_agent
    from agents.report_agent import report_agent
    from tools.cad_parser_node import cad_parser_node

    graph = StateGraph(FireSafetyState)

    graph.add_node("cad_parser", cad_parser_node)
    graph.add_node("fire_safety_agent", fire_safety_agent)
    graph.add_node("code_agent", code_agent)
    graph.add_node("system_design_agent", system_design_agent)
    graph.add_node("hydraulic_agent", hydraulic_agent)
    graph.add_node("compliance_agent", compliance_agent)
    graph.add_node("report_agent", report_agent)

    graph.add_edge(START, "cad_parser")
    graph.add_edge("cad_parser", "fire_safety_agent")
    graph.add_edge("fire_safety_agent", "code_agent")
    graph.add_edge("code_agent", "system_design_agent")
    graph.add_edge("system_design_agent", "hydraulic_agent")
    graph.add_edge("hydraulic_agent", "compliance_agent")
    graph.add_edge("compliance_agent", "report_agent")
    graph.add_edge("report_agent", END)

    return graph.compile()