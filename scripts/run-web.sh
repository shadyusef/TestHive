#!/usr/bin/env bash
# Runs a module's Playwright tests and stores the run with screenshots, videos and traces.
# Usage: bash scripts/run-web.sh <module> [--tag smoke|sanity|regression|e2e]   (reads .env and .env.<TEST_ENV>; needs: setup --install --web)
# Runs web/tests/<module>/, writes reports/web-<module>.xml, then stores the run in runs/ with
# Playwright's screenshots, videos and traces as evidence. NO_COLLECT=1 skips storing.
. "$(dirname "$0")/_env.sh"
MOD="${1:?module}"; TAG="${TH_TAG:-}"; [ "$2" = --tag ] && TAG="${3:?tag}"
mkdir -p reports; rm -f reports/web-"$MOD".xml
(cd web && MODULE="$MOD" npx playwright test "tests/$MOD" ${TAG:+--grep "@$TAG\b"}); RC=$?
EV=(); [ -d web/test-results ] && EV=(--evidence web/test-results)
[ -n "$NO_COLLECT" ] || [ ! -f reports/web-"$MOD".xml ] || bash "$(dirname "$0")/collect-run.sh" web "$MOD" --env "${TEST_ENV:-}" "${EV[@]}"
exit $RC
