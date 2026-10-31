"""Render reading crops of the hydraulic-circuit drawings, for checking (or extending) tests/golden/circuits.json by eye.

usage: python tools/golden_crops.py <sample_root> <out_dir>
For every Hyd.Ckt PDF it writes gNN_A.png (spec table + termination tables) and gNN_B.png (notes block), sized so the text is
~12-17 px tall. The extractor is used ONLY to locate the spec box on the page; no extracted value is drawn or printed, so
the crops do not bias the person reading them.
"""
import glob
import os
import sys

import pypdfium2 as pdfium

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from docsearch_ingest.circuit import extract_circuit  # noqa: E402

root, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
files = sorted(f for f in glob.glob(os.path.join(root, "**", "*.pdf"), recursive=True)
               if "hyd.ckt" in os.path.basename(f).lower() and " - copy" not in f.lower())
for i, f in enumerate(files, 1):
    r = extract_circuit(f)
    boxes = [v["bbox"] for v in r["specs"].values()] + [t["bbox"] for t in r["terminations"] if t.get("bbox")]
    x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
    x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
    W, H = r["page_size"]
    mh = r["text_height"]
    page = pdfium.PdfDocument(f)[0]

    def crop(name, ax0, ay0, ax1, ay1):
        sc = min(2.2, 1960 / (ax1 - ax0))
        img = page.render(scale=sc).to_pil()
        img.crop((int(ax0 * sc), int(ay0 * sc), int(ax1 * sc), int(ay1 * sc))).save(os.path.join(out, name))

    crop(f"g{i:02d}_A.png", max(0, x0 - 30), y0 - 34, x1 + 260, min(H, y1 + 12))
    crop(f"g{i:02d}_B.png", x1 + 5 * mh, y0 - 34, min(W, x1 + 105 * mh), min(H, y1 + 12))
    print(f"g{i:02d}  {os.path.relpath(f, root)}")
