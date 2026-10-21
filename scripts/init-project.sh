#!/usr/bin/env bash
# Creates the project files (brief, CONTEXT, board, case sheet, registers, .env) from templates.
# Usage: bash scripts/init-project.sh "<PROJECT_NAME>"
set -e
NAME="${1:?Usage: init-project.sh \"<PROJECT_NAME>\"}"
SAFE=$(printf '%s' "$NAME" | sed 's/[\/&|]/\\&/g')
mkdir -p workflow/intake test-cases reports reviews mobile/data requirements/sources analysis runs
[ -f PROJECT_BRIEF.md ] || sed "s|<PROJECT_NAME>|$SAFE|" templates/PROJECT_BRIEF.md > PROJECT_BRIEF.md
[ -f workflow/BOARD.md ] || cp templates/BOARD.md workflow/BOARD.md
[ -f test-cases/TestCases.csv ] || cp templates/TestCases.csv test-cases/TestCases.csv
[ -f .env ] || cp templates/env.example .env
[ -f CONTEXT.md ] || cp templates/CONTEXT.md CONTEXT.md
[ -f analysis/requirements.csv ] || head -1 templates/requirements.csv > analysis/requirements.csv
[ -f analysis/gaps.csv ] || head -1 templates/gaps.csv > analysis/gaps.csv
H="${TH_CMD:-bash scripts/hive.sh}"
echo "Project '$NAME' initialised. Next: fill in CONTEXT.md and .env, then run: $H setup --check   and   $H check-devices"
