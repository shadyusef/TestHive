#!/usr/bin/env bash
# Usage: bash scripts/run-mobile.sh <module> [device-id]   (reads .env)
set -e
[ -f .env ] && set -a && . ./.env && set +a
MOD="${1:?module}"; DEV="${2:-}"
mkdir -p reports
maestro ${DEV:+--device $DEV} test -e APP_ID="$APP_ID" --format junit --output reports/mobile-"$MOD".xml mobile/flows/"$MOD"
