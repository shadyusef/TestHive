#!/usr/bin/env bash
# Runs a module's Playwright tests and stores the run with screenshots, videos and traces.
# Usage: bash scripts/run-web.sh <module> [--tag smoke|sanity|regression|e2e] [--ids TC-X-001,TC-X-002]   (reads .env and .env.<TEST_ENV>; needs: setup --install --web)
#   --ids     only these cases (retest.sh uses it)
#   --target  a target from targets.json: a local browser (edge, chrome) or a BrowserStack browser (bs-win11-chrome, ...);
#             BrowserStack needs BROWSERSTACK_USERNAME and BROWSERSTACK_ACCESS_KEY in .env
# Runs web/tests/<module>/, writes reports/web-<module>.xml, then stores the run in runs/ with
# Playwright's screenshots, videos and traces as evidence. NO_COLLECT=1 skips storing.
. "$(dirname "$0")/_env.sh"
MOD="${1:?module}"; shift; TAG="${TH_TAG:-}"; IDS=""; TARGET=""
while [ $# -gt 0 ]; do
  case "$1" in --tag) TAG="${2:?tag}"; shift 2;; --ids) IDS="${2:?case IDs}"; shift 2;; --target) TARGET="${2:?target}"; shift 2;; *) echo "Unknown option: $1" >&2; exit 2;; esac
done
case "$IDS" in *[!A-Z0-9,-]*) echo "--ids: case IDs separated by commas" >&2; exit 2;; esac
if [ -n "$TARGET" ]; then . "$(dirname "$0")/_py.sh"; T=$($PY "$(dirname "$0")/lib/targets.py" shell "$TARGET" web) || exit 2; eval "$T"; fi
[ "$TH_TARGET_WHERE" != browserstack ] || [ -n "$BROWSERSTACK_USERNAME" -a -n "$BROWSERSTACK_ACCESS_KEY" ] || { echo "Add BROWSERSTACK_USERNAME and BROWSERSTACK_ACCESS_KEY to .env (you, in the file)."; exit 2; }
[ "$TH_TARGET_WHERE" = browserstack ] && export BROWSERSTACK_USERNAME BROWSERSTACK_ACCESS_KEY  # read by playwright.config.ts for the BrowserStack address
mkdir -p reports; rm -f reports/web-"$MOD".xml
G=(); [ -n "$TAG" ] && G=(--grep "@$TAG\b"); [ -n "$IDS" ] && G=(--grep "\[(${IDS//,/|})\]")
(cd web && MODULE="$MOD" npx playwright test "tests/$MOD" "${G[@]}"); RC=$?
EV=(); [ -d web/test-results ] && EV=(--evidence web/test-results)
[ -n "$NO_COLLECT" ] || [ ! -f reports/web-"$MOD".xml ] || bash "$(dirname "$0")/collect-run.sh" web "$MOD" --env "${TEST_ENV:-}" ${TH_TARGET:+--target "$TH_TARGET"} "${EV[@]}"
if [ "$TH_TARGET_WHERE" = browserstack ] && [ -n "$BROWSERSTACK_ACCESS_KEY" ]; then  # in case a report or a test printed the keys
  K="$BROWSERSTACK_ACCESS_KEY" $PY -c "import os,glob; k=os.environ['K']
for p in glob.glob('reports/web-*.xml') + glob.glob('runs/R-*/junit.xml') + glob.glob('runs/R-*/evidence/**/*.txt', recursive=True) + glob.glob('runs/R-*/evidence/**/*.md', recursive=True):
    t=open(p,encoding='utf-8',errors='replace').read()
    if k in t: open(p,'w',encoding='utf-8').write(t.replace(k,'***'))"
fi
exit $RC
