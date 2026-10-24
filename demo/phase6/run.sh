#!/usr/bin/env bash
# Phase 6 demo: the test report and the sign-off of the fictional Nakhla Rewards SIGNUP module. It runs the phase 5 demo (the test
# cycle, its bugs in reports/bugs.csv, the retest and the approval), then goes on: the report is built, a late bug change makes it
# stale, it is built again, a named person decides Go against TestHive's No-go suggestion (with the reason), and the stage is signed off.
# Usage: bash demo/phase6/run.sh [--check]          Windows PowerShell: .\hive demo/phase6/run.sh [--check]
#   --check  also checks Studio's Reports data and refusals through its API; exits 1 when a step is wrong (selftest, CI)
# Needs the web tools and Newman (as phase 5). The report is copied to demo/phase6/output/SIGNUP-report.html to open.
SRC="$(cd "$(dirname "$0")/../.." && pwd)"
OUT=$(TH_DEMO_NEXT="$SRC/demo/phase6/steps.sh" bash "$SRC/demo/phase5/run.sh" "$@" 2>&1); RC=$?
printf '%s\n' "$OUT"
[ "$RC" = 0 ] && ! printf '%s' "$OUT" | grep -q "WRONG" || { echo "PHASE 6 CHECK FAIL"; exit 1; }
if [ "$1" = "--check" ]; then printf '%s' "$OUT" | grep -q "STUDIO REPORTING CHECK PASS" && echo "PHASE 6 CHECK PASS" || { echo "PHASE 6 CHECK FAIL"; exit 1; }; fi
