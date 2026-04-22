from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


PART_KEY = "public_sample_plate_grid_300x200_v1_drawing_only"
VIEWER_ASSET_DIR = ROOT / "src" / "viewer" / "assets" / PART_KEY
DRAWING_DIR = ROOT / "src" / "sample_data" / "public_demo_drawings" / "sample_plate_grid_300x200_v1"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def render_summary_svg(spec: dict) -> str:
    dims = spec["dimensions_mm"]
    hole = spec["hole_pattern"]
    notes = spec.get("notes_ja", [])
    note_lines = "".join(
        f'<text x="62" y="{286 + i * 26}" fill="#a6b0bf" font-size="16" font-family="Segoe UI, sans-serif">- {note}</text>'
        for i, note in enumerate(notes)
    )
    return f"""
<svg viewBox="0 0 980 420" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="980" height="420" fill="#11161d" />
  <text x="42" y="42" fill="#eef2f7" font-size="24" font-family="Segoe UI, sans-serif">図面読取結果の要約</text>
  <text x="42" y="78" fill="#a6b0bf" font-size="16" font-family="Segoe UI, sans-serif">画像入力から固定できた見積条件を整理</text>

  <rect x="42" y="108" width="420" height="120" rx="18" fill="#171d26" stroke="#314155" />
  <text x="62" y="144" fill="#7dd3fc" font-size="15" font-family="Segoe UI, sans-serif">BASIC</text>
  <text x="62" y="178" fill="#eef2f7" font-size="18" font-family="Segoe UI, sans-serif">材質: {spec["material"]}</text>
  <text x="62" y="208" fill="#eef2f7" font-size="18" font-family="Segoe UI, sans-serif">板厚: t{dims["thickness"]}</text>
  <text x="62" y="238" fill="#eef2f7" font-size="18" font-family="Segoe UI, sans-serif">外形: {dims["length"]} x {dims["width"]} mm</text>

  <rect x="504" y="108" width="434" height="120" rx="18" fill="#171d26" stroke="#314155" />
  <text x="524" y="144" fill="#8bffa8" font-size="15" font-family="Segoe UI, sans-serif">HOLE PATTERN</text>
  <text x="524" y="178" fill="#eef2f7" font-size="18" font-family="Segoe UI, sans-serif">{hole["count"]}-φ{hole["diameter_mm"]} 貫通穴</text>
  <text x="524" y="208" fill="#eef2f7" font-size="18" font-family="Segoe UI, sans-serif">{hole["grid_columns"]} 列 x {hole["grid_rows"]} 段</text>
  <text x="524" y="238" fill="#eef2f7" font-size="16" font-family="Segoe UI, sans-serif">X: 40 / 55 / 55 / 55 / 55 / 40</text>
  <text x="524" y="262" fill="#eef2f7" font-size="16" font-family="Segoe UI, sans-serif">Y: 40 / 60 / 60 / 40</text>

  <rect x="42" y="254" width="896" height="116" rx="18" fill="#171d26" stroke="#314155" />
  <text x="62" y="286" fill="#f7b955" font-size="15" font-family="Segoe UI, sans-serif">NOTES</text>
  {note_lines}
  <text x="524" y="286" fill="#a6b0bf" font-size="16" font-family="Segoe UI, sans-serif">表面処理: 図面記載なし</text>
  <text x="524" y="312" fill="#a6b0bf" font-size="16" font-family="Segoe UI, sans-serif">熱処理: なし</text>
  <text x="524" y="338" fill="#a6b0bf" font-size="16" font-family="Segoe UI, sans-serif">概算工程: プレート抜き 1 / 通し穴 15</text>
</svg>
""".strip()


def main() -> None:
    VIEWER_ASSET_DIR.mkdir(parents=True, exist_ok=True)

    drawing_spec = json.loads((DRAWING_DIR / "drawing_spec.json").read_text(encoding="utf-8"))
    drawing_png = DRAWING_DIR / drawing_spec["recommended_filename"]
    if not drawing_png.exists():
        raise FileNotFoundError(f"drawing image not found: {drawing_png}")

    shutil.copy2(drawing_png, VIEWER_ASSET_DIR / "drawing.png")
    write_text(VIEWER_ASSET_DIR / "drawing_summary.svg", render_summary_svg(drawing_spec))

    dims = drawing_spec["dimensions_mm"]
    hole = drawing_spec["hole_pattern"]

    analysis = {
        "title": "図面画像単体入力デモ",
        "subtitle": "自作図面画像だけを入力として概算見積までつなぐ構成",
        "summary_cards": [
            {"label": "入力形式", "value": "PNG", "note": "自作図面画像のみ"},
            {
                "label": "外形",
                "value": f'{dims["length"]} x {dims["width"]} x {dims["thickness"]} mm',
                "note": "図面記載から読取",
            },
            {
                "label": "穴構成",
                "value": f'{hole["count"]}-φ{hole["diameter_mm"]}',
                "note": f'{hole["grid_columns"]} 列 x {hole["grid_rows"]} 段の配列',
            },
            {
                "label": "見積分類",
                "value": "板金プレート",
                "note": "画像読取から平板抜き + 穴加工として概算",
            },
        ],
        "sections": [
            {
                "title": "入力ソース",
                "items": [
                    f"図面画像: {drawing_png.name}",
                    "入力は図面画像のみ",
                    "2D CAD / 3D CAD は今回は未使用",
                ],
            },
            {
                "title": "図面から固定した条件",
                "items": [
                    "材質: SS400",
                    "板厚: t12",
                    "外形: 300 x 200",
                    "穴: 15-φ10 貫通穴",
                    "備考: 角部 C1 / バリ・カエリ除去",
                ],
            },
            {
                "title": "見積へ使う読取結果",
                "items": [
                    "プレート抜き: 1 点",
                    "通し穴: 15 箇所",
                    "表面処理: 図面記載なしのため なし扱い",
                    "熱処理: なし",
                ],
            },
        ],
    }
    write_json(VIEWER_ASSET_DIR / "analysis.json", analysis)

    estimate = {
        "part_key": PART_KEY,
        "part_name": "図面画像単体入力デモ / ベースプレート 300x200",
        "drawing_reference": str(drawing_png.relative_to(ROOT)),
        "quantity": 1,
        "service_family": "sheet_metal",
        "service_family_label": "板金プレート",
        "process_mode": "estimated",
        "process_note": "図面画像から読めた外形、材質、板厚、15-φ10 をもとに概算しています。",
        "stock_dimensions_mm": {
            "length": dims["length"],
            "width": dims["width"],
            "height": dims["thickness"],
        },
        "material": {
            "mode": "drawing_spec",
            "code": drawing_spec["material"],
            "note": "材質 SS400 は図面記載を採用しています。",
        },
        "surface_treatment": {
            "mode": "fallback_none",
            "id": "surf_none",
            "note": "図面に表面処理指示がないため、なし扱いです。",
        },
        "heat_treatment": {
            "mode": "drawing_spec",
            "id": "heat_none",
            "note": "熱処理はなしとして扱っています。",
        },
        "process_plan": [
            {
                "id": "proc_sheet_flat_blank",
                "count": 1,
                "note": "300 x 200 x t12 のプレートブランクとして計上。",
            },
            {
                "id": "proc_sheet_hole_round",
                "count": hole["count"],
                "note": f'{hole["count"]}-φ{hole["diameter_mm"]} を通し穴として計上。',
            },
        ],
        "assumptions": [
            "入力は図面画像のみで、寸法と穴数は図面記載から固定しています。",
            "表面処理は図面記載なしのため、なし扱いです。",
            "角部 C1 とバリ取りは工程注意として扱い、今回は追加単価にしていません。",
        ],
        "warnings": [
            "このページは図面画像単体入力のデモです。正式見積には使えません。",
            "OCR 精度、加工可能条件、数量割引、詳細工数は考慮していません。",
        ],
    }
    write_json(VIEWER_ASSET_DIR / "estimate_input.json", estimate)

    manifest = {
        "source_file": str(drawing_png.relative_to(ROOT)),
        "views": [
            {
                "key": "drawing_only",
                "title": "図面画像と読取要約",
                "subtitle": "図面画像単体入力から、見積用の条件整理まで",
                "crop_path": f"./assets/{PART_KEY}/drawing.png",
                "svg_path": f"./assets/{PART_KEY}/drawing_summary.svg",
                "input_panel_label": "図面画像入力",
                "feature_panel_label": "読取結果の要約",
                "comparison_note": "左は入力図面画像、右はそこから見積に使う条件を整理した要約です。",
            }
        ],
    }
    write_json(VIEWER_ASSET_DIR / "manifest.json", manifest)

    print(json.dumps({"part_key": PART_KEY}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
