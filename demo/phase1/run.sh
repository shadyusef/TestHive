#!/usr/bin/env bash
# Phase 1 demo: business analysis of a fictional app (Nakhla Rewards, module SIGNUP), from documents and a built web app.
# Usage: bash demo/phase1/run.sh [--live]          Windows PowerShell: .\hive demo/phase1/run.sh [--live]
#   default  replays a recorded run of the business-analyst agent (free, about 1 minute, same result every time)
#   --live   runs the agent for real with Claude Code (uses your Claude plan, about 15-25 minutes; results vary a little)
# Works in a temporary copy; your project is not touched. Outputs to open afterwards: demo/phase1/output/
set -e
SRC="$(cd "$(dirname "$0")/../.." && pwd)"; D="$SRC/demo/phase1"; REC="$D/recorded"
LIVE=0; [ "$1" = "--live" ] && LIVE=1
. "$SRC/demo/_lib.sh"
demo_copy
rm -rf analysis/* workflow/state.json workflow/APPROVALS.md .testhive-ready
. scripts/_py.sh
step() { printf '\n=== %s\n' "$1"; }
show() { printf '$ %s\n' "$*"; "$@" || true; }
analyst() { # $1 = task text
  if [ "$LIVE" = 1 ]; then
    command -v claude >/dev/null || { echo "claude is not installed: run setup --install"; exit 1; }
    claude --agent business-analyst --permission-mode acceptEdits --allowedTools "Bash(bash scripts/*)" --output-format text -p "$1"
  else
    echo "(recorded run of the business-analyst agent; use --live to run it for real)"
  fi
}

step "1. A new project with four requirement sources: PRD (PDF), user stories (Word), API spec (OpenAPI), design mock-up (image)"
bash scripts/init-project.sh "Nakhla Rewards" >/dev/null
show bash scripts/stage.sh init SIGNUP
mkdir -p requirements/sources/SIGNUP && cp "$D"/sources/* requirements/sources/SIGNUP/ && ls requirements/sources/SIGNUP

step "2. Ingest: every document becomes text the analyst can read (with the source of each line)"
show bash scripts/ingest.sh SIGNUP
echo "--- excerpt of the API spec as the analyst reads it"; sed -n 4,11p analysis/sources-text/SIGNUP/openapi.yaml.md

step "3. Explore the built product (a local copy of the web app): pages, fields, rules and messages"
if [ -d web/node_modules/@playwright/test ]; then
  show bash scripts/explore-web.sh SIGNUP demo/phase1/site/index.html --submit-valid
else
  echo "(web tools not installed: showing the recorded exploration; install with setup --install --web)"
  mkdir -p analysis/exploration/SIGNUP/web && cp "$REC"/exploration.md analysis/exploration/SIGNUP/web/
fi
grep -E "^## Page|^- Submitted" analysis/exploration/SIGNUP/web/exploration.md | cut -c1-170

step "4. The business-analyst agent writes the requirements and the gaps (first pass)"
bash scripts/stage.sh start SIGNUP analysis
analyst "Module SIGNUP. Analyse all documents in requirements/sources/SIGNUP/ (fictional data, no masking). The web app was already explored: read analysis/exploration/SIGNUP/web/exploration.md. Produce the registers and the workbook as your rules say."
[ "$LIVE" = 1 ] || cp "$REC"/first-pass/requirements.csv "$REC"/first-pass/gaps.csv analysis/
show bash scripts/check-analysis.sh SIGNUP
echo "--- the five highest-priority questions"
$PY -c "import csv,sys;sys.stdout.reconfigure(encoding='utf-8');[print(' ',r['ID'],r['Kind'],'|',r['Question'][:150]) for r in [g for g in csv.DictReader(open('analysis/gaps.csv',encoding='utf-8')) if g['Severity']=='High'][:5]]"

step "5. Benchmark: how many of the 23 gaps planted in these documents did the analyst find?"
show bash scripts/score-analysis.sh SIGNUP demo/phase1/answer-key.csv

step "6. The stage cannot be submitted while High gaps are open"
show bash scripts/stage.sh submit SIGNUP analysis

step "7. Round 1: the human answers in Excel (here a script plays the human), then TestHive imports the answers"
show bash scripts/analysis-workbook.sh SIGNUP
$PY "$D/make/answer-workbook.py" analysis/SIGNUP-analysis.xlsx "$REC/sample-answers.csv"
show bash scripts/import-answers.sh SIGNUP
echo "(approval is still refused: the analyst has not reviewed the answers yet)"
show bash scripts/check-analysis.sh SIGNUP --for-approval

step "8. The analyst re-checks: closes settled gaps, updates requirements, and asks follow-up questions"
analyst "Module SIGNUP. The human answered the workbook and the answers are imported. Re-check them as your rules say, then run the checks, rebuild the workbook, and submit if ready."
[ "$LIVE" = 1 ] || cp "$REC"/recheck-1/requirements.csv "$REC"/recheck-1/gaps.csv analysis/
show bash scripts/check-analysis.sh SIGNUP
echo "--- follow-up questions"
$PY -c "import csv,sys;sys.stdout.reconfigure(encoding='utf-8');[print(' ',r['ID'],r['Severity'],'|',r['Question'][:150]) for r in csv.DictReader(open('analysis/gaps.csv',encoding='utf-8')) if r['Question'].startswith('Follow-up') and r['Status']=='Open']"
echo "(a High follow-up is open, so the stage still cannot be submitted)"
show bash scripts/stage.sh submit SIGNUP analysis

step "9. Round 2: the human answers the follow-ups; the analyst re-checks and submits"
bash scripts/analysis-workbook.sh SIGNUP >/dev/null
$PY "$D/make/answer-workbook.py" analysis/SIGNUP-analysis.xlsx "$REC/sample-answers-2.csv"
show bash scripts/import-answers.sh SIGNUP
analyst "Module SIGNUP. The human answered the follow-up questions and the answers are imported. Re-check them as your rules say, then run the checks, rebuild the workbook, and submit if ready."
[ "$LIVE" = 1 ] || cp "$REC"/recheck-2/requirements.csv "$REC"/recheck-2/gaps.csv analysis/
show bash scripts/check-analysis.sh SIGNUP --for-approval
bash scripts/stage.sh status SIGNUP | grep -q "analysis    awaiting" || show bash scripts/stage.sh submit SIGNUP analysis

step "10. A named human approves; the requirements are frozen as baseline v1"
show bash scripts/stage.sh approve SIGNUP analysis --by "Sara (product owner)" --comment "All High gaps answered"
ls analysis/baseline/SIGNUP/v1/; show bash scripts/stage.sh status SIGNUP

step "11. Android: the same exploration on a phone (needs a connected device and the app's APK)"
if command -v adb >/dev/null && [ "$(adb get-state 2>/dev/null)" = device ]; then
  echo "A device is connected. To explore your app: bash scripts/explore-android.sh <MODULE> install <app.apk>, then launch, snap, tap, type."
else
  echo "(no device connected: showing how one recorded screen is read)"
fi
$PY scripts/lib/uiscreen.py summary demo/phase1/samples/android-signup.xml "01 sign up (sample)"

mkdir -p "$D/output"; cp analysis/SIGNUP-analysis.xlsx analysis/requirements.csv analysis/gaps.csv "$D/output/"
bash scripts/analysis-workbook.sh SIGNUP "$D/output/SIGNUP-analysis-final.xlsx" >/dev/null
printf '\nDemo finished. Open demo/phase1/output/SIGNUP-analysis.xlsx (answered workbook) and SIGNUP-analysis-final.xlsx (after the re-check). Temporary folder: %s\n' "$W"
