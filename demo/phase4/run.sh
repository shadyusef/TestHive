#!/usr/bin/env bash
# Phase 4 demo: automation for the fictional Nakhla Rewards SIGNUP module, from the tools approved in phase 3.
# Usage: bash demo/phase4/run.sh [--check]          Windows PowerShell: .\hive demo/phase4/run.sh [--check]
#   default  prints each step: the test project is set up, the engineers' smoke tests (recorded) run against a small local
#            stand-in of the app (demo/phase4/app/app.py), are proven stable, the contract tests are built from the spec and run
#            (known bugs listed; a second app started with app.py --break-contract, environment .env.broken, shows a wrong type
#            caught), and the gate says what is still missing
#   --check  the same, then drives Studio's Run buttons through its API; exits 1 when a step is wrong (selftest, CI)
# Needs the web tools (setup --install --web) and Newman. Works in a temporary copy; your project is not touched.
set -e
SRC="$(cd "$(dirname "$0")/../.." && pwd)"
. "$SRC/demo/_lib.sh"
demo_copy --exclude=./analysis --exclude=./test-cases --exclude=./tools --exclude=./automation --exclude=./reviews --exclude=./runs --exclude=./reports \
  --exclude=./workflow/state.json --exclude=./workflow/APPROVALS.md --exclude=./.testhive-ready --exclude=./web/tests --exclude=./web/pages --exclude=./web/fixtures --exclude=./dist --exclude=./build
drop_files PROJECT_BRIEF.md CONTEXT.md
. scripts/_py.sh
FAIL=0
step() { printf '\n=== %s\n' "$1"; }
show() { printf '$ %s\n' "$*"; "$@" 2>&1 | tee "$W/last.out" || true; }
expect() { grep -q -- "$1" "$W/last.out" && echo "  ok: $2" || { echo "  WRONG: $2 (expected: $1)"; FAIL=1; }; }
[ -d web/node_modules/@playwright/test ] || { echo "The web tools are not installed: run setup --install --web first."; exit 1; }
command -v newman >/dev/null || { echo "Newman is not installed: run setup --install."; exit 1; }

step "1. Where phase 3 ended: SIGNUP tools approved (Web UI: Playwright, API: Postman + Newman); the app runs on this PC"
. "$SRC/demo/phase4/_setup.sh"
$PY demo/phase4/app/app.py 0 --resend-cooldown 0 > "$W/app.log" 2>&1 &
for i in $(seq 1 50); do grep -q "^APP " "$W/app.log" 2>/dev/null && break; sleep 0.2; done
APP=$(sed -n 's/^APP //p' "$W/app.log"); [ -n "$APP" ] || { cat "$W/app.log"; echo "the demo app did not start"; exit 1; }
printf 'BASE_URL=%s\nAPI_BASE_URL=%s\nTEST_ENV=demo\n' "$APP" "$APP" > .env   # the demo copy's own .env (yours is never copied)
echo "Nakhla Rewards (demo stand-in) at $APP"
show bash scripts/stage.sh status SIGNUP
expect "tools       approved" "the tools are approved"

step "2. Set up the test project: one placeholder test per approved case to automate (no AI)"
show bash scripts/scaffold.sh SIGNUP
expect "56 placeholder tests" "56 web placeholders"
expect "33 placeholder tests" "33 API placeholders (requests in the collection)"
expect "contract tests, 3 endpoints" "3 contract tests built from the API spec"
echo "--- one placeholder: the case's steps are in it, with its @tags"
sed -n 3,10p web/tests/SIGNUP/TC-SIGNUP-001_*.spec.ts
show bash scripts/check-automation.sh SIGNUP
expect "stub 89" "nothing is automated yet"

step "3. The engineers write the smoke tests (recorded; page objects, unique data per test) and run them by tag"
$PY demo/phase4/recorded/apply.py web . | sed 's/^/  wrote /'
$PY demo/phase4/recorded/apply.py api . | sed 's/^/  wrote /'
show bash scripts/run-web.sh SIGNUP --tag smoke
expect "7 passed" "the 7 web smoke tests pass against the app"
show bash scripts/run-api.sh SIGNUP --tag smoke
expect "assertions │ *7 │ *0 " "the 4 API smoke tests pass (7 checks)"

step "4. Proven stable: 3 runs in a row"
TH_TAG=smoke NO_COLLECT=1 show bash scripts/stable.sh web SIGNUP
expect "STABLE (3/3 runs): TC-SIGNUP-001" "web smoke tests are stable"
TH_TAG=smoke NO_COLLECT=1 show bash scripts/stable.sh api SIGNUP
expect "TC-SIGNUP-098" "API smoke tests are stable"

step "5. Contract tests: every endpoint must answer as the API spec says (built by scaffold from the spec; no AI, no test data)"
show bash scripts/contract.sh SIGNUP
expect "up to date, 3 endpoints" "the contract tests match the spec"
show bash scripts/run-api.sh SIGNUP --contract
expect "status 404 is not in the spec" "the app answers 404 for an unknown signupId, which the spec does not list"
echo "--- the tester reports both as bugs and lists them, so the gate knows they are expected to fail"
printf 'POST /v1/otp/verify BUG-SIGNUP-201  # 404 for an unknown signupId is not in the spec\nPOST /v1/otp/resend BUG-SIGNUP-202  # same\n' > api/collections/SIGNUP.contract-bugs.txt
cat api/collections/SIGNUP.contract-bugs.txt
echo "--- a changed API (signupId comes back as a number) against a second environment, .env.broken"
$PY demo/phase4/app/app.py 0 --break-contract > "$W/app2.log" 2>&1 &
for i in $(seq 1 50); do grep -q "^APP " "$W/app2.log" 2>/dev/null && break; sleep 0.2; done
printf 'API_BASE_URL=%s\n' "$(sed -n 's/^APP //p' "$W/app2.log")" > .env.broken
TEST_ENV=broken NO_COLLECT=1 show bash scripts/run-api.sh SIGNUP --contract
expect "signupId" "the contract test catches the wrong type of signupId"

step "6. The gate: the automation is approved only when every case has a written, stable test"
show bash scripts/check-automation.sh SIGNUP --for-approval
expect "stable 11, stub 78" "11 stable, 78 still placeholders"
expect "expected to fail on BUG-SIGNUP-201" "the known contract bugs are warnings, not blockers"
show bash scripts/stage.sh submit SIGNUP automation
expect "BLOCKED" "it cannot be submitted yet"
mkdir -p "$SRC/demo/phase4/output"; ls runs/ > /dev/null 2>&1 && cp runs/index.csv "$SRC/demo/phase4/output/" 2>/dev/null || true
cp "$W/last.out" "$SRC/demo/phase4/output/check-automation.txt"

if [ "$1" = "--check" ]; then
  step "7. The same through Studio's Run buttons (recorded engineers)"
  export TH_CLAUDE_FAKE="$SRC/demo/phase2d/fake-claude.py" TH_FAKE_DELAY=0.05
  bash scripts/studio.sh --no-browser --port 0 > "$W/studio.log" 2>&1 &
  for i in $(seq 1 150); do grep -q "^STUDIO " "$W/studio.log" 2>/dev/null && break; sleep 0.2; done
  URL=$(sed -n 's/^STUDIO //p' "$W/studio.log"); [ -n "$URL" ] || { cat "$W/studio.log"; echo "Studio did not start"; exit 1; }
  $PY "$SRC/demo/phase4/walkthrough.py" "$URL" || FAIL=1
  [ "$FAIL" = 0 ] && echo "PHASE 4 CHECK PASS" || { echo "PHASE 4 CHECK FAIL"; exit 1; }
fi
printf '\nDemo finished. demo/phase4/output/ has the gate report. The temporary folder is removed now (TH_KEEP_DEMO=1 keeps it).\n'
