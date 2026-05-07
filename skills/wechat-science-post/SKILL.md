---
name: wechat-science-post
description: Use when drafting a Simplified-Chinese WeChat Official Account (微信公众号) science-explanation article from a GitHub repo, one or more local PDF files (the user must supply PDFs themselves; v0.1 dropped automatic resolvers), or both together. Triggers include "写公众号", "公众号推文", "科研解读", "介绍这个 repo 准备发公众号", "把这篇 PDF 写成科研解读", or any request to turn a code/paper artifact into a Chinese-language WeChat article. Symptoms: user pastes a repo URL or attaches a paper PDF and asks for an article, or mentions 公众号 / 推文 / 科普文.
---

# WeChat science post — gated co-writing workflow

This skill turns a research artifact (code repo, paper, or both) into a finished WeChat Official Account article that explains the science to a Chinese-reading audience. The writing is done by Claude under structured prompts; the scripts only do fuel delivery (ingest, regularize) and finishing (lint, render, push).

## Rule #1 — Output language policy (READ FIRST)

**Every artifact intended for the user — section drafts, titles, hooks, image captions, `questions-to-user.md`, the final article — MUST be written in Simplified Chinese**, with the following categories kept in their **original English** form (do NOT translate, do NOT transliterate into Chinese characters):

| Category | Examples |
|---|---|
| Algorithm / method / model / package names | `Harmony`, `Scanpy`, `UMAP`, `BERT`, `scVI`, `ChIP-seq`, `CellRank` |
| Person names (authors, PIs, cited researchers) | `Ilya Korsunsky`, `Fabian Theis`, `Peter Kharchenko` |
| Paper titles | Keep English as-is; use Chinese in surrounding narrative |
| Journal names | `Nature`, `Nature Methods`, `Cell`, `Science`, `Nature Genetics` |
| Gene / protein / dataset / accession | `TP53`, `CD4+ T cell`, `PBMC-10X`, `TCGA`, `GSE12345`, `GTEx` |
| Software / libraries / file formats | `PyTorch`, `R 4.3`, `anndata`, `.h5ad`, `CUDA`, `Docker` |
| Stats terms where the English is more recognizable to a research audience | `p-value`, `AUC`, `ROC`, `log-fold-change`, `silhouette score` |
| Repo names, URLs, DOIs, any identifier string | always literal, never translated |

Narrative connective tissue, explanations, analogies, transitions, section headings, summary paragraphs, CTA — all in Simplified Chinese.

Correct example:
> Harmony 的核心思路是在每个迭代里先做 soft clustering,再按 batch 标签计算每个 cluster 的 centroid 偏移,把样本往"去除 batch 效应后的位置"拉。
> 作者 Ilya Korsunsky 把代码开源在 GitHub 上 (`immunogenomics/harmony`),配套发表在 `Nature Methods` 2019。

Incorrect (do NOT do this):
> 和谐算法的核心是迭代式软聚类... (translating `Harmony`)
> 科松斯基等人... (transliterating the author's name into Chinese)

This rule propagates down: every prompt under `prompts/` that instructs Claude to produce user-facing text MUST repeat this policy. Claude must treat it as a hard rule, not a suggestion.

## When to use this skill

Trigger phrases:

- "write a 公众号 article about this paper / this repo"
- "给我写一篇解读 <paper> 的公众号推文"
- "介绍一下这个 repo,准备发公众号"
- "把 <arXiv id / DOI / PDF path> 写成一篇科研解读"
- "根据 <repo url> 和 <paper> 写篇推文"

## When NOT to use

- User wants a general blog post, not a WeChat Official Account article (layout constraints differ — use a general writing skill instead).
- User wants a Xiaohongshu 小红书 image-first post (different medium, use a separate skill).
- User wants a paper review in a professional register (peer-review tone, not 公众号 tone).
- Paper is behind a hard paywall and user has no PDF (skill cannot ingest; ask user to provide the PDF first).

## Core principles

1. **Prompts are the IP; scripts are fuel.** Every non-trivial judgment — what to emphasize, how to phrase, which figure to lead with, what analogies to use — is made by Claude under a specific prompt in `prompts/`. Scripts only ingest, regularize, and finish.
2. **Mode-specific article structure.**
   - **Paper mode**: 总览 → figure-by-figure (paper's own order) → 结论. The figure-centric walk mirrors how a careful reader re-reads a paper and gives the reader a path back to the original.
   - **Repo mode**: 总览 → algorithm steps → formulas / objective functions → code examples (with output images from executed `.ipynb`) → 结论. Method-walkthrough style for academic readers; NOT a tool-tutorial.
   - **Combined mode**: paper-mode shape, but each `method`-class figure section is expanded (500–900 chars) to include algorithm steps + formulas + a code anchor. No standalone "上手试试" section — code lives inside the method figures themselves.
3. **Confirm-first.** Before drafting, the user must explicitly approve: Python interpreter (`[0a]`), inputs (`[0b]`), task name (`[0c]`), title + hook + outline (`[3]`). No silent defaults.
4. **Uncertainty is reported, not hidden.** If Claude cannot determine what a figure panel shows, what a symbol means, or what a number is, it writes `[UNCERTAIN: ...]` in the draft and appends to `questions-to-user.md`. It does NOT guess.
5. **Numbers are quoted, not paraphrased.** Every numeric claim in the draft must trace to a specific sentence in caption / methods / results. Rephrased ranges are allowed; invented precision is not.
6. **The skill does not claim authorship of the paper.** Articles are positioned as 解读 (interpretive exposition) with mandatory attribution to the paper, authors, journal, and code repo. Figure usage is flagged as potentially requiring permission (see `references/wechat-gotchas.md`).

## Workflow (9 numbered steps + 1 mode-conditional sub-step `[4.5]` for paper / combined figure auto-extract)

All artifacts live under `work/<task_name>_<timestamp>/` so a failed run is `rm -rf`-able.

### [0a] Environment & preflight (NOT optional)

This skill needs a Python env with `pymupdf`, `pyyaml`, `Pillow`, `markdown-it-py`, `premailer` (and `git` on PATH for repo mode). Use **conda** to manage it. Don't silently default; resolve `$PY` deliberately at the start of every run.

#### Sub-step A — choose how to handle the env

Ask the user:

```
This skill needs a conda env with the deps in $SKILL_DIR/environment.yml.
Pick one:
  (1) use an EXISTING conda env (give me its name or absolute path)
  (2) CREATE a fresh env from environment.yml (I'll run conda env create)
```

Wait for explicit `Y`. Do not silently default.

#### Sub-step B — resolve `$PY`

**For (1)** — user gives `<env-name-or-path>`:

```bash
"$PY" = "$(conda run -n <env> python -c 'import sys; print(sys.executable)' 2>/dev/null)"
# or, given an absolute env path: "$PY" = "<env-path>/bin/python"
```

If the env doesn't exist, fall back to (2).

**For (2)** — agent creates the env:

```bash
conda env create -f "$SKILL_DIR/environment.yml"
```

Echo the env name (`wechat-science-post` per the YAML; let the user override before running). After creation:

```bash
"$PY" = "$(conda run -n wechat-science-post python -c 'import sys; print(sys.executable)')"
```

Echo back to user:

```
Resolved Python: <$PY>
  sys.executable: ...
  sys.prefix:     ...
  python --version: ...
Confirm? (Y/n)
```

#### Sub-step C — preflight imports

```bash
"$PY" -c "import fitz, yaml, PIL, markdown_it, premailer; print('v0.1 deps OK')"
```

If this fails:
- For path (1): the picked env is missing some deps. Run `conda env update -f "$SKILL_DIR/environment.yml" -n <env-name>` to merge them in, then retry preflight.
- For path (2): the env should have all deps; if a particular import fails (most likely `import fitz` with `GLIBCXX_3.4.32 not found`), try `conda install -c conda-forge "libstdcxx-ng>=14"` in the env, OR pin pymupdf to `<1.24`.
- Do NOT proceed past `[0a]` until preflight returns `v0.1 deps OK`.

#### Lock for the session

Once `$PY` is verified, lock the path into the conversation context. Every subsequent script invocation in `[1]` / `[7]` / `[8]` / `[9]` / `[10]` / `[11]` MUST use the same `"$PY"` — do not switch envs mid-run.

### [0b] Confirm inputs

Ask the user which combination applies:

```
What am I writing about?
  (A) GitHub repo only                  → repo mode
  (B) One or more local PDF files       → paper mode
  (C) Both together                     → combined mode

Please give exact identifiers:
  - repo:   <github org/name or URL>
  - paper:  one or more '[id:]<absolute-path-to.pdf>' specs
            (id is alnum/_/-, defaults to "main" for one PDF
             or "paper-1", "paper-2", ... for multiple)
```

v0.1 paper mode accepts ONLY local PDFs (no more arXiv / DOI / bioRxiv resolvers — the user is expected to bring their own PDF). The script verifies each file exists and starts with `%PDF-`.

**Paper-mode argument syntax:**

| Form | Effect |
|------|--------|
| `./paper.pdf` | single PDF, auto-id `main` |
| `main:./paper.pdf` | single PDF, explicit id `main` |
| `./a.pdf ./b.pdf` | two PDFs, auto-ids `paper-1`, `paper-2` |
| `main:./paper.pdf supp:./supp.pdf` | two PDFs, explicit ids |
| `primary:./a.pdf prior:./b.pdf` | typical: one main paper + one prior work |

The id becomes the directory name under `raw/` (`raw/<id>.pdf` + `raw/<id>/page-NNN.txt`), so it must match `[a-zA-Z0-9_-]+`. IDs must be unique within an invocation.

### [0c] Confirm task name

Ask the user for a short slug that identifies this article. The slug becomes a prefix in the work-dir path (`work/<task_name>_<YYYYMMDD-HHMMSS>/`), so it must be filesystem-safe and easy to grep for later.

Prompt:

```
Give this article a short task name (used in the work-dir path).
Format: ASCII lowercase letters, digits, and hyphens; ≤ 40 characters; must not start or end with `-`.
Example: harmony-batch-correction
Your task name?
```

Validate against `^[a-z0-9]([a-z0-9-]{0,38}[a-z0-9])?$`. If validation fails, ask again — do NOT silently coerce.

Once valid, echo back and wait for explicit `Y`:

```
Task name: <task_name>
Work dir: work/<task_name>_<YYYYMMDD-HHMMSS>/   (timestamp at confirmation, local time)
Confirm? (Y/n)
```

Lock the task name and timestamp into the session so every subsequent step writes to the same `work/<task_name>_<ts>/` directory. The article audience is **project-fixed** — see `references/user-writing-style.md § Target audience` — so no per-article audience choice is asked.

### [0d] Confirm the writing-style register is selected and populated

The skill ships a register system: `references/user-writing-style.md` is the
index + universal fields (author name, target audience, forbidden words);
two register-specific templates carry the per-mode voice spec
(`user-writing-style-academic-paper.md` for paper / combined modes,
`user-writing-style-repo-tutorial.md` for repo mode).

Gate checks:

1. **Universal fields filled** in `user-writing-style.md` (no `<FILL IN>` tokens).
2. **Active register selected** for the current article's mode — defaults are:
   - paper / combined → academic-paper register
   - repo → repo-tutorial register
3. **Active register's template file present** at `references/<filename>.md`.
4. **`examples/`** contains at least one anchor for the active register
   (warn-only, not blocking; without anchors, voice drift is likely on the
   first run).

If the user wants to override the default register for this article, they
say so at `[0b]` (e.g., "use repo-tutorial register for this paper article"
— legal, just unusual).

Without this gate, the draft drifts to a generic voice. Do not skip it.

### [1] Ingest (code)

```bash
# repo mode (git clone into local cache, symlink into ingest tree):
"$PY" "$SKILL_DIR/scripts/ingest.py" repo <owner/name or URL> --out work/<task_name>_<ts>/ingest
#   optional: --cache-dir <path>     override default ~/.cache/wechat-science-post/
#   optional: --allow-large          allow repos > 1 GB (rare)

# paper mode (one or more local PDFs):
"$PY" "$SKILL_DIR/scripts/ingest.py" paper [<id>:]<path-to.pdf> [...] --out work/<task_name>_<ts>/ingest
#   examples:
#     paper main:./paper.pdf
#     paper ./paper.pdf                     (auto-id "main")
#     paper main:./a.pdf supp:./b.pdf       (one + supplement)
#     paper primary:./a.pdf prior:./b.pdf   (paper + prior work)

# combined mode (repo + N paper PDFs):
"$PY" "$SKILL_DIR/scripts/ingest.py" combined --repo <owner/name> --paper main:./a.pdf [--paper supp:./b.pdf] --out work/<task_name>_<ts>/ingest
```

**Combined mode positioning:** paper provides the narrative spine (figures dictate section order); repo contributes **algorithm-depth** by expanding `method`-class figure sections to include algorithm steps + formulas + a code anchor (drawn from `cross-ref.md`). Non-method figures stay paper-style. There is no standalone "上手试试" wrap-up — code lives inside the method figure sections themselves.

**Repo caching:** `ingest.py repo` clones to `~/.cache/wechat-science-post/repos/<owner>_<name>/` once, then `git fetch && git reset --hard origin/<default_branch>` on subsequent runs. Network failures during refresh are non-fatal (warn + use cached). The work-dir's `repo_src/` is a symlink into the cache, so deleting `work/<task>_<ts>/` does not invalidate the cache. Repos > 1 GB are rejected by default; pass `--allow-large` to override.

**No paper resolvers:** the skill does not include arXiv / DOI / Crossref / Unpaywall / bioRxiv resolvers. The user is responsible for supplying PDFs (institutional access, author preprint, etc.). This trades convenience for predictability and avoids fragile API coupling.

**No script-side PDF parsing layer:** beyond per-page text dump, `ingest.py paper` does NOT extract sections, figure captions, or per-figure paragraph excerpts in script code. Per-page text comes from `pymupdf` block-level extraction sorted left-column-then-right-column-then-wide-blocks to recover correct narrative flow on 2-column journal layouts. The `read-and-propose` / `write` / `cross-ref` prompts identify abstract / intro / methods / results / figure captions semantically by reading the per-page text files directly. This avoids the brittleness of regex-based section detection (which fails on CS / math papers, panel-level figure references, supplementary figures, two-figure-on-one-page layouts).

**What is NOT in the ingest tree:** figure images from PDFs. Publisher PDFs encode figures as either many small image fragments (Springer / Nature encode a single "figure" as 50–100 PNG / JP2 slices) or vector content that pypdf cannot meaningfully extract. The skill expects the user to manually screenshot the figures they want into `work/<task>_<ts>/figures/cover.<ext>` and `work/<task>_<ts>/figures/fig-N/image.<ext>`; `figures_prep.py` then regularizes them.

**Code-example output images (repo / combined mode):** for the spine `.ipynb` notebook that was executed before the article run, embedded image outputs ARE extractable. Step `[5a]` (between the article writing in `[3]` and `figures_prep.py` in `[5b]`) calls:

```bash
"$PY" "$SKILL_DIR/scripts/notebook_outputs.py" \
    work/<task>_<ts>/ingest/repo_src/path/to/spine-notebook.ipynb \
    --out work/<task>_<ts>/figures/code-example-1/
```

This writes per-cell source text + per-cell PNG outputs + a `manifest.json` index for **all cells** of the spine notebook. The article(written in `[3]`) emits `<!-- IMG:code-example-1-cell-M-K -->` placeholders that `figures_prep.py` later resolves. For source-walkthrough mode (no spine notebook), this step is skipped — the article relies on cover + manually supplied figures only.

Output structure (repo mode):

```
ingest/
  repo.json              # GitHub metadata + size + local_clone path
  repo_src/              # symlink to ~/.cache/wechat-science-post/repos/<o>_<n>/
  repo_tree.txt          # 2-level navigation listing (full tree via repo_src/)
  paper_refs.md          # any arXiv / DOI / bioRxiv references found in README
  questions-to-user.md
```

Output structure (paper mode):

```
ingest/
  paper.json             # manifest: per-paper id / pdf path / pages_dir / sha256 / pdf_metadata
  raw/
    <id>.pdf             # original PDF copy (e.g. main.pdf, supp.pdf)
    <id>/
      page-001.txt       # pypdf-extracted text for page 1
      page-002.txt
      ...
      page-NNN.txt       # may be 0 bytes for image-only pages (typical for figure-only pages)
  questions-to-user.md
```

Output structure (combined mode):

```
ingest/
  repo.json              # \
  repo_src/              #  \  same as repo mode
  repo_tree.txt          #  /
  paper_refs.md          # /
  paper.json             # \
  raw/<id>.pdf           #  \  same as paper mode (one or more PDFs)
  raw/<id>/page-*.txt    #  /
  combined.json          # marker file (no auto cross-link signals; cross-ref prompt does its own correlation)
  questions-to-user.md
```

Gate: `ingest/` exists and the appropriate manifest JSON (`repo.json` and/or `paper.json`) is non-empty.

### [2] Read & propose (Claude)

Claude reads `prompts/read-and-propose.prompt.md`, operates on the ingest tree, and writes:

- `notes.md` — free-form reading notes (paper / repo understanding, figure inventory, proposed article approach with title + hook + structure + length estimate, hype flags). The structure of `notes.md` is set by the source's narrative, not a rigid schema.
- `questions-to-user.md` — any technical term, symbol, experimental detail, or substantive structure decision the user should sign off on before writing.

This step replaces the old separate `[2] scan` + `[3] plan` flow. Combining them gives the LLM room to propose a structure that fits the source's actual narrative (method paper → methods get their own depth; application paper → biology gets the depth; well-organized library → algorithm-first source walkthrough) instead of filling a fixed template.

**Repo + combined modes — shared truth hierarchy.** Source code in `repo_src/` is the gold standard for any implementation claim — README is project context only and must not be quoted as authoritative for behavior. This applies in both repo and combined modes.

**Pure repo mode — article scaffold.** The article picks ONE spine notebook to follow end-to-end (cells in order, imports / data / helpers preserved so reader runnability holds), OR — if no notebooks exist — the article is a source-code walkthrough. Either way, the spine is the repo itself.

**Combined mode — article scaffold.** Combined mode is **paper-driven**: paper figures provide the structural spine. Repo content (read deeply at this step) shows up later in `[3] write` as code anchors inside method-class figure sections, drawn from `cross-ref.md §3 / §4`. Combined mode does NOT scaffold on a notebook; reader runnability is not a contract here. The article's purpose is paper interpretation enriched by code, not a library tutorial.

Gate: the user answers / N/As every question in `questions-to-user.md` AND confirms (or amends) the proposed approach in `notes.md` (title pick, hook pick, structure adjustments). **Pure repo mode**: also confirm or override the spine notebook pick. Do NOT proceed past this gate without explicit confirmation.

### [2.5] Cross-ref (Claude) — combined mode only

Only runs when `work/<task_name>_<ts>/ingest/combined.json` is present (i.e., the user ran `ingest.py combined`).

Claude reads `prompts/cross-ref.prompt.md` and operates on the merged ingest tree — `paper.json` (with PDF metadata) + per-page text under `raw/<id>/page-NNN.txt` (read enough pages to identify the abstract / methods / algorithm description) + `repo.json` + the live source under `repo_src/` (use Read / Glob / Grep on actual files: README, main package directory, examples/, tests/) + `repo_tree.txt` for navigation. Writes:

- `cross-ref.md` — **standalone algorithm deep-dive**, not a per-figure lookup table. Sections: alignment class (A–E), algorithm summary, core entry points, algorithm-step↔code mapping (at step level, only where code evidence exists), formulas / objective functions, reproducibility entry, discrepancies / version skew, explicit NOT-claim guardrails.

Design principle: **a repo typically implements one algorithm, not one per figure**. The deep paper↔repo correspondence is isolated in this step partly because the anti-fabrication discipline (never name a function/class you didn't see in `repo_src/`) is too easy to lose if it folds into the writing step.

`[3] write` quotes from `cross-ref.md` when emitting code anchors in method-class figure sections (combined mode); never improvises function names.

Gate: cross-ref.md exists. If alignment class is D (loosely related) or E (tangential), Claude surfaces this to the user and asks whether the article should still claim a meaningful paper↔repo connection.

### [3] Write (Claude)

Claude reads `prompts/write.prompt.md` and produces `draft.md` in one stretch. Inputs:

- `notes.md` — central thesis, proposed structure, hype flags, figure inventory (with page numbers for targeted page reads)
- `questions-to-user.md` — answered; user answers are authoritative
- `cross-ref.md` (combined mode only) — for code anchors and formulas
- `ingest/paper.json` + `ingest/raw/<id>/page-NNN.txt` (re-read targeted pages as the article passes through them)
- `ingest/repo_src/` (repo / combined mode) — for accurate function/class names + example details
- `references/user-writing-style.md` — voice, term-handling, length budget, person-of-address
- `references/science-post-patterns.md` + `examples/published-article-*.md` — narrative reference patterns and few-shot voice anchors

This step replaces the old separate `[4] per-figure deep-read` + `[5] draft` flow. There are no `fig-N.md` intermediate files. Claude writes the article top-to-bottom, with internal coherence guaranteed by single-pass authorship rather than by stitching pre-written fragments.

Hard constraints (the prompt enforces these):
- Frontmatter: title ≤ 32, digest ≤ 120, author ≤ 8 chars; mandatory metadata fields populated from `paper.json.pdf_metadata` or page-001
- Body length 3000–9000 raw chars (typically 5000–8000); section length set by content density not a per-section budget
- No LaTeX `$$..$$`; no forbidden HTML; no unresolved placeholder tokens
- Bottom attribution is ONE line — no `## 解读者` / `## 说明` sections
- Image placeholder format `<!-- IMG:<id> -->`; ID is `1`, `2`, ... for paper figures, `formula-N` for screenshot formulas, `code-example-N-cell-M-K` for repo notebook outputs
- Combined mode: code anchors only name functions/classes that appear in `cross-ref.md`

Gate: user reviews `draft.md`. Issues → `[4] revise`. Clean → `[5] figures_prep`.

### [4] Revise (Claude, iterative)

Claude reads `prompts/revise.prompt.md`. Revision is targeted: the user points to a specific paragraph / phrase / number; Claude edits only that and leaves the rest untouched. Pointer types include section name (`总览段`, `Figure 3 section`, `结论`), paragraph number, quoted phrase, line range, or image placeholder ID. After 5+ revisions on the same section, the prompt asks the user whether to rerun `[3] write` for that section instead of patching further.

### [4.5] Figure extract (Claude, paper / combined modes only)

Claude reads `prompts/figure-extract.prompt.md` and orchestrates a Vision-LLM-driven crop for every `<!-- IMG:N -->` placeholder where `N` is an integer (paper figures). For each:

1. Render the source PDF page at 300 DPI via `scripts/figure_extract.py page-image` → PNG in `figures/_pages/`
2. `Read` the rendered PNG (multimodal); identify the figure's bounding box visually
3. `scripts/figure_extract.py crop` saves the bbox region to `figures/fig-N/image.png`

The Vision LLM (Claude) provides the bbox; the script does deterministic IO (render + crop). Cropped images go through `[5] figures_prep` for WeChat sizing (≤ 1080 px wide).

**Resolution**: 300 DPI gives a ~2481×3296 px page for a US-letter PDF; a figure occupying ~half the page crops to ~1240×1650 px, comfortably above the 1080 px WeChat target. `--dpi 400` available for very fine panel labels; below 200 DPI degrades both LLM-vision accuracy and final crop quality.

**Skip in repo mode**: code-example outputs come from `[5a] notebook_outputs.py`.

**User override**: if `figures/fig-N/image.<ext>` already exists, the prompt skips that figure and uses the user-supplied screenshot. Auto-extract is opt-out per figure.

**Cover handling (all modes — paper / repo / combined)**: writes a creative English image-generation prompt to `figures/cover-prompt.txt` (Claude crafts it from `notes.md` central thesis) AND generates a 1280×545 px light-gray placeholder at `figures/cover.png` (via `figure_extract.py placeholder-cover`) so `[5]` / `[6]` pass without blocking. User pastes the prompt into their preferred image-gen tool (DALL-E / ChatGPT / MidJourney / 文心一格 / 通义万相 / Stable Diffusion / etc.) and replaces `cover.png`. The cover prompt is English-only; the generated image must contain no text (visual metaphor only). Skipped entirely if user pre-supplied `figures/cover.<ext>`.

**Fallback to manual**: after 2 retries on the same figure, the prompt halts with a "manual screenshot needed" message; user places `figures/fig-N/image.<ext>` and re-runs `[5]`.

### [5] Figures prep (code)

```bash
"$PY" "$SKILL_DIR/scripts/figures_prep.py" work/<task_name>_<ts>/
```

- Reads `work/<task_name>_<ts>/figures/cover.{png,jpg,...}` and `work/<task_name>_<ts>/figures/fig-N/image.*`
- Resizes body images to ≤ 1080 px width; cover kept up to 2048 px (WeChat accepts larger covers and crops to 2.35:1)
- Steps JPEG quality 90 → 60 until each image is ≤ 1 MB; hard fails at 2 MB ceiling
- Preserves alpha-meaningful body images as PNG; cover is always JPEG
- Writes `work/<task_name>_<ts>/figures/prepared/*` and `work/<task_name>_<ts>/figures/manifest.json`

**Repo / combined mode — extracting spine-notebook cell outputs first**: if `notes.md § Notebook inventory` names a spine notebook(repo articles use exactly one spine, no supplements), extract every cell from that notebook **before** `figures_prep.py`:

```bash
"$PY" "$SKILL_DIR/scripts/notebook_outputs.py" \
  work/<task_name>_<ts>/ingest/repo_src/<tutorials-dir>/<spine-notebook>.ipynb \
  --out work/<task_name>_<ts>/figures/code-example-1
```

(No `--cells` filter — extract everything; the article scaffolds on the entire spine.)

`code-example-1/` will contain `cell-M-source.txt` + `cell-M-img-K.png` for each cell with output. `figures_prep.py` regularizes these into `prepared/code-example-1-cell-M-K.jpg` and writes manifest entries that `[7] render` resolves against `<!-- IMG:code-example-1-cell-M-K -->` placeholders in the draft. `M` is the unpadded cell index.

If the repo has no notebooks(source-walkthrough mode declared in `notes.md`), skip notebook extraction entirely; the article will not emit `code-example-*` placeholders. Skipping notebook extraction when a spine WAS declared is the most common silent failure mode for repo articles — `[6] lint` warns on it but does not hard-fail.

### [6] Lint (code)

```bash
"$PY" "$SKILL_DIR/scripts/lint.py" work/<task_name>_<ts>/draft.md
```

Hard gates (from `references/wechat-gotchas.md`):

- title ≤ 32 characters, author ≤ 8 characters, digest ≤ 120 characters (error 45004 defense)
- either `paper_doi` or `repo_url` present in frontmatter
- no `<script>` / `<style>` / `<iframe>` / `<form>` / `<input>` / `<button>` in body
- no LaTeX `$$..$$` blocks (WeChat does not render math)
- every `![](path)` image reference resolves; every `<!-- IMG:<id> -->` placeholder has a `figures/manifest.json` entry
- cover exists, ≥ 900×500, near-2.35:1 aspect (within ±15%)
- no unresolved `[NUM?]` / `[TERM-N]` / `[PANEL-?-UNCLEAR]` / `[UNCERTAIN]` / `[FORMULA-IMG-MISSING]` placeholders

Warnings (non-blocking):

- body length below 3000 or above 9000 chars
- digest above 115 chars (safety margin, hard fail at 120)
- hype-flag words from `notes.md § Hype flags` appearing verbatim in body

### [7] Render (code)

```bash
"$PY" "$SKILL_DIR/scripts/render.py" work/<task_name>_<ts>/draft.md --theme default
# default output: work/<task_name>_<ts>/output.html  (body-only fragment for WeChat paste)
# add --wrap to emit a standalone HTML doc instead (for browser preview)
# add --out <path> to override the filename — but path MUST stay in work_dir root
```

**Path contract**: `--out` must be in the same directory as `draft.md` (i.e., the work_dir root that contains `figures/`). Rendered HTML references `figures/prepared/...` as a single relative path; that resolves only when the output sits next to `figures/`. Subdirectory outputs are rejected (render.py exits non-zero with a clear error). To compare themes, render with different filenames at the root:

```bash
render.py draft.md --theme default       --out work_dir/output.html
render.py draft.md --theme dark-mono     --out work_dir/output-dark.html
render.py draft.md --theme paper-texture --out work_dir/output-paper.html
```

All three coexist as siblings of `figures/`; image paths work in all three; preview.py serves any of them without configuration.

- `markdown-it-py` for CommonMark + tables + strikethrough
- Replaces `<!-- IMG:N -->` placeholders using `figures/manifest.json`
- `premailer` inlines `themes/<name>.css` onto every element (with `keep_style_tags=False`)
- Defensive strip of `<script>` / `<style>` / `<iframe>` / `<form>` / `<input>` / `<button>` after inlining
- Output is a self-contained HTML fragment (body-only by default); paste into the WeChat 编辑器 directly

### [8] Preview (code)

```bash
"$PY" "$SKILL_DIR/scripts/preview.py" work/<task_name>_<ts>/output.html
# --port <N>   bind a specific port (default: random free port)
# --no-open    print URL, do not launch browser
```

Starts a local HTTP server in the draft directory and opens a wrapper page that iframes `output.html` at 375 px width (iPhone SE mobile). Works on body-only fragments (browser supplies the default shell). Ctrl-C shuts down and cleans up the wrapper file.

### [9] Push to WeChat draft (optional, code)

```bash
# dry-run first — does everything except network calls, prints the plan:
"$PY" "$SKILL_DIR/scripts/push_draft.py" work/<task_name>_<ts> --dry-run

# live push (requires credentials + IP whitelist):
"$PY" "$SKILL_DIR/scripts/push_draft.py" work/<task_name>_<ts>
#   --draft <path>              override draft.md location
#   --html <path>               override output.html location
#   --config <path>              override config.yaml location
#   --source-url <url>           override content_source_url (default: derived from paper_doi or repo_url)
#   --show-cover-pic 0|1         (default 1)
#   --need-open-comment 0|1      (default 0)
#   --only-fans-can-comment 0|1  (default 0)
#   --force                      re-push even if work/<task_name>_<ts>/.pushed sentinel exists
```

Credentials (resolved in this order):

1. `$WECHAT_APPID` + `$WECHAT_SECRET` environment variables, OR
2. `~/.config/wechat-science-post/config.yaml` with `chmod 600`:
   ```yaml
   wechat:
     appid: "wx..."
     secret: "..."
   ```

The server's outbound IP must be on the 公众号 后台 IP whitelist (开发 → 基本配置). Verify with `curl ifconfig.me`.

What push_draft.py does:

1. Parses `draft.md` frontmatter for title / author / digest / cover / paper_doi / repo_url.
2. Reads `output.html` (rendered body-only fragment from `[9]`).
3. Reads `figures/manifest.json` to find the prepared cover.
4. Fetches / refreshes WeChat `access_token` (cached under `~/.cache/wechat-science-post/token.json` with 7200 s expiry).
5. Uploads the cover as `永久素材 type=thumb` → `thumb_media_id`.
6. Uploads each body `<img>` referenced in `output.html` as `永久素材 type=image` → `mmbiz.qpic.cn` URL.
7. Rewrites `<img src>` in the HTML to the mmbiz URLs.
8. Derives `content_source_url` from `paper_doi` (preferred) or `repo_url` — gives readers a working 阅读原文 link.
9. POSTs the article to `cgi-bin/draft/add`.
10. Writes `work/<task_name>_<ts>/.pushed` sentinel with the returned draft `media_id` so re-runs warn about duplicates.

**Never auto-publishes.** `push_draft.py` only creates drafts; the user opens 公众号 后台 → 素材管理 → 草稿箱 and clicks 群发 manually.

If credentials are missing, `--dry-run` still works end-to-end: it parses everything, identifies uploads that would happen, and prints the exact article JSON that would be POSTed — useful for review before wiring up production credentials.

## Rollback

All state lives under `work/<task_name>_<timestamp>/`. A failed run is cleared with `rm -rf work/<task_name>_<timestamp>/`. No external state is mutated before `[9]`; step `[9]` is append-only (creates a new draft, does not overwrite existing ones).

## Defaults (v0.1)

| Decision | Default | How to override |
|---|---|---|
| Input mode | any of repo / paper / combined | `[0b]` picks at start |
| Task name | (none — required at `[0c]`) | answer at `[0c]`; locks the work-dir path |
| Audience (fixed) | academic researchers; every section must convey both the high-level scientific framing and the low-level methodology | not configurable; see `references/user-writing-style.md` |
| Uncertainty threshold | **strict** — stop and ask on any unfamiliar term, symbol, or experimental detail | set `STRICTNESS=medium` env var (NOT recommended) |
| Theme | `wechat-elegant.css` | `--theme <name>` on render.py |
| Render output mode | body-only fragment (paste-ready) | `--wrap` for standalone HTML doc |
| Draft push | skipped unless AppID/Secret are configured | configure per step `[9]`; `--dry-run` works without credentials |
| Figure handling | user manually screenshots from the source PDF into `work/<task_name>_<ts>/figures/cover.*` and `work/<task_name>_<ts>/figures/fig-N/image.*`; `figures_prep.py` regularizes for WeChat | n/a — v0.1 does not auto-extract figures from PDFs (extraction quality was unusable) |

## Files

- `SKILL.md` — this file; pipeline + gates + policy.
- `scripts/ingest.py` — single dispatcher with three subcommands: `repo` (git clone + symlink), `paper` (validate N local PDFs, extract per-page text via `pymupdf` block-level + column-aware sort), `combined` (repo + N PDFs).
- `scripts/notebook_outputs.py` — extract embedded image outputs from a `.ipynb` (pure stdlib JSON + base64); used by repo / combined modes for code-example sections.
- `scripts/figure_extract.py` — render a PDF page as PNG at given DPI; crop a PNG by pixel bbox. Used by `[4.5]` figure-extract step (Vision-LLM-driven crop) in paper / combined modes.
- `scripts/figures_prep.py` — image regularization for user-supplied figures.
- `scripts/lint.py` — hard gates for WeChat compatibility.
- `scripts/render.py` — Markdown + inline CSS → WeChat-compatible HTML.
- `scripts/preview.py` — local 375 px phone-width browser preview.
- `scripts/push_draft.py` — WeChat draft API client (optional).
- `prompts/read-and-propose.prompt.md` — step `[2]` deep reading + proposed article approach; produces `notes.md` and questions.
- `prompts/cross-ref.prompt.md` — step `[2.5]` combined-mode paper↔repo correspondence + algorithm deep-dive.
- `prompts/write.prompt.md` — step `[3]` write the full article in one stretch; produces `draft.md`.
- `prompts/revise.prompt.md` — step `[4]` targeted edits to draft.md.
- `prompts/figure-extract.prompt.md` — step `[4.5]` Vision-LLM-driven figure auto-extract for paper / combined modes; orchestrates `figure_extract.py` per draft figure placeholder.
- `references/wechat-gotchas.md` — hard limits, error codes, IP whitelist, `mmbiz` URL caveat.
- `references/science-post-patterns.md` — hook taxonomy, 总览 paragraph shape, CTA template, 解读者 identity anchor.
- `references/user-writing-style.md` — index + universal fields (author, contact, target audience, forbidden words); points to the active register template per mode.
- `references/user-writing-style-academic-paper.md` — full register spec for paper / combined modes; modeled after dense-scientific-blog style (rich connectives, third-person, multi-clause syntax, inline `Author Year Journal` citations).
- `references/user-writing-style-repo-tutorial.md` — full register spec for repo mode; modeled after hands-on-tutorial style **plus an algorithm-first discipline** (every code-example section opens with 200–400 chars of statistical / mathematical principle before the API call).
- `themes/<name>.css` — 9 WeChat-compatible themes; pick at render time with `--theme <name>`. All are premailer-safe (no `@media`, `::before`, `:hover`).
  - `default` — minimalist GitHub-blue accent on white; clean fallback.
  - `academic-serif` — classical CJK serif (Songti / 思源宋体), double-rule h1, deep-red 朱 accent.
  - `academic-warm` — sepia / cream paper palette, brown ink, rust accent; old-book reprint feel.
  - `academic-mono` — pure black/white/gray, no accent color; Nature-letter aesthetic.
  - `wechat-bold` — doocs/md "default"-inspired; centered h1 with bottom rule, filled-bg h2, vibrant blue.
  - `wechat-elegant` — doocs/md "grace"-inspired; rounded shadowed h2, italic blockquote, teal accent. **Default when `--theme` is omitted.**
  - `paper-texture` — cream paper bg with SVG-noise grain (data URI), parchment-tag h2, warm sepia.
  - `graph-paper` — engineering-notebook bg with faint blue grid (repeating-linear-gradient), navy ink.
  - `dark-mono` — slate dark bg, light text, cyan-green accent; terminal/coder feel for repo articles. Note: WeChat OA renders pages light by default — preview before publishing.
- `examples/` — user's past-published articles placed here as few-shot anchors (README inside explains the requirement).
- `environment.yml` — conda env spec consumed at `[0a]`; defines `pymupdf`, `pyyaml`, `Pillow`, `markdown-it-py`, `premailer`, plus `python>=3.10` and `git`.
- Versioning: there is no skill-local version file. `scripts/ingest.py` and `scripts/push_draft.py` read the plugin manifest (`.claude-plugin/plugin.json`) at runtime to derive `SKILL_VERSION`, `USER_AGENT`, and the `ingest_version` field stamped into manifest JSON files. The plugin version is the only version — bump it via `./scripts/bump-version.sh <new>` (or `/bump-version` slash command) at the repo root.

## Known limitations

1. **User must supply PDFs.** v0.1 dropped all paper resolvers (arXiv / Crossref / Unpaywall / bioRxiv). For paywalled journals, the user must obtain the PDF through institutional access, author contact, or preprint server.
2. **PDF text-only extraction.** `pymupdf` extracts text accurately for most modern publisher PDFs and resolves multi-column reading order via block-level extraction with bbox-based column sorting. Pure-image pages (e.g. supplementary figure pages) still yield empty `page-NNN.txt` files. Equations rendered as inline math may also extract poorly. The `read-and-propose` / `write` prompts treat these as known degraded cases and ask the user when uncertain.
3. **No automatic figure extraction.** Publisher PDFs encode figures as either many small image fragments (Nature, Springer) or vector content that pypdf cannot meaningfully extract. v0.1 expects the user to manually screenshot the figures into `work/<task>_<ts>/figures/fig-N/image.<ext>`.
4. **Writing-voice drift.** Even with few-shot anchors, Claude may drift between runs. The revise step is built in for this reason; budget time for 2–3 revision passes on the first article.
5. **Novel math / proofs.** For papers with heavy mathematical derivations, Claude's exposition may oversimplify. The 严 (strict) uncertainty threshold catches the worst cases by forcing questions, but the user remains the final sanity check on technical accuracy.
6. **Copyright on paper figures.** Using figures from a published paper in a 公众号 article is a gray area — defensible as 合理使用 / commentary for most journals, but not guaranteed. `references/wechat-gotchas.md` includes the attribution footer the skill auto-inserts.
