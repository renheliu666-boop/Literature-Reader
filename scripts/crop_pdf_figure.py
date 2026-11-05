#!/usr/bin/env python3
"""Render one PDF page (or selected figure rectangle) to PNG using PyMuPDF.

Optional dependency: python -m pip install pymupdf
Page and rectangle selection must be visually verified against the source PDF.
"""
import argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf", type=Path)
    ap.add_argument("page", type=int, help="1-based physical PDF page number")
    ap.add_argument("output", type=Path)
    ap.add_argument("--rect", nargs=4, type=float, metavar=("X0", "Y0", "X1", "Y1"),
                    help="crop rectangle in PDF points; omit to render the whole page")
    ap.add_argument("--dpi", type=int, default=220)
    a = ap.parse_args()
    try:
        import fitz
    except ImportError as ex:
        raise SystemExit("Requires PyMuPDF: python -m pip install pymupdf") from ex
    if not a.pdf.exists():
        raise SystemExit(f"File not found: {a.pdf}")
    with fitz.open(str(a.pdf)) as doc:
        if not (1 <= a.page <= len(doc)):
            raise SystemExit(f"page must be between 1 and {len(doc)}")
        page = doc[a.page - 1]
        if a.rect:
            rect = fitz.Rect(*a.rect)
            if rect.is_empty or not page.rect.intersects(rect):
                raise SystemExit(f"Invalid/empty rectangle: {a.rect}; page bounds: {page.rect}")
            rect &= page.rect
        else:
            rect = page.rect
        pix = page.get_pixmap(clip=rect, matrix=fitz.Matrix(a.dpi / 72, a.dpi / 72), alpha=False)
        a.output.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(a.output))
    print(f"Saved {a.output} ({pix.width} x {pix.height})")


if __name__ == "__main__":
    main()
