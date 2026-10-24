#!/usr/bin/env bash
# Test cycles (stage 5): one round of testing of a module on one environment, its results, bugs, retests and quarantine.
# Usage: bash scripts/cycle.sh start <MODULE> "<name>" --env <TEST_ENV name, or "" for .env> --by <you>   (starts the stage)
#        bash scripts/cycle.sh status <MODULE>                     the result of every case in the current cycle
#        bash scripts/cycle.sh result <MODULE> <TC-ID>[,...] Passed|Failed|Blocked [--bug BUG-<n>] [--note "..."] --by <you>   cases run by hand
#        bash scripts/cycle.sh bug <MODULE> <TC-ID> BUG-<n> --by <name>    links a bug to a failed automated test
#        bash scripts/cycle.sh fixed <MODULE> BUG-<n> --by <you>           its cases must be retested (retest.sh)
#        bash scripts/cycle.sh quarantine|unquarantine <MODULE> <TC-ID> --reason "why" --by <you>   a flaky test stops blocking
#        bash scripts/cycle.sh check <MODULE> [--for-approval]
# Every run stored for the module on the cycle's environment after it started counts (run-web, run-api, run-mobile).
. "$(dirname "$0")/_py.sh"
$PY "$(dirname "$0")/lib/execute.py" "$@"
