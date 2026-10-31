"""Low-level PDF text access via pypdfium2.

Why pdfium and not pdfminer/pdfplumber: pdfminer silently drops '/' and '%' glyphs in these
Hydac drawings ("250/300 Bar" -> "250300 Bar"). pdfium reads them correctly.

Key lessons baked in here:
  * Drawings overprint text 2-3x for faux-bold -> dedupe identical glyphs at the same spot.
  * pdfium's own space characters are in the right INDEX order but have bogus x boxes, so never
    sort chars by x. Keep index order and split into "runs" where position jumps instead.
  * Font sizes come back scaled (79.5, 1.0, ...); only use them relatively.

Coordinates are TOP-LEFT origin (y grows downward), PDF points.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import pypdfium2 as pdfium


@dataclass
class Ch:
    t: str
    x0: float
    x1: float
    y0: float  # top
    y1: float  # bottom
    size: float
    idx: int = 0


@dataclass
class Run:
    """A contiguous piece of text (one PDF text object / table cell) on one line."""
    text: str
    x0: float
    x1: float
    y0: float
    y1: float
    chars: list = field(default_factory=list, repr=False)

    @property
    def yc(self) -> float:
        return (self.y0 + self.y1) / 2


def _font_size(tp, i: int, fallback: float) -> float:
    try:
        import pypdfium2.raw as raw
        v = raw.FPDFText_GetFontSize(tp.raw, i)
        return float(v) if v else fallback
    except Exception:
        return fallback


def _view_mapper(page: "pdfium.PdfPage"):
    """Return f(l,b,r,t)->(x0,y0,x1,y1): PDF user-space box -> displayed top-left coords.

    Handles CropBox offset and /Rotate (0/90/180/270). Many A0 sheets are stored portrait with
    /Rotate 270; without this their text lands off-page.
    """
    rot = page.get_rotation() % 360
    # pypdfium2 returns a Letter-sized (0,0,612,792) box when the page has no MediaBox/CropBox of its own,
    # e.g. when it is inherited from the /Pages node (all the BOMs: A4 landscape, so every y came out 197 pt
    # too low). fallback_ok=False tells us when that happens; then take the size pdfium itself computed.
    box = page.get_cropbox(fallback_ok=False) or page.get_mediabox(fallback_ok=False)
    if box is None:
        dw, dh = page.get_size()                      # displayed size (rotation applied)
        cl, cb = 0.0, 0.0
        cr, ct = (dh, dw) if rot in (90, 270) else (dw, dh)
    else:
        cl, cb, cr, ct = box
    w, h = cr - cl, ct - cb

    def f(l, b, r, t):
        x0, x1 = l - cl, r - cl          # unrotated, top-left origin
        y0, y1 = ct - t, ct - b
        if rot == 0:
            return x0, y0, x1, y1
        if rot == 90:
            return h - y1, x0, h - y0, x1
        if rot == 180:
            return w - x1, h - y1, w - x0, h - y0
        return y0, w - x1, y1, w - x0     # 270
    return f


def page_chars(page: "pdfium.PdfPage", drop_small: bool = True) -> list[Ch]:
    """Characters in pdfium reading order (displayed orientation), overprint-duplicates removed."""
    to_view = _view_mapper(page)
    tp = page.get_textpage()
    out: list[Ch] = []
    for i in range(tp.count_chars()):
        t = tp.get_text_range(i, 1)
        if not t or t in ("\r", "\n", "\x00", "\ufffe", "\uffff"):
            continue
        L = to_view(*tp.get_charbox(i, loose=True))     # y extent: consistent per font
        T = to_view(*tp.get_charbox(i))                  # x extent: tight glyph box
        x0, x1 = (T[0], T[2]) if T[2] > T[0] else (L[0], L[2])
        out.append(Ch(t, x0, x1, L[1], L[3], _font_size(tp, i, L[3] - L[1]), i))
    out = dedupe(out)
    if drop_small and out:
        mode = Counter(round(c.size, 1) for c in out if not c.t.isspace()).most_common(1)[0][0]
        out = [c for c in out if c.t.isspace() or c.size >= 0.5 * mode]
    return out


def dedupe(chars: list[Ch], tol: float = 1.2) -> list[Ch]:
    """Drop faux-bold overprints: same glyph at (almost) the same place."""
    seen: dict[tuple, list[Ch]] = {}
    keep: list[Ch] = []
    for c in chars:
        bx, by = round(c.x0 / 4), round(c.y0 / 4)
        dup = False
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for o in seen.get((c.t, bx + dx, by + dy), ()):
                    if abs(o.x0 - c.x0) <= tol and abs(o.y0 - c.y0) <= tol:
                        dup = True
                        break
                if dup:
                    break
            if dup:
                break
        if dup:
            continue
        seen.setdefault((c.t, bx, by), []).append(c)
        keep.append(c)
    return keep


def runs(chars: list[Ch], y_rel: float = 0.34, gap_rel: float = 0.45) -> list[Run]:
    """Split the index-ordered char stream into runs (text objects / cells).
    Thresholds are relative to the glyph height so A0 and A2 sheets behave the same."""
    out: list[Run] = []
    cur: list[Ch] = []

    def flush():
        nonlocal cur
        vis = [c for c in cur if not c.t.isspace()]
        if vis:
            txt = " ".join("".join(c.t for c in cur).split())
            ys0 = sorted(c.y0 for c in vis); ys1 = sorted(c.y1 for c in vis)
            out.append(Run(txt, min(c.x0 for c in vis), max(c.x1 for c in vis),
                           ys0[len(ys0) // 2], ys1[len(ys1) // 2], list(cur)))
        cur = []

    prev: Ch | None = None
    for c in chars:
        if c.t.isspace():
            if cur:
                cur.append(c)
            continue
        if prev is not None and cur:
            h = max(prev.y1 - prev.y0, 1.0)
            same_line = abs((c.y0 + c.y1) / 2 - (prev.y0 + prev.y1) / 2) <= y_rel * h
            forward = c.x0 >= prev.x0 - 0.06 * h
            near = (c.x0 - prev.x1) <= gap_rel * h
            if not (same_line and forward and near):
                flush()
        cur.append(c)
        prev = c
    flush()
    return out


def group_lines(rs: list[Run], tol: float = 3.0) -> list[list[Run]]:
    """Cluster runs into lines by y (compare to the line's running mean, not its first run)."""
    rs = sorted(rs, key=lambda r: (r.yc, r.x0))
    lines: list[list[Run]] = []
    means: list[float] = []
    for r in rs:
        if lines and abs(r.yc - means[-1]) <= tol:
            lines[-1].append(r)
            means[-1] += (r.yc - means[-1]) / len(lines[-1])
        else:
            lines.append([r])
            means.append(r.yc)
    for ln in lines:
        ln.sort(key=lambda r: r.x0)
    return lines
