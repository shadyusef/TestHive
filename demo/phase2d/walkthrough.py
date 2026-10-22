"""Presses Studio's Run buttons through its API, from the analyst's first pass to an approved design (demo --check, CI).
Uses the recorded agents (TH_CLAUDE_FAKE). Usage: python walkthrough.py <studio address with ?t=token>. Exit 1 on a problem."""
import sys, json, time, urllib.request, urllib.error
from urllib.parse import urlparse, parse_qs

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
u = urlparse(sys.argv[1]); BASE = f"{u.scheme}://{u.netloc}"; TOKEN = parse_qs(u.query)["t"][0]
failed = []


def call(path, body=None):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(), method="GET" if body is None else "POST",
                                 headers={"X-TestHive-Token": TOKEN, **({"Content-Type": "application/json"} if body is not None else {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b"{}")


def step(text, ok):
    print(("  ok    " if ok else "  WRONG ") + text)
    if not ok: failed.append(text)


def module(): return call("/api/module?m=SIGNUP")[1]


def press(expect):
    """Presses the Run button shown under Next, waits for the job, prints its progress and result."""
    d = module(); n = d["next"]
    step(f"Next says: {n['text']} -> button 'Run: {n.get('title')}'", n["run"] == expect)
    code, r = call("/api/run", {"module": "SIGNUP", "action": n["run"]})
    if code != 200: step(f"run refused: {r}", False); return None
    for _ in range(300):
        time.sleep(0.5); j = call("/api/jobs?m=SIGNUP")[1]
        if not j["job"]: break
    last = j["last"]
    lines = call("/api/job?id=" + last["id"])[1]["lines"]
    print("        " + "\n        ".join(lines[:8]) + ("\n        ..." if len(lines) > 8 else ""))
    step(f"{last['title']}: {last['status']} -> {last['summary']}", last["status"] == "done")
    return last


d = module()
if d["next"]["run"] != "analyse":  # the browser click-through already ran the first pass; use the re-run of it for the Stop test
    print("  (first pass already run in the browser click-through)")
step(f"Next says: {d['next']['text']} -> button 'Run: {d['next'].get('title')}'", d["next"]["run"] in ("analyse", "analyst-recheck"))
code, r = call("/api/run", {"module": "SIGNUP", "action": "analyse"})
code2, r2 = call("/api/run", {"module": "SIGNUP", "action": "analyse"})
step(f"a second job on the same module is refused: {r2.get('message')}", code2 == 409)
code3, r3 = call("/api/answers", {"module": "SIGNUP", "version": "x", "rows": []})
step(f"saving on the module while the agent works is paused: {r3.get('message')}", code3 == 423)
code, r = call("/api/stop", {"module": "SIGNUP", "id": r["job"]["id"]})
step(f"Stop: {r.get('message')}", code == 200)
time.sleep(1)
step("the stopped job is listed in Activity as stopped", module()["jobs"][0]["status"] == "stopped")

if module()["next"]["run"] == "analyse": press("analyse")
d = module()
step(f"the analyst's questions are in Studio: {sum(1 for g in d['analysis']['gaps'] if g['Status'] == 'Open')} open", len(d["analysis"]["gaps"]) == 35)
gap = d["analysis"]["gaps"][0]
code, r = call("/api/answers", {"module": "SIGNUP", "version": d["analysis"]["version"], "rows": [
    {"ID": gap["ID"], "Answer": "8 characters is correct; the API will be fixed.", "Answered By": "Sara (product owner)", "Status": "Answered"}]})
step(f"the human answers in Studio: {r.get('message')}", code == 200)
press("analyst-recheck")
d = module()
step("analysis waits for approval", d["stages"][0]["status"] == "awaiting_approval")
code, r = call("/api/stage", {"module": "SIGNUP", "stage": "analysis", "action": "approve", "by": "Sara (product owner)", "comment": "All High gaps answered"})
step("the human approves the analysis -> " + (r.get("message", "").splitlines() or [""])[-1], code == 200)
press("design")
press("prereview")
press("design-fix")
d = module()
code, r = call("/api/review", {"module": "SIGNUP", "version": d["design"]["version"], "cases": [{"ID": "TC-SIGNUP-001", "Review": "Accepted", "Review Comment": ""}]})
step(f"the human reviews in Studio: {r.get('message')}", code == 200)
press("design-recheck")
d = module()
step("design waits for approval", d["stages"][1]["status"] == "awaiting_approval")
code, r = call("/api/stage", {"module": "SIGNUP", "stage": "design", "action": "approve", "by": "Sara (QA lead)", "comment": "Reviewed in Studio"})
step("the human approves the design -> " + (r.get("message", "").splitlines() or [""])[-1], code == 200)
d = module()
print("  readiness: " + "; ".join(f"{i['label']}: {'yes' if i['ok'] else 'no'}" for i in d["readiness"]["items"]))
print(f"  Activity: {len(d['jobs'])} runs: " + ", ".join(f"{j['title'].split(':')[0]} {j['status']}" for j in d["jobs"][::-1]))
step("2 of 3 approvals: only the tools (phase 3) remain", [i["ok"] for i in d["readiness"]["items"]] == [True, True, False])

print("--- after the approvals: documents, changes and archiving")
code, r = call("/api/review", {"module": "SIGNUP", "version": d["design"]["version"], "cases": [{"ID": "TC-SIGNUP-002", "Review": "Remove", "Review Comment": "x"}]})
step(f"an approved design is read-only: {(r.get('errors') or [''])[0]}", code == 400)
r = call("/api/source-text?m=SIGNUP&name=prd.pdf")[1]
step(f"the text TestHive read from prd.pdf can be checked ({len(r.get('text', '').split())} words)", len(r.get("text", "").split()) > 100)
raw = urllib.request.urlopen(urllib.request.Request(BASE + "/api/source-file?m=SIGNUP&name=prd.pdf", headers={"X-TestHive-Token": TOKEN})).read()
step("the original document opens", raw.startswith(b"%PDF"))
step("a path outside the module is refused", call("/api/source-file?m=SIGNUP&name=..%2F..%2F.env")[0] == 404)
req = urllib.request.Request(BASE + "/api/source?m=SIGNUP&name=change-note.txt&by=Sara", data=b"New rule: the minimum age is 21.", method="POST",
                             headers={"X-TestHive-Token": TOKEN, "Content-Type": "application/octet-stream"})
urllib.request.urlopen(req).read()
d = module()
step(f"a document added after the approval: Next says {d['next']['text'][:70]}…", "changed after the analysis was approved" in d["next"]["text"])
step("…and the module is not ready for automation any more", not d["readiness"]["ready"])
code, r = call("/api/source-remove", {"module": "SIGNUP", "name": "change-note.txt", "by": "Sara (product owner)"})
step(f"remove a document: {r.get('message')}", code == 200 and "change-note.txt" not in [f["name"] for f in module()["sources"]["files"]])
v = call("/api/source-versions?m=SIGNUP")[1]
kept = next((x for x in v["versions"] if x["name"] == "change-note.txt"), None)
step(f"it is kept as a removed version; history: {', '.join(h['Action'] for h in v['history'][::-1])}", kept and not kept["current"])
code, r = call("/api/source-restore", {"module": "SIGNUP", "version": kept["version"], "name": "change-note.txt", "by": "Sara (product owner)"})
step(f"restore it: {r.get('message', '')[:60]}…", code == 200 and "change-note.txt" in [f["name"] for f in module()["sources"]["files"]])
code, r = call("/api/module-archive", {"module": "SIGNUP", "by": "Sara (QA lead)", "comment": "demo", "confirm": "NOPE"})
step(f"archiving needs the module code typed: {r.get('message')}", code == 400)
code, r = call("/api/module-archive", {"module": "SIGNUP", "by": "Sara (QA lead)", "comment": "Demo: archive and restore", "confirm": "signup"})
step(f"archive the module: {(r.get('message') or '').splitlines()[0]}", code == 200 and call("/api/module?m=SIGNUP")[0] == 404)
arch = call("/api/archive")[1]["archived"]
step(f"it is listed as archived ({arch[0]['files'] if arch else 0} files or folders, {arch[0]['rows'] if arch else 0} register rows)", len(arch) == 1)
code, r = call("/api/module-restore", {"archive": arch[0]["name"], "by": "Sara (QA lead)"})
d = module() if code == 200 else {}
step(f"restore it: {(r.get('message') or '').splitlines()[-1]}", code == 200 and d["stages"][1]["status"] == "approved"
     and sum(1 for c in d["design"]["cases"] if c["Status"] != "Removed") == 121)
call("/api/shutdown", {})
print("STUDIO RUN CHECK " + ("PASS" if not failed else f"FAIL ({len(failed)})"))
sys.exit(1 if failed else 0)
