#!/usr/bin/env bash
# Checks a module's automated tests (stage 4): every approved case to automate has a written test with a real check.
# Usage: bash scripts/check-automation.sh <MODULE> [--for-approval]
#   --for-approval  also needs every test proven stable (reports/stable-<TC-ID>.txt from scripts/stable.sh)
# Exit 1 if anything is missing.
. "$(dirname "$0")/_py.sh"
$PY "$(dirname "$0")/lib/automate.py" check "$@"
