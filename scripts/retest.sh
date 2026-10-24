#!/usr/bin/env bash
# Retests the failures of the current test cycle: failed tests, and tests of bugs marked fixed (bug.sh status ... Fixed, or cycle.sh fixed).
# Usage: bash scripts/retest.sh web|api <MODULE> [--target <name>]   (mobile: run-mobile.sh runs the whole module)
. "$(dirname "$0")/_py.sh"
K="${1:?web|api}"; MOD="${2:?module}"
[ "$K" = web ] || [ "$K" = api ] || { echo "retest.sh: web or api (mobile flows are rerun with run-mobile.sh)"; exit 2; }
IDS=$($PY "$(dirname "$0")/lib/execute.py" retest "$K" "$MOD") || { echo "$IDS"; exit 1; }
[ -n "$IDS" ] || { echo "RETEST $MOD $K: nothing to retest"; exit 0; }
echo "RETEST $MOD $K: $IDS"
bash "$(dirname "$0")/run-$K.sh" "$MOD" --ids "$IDS" "${@:3}"
