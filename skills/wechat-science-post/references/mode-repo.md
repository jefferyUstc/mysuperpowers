# Repo mode: articles about a code repository

A method walkthrough for academic readers, not a how-to: each step explains the statistical or algorithmic principle before showing the call, so readers can adapt it to their own data. This file overrides `style.md` and the paper-mode parts of the prompts where they conflict; the wording differences are in `language.md` § 8.

## Truth order

Source files you opened in `ingest/repo_src/` are the only basis for what the library does: class names, stage order, dependencies, return values. Notebooks show usage; README is self-description and is quoted as such. Conventions from an R version or "how such libraries usually work" are not evidence. If a mechanism matters and you have not read its source, read it or describe only observable behavior. A wrong mechanism is worse than none.

## Reading → `notes.md`

Besides the general parts: the public API (from `__init__.py`), the core algorithm files and data flow, and a **notebook inventory** (`manifest.repo.notebooks`): for each notebook, cells, cells with image output, one-line topic.

Pick **one spine notebook**: the one that best demonstrates the article's thesis end to end, preferring self-contained notebooks with saved outputs. Name two rejected candidates and why. With no notebooks, the article is a **source walkthrough**: entry points → core algorithm → data flow → extension points.

## Structure

- **Spine notebook:** the article follows the notebook's cells in their order, including imports, data loading, and helpers, so a reader who copies the code blocks in order can run them. Adjacent short cells may merge; cells are never reordered or borrowed from another notebook. After each block with image output, `<!-- IMG:code-example-1-cell-M-K -->` (run `figures.py notebook` to produce them; `figures/code-example-1.json` lists cells and images).
- **Each step:** principle first (200–400 汉字: model, objective, key assumption), then the code (5–20 lines, language tag, short Chinese comments), then two to four sentences on what the output means given the principle.
- **Source walkthrough:** code blocks are constructed from the API and labelled as illustrative; every behavior claim names its file and function.
- Budget: spine articles may run long (lint range up to 20,000) because they unfold a full notebook; walkthroughs stay near paper length.

## Structure differences from `style.md`

- More frequent `##` headings named for the action or API (`加载数据`, `Niche model 训练`); no `(Fig. N)` tags.
- Hook may be declarative: what the tool does and the article's steps.

## Attribution

```markdown
---

代码: `<repo url>`. 示例数据: `<dataset>` (`<Author Year Journal>`). 关联论文: *<title>* (`<Journal>` `<Year>`). DOI: `<doi>`.
```

Omit the parts that do not apply. Frontmatter carries `repo_url`, and `paper_doi` when there is an associated paper.
