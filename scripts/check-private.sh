#!/usr/bin/env bash
# Checks that no private name (from the git-ignored .private-names file) appears in files git would publish.
# Usage: bash scripts/check-private.sh        exit 1 and the matching lines if a name is found; exit 0 if clean or no list exists
# .private-names: one name per line (lines starting with # are ignored), matched without regard to case.
cd "$(dirname "$0")/.." || exit 1
. scripts/_py.sh
[ -f .private-names ] || { echo "PRIVATE CHECK SKIPPED: no .private-names file (one private name per line, git-ignored)"; exit 0; }
git ls-files -co --exclude-standard -z | $PY -c '
import sys
names = [l.strip() for l in open(".private-names", encoding="utf-8-sig") if l.strip() and not l.startswith("#")]
if not names: print("PRIVATE CHECK SKIPPED: .private-names is empty"); sys.exit(0)
files = [f for f in sys.stdin.buffer.read().decode("utf-8").split("\0") if f and f != ".private-names"]
low, hits = [n.lower() for n in names], []
for f in files:
    try: data = open(f, "rb").read()
    except OSError: continue
    if b"\0" in data[:4096]: continue  # binary
    for i, line in enumerate(data.decode("utf-8", "replace").splitlines(), 1):
        if any(n in line.lower() for n in low): hits.append(f"{f}:{i}: {line.strip()[:160]}")
if hits:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("PRIVATE CHECK FAIL: private names found in files that would be published:"); print("\n".join(hits[:50])); sys.exit(1)
print(f"PRIVATE CHECK PASS ({len(names)} names, {len(files)} files)")
'
