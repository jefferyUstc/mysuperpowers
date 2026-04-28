---
description: Bump the mysuperpowers plugin version, or check / audit current versions
---

The user wants to invoke the version-bump tooling at `scripts/bump-version.sh`.

Parse `$ARGUMENTS`:

- **Empty or `--check`** → run `./scripts/bump-version.sh --check` and report drift status. Read-only.
- **`--audit`** → run `./scripts/bump-version.sh --audit` and report any undeclared files containing the current version string. Read-only.
- **Matches `X.Y.Z` (semver-ish)** → this is destructive (edits manifest files). Before running:
  1. Run `./scripts/bump-version.sh --check` first and show the user the current state.
  2. Confirm the target version with the user explicitly.
  3. Only then run `./scripts/bump-version.sh <X.Y.Z>` and report results.
  4. After bump, remind the user to: review the diff, `git commit`, and (if they tag releases) `git tag v<X.Y.Z>`.

Do NOT auto-commit or auto-tag — the script intentionally only edits manifest files; git operations are the user's call.

Argument: $ARGUMENTS
