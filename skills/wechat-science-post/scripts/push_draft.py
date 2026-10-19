#!/usr/bin/env python3
"""Push a rendered article to the WeChat Official Account draft box.

Optional last step: run render.py first (it writes output.html and
figures/manifest.json, which this script uploads). Requires:

  - WECHAT_APPID and WECHAT_SECRET in environment, OR
  - ~/.config/wechat-science-post/config.yaml with chmod 600:
        wechat:
          appid: "wx..."
          secret: "..."

The server's outbound IP must be on the WeChat whitelist (公众号 后台 →
开发 → 基本配置 → IP 白名单). Check the outbound IP with:

    curl ifconfig.me

Inputs (in order of precedence for each field):

  - the work dir:  work/<task_name>_<ts>/
      ├── draft.md         (frontmatter: title, author, digest, cover,
      │                     paper_doi, repo_url)
      ├── output.html      (fragment from render.py)
      └── figures/
          ├── manifest.json    (from render.py)
          └── prepared/        (cover.jpg, fig-N.jpg, ...)

Behavior:

  1. Read draft.md frontmatter → title / author / digest
  2. Read output.html (the body-only fragment)
  3. Read figures/manifest.json
  4. Upload cover → thumb_media_id (永久素材 type=thumb)
  5. For each body image referenced in output.html that matches a prepared
     path, upload as 永久素材 type=image → get mmbiz URL, rewrite <img src>
  6. Build the article object
  7. POST to cgi-bin/draft/add
  8. Print the draft's media_id

Safety:

  - --dry-run: do everything except network calls; print the plan
  - Never calls cgi-bin/freepublish/submit (no auto-publish)
  - Access token is cached under ~/.cache/wechat-science-post/token.json
    with expiry timestamp; refreshed when stale
  - A sentinel file work/<task_name>_<ts>/.pushed is written on success so re-runs
    can warn about duplicates

Exit codes:
  0 success / dry-run success
  1 recoverable failure (e.g. WeChat API errored)
  2 configuration / input problem
"""
from __future__ import annotations

import argparse
import io
import json
import mimetypes
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

from common import AUTHOR_MAX_UNITS, DIGEST_MAX, TITLE_MAX, VERSION, author_units
from common import parse_frontmatter as _parse_frontmatter

WECHAT_BASE = "https://api.weixin.qq.com"
TOKEN_CACHE_DEFAULT = Path.home() / ".cache" / "wechat-science-post" / "token.json"
CONFIG_DEFAULT = Path.home() / ".config" / "wechat-science-post" / "config.yaml"

USER_AGENT = f"wechat-science-post-push/{VERSION}"

# WeChat errors that matter for diagnostic quality
ERRCODE_HINTS = {
    40001: "access_token invalid or expired; local cache will be purged on next run",
    40125: "invalid AppSecret (40125); copy-paste error or rotated secret",
    41001: "missing access_token (41001)",
    45004: "digest exceeds 120 chars (45004) — lint.py should have caught this",
    45008: "content contains illegal words (45008); WeChat content moderation",
    45166: "media_id invalid or expired (45166); the upload must use 永久素材 (material/add_material)",
    40164: "IP not whitelisted (40164); add this server's outbound IP to 公众号 白名单",
    -1:    "WeChat server busy (-1); retry after a brief wait",
}


# =============================================================================
# Config loading
# =============================================================================


def load_credentials(config_path: Path | None) -> tuple[str, str]:
    """Return (appid, secret). Raises SystemExit with clear message on failure."""
    env_appid = os.environ.get("WECHAT_APPID")
    env_secret = os.environ.get("WECHAT_SECRET")
    if env_appid and env_secret:
        return env_appid, env_secret

    path = config_path or CONFIG_DEFAULT
    if not path.is_file():
        raise SystemExit(
            f"no WeChat credentials found.\n"
            f"  tried env: WECHAT_APPID + WECHAT_SECRET\n"
            f"  tried file: {path}\n"
            f"fix by ONE of:\n"
            f"  export WECHAT_APPID=wx... ; export WECHAT_SECRET=...\n"
            f"  OR write {path} with:\n"
            f"    wechat:\n      appid: \"wx...\"\n      secret: \"...\"\n"
            f"  and then: chmod 600 {path}"
        )

    # Permission hygiene
    mode = path.stat().st_mode & 0o777
    if mode & 0o044:
        print(f"[warn] {path} is mode {oct(mode)[2:]}, recommend `chmod 600`", file=sys.stderr)

    try:
        data = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        raise SystemExit(f"[error] {path} parse failed: {e}")
    wc = (data.get("wechat") or {}) if isinstance(data, dict) else {}
    appid = wc.get("appid") or ""
    secret = wc.get("secret") or ""
    if not appid or not secret:
        raise SystemExit(f"[error] {path} missing wechat.appid or wechat.secret")
    return appid, secret


# =============================================================================
# Access token (7200 s expiry, cached)
# =============================================================================


def get_access_token(appid: str, secret: str, cache: Path, refresh: bool = False) -> str:
    now = int(time.time())
    if not refresh and cache.is_file():
        try:
            cached = json.loads(cache.read_text())
            if cached.get("appid") == appid and cached.get("expires_at", 0) > now + 60:
                return cached["access_token"]
        except json.JSONDecodeError:
            pass

    url = (
        f"{WECHAT_BASE}/cgi-bin/token"
        f"?grant_type=client_credential&appid={urllib.parse.quote(appid)}"
        f"&secret={urllib.parse.quote(secret)}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read())

    if "access_token" not in body:
        code = body.get("errcode", "?")
        hint = ERRCODE_HINTS.get(code, "")
        raise RuntimeError(
            f"access_token fetch failed: errcode={code} errmsg={body.get('errmsg')}"
            + (f" — {hint}" if hint else "")
        )

    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({
        "appid": appid,
        "access_token": body["access_token"],
        "expires_at": now + int(body.get("expires_in", 7200)),
    }, indent=2))
    try:
        cache.chmod(0o600)
    except OSError:
        pass
    return body["access_token"]


# =============================================================================
# Multipart upload (stdlib-only)
# =============================================================================


def _build_multipart(field_name: str, file_path: Path) -> tuple[bytes, str]:
    """Return (body_bytes, content_type). One file part, one field."""
    boundary = "----WSP-" + secrets.token_hex(12)
    mime, _ = mimetypes.guess_type(str(file_path))
    mime = mime or "application/octet-stream"
    buf = io.BytesIO()
    crlf = b"\r\n"
    buf.write(f"--{boundary}".encode() + crlf)
    buf.write(
        f'Content-Disposition: form-data; name="{field_name}"; filename="{file_path.name}"'.encode()
        + crlf
    )
    buf.write(f"Content-Type: {mime}".encode() + crlf + crlf)
    buf.write(file_path.read_bytes())
    buf.write(crlf + f"--{boundary}--".encode() + crlf)
    return buf.getvalue(), f"multipart/form-data; boundary={boundary}"


def upload_material(token: str, file_path: Path, material_type: str) -> dict:
    """Upload to 永久素材 (material/add_material). material_type ∈ {image, thumb, voice, video}.

    Returns dict with at least {media_id: str}. For image, also {url: str}.
    """
    if not file_path.is_file():
        raise ValueError(f"file not found: {file_path}")
    url = (
        f"{WECHAT_BASE}/cgi-bin/material/add_material"
        f"?access_token={urllib.parse.quote(token)}&type={material_type}"
    )
    body, ctype = _build_multipart("media", file_path)
    req = urllib.request.Request(
        url,
        data=body,
        headers={"User-Agent": USER_AGENT, "Content-Type": ctype},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        reply = json.loads(resp.read())
    if "media_id" not in reply:
        code = reply.get("errcode", "?")
        hint = ERRCODE_HINTS.get(code, "")
        raise RuntimeError(
            f"material upload failed ({material_type} {file_path.name}): "
            f"errcode={code} errmsg={reply.get('errmsg')}"
            + (f" — {hint}" if hint else "")
        )
    return reply


def create_draft(token: str, article: dict) -> dict:
    url = f"{WECHAT_BASE}/cgi-bin/draft/add?access_token={urllib.parse.quote(token)}"
    payload = json.dumps({"articles": [article]}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        reply = json.loads(resp.read())
    if reply.get("errcode") and reply["errcode"] != 0:
        code = reply["errcode"]
        hint = ERRCODE_HINTS.get(code, "")
        raise RuntimeError(
            f"draft/add failed: errcode={code} errmsg={reply.get('errmsg')}"
            + (f" — {hint}" if hint else "")
        )
    if "media_id" not in reply:
        raise RuntimeError(f"draft/add returned no media_id: {reply}")
    return reply


# =============================================================================
# HTML image-src rewriting
# =============================================================================


IMG_SRC_RE = re.compile(r'(<img\b[^>]*\bsrc=")([^"]+)(")', re.IGNORECASE)


def referenced_images(html: str, work_dir: Path) -> list[Path]:
    """Return the list of local image paths referenced in <img src> that resolve under work_dir."""
    refs: list[Path] = []
    for m in IMG_SRC_RE.finditer(html):
        src = m.group(2)
        if src.startswith(("http://", "https://", "data:")):
            continue
        p = (work_dir / src).resolve()
        try:
            p.relative_to(work_dir.resolve())
        except ValueError:
            continue
        if p.is_file() and p not in refs:
            refs.append(p)
    return refs


def rewrite_img_src(html: str, mapping: dict[str, str]) -> tuple[str, int]:
    """Replace img src values according to mapping ({local_src: remote_url}). Returns (new_html, count)."""
    count = 0

    def _sub(m):
        nonlocal count
        pre, src, post = m.group(1), m.group(2), m.group(3)
        if src in mapping:
            count += 1
            return pre + mapping[src] + post
        return m.group(0)

    return IMG_SRC_RE.sub(_sub, html), count


# =============================================================================
# Orchestrator
# =============================================================================


def parse_frontmatter(text: str) -> tuple[dict, str]:
    try:
        return _parse_frontmatter(text)
    except ValueError as e:
        raise SystemExit(f"[error] draft.md: {e}")


def build_source_url(fm: dict, explicit: str | None) -> str:
    if explicit:
        return explicit
    if fm.get("paper_doi"):
        doi = str(fm["paper_doi"]).strip()
        return f"https://doi.org/{doi}" if not doi.startswith("http") else doi
    if fm.get("repo_url"):
        return str(fm["repo_url"]).strip()
    return ""


def _short(s: str, n: int = 80) -> str:
    s = s.strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def push(
    work_dir: Path,
    draft_md: Path,
    output_html: Path,
    config_path: Path | None,
    token_cache: Path,
    source_url_override: str | None,
    show_cover_pic: int,
    need_open_comment: int,
    only_fans_can_comment: int,
    dry_run: bool,
    force: bool,
) -> int:
    # 1. Load draft.md + output.html
    fm, _body = parse_frontmatter(draft_md.read_text())
    html = output_html.read_text()

    title = (fm.get("title") or "").strip()
    author = (fm.get("author") or "").strip()
    digest = (fm.get("digest") or "").strip()
    cover_relpath = (fm.get("cover") or "").strip()

    if not title or not author or not digest:
        raise SystemExit("[error] draft.md frontmatter missing one of: title / author / digest")
    if len(title) > TITLE_MAX or author_units(author) > AUTHOR_MAX_UNITS or len(digest) > DIGEST_MAX:
        raise SystemExit("[error] frontmatter exceeds WeChat limits — run lint.py first")

    # 2. Manifest
    manifest_path = work_dir / "figures" / "manifest.json"
    manifest: dict = {}
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError:
            manifest = {}

    # 3. Prefer prepared cover from manifest if present, else the raw frontmatter path
    cover_source: Path | None = None
    if "cover" in manifest:
        cover_source = (work_dir / manifest["cover"]["prepared_path"]).resolve()
    elif cover_relpath:
        cand = (work_dir / cover_relpath).resolve()
        if cand.is_file():
            cover_source = cand
    if not cover_source or not cover_source.is_file():
        raise SystemExit(
            "[error] no cover image found.\n"
            "  expected manifest['cover'] or frontmatter 'cover: path/to/cover.{jpg,png}'.\n"
            "  run render.py first."
        )

    # 4. Identify body images referenced in output.html (local paths)
    body_images = referenced_images(html, work_dir)

    # 5. Optional: content_source_url
    source_url = build_source_url(fm, source_url_override)

    # ---- Plan summary -----------------------------------------------------
    print("=" * 60)
    print(f"WeChat push plan {'(DRY RUN)' if dry_run else ''}")
    print("=" * 60)
    print(f"  work dir:   {work_dir}")
    print(f"  title:      {_short(title, 60)}  ({len(title)}/32)")
    print(f"  author:     {author}")
    print(f"  digest:     {_short(digest, 70)}  ({len(digest)}/120)")
    print(f"  cover src:  {cover_source.relative_to(work_dir)}")
    print(f"  body imgs:  {len(body_images)}")
    for bi in body_images:
        try:
            rel = bi.relative_to(work_dir)
        except ValueError:
            rel = bi
        print(f"               - {rel}")
    print(f"  source url: {source_url or '(none)'}")
    print(f"  show_cover_pic:        {show_cover_pic}")
    print(f"  need_open_comment:     {need_open_comment}")
    print(f"  only_fans_can_comment: {only_fans_can_comment}")
    print("=" * 60)

    sentinel = work_dir / ".pushed"
    if sentinel.is_file() and not force:
        print(f"[warn] {sentinel} exists — this work dir was previously pushed.")
        print("       Pass --force to create a new draft anyway (WeChat will accept duplicates).")
        if not dry_run:
            return 2

    if dry_run:
        print("\n[dry-run] skipping WeChat API calls. Article JSON that would be sent:")
        preview_article = {
            "title": title,
            "author": author,
            "digest": digest,
            "content_length": len(html),
            "content_first_200": _short(html, 200),
            "thumb_media_id": "<from cover upload>",
            "content_source_url": source_url,
            "show_cover_pic": show_cover_pic,
            "need_open_comment": need_open_comment,
            "only_fans_can_comment": only_fans_can_comment,
        }
        print(json.dumps(preview_article, indent=2, ensure_ascii=False))
        return 0

    # 6. Live path — credentials + token
    appid, secret = load_credentials(config_path)
    print(f"[auth] appid: {appid[:4]}...{appid[-4:]}  (cred source: {'env' if os.environ.get('WECHAT_APPID') else 'config.yaml'})")
    token = get_access_token(appid, secret, token_cache)
    print(f"[auth] access_token: {token[:6]}...{token[-4:]}")

    # 7. Upload cover as thumb
    print(f"[upload] cover (type=thumb): {cover_source.name}")
    thumb = upload_material(token, cover_source, "thumb")
    thumb_media_id = thumb["media_id"]
    print(f"         thumb_media_id: {thumb_media_id}")

    # 8. Upload each body image as image, build src mapping
    src_mapping: dict[str, str] = {}
    for bi in body_images:
        rel = str(bi.relative_to(work_dir))
        print(f"[upload] body image (type=image): {rel}")
        r = upload_material(token, bi, "image")
        if "url" not in r:
            raise RuntimeError(f"image upload returned no url: {r}")
        src_mapping[rel] = r["url"]
        print(f"         url: {r['url']}")

    # 9. Rewrite <img src> in HTML
    new_html, swapped = rewrite_img_src(html, src_mapping)
    print(f"[html] rewrote {swapped} <img> src(s)")

    # 10. Build article and create draft
    article = {
        "title": title,
        "author": author,
        "digest": digest,
        "content": new_html,
        "thumb_media_id": thumb_media_id,
        "show_cover_pic": show_cover_pic,
        "need_open_comment": need_open_comment,
        "only_fans_can_comment": only_fans_can_comment,
    }
    if source_url:
        article["content_source_url"] = source_url

    print("[draft] POST cgi-bin/draft/add")
    reply = create_draft(token, article)
    draft_media_id = reply["media_id"]
    print(f"[ok]  draft created — media_id: {draft_media_id}")

    sentinel.write_text(json.dumps({
        "pushed_at": int(time.time()),
        "draft_media_id": draft_media_id,
        "title": title,
    }, indent=2, ensure_ascii=False))

    print()
    print("Next: open 公众号 后台 → 素材管理 → 草稿箱 to review and 群发.")
    print("      The skill does NOT auto-publish; you click 群发 in the UI.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Push a rendered WeChat article to the draft box.")
    ap.add_argument("work_dir", help="work/<task_name>_<ts> directory (must contain draft.md and output.html)")
    ap.add_argument("--draft", default=None, help="override draft.md path (default: <work_dir>/draft.md)")
    ap.add_argument("--html", default=None, help="override output.html path (default: <work_dir>/output.html)")
    ap.add_argument("--config", default=None, help="override config.yaml path (default: ~/.config/wechat-science-post/config.yaml)")
    ap.add_argument("--token-cache", default=None, help="override token cache path")
    ap.add_argument("--source-url", default=None, help="override content_source_url (default: derived from paper_doi or repo_url)")
    ap.add_argument("--show-cover-pic", type=int, default=1, choices=(0, 1))
    ap.add_argument("--need-open-comment", type=int, default=0, choices=(0, 1))
    ap.add_argument("--only-fans-can-comment", type=int, default=0, choices=(0, 1))
    ap.add_argument("--dry-run", action="store_true", help="print the plan without making network calls")
    ap.add_argument("--force", action="store_true", help="push even if .pushed sentinel exists")
    args = ap.parse_args()

    work_dir = Path(args.work_dir).resolve()
    if not work_dir.is_dir():
        print(f"[error] not a directory: {work_dir}", file=sys.stderr)
        return 2
    draft_md = Path(args.draft).resolve() if args.draft else work_dir / "draft.md"
    output_html = Path(args.html).resolve() if args.html else work_dir / "output.html"
    config_path = Path(args.config).resolve() if args.config else None
    token_cache = Path(args.token_cache).resolve() if args.token_cache else TOKEN_CACHE_DEFAULT

    for path, label in ((draft_md, "draft.md"), (output_html, "output.html")):
        if not path.is_file():
            print(f"[error] {label} not found at {path}", file=sys.stderr)
            return 2

    try:
        return push(
            work_dir=work_dir,
            draft_md=draft_md,
            output_html=output_html,
            config_path=config_path,
            token_cache=token_cache,
            source_url_override=args.source_url,
            show_cover_pic=args.show_cover_pic,
            need_open_comment=args.need_open_comment,
            only_fans_can_comment=args.only_fans_can_comment,
            dry_run=args.dry_run,
            force=args.force,
        )
    except SystemExit:
        raise
    except urllib.error.HTTPError as e:
        print(f"[error] HTTP {e.code}: {e.reason}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"[error] network: {e.reason}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
