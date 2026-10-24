#!/usr/bin/env bash
# Phase 5 demo: a test cycle of the fictional Nakhla Rewards SIGNUP module, from an approved automation (phase 4).
# Usage: bash demo/phase5/run.sh [--check]          Windows PowerShell: .\hive demo/phase5/run.sh [--check]
#   default  prints each step: build 1.0 of the stand-in app (demo/phase4/app/app.py) has a planted bug and a flaky resend; the
#            cycle runs the web, API and contract tests on the "demo" environment, the tester links the bug, quarantines the flaky
#            test and records the cases run by hand; build 1.0.1 fixes the bug, the failures are retested and the cycle is approved
#   --check  the same, then checks Studio's Execution data and refusals through its API; exits 1 when a step is wrong (selftest, CI)
# Needs the web tools (setup --install --web) and Newman. Works in a temporary copy; your project is not touched.
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
[ -d web/node_modules/@playwright/test ] || { echo "The web tools are not installed: run setup --install --web first."; exit 1; }
command -v newman >/dev/null || { echo "Newman is not installed: run setup --install."; exit 1; }
app() {  # starts a build of the stand-in app and points the demo environment (.env.demo) at it
  [ -n "$APP_PID" ] && { kill "$APP_PID" 2>/dev/null; wait "$APP_PID" 2>/dev/null || true; }
  rm -f "$W/app.log"; $PY demo/phase4/app/app.py 0 --resend-cooldown 0 "$@" > "$W/app.log" 2>&1 & APP_PID=$!
  for i in $(seq 1 50); do grep -q "^APP " "$W/app.log" 2>/dev/null && break; sleep 0.2; done
  APP=$(sed -n 's/^APP //p' "$W/app.log"); [ -n "$APP" ] || { cat "$W/app.log"; echo "the demo app did not start"; exit 1; }
  printf 'BASE_URL=%s\nAPI_BASE_URL=%s\n' "$APP" "$APP" > .env.demo   # the demo copy's own files (yours are never copied)
}
S="TC-SIGNUP"
step "1. Where phase 4 ended: the 11 recorded tests are automated, stable and approved; the other cases are run by hand"
export ONLY_AUTOMATE="$S-001,$S-022,$S-034,$S-037,$S-048,$S-049,$S-051,$S-072,$S-087,$S-089,$S-098"
. "$SRC/demo/phase4/_setup.sh"
printf 'TEST_ENV=demo\n' > .env; app
{ bash scripts/scaffold.sh SIGNUP; $PY demo/phase4/recorded/apply.py web .; $PY demo/phase4/recorded/apply.py api .
  bash scripts/stable.sh web SIGNUP; bash scripts/stable.sh api SIGNUP; bash scripts/run-api.sh SIGNUP --contract
  printf 'POST /v1/otp/verify BUG-SIGNUP-201\nPOST /v1/otp/resend BUG-SIGNUP-202\n' > api/collections/SIGNUP.contract-bugs.txt
  bash scripts/stage.sh submit SIGNUP automation; bash scripts/stage.sh approve SIGNUP automation --by "Omar (QA manager)"; } > "$W/setup.log" 2>&1 || true
show bash scripts/stage.sh status SIGNUP
expect "automation  approved" "the automation is approved"

step "2. Build 1.0 is deployed to the demo environment (with a planted bug and a flaky resend); a test cycle starts"
app --bug otp-message --flaky-resend
show bash scripts/cycle.sh start SIGNUP "1.0 demo" --env demo --by "Sara (QA lead)"
expect "CYCLE SIGNUP C1" "cycle C1 started on the demo environment"

step "3. The cycle's automated tests run (each run is stored with its evidence)"
show bash scripts/run-web.sh SIGNUP
expect "1 failed" "one web test fails: the wrong-code message"
show bash scripts/run-api.sh SIGNUP
expect "status is 202" "the resend test fails once (503)"
show bash scripts/run-api.sh SIGNUP --contract
WEBRUN=$(ls runs | grep '^R-' | sort | sed -n '1p'); for r in $(ls runs | grep '^R-'); do grep -q '"kind": "web"' runs/$r/meta.json && WEBRUN=$r; done
echo "--- evidence of the failed web test (video, screenshot, trace) in runs/$WEBRUN/evidence/"
find runs/$WEBRUN/evidence -iname "*051*" -type d | head -1 | xargs -I{} ls {} | tee "$W/last.out"
expect "video.webm" "the failed web test kept its video"
APIRUN=$(for r in $(ls runs | grep '^R-'); do grep -q '"kind": "api"' runs/$r/meta.json && echo $r; done | tail -1)
echo "--- one API request and its response, as kept with run $APIRUN (secrets masked)"
sed -n 1,30p runs/$APIRUN/evidence/*TC-SIGNUP-072*.txt | grep -v -e "^User-Agent" -e "^Accept" -e "^Cache-Control" -e "^Postman-Token" -e "^Connection" | tee "$W/last.out"
expect '"password": "\*\*\*"' "the password in the request body is masked"

step "4. The tester triages: the web failure is a bug; the resend passes on a rerun, so it is flaky and quarantined"
show bash scripts/cycle.sh bug SIGNUP $S-051 BUG-SIGNUP-301 --by "Sara (QA lead)"
show bash scripts/run-api.sh SIGNUP
show bash scripts/cycle.sh status SIGNUP
expect "$S-098 *api *passed .*flaky" "TC-SIGNUP-098 failed, then passed: flaky"
show bash scripts/cycle.sh quarantine SIGNUP $S-098 --reason "503 on the first resend only; investigating with the backend team" --by "Sara (QA lead)"

step "5. The cases run by hand are recorded (one failed with its bug, one blocked)"
MAN=$(bash scripts/cycle.sh status SIGNUP | awk '$2 == "manual" && $3 == "not-run" {print $1}' | grep -v -e "$S-044" -e "$S-062" | paste -sd, -)
bash scripts/cycle.sh result SIGNUP "$MAN" Passed --by "Lina (tester)" | sed 's/^/  /'
show bash scripts/cycle.sh result SIGNUP $S-044 Failed --bug BUG-SIGNUP-302 --note "Arabic page still shows English labels" --by "Lina (tester)"
show bash scripts/cycle.sh result SIGNUP $S-062 Blocked --note "needs a clock that can be set forward 5 minutes in the demo environment" --by "Lina (tester)"
show bash scripts/cycle.sh check SIGNUP --for-approval
expect "EXECUTION OK" "every case has its result; failures carry a bug"

step "6. Build 1.0.1 fixes BUG-SIGNUP-301: the failures are retested, then the cycle is approved"
app
show bash scripts/cycle.sh fixed SIGNUP BUG-SIGNUP-301 --note "build 1.0.1" --by "Sara (QA lead)"
show bash scripts/cycle.sh check SIGNUP --for-approval
expect "BUG-SIGNUP-301 is fixed: retest it" "a fixed bug needs its retest"
show bash scripts/retest.sh web SIGNUP
expect "RETEST SIGNUP web: $S-051" "only the failed web test is retested"
expect "1 passed" "and it passes now"
show bash scripts/cycle.sh check SIGNUP --for-approval
expect "EXECUTION OK" "the cycle is ready"
show bash scripts/stage.sh submit SIGNUP execution
bash scripts/stage.sh approve SIGNUP execution --by "Omar (QA manager)" | tee "$W/last.out"
expect "EXECUTION BASELINE SIGNUP v1" "approval records the cycle's results in execution/baseline/"
mkdir -p "$SRC/demo/phase5/output"; bash scripts/cycle.sh status SIGNUP > "$SRC/demo/phase5/output/cycle-status.txt"

if [ "$1" = "--check" ]; then
  step "7. Studio: the Execution data and its refusals"
  bash scripts/studio.sh --no-browser --port 0 > "$W/studio.log" 2>&1 &
  for i in $(seq 1 150); do grep -q "^STUDIO " "$W/studio.log" 2>/dev/null && break; sleep 0.2; done
  URL=$(sed -n 's/^STUDIO //p' "$W/studio.log"); [ -n "$URL" ] || { cat "$W/studio.log"; echo "Studio did not start"; exit 1; }
  $PY "$SRC/demo/phase5/walkthrough.py" "$URL" "$WEBRUN" "$APIRUN" || FAIL=1
  [ "$FAIL" = 0 ] && echo "PHASE 5 CHECK PASS" || { echo "PHASE 5 CHECK FAIL"; exit 1; }
fi
[ "$FAIL" = 0 ] || echo "SOME STEPS WERE WRONG (see WRONG above)"
printf '\nDemo finished. demo/phase5/output/ has the cycle status. The temporary folder is removed now (TH_KEEP_DEMO=1 keeps it).\n'
