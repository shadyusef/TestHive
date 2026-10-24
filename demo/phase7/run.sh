#!/usr/bin/env bash
# Phase 7 demo: Studio answers the agents' questions, and explores an Android app. Recorded agents (demo/phase2d/fake-claude.py)
# stand in for Claude Code: one asks twice (to run npx playwright, then to write the Playwright config) and the person allows the
# first and denies the second in Studio; another walks two screens of the app on a stand-in device (a fake adb that lists one).
# Usage: bash demo/phase7/run.sh [--check]          Windows PowerShell: .\hive demo/phase7/run.sh [--check]
#   The demo always drives Studio through its API (as the page does) and exits 1 when a step is wrong (selftest, CI).
set -e
SRC="$(cd "$(dirname "$0")/../.." && pwd)"
. "$SRC/demo/_lib.sh"
demo_copy --exclude=./analysis --exclude=./test-cases --exclude=./tools --exclude=./automation --exclude=./execution --exclude=./reporting \
  --exclude=./reviews --exclude=./runs --exclude=./reports --exclude=./workflow/state.json --exclude=./workflow/APPROVALS.md --exclude=./.testhive-ready --exclude=./dist --exclude=./build
drop_files PROJECT_BRIEF.md CONTEXT.md
. scripts/_py.sh
bash scripts/init-project.sh "Nakhla Rewards" >/dev/null; bash scripts/stage.sh init SIGNUP >/dev/null
export TH_CLAUDE_FAKE="$SRC/demo/phase2d/fake-claude.py" TH_FAKE_DELAY=0.05 TH_ASK_POLL=0.1
mkdir -p "$W/bin"; printf '@echo List of devices attached\r\n@echo emulator-5554\tdevice\r\n' > "$W/bin/adb.cmd"
printf '#!/bin/sh\nprintf "List of devices attached\nemulator-5554\tdevice\n"\n' > "$W/bin/adb"; chmod +x "$W/bin/adb"
export PATH="$W/bin:$PATH"   # a stand-in adb: Studio sees one device (the recorded analyst never touches it)
studio() {  # starts Studio in the background (a job of this shell, stopped by the demo's cleanup); sets URL
  N=$((N + 1)); L="$W/studio$N.log"   # a new log each time: the last Studio may still be closing
  bash scripts/studio.sh --no-browser --port 0 > "$L" 2>&1 &
  for i in $(seq 1 150); do grep -q "^STUDIO " "$L" 2>/dev/null && break; sleep 0.2; done
  URL=$(sed -n 's/^STUDIO //p' "$L"); [ -n "$URL" ] || { cat "$L"; exit 1; }
}
set +e
printf '
=== 1. An agent asks; the person answers in Studio (Allow once, then Deny with a note)
'
TH_FAKE_ASK=1; export TH_FAKE_ASK; studio; unset TH_FAKE_ASK
$PY "$SRC/demo/phase7/walkthrough.py" "$URL" ask; A=$?
sleep 1
printf '
=== 2. Explore the Android app from Studio (the APK uploaded, the device picked)
'
studio
$PY "$SRC/demo/phase7/walkthrough.py" "$URL" explore; B=$?
mkdir -p "$SRC/demo/phase7/output"; ls runs/agents > "$SRC/demo/phase7/output/agent-runs.txt" 2>/dev/null || true
[ "$A$B" = 00 ] && echo "PHASE 7 CHECK PASS" || { echo "PHASE 7 CHECK FAIL"; exit 1; }
printf '\nDemo finished. The temporary folder is removed now (TH_KEEP_DEMO=1 keeps it).\n'
