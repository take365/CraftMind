from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path


INCH_TO_MM = 25.4
UNIT_TO_MM = {
    "1": 25.4,
    "4": 1.0,
}


@dataclass(frozen=True)
class LineEntity:
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass(frozen=True)
class CircleEntity:
    cx: float
    cy: float
    radius: float


@dataclass(frozen=True)
class PolylineEntity:
    points: list[tuple[float, float]]


def _pairs(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    return [(lines[i], lines[i + 1]) for i in range(0, len(lines) - 1, 2)]


def _collect_header_values(pairs: list[tuple[str, str]]) -> dict[str, list[str]]:
    header: dict[str, list[str]] = {}
    current_var: str | None = None
    in_header = False
    for raw_code, raw_value in pairs:
        code = raw_code.strip()
        value = raw_value.strip()
        if code == "0" and value == "SECTION":
            continue
        if code == "2" and value == "HEADER":
            in_header = True
            continue
        if in_header and code == "0" and value == "ENDSEC":
            break
        if not in_header:
            continue
        if code == "9":
            current_var = value
            header[current_var] = []
            continue
        if current_var is not None:
            header[current_var].append(value)
    return header


def _collect_entities(pairs: list[tuple[str, str]]) -> list[tuple[str, list[tuple[str, str]]]]:
    entities: list[tuple[str, list[tuple[str, str]]]] = []
    in_entities = False
    current_type: str | None = None
    current_data: list[tuple[str, str]] = []

    for raw_code, raw_value in pairs:
        code = raw_code.strip()
        value = raw_value.strip()
        if code == "2" and value == "ENTITIES":
            in_entities = True
            continue
        if not in_entities:
            continue
        if code == "0" and value == "ENDSEC":
            if current_type:
                entities.append((current_type, current_data))
            break
        if code == "0":
            if current_type:
                entities.append((current_type, current_data))
            current_type = value
            current_data = []
            continue
        if current_type:
            current_data.append((code, value))
    return entities


def _first_float(data: list[tuple[str, str]], target: str, default: float = 0.0) -> float:
    for code, value in data:
        if code == target:
            return float(value)
    return default


def _collect_polyline_points(data: list[tuple[str, str]]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    current_x: float | None = None
    for code, value in data:
        if code == "10":
            current_x = float(value)
        elif code == "20" and current_x is not None:
            points.append((current_x, float(value)))
            current_x = None
    return points


def _bbox_from_geometry(
    lines: list[LineEntity],
    circles: list[CircleEntity],
    polylines: list[PolylineEntity],
) -> dict[str, float]:
    xs: list[float] = []
    ys: list[float] = []

    for line in lines:
        xs.extend([line.x1, line.x2])
        ys.extend([line.y1, line.y2])

    for circle in circles:
        xs.extend([circle.cx - circle.radius, circle.cx + circle.radius])
        ys.extend([circle.cy - circle.radius, circle.cy + circle.radius])

    for polyline in polylines:
        for x, y in polyline.points:
            xs.append(x)
            ys.append(y)

    if not xs or not ys:
        return {"min_x": 0.0, "min_y": 0.0, "max_x": 0.0, "max_y": 0.0, "width": 0.0, "height": 0.0}

    min_x = min(xs)
    min_y = min(ys)
    max_x = max(xs)
    max_y = max(ys)
    return {
        "min_x": min_x,
        "min_y": min_y,
        "max_x": max_x,
        "max_y": max_y,
        "width": max_x - min_x,
        "height": max_y - min_y,
    }


def parse_dxf(path: str | Path) -> dict:
    source_path = Path(path)
    text = source_path.read_text(encoding="utf-8", errors="ignore")
    pairs = _pairs(text)
    header = _collect_header_values(pairs)
    entities = _collect_entities(pairs)

    lines: list[LineEntity] = []
    circles: list[CircleEntity] = []
    polylines: list[PolylineEntity] = []
    entity_counts = Counter()
    for entity_type, data in entities:
        entity_counts[entity_type] += 1
        if entity_type == "LINE":
            lines.append(
                LineEntity(
                    x1=_first_float(data, "10"),
                    y1=_first_float(data, "20"),
                    x2=_first_float(data, "11"),
                    y2=_first_float(data, "21"),
                )
            )
        elif entity_type == "CIRCLE":
            circles.append(
                CircleEntity(
                    cx=_first_float(data, "10"),
                    cy=_first_float(data, "20"),
                    radius=_first_float(data, "40"),
                )
            )
        elif entity_type == "LWPOLYLINE":
            points = _collect_polyline_points(data)
            if points:
                polylines.append(PolylineEntity(points=points))

    extmin = header.get("$EXTMIN", ["0", "0", "0"])
    extmax = header.get("$EXTMAX", ["0", "0", "0"])
    bbox_raw = {
        "min_x": float(extmin[0]),
        "min_y": float(extmin[1]),
        "max_x": float(extmax[0]),
        "max_y": float(extmax[1]),
    }
    bbox_raw["width"] = bbox_raw["max_x"] - bbox_raw["min_x"]
    bbox_raw["height"] = bbox_raw["max_y"] - bbox_raw["min_y"]
    bbox = bbox_raw if bbox_raw["width"] > 0 or bbox_raw["height"] > 0 else _bbox_from_geometry(lines, circles, polylines)
    unit_code = header.get("$INSUNITS", ["1"])[0]
    unit_scale = UNIT_TO_MM.get(unit_code, INCH_TO_MM)
    unit_note = "millimetres" if unit_scale == 1.0 else "inches"

    return {
        "path": str(source_path),
        "acad_version": header.get("$ACADVER", ["unknown"])[0],
        "unit_note": unit_note,
        "bbox_in": bbox,
        "bbox_mm": {
            "width": round(bbox["width"] * unit_scale, 2),
            "height": round(bbox["height"] * unit_scale, 2),
        },
        "entity_counts": dict(entity_counts),
        "line_entities": [line.__dict__ for line in lines],
        "circle_entities": [circle.__dict__ for circle in circles],
        "polyline_entities": [polyline.__dict__ for polyline in polylines],
        "hole_count_guess": len(circles),
    }


def render_dxf_svg(parsed: dict, title: str, subtitle: str) -> str:
    bbox = parsed["bbox_in"]
    width = max(bbox["width"], 1.0)
    height = max(bbox["height"], 1.0)
    canvas_w = 980
    canvas_h = 380
    pad = 40
    scale = min((canvas_w - pad * 2) / width, (canvas_h - pad * 2) / height)

    def map_x(x: float) -> float:
        return pad + (x - bbox["min_x"]) * scale

    def map_y(y: float) -> float:
        return canvas_h - pad - (y - bbox["min_y"]) * scale

    line_svg = []
    polyline_svg = []
    for polyline in parsed.get("polyline_entities", []):
        points = " ".join(f"{map_x(x):.2f},{map_y(y):.2f}" for x, y in polyline["points"])
        polyline_svg.append(
            f'<polyline points="{points}" fill="none" stroke="#dbe4ef" stroke-width="1.6" />'
        )

    for line in parsed["line_entities"]:
        line_svg.append(
            f'<line x1="{map_x(line["x1"]):.2f}" y1="{map_y(line["y1"]):.2f}" '
            f'x2="{map_x(line["x2"]):.2f}" y2="{map_y(line["y2"]):.2f}" '
            'stroke="#dbe4ef" stroke-width="1.2" />'
        )

    circle_svg = []
    for circle in parsed["circle_entities"]:
        circle_svg.append(
            f'<circle cx="{map_x(circle["cx"]):.2f}" cy="{map_y(circle["cy"]):.2f}" '
            f'r="{circle["radius"] * scale:.2f}" fill="none" stroke="#7dd3fc" stroke-width="1.8" />'
        )

    return f"""
<svg viewBox="0 0 {canvas_w} {canvas_h}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="{canvas_w}" height="{canvas_h}" fill="#11161d" />
  <text x="40" y="36" fill="#eef2f7" font-size="20" font-family="Segoe UI, sans-serif">{title}</text>
  <text x="40" y="64" fill="#a6b0bf" font-size="14" font-family="Segoe UI, sans-serif">{subtitle}</text>
  {''.join(polyline_svg)}
  {''.join(line_svg)}
  {''.join(circle_svg)}
</svg>
""".strip()


def render_dxf_feature_svg(parsed: dict) -> str:
    width_mm = parsed["bbox_mm"]["width"]
    height_mm = parsed["bbox_mm"]["height"]
    circles = parsed["circle_entities"]

    if circles:
        xs = [circle["cx"] for circle in circles]
        ys = [circle["cy"] for circle in circles]
        rs = [circle["radius"] for circle in circles]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        width_in = max(parsed["bbox_in"]["width"], 1.0)
        height_in = max(parsed["bbox_in"]["height"], 1.0)

        def proj_x(x: float) -> float:
            return 170 + (x - parsed["bbox_in"]["min_x"]) / width_in * 520

        def proj_y(y: float) -> float:
            return 280 - (y - parsed["bbox_in"]["min_y"]) / height_in * 120

        circles_svg = "".join(
            f'<circle cx="{proj_x(circle["cx"]):.2f}" cy="{proj_y(circle["cy"]):.2f}" '
            f'r="{max(circle["radius"] / width_in * 520, 4):.2f}" fill="none" stroke="#8bffa8" stroke-width="2.2" />'
            for circle in circles
        )
        hole_note = (
            f"推定穴数 {len(circles)} / 代表半径 {max(rs) * INCH_TO_MM:.2f} mm"
        )
    else:
        circles_svg = ""
        hole_note = "円要素なし"

    return f"""
<svg viewBox="0 0 860 360" xmlns="http://www.w3.org/2000/svg">
  <rect x="120" y="92" width="620" height="180" fill="none" stroke="#e5ecf5" stroke-width="2.2"/>
  <path d="M120 182 H740" stroke="#65707d" stroke-width="1.2" stroke-dasharray="6 5"/>
  {circles_svg}
  <text x="120" y="54" fill="#a6b0bf" font-size="20" font-family="Segoe UI, sans-serif">見積用 feature スケッチ</text>
  <text x="120" y="314" fill="#a6b0bf" font-size="18" font-family="Segoe UI, sans-serif">外形 {width_mm} x {height_mm} mm / {hole_note}</text>
  <text x="120" y="338" fill="#a6b0bf" font-size="14" font-family="Segoe UI, sans-serif">板厚、材質、表面処理は DXF 単独では取れないため仮定が必要</text>
</svg>
""".strip()
