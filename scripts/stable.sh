#!/usr/bin/env bash
# Usage: bash scripts/stable.sh mobile|api|web <module> [runs=3]
#        bash scripts/stable.sh --from <dir-with-one-junit-xml-per-run> [out-dir]
# Runs the module N times in a row. Every case ID that passed in ALL runs gets reports/stable-<ID>.txt
# (gate.sh needs it for "Done"). A case that failed any run loses its old stable file. Exit 1 if any case is not stable.
. "$(dirname "$0")/_py.sh"
if [ "$1" = "--from" ]; then
  RUNS="${2:?dir with junit xml files}"; OUT="${3:-reports}"; N=0
else
  K="${1:?mobile|api|web}"; MOD="${2:?module}"; N="${3:-3}"; OUT=reports; RUNS=$(mktemp -d)
  [ -f "$(dirname "$0")/run-$K.sh" ] || { echo "Unknown kind: $K (mobile|api|web)" >&2; exit 1; }
  for i in $(seq 1 "$N"); do
    echo "== run $i/$N"; rm -f "reports/$K-$MOD.xml"
    bash "$(dirname "$0")/run-$K.sh" "$MOD" >/dev/null 2>&1 || true
    [ -f "reports/$K-$MOD.xml" ] && cp "reports/$K-$MOD.xml" "$RUNS/run-$i.xml"
  done
fi
mkdir -p "$OUT"
$PY - "$RUNS" "$OUT" "$N" <<'PY'
import sys, glob, re, os, time, xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d, out, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
files = sorted(glob.glob(os.path.join(d, "*.xml")))
n = n or len(files)
ID = re.compile(r"TC-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}")
passes, seen = {}, set()
for f in files:
    run = {}
    try: root = ET.parse(f).getroot()
    except Exception: continue
    for s in root.iter("testsuite"):
        for tc in s.findall("testcase"):
            failed = any(tc.find(k) is not None for k in ("failure", "error", "skipped"))
            text = " ".join((s.get("name") or "", tc.get("classname") or "", tc.get("name") or ""))
            for i in set(ID.findall(text)): run[i] = run.get(i, True) and not failed
    for i, ok in run.items():
        seen.add(i); passes[i] = passes.get(i, 0) + (1 if ok else 0)
stable = sorted(i for i in seen if n and passes[i] == n)
flaky = sorted(seen - set(stable))
stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
for i in stable: open(os.path.join(out, f"stable-{i}.txt"), "w", encoding="utf-8").write(f"PASS {n}/{n} runs in a row, {stamp}\n")
for i in flaky:
    p = os.path.join(out, f"stable-{i}.txt")
    if os.path.exists(p): os.remove(p)
print("STABLE (%d/%d runs): %s" % (n, n, ", ".join(stable) or "none"))
if flaky: print("NOT STABLE: " + ", ".join("%s (%d/%d)" % (i, passes[i], n) for i in flaky))
if not seen: print("No case IDs found in the results (%d of %d result files). Name flows/requests with the TC-ID." % (len(files), n))
sys.exit(0 if stable and not flaky else 1)
PY
