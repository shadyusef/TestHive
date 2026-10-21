#!/usr/bin/env bash
# Starts one TestHive agent from the terminal, interactive or one-shot.
# Usage: bash scripts/th.sh <agent> ["task"]
#   With a task: runs that agent once (headless) and exits.  Without: opens an interactive session with it.
# Agents: lead manual mobile api web data triage review (or a full agent name)
# Headless runs cannot answer permission prompts, so they use --permission-mode acceptEdits (file edits allowed;
# commands still limited to .claude/settings.json). Override with TH_PERMISSION_MODE; add CLI flags with TH_CLAUDE_ARGS.
set -e
case "${1:?agent: lead|manual|mobile|api|web|data|triage|review}" in
  lead) A=testhive-lead;; manual) A=manual-tester;; mobile) A=mobile-automation-engineer;;
  api) A=api-backend-test-engineer;; web) A=web-automation-engineer;; data) A=test-data-env-manager;;
  triage) A=defect-triage;; review) A=qa-reviewer;; *) A="$1";;
esac
[ -f ".claude/agents/$A.md" ] || { echo "Unknown agent: $A" >&2; exit 1; }
shift
if [ -n "$1" ]; then claude --agent "$A" --permission-mode "${TH_PERMISSION_MODE:-acceptEdits}" $TH_CLAUDE_ARGS -p "$*"; else claude --agent "$A" $TH_CLAUDE_ARGS; fi
