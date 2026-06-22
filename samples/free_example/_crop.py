"""Crop figures and tables from FREE source.pdf using caption-anchored coordinates.

Convention:
- Figure: caption BELOW image → y_top = ~64pt (header excluded), y_bot = caption_bottom + ~6pt padding
- Table: caption ABOVE table → y_top = caption_top - 3pt, y_bot = table data bottom + ~6pt
- ACL format is roughly 612 x 792 pt, two columns at x_left ~71..302, x_right ~309..524, full ~71..524
"""
from pathlib import Path
import fitz

ROOT = Path(__file__).parent
PDF = ROOT / "source.pdf"
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)

DPI = 200
SCALE = DPI / 72

doc = fitz.open(str(PDF))

# (name, page (1-based), x0, y0, x1, y1, kind)
CROPS = [
    # Figure 1 caption @ y=392 (page 2). Image is ABOVE it (token caption examples).
    # y_top = 64 (skip header), y_bot = caption_bot ~430 + 4 = 434
    ("fig_1",   2, 71,  64, 524, 434, "figure"),
    # Figure 2 caption @ y=253 (page 3). Image is ABOVE it (architecture diagram).
    ("fig_2",   3, 71,  64, 524, 292, "figure"),
    # Figure 3 caption @ y=201 (page 5). Image is ABOVE it (two side-by-side plots).
    ("fig_3",   5, 71,  64, 524, 228, "figure"),
    # Table 1 caption @ y=242 (page 7), table ABOVE caption. y_top = 64 (header excl), y_bot = caption_top - 3 + table_data_height
    # The actual table data occupies above caption — y_top should be ~64, y_bot = caption_bottom = 270 (include caption)
    ("table_1", 7, 71,  64, 524, 270, "table"),
    # Table 2 caption @ y=448 (page 7), left column only x=[71,289], table data above. y_top = 280 (after table 1), y_bot = caption_bot 475
    ("table_2", 7, 71, 280, 289, 475, "table"),
    # Table 3 caption @ y=242 (page 9), full-width table above. y_top = 64, y_bot = caption_bot 270
    ("table_3", 9, 71,  64, 524, 270, "table"),
    # Table 4 caption @ y=427 (page 9), left column table above. y_top = 280, y_bot = caption_bot 454
    ("table_4", 9, 71, 280, 289, 454, "table"),
]

for name, pg, x0, y0, x1, y1, kind in CROPS:
    page = doc[pg - 1]
    rect = fitz.Rect(x0, y0, x1, y1)
    pix = page.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE), clip=rect)
    out = ASSETS / f"{name}.png"
    pix.save(str(out))
    print(f"  {name}.png  page={pg}  rect={rect}  -> {out.stat().st_size//1024} KB ({pix.width}x{pix.height})")

print(f"\n{len(CROPS)} assets written to {ASSETS}")
