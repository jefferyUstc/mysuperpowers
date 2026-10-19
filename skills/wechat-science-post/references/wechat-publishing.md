# Publishing on WeChat

## Limits (lint and push enforce these)

| Field | Limit | Notes |
|---|---|---|
| title | 32 characters | mobile lists truncate around 26–28; front-load the core |
| author | 8 汉字 / 16 ASCII | |
| digest | 120 characters | over → errcode 45004 on draft creation |
| body | no hard limit | finish rate drops past ~8,000 汉字 |
| images | ≤ 20 per article | render.py sizes them to ≤ 1080 px, ≤ 1 MB |
| cover | 2.35:1, ≥ 900×383 | WeChat crops other ratios |

The editor keeps only inline styles; render.py inlines the theme with premailer and wraps the fragment in a `<section>`. It strips `script`, `style`, `iframe`, `form`, `input`, `button`. Math must be prose, unicode, or an image.

## Pushing a draft

`push_draft.py` uploads the cover as a permanent `thumb`, each body image as a permanent `image` (rewriting `<img src>` to the returned `mmbiz.qpic.cn` URL), sets 阅读原文 to the DOI or repo URL, and calls `draft/add`. It never calls publish; the user clicks 群发 in the web UI. A `.pushed` file in the work dir records the draft id; `--force` pushes again.

Credentials, in lookup order:

1. `WECHAT_APPID` and `WECHAT_SECRET` environment variables
2. `~/.config/wechat-science-post/config.yaml`, mode 600:
   ```yaml
   wechat:
     appid: "wx..."
     secret: "..."
   ```

The calling machine's outbound IP (`curl ifconfig.me`) must be on the whitelist: 公众号后台 → 设置与开发 → 基本配置 → IP 白名单.

## Error codes

| Code | Meaning | Fix |
|---|---|---|
| 40001 | access_token invalid | cache is purged; re-run |
| 40125 | wrong AppSecret | re-copy it, or it was rotated |
| 40164 | IP not whitelisted | add the outbound IP |
| 45004 | digest over 120 characters | shorten `digest` |
| 45008 | content flagged by moderation | reword; the skill cannot predict this |
| 45166 | media_id invalid | images must be permanent material (the script does this) |
| -1 | server busy | retry |

## Rights

Reproducing a paper's figures in commentary is usually tolerated, more safely under CC-BY licenses (bioRxiv shows the license on every page). The attribution line credits paper, journal, DOI and code. Marking a 解读 as 原创 is the user's call in the editor.
