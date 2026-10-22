#!/usr/bin/env bash
# Creates the project files (brief, CONTEXT, board, case sheet, registers, .env) from templates; keeps the ones that exist.
# Usage: bash scripts/init-project.sh "<PROJECT_NAME>"
. "$(dirname "$0")/_py.sh"
exec $PY "$(dirname "$0")/lib/intake.py" init "${1:?Usage: init-project.sh \"<PROJECT_NAME>\"}"
