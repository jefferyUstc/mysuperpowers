# Style: author, reader, structure

Who the article is for and how it is built. Wording rules are in `language.md`. Repo-only articles use the structure in `mode-repo.md`.

## Author and reader

- **Author name** (frontmatter `author`, at most 8 汉字 or 16 ASCII characters): `jefferyLLLLL`
- **Reader:** researchers in computational biology, single-cell and multi-omics, and neighboring fields. Every section serves two readers at once: the one asking what scientific question this answers and why it matters, and the one asking what was actually done, with what data, against what comparison. Accessible, never dumbed down.

## Structure patterns

**Hook** — pick the type that fits the paper:
- A 背景: the field's history leading to this paper, anchored by one concrete detail.
- B 反差: only when the paper genuinely overturns a common assumption.
- C 问题: a research-practice pain the reader has felt, stated concretely.

**总览** — four beats, about 150–300 汉字: the problem; what the paper did and how; the key result with one checkable number; who should care. The claim must be visible in the first 400 characters.

**Headings** — descriptive and parallel in form (`scPRIME-seq 怎么让液滴同时拿到 gDNA 与 5' RNA（Fig. 1）`), never `Figure 1`. Use `##` only where the argument turns; consecutive paragraphs may run without one.

**Bridges** — one sentence linking sections. Two sentences means the next section has started inside the bridge.

**Conclusion** — the significance in the reader's terms: what becomes possible, for whom, and what remains open as the authors frame it. Not a plot summary.
