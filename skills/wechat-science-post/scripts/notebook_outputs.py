#!/usr/bin/env python3
"""Extract embedded image outputs from a Jupyter notebook (.ipynb).

Used by the wechat-science-post repo / combined modes when an article
section needs to demo a notebook cell with its rendered output.

Reads a .ipynb file (which is JSON), finds code cells with outputs that
include `image/png` MIME data, decodes the base64 image data, and writes:

    out/cell-N-source.txt      cell source code (verbatim; N is 0-based cell index, NOT zero-padded)
    out/cell-N-img-K.png       Kth IMAGE output of that cell (K starts at 0
                               and counts only images, ignoring stream / text outputs)
    out/manifest.json          [{cell, source, images: [{img_index, image}]}]

Pure stdlib (json + base64). No execution; only reads what was already
saved at the time the notebook was last run. If a cell was never run or
produced no image, it is skipped silently.

Usage:
    notebook_outputs.py <path-to.ipynb> --out <dir>
    notebook_outputs.py <path-to.ipynb> --out <dir> --cells 5,7,12   # subset

Exit codes:
    0  success (manifest written, possibly empty)
    2  bad input (file missing / not a .ipynb / bad --cells)
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path


def extract_outputs(
    nb_path: Path,
    out_dir: Path,
    cell_filter: set[int] | None = None,
) -> list[dict]:
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []
    for i, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        if cell_filter is not None and i not in cell_filter:
            continue
        outputs = cell.get("outputs", [])
        cell_images: list[dict] = []
        img_counter = 0  # image-only index, starts fresh per cell
        for j, out in enumerate(outputs):
            data = out.get("data", {})
            png = data.get("image/png")
            if not png:
                continue
            if isinstance(png, list):
                # nbformat 4.x sometimes stores as list of strings
                png = "".join(png)
            try:
                img_bytes = base64.b64decode(png)
            except (ValueError, TypeError) as e:
                print(
                    f"[warn] cell {i} output {j}: base64 decode failed ({e})",
                    file=sys.stderr,
                )
                continue
            img_path = out_dir / f"cell-{i}-img-{img_counter}.png"
            img_path.write_bytes(img_bytes)
            cell_images.append({"img_index": img_counter, "image": img_path.name})
            img_counter += 1
        if cell_images:
            src_lines = cell.get("source", [])
            src = "".join(src_lines) if isinstance(src_lines, list) else str(src_lines)
            src_path = out_dir / f"cell-{i}-source.txt"
            src_path.write_text(src)
            manifest.append({
                "cell": i,
                "source": src_path.name,
                "images": cell_images,
            })

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False)
    )
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Extract image outputs from a Jupyter notebook."
    )
    ap.add_argument("notebook", help="path to .ipynb file")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument(
        "--cells",
        default=None,
        help="comma-separated 0-based cell indices to extract; default: all",
    )
    args = ap.parse_args()

    nb_path = Path(args.notebook).expanduser()
    if not nb_path.is_file():
        print(f"[error] notebook not found: {nb_path}", file=sys.stderr)
        return 2
    if nb_path.suffix.lower() != ".ipynb":
        print(f"[error] not a .ipynb file: {nb_path}", file=sys.stderr)
        return 2

    cell_filter: set[int] | None = None
    if args.cells:
        try:
            cell_filter = {int(x.strip()) for x in args.cells.split(",") if x.strip()}
        except ValueError:
            print(
                f"[error] --cells must be comma-separated integers, got: {args.cells}",
                file=sys.stderr,
            )
            return 2

    out_dir = Path(args.out).expanduser()
    manifest = extract_outputs(nb_path, out_dir, cell_filter)

    if not manifest:
        print(
            f"[notebook_outputs] {nb_path}: no cells with image/png outputs found",
            file=sys.stderr,
        )
        return 0

    print(f"[notebook_outputs] {nb_path} -> {out_dir}")
    total_images = sum(len(m["images"]) for m in manifest)
    print(
        f"  {len(manifest)} cell(s) with output images, "
        f"{total_images} image file(s) written"
    )
    for m in manifest:
        imgs = ", ".join(img["image"] for img in m["images"])
        print(f"  cell {m['cell']:3d}: source={m['source']}, images=[{imgs}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
