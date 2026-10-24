#!/usr/bin/env bash
# Lists where the tests can run: the targets in targets.json (or templates/targets.json), the Android devices adb sees, and whether the BrowserStack keys are set.
# Usage: bash scripts/targets.sh      (run with: run-web / run-mobile <MODULE> --target <name>)
. "$(dirname "$0")/_py.sh"
$PY "$(dirname "$0")/lib/targets.py" list
$PY -c "import sys; sys.path.insert(0, sys.argv[1]); import targets as t; d = t.adb_devices(); print('Android devices (adb):', ', '.join(d) if d else 'none'); print('BrowserStack keys in .env:', 'set' if t.keys_set() else 'not set (BROWSERSTACK_USERNAME, BROWSERSTACK_ACCESS_KEY)')" "$(dirname "$0")/lib"
