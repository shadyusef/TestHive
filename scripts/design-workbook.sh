#!/usr/bin/env bash
# Creates the Excel test design workbook for a human review: cases, coverage, assumptions, requests.
# Usage: bash scripts/design-workbook.sh <MODULE> [out.xlsx]   default: test-cases/<MODULE>-design.xlsx
. "$(dirname "$0")/_py.sh"
$PY "$(dirname "$0")/lib/design.py" workbook "$@"
