# Skills — usage guide

Per-skill reference for **using** the skills in this library: trigger phrases, setup, typical flow, output, configuration. For installation see [README.md](README.md). For the deep workflow spec of each skill see its `SKILL.md`.

## How any skill is invoked

Skills auto-load via the SessionStart hook. You don't call them by name — you speak in the skill's trigger phrases, Claude matches and asks you to confirm before starting. All skills run a **gated pipeline**: each step requires your explicit `Y` before proceeding. Say `N` (or redirect with a different request) at any gate to stop or pivot.

If a skill doesn't activate when you expected: try a more on-trigger phrase, or check `/plugin list` to confirm `mysuperpowers` is enabled.

## Skills

| Skill | Use it when | Detail |
|---|---|---|
| [`python-pypi-release`](#python-pypi-release) | Releasing a Python package to PyPI | [SKILL.md](skills/python-pypi-release/SKILL.md) |
| [`wechat-science-post`](#wechat-science-post) | Writing a 微信公众号 article from a repo / paper / both | [SKILL.md](skills/wechat-science-post/SKILL.md) |
| [`save-claude`](#save-claude) | Making Claude Code subagents run on a cheaper model than the orchestrator | [SKILL.md](skills/save-claude/SKILL.md) |
| [`using-mysuperpowers`](#using-mysuperpowers) | Internal — never invoked directly | [SKILL.md](skills/using-mysuperpowers/SKILL.md) |

---

## python-pypi-release

13 gated steps that take a Python package from working tree → PyPI. Auto-detects first-ever publication vs. incremental update; supports patch / minor / major / post / pre-release versions.

### Trigger phrases

- "publish to PyPI" / "release a new version" / "upload to PyPI"
- "bump to X.Y.Z" / "release a .postN" / "cut a release"
- "first PyPI release"

### Required setup

| Item | What | Where |
|---|---|---|
| Python tools | `build`, `twine`, `packaging` installed in the env you'll release from | conda env or virtualenv |
| PyPI credentials | API token with upload scope for the project | `~/.pypirc` `[pypi]` section, OR `TWINE_USERNAME` / `TWINE_PASSWORD` env vars |
| Git | Clean working tree + a working `origin` remote | the project's git repo |

### Typical flow

1. **`[0a]`** Claude asks for `$PY` (the absolute path to the Python interpreter you want to release with). Answer with e.g. `/opt/conda/envs/foo/bin/python`.
2. **`[0]`** `preflight.py` runs — read-only checker for tooling, `pyproject.toml`, git state, and PyPI auth. Re-runnable until it returns clean.
3. Claude proposes the new version, awaits your `Y`.
4. Pytest → wheel build → wheel-sanity (catches `__all__`-without-import bugs) → commit → tag → upload.

### If a gate fails

Claude rolls back working-tree changes and deletes new-version dist artifacts. Re-run preflight after fixing, continue from where you left off.

### Output

- A new version tag pushed to origin
- New wheel + sdist on PyPI under the package name
- Commit + tag visible in `git log`

---

## wechat-science-post

Co-write a 微信公众号 science-explanation article for academic readers. Three input modes:

- **paper** — local PDF(s) you supply; a figure-by-figure interpretation;
- **repo** — a GitHub repo; a method walkthrough that explains the algorithm before the code;
- **combined** — repo + PDF; paper structure, with code anchors in the method sections.

### Trigger phrases

- "write a 公众号 article about this paper / this repo"
- "给我写一篇解读 \<paper\> 的公众号推文"
- "根据 \<repo url\> 和 \<paper\> 写篇推文"

### Setup (one time)

- **Python env:** `conda env create -f skills/wechat-science-post/environment.yml` (Claude offers to do this if the env is missing).
- **Author name:** `skills/wechat-science-post/references/style.md`.
- **Language rules:** `skills/wechat-science-post/references/language.md` holds every wording rule, including the word lists lint checks. Edit it there and lint follows.
- **Voice anchors:** past articles in `skills/wechat-science-post/examples/` (two reviewed articles ship there).
- **Standing decisions:** `skills/wechat-science-post/references/editorial-policy.md` records choices that apply to every article (e.g. no added critique, separate articles per paper). Claude reads it instead of asking again, and appends new general decisions you make.

### Flow (two review points)

```
0  confirm   mode, one-article-per-PDF vs supplements, work-dir slug   (one message)
1  ingest    ingest.py → work/<slug>/ingest/  (clean page text, DOI, figure index)
2  read      Claude writes notes.md and proposes titles + plan + questions with defaults   ← you reply once
3  write     Claude writes draft.md, then self-checks facts and Chinese wording
4  figures   figures.py auto extracts each figure at native resolution; crops only when needed
5  render    render.py = lint + image sizing + output.html + preview.html                   ← you review
6  revise    point at a passage; only that passage changes
7  push      optional; creates a WeChat draft, never publishes
```

### Output

- `work/<slug>/draft.md` — the article; the source of truth.
- `work/<slug>/output.html` — paste into the 公众号 editor.
- `work/<slug>/preview.html` — phone-width preview with cover, title, author and digest.
- `work/<slug>/figures/fig-N.png` — figure sources; drop your own file there to override one.

### Manual edit & re-render

Edit `draft.md` (or replace an image in `figures/`) in any editor, then:

```bash
$PY skills/wechat-science-post/scripts/render.py work/<slug>/draft.md [--theme wechat-elegant]
```

Themes: `wechat-elegant` (default), `wechat-bold`, `default`, `academic-serif`, `academic-warm`, `academic-mono`, `paper-texture`, `graph-paper`, `dark-mono`.

### Optional: push to the WeChat draft box

Put credentials in `WECHAT_APPID` / `WECHAT_SECRET`, or in `~/.config/wechat-science-post/config.yaml` (mode 600):

```yaml
wechat:
  appid: "wx..."
  secret: "..."
```

Add your outbound IP (`curl ifconfig.me`) under 公众号后台 → 设置与开发 → 基本配置 → IP 白名单, then:

```bash
$PY skills/wechat-science-post/scripts/push_draft.py work/<slug> --dry-run   # inspect, then drop --dry-run
```

Error codes and platform limits: [references/wechat-publishing.md](skills/wechat-science-post/references/wechat-publishing.md).

---

## save-claude

Stop burning Fable on subagent work Sonnet 5 or Opus 5 can do. Fable stays the orchestrator; every Agent-tool spawn runs on one of two pinned workers, and Fable picks the worker by task.

Claude Code resolves a subagent's model as: spawn `model:` param → agent frontmatter `model:` → `CLAUDE_CODE_SUBAGENT_MODEL` → the main model. With nothing set, every scan and test run you delegate runs on Fable ($10 / $50 per MTok vs Sonnet 5's $2 / $10). The skill sets the middle two; it never changes the session's own model or effort.

### When it runs

- **Automatically**, once per session, whenever the session model is Fable 5, Fable 5.1, or newer. Routing installed → one line and on with your task. Not installed → it installs (three files in `~/.claude/`, backed up first) and tells you; takes effect from the next session. Uninstalled by you → it stays quiet.
- **On request**: "save my Fable quota", "subagents should use sonnet / opus", "which model do my subagents run on", or `/save-claude [--dry-run | --verify | --uninstall | --force]`.
- **Override**: name a model for a task ("review this with opus") and that instruction wins for that task.

### Required setup

Claude Code ≥ 2.1.242 (`/tasks` shows subagent models; ≥ 2.1.257 for `--force`), `jq` on PATH, write access to `~/.claude/`. No Python.

### Workers

| Worker | Model / effort | Takes |
|---|---|---|
| `sonnet-worker` | `sonnet` / `xhigh` | repo scans and file inventories, edits limited to an explicit file list, running tests, extraction and summaries, checking processes or jobs and reporting progress |
| `opus-worker` | `opus` / `xhigh` | code review, non-trivial refactors, coding that needs design judgment |

Unnamed spawns default to `sonnet`. The division of labor is the `workers[].takes` field in `skills/save-claude/profiles/fable-routed.json`; it is rendered into the `CLAUDE.md` block and each worker's description, so edit it there and re-run `/save-claude`.

### First-time checklist

1. Install the plugin, open a new `claude` on Fable. The skill installs the routing and says so.
2. Open **another** new `claude` (the `env` block and `agents/` load at startup). Ask it to use `sonnet-worker` for a read-only repo inventory; check `/tasks` and `/usage` → *Usage by model*; then `/save-claude --verify` reads the session's `subagents/agent-*.jsonl` and fails if any child ran on the session's model.
3. Optional: A/B routing off (`--uninstall`) vs on, same task — `skills/save-claude/references/method.md`.

### Writes (and only these)

- `~/.claude/settings.json`: `env.CLAUDE_CODE_SUBAGENT_MODEL` (+ `_FORCE` with `--force`). Everything else untouched.
- `~/.claude/agents/sonnet-worker.md` and `opus-worker.md`: `model:` + `effort:` + the worker's `takes` as its description + a "you are a subagent" brief.
- `~/.claude/CLAUDE.md`: one block between `<!-- save-claude:begin -->` / `<!-- save-claude:end -->` listing each worker and what it takes; text outside the markers is preserved.

### Uninstall / rollback

```bash
skills/save-claude/scripts/install.sh --uninstall     # block + both workers + the two env keys; writes ~/.claude/save-claude.off
cp ~/.claude/backups/save-claude-<stamp>.*/settings.json ~/.claude/settings.json   # full restore
```

`save-claude.off` is the one file uninstall leaves behind: it stops the next Fable session from auto-installing again. `/save-claude` removes it and re-enables routing; delete it by hand for a fully clean state (auto-install then resumes). Backups stay under `~/.claude/backups/save-claude-*`.

The installed files live in `~/.claude/`, not in the plugin: `/plugin uninstall mysuperpowers` leaves them in place (routing keeps working without the plugin), and `/plugin update` does not refresh them. Run `--uninstall` before removing the plugin; re-run `/save-claude` after an update that changes `profiles/fable-routed.json`.

### Caveats

- `fork` always runs on the parent; `Explore` / `Plan` inherit it (`Explore` capped at Opus). The block routes scans to `sonnet-worker` by instruction; `--force` is the config-level override, but it also pins `opus-worker` to `sonnet`, so use it last.
- Plan quota ≠ API spend: `/usage`'s dollar figure is an estimate; the per-model split is what shows routing worked.
- Not "the cheapest setup": subagents can use more tokens in total and save money only when cheap tokens replace Fable tokens and quality holds. Measure.

---

## using-mysuperpowers

Internal index skill consulted by Claude at session start to know which skills are available and when to route to them. You do not invoke this directly. If you're curious what's loaded, ask: *"What mysuperpowers skills do you have?"*

---

## Configuration cheat sheet

Where each skill stores credentials / state on your machine:

| Skill | Credentials | Cache / state |
|---|---|---|
| `python-pypi-release` | `~/.pypirc` (or `TWINE_USERNAME` / `TWINE_PASSWORD` env vars) | `dist/` in the project; tags in git |
| `wechat-science-post` | `~/.config/wechat-science-post/config.yaml` (or `WECHAT_APPID` / `WECHAT_SECRET` env vars) | `~/.cache/wechat-science-post/token.json` (access_token, 7200 s TTL); `work/<slug>/.pushed` after a successful push |
| `save-claude` | none | `~/.claude/settings.json` (`env.CLAUDE_CODE_SUBAGENT_MODEL*`), `~/.claude/agents/<worker>.md`, `~/.claude/CLAUDE.md` block; backups in `~/.claude/backups/save-claude-<stamp>.*/` |

Per-article work directories (`work/<slug>/` for `wechat-science-post`) are listed in `.gitignore` — they're scratch space, safe to `rm -rf` after publishing.

## Troubleshooting

**The skill doesn't activate even though I said the trigger phrase.**
Run `/plugin list` and confirm `mysuperpowers` is enabled. Restart the session if you just installed (the SessionStart hook only fires at session start).

**The wechat-science-post preflight fails importing `pymupdf` with a GLIBCXX error.**
Newer pymupdf wheels need a recent libstdc++. Run `conda install -c conda-forge "libstdcxx-ng>=14"` in the env, or pin `pymupdf<1.24`.

**WeChat push fails with errcode `40164`.**
IP not on whitelist. Run `curl ifconfig.me` to find your outbound IP, then add it in 公众号后台 → 设置与开发 → 基本配置 → IP 白名单. The full errcode table is in [references/wechat-publishing.md](skills/wechat-science-post/references/wechat-publishing.md).

**PyPI upload fails with `403 Forbidden`.**
Token doesn't have upload scope for this project, or token is for a different account. Generate a project-scoped token in PyPI account settings; verify by running `preflight.py` again.

**save-claude verified OK but `/usage` still shows only `claude-fable-5-1`.**
Either the session predates the install (the `env` block loads at startup — open a new `claude`, `/clear` is not enough), or the spawn was a `fork` / `Explore` (both inherit the parent). Ask explicitly for the `sonnet-worker` subagent, then `scripts/verify.sh --transcript`. If a child still runs on Fable, reinstall with `--force`.

**save-claude `verify.sh` warns about a shell export.**
`CLAUDE_CODE_SUBAGENT_MODEL` or `CLAUDE_CODE_EFFORT_LEVEL` exported in your shell overrides the settings file (and, for effort, the worker's `effort:`). Unset it or make it agree with the profile.
