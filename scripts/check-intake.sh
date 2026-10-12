#!/usr/bin/env bash
# Usage: bash scripts/check-intake.sh <intake.md> [TestCases.csv]
# Fails if required sections are unfilled; with a CSV, lists business rules no test case references as [R<n>].
. "$(dirname "$0")/_py.sh"
$PY - "$@" <<'PY'
import sys, re, csv
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = sys.argv[1]; txt = open(p, encoding="utf-8-sig").read()
secs = {m.group(1): m.group(2) for m in re.finditer(r"^## (\d+)\. [^\n]*\n(.*?)(?=^## |\Z)", txt, re.S | re.M)}
bad = []
for n, name in (("1", "Scope"), ("2", "Business rules"), ("4", "Expected results"), ("6", "Priorities")):
    body = secs.get(n, "")
    lines = [l for l in body.splitlines() if l.strip() and not l.startswith("|---") and "Situation" not in l]
    if not lines or all(re.search(r"<[^>]*>", l) for l in lines): bad.append(f"section {n} ({name}) is empty or still a placeholder")
if re.search(r"^- Platforms:", secs.get("1", ""), re.M) and not re.search(r"^- Platforms:.*\[[xX]\]", secs.get("1", ""), re.M):
    bad.append("section 1 (Scope): no platform ticked")
rules = re.findall(r"^\s*(\d+)\.\s+(?!<)\S", secs.get("2", ""), re.M)
if len(sys.argv) > 2:
    used = set()
    for r in csv.DictReader(open(sys.argv[2], encoding="utf-8-sig", newline="")): used |= set(re.findall(r"\[R(\d+)\]", r.get("Title") or ""))
    miss = [r for r in rules if r not in used]
    if miss: bad.append("rules without a test case: " + ", ".join("R" + m for m in miss))
print("INTAKE OK (%d rules)" % len(rules) if not bad else "INTAKE INCOMPLETE\n" + "\n".join("- " + b for b in bad))
sys.exit(1 if bad else 0)
PY
