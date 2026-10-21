"""Draws a fake app screen with personal data, for the masking demo. Usage: python make-screenshot.py out.png"""
import sys
from PIL import Image, ImageDraw, ImageFont


def font(size):
    for f in ("arial.ttf", "DejaVuSans.ttf", "Arial.ttf"):
        try: return ImageFont.truetype(f, size)
        except OSError: pass
    return ImageFont.load_default()


img = Image.new("RGB", (900, 360), "white")
d = ImageDraw.Draw(img)
d.rectangle([0, 0, 900, 60], fill=(40, 70, 140))
d.text((24, 14), "My Profile", fill="white", font=font(30))
rows = [("Name", "John Smith"), ("Email", "ahmed.harbi@example.com"), ("Mobile", "0551234567"),
        ("National ID", "1012345672"), ("Order", "1012345678")]
for i, (k, v) in enumerate(rows):
    y = 90 + i * 52
    d.text((40, y), k + ":", fill=(90, 90, 90), font=font(26))
    d.text((260, y), v, fill="black", font=font(26))
img.save(sys.argv[1])
