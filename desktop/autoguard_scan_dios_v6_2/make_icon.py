from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
ORANGE = (255, 119, 0, 255)
ORANGE_DARK = (177, 70, 0, 255)
SILVER = (224, 228, 232, 255)
DARK = (5, 7, 9, 255)


def load_font(size: int, bold: bool = True):
    candidates = (
        "arialbd.ttf" if bold else "arial.ttf",
        "segoeuib.ttf" if bold else "segoeui.ttf",
        "calibrib.ttf" if bold else "calibri.ttf",
    )
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def centered_text(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, font, fill, stroke_width: int = 0, stroke_fill=None) -> None:
    left, top, right, bottom = box
    bounds = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    draw.text(
        ((left + right - width) / 2, (top + bottom - height) / 2 - bounds[1]),
        text,
        font=font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )


def gear_points(cx: float, cy: float, outer: float, root: float, teeth: int = 12) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    steps = teeth * 4
    for index in range(steps):
        phase = index % 4
        radius = outer if phase in {1, 2} else root
        angle = -math.pi / 2 + index * (2 * math.pi / steps)
        points.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    return points


def draw_gear(draw: ImageDraw.ImageDraw, cx: int, cy: int, outer: int, root: int, hole: int) -> None:
    points = gear_points(cx, cy, outer, root)
    draw.polygon(points, fill=ORANGE, outline=(255, 183, 77, 255))
    draw.ellipse((cx - root + 12, cy - root + 12, cx + root - 12, cy + root - 12), fill=ORANGE_DARK, outline=(255, 167, 55, 255), width=7)
    draw.ellipse((cx - hole, cy - hole, cx + hole, cy + hole), fill=(8, 10, 12, 255), outline=(203, 207, 211, 255), width=8)
    draw.ellipse((cx - hole + 17, cy - hole + 17, cx + hole - 17, cy + hole - 17), fill=(2, 4, 6, 255), outline=(61, 65, 70, 255), width=5)


def draw_metal_plaque(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = box
    bevel = 28
    polygon = [
        (left + bevel, top),
        (right - bevel, top),
        (right, top + bevel),
        (right - 22, bottom - bevel),
        (right - 48, bottom),
        (left + 48, bottom),
        (left + 22, bottom - bevel),
        (left, top + bevel),
    ]
    draw.polygon(polygon, fill=(6, 8, 10, 255), outline=(180, 185, 190, 255))
    inner = [(x, y + 8 if y == top else y - 8 if y == bottom else y) for x, y in polygon]
    draw.line(inner + [inner[0]], fill=(50, 55, 61, 255), width=5)
    draw.line((left + 42, top + 12, right - 42, top + 12), fill=(233, 236, 239, 255), width=3)
    draw.line((left + 60, bottom - 13, right - 60, bottom - 13), fill=(55, 58, 62, 255), width=3)


def create_rectangular_logo() -> Image.Image:
    width, height = 1420, 790
    base = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    # Subtle workshop-like background without distracting from the mark.
    bg = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bg)
    for index in range(18):
        alpha = max(0, 42 - index * 2)
        bg_draw.ellipse((760 - index * 18, 60 - index * 8, 1510 + index * 20, 790 + index * 18), fill=(93, 55, 22, alpha))
    bg = bg.filter(ImageFilter.GaussianBlur(28))
    base.alpha_composite(bg)
    draw = ImageDraw.Draw(base)

    draw_gear(draw, 710, 350, 330, 257, 152)
    draw_metal_plaque(draw, (56, 190, 1364, 482))

    auto_font = load_font(205, True)
    guard_font = load_font(205, True)
    service_font = load_font(96, True)
    tagline_font = load_font(43, False)

    # Split AUTO / GUARD to preserve the official white-orange identity.
    auto_box = (90, 208, 705, 432)
    guard_box = (650, 208, 1325, 432)
    centered_text(draw, auto_box, "AUTO", auto_font, SILVER, 4, (18, 20, 22, 255))
    centered_text(draw, guard_box, "GUARD", guard_font, ORANGE, 4, (55, 23, 0, 255))
    centered_text(draw, (340, 445, 1080, 585), "S E R V I C E", service_font, SILVER, 3, (10, 12, 14, 255))
    centered_text(draw, (255, 625, 1165, 715), "TU VEHÍCULO, NUESTRA PRIORIDAD", tagline_font, ORANGE, 2, (30, 12, 0, 255))

    # Thin premium frame and orange lower accent.
    draw.rounded_rectangle((8, 8, width - 9, height - 9), radius=24, outline=(82, 89, 96, 255), width=4)
    draw.line((290, 740, 1130, 740), fill=ORANGE_DARK, width=4)
    return base


def create_square_icon(rectangular: Image.Image) -> Image.Image:
    size = 1024
    icon = Image.new("RGBA", (size, size), (3, 5, 7, 255))
    draw = ImageDraw.Draw(icon)
    draw_gear(draw, 512, 445, 405, 320, 175)
    draw_metal_plaque(draw, (64, 300, 960, 610))
    centered_text(draw, (100, 320, 505, 530), "AUTO", load_font(135, True), SILVER, 3, (14, 16, 18, 255))
    centered_text(draw, (465, 320, 925, 530), "GUARD", load_font(135, True), ORANGE, 3, (55, 22, 0, 255))
    centered_text(draw, (210, 580, 814, 705), "SERVICE", load_font(76, True), SILVER, 2, (8, 10, 12, 255))
    centered_text(draw, (120, 820, 904, 905), "SCAN DIOS", load_font(62, True), ORANGE, 2, (35, 14, 0, 255))
    draw.rounded_rectangle((18, 18, size - 19, size - 19), radius=80, outline=(120, 127, 134, 255), width=8)
    return icon


def main() -> None:
    rectangular = create_rectangular_logo()
    rectangular.save(ROOT / "autoguard.png", optimize=True)
    icon = create_square_icon(rectangular)
    icon.save(ROOT / "autoguard_icon.png", optimize=True)
    icon.save(
        ROOT / "autoguard.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("Branding AUTO GUARD SERVICE e icono de escritorio generados")


if __name__ == "__main__":
    main()
