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

### save-claude
Route subagent work to Sonnet 5 or Opus 5 instead of letting it inherit the session's Fable-class model. Installs two pinned workers (`sonnet-worker` for scans, bounded edits, tests, extraction, progress checks; `opus-worker` for review, non-trivial refactors, coding), sets `CLAUDE_CODE_SUBAGENT_MODEL`, and adds a routing block to `~/.claude/CLAUDE.md`; backs up first; verifies with a real spawn.

**Invoke automatically** when the session model (named in your system prompt) is Fable 5, Fable 5.1, or newer: once, before the first Agent spawn. If routing is installed the skill confirms it in one line; if the user uninstalled it, it stays quiet; otherwise it installs (backed up, reversible) and says so in one line. A user instruction that names a model for a task overrides the routing for that task.

**Also invoke on:**
- "save my Fable quota" / "stop children inheriting fable"
- "subagents should use sonnet / opus" / "which model do my subagents run on"
- "install / verify / uninstall save-claude" / "switch routing profile"

## How to invoke a skill

In Claude Code:

```
Skill(skill="mysuperpowers:python-pypi-release")
```

Announce what you're doing in one short sentence, then follow the loaded SKILL.md exactly. If the skill has a checklist, create TodoWrite items for each step.
