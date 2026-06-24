from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from config import MODEL_NAME, OPENAI_API_KEY
from pipeline.graph import FireSafetyState


SYSTEM_PROMPT = (
	"You are a certified Fire & Safety Engineer specializing in NBC India 2016 "
	"and NFPA codes. Classify rooms by occupancy and hazard level."
)


def _get_openai_client() -> OpenAI:
	if not OPENAI_API_KEY:
		raise ValueError("OPENAI_API_KEY is not set. Configure it in your environment.")
	return OpenAI(api_key=OPENAI_API_KEY)


def _default_building_classification() -> dict[str, Any]:
	return {
		"occupancy_group": "Unknown",
		"risk_level": "Unknown",
		"required_fire_rating": None,
		"required_exits": None,
		"applicable_codes": [],
	}


def _default_room_update(room: dict[str, Any]) -> dict[str, Any]:
	return {
		"room_number": room.get("room_number"),
		"room_type": room.get("room_type", "Unknown"),
		"zone_type": room.get("zone_type", "UNKNOWN"),
		"hazards": room.get("hazards", []),
		"area_sqft": room.get("area_sqft"),
		"capacity": room.get("capacity"),
		"ceiling_height_ft": room.get("ceiling_height_ft"),
	}


def _merge_room_updates(
	rooms: list[dict[str, Any]],
	updates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
	updates_by_number = {
		str(update.get("room_number")): update
		for update in updates
		if update.get("room_number") is not None
	}

	merged_rooms: list[dict[str, Any]] = []
	for room in rooms:
		room_number = str(room.get("room_number", ""))
		update = updates_by_number.get(room_number, {})
		merged_room = dict(room)
		if update:
			merged_room["room_type"] = update.get("room_type", merged_room.get("room_type", "Unknown"))
			merged_room["zone_type"] = update.get("zone_type", merged_room.get("zone_type", "UNKNOWN"))
			merged_room["hazards"] = update.get("hazards", merged_room.get("hazards", []))
			if update.get("area_sqft") is not None:
				merged_room["area_sqft"] = update.get("area_sqft")
			if update.get("capacity") is not None:
				merged_room["capacity"] = update.get("capacity")
			if update.get("ceiling_height_ft") is not None:
				merged_room["ceiling_height_ft"] = update.get("ceiling_height_ft")
		else:
			merged_room.update(_default_room_update(room))
		merged_rooms.append(merged_room)

	return merged_rooms


def fire_safety_agent(state: FireSafetyState) -> dict[str, Any]:
	rooms = state.get("rooms", []) or []
	building_summary = state.get("building_summary", {}) or {}

	if not rooms:
		return {
			"current_agent": "fire_safety_agent",
			"occupancy_classification": _default_building_classification(),
			"rooms": [],
		}

	payload = {
		"rooms": rooms,
		"building_summary": building_summary,
		"required_room_output": {
			"room_number": "str",
			"room_type": "str",
			"zone_type": "str",
			"hazards": ["str"],
			"area_sqft": "float or null",
			"capacity": "int or null",
			"ceiling_height_ft": "float or null",
		},
		"required_building_output": {
			"occupancy_group": "Group E - Business",
			"risk_level": "Moderate",
			"required_fire_rating": "2 hours",
			"required_exits": 3,
			"applicable_codes": ["NBC 2016", "NFPA 13"],
		},
	}

	try:
		client = _get_openai_client()
		response = client.chat.completions.create(
			model=MODEL_NAME,
			messages=[
				{"role": "system", "content": SYSTEM_PROMPT},
				{
					"role": "user",
					"content": (
						"Classify the following building rooms and the overall building. "
						"Return valid JSON with top-level keys 'rooms' and 'building_classification'. "
						"Each room object must include room_number, room_type, zone_type, hazards, "
						"area_sqft, capacity, and ceiling_height_ft. The building classification must "
						"include occupancy_group, risk_level, required_fire_rating, required_exits, "
						"and applicable_codes.\n\n"
						f"INPUT:\n{json.dumps(payload, ensure_ascii=False)}"
					),
				},
			],
			response_format={"type": "json_object"},
		)

		content = response.choices[0].message.content or "{}"
		parsed = json.loads(content)
		raw_room_updates = parsed.get("rooms", [])
		building_classification = parsed.get("building_classification", {})

		if not isinstance(raw_room_updates, list):
			raw_room_updates = []
		if not isinstance(building_classification, dict):
			building_classification = _default_building_classification()

		merged_rooms = _merge_room_updates(rooms, raw_room_updates)

		return {
			"current_agent": "fire_safety_agent",
			"rooms": merged_rooms,
			"occupancy_classification": {
				**_default_building_classification(),
				**building_classification,
			},
		}
	except Exception as exc:
		return {
			"current_agent": "fire_safety_agent",
			"rooms": [dict(room) for room in rooms],
			"occupancy_classification": _default_building_classification(),
			"errors": [f"fire_safety_agent failed: {exc}"],
		}
