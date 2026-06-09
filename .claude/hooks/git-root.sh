#!/usr/bin/env bash
# git-root.sh — PreToolUse hook for Bash(git *) (wired in .claude/settings.json).
#
# Reports the git repo root the command will actually act on, not just the
# session cwd: best-effort parse of `git -C <dir>` or a leading `cd <dir>`
# from the command itself, falling back to the session cwd. When target and
# session roots differ, both are reported — the boundary signal for paired
# checkouts in multi-repo sessions. Advisory only; never blocks (exit 0).

set -u

input="$(cat)"
cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null || true)"
# Parse only the command's first line: later lines are heredoc/quoted content
# (commit messages, PR bodies) where "git -C <dir>" may appear as prose.
cmd="$(printf '%s\n' "$cmd" | head -n1)"

pick() { printf '%s\n' "$cmd" | sed -nE "$1" | head -n1; }

# `git -C <dir>` — double-quoted form, then bare token
target="$(pick 's/.*git[[:space:]]+-C[[:space:]]+"([^"]+)".*/\1/p')"
[ -n "$target" ] || target="$(pick 's/.*git[[:space:]]+-C[[:space:]]+([^[:space:];|&"'\''()]+).*/\1/p')"
# leading `cd <dir>` — double-quoted form, then bare token
[ -n "$target" ] || target="$(pick 's/^[[:space:]]*cd[[:space:]]+"([^"]+)".*/\1/p')"
[ -n "$target" ] || target="$(pick 's/^[[:space:]]*cd[[:space:]]+([^[:space:];|&"'\''()]+).*/\1/p')"

session_root="$(git rev-parse --show-toplevel 2>/dev/null || echo '(session cwd not in a git repo)')"

if [ -n "$target" ]; then
  target_root="$(git -C "$target" rev-parse --show-toplevel 2>/dev/null || echo "(target '$target' is not a git repo)")"
else
  target_root="$session_root"
fi

if [ "$target_root" = "$session_root" ]; then
  ctx="git repo root: $target_root"
else
  ctx="git TARGET repo: $target_root — differs from session cwd repo: $session_root"
fi

jq -cn --arg ctx "$ctx" '{hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:$ctx}}'
exit 0
