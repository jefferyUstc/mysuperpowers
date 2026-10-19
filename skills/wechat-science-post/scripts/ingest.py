#!/usr/bin/env python3
"""Ingest source material into work/<slug>/ingest/.

    ingest.py paper  <pdf> [<pdf> ...]            --work work/<slug>
    ingest.py repo   <owner/name | github URL>    --work work/<slug>
    ingest.py combined --repo <owner/name> --paper <pdf> [--paper <pdf>] --work work/<slug>

Several PDFs in one call form ONE article: the first is the primary paper,
the rest are supplements. For one article per paper, run ingest once per
paper with its own work dir. A PDF may carry an explicit id: `supp:./si.pdf`.

Writes ingest/manifest.json — the single place the article mode is decided —
plus cleaned per-page text (ingest/text/<id>/page-NNN.txt) and, for papers, a
figure index (caption page + large embedded images per page) that
figures.py uses to extract figures without cropping.

Scripts only do deterministic IO. Reading, judging, and writing are Claude's.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

from common import VERSION

CACHE_DIR = Path.home() / ".cache" / "wechat-science-post"
GITHUB_API = "https://api.github.com"
USER_AGENT = f"wechat-science-post/{VERSION}"

CAPTION_RE = re.compile(r"^\s*(?:Fig\.?|Figure)\s*(\d{1,2})\s*[|.:]\s*\S", re.MULTILINE)
DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s\"<>;,]+")
MIN_FIGURE_W, MIN_FIGURE_H = 400, 300   # embedded images smaller than this are not figures


# =============================================================================
# Paper text
# =============================================================================


def page_text(page) -> tuple[str, str]:
    """Reading-order text of one page. Returns (text, layout).

    Single-column pages keep pymupdf's top-to-bottom block order. Two-column
    pages are emitted segment by segment: full-width blocks (titles, wide
    figures, section breaks) cut the page into segments, and each segment is
    read left column then right column. Every text block is emitted exactly
    once, so nothing is dropped.
    """
    blocks = [b for b in page.get_text("blocks") if b[6] == 0 and b[4].strip()]
    if not blocks:
        return "", "empty"
    width = page.rect.width
    mid, tol = width / 2, width * 0.04
    left, right, wide = [], [], []
    for b in blocks:
        x0, x1 = b[0], b[2]
        if x1 <= mid + tol:
            left.append(b)
        elif x0 >= mid - tol:
            right.append(b)
        else:
            wide.append(b)
    chars = lambda bs: sum(len(b[4].strip()) for b in bs)  # noqa: E731
    total = chars(blocks)
    two_col = chars(left) >= 0.2 * total and chars(right) >= 0.2 * total

    if not two_col:
        ordered = sorted(blocks, key=lambda b: (round(b[1]), b[0]))
        return "\n".join(b[4].strip() for b in ordered), "single"

    wide.sort(key=lambda b: b[1])
    cuts = [b[1] for b in wide]
    seg = lambda b: sum(1 for c in cuts if c <= b[1])  # noqa: E731
    out = []
    for k in range(len(wide) + 1):
        for col in (left, right):
            out += sorted((b for b in col if seg(b) == k), key=lambda b: b[1])
        if k < len(wide):
            out.append(wide[k])
    return "\n".join(b[4].strip() for b in out), "two-column"


def _norm(line: str) -> str:
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", line.strip()))


NUM_ONLY = re.compile(r"^\s*\d{1,4}\s*$")


def _is_line_numbering(values: list[int]) -> bool:
    """Manuscript line numbers: many number-only lines forming a rising sequence."""
    if len(values) < 12:
        return False
    rising = sum(1 for a, b in zip(values, values[1:]) if 0 < b - a <= 3)
    return rising >= 0.8 * (len(values) - 1)


def clean_pages(pages: list[str]) -> tuple[list[str], dict]:
    """Drop running headers/footers (text lines repeated on most pages) and
    manuscript line numbers. Other number-only lines (table cells, page
    numbers) are kept."""
    n = len(pages)
    stats = {"boilerplate_lines": 0, "line_number_pages": 0}
    repeated: set[str] = set()
    if n >= 4:
        counts = Counter()
        for p in pages:
            counts.update({_norm(l) for l in p.splitlines()
                           if l.strip() and not NUM_ONLY.match(l)})
        threshold = max(3, n * 0.5)
        repeated = {k for k, c in counts.items() if c >= threshold and len(k) < 200}

    cleaned = []
    for p in pages:
        lines = p.splitlines()
        kept = [l for l in lines if not (l.strip() and _norm(l) in repeated)]
        stats["boilerplate_lines"] += len(lines) - len(kept)
        if _is_line_numbering([int(l) for l in kept if NUM_ONLY.match(l)]):
            kept = [l for l in kept if not NUM_ONLY.match(l)]
            stats["line_number_pages"] += 1
        cleaned.append(re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip() + "\n")
    return cleaned, stats


def detect_venue(raw_first_pages: str) -> str:
    for name in ("bioRxiv", "medRxiv", "arXiv", "Research Square", "SSRN"):
        if name.lower() in raw_first_pages.lower():
            return name
    return ""


def extract_paper(src: Path, paper_id: str, ingest_dir: Path) -> dict:
    import pymupdf

    pdf_dest = ingest_dir / f"{paper_id}.pdf"
    shutil.copy(src, pdf_dest)
    text_dir = ingest_dir / "text" / paper_id
    text_dir.mkdir(parents=True, exist_ok=True)

    doc = pymupdf.open(pdf_dest)
    raw_pages, layouts, warnings = [], Counter(), []
    large_images: dict[str, list] = {}
    captions: dict[str, int] = {}
    for i, page in enumerate(doc):
        text, layout = page_text(page)
        plain = page.get_text("text")
        if len(text.strip()) < 0.9 * len(plain.strip()):  # guard: never lose text
            warnings.append(f"page {i + 1}: block extraction short; used plain text")
            text, layout = plain, "fallback"
        raw_pages.append(text)
        layouts[layout] += 1
        for m in CAPTION_RE.finditer(text):
            captions.setdefault(m.group(1), i + 1)
        imgs = [
            [x[0], x[2], x[3]]  # xref, width, height
            for x in page.get_images(full=True)
            if x[2] >= MIN_FIGURE_W and x[3] >= MIN_FIGURE_H
        ]
        if imgs:
            large_images[str(i + 1)] = imgs

    first = "\n".join(raw_pages[:2])
    meta = {k: v.strip() for k, v in (doc.metadata or {}).items() if v and v.strip()}
    doi_m = DOI_RE.search(meta.get("subject", "") + "\n" + first)
    doi = doi_m.group(0).rstrip(".)]") if doi_m else ""
    page_count = doc.page_count
    doc.close()

    pages, stats = clean_pages(raw_pages)
    for i, t in enumerate(pages):
        (text_dir / f"page-{i + 1:03d}.txt").write_text(t, encoding="utf-8")

    figures = {
        n: {"caption_page": p}
        for n, p in sorted(captions.items(), key=lambda kv: int(kv[0]))
    }
    return {
        "id": paper_id,
        "pdf": f"ingest/{paper_id}.pdf",
        "text_dir": f"ingest/text/{paper_id}/",
        "page_count": page_count,
        "title": meta.get("title", ""),
        "doi": doi,
        "venue": detect_venue(first),
        "pdf_metadata": meta,
        "layout_pages": dict(layouts),
        "cleaning": stats,
        "figures": figures,
        "large_images": large_images,
        "sha256": hashlib.sha256(pdf_dest.read_bytes()).hexdigest(),
        "warnings": warnings,
    }


def parse_paper_arg(s: str) -> tuple[str | None, str]:
    m = re.match(r"^([A-Za-z0-9_-]+):(?!//)(.+)$", s)
    if m and not re.match(r"^[A-Za-z]:\\", s):
        return m.group(1), m.group(2)
    return None, s


def ingest_papers(paper_args: list[str], ingest_dir: Path) -> list[dict]:
    ingest_dir.mkdir(parents=True, exist_ok=True)
    papers, seen = [], set()
    for i, arg in enumerate(paper_args):
        pid, path = parse_paper_arg(arg)
        pid = pid or ("main" if i == 0 else f"supp-{i}")
        src = Path(path).expanduser()
        if not src.is_file() or src.read_bytes()[:5] != b"%PDF-":
            raise ValueError(f"not a PDF: {path}")
        if pid in seen:
            raise ValueError(f"duplicate paper id: {pid}")
        seen.add(pid)
        entry = extract_paper(src, pid, ingest_dir)
        papers.append(entry)
        figs = ", ".join(f"Fig {n}→p{v['caption_page']}" for n, v in entry["figures"].items())
        print(f"[paper] {pid}: {entry['page_count']} pages {entry['layout_pages']}; "
              f"doi={entry['doi'] or '?'}; venue={entry['venue'] or '?'}")
        print(f"        cleaned {entry['cleaning']['boilerplate_lines']} header/footer lines, "
              f"line numbers on {entry['cleaning']['line_number_pages']} pages")
        print(f"        figure captions: {figs or 'none found'}")
        for w in entry["warnings"]:
            print(f"        [warn] {w}")
    return papers


# =============================================================================
# Repo
# =============================================================================

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".ipynb_checkpoints", "build", "dist"}


def gh_get(path: str) -> dict:
    req = urllib.request.Request(
        GITHUB_API + path,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def parse_repo(s: str) -> tuple[str, str]:
    s = s.strip().rstrip("/")
    m = re.match(r"^(?:https?://(?:www\.)?github\.com/)?([^/\s]+)/([^/\s]+?)(?:\.git)?$", s)
    if not m:
        raise ValueError(f"expected owner/name or a github.com URL, got: {s}")
    return m.group(1), m.group(2)


def clone_or_refresh(owner: str, name: str, branch: str) -> Path:
    dest = CACHE_DIR / "repos" / f"{owner}_{name}"
    if dest.is_dir():
        try:
            subprocess.run(["git", "-C", str(dest), "fetch", "origin"], check=True,
                           timeout=60, capture_output=True)
            subprocess.run(["git", "-C", str(dest), "reset", "--hard", f"origin/{branch}"],
                           check=True, timeout=10, capture_output=True)
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            print("[warn] could not refresh cached clone; using it as is")
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "50",
                        f"https://github.com/{owner}/{name}.git", str(dest)],
                       check=True, timeout=300)
    return dest


def repo_tree(root: Path, max_entries: int = 400) -> str:
    lines: list[str] = []
    for cur, dirs, files in os.walk(root):
        rel = Path(cur).relative_to(root)
        if len(rel.parts) > 2:
            dirs.clear()
            continue
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        if rel.parts:
            lines.append(f"{rel}/")
        lines += [f"  {rel / f}" for f in sorted(files) if not f.startswith(".")]
        if len(lines) >= max_entries:
            return "\n".join(lines[:max_entries]) + "\n... (truncated)\n"
    return "\n".join(lines) + "\n"


def ingest_repo(identifier: str, ingest_dir: Path, allow_large: bool) -> dict:
    owner, name = parse_repo(identifier)
    meta = gh_get(f"/repos/{owner}/{name}")
    if meta.get("size", 0) > 1_000_000 and not allow_large:
        raise ValueError("repo is larger than 1 GB; pass --allow-large to proceed")
    branch = meta.get("default_branch") or "main"
    clone = clone_or_refresh(owner, name, branch)
    ingest_dir.mkdir(parents=True, exist_ok=True)

    link = ingest_dir / "repo_src"
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(clone.resolve())
    (ingest_dir / "repo_tree.txt").write_text(repo_tree(clone))

    notebooks = sorted(str(p.relative_to(clone)) for p in clone.rglob("*.ipynb")
                       if not any(part in SKIP_DIRS for part in p.parts))
    last = subprocess.run(["git", "-C", str(clone), "log", "-1", "--format=%ai %h %s"],
                          capture_output=True, text=True).stdout.strip()
    info = {
        "full_name": meta["full_name"],
        "url": meta["html_url"],
        "description": meta.get("description") or "",
        "language": meta.get("language") or "",
        "stars": meta.get("stargazers_count", 0),
        "license": (meta.get("license") or {}).get("spdx_id") or "",
        "default_branch": branch,
        "last_commit": last,
        "local_clone": str(clone),
        "notebooks": notebooks,
    }
    print(f"[repo]  {info['full_name']} ({info['stars']} stars, {info['language']}); "
          f"{len(notebooks)} notebook(s); last commit {last}")
    return info


# =============================================================================
# CLI
# =============================================================================


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("paper")
    p.add_argument("pdfs", nargs="+")
    r = sub.add_parser("repo")
    r.add_argument("repo")
    c = sub.add_parser("combined")
    c.add_argument("--repo", required=True)
    c.add_argument("--paper", action="append", required=True)
    for sp in (p, r, c):
        sp.add_argument("--work", required=True, help="work/<slug>")
    for sp in (r, c):
        sp.add_argument("--allow-large", action="store_true")
    args = ap.parse_args()

    work = Path(args.work)
    ingest_dir = work / "ingest"
    manifest: dict = {"mode": args.mode, "version": VERSION}
    try:
        if args.mode in ("repo", "combined"):
            manifest["repo"] = ingest_repo(args.repo, ingest_dir, args.allow_large)
        if args.mode == "paper":
            manifest["papers"] = ingest_papers(args.pdfs, ingest_dir)
        elif args.mode == "combined":
            manifest["papers"] = ingest_papers(args.paper, ingest_dir)
    except urllib.error.HTTPError as e:
        hint = " (set GITHUB_TOKEN to raise the rate limit)" if e.code == 403 else ""
        print(f"[error] GitHub HTTP {e.code}: {e.reason}{hint}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, subprocess.CalledProcessError, ValueError) as e:
        print(f"[error] {e}", file=sys.stderr)
        return 1

    (ingest_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"[ok]    mode={args.mode} → {ingest_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
