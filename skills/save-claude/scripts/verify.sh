#!/usr/bin/env bash
#
# verify.sh - check a save-claude install. Read-only.
#
# Default: settings.json, the worker files, and the CLAUDE.md block agree with the profile.
#   With the opt-out marker present, checks instead that everything was removed cleanly.
# --transcript [SESSION_ID]: also read ~/.claude/projects/<encoded cwd>/<session>/subagents/agent-*.jsonl
#   and report the model each child actually ran on; FAIL if any child ran on the session's own model.
#
# Usage: verify.sh [--profile NAME] [--claude-home DIR] [--transcript [SESSION_ID]] [--project-dir DIR]
# Exit: 0 OK, 1 FAIL, 2 usage.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROFILES_DIR="$(cd "$SCRIPT_DIR/.." && pwd)/profiles"
BEGIN_MARK='<!-- save-claude:begin'

PROFILE=""
CONF_DIR="$HOME/.claude"
TRANSCRIPT=0
SESSION_ID=""
PROJECT_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)     PROFILE="$2"; shift 2 ;;
    --claude-home) CONF_DIR="$2"; shift 2 ;;
    --project-dir) PROJECT_DIR="$2"; shift 2 ;;
    --transcript)
      TRANSCRIPT=1; shift
      if [[ $# -gt 0 && "$1" != --* ]]; then SESSION_ID="$1"; shift; fi ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

command -v jq >/dev/null || { echo "error: jq is required" >&2; exit 2; }

SETTINGS="$CONF_DIR/settings.json"
AGENTS_DIR="$CONF_DIR/agents"
CLAUDE_MD="$CONF_DIR/CLAUDE.md"
MARKER="$CONF_DIR/save-claude.off"

# Profile: flag, else the one named in the CLAUDE.md marker, else default.
if [[ -z "$PROFILE" && -f "$CLAUDE_MD" ]]; then
  PROFILE=$(sed -n 's/^<!-- save-claude:begin (profile \([a-z0-9-]*\).*/\1/p' "$CLAUDE_MD" | head -1)
fi
PROFILE="${PROFILE:-fable-routed}"
PROFILE_FILE="$PROFILES_DIR/$PROFILE.json"
[[ -f "$PROFILE_FILE" ]] || { echo "unknown profile: $PROFILE" >&2; exit 2; }

PARENT_MODEL=$(jq -r '.parent_model' "$PROFILE_FILE")
DEFAULT_SUB=$(jq -r '.default_subagent_model' "$PROFILE_FILE")
WORKERS=$(jq -c '.workers[]' "$PROFILE_FILE")
FIRST_WORKER=$(jq -r '.workers[0].name' "$PROFILE_FILE")

errors=()
warns=()

s_model=$(jq -r '.model // empty' "$SETTINGS" 2>/dev/null || true)
s_sub=$(jq -r '.env.CLAUDE_CODE_SUBAGENT_MODEL // empty' "$SETTINGS" 2>/dev/null || true)
s_force=$(jq -r '.env.CLAUDE_CODE_SUBAGENT_MODEL_FORCE // empty' "$SETTINGS" 2>/dev/null || true)

verdict() {
  for w in "${warns[@]:-}"; do [[ -n "$w" ]] && echo "warn: $w"; done
  if (( ${#errors[@]} )); then
    echo "verify: FAIL"; printf -- '- %s\n' "${errors[@]}"; exit 1
  fi
  echo "verify: OK"; exit 0
}

# --- uninstalled state: everything must be gone ---

if [[ -f "$MARKER" ]]; then
  echo "status:    disabled ($MARKER)"
  [[ -z "$s_sub" ]] || errors+=("marker present but env.CLAUDE_CODE_SUBAGENT_MODEL='$s_sub' remains")
  [[ -z "$s_force" ]] || errors+=("marker present but env.CLAUDE_CODE_SUBAGENT_MODEL_FORCE remains")
  if grep -qs "$BEGIN_MARK" "$CLAUDE_MD"; then errors+=("marker present but CLAUDE.md still has the block"); fi
  while IFS= read -r w; do
    [[ -n "$w" ]] || continue
    f="$AGENTS_DIR/$(jq -r '.name' <<<"$w").md"; [[ -f "$f" ]] && errors+=("marker present but $f remains")
  done <<<"$WORKERS"
  verdict
fi

# --- settings.json ---

if [[ ! -s "$SETTINGS" ]]; then
  errors+=("missing $SETTINGS")
elif ! jq -e . "$SETTINGS" >/dev/null 2>&1; then
  errors+=("$SETTINGS is not valid JSON")
else
  [[ "$s_sub" == "$DEFAULT_SUB" ]] || errors+=("env.CLAUDE_CODE_SUBAGENT_MODEL is '${s_sub:-unset}', want '$DEFAULT_SUB'")
fi

# Shell exports win over the settings file for these keys.
if [[ -n "${CLAUDE_CODE_SUBAGENT_MODEL:-}" && "$CLAUDE_CODE_SUBAGENT_MODEL" != "$DEFAULT_SUB" ]]; then
  warns+=("shell exports CLAUDE_CODE_SUBAGENT_MODEL=$CLAUDE_CODE_SUBAGENT_MODEL, which overrides the settings env block")
fi
if [[ -n "${CLAUDE_CODE_EFFORT_LEVEL:-}" ]]; then
  warns+=("shell exports CLAUDE_CODE_EFFORT_LEVEL=$CLAUDE_CODE_EFFORT_LEVEL, which overrides every effort setting including the workers'")
fi
[[ -n "$s_force" ]] && warns+=("FORCE is set: every subagent, workers included, runs on '$s_sub'")

# --- workers + CLAUDE.md ---

worker_summary=()
[[ -f "$CLAUDE_MD" ]] || errors+=("missing $CLAUDE_MD")
if [[ -f "$CLAUDE_MD" ]] && ! grep -q "$BEGIN_MARK" "$CLAUDE_MD"; then errors+=("CLAUDE.md has no save-claude block"); fi
while IFS= read -r w; do
  [[ -n "$w" ]] || continue
  name=$(jq -r '.name' <<<"$w"); model=$(jq -r '.model' <<<"$w"); effort=$(jq -r '.effort' <<<"$w")
  file="$AGENTS_DIR/$name.md"
  if [[ ! -f "$file" ]]; then
    errors+=("missing worker $file"); worker_summary+=("$name = $model/$effort  [missing]"); continue
  fi
  w_model=$(sed -n 's/^model:[[:space:]]*//p' "$file" | head -1)
  w_effort=$(sed -n 's/^effort:[[:space:]]*//p' "$file" | head -1)
  [[ "$w_model" == "$model" ]] || errors+=("$name model is '${w_model:-unset}', want '$model'")
  [[ "$w_effort" == "$effort" ]] || errors+=("$name effort is '${w_effort:-unset}', want '$effort'")
  [[ "$w_model" == "$PARENT_MODEL" ]] && errors+=("$name runs on the parent model")
  if [[ -f "$CLAUDE_MD" ]] && ! grep -q "\`$name\`" "$CLAUDE_MD"; then errors+=("CLAUDE.md block does not name $name"); fi
  worker_summary+=("$name = $w_model/$w_effort  [$file]")
done <<<"$WORKERS"

# --- summary ---

echo "profile:   $PROFILE   [settings model: ${s_model:-unset}, left as-is]"
echo "default:   unnamed spawns -> ${s_sub:-unset}   [force: ${s_force:-off}]"
for line in "${worker_summary[@]}"; do echo "worker:    $line"; done
echo "claude.md: $CLAUDE_MD"

# --- transcript check ---

if (( TRANSCRIPT )); then
  echo
  [[ -n "$PROJECT_DIR" ]] || PROJECT_DIR="$HOME/.claude/projects/$(printf '%s' "$PWD" | sed 's#[^A-Za-z0-9-]#-#g')"
  if [[ ! -d "$PROJECT_DIR" ]]; then
    errors+=("no transcript dir for this cwd: $PROJECT_DIR (run a session here first, or pass --project-dir)")
  else
    if [[ -n "$SESSION_ID" ]]; then SUB_DIR="$PROJECT_DIR/$SESSION_ID/subagents"
    else SUB_DIR=$(ls -td "$PROJECT_DIR"/*/subagents 2>/dev/null | head -1 || true); fi
    if [[ -n "$SUB_DIR" && -d "$SUB_DIR" ]]; then
      session=$(basename "$(dirname "$SUB_DIR")")
      # The session's own model comes from its main transcript; fall back to the profile's family.
      parent=$(jq -r 'select(.type=="assistant" and ((.isSidechain // false) | not)) | .message.model // empty' \
                 "$PROJECT_DIR/$session.jsonl" 2>/dev/null | sort | uniq -c | sort -rn | head -1 | awk '{print $2}')
      echo "session:   $session   (model: ${parent:-unknown, matching family '$PARENT_MODEL'})"
      cloned=0; n=0
      for f in "$SUB_DIR"/agent-*.jsonl; do
        [[ -f "$f" ]] || continue
        n=$((n+1))
        models=$(jq -r 'select(.type=="assistant") | .message.model // empty' "$f" 2>/dev/null \
                 | sort | uniq -c | sort -rn | awk '{printf "%s x%s ", $2, $1}')
        printf '  %-28s %s\n' "$(basename "$f" .jsonl)" "${models:-(no assistant turns)}"
        if [[ -n "$parent" ]]; then [[ "$models" == *"$parent"* ]] && cloned=$((cloned+1))
        else [[ "$models" == *"-$PARENT_MODEL-"* ]] && cloned=$((cloned+1)); fi
      done
      (( n == 0 )) && errors+=("$SUB_DIR has no agent-*.jsonl files")
      (( cloned > 0 )) && errors+=("$cloned subagent(s) ran on the session model; see SKILL.md, 'If a child still runs on Fable'")
    else
      # Older layout: sidechain turns inline in the session file.
      main=$(ls -t "$PROJECT_DIR"/*.jsonl 2>/dev/null | head -1 || true)
      if [[ -n "$main" ]] && grep -q '"isSidechain":true' "$main"; then
        echo "session:   $(basename "$main" .jsonl) (inline sidechain turns)"
        models=$(grep '"isSidechain":true' "$main" | jq -r 'select(.type=="assistant") | .message.model // empty' | sort | uniq -c | sort -rn)
        echo "$models" | sed 's/^/  /'
        echo "$models" | grep -q -- "-$PARENT_MODEL-" && errors+=("a subagent ran on the session model family ($PARENT_MODEL)")
      else
        errors+=("no subagent transcripts under $PROJECT_DIR; spawn one $FIRST_WORKER task in a NEW session, then re-run")
      fi
    fi
  fi
fi

verdict
