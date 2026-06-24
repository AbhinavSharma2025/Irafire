from __future__ import annotations

import math
from collections import Counter
from typing import Any

from pipeline.graph import FireSafetyState


CAD_UNIT_TO_METRE = 1 / 40.77


def _empty_hydraulic_design() -> dict[str, Any]:
    return {
        "building_summary": {},
        "zone_summary": [],
        "design_area": {},
        "sprinkler_design": {},
        "water_demand": {},
        "pressure": {},
        "water_storage": {},
        "review_required": True,
        "review_notes": ["Hydraulic design could not be fully calculated."],
    }


def _room_area_m2(room: dict[str, Any]) -> float:
    geometry = room.get("geometry", {}) or {}
    area_cad_units = float(geometry.get("area_cad_units", 0.0) or 0.0)
    return area_cad_units * (CAD_UNIT_TO_METRE ** 2)


def _classify_room_hazard(room: dict[str, Any]) -> str:
    system_design = room.get("system_design", {}) or {}
    sprinkler_system = str(system_design.get("sprinkler_system", "") or "").lower()
    zone_type = str(room.get("zone_type", "") or "").upper()
    if "wet pipe" in sprinkler_system and ("MECHANICAL" in zone_type or "UTILITY" in zone_type):
        return "Ordinary Hazard Group 1 (OH1)"
    return "Light Hazard (LH)"


def _hazard_params(hazard_class: str) -> dict[str, float]:
    if hazard_class == "Ordinary Hazard Group 1 (OH1)":
        return {"design_density": 5.0, "coverage": 12.0, "k_factor": 8.0, "design_area": 72.0}
    return {"design_density": 2.25, "coverage": 21.0, "k_factor": 5.6, "design_area": 84.0}


def hydraulic_agent(state: FireSafetyState) -> dict[str, Any]:
    rooms = state.get("system_design", []) or state.get("rooms", []) or []
    building_summary = state.get("building_summary", {}) or {}
    occupancy_classification = state.get("occupancy_classification", {}) or {}
    errors = list(state.get("errors", []) or [])

    if not rooms:
        return {
            "current_agent": "hydraulic_agent",
            "hydraulic_design": _empty_hydraulic_design(),
            "errors": errors,
        }

    zone_details: list[dict[str, Any]] = []
    hazard_counts: Counter[str] = Counter()
    room_areas_m2: list[float] = []

    for room in rooms:
        hazard_class = _classify_room_hazard(room)
        hazard_counts[hazard_class] += 1
        area_m2 = _room_area_m2(room)
        room_areas_m2.append(area_m2)
        zone_details.append({
            "room_number": room.get("room_number"),
            "zone_type": room.get("zone_type"),
            "hazard_class": hazard_class,
            "room_area_m2": round(area_m2, 3),
        })

    dominant_hazard = (
        "Ordinary Hazard Group 1 (OH1)"
        if hazard_counts["Ordinary Hazard Group 1 (OH1)"] > hazard_counts["Light Hazard (LH)"]
        else "Light Hazard (LH)"
    )
    params = _hazard_params(dominant_hazard)
    design_area_m2 = params["design_area"]
    design_density = params["design_density"]
    coverage_m2_per_head = params["coverage"]
    k_factor = params["k_factor"]

    # ✅ FIX: separate list and per-room variable
    estimated_heads_list: list[int] = []
    room_design_rows: list[dict[str, Any]] = []

    for room, area_m2, zone_detail in zip(rooms, room_areas_m2, zone_details):
        hazard_class = zone_detail["hazard_class"]
        room_params = _hazard_params(hazard_class)
        heads_for_room = max(1, math.ceil(area_m2 / room_params["coverage"])) if area_m2 > 0 else 1
        estimated_heads_list.append(heads_for_room)

        room_design_rows.append({
            "room_number": room.get("room_number"),
            "hazard_class": hazard_class,
            "room_area_m2": round(area_m2, 3),
            "design_density_lpm_m2": room_params["design_density"],
            "coverage_m2_per_head": room_params["coverage"],
            "k_factor": room_params["k_factor"],
            "estimated_heads": heads_for_room,
            "min_flow_per_head_lpm": round(room_params["design_density"] * room_params["coverage"], 2),
            "min_pressure_per_head_bar": round(
                ((room_params["design_density"] * room_params["coverage"]) / room_params["k_factor"]) ** 2 / 10.0, 3
            ),
        })

    sprinkler_demand_lpm = design_density * design_area_m2
    hose_stream_lpm = 1125
    total_demand_lpm = sprinkler_demand_lpm + hose_stream_lpm

    min_pressure_at_head_bar = 0.5
    estimated_friction_loss_bar = 0.5
    required_pressure_bar = min_pressure_at_head_bar + estimated_friction_loss_bar
    available_municipal_pressure_bar = 2.0
    margin_bar = available_municipal_pressure_bar - required_pressure_bar
    pump_required = margin_bar < 0

    building_height = float(building_summary.get("building_height_m", 15.0) or 15.0)
    occupancy_group = str(occupancy_classification.get("occupancy_group", "") or "")
    if building_height <= 15.0 and "Group E" in occupancy_group:
        underground_sump = 0
        terrace_tank = 0
        wet_riser_required = False
    else:
        underground_sump = 150000
        terrace_tank = 25000
        wet_riser_required = building_height > 15.0

    hydraulic_design = {
        "building_summary": {
            "building_height_m": building_height,
            "occupancy_group": occupancy_group or None,
            "dominant_hazard_class": dominant_hazard,
            "wet_riser_required": wet_riser_required,
        },
        "zone_summary": zone_details,
        "design_area": {
            "hazard_class": dominant_hazard,
            "design_area_m2": design_area_m2,
            "design_density_lpm_m2": design_density,
        },
        "sprinkler_design": {
            "hazard_class": dominant_hazard,
            "design_density_lpm_m2": design_density,
            "coverage_m2_per_head": coverage_m2_per_head,
            "k_factor": k_factor,
            "estimated_heads_total": sum(estimated_heads_list),
            "min_flow_per_head_lpm": round(design_density * coverage_m2_per_head, 2),
            "min_pressure_per_head_bar": round(
                ((design_density * coverage_m2_per_head) / k_factor) ** 2 / 10.0, 3
            ),
            "room_designs": room_design_rows,
        },
        "water_demand": {
            "sprinkler_demand_lpm": sprinkler_demand_lpm,
            "hose_stream_lpm": hose_stream_lpm,
            "total_demand_lpm": total_demand_lpm,
            "total_demand_m3h": round(total_demand_lpm / 1000 * 60, 2),
        },
        "pressure": {
            "min_pressure_at_head_bar": min_pressure_at_head_bar,
            "estimated_friction_loss_bar": estimated_friction_loss_bar,
            "required_pressure_bar": required_pressure_bar,
            "available_municipal_pressure_bar": available_municipal_pressure_bar,
            "margin_bar": margin_bar,
            "pump_required": pump_required,
        },
        "water_storage": {
            "underground_sump_liters": underground_sump,
            "terrace_tank_liters": terrace_tank,
            "wet_riser_required": wet_riser_required,
            "nbc_reference": "NBC 2016 Part 4 Table 7 — Group E",
        },
        "review_required": pump_required or wet_riser_required,
        "review_notes": [
            "⚠️ Building height assumed at 15m — verify from drawings.",
            "⚠️ CAD scale not verified — confirm 1 CAD unit = 1/40.77 metres.",
            "⚠️ Friction loss estimated at 0.5 bar — recalculate after layout verification.",
        ],
    }

    return {
        "current_agent": "hydraulic_agent",
        "hydraulic_design": hydraulic_design,
        "errors": errors,
    }