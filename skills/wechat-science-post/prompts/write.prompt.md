# Step [3] — Write prompt

## Your role here

You are the **single-hand author** of the entire article — produced in one stretch from `notes.md` and the ingest tree. You are **not** a per-section stitcher (the prior process was, and voice drifted; that's why this step is one author writing one article). You are **not** a first-time reader either — `[2] read-and-propose` already understood the paper; trust that work.

The goal is **internal coherence + voice consistency** — qualities a stitched-together draft cannot achieve. Write top to bottom in narrative order; re-read targeted pages as you reach them, but commit to one author's voice throughout.

## What this step produces (output contract)

| File | What's in it | Consumed by |
|---|---|---|
| `work/<task>_<ts>/draft.md` | full article: frontmatter + body + one-line bottom attribution | `[4] revise` (surgical edits) → `[6] lint` (hard checks) → `[7] render` |

**Forward reference.** `[4] revise` will edit your draft passage-by-passage based on user pointers — keep section boundaries clean and bridge sentences atomic so surgical edits don't ripple. `[6] lint` will hard-fail on title>32 / digest>120 / unresolved placeholder tokens / hype-flag parroting / LaTeX `$$..$$` — every check below has a corresponding lint rule.

## Hard rules

- **Output language.** Rule #1 applies (Simplified Chinese narrative; English preserved for algorithm / method / package / person / journal / paper-title / gene / dataset / file-format / identifier names). See SKILL.md § Rule #1.
- **One author, one stretch.** Don't decompose to per-section LLM calls. Don't outline-then-fill in two passes. The voice has to come from one continuous act of writing.
- **No fabrication.** Every number traces to a specific page. Every function / class name (combined mode) appears in `cross-ref.md` §3 or §4. Every claim attribution traces to the paper.

- **Repo + combined modes — source code is the gold standard.** Every claim about what the library does (function / class / method names, internal stage / step order, imported third-party libraries, return types, side effects, algorithm semantics) must trace to a specific source file in `repo_src/` that you (or `[2]`) Read. README is project context, not authoritative for implementation. R-side conventions and generic Python ecosystem common sense are NOT licenses to claim about THIS repo's behavior. If you're tempted to write "X works by doing Y" and Y comes from your priors rather than source, **stop and Read the source file first** — or hedge ("according to the README, ...") with that hedge visible to the reader.

- **Repo + combined modes — no silent paraphrase from README.** When prose says "X works by doing Y", Y traces to source. If Y is only available in README, the prose must read "README mentions X works by Y" (or equivalent hedge), and `notes.md` should record that the source verification is missing.

- **Pure repo mode (NOT combined) — spine notebook scaffolds the article (if `notes.md § Notebook inventory` names one).** Code blocks come **verbatim** from the spine notebook **in the notebook's cell order**. Imports, data loading, helper function definitions are included so a reader can copy the article's code blocks in order and run them. Adjacent short cells may be merged; cells without logical role (markdown-only intro cells) may be skipped; but cells must NOT be reordered for narrative convenience. Place a `<!-- IMG:code-example-1-cell-M-K -->` placeholder after each code block whose cell has a saved output image (the spine notebook's `code-example` index is `1`).

- **Pure repo mode (NOT combined) — no-spine fallback (if `notes.md § Notebook inventory` says `source-walkthrough mode`).** The article's structure follows the source code's logical organization (entry point → core algorithm → data flow → extension points). Code blocks are LLM-constructed from the API surface and **explicitly labeled as illustrative** in surrounding prose. Every behavior claim still cites a source file with at minimum the filename and a function / class name; ideally a line range.

- **Combined mode is paper-driven.** The article's structural spine is paper figures (`notes.md § Figure inventory`), NOT a notebook. `method`-class figure sections may include code anchors drawn from `cross-ref.md §3 / §4`(typically a function / class name + file path + 1-3 lines, NOT a full runnable code block). Reader runnability is NOT a contract in combined mode — the article's purpose is paper interpretation, not library tutorial. Do NOT scaffold combined-mode articles on a notebook.

## Inputs (halt if missing)

### Trusted from upstream (don't re-derive)

- `work/<task>_<ts>/notes.md` — `[2]`'s reading notes. **Trust** the central thesis, figure inventory page numbers, hype-flag list, and proposed structure (with user's amendments at the gate).
- `work/<task>_<ts>/questions-to-user.md` — answered. User's answers are authoritative. If any question is unanswered, halt and ask before writing.
- `work/<task>_<ts>/cross-ref.md` — **combined mode only.** **Trust** §3 entry points, §4 algorithm-step↔code map, §4.5 formulas, §7 NOT-claim guardrails. These are anti-fabrication anchors.
- `work/<task>_<ts>/ingest/paper.json` — paper metadata for frontmatter (`pdf_metadata`).

### Verified by you (re-read as you write)

- `work/<task>_<ts>/ingest/raw/<id>/page-NNN.txt` — re-read targeted pages as you reach them in the narrative. Use `notes.md` figure inventory's page numbers; do NOT read sequentially.
- `work/<task>_<ts>/ingest/repo_src/` (repo / combined mode) — for accurate function / class names + example details.
- `references/user-writing-style.md` — INDEX file; identify the active register from its "Active register" table.
- `references/user-writing-style-<active-register>.md` — the authoritative voice spec; **read in full at the start of writing** and apply throughout (hook style, sentence rhythm, citation format, length budget, person-of-address, emoji policy, term-handling).
- `references/science-post-patterns.md` — narrative reference patterns (NOT contracts).
- `examples/published-article-<active-register>-*.md` — few-shot voice anchors for the active register, when present.

## Hard constraints (non-negotiable; lint enforces)

These are real product constraints — WeChat's, the audience's, the lint's. Stay inside them.

### Frontmatter

YAML at the very top. Pull `paper_title` / `paper_doi` / `paper_journal` / `paper_year` from `paper.json.papers[0].pdf_metadata` first; fall back to `raw/<primary_id>/page-001.txt` for fields the metadata lacks. Do NOT fabricate.

```yaml
---
title: "<≤ 32 chars; from notes.md proposed title (user-amended if edited)>"
author: "<≤ 8 chars; from user-writing-style.md author name>"
digest: "<≤ 120 chars; tightened version of the article's central thesis>"
cover: "figures/cover.png"
paper_title: "<exact English title from page-001 or pdf_metadata>"
paper_doi: "<10.xxxx/...>"
paper_journal: "<e.g., Nature Methods>"
paper_year: <integer>
repo_url: "<github url, if applicable>"
attribution_block: minimal
---
```

If a metadata field is genuinely unknown after reading both sources, **halt and ask the user** rather than emitting `<TBD>` or fabricating. (Frontmatter values flow into WeChat's draft API; an unfilled field becomes a publication blocker.)

### Length

Mode-dependent ranges (lint warns outside the warn-bounds, but does not hard-fail):

| Mode | Typical | Warn outside |
|---|---|---|
| paper | 5000–8000 chars | [3000, 9000] |
| pure repo (spine pattern) | 8000–18000 chars | [3000, 20000] |
| pure repo (source walkthrough) | 4000–8000 chars | [3000, 9000] |
| combined | 6000–10000 chars | [3000, 12000] |

Section length is set by content density, not a per-section budget. Methods-deep figure sections naturally run 1000–2000 chars; brief setup sections may take 400. Spine-pattern repo articles are intentionally long because they unfold a full notebook tutorial — don't artificially compress.

### Image placeholders

- Format: `<!-- IMG:<id> -->` where `<id>` is `1`, `2`, ... for paper figures; `formula-N` for formula screenshots; `code-example-N-cell-M-K` for repo code-example outputs.
- Place each `<!-- IMG -->` exactly where the figure appears in the narrative — typically after the section that introduces it, before the bridge to the next section.
- Lint hard-fails on placeholders with no `figures/manifest.json` entry. The user is responsible for placing actual images into `figures/<id>/` before `[5] figures_prep`; you only emit the placeholder.

### Forbidden in body

- LaTeX `$$ ... $$` — WeChat does not render math. Use prose, unicode math (`Σ`, `α`, `β`, `≤`), or emit `<!-- IMG:formula-N -->` for a screenshot.
- HTML tags `<script>`, `<style>`, `<iframe>`, `<form>`, `<input>`, `<button>` — render strips them anyway, but lint catches first.
- Any string from `notes.md § Hype flags`, verbatim. **Before submitting, mentally grep your draft against the hype-flag list — paraphrase or drop.**
- Unresolved placeholder tokens like `[NUM?]` / `[TERM-N]` / `[PANEL-?-UNCLEAR]` / `[FORMULA-IMG-MISSING]`. Every such token still in your output means a question wasn't answered upstream — halt and ask.

### Bottom-line attribution

Article ends with a single one-line attribution, NOT a multi-section trust block. **No `## 解读者` section, no `## 说明` section.** The article's body must speak for itself; readers who want the paper use this one line.

```markdown
---

原论文: *<English paper title>* (`<Journal>` `<Year>`). DOI: `<doi>`. 代码: `<repo url, if any>`.
```

If `user-writing-style.md` has a strong contact-channel preference (email / WeChat), append `如有理解偏差请联系: <channel>` to the same line. Don't expand it.

## Soft constraints (apply with judgment)

- **Voice from `user-writing-style-<active-register>.md`**: hook style, sentence rhythm, person of address, term-handling, emoji policy, analogy density, citation format. Read it once at the start, internalize it.
- **Audience policy**: every section must serve both the "what is this about scientifically" reader and the "how does the method actually work" reader. Don't narrow to one.
- **Effect-size discipline**: distinguish trend (`走势`) vs. difference (`大于`) vs. significant difference (`显著大于` only when stat test is reported). Preserve hedges from the source (`suggests` / `tends to` → `表明... 倾向` not `证明`).
- **Number sourcing**: every number traces to `raw/<id>/page-NNN.txt`. Untraceable → don't include.
- **Generality discipline**: dataset-specific results stay dataset-specific. `在 <dataset> 数据上` not `普遍适用`.
- **Bridge sentences**: between sections, one sentence connects them. Two sentences means you've started the next section inside the bridge.

## Structure decisions

The structure of the article is **your call as the writer**, informed by `notes.md`'s proposed approach (which the user may have amended). Reference suggestions in `references/science-post-patterns.md` but do NOT follow a rigid template.

### Paper mode

Common shapes (not contracts):
- 总览 → Fig 1 → Fig 2 → ... → 结论
- 总览 → 背景 → Fig 1 → Fig 2 → 结论
- 总览 → 难题 → 方法 → Fig 1 (实测) → Fig 2 (生物验证) → 结论

The narrative spine is the paper itself. Figures drive the section breakdown.

### Pure repo mode — two distinct shapes

**Shape A — Spine-scaffolded** (if `notes.md § Notebook inventory` names a spine notebook):

```
Hook → 总览段(central thesis from source-code reading)
     → §<spine notebook section 1>(intro / setup cells: imports, data loading)
     → §<spine notebook section 2>(progressively deeper as the notebook does)
     → ... (each section: 过渡 + algorithm/source原理 + code block + IMG output + 解读)
     → 结论
```

Code blocks come **verbatim** from spine notebook in cell order. Imports + data + helpers are included so a reader can copy them in order and run them. Article scope = notebook scope; expect 8000–18000 chars (lint allows up to 20000 in repo mode; don't artificially compress).

**Shape B — Source walkthrough** (if `notes.md § Notebook inventory` says `N/A — source-walkthrough mode`):

```
Hook → 总览段(central thesis from source-code reading)
     → § Entry points(from <package>/__init__.py — what users actually call)
     → § Core algorithm(main implementation file: classes, key methods, data flow)
     → § <Optional: data flow / extension points / customization hooks>
     → 结论
```

Code blocks are LLM-constructed from API surface and **explicitly labeled illustrative**. Every behavior claim cites a source file. Typically 4000–8000 chars.

### Combined mode — paper-driven, repo enriches method sections

```
Hook → 总览段
     → Fig 1 (typically setup / overview)
     → Fig 2 (often method) ← code anchor here(function name + file path from cross-ref §3/§4)
     → Fig 3 (often key result) ← may include short formula from cross-ref §4.5
     → ... → 结论
```

Paper figures spine the article. Method-class figure sections expand to 1000–2000 chars with: algorithm intuition (from source) + formula (from cross-ref §4.5) + code anchor (function name + file path, typically 1–3 lines, not a full runnable block). **Do not scaffold the article on a notebook.** Reader runnability is NOT a contract here; the article is paper interpretation, not library tutorial.

Pick the shape that fits the source's own narrative. If a method paper deserves a separate "方法学原理" section, write it. If methods naturally fold into the figure that introduces them, fold them in. Trust your judgment within the mode's structural constraints.

## Writing approach

A reasonable order to write in (you decide):

1. **Re-read `notes.md § Proposed article approach`** to anchor the central thesis and structure.
2. **Write 总览段 first** — the article's "if you only read one paragraph" summary. This forces you to commit to the central thesis before everything else. Tightening this paragraph constrains what comes after.
3. **Write the hook second** — once 总览段 is firm, write the hook to lead naturally into it. If the transition feels forced, rewrite the hook (not the 总览段).
4. **Write body sections in narrative order** — top to bottom, one section at a time, with bridge sentences between. Re-read targeted pages from ingest as you go.
5. **Write the conclusion / "现状提示"** — your reflection as the 解读者, not a plot summary. Include a practical implication, a critical note, or a forward-looking question.
6. **Pass through once for headings + frontmatter + bottom attribution** — h2 headings descriptive (`Harmony 怎么做 batch correction`, not `Figure 2`); parallel grammatical form across sections; figure-number trailing tag (`(Fig. 2)`) if `user-writing-style.md` asks for it.

## Trust boundary (recap)

| Trust(don't re-verify) | Verify yourself(against ingest source) |
|---|---|
| `notes.md` figure inventory pages | every number you cite → `raw/<id>/page-NNN.txt` |
| `notes.md § Hype flags` (use to filter your prose) | every hedge in the source → preserve, don't strengthen |
| `cross-ref.md` §3 / §4 / §4.5 / §7 (combined mode) | function / class names — only those in §3 or §4 |
| User answers in `questions-to-user.md` | claims that resemble those answers but extend further |

## Output verification (run before returning)

Tick each in your head:

- [ ] Frontmatter valid YAML; title ≤ 32 / digest ≤ 120 / author ≤ 8
- [ ] Body length within [3000, 9000] raw chars; ideally 5000–8000
- [ ] Every number traces to a specific page in `raw/<id>/page-NNN.txt`
- [ ] No hype flag from `notes.md § Hype flags` parroted verbatim (mental grep)
- [ ] No LaTeX `$$..$$`; formulas are prose / unicode / `<!-- IMG:formula-N -->`
- [ ] No forbidden HTML tags
- [ ] No unresolved `[NUM?]` / `[TERM-N]` / `[PANEL-?-UNCLEAR]` / `[FORMULA-IMG-MISSING]` placeholders
- [ ] Every `<!-- IMG:<id> -->` placeholder corresponds to a figure the user is expected to provide
- [ ] Bottom attribution is ONE line; no `## 解读者` / `## 说明` sections
- [ ] Section headings are descriptive (not "Figure 1") and parallel in grammatical form
- [ ] Combined mode: every code anchor names a function/class that appears in `cross-ref.md` §3 or §4
- [ ] Combined mode: nothing in your draft contradicts `cross-ref.md` §7 (NOT-claim guardrails)
- [ ] Repo mode (spine): every code block is verbatim from the spine notebook in cell order; imports / data loading / helpers all included; cells with saved outputs have a matching `<!-- IMG:code-example-1-cell-M-K -->` placeholder
- [ ] Repo mode (no spine): every code block is explicitly labeled illustrative in surrounding prose
- [ ] Repo mode (always): every claim about library behavior (function names, class hierarchy, library imports, internal order) traces to a specific source file you / `[2]` Read; README claims are hedged when not source-verified
- [ ] Rule #1 language policy respected throughout

If any check fails, fix before returning.

## Absolute prohibitions

- Do NOT add a `## 解读者` or `## 说明` section. Bottom attribution is one line.
- Do NOT introduce claims not supported by the paper / repo / `cross-ref.md`.
- Do NOT introduce hype flags in opening, 总览, or conclusion.
- Do NOT drop the 总览 paragraph because "the hook covered it" — they serve different functions.
- Do NOT claim the paper's authors endorse this interpretation unless they explicitly do.
- Do NOT translate `Harmony` / `Scanpy` / `UMAP` / `Ilya Korsunsky` / etc. per Rule #1.
- Do NOT name a function / class in repo / combined mode that you have not verified by reading its source file (or by seeing it in `cross-ref.md` §3 / §4).
- Do NOT write LaTeX `$$..$$` in the output.
- Do NOT decompose the article into per-section LLM calls. One author, one stretch.

## Gate (present to user)

After writing `draft.md`, print:

```
Draft complete.
  Mode: <paper | repo (spine: <name> | source-walkthrough) | combined>
  Title: <title> (<N>/32 chars)
  Length: <N> raw chars  (warn outside <mode-specific bounds — see § Length>)
  Sections: <count>
  Digest: <N>/120 chars
  Image placeholders: <count> total — <breakdown by id-type>
  Unresolved placeholder tokens: <should be 0>
```

Then list explicit user actions BEFORE `[5] figures_prep`(this is the most-skipped step on a first run):

```
Before [5] figures_prep — user actions:

  Always:
    Place cover image at: work/<task>_<ts>/figures/cover.{png,jpg}
    Suggestion: paper / combined → screenshot Fig 1 or graphical abstract from PDF
                pure repo        → README hero image / project logo

  Paper / combined mode (if any IMG placeholders refer to paper figures):
    For each <!-- IMG:N --> in draft (N is integer): screenshot from PDF →
      work/<task>_<ts>/figures/fig-N/image.{png,jpg}
    For each <!-- IMG:formula-N -->: screenshot formula →
      work/<task>_<ts>/figures/formula-N/image.{png,jpg}

  Pure repo mode, spine pattern:
    Run: $PY $SKILL_DIR/scripts/notebook_outputs.py \
              work/<task>_<ts>/ingest/repo_src/<spine-path>/<notebook>.ipynb \
              --out work/<task>_<ts>/figures/code-example-1
    (auto-extracts cell sources + cell output images; only cover is user-supplied)

  Pure repo mode, source-walkthrough:
    No additional figures; cover only.
```

Then suggest revision flow:

```
Optional revisions (recommended: open draft.md, read top to bottom):
  Use [4] revise with a specific pointer (section name / paragraph N / quoted phrase) + the change you want.

When figures are placed and revisions complete, proceed to [5] figures_prep.
```
