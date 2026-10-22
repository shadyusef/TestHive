#!/usr/bin/env bash
# Opens TestHive Studio: a local web page to see the stages, answer questions, review cases and approve (no terminal needed).
# Usage: bash scripts/studio.sh [--port N] [--no-browser]        Windows PowerShell: .\hive studio
#   Runs on this PC only (127.0.0.1). Prints the address with its access token; keep the window open, Ctrl+C stops it.
#   Studio reads and writes the same files as the scripts, Excel and the agents (see README, "TestHive Studio").
cd "$(dirname "$0")/.." || exit 1
. scripts/_py.sh
[ -f workflow/state.json ] || echo "No modules yet: add the first one in Studio (New module)."
export TH_BASH="$(cygpath -w "$BASH" 2>/dev/null || echo "$BASH")"   # stage decisions run scripts/stage.sh with this bash
exec $PY scripts/lib/studio.py "$@"
