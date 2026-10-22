#!/usr/bin/env bash
# Phase 2 demo: test design for the fictional Nakhla Rewards SIGNUP module, from the analysis approved in phase 1.
# Usage: bash demo/phase2/run.sh [--live]          Windows PowerShell: .\hive demo/phase2/run.sh [--live]
#   default  replays a recorded run of the manual-tester and qa-reviewer agents (free, about 1 minute, same result every time)
#   --live   runs the agents for real with Claude Code (uses your Claude plan, about 30-45 minutes; results vary)
# Works in a temporary copy; your project is not touched. Outputs to open afterwards: demo/phase2/output/
set -e
SRC="$(cd "$(dirname "$0")/../.." && pwd)"; D="$SRC/demo/phase2"; REC="$D/recorded"; P1="$SRC/demo/phase1/recorded"
LIVE=0; [ "$1" = "--live" ] && LIVE=1
. "$SRC/demo/_lib.sh"
demo_copy --exclude=./analysis --exclude=./test-cases --exclude=./reviews --exclude=./workflow/state.json --exclude=./workflow/APPROVALS.md --exclude=./.testhive-ready  # without the project's own work: analysis, cases, reviews, stage state
. scripts/_py.sh
step() { printf '\n=== %s\n' "$1"; }
show() { printf '$ %s\n' "$*"; "$@" || true; }
agent() { # $1 = agent, $2 = task text, then extra claude options
  if [ "$LIVE" = 1 ]; then
    command -v claude >/dev/null || { echo "claude is not installed: run setup --install"; exit 1; }
    a="$1"; t="$2"; shift 2
    claude --agent "$a" --permission-mode acceptEdits --allowedTools "Bash(bash scripts/*)" --output-format text "$@" -p "$t"
  else
    echo "(recorded run of the $1 agent; use --live to run it for real)"
  fi
}
cases() { # replay: the recorded cases, requests and the questions the designer added to analysis/gaps.csv
  [ "$LIVE" = 1 ] && return; cp "$REC/$1/TestCases.csv" test-cases/
  [ ! -f "$REC/$1/requests.csv" ] || cp "$REC/$1/requests.csv" test-cases/; [ ! -f "$REC/$1/gaps.csv" ] || cp "$REC/$1/gaps.csv" analysis/; }

step "1. Where phase 1 ended: SIGNUP requirements approved by the product owner (analysis baseline v1)"
bash scripts/init-project.sh "Nakhla Rewards" >/dev/null; cp "$D/CONTEXT.md" CONTEXT.md
cp "$P1"/recheck-2/requirements.csv "$P1"/recheck-2/gaps.csv analysis/
mkdir -p analysis/exploration/SIGNUP/web && cp "$P1/exploration.md" analysis/exploration/SIGNUP/web/
bash scripts/stage.sh init SIGNUP >/dev/null; bash scripts/stage.sh start SIGNUP analysis >/dev/null; bash scripts/stage.sh submit SIGNUP analysis >/dev/null
show bash scripts/stage.sh approve SIGNUP analysis --by "Sara (product owner)" --comment "All High gaps answered"

step "2. The manual-tester designs the cases from the baseline (techniques, risk, tags, links to requirements)"
bash scripts/stage.sh start SIGNUP design
agent manual-tester "Module SIGNUP. Design the test cases from the approved analysis baseline as your rules say (platforms in CONTEXT.md: Web and API). Run the checks and create the workbook. Do not submit."
cases first-pass
show bash scripts/check-design.sh SIGNUP
echo "--- three of the cases"
$PY -c "import csv,sys;sys.stdout.reconfigure(encoding='utf-8');r=[c for c in csv.DictReader(open('test-cases/TestCases.csv',encoding='utf-8')) if c['Module']=='SIGNUP'];[print(' ',c['ID'],c['Priority'],c['Technique'],'|',c['Title'][:70],'\n     expected:',c['Expected Result'][:110]) for c in (r[0],r[len(r)//3],r[2*len(r)//3])]"

step "3. Benchmark: how many of the 46 test conditions a QA expert listed for SIGNUP are covered?"
show bash scripts/score-design.sh SIGNUP demo/phase2/condition-key.csv

step "4. AI pre-review: the qa-reviewer audits the design before any human sees it"
agent qa-reviewer "Design pre-review of module SIGNUP as your rules say." --model sonnet
[ "$LIVE" = 1 ] || cp "$REC/DESIGN-SIGNUP-1.md" reviews/
f=$(ls reviews/DESIGN-SIGNUP-*.md 2>/dev/null | tail -1); [ -n "$f" ] && sed -n '1,30p' "$f" | cut -c1-200

step "5. The manual-tester fixes the reviewer's findings"
agent manual-tester "Module SIGNUP. The QA reviewer wrote $f. Fix every Blocker and Major finding and every Minor one that is right, then run the checks and rebuild the workbook. Do not submit."
cases after-review
show bash scripts/check-design.sh SIGNUP
show bash scripts/score-design.sh SIGNUP demo/phase2/condition-key.csv | sed -n 1,2p
echo "--- questions the designer raised for the business (they go into the next analysis round)"
$PY -c "import csv,sys;sys.stdout.reconfigure(encoding='utf-8');[print(' ',g['ID'],g['Severity'],'|',g['Question'][13:140]) for g in csv.DictReader(open('analysis/gaps.csv',encoding='utf-8')) if g['Question'].startswith('From design')]"

step "6. The human reviews in Excel (here a script plays the human): accepts, asks for changes, removes one, adds a case and a request"
show bash scripts/design-workbook.sh SIGNUP
$PY "$D/make/review-workbook.py" test-cases/SIGNUP-design.xlsx "$REC/sample-review.csv"
show bash scripts/import-review.sh SIGNUP
echo "(the design cannot be submitted while the review is not handled)"
show bash scripts/stage.sh submit SIGNUP design

step "7. The manual-tester handles the review: changes, removal, the human's case, the request"
agent manual-tester "Module SIGNUP. The human reviewed the workbook and the review is imported. Handle it as your rules say, then run the checks, rebuild the workbook, and submit if ready."
cases recheck-1
show bash scripts/check-design.sh SIGNUP --for-approval
bash scripts/stage.sh status SIGNUP | grep -q "design      awaiting" || show bash scripts/stage.sh submit SIGNUP design

step "8. A named human approves; the cases are frozen as design baseline v1"
show bash scripts/stage.sh approve SIGNUP design --by "Sara (QA lead)" --comment "Reviewed in Excel"
ls test-cases/baseline/SIGNUP/v1/
bash scripts/design-workbook.sh SIGNUP "$W/SIGNUP-design-approved.xlsx" >/dev/null

step "9. Later the analysis is reopened: the OTP now expires after 3 minutes, and the business answers the High design questions"
show bash scripts/stage.sh reopen SIGNUP analysis --by "Sara (product owner)" --comment "OTP expiry changes from 5 to 3 minutes"
$PY - <<'PY'
import csv
p = "analysis/requirements.csv"; rows = list(csv.DictReader(open(p, encoding="utf-8")))
for r in rows:
    if r["ID"] == "REQ-SIGNUP-016":
        r["Text"] = r["Text"].replace("5 minutes", "3 minutes"); r["Version"] = str(int(r["Version"]) + 1); r["Status"] = "Changed"
w = csv.DictWriter(open(p, "w", encoding="utf-8", newline=""), rows[0].keys(), lineterminator="\n"); w.writeheader(); w.writerows(rows)
p = "analysis/gaps.csv"; gaps = list(csv.DictReader(open(p, encoding="utf-8")))
for g in gaps:
    if g["Question"].startswith("From design") and g["Severity"] == "High":
        g["Answer"] = "The content team delivers the message catalogue in sprint 15. Until then check that a message appears at the field, in the page language; exact texts are added when the catalogue arrives."
        g["Answered By"], g["Status"] = "Sara (product owner)", "Closed"
w = csv.DictWriter(open(p, "w", encoding="utf-8", newline=""), gaps[0].keys(), lineterminator="\n"); w.writeheader(); w.writerows(gaps)
print("(the analyst updated REQ-SIGNUP-016: 5 minutes -> 3 minutes, and closed the High design questions with the business's answer)")
PY
bash scripts/stage.sh submit SIGNUP analysis >/dev/null
show bash scripts/stage.sh approve SIGNUP analysis --by "Sara (product owner)" --comment "OTP expiry 3 minutes"
show bash scripts/design-impact.sh SIGNUP --apply
echo "(design approval is refused until the manual-tester updates those cases)"
show bash scripts/check-design.sh SIGNUP --for-approval
show bash scripts/stage.sh status SIGNUP

mkdir -p "$D/output"; cp "$W/SIGNUP-design-approved.xlsx" test-cases/TestCases.csv "$D/output/"
cp "$f" "$D/output/" 2>/dev/null || true
printf '\nDemo finished. Open demo/phase2/output/SIGNUP-design-approved.xlsx (the approved design) and %s (the AI pre-review). The temporary folder is removed now (TH_KEEP_DEMO=1 keeps it).\n' "$(basename "$f")"
