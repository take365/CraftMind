from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = ROOT / "public_demo_parts"


@dataclass
class Circle2D:
    cx: float
    cy: float
    radius: float
    layer: str = "HOLES"


@dataclass
class Line2D:
    start: tuple[float, float]
    end: tuple[float, float]
    layer: str = "DETAIL"


@dataclass
class Circle3D:
    center: tuple[float, float, float]
    radius: float
    normal: tuple[float, float, float]
    refdir: tuple[float, float, float]


@dataclass
class PartSpec:
    key: str
    name_ja: str
    category: str
    description_ja: str
    material: str
    surface_treatment: str
    heat_treatment: str
    process_summary_ja: str
    dimensions_mm: dict[str, float]
    dxf_outline: list[tuple[float, float]]
    dxf_circles: list[Circle2D]
    dxf_lines: list[Line2D]
    step_segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]]
    step_circles: list[Circle3D]
    notes_ja: list[str] = field(default_factory=list)


def fmt(value: float) -> str:
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text if text else "0"


def closed_box_segments(length: float, width: float, height: float) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
    p000 = (0.0, 0.0, 0.0)
    p100 = (length, 0.0, 0.0)
    p110 = (length, width, 0.0)
    p010 = (0.0, width, 0.0)
    p001 = (0.0, 0.0, height)
    p101 = (length, 0.0, height)
    p111 = (length, width, height)
    p011 = (0.0, width, height)
    return [
        (p000, p100),
        (p100, p110),
        (p110, p010),
        (p010, p000),
        (p001, p101),
        (p101, p111),
        (p111, p011),
        (p011, p001),
        (p000, p001),
        (p100, p101),
        (p110, p111),
        (p010, p011),
    ]


def render_dxf(spec: PartSpec) -> str:
    lines: list[str] = [
        "0",
        "SECTION",
        "2",
        "HEADER",
        "9",
        "$ACADVER",
        "1",
        "AC1015",
        "9",
        "$INSUNITS",
        "70",
        "4",
        "0",
        "ENDSEC",
        "0",
        "SECTION",
        "2",
        "ENTITIES",
    ]

    lines.extend(
        [
            "0",
            "LWPOLYLINE",
            "8",
            "OUTLINE",
            "90",
            str(len(spec.dxf_outline)),
            "70",
            "1",
        ]
    )
    for x, y in spec.dxf_outline:
        lines.extend(["10", fmt(x), "20", fmt(y)])

    for circle in spec.dxf_circles:
        lines.extend(
            [
                "0",
                "CIRCLE",
                "8",
                circle.layer,
                "10",
                fmt(circle.cx),
                "20",
                fmt(circle.cy),
                "30",
                "0",
                "40",
                fmt(circle.radius),
            ]
        )

    for detail in spec.dxf_lines:
        lines.extend(
            [
                "0",
                "LINE",
                "8",
                detail.layer,
                "10",
                fmt(detail.start[0]),
                "20",
                fmt(detail.start[1]),
                "30",
                "0",
                "11",
                fmt(detail.end[0]),
                "21",
                fmt(detail.end[1]),
                "31",
                "0",
            ]
        )

    lines.extend(["0", "ENDSEC", "0", "EOF"])
    return "\n".join(lines) + "\n"


def render_step(spec: PartSpec) -> str:
    ids: list[str] = []
    entity_id = 100

    def next_id() -> int:
        nonlocal entity_id
        entity_id += 1
        return entity_id

    def add(line: str) -> int:
        idx = next_id()
        ids.append(f"#{idx}={line};")
        return idx

    def cartesian_point(point: tuple[float, float, float]) -> int:
        return add(
            f"CARTESIAN_POINT('',({fmt(point[0])},{fmt(point[1])},{fmt(point[2])}))"
        )

    def direction(vector: tuple[float, float, float]) -> int:
        return add(
            f"DIRECTION('',({fmt(vector[0])},{fmt(vector[1])},{fmt(vector[2])}))"
        )

    curve_ids: list[int] = []

    for start, end in spec.step_segments:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dz = end[2] - start[2]
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length == 0:
            continue
        start_id = cartesian_point(start)
        dir_id = direction((dx / length, dy / length, dz / length))
        vec_id = add(f"VECTOR('',#{dir_id},{fmt(length)})")
        line_id = add(f"LINE('',#{start_id},#{vec_id})")
        curve_ids.append(line_id)

    for circle in spec.step_circles:
        center_id = cartesian_point(circle.center)
        normal_id = direction(circle.normal)
        refdir_id = direction(circle.refdir)
        axis_id = add(f"AXIS2_PLACEMENT_3D('',#{center_id},#{normal_id},#{refdir_id})")
        circle_id = add(f"CIRCLE('',#{axis_id},{fmt(circle.radius)})")
        curve_ids.append(circle_id)

    curve_refs = ",".join(f"#{curve_id}" for curve_id in curve_ids)
    curve_set_id = add(f"GEOMETRIC_CURVE_SET('',({curve_refs}))")

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    header = f"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('Synthetic public demo sample'),'2;1');
FILE_NAME('{spec.key}.step','{generated_at}',('OpenAI Codex'),('OpenAI Codex'),'CraftMind synthetic sample','','');
FILE_SCHEMA(('CONFIG_CONTROL_DESIGN'));
ENDSEC;
DATA;
#1=APPLICATION_CONTEXT('configuration controlled 3d designs of mechanical parts');
#2=MECHANICAL_CONTEXT('',#1,'mechanical');
#3=PRODUCT('{spec.key}','{spec.name_ja}','',(#2));
#4=PRODUCT_DEFINITION_FORMATION('1','',#3);
#5=PRODUCT_DEFINITION_CONTEXT('part definition',#1,'design');
#6=PRODUCT_DEFINITION('definition','',#4,#5);
#7=PRODUCT_DEFINITION_SHAPE('','',#6);
#8=(LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.));
#9=(NAMED_UNIT(*) PLANE_ANGLE_UNIT() SI_UNIT($,.RADIAN.));
#10=(NAMED_UNIT(*) SOLID_ANGLE_UNIT() SI_UNIT($,.STERADIAN.));
#11=UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-6),#8,'distance_accuracy_value','confusion accuracy');
#12=(GEOMETRIC_REPRESENTATION_CONTEXT(3) GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#11)) GLOBAL_UNIT_ASSIGNED_CONTEXT((#8,#9,#10)) REPRESENTATION_CONTEXT('Context #1','3D Context'));
"""
    footer = f"""
#{curve_set_id + 1}=SHAPE_REPRESENTATION('{spec.name_ja}',(#{curve_set_id}),#12);
#{curve_set_id + 2}=SHAPE_DEFINITION_REPRESENTATION(#7,#{curve_set_id + 1});
ENDSEC;
END-ISO-10303-21;
"""
    return header + "\n".join(ids) + footer


def write_part(spec: PartSpec) -> dict:
    part_dir = OUTPUT_ROOT / spec.key
    part_dir.mkdir(parents=True, exist_ok=True)

    dxf_name = f"{spec.key}.dxf"
    step_name = f"{spec.key}.step"
    notes_name = "notes_ja.md"
    spec_name = "part_spec.json"

    (part_dir / dxf_name).write_text(render_dxf(spec), encoding="utf-8")
    (part_dir / step_name).write_text(render_step(spec), encoding="utf-8")

    notes_lines = [
        f"# {spec.name_ja}",
        "",
        f"- カテゴリ: {spec.category}",
        f"- 材質: {spec.material}",
        f"- 表面処理: {spec.surface_treatment}",
        f"- 熱処理: {spec.heat_treatment}",
        f"- 想定工程: {spec.process_summary_ja}",
        "",
        "## メモ",
    ]
    notes_lines.extend(f"- {line}" for line in spec.notes_ja)
    (part_dir / notes_name).write_text("\n".join(notes_lines) + "\n", encoding="utf-8")

    spec_payload = {
        "key": spec.key,
        "name_ja": spec.name_ja,
        "category": spec.category,
        "description_ja": spec.description_ja,
        "authoring_note": "Self-authored synthetic sample for public-safe demos.",
        "material": spec.material,
        "surface_treatment": spec.surface_treatment,
        "heat_treatment": spec.heat_treatment,
        "process_summary_ja": spec.process_summary_ja,
        "dimensions_mm": spec.dimensions_mm,
        "files": {
            "dxf": dxf_name,
            "step": step_name,
            "notes": notes_name,
        },
    }
    (part_dir / spec_name).write_text(
        json.dumps(spec_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return spec_payload


def part_specs() -> list[PartSpec]:
    public_plate = PartSpec(
        key="sample_plate_grid_300x200_v1",
        name_ja="サンプルベースプレート 300x200",
        category="plate",
        description_ja="300 x 200 の板に 15-φ10 を 5 x 3 配列した公開向けサンプル。",
        material="SS400",
        surface_treatment="なし",
        heat_treatment="なし",
        process_summary_ja="レーザー切断 -> 15-φ10 穴加工 -> バリ取り",
        dimensions_mm={"length": 300.0, "width": 200.0, "thickness": 12.0},
        dxf_outline=[(0, 0), (300, 0), (300, 200), (0, 200)],
        dxf_circles=[
            Circle2D(40, 40, 5), Circle2D(95, 40, 5), Circle2D(150, 40, 5), Circle2D(205, 40, 5), Circle2D(260, 40, 5),
            Circle2D(40, 100, 5), Circle2D(95, 100, 5), Circle2D(150, 100, 5), Circle2D(205, 100, 5), Circle2D(260, 100, 5),
            Circle2D(40, 160, 5), Circle2D(95, 160, 5), Circle2D(150, 160, 5), Circle2D(205, 160, 5), Circle2D(260, 160, 5),
        ],
        dxf_lines=[
            Line2D((40, 20), (40, 180), "CENTER"),
            Line2D((95, 20), (95, 180), "CENTER"),
            Line2D((150, 20), (150, 180), "CENTER"),
            Line2D((205, 20), (205, 180), "CENTER"),
            Line2D((260, 20), (260, 180), "CENTER"),
            Line2D((20, 40), (280, 40), "CENTER"),
            Line2D((20, 100), (280, 100), "CENTER"),
            Line2D((20, 160), (280, 160), "CENTER"),
        ],
        step_segments=closed_box_segments(300, 200, 12),
        step_circles=[
            Circle3D((40, 40, 12), 5, (0, 0, 1), (1, 0, 0)),
            Circle3D((95, 40, 12), 5, (0, 0, 1), (1, 0, 0)),
            Circle3D((150, 40, 12), 5, (0, 0, 1), (1, 0, 0)),
            Circle3D((205, 40, 12), 5, (0, 0, 1), (1, 0, 0)),
            Circle3D((260, 40, 12), 5, (0, 0, 1), (1, 0, 0)),
            Circle3D((40, 100, 12), 5, (0, 0, 1), (1, 0, 0)),
            Circle3D((95, 100, 12), 5, (0, 0, 1), (1, 0, 0)),
            Circle3D((150, 100, 12), 5, (0, 0, 1), (1, 0, 0)),
            Circle3D((205, 100, 12), 5, (0, 0, 1), (1, 0, 0)),
            Circle3D((260, 100, 12), 5, (0, 0, 1), (1, 0, 0)),
            Circle3D((40, 160, 12), 5, (0, 0, 1), (1, 0, 0)),
            Circle3D((95, 160, 12), 5, (0, 0, 1), (1, 0, 0)),
            Circle3D((150, 160, 12), 5, (0, 0, 1), (1, 0, 0)),
            Circle3D((205, 160, 12), 5, (0, 0, 1), (1, 0, 0)),
            Circle3D((260, 160, 12), 5, (0, 0, 1), (1, 0, 0)),
        ],
        notes_ja=[
            "ChatGPT で作成したベースプレート図面に合わせた公開向けサンプルです。",
            "2D CAD は平面穴配列をそのまま表現し、STEP は同寸法の板厚付きワイヤーフレームです。",
            "図面画像、DXF、STEP を同一寸法でそろえているため、公開デモの差し替え元として使いやすい構成です。",
        ],
    )

    base_plate = PartSpec(
        key="sample_base_plate_a",
        name_ja="サンプルベースプレート A",
        category="plate",
        description_ja="4-φ14 の取り付け穴を持つ矩形プレート。公開用デモの基本形状。",
        material="SS400",
        surface_treatment="三価クロメート白",
        heat_treatment="なし",
        process_summary_ja="レーザー切断 -> 穴加工 -> 表面処理",
        dimensions_mm={"length": 220.0, "width": 140.0, "thickness": 12.0},
        dxf_outline=[(0, 0), (220, 0), (220, 140), (0, 140)],
        dxf_circles=[
            Circle2D(35, 35, 7),
            Circle2D(185, 35, 7),
            Circle2D(35, 105, 7),
            Circle2D(185, 105, 7),
        ],
        dxf_lines=[
            Line2D((110, 20), (110, 120), "CENTER"),
            Line2D((20, 70), (200, 70), "CENTER"),
        ],
        step_segments=closed_box_segments(220, 140, 12),
        step_circles=[
            Circle3D((35, 35, 12), 7, (0, 0, 1), (1, 0, 0)),
            Circle3D((185, 35, 12), 7, (0, 0, 1), (1, 0, 0)),
            Circle3D((35, 105, 12), 7, (0, 0, 1), (1, 0, 0)),
            Circle3D((185, 105, 12), 7, (0, 0, 1), (1, 0, 0)),
        ],
        notes_ja=[
            "2D CAD は外形と穴位置の確認用レイアウトです。",
            "STEP は同一寸法の簡易ワイヤーフレーム表現です。",
            "図面画像を別途生成する場合は、この寸法セットを基準にしてください。",
        ],
    )

    guide_block = PartSpec(
        key="sample_guide_block_b",
        name_ja="サンプルガイドブロック B",
        category="machined_block",
        description_ja="中央φ32の貫通穴と 4-φ8 取り付け穴を持つ加工ブロック。",
        material="A5052",
        surface_treatment="白アルマイト",
        heat_treatment="なし",
        process_summary_ja="切削 -> 穴加工 -> 面取り -> 表面処理",
        dimensions_mm={"length": 120.0, "width": 70.0, "height": 45.0},
        dxf_outline=[(0, 0), (120, 0), (120, 70), (0, 70)],
        dxf_circles=[
            Circle2D(60, 35, 16),
            Circle2D(20, 20, 4),
            Circle2D(100, 20, 4),
            Circle2D(20, 50, 4),
            Circle2D(100, 50, 4),
        ],
        dxf_lines=[
            Line2D((60, 5), (60, 65), "CENTER"),
            Line2D((5, 35), (115, 35), "CENTER"),
        ],
        step_segments=closed_box_segments(120, 70, 45),
        step_circles=[
            Circle3D((60, 35, 45), 16, (0, 0, 1), (1, 0, 0)),
            Circle3D((20, 0, 22.5), 4, (0, -1, 0), (1, 0, 0)),
            Circle3D((100, 0, 22.5), 4, (0, -1, 0), (1, 0, 0)),
            Circle3D((20, 70, 22.5), 4, (0, 1, 0), (1, 0, 0)),
            Circle3D((100, 70, 22.5), 4, (0, 1, 0), (1, 0, 0)),
        ],
        notes_ja=[
            "中心穴の周りに対称な取り付け穴を持つ標準的な加工ブロック想定です。",
            "2D CAD は上面基準、STEP は外形と主要穴だけを示すワイヤーフレームです。",
            "熱処理なしで、表面処理は白アルマイトの仮設定です。",
        ],
    )

    bracket_segments = closed_box_segments(100, 60, 6) + [
        ((0, 0, 6), (6, 0, 6)),
        ((6, 0, 6), (6, 60, 6)),
        ((6, 60, 6), (0, 60, 6)),
        ((0, 0, 76), (6, 0, 76)),
        ((6, 0, 76), (6, 60, 76)),
        ((6, 60, 76), (0, 60, 76)),
        ((0, 0, 6), (0, 0, 76)),
        ((6, 0, 6), (6, 0, 76)),
        ((6, 60, 6), (6, 60, 76)),
        ((0, 60, 6), (0, 60, 76)),
    ]
    sensor_bracket = PartSpec(
        key="sample_sensor_bracket_c",
        name_ja="サンプルセンサーブラケット C",
        category="sheet_metal_bracket",
        description_ja="曲げ 1 回を想定した L 字ブラケット。ベース側 2-φ9、立ち上がり側 2-φ6。",
        material="SPHC",
        surface_treatment="四三酸化鉄被膜（黒染め）",
        heat_treatment="なし",
        process_summary_ja="レーザー切断 -> 曲げ 1 回 -> 穴加工 -> 黒染め",
        dimensions_mm={"flat_length": 160.0, "width": 60.0, "thickness": 6.0, "formed_height": 76.0},
        dxf_outline=[(0, 0), (160, 0), (160, 60), (0, 60)],
        dxf_circles=[
            Circle2D(100, 15, 4.5),
            Circle2D(100, 45, 4.5),
            Circle2D(30, 15, 3),
            Circle2D(30, 45, 3),
        ],
        dxf_lines=[
            Line2D((60, 0), (60, 60), "BEND"),
            Line2D((0, 30), (160, 30), "CENTER"),
        ],
        step_segments=bracket_segments,
        step_circles=[
            Circle3D((70, 15, 6), 4.5, (0, 0, 1), (1, 0, 0)),
            Circle3D((70, 45, 6), 4.5, (0, 0, 1), (1, 0, 0)),
            Circle3D((6, 15, 40), 3, (1, 0, 0), (0, 1, 0)),
            Circle3D((6, 45, 40), 3, (1, 0, 0), (0, 1, 0)),
        ],
        notes_ja=[
            "2D CAD は板金の展開イメージです。BEND レイヤーの 1 本線を曲げ位置として使います。",
            "STEP は折り曲げ後の L 字形状を簡易ワイヤーフレームで表現しています。",
            "図面画像を作る場合は、2D は展開図、3D は完成形という構成で使い分けできます。",
        ],
    )

    return [public_plate, base_plate, guide_block, sensor_bracket]


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    catalog = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kind": "synthetic_public_demo_inputs",
        "parts": [write_part(spec) for spec in part_specs()],
    }
    (OUTPUT_ROOT / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
