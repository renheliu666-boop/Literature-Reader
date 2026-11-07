#!/usr/bin/env python3
"""Crop a complete figure region from a PDF page using optional PyMuPDF.
Page is 1-based. --rect coordinates are PDF points from the page top-left.
Without --rect, the entire page is exported.
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf",type=Path);parser.add_argument("page",type=int)
    parser.add_argument("output",type=Path);parser.add_argument("--dpi",type=int,default=240)
    parser.add_argument("--rect",nargs=4,type=float,metavar=("X0","Y0","X1","Y1"))
    args=parser.parse_args()
    try:import fitz
    except ImportError:
        print("Install optional dependency: python -m pip install pymupdf",file=sys.stderr);return 2
    if not args.pdf.is_file():parser.error(f"PDF not found: {args.pdf}")
    doc=fitz.open(args.pdf)
    if not 1<=args.page<=len(doc):parser.error(f"page must be between 1 and {len(doc)}")
    page=doc[args.page-1];clip=page.rect
    if args.rect:
        clip=fitz.Rect(*args.rect)&page.rect
        if clip.is_empty or clip.width<=0 or clip.height<=0:parser.error("crop rectangle does not intersect the page")
    pix=page.get_pixmap(matrix=fitz.Matrix(args.dpi/72,args.dpi/72),clip=clip,alpha=False,annots=True)
    args.output.parent.mkdir(parents=True,exist_ok=True);pix.save(args.output)
    print(f"Created {args.output} ({pix.width}x{pix.height})");return 0

if __name__=="__main__":raise SystemExit(main())
