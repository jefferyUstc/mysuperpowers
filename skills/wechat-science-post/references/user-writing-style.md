# User writing style — wechat-science-post

This file is the **index** of writing-style registers and the home of
**universal fields** that apply across all registers (author name, contact
channel, target audience, forbidden words). Register-specific voice rules
(hook style, sentence rhythm, person of address, citation format, etc.) live
in the per-register template files referenced below.

Gate `[0d]` confirms the universal fields are filled and a register is
selected before letting the run proceed.

---

## Active register (selected per article at `[0b]`)

| Article mode | Default register | Template file |
|---|---|---|
| `paper` | academic-paper | `user-writing-style-academic-paper.md` |
| `combined` | academic-paper | `user-writing-style-academic-paper.md` |
| `repo` | repo-tutorial | `user-writing-style-repo-tutorial.md` |

To override per-article: at `[0b]`, request `--register academic-paper` or
`--register repo-tutorial` (overrides the mode default). The two templates
ship with the skill; you can clone one to a new file for a third register
(e.g., `user-writing-style-popsci.md`) and add a row to the table above.

`[2] read & propose` and `[3] write` read this index file FIRST, identify the
active register from the table, then read the corresponding template as the
authoritative voice anchor.

## Universal fields (apply across all registers)

### Author name

`jefferyLLLLL`

(Maximum 8 Chinese characters / WeChat metadata limit. The `author` frontmatter
field in `draft.md` is populated from this value.)

### Target audience (project-fixed; not user-configurable per-article)

> Academic readers (researchers). Make the writing accessible without
> dumbing it down: every section must convey both the high-level scientific
> framing (what question, why it matters) and the low-level methodology
> (what was actually done, with what data and comparisons).

Prompts treat this as a hard constraint. Every section must serve both the
"what is this about scientifically" reader and the "how does the method
actually work" reader within the same paragraph budget. Do not narrow to one
or the other.

### Forbidden words / tone

These trigger lint warnings (the `[2] read & propose` step injects this list
into `notes.md § Hype flags`; the `[3] write` step avoids parroting them):

- **震惊体**: `震惊!`, `重磅!`, `炸裂` — never. Academic registers do not use them.
- **Marketing buzzwords**: `颠覆`, `革命性`, `赋能`, `黑科技`, `史无前例` — avoid.
- **Hype hedges**: `也许能彻底解决`, `有望成为`, `或将颠覆` — avoid.
- **Unsourced superlatives**: `首次`, `第一个`, `unprecedented`, `first-ever`,
  `state-of-the-art` (without naming the comparator) — avoid; if the paper
  itself makes such a claim, paraphrase as "作者把它定位为相对 X 的改进"
  rather than repeating the bare claim.
- **Rough English-Chinese mixing**: `这个 idea 很 elegant`,
  `model 跑得很 work` — avoid. English NOUNS are kept (per Rule #1) but
  English adjectives / verbs in narrative flow read amateurish.

### Identity anchor (optional; only used if a register's template asks for it)

The current academic-paper and repo-tutorial templates do NOT include a
`## 解读者` section in the article output (the v0.1 design dropped it as
formalism — academic readers don't want PR-style "about the author"
framing). This field is therefore unused in the default registers, but kept
here for users who want to fork a template that does include it.

```
jefferyLLLLL,计算生物学方向,关注单细胞 / 多组学的方法学发展。
```

### Term handling defaults

These apply unless the active register overrides:

- First mention of an English-name method / tool / library: drop in English
  without translation. If the term is genuinely obscure within the audience,
  add a 4–10 char Chinese gloss in parentheses.
- Subsequent mentions: always English. Do NOT introduce a Chinese alias
  mid-article.
- Equations: WeChat does not render LaTeX. Describe in prose by default;
  screenshot from paper Methods for load-bearing key formulas
  (`<!-- IMG:formula-N -->` placeholder). Inline single symbols can use
  unicode (`Σ`, `α`, `β`, `≤`).

## Few-shot anchors (`examples/`)

The skill expects, when present, register-tagged anchor articles:

- `examples/published-article-academic-paper-01.md` — anchor for academic-paper register
- `examples/published-article-repo-tutorial-01.md` — anchor for repo-tutorial register

A common reasonable starting point is to ship 1–2 of your past published
articles per register. Without an anchor in the active register, the `[3]
write` step will warn at `[0d]` and the draft voice may drift on the first
run.

`examples/` is currently empty (only contains `README.md`). Drop in past
articles before the first real-publication run; for smoke-testing the
pipeline, the absence is acceptable and produces a draft drawn purely from
the active register's specifications.

## Files in this register system

- `user-writing-style.md` (this file) — index + universal fields
- `user-writing-style-academic-paper.md` — full register spec for paper / combined modes
- `user-writing-style-repo-tutorial.md` — full register spec for repo mode
