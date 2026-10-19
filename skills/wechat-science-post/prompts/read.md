# Read and propose

Read the source the way you would if you had to teach it to a colleague tomorrow: well enough to defend every sentence the article will contain. The output is `work/<slug>/notes.md`, which the writing step trusts, and one message to the user.

## Before reading

- `references/editorial-policy.md` — decisions already made. Anything it covers is not a question.
- `references/style.md` and `references/language.md` — who the reader is, and the wording rules `notes.md` already follows.
- `ingest/manifest.json` — title, DOI, venue, page count, and `figures` (main figure → caption page).

## Reading

The page text in `ingest/text/<id>/` is clean prose with headers and line numbers removed. Tables are flattened and equations may be garbled; when either matters, Read that page of the PDF itself.

A reasonable order: abstract and introduction for the question and claim; each main figure's legend at its caption page; the results text that walks through each figure; methods for anything the article will explain; discussion for the authors' own framing and limits. Read supplementary material only where the main text leans on it.

You are done when you can state the contribution in two Chinese sentences (the problem, then what was done) and can point to the page behind every number you intend to use.

## `notes.md`

Write it following `references/language.md`. Free-form prose is fine; these parts must be present because the next step relies on them:

1. **元信息** — exact English title, first and corresponding authors with institutions, venue and year, DOI, code / data links.
2. **核心论点** — the two sentences.
3. **方法要点** — the method at the depth a peer needs: what is measured, how, and what makes it work. Name the design choices that matter.
4. **图清单** — one row per main figure: number, caption page, one-line take-home, role (method / setup / key result / application), and whether it gets its own section, shares one, or is skipped and why.
5. **关键数字** — every number the article may cite, each with its page (`436,908 个双模态细胞 — p7`). The writer quotes from this list.
6. **作者自己的限定** — hedged claims, stated limitations, open questions, in the authors' words. These are reproduced faithfully; whether the article adds its own critique is an editorial-policy matter.
7. **Hype flags** — phrases from the paper the article must not echo, each in backticks (`` `ultra-high-throughput` ``). Lint warns if one appears in the draft. Write `无` if there are none.
8. **提案** — two or three titles of at most 32 characters with a one-line trade-off each; the hook direction; the section plan with a character budget per section that sums to the article budget (see `prompts/write.md`); what is merged or skipped and why.
9. **待确认** — only what the material and the policy cannot settle: an unclear term, an unreadable panel, a number the abstract states but the figures do not show, a structural choice the user should own. Every question carries a default answer. Zero questions is fine; more than six means you are stalling.

## Message to the user (gate 1)

Short: the thesis, the titles, the section plan, and the 待确认 list with defaults, plus the path to `notes.md`. Say that unanswered questions take their defaults. If a reply contains a decision about articles in general, record it in `references/editorial-policy.md`.
