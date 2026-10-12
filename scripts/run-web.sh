#!/usr/bin/env bash
# Usage: bash scripts/run-web.sh <module>   (reads .env; needs: bash scripts/setup.sh --install --web)
# Runs web/tests/<module>/ and writes reports/web-<module>.xml
set -e
[ -f .env ] && { set -a; eval "$(tr -d '\r' < .env)"; set +a; }
MOD="${1:?module}"
mkdir -p reports
cd web && MODULE="$MOD" npx playwright test "tests/$MOD"
