#!/usr/bin/env bash
# Usage: bash scripts/selftest.sh   Proves the template itself is healthy.
set -e
. scripts/_py.sh
for f in scripts/*.sh; do bash -n "$f"; done
bash scripts/setup.sh --help >/dev/null
for f in api/collections/*.json api/environments/*.json .claude/settings.json web/package.json; do $PY -c "import json,sys;json.load(open(sys.argv[1], encoding='utf-8'))" "$f"; done
# gate: template passes; API-style IDs and Excel's BOM are accepted; bad IDs, bad priorities and unproven "Done" are rejected
bash scripts/gate.sh templates/TestCases.csv
G=$(mktemp -d)
sed 's/^TC-EXAMPLE-001/TC-EXAMPLE-API-001/' templates/TestCases.csv > "$G/api.csv"; bash scripts/gate.sh "$G/api.csv" >/dev/null
{ printf '\xef\xbb\xbf'; cat templates/TestCases.csv; } > "$G/bom.csv"; bash scripts/gate.sh "$G/bom.csv" >/dev/null
sed 's/^TC-EXAMPLE-001/EXAMPLE-1/' templates/TestCases.csv > "$G/id.csv"; ! bash scripts/gate.sh "$G/id.csv" >/dev/null
sed 's/,P0,/,High,/' templates/TestCases.csv > "$G/pr.csv"; ! bash scripts/gate.sh "$G/pr.csv" >/dev/null
sed 's/,Draft$/,Done/' templates/TestCases.csv > "$G/done.csv"; ! bash scripts/gate.sh "$G/done.csv" >/dev/null
# intake
T0=$(mktemp -d); printf '## 1. Scope\n- Module: X\n- Platforms: [x] Android [ ] iOS\n## 2. Business rules\n1. Rule one\n## 4. Expected results\n| Situation | Expected |\n|---|---|\n| ok | fine |\n## 6. Priorities\n- P0: a\n' > "$T0/i.md"
bash scripts/check-intake.sh "$T0/i.md"
! bash scripts/check-intake.sh templates/MODULE_INTAKE.md >/dev/null
# digest
T=$(mktemp -d); mkdir -p "$T/r"
cat > "$T/r/a.xml" <<'X'
<testsuite><testcase classname="s" name="ok"/><testcase classname="s" name="bad"><failure message="boom"/></testcase></testsuite>
X
bash scripts/digest-failures.sh "$T/r" | grep -q "boom"
# stable: A passes 3 of 3, B fails once -> only A gets a stable file
S=$(mktemp -d); mkdir -p "$S/runs" "$S/out"; echo old > "$S/out/stable-TC-B-002.txt"
for i in 1 2 3; do
  F=""; [ "$i" = 2 ] && F='<failure message="x"/>'
  echo "<testsuites><testsuite name=\"m\"><testcase name=\"TC-A-001_ok\"/><testcase name=\"TC-B-002_flaky\">$F</testcase></testsuite></testsuites>" > "$S/runs/run-$i.xml"
done
bash scripts/stable.sh --from "$S/runs" "$S/out" >/dev/null && { echo "stable.sh passed a flaky case"; exit 1; }
[ -s "$S/out/stable-TC-A-001.txt" ] && [ ! -e "$S/out/stable-TC-B-002.txt" ] || { echo "stable.sh wrote the wrong files"; exit 1; }
# commands and agents
for c in .claude/commands/th-*.md; do
  a=$(grep -o 'Use the [a-z-]* subagent' "$c" | awk '{print $3}'); [ -n "$a" ] || a=$(sed -n 's#.*\.claude/agents/\([a-z-]*\)\.md.*#\1#p' "$c" | head -1)
  [ -f ".claude/agents/$a.md" ] || { echo "bad command $c -> $a"; exit 1; }
done
for a in .claude/agents/*.md; do n=$(sed -n 's/^name: //p' "$a" | head -1); [ "$n" = "$(basename "$a" .md)" ] || { echo "name mismatch $a"; exit 1; }; done
bash scripts/th.sh nope >/dev/null 2>&1 && { echo "th.sh accepted bad agent"; exit 1; }
bash scripts/gen-user.sh | grep -Eq '^qa\+[0-9]+@example\.com$' || { echo "gen-user.sh output is wrong"; exit 1; }
echo "SELFTEST PASS"
