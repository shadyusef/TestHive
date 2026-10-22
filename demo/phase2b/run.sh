#!/usr/bin/env bash
# Phase 2b demo: TestHive Studio on the fictional Nakhla Rewards project, where phase 2 left it (cases waiting for approval).
# Usage: bash demo/phase2b/run.sh [--check | --no-browser]          Windows PowerShell: .\hive demo/phase2b/run.sh [--check]
#   default  builds the demo project in a temporary folder and opens Studio in your browser (Ctrl+C stops it)
#   --check  no browser: drives Studio's API like a user would (answer, review, approve) and prints what happened (used by CI)
# Your project is not touched.
set -e
SRC="$(cd "$(dirname "$0")/../.." && pwd)"; P1="$SRC/demo/phase1/recorded"; P2="$SRC/demo/phase2/recorded"
W=$(mktemp -d); cd "$SRC"  # copy without the project's own work: analysis, cases, reviews, stage state
tar --exclude=.git --exclude=./runs/R-* --exclude='./demo/*/output' --exclude=./analysis --exclude=./test-cases --exclude=./reviews --exclude=./workflow/state.json --exclude=./workflow/APPROVALS.md --exclude=./.testhive-ready -cf - . | (cd "$W" && tar -xf -); cd "$W"
. scripts/_py.sh
bash scripts/init-project.sh "Nakhla Rewards" >/dev/null; cp demo/phase2/CONTEXT.md CONTEXT.md
cp "$P1"/recheck-2/requirements.csv "$P1"/recheck-2/gaps.csv analysis/
bash scripts/stage.sh init SIGNUP >/dev/null; bash scripts/stage.sh start SIGNUP analysis >/dev/null; bash scripts/stage.sh submit SIGNUP analysis >/dev/null
bash scripts/stage.sh approve SIGNUP analysis --by "Sara (product owner)" --comment "All High gaps answered" >/dev/null
bash scripts/stage.sh start SIGNUP design >/dev/null
cp "$P2"/recheck-1/TestCases.csv "$P2"/recheck-1/requests.csv test-cases/; cp "$P2"/recheck-1/gaps.csv analysis/
bash scripts/stage.sh submit SIGNUP design >/dev/null
echo "Demo project ready in $W: SIGNUP analysis approved, 123 test cases waiting for approval, 20 open questions."

if [ "$1" != "--check" ]; then
  echo "Starting Studio. In the browser: answer a question (Analysis), review cases (Design), approve the design (Approvals)."
  exec bash scripts/studio.sh "$@"
fi

LOGF="$W/studio.log"
bash scripts/studio.sh --no-browser --port 0 > "$LOGF" 2>&1 &
for i in $(seq 1 50); do grep -q "^STUDIO " "$LOGF" 2>/dev/null && break; sleep 0.2; done
URL=$(sed -n 's/^STUDIO //p' "$LOGF"); [ -n "$URL" ] || { cat "$LOGF"; echo "Studio did not start"; exit 1; }
echo "Studio started at ${URL%%\?*} (address with access key hidden)"
if [ -d web/node_modules/@playwright/test ]; then
  echo "--- the screens, clicked through in a real browser (screenshots go to demo/phase2b/output/)"
  node web/studio-smoke.mjs "$URL" "$SRC/demo/phase2b/output" || { echo "UI smoke test failed"; exit 1; }
else
  echo "(web tools not installed: skipping the browser click-through; install with setup --install --web)"
fi
echo "--- the same actions through Studio's API, with the refusals a person would see"
$PY "$SRC/demo/phase2b/walkthrough.py" "$URL"
