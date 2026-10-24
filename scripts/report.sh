#!/usr/bin/env bash
# The test report of a module (stage 6): one HTML file from the approved test cycle, and the Go / No-go decision.
# Usage: bash scripts/report.sh <MODULE>                                          builds reports/<MODULE>-report.html (starts the stage)
#        bash scripts/report.sh decide <MODULE> Go|No-go --reason "..." --by <you>  the release decision (a person; Go is refused with an open Blocker)
#        bash scripts/report.sh check <MODULE> [--for-approval]
. "$(dirname "$0")/_py.sh"
case "${1:-}" in decide|check) C="$1"; shift; $PY "$(dirname "$0")/lib/report.py" "$C" "$@";; ""|-*) sed -n 3,5p "$0"; exit 2;; *) $PY "$(dirname "$0")/lib/report.py" build "$@";; esac
