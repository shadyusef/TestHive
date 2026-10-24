# Sourced by demo/phase5/run.sh when demo/phase6/run.sh starts it (TH_DEMO_NEXT): the test cycle is approved; now the report.
step "8. The test report, built from the approved cycle (one HTML file to share or print)"
show bash scripts/report.sh SIGNUP
expect "REPORT SIGNUP: reports/SIGNUP-report.html" "the report is built"
expect "TestHive suggests No-go" "No-go: a P1 case (TC-SIGNUP-044, Arabic labels) failed"
grep -o "TestHive suggests: [^<]*" reports/SIGNUP-report.html | head -1
grep -o "<li>TC-SIGNUP-044[^<]*</li>" reports/SIGNUP-report.html | head -1
show bash scripts/bug.sh list SIGNUP
expect "BUG-SIGNUP-001   Major    Fixed" "the fixed bug is in the register"

step "9. The decision: a named person, with the reason; a late change makes it stale"
show bash scripts/report.sh decide SIGNUP Go --by "Mona (product owner)"
expect "Usage" "a decision needs its reason"
show bash scripts/report.sh decide SIGNUP Go --reason "Launch English-only first; BUG-SIGNUP-002 (Arabic labels) is fixed in 1.1" --by "Mona (product owner)"
expect "DECISION SIGNUP: Go by Mona" "Go is recorded, against the suggestion, with the reason"
show bash scripts/bug.sh status SIGNUP BUG-SIGNUP-001 Verified --note "retested in 1.0.1" --by "Sara (QA lead)"
show bash scripts/report.sh check SIGNUP --for-approval
expect "the report is older than the approved cycle or the bug register" "a bug changed: the report must be built again"
expect "decide again" "and the decision made again"
bash scripts/report.sh SIGNUP | sed 's/^/  /'
bash scripts/report.sh decide SIGNUP Go --reason "Launch English-only first; BUG-SIGNUP-002 (Arabic labels) is fixed in 1.1" --by "Mona (product owner)" | sed 's/^/  /'
show bash scripts/report.sh check SIGNUP --for-approval
expect "REPORTING OK" "ready for the sign-off"
expect "Go although TestHive suggests No-go" "the warning stays visible"

step "10. The sign-off: reporting is approved and the report is frozen"
show bash scripts/stage.sh submit SIGNUP reporting
bash scripts/stage.sh approve SIGNUP reporting --by "Omar (QA manager)" | tee "$W/last.out"
expect "REPORTING BASELINE SIGNUP v1" "the report and the bug register are kept in reporting/baseline/"
show bash scripts/stage.sh status SIGNUP
expect "next: all stages approved" "every stage of SIGNUP is approved"
mkdir -p "$SRC/demo/phase6/output"; cp reports/SIGNUP-report.html "$SRC/demo/phase6/output/"
if [ "$1" = "--check" ]; then
  bash scripts/studio.sh --no-browser --port 0 > "$W/studio6.log" 2>&1 &
  for i in $(seq 1 150); do grep -q "^STUDIO " "$W/studio6.log" 2>/dev/null && break; sleep 0.2; done
  $PY "$SRC/demo/phase6/walkthrough.py" "$(sed -n 's/^STUDIO //p' "$W/studio6.log")" || FAIL=1
fi
