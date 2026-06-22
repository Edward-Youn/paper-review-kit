"""Voila-A asset cropping — caption-anchored bboxes (PDF points, 612x792 page)."""
import fitz
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).parent
PDF = ROOT.parents[1] / "rawpaper" / "VOILA-A_ALIGNING_VISION-LANGUAGE_MODELS_WITH_USER_S_GAZE_ATTENTION.pdf"
OUT = ROOT / "assets"
DPI = 200
SC = DPI / 72.0

# (filename, page_1based, (x0,y0,x1,y1) in PDF points)
CROPS = [
    ("fig_1.png",   3, (48,  58, 564, 318)),
    ("fig_2.png",   4, (300, 272, 512, 478)),   # img y0=279, 캡션 3줄(438→472) 전체 포함 → y_bot 478
    ("fig_3.png",   4, (300, 545, 566, 716)),
    ("fig_4.png",   6, (48,  60, 566, 246)),
    ("fig_5.png",   7, (267, 612, 566, 748)),
    ("fig_6.png",   8, (268, 140, 566, 278)),
    ("fig_7.png",  14, (110, 64,  500, 314)),
    ("fig_8.png",  15, (48,  62, 564, 596)),
    ("table_1.png", 5, (100, 78, 510, 176)),   # cap y0=82(상단), 표 데이터 끝 y≈170 → 하단 본문 누수 제거
    ("table_2.png", 8, (48,  364, 566, 468)),
    ("table_3.png", 8, (48,  612, 566, 707)),
    ("table_4.png", 9, (48,  170, 566, 276)),
]

def crop():
    doc = fitz.open(PDF)
    mat = fitz.Matrix(SC, SC)
    for fn, pno, (x0, y0, x1, y1) in CROPS:
        page = doc[pno - 1]
        clip = fitz.Rect(x0, y0, x1, y1)
        pix = page.get_pixmap(matrix=mat, clip=clip)
        pix.save(OUT / fn)
    print("cropped", len(CROPS))

def contact():
    imgs = [(fn, Image.open(OUT / fn)) for fn, *_ in CROPS]
    cols = 3
    cw, pad = 360, 28
    rows = (len(imgs) + cols - 1) // cols
    cells = []
    for fn, im in imgs:
        r = cw / im.width
        cells.append((fn, im.resize((cw, int(im.height * r)))))
    rowh = [max(cells[r*cols+c][1].height for c in range(cols) if r*cols+c < len(cells)) for r in range(rows)]
    W = cols * cw + (cols + 1) * pad
    H = sum(rowh) + (rows + 1) * pad + rows * 22
    sheet = Image.new("RGB", (W, H), "white")
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    y = pad
    for r in range(rows):
        x = pad
        for c in range(cols):
            i = r*cols+c
            if i >= len(cells): break
            fn, im = cells[i]
            d.text((x, y), fn, fill="red")
            sheet.paste(im, (x, y + 20))
            x += cw + pad
        y += rowh[r] + 22 + pad
    sheet.save(OUT / "_contact.png")
    print("contact sheet saved")

if __name__ == "__main__":
    crop()
    contact()
