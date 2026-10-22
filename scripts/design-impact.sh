#!/usr/bin/env bash
# Lists the test cases affected when requirements change between two approved analysis baselines.
# Usage: bash scripts/design-impact.sh <MODULE> [--from vN] [--to vN] [--apply]
#   default --from: the analysis version of the latest design baseline; default --to: the latest analysis baseline
#   --apply  sets the affected cases to Status "Needs update" (the design cannot be approved until they are fixed)
. "$(dirname "$0")/_py.sh"
$PY "$(dirname "$0")/lib/design.py" impact "$@"
