#!/usr/bin/env bash
# Checks a module's test cases against its approved analysis baseline: fields, links, coverage, negatives, boundaries.
# Usage: bash scripts/check-design.sh <MODULE> [--set-priority] [--for-approval]
#   --set-priority  fills empty Priority cells with the risk rule (impact of the requirement x Risk of the case)
#   --for-approval  also requires no orphan case, no case marked Needs update, no unhandled Change/Remove, no open request
# Reads test-cases/TestCases.csv, test-cases/requests.csv and analysis/baseline/<MODULE>/v<latest>/. Exit 1 if anything is wrong.
. "$(dirname "$0")/_py.sh"
$PY "$(dirname "$0")/lib/design.py" check "$@"
