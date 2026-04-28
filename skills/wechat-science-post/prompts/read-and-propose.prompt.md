# Step [2] — Read & propose prompt

## Your role here

You read this paper / repo like a **science explainer preparing to teach it** to a Chinese-reading academic peer — not as a referee evaluating soundness, not as an abstract-skimmer collecting headlines. The article that eventually comes out has to hold up to a researcher reading it on their phone, so "I understood it" must mean "I could explain this to a colleague," not "the abstract was clear." Read enough that you can defend every claim the article will later make.

## What this step produces (output contract)

Two files. No article prose at this step.

| File | What's in it | Consumed by |
|---|---|---|
| `work/<task>_<ts>/notes.md` | reading notes + figure inventory (with page numbers) + proposed article approach | `[2.5] cross-ref` (combined mode) and `[3] write` |
| `work/<task>_<ts>/questions-to-user.md` | anything unresolvable from the materials | the user (must answer before `[3]`) |

**Forward reference.** Step `[3] write` will navigate to figure pages **using the page numbers in your figure inventory** without re-grepping. Keep page numbers exact. The `Hype flags` section is grep'd against the final draft to catch parroting. Mode-specific outputs from `[2.5] cross-ref` get woven into `[3]` separately — you don't need to anticipate that.

## Hard rules

- **Output language.** Rule #1 applies (Simplified Chinese narrative; English preserved for algorithm / method / package / person / journal / paper-title / gene / dataset / file-format / identifier names). See SKILL.md § Rule #1 for the full text.
- **No article prose.** Reconnaissance + proposal only. Article writing is `[3]`.

## Inputs (halt if missing)

### Paper mode / combined mode

- `ingest/paper.json` — manifest with each paper's id + page count + `pdf_metadata` (title / author / DOI / journal subject; usually clean enough to quote in the bottom-line attribution)
- `ingest/raw/<id>/page-NNN.txt` — `pymupdf` block-level + column-aware text per page; navigate by page number
- `ingest/raw/<id>.pdf` — original PDF if your tools support direct read
- Image-only pages → empty 0-byte text files; treat as "this page is figure or table"

**Multi-PDF input (N > 1):** `paper.json.papers[0]` is the **primary** paper (the user's ingest-time id ordering decides which); `papers[1..]` are supplementary or companion PDFs. Center your central thesis, figure inventory, and proposed structure on the primary. Read supp pages only when the primary explicitly references them (e.g., "see Supp. Fig. S2"). The article's bottom-line attribution always cites the primary.

### Repo mode / combined mode

- `ingest/repo.json` — GitHub metadata
- `ingest/repo_src/` — symlink into a local `git clone`. Use `Read`, `Glob`, `Grep`, `Bash` (e.g., `git -C repo_src log --oneline | head`) freely
- `ingest/repo_tree.txt` — 2-level navigation listing
- `ingest/paper_refs.md` — arXiv / DOI / bioRxiv references found in README

### Style anchors (read once, do not deep-read)

- `references/user-writing-style.md` — INDEX file. Identify the active register from its "Active register" table based on the current article's mode (paper / combined → `academic-paper`; repo → `repo-tutorial`).
- `references/user-writing-style-<active-register>.md` — the actual voice anchor; read this file in full. Hook style preference, sentence rhythm, person-of-address, citation style, length budget, etc., all live here.
- `references/science-post-patterns.md` — narrative reference patterns (NOT contracts)
- `examples/published-article-<active-register>-*.md` — few-shot voice anchors for the active register, when present.

### PDF text extraction quirks

`raw/<id>/page-NNN.txt` is `pymupdf` output with column-aware sort, so multi-column reading order is preserved. Common noise to ignore:

- Panel labels / axis ticks / legend entries (`a b c`, `0 20`, `B cell`) — short isolated lines from figure regions; not body content
- Tables — concatenated rows without column alignment; look at the table caption nearby for the actual claim
- Equations — TeX/MathML often loses characters; describe in prose, screenshot if load-bearing
- Ligature artifacts (`f.short` for `fi`); recover from context

**Heuristic**: body sentences flow grammatically; figure noise is isolated short lines that don't connect to neighbors.

## Reading approach (suggestion, not protocol)

You decide how to read efficiently. A reasonable starting point:

1. **Read `paper.json` (or `repo.json`)** to know what you have.
2. **Sample page lengths** (`Bash: wc -c raw/<id>/page-*.txt`) — 0-byte pages are figure-only, very long pages are body.
3. **Read pages 1–3** (paper) — abstract + intro give you 80% of the central thesis.
4. **Locate figures** (`Bash: grep -nE '^Fig(\.|ure)?\s+[0-9]' raw/<id>/page-*.txt`) — note which page each caption *starts* on. The same regex also matches in-text references (`see Fig. 1 for ...`); a caption is recognizable as a continuous 50–300-char block opening with the figure number, while a reference is a single-sentence mention. `Read` the page once before writing it into the inventory.
5. **Read Methods / Results pages** based on the figure locator + section heading scan. Targeted Reads, not whole-paper sequential reads.
6. **Read enough** that you can defend each claim you'll make in the article.

### Repo + combined modes — shared truth hierarchy(applies to both)

- **Source code** (`repo_src/<package>/*.py`) — gold standard. Any claim about what the library does — class hierarchy, function names, internal stage order, imported libraries, return types, side effects — must trace to a source file you Read.
- **Notebooks** (`repo_src/tutorials/*.ipynb` or similar) — teaching narrative material. Cells provide imports, data setup, and worked examples. Notebooks reveal *how the API is used*; they do NOT reveal *how the algorithm is implemented*.
- **README** — project context only. Treat README as the project's self-description (often marketing). Claims about behavior in README must be verified against source before quoting; if only README has a claim, hedge it ("according to the README, ...") in `notes.md`.

**Shared reading steps**(repo + combined):

1. **README** for orientation only. Note the claims you'll later verify.
2. **Source code** — primary work. At minimum:
   - `<package>/__init__.py` — public API surface (what's exported = what users actually call)
   - The main algorithm / core class file(s) — read in full if reasonable size, or with targeted `Grep` + `Read` for large files. Capture: class hierarchy, key entry points, data flow, dependencies (which third-party imports actually matter).
   - For any feature the article will discuss, Read the implementing file. Don't claim behavior you haven't seen in source.
   - Optional `git -C repo_src log --oneline -20` for version history.

### Pure repo mode only — Steps 3–4(combined mode SKIPS these)

3. **Notebooks** (if `tutorials/` / `examples/` / `notebooks/` exists with `*.ipynb`):
   - Inventory all of them — filename, cells, code cells, cells with saved image output, one-line topic.
   - Pick **one spine notebook** — the notebook that best demonstrates the article's central thesis end-to-end. The whole article will follow this notebook's cell order; readers must be able to copy code blocks in order and run them.
   - **No supplement notebook.** Repo articles use one spine, period.
   - User can override the choice at the gate by naming a specific notebook.
4. **No-notebook fallback**: if there are no `*.ipynb` files, the article is a **source walkthrough** — structured by the source code's logical organization (entry point → core algorithm → data flow → extension points). Code examples in the article are LLM-constructed from the API surface (clearly labeled as illustrative); every behavior claim still cites a source file.

### Combined mode specifically

Combined mode applies Steps 1–2 (truth hierarchy + source reading) but **does NOT** apply Steps 3–4. The article structure in combined mode is **paper-driven** (paper figures provide the structural spine), not notebook-driven. Code anchors in method-class figure sections come from `cross-ref.md §3 / §4` (built by `[2.5] cross-ref`), which can reference notebook cells but does not scaffold the article on a notebook. After reading paper + repo source here in `[2]`, hand off to `[2.5]` for the paper↔repo correlation.

## Output 1: `notes.md`

Free-form. The structure below is a **suggestion**; reorder, merge, split, add, drop sections based on the paper's specific narrative. The point is that the user (and step `[3] write`) can read your notes and feel "this person actually understood the paper."

Suggested skeleton:

```markdown
# Reading notes — <paper title or repo full_name>

## Paper / repo understanding
<3-6 paragraphs of free-form prose. Demonstrate that you actually understood:
 - What's the central thesis (one sentence)?
 - What's the methodology, in enough depth that you could explain it to a peer?
 - What's the prior-work landscape this contributes to?
 - What biology / application matters here?
 - What's the relationship between the figures and the claims?
 - What hedges or caveats does the paper itself acknowledge?>

## Figure inventory (paper / combined)
<For each main figure: label, page where caption starts, one-sentence take-home, function class
 (`setup` / `method` / `baseline` / `key result` / `ablation` / `application`),
 must-cover-in-article: 是 / 否 / 存疑.
 This is the only piece of "structured data" notes.md needs — `[3] write` will navigate
 to figure pages using these page numbers without re-grepping.>

## Algorithm / formula / code-example inventory (repo / combined, when relevant)
<If the article will explain an algorithm: a short list of algorithm steps, where each is
 described (paper Methods page or repo source file), and whether a formula or code example
 should accompany it. Skip for pure application papers.>

## Notebook inventory (PURE REPO MODE ONLY — combined mode skips this section)

> Combined mode: this section is N/A. Code anchors in combined-mode articles come from `cross-ref.md §3 / §4` (the [2.5] cross-ref step), not from a spine notebook. Skip directly to "Proposed article approach". Combined-mode articles are scaffolded by **paper figures**, not notebooks.

<**Step 1 — list every `*.ipynb`** in `tutorials/`, `examples/`, `notebooks/`(or wherever the repo keeps them):

| Notebook | Cells | Code | With image output | One-line topic |
|---|---|---|---|---|
| <filename> | <total> | <code-cells> | <cells-with-image-output> | <what this notebook teaches end-to-end> |
| ... | ... | ... | ... | ... |

**Step 2 — pick exactly ONE spine notebook**(or write `N/A — source-walkthrough mode` if no notebooks exist).

The spine notebook is the notebook the article follows from start to finish. Reader runnability is non-negotiable: a reader copying the article's code blocks in order must be able to run them, which means the article's code blocks come from the spine notebook **in the spine notebook's cell order**, with imports / data loading / helper definitions all included.

Selection criteria(in priority order):
1. **Aligns with article central thesis** — the spine should be the notebook that most directly demonstrates what the article is trying to teach.
2. **Self-contained** — preferred over notebooks that depend on external state.
3. **Has saved cell outputs** — so figures-prep can extract real visuals; if no notebook has saved outputs, the article still works but loses image evidence.

Patterns(what kind of notebook usually fits which thesis):
- A canonical / main walkthrough notebook → for "introduce the library" articles
- A feature-focused notebook → for "deep dive on feature X" articles
- An advanced / extension notebook → for "how to extend / customize" articles

Anti-patterns:
- ❌ Cherry-picking cells from multiple notebooks → reader cannot run the result; cells from different notebooks have different imports and data state
- ❌ Showcase / gallery notebooks as spine → optimized for "demonstrate variety", weak narrative through-line
- ❌ Internal / developer notebooks as spine → audience mismatch (contributors vs article readers)

**Spine selection**:
- Spine: `<notebook filename>`(<reason in one line tied to the article's thesis>)
- Considered & rejected: list 2–3 candidates and why they don't fit (e.g. "<other.ipynb>: feature-focused on a tangential capability", "<gallery.ipynb>: showcase, no narrative")

**No-notebook fallback** (write this if no `*.ipynb` exist):
> N/A — source-walkthrough mode. Article structure is determined by source code's logical organization (entry points → core algorithm → data flow). Code blocks are LLM-constructed from the API surface and clearly labeled as illustrative; every behavior claim cites a source file.

**Step 3 — extraction**: `scripts/notebook_outputs.py` will be run on the spine notebook (full extraction, no `--cells` filter) before `[5] figures_prep`. You only commit to the spine choice here.>

## Proposed article approach
<A few paragraphs:
 - Central thesis of the article (one sentence; this is what every section serves)
 - Proposed structure — list the sections you'd write, in order, with rough length estimates.
   Don't follow a template; let the paper's narrative dictate. Method papers may need a
   methods section; application papers may not. Repo articles may need an
   algorithm-step-then-code-example structure. Combined articles may interleave.
 - Title candidates: 1-3 options with one-line tradeoff each
 - Hook candidate: 1 (or 2 alternatives) of type A (background) / B (contrast) / C (question-driven)
 - What gets emphasis vs. brief mention vs. skipped, with rationale.
 - Length estimate (raw chars). Lint warns outside [3000, 9000].>

## Hype flags
<Words from the paper's abstract or README that the article should NOT parrot verbatim:
 e.g., "revolutionize", "first-ever", "fully unsupervised" if it's actually partial.
 The `[3] write` step uses this list to keep the article honest.
 If the paper has no hype tendency (rare for method papers, common for math-heavy work),
 write a single line `No hype flags found.` Do NOT invent flags to fill the section.>

## Cross-ref preview (combined mode only)
<One line: does the repo plausibly implement this paper, or is it a different version /
 different scope / tangential? Flag any obvious version skew. Deep correlation lives in `[2.5] cross-ref`.>
```

Lengths: typical `notes.md` is 400–800 lines depending on paper depth. Don't pad; don't truncate. If a section doesn't apply (e.g., "Algorithm inventory" for a pure application paper), drop it.

If the run was interrupted and you are resuming, an optional first line `(Resuming: previous pass reviewed pages X–Y / repo file Z)` is fine. Otherwise omit.

## Output 2: `questions-to-user.md`

For every technical term, symbol, experimental setting, hedge, or methodological detail you encountered but cannot resolve from the materials, append:

```markdown
## Q1
**Question:** <your question, in Chinese>
**Context:** <where you saw it — file + short quote>
**Why asking:** <what part of the article this will block if unanswered>
```

**Append a question when:**
- A technical term / symbol cannot be confidently defined from context
- A figure's caption is unreadable (image-only page, fragmented panel labels)
- The paper hedges (`suggests`, `may indicate`) on a claim you'd otherwise treat as fact
- A number in the abstract doesn't appear in any figure or methods text
- The paper appears to be a follow-up to an earlier work and you can't tell without it
- Your "Proposed article approach" makes a substantive choice (skip a figure, expand a section beyond default) that the user should sign off on

Err on the side of asking for technical / numerical questions. **Don't ask "what's the article tone"** — that's `user-writing-style.md`'s job. **Don't ask "how long should the article be"** — your proposed approach should answer that.

Target: **3–8 questions** on a first run for a typical paper. Fewer than 2 → you're not scrutinizing. More than 15 → you're stalling; consolidate.

## Thinking discipline (do silently, don't write)

Before producing `notes.md`, run these checks in your head:

- **Two-sentence sanity**: can you explain the paper's contribution in two Chinese sentences (one for the problem, one for what they did)? If not, you haven't understood; reread.
- **Hedge filter**: which claims are stated as facts vs. hedged with `suggests` / `tends to` / `may`? The article must preserve hedges.
- **Comparator check**: when the paper says "improves over X", is X named specifically? If not, flag in `questions-to-user.md`.
- **Number traceability**: every number you might cite in the article — can you trace it to a specific page + paragraph in `raw/<id>/page-NNN.txt`? Note the source in your understanding section so `[3] write` can quote with confidence.

## Absolute prohibitions

- Do NOT write any article prose at this step. Reconnaissance + proposal only.
- Do NOT translate paper title verbatim and call it your article's central thesis.
- Do NOT use any abstract phrase verbatim as a Chinese translation. If the abstract says "a novel framework", your understanding section should say what the framework does.
- Do NOT invent contributions or numbers the paper does not claim.
- Do NOT skip figures without explanation in your proposed approach (a deliberate skip is fine; an unexplained omission is sloppy).

## Gate before proceeding

After writing `notes.md` and `questions-to-user.md`, print the gate handshake. Format depends on mode:

**Paper mode:**
```
Reading complete.
  Mode: paper
  Central thesis: <one-line summary>
  Proposed sections: <count> | length estimate: <N> raw chars
  Figure inventory: <N> figures (must-cover: <K>)
  Open questions: <K> in questions-to-user.md, please answer before [3] write.
```

**Pure repo mode:**
```
Reading complete.
  Mode: repo
  Central thesis: <one-line summary>
  Proposed sections: <count> | length estimate: <N> raw chars
  Spine notebook: <filename>     OR     source-walkthrough mode (no notebooks)
  Open questions: <K> in questions-to-user.md, please answer before [3] write.
```

**Combined mode:**
```
Reading complete.
  Mode: combined (paper-driven; repo provides code depth in method sections)
  Central thesis: <one-line summary>
  Proposed sections: <count> | length estimate: <N> raw chars
  Figure inventory: <N> figures (must-cover: <K>)
  Open questions: <K> in questions-to-user.md, please answer before [2.5] cross-ref.
```

Wait for the user to:
1. Answer / N/A every question in `questions-to-user.md`
2. Confirm or amend the proposed article approach (title pick, hook pick, structure adjustments)
3. **Pure repo mode**: confirm or override the spine notebook pick

Only then proceed to `[2.5] cross-ref` (combined mode) or `[3] write` (paper / pure repo).
