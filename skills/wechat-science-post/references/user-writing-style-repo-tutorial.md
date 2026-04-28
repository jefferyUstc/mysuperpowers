# Writing style — repo-tutorial register

**For repo mode.** Modeled after Spateo / scverse-style hands-on tutorials
where the reader expects to copy code, run it, see output, and leave with a
working notebook — but with a critical addition that pure tutorial blogs lack:
**algorithm internals must be explained before code, not skipped.**

## Identifier fields

These are pulled from the universal section in `user-writing-style.md`.

- Author name: `jefferyLLLLL`

## Positioning (one sentence)

A method-walkthrough blog for academic readers in computational biology /
single-cell / multi-omics. Each article unpacks one open-source tool by first
explaining the algorithm's statistical / mathematical principle and then
demonstrating it with runnable code on a published dataset.

## Algorithm-first discipline (most important rule)

Pure tutorial blogs often lack algorithm explanation — they show
`some_lib.do_thing(...)` as a black box. **This register explicitly rejects
that pattern.** Every code-example section must satisfy:

1. **Algorithm intuition first** (200–400 chars): what statistical /
   mathematical model does this API call implement? What's the loss function /
   probability distribution / optimization target? What's the key assumption?
2. **Then code** (5–20 lines): the API call with realistic parameters.
3. **Then output interpretation** (2–4 sentences + image): what does the
   output mean in light of the algorithm explained in step 1?

Skipping step 1 ("just call this function") yields a how-to-blog that loses
its place once the reader's data differs from the example. With step 1, the
reader can adapt parameters intelligently.

### Algorithm intuition must come from source code, not priors

The "algorithm intuition" in step 1 is the article's **truth claim** about
what the library does. It MUST be rooted in source code that you actually
Read in `repo_src/` — not in:

- the project's README (which describes how the project wants to be seen,
  not always how it's implemented),
- common conventions from the algorithm's R / MATLAB / paper version (the
  Python port may have made different implementation choices),
- generic ecosystem common sense ("most libraries doing X use Y").

If the article needs to explain a feature whose implementation you have
not Read, either Read the implementing source file first, or omit the
mechanism description and stick to behavioral observations. **A wrong
algorithm intuition is worse than no intuition** — it teaches the reader
something false.

### Reader runnability rule (spine-notebook articles)

When the article scaffolds on a spine notebook, the article's code blocks
must be runnable in order: imports, data loading, helper function
definitions all appear in the article in the order the spine notebook ran
them. The reader copying the article's code blocks one by one into a
Python session must end with the same state the spine notebook ended at.
This is a hard contract; cherry-picking interesting cells from across
multiple notebooks breaks it and is forbidden.

## Hook style preference

Default: **A — direct declarative**, modeled after `本推文将介绍如何使用 ...`
patterns. State the article's scope and the article's three / four sub-steps
in the opening paragraph. Type C (问题驱动) works for tools that solve a
recently-felt practical pain.

## Person of address

- Self reference: **`我们` is acceptable** in instructional contexts —
  `这里我们选择空间自相关性高的基因`, `下面我们检查模型输出`. Avoid `我`
  unless quoting subjective experience (rare).
- Reader address: **`你` sparingly**, only in caveats / customization notes:
  `根据你自己的需求调整这一步`, `如果你的数据格式不同 ...`. Default is
  third-person.
- Tool author / paper author reference: short cite. `Wei et al. Science 2022`,
  `Trapnell 等在 Nature Biotechnology 2014` — enough to anchor, no
  full-institution paragraph required.

## Sentence rhythm

- Average sentence length: **short-to-medium**, 15–40 Chinese characters per
  sentence. Tutorial register prioritizes step-by-step clarity; long
  multi-clause sentences slow the reader between code blocks.
- Connective density: **sparse**. The code blocks themselves are the logical
  scaffold; over-using `因此` / `进一步` / `综合来看` makes the prose feel
  bolted onto the code.
- Paragraph length: **1–3 sentences** outside code blocks; this density pairs
  with the heavy code interruption.

## Technical term handling

- Same as academic-paper register: drop English terms in; gloss obscure ones
  briefly. For tutorial register, in particular, **method names follow the
  exact API form** — `st.tl.Niche_Model` not `Niche-Model`, `adata.var_names`
  not `var-names`. This matters because readers may copy and paste.
- API parameters in inline `code` form: `n_neighbors=15`, `distr="poisson"`.
- Equations: same default — prose first, screenshot for load-bearing math.
  But in tutorial register, the algorithm-intuition paragraph (rule #1 above)
  often benefits from a unicode equation snippet:
  `min ‖f(z) − x‖² + λ Σ b_ij ‖f(z_i) − f(z_j)‖²`. Use sparingly; full
  derivations go via screenshot.

## Code blocks

- Language tag required: ` ```python ` / ` ```r ` / ` ```bash `.
- Length: 5–20 lines per block. If the example genuinely needs more, split
  across multiple code blocks with prose in between.
- Inline Chinese comments are encouraged for clarity:
  `# 该数据已经注释好,包括18个亚群`. Comments should explain what the line
  does, not paraphrase the code.
- **Data source citation**: if the example uses a published dataset, cite it
  inline: `示例数据来源于 Wei et al. Science 2022 蝾螈脑再生研究` —
  preserves traceability and builds trust.

## Output interpretation

Every code block that produces an image / table / metric should be followed
by 2–4 sentences interpreting the output:
- What numerical / visual feature is meaningful?
- How does it relate to the algorithm intuition stated above?
- What would a reader notice / care about in their own data?

Don't paraphrase the output literally ("UMAP 上有 5 个 cluster"); explain
what it tells them about the underlying biology / data structure.

## Emoji / analogy / rhetorical questions

- **No emoji** in body text or headings (same as academic register).
- **Occasional analogies** OK if the concept is non-obvious to a tutorial
  reader (e.g., explaining KNN graph as "查找最近邻居"). State the limit
  briefly.
- **No rhetorical questions** in narration; the A-type declarative hook
  doesn't use them.

## Length

- Per-article target: **4500–9000 raw chars** (excluding code block content;
  code blocks add to the rendered length but don't count toward narrative
  budget).
- Lint warns outside `[3000, 9000]` for the prose body.
- Per-section: algorithm-explanation 200–400 chars; output-interpretation
  150–400 chars; setup / data-loading sections 300–600 chars.

## Section heading conventions

- **More frequent `##` h2 headings** than academic register — each step in the
  tutorial gets a clear heading. Short, action-oriented:
  - `加载数据` / `选择基因集` / `Niche model 训练` / `Niche LR model 解释`
  - Avoid generic names like `分析` or `结果`; use the API name or the
    semantic action.
- No figure-tag suffix: tutorial sections don't pair 1-to-1 with paper
  figures.

## Bottom attribution

One line at the end (no `## 解读者`, no `## 说明`):

```markdown
---

代码: `<repo URL>`. 示例数据: `<dataset source>` (`<Author Year Journal>`). 主页: `<docs URL, if any>`.
```

If the article's hook references an associated paper (combined-mode-style),
add an extra line:
```markdown
关联论文: *<English paper title>* (`<Journal>` `<Year>`). DOI: `<doi>`.
```

## Few-shot anchor

- `examples/published-article-repo-tutorial-01.md` — when populated, this is
  the primary voice anchor. The skill warns at `[0d]` if `examples/` has no
  matching anchor for the active register.
