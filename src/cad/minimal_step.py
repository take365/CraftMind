from __future__ import annotations

import re
from pathlib import Path


METRE_TO_MM = 1000.0
UNIT_SCALE_TO_MM = {
    "$": 1000.0,
    ".MILLI.": 1.0,
    ".CENTI.": 10.0,
    ".DECI.": 100.0,
    ".KILO.": 1_000_000.0,
}


def detect_length_unit_scale_to_mm(text: str) -> tuple[float, str]:
    match = re.search(r"SI_UNIT\(([^,]+),\s*\.METRE\.\)", text)
    if not match:
        return METRE_TO_MM, "metre"

    prefix = match.group(1).strip()
    scale = UNIT_SCALE_TO_MM.get(prefix, METRE_TO_MM)
    note = "millimetre" if prefix == ".MILLI." else "metre"
    return scale, note


def parse_step(path: str | Path) -> dict:
    source_path = Path(path)
    text = source_path.read_text(encoding="utf-8", errors="ignore")
    scale_to_mm, unit_note = detect_length_unit_scale_to_mm(text)
    entity_map = {
        int(match.group(1)): match.group(2)
        for match in re.finditer(r"#(\d+)\s*=\s*(.+?);", text, re.DOTALL)
    }

    points = [
        tuple(float(match.group(i)) for i in range(1, 4))
        for match in re.finditer(
            r"CARTESIAN_POINT\([^\)]*\(\s*([\-0-9.E+]+)\s*,\s*([\-0-9.E+]+)\s*,\s*([\-0-9.E+]+)\s*\)\)",
            text,
        )
    ]
    if not points:
        raise ValueError(f"no CARTESIAN_POINT found in {source_path}")

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    zs = [point[2] for point in points]

    radii_m = [
        float(match.group(1))
        for match in re.finditer(r"CIRCLE\([^,]*,[^,]*,([\-0-9.E+]+)\)", text)
    ]
    circle_entities = []
    for entity_id, entity in entity_map.items():
        circle_match = re.match(r"CIRCLE\('',#(\d+),([\-0-9.E+]+)\)", entity)
        if not circle_match:
            continue
        axis_id = int(circle_match.group(1))
        radius_m = float(circle_match.group(2))
        axis = entity_map.get(axis_id, "")
        axis_match = re.match(r"AXIS2_PLACEMENT_3D\('',#(\d+),#(\d+),#(\d+)\)", axis)
        if not axis_match:
            continue
        point_id = int(axis_match.group(1))
        point_entity = entity_map.get(point_id, "")
        point_match = re.match(
            r"CARTESIAN_POINT\('',\(\s*([\-0-9.E+]+)\s*,\s*([\-0-9.E+]+)\s*,\s*([\-0-9.E+]+)\s*\)\)",
            point_entity,
        )
        if not point_match:
            continue
        circle_entities.append(
            {
                "center_mm": {
                    "x": round(float(point_match.group(1)) * scale_to_mm, 3),
                    "y": round(float(point_match.group(2)) * scale_to_mm, 3),
                    "z": round(float(point_match.group(3)) * scale_to_mm, 3),
                },
                "radius_mm": round(radius_m * scale_to_mm, 3),
            }
        )
    face_count = text.count("ADVANCED_FACE")
    edge_count = text.count("EDGE_CURVE")
    cylindrical_surface_count = text.count("CYLINDRICAL_SURFACE")
    solid_count = text.count("MANIFOLD_SOLID_BREP")

    bbox_m = {
        "min_x": min(xs),
        "max_x": max(xs),
        "min_y": min(ys),
        "max_y": max(ys),
        "min_z": min(zs),
        "max_z": max(zs),
    }
    bbox_mm = {
        "length": round((bbox_m["max_x"] - bbox_m["min_x"]) * scale_to_mm, 2),
        "width": round((bbox_m["max_y"] - bbox_m["min_y"]) * scale_to_mm, 2),
        "height": round((bbox_m["max_z"] - bbox_m["min_z"]) * scale_to_mm, 2),
    }

    return {
        "path": str(source_path),
        "unit_note": unit_note,
        "bbox_mm": bbox_mm,
        "point_count": len(points),
        "face_count": face_count,
        "edge_count": edge_count,
        "cylindrical_surface_count": cylindrical_surface_count,
        "solid_count": solid_count,
        "circle_radii_mm": [round(radius * scale_to_mm, 3) for radius in radii_m],
        "circle_entities": circle_entities,
        "hole_count_guess": cylindrical_surface_count,
    }


def render_step_projection_svg(parsed: dict) -> str:
    length = parsed["bbox_mm"]["length"]
    width = parsed["bbox_mm"]["width"]
    circles = parsed.get("circle_entities", [])
    canvas_w = 920
    canvas_h = 360
    pad = 70
    body_scale = min((canvas_w - pad * 2) / max(length, 1), (canvas_h - 120) / max(width, 1))
    body_w = length * body_scale
    body_h = width * body_scale
    body_x = (canvas_w - body_w) / 2
    body_y = 170 - body_h / 2

    def map_x(x_mm: float) -> float:
        return body_x + x_mm * body_scale

    def map_y(y_mm: float) -> float:
        return body_y + body_h - y_mm * body_scale

    circle_svg = []
    for circle in circles:
        circle_svg.append(
            f'<circle cx="{map_x(circle["center_mm"]["x"]):.2f}" cy="{map_y(circle["center_mm"]["y"]):.2f}" '
            f'r="{circle["radius_mm"] * body_scale:.2f}" fill="none" stroke="#7dd3fc" stroke-width="2.2" />'
        )

    return f"""
<svg viewBox="0 0 {canvas_w} {canvas_h}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="{canvas_w}" height="{canvas_h}" fill="#11161d" />
  <rect x="{body_x:.2f}" y="{body_y:.2f}" width="{body_w:.2f}" height="{body_h:.2f}" fill="none" stroke="#e5ecf5" stroke-width="2.4"/>
  {''.join(circle_svg)}
  <path d="M{body_x:.2f} 300 H{body_x + body_w:.2f}" stroke="#8bffa8" stroke-width="2.2"/>
  <path d="M{body_x:.2f} 300 V318" stroke="#8bffa8" stroke-width="2.2"/>
  <path d="M{body_x + body_w:.2f} 300 V318" stroke="#8bffa8" stroke-width="2.2"/>
  <text x="{body_x + body_w / 2 - 28:.2f}" y="292" fill="#a6b0bf" font-size="18" font-family="Segoe UI, sans-serif">{length} mm</text>
  <text x="40" y="36" fill="#eef2f7" font-size="20" font-family="Segoe UI, sans-serif">入力 STEP からの投影プレビュー</text>
  <text x="40" y="64" fill="#a6b0bf" font-size="14" font-family="Segoe UI, sans-serif">bbox と CIRCLE 軸情報から上面投影を簡易描画</text>
</svg>
""".strip()


def render_step_feature_svg(parsed: dict) -> str:
    length = parsed["bbox_mm"]["length"]
    width = parsed["bbox_mm"]["width"]
    height = parsed["bbox_mm"]["height"]
    radii = parsed["circle_radii_mm"]
    hole_d = round(radii[0] * 2, 2) if radii else 0

    return f"""
<svg viewBox="0 0 860 360" xmlns="http://www.w3.org/2000/svg">
  <path d="M180 116 H520 V240 H180 Z" fill="none" stroke="#e5ecf5" stroke-width="2.2"/>
  <circle cx="350" cy="178" r="50" fill="none" stroke="#8bffa8" stroke-width="2.2"/>
  <path d="M560 116 V240" stroke="#7dd3fc" stroke-width="2.2"/>
  <path d="M548 116 H560" stroke="#7dd3fc" stroke-width="2.2"/>
  <path d="M548 240 H560" stroke="#7dd3fc" stroke-width="2.2"/>
  <text x="584" y="188" fill="#a6b0bf" font-size="18" font-family="Segoe UI, sans-serif" transform="rotate(-90 584 188)">{width} mm</text>
  <text x="180" y="64" fill="#a6b0bf" font-size="20" font-family="Segoe UI, sans-serif">見積用 feature スケッチ</text>
  <text x="180" y="296" fill="#a6b0bf" font-size="18" font-family="Segoe UI, sans-serif">外形 {length} x {width} x {height} mm / 推定穴径 {hole_d} mm</text>
  <text x="180" y="322" fill="#a6b0bf" font-size="14" font-family="Segoe UI, sans-serif">材質や処理は STEP 単独では取れないため仮定が必要</text>
</svg>
""".strip()
