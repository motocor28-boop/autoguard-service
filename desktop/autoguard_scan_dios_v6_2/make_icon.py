from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent


def main() -> None:
    size = 512
    image = Image.new("RGBA", (size, size), (12, 17, 24, 255))
    draw = ImageDraw.Draw(image)
    # Shield.
    shield = [(256, 34), (438, 102), (414, 330), (256, 474), (98, 330), (74, 102)]
    draw.polygon(shield, fill=(35, 43, 55, 255), outline=(230, 6, 0, 255), width=22)
    draw.line([(256, 64), (256, 438)], fill=(105, 115, 128, 255), width=5)
    # Stylized vehicle silhouette.
    draw.rounded_rectangle((116, 214, 396, 340), radius=48, fill=(225, 6, 0, 255), outline=(255, 255, 255, 255), width=10)
    draw.polygon([(158, 214), (207, 145), (312, 145), (365, 214)], fill=(225, 6, 0, 255), outline=(255, 255, 255, 255))
    draw.polygon([(211, 164), (302, 164), (337, 211), (179, 211)], fill=(20, 31, 43, 255))
    draw.ellipse((146, 302, 214, 370), fill=(12, 17, 24, 255), outline=(235, 240, 245, 255), width=9)
    draw.ellipse((298, 302, 366, 370), fill=(12, 17, 24, 255), outline=(235, 240, 245, 255), width=9)
    draw.ellipse((170, 254, 205, 274), fill=(255, 220, 70, 255))
    draw.ellipse((307, 254, 342, 274), fill=(255, 220, 70, 255))
    # Letter A.
    try:
        font = ImageFont.truetype("arialbd.ttf", 92)
    except OSError:
        font = ImageFont.load_default()
    text = "A"
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text(((size - (bbox[2] - bbox[0])) / 2, 53), text, font=font, fill=(255, 255, 255, 255))
    image.save(ROOT / "autoguard.png")
    image.save(
        ROOT / "autoguard.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("Icono AUTOGUARD generado")


if __name__ == "__main__":
    main()
