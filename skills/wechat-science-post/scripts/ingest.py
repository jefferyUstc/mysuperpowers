#!/usr/bin/env python3
"""Ingest for wechat-science-post (v0.1).

Subcommands:
  repo      git clone a GitHub repo into local cache; symlink into ingest tree
  paper     organize one or more local PDFs; per-page text via pypdf
  combined  repo + N papers in one tree

Design principle: scripts only do deterministic IO + organize. All semantic
judgment (which sections, which figure means what, how to summarize) happens
in prompts under prompts/, with Claude reading the ingest tree directly via
Read / Glob / Grep.
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
from pathlib import Path

GITHUB_API = "https://api.github.com"

# Single-source version: read from the plugin manifest at the repo root.
# Plugin version is the only version — skills don't version independently.
_SKILL_DIR = Path(__file__).resolve().parent.parent
_PLUGIN_JSON = _SKILL_DIR.parent.parent / ".claude-plugin" / "plugin.json"
SKILL_VERSION = json.loads(_PLUGIN_JSON.read_text(encoding="utf-8"))["version"]
USER_AGENT = f"wechat-science-post-ingest/{SKILL_VERSION}"
CACHE_DIR_DEFAULT = Path.home() / ".cache" / "wechat-science-post"
# INGEST_VERSION is the manifest field name for the ingest schema version.
# It tracks SKILL_VERSION 1:1 today; split them only if the manifest schema
# diverges from the plugin release cadence.
INGEST_VERSION = SKILL_VERSION

QUESTIONS_HEADER = (
    "# Open questions for the user\n\n"
    "(Scan / figure / draft prompts append questions here. "
    "Answer each question inline, or mark `N/A — proceed without`, "
    "before moving to the next step.)\n"
)


# =============================================================================
# Shared utilities
# =============================================================================


def gh_get(path: str, token: str | None = None) -> dict:
    url = f"{GITHUB_API}{path}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# =============================================================================
# Repo mode
# =============================================================================


def parse_repo_identifier(s: str) -> tuple[str, str]:
    s = s.strip().rstrip("/")
    if s.startswith(("http://", "https://")):
        m = re.match(
            r"https?://(?:www\.)?github\.com/([^/]+)/([^/]+?)(?:\.git)?$", s
        )
        if not m:
            raise ValueError(f"cannot parse GitHub URL: {s}")
        return m.group(1), m.group(2)
    if s.count("/") == 1:
        owner, name = s.split("/")
        return owner, name.removesuffix(".git")
    raise ValueError(f"expected 'owner/name' or github.com URL, got: {s}")


def clone_or_refresh_repo(
    owner: str, name: str, default_branch: str, cache_dir: Path
) -> Path:
    repo_cache = cache_dir / "repos" / f"{owner}_{name}"
    if repo_cache.is_dir():
        print(f"[repo] cache hit at {repo_cache}; refreshing")
        try:
            subprocess.run(
                ["git", "-C", str(repo_cache), "fetch", "origin"],
                check=True, timeout=60, capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(repo_cache), "reset", "--hard",
                 f"origin/{default_branch}"],
                check=True, timeout=10, capture_output=True,
            )
        except (subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
            print(f"[warn] could not refresh ({type(e).__name__}); using cached version")
    else:
        url = f"https://github.com/{owner}/{name}.git"
        print(f"[repo] cloning {url} → {repo_cache}")
        repo_cache.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", url, str(repo_cache)],
            check=True, timeout=300,
        )
    return repo_cache


SKIP_DIRS = {
    "node_modules", "__pycache__", ".git", "dist", "build", "target",
    ".venv", "venv", "vendor", ".idea", ".vscode", ".github",
    ".mypy_cache", ".pytest_cache", "coverage", "htmlcov",
}


def make_repo_tree(repo_path: Path, max_entries: int = 400) -> str:
    """2-level navigation listing. Full tree is available via repo_src/ symlink."""
    lines: list[str] = []
    for root, dirs, files in os.walk(repo_path):
        rel = Path(root).relative_to(repo_path)
        depth = len(rel.parts)
        if depth > 2:
            dirs.clear()
            continue
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        if depth >= 1:
            lines.append(f"[dir] {rel}/")
        for f in sorted(files):
            if f.startswith("."):
                continue
            rp = rel / f
            try:
                size = (repo_path / rp).stat().st_size
                lines.append(f"      {rp}  ({size} bytes)")
            except OSError:
                lines.append(f"      {rp}")
            if len(lines) >= max_entries:
                lines.append(f"... truncated at {max_entries} entries")
                return "\n".join(lines) + "\n"
    return "\n".join(lines) + "\n" if lines else "(empty)\n"


def find_paper_refs(readme: str) -> list[dict]:
    refs = []
    for m in re.finditer(r"arXiv:\s*(\d{4}\.\d{4,5})", readme, re.IGNORECASE):
        refs.append({"kind": "arxiv", "id": m.group(1)})
    for m in re.finditer(
        r"(?:https?://doi\.org/|doi:\s*)(10\.\d{4,9}/[-._;/:a-zA-Z0-9]+)",
        readme, re.IGNORECASE,
    ):
        doi = m.group(1).rstrip(").,;]")
        refs.append({"kind": "doi", "id": doi})
    for m in re.finditer(
        r"https?://(?:www\.)?biorxiv\.org/content/([^\s)]+)", readme,
    ):
        refs.append({
            "kind": "biorxiv",
            "url": "https://www.biorxiv.org/content/" + m.group(1),
        })
    seen, dedup = set(), []
    for r in refs:
        key = (r["kind"], r.get("id") or r.get("url"))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)
    return dedup


def write_paper_refs(refs: list[dict], out_path: Path) -> None:
    if not refs:
        out_path.write_text("(no arXiv / DOI / bioRxiv references found in README)\n")
        return
    lines = ["# Paper references detected in README", ""]
    for r in refs:
        if r["kind"] == "arxiv":
            lines.append(f"- arXiv: `{r['id']}` — https://arxiv.org/abs/{r['id']}")
        elif r["kind"] == "doi":
            lines.append(f"- DOI: `{r['id']}` — https://doi.org/{r['id']}")
        elif r["kind"] == "biorxiv":
            lines.append(f"- bioRxiv: {r['url']}")
    out_path.write_text("\n".join(lines) + "\n")


def ingest_repo(
    identifier: str,
    out_dir: Path,
    token: str | None,
    cache_dir: Path,
    allow_large: bool = False,
) -> None:
    owner, name = parse_repo_identifier(identifier)
    print(f"[ingest/repo] {owner}/{name}")

    meta = gh_get(f"/repos/{owner}/{name}", token=token)
    size_kb = meta.get("size", 0)
    print(f"[repo] reported size: {size_kb} KB")
    if size_kb > 1_000_000 and not allow_large:
        raise ValueError(
            f"repo is {size_kb / 1024:.0f} MB (> 1 GB). "
            f"Pass --allow-large to proceed, or use a smaller repo."
        )

    default_branch = meta.get("default_branch") or "main"
    repo_cache = clone_or_refresh_repo(owner, name, default_branch, cache_dir)

    out_dir.mkdir(parents=True, exist_ok=True)

    repo_json = {
        "ingest_version": INGEST_VERSION,
        "full_name": meta["full_name"],
        "url": meta["html_url"],
        "description": meta.get("description") or "",
        "language": meta.get("language") or "",
        "stars": meta.get("stargazers_count", 0),
        "forks": meta.get("forks_count", 0),
        "license": (meta.get("license") or {}).get("spdx_id") or "",
        "topics": meta.get("topics") or [],
        "default_branch": default_branch,
        "created_at": meta.get("created_at") or "",
        "pushed_at": meta.get("pushed_at") or "",
        "homepage": meta.get("homepage") or "",
        "archived": meta.get("archived", False),
        "open_issues": meta.get("open_issues_count", 0),
        "size_kb": size_kb,
        "local_clone": str(repo_cache),
    }
    (out_dir / "repo.json").write_text(
        json.dumps(repo_json, indent=2, ensure_ascii=False)
    )

    link = out_dir / "repo_src"
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(repo_cache.resolve())

    (out_dir / "repo_tree.txt").write_text(make_repo_tree(repo_cache))

    readme_path = repo_cache / "README.md"
    if not readme_path.is_file():
        for alt in ("README.rst", "README.txt", "README", "readme.md"):
            cand = repo_cache / alt
            if cand.is_file():
                readme_path = cand
                break
    readme = (
        readme_path.read_text(encoding="utf-8", errors="replace")
        if readme_path.is_file()
        else ""
    )
    refs = find_paper_refs(readme)
    write_paper_refs(refs, out_dir / "paper_refs.md")

    (out_dir / "questions-to-user.md").write_text(QUESTIONS_HEADER)

    print(f"[ingest/repo] done → {out_dir}")
    print(f"  repo.json           {repo_json['full_name']} "
          f"({repo_json['stars']} stars, {repo_json['language']})")
    print(f"  repo_src/           → {repo_cache} ({size_kb} KB)")
    print(f"  repo_tree.txt       {len(make_repo_tree(repo_cache).splitlines())} entries")
    print(f"  paper_refs.md       {len(refs)} reference(s)")


# =============================================================================
# Paper mode (N local PDFs)
# =============================================================================


_PAPER_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def parse_paper_arg(s: str) -> tuple[str | None, str]:
    """Accept '[id:]<path>'. Return (id_or_None, path).

    An explicit id is detected when the first ':' precedes the first '/'.
    Bare paths (no leading id) return id=None.
    """
    if ":" not in s or s.startswith("/"):
        return None, s
    if len(s) >= 3 and s[1] == ":" and s[2] == "\\":  # Windows-style C:\path
        return None, s
    first_colon = s.index(":")
    first_slash = s.find("/")
    if first_slash == -1 or first_colon < first_slash:
        return s[:first_colon], s[first_colon + 1:]
    return None, s


def validate_pdf(path_str: str) -> Path:
    p = Path(path_str).expanduser()
    if not p.is_file():
        raise ValueError(f"PDF not found: {p}")
    with open(p, "rb") as f:
        if f.read(5) != b"%PDF-":
            raise ValueError(f"not a PDF (bad magic bytes): {p}")
    return p.resolve()


def _extract_page_columns(page, narrow_threshold: float = 0.6) -> str:
    """Reading-order text from a possibly multi-column PDF page.

    Strategy: pymupdf returns paragraph-level text blocks with bounding boxes.
    Classify each block as 'wide' (spans > narrow_threshold * page width;
    typically titles, abstracts, full-width section headings), 'left' (narrow,
    centered in left half) or 'right' (narrow, centered in right half).
    Render order: wide blocks above the narrow region, then left column
    top-to-bottom, then right column top-to-bottom, then wide blocks below.

    This recovers correct narrative flow for 2-column journal layouts where
    naive y-sorted extraction interleaves columns.
    """
    blocks = page.get_text("blocks")
    text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]
    if not text_blocks:
        return ""
    page_width = page.rect.width
    midpoint = page_width / 2
    wide_thr = page_width * narrow_threshold
    classified = []  # (kind, y0, text)
    for x0, y0, x1, y1, text, *_ in text_blocks:
        width = x1 - x0
        center = (x0 + x1) / 2
        if width > wide_thr:
            kind = "wide"
        elif center < midpoint:
            kind = "left"
        else:
            kind = "right"
        classified.append((kind, y0, text.strip()))
    narrow = [c for c in classified if c[0] != "wide"]
    if not narrow:
        return "\n\n".join(c[2] for c in sorted(classified, key=lambda c: c[1]))
    nmin = min(c[1] for c in narrow)
    nmax = max(c[1] for c in narrow)
    top_wide = sorted(
        [c for c in classified if c[0] == "wide" and c[1] < nmin],
        key=lambda c: c[1],
    )
    left = sorted([c for c in classified if c[0] == "left"], key=lambda c: c[1])
    right = sorted([c for c in classified if c[0] == "right"], key=lambda c: c[1])
    bot_wide = sorted(
        [c for c in classified if c[0] == "wide" and c[1] > nmax],
        key=lambda c: c[1],
    )
    return "\n\n".join(c[2] for c in (top_wide + left + right + bot_wide))


def _doi_from_subject(subject: str) -> str:
    """Extract DOI from the PDF Subject field (often 'Journal Name, doi:10.xxxx/...')."""
    if not subject:
        return ""
    m = re.search(r"\b10\.\d{4,9}/[-._;/:a-zA-Z0-9]+", subject)
    return m.group(0) if m else ""


def extract_paper(src_path: Path, paper_id: str, raw_dir: Path) -> dict:
    """Copy PDF into raw/, dump per-page column-aware text via pymupdf, return manifest entry."""
    import fitz  # pymupdf

    pdf_dest = raw_dir / f"{paper_id}.pdf"
    shutil.copy(src_path, pdf_dest)

    pages_dir = raw_dir / paper_id
    pages_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_dest))
    try:
        page_count = doc.page_count
        text_pages_with_content = 0
        for i in range(page_count):
            text = _extract_page_columns(doc[i])
            (pages_dir / f"page-{i + 1:03d}.txt").write_text(text, encoding="utf-8")
            if text.strip():
                text_pages_with_content += 1
        meta = doc.metadata or {}
    finally:
        doc.close()

    pdf_metadata = {k: v.strip() for k, v in meta.items() if v and v.strip()}
    if "doi" not in pdf_metadata and "subject" in pdf_metadata:
        doi = _doi_from_subject(pdf_metadata["subject"])
        if doi:
            pdf_metadata["doi"] = doi

    return {
        "id": paper_id,
        "pdf": f"raw/{paper_id}.pdf",
        "pages_dir": f"raw/{paper_id}/",
        "page_count": page_count,
        "text_pages_with_content": text_pages_with_content,
        "size_bytes": pdf_dest.stat().st_size,
        "sha256": sha256_file(pdf_dest),
        "pdf_metadata": pdf_metadata,
    }


def ingest_paper(paper_args: list[str], out_dir: Path) -> None:
    if not paper_args:
        raise ValueError("at least one PDF path required")

    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(exist_ok=True)

    parsed: list[tuple[str, Path]] = []
    auto_count = 0
    seen_ids: set[str] = set()
    for arg in paper_args:
        explicit_id, path_str = parse_paper_arg(arg)
        src = validate_pdf(path_str)
        if explicit_id is not None:
            paper_id = explicit_id
        elif len(paper_args) == 1:
            paper_id = "main"
        else:
            auto_count += 1
            paper_id = f"paper-{auto_count}"
        if not _PAPER_ID_RE.match(paper_id):
            raise ValueError(
                f"invalid paper id {paper_id!r}: must match [a-zA-Z0-9_-]+"
            )
        if paper_id in seen_ids:
            raise ValueError(f"duplicate paper id: {paper_id!r}")
        seen_ids.add(paper_id)
        parsed.append((paper_id, src))

    papers = []
    for paper_id, src in parsed:
        print(f"[ingest/paper] {paper_id}: {src}")
        entry = extract_paper(src, paper_id, raw_dir)
        papers.append(entry)
        print(
            f"  → {entry['page_count']} pages "
            f"({entry['text_pages_with_content']} with text), "
            f"{entry['size_bytes']:,} bytes"
        )
        if entry["pdf_metadata"]:
            keys = list(entry["pdf_metadata"].keys())
            print(f"  → PDF metadata keys: {keys}")

    manifest = {"ingest_version": INGEST_VERSION, "papers": papers}
    (out_dir / "paper.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False)
    )
    (out_dir / "questions-to-user.md").write_text(QUESTIONS_HEADER)

    print(f"[ingest/paper] done → {out_dir}")


# =============================================================================
# Combined mode
# =============================================================================


def ingest_combined(
    repo_id: str,
    paper_args: list[str],
    out_dir: Path,
    token: str | None,
    cache_dir: Path,
    allow_large: bool = False,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("[ingest/combined] step 1/2 — repo")
    print("=" * 60)
    ingest_repo(repo_id, out_dir, token, cache_dir, allow_large=allow_large)
    print()
    print("=" * 60)
    print(f"[ingest/combined] step 2/2 — paper(s) (n={len(paper_args)})")
    print("=" * 60)
    ingest_paper(paper_args, out_dir)

    (out_dir / "combined.json").write_text(
        json.dumps(
            {
                "ingest_version": INGEST_VERSION,
                "mode": "combined",
                "note": (
                    "Cross-link detection between paper(s) and repo is now performed "
                    "by the [2.5] cross-ref prompt by reading both ingest trees "
                    "directly. No automatic signals are pre-computed."
                ),
            },
            indent=2,
        )
    )
    print(f"\n[ingest/combined] done → {out_dir}")


# =============================================================================
# CLI
# =============================================================================


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Ingest a repo / paper(s) / both into a structured work tree for "
            "wechat-science-post."
        )
    )
    sub = ap.add_subparsers(dest="mode", required=True)

    ap_repo = sub.add_parser("repo", help="ingest a GitHub repository (git clone)")
    ap_repo.add_argument("identifier", help="owner/name or full GitHub URL")
    ap_repo.add_argument(
        "--out", required=True,
        help="output directory, e.g. work/<task_name>_<ts>/ingest",
    )
    ap_repo.add_argument(
        "--cache-dir", default=None,
        help="override default ~/.cache/wechat-science-post/",
    )
    ap_repo.add_argument(
        "--allow-large", action="store_true",
        help="allow repo > 1 GB",
    )

    ap_paper = sub.add_parser("paper", help="ingest one or more local PDFs")
    ap_paper.add_argument(
        "papers", nargs="+",
        help="one or more '[id:]<path-to-pdf>' specs (id is alnum/_/-)",
    )
    ap_paper.add_argument(
        "--out", required=True,
        help="output directory, e.g. work/<task_name>_<ts>/ingest",
    )

    ap_comb = sub.add_parser(
        "combined", help="repo + paper(s) into one tree (paper-primary article)"
    )
    ap_comb.add_argument("--repo", required=True, help="owner/name or GitHub URL")
    ap_comb.add_argument(
        "--paper", required=True, action="append",
        help="'[id:]<path-to-pdf>'; repeat the flag for multiple PDFs",
    )
    ap_comb.add_argument("--out", required=True)
    ap_comb.add_argument("--cache-dir", default=None)
    ap_comb.add_argument("--allow-large", action="store_true")

    args = ap.parse_args()
    out_dir = Path(args.out)
    cache_dir = (
        Path(args.cache_dir)
        if getattr(args, "cache_dir", None)
        else CACHE_DIR_DEFAULT
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    token = os.environ.get("GITHUB_TOKEN") or None

    try:
        if args.mode == "repo":
            ingest_repo(
                args.identifier, out_dir, token, cache_dir,
                allow_large=args.allow_large,
            )
        elif args.mode == "paper":
            ingest_paper(args.papers, out_dir)
        elif args.mode == "combined":
            ingest_combined(
                args.repo, args.paper, out_dir, token, cache_dir,
                allow_large=args.allow_large,
            )
    except urllib.error.HTTPError as e:
        print(f"[error] HTTP {e.code}: {e.reason}", file=sys.stderr)
        if e.code == 403:
            print("       hint: set GITHUB_TOKEN to raise the rate limit",
                  file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"[error] network: {e.reason}", file=sys.stderr)
        return 1
    except (ValueError, subprocess.CalledProcessError) as e:
        print(f"[error] {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
