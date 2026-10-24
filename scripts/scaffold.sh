#!/usr/bin/env bash
# Sets up the test project for a module's approved tools (stage 4): one placeholder test per approved case to automate.
# Usage: bash scripts/scaffold.sh <MODULE>
# Needs the tools stage approved. Playwright -> web/tests/<MODULE>/<TC-ID>_<title>.spec.ts (and web/fixtures/testhive.ts);
# Postman + Newman -> api/collections/<MODULE>.postman_collection.json (a request per case) and its environment;
# Maestro -> mobile/flows/<MODULE>/<TC-ID>_<title>.yaml. Each placeholder carries the case's steps and @tags and fails or is
# skipped until an engineer writes it. Never overwrites what exists; fills the Automation Spec column; starts the stage.
. "$(dirname "$0")/_py.sh"
$PY "$(dirname "$0")/lib/automate.py" scaffold "$@"
