from __future__ import annotations

from typing import Any

from pipeline.graph import FireSafetyState


def _add_violation(
	violations: list[dict[str, Any]],
	violation_id: str,
	room_number: str,
	severity: str,
	description: str,
	nbc_reference: str,
) -> None:
	violations.append(
		{
			"violation_id": violation_id,
			"room_number": room_number,
			"severity": severity,
			"description": description,
			"nbc_reference": nbc_reference,
		}
	)


def compliance_agent(state: FireSafetyState) -> dict[str, Any]:
	rooms = state.get("code_analysis", []) or state.get("rooms", []) or []
	hydraulic_design = state.get("hydraulic_design", {}) or {}
	occupancy_classification = state.get("occupancy_classification", {}) or {}
	errors = list(state.get("errors", []) or [])

	violations: list[dict[str, Any]] = []
	score = 100
	violation_index = 1

	for room in rooms:
		room_number = str(room.get("room_number", "BUILDING") or "BUILDING")
		fire_requirements = room.get("fire_requirements", {}) or {}

		if fire_requirements.get("classification_confidence") == "LOW":
			_add_violation(
				violations,
				f"V{violation_index:03d}",
				room_number,
				"MEDIUM",
				"LOW confidence classification for room fire requirements.",
				"NBC 2016 classification requires reviewer verification.",
			)
			violation_index += 1
			score -= 5

		if fire_requirements.get("review_required") is True:
			_add_violation(
				violations,
				f"V{violation_index:03d}",
				room_number,
				"LOW",
				"Room classification requires manual review.",
				"NBC 2016 requires engineering review for uncertain classifications.",
			)
			violation_index += 1
			score -= 3

		if fire_requirements.get("sprinkler_required") is True and not fire_requirements.get("sprinkler_system_type"):
			_add_violation(
				violations,
				f"V{violation_index:03d}",
				room_number,
				"HIGH",
				"Sprinkler is required but sprinkler system type is missing.",
				"NBC 2016 Part 4 sprinkler system selection.",
			)
			violation_index += 1
			score -= 10

		if fire_requirements.get("detector_required") is True and not fire_requirements.get("detector_type"):
			_add_violation(
				violations,
				f"V{violation_index:03d}",
				room_number,
				"HIGH",
				"Detector is required but detector type is missing.",
				"NBC 2016 Part 4 detection system selection.",
			)
			violation_index += 1
			score -= 8

	pressure = hydraulic_design.get("pressure", {}) or {}
	water_storage = hydraulic_design.get("water_storage", {}) or {}
	occupancy_required_exits = occupancy_classification.get("required_exits")

	if pressure.get("pump_required") is True:
		_add_violation(
			violations,
			f"V{violation_index:03d}",
			"BUILDING",
			"MEDIUM",
			"Hydraulic design indicates a pump is required.",
			"NBC 2016 Part 4 hydraulic capacity review.",
		)
		violation_index += 1
		score -= 5

	if water_storage.get("wet_riser_required") is True and float(water_storage.get("terrace_tank_liters", 0) or 0) == 0:
		_add_violation(
			violations,
			f"V{violation_index:03d}",
			"BUILDING",
			"HIGH",
			"Wet riser is required but terrace tank capacity is zero.",
			"NBC 2016 Part 4 Table 7.",
		)
		violation_index += 1
		score -= 10

	if occupancy_required_exits is not None and int(occupancy_required_exits) < 2:
		_add_violation(
			violations,
			f"V{violation_index:03d}",
			"BUILDING",
			"HIGH",
			"Required exits are below the minimum threshold.",
			"NBC 2016 Part 4 exit requirements.",
		)
		violation_index += 1
		score -= 15

	score = max(0, min(100, score))

	total_rooms_checked = len(rooms)
	violation_count = len(violations)
	if violation_count == 0:
		summary = f"Compliance score {score}/100 with no violations across {total_rooms_checked} rooms."
	else:
		summary = f"Compliance score {score}/100 with {violation_count} violation(s) across {total_rooms_checked} rooms."

	return {
		"current_agent": "compliance_agent",
		"compliance_report": {
			"compliance_score": score,
			"total_rooms_checked": total_rooms_checked,
			"violations": violations,
			"summary": summary,
		},
		"errors": errors,
	}
