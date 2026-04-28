# Few-shot anchor articles

Place 1–3 of your past published WeChat articles here as
`published-article-01.md`, `published-article-02.md`,
`published-article-03.md`.

These files are read by the `scan` / `plan` / `figure` / `draft` /
`revise` prompts as voice anchors. Without at least one anchor, the
skill's output will drift toward a generic science-writing voice on the
first run.

## Format

Plain Markdown. Keep the article as you published it — do NOT rewrite
for the skill's consumption. The prompts care about voice, rhythm,
term-handling, and connective density, all of which are visible in raw
published form.

Include at the top:

```markdown
---
title: "..."
published_at: "YYYY-MM-DD"
wechat_url: "..."
paper_reference: "DOI or arXiv id, if this was a paper walkthrough"
---

<body>
```

## Selection guidance

Pick articles where:

- You were satisfied with the voice
- The topic overlaps with what you usually write about
- The length is close to your typical target

Avoid articles that were heavily edited by an external editor, were
first drafts, or were off-topic experiments — those would anchor the
voice in a direction you do not want to repeat.

## Do not place anything else in this directory

The skill enumerates `examples/published-article-*.md` as few-shot
input. Placeholder files, notes, or other artifacts will confuse the
enumeration.
