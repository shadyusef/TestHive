#!/usr/bin/env bash
# Phase 2c demo: TestHive Studio from an empty project: set up the project, add a module, upload its documents, read them.
# Usage: bash demo/phase2c/run.sh [--check | --no-browser]          Windows PowerShell: .\hive demo/phase2c/run.sh [--check]
#   default  makes an empty project in a temporary folder and opens Studio in your browser (Ctrl+C stops it).
#            The fictional documents to upload are in demo/phase1/sources/ (PRD, user stories, API spec, mock-up).
#   --check  no browser: drives Studio's API like a newcomer would and prints what happened (used by CI); with the web
#            tools installed it also clicks through the screens and saves screenshots in demo/phase2c/output/
# Your project is not touched.
set -e
SRC="$(cd "$(dirname "$0")/../.." && pwd)"
W=$(mktemp -d); cd "$SRC"  # copy the tool only: no project files, no requirements, no work
tar --exclude=.git --exclude=./runs/R-* --exclude='./demo/*/output' --exclude=./analysis --exclude=./test-cases --exclude=./reviews --exclude=./requirements --exclude=./workflow/state.json --exclude=./workflow/APPROVALS.md --exclude=./.testhive-ready --exclude=./PROJECT_BRIEF.md --exclude=./CONTEXT.md --exclude=./.env --exclude=./.mask-terms --exclude=./.mask-allow --exclude=./.mask-map.json -cf - . | (cd "$W" && tar -xf -); cd "$W"
. scripts/_py.sh
echo "Empty project ready in $W."

if [ "$1" != "--check" ]; then
  echo "Starting Studio. In the browser: fill in the project, add module SIGNUP, upload the files from $SRC/demo/phase1/sources/, click 'Read the documents'."
  exec bash scripts/studio.sh "$@"
fi

LOGF="$W/studio.log"
bash scripts/studio.sh --no-browser --port 0 > "$LOGF" 2>&1 &
for i in $(seq 1 150); do grep -q "^STUDIO " "$LOGF" 2>/dev/null && break; sleep 0.2; done
URL=$(sed -n 's/^STUDIO //p' "$LOGF"); [ -n "$URL" ] || { cat "$LOGF"; echo "Studio did not start"; exit 1; }
echo "Studio started at ${URL%%\?*} (address with access key hidden)"
[ -d web/node_modules/@playwright/test ] && { node web/studio-intake-smoke.mjs "$URL" "$SRC/demo/phase2c/output" none --welcome || R=1; }
$PY "$SRC/demo/phase2c/walkthrough.py" "$URL" "$SRC/demo/phase1/sources" "$W" --keep || R=1
if [ -z "$R" ] && [ -d web/node_modules/@playwright/test ]; then
  echo "--- the same screens in a real browser (screenshots go to demo/phase2c/output/)"
  echo "Meeting notes: the sign-up page must also work on small phones." > "$W/notes.txt"
  node web/studio-intake-smoke.mjs "$URL" "$SRC/demo/phase2c/output" "$W/notes.txt" || R=1
elif [ -z "$R" ]; then
  echo "(web tools not installed: skipping the browser click-through; install with setup --install --web)"
fi
$PY -c "import sys,urllib.request as u; u.urlopen(u.Request(sys.argv[1].split('?')[0]+'api/shutdown', data=b'{}', headers={'X-TestHive-Token': sys.argv[1].split('t=')[1], 'Content-Type': 'application/json'}))" "$URL" >/dev/null 2>&1 || true
exit ${R:-0}
