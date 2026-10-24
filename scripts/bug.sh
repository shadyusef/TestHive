#!/usr/bin/env bash
# The bug register (reports/bugs.csv): report a bug, change its status, list a module's bugs.
# Usage: bash scripts/bug.sh add <MODULE> --title "..." --severity Blocker|Major|Minor --cases TC-X-001[,...] [--steps --expected --actual "..."]
#                            [--evidence R-<run>/evidence/<file>] [--target <name>] --by <name>     (a person's report also links it in the cycle)
#        bash scripts/bug.sh status <MODULE> BUG-<MODULE>-<NNN> Open|Fixed|Verified|"Won't fix" --by <you> [--note "build 1.4.2"]   (Fixed: retest)
#        bash scripts/bug.sh list <MODULE>
. "$(dirname "$0")/_py.sh"
C="${1:-}"; shift || true
case "$C" in add|status|list) $PY "$(dirname "$0")/lib/report.py" "bug-$C" "$@";; *) sed -n 3,6p "$0"; exit 2;; esac
