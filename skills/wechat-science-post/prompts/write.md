# Write

Write `work/<slug>/draft.md` top to bottom in one pass, as a single author. Trust `notes.md` and the user's answers at gate 1; re-read source pages as you reach each section rather than writing from memory. Wording: `references/language.md`. Structure: `references/style.md`. Rhythm: one article from `examples/`. Repo and combined modes: also follow their `references/mode-*.md`.

## Frontmatter

Fill it from `ingest/manifest.json` and `notes.md`. If a value is genuinely unknown, ask; never invent one.

```yaml
---
title: "≤ 32 characters, the title the user chose"
author: "from references/style.md"
digest: "≤ 120 characters: what was done and the one finding that matters"
cover: "figures/cover.png"
paper_title: "exact English title"
paper_doi: "10.xxxx/..."
paper_journal: "journal or preprint server"
paper_year: 2026
repo_url: "code repository, if the paper releases one"
---
```

## Shape

Paper mode, as a default rather than a template:

1. **Hook** — the concrete research problem a reader in this field has felt, in one paragraph.
2. **总览** — institutions and authors (`<机构> <PI> 等在 <期刊/预印本> 发表了题为 <English title> 的研究文章`), what was built or done, the key result with one checkable number, and why it matters. A reader who stops here has the article's claim.
3. **Figure sections** in the paper's order, `##` headings that say what the section shows, with `(Fig. N)` appended. Merge adjacent figures that make one point; give the central method or result the most room; a setup figure may need only a paragraph. Put `<!-- IMG:N -->` on its own line after the text that discusses Fig N. Bridge sections with one sentence, not two.
4. **现状与意义** — what this changes for people working on the problem, and what remains open in the authors' own terms. Follow `references/editorial-policy.md` on whether to add critique of your own.
5. **Attribution** — exactly one line after a rule:

```markdown
---

原论文: *<English title>* (`<Journal>` `<Year>`). DOI: `<doi>`. 代码: `<repo url>`.
```

**Budget.** About 6,000–9,000 characters of body for a six-figure paper; lint warns outside 3,000–10,000. Set the total first, then split it by importance. When over budget, cut repetition and secondary numbers before cutting a figure's point.

**Never in the body:** LaTeX `$$…$$` (use prose, unicode such as `Σ α ≤`, or `<!-- IMG:formula-N -->` with a screenshot), `<!-- IMG:cover -->`, a `# ` title, an about-the-author section, HTML other than the image comments.

## Self-check

After the draft is complete, re-read all of it once and fix what you find:

- Every number matches `notes.md § 关键数字` and its page; ratios and denominators are the paper's.
- Every sentence passes `references/language.md` § 0 and § 4–6: natural Chinese, precise and concise, sentence and paragraph length, evidence wording, translationese and filler. Delete any sentence that adds no new information. These come from errors found in reviewed drafts.

Then go to the figures step. `render.py` runs lint, which checks the mechanical rules and the word lists in `language.md` § 7; the re-read covers what lint cannot see.
