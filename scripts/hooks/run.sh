#!/usr/bin/env bash
# Runs a Claude Code hook (scripts/hooks/<name>.py) with a Python that really works; the hook's JSON input passes through.
# Usage (in .claude/settings.json): bash "$CLAUDE_PROJECT_DIR/scripts/hooks/run.sh" check_edit|guard_records
. "$(dirname "$0")/../_py.sh"
exec $PY "$(dirname "$0")/$1.py"
