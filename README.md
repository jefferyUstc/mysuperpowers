# mysuperpowers

My personal skills library for Claude Code. Reusable, opinionated workflows that I want my coding agent to follow.

Inspired by [obra/superpowers](https://github.com/obra/superpowers), scoped down to what I actually need.

## What's inside

| Skill | One-line | Spec |
|---|---|---|
| `python-pypi-release` | Take a Python package from working tree to PyPI in 13 gated steps. | [SKILL.md](skills/python-pypi-release/SKILL.md) |
| `wechat-science-post` | Co-write a 微信公众号 science article from a paper / repo / both. 9 steps + 4 gates. | [SKILL.md](skills/wechat-science-post/SKILL.md) |
| `save-claude` | Route subagents to Sonnet 5 / Opus 5 instead of inheriting Fable 5.1. Install, verify with a real spawn, uninstall. | [SKILL.md](skills/save-claude/SKILL.md) |
| `using-mysuperpowers` | Internal index — Claude consults this at session start to know which skills are available. | [SKILL.md](skills/using-mysuperpowers/SKILL.md) |

For trigger phrases, setup steps, and typical flows, see **[user_manual.md](user_manual.md)**.

## Installation

### From GitHub

```
/plugin marketplace add jefferyUstc/mysuperpowers
/plugin install mysuperpowers@mysuperpowers
```

### From a local clone

```
/plugin marketplace add /absolute/path/to/mysuperpowers
/plugin install mysuperpowers@mysuperpowers
```

After install, restart the session — the SessionStart hook injects the skill index automatically.

Verify with `/plugin list` (you should see `mysuperpowers` enabled), or ask: *"What mysuperpowers skills do you have?"*

### Updating

```
/plugin update
```

`save-claude` writes its routing into `~/.claude/` (outside the plugin); `/plugin update` does not refresh those files. Re-run `/save-claude` after an update that changes its profile.

### Uninstalling

```
/save-claude --uninstall                      # first, if save-claude routing is installed: its files live in ~/.claude/ and survive plugin removal
/plugin uninstall mysuperpowers
/plugin marketplace remove mysuperpowers      # optional, removes the marketplace registration
```

## Issues / contributions

File issues at <https://github.com/jefferyUstc/mysuperpowers/issues>. PRs welcome — keep changes scoped to one skill at a time and update that skill's `SKILL.md` + `user_manual.md` section together.

## License

MIT — see plugin manifest for the canonical license field.

---

## For maintainers

Plugin version lives in two manifest files (`.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`); they must stay in sync. `scripts/bump-version.sh` (declared in `.version-bump.json`) handles the bump:

```bash
./scripts/bump-version.sh --check     # show current versions, detect drift
./scripts/bump-version.sh --audit     # check + scan repo for stray version strings
./scripts/bump-version.sh 0.2.0       # bump all declared manifests to 0.2.0
```

In a Claude Code session, `/bump-version 0.2.0` (or `--check` / `--audit`) runs the same flow with a confirmation prompt before any destructive bump.

Requires `jq` on PATH.

The skill scripts read the plugin version at runtime (no per-skill version file) — bump the plugin and every skill picks it up on the next run.
