from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cad.minimal_dxf import parse_dxf, render_dxf_feature_svg, render_dxf_svg


PART_KEY = "cad_input_dxf_guide_block_b"
OUT_DIR = ROOT / "src" / "viewer" / "assets" / PART_KEY
PART_DIR = ROOT / "src" / "sample_data" / "public_demo_parts" / "sample_guide_block_b"
SOURCE_DXF = PART_DIR / "sample_guide_block_b.dxf"
PART_SPEC_PATH = PART_DIR / "part_spec.json"
NOTES_PATH = PART_DIR / "notes_ja.md"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def hole_summary(parsed: dict) -> tuple[int, int, float, float]:
    circles = parsed.get("circle_entities", [])
    if not circles:
        return (0, 0, 0.0, 0.0)

    radii = sorted(circle["radius"] for circle in circles)
    largest = radii[-1] * 2
    small = radii[0] * 2
    large_count = sum(1 for radius in radii if abs(radius * 2 - largest) < 1e-6)
    small_count = len(radii) - large_count
    return (large_count, small_count, largest, small)


def main() -> None:
    if not SOURCE_DXF.exists():
        raise FileNotFoundError(f"dxf not found: {SOURCE_DXF}")
    if not PART_SPEC_PATH.exists():
        raise FileNotFoundError(f"part spec not found: {PART_SPEC_PATH}")
    if not NOTES_PATH.exists():
        raise FileNotFoundError(f"notes not found: {NOTES_PATH}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    part_spec = json.loads(PART_SPEC_PATH.read_text(encoding="utf-8"))
    notes_text = NOTES_PATH.read_text(encoding="utf-8")
    parsed = parse_dxf(SOURCE_DXF)
    dims = part_spec["dimensions_mm"]
    large_count, small_count, large_dia, small_dia = hole_summary(parsed)

    write_text(
        OUT_DIR / "source_render.svg",
        render_dxf_svg(
            parsed,
            "入力 DXF レンダリング",
            "sample_guide_block_b.dxf から上面外形と穴構成を簡易描画",
        ),
    )
    write_text(OUT_DIR / "feature_sketch.svg", render_dxf_feature_svg(parsed))

    analysis = {
        "title": "CAD入力デモ",
        "subtitle": "sample_guide_block_b.dxf + part_spec.json + notes_ja.md からの仮見積",
        "summary_cards": [
            {"label": "入力形式", "value": "DXF + メタ情報", "note": "STEP は未使用"},
            {
                "label": "外形",
                "value": f'{dims["length"]} x {dims["width"]} x {dims["height"]} mm',
                "note": "part_spec.json の寸法を採用",
            },
            {
                "label": "穴構成",
                "value": f'中心 φ{large_dia:.0f} x {large_count} / 取付 φ{small_dia:.0f} x {small_count}',
                "note": f'DXF 円要素 {parsed["hole_count_guess"]} 個を集計',
            },
            {"label": "見積分類", "value": "切削部品", "note": "machined_block として仮見積"},
        ],
        "sections": [
            {
                "title": "入力ソース",
                "items": [
                    f"DXF: {SOURCE_DXF.relative_to(ROOT)}",
                    f"仕様: {PART_SPEC_PATH.relative_to(ROOT)}",
                    f"メモ: {NOTES_PATH.relative_to(ROOT)}",
                    "STEP は今回のデモでは使用しない",
                ],
            },
            {
                "title": "抽出メトリクス",
                "items": [
                    f'DXF bbox: {parsed["bbox_mm"]["width"]} x {parsed["bbox_mm"]["height"]} mm',
                    f'円要素: {parsed["entity_counts"].get("CIRCLE", 0)}',
                    f'中心穴候補: φ{large_dia:.0f} x {large_count}',
                    f'取付穴候補: φ{small_dia:.0f} x {small_count}',
                ],
            },
            {
                "title": "見積仮定",
                "items": [
                    f'材質: {part_spec["material"]}',
                    f'表面処理: {part_spec["surface_treatment"]}',
                    f'熱処理: {part_spec["heat_treatment"]}',
                    f'想定工程: {part_spec["process_summary_ja"]}',
                ],
            },
            {
                "title": "notes_ja.md 要約",
                "items": [
                    line.removeprefix("- ").strip()
                    for line in notes_text.splitlines()
                    if line.startswith("- ")
                ],
            },
        ],
    }
    write_json(OUT_DIR / "analysis.json", analysis)

    estimate = {
        "part_key": PART_KEY,
        "part_name": "CAD入力デモ DXF / サンプルガイドブロック B",
        "drawing_reference": str(SOURCE_DXF.relative_to(ROOT)),
        "quantity": 1,
        "service_family": "machining",
        "service_family_label": "切削部品",
        "process_mode": "estimated",
        "process_note": "DXF の外形と円要素を上面形状として読み、part_spec.json の寸法・材質・処理条件を使って切削部品へ分類しています。",
        "stock_dimensions_mm": {
            "length": dims["length"],
            "width": dims["width"],
            "height": dims["height"],
        },
        "material": {
            "mode": "user_specified",
            "code": part_spec["material"],
            "note": "材質 A5052 は part_spec.json 記載を採用しています。",
        },
        "surface_treatment": {
            "mode": "user_specified",
            "id": "surf_anodize_white",
            "note": "表面処理は notes_ja.md / part_spec.json の白アルマイトを、デモ用マスター上の アルマイト（白） に対応付けています。",
        },
        "heat_treatment": {
            "mode": "drawing_spec",
            "id": "heat_none",
            "note": "熱処理なしは part_spec.json 記載を採用しています。",
        },
        "process_plan": [
            {
                "id": "proc_machining_profile",
                "count": 1,
                "note": "120 x 70 x 45 のブロック外形加工として計上。",
            },
            {
                "id": "proc_machining_through_hole",
                "count": parsed["hole_count_guess"],
                "note": f'中心 φ{large_dia:.0f} x {large_count} と取付 φ{small_dia:.0f} x {small_count} を通し穴として合算計上。',
            },
        ],
        "assumptions": [
            "DXF は上面基準の 2D 形状として扱い、厚み 45 mm は part_spec.json の値を採用しています。",
            "DXF の円要素 5 個はすべて穴として扱い、中心の大径穴と四隅取付穴に分けて解釈しています。",
            "想定工程の面取りは notes_ja.md にあるものの、デモ用工程マスターに独立費目がないため工程費へ含めています。",
            "価格はデモ用マスターに基づく概算であり、正式見積の単価体系とは一致しません。",
        ],
        "warnings": [
            "この見積は DXF と付随メタ情報から作ったデモ用概算です。正式見積には使えません。",
            "DXF 単独では厚みや材質は分からないため、part_spec.json への依存があります。",
            "中心 φ32 穴の公差、面粗さ、面取り量、取付穴精度はこのデモでは反映していません。",
        ],
    }
    write_json(OUT_DIR / "estimate_input.json", estimate)

    manifest = {
        "source_file": str(SOURCE_DXF.relative_to(ROOT)),
        "views": [
            {
                "key": "dxf_main",
                "title": "DXF 入力レンダリング",
                "subtitle": "上面外形と 5 穴構成を簡易描画",
                "crop_path": f"./assets/{PART_KEY}/source_render.svg",
                "svg_path": f"./assets/{PART_KEY}/feature_sketch.svg",
                "input_panel_label": "入力 CAD プレビュー",
                "feature_panel_label": "見積用 feature スケッチ",
                "comparison_note": "左は DXF からの簡易レンダリング、右は見積で使う外形と穴構成の要約です。",
            }
        ],
    }
    write_json(OUT_DIR / "manifest.json", manifest)

    print(json.dumps({"part_key": PART_KEY}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
