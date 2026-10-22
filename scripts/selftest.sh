#!/usr/bin/env bash
# Proves TestHive itself works on this machine (run it after setup and after every change).
# Usage: bash scripts/selftest.sh   Proves the template itself is healthy (includes the unit tests in tests/).
set -eE
# a failing line names itself (otherwise "set -e" exits silently, e.g. inside VAR=$(...))
trap 'echo "SELFTEST FAIL at scripts/selftest.sh line $LINENO: $BASH_COMMAND" >&2' ERR
TROOT=$(mktemp -d)  # every temporary folder lives here and goes at the end, after any Studio started here has closed
cleanup() {
  trap - ERR; cd /; for p in $(jobs -p); do for i in $(seq 1 30); do kill -0 "$p" 2>/dev/null || break; sleep 0.5; done; kill "$p" 2>/dev/null || true; done
  for i in 1 2 3 4 5; do rm -rf "$TROOT" 2>/dev/null; [ -d "$TROOT" ] || break; sleep 1; done
}
trap cleanup EXIT
tmpd() { mktemp -d "$TROOT/t.XXXXXX"; }
. scripts/_py.sh
for f in scripts/*.sh; do bash -n "$f"; done
bash scripts/setup.sh --help >/dev/null
for f in api/collections/*.json api/environments/*.json .claude/settings.json web/package.json; do $PY -c "import json,sys;json.load(open(sys.argv[1], encoding='utf-8'))" "$f"; done
# unit tests of the Python libraries and Studio's API (tests/; each test uses its own temporary project)
U=$(TH_BASH="$(cygpath -w "$BASH" 2>/dev/null || echo "$BASH")" $PY -m unittest discover -s tests 2>&1) || { echo "$U" | grep -v ResourceWarning | tail -30; echo "unit tests failed"; exit 1; }
# gate: template passes; API-style IDs and Excel's BOM are accepted; bad IDs, bad priorities and unproven "Done" are rejected
bash scripts/gate.sh templates/TestCases.csv
G=$(tmpd)
sed 's/^TC-EXAMPLE-001/TC-EXAMPLE-API-001/' templates/TestCases.csv > "$G/api.csv"; bash scripts/gate.sh "$G/api.csv" >/dev/null
{ printf '\xef\xbb\xbf'; cat templates/TestCases.csv; } > "$G/bom.csv"; bash scripts/gate.sh "$G/bom.csv" >/dev/null
sed 's/^TC-EXAMPLE-001/EXAMPLE-1/' templates/TestCases.csv > "$G/id.csv"; ! bash scripts/gate.sh "$G/id.csv" >/dev/null
sed 's/,P0,/,High,/' templates/TestCases.csv > "$G/pr.csv"; ! bash scripts/gate.sh "$G/pr.csv" >/dev/null
sed 's/,Draft$/,Done/' templates/TestCases.csv > "$G/done.csv"; ! bash scripts/gate.sh "$G/done.csv" >/dev/null
# intake
T0=$(tmpd); printf '## 1. Scope\n- Module: X\n- Platforms: [x] Android [ ] iOS\n## 2. Business rules\n1. Rule one\n## 4. Expected results\n| Situation | Expected |\n|---|---|\n| ok | fine |\n## 6. Priorities\n- P0: a\n' > "$T0/i.md"
bash scripts/check-intake.sh "$T0/i.md"
! bash scripts/check-intake.sh templates/MODULE_INTAKE.md >/dev/null
# digest
T=$(tmpd); mkdir -p "$T/r"
cat > "$T/r/a.xml" <<'X'
<testsuite><testcase classname="s" name="ok"/><testcase classname="s" name="bad"><failure message="boom"/></testcase></testsuite>
X
bash scripts/digest-failures.sh "$T/r" | grep -q "boom"
# stable: A passes 3 of 3, B fails once -> only A gets a stable file
S=$(tmpd); mkdir -p "$S/runs" "$S/out"; echo old > "$S/out/stable-TC-B-002.txt"
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
W=$(tmpd); export TH_STATE="$W/state.json"
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
R=$(tmpd); export TH_RUNS="$R/runs"; mkdir -p "$R/ev"; echo x > "$R/ev/TC-DEMO-002_fail.png"
echo '<testsuites><testsuite name="demo"><testcase name="TC-DEMO-001_ok" time="1.5"/><testcase name="TC-DEMO-002_fail"><failure message="Expected Welcome"/></testcase></testsuite></testsuites>' > "$R/j.xml"
bash scripts/collect-run.sh mobile demo --junit "$R/j.xml" --evidence "$R/ev" | grep -q "2 cases, 1 passed, 1 failed" || { echo "collect-run.sh totals are wrong"; exit 1; }
bash scripts/collect-run.sh mobile demo --junit "$R/j.xml" | grep -Eq "R-[0-9]{8}-02" || { echo "collect-run.sh run numbering is wrong"; exit 1; }
$PY -c "import json,sys,glob;r=json.load(open(sorted(glob.glob(sys.argv[1]+'/R-*-01/results.json'))[0],encoding='utf-8'));c=r['cases'][1];sys.exit(not(c['id']=='TC-DEMO-002' and c['status']=='failed' and len(c['evidence'])==1))" "$TH_RUNS" || { echo "collect-run.sh results.json is wrong"; exit 1; }
unset TH_RUNS
# masking: Arabic + English, round trip restores the original exactly
M=$(tmpd); export TH_MASK_MAP="$M/map.json" TH_MASK_TERMS="$M/terms" TH_MASK_ALLOW="$M/allow"
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
H_OUT=$(bash scripts/hive.sh 2>&1 || true); echo "$H_OUT" | grep -q "stage" || { echo "hive.sh does not list the scripts"; exit 1; }
H_OUT=$(bash scripts/hive.sh gen-user); echo "$H_OUT" | grep -q "@example.com" || { echo "hive.sh did not run gen-user"; exit 1; }
bash scripts/hive.sh nope >/dev/null 2>&1 && { echo "hive.sh accepted an unknown script"; exit 1; }
# phase 1: ingest, analysis registers, workbook round trip, approval gate + baseline, score, Android screen parser
A=$(tmpd); export TH_ANALYSIS="$A/analysis" TH_STATE="$A/state.json"
mkdir -p "$A/src"; cp demo/phase1/sources/openapi.yaml demo/phase1/sources/user-stories.docx "$A/src/"; printf 'R1 Full name is required.\n' > "$A/src/notes.txt"
(cd "$A" && mkdir -p requirements/sources && mv src requirements/sources/SIGNUP && TH_ANALYSIS="$A/analysis" bash "$OLDPWD/scripts/ingest.sh" SIGNUP) | grep -q "INGESTED 3 sources" || { echo "ingest.sh did not convert the sources"; exit 1; }
grep -q "minLength=6" "$A/analysis/sources-text/SIGNUP/openapi.yaml.md" && grep -q "US-2" "$A/analysis/sources-text/SIGNUP/user-stories.docx.md" || { echo "ingest.sh output is wrong"; exit 1; }
cat > "$TH_ANALYSIS/requirements.csv" <<'X'
ID,Module,Source,Section,Text,Type,Priority,Version,Status,Notes
REQ-DEMO-001,DEMO,prd R4,3,Password must be at least 8 characters,Business rule,P0,1,Draft,
REQ-DEMO-002,DEMO,openapi.yaml,signup,Password minLength 6,API,P0,1,Draft,
REQ-DEMO-003,DEMO,observed: web page 01,form,Resend is disabled for 30 seconds,UI,P2,1,Observed,
X
cat > "$TH_ANALYSIS/gaps.csv" <<'X'
ID,Module,Requirement,Kind,Severity,Question,Answer,Answered By,Status
GAP-DEMO-001,DEMO,REQ-DEMO-001;REQ-DEMO-002,Conflict,High,PRD says the password needs 8 characters and the API 6. Which is correct: 8 or 6?,,,Open
GAP-DEMO-002,DEMO,REQ-DEMO-003,To confirm,Low,The app waits 30 seconds before Resend. Is that intended?,,,Open
X
bash scripts/check-analysis.sh DEMO >/dev/null || { echo "check-analysis rejected valid registers"; exit 1; }
bash scripts/check-analysis.sh DEMO --for-approval >/dev/null && { echo "check-analysis allowed approval with a High gap open"; exit 1; }
sed 's/,Draft,$/,Ready,/' "$TH_ANALYSIS/requirements.csv" > "$A/bad.csv"; cp "$TH_ANALYSIS/requirements.csv" "$A/good.csv"; cp "$A/bad.csv" "$TH_ANALYSIS/requirements.csv"
bash scripts/check-analysis.sh DEMO >/dev/null && { echo "check-analysis accepted a bad Status"; exit 1; }; cp "$A/good.csv" "$TH_ANALYSIS/requirements.csv"
bash scripts/analysis-workbook.sh DEMO | grep -q "WORKBOOK" || { echo "analysis-workbook failed"; exit 1; }
$PY - "$TH_ANALYSIS/DEMO-analysis.xlsx" <<'PY'
import sys, openpyxl
wb = openpyxl.load_workbook(sys.argv[1]); ws = wb["Gaps"]
head = [c.value for c in ws[1]]; col = lambda h: head.index(h) + 1
ws.cell(2, col("Answer")).value = "8 characters"; ws.cell(2, col("Answered By")).value = "Product owner"
ws.cell(3, col("Answer")).value = "Yes, 30 seconds"; ws.cell(3, col("Answered By")).value = "Product owner"
r = ws.max_row + 1; ws.cell(r, col("Question")).value = "Is the password case-sensitive?"; ws.cell(r, col("Severity")).value = "Medium"; ws.cell(r, col("Kind")).value = "Missing"
wb.save(sys.argv[1])
PY
bash scripts/import-answers.sh DEMO | grep -q "2 gaps updated, 1 new" || { echo "import-answers did not read the workbook"; exit 1; }
grep -q "GAP-DEMO-003,DEMO,,Missing,Medium,Is the password case-sensitive" "$TH_ANALYSIS/gaps.csv" || { echo "import-answers did not add the new question"; exit 1; }
bash scripts/check-analysis.sh DEMO --for-approval >/dev/null && { echo "approval allowed with answered-but-unreviewed gaps"; exit 1; }
for f in "$TH_ANALYSIS/gaps.csv" "$TH_ANALYSIS/requirements.csv"; do sed 's/,Answered$/,Closed/; s/,Observed,$/,Confirmed,/' "$f" > "$f.tmp" && mv "$f.tmp" "$f"; done  # no sed -i: BSD sed (macOS) differs
bash scripts/stage.sh init DEMO >/dev/null; bash scripts/stage.sh start DEMO analysis >/dev/null; bash scripts/stage.sh submit DEMO analysis >/dev/null
S_OUT=$(bash scripts/stage.sh approve DEMO analysis --by tester); echo "$S_OUT" | grep -q "BASELINE DEMO v1" || { echo "approving analysis did not create the baseline: $S_OUT"; exit 1; }
[ -s "$TH_ANALYSIS/baseline/DEMO/v1/requirements.csv" ] && [ -s "$TH_ANALYSIS/baseline/DEMO/v1/meta.json" ] || { echo "baseline files missing"; exit 1; }
printf 'Key,Gap,Where,Keywords\nK1,Password conflict,x,password;8;6\nK2,Lockout,x,lock\n' > "$A/key.csv"
S_OUT=$(TH_SCORE_TARGET=50 bash scripts/score-analysis.sh DEMO "$A/key.csv"); echo "$S_OUT" | grep -q "found 1 of 2" || { echo "score-analysis counted wrong: $S_OUT"; exit 1; }
printf 'Key,Gap,Where,Keywords
K1,Lockout,x,lock
' > "$A/key2.csv"; printf 'GAP-DEMO-009,DEMO,,Missing,Low,Is the user blocked after 3 tries?,,,Open
' >> "$TH_ANALYSIS/gaps.csv"
S_OUT=$(TH_SCORE_TARGET=0 bash scripts/score-analysis.sh DEMO "$A/key2.csv"); echo "$S_OUT" | grep -q "found 0 of 1" || { echo "score-analysis matched inside a word (lock in blocked)"; exit 1; }
unset TH_ANALYSIS TH_STATE
$PY scripts/lib/uiscreen.py find demo/phase1/samples/android-signup.xml sign_up | grep -q "540 960" || { echo "uiscreen.py could not find the button"; exit 1; }
$PY scripts/lib/uiscreen.py summary demo/phase1/samples/android-signup.xml s | grep -q "input (password)" || { echo "uiscreen.py summary is wrong"; exit 1; }
# phase 2: design check (coverage, negatives, boundaries), risk priority, review workbook round trip, design gate + baseline, reopen + impact, score
A=$(tmpd); export TH_ANALYSIS="$A/analysis" TH_STATE="$A/state.json" TH_CASES="$A/tc"; mkdir -p "$TH_ANALYSIS" "$TH_CASES"
cat > "$TH_ANALYSIS/requirements.csv" <<'X'
ID,Module,Source,Section,Text,Type,Priority,Version,Status,Notes
REQ-DEMO-001,DEMO,prd R4,3,Password must be at least 8 characters,Business rule,P0,1,Confirmed,
REQ-DEMO-002,DEMO,prd R5,3,The Help link opens the help page,UI,P2,1,Confirmed,
REQ-DEMO-003,DEMO,prd R6,3,Old rule,Functional,P1,2,Removed,
X
printf 'ID,Module,Requirement,Kind,Severity,Question,Answer,Answered By,Status\nGAP-DEMO-001,DEMO,REQ-DEMO-002,Missing,Medium,Which help page does the link open?,,,Open\n' > "$TH_ANALYSIS/gaps.csv"
printf 'ID,Module,Requirement,Request,Requested By,Status,Response\n' > "$TH_CASES/requests.csv"
bash scripts/stage.sh init DEMO >/dev/null; bash scripts/stage.sh start DEMO analysis >/dev/null; bash scripts/stage.sh submit DEMO analysis >/dev/null; bash scripts/stage.sh approve DEMO analysis --by tester >/dev/null
H='ID,Module,Platform,Title,Priority,Type,Requirements,Technique,Risk,Tags,Preconditions,Steps,Expected Result,Test Data,Assumption,Origin,Review,Review Comment,Automation,Automation Spec,Status'
C1='TC-DEMO-001,DEMO,Web,Password of 8 characters is accepted,,Positive,REQ-DEMO-001,Boundary,Medium,smoke;regression,On sign-up,1. Enter Abcdefg1; 2. Submit,The OTP page opens,Abcdefg1,,Designed,,,Candidate,,Draft'
C2='TC-DEMO-002,DEMO,Web,Password of 7 characters is refused,,Negative,REQ-DEMO-001,Boundary,High,regression,On sign-up,1. Enter Abcdef1; 2. Submit,Message: Password must be at least 8 characters,Abcdef1,,Designed,,,Candidate,,Draft'
C3='TC-DEMO-003,DEMO,Web,Help link opens the help page,,Positive,REQ-DEMO-002,Use case,Low,regression,On sign-up,1. Tap Help,The help page opens,,GAP-DEMO-001,Designed,,,Candidate,,Draft'
printf '%s\n' "$H" "$C1" > "$TH_CASES/TestCases.csv"
D_OUT=$(bash scripts/check-design.sh DEMO --set-priority || true); echo "$D_OUT" | grep -q "REQ-DEMO-001: P0 business rule with no Negative case" && echo "$D_OUT" | grep -q "REQ-DEMO-002: no test case" || { echo "check-design missed a coverage gap: $D_OUT"; exit 1; }
printf '%s\n' "$H" "$C1" "$C2" "$C3" > "$TH_CASES/TestCases.csv"
D_OUT=$(bash scripts/check-design.sh DEMO --set-priority) || { echo "check-design rejected a complete design: $D_OUT"; exit 1; }
grep -q "^TC-DEMO-001,DEMO,Web,[^,]*,P1," "$TH_CASES/TestCases.csv" && grep -q "^TC-DEMO-003,DEMO,Web,[^,]*,P3," "$TH_CASES/TestCases.csv" || { echo "risk rule set the wrong priority"; exit 1; }
cp "$TH_CASES/TestCases.csv" "$A/good.csv"
sed 's/,smoke;regression,/,smoke;nightly,/' "$A/good.csv" > "$TH_CASES/TestCases.csv"; bash scripts/check-design.sh DEMO >/dev/null && { echo "check-design accepted an unknown tag"; exit 1; }
sed 's/^\(TC-DEMO-003,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,\)REQ-DEMO-002/\1REQ-DEMO-003/' "$A/good.csv" > "$TH_CASES/TestCases.csv"; bash scripts/check-design.sh DEMO | grep -q "Removed in baseline" || { echo "check-design accepted a case linked to a removed requirement"; exit 1; }
cp "$A/good.csv" "$TH_CASES/TestCases.csv"
bash scripts/design-workbook.sh DEMO | grep -q "WORKBOOK" || { echo "design-workbook failed"; exit 1; }
review() { $PY - "$TH_CASES/DEMO-design.xlsx" "$1" <<'PY'
import sys, openpyxl
wb = openpyxl.load_workbook(sys.argv[1]); ws = wb["Cases"]; head = [c.value for c in ws[1]]; col = lambda h: head.index(h) + 1
ws.cell(2, col("Review")).value = "Accepted"; ws.cell(3, col("Review")).value = "Change"
if sys.argv[2] == "ok": ws.cell(3, col("Review Comment")).value = "Also check the message in Arabic"
r = ws.max_row + 1; ws.cell(r, col("Title")).value = "Password with spaces"; ws.cell(r, col("Steps")).value = "1. Enter ' Abcdefg1 '"; ws.cell(r, col("Expected Result")).value = "Spaces are kept"
rq = wb["Requests"]; h = [c.value for c in rq[1]]; rq.cell(2, h.index("Request") + 1).value = "Add a case for a pasted password"; rq.cell(2, h.index("Requested By") + 1).value = "Sara"
wb.save(sys.argv[1])
PY
}
review bad; bash scripts/import-review.sh DEMO | grep -q "IMPORT REFUSED" && cmp -s "$A/good.csv" "$TH_CASES/TestCases.csv" || { echo "import-review accepted a Change without a comment, or changed files"; exit 1; }
bash scripts/design-workbook.sh DEMO >/dev/null; review ok
I_OUT=$(bash scripts/import-review.sh DEMO); echo "$I_OUT" | grep -q "1 accepted, 1 to change, 0 to remove, 0 edited in Excel, 1 new cases, 1 new requests" || { echo "import-review counted wrong: $I_OUT"; exit 1; }
grep -q "^TC-DEMO-004,DEMO,,Password with spaces,.*,Human,Accepted," "$TH_CASES/TestCases.csv" && grep -q "^ASK-DEMO-001,DEMO,,Add a case for a pasted password,Sara,Open," "$TH_CASES/requests.csv" || { echo "import-review did not add the new case or request"; exit 1; }
bash scripts/stage.sh start DEMO design >/dev/null; bash scripts/stage.sh submit DEMO design >/dev/null && { echo "design submitted with an unhandled review"; exit 1; }
$PY - "$TH_CASES" <<'PY'
import sys, csv, os
p = os.path.join(sys.argv[1], "TestCases.csv"); rows = list(csv.DictReader(open(p, encoding="utf-8")))
for r in rows:
    if r["ID"] == "TC-DEMO-002": r["Review"] = "Updated"
    if r["ID"] == "TC-DEMO-004": r.update({"Platform": "Web", "Priority": "P1", "Type": "Positive", "Requirements": "REQ-DEMO-001", "Technique": "Error guessing", "Risk": "Medium", "Tags": "regression", "Expected Result": "The OTP page opens; the password is saved with its spaces"})
w = csv.DictWriter(open(p, "w", encoding="utf-8", newline=""), rows[0].keys(), lineterminator="\n"); w.writeheader(); w.writerows(rows)
q = os.path.join(sys.argv[1], "requests.csv"); txt = open(q, encoding="utf-8").read().replace(",Sara,Open,", ",Sara,Done,TC-DEMO-004 covers it")
open(q, "w", encoding="utf-8", newline="").write(txt)
PY
bash scripts/design-workbook.sh DEMO >/dev/null; I_OUT=$(bash scripts/import-review.sh DEMO); echo "$I_OUT" | grep -q "0 accepted, 0 to change, 0 to remove, 0 edited in Excel, 0 new cases, 0 new requests" || { echo "re-importing an untouched workbook changed something: $I_OUT"; exit 1; }
bash scripts/check-design.sh DEMO --for-approval >/dev/null || { echo "check-design refused a handled review: $(bash scripts/check-design.sh DEMO --for-approval)"; exit 1; }
bash scripts/stage.sh submit DEMO design >/dev/null || { echo "stage refused a ready design"; exit 1; }
S_OUT=$(bash scripts/stage.sh approve DEMO design --by tester); echo "$S_OUT" | grep -q "DESIGN BASELINE DEMO v1: 4 active cases (from analysis v1)" || { echo "approving design did not create the baseline: $S_OUT"; exit 1; }
bash scripts/stage.sh reopen DEMO analysis --by tester --comment "8 becomes 10" | grep -q "design back to in progress" || { echo "reopen did not send design back"; exit 1; }
sed 's/at least 8 characters,Business rule,P0,1,/at least 10 characters,Business rule,P0,2,/' "$TH_ANALYSIS/requirements.csv" > "$A/r.csv" && mv "$A/r.csv" "$TH_ANALYSIS/requirements.csv"
bash scripts/stage.sh submit DEMO design >/dev/null && { echo "design submitted while the analysis is reopened"; exit 1; }
bash scripts/stage.sh submit DEMO analysis >/dev/null; bash scripts/stage.sh approve DEMO analysis --by tester >/dev/null
I_OUT=$(bash scripts/design-impact.sh DEMO --apply); echo "$I_OUT" | grep -q "analysis v1 -> v2: 1 changed, 0 removed, 0 new requirements; 3 cases affected" || { echo "design-impact is wrong: $I_OUT"; exit 1; }
bash scripts/check-design.sh DEMO --for-approval | grep -q "TC-DEMO-001: Needs update" || { echo "Needs update did not block approval"; exit 1; }
printf 'Key,Condition,Requirement,Keywords\nK1,Seven,REQ-DEMO-001,password;7 char\nK2,Seventeen,,password;17\nK3,Help,REQ-DEMO-002,help\n' > "$A/key.csv"
S_OUT=$(TH_SCORE_TARGET=60 bash scripts/score-design.sh DEMO "$A/key.csv"); echo "$S_OUT" | grep -q "2 of 3 required test conditions" || { echo "score-design counted wrong (7 must not match 17): $S_OUT"; exit 1; }
# phase 2b: Studio on the same fixture (token, host check, JSON only, stale page refused, answer saved, gate kept)
bash scripts/studio.sh --no-browser --port 0 > "$A/studio.log" 2>&1 &
for i in $(seq 1 150); do grep -q "^STUDIO " "$A/studio.log" 2>/dev/null && break; sleep 0.2; done
U=$(sed -n 's/^STUDIO //p' "$A/studio.log"); [ -n "$U" ] || { cat "$A/studio.log"; echo "studio did not start"; exit 1; }
$PY - "$U" <<'PY' || exit 1
import sys, json, http.client
from urllib.parse import urlparse, parse_qs
u = urlparse(sys.argv[1]); tok = parse_qs(u.query)["t"][0]; bad = []
def call(path, body=None, token=tok, host=None, ctype="application/json"):
    c = http.client.HTTPConnection(u.hostname, u.port, timeout=30)
    h = {"X-TestHive-Token": token, "Host": host or u.netloc}
    if body is not None: h["Content-Type"] = ctype
    c.request("GET" if body is None else "POST", path, body=None if body is None else (body if isinstance(body, str) else json.dumps(body)), headers=h)
    r = c.getresponse(); raw = r.read()
    try: return r.status, json.loads(raw)
    except ValueError: return r.status, {}
s, o = call("/api/overview"); s == 200 and o["modules"][0]["module"] == "DEMO" or bad.append(f"overview {s}")
call("/api/overview", token="x")[0] == 403 or bad.append("no token accepted")
call("/api/overview", host="evil.example:80")[0] == 403 or bad.append("foreign Host accepted")
s, m = call("/api/module?m=DEMO"); s == 200 and m["design"]["baseline"] == "v2" or bad.append(f"module {s}")
call("/api/answers", "module=DEMO", ctype="application/x-www-form-urlencoded")[0] == 415 or bad.append("form post accepted")
row = {"ID": "GAP-DEMO-001", "Answer": "The /help page", "Answered By": "tester", "Status": "Answered"}
s, r = call("/api/answers", {"module": "DEMO", "version": m["analysis"]["version"], "rows": [row]}); s == 200 or bad.append(f"answer not saved {r}")
call("/api/answers", {"module": "DEMO", "version": m["analysis"]["version"], "rows": [row]})[0] == 409 or bad.append("stale page accepted")
s, r = call("/api/stage", {"module": "DEMO", "stage": "design", "action": "approve", "by": "tester"}); s == 400 or bad.append("approve of an unsubmitted design accepted")
call("/api/shutdown", {})
if bad: print("studio: " + "; ".join(bad)); sys.exit(1)
PY
grep -q "^GAP-DEMO-001,DEMO,REQ-DEMO-002,Missing,Medium,Which help page does the link open?,The /help page,tester,Answered" "$TH_ANALYSIS/gaps.csv" || { echo "studio did not write the answer"; exit 1; }
unset TH_ANALYSIS TH_STATE TH_CASES
# phase 2c: Studio from an empty project (setup, module, uploads and refusals, masking preview, read, readiness), in a temporary copy
# Claude Code hooks: the edit check catches broken files, the guard refuses direct edits of the approval records
H=$(tmpd); HW=$(cygpath -m "$H" 2>/dev/null || echo "$H")
printf 'echo "unclosed\n' > "$H/bad.sh"; printf 'x = (\n' > "$H/bad.py"; printf 'echo ok\n' > "$H/good.sh"; printf 'x = 1%b\n' '\r' > "$H/cr.py"
P=$(cygpath -m "$PWD" 2>/dev/null || echo "$PWD")   # Claude Code passes native paths; so does this test
hook() { local r=0; printf '{"tool_input":{"file_path":"%s"}}' "$2" | CLAUDE_PROJECT_DIR="$P" bash scripts/hooks/run.sh "$1" 2>/dev/null || r=$?; echo $r; }
HK="$(hook check_edit "$HW/bad.sh")$(hook check_edit "$HW/bad.py")$(hook check_edit "$HW/cr.py")$(hook check_edit "$HW/good.sh")"; [ "$HK" = "2220" ] || { echo "the edit-check hook is wrong: exit codes $HK for bad.sh bad.py cr.py good.sh (expected 2220)"; printf '{"tool_input":{"file_path":"%s"}}' "$HW/good.sh" | bash scripts/hooks/run.sh check_edit; exit 1; }
[ "$(hook guard_records "$P/workflow/APPROVALS.md")$(hook guard_records "$P/test-cases/baseline/X/v1/TestCases.csv")$(hook guard_records "$P/analysis/gaps.csv")" = "220" ] || { echo "the approval-records guard is wrong"; exit 1; }
bash scripts/check-private.sh >/dev/null || { bash scripts/check-private.sh; exit 1; }
PR=$(tmpd); mkdir -p "$PR/scripts"; cp scripts/check-private.sh scripts/_py.sh "$PR/scripts/"   # a planted name must fail
(cd "$PR" && git init -q && printf 'Acme-Secret\n' > .private-names && printf 'see acme-secret here\n' > notes.txt && printf '.private-names\n' > .gitignore)
bash "$PR/scripts/check-private.sh" >/dev/null 2>&1 && { echo "check-private missed a planted private name"; exit 1; }
# phase 2d: Run buttons with the recorded agents (jobs, progress, Stop, lock, every step to an approved design)
D_OUT=$(bash demo/phase2d/run.sh --check 2>&1 || true); echo "$D_OUT" | grep -q "STUDIO RUN CHECK PASS" || { echo "$D_OUT" | tail -25; echo "studio run check failed"; exit 1; }
C_OUT=$(bash demo/phase2c/run.sh --check 2>&1 || true); echo "$C_OUT" | grep -q "STUDIO INTAKE CHECK PASS" || { echo "$C_OUT" | tail -25; echo "studio intake check failed"; exit 1; }
$PY -m py_compile scripts/lib/analysis.py scripts/lib/ingest.py scripts/lib/uiscreen.py scripts/lib/design.py scripts/lib/studio.py scripts/lib/intake.py scripts/lib/jobs.py
# Windows: every PowerShell script must parse (CI checks this too, but catch it before pushing)
if command -v powershell.exe >/dev/null 2>&1; then
  for f in scripts/*.ps1; do
    r=$(powershell.exe -NoProfile -Command "\$e=\$null; [void][System.Management.Automation.Language.Parser]::ParseFile('$(cygpath -w "$PWD/$f")',[ref]\$null,[ref]\$e); if(\$e){\$e[0].Extent.StartLineNumber.ToString() + ': ' + \$e[0].Message}else{'ok'}" | tr -d '[:cntrl:]')
    [ "$r" = ok ] || { echo "$f does not parse: line $r"; exit 1; }
  done
fi
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
