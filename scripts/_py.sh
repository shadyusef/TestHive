#!/usr/bin/env bash
# Sourced by the other scripts: sets PY to a Python 3 that really runs.
# (On Windows `python3` is often a Microsoft Store stub that exists but does nothing.)
PY=""
for c in python3 python "py -3"; do
  if $c -c "import sys; sys.exit(sys.version_info[0] != 3)" >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "Python 3 not found. Run scripts/setup.sh --check (Windows: scripts/setup.ps1 -Check)." >&2; exit 1; }
