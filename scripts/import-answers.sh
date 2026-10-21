#!/usr/bin/env bash
# Reads the answers from the Excel analysis workbook back into analysis/gaps.csv.
# Usage: bash scripts/import-answers.sh <MODULE> [workbook.xlsx]   default: analysis/<MODULE>-analysis.xlsx
# Updates Answer, Answered By and Status; rows with an empty ID become new questions. If any row is invalid,
# nothing is changed and every problem is listed.
. "$(dirname "$0")/_py.sh"
$PY "$(dirname "$0")/lib/analysis.py" import "$@"
