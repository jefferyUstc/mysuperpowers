#!/usr/bin/env python3
"""Render draft.md into WeChat-compatible inline-CSS HTML.

Step [9] of the pipeline. Runs after [7] figures_prep and [8] lint.

Default output is a body-only fragment (paste into WeChat 编辑器).
Use --wrap to emit a standalone HTML document (for browser preview).
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
    from markdown_it import MarkdownIt
except ImportError:
    print("[error] markdown-it-py not installed; pip install markdown-it-py", file=sys.stderr)
    sys.exit(2)

try:
    from premailer import transform
except ImportError:
    print("[error] premailer not installed; pip install premailer", file=sys.stderr)
    sys.exit(2)

# Defensive strip after inlining (premailer should have already removed <style>
# but we belt-and-suspender for anything the user snuck into draft.md).
STRIP_BLOCKS = re.compile(
    r"<\s*(?P<tag>script|style)\b[^>]*>.*?</\s*(?P=tag)\s*>",
    re.IGNORECASE | re.DOTALL,
)
STRIP_SINGLES = re.compile(
    r"</?\s*(?:iframe|form|input|button)\b[^>]*/?>",
    re.IGNORECASE,
)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    try:
        fm = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError as e:
        print(f"[warn] frontmatter YAML parse failed ({e}); proceeding with empty metadata", file=sys.stderr)
        fm = {}
    if not isinstance(fm, dict):
        fm = {}
    return fm, text[end + 5:]


def substitute_placeholders(body: str, manifest: dict) -> str:
    """Replace <!-- IMG:<id> --> with ![alt](prepared_path).

    v0.1: <id> is any [a-zA-Z0-9_-]+ — bare integers (`1`, `2`) for paper figures,
    or compound names like `formula-1`, `code-example-1-cell-13-0` for repo /
    combined modes. Look up the manifest by exact id.
    """

    def _sub(match: re.Match) -> str:
        idx = match.group(1)
        entry = manifest.get(idx) if isinstance(manifest, dict) else None
        if not entry:
            return match.group(0)  # leave placeholder for lint to catch
        # Alt text: humanize the id for screen readers
        alt = f"Figure {idx}" if idx.isdigit() else idx.replace("-", " ")
        return f"![{alt}]({entry['prepared_path']})"

    return re.sub(r"<!--\s*IMG:([a-zA-Z0-9_-]+)\s*-->", _sub, body)


def render_markdown(body: str) -> str:
    md = (
        MarkdownIt("commonmark", {"html": True, "linkify": True, "typographer": False})
        .enable("table")
        .enable("strikethrough")
    )
    return md.render(body)


def inline_css(body_html: str, css: str) -> tuple[str, str]:
    """Run premailer on the HTML fragment with the theme CSS.

    Returns (inner_html, body_attrs). `body_attrs` is the **entire
    attribute string** premailer produced on the <body> open tag
    (e.g. ` style='...'` or ` style="..."`, including the leading
    space and the quotes premailer chose). It carries page background
    and base typography that won't inherit otherwise.

    We preserve premailer's exact form (which quote style it used,
    which characters are entity-encoded vs. literal) instead of trying
    to re-quote — that avoids the double-encoding bug for themes whose
    CSS contains nested ``"`` or ``<``/``>`` (e.g. SVG data URIs in
    ``background-image``). Caller decides whether to embed it (--wrap)
    or drop it (WeChat fragment, since WeChat strips body-level styling).
    """
    wrapped = (
        "<html><head><meta charset='utf-8'>"
        f"<style>{css}</style></head><body>{body_html}</body></html>"
    )
    inlined = transform(
        wrapped,
        remove_classes=False,
        keep_style_tags=False,
        disable_validation=True,
        cssutils_logging_level="ERROR",
        allow_loading_external_files=False,
    )
    m = re.search(r"<body([^>]*)>(.*)</body>", inlined, re.DOTALL)
    if not m:
        return inlined, ""
    body_attrs = m.group(1)
    inner = m.group(2).strip()
    return inner, body_attrs


def strip_forbidden(html: str) -> tuple[str, list[str]]:
    removed: list[str] = []

    def _block(match: re.Match) -> str:
        removed.append(match.group("tag").lower())
        return ""

    cleaned = STRIP_BLOCKS.sub(_block, html)

    def _single(match: re.Match) -> str:
        tag_match = re.match(r"</?\s*([a-zA-Z]+)", match.group(0))
        if tag_match:
            removed.append(tag_match.group(1).lower())
        return ""

    cleaned = STRIP_SINGLES.sub(_single, cleaned)
    return cleaned, removed


STANDALONE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
</head>
<body{body_attrs}>
{body}
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Render draft.md to WeChat HTML")
    ap.add_argument("draft", help="path to draft.md")
    ap.add_argument("--theme", default="wechat-elegant", help="theme name (themes/<name>.css)")
    ap.add_argument("--out", help="output path (default: <draft_dir>/output.html)")
    ap.add_argument("--wrap", action="store_true", help="emit full HTML doc (default: body-only fragment)")
    args = ap.parse_args()

    draft_path = Path(args.draft).resolve()
    if not draft_path.is_file():
        print(f"[error] not found: {draft_path}", file=sys.stderr)
        return 2
    draft_dir = draft_path.parent

    skill_dir = Path(__file__).resolve().parent.parent
    theme_path = skill_dir / "themes" / f"{args.theme}.css"
    if not theme_path.is_file():
        print(f"[error] theme not found: {theme_path}", file=sys.stderr)
        return 2

    text = draft_path.read_text()
    fm, body = parse_frontmatter(text)

    manifest_path = draft_dir / "figures" / "manifest.json"
    manifest: dict = {}
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError as e:
            print(f"[warn] manifest.json invalid ({e}); skipping <!-- IMG --> substitution")

    body_md = substitute_placeholders(body, manifest)
    body_html = render_markdown(body_md)

    css = theme_path.read_text()
    inlined, body_attrs = inline_css(body_html, css)

    cleaned, removed = strip_forbidden(inlined)
    if removed:
        print(f"[warn] stripped forbidden tags: {sorted(set(removed))}")

    if args.wrap:
        # body_attrs is the verbatim attr string premailer produced on <body>
        # (e.g. ` style='...'` or empty). Splice it directly without re-escaping
        # to preserve whatever entity / quote choices premailer made.
        final = STANDALONE_TEMPLATE.format(
            title=fm.get("title", "Preview"),
            body=cleaned,
            body_attrs=body_attrs,
        )
    else:
        # Fragment mode (paste-into-WeChat). premailer inlined the body-level
        # CSS (max-width / margin auto / padding / base font / color / bg)
        # onto the <body> tag, but the fragment drops <body>. Without a
        # carrier element those styles are lost: a browser-direct-open of
        # the fragment shows full-viewport width with no padding. Wrap the
        # cleaned body content in a <section> that carries body_attrs so
        # the styles survive in both contexts: browsers honour the inline
        # max-width on a top-level <section>, and WeChat 编辑器 (plus
        # 秀米 / 壹伴 typesetting tools) explicitly preserve <section>
        # with inline style — it's the typesetters' canonical container.
        if body_attrs.strip():
            final = f"<section{body_attrs}>{cleaned}</section>"
        else:
            final = cleaned

    out_path = Path(args.out) if args.out else draft_dir / "output.html"
    # Contract: `--out` MUST be in the same directory as draft.md (i.e., the
    # work_dir root that contains `figures/`). The rendered HTML references
    # `figures/prepared/...` as a single relative path and assumes that path
    # resolves from the output's directory. Subdirectory outputs are not
    # supported — re-render with a different filename instead.
    if out_path.parent.resolve() != draft_dir.resolve():
        print(
            f"[error] --out must be in the same directory as draft.md ({draft_dir});\n"
            f"        got: {out_path.parent}\n"
            f"        rationale: rendered HTML uses relative `figures/...` paths\n"
            f"        which only resolve when output is sibling to figures/.",
            file=sys.stderr,
        )
        return 2

    out_path.write_text(final)
    size = out_path.stat().st_size
    mode = "standalone" if args.wrap else "body-only"
    print(f"[ok] rendered {mode} → {out_path} ({size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
