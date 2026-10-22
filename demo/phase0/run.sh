#!/usr/bin/env bash
# Phase 0 demo: stage gates, approval log, common run format, masking.
# Usage: bash demo/phase0/run.sh     Windows PowerShell: .\hive demo/phase0/run.sh
# Works in a temporary copy; the project is not touched.
set -e
SRC="$(cd "$(dirname "$0")/../.." && pwd)"; D="$SRC/demo/phase0"
. "$SRC/demo/_lib.sh"
W=$(mktemp -d); trap demo_cleanup EXIT; cp -r "$SRC/scripts" "$SRC/templates" "$SRC/mobile" "$W/"; cd "$W"
. scripts/_py.sh
step() { printf '\n=== %s\n' "$1"; }
show() { printf '$ %s\n' "$*"; "$@" || true; }

step "1. A new module starts with every stage pending"
show bash scripts/stage.sh init SIGNUP
show bash scripts/stage.sh status SIGNUP

step "2. Gate: test design cannot start before the analysis is approved"
show bash scripts/stage.sh start SIGNUP design

step "3. Analysis is done and handed to the human"
show bash scripts/stage.sh start SIGNUP analysis
show bash scripts/stage.sh submit SIGNUP analysis

step "4. Approval needs a named person; a rejection needs a reason"
show bash scripts/stage.sh approve SIGNUP analysis
show bash scripts/stage.sh reject SIGNUP analysis --by "Sara (QA lead)" --comment "Ask about OTP expiry and Arabic error messages"
show bash scripts/stage.sh submit SIGNUP analysis
show bash scripts/stage.sh approve SIGNUP analysis --by "Sara (QA lead)" --comment "All High gaps answered"

step "5. Now test design may start"
show bash scripts/stage.sh start SIGNUP design
show bash scripts/stage.sh status SIGNUP

step "6. Every decision is in the approvals log"
cat workflow/APPROVALS.md

step "7. A test run is saved automatically, in one format, with evidence linked to each case"
mkdir -p bin mobile/flows/signup
cat > bin/maestro <<'M'
#!/bin/sh
# stands in for Maestro in this demo: copies the sample results to where Maestro would write them
while [ $# -gt 0 ]; do [ "$1" = --output ] && out="$2"; shift; done
cp "$DEMO_JUNIT" "$out"; exit 1
M
chmod +x bin/maestro; printf 'APP_ID=com.example.app\nTEST_ENV=staging\n' > .env
export PATH="$W/bin:$PATH" DEMO_JUNIT="$D/sample-junit.xml"
show bash scripts/run-mobile.sh signup
echo "(The same run with evidence attached:)"
show bash scripts/collect-run.sh mobile signup --env staging --junit "$D/sample-junit.xml" --evidence "$D/sample-evidence"
RUN=$(ls -d runs/R-* | tail -1)
echo "--- $RUN/results.json (the failed case)"
$PY -c "import json,sys;r=json.load(open(sys.argv[1],encoding='utf-8'));print(json.dumps(r['cases'][1],indent=2,ensure_ascii=False))" "$RUN/results.json"
echo "--- runs/index.csv"; cat runs/index.csv

step "8. Masking, Arabic and English. First the human finds names to hide (suggest) ..."
echo "--- original"; cat "$D/sample-requirement.txt"
show bash scripts/mask.sh suggest "$D/sample-requirement.txt"
echo "(The human confirms all three, adds them to .mask-terms with the customer name, and puts the public office line in .mask-allow:)"
cp "$D/mask-terms.txt" .mask-terms; printf '+966 11 000 0000\n' > .mask-allow; cat .mask-terms .mask-allow

step "9. ... checks every match in context (review) ..."
show bash scripts/mask.sh review "$D/sample-requirement.txt"

step "10. ... then masks. This is all Claude would see"
show bash scripts/mask.sh mask "$D/sample-requirement.txt" masked.txt
cat masked.txt
echo "Kept on purpose: order 1012345678 (fails the ID check), the public office line (in .mask-allow), the Arabic sentence (no personal data)."
show bash scripts/mask.sh unmask masked.txt restored.txt
cmp -s "$D/sample-requirement.txt" restored.txt && echo "Restored text is identical to the original."

step "11. Screenshots: personal data is blacked out with OCR"
if $PY -c "import PIL, pytesseract" 2>/dev/null && { command -v tesseract >/dev/null || [ -x "/c/Program Files/Tesseract-OCR/tesseract.exe" ]; }; then
  $PY "$D/make-screenshot.py" shot.png
  show bash scripts/mask.sh mask shot.png shot-masked.png
  mkdir -p "$SRC/demo/phase0/output"; cp shot.png shot-masked.png "$SRC/demo/phase0/output/"
  EDGE="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
  if [ -x "$EDGE" ]; then
    echo "--- the same on an Arabic screen (drawn by Edge from demo/phase0/arabic-screen.html)"
    timeout 60 "$EDGE" --headless --disable-gpu --no-first-run --user-data-dir="$(cygpath -w "$W/edge")" --window-size=760,460 \
      --screenshot="$(cygpath -w "$W/arabic-shot.png")" "file:///$(cygpath -m "$D/arabic-screen.html")" >/dev/null 2>&1 || true
    for i in $(seq 1 15); do [ -s arabic-shot.png ] && break; sleep 1; done   # Edge writes the file after it returns
    if [ -s arabic-shot.png ]; then
      show bash scripts/mask.sh mask arabic-shot.png arabic-shot-masked.png
      cp arabic-shot.png arabic-shot-masked.png "$SRC/demo/phase0/output/"
    fi
  fi
  echo "Before and after images are in demo/phase0/output/"
else
  echo "Skipped: Tesseract is not installed (setup -Install -Ocr)."
fi
echo; echo "Demo finished. The temporary folder is removed now (TH_KEEP_DEMO=1 keeps it to look around)."
