#!/usr/bin/env bash
# Stores one test run in runs/ in a common format, whatever the tool (Maestro, Newman, Playwright).
# Usage: bash scripts/collect-run.sh <mobile|api|web> <module> [--env <env>] [--platform <android|ios|web|api>]
#                                     [--junit <file>] [--evidence <dir>]
#   --junit     default: reports/<kind>-<module>.xml (what the run-*.sh scripts write)
#   --evidence  folder of screenshots, videos and logs to keep with the run; files are linked to a case by its TC-ID
# Creates runs/<RUN-ID>/ (RUN-ID = R-<yyyymmdd>-<nn>) with meta.json, results.json, junit.xml and evidence/,
# and adds one line to runs/index.csv. The format is described in docs/FORMATS.md.
. "$(dirname "$0")/_py.sh"
$PY - "$@" <<'PY'
import sys, os, re, json, glob, time, shutil, platform, csv, xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
def die(m): print(m); sys.exit(1)
a = sys.argv[1:]
if len(a) < 2 or a[0] not in ("mobile", "api", "web"): die("Usage: collect-run.sh <mobile|api|web> <module> [--env E] [--platform P] [--junit F] [--evidence D]")
kind, mod, opt, i = a[0], a[1], {}, 2
while i < len(a):
    if a[i] in ("--env", "--platform", "--junit", "--evidence") and i + 1 < len(a): opt[a[i][2:]] = a[i + 1]; i += 2
    else: die(f"Unknown or incomplete option: {a[i]}")
junit = opt.get("junit") or f"reports/{kind}-{mod}.xml"
if not os.path.isfile(junit): die(f"No results file: {junit}. Run the tests first, or pass --junit.")
try: root = ET.parse(junit).getroot()
except Exception as e: die(f"Unreadable results file {junit}: {e}")

ID = re.compile(r"TC-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}")
cases = []
for s in root.iter("testsuite"):
    for tc in s.findall("testcase"):
        text = " ".join(x for x in (s.get("name"), tc.get("classname"), tc.get("name")) if x)
        m = ID.search(text); status, msg = "passed", ""
        for tag, st in (("failure", "failed"), ("error", "error"), ("skipped", "skipped")):
            n = tc.find(tag)
            if n is not None: status, msg = st, (n.get("message") or n.text or "").strip()[:500]; break
        try: dur = float(tc.get("time") or 0)
        except ValueError: dur = 0.0
        cases.append({"id": m.group(0) if m else None, "name": tc.get("name"), "suite": s.get("name"),
                      "status": status, "duration_s": dur, "message": msg, "evidence": []})

base = os.environ.get("TH_RUNS", "runs"); os.makedirs(base, exist_ok=True)
day = time.strftime("%Y%m%d", time.gmtime())
seq = [int(p.rsplit("-", 1)[1]) for p in (os.path.basename(x) for x in glob.glob(os.path.join(base, f"R-{day}-*"))) if p.rsplit("-", 1)[1].isdigit()]
rid = f"R-{day}-{max(seq, default=0) + 1:02d}"
rdir = os.path.join(base, rid); os.makedirs(rdir)
shutil.copyfile(junit, os.path.join(rdir, "junit.xml"))
ev = opt.get("evidence")
if ev:
    if not os.path.isdir(ev): die(f"Evidence folder not found: {ev}")
    shutil.copytree(ev, os.path.join(rdir, "evidence"))
    files = [os.path.relpath(p, rdir).replace(os.sep, "/") for p in glob.glob(os.path.join(rdir, "evidence", "**", "*"), recursive=True) if os.path.isfile(p)]
    for c in cases:
        if c["id"]: c["evidence"] = [f for f in files if c["id"].lower() in f.lower()]
else:
    os.makedirs(os.path.join(rdir, "evidence"))

tot = {k: sum(1 for c in cases if c["status"] == k) for k in ("passed", "failed", "error", "skipped")}
tot["total"] = len(cases)
meta = {"format": "testhive-run/1", "run_id": rid, "kind": kind, "module": mod.upper(), "env": opt.get("env", ""),
        "platform": opt.get("platform", {"mobile": "android", "api": "api", "web": "web"}[kind]),
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "host_os": platform.system(),
        "source": junit.replace(os.sep, "/"), "totals": tot}
def dump(name, obj):
    with open(os.path.join(rdir, name), "w", encoding="utf-8", newline="\n") as f: json.dump(obj, f, indent=2, ensure_ascii=False)
dump("meta.json", meta)
dump("results.json", {"format": "testhive-results/1", "run_id": rid, "cases": cases})
idx = os.path.join(base, "index.csv"); new = not os.path.exists(idx)
with open(idx, "a", encoding="utf-8", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    if new: w.writerow(["Run", "Collected", "Kind", "Module", "Env", "Platform", "Total", "Passed", "Failed", "Error", "Skipped"])
    w.writerow([rid, meta["collected_at"], kind, meta["module"], meta["env"], meta["platform"], tot["total"], tot["passed"], tot["failed"], tot["error"], tot["skipped"]])
print(f"RUN {rid}: {tot['total']} cases, {tot['passed']} passed, {tot['failed']} failed, {tot['error']} error, {tot['skipped']} skipped -> {rdir.replace(os.sep, '/')}")
PY
