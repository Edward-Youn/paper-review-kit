"""Extract full text from FREE source.pdf (page-by-page) and find figure/table caption coordinates."""
import re
from pathlib import Path
import fitz

ROOT = Path(__file__).parent
PDF = ROOT / "source.pdf"

doc = fitz.open(str(PDF))
out_text = ROOT / "fulltext.txt"

with open(out_text, "w", encoding="utf-8") as f:
    for i in range(doc.page_count):
        f.write(f"===== PAGE {i+1} =====\n")
        f.write(doc[i].get_text())
        f.write("\n\n")

print(f"fulltext.txt written ({doc.page_count} pages)")

# Find caption coords for figures + tables
caption_pat = re.compile(r"^(Figure|Table)\s+(\d+):", re.M)

for i in range(min(9, doc.page_count)):
    page = doc[i]
    blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)
    for b in blocks:
        x0, y0, x1, y1, text, *_ = b
        m = caption_pat.search(text)
        if m:
            kind, num = m.group(1), m.group(2)
            print(f"  PAGE {i+1}: {kind} {num} @ x=[{x0:.0f},{x1:.0f}] y=[{y0:.0f},{y1:.0f}] — {text[:80].strip().replace(chr(10), ' ')!r}")
