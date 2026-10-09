#!/usr/bin/env bash
# Usage: bash scripts/digest-failures.sh [reports-dir]
# Trims junit XML (Maestro/Newman) to failing tests only -> reports/digest.md. Triage reads only this file.
D="${1:-reports}"
python3 - "$D" <<'PY'
import sys, glob, xml.etree.ElementTree as ET
d = sys.argv[1]; out = []; total = 0
for f in sorted(glob.glob(d + "/*.xml")):
    try: root = ET.parse(f).getroot()
    except Exception as e: out.append(f"- {f}: unreadable ({e})"); continue
    for tc in root.iter("testcase"):
        total += 1
        for k in ("failure", "error"):
            n = tc.find(k)
            if n is not None:
                msg = (n.get("message") or n.text or "").strip().replace("\n", " ")[:200]
                out.append(f"- {tc.get('classname','')}/{tc.get('name','')} [{f}]: {msg}")
body = "ALL PASS (%d tests)" % total if not out else "# Failures (%d of %d)\n" % (len(out), total) + "\n".join(out)
open(d + "/digest.md", "w").write(body + "\n"); print(body)
PY
