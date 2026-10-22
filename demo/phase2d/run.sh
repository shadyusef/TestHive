#!/usr/bin/env bash
# Phase 2d demo: run the agents from TestHive Studio (Run buttons) instead of copying commands into Claude Code.
# Usage: bash demo/phase2d/run.sh [--check | --live] [--no-browser]     Windows PowerShell: .\hive demo/phase2d/run.sh [--check | --live]
#   default  SIGNUP project with its documents read, Studio open; the Run buttons replay recorded agent runs (free, seconds)
#   --live   the same project, but the Run buttons start Claude Code for real (uses your Claude plan; minutes per run)
#   --check  no browser: presses the Run buttons through Studio's API from first pass to approved design (used by CI)
# Your project is not touched.
set -e
SRC="$(cd "$(dirname "$0")/../.." && pwd)"
W=$(mktemp -d); cd "$SRC"  # copy the tool only: no project files, no requirements, no work
tar --exclude=.git --exclude=./runs/R-* --exclude=./runs/agents --exclude='./demo/*/output' --exclude=./analysis --exclude=./test-cases --exclude=./reviews --exclude=./requirements --exclude=./workflow/state.json --exclude=./workflow/APPROVALS.md --exclude=./.testhive-ready --exclude=./PROJECT_BRIEF.md --exclude=./CONTEXT.md --exclude=./.env --exclude=./.mask-terms --exclude=./.mask-allow --exclude=./.mask-map.json -cf - . | (cd "$W" && tar -xf -); cd "$W"
. scripts/_py.sh
bash scripts/init-project.sh "Nakhla Rewards" >/dev/null; cp demo/phase2/CONTEXT.md CONTEXT.md
bash scripts/stage.sh init SIGNUP >/dev/null
mkdir -p requirements/sources/SIGNUP requirements/modules && cp demo/phase1/sources/* requirements/sources/SIGNUP/
printf '{\n  "title": "Sign-up and mobile verification",\n  "url": "",\n  "test_env": false,\n  "apk": "",\n  "mask": false\n}\n' > requirements/modules/SIGNUP.json
bash scripts/ingest.sh SIGNUP >/dev/null
echo "Demo project ready in $W: module SIGNUP with its 4 documents read, nothing analysed yet."

MODE=recorded; [ "$1" = "--live" ] && MODE=live && shift
[ "$MODE" = recorded ] && export TH_CLAUDE_FAKE="$SRC/demo/phase2d/fake-claude.py"
if [ "$1" != "--check" ]; then
  echo "Starting Studio ($MODE agents). Open SIGNUP and press the Run button under Next; answer questions and review cases between runs."
  exec bash scripts/studio.sh "$@"
fi
export TH_FAKE_DELAY=0.4
LOGF="$W/studio.log"
bash scripts/studio.sh --no-browser --port 0 > "$LOGF" 2>&1 &
for i in $(seq 1 50); do grep -q "^STUDIO " "$LOGF" 2>/dev/null && break; sleep 0.2; done
URL=$(sed -n 's/^STUDIO //p' "$LOGF"); [ -n "$URL" ] || { cat "$LOGF"; echo "Studio did not start"; exit 1; }
echo "Studio started at ${URL%%\?*} (address with access key hidden); agents: recorded"
if [ -d web/node_modules/@playwright/test ]; then
  echo "--- the Run button in a real browser (screenshots go to demo/phase2d/output/)"
  node web/studio-run-smoke.mjs "$URL" "$SRC/demo/phase2d/output" || { echo "UI smoke test failed"; exit 1; }
else
  echo "(web tools not installed: skipping the browser click-through; install with setup --install --web)"
fi
echo "--- every Run button through Studio's API, from the first pass to an approved design"
$PY "$SRC/demo/phase2d/walkthrough.py" "$URL"
