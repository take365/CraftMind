from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import cadquery as cq
from cadquery import exporters


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT.parent / "meviy_quotation_examples" / "pdfs"
OUT_DIR = ROOT / "viewer" / "assets" / "hem_clip"


@dataclass(frozen=True)
class HemClipSpec:
    part_name: str = "Inspection Clip"
    material: str = "SUS304-2B"
    thickness_mm: float = 0.5
    length_mm: float = 70.0
    width_mm: float = 30.0
    hole_diameter_mm: float = 4.0
    hole_spacing_mm: float = 20.0
    hole_offset_y_mm: float = 0.0
    flange_length_mm: float = 12.0
    hem_return_mm: float = 6.0
    bend_angle_deg: float = 90.0
    corner_radius_mm: float = 3.0
    source_pdf: str = ""


def resolve_source_pdf() -> Path:
    matches = sorted(SOURCE_DIR.glob("009_12213_*.pdf"))
    if not matches:
        raise FileNotFoundError(f"no source PDF found under {SOURCE_DIR}")
    return matches[0]


def flat_blank(spec: HemClipSpec) -> cq.Workplane:
    blank = cq.Workplane("XY").box(spec.length_mm, spec.width_mm, spec.thickness_mm, centered=(True, True, False))
    x = spec.hole_spacing_mm / 2.0
    blank = blank.faces(">Z").workplane().pushPoints([(-x, spec.hole_offset_y_mm), (x, spec.hole_offset_y_mm)]).hole(
        spec.hole_diameter_mm
    )
    return blank


def add_bent_flange(blank: cq.Workplane, spec: HemClipSpec) -> cq.Workplane:
    flange = (
        cq.Workplane("XY")
        .box(spec.flange_length_mm, spec.width_mm, spec.thickness_mm, centered=(False, True, False))
        .rotate((0, 0, 0), (0, 1, 0), 90)
        .translate((spec.length_mm / 2.0, 0.0, spec.thickness_mm))
    )
    return blank.union(flange)


def add_hem_return(bent: cq.Workplane, spec: HemClipSpec) -> cq.Workplane:
    return_strip = (
        cq.Workplane("XY")
        .box(spec.hem_return_mm, spec.width_mm * 0.85, spec.thickness_mm, centered=(False, True, False))
        .rotate((0, 0, 0), (0, 1, 0), 90)
        .translate((spec.length_mm / 2.0 + spec.thickness_mm, 0.0, spec.thickness_mm + spec.flange_length_mm - spec.thickness_mm))
    )
    return bent.union(return_strip)


def make_models(spec: HemClipSpec) -> dict[str, cq.Workplane]:
    flat = flat_blank(spec)
    bent = add_bent_flange(flat, spec)
    hemmed = add_hem_return(bent, spec)
    return {"flat": flat, "bent": bent, "hemmed": hemmed}


def export_models(spec: HemClipSpec, output_dir: Path = OUT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    models = make_models(spec)
    source_pdf = resolve_source_pdf()

    manifest = {
        "part": {
            **asdict(spec),
            "source_pdf": str(source_pdf),
        },
        "stages": [],
    }

    labels = {
        "flat": "Flat blank",
        "bent": "After first bend",
        "hemmed": "After hem bend",
    }

    for stage_name, model in models.items():
        stage_dir = output_dir / stage_name
        stage_dir.mkdir(parents=True, exist_ok=True)

        stl_path = stage_dir / f"{stage_name}.stl"
        step_path = stage_dir / f"{stage_name}.step"
        export_step = os.environ.get("EXPORT_STEP", "0") == "1"

        exporters.export(model, str(stl_path))
        if export_step:
            exporters.export(model, str(step_path))

        manifest["stages"].append(
            {
                "name": stage_name,
                "label": labels[stage_name],
                "stl": f"./assets/hem_clip/{stage_name}/{stage_name}.stl",
                "step": f"./assets/hem_clip/{stage_name}/{stage_name}.step" if export_step else None,
            }
        )

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def main() -> None:
    manifest_path = export_models(HemClipSpec(source_pdf=str(resolve_source_pdf())))
    print(f"wrote {manifest_path}")


if __name__ == "__main__":
    main()
