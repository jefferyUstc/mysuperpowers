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

Co-write a 微信公众号 science-explanation article. Three input modes:

- **repo** — a GitHub repo, for a tutorial-style article;
- **paper** — one or more local PDFs, for a figure-by-figure deep-dive;
- **combined** — repo + PDF(s), paper spine with algorithm-depth drawn from code.

v0.1 has no online paper resolver — paper / combined modes need PDFs you supply yourself.

### Trigger phrases

- "write a 公众号 article about this paper / this repo"
- "给我写一篇解读 \<paper\> 的公众号推文"
- "根据 \<repo url\> 和 \<paper\> 写篇推文"

### Required setup (one-time)

The skill refuses to draft without these:

1. **Universal style fields** — fill `skills/wechat-science-post/references/user-writing-style.md` (author name, target audience, forbidden words). It's an INDEX file pointing to register-specific templates.
2. **Active register template** — fill the per-mode voice spec:
   - `references/user-writing-style-academic-paper.md` for paper / combined modes
   - `references/user-writing-style-repo-tutorial.md` for repo mode
3. **Voice anchors** — drop 1–3 of your past articles into `skills/wechat-science-post/examples/` as `published-article-<register>-*.md` (e.g. `published-article-academic-paper-01.md`). Without anchors, voice drift is likely on the first run.

### Required setup (per session)

- A Python env with `pymupdf`, `pyyaml`, `Pillow`, `markdown-it-py`, `premailer`, plus `git` on PATH. Create with `conda env create -f skills/wechat-science-post/environment.yml`, or merge into an existing env. Tell Claude the absolute `$PY` path at the first gate.

### Pipeline (9 numbered steps + 1 conditional sub-step + 4 setup gates)

```
[0a-0d] env / mode / task-name / writing-style gates
[1]     ingest           — git clone (repo) or pymupdf text extraction (paper)
[2]     read-and-propose — Claude reads deeply, produces notes.md + questions
[2.5]   cross-ref        — combined mode only: paper↔repo correspondence
[3]     write            — Claude writes draft.md in one stretch
[4]     revise           — targeted edits driven by your pointers
[4.5]   figure_extract   — Vision-LLM auto-crops paper figures (paper / combined only)
[5]     figures_prep     — regularize figure images for WeChat
[6]     lint             — WeChat hard-limit checks
[7]     render           — Markdown + theme CSS → inline-styled HTML
[8]     preview          — local 375 px phone-width browser preview
[9]     push             — optional, draft to WeChat (never auto-publishes)
```

### Figures

**Paper / combined modes**: `[4.5]` auto-extracts figures from the source PDF. For each `<!-- IMG:N -->` placeholder in the draft, Claude:
1. Renders the source page at 300 DPI via `figure_extract.py page-image`
2. Reads the rendered PNG (multimodal vision)
3. Identifies the figure's bounding box visually
4. Calls `figure_extract.py crop` to save `figures/fig-N/image.png`

User override: place your own screenshot at `figures/fig-N/image.{png,jpg}` BEFORE `[4.5]` and the prompt skips that figure (yours wins). Cover image follows the same path.

**Repo mode**: `[5a]` runs `notebook_outputs.py` on the spine notebook to extract `code-example-N-cell-M-K` images; cover is user-supplied.

**Manual fallback paths** (if auto-extract is wrong or you prefer hand-curated):

- `work/<task>_<ts>/figures/cover.{png,jpg}`
- `work/<task>_<ts>/figures/fig-N/image.<ext>` for each paper figure
- `work/<task>_<ts>/figures/formula-N/image.<ext>` for screenshot formulas
- `work/<task>_<ts>/figures/code-example-N/cell-M-img-K.png` for repo notebook outputs

Then run `[5] figures_prep` to regularize.

### Writing-style registers (set at `[0d]`)

The article's **voice** (sentence rhythm, person-of-address, citation format, code-vs-prose discipline) comes from a register file under `references/`. Auto-picked at `[0d]`; user can override.

| Register | Voice |
|---|---|
| `academic-paper` | 第三人称密集学术博客;中长句;无 `我们`;`<Lab Institution> 等在 <Journal>` 引用格式 |
| `repo-tutorial` | 动手教程;短中句;允许 `我们`;algorithm-first 三段式(原理 → 代码 → 输出);reader 可顺序复制运行 |

Default mapping:
- paper / combined mode → `academic-paper`
- repo mode → `repo-tutorial`

### Themes (set at render time via `--theme <name>`; default = `default`)

The article's **visual style** is independent from voice. Pick at `render.py` invocation; can re-render the same draft with different themes for comparison.

| Theme | Visual |
|---|---|
| `default` | 炭灰文字 + 白底 + GitHub 蓝 accent |
| `academic-serif` | CJK 衬线 + 双线 h1 + 朱红 accent |
| `academic-warm` | 米黄纸底 + 棕墨水 + 锈色 accent |
| `academic-mono` | 纯黑白灰,无 accent |
| `wechat-bold` | 居中 h1 + 填色 h2 + 鲜亮蓝 accent |
| `wechat-elegant` | 圆角 + 阴影 + 斜体 blockquote + 青绿 accent |
| `paper-texture` | 米黄纸 + SVG 噪点纸纹背景 |
| `graph-paper` | 浅蓝方格背景 + 海军蓝 accent |
| `dark-mono` | 暗石板 + 青绿 accent |

### Output

- `work/<task>_<ts>/draft.md` — the article in Markdown (frontmatter + body + 1-line attribution)
- `work/<task>_<ts>/output.html` — WeChat-compatible HTML fragment, ready to paste into the 公众号 编辑器

### Manual edit & re-render

`draft.md` is the source of truth; everything else (`output*.html`, `figures/manifest.json`) is rebuildable. Edit `draft.md` in any editor, then re-render:

```bash
# Lint first (catches title>32 / digest>120 / missing IMG entries / etc.)
$PY skills/wechat-science-post/scripts/lint.py work/<task>_<ts>/draft.md

# Re-render the active theme
$PY skills/wechat-science-post/scripts/render.py \
    work/<task>_<ts>/draft.md --theme default --wrap \
    --out work/<task>_<ts>/output.html
```

When figures change as well (replaced cover, added new `<!-- IMG:N -->`, swapped a `fig-N/image.<ext>`), re-run `figures_prep.py` BEFORE `render.py`. Pure text edits skip that step.

LLM-driven targeted edits remain available via `[4] revise`; the manual path above is for "I know exactly what to fix."

### Optional: live push to WeChat draft (`[9]`)

The skill can create the draft for you via WeChat's API (still requires you to manually click 群发 in the web UI — never auto-publishes).

**Two-part config:**

1. **AppID + AppSecret** — pick one of:

   *Env vars (CI / temporary):*
   ```bash
   export WECHAT_APPID=wx1234567890abcdef
   export WECHAT_SECRET=abc123...
   ```

   *Config file (long-term, recommended):*
   ```bash
   mkdir -p ~/.config/wechat-science-post
   cat > ~/.config/wechat-science-post/config.yaml <<'EOF'
   wechat:
     appid: "wx1234567890abcdef"
     secret: "abc123..."
   EOF
   chmod 600 ~/.config/wechat-science-post/config.yaml
   ```

   Lookup order: env vars → config file → fail with a helpful message.

2. **IP whitelist** — find your outbound IP with `curl ifconfig.me`, then add it in 公众号后台 → 设置与开发 → 基本配置 → IP 白名单. Without this, WeChat returns errcode `40164`.

**Verify before pushing:**

```bash
$PY skills/wechat-science-post/scripts/push_draft.py work/<task>_<ts> --dry-run
```

`--dry-run` works without credentials; it parses everything and prints the exact JSON that would be POSTed. Use it to sanity-check title / digest / `content_source_url` before committing to the network call.

For the full errcode table, see [skills/wechat-science-post/SKILL.md § [9]](skills/wechat-science-post/SKILL.md).

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
| `wechat-science-post` | `~/.config/wechat-science-post/config.yaml` (or `WECHAT_APPID` / `WECHAT_SECRET` env vars) | `~/.cache/wechat-science-post/token.json` (access_token, 7200 s TTL); `work/<task>_<ts>/.pushed` sentinel after a successful push |
| `save-claude` | none | `~/.claude/settings.json` (`env.CLAUDE_CODE_SUBAGENT_MODEL*`), `~/.claude/agents/<worker>.md`, `~/.claude/CLAUDE.md` block; backups in `~/.claude/backups/save-claude-<stamp>.*/` |

Per-task work directories (`work/<task>_<ts>/` for `wechat-science-post`) are listed in `.gitignore` — they're scratch space, safe to `rm -rf` after publishing.

## Troubleshooting

**The skill doesn't activate even though I said the trigger phrase.**
Run `/plugin list` and confirm `mysuperpowers` is enabled. Restart the session if you just installed (the SessionStart hook only fires at session start).

**`[0a]` preflight fails with `import fitz` GLIBCXX error.**
This is the pymuppdf 1.27 / older glibc combo. Either `conda install -c conda-forge "libstdcxx-ng>=14"` in the env, or pin `pymupdf<1.24`. See [skills/wechat-science-post/SKILL.md § [0a]](skills/wechat-science-post/SKILL.md) for the full hint.

**WeChat push fails with errcode `40164`.**
IP not on whitelist. Run `curl ifconfig.me` to find your outbound IP, then add it in 公众号后台 → 设置与开发 → 基本配置 → IP 白名单. The full errcode table is in [skills/wechat-science-post/SKILL.md § [9]](skills/wechat-science-post/SKILL.md).

**PyPI upload fails with `403 Forbidden`.**
Token doesn't have upload scope for this project, or token is for a different account. Generate a project-scoped token in PyPI account settings; verify by running `preflight.py` again.

**save-claude verified OK but `/usage` still shows only `claude-fable-5-1`.**
Either the session predates the install (the `env` block loads at startup — open a new `claude`, `/clear` is not enough), or the spawn was a `fork` / `Explore` (both inherit the parent). Ask explicitly for the `sonnet-worker` subagent, then `scripts/verify.sh --transcript`. If a child still runs on Fable, reinstall with `--force`.

**save-claude `verify.sh` warns about a shell export.**
`CLAUDE_CODE_SUBAGENT_MODEL` or `CLAUDE_CODE_EFFORT_LEVEL` exported in your shell overrides the settings file (and, for effort, the worker's `effort:`). Unset it or make it agree with the profile.
