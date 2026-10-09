#!/usr/bin/env bash
# Usage: bash scripts/selftest.sh   Proves the template itself is healthy.
set -e
for f in scripts/*.sh; do bash -n "$f"; done
for f in api/collections/*.json api/environments/*.json; do python3 -c "import json,sys;json.load(open(sys.argv[1]))" "$f"; done
bash scripts/gate.sh templates/TestCases.csv
T=$(mktemp -d); mkdir -p "$T/r"
cat > "$T/r/a.xml" <<'X'
<testsuite><testcase classname="s" name="ok"/><testcase classname="s" name="bad"><failure message="boom"/></testcase></testsuite>
X
bash scripts/digest-failures.sh "$T/r" | grep -q "boom"
echo "SELFTEST PASS"
