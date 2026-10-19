#!/usr/bin/env python3
"""Check draft.md against WeChat hard limits and the skill's writing rules.

    lint.py work/<slug>/draft.md

render.py runs this first and refuses to render on errors; run it alone
while editing. Exit 1 on any error, 0 otherwise (warnings are advisory).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from common import (
    AUTHOR_MAX_UNITS, COVER_ASPECT, DIGEST_MAX, IMG_RE, TITLE_MAX, article_mode,
    SKILL_DIR, author_units, cjk_count, find_cover, find_figure, is_placeholder_cover, parse_frontmatter,
)

BODY_BOUNDS = {"paper": (3000, 10000), "combined": (3000, 12000), "repo": (3000, 20000)}

FORBIDDEN_TAGS = re.compile(r"<\s*(script|style|iframe|form|input|button)\b", re.I)
LATEX_BLOCK = re.compile(r"\$\$[^$]+\$\$", re.S)
UNRESOLVED = re.compile(r"\[(?:NUM\?|TERM-\d+|UNCERTAIN[^\]]*|TODO[^\]]*|待确认[^\]]*)\]")

LANGUAGE_FILE = SKILL_DIR / "references" / "language.md"


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: list[str] = []

    def fail(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def ok(self, msg: str) -> None:
        self.info.append(msg)

    def print(self) -> None:
        for m in self.info:
            print(f"  [ok]   {m}")
        for m in self.warnings:
            print(f"  [warn] {m}")
        for m in self.errors:
            print(f"  [FAIL] {m}")
        print(f"LINT: {len(self.errors)} error(s), {len(self.warnings)} warning(s)")


def word_list(heading: str) -> list[str]:
    """Backticked items under `### <heading>` in references/language.md (single source)."""
    if not LANGUAGE_FILE.is_file():
        return []
    m = re.search(rf"^### {heading}\s*\n(.+?)(?=^#{{2,3}} |\Z)", LANGUAGE_FILE.read_text(), re.S | re.M)
    return re.findall(r"`([^`]+)`", m.group(1)) if m else []


def notes_hype_flags(work: Path) -> list[str]:
    notes = work / "notes.md"
    if not notes.is_file():
        return []
    m = re.search(r"^##[^\n]*Hype flags[^\n]*\n(.+?)(?=^## |\Z)", notes.read_text(), re.S | re.M)
    return re.findall(r"`([^`]+)`", m.group(1)) if m else []


def run(draft: Path) -> Report:
    r = Report()
    work = draft.parent
    try:
        fm, body = parse_frontmatter(draft.read_text(encoding="utf-8"))
    except ValueError as e:
        r.fail(str(e))
        return r

    # --- frontmatter ---------------------------------------------------------
    title = str(fm.get("title") or "").strip()
    author = str(fm.get("author") or "").strip()
    digest = str(fm.get("digest") or "").strip()
    if not title or len(title) > TITLE_MAX:
        r.fail(f"title must be 1–{TITLE_MAX} characters (has {len(title)})")
    else:
        r.ok(f"title {len(title)}/{TITLE_MAX}")
    if not author or author_units(author) > AUTHOR_MAX_UNITS:
        r.fail(f"author must be ≤ 8 CJK characters (16 ASCII); '{author}' = {author_units(author)} units")
    if not digest or len(digest) > DIGEST_MAX:
        r.fail(f"digest must be 1–{DIGEST_MAX} characters (has {len(digest)}); over → errcode 45004")
    else:
        r.ok(f"digest {len(digest)}/{DIGEST_MAX}")
    if not (fm.get("paper_doi") or fm.get("repo_url")):
        r.fail("frontmatter needs paper_doi or repo_url (attribution and 阅读原文 link)")

    # --- body ----------------------------------------------------------------
    mode = article_mode(work, fm)
    lo, hi = BODY_BOUNDS.get(mode, BODY_BOUNDS["paper"])
    text = IMG_RE.sub("", body).strip()
    n = len(text)
    msg = f"body {n} chars ({cjk_count(text)} 汉字), {mode} mode range {lo}–{hi}"
    (r.warn if not lo <= n <= hi else r.ok)(msg)
    if FORBIDDEN_TAGS.search(body):
        r.fail("forbidden HTML tag (script/style/iframe/form/input/button) in body")
    if LATEX_BLOCK.search(body):
        r.fail("LaTeX $$…$$ block: WeChat does not render math; use prose, unicode, or <!-- IMG:formula-N -->")
    for hit in sorted(set(UNRESOLVED.findall(body))):
        r.fail(f"unresolved marker {hit}")
    if re.search(r"^#\s", body, re.M):
        r.warn("body contains an h1 (`# `); the title already comes from frontmatter")

    # --- images --------------------------------------------------------------
    ids = IMG_RE.findall(body)
    if "cover" in ids:
        r.fail("<!-- IMG:cover --> in body: the cover is set by frontmatter only")
    missing = [i for i in ids if i != "cover" and not find_figure(work, i)]
    for i in missing:
        r.fail(f"<!-- IMG:{i} --> has no image (expected figures/{'fig-' + i if i.isdigit() else i}.png)")
    if ids and not missing:
        r.ok(f"{len(ids)} image placeholder(s) resolved")
    for path in re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", body):
        if not path.startswith(("http://", "https://")) and not (work / path).is_file():
            r.fail(f"image file missing: {path}")

    cover = find_cover(work)
    if not cover:
        r.fail("no figures/cover.* (run `figures.py cover` for a placeholder)")
    else:
        try:
            from PIL import Image

            with Image.open(cover) as img:
                w, h = img.size
            if w < 900 or h < 383:
                r.fail(f"cover is {w}x{h}; needs at least 900x383")
            elif abs(w / h - COVER_ASPECT) > COVER_ASPECT * 0.15:
                r.warn(f"cover aspect {w / h:.2f}; WeChat crops to 2.35:1")
        except Exception as e:  # noqa: BLE001
            r.fail(f"cover unreadable: {e}")
        if is_placeholder_cover(cover):
            r.warn("cover is the gray placeholder; replace figures/cover.png before publishing")

    # --- wording -------------------------------------------------------------
    for w in sorted(set(word_list("Banned") + notes_hype_flags(work))):
        if w in body:
            r.warn(f"banned word in body (references/language.md § 7): '{w}'")
    for w in word_list("Check"):
        if w in body:
            r.warn(f"check wording (references/language.md § 7): '{w}'")

    # --- repo mode: notebook images expected when the repo has notebooks ----
    if mode == "repo" and not any(i.startswith("code-example-") for i in ids):
        from common import load_manifest

        if load_manifest(work).get("repo", {}).get("notebooks"):
            r.warn("repo has notebooks but the draft shows no notebook output; "
                   "intended (source walkthrough)? otherwise run `figures.py notebook`")
    return r


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    draft = Path(sys.argv[1]).resolve()
    if not draft.is_file():
        print(f"[error] not found: {draft}", file=sys.stderr)
        return 2
    print(f"Linting {draft}")
    r = run(draft)
    r.print()
    return 1 if r.errors else 0


if __name__ == "__main__":
    sys.exit(main())
