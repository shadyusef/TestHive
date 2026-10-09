#!/usr/bin/env bash
# Usage: bash scripts/gate.sh [csv]   Definition-of-done check. Exit 1 on any problem.
CSV="${1:-test-cases/TestCases.csv}"
python3 - "$CSV" <<'PY'
import sys, csv, re, os
p = sys.argv[1]; bad = []
if not os.path.exists(p): print("FAIL: missing " + p); sys.exit(1)
rows = list(csv.DictReader(open(p, encoding="utf-8")))
seen = set()
for r in rows:
    i = r.get("ID", "")
    if not re.fullmatch(r"TC-[A-Z0-9]+-\d{3}", i): bad.append(f"{i or '?'}: bad ID format")
    if i in seen: bad.append(f"{i}: duplicate ID")
    seen.add(i)
    for c in ("Module", "Platform", "Title", "Priority", "Steps", "Expected Result", "Status"):
        if not (r.get(c) or "").strip(): bad.append(f"{i}: empty {c}")
    if (r.get("Automation") or "").strip().lower() == "yes":
        s = (r.get("Automation Spec") or "").strip()
        if not s or not os.path.exists(s): bad.append(f"{i}: automation spec missing: {s or 'empty'}")
    if (r.get("Status") or "") == "Done" and not os.path.exists(f"reports/stable-{i}.txt"):
        bad.append(f"{i}: Done without reports/stable-{i}.txt (3 passes in a row)")
print("GATE PASS (%d cases)" % len(rows) if not bad else "GATE FAIL\n" + "\n".join("- " + b for b in bad))
sys.exit(1 if bad else 0)
PY
