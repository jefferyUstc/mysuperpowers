---
description: Route Claude Code subagents to Sonnet 5 / Opus 5 instead of Fable — install, refresh, verify, or remove
---

Invoke `mysuperpowers:save-claude` via the Skill tool, then act on `$ARGUMENTS`:

- empty → `scripts/install.sh` (install or refresh; clears the opt-out marker); report in one line what was written, that it takes effect from the next session, and how to undo
- `--dry-run` → `scripts/install.sh --dry-run`; no writes
- `--verify` → `scripts/verify.sh --transcript` for this repo; no writes
- `--uninstall` → `scripts/install.sh --uninstall`; report the backup path and that auto-install is now off
- `--force` → explain that `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` also pins `opus-worker` to `sonnet`, then `scripts/install.sh --force`

Argument: $ARGUMENTS
