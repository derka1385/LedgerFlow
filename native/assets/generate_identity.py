"""Code-native LF monogram, Ledger Grid identity: the forest tile is a selected cell, the mint square is the fill handle.
PNGs are local source assets (web, iOS, Mac). Same geometry as frontend/src/Brand.tsx."""
from pathlib import Path
from PIL import Image, ImageDraw, PngImagePlugin

root = Path(__file__).resolve().parents[2]
out = root / "frontend/public/icons"
S = 1024
FOREST, MINT, F_TINT, LINE = "#0B5A45", "#8FE3B8", "#BFEBD3", (255, 255, 255, 18)


def draw_icon(size: int) -> Image.Image:
    k = size / 64
    img = Image.new("RGBA", (size, size), FOREST)
    grid = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    g = ImageDraw.Draw(grid)
    step = size / 8
    for i in range(1, 8):  # the sheet the cell lives in
        g.line([(i * step, 0), (i * step, size)], fill=LINE, width=max(1, round(size / 512)))
        g.line([(0, i * step), (size, i * step)], fill=LINE, width=max(1, round(size / 512)))
    img = Image.alpha_composite(img, grid)
    d = ImageDraw.Draw(img)
    sx = 0.66  # letters sit inside the cell with air around them
    ox, oy = 32 - 32.5 * sx, 32 - 31.5 * sx

    def pt(x, y):
        return ((ox + x * sx) * k, (oy + y * sx) * k)
    d.polygon([pt(*p) for p in [(16, 14), (24, 14), (24, 41), (34, 41), (34, 49), (16, 49)]], fill="#FFFFFF")
    d.polygon([pt(*p) for p in [(32, 14), (49, 14), (49, 22), (40, 22), (40, 29), (47, 29), (47, 37), (40, 37), (40, 49), (32, 49)]], fill=F_TINT)
    # selection rectangle around the letters, with the fill handle
    x0, y0, x1, y1 = 14.5 * k, 13.8 * k, 49.5 * k, 50.2 * k
    d.rounded_rectangle([x0, y0, x1, y1], radius=1.2 * k, outline=MINT, width=max(2, round(1.6 * k)))
    h = 6.2 * k
    d.rounded_rectangle([x1 - h / 2, y1 - h / 2, x1 + h / 2, y1 + h / 2], radius=0.9 * k, fill=MINT, outline=FOREST, width=max(2, round(1.3 * k)))
    return img


meta = PngImagePlugin.PngInfo()
meta.add_text("Origin", "LedgerFlow Ledger Grid monogram, drawn by native/assets/generate_identity.py (code-native, no external artwork). Outlined wordmark retained.")
icon = draw_icon(S)
for name, px in [("app-icon-1024.png", 1024), ("icon-512.png", 512), ("icon-192.png", 192), ("apple-touch-icon.png", 180), ("maskable-512.png", 512)]:
    icon.convert("RGB").resize((px, px), Image.Resampling.LANCZOS).save(out / name, pnginfo=meta)
mask = Image.new("L", (S, S))
ImageDraw.Draw(mask).rounded_rectangle((32, 32, 992, 992), radius=217, fill=255)
mac = icon.copy()
mac.putalpha(mask)
mac.save(out / "mac-icon-1024.png", pnginfo=meta)
print("Generated Ledger Grid LF icon sources.")
