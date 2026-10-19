---
name: wechat-science-post
description: Use when drafting a Simplified-Chinese WeChat Official Account (微信公众号) science-explanation article from local paper PDF(s), a GitHub repo, or both. Triggers include "写公众号", "公众号推文", "科研解读", "把这篇 PDF 写成科研解读", "介绍这个 repo 准备发公众号", or a pasted repo URL / attached PDF with a request for an article. The user supplies PDFs; there is no online paper fetching.
---

# WeChat science post

Turn a paper (or a repo, or both) into a finished 公众号 article for academic readers: Simplified-Chinese prose, figures in place, an HTML fragment ready to paste, and a phone-width preview.

Division of labor: **Claude does every judgment** — reading, choosing the angle, structure, prose, and locating figures on a page when a crop is needed. **Scripts do deterministic IO** — PDF text and figure extraction, image sizing, lint, HTML rendering, the WeChat API. Do not ask a script to judge, and do not hand-do what a script does.

## Non-negotiables

These apply to every word the user or reader sees.

1. **Language — you MUST Read `references/language.md` in full before step 2, and again before step 3.** SKILL.md carries only this summary; every language rule lives in language.md (names kept in English, term glossing, voice, sentence length, evidence wording, translationese, the word lists lint checks). Do not write `notes.md`, a title, or any part of `draft.md` without having read it in this session. The core rule: write idiomatic Chinese. Be precise and concise: no rambling, no filler.
2. **Faithful.** Every number traces to a page of the source, and the wording claims exactly what the source claims (`language.md` § 5). Add nothing the source does not say.
3. **Ask, don't guess.** When a term, panel, or number cannot be resolved from the material, ask — with a proposed default.
4. **Standing decisions are recorded, not re-asked.** Content decisions live in `references/editorial-policy.md`, wording decisions in `references/language.md`. Read both before proposing anything and never ask a question they already answer. When the user makes a decision about articles in general rather than this paper, add it to the right file with the date and tell the user in one line.

## Setup

- `S` = this skill's directory. Python: `PY=$(conda run -n wechat-science-post python -c 'import sys; print(sys.executable)')`. If the env is missing, ask once, then `conda env create -f $S/environment.yml`. Preflight: `$PY -c "import pymupdf, yaml, PIL, markdown_it, premailer"`.
- The author name lives in `references/style.md`; if it is empty, ask once and fill it in.
- One article = one work dir `work/<slug>/` (slug: lowercase ASCII from the PDF or repo name, e.g. `scprime-seq`; add `-2` if taken). `draft.md` is the source of truth; everything else is rebuildable.

## Workflow

### 0. Confirm the job (one message)

Settle in a single exchange, skipping anything already unambiguous:

- **Mode.** PDFs only → `paper`; repo only → `repo`; both → `combined`.
- **Several PDFs.** Ask whether they are *one article per paper* (separate work dirs, run everything per paper) or *one article with supplements* (first PDF primary). This changes all later work; never guess.
- **Slug(s)**, proposed, not asked open-ended.

### 1. Ingest

```bash
$PY $S/scripts/ingest.py paper    <main.pdf> [<supp.pdf> ...]              --work work/<slug>
$PY $S/scripts/ingest.py repo     <owner/name | URL>                        --work work/<slug>
$PY $S/scripts/ingest.py combined --repo <owner/name> --paper <main.pdf>    --work work/<slug>
```

Writes `ingest/manifest.json` (mode, title, DOI, venue, figure index with caption pages) and cleaned page text in `ingest/text/<id>/page-NNN.txt` with running headers and line numbers removed. Check the printed summary: page layout, DOI, and that every main figure has a caption page. Repo modes symlink the clone at `ingest/repo_src/`.

### 2. Read and propose → `notes.md` — gate 1

First Read `references/language.md` in full (required, see Non-negotiable 1). Then follow `prompts/read.md` (plus `references/mode-combined.md` or `references/mode-repo.md` for those modes). Then send the user one message: the two-sentence thesis, two or three titles, the section plan with lengths, and the open questions, each with a default. Proceed when the user replies; an unanswered question takes its default.

### 3. Write → `draft.md`

Re-read `references/language.md` in full (required, see Non-negotiable 1). Then follow `prompts/write.md` in one continuous pass, and do its self-check pass over the whole draft.

### 4. Figures

```bash
$PY $S/scripts/figures.py auto  work/<slug>     # paper figures for every <!-- IMG:N --> in the draft
$PY $S/scripts/figures.py cover work/<slug>     # placeholder cover if none exists
```

`auto` saves a figure's embedded image losslessly when its caption page holds exactly one. For any `NEEDS CROP` line, Read the rendered page it names, pick the bounding box of the panels (no caption text, no page header), and run `figures.py crop --src <page.png> --bbox x0,y0,x1,y1 --out work/<slug>/figures/fig-N.png`; Read the result once to confirm. Files already in `figures/` are never overwritten, so a user screenshot always wins.

For the cover, write a one-paragraph English image-generation prompt to `figures/cover-prompt.txt`: a visual metaphor for the thesis, a style and two or three colors, `Aspect ratio 2.35:1 (1280x545)`, `No text, no logos, no faces`. If a figure has a clean schematic panel, `figures.py cover work/<slug> --src figures/fig-1.png --bbox ...` makes a usable interim cover.

Repo mode: `figures.py notebook work/<slug> <spine.ipynb>` saves each output image as `code-example-1-cell-M-K.png` for `<!-- IMG:code-example-1-cell-M-K -->`.

### 5. Render — gate 2

```bash
$PY $S/scripts/render.py work/<slug>/draft.md [--theme wechat-elegant]
```

Runs lint first and stops on errors. Fix errors in `draft.md` and re-run; judge each warning rather than ignoring it. Writes `output.html` (paste into the 公众号 editor) and `preview.html` (open it with `open`). Then report to the user: title, digest, length, figures, whether the cover is still the placeholder, and the absolute paths of the two HTML files.

Themes: `wechat-elegant` (default), `wechat-bold`, `default`, `academic-serif`, `academic-warm`, `academic-mono`, `paper-texture`, `graph-paper`, `dark-mono`.

### 6. Revise

Change only what the user points at; leave every other paragraph byte-identical. A corrected fact is fixed everywhere it recurs. Re-render after each round. If the same section keeps coming back, offer to rewrite that section from `notes.md` instead of patching again. If a requested change would make the article wrong (a number the paper contradicts, a dropped hedge), say so once with the page reference, then do what the user decides.

### 7. Publish (optional)

```bash
$PY $S/scripts/push_draft.py work/<slug> --dry-run   # then without --dry-run
```

Creates a draft in the 公众号 draft box; it never publishes. Credentials, IP whitelist, and error codes: `references/wechat-publishing.md`.

## Files

| Path | Role |
|---|---|
| `prompts/read.md` | How to read the source and what `notes.md` must contain |
| `prompts/write.md` | How to write `draft.md`, frontmatter, and the self-check |
| `references/language.md` | All language rules and the word lists lint reads; **must be read before steps 2 and 3** |
| `references/style.md` | Author, reader, and article structure |
| `references/editorial-policy.md` | The user's standing content decisions; grows over time |
| `references/mode-combined.md` | Paper + repo: how code enters the article |
| `references/mode-repo.md` | Repo-only articles: structure and tutorial voice |
| `references/wechat-publishing.md` | Platform limits, push setup, error codes |
| `examples/` | Past articles as voice anchors |
| `scripts/` | `ingest.py`, `figures.py`, `lint.py`, `render.py`, `push_draft.py` (`common.py` is shared) |
| `themes/*.css` | Render themes; premailer-safe |
