#!/usr/bin/env bash
# Usage: bash scripts/gate.sh [csv]   Definition-of-done check. Exit 1 on any problem.
# Checks: ID format and uniqueness, required fields, priority P0-P3, automation spec exists.
# A "Done" case also needs reports/stable-<ID>.txt (written by scripts/stable.sh) and a spec with a real assertion.
CSV="${1:-test-cases/TestCases.csv}"
. "$(dirname "$0")/_py.sh"
$PY - "$CSV" <<'PY'
import sys, csv, re, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = sys.argv[1]; bad = []
if not os.path.exists(p): print("FAIL: missing " + p); sys.exit(1)
rows = list(csv.DictReader(open(p, encoding="utf-8-sig", newline="")))
ASSERT = {".yaml": r"^\s*-\s*(assert\w*|extendedWaitUntil)", ".yml": r"^\s*-\s*(assert\w*|extendedWaitUntil)",
          ".ts": r"expect\(", ".js": r"expect\(", ".json": r"pm\.(test|expect)"}
seen = set()
for r in rows:
    i = (r.get("ID") or "").strip()
    if not re.fullmatch(r"TC-[A-Z0-9]+(-[A-Z0-9]+)*-\d{3}", i): bad.append(f"{i or '?'}: bad ID format")
    if i in seen: bad.append(f"{i}: duplicate ID")
    seen.add(i)
    for c in ("Module", "Platform", "Title", "Priority", "Steps", "Expected Result", "Status"):
        if not (r.get(c) or "").strip(): bad.append(f"{i}: empty {c}")
    pr = (r.get("Priority") or "").strip()
    if pr and not re.fullmatch(r"P[0-3]", pr): bad.append(f"{i}: priority must be P0-P3, got {pr}")
    auto = (r.get("Automation") or "").strip().lower() == "yes"
    s = (r.get("Automation Spec") or "").strip()
    spec_ok = bool(s) and os.path.exists(s) and os.path.getsize(s) > 0
    if auto and not spec_ok: bad.append(f"{i}: automation spec missing or empty: {s or 'empty'}")
    if (r.get("Status") or "").strip().lower() == "done":
        st = f"reports/stable-{i}.txt"
        if not os.path.exists(st) or os.path.getsize(st) == 0:
            bad.append(f"{i}: Done without {st} (3 passes in a row; run scripts/stable.sh)")
        if auto and spec_ok and os.path.isfile(s):
            txt = open(s, encoding="utf-8", errors="replace").read()
            pat = ASSERT.get(os.path.splitext(s)[1].lower())
            if pat and not re.search(pat, txt, re.M): bad.append(f"{i}: Done but spec has no assertion: {s}")
            if re.search(r":\s*[\"']\.\*[\"']", txt): bad.append(f"{i}: Done but spec still has the placeholder \".*\" check: {s}")
print("GATE PASS (%d cases)" % len(rows) if not bad else "GATE FAIL\n" + "\n".join("- " + b for b in bad))
sys.exit(1 if bad else 0)
PY
