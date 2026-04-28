---
name: using-mysuperpowers
description: Use when starting any conversation — index of available mysuperpowers skills and when to invoke them. Establishes that skills must be loaded via the Skill tool before action, not via Read.
---

# Using mysuperpowers

`mysuperpowers` is a personal, curated skills library. Each skill encodes a proven workflow that should be followed exactly when its trigger matches. Skills override default behavior; user instructions in CLAUDE.md / AGENTS.md still take precedence.

## The rule

If there is even a small chance a skill applies to the user's request, invoke it via the `Skill` tool **before** taking any other action (including clarifying questions or exploration). Never use `Read` on a `SKILL.md` — the `Skill` tool loads it as an instruction; `Read` treats it as reference material the agent can ignore.

## Available skills

### python-pypi-release
Release a Python package to PyPI. Handles both first-ever publication and incremental version bumps (patch / minor / major / post / pre-release); mode is auto-detected from PyPI state.

**Trigger phrases (invoke on any of these):**
- "publish to PyPI" / "release a new version" / "upload to PyPI"
- "bump to X.Y.Z" / "release a .postN" / "cut a release"
- "first PyPI release" / "initial PyPI upload"
- "tag and push to PyPI"

### wechat-science-post
Co-write a WeChat Official Account (微信公众号) science-explanation article from a GitHub repo, a research paper, or both. Output is Simplified Chinese narrative with English proper nouns (algorithm names, person names, journal names, paper titles, identifiers) preserved.

**Trigger phrases (invoke on any of these):**
- "write a 公众号 article about this paper / this repo"
- "给我写一篇解读 <paper> 的公众号推文"
- "介绍一下这个 repo,准备发公众号"
- "把 <arXiv id / DOI / PDF path> 写成一篇科研解读"
- "根据 <repo url> 和 <paper> 写篇推文"

## How to invoke a skill

In Claude Code:

```
Skill(skill="mysuperpowers:python-pypi-release")
```

Announce what you're doing in one short sentence, then follow the loaded SKILL.md exactly. If the skill has a checklist, create TodoWrite items for each step.
