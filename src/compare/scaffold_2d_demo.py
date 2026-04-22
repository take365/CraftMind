from __future__ import annotations

import argparse
import json
from pathlib import Path
from string import Template


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = ROOT / "src" / "templates" / "2d_auto_quote_demo"
WORKFLOW_DIR = ROOT / "src" / "workflow"
DEFAULT_DRAWING_REFERENCE = "meviy_quotation_examples/pdfs/REPLACE_ME.pdf"


def load_template(name: str) -> Template:
    return Template((TEMPLATE_DIR / name).read_text(encoding="utf-8"))


def write_text(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
      raise FileExistsError(f"already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json_template(path: Path, template_name: str, context: dict[str, str], force: bool) -> None:
    rendered = load_template(template_name).substitute(context)
    payload = json.loads(rendered)
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n", force)


def write_text_template(path: Path, template_name: str, context: dict[str, str], force: bool) -> None:
    rendered = load_template(template_name).substitute(context)
    write_text(path, rendered.rstrip() + "\n", force)


def copy_workflow_template(src_name: str, dst_name: str, force: bool) -> None:
    src_path = WORKFLOW_DIR / src_name
    dst_path = WORKFLOW_DIR / dst_name
    if dst_path.exists() and not force:
        raise FileExistsError(f"already exists: {dst_path}")
    dst_path.write_text(src_path.read_text(encoding="utf-8"), encoding="utf-8")


def service_label_for(service_family: str) -> str:
    mapping = {
        "sheet_metal": "板金部品",
        "machining": "切削部品",
        "turning": "旋盤部品",
    }
    return mapping.get(service_family, service_family)


def insert_demo_card(index_path: Path, product_name: str, asset_key: str, summary: str) -> bool:
    href = f"./demos/{asset_key}.html"
    html = index_path.read_text(encoding="utf-8")
    if href in html:
        return False

    card = f"""
        <section class="view-card">
          <div class="section-head">
            <div>
              <h2>{product_name}</h2>
              <p class="subline">2D 図面比較 + 自動概算見積</p>
            </div>
            <span class="chip">概算 準備中</span>
          </div>
          <p class="note">{summary}</p>
          <p class="note"><a href="{href}">demos/{asset_key}.html</a></p>
        </section>
"""

    marker = "      </div>\n    </section>\n  </main>"
    if marker not in html:
        raise RuntimeError("failed to find insertion point in src/viewer/index.html")

    updated = html.replace(marker, card + "      </div>\n    </section>\n  </main>", 1)
    index_path.write_text(updated, encoding="utf-8")
    return True


def insert_after_last_matching_line(path: Path, line_to_insert: str, prefix: str) -> bool:
    content = path.read_text(encoding="utf-8")
    if line_to_insert in content:
        return False

    lines = content.splitlines()
    insert_at = None
    for i, line in enumerate(lines):
        if line.startswith(prefix):
            insert_at = i + 1

    if insert_at is None:
        lines.append(line_to_insert)
    else:
        lines.insert(insert_at, line_to_insert)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold a new 2D auto quote demo.")
    parser.add_argument("part_key", help="図面を識別するスネークケースの part_key")
    parser.add_argument("--product-name", required=True, help="表示用の製品名")
    parser.add_argument("--drawing-reference", default=DEFAULT_DRAWING_REFERENCE, help="ROOT からの図面相対パス")
    parser.add_argument("--service-family", default="machining", choices=["machining", "sheet_metal", "turning"], help="見積のサービス分類")
    parser.add_argument("--service-family-label", default="", help="表示用のサービス分類ラベル")
    parser.add_argument("--summary", default="TODO: 対象部品の材質、加工、見積要点を更新してください。", help="index 用の部品要約")
    parser.add_argument("--skip-register", action="store_true", help="index / README への登録を行わない")
    parser.add_argument("--force", action="store_true", help="既存ファイルを上書きする")
    args = parser.parse_args()

    part_key = args.part_key
    asset_key = f"{part_key}_2d"
    service_family_label = args.service_family_label or service_label_for(args.service_family)

    context = {
        "part_key": part_key,
        "asset_key": asset_key,
        "product_name": args.product_name,
        "drawing_reference": args.drawing_reference,
        "service_family": args.service_family,
        "service_family_label": service_family_label,
    }

    compare_path = ROOT / "src" / "compare" / f"{asset_key}.py"
    demo_path = ROOT / "src" / "viewer" / "demos" / f"{asset_key}.html"
    asset_dir = ROOT / "src" / "viewer" / "assets" / asset_key
    estimate_path = asset_dir / "estimate_input.json"
    manifest_path = asset_dir / "manifest.json"

    created: list[str] = []

    write_text_template(compare_path, "compare_script.py.tmpl", context, args.force)
    created.append(str(compare_path.relative_to(ROOT)))

    write_text_template(demo_path, "demo_page.html.tmpl", context, args.force)
    created.append(str(demo_path.relative_to(ROOT)))

    write_json_template(estimate_path, "estimate_input.json.tmpl", context, args.force)
    created.append(str(estimate_path.relative_to(ROOT)))

    write_json_template(manifest_path, "manifest.json.tmpl", context, args.force)
    created.append(str(manifest_path.relative_to(ROOT)))

    workflow_pairs = [
        ("intake_template.md", f"{part_key}_intake.md"),
        ("dimension_table_template.md", f"{part_key}_dimension_table.md"),
        ("process_plan_template.md", f"{part_key}_process_plan.md"),
        ("validation_template.md", f"{part_key}_validation.md"),
        ("final_summary_template.md", f"{part_key}_final_summary.md"),
    ]
    for src_name, dst_name in workflow_pairs:
        copy_workflow_template(src_name, dst_name, args.force)
        created.append(str((WORKFLOW_DIR / dst_name).relative_to(ROOT)))

    if not args.skip_register:
        insert_demo_card(
            ROOT / "src" / "viewer" / "index.html",
            args.product_name,
            asset_key,
            args.summary,
        )
        insert_after_last_matching_line(
            ROOT / "src" / "README.md",
            f"http://localhost:8000/demos/{asset_key}.html",
            "http://localhost:8000/demos/",
        )
        insert_after_last_matching_line(
            ROOT / "src" / "README.md",
            f"python src/compare/{asset_key}.py",
            "python src/compare/",
        )
        insert_after_last_matching_line(
            ROOT / "src" / "viewer" / "README.md",
            f"- `http://localhost:8000/demos/{asset_key}.html`",
            "- `http://localhost:8000/demos/",
        )

    print("created:")
    for item in created:
        print(f"  - {item}")

    if args.skip_register:
        print("registration: skipped")
    else:
        print("registration: index and README updated")

    print("next steps:")
    print(f"  1. Edit src/compare/{asset_key}.py with the real PDF path and crop ranges.")
    print(f"  2. Fill src/viewer/assets/{asset_key}/estimate_input.json.")
    print(f"  3. Run: python src/compare/{asset_key}.py")
    print(f"  4. Open: http://localhost:8000/demos/{asset_key}.html")


if __name__ == "__main__":
    main()
