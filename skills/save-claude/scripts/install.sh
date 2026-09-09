#!/usr/bin/env bash
#
# install.sh - install, inspect, or remove save-claude subagent routing in a Claude Code config dir.
#
# Install writes three things and nothing else (the session's model and effort are never touched):
#   settings.json       env.CLAUDE_CODE_SUBAGENT_MODEL (default for unnamed spawns), plus
#                       env.CLAUDE_CODE_SUBAGENT_MODEL_FORCE with --force
#   agents/<worker>.md  one pinned worker per profile entry (frontmatter model + effort)
#   CLAUDE.md           one block between <!-- save-claude:begin --> and <!-- save-claude:end -->
# Existing files are copied to ~/.claude/backups/save-claude-<stamp>.*/ first.
#
# --uninstall removes all three and writes <config dir>/save-claude.off so no Fable session
# auto-installs again. A plain install removes that marker.
#
# Usage: install.sh [--profile NAME] [--force] [--dry-run] [--status] [--uninstall]
#                   [--claude-home DIR] [--list-profiles]
# Requires bash 4+ and jq.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROFILES_DIR="$SKILL_DIR/profiles"
TEMPLATES_DIR="$SKILL_DIR/templates"

BEGIN_MARK='<!-- save-claude:begin'
END_MARK='<!-- save-claude:end -->'
WORKER_STAMP='installed-by: mysuperpowers:save-claude'

PROFILE="fable-routed"
CONF_DIR="$HOME/.claude"
FORCE=0
DRY_RUN=0
STATUS=0
UNINSTALL=0

usage() {
  cat <<EOF
Usage: $(basename "$0") [--profile NAME] [--force] [--dry-run] [--status] [--uninstall]
                  [--claude-home DIR] [--list-profiles]

  (no flag)          install or refresh the routing; clears the opt-out marker
  --profile NAME     profile under profiles/ (default: fable-routed)
  --force            also set CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1: every subagent, workers
                     included, runs on the env model (Claude Code >= 2.1.257). Last resort.
  --dry-run          print the settings diff, workers, and CLAUDE.md block; write nothing
  --status           print one line: active (...) | disabled (...) | missing: ...; write nothing
  --uninstall        remove the block, the workers, and the two env keys; write the opt-out marker
  --claude-home DIR  config dir (default ~/.claude); CLAUDE.md goes to DIR/CLAUDE.md
  --list-profiles    show the profile table and exit
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)     PROFILE="$2"; shift 2 ;;
    --claude-home) CONF_DIR="$2"; shift 2 ;;
    --force)       FORCE=1; shift ;;
    --dry-run)     DRY_RUN=1; shift ;;
    --status)      STATUS=1; shift ;;
    --uninstall)   UNINSTALL=1; shift ;;
    --list-profiles)
      printf '%-13s %-46s %s\n' PROFILE WORKERS NOTES
      for f in "$PROFILES_DIR"/*.json; do
        jq -r '[.name, (.workers | map(.name + "=" + .model + "/" + .effort) | join(", ")), .notes] | @tsv' "$f" \
          | awk -F'\t' '{printf "%-13s %-46s %s\n", $1, $2, $3}'
      done
      exit 0 ;;
    -h|--help)     usage; exit 0 ;;
    *) echo "unknown arg: $1" >&2; usage >&2; exit 2 ;;
  esac
done

command -v jq >/dev/null || { echo "error: jq is required" >&2; exit 2; }

SETTINGS="$CONF_DIR/settings.json"
AGENTS_DIR="$CONF_DIR/agents"
CLAUDE_MD="$CONF_DIR/CLAUDE.md"
MARKER="$CONF_DIR/save-claude.off"
BACKUP_ROOT="$HOME/.claude/backups"

# --- profile ---

PROFILE_FILE="$PROFILES_DIR/$PROFILE.json"
if [[ ! -f "$PROFILE_FILE" ]]; then
  echo "unknown profile: $PROFILE (available: $(ls "$PROFILES_DIR" | sed 's/\.json$//' | tr '\n' ' '))" >&2
  exit 2
fi
PARENT_MODEL=$(jq -r '.parent_model' "$PROFILE_FILE")
DEFAULT_SUB=$(jq -r '.default_subagent_model' "$PROFILE_FILE")
WORKERS=$(jq -c '.workers[]' "$PROFILE_FILE")   # one JSON object per line

# --- helpers ---

each_worker() {  # run "$1 <worker json>" for every worker
  local w
  while IFS= read -r w; do [[ -n "$w" ]] && "$1" "$w"; done <<<"$WORKERS"
}

worker_name() { jq -r '.name' <<<"$1"; }

render_worker() {  # $1: worker JSON -> stdout
  local name model effort takes
  name=$(jq -r '.name' <<<"$1"); model=$(jq -r '.model' <<<"$1")
  effort=$(jq -r '.effort' <<<"$1"); takes=$(jq -r '.takes' <<<"$1")
  sed -e "s|{{PROFILE}}|$PROFILE|g" -e "s|{{WORKER_NAME}}|$name|g" -e "s|{{WORKER_MODEL}}|$model|g" \
      -e "s|{{WORKER_EFFORT}}|$effort|g" -e "s|{{WORKER_TAKES}}|$takes|g" "$TEMPLATES_DIR/agents/worker.md"
}

worker_line() { jq -r '"- `\(.name)` (`\(.model)`, effort `\(.effort)`): \(.takes)."' <<<"$1"; }

render_block() {  # the CLAUDE.md block with one bullet per worker
  local lines; lines=$(each_worker worker_line)
  sed -e "s|{{PROFILE}}|$PROFILE|g" -e "s|{{PARENT_MODEL}}|$PARENT_MODEL|g" "$TEMPLATES_DIR/CLAUDE.routing.md" \
    | awk -v repl="$lines" '$0 == "{{WORKER_LINES}}" { print repl; next } { print }'
}

existing_settings() { if [[ -s "$SETTINGS" ]]; then cat "$SETTINGS"; else echo '{}'; fi; }

merge_settings() {  # stdin: existing JSON -> stdout: merged JSON
  # Aliases, not IDs, so the workers float to the newest model of each tier.
  jq --arg sub "$DEFAULT_SUB" --argjson force "$FORCE" '
    .env = ((.env // {}) + {CLAUDE_CODE_SUBAGENT_MODEL: $sub})
    | (if $force == 1 then .env.CLAUDE_CODE_SUBAGENT_MODEL_FORCE = "1"
       else del(.env.CLAUDE_CODE_SUBAGENT_MODEL_FORCE) end)
  '
}

uninstall_settings() {  # stdin -> stdout; drops only the two subagent env keys
  jq 'del(.env.CLAUDE_CODE_SUBAGENT_MODEL, .env.CLAUDE_CODE_SUBAGENT_MODEL_FORCE)
      | (if (.env // {}) == {} then del(.env) else . end)'
}

strip_block() {  # stdin -> stdout without any save-claude block, marker lines included
  awk -v b="$BEGIN_MARK" -v e="$END_MARK" '
    index($0, b) == 1 { skip = 1 }
    !skip { print }
    index($0, e) == 1 { skip = 0 }
  '
}

stripped_claude_md() { if [[ -f "$CLAUDE_MD" ]]; then strip_block < "$CLAUDE_MD"; fi; }

merged_claude_md() {  # existing CLAUDE.md minus old block, plus fresh block
  local base; base=$(stripped_claude_md)
  if [[ -n "${base//[[:space:]]/}" ]]; then printf '%s\n\n' "$base"; fi
  render_block
}

installed_workers() {  # agent files this skill wrote, any profile
  [[ -d "$AGENTS_DIR" ]] || return 0
  grep -ls "$WORKER_STAMP" "$AGENTS_DIR"/*.md 2>/dev/null || true
}

write_atomic() {  # $1: target; stdin: content
  local target="$1" tmp
  mkdir -p "$(dirname "$target")"
  tmp=$(mktemp "$target.XXXXXX")
  cat > "$tmp"
  mv -f "$tmp" "$target"
}

write_worker() { render_worker "$1" | write_atomic "$AGENTS_DIR/$(worker_name "$1").md"; }

print_worker() { echo; echo "--- $AGENTS_DIR/$(worker_name "$1").md ---"; render_worker "$1"; }

write_claude_md_without_block() {
  local rest; rest=$(stripped_claude_md)
  if [[ -n "${rest//[[:space:]]/}" ]]; then printf '%s\n' "$rest" | write_atomic "$CLAUDE_MD"
  elif [[ -f "$CLAUDE_MD" ]]; then rm -f "$CLAUDE_MD"; echo "removed $CLAUDE_MD (only the block was in it)"; fi
}

# --- status ---

if (( STATUS )); then
  if [[ -f "$MARKER" ]]; then echo "disabled ($MARKER present; run /save-claude to re-enable)"; exit 0; fi
  missing=()
  [[ "$(jq -r '.env.CLAUDE_CODE_SUBAGENT_MODEL // empty' "$SETTINGS" 2>/dev/null)" == "$DEFAULT_SUB" ]] || missing+=("env.CLAUDE_CODE_SUBAGENT_MODEL")
  grep -qs "$BEGIN_MARK" "$CLAUDE_MD" || missing+=("CLAUDE.md block")
  while IFS= read -r w; do
    [[ -n "$w" ]] || continue
    n=$(worker_name "$w"); [[ -f "$AGENTS_DIR/$n.md" ]] || missing+=("$n")
  done <<<"$WORKERS"
  if (( ${#missing[@]} )); then echo "missing: ${missing[*]}"
  else echo "active ($(each_worker worker_name | paste -sd, -); unnamed spawns -> $DEFAULT_SUB)"; fi
  exit 0
fi

# --- dry run ---

if (( DRY_RUN )); then
  if (( UNINSTALL )); then
    echo "DRY RUN: uninstall (nothing written)"
    echo "--- settings.json diff ---"
    diff -u <(existing_settings | jq .) <(existing_settings | uninstall_settings) || true
    echo "--- worker files that would be removed ---"; installed_workers | sed 's/^/  /'
    echo "--- CLAUDE.md after removing the block ---"; stripped_claude_md
    echo "--- marker that would be written ---"; echo "  $MARKER"
    exit 0
  fi
  echo "DRY RUN: profile $PROFILE (nothing written)"
  echo "workers: $(each_worker worker_name | tr '\n' ' ')(default for unnamed spawns: $DEFAULT_SUB; force=$FORCE)"
  echo "targets: $SETTINGS | $AGENTS_DIR/ | $CLAUDE_MD"
  echo; echo "--- settings.json diff ---"
  diff -u <(existing_settings | jq .) <(existing_settings | merge_settings) || true
  each_worker print_worker
  echo; echo "--- block merged into $CLAUDE_MD ---"; render_block
  exit 0
fi

# --- backup ---

mkdir -p "$BACKUP_ROOT"
BACKUP="$(mktemp -d "$BACKUP_ROOT/save-claude-$(date -u +%Y%m%dT%H%M%SZ).XXXX")"
[[ -f "$SETTINGS" ]] && cp -p "$SETTINGS" "$BACKUP/settings.json"
[[ -f "$CLAUDE_MD" ]] && cp -p "$CLAUDE_MD" "$BACKUP/CLAUDE.md"
if [[ -d "$AGENTS_DIR" ]] && compgen -G "$AGENTS_DIR/*.md" > /dev/null; then
  mkdir -p "$BACKUP/agents"; cp -p "$AGENTS_DIR"/*.md "$BACKUP/agents/"
fi

# --- uninstall ---

if (( UNINSTALL )); then
  [[ -f "$SETTINGS" ]] && existing_settings | uninstall_settings | write_atomic "$SETTINGS"
  while IFS= read -r w; do [[ -n "$w" ]] && rm -f "$w" && echo "removed $w"; done < <(installed_workers)
  write_claude_md_without_block
  : > "$MARKER"
  echo "uninstalled save-claude routing from $CONF_DIR"
  echo "marker:   $MARKER (no Fable session auto-installs again; /save-claude re-enables)"
  echo "backup:   $BACKUP (earlier backups stay under $BACKUP_ROOT/save-claude-*)"
  exit 0
fi

# --- install ---

mkdir -p "$CONF_DIR"
rm -f "$MARKER"
existing_settings | merge_settings | write_atomic "$SETTINGS"
while IFS= read -r w; do [[ -n "$w" ]] && rm -f "$w"; done < <(installed_workers)   # drop workers from any earlier profile
each_worker write_worker
merged_claude_md | write_atomic "$CLAUDE_MD"

echo "installed $PROFILE into $CONF_DIR (takes effect from the next session)"
echo "backup:   $BACKUP"
echo
"$SCRIPT_DIR/verify.sh" --profile "$PROFILE" --claude-home "$CONF_DIR"
