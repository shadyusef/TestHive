#!/usr/bin/env bash
# Builds the contract tests of a module from its OpenAPI spec (stage 4; no agent, no test data).
# Usage: bash scripts/contract.sh <MODULE>
# Reads the OpenAPI files among requirements/sources/<MODULE>/ and writes api/collections/<MODULE>.contract.postman_collection.json:
# one request per endpoint, checking that the status is one the spec lists and the body matches its schema. Rebuilt when the
# spec changes (never edit it by hand); scaffold.sh builds it too. Run it with: bash scripts/run-api.sh <MODULE> --contract
# Known bugs: api/collections/<MODULE>.contract-bugs.txt, one "<METHOD> <path> <BUG-ID>" per line.
. "$(dirname "$0")/_py.sh"
$PY "$(dirname "$0")/lib/automate.py" contract "$@"
