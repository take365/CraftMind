from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "src" / "viewer" / "assets" / "lb001_l_bracket_2d"
SOURCE_DRAWING = ROOT / "src" / "sample_data" / "public_demo_drawings" / "sample_l_bracket_260x120_v1" / "sample_l_bracket_260x120_v1_drawing.png"
SOURCE_REFERENCE = "src/sample_data/public_demo_drawings/sample_l_bracket_260x120_v1/sample_l_bracket_260x120_v1_drawing.png"
SOURCE_IMAGE = OUT_DIR / "source_page.png"

CANVAS_SIZE = (1536, 1024)
LINE = "#17191c"
DIM = "#57606a"
ACCENT_A = "#0ea5e9"
ACCENT_B = "#22c55e"
ACCENT_C = "#f97316"
BG = "white"


@dataclass(frozen=True)
class ViewSpec:
    key: str
    title: str
    subtitle: str
    crop: tuple[int, int, int, int]
    accent: str
    svg: str
    input_panel_label: str = "元図面からの切り出し"
    feature_panel_label: str = "簡易 2D CAD スケッチ"
    comparison_note: str = ""


def load_font(size: int = 24) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/msgothic.ttc",
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                pass
    return ImageFont.load_default()


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: str = LINE,
) -> None:
    draw.text(xy, text, font=font, fill=fill)


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: str = LINE,
) -> None:
    box = draw.textbbox((0, 0), text, font=font)
    x = center[0] - (box[2] - box[0]) / 2
    y = center[1] - (box[3] - box[1]) / 2
    draw.text((x, y), text, font=font, fill=fill)


def arrow_polygon(tip: tuple[float, float], direction: str, size: int = 8) -> list[tuple[float, float]]:
    x, y = tip
    if direction == "left":
        return [(x, y), (x + size, y - size / 2), (x + size, y + size / 2)]
    if direction == "right":
        return [(x, y), (x - size, y - size / 2), (x - size, y + size / 2)]
    if direction == "up":
        return [(x, y), (x - size / 2, y + size), (x + size / 2, y + size)]
    return [(x, y), (x - size / 2, y - size), (x + size / 2, y - size)]


def draw_dimension_h(
    draw: ImageDraw.ImageDraw,
    x0: float,
    x1: float,
    y: float,
    text: str,
    font: ImageFont.ImageFont,
    ext0: float,
    ext1: float,
    fill: str = DIM,
) -> None:
    draw.line((x0, y, x1, y), fill=fill, width=2)
    draw.line((x0, ext0, x0, y), fill=fill, width=2)
    draw.line((x1, ext1, x1, y), fill=fill, width=2)
    draw.polygon(arrow_polygon((x0, y), "right"), fill=fill)
    draw.polygon(arrow_polygon((x1, y), "left"), fill=fill)
    draw_centered_text(draw, (int((x0 + x1) / 2), int(y - 18)), text, font, fill)


def draw_dimension_v(
    draw: ImageDraw.ImageDraw,
    x: float,
    y0: float,
    y1: float,
    text: str,
    font: ImageFont.ImageFont,
    ext0: float,
    ext1: float,
    fill: str = DIM,
) -> None:
    draw.line((x, y0, x, y1), fill=fill, width=2)
    draw.line((ext0, y0, x, y0), fill=fill, width=2)
    draw.line((ext1, y1, x, y1), fill=fill, width=2)
    draw.polygon(arrow_polygon((x, y0), "down"), fill=fill)
    draw.polygon(arrow_polygon((x, y1), "up"), fill=fill)

    label = Image.new("RGBA", (120, 36), (255, 255, 255, 0))
    label_draw = ImageDraw.Draw(label)
    box = label_draw.textbbox((0, 0), text, font=font)
    lx = (120 - (box[2] - box[0])) / 2
    ly = (36 - (box[3] - box[1])) / 2
    label_draw.text((lx, ly), text, font=font, fill=fill)
    rotated = label.rotate(90, expand=True)
    draw.bitmap((x - rotated.width / 2 + 18, (y0 + y1) / 2 - rotated.height / 2), rotated)


def draw_circle(
    draw: ImageDraw.ImageDraw,
    center: tuple[float, float],
    radius: float,
    outline: str = LINE,
    width: int = 3,
    crosshair: bool = True,
) -> None:
    x, y = center
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=outline, width=width)
    if crosshair:
        draw.line((x - radius - 8, y, x + radius + 8, y), fill=DIM, width=1)
        draw.line((x, y - radius - 8, x, y + radius + 8), fill=DIM, width=1)


def dashed_line(
    draw: ImageDraw.ImageDraw,
    start: tuple[float, float],
    end: tuple[float, float],
    dash: int = 10,
    gap: int = 8,
    fill: str = DIM,
    width: int = 2,
) -> None:
    x0, y0 = start
    x1, y1 = end
    dx = x1 - x0
    dy = y1 - y0
    length = (dx * dx + dy * dy) ** 0.5
    if length == 0:
        return
    ux = dx / length
    uy = dy / length
    distance = 0
    while distance < length:
        seg_start = distance
        seg_end = min(distance + dash, length)
        sx = x0 + ux * seg_start
        sy = y0 + uy * seg_start
        ex = x0 + ux * seg_end
        ey = y0 + uy * seg_end
        draw.line((sx, sy, ex, ey), fill=fill, width=width)
        distance += dash + gap


def draw_flat_pattern(draw: ImageDraw.ImageDraw, origin: tuple[int, int]) -> None:
    x, y = origin
    scale = 2.25
    base_top = y + 92
    base_bottom = base_top + 80 * scale
    tab_top = base_top - 40 * scale
    left_tab_x0 = x + 40 * scale
    left_tab_x1 = left_tab_x0 + 90 * scale
    mid_x0 = left_tab_x1
    mid_x1 = mid_x0 + 40 * scale
    right_tab_x0 = mid_x1
    right_tab_x1 = right_tab_x0 + 90 * scale
    end_x = x + 260 * scale

    draw.rectangle((x, base_top, end_x, base_bottom), outline=LINE, width=3)
    draw.rectangle((left_tab_x0, tab_top, left_tab_x1, base_top), outline=LINE, width=3)
    draw.rectangle((right_tab_x0, tab_top, right_tab_x1, base_top), outline=LINE, width=3)

    dashed_line(draw, (x, base_top), (end_x, base_top), fill=DIM)
    for xpos in (left_tab_x0, left_tab_x1, right_tab_x0):
        dashed_line(draw, (xpos, tab_top + 10), (xpos, base_bottom), fill=DIM)

    hole_y = tab_top + 20 * scale
    for hx in (
        left_tab_x0 + 25 * scale,
        left_tab_x0 + 65 * scale,
        right_tab_x0 + 25 * scale,
        right_tab_x0 + 65 * scale,
    ):
        draw_circle(draw, (hx, hole_y), 10 * scale / 2, outline=LINE, width=3)

    for hx in (x + 20 * scale, x + 238 * scale):
        draw_circle(draw, (hx, base_bottom - 20 * scale), 14 * scale / 2, outline=LINE, width=3)

    dim_font = load_font(18)
    draw_dimension_h(draw, x, end_x, tab_top - 62, "260", dim_font, tab_top - 8, tab_top - 8)
    draw_dimension_h(draw, x, left_tab_x0, tab_top - 18, "40", dim_font, tab_top - 8, tab_top - 8)
    draw_dimension_h(draw, left_tab_x0, left_tab_x1, tab_top - 18, "90", dim_font, tab_top - 8, tab_top - 8)
    draw_dimension_h(draw, left_tab_x1, right_tab_x0, tab_top - 18, "40", dim_font, tab_top - 8, tab_top - 8)
    draw_dimension_h(draw, right_tab_x0, right_tab_x1, tab_top - 18, "90", dim_font, tab_top - 8, tab_top - 8)
    draw_dimension_v(draw, x - 70, tab_top, base_bottom, "120", dim_font, x - 10, x - 10)

    note_font = load_font(18)
    draw.line((left_tab_x0 + 68, hole_y + 8, left_tab_x0 + 110, hole_y - 12), fill=LINE, width=2)
    draw.line((left_tab_x0 + 110, hole_y - 12, left_tab_x0 + 178, hole_y - 12), fill=LINE, width=2)
    draw_text(draw, (left_tab_x0 + 118, int(hole_y - 28)), "4-φ10", note_font, LINE)

    left_big = (x + 20 * scale, base_bottom - 20 * scale)
    draw.line((left_big[0] + 10, left_big[1] + 12, left_big[0] + 40, left_big[1] + 28), fill=LINE, width=2)
    draw.line((left_big[0] + 40, left_big[1] + 28, left_big[0] + 112, left_big[1] + 28), fill=LINE, width=2)
    draw_text(draw, (int(left_big[0] + 46), int(left_big[1] + 12)), "2-φ14", note_font, LINE)

    caption_font = load_font(20)
    draw_centered_text(draw, (int((x + end_x) / 2), int(base_bottom + 44)), "展開図（切断形状）", caption_font, LINE)


def draw_front_view(draw: ImageDraw.ImageDraw, origin: tuple[int, int]) -> None:
    x, y = origin
    scale = 1.75
    inner_width = 260 * scale
    leg_height = 40 * scale
    thickness = 6 * scale
    radius = 6 * scale
    left = x
    right = x + inner_width
    top = y
    base_y = y + leg_height

    draw.line((left, top, left, top + leg_height - radius), fill=LINE, width=3)
    draw.arc((left, base_y - 2 * radius, left + 2 * radius, base_y), start=180, end=270, fill=LINE, width=3)
    draw.line((left + radius, base_y, right - radius, base_y), fill=LINE, width=3)
    draw.arc((right - 2 * radius, base_y - 2 * radius, right, base_y), start=270, end=360, fill=LINE, width=3)
    draw.line((right, top, right, top + leg_height - radius), fill=LINE, width=3)

    inset = thickness
    draw.line((left + inset, top, left + inset, top + leg_height - radius), fill=LINE, width=2)
    draw.arc((left + inset, base_y - 2 * radius + inset, left + 2 * radius + inset, base_y + inset), start=180, end=270, fill=LINE, width=2)
    draw.line((left + radius + inset, base_y + inset, right - radius - inset, base_y + inset), fill=LINE, width=2)
    draw.arc((right - 2 * radius - inset, base_y - 2 * radius + inset, right - inset, base_y + inset), start=270, end=360, fill=LINE, width=2)
    draw.line((right - inset, top, right - inset, top + leg_height - radius), fill=LINE, width=2)

    dim_font = load_font(18)
    draw_dimension_h(draw, left, right, top - 54, "260", dim_font, top, top)
    draw_dimension_v(draw, left - 48, top, top + leg_height, "40", dim_font, left, left)
    draw_dimension_v(draw, right + 48, top, top + leg_height, "40", dim_font, right, right)

    note_font = load_font(18)
    draw.line((left + 50, top + 24, left + 28, top + 10), fill=LINE, width=2)
    draw.line((left + 28, top + 10, left + 96, top + 10), fill=LINE, width=2)
    draw_text(draw, (left + 100, top - 8), "R6", note_font, LINE)
    draw.line((right - 50, top + 24, right - 28, top + 10), fill=LINE, width=2)
    draw.line((right - 96, top + 10, right - 28, top + 10), fill=LINE, width=2)
    draw_text(draw, (right - 130, top - 8), "R6", note_font, LINE)

    caption_font = load_font(20)
    draw_centered_text(draw, (int((left + right) / 2), int(base_y + 112)), "正面図", caption_font, LINE)


def draw_side_view(draw: ImageDraw.ImageDraw, origin: tuple[int, int]) -> None:
    x, y = origin
    scale = 2.35
    base_len = 120 * scale
    leg_height = 40 * scale
    thickness = 6 * scale
    radius = 6 * scale

    left = x
    bend_x = x + base_len
    base_y = y + leg_height

    draw.line((left, base_y, bend_x - radius, base_y), fill=LINE, width=3)
    draw.arc((bend_x - 2 * radius, base_y - 2 * radius, bend_x, base_y), start=0, end=90, fill=LINE, width=3)
    draw.line((bend_x, y, bend_x, base_y - radius), fill=LINE, width=3)

    draw.line((left, base_y - thickness, bend_x - radius - thickness, base_y - thickness), fill=LINE, width=2)
    draw.arc((bend_x - 2 * radius - thickness, base_y - 2 * radius - thickness, bend_x - thickness, base_y - thickness), start=0, end=90, fill=LINE, width=2)
    draw.line((bend_x - thickness, y, bend_x - thickness, base_y - radius - thickness), fill=LINE, width=2)

    dim_font = load_font(18)
    draw_dimension_h(draw, left, bend_x, base_y + 84, "120", dim_font, base_y + 8, base_y + 8)
    draw_dimension_h(draw, left, left + 30 * scale, base_y + 48, "30", dim_font, base_y + 8, base_y + 8)
    draw_dimension_h(draw, left + 30 * scale, bend_x, base_y + 48, "90", dim_font, base_y + 8, base_y + 8)
    draw_dimension_v(draw, bend_x + 56, y, y + leg_height, "40", dim_font, bend_x, bend_x)

    note_font = load_font(18)
    draw_dimension_v(draw, left - 54, base_y - thickness, base_y, "t6", dim_font, left, left)
    draw.line((bend_x - 10, base_y - 18, bend_x - 50, base_y - 36), fill=LINE, width=2)
    draw.line((bend_x - 126, base_y - 36, bend_x - 50, base_y - 36), fill=LINE, width=2)
    draw_text(draw, (bend_x - 162, base_y - 54), "R6", note_font, LINE)

    caption_font = load_font(20)
    draw_centered_text(draw, (int((left + bend_x) / 2), int(base_y + 120)), "側面図", caption_font, LINE)


def draw_bend_table(draw: ImageDraw.ImageDraw, origin: tuple[int, int]) -> None:
    x, y = origin
    w = 320
    h = 146
    draw.rectangle((x, y, x + w, y + h), outline=LINE, width=2)
    row_h = 36
    for row in range(1, 4):
        draw.line((x, y + row * row_h, x + w, y + row * row_h), fill=LINE, width=1)
    for xpos in (x + 58, x + 132, x + 202, x + 260):
        draw.line((xpos, y + row_h, xpos, y + h), fill=LINE, width=1)

    font_h = load_font(18)
    font_b = load_font(16)
    draw_text(draw, (x + 14, y + 8), "曲げ条件", font_h)
    headers = [("No.", 18), ("工程", 74), ("角度", 142), ("内R", 214), ("備考", 272)]
    for text, dx in headers:
        draw_text(draw, (x + dx, y + 44), text, font_b)

    rows = [
        ("①", "曲げ", "90°", "R6", "内側"),
        ("②", "曲げ", "90°", "R6", "内側"),
    ]
    for idx, row in enumerate(rows):
        yy = y + 80 + idx * 32
        for text, dx in zip(row, (18, 72, 154, 218, 270)):
            draw_text(draw, (x + dx, yy), text, font_b)


def draw_title_block(draw: ImageDraw.ImageDraw, origin: tuple[int, int]) -> None:
    x, y = origin
    w = 430
    h = 158
    draw.rectangle((x, y, x + w, y + h), outline=LINE, width=2)
    for row in (38, 78, 118):
        draw.line((x, y + row, x + w, y + row), fill=LINE, width=1)
    for col in (110, 240, 350):
        draw.line((x + col, y, x + col, y + h), fill=LINE, width=1)

    font = load_font(18)
    small = load_font(16)
    draw_text(draw, (x + 18, y + 10), "品名", small)
    draw_text(draw, (x + 128, y + 10), "Lブラケット", font)
    draw_text(draw, (x + 256, y + 10), "材質", small)
    draw_text(draw, (x + 366, y + 10), "SS400", font)
    draw_text(draw, (x + 18, y + 48), "図番", small)
    draw_text(draw, (x + 128, y + 48), "LB-001", font)
    draw_text(draw, (x + 256, y + 48), "数量", small)
    draw_text(draw, (x + 382, y + 48), "1", font)
    draw_text(draw, (x + 18, y + 88), "表面処理", small)
    draw_text(draw, (x + 146, y + 88), "-", font)
    draw_text(draw, (x + 256, y + 88), "重量(参考)", small)
    draw_text(draw, (x + 372, y + 88), "-", font)
    draw_text(draw, (x + 18, y + 128), "尺度", small)
    draw_text(draw, (x + 146, y + 128), "1:2", font)
    draw_text(draw, (x + 256, y + 128), "単位", small)
    draw_text(draw, (x + 366, y + 128), "mm", font)


def draw_isometric(draw: ImageDraw.ImageDraw, origin: tuple[int, int]) -> None:
    x, y = origin
    p1 = (x, y + 80)
    p2 = (x + 180, y)
    p3 = (x + 390, y + 120)
    p4 = (x + 210, y + 200)
    p5 = (x + 62, y + 48)
    p6 = (x + 242, y - 32)
    p7 = (x + 454, y + 88)
    p8 = (x + 274, y + 168)

    draw.line((p1, p2, p3, p4, p1), fill=LINE, width=3)
    draw.line((p5, p6, p7, p8, p5), fill=LINE, width=2)

    leg_a = [(x + 86, y + 56), (x + 154, y + 26), (x + 154, y - 68), (x + 86, y - 38), (x + 86, y + 56)]
    leg_b = [(x + 310, y + 150), (x + 378, y + 120), (x + 378, y + 26), (x + 310, y + 56), (x + 310, y + 150)]
    draw.line(leg_a, fill=LINE, width=3)
    draw.line(leg_b, fill=LINE, width=3)
    draw.line(((x + 86, y - 38), (x + 154, y - 68)), fill=LINE, width=2)
    draw.line(((x + 310, y + 56), (x + 378, y + 26)), fill=LINE, width=2)

    for cx, cy in ((x + 108, y - 8), (x + 132, y - 18), (x + 332, y + 86), (x + 356, y + 76)):
        draw.ellipse((cx - 8, cy - 12, cx + 8, cy + 12), outline=LINE, width=2)
    for cx, cy in ((x + 82, y + 126), (x + 248, y + 196)):
        draw.ellipse((cx - 14, cy - 8, cx + 14, cy + 8), outline=LINE, width=2)


def render_source_page() -> Image.Image:
    image = Image.new("RGB", CANVAS_SIZE, BG)
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 16, CANVAS_SIZE[0] - 16, CANVAS_SIZE[1] - 16), outline=LINE, width=2)

    title_font = load_font(28)
    body_font = load_font(18)
    caption_font = load_font(16)

    draw_text(draw, (34, 32), "3. Lブラケット", title_font)
    draw_text(draw, (34, 88), "材質 : SS400", load_font(18))
    draw_text(draw, (34, 124), "板厚 : t = 6", load_font(18))
    draw_text(draw, (24, 190), "※ 指示無き角は R2", body_font)
    draw_text(draw, (24, 224), "※ バリ・カエリ除去", body_font)
    draw_text(draw, (24, 258), "※ 一般公差 ±0.5", body_font)

    draw_flat_pattern(draw, (316, 98))
    draw_isometric(draw, (1086, 208))
    draw_text(draw, (1256, 496), "※イメージ図（NTS）", caption_font)
    draw_front_view(draw, (108, 680))
    draw_side_view(draw, (778, 672))
    draw_bend_table(draw, (1172, 652))
    draw_title_block(draw, (1068, 850))
    return image


def svg_flat_pattern() -> str:
    return """
<svg viewBox="0 0 980 520" xmlns="http://www.w3.org/2000/svg">
  <rect x="120" y="180" width="585" height="180" fill="none" stroke="#e5ecf5" stroke-width="2.4"/>
  <rect x="210" y="90" width="202" height="90" fill="none" stroke="#e5ecf5" stroke-width="2.4"/>
  <rect x="502" y="90" width="203" height="90" fill="none" stroke="#e5ecf5" stroke-width="2.4"/>
  <path d="M120 180 H705" stroke="#6b7280" stroke-width="1.2" stroke-dasharray="7 6"/>
  <path d="M210 100 V360 M412 100 V360 M502 100 V360" stroke="#6b7280" stroke-width="1.2" stroke-dasharray="7 6"/>
  <circle cx="266" cy="135" r="11" fill="none" stroke="#0ea5e9" stroke-width="2.4"/>
  <circle cx="356" cy="135" r="11" fill="none" stroke="#0ea5e9" stroke-width="2.4"/>
  <circle cx="558" cy="135" r="11" fill="none" stroke="#0ea5e9" stroke-width="2.4"/>
  <circle cx="648" cy="135" r="11" fill="none" stroke="#0ea5e9" stroke-width="2.4"/>
  <circle cx="165" cy="315" r="15" fill="none" stroke="#f97316" stroke-width="2.4"/>
  <circle cx="655" cy="315" r="15" fill="none" stroke="#f97316" stroke-width="2.4"/>
  <path d="M120 46 H705 M120 46 V68 M705 46 V68" stroke="#0ea5e9" stroke-width="2.2"/>
  <text x="392" y="34" fill="#94a3b8" font-size="18">260</text>
  <path d="M120 82 H210 M120 82 V96 M210 82 V96" stroke="#22c55e" stroke-width="2"/>
  <path d="M210 82 H412 M412 82 V96 M210 82 V96" stroke="#22c55e" stroke-width="2"/>
  <path d="M412 82 H502 M412 82 V96 M502 82 V96" stroke="#22c55e" stroke-width="2"/>
  <path d="M502 82 H705 M502 82 V96 M705 82 V96" stroke="#22c55e" stroke-width="2"/>
  <text x="152" y="72" fill="#94a3b8" font-size="18">40</text>
  <text x="294" y="72" fill="#94a3b8" font-size="18">90</text>
  <text x="446" y="72" fill="#94a3b8" font-size="18">40</text>
  <text x="586" y="72" fill="#94a3b8" font-size="18">90</text>
      <text x="742" y="130" fill="#94a3b8" font-size="18">4-φ10</text>
      <text x="742" y="320" fill="#94a3b8" font-size="18">2-φ14</text>
      <text x="122" y="408" fill="#94a3b8" font-size="18">見積では 260 x 120 x t6 の展開板を素材寸法として採用</text>
</svg>
""".strip()


def svg_front_view() -> str:
    return """
<svg viewBox="0 0 760 420" xmlns="http://www.w3.org/2000/svg">
  <path d="M130 124 V194 A20 20 0 0 0 150 214 H610 A20 20 0 0 0 630 194 V124" fill="none" stroke="#e5ecf5" stroke-width="2.8"/>
  <path d="M146 124 V192 A10 10 0 0 0 156 202 H604 A10 10 0 0 0 614 192 V124" fill="none" stroke="#cbd5e1" stroke-width="2"/>
  <path d="M130 68 H630 M130 68 V90 M630 68 V90" stroke="#0ea5e9" stroke-width="2.2"/>
  <text x="365" y="54" fill="#94a3b8" font-size="18">260</text>
  <path d="M78 124 V194 M94 124 H78 M94 194 H78" stroke="#22c55e" stroke-width="2"/>
  <path d="M682 124 V194 M666 124 H682 M666 194 H682" stroke="#22c55e" stroke-width="2"/>
  <text x="58" y="164" fill="#94a3b8" font-size="18" transform="rotate(-90 58 164)">40</text>
  <text x="704" y="164" fill="#94a3b8" font-size="18" transform="rotate(-90 704 164)">40</text>
  <text x="188" y="116" fill="#94a3b8" font-size="18">R6</text>
  <text x="512" y="116" fill="#94a3b8" font-size="18">R6</text>
  <text x="172" y="308" fill="#94a3b8" font-size="18">2 箇所の 90° 曲げ後の正面外観を比較確認</text>
</svg>
""".strip()


def svg_side_profile() -> str:
    return """
<svg viewBox="0 0 620 420" xmlns="http://www.w3.org/2000/svg">
  <path d="M120 232 H398 A22 22 0 0 0 420 210 V96" fill="none" stroke="#e5ecf5" stroke-width="2.8"/>
  <path d="M120 218 H384 A10 10 0 0 0 394 208 V96" fill="none" stroke="#cbd5e1" stroke-width="2"/>
  <path d="M120 318 H420 M120 318 V300 M420 318 V300" stroke="#0ea5e9" stroke-width="2.2"/>
  <path d="M120 282 H190 M120 282 V264 M190 282 V264" stroke="#22c55e" stroke-width="2"/>
  <path d="M190 282 H420 M190 282 V264 M420 282 V264" stroke="#22c55e" stroke-width="2"/>
  <path d="M474 96 V190 M458 96 H474 M458 190 H474" stroke="#22c55e" stroke-width="2"/>
  <path d="M76 218 V232 M92 218 H76 M92 232 H76" stroke="#f97316" stroke-width="2"/>
  <text x="248" y="340" fill="#94a3b8" font-size="18">120</text>
  <text x="146" y="264" fill="#94a3b8" font-size="18">30</text>
  <text x="288" y="264" fill="#94a3b8" font-size="18">90</text>
  <text x="492" y="148" fill="#94a3b8" font-size="18" transform="rotate(-90 492 148)">40</text>
  <text x="46" y="230" fill="#94a3b8" font-size="18" transform="rotate(-90 46 230)">t6</text>
  <text x="302" y="198" fill="#94a3b8" font-size="18">R6</text>
  <text x="132" y="376" fill="#94a3b8" font-size="18">底面 120、立上り 40、内 R6 を確認する比較スケッチ</text>
</svg>
""".strip()


def build_views() -> list[ViewSpec]:
    return [
        ViewSpec(
            key="flat_pattern",
            title="展開図",
            subtitle="260 x 120 の切断形状、4-φ10、2-φ14 を確認",
            crop=(190, 70, 980, 590),
            accent=ACCENT_A,
            svg=svg_flat_pattern(),
            comparison_note="添付図面の展開図を基準に、見積では 260 x 120 x t6 の矩形板を素材寸法として扱っています。",
        ),
        ViewSpec(
            key="front_view",
            title="正面図",
            subtitle="完成形の全長 260 と両端 R6 曲げを確認",
            crop=(60, 610, 720, 980),
            accent=ACCENT_B,
            svg=svg_front_view(),
            comparison_note="正面図は 2 箇所の 90 度曲げ後の外観確認用です。耳の孔位置詳細は展開図とイメージ図を優先しています。",
        ),
        ViewSpec(
            key="side_profile",
            title="側面図",
            subtitle="底面 120、立上り 40、板厚 t6 を確認",
            crop=(720, 620, 1128, 944),
            accent=ACCENT_C,
            svg=svg_side_profile(),
            comparison_note="側面図から 30 + 90 の奥行きと R6 内側曲げを確認し、標準曲げ 2 回として工程化しています。",
        ),
    ]


def save_svg(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def draw_label(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    fill: str,
    font: ImageFont.ImageFont,
) -> None:
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=16, outline=fill, width=5)
    box2 = draw.textbbox((0, 0), text, font=font)
    tx = x0 + 14
    ty = max(18, y0 + 10)
    bg = (tx - 8, ty - 6, tx + (box2[2] - box2[0]) + 8, ty + (box2[3] - box2[1]) + 8)
    draw.rounded_rectangle(bg, radius=8, fill="white")
    draw.text((tx, ty), text, fill=fill, font=font)


def make_original_with_boxes(img: Image.Image, views: list[ViewSpec]) -> Image.Image:
    annotated = img.convert("RGB").copy()
    draw = ImageDraw.Draw(annotated)
    font = load_font(24)
    for view in views:
        draw_label(draw, view.crop, view.title, view.accent, font)
    return annotated


def generate() -> dict[str, object]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not SOURCE_DRAWING.exists():
        raise FileNotFoundError(f"source drawing not found: {SOURCE_DRAWING}")

    page = Image.open(SOURCE_DRAWING).convert("RGB")
    page.save(SOURCE_IMAGE)

    views = build_views()
    annotated = make_original_with_boxes(page, views)
    annotated_path = OUT_DIR / "original_annotated.png"
    annotated.save(annotated_path)

    manifest: dict[str, object] = {
        "source_reference": SOURCE_REFERENCE,
        "source_image": "./assets/lb001_l_bracket_2d/source_page.png",
        "original": {
            "path": "./assets/lb001_l_bracket_2d/original_annotated.png",
            "width": annotated.width,
            "height": annotated.height,
        },
        "views": [],
    }

    for view in views:
        crop = page.crop(view.crop)
        crop_path = OUT_DIR / f"{view.key}_crop.png"
        crop.save(crop_path)

        svg_path = OUT_DIR / f"{view.key}_cad.svg"
        save_svg(svg_path, view.svg)

        manifest["views"].append(
            {
                **asdict(view),
                "crop_path": f"./assets/lb001_l_bracket_2d/{view.key}_crop.png",
                "svg_path": f"./assets/lb001_l_bracket_2d/{view.key}_cad.svg",
                "crop_box": list(view.crop),
            }
        )

    manifest_path = OUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    manifest = generate()
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
