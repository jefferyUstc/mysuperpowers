# Science-post patterns

Structural patterns for Chinese WeChat Official Account science-explanation
articles. These are writing-craft guidance, not hard rules — the prompts
under `prompts/` reference this file when they need a template.

## 总览 paragraph shape (reference, not contract)

The single most load-bearing paragraph in a science-explanation article.
It appears immediately after the opening hook and before any figure section.

A typical 总览 paragraph runs 150–250 Chinese characters and conveys
the key claim, but length and exact shape depend on the paper's own
narrative. The four-sentence pattern below is a common starting point —
adapt freely based on what the paper actually argues.

Four-sentence pattern (one common shape):

```
<一句话痛点 / 现象 / 研究问题>。
<这篇论文 / 这个 repo 做了什么,用什么方法,一句话说清>。
<关键结果 — 带一个精确的、可核对的数字>。
<这个结果对谁有意义,为什么值得读下去>。
```

Concrete example (Harmony 2019 paper):

> 把十个实验室的 `scRNA-seq` 数据合在一起,UMAP 上永远是十团彼此不重合的云 —— 这就是 `batch effect`。`Harmony` 提出一种迭代式 soft clustering 方案,在 2D 嵌入空间里直接把不同批次的细胞"拉"到一起,不需要建立生成式模型。在五个 benchmark 数据上,`silhouette score` 平均提升 0.21,跑一次 10 万细胞只要 3 分钟。对于把单细胞数据整合当日常操作的人,这是一个 default 工具值得替换的瞬间。

## Opening hook types (three, choose one per article)

### Type A — 背景故事 (background story)

Use when the method has a long lineage, a charismatic researcher behind
it, or a specific funding / historical moment that makes the work
meaningful. Tends to work for 综述类 解读 or career-arc pieces.

Template:

```
<年份 / 时间点>,<人 / 机构> 做了 <具体一件事>。在此之前,<领域现状>。
```

Risk: sounds like a textbook if the story isn't specific enough. Must
include a concrete detail (a number, a quote, a date) to earn the hook.

### Type B — 反差 (contrast)

Use when the paper overturns a widely-held assumption, challenges a
dominant paradigm, or re-frames a well-known problem. Most effective
for method papers that introduce a counterintuitive design choice.

Template:

```
<过去 N 年 / 大多数人 / 整个领域> 都在 <做某事 / 相信某事>。
但 <作者 / 这篇论文> 问了一个不同的问题:<具体问题>。
```

Risk: sounds contrarian-for-the-sake-of-it if the contrast isn't real.
Verify against `scan.md § 4 prior-work comparator` before using.

### Type C — 问题驱动 (question-driven)

Use when the paper solves a pain point many readers have personally
encountered. Strongest hook type for 工具类 解读 (method implementations
that readers can install and use).

Template:

```
<具体场景>,<每个从业者都遇到的具体困扰>。
<一个直接的问题:能不能 / 为什么 / 是不是可以 ...>?
```

Risk: assumes the reader shares the pain. For an academic audience this
is usually safe, but the pain must be a concrete research-practice pain
point (e.g., batch-integration alignment quirks, reproducibility
blockers) — not a generic "research is hard".

## Section heading conventions

Chinese WeChat articles have no strict heading convention, but good
科研解读 号 tend to use `##` h2 headings that are:

- **Descriptive, not enumerative.** Write `Harmony 怎么做 batch correction`,
  not `Figure 2`.
- **Consistent in grammatical form within one article.** If the first
  section heading is a verb phrase (怎么做...), keep all subsequent
  section headings as verb phrases. Don't mix with noun phrases or
  questions.
- **Short.** Target 8–18 Chinese characters.
- **Optional figure-number trailing tag.** Some authors append `(Fig. 2)`
  to make it easy for readers to find the figure in the paper. The
  user's preference lives in `user-writing-style.md`.

## Inter-section bridges

One sentence. Always ONE sentence. Two sentences means you started
explaining the next section inside the bridge — don't.

Good bridge shapes:

- `解决了 <问题> 之后,作者转向 <下一个问题>` — causal chain
- `这只是 benchmark。真实数据上呢?下一张图给了答案` — anticipatory
- `看起来很干净,但这里面藏着一个 tradeoff` — critical

Bad bridges (avoid):

- `接下来我们看 Figure 3` — tautological
- `综上所述` — only acceptable in 结论 section
- Two-sentence bridges that preview the next section's contents

## Conclusion section shape

150–250 Chinese characters. Three-part structure:

```
<一句总结本文核心贡献 — 和 key claim 相关但带解读者视角>
<这个工作对谁有用 / 改变了什么 / 未来可能走向>
<一句可以落地的建议 — 推荐读原文?clone 代码?等 follow-up?>
```

The conclusion is NOT a plot summary. It is **the 解读者 stepping
forward and offering a judgment**. Include at least ONE of:

- (a) a practical implication for practitioners,
- (b) a critical note (what the paper does not solve / limitations),
- (c) a forward-looking question.

## Bottom-line attribution (minimal)

The article ends with a single one-line attribution, NOT a multi-section
trust block. This skill targets academic readers who do not want PR-style
"about the author" framing.

Format (one line, may wrap to 2-3 if DOI / repo URL push the length):

```markdown
---

原论文: *<English paper title>* (`<Journal>` `<Year>`). DOI: `<doi>`. 代码: `<repo url, if any>`.
```

That is the entire CTA / attribution. **No `## 解读者` section, no
`## 说明` section, no separate `## 原文与代码` heading.** The earlier
sections of the article speak for themselves; readers who want to find
the paper can use this one line.

## Numbers and claims discipline

Three classes of numeric claim, decreasing strength:

1. **Reported with stat test.** `A 显著高于 B (p < 0.01)` — use `显著`, `significant` permitted.
2. **Reported without stat test but with numeric comparison.** `A 高于 B (0.78 vs 0.72)` — use `高于`, `提升`, `优于` — do NOT use `显著`.
3. **Trend only.** `呈上升趋势`, `略有提升` — use when data direction is visible but no comparison number is given.

Never promote class 3 to class 2 or 2 to 1. When a paper uses hedge words
(`suggests`, `tends to`, `may indicate`), preserve them or drop the claim.
Translating a hedge into Chinese certainty (`表明`, `说明`) is the single
most common hallucination in science-explanation articles.

## Analogy discipline

Analogies are high-leverage but dangerous — a wrong analogy survives in
the reader's memory longer than the correct technical explanation. Rules:

- Use an analogy only when the concept would be incomprehensible to an
  academic reader from a neighboring field without one. Do not analogize
  for the sake of accessibility when the methodology can be stated
  directly in 3–5 sentences.
- After introducing an analogy, state its limits explicitly: `这个类比
  只在 X 范围内成立; 当 Y 发生时就不对了`.
- Do not stack analogies — one per concept.
- Prefer user-historical analogies (from `examples/`) over newly-invented
  ones; the user's past audience already speaks that analogy vocabulary.

## Emoji and decoration policy

Follows `user-writing-style.md § emoji`. If unspecified: **no emoji in
body text**, optional single emoji in section headings for navigation
anchors. Dividers and tables are preferred over emoji for visual
rhythm.

## Length (reference targets, not contracts)

| Target total | Per-section reference | Lint warn outside |
|---|---|---|
| 5000–8000 raw chars | 500–2000 raw chars | < 3000 or > 9000 |

Sections are **not equal-sized**. A method-overview figure section that
needs to convey both algorithm and benchmark naturally runs 1500–2500
chars; a brief setup figure may take only 400. Let the section's actual
information density dictate length, not a per-section budget.

The audience is **project-fixed** — see `user-writing-style.md § Target
audience`. Match the user's historical length when one exists; otherwise
let the paper's own structure decide.

Over-length kills finish rate; under-length leaves the reader feeling
underserved. If a method paper genuinely needs 7000+ chars to do justice
to algorithm + benchmarks + biology, write 7000+ chars rather than
amputate. If a one-result paper can be done in 3500 chars, do not pad.

## What NOT to do

- Do not write 震惊体 / 重磅 / 颠覆 headlines; science-号 readers view
  this as a negative trust signal.
- Do not open with "大家好,我是 XXX" — modern Chinese tech-号 convention
  is to hook first, introduce self only in the 解读者 block at the end.
- Do not translate the paper's abstract sentence-by-sentence as the
  article body. Readers who wanted the abstract would have read the
  abstract.
- Do not claim 首次 / 第一个 / unprecedented without tracing the exact
  comparison from the paper (see Rule #1 in scan.prompt.md).
- Do not bury the key claim beyond the 总览 paragraph. Readers who don't
  find the claim in the first 400 characters close the tab.
