"""Shared helpers for the wechat-science-post scripts.

Work-dir layout (one article per work dir):

    work/<slug>/
      ingest/manifest.json      mode + paper/repo metadata + figure index   (ingest.py)
      ingest/text/<id>/page-NNN.txt                                         (ingest.py)
      notes.md                  reading notes + proposal                    (Claude)
      draft.md                  the article; source of truth                (Claude)
      figures/fig-N.png, formula-N.png, code-example-*.png, cover.png      (figures.py / user)
      figures/prepared/ + manifest.json                                     (render.py)
      output.html, preview.html                                             (render.py)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
_PLUGIN_JSON = SKILL_DIR.parent.parent / ".claude-plugin" / "plugin.json"
try:
    VERSION = json.loads(_PLUGIN_JSON.read_text(encoding="utf-8"))["version"]
except (OSError, KeyError, json.JSONDecodeError):
    VERSION = "unknown"

# WeChat hard limits (see references/wechat-publishing.md).
TITLE_MAX = 32          # characters
AUTHOR_MAX_UNITS = 16   # 8 CJK characters; an ASCII character counts as half
DIGEST_MAX = 120        # characters; over → errcode 45004
COVER_ASPECT = 2.35

IMG_RE = re.compile(r"<!--\s*IMG:([A-Za-z0-9_-]+)\s*-->")
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif")
PLACEHOLDER_COVER_TAG = "wechat-science-post placeholder cover"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split a Markdown file into (frontmatter dict, body). Raises ValueError."""
    import yaml

    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter (file must start with ---)")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("frontmatter not closed with ---")
    try:
        fm = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"frontmatter YAML parse failed: {e}") from e
    if not isinstance(fm, dict):
        raise ValueError("frontmatter is not a YAML mapping")
    return fm, text[end + 5:]


def author_units(s: str) -> int:
    """WeChat counts the author field roughly in CJK characters; ASCII is half-width."""
    return sum(1 if ord(c) < 0x2E80 else 2 for c in s)


def cjk_count(s: str) -> int:
    return sum(1 for c in s if "一" <= c <= "鿿")


def load_manifest(work_dir: Path) -> dict:
    p = work_dir / "ingest" / "manifest.json"
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def article_mode(work_dir: Path, fm: dict | None = None) -> str:
    """Mode is decided once at ingest time. Frontmatter is only a fallback."""
    mode = load_manifest(work_dir).get("mode")
    if mode:
        return mode
    if fm and fm.get("mode"):
        return str(fm["mode"])
    return "paper"


def figure_stem(fig_id: str) -> str:
    """Placeholder id → file stem under figures/. `3` → `fig-3`; others unchanged."""
    return f"fig-{fig_id}" if fig_id.isdigit() else fig_id


def find_figure(work_dir: Path, fig_id: str) -> Path | None:
    figs = work_dir / "figures"
    stem = figure_stem(fig_id)
    for ext in IMAGE_EXTS:
        for cand in (figs / f"{stem}{ext}", figs / stem / f"image{ext}"):  # flat, then v0.1 layout
            if cand.is_file():
                return cand
    return None


def find_cover(work_dir: Path) -> Path | None:
    for ext in IMAGE_EXTS:
        cand = work_dir / "figures" / f"cover{ext}"
        if cand.is_file():
            return cand
    return None


def is_placeholder_cover(path: Path) -> bool:
    try:
        from PIL import Image

        with Image.open(path) as img:
            return img.info.get("Software") == PLACEHOLDER_COVER_TAG
    except Exception:
        return False
