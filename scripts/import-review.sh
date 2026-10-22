#!/usr/bin/env bash
# Reads the human's review from the Excel design workbook back into test-cases/TestCases.csv and requests.csv.
# Usage: bash scripts/import-review.sh <MODULE> [workbook.xlsx]   default: test-cases/<MODULE>-design.xlsx
# Imports Review decisions (Accepted, Change, Remove) and comments, direct edits (marked Updated), new case rows
# (Origin Human) and new requests. If any row is invalid, nothing is changed and every problem is listed.
. "$(dirname "$0")/_py.sh"
$PY "$(dirname "$0")/lib/design.py" import "$@"
