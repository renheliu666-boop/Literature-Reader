#!/usr/bin/env python3
"""Render a PDF page or crop rectangle to PNG using optional PyMuPDF.

Usage:
  python scripts/crop_pdf_figure.py paper.pdf 5 figures/page5.png --dpi 240
  python scripts/crop_pdf_figure.py paper.pdf 5 figures/figure1.png --rect 50 80 550 700
Page numbers are 1-based physical PDF page numbers.
"""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("page", type=int)
    parser.add_argument("output", type=Path)
    parser.add_argument("--rect", nargs=4, type=float, metavar=("X0", "Y0", "X1", "Y1"))
    parser.add_argument("--dpi", type=int, default=240)
    args = parser.parse_args()
    try:
        import fitz
    except ImportError as exc:
        raise SystemExit("需要 PyMuPDF：python -m pip install pymupdf") from exc
    if not args.pdf.exists():
        raise SystemExit(f"PDF 不存在：{args.pdf}")
    if args.dpi < 36 or args.dpi > 1200:
        raise SystemExit("--dpi 应在 36 到 1200 之间")
    with fitz.open(str(args.pdf)) as doc:
        if not 1 <= args.page <= len(doc):
            raise SystemExit(f"页码必须在 1 到 {len(doc)} 之间")
        page = doc[args.page - 1]
        rect = page.rect
        if args.rect:
            crop = fitz.Rect(*args.rect)
            if crop.is_empty or not page.rect.intersects(crop):
                raise SystemExit(f"裁剪矩形无效：{args.rect}")
            rect = crop & page.rect
        pix = page.get_pixmap(clip=rect, matrix=fitz.Matrix(args.dpi / 72, args.dpi / 72), alpha=False)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(args.output))
    print(f"已保存：{args.output}（{pix.width} × {pix.height}）")


if __name__ == "__main__":
    main()
