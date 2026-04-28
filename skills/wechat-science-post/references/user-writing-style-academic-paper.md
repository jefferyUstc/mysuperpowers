# Writing style — academic-paper register

**For paper mode + combined mode.** Modeled after dense, multi-clause academic
science blogs (BioArt-style) where the reader is a researcher who wants the
methodology and biology compressed into long, logically-scaffolded paragraphs.

## Identifier fields

These are pulled from the universal section in `user-writing-style.md`.

- Author name: `jefferyLLLLL`

## Positioning (one sentence)

A serious science blog for academic readers in computational biology,
single-cell / multi-omics, and adjacent methodology fields. Each article is a
critical reading of one method paper that exposes design trade-offs and the
biology context that motivated the work.

## Hook style preference

Default: **A — 背景故事 (background story)** or **C — 问题驱动 (question-driven)**.
Method papers with a long lineage (Monocle 1 → 2 → 3, Harmony, Cellpose) often
suit A; papers solving a recently-felt practical pain often suit C. Type B
(contrast) only when the paper genuinely overturns a dominant assumption (rare).

## Person of address

- Self reference: **avoid `我` and `我们`**. The article is a paper 解读, not a
  personal essay or a tutorial. Use passive voice / third-person constructions
  ("研究者...", "作者...", "本研究...") in their place.
- Reader address: **avoid `你`**. Pure third-person register; the reader is
  positioned as a peer scientist, not a tutorial follower.
- Paper author reference, first mention: **`<Institution / Lab name>` 等在
  `<Journal>` 杂志发表了题为 `<English title>` 的研究文章** (BioArt's standard
  pattern). Subsequent mentions: just `<English first author> 等`.

  Examples:
  - 第一次提:`荷兰乌得勒支大学医学中心 Hugo J. G. Snippert 实验室等在 Nature 杂志发表了题为 Emergence of oncofetal plasticity is ubiquitous in early colorectal cancers 的研究文章`
  - 后续:`Snippert 等在第二次实验中...` 或 `Snippert 团队进一步...`

## Sentence rhythm

- Average sentence length: **medium-to-long**, 30–70 Chinese characters per
  sentence. Multi-clause syntax is expected; subordinate clauses with `；` and
  `。` separating beats are common.
- Connective density: **rich, not sparse**. Use logical scaffolds explicitly:
  `然而` / `因此` / `与此同时` / `此外` / `尽管 ... 却` /
  `进一步 ... 显示` / `上述结果表明` / `综合来看` / `由此` /
  `值得注意的是` / `更关键的是` are all in the active vocabulary.
  Academic Chinese readers EXPECT these scaffolds; their absence reads as
  fragmented or unfinished thinking.
- Paragraph length: **3–7 sentences**. One paragraph = one logical step in the
  argument. Paragraphs typically open with a connective or a frame-setting
  noun phrase ("综合来看,该研究提出了一个新的模型 ...").

## Technical term handling

- First mention of an English-name method / tool / library: **drop in English
  without translation**. If the term is genuinely obscure within the audience
  (a niche statistical procedure or a new biology coinage), add a 4–10 char
  parenthetical Chinese gloss: `oncofetal("癌胚"样)`, `Harmony(单细胞批次校正方法)`.
  Common-knowledge terms (`UMAP`, `scRNA-seq`, `Scanpy`, `PCA`, `ChIP-seq`) get
  no gloss.
- Subsequent mentions: always English. No Chinese alias mid-article.
- Equations: **describe in prose by default**; WeChat does not render LaTeX.
  For load-bearing key formulas, screenshot from paper Methods into
  `figures/formula-N/image.<ext>` and reference as `<!-- IMG:formula-N -->`.
  Inline single-symbol references can use unicode (`Σ`, `α`, `β`, `≤`).

## Citation style

- **Inline citation** for non-trivial claims: `<English first author> et al. <Journal> <Year>`.
  Examples: `Trapnell et al. Nature Biotechnology 2014`, `Olsson et al. Nature 2016`,
  `Setty et al. Nature Biotechnology 2016`.
  This format anchors readers at the right place without forcing them to flip to a
  reference list.
- **Optional footnote-style numbering** `【1】` `【2】` for high-density
  reference lists at the article's end. v0.1 does NOT auto-maintain numbered
  footnotes — write them by hand if you choose to use them. v0.2 may add a
  citation-collector lint pass if needed.
- The bottom-line attribution is still ONE line ("原论文: ..."), separate from
  in-body citations.

## Emoji / analogy / rhetorical questions

- **No emoji** in body text or headings.
- **Rare analogies** — only when a concept would be incomprehensible to an
  academic reader from a neighboring field. State the analogy's limit
  explicitly when used.
- **No rhetorical questions** in narration. The C-type hook may pose one
  question at the very start to set up the article; do not repeat the device
  inside body sections.

## Length

- Per-article target: **5000–8000 raw chars** (`len()` count includes English
  terms, punctuation, whitespace; actual Chinese-character density is
  typically 60–70% of this).
- Lint warns outside `[3000, 9000]`.
- Method-deep sections naturally run 1000–2000 chars; biology-context
  sections 800–1500 chars; brief setup sections 400–700.

## Section heading conventions

- **Sparing use of `##` h2 headings.** BioArt-style articles often run multi-
  paragraph sections without an h2 break, relying on connective phrases to
  signal section transitions. Use `##` only when the article shifts to a
  meaningfully different sub-thesis (e.g., "总览" → "实验设计与第一发现"
  → "进一步验证" → "现状与意义").
- When you do use h2: descriptive, not enumerative. Write
  `Monocle 2 怎么"自己"学到多分支轨迹` not `Figure 1`.
- Section heading trailing figure tag: append `(Fig. N)` when the section is
  paired one-to-one with a figure.

## Bottom attribution

One line at the end (no `## 解读者`, no `## 说明`):

```markdown
---

原论文: *<English paper title>* (`<Journal>` `<Year>`). DOI: `<doi>`. 代码: `<repo url, if any>`.
```

If a separate reference list is genuinely useful (multiple cited works,
high-density citation), append `## 参考文献` as a numbered list AFTER the
horizontal rule, but before the one-line attribution. Keep it minimal.

## Few-shot anchor

- `examples/published-article-academic-paper-01.md` — when populated, this is
  the primary voice anchor. The skill warns at `[0d]` if `examples/` has no
  matching anchor for the active register.
