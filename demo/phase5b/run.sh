#!/usr/bin/env bash
# Phase 5b demo: run targets. The same web smoke tests run on a local browser and on a BrowserStack browser, and Maestro flows run
# on a BrowserStack device. Here BrowserStack is played by local stand-ins: Playwright's own browser server, and a small fake of the
# App Automate API (demo/phase5b/fake_browserstack.py); the real service is never called, and the keys are made up.
# Usage: bash demo/phase5b/run.sh [--check]          Windows PowerShell: .\hive demo/phase5b/run.sh [--check]
#   --check  the same, then checks Studio's Run picker data and refusals through its API; exits 1 when a step is wrong (selftest, CI)
# Needs the web tools (setup --install --web). Works in a temporary copy; your project is not touched.
set -e
SRC="$(cd "$(dirname "$0")/../.." && pwd)"
. "$SRC/demo/_lib.sh"
demo_copy --exclude=./analysis --exclude=./test-cases --exclude=./tools --exclude=./automation --exclude=./execution --exclude=./reviews --exclude=./runs --exclude=./reports \
  --exclude=./workflow/state.json --exclude=./workflow/APPROVALS.md --exclude=./.testhive-ready --exclude=./web/tests --exclude=./web/pages --exclude=./web/fixtures --exclude=./dist --exclude=./build
drop_files PROJECT_BRIEF.md CONTEXT.md
. scripts/_py.sh
FAIL=0
step() { printf '\n=== %s\n' "$1"; }
show() { printf '$ %s\n' "$*"; "$@" 2>&1 | tee "$W/last.out" || true; }
expect() { grep -q -- "$1" "$W/last.out" && echo "  ok: $2" || { echo "  WRONG: $2 (expected: $1)"; FAIL=1; }; }
lastrun() { for r in $(ls runs | grep '^R-' | sort); do grep -q "\"kind\": \"$1\"" runs/$r/meta.json && L=$r; done; echo "$L"; }
[ -d web/node_modules/@playwright/test ] || { echo "The web tools are not installed: run setup --install --web first."; exit 1; }
KEY="demo-key-not-real-7f3a"   # made up: the fake BrowserStack accepts it, and the demo checks it is written nowhere

step "1. The project: SIGNUP's web smoke tests (recorded), the app on this PC, and made-up BrowserStack keys in .env"
export ONLY_AUTOMATE="TC-SIGNUP-001,TC-SIGNUP-022,TC-SIGNUP-034,TC-SIGNUP-037,TC-SIGNUP-048,TC-SIGNUP-049,TC-SIGNUP-051,TC-SIGNUP-072,TC-SIGNUP-087,TC-SIGNUP-089,TC-SIGNUP-098"  # the API cases too: the API tool is chosen in the setup
. "$SRC/demo/phase4/_setup.sh"
{ bash scripts/scaffold.sh SIGNUP && $PY demo/phase4/recorded/apply.py web .; } > "$W/setup.log" 2>&1 || { tail -5 "$W/setup.log"; exit 1; }
$PY demo/phase4/app/app.py 0 --resend-cooldown 0 > "$W/app.log" 2>&1 &
for i in $(seq 1 50); do grep -q "^APP " "$W/app.log" 2>/dev/null && break; sleep 0.2; done
APP=$(sed -n 's/^APP //p' "$W/app.log")
printf 'BASE_URL=%s\nAPI_BASE_URL=%s\nAPP_ID=com.nakhla.rewards\nAPP_FILE=demo-app.apk\nBROWSERSTACK_USERNAME=demo-user\nBROWSERSTACK_ACCESS_KEY=%s\n' "$APP" "$APP" "$KEY" > .env
printf 'not a real app: the fake BrowserStack only stores it\n' > demo-app.apk
show bash scripts/targets.sh
expect "bs-win11-chrome    web     browserstack" "the targets are listed"
expect "BrowserStack keys in .env: set" "the keys are set (only that: never their values)"

step "2. A local browser: the smoke tests on Microsoft Edge"
show bash scripts/run-web.sh SIGNUP --tag smoke --target edge
expect "7 passed" "7 passed on Edge"
grep -h '"target"' runs/$(lastrun web)/meta.json | tee "$W/last.out"; expect '"target": "edge"' "the run records its target"

step "3. A BrowserStack browser (Playwright's browser server stands in for BrowserStack)"
PORT=$($PY -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1])")
(cd web && exec npx playwright run-server --host 127.0.0.1 --port "$PORT" > "$W/pwserver.log" 2>&1) &
for i in $(seq 1 100); do grep -q "Listening" "$W/pwserver.log" 2>/dev/null && break; sleep 0.2; done
TH_BS_WS="ws://127.0.0.1:$PORT/" show bash scripts/run-web.sh SIGNUP --tag smoke --target bs-win11-chrome
expect "7 passed" "the same 7 tests pass on the remote browser"
grep -h '"target"' runs/$(lastrun web)/meta.json | tee "$W/last.out"; expect '"target": "bs-win11-chrome"' "the run records the BrowserStack target"
CLOSED=$($PY -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1])")
TH_BS_WS="ws://127.0.0.1:$CLOSED/" NO_COLLECT=1 show bash scripts/run-web.sh SIGNUP --tag 'smoke' --ids TC-SIGNUP-001 --target bs-win11-chrome
expect "1 failed" "with no remote browser listening the test cannot run: the tests really went to the remote browser"
TH_BS_WS="ws://evil.example:443/" show bash scripts/run-web.sh SIGNUP --tag smoke --target bs-win11-chrome
expect "may only point to a local stand-in" "the keys never go to another address"

step "4. A BrowserStack device: the Maestro flows are uploaded, run on a Pixel 7 and read back as a run"
mkdir -p mobile/flows/SIGNUP
printf 'appId: ${APP_ID}\nname: "[TC-SIGNUP-005] Sign-up form opens @smoke"\ntags:\n  - smoke\n---\n- launchApp\n- assertVisible: "Create your account"\n' > mobile/flows/SIGNUP/TC-SIGNUP-005_sign-up-form-opens.yaml
printf '# demo: fails at BrowserStack\nappId: ${APP_ID}\nname: "[TC-SIGNUP-006] Terms link opens @smoke"\ntags:\n  - smoke\n---\n- launchApp\n- tapOn: "Terms"\n' > mobile/flows/SIGNUP/TC-SIGNUP-006_terms-link-opens.yaml
$PY "$SRC/demo/phase5b/fake_browserstack.py" demo-user "$KEY" > "$W/fakebs.log" 2>&1 &
for i in $(seq 1 50); do grep -q "^FAKEBS " "$W/fakebs.log" 2>/dev/null && break; sleep 0.2; done
export TH_BS_API=$(sed -n 's/^FAKEBS //p' "$W/fakebs.log") TH_BS_POLL_SECONDS=0.2
show bash scripts/run-mobile.sh SIGNUP --target bs-pixel7
expect "2 test cases, 1 not passed" "2 flows ran on the device; the planted failure is reported"
expect "RUN R-" "the results are stored as a run"
R=$(lastrun mobile); grep -h -e '"target"' -e '"platform"' runs/$R/meta.json | tee "$W/last.out"
expect '"target": "bs-pixel7"' "the run records the device target"
cat runs/$R/evidence/*TC-SIGNUP-006*.txt | tee "$W/last.out"; expect "video: https://" "the failed flow keeps its BrowserStack video link"
printf 'BROWSERSTACK_ACCESS_KEY=wrong-key\n' > .env.wrongkey
TEST_ENV=wrongkey show bash scripts/run-mobile.sh SIGNUP --target bs-pixel7
expect "BrowserStack answered 401" "a wrong key is refused, and the key is not printed"
echo "--- the access key is written nowhere: runs, reports, the demo's output"
if grep -rl -- "$KEY" runs reports "$W"/last.out 2>/dev/null; then echo "  WRONG: the access key was written"; FAIL=1; else echo "  ok: the access key is in none of them"; fi

if [ "$1" = "--check" ]; then
  step "5. Studio: the Run picker's targets and its refusals"
  export TH_CLAUDE_FAKE="$SRC/demo/phase2d/fake-claude.py"  # the recorded agents: Run works on a PC without Claude Code (CI) instead of review mode
  bash scripts/studio.sh --no-browser --port 0 > "$W/studio.log" 2>&1 &
  for i in $(seq 1 150); do grep -q "^STUDIO " "$W/studio.log" 2>/dev/null && break; sleep 0.2; done
  URL=$(sed -n 's/^STUDIO //p' "$W/studio.log"); [ -n "$URL" ] || { cat "$W/studio.log"; echo "Studio did not start"; exit 1; }
  $PY "$SRC/demo/phase5b/walkthrough.py" "$URL" "$KEY" || FAIL=1
  [ "$FAIL" = 0 ] && echo "PHASE 5B CHECK PASS" || { echo "PHASE 5B CHECK FAIL"; exit 1; }
fi
[ "$FAIL" = 0 ] || echo "SOME STEPS WERE WRONG (see WRONG above)"
printf '\nDemo finished. The temporary folder is removed now (TH_KEEP_DEMO=1 keeps it).\n'
