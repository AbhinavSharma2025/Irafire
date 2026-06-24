from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from config import MODEL_NAME, OPENAI_API_KEY
from pipeline.graph import FireSafetyState


SYSTEM_PROMPT = (
	"You are a fire protection systems designer. Based on code requirements, "
	"specify exact detection, suppression and alarm systems for each room. "
	"Return strict JSON only."
)


def _get_openai_client() -> OpenAI:
	if not OPENAI_API_KEY:
		raise ValueError("OPENAI_API_KEY is not set.")
	return OpenAI(api_key=OPENAI_API_KEY)


def _null_system_design(room_number: str | None) -> dict[str, Any]:
	return {
		"room_number": room_number,
		"system_design_agent_version": "system_design_v1",
		"system_design": {
			"detection_system": None,
			"sprinkler_system": None,
			"suppression_system": None,
			"extinguisher_type": None,
			"alarm_devices": [],
			"design_notes": [],
			"review_required": True,
			"review_reason": "System design could not be generated automatically.",
		},
	}


def _parse_system_design_response(content: str, room_number: str | None) -> dict[str, Any]:
	parsed = json.loads(content)
	system_design = parsed.get("system_design", {})
	return {
		"room_number": parsed.get("room_number", room_number),
		"system_design_agent_version": parsed.get("system_design_agent_version", "system_design_v1"),
		"system_design": {
			"detection_system": system_design.get("detection_system"),
			"sprinkler_system": system_design.get("sprinkler_system"),
			"suppression_system": system_design.get("suppression_system"),
			"extinguisher_type": system_design.get("extinguisher_type"),
			"alarm_devices": system_design.get("alarm_devices", []),
			"design_notes": system_design.get("design_notes", []),
			"review_required": bool(system_design.get("review_required", False)),
			"review_reason": system_design.get("review_reason"),
		},
	}


def system_design_agent(state: FireSafetyState) -> dict[str, Any]:
	rooms = state.get("code_analysis", []) or state.get("rooms", []) or []
	updated_rooms: list[dict[str, Any]] = []
	errors = list(state.get("errors", []) or [])
	client = _get_openai_client()

	for room in rooms:
		room_number = room.get("room_number")
		fire_requirements = room.get("fire_requirements", {}) or {}
		try:
			response = client.chat.completions.create(
				model=MODEL_NAME,
				messages=[
					{"role": "system", "content": SYSTEM_PROMPT},
					{
						"role": "user",
						"content": (
							"Generate a detailed room system design from the following fire "
							"requirements. Return valid JSON with the exact schema requested.\n\n"
							f"ROOM_NUMBER: {room_number}\n"
							f"FIRE_REQUIREMENTS:\n{json.dumps(fire_requirements, ensure_ascii=False)}"
						),
					},
				],
				response_format={"type": "json_object"},
			)

			content = response.choices[0].message.content or "{}"
			system_design_result = _parse_system_design_response(content, room_number)
			merged_room = dict(room)
			merged_room.update(system_design_result)
			updated_rooms.append(merged_room)
		except Exception as exc:
			errors.append(f"system_design_agent failed for room {room_number}: {exc}")
			fallback_room = dict(room)
			fallback_room.update(_null_system_design(room_number))
			updated_rooms.append(fallback_room)

	return {
		"current_agent": "system_design_agent",
		"rooms": updated_rooms,
		"system_design": updated_rooms,
		"errors": errors,
	}
