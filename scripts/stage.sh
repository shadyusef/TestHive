#!/usr/bin/env bash
# Stage gates: no stage starts until the stage before it is approved by a human.
# Usage: bash scripts/stage.sh <command> ...
#   init    <MODULE>                     add a module (all stages pending)
#   status  [MODULE]                     show every stage and what comes next
#   start   <MODULE> <stage>             begin a stage (refused unless the previous stage is approved)
#   submit  <MODULE> <stage>             output is ready: the stage now waits for a human
#   approve <MODULE> <stage> --by <name> [--comment "..."]
#   reject  <MODULE> <stage> --by <name> --comment "why"      sends the stage back to in progress
#   reopen  <MODULE> <stage> --by <name> --comment "why"      an approved stage changes again (e.g. new requirements);
#                                        later stages that were started go back to in progress and need a new approval
#   check   <MODULE> <stage>             exit 0 if the stage may start, 2 if not
#   archive <MODULE> --by <name> --comment "why"    moves the module, its files and its register rows to archive/<MODULE>-<time>/
#   restore <MODULE>-<time> --by <name> [--comment "..."]   puts an archived module back (nothing is ever deleted)
# Stages, in order: analysis design tools automation execution reporting
# State lives in workflow/state.json; every decision is appended to workflow/APPROVALS.md.
# Submitting or approving "analysis" first runs check-analysis --for-approval (when analysis/requirements.csv exists) and then
# freezes the module's registers as a baseline in analysis/baseline/<MODULE>/v<n>/.
# Submitting or approving "design" first runs check-design --for-approval (when test-cases/TestCases.csv exists) and then
# freezes the module's cases as a baseline in test-cases/baseline/<MODULE>/v<n>/.
# Submitting or approving "tools" first runs tool-advice check --for-approval and then freezes the choice in tools/baseline/<MODULE>/v<n>/.
# Submitting or approving "automation" first runs check-automation --for-approval and then records the tests in automation/baseline/<MODULE>/v<n>/.
. "$(dirname "$0")/_py.sh"
exec $PY "$(dirname "$0")/lib/stage.py" "$@"
