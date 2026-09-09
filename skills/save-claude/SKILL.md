---
name: save-claude
description: Route subagent work to Sonnet 5 or Opus 5 instead of letting it inherit the session's Fable-class model. Invoke at the start of any session running Fable 5, Fable 5.1, or a newer model (the model named in your system prompt), before the first Agent spawn, so Fable tokens go to orchestration/thinking only. If the user explicitly names a model for a task, follow the user for that task.
when_to_use: >-
  Session model is claude-fable-5, claude-fable-5-1, or newer: invoke once, automatically, before delegating anything.
  User asks to save Fable quota, make subagents cheaper, or which model subagents run on.
  /usage "Usage by model" lists only the Fable model even though Agent spawns happened.
argument-hint: "[--dry-run | --verify | --uninstall | --force]"
---

# save-claude

Stop burning Fable on subagent work Sonnet 5 or Opus 5 can do. Fable stays the orchestrator; every Agent-tool spawn runs on one of two pinned workers.

Precedence: a user instruction that names a model for a task wins for that task. Everything else follows the routing below.

## Every Fable session

```bash
"${CLAUDE_SKILL_DIR}/scripts/install.sh" --status
```

| Output | Do |
|---|---|
| `active (...)` | One line: routing is active. Continue the task; delegate as `~/.claude/CLAUDE.md` describes. |
| `disabled (...)` | The user uninstalled it. Say nothing and continue without routing; only an explicit `/save-claude` re-enables it. |
| `missing: ...` | Run `"${CLAUDE_SKILL_DIR}/scripts/install.sh"` without asking; it backs up first. Report in one line what was written, that it takes effect from the next session, and that `/save-claude --uninstall` undoes it. Continue the task. |

## How Claude Code picks a subagent's model

| Priority | Source | Set by this skill |
|---|---|---|
| 1 | Agent-tool `model:` parameter on the spawn | no; the CLAUDE.md block forbids passing your own model |
| 2 | Agent frontmatter `model:` | yes: `~/.claude/agents/sonnet-worker.md`, `opus-worker.md` |
| 3 | `CLAUDE_CODE_SUBAGENT_MODEL` (settings `env` block) | yes: `sonnet`, the default for any spawn without its own `model:` |
| 4 | The main conversation's model | the inheritance this skill prevents |

Bypasses: `fork` always runs on the parent; `Explore` and `Plan` inherit it (`Explore` capped at Opus). `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` (`--force`, Claude Code 2.1.257+) makes 3 win over 1 and 2, which also pins `opus-worker` to `sonnet`; last resort only. A worker's `effort:` pins the child's effort unless the shell exports `CLAUDE_CODE_EFFORT_LEVEL`.

## Workers

| Worker | Model / effort | Takes |
|---|---|---|
| `sonnet-worker` | `sonnet` / `xhigh` | repo scans and file inventories, edits limited to an explicit file list, running tests, extraction and summaries, checking processes or jobs and reporting progress and status |
| `opus-worker` | `opus` / `xhigh` | code review, non-trivial refactors, coding that needs design judgment |

Unnamed spawns default to `sonnet`. The session's own model and effort are never changed. The division of labor is `workers[].takes` in `profiles/fable-routed.json`; it is rendered into the CLAUDE.md block and each worker's description, so edit it there and re-run the install.

## What install writes

- `~/.claude/settings.json`: `env.CLAUDE_CODE_SUBAGENT_MODEL` (+ `_FORCE` with `--force`). Every other key untouched.
- `~/.claude/agents/<worker>.md`, one per worker: `model:`, `effort:`, its `takes` as the description, and a "you are a subagent" brief.
- `~/.claude/CLAUDE.md`: one block between `<!-- save-claude:begin -->` and `<!-- save-claude:end -->` listing each worker and what it takes; text outside the markers is preserved.

Backups go to `~/.claude/backups/save-claude-<stamp>.*/`. `--claude-home DIR` targets another config dir.

## Commands

| Command | Effect |
|---|---|
| `install.sh` | Install or refresh; clears the opt-out marker |
| `install.sh --dry-run` | Show the settings diff, worker files, and block; write nothing |
| `install.sh --uninstall` | Remove the block, both workers, and the two env keys; write `~/.claude/save-claude.off` so no Fable session auto-installs again; backups kept |
| `install.sh --force` | Install with `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`; explain the opus-worker consequence first |
| `verify.sh` | Static check of the three pieces (or, with the marker present, that all three are gone) |
| `verify.sh --transcript [session-id]` | Read `~/.claude/projects/<cwd>/<session>/subagents/agent-*.jsonl`; fail if any child ran on the session's model |

## Verify once after the first install

The `env` block and `agents/` load at session start, so the installing session proves nothing. Tell the user:

1. Open a new `claude` (not just `/clear`).
2. Ask it: *"Use the `sonnet-worker` subagent for a read-only inventory of this repo's top-level files."*
3. `/tasks` names the subagent's model; `/usage` under *Usage by model* must list `claude-sonnet-5`.
4. From that repo: `"${CLAUDE_SKILL_DIR}/scripts/verify.sh" --transcript`.

To measure the saving, follow `references/method.md`.

## If a child still runs on Fable

- The spawn passed the parent model, was a `fork`, or an agent says `model: inherit`: reinstall with `--force`, open a new session, verify again.
- `Explore` on `claude-opus-5` is its documented cap, not a routing failure; the block routes scans to `sonnet-worker` instead.
- A worker's model is rejected by an `availableModels` policy: the block says to use the other worker. If both are blocked, `--uninstall` and say routing is unavailable on this account.

## Files

- `profiles/fable-routed.json`: workers (model, effort, `takes`), default model for unnamed spawns
- `templates/CLAUDE.routing.md`, `templates/agents/worker.md`: rendered per worker
- `scripts/install.sh`, `scripts/verify.sh`: bash + jq, no Python
- `references/method.md`: measuring, list prices, claim rules
