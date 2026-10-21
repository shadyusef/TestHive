#!/usr/bin/env bash
# Runs a module's Playwright tests and stores the run with screenshots, videos and traces.
# Usage: bash scripts/run-web.sh <module>   (reads .env; needs: bash scripts/setup.sh --install --web)
# Runs web/tests/<module>/, writes reports/web-<module>.xml, then stores the run in runs/ with
# Playwright's screenshots, videos and traces as evidence. NO_COLLECT=1 skips storing.
[ -f .env ] && { set -a; eval "$(tr -d '\r' < .env)"; set +a; }
MOD="${1:?module}"
mkdir -p reports; rm -f reports/web-"$MOD".xml
(cd web && MODULE="$MOD" npx playwright test "tests/$MOD"); RC=$?
EV=(); [ -d web/test-results ] && EV=(--evidence web/test-results)
[ -n "$NO_COLLECT" ] || [ ! -f reports/web-"$MOD".xml ] || bash "$(dirname "$0")/collect-run.sh" web "$MOD" --env "${TEST_ENV:-}" "${EV[@]}"
exit $RC
