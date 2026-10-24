#!/usr/bin/env bash
# Runs a module's Playwright tests and stores the run with screenshots, videos and traces.
# Usage: bash scripts/run-web.sh <module> [--tag smoke|sanity|regression|e2e] [--ids TC-X-001,TC-X-002]   (reads .env and .env.<TEST_ENV>; needs: setup --install --web)
#   --ids  only these cases (retest.sh uses it)
# Runs web/tests/<module>/, writes reports/web-<module>.xml, then stores the run in runs/ with
# Playwright's screenshots, videos and traces as evidence. NO_COLLECT=1 skips storing.
. "$(dirname "$0")/_env.sh"
MOD="${1:?module}"; shift; TAG="${TH_TAG:-}"; IDS=""
while [ $# -gt 0 ]; do
  case "$1" in --tag) TAG="${2:?tag}"; shift 2;; --ids) IDS="${2:?case IDs}"; shift 2;; *) echo "Unknown option: $1" >&2; exit 2;; esac
done
case "$IDS" in *[!A-Z0-9,-]*) echo "--ids: case IDs separated by commas" >&2; exit 2;; esac
mkdir -p reports; rm -f reports/web-"$MOD".xml
G=(); [ -n "$TAG" ] && G=(--grep "@$TAG\b"); [ -n "$IDS" ] && G=(--grep "\[(${IDS//,/|})\]")
(cd web && MODULE="$MOD" npx playwright test "tests/$MOD" "${G[@]}"); RC=$?
EV=(); [ -d web/test-results ] && EV=(--evidence web/test-results)
[ -n "$NO_COLLECT" ] || [ ! -f reports/web-"$MOD".xml ] || bash "$(dirname "$0")/collect-run.sh" web "$MOD" --env "${TEST_ENV:-}" "${EV[@]}"
exit $RC
