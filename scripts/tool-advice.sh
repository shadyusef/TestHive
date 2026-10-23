#!/usr/bin/env bash
# Tool advice (stage 3, functional tests): a decision matrix per test type from the approved design, and the human's choice.
# Usage: bash scripts/tool-advice.sh <MODULE>                                   the matrix: test types, tools, scores, the recommendation
#        bash scripts/tool-advice.sh choose <MODULE> "<test type>" <tool> --by <name> [--reason "why"]   (a reason is needed when
#                                                                               the tool is not the recommended one)
#        bash scripts/tool-advice.sh check <MODULE> [--for-approval]            exit 1 if a test type has no valid choice
#        bash scripts/tool-advice.sh settings [--weights fit=3,testhive=3,...] [--skills Java,Python]   the project's weights and team skills
# Test types: Web UI, API, Android, iOS. Reads test-cases/baseline/<MODULE>/v<latest>/; writes tools/choices.csv and tools/settings.json.
# Flow: stage.sh start <MODULE> tools, choose each type, stage.sh submit, a human approves (freezes tools/baseline/<MODULE>/v<n>/).
. "$(dirname "$0")/_py.sh"
$PY "$(dirname "$0")/lib/tools.py" "$@"
