#!/usr/bin/env bash
# Builds the Excel analysis workbook for a module (Cover, Gaps to answer, Requirements, Sources).
# Usage: bash scripts/analysis-workbook.sh <MODULE> [out.xlsx]     default: analysis/<MODULE>-analysis.xlsx
# The human fills the yellow columns of the Gaps sheet (Answer, Answered By, Status) and may add new questions,
# then runs scripts/import-answers.sh. Arabic text is right-aligned.
. "$(dirname "$0")/_py.sh"
$PY "$(dirname "$0")/lib/analysis.py" workbook "$@"
