from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import ezdxf
import fitz


def _shoelace_area(vertices: list[tuple[float, float]]) -> float:
	if len(vertices) < 3:
		return 0.0

	total = 0.0
	count = len(vertices)
	for index in range(count):
		x1, y1 = vertices[index]
		x2, y2 = vertices[(index + 1) % count]
		total += x1 * y2 - x2 * y1
	return abs(total) / 2.0


def _centroid(vertices: list[tuple[float, float]]) -> list[float]:
	if not vertices:
		return [0.0, 0.0]

	x_total = sum(x for x, _ in vertices)
	y_total = sum(y for _, y in vertices)
	return [x_total / len(vertices), y_total / len(vertices)]


def _bbox(vertices: list[tuple[float, float]]) -> list[float]:
	if not vertices:
		return [0.0, 0.0, 0.0, 0.0]

	xs = [x for x, _ in vertices]
	ys = [y for _, y in vertices]
	return [min(xs), min(ys), max(xs), max(ys)]


def _is_closed_polyline(entity: Any) -> bool:
	return bool(getattr(entity, "closed", False) or getattr(entity, "is_closed", False))


def _extract_polyline_vertices(entity: Any) -> list[tuple[float, float]]:
	if entity.dxftype() == "LWPOLYLINE":
		return [(float(point[0]), float(point[1])) for point in entity.get_points("xy")]

	if entity.dxftype() == "POLYLINE":
		vertices: list[tuple[float, float]] = []
		for vertex in entity.vertices():
			location = vertex.dxf.location
			vertices.append((float(location.x), float(location.y)))
		return vertices

	return []


def _entity_text(entity: Any) -> str:
	if entity.dxftype() == "TEXT":
		return str(getattr(entity.dxf, "text", "")).strip()

	if entity.dxftype() == "MTEXT":
		text_method = getattr(entity, "plain_text", None)
		if callable(text_method):
			return str(text_method()).strip()
		return str(getattr(entity, "text", "")).strip()

	return ""


def _entity_point(entity: Any) -> tuple[float, float]:
	insert = getattr(entity.dxf, "insert", None)
	if insert is not None:
		return float(insert.x), float(insert.y)

	location = getattr(entity.dxf, "location", None)
	if location is not None:
		return float(location.x), float(location.y)

	return 0.0, 0.0


def _nearest_text_label(text_entities: list[Any], centroid: list[float]) -> str:
	if not text_entities:
		return ""

	nearest_label = ""
	nearest_distance = math.inf
	centroid_x, centroid_y = centroid

	for entity in text_entities:
		label = _entity_text(entity)
		if not label:
			continue

		point_x, point_y = _entity_point(entity)
		distance = math.hypot(point_x - centroid_x, point_y - centroid_y)
		if distance < nearest_distance:
			nearest_distance = distance
			nearest_label = label

	return nearest_label


def _empty_result(source: str | None = None) -> dict[str, Any]:
	result: dict[str, Any] = {
		"rooms": [],
		"building_summary": {"total_rooms": 0, "total_area_cad_units": 0.0},
		"raw_entity_count": 0,
	}
	if source is not None:
		result["source"] = source
	return result


def parse_dxf(file_path: str) -> dict[str, Any]:
	try:
		dxf_document = ezdxf.readfile(file_path)
		modelspace = dxf_document.modelspace()

		all_entities = list(modelspace)
		text_entities = [entity for entity in all_entities if entity.dxftype() in {"TEXT", "MTEXT"}]

		rooms: list[dict[str, Any]] = []
		total_area = 0.0
		room_index = 1

		for entity in all_entities:
			if entity.dxftype() not in {"LWPOLYLINE", "POLYLINE"}:
				continue

			if not _is_closed_polyline(entity):
				continue

			vertices = _extract_polyline_vertices(entity)
			if len(vertices) < 3:
				continue

			area = _shoelace_area(vertices)
			centroid = _centroid(vertices)
			bbox = _bbox(vertices)
			label = _nearest_text_label(text_entities, centroid)
			room_number = label if label else f"R{room_index:03d}"

			rooms.append(
				{
					"room_number": room_number,
					"room_type": "Unknown",
					"geometry": {
						"area_cad_units": area,
						"centroid": centroid,
						"bbox": bbox,
					},
				}
			)
			total_area += area
			room_index += 1

		return {
			"rooms": rooms,
			"building_summary": {
				"total_rooms": len(rooms),
				"total_area_cad_units": total_area,
			},
			"raw_entity_count": len(all_entities),
		}
	except Exception:
		return _empty_result()


def parse_pdf_floorplan(file_path: str) -> dict[str, Any]:
	try:
		pdf_document = fitz.open(file_path)
		rooms: list[dict[str, Any]] = []
		total_area = 0.0
		raw_entity_count = 0
		room_index = 1

		for page in pdf_document:
			blocks = page.get_text("blocks")
			raw_entity_count += len(blocks)

			for block in blocks:
				x0, y0, x1, y1, text, *_ = block
				label = str(text).strip().splitlines()[0].strip() if str(text).strip() else ""
				if not label:
					continue

				bbox = [float(x0), float(y0), float(x1), float(y1)]
				centroid = [(float(x0) + float(x1)) / 2.0, (float(y0) + float(y1)) / 2.0]

				rooms.append(
					{
						"room_number": label if label else f"R{room_index:03d}",
						"room_type": "Unknown",
						"geometry": {
							"area_cad_units": 0.0,
							"centroid": centroid,
							"bbox": bbox,
						},
					}
				)
				room_index += 1

		pdf_document.close()

		return {
			"rooms": rooms,
			"building_summary": {
				"total_rooms": len(rooms),
				"total_area_cad_units": total_area,
			},
			"raw_entity_count": raw_entity_count,
			"source": "pdf_text_extraction",
		}
	except Exception:
		return _empty_result(source="pdf_text_extraction")
