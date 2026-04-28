#!/usr/bin/env python3
"""Render PDF pages to PNG; crop PNG by pixel bbox.

Used by [4.5] figure-extract step in paper / combined modes. The Vision
LLM (Claude) chains the two subcommands:
  1. page-image — render the source page as PNG at a known DPI
  2. (Claude) Read the PNG (multimodal) and decide the figure's bbox
  3. crop — save the bounding region to figures/fig-N/image.png

Subcommands
-----------

    figure_extract.py page-image \\
        --pdf  work/<task>/ingest/raw/<id>.pdf \\
        --page <1-based-page-number> \\
        --dpi  <300>           # default 300 — see "Resolution" below
        --out  work/<task>/figures/_pages/<id>-page-<NNN>.png

    figure_extract.py crop \\
        --src  <rendered.png> \\
        --bbox <x1,y1,x2,y2>   # pixel coords; (0,0) is top-left
        --out  <output-figure.png>

Resolution
----------
At 300 DPI a US-letter page renders to ~2550x3300 px. A figure that
occupies ~half the page is ~1275x1650 px after cropping — comfortably
above the 1080 px WeChat width target that figures_prep targets, so
final downscale preserves anti-aliased edges and panel labels.

Lower DPI (e.g. 150) loses small panel labels (a, b, c) that the LLM
needs to see, AND produces crops below WeChat target. Higher DPI
(400+) yields no additional WeChat-level quality but inflates file
sizes. 300 DPI is the right zone; --dpi overrides if needed.

Pure pymupdf + Pillow — no Java, no external API.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import fitz  # pymupdf
except ImportError:
    print("[error] pymupdf (fitz) not installed; pip install pymupdf", file=sys.stderr)
    sys.exit(2)

try:
    from PIL import Image
except ImportError:
    print("[error] Pillow not installed; pip install Pillow", file=sys.stderr)
    sys.exit(2)


def cmd_page_image(args: argparse.Namespace) -> int:
    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.is_file():
        print(f"[error] PDF not found: {pdf_path}", file=sys.stderr)
        return 2

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    if args.page < 1 or args.page > len(doc):
        print(
            f"[error] page {args.page} out of range (1..{len(doc)} for {pdf_path.name})",
            file=sys.stderr,
        )
        doc.close()
        return 2

    page = doc[args.page - 1]
    pixmap = page.get_pixmap(dpi=args.dpi, alpha=False)
    pixmap.save(out_path)
    width, height = pixmap.width, pixmap.height
    doc.close()

    print(f"[ok] rendered page {args.page} of {pdf_path.name} → {out_path}")
    print(f"     dimensions: {width}x{height} px (at {args.dpi} DPI)")
    print(
        f"     bbox space: x in [0, {width}), y in [0, {height}); "
        f"origin (0,0) is top-left."
    )
    return 0


def cmd_crop(args: argparse.Namespace) -> int:
    src = Path(args.src).resolve()
    if not src.is_file():
        print(f"[error] source not found: {src}", file=sys.stderr)
        return 2

    parts = args.bbox.split(",")
    if len(parts) != 4:
        print("[error] --bbox must be x1,y1,x2,y2 (4 integers)", file=sys.stderr)
        return 2
    try:
        x1, y1, x2, y2 = (int(v.strip()) for v in parts)
    except ValueError:
        print("[error] --bbox values must be integers", file=sys.stderr)
        return 2

    if x2 <= x1 or y2 <= y1:
        print(
            f"[error] invalid bbox ({x1},{y1},{x2},{y2}): need x2>x1 and y2>y1",
            file=sys.stderr,
        )
        return 2

    img = Image.open(src)
    w, h = img.size
    # Clamp to image bounds (silent clamp: defensive)
    cx1 = max(0, min(x1, w))
    cy1 = max(0, min(y1, h))
    cx2 = max(0, min(x2, w))
    cy2 = max(0, min(y2, h))
    if (cx2 - cx1) < 50 or (cy2 - cy1) < 50:
        print(
            f"[error] crop region too small after clamp "
            f"({cx2-cx1}x{cy2-cy1} px; minimum 50x50). "
            f"Original bbox: ({x1},{y1},{x2},{y2}); image is {w}x{h}.",
            file=sys.stderr,
        )
        return 2
    if (cx1, cy1, cx2, cy2) != (x1, y1, x2, y2):
        print(
            f"[warn] bbox clamped to image bounds: "
            f"({x1},{y1},{x2},{y2}) -> ({cx1},{cy1},{cx2},{cy2}) "
            f"(image is {w}x{h})",
            file=sys.stderr,
        )

    cropped = img.crop((cx1, cy1, cx2, cy2))
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(out_path, "PNG")

    print(f"[ok] cropped {cx2-cx1}x{cy2-cy1} px → {out_path}")
    return 0


def cmd_placeholder_cover(args: argparse.Namespace) -> int:
    """Generate a deterministic light-gray placeholder cover.

    Sized to WeChat 2.35:1 cover standard (1280x545 px). Has a small
    centered hint text so users immediately recognize it as a placeholder
    that should be replaced via the AI-generated cover (cover-prompt.txt
    is written separately by the [4.5] prompt). Lint and figures_prep
    pass with this image — downstream pipeline doesn't block while
    waiting for an AI cover.
    """
    try:
        from PIL import ImageDraw, ImageFont
    except ImportError:
        print("[error] Pillow not installed", file=sys.stderr)
        return 2

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    width, height = 1280, 545  # exact WeChat cover ratio (2.348:1)
    img = Image.new("RGB", (width, height), color=(232, 232, 232))
    d = ImageDraw.Draw(img)
    # Subtle border so it's distinct from white-bg renders
    d.rectangle([(0, 0), (width - 1, height - 1)], outline=(200, 200, 200), width=2)

    try:
        font_lg = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36,
        )
        font_sm = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20,
        )
    except OSError:
        font_lg = ImageFont.load_default()
        font_sm = ImageFont.load_default()

    text_lg = "Cover placeholder"
    text_sm = "Generate via figures/cover-prompt.txt and replace this file"

    bbox_lg = d.textbbox((0, 0), text_lg, font=font_lg)
    bbox_sm = d.textbbox((0, 0), text_sm, font=font_sm)
    h_lg = bbox_lg[3] - bbox_lg[1]
    h_sm = bbox_sm[3] - bbox_sm[1]
    gap = 16
    total_h = h_lg + gap + h_sm
    y_top = (height - total_h) // 2

    x_lg = (width - (bbox_lg[2] - bbox_lg[0])) // 2
    d.text((x_lg, y_top), text_lg, fill=(140, 140, 140), font=font_lg)
    x_sm = (width - (bbox_sm[2] - bbox_sm[0])) // 2
    d.text((x_sm, y_top + h_lg + gap), text_sm, fill=(160, 160, 160), font=font_sm)

    img.save(out_path, "PNG")
    print(f"[ok] placeholder cover → {out_path} ({width}x{height} px, 2.35:1)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Render PDF page as PNG; crop PNG by pixel bbox.",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp_page = sub.add_parser(
        "page-image", help="render a PDF page as PNG at given DPI",
    )
    sp_page.add_argument("--pdf", required=True, help="path to source PDF")
    sp_page.add_argument(
        "--page", type=int, required=True, help="1-based page number",
    )
    sp_page.add_argument(
        "--dpi", type=int, default=300,
        help="render DPI (default 300). At 300 DPI a US-letter page "
             "renders ~2550x3300 px; a half-page figure crops to "
             "~1275x1650 px, above the 1080 px WeChat target.",
    )
    sp_page.add_argument("--out", required=True, help="output PNG path")
    sp_page.set_defaults(func=cmd_page_image)

    sp_crop = sub.add_parser("crop", help="crop a PNG by pixel bbox")
    sp_crop.add_argument("--src", required=True, help="path to source PNG")
    sp_crop.add_argument(
        "--bbox", required=True,
        help="x1,y1,x2,y2 in pixels; origin top-left "
             "(e.g. --bbox 145,210,895,640)",
    )
    sp_crop.add_argument("--out", required=True, help="output PNG path")
    sp_crop.set_defaults(func=cmd_crop)

    sp_ph = sub.add_parser(
        "placeholder-cover",
        help="generate a 1280x545 light-gray cover placeholder (2.35:1)",
    )
    sp_ph.add_argument("--out", required=True, help="output PNG path")
    sp_ph.set_defaults(func=cmd_placeholder_cover)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
