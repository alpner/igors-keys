"""Draws the tray/program icon (a keycap with an "I") into igorskeys/icon.ico."""
import os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))


def draw(size):
    # drawn 4x larger and scaled down, so the small sizes stay smooth
    big = size * 4
    im = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = big / 64.0
    # keycap: dark base, lighter top face
    d.rounded_rectangle([3 * s, 5 * s, 61 * s, 61 * s], radius=10 * s, fill=(38, 70, 120, 255))
    d.rounded_rectangle([9 * s, 7 * s, 55 * s, 51 * s], radius=8 * s, fill=(74, 128, 200, 255))
    # the letter I (serif style, built from rectangles so no font is needed)
    white = (255, 255, 255, 255)
    d.rectangle([28 * s, 16 * s, 36 * s, 42 * s], fill=white)
    d.rectangle([22 * s, 14 * s, 42 * s, 19 * s], fill=white)
    d.rectangle([22 * s, 39 * s, 42 * s, 44 * s], fill=white)
    return im.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [draw(n) for n in sizes]
    out = os.path.join(HERE, "igorskeys", "icon.ico")
    images[-1].save(out, format="ICO", sizes=[(n, n) for n in sizes], append_images=images[:-1])
    print("wrote", out)
