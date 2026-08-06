from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent


def load_font(size: int):
    for name in ("arialbd.ttf", "segoeuib.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> None:
    size = 1024
    image = Image.new("RGBA", (size, size), (8, 12, 17, 255))
    draw = ImageDraw.Draw(image)
    # Metallic outer halo.
    draw.ellipse((58, 58, 966, 966), fill=(18, 25, 34, 255), outline=(123, 135, 148, 255), width=24)
    draw.ellipse((92, 92, 932, 932), fill=(9, 14, 20, 255), outline=(255, 122, 0, 255), width=28)
    # Shield.
    shield = [(512, 116), (832, 232), (790, 650), (512, 900), (234, 650), (192, 232)]
    draw.polygon(shield, fill=(30, 39, 50, 255), outline=(255, 122, 0, 255), width=30)
    draw.line([(512, 150), (512, 840)], fill=(98, 110, 124, 255), width=8)
    # Professional vehicle silhouette.
    draw.rounded_rectangle((270, 438, 754, 648), radius=76, fill=(255, 122, 0, 255), outline=(245, 248, 250, 255), width=16)
    draw.polygon([(338, 438), (424, 318), (602, 318), (686, 438)], fill=(255, 122, 0, 255), outline=(245, 248, 250, 255))
    draw.polygon([(430, 350), (594, 350), (650, 430), (374, 430)], fill=(13, 22, 31, 255))
    draw.ellipse((320, 590, 430, 700), fill=(8, 12, 17, 255), outline=(240, 244, 248, 255), width=14)
    draw.ellipse((594, 590, 704, 700), fill=(8, 12, 17, 255), outline=(240, 244, 248, 255), width=14)
    draw.ellipse((360, 505, 410, 535), fill=(255, 225, 96, 255))
    draw.ellipse((614, 505, 664, 535), fill=(255, 225, 96, 255))
    # Letter A and scan pulse.
    font = load_font(170)
    text = "A"
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text(((size - (bbox[2] - bbox[0])) / 2, 130), text, font=font, fill=(255, 255, 255, 255))
    draw.line([(270, 760), (370, 760), (410, 705), (460, 810), (520, 690), (575, 760), (754, 760)], fill=(255, 122, 0, 255), width=16, joint="curve")
    image.save(ROOT / "autoguard.png")
    image.save(
        ROOT / "autoguard.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("Logo HD naranja AUTOGUARD generado")


if __name__ == "__main__":
    main()
