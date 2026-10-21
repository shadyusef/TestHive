#!/usr/bin/env bash
# Proves TestHive itself works on this machine (run it after setup and after every change).
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
# stage gates: order enforced, named approver required, reject needs a comment, decisions logged
W=$(mktemp -d); export TH_STATE="$W/state.json"
bash scripts/stage.sh init demo >/dev/null
bash scripts/stage.sh start DEMO design >/dev/null && { echo "stage.sh started design before analysis was approved"; exit 1; }
bash scripts/stage.sh start DEMO analysis >/dev/null; bash scripts/stage.sh submit DEMO analysis >/dev/null
bash scripts/stage.sh approve DEMO analysis >/dev/null && { echo "stage.sh approved without --by"; exit 1; }
bash scripts/stage.sh approve DEMO analysis --by tester >/dev/null
bash scripts/stage.sh check DEMO design >/dev/null
bash scripts/stage.sh start DEMO design >/dev/null; bash scripts/stage.sh submit DEMO design >/dev/null
bash scripts/stage.sh reject DEMO design --by tester >/dev/null && { echo "stage.sh rejected without a comment"; exit 1; }
bash scripts/stage.sh reject DEMO design --by tester --comment "add negative cases" >/dev/null
bash scripts/stage.sh status DEMO | grep -q "design      in progress" || { echo "stage.sh status is wrong"; exit 1; }
[ "$(grep -c '^| 20' "$W/APPROVALS.md")" = 2 ] || { echo "APPROVALS.md does not have 2 decisions"; exit 1; }
unset TH_STATE
# collect-run: common results format, case IDs and evidence linked
R=$(mktemp -d); export TH_RUNS="$R/runs"; mkdir -p "$R/ev"; echo x > "$R/ev/TC-DEMO-002_fail.png"
echo '<testsuites><testsuite name="demo"><testcase name="TC-DEMO-001_ok" time="1.5"/><testcase name="TC-DEMO-002_fail"><failure message="Expected Welcome"/></testcase></testsuite></testsuites>' > "$R/j.xml"
bash scripts/collect-run.sh mobile demo --junit "$R/j.xml" --evidence "$R/ev" | grep -q "2 cases, 1 passed, 1 failed" || { echo "collect-run.sh totals are wrong"; exit 1; }
bash scripts/collect-run.sh mobile demo --junit "$R/j.xml" | grep -Eq "R-[0-9]{8}-02" || { echo "collect-run.sh run numbering is wrong"; exit 1; }
$PY -c "import json,sys,glob;r=json.load(open(sorted(glob.glob(sys.argv[1]+'/R-*-01/results.json'))[0],encoding='utf-8'));c=r['cases'][1];sys.exit(not(c['id']=='TC-DEMO-002' and c['status']=='failed' and len(c['evidence'])==1))" "$TH_RUNS" || { echo "collect-run.sh results.json is wrong"; exit 1; }
unset TH_RUNS
# masking: Arabic + English, round trip restores the original exactly
M=$(mktemp -d); export TH_MASK_MAP="$M/map.json" TH_MASK_TERMS="$M/terms" TH_MASK_ALLOW="$M/allow"
printf 'أحمد الحربي\nAcme Bank\n' > "$TH_MASK_TERMS"; printf '+966 11 000 0000\n' > "$TH_MASK_ALLOW"
printf 'العميل أحمد الحربي من Acme Bank\nEmail: ahmed.h@example.com Phone: +966 55 123 4567 / 0551234567 Office: +966 11 000 0000\nID: 1012345672 Order: 1012345678 Card: 4111 1111 1111 1111 Ref: 4111 1111 1111 1112\nIBAN: SA03 8000 0000 6080 1016 7519\n' > "$M/in.txt"
bash scripts/mask.sh mask "$M/in.txt" "$M/masked.txt" >/dev/null
grep -Eq 'example\.com|أحمد|Acme|1012345672|123 4567|1111 1111 1111 1111|7519' "$M/masked.txt" && { echo "mask.sh left personal data"; exit 1; }
grep -q 'Order: 1012345678' "$M/masked.txt" || { echo "mask.sh masked a number that fails the ID check"; exit 1; }
grep -q 'Ref: 4111 1111 1111 1112' "$M/masked.txt" || { echo "mask.sh masked a number that fails the card check"; exit 1; }
grep -q 'Office: +966 11 000 0000' "$M/masked.txt" || { echo "mask.sh ignored .mask-allow"; exit 1; }
bash scripts/mask.sh unmask "$M/masked.txt" "$M/back.txt" >/dev/null
cmp -s "$M/in.txt" "$M/back.txt" || { echo "mask.sh round trip changed the text"; exit 1; }
printf 'Contact Mr. John Smith or المهندس خالد العتيبي about it.\n' > "$M/s.txt"
bash scripts/mask.sh suggest "$M/s.txt" | grep -q 'John Smith' && bash scripts/mask.sh suggest "$M/s.txt" | grep -q 'خالد العتيبي' || { echo "mask.sh suggest missed a name"; exit 1; }
bash scripts/mask.sh check "$M/in.txt" | grep -q '^Would mask' || { echo "mask.sh check failed"; exit 1; }
if $PY -c "import PIL, pytesseract" >/dev/null 2>&1 && { command -v tesseract >/dev/null || [ -x "/c/Program Files/Tesseract-OCR/tesseract.exe" ]; }; then
  $PY -c "from PIL import Image,ImageDraw,ImageFont;import sys;i=Image.new('RGB',(900,120),'white');d=ImageDraw.Draw(i);f=ImageFont.load_default(size=32) if hasattr(ImageFont,'load_default') else None;d.text((20,40),'Contact: ahmed.h@example.com',fill='black',font=f);i.save(sys.argv[1])" "$M/shot.png"
  bash scripts/mask.sh mask "$M/shot.png" "$M/shot-masked.png" | grep -q 'EMAIL 1' || { echo "mask.sh image masking missed the email"; exit 1; }
else echo "(image masking test skipped: Tesseract not installed)"; fi
unset TH_MASK_MAP TH_MASK_TERMS TH_MASK_ALLOW
$PY -m py_compile scripts/lib/mask.py
# launcher: maps a short name to scripts/<name>.sh and lists scripts when called bare
bash scripts/hive.sh >/dev/null 2>&1 && { echo "hive.sh with no arguments should fail"; exit 1; }
bash scripts/hive.sh | grep -q "stage" || { echo "hive.sh does not list the scripts"; exit 1; }
bash scripts/hive.sh gen-user | grep -q "@example.com" || { echo "hive.sh did not run gen-user"; exit 1; }
bash scripts/hive.sh nope >/dev/null 2>&1 && { echo "hive.sh accepted an unknown script"; exit 1; }
# docs: every local link points to a file that exists; every script has a one-line description on line 2
$PY - <<'PY' || exit 1
import re, os, glob, sys
bad = []
for doc in ["README.md", "QUICKSTART.md", "CHANGELOG.md"] + glob.glob("docs/*.md"):
    for link in re.findall(r"\]\(([^)#]+)\)", open(doc, encoding="utf-8").read()):
        if "://" in link: continue
        if not os.path.exists(os.path.join(os.path.dirname(doc), link)): bad.append(f"{doc}: broken link {link}")
for s in glob.glob("scripts/*.sh"):
    l2 = open(s, encoding="utf-8").read().split("\n")[1]
    if not l2.startswith("# ") or l2.startswith("# Usage"): bad.append(f"{s}: line 2 must be a one-line description")
if bad: print("\n".join(bad)); sys.exit(1)
PY
[ -s VERSION ] && grep -q "## $(cat VERSION)" CHANGELOG.md || { echo "VERSION has no CHANGELOG.md entry"; exit 1; }
echo "SELFTEST PASS"
