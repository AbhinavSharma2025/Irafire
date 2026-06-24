from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from config import MODEL_NAME, OPENAI_API_KEY
from pipeline.graph import FireSafetyState
from tools.qdrant_tools import search_rules


SYSTEM_PROMPT = (
	"You are a fire code compliance specialist. Use retrieved NBC rules to map the "
	"room to fire requirements and return strict JSON only."
)


def _get_openai_client() -> OpenAI:
	if not OPENAI_API_KEY:
		raise ValueError("OPENAI_API_KEY is not set.")
	return OpenAI(api_key=OPENAI_API_KEY)


def _default_fire_requirements(room_number: str | None) -> dict[str, Any]:
	return {
		"room_number": room_number,
		"code_agent_version": "rag_v2",
		"fire_requirements": {
			"mapped_category": "Unknown",
			"hazard_class": "Unknown",
			"sprinkler_required": False,
			"sprinkler_system_type": None,
			"detector_required": False,
			"detector_type": None,
			"manual_call_point_required": False,
			"extinguisher_required": False,
			"special_suppression_required": False,
			"special_suppression_type": None,
			"classification_confidence": "LOW",
			"confidence_reason": "Classification unavailable due to processing error.",
			"rule_type_used": ["NBC"],
			"review_required": True,
			"review_reason": "Manual review required because the room could not be fully classified.",
			"assumptions": [],
			"rule_references": [],
		},
	}


def _normalize_rule_context(rules: list[dict[str, Any]]) -> str:
	if not rules:
		return "No relevant NBC rules retrieved."

	lines: list[str] = []
	for index, rule in enumerate(rules, start=1):
		lines.append(
			f"{index}. {rule.get('id', '')} | {rule.get('category', '')} | "
			f"{rule.get('rule', '')} | {rule.get('reference', '')}"
		)
	return "\n".join(lines)


def _build_room_query(room: dict[str, Any]) -> str:
	room_type = str(room.get("room_type", "Unknown")).strip()
	hazards = room.get("hazards", []) or []
	hazard_text = ", ".join(str(hazard) for hazard in hazards if str(hazard).strip())
	query_parts = [room_type or "Unknown"]
	if hazard_text:
		query_parts.append(hazard_text)
	query_parts.append("fire requirements")
	return " ".join(part for part in query_parts if part).strip()


def _parse_fire_requirements_response(content: str, room_number: str | None) -> dict[str, Any]:
	parsed = json.loads(content)
	fire_requirements = parsed.get("fire_requirements", {})
	return {
		"room_number": parsed.get("room_number", room_number),
		"code_agent_version": parsed.get("code_agent_version", "rag_v2"),
		"fire_requirements": {
			"mapped_category": fire_requirements.get("mapped_category", "Unknown"),
			"hazard_class": fire_requirements.get("hazard_class", "Unknown"),
			"sprinkler_required": bool(fire_requirements.get("sprinkler_required", False)),
			"sprinkler_system_type": fire_requirements.get("sprinkler_system_type"),
			"detector_required": bool(fire_requirements.get("detector_required", False)),
			"detector_type": fire_requirements.get("detector_type"),
			"manual_call_point_required": bool(fire_requirements.get("manual_call_point_required", False)),
			"extinguisher_required": bool(fire_requirements.get("extinguisher_required", False)),
			"special_suppression_required": bool(fire_requirements.get("special_suppression_required", False)),
			"special_suppression_type": fire_requirements.get("special_suppression_type"),
			"classification_confidence": fire_requirements.get("classification_confidence", "LOW"),
			"confidence_reason": fire_requirements.get("confidence_reason", ""),
			"rule_type_used": fire_requirements.get("rule_type_used", ["NBC"]),
			"review_required": bool(fire_requirements.get("review_required", False)),
			"review_reason": fire_requirements.get("review_reason"),
			"assumptions": fire_requirements.get("assumptions", []),
			"rule_references": fire_requirements.get("rule_references", []),
		},
	}


def code_agent(state: FireSafetyState) -> dict[str, Any]:
	rooms = state.get("rooms", []) or []
	updated_rooms: list[dict[str, Any]] = []
	errors = list(state.get("errors", []) or [])
	client = _get_openai_client()

	for room in rooms:
		room_number = room.get("room_number")
		query = _build_room_query(room)
		try:
			rules = search_rules(query=query, category_filter=None, top_k=3)
			rule_context = _normalize_rule_context(rules)

			response = client.chat.completions.create(
				model=MODEL_NAME,
				messages=[
					{"role": "system", "content": SYSTEM_PROMPT},
					{
						"role": "user",
						"content": (
							"Classify the room fire code requirements using the retrieved NBC "
							"rules as context. Return valid JSON with the exact structure "
							"requested.\n\n"
							f"ROOM:\n{json.dumps(room, ensure_ascii=False)}\n\n"
							f"RETRIEVED_RULES:\n{rule_context}"
						),
					},
				],
				response_format={"type": "json_object"},
			)

			content = response.choices[0].message.content or "{}"
			room_analysis = _parse_fire_requirements_response(content, room_number)
			merged_room = dict(room)
			merged_room.update(room_analysis)
			updated_rooms.append(merged_room)
		except Exception as exc:
			errors.append(f"code_agent failed for room {room_number}: {exc}")
			fallback_room = dict(room)
			fallback_room.update(_default_fire_requirements(room_number))
			updated_rooms.append(fallback_room)

	return {
		"current_agent": "code_agent",
		"rooms": updated_rooms,
		"code_analysis": updated_rooms,
		"errors": errors,
	}
