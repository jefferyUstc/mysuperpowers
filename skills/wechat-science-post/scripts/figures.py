#!/usr/bin/env python3
"""Put article images into work/<slug>/figures/.

    figures.py auto     work/<slug>                 paper figures for every <!-- IMG:N --> in draft.md
    figures.py page     --pdf X.pdf --page P --out page.png [--dpi 300]
    figures.py crop     --src page.png --bbox x0,y0,x1,y1 --out figures/fig-N.png
    figures.py cover    work/<slug> [--src image.png] [--bbox x0,y0,x1,y1]
    figures.py notebook work/<slug> path/to/notebook.ipynb [--example 1]

`auto` uses the figure index written by ingest.py. When the caption page (or
the page before it) carries exactly one large embedded image, that image is
the figure: it is saved losslessly at native resolution. Otherwise the page
is rendered to figures/_pages/ and reported as NEEDS CROP; Claude looks at
the rendered page and calls `crop`. Files already present (user-supplied or
from an earlier run) are never overwritten.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from pathlib import Path

from common import IMG_RE, PLACEHOLDER_COVER_TAG, find_cover, find_figure, load_manifest

COVER_W, COVER_H = 1280, 545


def save_embedded(doc, xref: int, smask: int, out: Path) -> tuple[int, int]:
    import pymupdf

    pix = pymupdf.Pixmap(doc, xref)
    if pix.colorspace and pix.colorspace.n > 3:      # CMYK etc. → RGB
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    if smask:
        pix = pymupdf.Pixmap(pix, pymupdf.Pixmap(doc, smask))  # keep transparency; render flattens it
    out.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(out))
    return pix.width, pix.height


def render_page(pdf: Path, page_no: int, out: Path, dpi: int = 300) -> tuple[int, int]:
    import pymupdf

    doc = pymupdf.open(pdf)
    pix = doc[page_no - 1].get_pixmap(dpi=dpi)
    out.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(out))
    return pix.width, pix.height


def cmd_auto(work: Path, dpi: int) -> int:
    import pymupdf

    manifest = load_manifest(work)
    if not manifest.get("papers"):
        print("[error] no papers in ingest/manifest.json (run ingest.py first)", file=sys.stderr)
        return 2
    paper = manifest["papers"][0]
    pdf = work / paper["pdf"]
    draft = work / "draft.md"
    if draft.is_file():
        wanted = sorted({m for m in IMG_RE.findall(draft.read_text()) if m.isdigit()}, key=int)
    else:
        wanted = sorted(paper["figures"], key=int)
    if not wanted:
        print("[info] draft.md has no <!-- IMG:N --> paper-figure placeholders")
        return 0

    caption_pages = {v["caption_page"] for v in paper["figures"].values()}
    large = {int(k): v for k, v in paper.get("large_images", {}).items()}
    doc = pymupdf.open(pdf)
    smasks = {}  # xref → smask xref
    for page in doc:
        for x in page.get_images(full=True):
            smasks[x[0]] = x[1]

    needs_crop = 0
    for n in wanted:
        existing = find_figure(work, n)
        if existing:
            print(f"fig-{n}: exists, kept ({existing.relative_to(work)})")
            continue
        info = paper["figures"].get(n)
        if not info:
            print(f"fig-{n}: NEEDS MANUAL — no caption starting 'Fig. {n}' / 'Figure {n}' found in the PDF")
            needs_crop += 1
            continue
        p = info["caption_page"]
        source = None
        if len(large.get(p, [])) == 1:
            source = (p, large[p][0])
        elif not large.get(p) and len(large.get(p - 1, [])) == 1 and (p - 1) not in caption_pages:
            source = (p - 1, large[p - 1][0])
        if source:
            page_no, (xref, w, h) = source
            out = work / "figures" / f"fig-{n}.png"
            save_embedded(doc, xref, smasks.get(xref, 0), out)
            note = "" if w >= 800 else "  [warn] low resolution; consider a 300-dpi crop instead"
            print(f"fig-{n}: extracted embedded image from page {page_no} ({w}x{h}) → figures/fig-{n}.png{note}")
            continue
        needs_crop += 1
        pages = [p] + ([p - 1] if large.get(p - 1) and (p - 1) not in caption_pages else [])
        for q in pages:
            out = work / "figures" / "_pages" / f"{paper['id']}-p{q:03d}.png"
            w, h = render_page(pdf, q, out, dpi)
            print(f"fig-{n}: NEEDS CROP — rendered page {q} → {out.relative_to(work)} ({w}x{h} @ {dpi} dpi)")
    if needs_crop:
        print(f"\n{needs_crop} figure(s) need a crop: Read the rendered page, then run "
              "`figures.py crop --src <page.png> --bbox x0,y0,x1,y1 --out figures/fig-N.png` "
              "(panels only, no caption text).")
    return 0


def cmd_crop(src: Path, bbox: str, out: Path) -> int:
    from PIL import Image

    x0, y0, x1, y1 = (int(v) for v in bbox.split(","))
    with Image.open(src) as img:
        if not (0 <= x0 < x1 <= img.width and 0 <= y0 < y1 <= img.height):
            print(f"[error] bbox outside image {img.width}x{img.height}", file=sys.stderr)
            return 2
        out.parent.mkdir(parents=True, exist_ok=True)
        img.crop((x0, y0, x1, y1)).save(out)
    print(f"[ok] {out} ({x1 - x0}x{y1 - y0})")
    return 0


def cmd_cover(work: Path, src: Path | None, bbox: str | None) -> int:
    from PIL import Image, PngImagePlugin

    out = work / "figures" / "cover.png"
    existing = find_cover(work)
    if src is None:
        if existing:
            print(f"[ok] cover exists, kept ({existing.relative_to(work)})")
            return 0
        info = PngImagePlugin.PngInfo()
        info.add_text("Software", PLACEHOLDER_COVER_TAG)
        out.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (COVER_W, COVER_H), (236, 238, 241)).save(out, pnginfo=info)
        print(f"[ok] placeholder cover → {out.relative_to(work)} (replace before publishing)")
        return 0
    with Image.open(src) as img:
        img = img.convert("RGB")
        if bbox:
            img = img.crop(tuple(int(v) for v in bbox.split(",")))
        # Fit inside 2.35:1 on white, never cutting content.
        scale = min(COVER_W / img.width, COVER_H / img.height)
        fitted = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))),
                            Image.LANCZOS)
        canvas = Image.new("RGB", (COVER_W, COVER_H), (255, 255, 255))
        canvas.paste(fitted, ((COVER_W - fitted.width) // 2, (COVER_H - fitted.height) // 2))
        out.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(out)
    print(f"[ok] cover from {src.name} → {out.relative_to(work)} ({COVER_W}x{COVER_H})")
    return 0


def cmd_notebook(work: Path, nb_path: Path, example: int) -> int:
    """Save every image output of a notebook as figures/code-example-E-cell-M-K.png
    (M = 0-based cell index, K = image index within the cell) and an index JSON
    with each such cell's source. Nothing is executed."""
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    figs = work / "figures"
    figs.mkdir(parents=True, exist_ok=True)
    index = []
    for m, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        images = [o["data"]["image/png"] for o in cell.get("outputs", [])
                  if isinstance(o.get("data"), dict) and "image/png" in o["data"]]
        ids = []
        for k, b64 in enumerate(images):
            fig_id = f"code-example-{example}-cell-{m}-{k}"
            (figs / f"{fig_id}.png").write_bytes(base64.b64decode(re.sub(r"\s", "", "".join(b64))))
            ids.append(fig_id)
        if ids:
            index.append({"cell": m, "source": "".join(cell.get("source", [])), "images": ids})
    (figs / f"code-example-{example}.json").write_text(json.dumps(index, indent=2, ensure_ascii=False))
    print(f"[ok] {sum(len(c['images']) for c in index)} image(s) from {len(index)} cell(s) → "
          f"figures/code-example-{example}-cell-*.png; index: figures/code-example-{example}.json")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("auto")
    a.add_argument("work")
    a.add_argument("--dpi", type=int, default=300)
    p = sub.add_parser("page")
    p.add_argument("--pdf", required=True)
    p.add_argument("--page", type=int, required=True, help="1-based")
    p.add_argument("--out", required=True)
    p.add_argument("--dpi", type=int, default=300)
    c = sub.add_parser("crop")
    c.add_argument("--src", required=True)
    c.add_argument("--bbox", required=True, help="x0,y0,x1,y1 in pixels of --src")
    c.add_argument("--out", required=True)
    v = sub.add_parser("cover")
    v.add_argument("work")
    v.add_argument("--src")
    v.add_argument("--bbox")
    n = sub.add_parser("notebook")
    n.add_argument("work")
    n.add_argument("ipynb")
    n.add_argument("--example", type=int, default=1)
    args = ap.parse_args()

    if args.cmd == "auto":
        return cmd_auto(Path(args.work), args.dpi)
    if args.cmd == "page":
        w, h = render_page(Path(args.pdf), args.page, Path(args.out), args.dpi)
        print(f"[ok] {args.out} ({w}x{h} @ {args.dpi} dpi)")
        return 0
    if args.cmd == "crop":
        return cmd_crop(Path(args.src), args.bbox, Path(args.out))
    if args.cmd == "cover":
        return cmd_cover(Path(args.work), Path(args.src) if args.src else None, args.bbox)
    return cmd_notebook(Path(args.work), Path(args.ipynb), args.example)


if __name__ == "__main__":
    sys.exit(main())
