#!/usr/bin/env python3
"""Lint draft.md against WeChat Official Account hard limits.

Step [8] of the pipeline. Runs AFTER figures_prep (step [7]) so that
<!-- IMG:N --> placeholders can be validated against figures/manifest.json,
and BEFORE render.py (step [9]).

Exit 0 = clean or warnings only.
Exit 1 = at least one hard-gate failure.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[error] pyyaml not installed; pip install pyyaml", file=sys.stderr)
    sys.exit(2)

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

# Hard limits (see references/wechat-gotchas.md)
TITLE_MAX = 32
# WeChat docs say author <= 8 Chinese chars; ASCII-only authors fit more in
# the same byte budget. We allow up to 16 ASCII / 8 Chinese chars worth.
# If WeChat rejects on push, errcode 45004 will tell us.
AUTHOR_MAX = 16
DIGEST_MAX = 120
DIGEST_WARN = 115

# Body length warn-bounds are mode-dependent.
# Mode is detected from frontmatter: paper_doi alone → paper; repo_url alone → repo;
# both → combined. See references/wechat-gotchas.md for rationale.
BODY_BOUNDS_BY_MODE = {
    "paper":    (3000, 9000),
    "repo":     (3000, 20000),  # spine pattern unfolds a full notebook tutorial
    "combined": (3000, 12000),
}
BODY_BOUNDS_DEFAULT = (3000, 9000)
COVER_MIN_W = 900
COVER_MIN_H = 500
COVER_ASPECT = 2.35
COVER_ASPECT_TOLERANCE = 0.15

FORBIDDEN_TAGS = re.compile(
    r"<\s*(script|style|iframe|form|input|button)\b",
    re.IGNORECASE,
)

PLACEHOLDER_PATTERNS = [
    (re.compile(r"\[NUM\?\]"), "NUM"),
    (re.compile(r"\[TERM-\d+\]"), "TERM"),
    (re.compile(r"\[PANEL-[A-Z0-9]+-UNCLEAR\]"), "PANEL"),
    (re.compile(r"\[UNCERTAIN[^\]]*\]"), "UNCERTAIN"),
    (re.compile(r"\[FORMULA-IMG-MISSING\]"), "FORMULA-IMG-MISSING"),
]

# v0.1: WeChat does not render LaTeX. Any `$$ ... $$` block must be either
# rewritten in prose or replaced with a screenshot via <!-- IMG:formula-N -->.
LATEX_BLOCK_RE = re.compile(r"\$\$[^$]+\$\$", re.DOTALL)

HYPE_FLAGS_DEFAULT = [
    "震惊", "重磅", "颠覆", "革命性", "前所未有",
    "unprecedented", "revolutionize", "first-ever",
]


class Report:
    def __init__(self) -> None:
        self.errors = 0
        self.warnings = 0

    def section(self, title: str) -> None:
        print(f"\n=== {title} ===")

    def ok(self, msg: str) -> None:
        print(f"  [OK]   {msg}")

    def warn(self, msg: str) -> None:
        print(f"  [WARN] {msg}")
        self.warnings += 1

    def fail(self, msg: str) -> None:
        print(f"  [FAIL] {msg}")
        self.errors += 1


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        raise ValueError("draft.md missing YAML frontmatter (expected leading ---)")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("draft.md frontmatter not closed with a trailing ---")
    try:
        fm = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"frontmatter YAML parse failed: {e}")
    if not isinstance(fm, dict):
        raise ValueError("frontmatter is not a YAML mapping")
    return fm, text[end + 5:]


def lint_frontmatter(fm: dict, r: Report) -> None:
    r.section("Frontmatter")

    title = (fm.get("title") or "").strip()
    if not title:
        r.fail("title missing")
    elif len(title) > TITLE_MAX:
        r.fail(f"title is {len(title)} chars, exceeds WeChat limit {TITLE_MAX}")
    else:
        r.ok(f"title: {len(title)}/{TITLE_MAX} chars")

    author = (fm.get("author") or "").strip()
    if not author:
        r.fail("author missing")
    elif len(author) > AUTHOR_MAX:
        r.fail(f"author is {len(author)} chars, exceeds WeChat limit {AUTHOR_MAX}")
    else:
        r.ok(f"author: {len(author)}/{AUTHOR_MAX} chars")

    digest = (fm.get("digest") or "").strip()
    if not digest:
        r.fail("digest missing (WeChat requires one; empty digest → error 45004)")
    elif len(digest) > DIGEST_MAX:
        r.fail(f"digest is {len(digest)} chars, exceeds {DIGEST_MAX} (will trigger error 45004)")
    elif len(digest) > DIGEST_WARN:
        r.warn(f"digest is {len(digest)} chars, above safety margin {DIGEST_WARN}")
    else:
        r.ok(f"digest: {len(digest)}/{DIGEST_MAX} chars")

    has_paper = bool(fm.get("paper_doi"))
    has_repo = bool(fm.get("repo_url"))
    if not has_paper and not has_repo:
        r.fail("neither paper_doi nor repo_url set (attribution missing)")
    else:
        if has_paper:
            r.ok(f"paper_doi: {fm['paper_doi']}")
        if has_repo:
            r.ok(f"repo_url: {fm['repo_url']}")


def detect_mode(fm: dict) -> str:
    has_paper = bool(fm.get("paper_doi"))
    has_repo = bool(fm.get("repo_url"))
    if has_paper and has_repo:
        return "combined"
    if has_paper:
        return "paper"
    if has_repo:
        return "repo"
    return "unknown"


def lint_body(body: str, fm: dict, r: Report) -> None:
    r.section("Body content")

    mode = detect_mode(fm)
    lo, hi = BODY_BOUNDS_BY_MODE.get(mode, BODY_BOUNDS_DEFAULT)

    n = len(body.strip())
    if n == 0:
        r.fail("body is empty")
        return
    if n < lo:
        r.warn(f"body is {n} chars, below {lo} (short for {mode}-mode science-explanation format)")
    elif n > hi:
        r.warn(f"body is {n} chars, above {hi} (long for {mode} mode; may hurt finish-rate)")
    else:
        r.ok(f"body: {n} chars (within {mode}-mode warn-bounds [{lo}, {hi}])")

    found = FORBIDDEN_TAGS.findall(body)
    if found:
        r.fail(f"forbidden HTML tags present: {sorted(set(t.lower() for t in found))}")
    else:
        r.ok("no forbidden HTML tags")

    latex = LATEX_BLOCK_RE.findall(body)
    if latex:
        sample = latex[0][:60].replace("\n", " ")
        r.fail(
            f"{len(latex)} LaTeX block(s) `$$..$$` present; WeChat will NOT render math. "
            f"Either describe in prose or use <!-- IMG:formula-N -->. First: '{sample}...'"
        )
    else:
        r.ok("no LaTeX blocks")

    for pat, name in PLACEHOLDER_PATTERNS:
        hits = pat.findall(body)
        if hits:
            sample = hits[:3]
            r.fail(f"{len(hits)} unresolved [{name}] placeholder(s); first: {sample}")
    else:
        pass

    any_ph = any(pat.search(body) for pat, _ in PLACEHOLDER_PATTERNS)
    if not any_ph:
        r.ok("no unresolved placeholders")


def lint_images(body: str, draft_dir: Path, manifest: dict, r: Report) -> None:
    r.section("Image references")

    md_refs = re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", body)
    # v0.1: placeholder ID is now any [a-zA-Z0-9_-]+ (paper figures use bare integers
    # like "1"; repo / combined uses "formula-1", "code-example-1-cell-13-0", etc.)
    ph_refs = re.findall(r"<!--\s*IMG:([a-zA-Z0-9_-]+)\s*-->", body)

    if not md_refs and not ph_refs:
        r.ok("no image references in body (OK for some repo-mode walkthroughs)")
        return

    for path in md_refs:
        if path.startswith(("http://", "https://")):
            r.ok(f"remote image ref: {path}")
            continue
        full = (draft_dir / path).resolve()
        if full.is_file():
            r.ok(f"image exists: {path}")
        else:
            r.fail(f"image missing: {path}")

    for idx in ph_refs:
        if not manifest:
            r.fail(f"<!-- IMG:{idx} --> but no figures/manifest.json (run figures_prep.py)")
            continue
        if idx not in manifest:
            r.fail(f"<!-- IMG:{idx} --> has no entry in manifest.json")
            continue
        entry = manifest[idx]
        prepared = draft_dir / entry["prepared_path"]
        if prepared.is_file():
            r.ok(f"IMG:{idx} → {entry['prepared_path']} ({entry.get('bytes', '?')} bytes)")
        else:
            r.fail(f"IMG:{idx} manifest points to missing file: {entry['prepared_path']}")


def lint_cover(fm: dict, draft_dir: Path, manifest: dict, r: Report) -> None:
    r.section("Cover image")

    cover = fm.get("cover")
    if not cover or cover == "SKIP":
        r.warn("no cover configured in frontmatter (WeChat requires one; add in editor)")
        return

    # Prefer the prepared cover if manifest carries one
    cover_entry = manifest.get("cover") if isinstance(manifest, dict) else None
    if cover_entry:
        full = draft_dir / cover_entry["prepared_path"]
    else:
        full = (draft_dir / cover).resolve()

    if not full.is_file():
        r.fail(f"cover file missing: {full}")
        return
    r.ok(f"cover file: {full.relative_to(draft_dir) if full.is_relative_to(draft_dir) else full}")

    if not HAVE_PIL:
        r.warn("Pillow not installed; skipping cover dimension/aspect check")
        return

    try:
        with Image.open(full) as img:
            w, h = img.size
    except Exception as e:
        r.fail(f"cover not readable as image: {e}")
        return

    if w < COVER_MIN_W or h < COVER_MIN_H:
        r.fail(f"cover is {w}×{h}, below {COVER_MIN_W}×{COVER_MIN_H}")
    else:
        r.ok(f"cover dims: {w}×{h}")

    aspect = w / h if h > 0 else 0
    low = COVER_ASPECT * (1 - COVER_ASPECT_TOLERANCE)
    high = COVER_ASPECT * (1 + COVER_ASPECT_TOLERANCE)
    if aspect < low or aspect > high:
        r.warn(f"cover aspect {aspect:.2f} outside target {low:.2f}–{high:.2f} (WeChat crops to 2.35:1)")
    else:
        r.ok(f"cover aspect: {aspect:.2f}")


def lint_hype(body: str, notes_path: Path | None, r: Report) -> None:
    r.section("Hype / marketing flags (warnings)")

    flags = list(HYPE_FLAGS_DEFAULT)

    if notes_path and notes_path.is_file():
        notes_text = notes_path.read_text()
        # Match `## Hype flags` or `## <number>. Hype flags` — both shapes appear
        # in the suggested skeleton.
        m = re.search(
            r"##\s*(?:\d{1,2}\.\s*)?Hype flags.*?\n(.+?)(?=\n##|\Z)",
            notes_text, re.DOTALL,
        )
        if m:
            flags.extend(re.findall(r"`([^`]+)`", m.group(1)))

    seen_hits = []
    for flag in sorted(set(f.strip() for f in flags if f.strip())):
        if flag in body:
            seen_hits.append(flag)
    if seen_hits:
        for f in seen_hits:
            r.warn(f"hype flag appears verbatim in body: '{f}'")
    else:
        r.ok("no hype flags found in body")


def lint_repo_notebooks(body: str, fm: dict, draft_dir: Path, r: Report) -> None:
    """Warn if a PURE REPO article skips notebook content silently.

    When the ingest tree contains tutorial notebooks with saved outputs but the
    draft has zero `<!-- IMG:code-example-* -->` placeholders, the LLM likely
    paraphrased code from README instead of quoting real cells (a known failure
    mode). Warn — don't fail — because some repos are pure libraries and
    deliberately have no notebooks.

    Combined mode (paper_doi AND repo_url both set) is paper-driven, NOT
    notebook-scaffolded — having 0 code-example placeholders is legitimate.
    Skip this check for combined mode to avoid false positives.
    """
    if not fm.get("repo_url"):
        return  # paper-only mode; not applicable
    if fm.get("paper_doi"):
        return  # combined mode; article is paper-driven, 0 code-example placeholders is OK

    # Find ingest tree relative to draft_dir; fall back to draft_dir/ingest
    ingest = draft_dir / "ingest"
    if not ingest.is_dir():
        return

    repo_src = ingest / "repo_src"
    if not repo_src.exists():
        return

    notebook_dirs = ["tutorials", "examples", "notebooks"]
    notebooks = []
    for d in notebook_dirs:
        notebooks.extend((repo_src / d).glob("*.ipynb")) if (repo_src / d).is_dir() else None
    notebooks = [p for p in notebooks if p is not None]
    if not notebooks:
        return  # no notebooks; nothing to warn about

    code_example_refs = re.findall(r"<!--\s*IMG:code-example-[^-\s]+-cell-\d+-\d+\s*-->", body)
    if code_example_refs:
        r.section("Repo notebook coverage")
        r.ok(f"{len(notebooks)} notebook(s) in repo_src/; {len(code_example_refs)} code-example placeholder(s) in draft")
        return

    # Count cells with saved image/png across all notebooks
    total_img_cells = 0
    for nb in notebooks:
        try:
            nbjson = json.loads(nb.read_text(encoding="utf-8"))
        except Exception:
            continue
        for cell in nbjson.get("cells", []):
            if cell.get("cell_type") != "code":
                continue
            for out in cell.get("outputs", []):
                if out.get("data", {}).get("image/png"):
                    total_img_cells += 1
                    break

    if total_img_cells > 0:
        r.section("Repo notebook coverage")
        r.warn(
            f"pure-repo article has 0 code-example placeholders, but {len(notebooks)} notebook(s) "
            f"with {total_img_cells} cells with saved image output exist in repo_src/. "
            f"Likely a silent skip — re-read [2] read-and-propose Notebook inventory rules. "
            f"(If you intentionally picked source-walkthrough mode despite notebooks existing, "
            f"ignore this warning.)"
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="Lint a draft.md for WeChat compatibility")
    ap.add_argument("draft", help="path to draft.md")
    args = ap.parse_args()

    draft_path = Path(args.draft).resolve()
    if not draft_path.is_file():
        print(f"[error] not found: {draft_path}", file=sys.stderr)
        return 2

    text = draft_path.read_text()
    try:
        fm, body = parse_frontmatter(text)
    except ValueError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 2

    draft_dir = draft_path.parent
    manifest_path = draft_dir / "figures" / "manifest.json"
    manifest: dict = {}
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError as e:
            print(f"[warn] manifest.json invalid JSON: {e}")
    notes_path = draft_dir / "notes.md"

    r = Report()
    print(f"Linting {draft_path}")
    lint_frontmatter(fm, r)
    lint_body(body, fm, r)
    lint_images(body, draft_dir, manifest, r)
    lint_cover(fm, draft_dir, manifest, r)
    lint_hype(body, notes_path, r)
    lint_repo_notebooks(body, fm, draft_dir, r)

    print()
    print("=" * 60)
    print(f"LINT: {r.errors} error(s), {r.warnings} warning(s)")
    print("=" * 60)
    return 1 if r.errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
