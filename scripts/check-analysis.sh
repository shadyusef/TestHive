#!/usr/bin/env bash
# Validates the requirement and gap registers (IDs, required fields, allowed values, links between them).
# Usage: bash scripts/check-analysis.sh [MODULE] [--for-approval]
#   --for-approval  also requires every High gap Closed, no answered-but-unreviewed gap, no unconfirmed Observed requirement.
# Reads analysis/requirements.csv and analysis/gaps.csv (formats: docs/FORMATS.md). Exit 1 if anything is wrong.
. "$(dirname "$0")/_py.sh"
$PY "$(dirname "$0")/lib/analysis.py" check "$@"
