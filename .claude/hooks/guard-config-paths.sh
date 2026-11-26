#!/bin/bash
# Asks the owner before a shell command that names a protected path and looks like a write.
# Protected: CLAUDE.md, .claude/, .github/, .git/hooks/
INPUT=$(cat)
CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty')
PROTECTED='(\.claude\b|CLAUDE\.md|\.github\b|\.git/hooks)'
WRITES='(>[[:space:]]*[^&[:space:]]|\btee\b|\bsed[[:space:]]+-i|\bmv\b|\bcp\b|\brm\b|\bchmod\b|\bln\b|\btouch\b|\binstall\b|\bdd\b|\bpython3?\b|\bnode\b|\bperl\b|\bruby\b|\bgit[[:space:]]+(checkout|restore|apply|am|mv|rm)\b)'
if printf '%s' "$CMD" | grep -qE "$PROTECTED" && printf '%s' "$CMD" | grep -qE "$WRITES"; then
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"This shell command looks like it writes to CLAUDE.md, .claude/, .github/ or git hooks. Approve only if you expected it."}}'
fi
exit 0
