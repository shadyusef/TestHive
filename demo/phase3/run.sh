#!/usr/bin/env bash
# Phase 3 demo: tool advice for the fictional Nakhla Rewards SIGNUP module, from the test cases approved in phase 2.
# Usage: bash demo/phase3/run.sh [--check]          Windows PowerShell: .\hive demo/phase3/run.sh [--check]
#   default  prints each step (a few seconds, no agents: the advice is a script)
#   --check  the same, and exits 1 when a step does not behave as expected (used by the selftest)
# Works in a temporary copy; your project is not touched. Outputs to open afterwards: demo/phase3/output/
set -e
SRC="$(cd "$(dirname "$0")/../.." && pwd)"; D="$SRC/demo/phase3"; P1="$SRC/demo/phase1/recorded"; P2="$SRC/demo/phase2"
. "$SRC/demo/_lib.sh"
demo_copy --exclude=./analysis --exclude=./test-cases --exclude=./tools --exclude=./reviews --exclude=./workflow/state.json --exclude=./workflow/APPROVALS.md --exclude=./.testhive-ready
. scripts/_py.sh
FAIL=0
step() { printf '\n=== %s\n' "$1"; }
show() { printf '$ %s\n' "$*"; "$@" 2>&1 | tee "$W/last.out" || true; }
expect() { grep -q -- "$1" "$W/last.out" && echo "  ok: $2" || { echo "  WRONG: $2 (expected: $1)"; FAIL=1; }; }

step "1. Where phase 2 ended: SIGNUP test cases approved (design baseline v1)"
bash scripts/init-project.sh "Nakhla Rewards" >/dev/null; cp "$P2/CONTEXT.md" CONTEXT.md
cp "$P1"/recheck-2/requirements.csv "$P1"/recheck-2/gaps.csv analysis/
bash scripts/stage.sh init SIGNUP >/dev/null
for st in analysis design; do bash scripts/stage.sh start SIGNUP $st >/dev/null; [ $st = design ] && cp "$P2"/recorded/recheck-1/TestCases.csv "$P2"/recorded/recheck-1/requests.csv test-cases/ && cp "$P2"/recorded/recheck-1/gaps.csv analysis/
  bash scripts/stage.sh submit SIGNUP $st >/dev/null; bash scripts/stage.sh approve SIGNUP $st --by "Sara (QA lead)" >/dev/null; done
show bash scripts/stage.sh status SIGNUP
expect "design      approved" "analysis and design are approved"

step "2. The decision matrix: the functional cases to automate, grouped by test type, and the tools scored on each criterion"
show bash scripts/tool-advice.sh SIGNUP
expect "Recommended: Playwright" "Playwright is recommended for the Web UI cases"
expect "Recommended: Postman + Newman" "Postman + Newman is recommended for the API cases"
expect "non-functional cases" "accessibility, security and performance cases are counted, not advised yet"
cp "$W/last.out" "$W/matrix.txt"

step "3. The stage cannot be submitted before every test type has a tool"
bash scripts/stage.sh start SIGNUP tools >/dev/null
show bash scripts/stage.sh submit SIGNUP tools
expect "no tool chosen yet" "submitting without choices is refused"

step "4. The team writes Java: the scores change. Choosing another tool than the recommended one needs a reason"
show bash scripts/tool-advice.sh settings --skills Java
show bash scripts/tool-advice.sh choose SIGNUP API "REST Assured" --by "Sara (QA lead)"
expect "say why" "a tool other than the recommended one without a reason is refused"
show bash scripts/tool-advice.sh choose SIGNUP API "REST Assured" --by "Sara (QA lead)" --reason "The developers keep API tests in Java next to the service"
expect "SAVED" "with a reason it is saved"
show bash scripts/tool-advice.sh choose SIGNUP "Web UI" playwright --by "Sara (QA lead)"
show bash scripts/tool-advice.sh check SIGNUP --for-approval
expect "no ready-made TestHive setup" "a warning says REST Assured has no TestHive setup yet"
expect "TOOLS OK" "every test type has a valid choice"

step "5. Submit, and a named human approves: the choice is frozen as tools baseline v1"
bash scripts/stage.sh submit SIGNUP tools
show bash scripts/stage.sh approve SIGNUP tools --by "Omar (QA manager)" --comment "Java for API, Playwright for web"
expect "TOOLS BASELINE SIGNUP v1" "the choice is frozen"
show bash scripts/tool-advice.sh choose SIGNUP API "Postman + Newman" --by "Sara (QA lead)"
expect "reopen the tools stage" "an approved choice is read-only"

step "6. Later the design is reopened and approved again (design v2): the tool choice must be checked again"
bash scripts/stage.sh reopen SIGNUP design --by "Sara (QA lead)" --comment "One more review round" >/dev/null
show bash scripts/stage.sh status SIGNUP
expect "tools       in progress" "the tools stage went back to in progress"
bash scripts/stage.sh submit SIGNUP design >/dev/null; bash scripts/stage.sh approve SIGNUP design --by "Sara (QA lead)" >/dev/null
show bash scripts/tool-advice.sh check SIGNUP --for-approval
expect "test cases changed since" "the old choices point at design v1"
bash scripts/tool-advice.sh choose SIGNUP API "REST Assured" --by "Sara (QA lead)" --reason "Still Java" >/dev/null
bash scripts/tool-advice.sh choose SIGNUP "Web UI" Playwright --by "Sara (QA lead)" >/dev/null
bash scripts/stage.sh submit SIGNUP tools >/dev/null
show bash scripts/stage.sh approve SIGNUP tools --by "Omar (QA manager)"
expect "TOOLS BASELINE SIGNUP v2" "checked again and approved"

mkdir -p "$D/output"; cp tools/choices.csv "$W/matrix.txt" "$D/output/"
printf '\nDemo finished. Open demo/phase3/output/matrix.txt (the decision matrix) and choices.csv (the approved choice). The temporary folder is removed now (TH_KEEP_DEMO=1 keeps it).\n'
if [ "$1" = "--check" ]; then [ "$FAIL" = 0 ] && echo "PHASE 3 CHECK PASS" || { echo "PHASE 3 CHECK FAIL"; exit 1; }; fi
