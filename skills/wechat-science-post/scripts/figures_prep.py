#!/usr/bin/env python3
"""Prepare figures for WeChat publication.

Step [7] of the pipeline. Walks four kinds of source layouts:

    work/<task_name>_<ts>/figures/
        cover.{png,jpg,jpeg,webp}                 (cover image; paper / repo / combined)
        fig-N/image.{png,jpg,jpeg,webp}           (paper / combined figure N)
        formula-N/image.{png,jpg,jpeg,webp}       (repo / combined formula screenshot N)
        code-example-N/cell-MMM-img-K.png         (repo code-example N, image K of cell MMM,
                                                   produced by notebook_outputs.py)

Produces:

    work/<task_name>_<ts>/figures/prepared/
        cover.jpg
        fig-1.jpg                                 → manifest key "1"
        formula-1.jpg                             → manifest key "formula-1"
        code-example-1-cell-13-0.jpg              → manifest key "code-example-1-cell-13-0"
        ...
    work/<task_name>_<ts>/figures/manifest.json

The manifest is a flat dict: {<key>: {prepared_path, ...}}. Keys correspond to
the IDs used in `<!-- IMG:<key> -->` placeholders inside draft.md.

Operations per image:
  - resize to max 1080 px width (preserves aspect)
  - re-encode JPEG quality stepping down from 90 to 60 until <= 1 MB
  - cover is always JPEG (WeChat requirement); body images JPEG unless
    original had meaningful transparency, in which case PNG
  - warn (non-fatal) if cover below 900x500 or aspect outside 2.35:1 ± 15%

Exit 0 on success, 1 if any image hit the 2 MB hard ceiling after
quality-stepping, 2 on fatal setup errors.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("[error] Pillow not installed; pip install Pillow", file=sys.stderr)
    sys.exit(2)

MAX_WIDTH = 1080              # body images
MAX_WIDTH_COVER = 2048        # cover — keep high-res, WeChat accepts up to 2048
SOFT_MAX_BYTES = 1_000_000    # 1 MB target
HARD_MAX_BYTES = 2_000_000    # 2 MB absolute ceiling
JPEG_QUALITY_START = 90
JPEG_QUALITY_STEP = 8
JPEG_QUALITY_FLOOR = 60
COVER_MIN_W = 900
COVER_MIN_H = 500
COVER_ASPECT = 2.35
COVER_ASPECT_TOL = 0.15
SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def resize_if_needed(img: Image.Image, max_width: int = MAX_WIDTH) -> Image.Image:
    if img.width <= max_width:
        return img
    ratio = max_width / img.width
    new_h = max(1, int(round(img.height * ratio)))
    return img.resize((max_width, new_h), Image.LANCZOS)


def flatten_alpha(img: Image.Image) -> Image.Image:
    """Composite onto white background for JPEG output."""
    if img.mode == "RGB":
        return img
    if img.mode == "P":
        img = img.convert("RGBA")
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        alpha = img.split()[-1]
        bg.paste(img.convert("RGB"), mask=alpha)
        return bg
    return img.convert("RGB")


def save_jpeg_step(img: Image.Image, out_path: Path) -> tuple[int, int]:
    """Save JPEG, stepping quality down. Return (bytes, final_quality)."""
    img = flatten_alpha(img)
    q = JPEG_QUALITY_START
    last_size = 0
    last_q = q
    while q >= JPEG_QUALITY_FLOOR:
        img.save(out_path, format="JPEG", quality=q, optimize=True, progressive=True)
        last_size = out_path.stat().st_size
        last_q = q
        if last_size <= SOFT_MAX_BYTES:
            return last_size, q
        q -= JPEG_QUALITY_STEP
    return last_size, last_q


def save_png(img: Image.Image, out_path: Path) -> int:
    img.save(out_path, format="PNG", optimize=True)
    return out_path.stat().st_size


def has_useful_alpha(img: Image.Image) -> bool:
    """Heuristic: does the image have non-trivial transparency?"""
    if img.mode not in ("RGBA", "LA", "P"):
        return False
    if img.mode == "P":
        return "transparency" in img.info
    alpha = img.split()[-1]
    extrema = alpha.getextrema()
    return extrema[0] < 250


def process_one(src: Path, dst_stem: Path, work_dir: Path, allow_png: bool, is_cover: bool = False) -> dict:
    """Process a single image. dst_stem is the prepared path without extension."""
    with Image.open(src) as img:
        img.load()
        orig_w, orig_h = img.size
        keep_png = allow_png and has_useful_alpha(img)
        max_w = MAX_WIDTH_COVER if is_cover else MAX_WIDTH
        resized = resize_if_needed(img, max_w)
        if keep_png:
            out = dst_stem.with_suffix(".png")
            size = save_png(resized, out)
            quality = None
        else:
            out = dst_stem.with_suffix(".jpg")
            size, quality = save_jpeg_step(resized, out)

    rel = out.relative_to(work_dir) if out.is_relative_to(work_dir) else out
    entry = {
        "original_path": str(src.relative_to(work_dir) if src.is_relative_to(work_dir) else src),
        "prepared_path": str(rel),
        "width": resized.width,
        "height": resized.height,
        "bytes": size,
        "original_dims": [orig_w, orig_h],
        "format": "PNG" if keep_png else "JPEG",
    }
    if quality is not None:
        entry["jpeg_quality"] = quality
    return entry


def check_cover(entry: dict) -> list[str]:
    warnings = []
    w, h = entry["original_dims"]
    if w < COVER_MIN_W or h < COVER_MIN_H:
        warnings.append(f"original cover {w}×{h} is below {COVER_MIN_W}×{COVER_MIN_H}")
    aspect = w / h if h > 0 else 0
    low = COVER_ASPECT * (1 - COVER_ASPECT_TOL)
    high = COVER_ASPECT * (1 + COVER_ASPECT_TOL)
    if aspect < low or aspect > high:
        warnings.append(f"cover aspect {aspect:.2f} outside {low:.2f}–{high:.2f}; WeChat crops to 2.35:1")
    return warnings


def find_one(dir_path: Path, stem: str) -> Path | None:
    for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        p = dir_path / f"{stem}{ext}"
        if p.is_file():
            return p
    for p in dir_path.iterdir():
        if p.is_file() and p.stem == stem and p.suffix.lower() in SUPPORTED_EXTS:
            return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Prepare figures for WeChat publication")
    ap.add_argument("work_dir", help="work/<task_name>_<ts> directory (parent of figures/)")
    args = ap.parse_args()

    work_dir = Path(args.work_dir).resolve()
    figures_dir = work_dir / "figures"
    prepared_dir = figures_dir / "prepared"

    if not work_dir.is_dir():
        print(f"[error] not a directory: {work_dir}", file=sys.stderr)
        return 2

    if not figures_dir.is_dir():
        print(f"[info] no figures/ directory under {work_dir}; nothing to prepare")
        # Write empty manifest so downstream steps see a consistent file
        figures_dir.mkdir(parents=True, exist_ok=True)
        (figures_dir / "manifest.json").write_text("{}")
        return 0

    prepared_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict = {}
    over_ceiling = []

    # Cover
    cover_src = find_one(figures_dir, "cover")
    if cover_src:
        cover_dst = prepared_dir / "cover"
        entry = process_one(cover_src, cover_dst, work_dir, allow_png=False, is_cover=True)
        manifest["cover"] = entry
        print(f"[ok]   cover: {cover_src.name} -> {entry['prepared_path']} ({entry['bytes']:,} bytes)")
        for w in check_cover(entry):
            print(f"[warn] {w}")
        if entry["bytes"] > HARD_MAX_BYTES:
            over_ceiling.append("cover")
    else:
        print(f"[info] no cover.* in {figures_dir} (configure cover in WeChat editor instead)")

    # fig-N subdirectories (paper / combined figures; manifest key = "N")
    fig_dirs = sorted(
        [d for d in figures_dir.iterdir() if d.is_dir() and re.match(r"^fig-\d+$", d.name)],
        key=lambda d: int(re.match(r"fig-(\d+)", d.name).group(1)),
    )
    for fig_dir in fig_dirs:
        idx = re.match(r"fig-(\d+)", fig_dir.name).group(1)
        img_src = find_one(fig_dir, "image")
        if not img_src:
            print(f"[warn] fig-{idx}: no image.* in {fig_dir}")
            continue
        img_dst = prepared_dir / f"fig-{idx}"
        try:
            entry = process_one(img_src, img_dst, work_dir, allow_png=True)
        except Exception as e:
            print(f"[fail] fig-{idx}: {e}")
            return 1
        manifest[idx] = entry
        note = f"Q={entry['jpeg_quality']}" if "jpeg_quality" in entry else entry["format"]
        print(f"[ok]   fig-{idx}: {img_src.name} -> {entry['prepared_path']} ({entry['bytes']:,} bytes, {note})")
        if entry["bytes"] > HARD_MAX_BYTES:
            over_ceiling.append(f"fig-{idx}")

    # formula-N subdirectories (repo / combined formula screenshots; manifest key = "formula-N")
    formula_dirs = sorted(
        [d for d in figures_dir.iterdir() if d.is_dir() and re.match(r"^formula-\d+$", d.name)],
        key=lambda d: int(re.match(r"formula-(\d+)", d.name).group(1)),
    )
    for fdir in formula_dirs:
        idx = re.match(r"formula-(\d+)", fdir.name).group(1)
        img_src = find_one(fdir, "image")
        if not img_src:
            print(f"[warn] formula-{idx}: no image.* in {fdir}")
            continue
        img_dst = prepared_dir / f"formula-{idx}"
        try:
            entry = process_one(img_src, img_dst, work_dir, allow_png=True)
        except Exception as e:
            print(f"[fail] formula-{idx}: {e}")
            return 1
        manifest[f"formula-{idx}"] = entry
        note = f"Q={entry['jpeg_quality']}" if "jpeg_quality" in entry else entry["format"]
        print(f"[ok]   formula-{idx}: {img_src.name} -> {entry['prepared_path']} ({entry['bytes']:,} bytes, {note})")
        if entry["bytes"] > HARD_MAX_BYTES:
            over_ceiling.append(f"formula-{idx}")

    # code-example-N subdirectories (repo code-example notebook outputs; one manifest entry per
    # cell-MMM-img-K.png file, manifest key = "code-example-N-cell-M-K")
    code_ex_dirs = sorted(
        [d for d in figures_dir.iterdir() if d.is_dir() and re.match(r"^code-example-\d+$", d.name)],
        key=lambda d: int(re.match(r"code-example-(\d+)", d.name).group(1)),
    )
    cell_img_re = re.compile(r"^cell-(\d+)-img-(\d+)\.(png|jpg|jpeg|webp)$", re.IGNORECASE)
    for cdir in code_ex_dirs:
        ex_idx = re.match(r"code-example-(\d+)", cdir.name).group(1)
        # Collect all per-cell image files, sort by (cell, img_idx)
        items = []
        for f in cdir.iterdir():
            m = cell_img_re.match(f.name)
            if m:
                items.append((int(m.group(1)), int(m.group(2)), f))
        items.sort()
        if not items:
            print(f"[warn] code-example-{ex_idx}: no cell-*-img-*.png in {cdir}")
            continue
        for cell_no, img_no, src in items:
            key = f"code-example-{ex_idx}-cell-{cell_no}-{img_no}"
            dst_stem = prepared_dir / key
            try:
                entry = process_one(src, dst_stem, work_dir, allow_png=True)
            except Exception as e:
                print(f"[fail] {key}: {e}")
                return 1
            manifest[key] = entry
            note = f"Q={entry['jpeg_quality']}" if "jpeg_quality" in entry else entry["format"]
            print(f"[ok]   {key}: {src.name} -> {entry['prepared_path']} ({entry['bytes']:,} bytes, {note})")
            if entry["bytes"] > HARD_MAX_BYTES:
                over_ceiling.append(key)

    # Manifest
    manifest_path = figures_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    total = sum(e["bytes"] for e in manifest.values())
    print()
    print("=" * 60)
    print(f"PREPARED: {len(manifest)} image(s), total {total:,} bytes")
    print(f"  manifest: {manifest_path}")
    if over_ceiling:
        print(f"  [FAIL] over 2 MB ceiling: {over_ceiling}")
        return 1
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
