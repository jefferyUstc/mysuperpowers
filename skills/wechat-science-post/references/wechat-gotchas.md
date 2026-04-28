# WeChat Official Account publication gotchas

Hard limits, known error codes, and platform quirks that the skill must
respect. Treat this file as an authoritative checklist, not as style
guidance.

## Character limits (hard)

| Field | Limit | Notes |
|---|---|---|
| title | 64 bytes ≈ 32 Chinese characters | Mobile preview may truncate earlier (26–28 chars). Plan for 24-char core title + optional 6-char tail. |
| author | 8 Chinese characters | WeChat enforces this tighter than most guides say. `references/user-writing-style.md` should state the user's 公众号 author name within this. |
| digest | 120 Chinese characters | This is the "摘要" shown in session / Moments previews. Overrunning is error 45004 on draft creation. Target 100–115 to leave safety margin. |
| body | ~20,000 Chinese characters | Not a hard limit in practice, but posts > 8,000 chars see sharp drop-off in finish-rate. |
| images per article | 10 recommended / 20 max | Beyond this, draft save is slow; readers skim past. |

## Known error codes (from WeChat draft / material API)

| Code | Meaning | Fix |
|---|---|---|
| `40001` | Invalid access_token | Token cache stale; regenerate with AppID + Secret. |
| `40125` | Invalid appsecret | Wrong AppSecret — copy-paste error, or secret was rotated. |
| `41001` | Missing access_token | Request not authenticated. |
| `45004` | Digest exceeds 120 chars | Trim `digest` in draft frontmatter. Does NOT indicate body-too-long despite the wording — the skill's `lint.py` checks digest specifically. |
| `45008` | Content contains illegal words | Usually political or spam keywords; the skill does not attempt to detect — let WeChat flag on upload. |
| `45166` | Image `media_id` invalid or expired | `media_id` from 临时素材 (type=image) expires in 3 days; use 永久素材 `material/add_material` for article images. |
| `-1` | Server busy | Retry with exponential backoff. |
| `40164` | IP whitelist mismatch | The server calling the WeChat API must be on the whitelist set in 公众号 后台 → 开发 → 基本配置 → IP 白名单. HPC / compute nodes behind a NAT expose their outbound IP — check via `curl ifconfig.me` first. |

## URL substitution trap (`mmbiz.qpic.cn`)

When an image is uploaded to WeChat, you get back two kinds of identifiers:

- **`url`** — a `https://mmbiz.qpic.cn/mmbiz_jpg/...` CDN URL, usable in
  HTML `<img src="...">`.
- **`media_id`** — an opaque WeChat asset ID. Required for the `draft`
  API's `thumb_media_id` (cover image).

**These are not interchangeable.** Using a `mmbiz.qpic.cn` URL as
`thumb_media_id` fails with a cryptic error. Using a `media_id` in an
HTML `<img>` src renders as broken. The skill's `push_draft.py` must
keep them in separate fields:

- `thumb_media_id` → from `material/add_material` with `type=thumb`
- body `<img>` URLs → from `material/add_material` with `type=image`

One image uploaded twice (once as thumb, once as image) yields two
different identifiers.

## Inline CSS is mandatory

WeChat's editor strips `<style>` blocks and most `<link rel="stylesheet">`.
All styling must be inline on each element:

```html
<p style="font-size: 17px; line-height: 1.75; color: #333;">...</p>
```

The skill's `render.py` uses `premailer` to inline CSS from
`themes/<name>.css` onto every element before emitting `output.html`.
Do NOT hand-author `<style>` blocks in `draft.md` — they will render on
preview and silently disappear on WeChat.

Tags that WeChat supports reliably:

- block: `p`, `h1`–`h6`, `blockquote`, `pre`, `ul`, `ol`, `li`, `table`, `tr`, `td`, `hr`
- inline: `a`, `strong`, `em`, `code`, `img`, `br`, `span`

Tags WeChat strips or mangles:

- `script`, `style`, `iframe`, `video` (videos need a special WeChat player embed)
- `form`, `input`, `button`
- most HTML5 semantic tags (`article`, `section`, `aside`) are converted
  to `div` or stripped

## Image spec recommendations

| Role | Aspect | Min dimension | Max file | Notes |
|---|---|---|---|---|
| Cover (封面) | 2.35:1 (landscape) | 900 × 383 | 5 MB | Aspect is enforced in draft preview; WeChat crops wrong aspects. |
| In-article | any | 640 × 360 | 2 MB | Width > 1080 is wasted; mobile displays 750 logical pixels max. |
| GIF | any | — | 2 MB | GIF `media_id` can be used directly; use sparingly. |

The skill's `figures_prep.py` enforces max 1080 px width and
≤ 1 MB per image.

## Draft creation flow

The `cgi-bin/draft/add` endpoint requires one article object per draft
(the skill always creates single-article drafts, not bundled):

```json
{
  "articles": [{
    "title": "...",
    "author": "...",
    "digest": "...",
    "content": "<html body>",
    "content_source_url": "<optional external link>",
    "thumb_media_id": "<media_id from 永久素材>",
    "show_cover_pic": 1,
    "need_open_comment": 0,
    "only_fans_can_comment": 0
  }]
}
```

Response gives a top-level `media_id` (the draft's id), which is used
for `draft/get`, `draft/update`, `draft/delete`, or `freepublish/submit`.

The skill **never** auto-publishes. `push_draft.py` stops at creating
the draft; the user must click 群发 in the WeChat admin UI.

## Originality declaration

Claiming 原创 on an article that is a 解读 of someone else's paper is
not strictly forbidden by WeChat, but it is ethically dubious. The
skill's `draft.md` frontmatter does NOT set `need_open_comment` to
enable 原创 — the user must do that manually in the editor if they
genuinely believe the 解读 is original commentary (which is often the
case for a substantive Chinese walkthrough of an English paper).

Guidance from the skill's attribution block in `science-post-patterns.md`
treats the article as 解读, not 原创: the footer explicitly credits the
paper and repo.

## AppID / Secret / whitelist bootstrap

First-time users must:

1. Log into 微信公众平台 → 开发 → 基本配置
2. Generate AppSecret (one-time reveal; save immediately to a password
   manager)
3. Add the outbound IP of the server running `push_draft.py` to the IP
   whitelist. For HPC nodes with dynamic NAT egress IPs, this may
   require your IT to assign a static outbound IP or forward through a
   bastion.
4. Export as env vars or write to `~/.config/wechat-science-post/config.yaml`:
   ```yaml
   wechat:
     appid: "wx..."
     secret: "..."
   ```
   `chmod 600` afterward.

For users whose server has dynamic IPs and cannot get a static egress:
use the skill up to `[10] Preview` only, then manually copy-paste
`output.html` into the WeChat 编辑器 web UI. This is a valid
workflow — you lose `[11]` automation, keep everything else.
