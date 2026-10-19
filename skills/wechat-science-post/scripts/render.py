#!/usr/bin/env python3
"""Build the article: lint → prepare images → output.html + preview.html.

    render.py work/<slug>/draft.md [--theme wechat-elegant] [--force]

- Runs lint.py first; stops on errors unless --force.
- Prepares every referenced image and the cover into figures/prepared/
  (≤ 1080 px wide, JPEG stepped down to ≤ 1 MB; cover ≤ 2048 px) and writes
  figures/manifest.json, which push_draft.py reads.
- output.html: inline-styled fragment to paste into the 公众号 editor.
- preview.html: the same fragment in a phone-width frame with the cover,
  title, author and digest as readers will see them; open it in a browser.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

from common import IMG_RE, SKILL_DIR, find_cover, find_figure, parse_frontmatter
import lint

BODY_MAX_W, COVER_MAX_W = 1080, 2048
SOFT_MAX, HARD_MAX = 1_000_000, 2_000_000

STRIP_BLOCKS = re.compile(r"<\s*(script|style)\b[^>]*>.*?</\s*\1\s*>", re.I | re.S)
STRIP_SINGLES = re.compile(r"</?\s*(?:iframe|form|input|button)\b[^>]*/?>", re.I)

PREVIEW = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ margin: 0; background: #e8e8ea; }}
  .phone {{ max-width: 414px; margin: 24px auto; background: #fff; box-shadow: 0 2px 16px rgba(0,0,0,.12); }}
  .head {{ padding: 20px 16px 8px; font-family: -apple-system, "PingFang SC", sans-serif; }}
  .head img {{ width: 100%; display: block; margin-bottom: 14px; }}
  .head h1 {{ font-size: 22px; line-height: 1.4; margin: 0 0 8px; color: #191919; }}
  .head .by {{ font-size: 14px; color: #576b95; }}
  .head .digest {{ font-size: 13px; color: #888; margin-top: 10px; padding: 8px; background: #f7f7f7; }}
</style></head>
<body><div class="phone">
<div class="head">{cover}<h1>{title}</h1><div class="by">{author}</div>
<div class="digest">摘要：{digest}</div></div>
{body}
</div></body></html>
"""


def prepare(src: Path, dst_stem: Path, max_w: int, force_jpeg: bool) -> Path:
    from PIL import Image

    with Image.open(src) as img:
        img.load()
        if img.width > max_w:
            img = img.resize((max_w, round(img.height * max_w / img.width)), Image.LANCZOS)
        alpha = img.mode in ("RGBA", "LA") and img.getchannel("A").getextrema()[0] < 250
        if alpha and not force_jpeg:
            out = dst_stem.with_suffix(".png")
            img.save(out, optimize=True)
            return out
        if img.mode != "RGB":
            rgba = img.convert("RGBA")
            img = Image.new("RGB", rgba.size, (255, 255, 255))
            img.paste(rgba, mask=rgba.getchannel("A"))
        out = dst_stem.with_suffix(".jpg")
        for q in (90, 82, 74, 66, 60):
            img.save(out, "JPEG", quality=q, optimize=True, progressive=True)
            if out.stat().st_size <= SOFT_MAX:
                break
        return out


def prepare_all(work: Path, ids: list[str]) -> dict:
    prepared = work / "figures" / "prepared"
    prepared.mkdir(parents=True, exist_ok=True)
    manifest = {}
    jobs = [(i, find_figure(work, i), BODY_MAX_W, False) for i in ids]
    cover = find_cover(work)
    if cover:
        jobs.append(("cover", cover, COVER_MAX_W, True))
    for fig_id, src, max_w, force_jpeg in jobs:
        stem = prepared / (f"fig-{fig_id}" if fig_id.isdigit() else fig_id)
        out = prepare(src, stem, max_w, force_jpeg)
        size = out.stat().st_size
        if size > HARD_MAX:
            raise SystemExit(f"[error] {out.name} is {size:,} bytes after compression (limit 2 MB)")
        manifest[fig_id] = {"source": str(src.relative_to(work)),
                            "prepared_path": str(out.relative_to(work)), "bytes": size}
    (work / "figures" / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    return manifest


def to_html(body: str, manifest: dict, css: str) -> str:
    from markdown_it import MarkdownIt
    from premailer import transform

    def img(m: re.Match) -> str:
        entry = manifest.get(m.group(1))
        return f"\n![]({entry['prepared_path']})\n" if entry else m.group(0)

    md = MarkdownIt("commonmark", {"html": True, "linkify": True}).enable(["table", "strikethrough"])
    fragment = md.render(IMG_RE.sub(img, body))
    doc = f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{fragment}</body></html>"
    inlined = transform(doc, remove_classes=False, keep_style_tags=False, disable_validation=True,
                        cssutils_logging_level="ERROR", allow_loading_external_files=False)
    m = re.search(r"<body([^>]*)>(.*)</body>", inlined, re.S)
    attrs, inner = (m.group(1), m.group(2).strip()) if m else ("", inlined)
    inner = STRIP_SINGLES.sub("", STRIP_BLOCKS.sub("", inner))
    # WeChat drops <body>; a <section> carries the body-level styles and survives pasting.
    return f"<section{attrs}>{inner}</section>" if attrs.strip() else inner


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("draft")
    ap.add_argument("--theme", default="wechat-elegant", help="themes/<name>.css")
    ap.add_argument("--force", action="store_true", help="render even if lint reports errors")
    args = ap.parse_args()

    draft = Path(args.draft).resolve()
    work = draft.parent
    theme = SKILL_DIR / "themes" / f"{args.theme}.css"
    if not theme.is_file():
        names = ", ".join(sorted(p.stem for p in theme.parent.glob("*.css")))
        print(f"[error] unknown theme '{args.theme}'; available: {names}", file=sys.stderr)
        return 2

    report = lint.run(draft)
    report.print()
    if report.errors and not args.force:
        print("[stop] fix the errors above (or pass --force)", file=sys.stderr)
        return 1

    fm, body = parse_frontmatter(draft.read_text(encoding="utf-8"))
    ids = [i for i in dict.fromkeys(IMG_RE.findall(body)) if i != "cover" and find_figure(work, i)]
    manifest = prepare_all(work, ids)
    fragment = to_html(body, manifest, theme.read_text())
    (work / "output.html").write_text(fragment, encoding="utf-8")

    cover = manifest.get("cover")
    (work / "preview.html").write_text(PREVIEW.format(
        title=html.escape(str(fm.get("title", ""))),
        author=html.escape(str(fm.get("author", ""))),
        digest=html.escape(str(fm.get("digest", ""))),
        cover=f'<img src="{cover["prepared_path"]}" alt="">' if cover else "",
        body=fragment,
    ), encoding="utf-8")
    total = sum(e["bytes"] for e in manifest.values())
    print(f"[ok] {len(ids)} image(s) + {'cover' if cover else 'no cover'} prepared ({total:,} bytes)")
    print(f"[ok] {work / 'output.html'}  (paste into the 公众号 editor)")
    print(f"[ok] {work / 'preview.html'}  (open in a browser)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
